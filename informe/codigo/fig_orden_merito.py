"""Figura del orden de mérito: cómo se forma el precio de bolsa de una hora (esquema simplificado).
El recurso marginal es la última planta que hace falta para cubrir la demanda; su oferta fija el
precio. La parte de su capacidad que queda a la derecha de la demanda no se despacha."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from estilo_graficas import EXTRA, GRISES, TINTA, aplicar, claro

aplicar()
SALIDA = Path(__file__).resolve().parents[1] / "figuras" / "f00_orden_merito.png"
VERDE, ROJO = EXTRA["verde"], EXTRA["rojo"]   # plantas despachadas y planta marginal

anchos = [3.0, 3.6, 3.4, 3.4]      # capacidad ofertada de cada recurso (unidades arbitrarias)
precios = [0.9, 2.0, 3.0, 4.4]     # precio de oferta de cada recurso
DEMANDA = 12.4                     # cae dentro del recurso 4

fig, ax = plt.subplots(figsize=(7.2, 4.2))
x = 0.0
for i, (w, p) in enumerate(zip(anchos, precios), start=1):
    if i < 4:
        ax.add_patch(Rectangle((x, 0), w, p, facecolor=claro(VERDE, 0.22), edgecolor=VERDE, lw=1))
        ax.text(x + w / 2, p + 0.12, f"Recurso {i}", ha="center", va="bottom", fontsize=10)
    else:
        despachado = DEMANDA - x
        ax.add_patch(Rectangle((x, 0), despachado, p, facecolor=ROJO, edgecolor=ROJO, lw=1))
        ax.add_patch(Rectangle((DEMANDA, 0), w - despachado, p, facecolor="white", edgecolor=claro(ROJO, 0.7),
                               hatch="///", lw=1))
        ax.text(x + despachado / 2, p / 2, "Recurso 4\n(marginal)", ha="center", va="center", fontsize=10,
                color="white", fontweight="bold")
        ax.text(x + w + 0.15, p / 2, "capacidad\nno despachada", ha="left", va="center",
                fontsize=9, color=GRISES["oscuro"])
    x += w

# precio de bolsa: la oferta del recurso marginal
ax.plot([0, DEMANDA], [precios[3], precios[3]], ls="--", color=TINTA, lw=1.2)
ax.text(0.15, precios[3] + 0.12, "Precio de bolsa", ha="left", va="bottom", fontsize=10.5, fontweight="bold")
# demanda de la hora
ax.plot([DEMANDA, DEMANDA], [0, 5.6], ls="-", color=TINTA, lw=1.8)
ax.text(DEMANDA, 5.7, "Demanda", ha="center", va="bottom", fontsize=10.5, fontweight="bold")

ax.set_xlim(0, sum(anchos) + 2.6)
ax.set_ylim(0, 6.3)
ax.set_xticks([])
ax.set_yticks([])
ax.set_xlabel("Capacidad disponible acumulada (MW)")
ax.set_ylabel("Precio de oferta (COP/kWh)")
ax.spines[["left", "bottom"]].set_color(TINTA)
plt.tight_layout()
plt.savefig(SALIDA)
print("ok", SALIDA)
