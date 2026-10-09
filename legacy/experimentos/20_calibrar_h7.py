"""
================================================================================
CALIBRACION DEL MODELO A 7 DIAS — dejarlo listo para usar
================================================================================

EL PROBLEMA
-----------
Los cuantiles que produce XGBoost estan mal calibrados: el intervalo que dice
80% cubre 72%. Un intervalo asi es peor que no tener intervalo, porque da falsa
confianza justo cuando se usa para decidir.

LA SOLUCION: CONFORMAL CUANTILICO ADAPTATIVO
--------------------------------------------
La idea del conformal es simple: se mide cuanto se equivoco el intervalo en el
pasado reciente y se ensancha lo necesario para que cubra lo que promete.

Para cada dia t se calcula el "score de conformidad" de los casos ya resueltos:

    E = max( q_bajo(x) - y ,  y - q_alto(x) )

E es positivo cuando el valor real quedo FUERA del intervalo, y su magnitud dice
por cuanto. El cuantil (1-alfa) de esos E es lo que hay que sumar y restar para
que el intervalo cubra de verdad.

POR QUE ADAPTATIVO Y NO ESTATICO
--------------------------------
El conformal clasico supone intercambiabilidad: que el futuro se parezca al
pasado. Aqui NO se cumple, y esta medido: 2023-2026 tuvo colas mas gruesas que
2015-2022, por eso hasta la climatologia se queda corta (cubre 63-75%).

Una correccion fija calculada en 2020-2022 volveria a quedarse corta en 2026.
La version adaptativa recalibra con una ventana movil reciente, asi que se
ajusta sola cuando cambia el regimen.

ANTI-FUGA
---------
Para predecir y_t = log P(t+h) - log P(t), en el dia t solo se conocen los
resultados de los origenes s con s+h <= t, o sea s <= t-h. La ventana de
calibracion en t es [t-h-N, t-h]. Nunca entra un caso cuyo desenlace todavia
no ocurrio.

Uso
---
  python 20_calibrar_h7.py
================================================================================
"""

import importlib.util
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

H = 7
K = 30                      # elegido por la validacion en 19_cuantilica.py
CUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]
NIVEL = 0.80                # cobertura objetivo del intervalo central
VENTANAS_CAL = [90, 180, 365]
SEMILLA = 42

FIN_SELECCION = pd.Timestamp("2019-12-31")
INI_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

EXCLUIR = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]
UMBRALES = [300, 500, 800]


def pinball(y, pred, q):
    d = y - pred
    return float(np.mean(np.maximum(q * d, (q - 1) * d)))


def ranquear(X, y):
    tscv = TimeSeriesSplit(n_splits=3, gap=H)
    Xs = StandardScaler().fit_transform(X)
    la = LassoCV(cv=tscv, max_iter=20000, random_state=SEMILLA, n_jobs=-1).fit(Xs, y)
    r1 = pd.Series(np.abs(la.coef_), index=X.columns).rank(ascending=False)
    mo = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.03,
                          subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
                          reg_lambda=3.0, random_state=SEMILLA, n_jobs=-1,
                          tree_method="hist").fit(X, y)
    r2 = pd.Series(mo.feature_importances_, index=X.columns).rank(ascending=False)
    return ((r1 + r2) / 2).sort_values()


def entrenar(entrena, cols, params):
    modelos = {}
    for q in CUANTILES:
        modelos[q] = xgb.XGBRegressor(objective="reg:quantileerror", quantile_alpha=q,
                                      random_state=SEMILLA, n_jobs=-1,
                                      tree_method="hist", **params).fit(
            entrena[cols], entrena["y"])
    return modelos


def predecir(modelos, X, cols):
    d = pd.DataFrame({q: m.predict(X[cols]) for q, m in modelos.items()}, index=X.index)
    d.values.sort(axis=1)
    return d


def calibrar_adaptativo(q_todo, y_todo, indice_prueba, ventana):
    """
    Para cada dia de prueba, ensancha el intervalo con los scores de conformidad
    de los casos ya resueltos en los ultimos `ventana` dias.
    """
    lo_col, hi_col = CUANTILES[0], CUANTILES[-1]
    # score: cuanto se salio el valor real del intervalo (negativo = quedo dentro)
    score = np.maximum(q_todo[lo_col] - y_todo, y_todo - q_todo[hi_col])

    ajustes = pd.Series(index=indice_prueba, dtype=float)
    for t in indice_prueba:
        fin = t - pd.Timedelta(days=H)          # ultimo origen ya resuelto en t
        ini = fin - pd.Timedelta(days=ventana)
        s = score.loc[(score.index > ini) & (score.index <= fin)].dropna()
        if len(s) < 20:
            ajustes[t] = 0.0
            continue
        n = len(s)
        nivel = min(1.0, np.ceil((n + 1) * NIVEL) / n)   # correccion de muestra finita
        ajustes[t] = float(np.quantile(s, nivel))
    return ajustes


def evaluar(qp, ajuste, prueba, precio):
    y = prueba["y"]
    lo = qp[CUANTILES[0]] - ajuste
    hi = qp[CUANTILES[-1]] + ajuste

    r = {"cobertura": float(((y >= lo) & (y <= hi)).mean()),
         "ancho_log": float(np.mean(hi - lo)),
         "pinball": float(np.mean([pinball(y, qp[q], q) for q in CUANTILES]))}

    precio_hoy = precio.reindex(prueba.index)
    precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=H))
    precio_fut.index = prueba.index
    ok = precio_fut.notna()
    r["ancho_cop"] = float(np.mean(precio_hoy[ok] * (np.exp(hi[ok]) - np.exp(lo[ok]))))

    for u in UMBRALES:
        obj = np.log(u) - np.log(precio_hoy)
        p = prob_supera(qp, ajuste, obj)
        real = (precio_fut > u).astype(float)
        r[f"brier_{u}"] = float(np.mean((p[ok] - real[ok]) ** 2))
    return r


def prob_supera(qp, ajuste, objetivo):
    """P(y > objetivo) interpolando sobre los cuantiles ya ensanchados."""
    qs = np.array(CUANTILES)
    M = qp[CUANTILES].values.copy()
    M[:, 0] -= ajuste.values
    M[:, -1] += ajuste.values
    M.sort(axis=1)
    obj = np.asarray(objetivo, dtype=float)
    out = np.empty(len(obj))
    for i in range(len(obj)):
        out[i] = 1.0 - np.interp(obj[i], M[i], qs, left=0.0, right=1.0)
    return pd.Series(out, index=qp.index)


def main():
    print("=" * 80)
    print(f"CALIBRACION DEL MODELO A {H} DIAS")
    print("=" * 80)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in EXCLUIR if c in df.columns])
    X, precio, log_precio = h10.construir_features(df)
    COLUMNAS = h10.limpiar(X.loc[:FIN_SELECCION].dropna())

    y_h = (log_precio.shift(-H) - log_precio).rename("y")
    datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

    orden = ranquear(datos.loc[:FIN_SELECCION, COLUMNAS],
                     datos.loc[:FIN_SELECCION, "y"])
    cols = list(orden.index[:K])
    params = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))[str(H)]
    print(f"[modelo]  {K} variables, {len(CUANTILES)} cuantiles")

    # --- elegir la ventana de calibracion en la VALIDACION -------------------
    print("\n" + "-" * 80)
    print("PASO 1 — elegir la ventana de calibracion en 2020-2022")
    print("-" * 80)
    ent_v = datos.loc[:INI_VALIDACION - pd.Timedelta(days=H + 1)]
    val = datos.loc[INI_VALIDACION:FIN_VALIDACION]
    mod_v = entrenar(ent_v, cols, params)

    # scores sobre todo lo anterior a la validacion, mas la validacion misma
    hist_v = datos.loc[:FIN_VALIDACION]
    q_hist_v = predecir(mod_v, hist_v, cols)

    mejor, mejor_err = None, np.inf
    for w in VENTANAS_CAL:
        aj = calibrar_adaptativo(q_hist_v, hist_v["y"], val.index, w)
        r = evaluar(predecir(mod_v, val, cols), aj, val, precio)
        err = abs(r["cobertura"] - NIVEL)
        print(f"  ventana {w:3d} dias  cobertura {r['cobertura']:.1%}  "
              f"ancho {r['ancho_cop']:.0f} COP  (error {err:.3f})")
        if err < mejor_err:
            mejor, mejor_err = w, err
    print(f"  ==> ventana elegida: {mejor} dias")

    # --- medir en prueba -----------------------------------------------------
    print("\n" + "-" * 80)
    print("PASO 2 — medicion")
    print("-" * 80)

    filas = []
    for etapa, ini, fin in [("2023-2025", INI_PRUEBA, INI_2026 - pd.Timedelta(days=1)),
                            ("2026", INI_2026, datos.index.max())]:
        entrena = datos.loc[:ini - pd.Timedelta(days=H + 1)]
        prueba = datos.loc[ini:fin]
        modelos = entrenar(entrena, cols, params)

        hist = datos.loc[:fin]
        q_hist = predecir(modelos, hist, cols)
        aj = calibrar_adaptativo(q_hist, hist["y"], prueba.index, mejor)

        qp = predecir(modelos, prueba, cols)
        sin = evaluar(qp, pd.Series(0.0, index=prueba.index), prueba, precio)
        con = evaluar(qp, aj, prueba, precio)

        print(f"\n  {etapa} ({len(prueba)} dias)")
        print(f"    cobertura 80%   sin calibrar {sin['cobertura']:.1%}  ->  "
              f"calibrado {con['cobertura']:.1%}   (objetivo {NIVEL:.0%})")
        print(f"    ancho del intervalo  {sin['ancho_cop']:.0f}  ->  "
              f"{con['ancho_cop']:.0f} COP/kWh")
        print(f"    ajuste medio aplicado: {aj.mean():+.4f} en log")
        for u in UMBRALES:
            print(f"    Brier P(>{u:4d})   {sin[f'brier_{u}']:.4f}  ->  "
                  f"{con[f'brier_{u}']:.4f}")

        filas.append({"etapa": etapa, "n": len(prueba), "ventana": mejor,
                      **{f"sin_{k}": v for k, v in sin.items()},
                      **{f"cal_{k}": v for k, v in con.items()}})

        if etapa == "2026":
            graficar(qp, aj, prueba, precio)
            ejemplo(qp, aj, prueba, precio)

    pd.DataFrame(filas).to_csv(SALIDA / f"calibracion_h{H}.csv", index=False)
    print(f"\n[salida] {SALIDA/f'calibracion_h{H}.csv'}, "
          f"{SALIDA/f'calibracion_h{H}_2026.png'}")


def ejemplo(qp, aj, prueba, precio):
    """Como se veria el producto final en uso."""
    print("\n" + "=" * 80)
    print("EJEMPLO DE USO — ultimos dias disponibles")
    print("=" * 80)
    hoy = precio.reindex(prueba.index)
    for t in prueba.index[-5:]:
        p0 = hoy[t]
        lo = p0 * np.exp(qp.loc[t, CUANTILES[0]] - aj[t])
        med = p0 * np.exp(qp.loc[t, 0.50])
        hi = p0 * np.exp(qp.loc[t, CUANTILES[-1]] + aj[t])
        obj = np.log(500) - np.log(p0)
        p500 = prob_supera(qp.loc[[t]], aj.loc[[t]], pd.Series([obj], index=[t]))[t]
        real = precio.get(t + pd.Timedelta(days=H), np.nan)
        print(f"  {t.date()}  hoy {p0:6.0f}  ->  a {H} dias: "
              f"mediana {med:6.0f}, 80% en [{lo:5.0f}, {hi:6.0f}]  "
              f"P(>500)={p500:.0%}   real {real:6.0f}")


def graficar(qp, aj, prueba, precio):
    hoy = precio.reindex(prueba.index)
    fut = prueba.index + pd.Timedelta(days=H)
    real = precio.reindex(fut)
    lo = hoy.values * np.exp(qp[CUANTILES[0]].values - aj.values)
    hi = hoy.values * np.exp(qp[CUANTILES[-1]].values + aj.values)
    med = hoy.values * np.exp(qp[0.50].values)

    fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    ax[0].fill_between(fut, lo, hi, alpha=0.3, color="tab:red",
                       label="intervalo 80% calibrado")
    ax[0].plot(fut, med, color="tab:red", lw=1, label="mediana")
    ax[0].plot(fut, real.values, color="k", lw=1.2, label="real")
    dentro = ((real.values >= lo) & (real.values <= hi))
    ax[0].set_title(f"Pronostico a {H} dias en 2026 — cobertura empirica "
                    f"{np.nanmean(dentro):.1%}")
    ax[0].set_ylabel("COP/kWh"); ax[0].legend(fontsize=8)

    obj = np.log(500) - np.log(hoy)
    p500 = prob_supera(qp, aj, obj)
    ax[1].plot(fut, p500.values, color="tab:purple", lw=1.2, label="P(precio > 500)")
    ax[1].plot(fut, (real.values > 500).astype(float), color="k", lw=0.8,
               alpha=0.5, label="ocurrio")
    ax[1].set_ylabel("probabilidad"); ax[1].legend(fontsize=8)
    ax[1].set_title("La salida que sirve para decidir")
    plt.tight_layout()
    plt.savefig(SALIDA / f"calibracion_h{H}_2026.png", dpi=110)


if __name__ == "__main__":
    main()
