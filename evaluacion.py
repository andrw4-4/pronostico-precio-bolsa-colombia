"""
Medidas y carga de pronósticos para los análisis de la revisión de noviembre de 2026.

No entrena nada. Reúne en un solo lugar lo que ya usaban 4_modelo_xgboost.ipynb,
6d_lstm_busqueda_y_test.ipynb e informe/codigo/fig_resultados.py, para que los modelos que se
agregan después de la prueba (LEAR, combinaciones, XGBoost con la información alineada) se midan
con las mismas funciones y en las mismas filas.

Regla de las filas, la misma para todos los modelos: un origen t entra a un periodo en el
horizonte h si el día objetivo t + h cae dentro del periodo. Por eso el número de orígenes baja
de a uno entre h = 3 y h = 9.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parent
RES = RAIZ / "resultados"
# Los paneles congelados. Para el periodo limpio se apunta a los paneles actualizados con TESIS_PANELES.
PANELES = Path(os.environ.get("TESIS_PANELES", RAIZ / "paneles"))
HS = list(range(3, 10))
BLOQUES = {"h = 3 a 9": HS, "h = 3": [3], "h = 3 a 7": [3, 4, 5, 6, 7], "h = 8 a 9": [8, 9]}
PERIODOS = {"2020-2022": ("2020-01-01", "2022-12-31"), "2023-2025": ("2023-01-01", "2025-12-31"),
            "2026": ("2026-01-01", "2026-10-06")}
CLAVES = ["fecha", "hora", "h"]


# ----------------------------------------------------------------------------- precio y filas
def precios():
    """Precio de bolsa por día y hora del panel de los modelos (2015-03-01 a 2026-10-06 en el congelado)."""
    p = pd.read_csv(PANELES / "panel_horario_modelo.csv.gz", usecols=["fecha", "hora", "precio"],
                    parse_dates=["fecha"]).sort_values(["fecha", "hora"]).reset_index(drop=True)
    assert len(p) == p["fecha"].nunique() * 24
    return p


def marco(desde, hasta, hs=HS, precio=None):
    """Filas (origen t, hora, h) con el objetivo y = ln P(t+h, H) - ln P(t, H) y el ingenuo semanal.
    Entra el origen t si desde <= t y t + h <= hasta."""
    p = precios() if precio is None else precio
    f = p["fecha"].to_numpy("datetime64[D]")
    lp = np.log(p["precio"].to_numpy(float))
    n = len(p)
    partes = []
    for h in hs:
        y = np.full(n, np.nan)
        y[:n - 24 * h] = lp[24 * h:] - lp[:n - 24 * h]
        k = 7 * int(np.ceil(h / 7)) - h              # días hasta el mismo día de la semana ya conocido
        y_sem = np.full(n, np.nan)
        y_sem[24 * k:] = lp[:n - 24 * k] - lp[24 * k:] if k else 0.0
        m = (f >= np.datetime64(desde)) & (f + h <= np.datetime64(hasta)) & ~np.isnan(y)
        partes.append(pd.DataFrame({"fecha": p["fecha"].to_numpy()[m], "hora": p["hora"].to_numpy()[m], "h": h,
                                    "precio_t": p["precio"].to_numpy()[m], "y": y[m], "y_semanal": y_sem[m]}))
    return pd.concat(partes, ignore_index=True)


# ----------------------------------------------------------------------------- medidas
def rmse(e):
    return float(np.sqrt(np.mean(np.square(e))))


def newey_west(d, L):
    """Media de una serie diaria y su error estándar con L rezagos (Newey y West, 1987)."""
    d = np.asarray(d, float)
    u = d - d.mean()
    v = np.mean(u * u)
    for l in range(1, min(L, len(d) - 1) + 1):
        v += 2 * (1 - l / (L + 1)) * np.mean(u[l:] * u[:-l])
    return d.mean(), np.sqrt(v / len(d))


def diebold_mariano(e_a, e_b, fechas, L, h=None):
    """
    Diebold y Mariano (1995) con pérdida cuadrática. La pérdida de cada día de origen es el promedio
    de sus filas. t negativo: a tiene menos error. Devuelve t y p con la normal, y además t y p con
    la corrección de Harvey, Leybourne y Newbold (1997) si se da el horizonte h: el estadístico se
    multiplica por raíz de (T + 1 - 2h + h(h - 1)/T) / T y se compara con una t de Student de T - 1
    grados de libertad.
    """
    dif = np.square(np.asarray(e_a, float)) - np.square(np.asarray(e_b, float))
    d = pd.Series(dif).groupby(np.asarray(fechas)).mean().to_numpy()
    m, ee = newey_west(d, L)
    t = m / ee
    r = {"t": t, "p": 2 * stats.norm.sf(abs(t)), "T": len(d)}
    if h is not None:
        T = len(d)
        t_hln = t * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
        r.update(t_hln=t_hln, p_hln=2 * stats.t.sf(abs(t_hln), T - 1))
    return r


def criterio(g, pron, bloques=BLOQUES):
    """El criterio de la tesis por bloque de horizontes, contra el ingenuo de menor RMSE en el bloque."""
    filas = []
    for nombre, hs in bloques.items():
        b = g[g["h"].isin(hs)]
        if b.empty:
            continue
        e = b["y"] - b[pron]
        ingenuos = {"del día": b["y"], "semanal": b["y"] - b["y_semanal"]}
        ref = min(ingenuos, key=lambda k: rmse(ingenuos[k]))
        dm = diebold_mariano(e, ingenuos[ref], b["fecha"], max(hs) - 1 + 7, h=max(hs))
        mejora = 100 * (1 - rmse(e) / rmse(ingenuos[ref]))
        filas.append({"bloque": nombre, "origenes": dm["T"], "rmse": rmse(e), "ingenuo": ref,
                      "rmse_ingenuo": rmse(ingenuos[ref]), "mejora": mejora, "dm_t": dm["t"], "dm_p": dm["p"],
                      "dm_t_hln": dm["t_hln"], "dm_p_hln": dm["p_hln"],
                      "cumple": bool(mejora >= 5 and dm["p"] < 0.05),
                      "cumple_hln": bool(mejora >= 5 and dm["p_hln"] < 0.05)})
    return pd.DataFrame(filas).set_index("bloque")


def nivel_y_forma(g, pron):
    """Parte el error en el nivel del día (promedio de las 24 horas) y la forma (lo que queda)."""
    e = (g["y"] - g[pron]).to_numpy()
    media = pd.Series(e).groupby([g["fecha"].to_numpy(), g["h"].to_numpy()]).transform("mean").to_numpy()
    return rmse(media), rmse(e - media)


# ----------------------------------------------------------------------------- pronósticos guardados
def prueba_tres_modelos():
    """Los tres modelos de la tesis en las filas de la prueba (2023-2025 y 2026), sin reentrenar nada."""
    xgb = pd.concat([pd.read_csv(RES / "modelo_xgboost" / f"prueba_h{h}.csv.gz").assign(periodo="2023-2025")
                     for h in HS]
                    + [pd.read_csv(RES / "modelo_xgboost" / "prueba2026_mensual.csv.gz").query("3 <= h <= 9")
                       .assign(periodo="2026")], ignore_index=True)
    sar = pd.concat([pd.read_csv(RES / "modelo_sarimax" / f"prueba_{p}.csv.gz") for p in ("2023_2025", "2026")])
    lstm = pd.concat([pd.read_csv(RES / "modelo_lstm_bloques" / f"prueba_{p}.csv.gz") for p in ("2023_2025", "2026")])
    d = (xgb.rename(columns={"y_hat": "XGBoost"})
         .merge(sar[CLAVES + ["lp_hat", "lo80", "hi80"]], on=CLAVES, validate="one_to_one")
         .merge(lstm.rename(columns={"y_hat": "LSTM"}), on=CLAVES, validate="one_to_one"))
    assert len(d) == len(xgb) == len(sar) == len(lstm) == 228984
    d["SARIMAX"] = d["lp_hat"] - np.log(d["precio_t"])       # SARIMAX pronostica el nivel del logaritmo
    d["Ingenuo del día"] = 0.0
    d["Ingenuo semanal"] = d["y_semanal"]
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d.drop(columns=["lp_hat"])


def agregar(d, ruta, columna, nombre, obligatorio=True):
    """Une a la tabla d el pronóstico de otro modelo guardado con las claves fecha, hora y h."""
    ruta = Path(ruta)
    if not ruta.exists():
        assert not obligatorio, f"falta {ruta}"
        return d
    o = pd.read_csv(ruta, parse_dates=["fecha"])[CLAVES + [columna]].rename(columns={columna: nombre})
    r = d.merge(o, on=CLAVES, how="left", validate="one_to_one")
    assert r[nombre].notna().all(), f"{nombre} no cubre todas las filas"
    return r


def prueba_pareada(d, L, h):
    """Media de una serie de diferencias por origen, con Newey-West y la corrección de Harvey et al. (1997)."""
    d = np.asarray(d, float)
    m, ee = newey_west(d, L)
    T = len(d)
    t = m / ee * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return {"media": m, "t_hln": t, "p_hln": 2 * stats.t.sf(abs(t), T - 1), "T": T}


# ----------------------------------------------------------------------------- todos los modelos
# Modelos que se agregaron en la revisión del 26 de noviembre de 2026: (carpeta, columna, nombre)
AGREGADOS = [("modelo_lear", "y_hat_lear", "LEAR"), ("modelo_lear", "y_hat_lear_alineado", "LEAR alineado"),
             ("modelo_xgboost_alineado", "y_hat_alineado", "XGBoost alineado")]
LSTM_REVISION = {"2020-2022": [("A", "LSTM bloques 1 y 2"), ("B", "LSTM")],
                 "2023-2025": [("C", "LSTM bloques 1 y 2")], "2026": [("C", "LSTM bloques 1 y 2")]}


def tabla_modelos(periodo):
    """Todos los pronósticos disponibles de un periodo, en las mismas filas. Los que faltan se omiten."""
    sufijo = periodo.replace("-", "_")
    if periodo == "2020-2022":
        d = marco(*PERIODOS[periodo])
        sar = pd.read_csv(RES / "modelo_sarimax" / "etapa4_comun.csv.gz", parse_dates=["fecha"])
        d = d.merge(sar[CLAVES + ["lp_hat"]], on=CLAVES, validate="one_to_one")
        d["SARIMAX"] = d["lp_hat"] - np.log(d["precio_t"])
        d = d.drop(columns="lp_hat")
        d = agregar(d, RES / "modelo_xgboost_alineado" / f"pronosticos_{sufijo}.csv.gz", "y_hat_corte_t", "XGBoost",
                    obligatorio=False)
        d["Ingenuo del día"], d["Ingenuo semanal"] = 0.0, d["y_semanal"]
    else:
        t = prueba_tres_modelos()
        d = t[t["periodo"] == periodo].drop(columns=["periodo", "lo80", "hi80"]).reset_index(drop=True)
    for carpeta, columna, nombre in AGREGADOS:
        d = agregar(d, RES / carpeta / f"pronosticos_{sufijo}.csv.gz", columna, nombre, obligatorio=False)
    for letra, nombre in LSTM_REVISION[periodo]:
        d = agregar(d, RES / "modelo_lstm_revision" / f"corrida_{letra}_{sufijo}.csv.gz", "y_hat", nombre,
                    obligatorio=False)
    # combinaciones sin parámetros (Bates y Granger, 1969): promedio simple, y nivel de la LSTM con forma de XGBoost
    if {"SARIMAX", "XGBoost", "LSTM"} <= set(d.columns):
        d["Promedio de los tres"] = d[["SARIMAX", "XGBoost", "LSTM"]].mean(axis=1)
        grupo = [d["fecha"], d["h"]]
        d["Nivel LSTM y forma XGBoost"] = (d.groupby(grupo)["LSTM"].transform("mean") + d["XGBoost"]
                                           - d.groupby(grupo)["XGBoost"].transform("mean"))
    return d


def modelos_de(d):
    fijas = set(CLAVES) | {"precio_t", "y", "y_semanal", "periodo", "Ingenuo del día", "Ingenuo semanal"}
    return [c for c in d.columns if c not in fijas]
