"""Figura del capítulo III: el diseño del pronóstico en el tiempo. Los atrasos salen de docs/PANEL_HORARIO.md
(panel de la LSTM). La arquitectura de la LSTM ahora está hecha con formas de Word (diagramas_word.py)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from estilo_graficas import EXTRA, PERIODOS, TINTA, aplicar, claro

aplicar()
FIG = Path(__file__).resolve().parents[1] / "figuras"


# ----------------------------------------------------------------------------- diseño en el tiempo
def diseno():
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.4, 5.4), gridspec_kw=dict(height_ratios=[1, 2.3], hspace=0.55))

    # (a) los periodos
    tramos = [(2015 + 2 / 12, 2020, "Ajuste y selección\nde variables", PERIODOS["Ajuste"], "white"),
              (2020, 2023, "Validación", PERIODOS["Validación"], "#0b0b0b"),
              (2023, 2026, "Prueba", PERIODOS["Prueba"], "white"),
              (2026, 2026 + 279 / 365, "", PERIODOS["Prueba 2026"], "white")]
    for x0, x1, txt, color, tinta in tramos:
        a.add_patch(Rectangle((x0, 0), x1 - x0, 1, facecolor=color, edgecolor="white", lw=2))
        a.text((x0 + x1) / 2, 0.5, txt, ha="center", va="center", fontsize=9, color=tinta)
    # el tramo de 2026 es angosto: su etiqueta va encima
    a.text(2026 + 279 / 730, 1.08, "Prueba 2026\n(hasta el 6 de oct.)", ha="center", va="bottom", fontsize=8,
           color=TINTA)
    a.set_xlim(2015, 2027)
    a.set_ylim(0, 1)
    a.set_yticks([])
    a.set_xticks(range(2015, 2028))
    a.set_xticklabels([str(x) if x % 2 == 1 or x == 2026 else "" for x in range(2015, 2028)])
    a.spines[["left"]].set_visible(False)
    a.set_title("a) Periodos", loc="left", fontsize=10)

    # (b) qué se conoce el día del pronóstico R = t + 2
    filas = [("Ofertas y curva de mérito", 10), ("Contratos y restricciones", 5),
             ("Precio, demanda y generación", 2), ("Aportes y embalses", 1), ("Despacho programado", 0)]
    R = 0
    for i, (nombre, atraso) in enumerate(filas):
        fin = R - atraso
        b.add_patch(Rectangle((-16, i - 0.3), fin + 16 + 0.5, 0.6, facecolor=claro(EXTRA["verde"], 0.3),
                              edgecolor="none"))
        b.plot([fin + 0.5], [i], marker="o", color=TINTA, ms=4)
        b.text(-16.3, i, nombre, ha="right", va="center", fontsize=9)
        etiqueta = {0: "el mismo día", 1: "1 día antes"}.get(atraso, f"{atraso} días antes")
        # la etiqueta va dentro de la barra, a la izquierda del punto, para no pisar la semana pronosticada
        b.text(fin + 0.1, i, etiqueta, ha="right", va="center", fontsize=8, color=TINTA)
    # la semana que se pronostica: t + 3 a t + 9 = R + 1 a R + 7
    b.add_patch(Rectangle((R + 0.5, -0.4), 7, len(filas) - 0.2, facecolor="white", edgecolor=EXTRA["rojo"],
                          hatch="///", lw=1))
    b.text(R + 4, len(filas) - 0.45, "semana pronosticada\nt + 3 a t + 9\n(168 precios)", ha="center",
           va="bottom", fontsize=9)
    b.axvline(R + 0.5, color=TINTA, lw=1.2)
    # la línea de t llega solo hasta la fila del precio, para no cruzar las etiquetas de arriba
    b.vlines(-2 + 0.5, -1.6, 2.35, color=TINTA, lw=1, ls="--")
    b.text(R + 0.7, -0.75, "R = t + 2: día\ndel pronóstico", ha="left", va="top", fontsize=8.5)
    b.text(-2 + 0.3, -0.75, "t: último precio\nconocido", ha="right", va="top", fontsize=8.5)
    b.set_xlim(-16, 8.2)
    b.set_ylim(-1.6, len(filas) + 0.9)
    b.set_xticks([])
    b.set_yticks([])
    b.spines[["left", "bottom"]].set_visible(False)
    b.set_title("b) Último dato publicado de cada fuente el día del pronóstico", loc="left", fontsize=10)

    salida = FIG / "f03_diseno_pronostico.png"
    fig.savefig(salida)
    print("ok", salida)


if __name__ == "__main__":
    diseno()
