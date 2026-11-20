"""
¿Sirve pronosticar las ofertas? Dos preguntas, solo hasta 2022 y sin escribir en el repo:
1. ¿Qué tan pronosticable es cada variable de ofertas, con lo que se sabe en t?
2. Si esos pronósticos, y no los valores reales, entran al modelo del precio, ¿baja el error?

Purga: al cortar en c, el objetivo v(t+h) solo se conoce si t + h + atraso <= c - 1.
Los pronósticos de ofertas que entran al segundo paso son siempre fuera de muestra.
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200, "display.max_columns", 30)

OFERTAS = ["oferta_marginal", "margen_ofertado", "holgura_rel", "cap_bajo_200_rel", "cap_bajo_500_rel", "oferta_dispersion"]
HS = [3, 7]
FIN = np.datetime64("2022-12-31")
INI_OFERTAS = "2018-01-01"
INI_PRECIO = np.datetime64("2020-01-01")

tabla = pd.read_csv("paneles/panel_horario_modelo.csv.gz", parse_dates=["fecha"])
sel = pd.read_csv("paneles/panel_horario_modelo_columnas.csv")
info = pd.read_csv("paneles/panel_caracteristicas_variables.csv").set_index("variable")
config = json.load(open("resultados/modelo_xgboost/configuracion_final.json", encoding="utf-8"))
car = pd.read_csv("paneles/panel_caracteristicas.csv.gz", usecols=["fecha", "hora"] + OFERTAS, parse_dates=["fecha"]).sort_values(["fecha", "hora"])
dias = pd.DatetimeIndex(car["fecha"].unique())
V = {v: car[v].to_numpy(float).reshape(-1, 24) for v in OFERTAS}

F = tabla["fecha"].to_numpy("datetime64[D]")
H = tabla["hora"].to_numpy()
LP = np.log(tabla["precio"].to_numpy(float))
dia_t = (tabla["fecha"] - dias[0]).dt.days.to_numpy()
r = lambda x: float(np.sqrt(np.nanmean(np.square(x))))


def adelante(x, k):
    o = np.full(len(x), np.nan)
    o[:-k] = x[k:]
    return o


def fila(v, d):
    o = np.full(len(d), np.nan)
    ok = (d >= 0) & (d < V[v].shape[0])
    o[ok] = V[v][d[ok], H[ok] - 1]
    return o


meses_of = pd.date_range(INI_OFERTAS, "2022-12-01", freq="MS").to_numpy().astype("datetime64[D]")
meses_pr = pd.date_range("2020-01-01", "2022-12-01", freq="MS").to_numpy().astype("datetime64[D]")
filas_of, filas_pr = [], []

for h in HS:
    y = adelante(LP, 24 * h) - LP
    base = sel[sel[f"entra_h{h}"]].sort_values(f"orden_h{h}", na_position="first")["columna"].tolist()
    p = config[str(h)]["parametros"]
    A0 = tabla[base].to_numpy(np.float32)
    nuevos = {}
    for v in OFERTAS:
        t0 = time.time()
        at = int(info.loc[v, "atraso_extra_dias"])
        obj = fila(v, dia_t + h + at)                      # el valor real del día t + h
        ult = fila(v, dia_t)                               # lo último conocido en t: la fila t es el día t - atraso
        ult7 = np.mean([fila(v, dia_t - k) for k in range(7)], axis=0)
        A = np.column_stack([A0, ult, ult7])
        oos = np.full(len(F), np.nan)
        for k, c in enumerate(meses_of):
            sig = meses_of[k + 1] if k + 1 < len(meses_of) else FIN + 1
            tr = (F <= c - (h + 1 + at)) & ~np.isnan(obj)
            ev = (F >= c) & (F < sig)
            m = xgb.XGBRegressor(tree_method="hist", n_jobs=-1, random_state=0, learning_rate=0.03, **p).fit(A[tr], obj[tr])
            oos[ev] = m.predict(A[ev])
        nuevos[v] = oos
        ev = (F >= INI_PRECIO) & (F + h <= FIN) & ~np.isnan(obj)
        e_m, e_u = obj[ev] - oos[ev], obj[ev] - ult[ev]
        real = fila(v, dia_t + h + at)[ev]
        # R² frente a la media, y qué tan parecido es al valor real
        filas_of.append(dict(h=h, variable=v, atraso=at, dias_adelante=h + at, rmse_modelo=r(e_m), rmse_ultimo=r(e_u), sd=float(np.nanstd(real)),
                             mejora_vs_ultimo=100 * (1 - r(e_m) / r(e_u)), corr=float(pd.Series(oos[ev]).corr(pd.Series(real))), seg=round(time.time() - t0)))
        print(filas_of[-1], flush=True)

    O = np.column_stack([nuevos[v] for v in OFERTAS])
    reales = np.column_stack([fila(v, dia_t + h + int(info.loc[v, "atraso_extra_dias"])) for v in OFERTAS])
    versiones = {"actual, toda la historia": (A0, None), "actual, desde 2018": (A0, "2018-01-01"),
                 "+ ofertas pronosticadas, desde 2018": (np.column_stack([A0, O]), "2018-01-01"),
                 "+ ofertas reales (oráculo), desde 2018": (np.column_stack([A0, reales]), "2018-01-01")}
    for nombre, (A, ini) in versiones.items():
        idx, pred = [], []
        for k, c in enumerate(meses_pr):
            sig = meses_pr[k + 1] if k + 1 < len(meses_pr) else FIN + 1
            tr = (F <= c - (h + 1)) & ~np.isnan(y)
            if ini:
                tr &= F >= np.datetime64(ini)
            ev = (F >= c) & (F < sig) & (F + h <= FIN) & ~np.isnan(y)
            m = xgb.XGBRegressor(tree_method="hist", n_jobs=-1, random_state=0, learning_rate=0.03, **p).fit(A[tr], y[tr])
            idx.append(np.flatnonzero(ev))
            pred.append(m.predict(A[ev]))
        idx, pred = np.concatenate(idx), np.concatenate(pred)
        d = pd.DataFrame({"f": F[idx], "e": y[idx] - pred, "i": y[idx]})
        nivel = d.groupby("f")["e"].transform("mean")
        filas_pr.append(dict(h=h, version=nombre, rmse=r(d["e"]), mejora=100 * (1 - r(d["e"]) / r(d["i"])), nivel=r(nivel), forma=r(d["e"] - nivel)))
        print(filas_pr[-1], flush=True)

print("\n=== 1. pronosticar las ofertas")
print(pd.DataFrame(filas_of).drop(columns="seg").round(3).to_string(index=False))
print("\n=== 2. esos pronósticos dentro del modelo del precio")
print(pd.DataFrame(filas_pr).round(3).to_string(index=False))
