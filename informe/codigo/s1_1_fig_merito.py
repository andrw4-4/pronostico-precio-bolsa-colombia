"""Cambia la imagen del orden de mérito que Andrés pegó en 1.1 por la versión de fig_orden_merito.py,
con su leyenda numerada, y ajusta las referencias a las figuras 1 y 2.
Uso: python s1_1_fig_merito.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import Docx, figura

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
PNG = Path(__file__).resolve().parents[1] / "figuras" / "f00_orden_merito.png"
LEYENDA = ("Formación del precio de bolsa en una hora, esquema simplificado. Las plantas se ordenan de la oferta "
           "más barata a la más cara hasta cubrir la demanda; el precio de bolsa es la oferta del recurso marginal, la "
           "última planta que hace falta. Fuente: elaboración propia con base en CREG (1995).")

d = Docx(ENTRADA)
d.agregar_imagen(PNG, "rIdFig00")
d.reemplazar_parrafo_con_imagen("Imagen 1", figura(PNG, "rIdFig00", 2002, 13, LEYENDA))
d.cambiar_texto("a la oferta de la última planta que hace falta en esa hora.",
                "a la oferta de la última planta que hace falta en esa hora (figura 1).")
d.cambiar_texto("1.000 COP/kWh (figura 1).", "1.000 COP/kWh (figura 2).")
d.guardar(SALIDA)
print("ok", SALIDA)
