"""
Paso 9a: LEAR, el modelo de referencia de Lago et al. (2021).

    python 9a_lear.py

Una regresión lineal con regularización LASSO por cada horizonte h y cada hora H (168 modelos),
con el mismo objetivo de los otros modelos: y = ln P(t+h, H) - ln P(t, H). Se recalibra el primer
día de cada mes con todo lo anterior, con la misma purga de XGBoost (se entrena con t <= corte -
(h + 1)). El parámetro de regularización se elige con el criterio de Akaike en cada recalibración,
como en la librería epftoolbox de Lago et al. Las variables se estandarizan solo con los días de
entrenamiento.

Dos versiones:
    lear            los 24 logaritmos del precio de los días t, t-1, t-2 y t-6, y el día de la
                    semana y el festivo del día pronosticado (información cortada en t)
    lear_alineado   lo anterior más las nueve variables de los bloques 3 y 4 de la LSTM, cada una
                    con el valor más reciente ya publicado el día del pronóstico

LEAR se agregó después de abrir la prueba de 2023-2026 (revisión del 26 de noviembre de 2026). No
tiene nada que elegir con los datos: las variables y la regla salen de la literatura. Aun así, sus
cifras de 2023-2026 se reportan como modelo agregado después.

Salidas, en resultados/modelo_lear/: los pronósticos de cada periodo y criterio.csv.
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")          # cada proceso con un hilo; se reparte por tareas
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import time
import warnings

import holidays
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import LassoLarsIC
from sklearn.preprocessing import StandardScaler

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
SALIDA = ev.RES / "modelo_lear"
REZAGOS = (0, 1, 2, 6)
HORARIAS = ["cmg_despacho", "disp_decl_hoy_rel", "cmg_hoy_vs_precio", "frac_termica_prog", "brecha_escasez",
            "presion_hidro_horaria"]
DIARIAS = ["aportes_media_hist", "volumen_util_pct", "dias_autonomia"]
INICIO = "2015-03-01"
PROCESOS = 10


def datos(hs):
    """Matrices por día: precio rezagado, variables alineadas, calendario del día objetivo y objetivo."""
    p = ev.precios()
    f = pd.DatetimeIndex(p["fecha"].drop_duplicates())
    lp = np.log(p["precio"].to_numpy(float)).reshape(len(f), 24)
    assert not np.isnan(lp).any()

    def atras(k):
        out = np.full_like(lp, np.nan)
        out[k:] = lp[:len(f) - k]
        return out

    x_precio = np.hstack([atras(k) for k in REZAGOS])
    b = pd.read_csv(ev.PANELES / "panel_lstm_bloques.csv.gz", usecols=["fecha", "hora"] + HORARIAS + DIARIAS,
                    parse_dates=["fecha"]).sort_values(["fecha", "hora"])
    b = b[b["fecha"].isin(f)]
    assert len(b) == len(f) * 24 and (b["fecha"].to_numpy().reshape(len(f), 24)[:, 0] == f.to_numpy()).all()
    x_alin = np.hstack([b[v].to_numpy(float).reshape(len(f), 24) for v in HORARIAS]
                       + [b[v].to_numpy(float).reshape(len(f), 24)[:, :1] for v in DIARIAS])
    festivos = holidays.Colombia(years=range(f[0].year, f[-1].year + 2))
    cal, y = {}, {}
    for h in hs:
        objetivo = f + pd.Timedelta(days=h)
        cal[h] = np.column_stack([np.eye(7)[objetivo.dayofweek][:, 1:], [float(d in festivos) for d in objetivo]])
        y[h] = np.full_like(lp, np.nan)
        y[h][:len(f) - h] = lp[h:] - lp[:len(f) - h]
    return f.to_numpy("datetime64[D]"), x_precio, x_alin, cal, y


def un_mes(X, y, f, h, corte, sig, hasta):
    """Recalibra con t <= corte - (h + 1) y pronostica los orígenes del mes cuyo objetivo cae en el periodo."""
    usable = ~np.isnan(X).any(axis=1)
    tr = usable & (f >= np.datetime64(INICIO)) & (f <= corte - np.timedelta64(h + 1, 'D')) & ~np.isnan(y).any(axis=1)
    ev_ = usable & (f >= corte) & (f < sig) & (f + np.timedelta64(h, 'D') <= hasta)
    if not ev_.any():
        return None
    assert (f[tr] + np.timedelta64(h, 'D')).max() < corte, "un objetivo del entrenamiento cae en el periodo evaluado"
    esc = StandardScaler().fit(X[tr])
    A, B = esc.transform(X[tr]), esc.transform(X[ev_])
    pred, activas = np.empty((ev_.sum(), 24)), []
    for H in range(24):
        m = LassoLarsIC(criterion="aic").fit(A, y[tr, H])
        pred[:, H] = m.predict(B)
        activas.append(int(np.count_nonzero(m.coef_)))
    return h, f[ev_], pred, int(tr.sum()), float(np.mean(activas))


def correr(nombre, desde, hasta, versiones, f, cal, y, hs):
    cortes = list(pd.date_range(desde, hasta, freq="MS").to_numpy().astype("datetime64[D]"))
    sigs = cortes[1:] + [np.datetime64(hasta) + np.timedelta64(1, 'D')]
    tabla, resumen = None, []
    for version, X0 in versiones.items():
        t0 = time.time()
        tareas = [delayed(un_mes)(np.hstack([X0, cal[h]]), y[h], f, h, c, s, np.datetime64(hasta))
                  for h in hs for c, s in zip(cortes, sigs)]
        partes = [x for x in Parallel(n_jobs=PROCESOS)(tareas) if x is not None]
        filas = pd.concat([pd.DataFrame({"fecha": np.repeat(fe, 24), "hora": np.tile(np.arange(1, 25), len(fe)),
                                         "h": h, f"y_hat_{version}": pr.reshape(-1)})
                           for h, fe, pr, _, _ in partes], ignore_index=True)
        tabla = filas if tabla is None else tabla.merge(filas, on=ev.CLAVES, validate="one_to_one")
        resumen.append({"periodo": nombre, "version": version, "columnas": X0.shape[1] + cal[hs[0]].shape[1],
                        "recalibraciones": len(partes), "dias_entrenamiento_min": min(p[3] for p in partes),
                        "dias_entrenamiento_max": max(p[3] for p in partes),
                        "variables_activas_media": float(np.mean([p[4] for p in partes]))})
        print(f"  {nombre}, {version}: {len(filas):,} pronósticos, {time.time() - t0:.0f} s", flush=True)
    return tabla.sort_values(ev.CLAVES).reset_index(drop=True), resumen


def main(periodos=None, hs=ev.HS, salida=SALIDA):
    salida.mkdir(parents=True, exist_ok=True)
    periodos = periodos or ev.PERIODOS
    f, x_precio, x_alin, cal, y = datos(hs)
    versiones = {"lear": x_precio, "lear_alineado": np.hstack([x_precio, x_alin])}
    precio, criterios, resumenes = ev.precios(), [], []
    for nombre, (desde, hasta) in periodos.items():
        ruta = salida / f"pronosticos_{nombre.replace('-', '_')}.csv.gz"
        if ruta.exists():
            tabla = pd.read_csv(ruta, parse_dates=["fecha"])
        else:
            tabla, res = correr(nombre, desde, hasta, versiones, f, cal, y, hs)
            tabla.to_csv(ruta, index=False, float_format="%.6f")
            resumenes += res
        m = ev.marco(desde, hasta, hs=hs, precio=precio).merge(tabla, on=ev.CLAVES, validate="one_to_one")
        assert len(m) == len(tabla) == len(ev.marco(desde, hasta, hs=hs, precio=precio)), "no son las filas de los otros modelos"
        bloques = ev.BLOQUES if hs == ev.HS else {f"h = {hs[0]} a {hs[-1]}": hs}
        for version in versiones:
            criterios.append(ev.criterio(m, f"y_hat_{version}", bloques).assign(periodo=nombre, modelo=version))
    crit = pd.concat(criterios).reset_index().set_index(["periodo", "modelo", "bloque"])
    crit.to_csv(salida / "criterio.csv", float_format="%.6g")
    if resumenes:
        pd.DataFrame(resumenes).to_csv(salida / "recalibraciones.csv", index=False, float_format="%.6g")
    print(crit[["origenes", "rmse", "rmse_ingenuo", "mejora", "dm_p", "dm_p_hln", "cumple_hln"]].round(4).to_string())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
