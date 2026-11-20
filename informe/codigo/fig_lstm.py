"""Figura de la sección 3.6, LSTM: la importancia de cada grupo de variables. Las etapas de la construcción y
la arquitectura ahora están hechas con formas de Word (diagramas_word.py). Las cifras salen de
resultados/modelo_lstm_bloques/importancia_grupos.csv, que escribió 6c_lstm_seleccion.ipynb."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from estilo_graficas import COLORES, GRISES, TENUE, TINTA, aplicar, claro

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
RES = RAIZ / "resultados" / "modelo_lstm_bloques"
AZUL, FUERA = COLORES["LSTM"], GRISES["claro"]


# ----------------------------------------------------------------------------- importancia por grupos
NOMBRES = {
    "bloque 3: despacho de hoy": "Bloque 3, despacho de hoy",
    "bloque 4: estado hidrológico": "Bloque 4, estado hidrológico",
    "bloque 5: despacho de ayer": "Bloque 5, despacho de ayer",
    "bloque 6: clima que viene": "Bloque 6, clima que viene",
    "precio": "Precio",
    "generacion": "Generación",
    "ofertas": "Ofertas",
    "red_y_contratos": "Red y contratos",
    "demanda": "Demanda",
    "sistema": "Sistema",
    "mezcla_por_planta": "Mezcla por planta",
}


def importancia():
    d = pd.read_csv(RES / "importancia_grupos.csv")
    media = d.groupby("unidad").agg(variables=("variables", "first"), media=("aumento", "mean"))
    por_año = d.groupby(["unidad", "año"])["aumento"].mean().unstack()
    t = media.join(por_año).sort_values("media")
    color = [AZUL if u in ("bloque 3: despacho de hoy", "bloque 4: estado hidrológico")
             else COLORES["Precio real"] if u == "precio"
             else claro(AZUL, 0.4) if u.startswith("bloque") else FUERA for u in t.index]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    y = np.arange(len(t))
    ax.barh(y, t["media"], color=color, height=0.68, zorder=2)
    for i, (u, fila) in enumerate(t.iterrows()):
        ax.plot([fila[[2020, 2021, 2022]].min(), fila[[2020, 2021, 2022]].max()], [i, i], color=TINTA, lw=0.8,
                zorder=3)
        ax.scatter(fila[[2020, 2021, 2022]], [i] * 3, s=9, color=TINTA, zorder=4)
    ax.axvline(0, color=TENUE, lw=0.8)
    ax.set_yticks(y, [f"{NOMBRES[u]} ({int(n)})" for u, n in zip(t.index, t["variables"])], fontsize=7.5)
    ax.set_xlabel("Aumento del RMSE de la semana al desordenar el grupo (%)", fontsize=8)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.xaxis.grid(True, zorder=0)
    fig.legend(handles=[Patch(color=AZUL, label="Bloques que entraron"),
                        Patch(color=claro(AZUL, 0.4), label="Bloques que no entraron"),
                        Patch(color=FUERA, label="Grupos fuera de los bloques"),
                        Patch(color=COLORES["Precio real"], label="Precio"),
                        plt.Line2D([], [], color=TINTA, marker="o", ms=3, lw=0.8, label="Promedio de cada año")],
               loc="lower center", ncol=5, fontsize=6.8, bbox_to_anchor=(0.5, -0.07), handlelength=1.4,
               columnspacing=1.0)
    fig.savefig(FIG / "f26_lstm_importancia.png")
    plt.close(fig)
    print(t.round(2).to_string())


if __name__ == "__main__":
    importancia()
