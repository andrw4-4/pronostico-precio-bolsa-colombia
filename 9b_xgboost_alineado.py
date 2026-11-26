"""
Paso 9b: XGBoost con la información alineada a su publicación.

    python 9b_xgboost_alineado.py

Responde la pregunta de la revisión del 26 de noviembre de 2026: cuánto de la ventaja de la LSTM
viene de la red y cuánto de la información. Es el mismo XGBoost de 4_modelo_xgboost.ipynb, con la
selección de columnas y los hiperparámetros congelados (configuracion_final.json), al que solo se
le agregan las nueve variables de los bloques 3 y 4 de la LSTM, tal como entran a la red: el valor
más reciente ya publicado el día del pronóstico y los de los dos días anteriores (27 columnas).
No se repite la selección ni la búsqueda: lo único que cambia es la información.

Corre dos versiones con el mismo código:
    corte_t     el XGBoost de la tesis, solo en 2020-2022, para tener sus pronósticos fila por fila
                con reentrenamiento mensual (en 2023-2026 ya están guardados y no se repiten)
    alineado    el XGBoost con las 27 columnas nuevas, en 2020-2022 y en 2023-2026

Las cifras de 2023-2026 del XGBoost alineado son exploratorias: ese periodo ya se había abierto
cuando se decidió correrlo. La purga, las filas y las medidas son las del notebook 4.

Salidas, en resultados/modelo_xgboost_alineado/.
"""
import json
import shutil
import sys
import time
import warnings

import holidays
import numpy as np
import pandas as pd
import xgboost as xgb

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
PANELES = ev.PANELES
CONGELADO = ev.RES / "modelo_xgboost"
SALIDA = ev.RES / "modelo_xgboost_alineado"
HORARIAS = ["cmg_despacho", "disp_decl_hoy_rel", "cmg_hoy_vs_precio", "frac_termica_prog", "brecha_escasez",
            "presion_hidro_horaria"]
DIARIAS = ["aportes_media_hist", "volumen_util_pct", "dias_autonomia"]
DIAS_ATRAS = (0, 1, 2)
ANCLAS = [1, 2, 3, 4, 5, 6, 7, 14, 30]
DISPOSITIVO = "cuda" if shutil.which("nvidia-smi") else "cpu"
COMUNES = dict(tree_method="hist", device=DISPOSITIVO, n_jobs=-1, random_state=0, learning_rate=0.03,
               eval_metric="rmse")
HUBER_SLOPE, VENTANA_CORTA = 0.2, 1096


def ancla(h):
    return h if h <= 7 else 7 if h <= 10 else 14 if h <= 21 else 30


class Datos:
    """La tabla del notebook 4 (panel 2d) más las 27 columnas alineadas del panel de la LSTM."""

    def __init__(self, hs):
        tabla = pd.read_csv(PANELES / "panel_horario_modelo.csv.gz", parse_dates=["fecha"])
        self.seleccion = pd.read_csv(PANELES / "panel_horario_modelo_columnas.csv")
        assert len(tabla) == tabla["fecha"].nunique() * 24
        self.F = tabla["fecha"].to_numpy("datetime64[D]")
        self.hora = tabla["hora"].to_numpy()
        lp = np.log(tabla["precio"].to_numpy(float))
        self.Y = {}
        for h in hs:
            self.Y[h] = np.full(len(lp), np.nan)
            self.Y[h][:-24 * h] = lp[24 * h:] - lp[:-24 * h]
        # calendario del día objetivo para los horizontes que no son ancla, con la fórmula del notebook 4
        fechas = pd.DatetimeIndex(tabla["fecha"])
        dias = pd.date_range(fechas.min(), fechas.max() + pd.offsets.Day(60))
        co = holidays.Colombia(years=range(dias[0].year, dias[-1].year + 1))
        es_festivo = pd.Series([int(d in co) for d in dias], index=dias)
        nuevas = {}
        for h in hs:
            if h in ANCLAS:
                continue
            objetivo = fechas.shift(h, freq="D")
            angulo = 2 * np.pi * objetivo.dayofweek.to_numpy() / 7
            nuevas[f"dia_semana_h{h}"] = objetivo.dayofweek.to_numpy()
            nuevas[f"es_festivo_h{h}"] = es_festivo.reindex(objetivo).to_numpy()
            nuevas[f"dia_semana_h{h}_sin"] = np.sin(angulo)
            nuevas[f"dia_semana_h{h}_cos"] = np.cos(angulo)
        # las nueve variables de los bloques 3 y 4, como están en el panel de la LSTM (valor del día R - L)
        b = pd.read_csv(PANELES / "panel_lstm_bloques.csv.gz", usecols=["fecha", "hora"] + HORARIAS + DIARIAS,
                        parse_dates=["fecha"])
        b = tabla[["fecha", "hora"]].merge(b, on=["fecha", "hora"], how="left", validate="one_to_one")
        self.alineadas = []
        for v in HORARIAS + DIARIAS:
            x = b[v].to_numpy(float)
            for k in DIAS_ATRAS:
                col = f"{v}_alin{k}"
                nuevas[col] = np.concatenate([np.full(24 * k, np.nan), x[:len(x) - 24 * k]])
                self.alineadas.append(col)
        tabla = pd.concat([tabla, pd.DataFrame(nuevas)], axis=1)
        numericas = [c for c in tabla.columns if c not in ("fecha", "bloque", "precio") and not c.startswith("y_h")]
        self.M = tabla[numericas].to_numpy(np.float32)
        self.POS = {c: j for j, c in enumerate(numericas)}
        self.techo = None

    def columnas(self, h, version):
        a = ancla(h)
        s = self.seleccion
        c = s[s[f"entra_h{a}"]].sort_values(f"orden_h{a}", na_position="first")["columna"]
        cols = [x.replace(f"_h{a}", f"_h{h}") if x.startswith(("dia_semana_h", "es_festivo_h")) else x for x in c]
        return cols + (self.alineadas if version == "alineado" else [])

    def para_entrenar(self, h, corte, ventana=None):
        m = (self.F <= corte - (h + 1)) & ~np.isnan(self.Y[h])
        return m if ventana is None else m & (self.F >= corte - ventana)

    def para_medir(self, h, ini, fin, tope):
        return (self.F >= ini) & (self.F <= fin) & (self.F + h <= tope) & ~np.isnan(self.Y[h])

    def matriz(self, filas, h, cols):
        assert (self.F[filas] + h).max() <= self.techo, f"objetivo posterior a {self.techo}"
        i = np.flatnonzero(filas)
        return self.M[np.ix_(i, [self.POS[c] for c in cols])], self.Y[h][i]


def parametros(h, config):
    cfg = config[str(ancla(h))]
    p = dict(cfg["parametros"])
    if cfg["variante"] == "pseudo_huber":
        p.update(objective="reg:pseudohubererror", huber_slope=HUBER_SLOPE)
    assert cfg["variante"] in ("base", "pseudo_huber", "tres_años")
    return p, (VENTANA_CORTA if cfg["variante"] == "tres_años" else None)


def walk_forward(D, h, version, config, desde, hasta):
    """Reentrena el primer día de cada mes y pronostica desde cada día del mes, como en el notebook 4."""
    cols = D.columnas(h, version)
    p, ventana = parametros(h, config)
    cortes = list(pd.date_range(desde, hasta, freq="MS").to_numpy().astype("datetime64[D]"))
    fin = np.datetime64(hasta)
    partes = []
    for ini, sig in zip(cortes, cortes[1:] + [fin + 1]):
        medir = D.para_medir(h, ini, sig - 1, fin)
        if not medir.any():
            continue
        A, y = D.matriz(D.para_entrenar(h, ini, ventana), h, cols)
        m = xgb.XGBRegressor(**{**COMUNES, **p}).fit(A, y)
        i = np.flatnonzero(medir)
        partes.append(pd.DataFrame({"fecha": D.F[i], "hora": D.hora[i], "h": h,
                                    "y_hat": m.predict(D.matriz(medir, h, cols)[0])}))
    return pd.concat(partes, ignore_index=True)


def comprobar_fuga(D, config):
    """Alterar todo objetivo desde el corte en adelante no puede cambiar el pronóstico."""
    h, corte = 7, np.datetime64("2021-06-01")
    cols = D.columnas(h, "alineado")
    p = dict(max_depth=3, n_estimators=50, min_child_weight=10, subsample=1.0, colsample_bytree=1.0)
    tr = D.para_entrenar(h, corte)
    medir = D.para_medir(h, corte, corte + 29, np.datetime64("2022-12-31"))
    assert (D.F[tr] + h).max() < corte
    antes = xgb.XGBRegressor(**{**COMUNES, **p}).fit(*D.matriz(tr, h, cols)).predict(D.matriz(medir, h, cols)[0])
    original = D.Y[h].copy()
    try:
        D.Y[h][D.F + h >= corte] += 5.0
        despues = xgb.XGBRegressor(**{**COMUNES, **p}).fit(*D.matriz(tr, h, cols)).predict(D.matriz(medir, h, cols)[0])
    finally:
        D.Y[h] = original
    assert np.array_equal(antes, despues), "hay fuga: el pronóstico cambió"
    print("sin fuga: alterar objetivos posteriores al corte no cambia el pronóstico", flush=True)


def comprobar_congelado(tabla):
    """corte_t en 2020-2022 tiene que dar el mismo error diario que guardó la etapa 3 del notebook 4."""
    precio = ev.precios()
    m = ev.marco(*ev.PERIODOS["2020-2022"], precio=precio).merge(tabla, on=ev.CLAVES, validate="one_to_one")
    m["e2"] = (m["y"] - m["y_hat_corte_t"]) ** 2
    filas = []
    for a in (3, 4, 5, 6, 7):
        viejo = pd.read_csv(CONGELADO / f"etapa3_h{a}.csv.gz", parse_dates=["fecha"])
        nuevo = m[m["h"] == a].groupby("fecha")["e2"].mean()
        # la etapa 3 guardó las tres finalistas; la congelada es la que coincide
        dif = {c: float((g.set_index("fecha")["mse_dia"] - nuevo).abs().max()) for c, g in viejo.groupby("combinacion")}
        filas.append({"h": a, "combinacion": min(dif, key=dif.get), "diferencia_maxima": min(dif.values())})
    r = pd.DataFrame(filas)
    print(r.to_string(index=False), flush=True)
    assert (r["diferencia_maxima"] < 1e-4).all(), "corte_t no reproduce el XGBoost congelado"
    return r


def main(periodos=None, hs=ev.HS, salida=SALIDA, versiones_por_periodo=None):
    salida.mkdir(parents=True, exist_ok=True)
    config = json.loads((CONGELADO / "configuracion_final.json").read_text(encoding="utf-8"))
    periodos = periodos or ev.PERIODOS
    versiones_por_periodo = versiones_por_periodo or {"2020-2022": ["corte_t", "alineado"]}
    D = Datos(hs)
    D.techo = np.datetime64("2022-12-31")
    comprobar_fuga(D, config)
    precio, criterios = ev.precios(), []
    for nombre, (desde, hasta) in periodos.items():
        D.techo = np.datetime64(hasta)
        ruta = salida / f"pronosticos_{nombre.replace('-', '_')}.csv.gz"
        versiones = versiones_por_periodo.get(nombre, ["alineado"])
        if ruta.exists():
            tabla = pd.read_csv(ruta, parse_dates=["fecha"])
        else:
            tabla = None
            for version in versiones:
                t0 = time.time()
                filas = pd.concat([walk_forward(D, h, version, config, desde, hasta) for h in hs], ignore_index=True)
                filas = filas.rename(columns={"y_hat": f"y_hat_{version}"})
                tabla = filas if tabla is None else tabla.merge(filas, on=ev.CLAVES, validate="one_to_one")
                print(f"  {nombre}, {version}: {len(filas):,} pronósticos, {(time.time() - t0) / 60:.1f} min", flush=True)
            tabla = tabla.sort_values(ev.CLAVES).reset_index(drop=True)
            tabla.to_csv(ruta, index=False, float_format="%.6f")
        base = ev.marco(desde, hasta, hs=hs, precio=precio)
        m = base.merge(tabla, on=ev.CLAVES, validate="one_to_one")
        assert len(m) == len(tabla) == len(base), "no son las filas de los otros modelos"
        if nombre == "2020-2022" and "y_hat_corte_t" in tabla and hs == ev.HS:
            comprobar_congelado(tabla).to_csv(salida / "comprobacion_congelado.csv", index=False)
        bloques = ev.BLOQUES if hs == ev.HS else {f"h = {hs[0]} a {hs[-1]}": hs}
        for version in versiones:
            criterios.append(ev.criterio(m, f"y_hat_{version}", bloques).assign(periodo=nombre, modelo=version))
    crit = pd.concat(criterios).reset_index().set_index(["periodo", "modelo", "bloque"])
    crit.to_csv(salida / "criterio.csv", float_format="%.6g")
    print(crit[["origenes", "rmse", "rmse_ingenuo", "mejora", "dm_p", "dm_p_hln", "cumple_hln"]].round(4).to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
