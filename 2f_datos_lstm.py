"""
Paso 2f: qué datos recibe la LSTM.

    python 2f_datos_lstm.py                  # sobre panel_lstm.csv.gz (precio a 2 días)
    ATRASO_PRECIO=3 python 2f_datos_lstm.py  # sobre panel_lstm_atraso3.csv.gz

Elige con 2015-2022 y no toca el test. El modelo de prueba es XGBoost con la
configuración fija del paso 2d, sobre un resumen de cada variable: su valor en
la fila t, la media de su día y el cambio frente a 7 días antes (en las
diarias, frente a 7 y 30 días). No es la LSTM: mide cuánta información trae
cada grupo de datos. Horizontes h = D+1, D+4 y D+7 (mañana, mitad y final de
la semana).

1. Grupos (2015-2019). Entrena hasta 2017 y mide 2018; hasta 2018 y mide 2019.
   Un grupo pasa si, agregado a la base (precio y calendario), baja el error en
   los dos años y en los tres horizontes.
2. Variables (2015-2019). Dentro de los grupos que pasaron, como en la etapa 2
   del paso 2d: XGBoost con 10 variables de ruido (copias de variables al azar
   con los días barajados). Pasa la variable cuyo |SHAP| medio le gana al mejor
   ruido en los dos años, en al menos un horizonte (la LSTM pronostica toda la
   semana con una sola red).
3. Cuántos grupos (2020-2022, walk-forward anual). Partiendo de la base, se
   agregan los grupos en el orden de su mejora en el paso 1. Un grupo entra
   solo si le gana al conjunto anterior con Diebold-Mariano p < 0,05 en al
   menos un horizonte y no pierde con p < 0,05 en ninguno. Es la misma regla de
   simplicidad de SARIMAX. Como referencia se mide también el conjunto final
   sin la frescura (las variables que se publican antes que el precio, llevadas
   al día t como en el panel 2c) y las 135 variables.

Salidas, en paneles/ (con sufijo _atraso3 si D = 3):
    panel_lstm_grupos.csv          paso 1
    panel_lstm_seleccion.csv       paso 2, y qué variables quedan al final
    panel_lstm_confirmacion.csv    paso 3 y las referencias
    panel_lstm_modelo.csv.gz       lo que necesita la LSTM: identificación,
                                   calendario, objetivos y las variables finales
"""

import os
import time
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

BASE = Path(__file__).resolve().parent
D = int(os.environ.get("ATRASO_PRECIO", "2"))
SUFIJO = "" if D == 2 else f"_atraso{D}"
PANELES = BASE / "paneles"
HS = [D + 1, D + 4, D + 7]
PLIEGUES = [(2017, 2018), (2018, 2019)]       # (último año de entrenamiento, año medido)
AÑOS_VALIDACION = [2020, 2021, 2022]
INICIO = np.datetime64("2015-03-01")
NIVEL = 0.05
N_RUIDO = 10
# la de la etapa 2 del paso 2d
PARAMETROS = dict(max_depth=5, learning_rate=0.05, n_estimators=600, min_child_weight=10,
                  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                  tree_method="hist", n_jobs=-1, random_state=0)

# Grupos de datos. Los dos del despacho se separan del grupo "costo_marginal" del
# 2c porque se publican distinto: el de hoy sale la víspera, el de ayer cambia
# durante el día. Los demás son los grupos del 2c.
GRUPOS = {
    "despacho_de_hoy": ["cmg_despacho", "cmg_hoy_vs_precio", "gen_programada_rel",
                        "disp_decl_hoy_rel", "disp_termica_frac"],
    "despacho_de_ayer": ["cmg_redespacho", "ajuste_cmg", "redespacho_vs_programa",
                         "disp_real_vs_decl", "error_cmg_despacho"],
    "demanda": ["demanda", "dem_no_regulada_frac", "margen_declarado", "pron_demanda",
                "error_pron_demanda"],
    "ofertas": ["curva_de_merito", "curva_del_dia", "planta_marginal"],
    **dict.fromkeys(["aportes", "embalses", "generacion", "mezcla_por_planta",
                     "red_y_contratos", "lluvia", "el_nino", "ideam", "sistema",
                     "interaccion"]),
}
CALENDARIO = ["hora_sin", "hora_cos", "dia_semana", "dia_semana_sin", "dia_semana_cos",
              "es_festivo", "mes", "mes_sin", "mes_cos", "dia_ano_sin", "dia_ano_cos"]


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def leer():
    info = pd.read_csv(PANELES / f"panel_lstm_variables{SUFIJO}.csv").set_index("variable")
    info = info[info["entra"]]
    panel = pd.read_csv(PANELES / f"panel_lstm{SUFIJO}.csv.gz", parse_dates=["fecha"])
    panel = panel.sort_values(["fecha", "hora"]).reset_index(drop=True)
    assert (panel.groupby("fecha").size() == 24).all()
    return panel, info


def grupos(info):
    """Variables de cada grupo; las de despacho y demanda se sacan de sus grupos del 2c."""
    fijas = {v for n in ("despacho_de_hoy", "despacho_de_ayer", "demanda") for v in GRUPOS[n]}
    g = {}
    for n, lista in GRUPOS.items():
        if n in ("despacho_de_hoy", "despacho_de_ayer", "demanda"):
            g[n] = lista
        elif n == "ofertas":
            g[n] = info.index[info["grupo"].isin(lista)].tolist()
        else:
            g[n] = [v for v in info.index[info["grupo"] == n] if v not in fijas]
    sueltas = set(info.index) - {"lp"} - {v for l in g.values() for v in l}
    assert not sueltas, f"variables sin grupo: {sueltas}"
    return g


def atras(x, filas):
    o = np.full(len(x), np.nan)
    o[filas:] = x[:-filas]
    return o


def media_dia(x):
    m = x.reshape(-1, 24)
    n = np.isfinite(m).sum(axis=1)
    s = np.where(np.isfinite(m), m, 0).sum(axis=1)
    return np.repeat(np.where(n > 0, s / np.maximum(n, 1), np.nan), 24)


def resumen(panel, info):
    """Tres columnas por variable y qué columnas son de cada una."""
    col, de = {}, {}
    for v in info.index:
        if v == "lp":
            continue
        x = panel[v].to_numpy(float)
        col[v] = x
        col[f"{v}__c7"] = x - atras(x, 24 * 7)
        if info.loc[v, "tipo"] == "horaria":
            col[f"{v}__dia"] = media_dia(x)
            de[v] = [v, f"{v}__c7", f"{v}__dia"]
        else:
            col[f"{v}__c30"] = x - atras(x, 24 * 30)
            de[v] = [v, f"{v}__c7", f"{v}__c30"]
    return pd.DataFrame(col).astype(np.float32), de


def base(panel, h):
    """Precio y calendario: lo que tiene cualquier versión."""
    lp = panel["lp"].to_numpy(float)
    semana = np.column_stack([atras(lp, 24 * j) if j else lp for j in range(7)])
    k = h - D
    b = pd.DataFrame({
        "lp": lp, "lp_dia": media_dia(lp), "dlp1": lp - atras(lp, 24), "dlp7": lp - atras(lp, 24 * 7),
        "lp_sd_dia": np.repeat(np.nanstd(lp.reshape(-1, 24), axis=1), 24),
        "lp_vs_ma7": lp - np.nanmean(semana, axis=1),
        "hora": panel["hora"], "dia_semana": panel["dia_semana"], "mes_sin": panel["mes_sin"],
        "mes_cos": panel["mes_cos"], "es_festivo": panel["es_festivo"],
        "dia_semana_obj": panel[f"dia_semana_k{k}"], "es_festivo_obj": panel[f"es_festivo_k{k}"],
    })
    return b.astype(np.float32)


# ---------------------------------------------------------------------------
# Medir
# ---------------------------------------------------------------------------

def filas(F, y, h, ultimo_año_entrena, año):
    corte = np.datetime64(f"{ultimo_año_entrena}-12-31")
    tr = (F >= INICIO) & (F <= corte - np.timedelta64(h, "D")) & ~np.isnan(y)
    ev = (F > corte) & (F <= np.datetime64(f"{año}-12-31") - np.timedelta64(h, "D")) & ~np.isnan(y)
    return tr, ev


def errores_por_dia(F, y, A, tr, ev):
    m = xgb.XGBRegressor(**PARAMETROS).fit(A[tr], y[tr])
    e = y[ev] - m.predict(A[ev])
    return pd.DataFrame({"f": F[ev], "e2": e ** 2, "i2": y[ev] ** 2}).groupby("f").mean()


def media_y_ee(d, L):
    """Promedio de una serie diaria y su error estándar de Newey-West con L rezagos."""
    n = len(d)
    u = d - d.mean()
    v = np.mean(u * u)
    for l in range(1, min(L, n - 1) + 1):
        v += 2 * (1 - l / (L + 1)) * np.mean(u[l:] * u[:-l])
    return d.mean(), np.sqrt(v / n)


def diebold_mariano(e2_a, e2_b, h):
    """t y p de la diferencia de pérdida diaria; t negativo: a es mejor que b."""
    m, ee = media_y_ee((e2_a - e2_b).to_numpy(), h - 1 + 7)
    t = m / ee
    return t, 1 - erf(abs(t) / sqrt(2))


def rmse(d, col="e2"):
    return float(np.sqrt(d[col].mean()))


# ---------------------------------------------------------------------------
# Pasos
# ---------------------------------------------------------------------------

def paso_grupos(panel, R, de, g):
    F = panel["fecha"].to_numpy("datetime64[D]")
    res = []
    for h in HS:
        y = panel[f"y_h{h}"].to_numpy(float)
        B = base(panel, h)
        for ultimo, año in PLIEGUES:
            tr, ev = filas(F, y, h, ultimo, año)
            ref = errores_por_dia(F, y, B.to_numpy(np.float32), tr, ev)
            for n, vs in g.items():
                A = pd.concat([B, R[[c for v in vs for c in de[v]]]], axis=1).to_numpy(np.float32)
                d = errores_por_dia(F, y, A, tr, ev)
                t, _ = diebold_mariano(d["e2"], ref["e2"], h)
                res.append(dict(grupo=n, h=h, año=año, cambio_rmse=100 * (rmse(d) / rmse(ref) - 1), t=t))
            print(f"   h = {h}, {año}: listo", flush=True)
    t = pd.DataFrame(res)
    resumen_g = t.groupby("grupo").agg(cambio_medio=("cambio_rmse", "mean"),
                                       mejora_en=("cambio_rmse", lambda x: int((x < 0).sum())))
    resumen_g["pasa"] = resumen_g["mejora_en"] == len(HS) * len(PLIEGUES)
    return t, resumen_g.sort_values("cambio_medio")


def paso_variables(panel, R, de, g, elegidos):
    variables = [v for n in elegidos for v in g[n]]
    rng = np.random.default_rng(0)
    dias = len(panel) // 24
    ruido, de_ruido = {}, {}
    for k, v in enumerate(rng.choice(variables, N_RUIDO, replace=False)):
        orden = rng.permutation(dias)
        fila = (orden[:, None] * 24 + np.arange(24)).ravel()      # se barajan días enteros
        de_ruido[f"ruido{k}"] = [f"ruido{k}__{c}" for c in de[v]]
        for c in de[v]:
            ruido[f"ruido{k}__{c}"] = R[c].to_numpy()[fila]
    Z = pd.concat([R[[c for v in variables for c in de[v]]], pd.DataFrame(ruido)], axis=1)
    todas = {**{v: de[v] for v in variables}, **de_ruido}
    F = panel["fecha"].to_numpy("datetime64[D]")
    imp = []
    for h in HS:
        y = panel[f"y_h{h}"].to_numpy(float)
        A = pd.concat([base(panel, h), Z], axis=1)
        nombres, A = A.columns, A.to_numpy(np.float32)
        for ultimo, año in PLIEGUES:
            tr, ev = filas(F, y, h, ultimo, año)
            m = xgb.XGBRegressor(**PARAMETROS).fit(A[tr], y[tr])
            shap = m.get_booster().predict(xgb.DMatrix(A[ev]), pred_contribs=True)[:, :-1]
            s = pd.Series(np.abs(shap).mean(axis=0), index=nombres)
            imp += [dict(variable=v, h=h, año=año, importancia=float(s[c].sum())) for v, c in todas.items()]
    piv = pd.DataFrame(imp).pivot_table(index="variable", columns=["h", "año"], values="importancia")
    es_ruido = [i for i in piv.index if i.startswith("ruido")]
    reales = piv.drop(es_ruido)
    gana = reales.gt(piv.loc[es_ruido].max())
    por_h = pd.DataFrame({f"gana_h{h}": gana[h].all(axis=1) for h in HS})
    grupo_de = {v: n for n in elegidos for v in g[n]}
    sel = pd.DataFrame({"grupo": pd.Series(grupo_de), **por_h,
                        "importancia_media": reales.mean(axis=1)})
    sel["pasa_ruido"] = por_h.any(axis=1)
    return sel.sort_values("importancia_media", ascending=False)


def paso_conjuntos(panel, info, R, de, orden, sel):
    """Agrega grupos de a uno en 2020-2022 y deja el más simple que no pierde."""
    F = panel["fecha"].to_numpy("datetime64[D]")
    pasan = sel.index[sel["pasa_ruido"]]

    def medir(vars_, R_=R):
        err = {}
        for h in HS:
            y = panel[f"y_h{h}"].to_numpy(float)
            A = pd.concat([base(panel, h), R_[[c for v in vars_ for c in de[v]]]], axis=1).to_numpy(np.float32)
            err[h] = pd.concat([errores_por_dia(F, y, A, *filas(F, y, h, año - 1, año))
                                for año in AÑOS_VALIDACION])
        return err

    def fila(nombre, vars_, err, contra=None):
        f = dict(conjunto=nombre, n_variables=len(vars_))
        for h in HS:
            f[f"mejora_h{h}"] = 100 * (1 - rmse(err[h]) / rmse(err[h], "i2"))
            if contra is not None:
                f[f"t_h{h}"], f[f"p_h{h}"] = diebold_mariano(err[h]["e2"], contra[h]["e2"], h)
        return f

    actual, vars_actual = medir([]), []
    res = [fila("base", [], actual)]
    for n in orden:
        nuevas = vars_actual + [v for v in pasan if sel.loc[v, "grupo"] == n]
        err = medir(nuevas)
        f = fila(f"+ {n}", nuevas, err, actual)
        gana = any(f[f"p_h{h}"] < NIVEL and f[f"t_h{h}"] < 0 for h in HS)
        pierde = any(f[f"p_h{h}"] < NIVEL and f[f"t_h{h}"] > 0 for h in HS)
        f["entra"] = gana and not pierde
        res.append(f)
        print(f"   + {n}: {'entra' if f['entra'] else 'no entra'}", flush=True)
        if f["entra"]:
            actual, vars_actual = err, nuevas
    finales = vars_actual

    # referencias: el conjunto final sin frescura, y las 135
    frescas = [v for v in finales if info.loc[v, "dias_frente_al_precio"] < 0]
    viejo = panel.copy()
    for v in frescas:
        viejo[v] = viejo[v].shift(-24 * int(info.loc[v, "dias_frente_al_precio"]))
    Rv, _ = resumen(viejo, info.loc[["lp"] + frescas])
    R_sin = pd.concat([R[[c for v in finales if v not in frescas for c in de[v]]],
                       Rv[[c for v in frescas for c in de[v]]]], axis=1)
    res.append(fila("referencia: finales sin frescura", finales, medir(finales, R_sin), actual))
    todas = [v for v in info.index if v != "lp"]
    res.append(fila("referencia: las 135", todas, medir(todas), actual))
    return pd.DataFrame(res), finales


def panel_modelo(panel, finales, sel):
    """Lo que necesita la LSTM, en un archivo chico para subir a Colab."""
    objetivos = [f"y_h{D + k}" for k in range(1, 8)]
    objetivo_cal = [f"{c}_k{k}" for k in range(1, 8) for c in ("dia_semana", "es_festivo")]
    otras = [v for v in sel.index[sel["pasa_ruido"]] if v not in finales]
    cols = (["fecha", "hora", "bloque", "precio", "lp"] + CALENDARIO + objetivo_cal + objetivos
            + finales + otras)
    return panel[cols], otras


# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print(f"Datos para la LSTM, con el precio a {D} días (h = {', '.join(map(str, HS))})")
    panel, info = leer()
    g = grupos(info)
    R, de = resumen(panel, info)

    print("1. Grupos, 2015-2019")
    detalle, por_grupo = paso_grupos(panel, R, de, g)
    detalle.to_csv(PANELES / f"panel_lstm_grupos{SUFIJO}.csv", index=False)
    print(por_grupo.round(2).to_string())
    elegidos = por_grupo.index[por_grupo["pasa"]].tolist()

    print(f"2. Variables de {', '.join(elegidos)}, 2015-2019")
    sel = paso_variables(panel, R, de, g, elegidos)
    print(f"   pasan el ruido {int(sel['pasa_ruido'].sum())} de {len(sel)}")

    print("3. Conjuntos, 2020-2022")
    conf, finales = paso_conjuntos(panel, info, R, de, elegidos, sel)
    conf.to_csv(PANELES / f"panel_lstm_confirmacion{SUFIJO}.csv", index=False)
    sel["final"] = sel.index.isin(finales)
    sel.to_csv(PANELES / f"panel_lstm_seleccion{SUFIJO}.csv")
    cols = ["conjunto", "n_variables"] + [f"mejora_h{h}" for h in HS] + [f"t_h{h}" for h in HS] + ["entra"]
    print(conf[cols].round(2).to_string(index=False))

    modelo, otras = panel_modelo(panel, finales, sel)
    ruta = PANELES / f"panel_lstm_modelo{SUFIJO}.csv.gz"
    modelo.to_csv(ruta, index=False, compression="gzip", float_format="%.6g")
    print(f"\nfinales ({len(finales)}): {', '.join(finales)}")
    print(f"pasaron el ruido pero no entraron ({len(otras)}): {', '.join(otras)}")
    print(f"{ruta.name}: {modelo.shape[0]:,} filas x {modelo.shape[1]} columnas, "
          f"{ruta.stat().st_size / 1e6:.1f} MB [{time.time() - t0:.0f} s]")


if __name__ == "__main__":
    main()
