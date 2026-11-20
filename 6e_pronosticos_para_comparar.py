"""Junta en un solo archivo los pronósticos del test de XGBoost y SARIMAX.

El notebook 6d corre en Colab y compara la LSTM contra los otros dos modelos. Para no subir
los once archivos de cada modelo, aquí se dejan en uno solo, con el pronóstico de cada modelo
en la misma escala: y_hat = ln P(t+h, H) pronosticado menos ln P(t, H).

Sale resultados/comparacion/pronosticos_xgboost_sarimax.csv.gz
"""
from pathlib import Path

import numpy as np
import pandas as pd

XGB = Path("resultados/modelo_xgboost")
SAR = Path("resultados/modelo_sarimax")
SALIDA = Path("resultados/comparacion/pronosticos_xgboost_sarimax.csv.gz")
HS = range(3, 10)
FILAS = {"2023_2025": 183_120, "2026": 45_864}

xgb = pd.concat([pd.read_csv(XGB / f"prueba_h{h}.csv.gz").assign(periodo="2023_2025") for h in HS]
                + [pd.read_csv(XGB / "prueba2026_mensual.csv.gz").query("3 <= h <= 9").assign(periodo="2026")])
sar = pd.concat([pd.read_csv(SAR / "prueba_2023_2025.csv.gz"), pd.read_csv(SAR / "prueba_2026.csv.gz")])

d = xgb.merge(sar[["fecha", "hora", "h", "lp_hat"]], on=["fecha", "hora", "h"], validate="one_to_one")
assert len(d) == len(xgb) == len(sar), "XGBoost y SARIMAX no tienen las mismas filas"
assert d.groupby("periodo").size().to_dict() == FILAS

# SARIMAX pronostica el logaritmo del precio; se pasa a diferencia frente al último precio conocido
d["y_hat_xgboost"] = d["y_hat"]
d["y_hat_sarimax"] = d["lp_hat"] - np.log(d["precio_t"])

d = d[["periodo", "fecha", "hora", "h", "y_hat_xgboost", "y_hat_sarimax"]].sort_values(["fecha", "h", "hora"])
SALIDA.parent.mkdir(parents=True, exist_ok=True)
d.to_csv(SALIDA, index=False, float_format="%.6f")
print(f"{len(d):,} filas en {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)")
