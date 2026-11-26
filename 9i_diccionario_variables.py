"""Diccionario de variables: nombre, grupo, fuente (métricas de XM), transformación y cuándo se conoce.

Une los metadatos que ya escriben los pasos 2c y 2e (paneles/panel_caracteristicas_variables.csv y
paneles/panel_lstm_variables.csv) en un solo archivo, docs/diccionario_variables.csv. La columna que
demuestra que no hay fuga es dias_antes_de_R: el día R en que se pronostica, el último dato conocido de
la variable es el del día R menos ese número (sección 3.1 del informe y tabla 2).
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
lstm = pd.read_csv(RAIZ / "paneles" / "panel_lstm_variables.csv")
xgb = pd.read_csv(RAIZ / "paneles" / "panel_caracteristicas_variables.csv")

d = lstm.rename(columns={"fuente": "metricas_xm", "regla": "transformacion", "entra": "entra_panel_lstm"})[
    ["variable", "grupo", "tipo", "metricas_xm", "transformacion", "dias_antes_de_R", "dias_frente_al_precio",
     "faltante_pct", "entra_panel_lstm"]]
x = xgb[["variable", "de_antemano", "atraso_extra_dias", "entra"]].rename(columns={
    "de_antemano": "xgboost_se_conoce_antes", "atraso_extra_dias": "xgboost_atraso_extra_dias",
    "entra": "entra_panel_xgboost"})
d = d.merge(x, on="variable", how="outer")
d["cuando_se_conoce"] = d["dias_antes_de_R"].map(
    lambda v: "" if pd.isna(v) else ("el mismo día R (programado o publicado ese día)" if v == 0
                                      else f"día R − {int(v)}"))
for c in ("dias_antes_de_R", "dias_frente_al_precio", "xgboost_atraso_extra_dias"):
    d[c] = d[c].astype("Int64")
d = d.sort_values(["grupo", "variable"])
d.to_csv(RAIZ / "docs" / "diccionario_variables.csv", index=False, encoding="utf-8")
print(len(d), "variables;", d["dias_antes_de_R"].value_counts().sort_index().to_dict())
