"""Quita del informe los dos casos de decisión que al final no se hicieron (24 de noviembre de 2026).
Elegir el día más barato de la semana y estimar el costo de la semana de un comercializador se anunciaban en tres
partes, pero el informe ya no los compara: la 4.2 revisa los usos del pronóstico a partir de la literatura.
- Resumen: salen las cifras de los casos (43 a 51 COP/kWh y el 74% de las semanas). En su lugar queda lo que sí
  muestran los resultados (la LSTM pronostica mejor el nivel y XGBoost la forma) y que el valor no se midió.
- 1.1: la frase que anunciaba los dos casos pasa a anunciar la revisión de la 4.2.
- 1.3: sale la frase que decía que el valor se medía con los dos casos.
Uso: python s_43_sin_casos_24nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, reemplazar_en_bloque

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
CAMBIOS = [
    # resumen
    ("Si se usa para elegir el día más barato de la semana, el pronóstico de la LSTM ahorra entre 43 y 51 COP/kWh "
     "frente a consumir lo mismo todos los días. Es más del doble de lo que ahorra el ingenuo semanal. ", ""),
    ("Para estimar el costo de la semana de un comercializador, ningún modelo mejora de forma significativa, aunque la "
     "LSTM acierta si el precio de la semana sube o baja en 74% de las semanas en que cambia más de 10%.",
     "La LSTM pronostica mejor el nivel de cada día y XGBoost la forma de las horas dentro del día. El trabajo no mide "
     "cuánto vale esa mejora en una decisión concreta, como la compra de energía de un comercializador; eso queda "
     "como trabajo futuro."),
    # 1.1
    ("Además, traduce la mejora del pronóstico a dos casos concretos, elegir el día más barato de la semana para un "
     "consumidor y estimar el costo de la semana para un comercializador, para medir cuánto vale en pesos.",
     "Además, revisa en la literatura para qué decisiones sirve un pronóstico del precio y qué indican los resultados "
     "sobre esos usos (sección 4.2)."),
    # 1.3
    (" El valor del pronóstico se mide con dos casos sencillos, elegir el día más barato de la semana y estimar el "
     "costo de la semana para un comercializador, y no con una estrategia de contratación o de operación de una "
     "planta.", ""),
]


def cuerpo(d):
    """(inicio, fin, texto) de cada bloque del cuerpo, sin el índice."""
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


d = Docx(ENTRADA)
antes = [t for _, _, t in cuerpo(d)]

for viejo, nuevo in CAMBIOS:
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]

despues = [t for _, _, t in cuerpo(d)]
# mismos bloques, y solo cambian los tres párrafos
assert len(antes) == len(despues)
cambiados = [i for i, (a, b) in enumerate(zip(antes, despues)) if a != b]
assert len(cambiados) == 3, cambiados
# no queda nada de los casos en el cuerpo
todo = " ".join(despues)
# ("dos casos" sigue en la búsqueda de control de la LSTM, que es otra cosa)
for x in ("dos casos concretos", "dos casos sencillos", "día más barato", "43 y 51", "74%", "costo de la semana"):
    assert x not in todo, x
# lo que dice el resumen nuevo ya está en el cuerpo
assert "la LSTM pronostica mejor" in todo and "XGBoost pronostica mejor la forma de las horas dentro del día" in todo
assert re.search(r"Valor para la toma de decisiones", todo)
for i in cambiados:
    print("ANTES:  ", antes[i][-420:])
    print("DESPUÉS:", despues[i][-420:])
    print()
d.guardar(SALIDA)
print("ok", SALIDA)
