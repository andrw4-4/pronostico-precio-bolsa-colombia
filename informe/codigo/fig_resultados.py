"""Cifras y figuras del capítulo IV. No entrena nada ni repite ninguna prueba: lee los pronósticos que cada modelo
guardó en su prueba (resultados/modelo_xgboost, modelo_sarimax y modelo_lstm_bloques), los une por fecha, hora y
horizonte, y calcula lo mismo que resumen_modelos_hallazgos/4_comparacion.ipynb, con las mismas funciones.
Las tablas quedan en informe/figuras/datos_resultados_*.csv y la figura en f27.
La decisión de la sección 4.2 sigue el ejercicio del día más barato de la semana: cada día t se elige, entre t + 3 y
t + 9, el día con el menor precio promedio pronosticado."""
from pathlib import Path
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy import stats

from estilo_graficas import COLORES, LINEAS, TENUE, TINTA, aplicar

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
RES = RAIZ / "resultados"
HS = list(range(3, 10))
BLOQUES = {"h = 3 a 9": HS, "h = 3": [3], "h = 3 a 7": [3, 4, 5, 6, 7], "h = 8 a 9": [8, 9]}
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]
INGENUOS = ["Ingenuo del día", "Ingenuo semanal"]
PERIODOS = ["2023-2025", "2026"]


# ----------------------------------------------------------------------------- medidas (sección 2.4 y 3.3)
def rmse(e):
    return float(np.sqrt(np.mean(np.square(e))))


def newey_west(d, L):
    # media de una serie diaria y su error estándar con L rezagos (Newey y West, 1987)
    u = d - d.mean()
    v = np.mean(u * u)
    for l in range(1, min(L, len(d) - 1) + 1):
        v += 2 * (1 - l / (L + 1)) * np.mean(u[l:] * u[:-l])
    return d.mean(), np.sqrt(v / len(d))


def diebold_mariano(e_a, e_b, fechas, L):
    # la pérdida de cada día de origen es el error cuadrático promedio de sus filas; t negativo: a tiene menos error
    dif = np.square(np.asarray(e_a)) - np.square(np.asarray(e_b))
    d = pd.Series(dif).groupby(np.asarray(fechas)).mean().to_numpy()
    m, ee = newey_west(d, L)
    return m / ee, 2 * stats.norm.sf(abs(m / ee))


def criterio(g, pron, bloques=BLOQUES):
    filas = []
    for nombre, hs in bloques.items():
        b = g[g["h"].isin(hs)]
        e = b["y"] - b[pron]
        ingenuos = {"del día": b["y"], "semanal": b["y"] - b["y_semanal"]}
        ref = min(ingenuos, key=lambda k: rmse(ingenuos[k]))
        t, p = diebold_mariano(e, ingenuos[ref], b["fecha"], max(hs) - 1 + 7)
        mejora = 100 * (1 - rmse(e) / rmse(ingenuos[ref]))
        filas.append({"bloque": nombre, "RMSE": rmse(e), "ingenuo": ref, "RMSE ingenuo": rmse(ingenuos[ref]),
                      "mejora": mejora, "t": t, "p": p, "cumple": bool(mejora >= 5 and p < 0.05)})
    return pd.DataFrame(filas).set_index("bloque")


# ----------------------------------------------------------------------------- datos de la prueba
def cargar():
    xgb = pd.concat([pd.read_csv(RES / "modelo_xgboost" / f"prueba_h{h}.csv.gz").assign(periodo="2023-2025")
                     for h in HS]
                    + [pd.read_csv(RES / "modelo_xgboost" / "prueba2026_mensual.csv.gz").query("3 <= h <= 9")
                       .assign(periodo="2026")], ignore_index=True)
    sar = pd.concat([pd.read_csv(RES / "modelo_sarimax" / f"prueba_{p}.csv.gz") for p in ("2023_2025", "2026")])
    lstm = pd.concat([pd.read_csv(RES / "modelo_lstm_bloques" / f"prueba_{p}.csv.gz") for p in ("2023_2025", "2026")])
    claves = ["fecha", "hora", "h"]
    d = (xgb.rename(columns={"y_hat": "XGBoost"})
         .merge(sar[claves + ["lp_hat"]], on=claves, validate="one_to_one")
         .merge(lstm.rename(columns={"y_hat": "LSTM"}), on=claves, validate="one_to_one"))
    assert len(d) == len(xgb) == len(sar) == len(lstm) == 228984
    # SARIMAX pronostica el nivel del logaritmo; se pasa al mismo cambio de la ecuación (21)
    d["SARIMAX"] = d["lp_hat"] - np.log(d["precio_t"])
    d["Ingenuo del día"] = 0.0
    d["Ingenuo semanal"] = d["y_semanal"]
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d


def tablas(d):
    T = {}
    # criterio por periodo y bloque, con las medidas de la sección 2.4 para los cinco pronósticos
    crit = pd.concat({(p, mo): criterio(g, mo) for p, g in d.groupby("periodo") for mo in MODELOS},
                     names=["periodo", "modelo"]).reset_index()
    T["criterio"] = crit
    filas = []
    for p, g in d.groupby("periodo"):
        real = g["precio_t"] * np.exp(g["y"])
        for mo in MODELOS + INGENUOS:
            e = g["y"] - g[mo]
            pron = g["precio_t"] * np.exp(g[mo])
            filas.append({"periodo": p, "pronostico": mo, "RMSE": rmse(e), "MAE": float(np.mean(np.abs(e))),
                          "MAPE": float(100 * np.mean(np.abs(pron - real) / real)),
                          "RMSE pesos": rmse(pron - real), "MAE pesos": float(np.mean(np.abs(pron - real))),
                          "sesgo pesos": float(np.mean(pron - real)), "precio medio": float(real.mean())})
    T["medidas"] = pd.DataFrame(filas)
    # por año del día de origen, en la semana completa
    t = d[d["periodo"] == "2023-2025"]
    casos = {str(a): g for a, g in t.groupby(t["fecha"].dt.year)} | {"2026": d[d["periodo"] == "2026"]}
    T["por_anio"] = pd.concat({(a, mo): criterio(g, mo, {"h = 3 a 9": HS}) for a, g in casos.items()
                               for mo in MODELOS}, names=["año", "modelo"]).reset_index()
    # Diebold-Mariano entre modelos
    casos = {p: g for p, g in d.groupby("periodo")} | {str(a): g for a, g in t.groupby(t["fecha"].dt.year)}
    filas = []
    for nombre, g in casos.items():
        for a, b in [("LSTM", "XGBoost"), ("LSTM", "SARIMAX"), ("XGBoost", "SARIMAX")]:
            tt, pp = diebold_mariano(g["y"] - g[a], g["y"] - g[b], g["fecha"], max(HS) - 1 + 7)
            filas.append({"caso": nombre, "par": f"{a} y {b}", "t": tt, "p": pp, "menor": a if tt < 0 else b})
    T["pares"] = pd.DataFrame(filas)
    # nivel y forma del día (sección 3.2): RMSE^2 = nivel^2 + forma^2
    filas = []
    for p, g in d.groupby("periodo"):
        for mo in MODELOS + INGENUOS:
            e = g["y"] - g[mo]
            medio = e.groupby([g["fecha"], g["h"]]).transform("mean")
            filas.append({"periodo": p, "pronostico": mo, "nivel": rmse(medio), "forma": rmse(e - medio),
                          "RMSE": rmse(e)})
    T["nivel_forma"] = pd.DataFrame(filas)
    # RMSE en logaritmo por horizonte
    T["por_horizonte"] = pd.DataFrame([{"periodo": p, "h": h, "pronostico": mo, "RMSE": rmse(gh["y"] - gh[mo])}
                                       for p, g in d.groupby("periodo") for h, gh in g.groupby("h")
                                       for mo in MODELOS + INGENUOS])
    # el mejor de los cinco pronósticos en cada horizonte y hora, por RMSE en logaritmo
    filas = []
    for p, g in d.groupby("periodo"):
        for (h, hora), c in g.groupby(["h", "hora"]):
            err = {mo: rmse(c["y"] - c[mo]) for mo in MODELOS + INGENUOS}
            filas.append({"periodo": p, "h": h, "hora": hora, "mejor": min(err, key=err.get)})
    T["mejor_celda"] = pd.DataFrame(filas)
    T["decision"] = decision(d)
    return T


# ----------------------------------------------------------------------------- sección 4.2
def decision(d, bloque=28, repeticiones=2000):
    """Ahorro de elegir el día más barato de la semana: precio promedio de los siete días menos el del día
    elegido, en COP/kWh. Intervalo de 95% con bootstrap de bloques móviles de cuatro semanas (Künsch, 1989)."""
    filas = []
    for p, g in d.groupby("periodo"):
        g = g.assign(real=g["precio_t"] * np.exp(g["y"]),
                     **{mo: g["precio_t"] * np.exp(g[mo]) for mo in MODELOS + ["Ingenuo semanal"]})
        dia = g.groupby(["fecha", "h"])[["real"] + MODELOS + ["Ingenuo semanal"]].mean().reset_index()
        dia = dia[dia.groupby("fecha")["h"].transform("size") == 7]
        semana = dia.groupby("fecha")["real"].mean()
        oraculo = None
        for s in ["Oráculo"] + MODELOS + ["Ingenuo semanal"]:
            col = "real" if s == "Oráculo" else s
            elegido = dia.loc[dia.groupby("fecha")[col].idxmin()].set_index("fecha")["real"]
            v = (semana - elegido).to_numpy()
            rng = np.random.default_rng(0)
            n = len(v)
            medias = [np.mean(np.concatenate([v[i:i + bloque] for i in rng.integers(0, n - bloque, n // bloque)]))
                      for _ in range(repeticiones)]
            oraculo = v.mean() if s == "Oráculo" else oraculo
            filas.append({"periodo": p, "pronostico": s, "semanas": n, "precio semana": semana.mean(),
                          "ahorro": v.mean(), "inf": np.percentile(medias, 2.5), "sup": np.percentile(medias, 97.5),
                          "ahorro %": 100 * v.mean() / semana.mean(), "del oraculo %": 100 * v.mean() / oraculo})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------- figuras
NOMBRE_PERIODO = {"2023-2025": "a) Prueba 2023-2025", "2026": "b) Prueba 2026, hasta el 6 de octubre"}


def por_horizonte(t):
    fig, ejes = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
    for ax, p in zip(ejes, PERIODOS):
        for mo in INGENUOS + MODELOS:
            r = t[(t["periodo"] == p) & (t["pronostico"] == mo)]
            ax.plot(r["h"], r["RMSE"], color=COLORES[mo], marker="o" if mo in MODELOS else None, ms=3.5,
                    **LINEAS[mo])
        ax.set_title(NOMBRE_PERIODO[p], loc="left", fontsize=10)
        ax.set_xticks(HS)
        ax.set_xlabel("Horizonte h (días)")
        ax.grid(axis="y")
    ejes[0].set_ylabel("RMSE en logaritmo")
    lineas = [Line2D([], [], color=COLORES[mo], marker="o" if mo in MODELOS else None, ms=3.5, label=mo,
                     **LINEAS[mo]) for mo in MODELOS + INGENUOS]
    fig.legend(handles=lineas, ncol=5, loc="lower center", fontsize=8.5, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(FIG / "f27_error_por_horizonte.png")
    plt.close(fig)


if __name__ == "__main__":
    T = tablas(cargar())
    for nombre, t in T.items():
        t.to_csv(FIG / f"datos_resultados_{nombre}.csv", index=False)
    por_horizonte(T["por_horizonte"])
    print("ok")
