"""
Paso 9g: los modelos en el periodo limpio, del 7 de octubre de 2026 en adelante.

    python 9g_periodo_limpio.py            corre XGBoost (el de la tesis y el alineado) y LEAR
    python 9g_periodo_limpio.py medir      solo mide, con lo que ya esté guardado

Todas las decisiones de la tesis se tomaron con datos hasta el 6 de octubre de 2026. Aquí los
modelos corren, sin cambiar nada, sobre los paneles actualizados del paso 9f. Cada modelo se
reentrena el 1 de octubre y el 1 de noviembre, como en la prueba, y se miden solo los orígenes desde
el 7 de octubre. Se reportan dos grupos:

    desde el 7 de octubre        orígenes que ningún modelo vio
    después de las decisiones    orígenes cuya semana empieza después del 14 de noviembre

SARIMAX corre con 9d_sarimax_dia_semana.R (variable LIMPIO=1) y la LSTM en Colab; si sus archivos
están en resultados/periodo_limpio/, entran a la medición.

Con tan pocos orígenes la prueba de Diebold-Mariano tiene poca potencia: las cifras se reportan sin
conclusiones fuertes.
"""
import importlib.util
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.environ["TESIS_PANELES"] = str(RAIZ / "periodo_limpio" / "paneles")

import numpy as np
import pandas as pd

import evaluacion as ev

SALIDA = ev.RES / "periodo_limpio"
PRIMER_ORIGEN = "2026-10-07"
DESPUES_DE_DECISIONES = "2026-11-14"          # la última decisión, el test de la LSTM, es de ese día
SEMANA = {"h = 3 a 9": ev.HS, "h = 3": [3]}


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / archivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def periodo():
    ultimo = ev.precios()["fecha"].max()
    return {"limpio": ("2026-10-01", str(ultimo.date()))}


def correr():
    p = periodo()
    cargar("lear", "9a_lear.py").main(periodos=p, salida=SALIDA / "lear")
    cargar("xgb", "9b_xgboost_alineado.py").main(periodos=p, salida=SALIDA / "xgboost",
                                                 versiones_por_periodo={"limpio": ["corte_t", "alineado"]})


def medir():
    (desde, hasta), = periodo().values()
    d = ev.marco(desde, hasta)
    d["Ingenuo del día"], d["Ingenuo semanal"] = 0.0, d["y_semanal"]
    fuentes = [(SALIDA / "xgboost" / "pronosticos_limpio.csv.gz", "y_hat_corte_t", "XGBoost"),
               (SALIDA / "xgboost" / "pronosticos_limpio.csv.gz", "y_hat_alineado", "XGBoost alineado"),
               (SALIDA / "lear" / "pronosticos_limpio.csv.gz", "y_hat_lear", "LEAR"),
               (SALIDA / "lear" / "pronosticos_limpio.csv.gz", "y_hat_lear_alineado", "LEAR alineado"),
               (SALIDA / "lstm" / "corrida_E_limpio.csv.gz", "y_hat", "LSTM"),
               (SALIDA / "lstm" / "corrida_F_limpio.csv.gz", "y_hat", "LSTM bloques 1 y 2")]
    for ruta, columna, nombre in fuentes:
        d = ev.agregar(d, ruta, columna, nombre, obligatorio=False)
    for version, nombre in (("fijada", "SARIMAX"), ("dia_semana", "SARIMAX con día de la semana")):
        ruta = SALIDA / "sarimax" / f"{version}_limpio.csv.gz"
        if ruta.exists():
            s = pd.read_csv(ruta, parse_dates=["fecha"]).query("h <= 9")
            d = d.merge(s[ev.CLAVES + ["lp_hat"]], on=ev.CLAVES, how="left", validate="one_to_one")
            d[nombre] = d.pop("lp_hat") - np.log(d["precio_t"])
    if {"SARIMAX", "XGBoost", "LSTM"} <= set(d.columns):
        d["Promedio de los tres"] = d[["SARIMAX", "XGBoost", "LSTM"]].mean(axis=1)
        g = [d["fecha"], d["h"]]
        d["Nivel LSTM y forma XGBoost"] = (d.groupby(g)["LSTM"].transform("mean") + d["XGBoost"]
                                           - d.groupby(g)["XGBoost"].transform("mean"))
    d = d[d["fecha"] >= PRIMER_ORIGEN]
    grupos = {"desde el 7 de octubre": d,
              "después de las decisiones": d[d["fecha"] + pd.Timedelta(days=3) > pd.Timestamp(DESPUES_DE_DECISIONES)]}
    filas = []
    for nombre, g in grupos.items():
        for m in ev.modelos_de(g):
            c = ev.criterio(g, m, SEMANA).reset_index()
            filas.append(c.assign(grupo=nombre, modelo=m, primer_origen=g["fecha"].min().date(),
                                  ultimo_origen=g["fecha"].max().date(),
                                  semanas_completas=int(g.groupby("fecha")["h"].nunique().eq(7).sum())))
    r = pd.concat(filas, ignore_index=True)
    r.to_csv(SALIDA / "criterio.csv", index=False, float_format="%.6g")
    d.to_csv(SALIDA / "pronosticos_todos.csv.gz", index=False, float_format="%.6f")
    print(f"periodo limpio: orígenes del {d['fecha'].min().date()} al {d['fecha'].max().date()}, precio hasta {hasta}")
    print(r[r["bloque"] == "h = 3 a 9"][["grupo", "modelo", "origenes", "semanas_completas", "rmse", "rmse_ingenuo",
                                           "mejora", "dm_p_hln"]].round(4).to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    SALIDA.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:] != ["medir"]:
        correr()
    medir()
