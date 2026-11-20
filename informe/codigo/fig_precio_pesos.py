"""Figura de la sección 1.1 con el precio de bolsa en pesos, sin logaritmo, y cifras de la sección 3.3 que justifican
pronosticar el cambio en logaritmo y no el precio, su logaritmo ni el cambio porcentual simple.
La figura 2 ya muestra el precio en escala logarítmica junto al agua y a El Niño; esta muestra su escala real, en
COP/kWh, con el promedio diario de 2015-2021 y de 2023-2025 que cita la sección 1.1. La serie es la misma de la
figura 2 (paneles/panel_caracteristicas.csv.gz, desde el 1 de enero de 2015).
Las cifras de la respuesta usan 2015-2022, los datos con que se diseñaron los modelos, y los cambios a tres y a
nueve días de cada hora, del panel con que se entrenaron (paneles/panel_horario_modelo.csv.gz). No se entrena nada.
Salidas: informe/figuras/f28_precio_pesos.png y datos_respuesta.csv."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd

from estilo_graficas import EXTRA, TENUE, TINTA, aplicar, claro

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
ROJO = EXTRA["rojo"]

h = pd.read_csv(RAIZ / "paneles" / "panel_horario_modelo.csv.gz", parse_dates=["fecha"],
                usecols=["fecha", "hora", "lp"])
LP = h.pivot(index="fecha", columns="hora", values="lp").loc["2015-03-01":"2026-10-06"]
p = pd.read_csv(RAIZ / "paneles" / "panel_caracteristicas.csv.gz", usecols=["fecha", "precio"], parse_dates=["fecha"])
dia = p[p["precio"].notna()].groupby("fecha")["precio"].mean()     # promedio de los 24 precios del día, en COP/kWh

# ----------------------------------------------------------------------------- figura
tramos = {"2015-2021": ("2015-01-01", "2021-12-31"), "2023-2025": ("2023-01-01", "2025-12-31")}
medias = {k: float(dia.loc[a:b].mean()) for k, (a, b) in tramos.items()}

fig, ax = plt.subplots(figsize=(7.6, 3.1))
ax.plot(dia.index, dia.values, color=TINTA, lw=0.7)
for k, (a, b) in tramos.items():
    x0, x1 = pd.Timestamp(a), pd.Timestamp(b)
    ax.plot([x0, x1], [medias[k]] * 2, color=ROJO, lw=1.6, ls="--")
    ax.text(x0 + (x1 - x0) / 2, medias[k] + 70, f"promedio {k}: {medias[k]:.0f} COP/kWh", ha="center", fontsize=8,
            color=ROJO, bbox=dict(facecolor="white", edgecolor="none", pad=1))
ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
ax.set_ylim(0, 2650)
ax.set_xlim(dia.index[0], dia.index[-1])
ax.set_ylabel("COP/kWh")
ax.set_title("Precio de bolsa promedio del día, 2015 a octubre de 2026", loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "f28_precio_pesos.png", dpi=200)

# ----------------------------------------------------------------------------- cifras de la respuesta
filas = [{"medida": f"promedio {k}", "valor": v} for k, v in medias.items()]
filas += [{"medida": "minimo dia", "valor": float(dia.min())}, {"medida": "maximo dia", "valor": float(dia.max())}]
for hh in (3, 9):
    r = (LP.shift(-hh) - LP).loc[:"2022-12-31"].stack()      # cambio en logaritmo de cada hora, de t a t + h
    s = np.exp(r) - 1                                       # el mismo cambio, en porcentaje simple
    filas += [{"medida": f"log h{hh} {m}", "valor": float(v)} for m, v in
              [("min", r.min()), ("max", r.max()), ("asimetria", r.skew()), ("media", r.mean())]]
    filas += [{"medida": f"simple h{hh} {m}", "valor": float(v)} for m, v in
              [("min", 100 * s.min()), ("max", 100 * s.max()), ("asimetria", s.skew()), ("media", 100 * s.mean()),
               ("mas de 30%", 100 * (s.abs() > 0.3).mean())]]
    filas.append({"medida": f"n h{hh}", "valor": float(len(r))})
pd.DataFrame(filas).to_csv(FIG / "datos_respuesta.csv", index=False)
print(pd.DataFrame(filas).to_string())
