"""Quita la sección 4.3 (Ahorro aproximado en un año) y lleva la idea a la 5.2, como limitación y como línea de
trabajo futuro, a pedido de Andrés del 19 de noviembre de 2026: en vez de estimar cuánto ahorraría al año una planta
con reglas sencillas, se propone construir un algoritmo que optimice una decisión con el pronóstico.
1. Se borran el título 4.3, sus párrafos, la tabla 20 y su nota, y las frases que la citaban en el resumen y la 5.1.
2. En la 5.2, la limitación de los dos casos de la sección 4.2 dice que son reglas sencillas y no una decisión
   optimizada, y se agrega la línea "Optimizar una decisión con el pronóstico" después de la de pronósticos con
   incertidumbre; las líneas de trabajo pasan de seis a siete.
La 4.2 no cambia: sigue con elegir el día más barato (tabla 18) y con el comercializador (tabla 19).
Uso: python s4_3_quitar.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, par

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
TITULO = "4.3 Ahorro aproximado en un año"

CAMBIOS = [
    # resumen y 5.1: vuelven a como estaban antes de la 4.3
    ("frente a consumir lo mismo todos los días, unos 53 millones de pesos por año por cada MW que se mueva un día "
     "por semana.",
     "frente a consumir lo mismo todos los días."),
    ("quien conociera los precios reales (tabla 18). Para una planta que mueve cada semana un día de un proceso de "
     "1 MW, eso equivale a unos 53 millones de pesos por año en 2023-2025 (sección 4.3).",
     "quien conociera los precios reales (tabla 18)."),
    # 5.2: la limitación
    ("Y los dos casos de la sección 4.2 son sencillos: el consumidor paga el precio de bolsa sin contratos, mover su "
     "consumo no cuesta nada y su consumo no cambia el precio, y el comercializador compra un bloque plano, sin contar "
     "el error en el pronóstico de su propia demanda. Con eso en cuenta, quedan seis líneas de trabajo.",
     "Y los dos casos de la sección 4.2 son reglas sencillas y no una decisión optimizada: el consumidor paga el precio "
     "de bolsa sin contratos, mover su consumo no cuesta nada y su consumo no cambia el precio, y el comercializador "
     "compra un bloque plano, sin contar el error en el pronóstico de su propia demanda. Por eso no miden cuánto "
     "ahorraría en un año quien use el pronóstico. Con eso en cuenta, quedan siete líneas de trabajo."),
]

LINEA = ("Optimizar una decisión con el pronóstico. Las reglas de la sección 4.2 solo eligen el día más barato de la "
         "semana o leen si la semana sube o baja. Un trabajo futuro podría construir un algoritmo que use los 168 "
         "precios pronosticados para optimizar una decisión concreta, con sus restricciones y costos reales: el "
         "programa semanal de producción de una planta, cuánta energía comprar en bolsa o en contratos un "
         "comercializador, o en qué días hacer un mantenimiento. Con esa decisión se podría medir cuánto ahorraría en "
         "un año quien use el pronóstico, algo que este trabajo no estima.")


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


d = Docx(ENTRADA)
assert d.doc.count("SEQ Tabla ") == 20 and d.doc.count("SEQ Figura ") == 17
B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]
X = [d.doc[s:e] for s, e in B]
i = [k for k, t in enumerate(T) if t == TITULO and "Ttulo2" in X[k]]
j = [k for k, t in enumerate(T) if t == "V. Conclusiones" and "Ttulo1" in X[k]]
assert len(i) == 1 and len(j) == 1 and i[0] < j[0]
quitar = T[i[0]:j[0]]
assert quitar[1].startswith("Para dar una idea de lo que vale el pronóstico en dinero")
assert quitar[2].startswith("Tabla 20. ") and quitar[-1].startswith("Estas cifras son una idea del orden de magnitud")
assert len(quitar) == 8, len(quitar)          # título, párrafo, leyenda, tabla, nota y tres párrafos
d.doc = d.doc[:B[i[0]][0]] + d.doc[B[j[0]][0]:]

for viejo, nuevo in CAMBIOS:
    d.cambiar_texto(viejo, nuevo)

# la línea nueva va después de la de pronósticos con incertidumbre
B = d.bloques()
k = [n for n, (s, e) in enumerate(B) if texto(d.doc[s:e]).startswith("Pronósticos con incertidumbre.")]
assert len(k) == 1
p = d.doc[B[k[0]][0]:B[k[0]][1]]
# el título de cada línea va en cursiva al comienzo del párrafo: se copia el mismo formato
assert re.search(r"<w:i/><w:iCs/></w:rPr><w:t>Pronósticos con incertidumbre\.</w:t>", p), "otro formato"
fin = B[k[0]][1]
d.doc = d.doc[:fin] + par(LINEA.replace("Optimizar una decisión con el pronóstico.",
                                        "*Optimizar una decisión con el pronóstico.*", 1)) + d.doc[fin:]

d.renumerar()
todo = "".join(texto(d.doc[s:e]) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e])
assert TITULO not in todo and "sección 4.3" not in todo and "tabla 20" not in todo and "Tabla 20" not in todo
assert "53 millones" not in todo and "quedan siete líneas de trabajo" in todo
assert todo.count("Optimizar una decisión con el pronóstico.") == 1
assert d.doc.count("SEQ Tabla ") == 19 and d.doc.count("SEQ Figura ") == 17
d.guardar(SALIDA)
print("ok", SALIDA)
