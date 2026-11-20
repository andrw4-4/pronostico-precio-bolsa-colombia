"""Semana final, del 9 al 15 de octubre de 2026, con los precios conocidos hasta el 6 de octubre: el precio real
contra los cinco pronósticos (LSTM, XGBoost, SARIMAX y los dos ingenuos), hora por hora.
Los pronósticos son los que guardó cada modelo (resultados/modelo_*/pronostico_final.csv) y el precio real es el
de resultados/modelo_xgboost/precio_real_final.csv. El ingenuo del día repite el precio del 6 de octubre a la misma
hora; el semanal repite el de la misma hora una semana antes (dos semanas en h = 8 y 9), y viene en el archivo de
XGBoost. No se entrena ni se descarga nada.
Salidas: informe/figuras/f29_semana_final.png y datos_semana_final.csv."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo_graficas import COLORES, CUADRICULA, LINEAS, aplicar

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
RES = RAIZ / "resultados"
FIG = RAIZ / "informe" / "figuras"
ORDEN = ["Ingenuo semanal", "Ingenuo del día", "SARIMAX", "XGBoost", "LSTM", "Precio real"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

px = pd.read_csv(RES / "modelo_xgboost" / "pronostico_final.csv", parse_dates=["fecha_objetivo"])
pl = pd.read_csv(RES / "modelo_lstm_bloques" / "pronostico_final.csv", parse_dates=["fecha_objetivo"])
ps = pd.read_csv(RES / "modelo_sarimax" / "pronostico_final.csv", parse_dates=["fecha"])
real = pd.read_csv(RES / "modelo_xgboost" / "precio_real_final.csv", parse_dates=["fecha_objetivo"])
ps["fecha_objetivo"] = ps["fecha"] + pd.to_timedelta(ps["h"], unit="D")

claves = ["fecha_objetivo", "hora"]
d = (px[claves + ["h", "precio_t", "precio_semanal", "precio_pron"]]
     .rename(columns={"precio_t": "Ingenuo del día", "precio_semanal": "Ingenuo semanal", "precio_pron": "XGBoost"})
     .merge(pl[claves + ["precio_pron"]].rename(columns={"precio_pron": "LSTM"}), on=claves, validate="one_to_one")
     .merge(ps.assign(SARIMAX=np.exp(ps["lp_hat"]))[claves + ["SARIMAX"]], on=claves, validate="one_to_one")
     .merge(real.rename(columns={"precio_real": "Precio real"}), on=claves, validate="one_to_one"))
assert len(d) == 168 and d.notna().all().all()
d["momento"] = d["fecha_objetivo"] + pd.to_timedelta(d["hora"] - 1, unit="h")
d = d.sort_values("momento")

# ----------------------------------------------------------------------------- medidas de la semana
filas = []
for mo in ORDEN[:-1]:
    e = d[mo] - d["Precio real"]
    filas.append({"pronostico": mo,
                  "RMSE log": float(np.sqrt(np.mean((np.log(d[mo]) - np.log(d["Precio real"])) ** 2))),
                  "MAE pesos": float(np.mean(np.abs(e))), "sesgo pesos": float(np.mean(e)),
                  "MAPE": float(100 * np.mean(np.abs(e) / d["Precio real"]))})
m = pd.DataFrame(filas).set_index("pronostico")
m.to_csv(FIG / "datos_semana_final.csv")
print(m.round(3).to_string())

# ----------------------------------------------------------------------------- figura
fig, ax = plt.subplots(figsize=(7.6, 3.4))
for mo in ORDEN:
    ax.plot(d["momento"], d[mo], color=COLORES[mo], label=mo, **LINEAS[mo])
dias = pd.date_range("2026-10-09", "2026-10-16")
# las rayas marcan la medianoche y el nombre del día va en el medio de cada día
ax.set_xticks(dias)
ax.set_xticklabels([])
ax.set_xticks(pd.date_range("2026-10-09 12:00", periods=7, freq="D"), minor=True)
ax.set_xticklabels([f"{DIAS[x.dayofweek]} {x.day}" for x in dias[:-1]], minor=True)
ax.tick_params(axis="x", which="minor", length=0)
for x in dias:
    ax.axvline(x, color=CUADRICULA, lw=0.8, zorder=0)
ax.set_xlim(dias[0], dias[-1])
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
ax.set_ylabel("COP/kWh")
ax.set_xlabel("Octubre de 2026")
ax.set_title("Semana del 9 al 15 de octubre de 2026, con precios conocidos hasta el 6 de octubre", loc="left",
             fontsize=10)
h, l = ax.get_legend_handles_labels()
orden_leyenda = [5, 4, 3, 2, 1, 0]
ax.legend([h[i] for i in orden_leyenda], [l[i] for i in orden_leyenda], loc="upper center",
          bbox_to_anchor=(0.5, -0.2), ncol=6, fontsize=8, handlelength=2.2, columnspacing=1.2)
fig.tight_layout()
fig.savefig(FIG / "f29_semana_final.png", dpi=200)
print("ok", FIG / "f29_semana_final.png")
