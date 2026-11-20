"""Figura de la sección 1.1: el precio de bolsa promedio del día con el volumen útil de los embalses y el índice ONI.
Los datos salen de paneles/panel_caracteristicas.csv.gz. Antes la hacía figuras_informe.py; aquí tiene los
colores del informe final: el agua y La Niña en azul, y El Niño y sus episodios fuertes en rojo."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from estilo_graficas import COLORES, EXTRA, TENUE, TINTA, claro

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "informe" / "figuras" / "f01_precio_embalses_nino.png"
AZUL, ROJO = COLORES["LSTM"], EXTRA["rojo"]

plt.rcParams.update({"font.size": 10, "axes.edgecolor": TENUE, "axes.labelcolor": TINTA,
                     "xtick.color": TENUE, "ytick.color": TENUE, "figure.facecolor": "#ffffff",
                     "axes.facecolor": "#ffffff", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
                     "axes.titlelocation": "left", "axes.titlesize": 11})

p = pd.read_csv(RAIZ / "paneles/panel_caracteristicas.csv.gz", usecols=["fecha", "precio", "volumen_util_pct", "oni"])
p["fecha"] = pd.to_datetime(p["fecha"])
p = p[p.precio.notna()]
d = p.groupby("fecha").agg(precio=("precio", "mean"), vol=("volumen_util_pct", "first"),
                           oni=("oni", "first")).reset_index()

fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8.5, 7), sharex=True, gridspec_kw={"height_ratios": [1.6, 1, 1]})
a1.plot(d.fecha, d.precio, color=claro(TINTA, 0.35), lw=0.7, label="precio del día")
a1.plot(d.fecha, d.precio.rolling(30, min_periods=20).mean(), color=TINTA, lw=1.4, label="media móvil de 30 días")
a1.set_yscale("log")
a1.set_ylabel("COP/kWh (escala log)")
a1.set_title("Precio de bolsa promedio del día, marzo de 2015 a octubre de 2026")
a1.legend(frameon=False, loc="upper left", ncol=2)
a2.plot(d.fecha, d.vol * (100 if d.vol.max() <= 1.5 else 1), color=AZUL, lw=1.2)
a2.set_ylabel("volumen útil\nde embalses (%)")
oni = d.oni.to_numpy()
a3.fill_between(d.fecha, 0, oni, where=oni >= 0, color=ROJO, alpha=0.75, lw=0, label="El Niño (+)")
a3.fill_between(d.fecha, 0, oni, where=oni < 0, color=AZUL, alpha=0.75, lw=0, label="La Niña (−)")
a3.axhline(0, color=TENUE, lw=0.8)
a3.set_ylabel("ONI (°C)")
a3.legend(frameon=False, loc="upper left", ncol=2)
for a in (a1, a2, a3):
    for x0, x1 in (("2015-09-01", "2016-04-30"), ("2023-07-01", "2024-05-31")):
        a.axvspan(pd.Timestamp(x0), pd.Timestamp(x1), color=claro(ROJO, 0.13), lw=0, zorder=0)
fig.tight_layout()
fig.savefig(SALIDA, dpi=170)
print("ok", SALIDA)
