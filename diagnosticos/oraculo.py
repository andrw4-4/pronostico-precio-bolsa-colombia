"""
Experimento de oráculo, solo en 2020-2022 y sin escribir en el repo: ¿cuánto baja el error si el
modelo conociera el futuro real de ciertas variables? Nadie tendría estos datos al pronosticar.
Mide qué información falta, no un modelo que se pueda usar.
"""
import json
import time
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200, "display.max_columns", 30)

GRUPOS = {
    "demanda": ["demanda"],
    "hidrologia": ["aportes_pct_sistema", "aportes_caudal_pct", "capacidad_util_dias", "vertimientos_rel"],
    "ofertas": ["oferta_marginal", "margen_ofertado", "holgura_rel", "cap_bajo_200_rel", "cap_bajo_500_rel", "oferta_dispersion"],
}
VERSIONES = {
    "actual": [],
    "+ demanda futura": ["demanda"],
    "+ hidrología futura": ["hidrologia"],
    "+ demanda e hidrología": ["demanda", "hidrologia"],
    "+ ofertas futuras": ["ofertas"],
    "+ todo": ["demanda", "hidrologia", "ofertas"],
}
HS = [3, 7]
INI, FIN = np.datetime64("2020-01-01"), np.datetime64("2022-12-31")

tabla = pd.read_csv("paneles/panel_horario_modelo.csv.gz", parse_dates=["fecha"])
sel = pd.read_csv("paneles/panel_horario_modelo_columnas.csv")
info = pd.read_csv("paneles/panel_caracteristicas_variables.csv").set_index("variable")
config = json.load(open("resultados/modelo_xgboost/configuracion_final.json", encoding="utf-8"))
todas = [v for g in GRUPOS.values() for v in g]
print({v: (info.loc[v, "tipo"], int(info.loc[v, "atraso_extra_dias"])) for v in todas})
car = pd.read_csv("paneles/panel_caracteristicas.csv.gz", usecols=["fecha", "hora"] + todas, parse_dates=["fecha"]).sort_values(["fecha", "hora"])
dias = pd.DatetimeIndex(car["fecha"].unique())
V = {v: car[v].to_numpy(float).reshape(-1, 24) for v in todas}

F = tabla["fecha"].to_numpy("datetime64[D]")
H = tabla["hora"].to_numpy()
LP = np.log(tabla["precio"].to_numpy(float))
dia_t = (tabla["fecha"] - dias[0]).dt.days.to_numpy()


def adelante(x, k):
    o = np.full(len(x), np.nan)
    o[:-k] = x[k:]
    return o


def oraculo(v, h):
    # El panel guarda cada columna corrida por su atraso: el dato real del día d está en la fila d + atraso
    d = dia_t + h + int(info.loc[v, "atraso_extra_dias"])
    o = np.full(len(d), np.nan)
    ok = d < V[v].shape[0]
    o[ok] = V[v][d[ok], H[ok] - 1]
    return o


meses = pd.date_range("2020-01-01", "2022-12-01", freq="MS").to_numpy().astype("datetime64[D]")
resultados = []
for h in HS:
    y = adelante(LP, 24 * h) - LP
    base = sel[sel[f"entra_h{h}"]].sort_values(f"orden_h{h}", na_position="first")["columna"].tolist()
    p = config[str(h)]["parametros"]
    A0 = tabla[base].to_numpy(np.float32)
    for nombre, grupos in VERSIONES.items():
        extra = [v for g in grupos for v in GRUPOS[g]]
        A = np.column_stack([A0] + [oraculo(v, h) for v in extra]) if extra else A0
        t0 = time.time()
        idx, pred = [], []
        for k, c in enumerate(meses):
            sig = meses[k + 1] if k + 1 < len(meses) else FIN + 1
            tr = (F <= c - (h + 1)) & ~np.isnan(y)
            ev = (F >= c) & (F < sig) & (F + h <= FIN) & ~np.isnan(y)
            m = xgb.XGBRegressor(tree_method="hist", n_jobs=-1, random_state=0, learning_rate=0.03, **p).fit(A[tr], y[tr])
            idx.append(np.flatnonzero(ev))
            pred.append(m.predict(A[ev]))
        idx, pred = np.concatenate(idx), np.concatenate(pred)
        d = pd.DataFrame({"f": F[idx], "e": y[idx] - pred, "i": y[idx]})
        nivel = d.groupby("f")["e"].transform("mean")
        nivel_i = d.groupby("f")["i"].transform("mean")
        r = lambda x: float(np.sqrt(np.mean(np.square(x))))
        resultados.append(dict(h=h, version=nombre, rmse=r(d["e"]), mejora=100 * (1 - r(d["e"]) / r(d["i"])),
                               nivel=r(nivel), forma=r(d["e"] - nivel), ing_rmse=r(d["i"]), ing_nivel=r(nivel_i), ing_forma=r(d["i"] - nivel_i),
                               columnas=A.shape[1], seg=round(time.time() - t0)))
        print(resultados[-1], flush=True)

t = pd.DataFrame(resultados)
print(t[["h", "version", "rmse", "mejora", "nivel", "forma", "ing_rmse", "ing_nivel", "ing_forma"]].round(3).to_string(index=False))
