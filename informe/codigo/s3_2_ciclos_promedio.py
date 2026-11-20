"""Aclara con qué se compara cada día y cada mes en los ciclos del precio (sección 3.2 y figura 7). Antes decía "la
media de los siete días centrada en él" y "más barato que su semana"; ahora dice "el promedio de su semana" y "el
promedio de su año", como la gráfica a) ya decía "el promedio de su día". El cálculo no cambia: la semana de cada día
son los siete días centrados en él y el año de cada mes, los 365 días centrados en él (fig_datos.py).
Uso: python s3_2_ciclos_promedio.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

CAMBIOS = [
    ("cada día con la media de los siete días centrada en él y cada mes con la media de los 365 días centrada en él, "
     "siempre en logaritmo.",
     "cada día con el promedio de su semana (los siete días centrados en él) y cada mes con el promedio de su año "
     "(los 365 días centrados en él), siempre en logaritmo."),
    ("El domingo es 8,6% más barato que su semana y un festivo entre semana, 5,7%.",
     "El domingo es 8,6% más barato que el promedio de su semana, y un festivo entre semana, 5,7%."),
    ("b) Cada día frente a la media de siete días centrada en él; F es un festivo entre semana. c) Cada mes frente a "
     "la media de 365 días centrada en él, en la mediana.",
     "b) Cada día frente al promedio de su semana; F es un festivo entre semana. c) Cada mes frente al promedio de "
     "su año, en la mediana."),
]

d = Docx(ENTRADA)
for viejo, nuevo in CAMBIOS:
    d.cambiar_texto(viejo, nuevo)
assert "centrada en él" not in d.doc and "que su semana" not in d.doc
d.guardar(SALIDA)
print("ok", SALIDA)
