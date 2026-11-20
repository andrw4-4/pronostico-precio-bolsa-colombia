"""Ajusta el párrafo que sigue a los antecedentes de la 1.1 para que encaje con la versión nueva:
ya no se habla de un "vacío" y el ingenuo se llama "pronóstico de referencia".
Uso: python s1_1_antecedentes_v2b.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

d = Docx(ENTRADA)
d.cambiar_texto("Este proyecto busca cubrir ese vacío. Pronostica los 168", "En concreto, este proyecto pronostica los 168")
d.cambiar_texto("y juzga cada uno contra el pronóstico ingenuo, con un criterio",
                "y juzga cada uno contra el pronóstico de referencia, con un criterio")
d.guardar(SALIDA)
print("ok", SALIDA)
