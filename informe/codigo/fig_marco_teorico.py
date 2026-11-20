"""Figura de la sección 2.1: el cambio diario del logaritmo del precio. El precio en pesos ya está en la figura
de la sección 1.1 (fig_contexto.py), así que aquí va solo el cambio. El esquema del mercado de corto plazo
ahora está hecho con formas de Word (diagramas_word.py). El precio sale de paneles/panel_diario.csv, como en
3_datos_y_caracteristicas.ipynb."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo_graficas import PERIODOS, TENUE, TINTA, aplicar, claro

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"


# ----------------------------------------------------------------------------- precio y su cambio diario
def precio_y_cambio():
    panel = pd.read_csv(RAIZ / "paneles" / "panel_diario.csv", usecols=["fecha", "precio_bolsa"], parse_dates=["fecha"],
                        index_col="fecha")
    precio = panel["precio_bolsa"].loc["2015-01-01":"2026-10-06"]
    cambio = np.log(precio).diff()

    fig, b = plt.subplots(figsize=(7.4, 2.5))
    b.plot(cambio.index, cambio, color=TINTA, lw=0.4)
    b.axhline(0, color=TENUE, lw=0.6)
    b.set_ylabel("Cambio en logaritmo")
    # selección, validación y las dos pruebas (sección 3.3), con los colores de cada periodo
    alto = cambio.max() * 1.05
    for x0, x1, txt, periodo in [("2015-01-01", "2020-01-01", "Selección", "Ajuste"),
                                 ("2020-01-01", "2023-01-01", "Validación", "Validación"),
                                 ("2023-01-01", "2026-01-01", "Prueba", "Prueba"),
                                 ("2026-01-01", "2026-10-06", "2026", "Prueba 2026")]:
        b.axvspan(pd.Timestamp(x0), pd.Timestamp(x1), color=claro(PERIODOS[periodo], 0.14), lw=0, zorder=0)
        medio = pd.Timestamp(x0) + (pd.Timestamp(x1) - pd.Timestamp(x0)) / 2
        b.text(medio, alto, txt, ha="center", va="bottom", fontsize=8, color=TINTA)
    b.set_ylim(cambio.min() * 1.05, alto * 1.25)
    b.set_xlim(pd.Timestamp("2015-01-01"), pd.Timestamp("2026-10-06"))
    fig.savefig(FIG / "f13_precio_y_cambio.png")
    plt.close(fig)
    print(f"precio diario: {precio.min():.0f} a {precio.max():.0f} COP/kWh; cambio diario: {cambio.min():.2f} a "
          f"{cambio.max():.2f}; desviación por periodo:")
    print(cambio.groupby(pd.cut(cambio.index, pd.to_datetime(["2015", "2020", "2023", "2026", "2027"]),
                                right=False), observed=True).std().round(3).to_string())


if __name__ == "__main__":
    precio_y_cambio()
