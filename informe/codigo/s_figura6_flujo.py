"""Rehace la figura 6 (flujo de los datos) para que muestre qué toma cada modelo. Antes las 134 variables base y las
1.861 columnas derivadas salían juntas del paso 2c, y SARIMAX quedaba colgado del 2d, que es la selección de
XGBoost. Ahora de las variables base salen tres caminos: SARIMAX las toma como candidatas sin derivar (sección 3.4),
XGBoost pasa por las columnas derivadas y la selección del 2d (sección 3.5) y la LSTM por su propio panel, del 2e al
2h, con cada variable desde el día en que se publica (sección 3.6). Los tres llegan a la comparación del capítulo IV.
Los pasos 2 y 2b quedan en un mismo recuadro para que quepan las seis columnas. El dibujo sale de
diagramas_word.flujo() y conserva su número (Diagrama 3014); la leyenda se ajusta.
Uso: python s_figura6_flujo.py ENTRADA.docx SALIDA.docx"""
import sys

import diagramas_word as dw
from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

d = Docx(ENTRADA)
bloques = [(s, e) for s, e in d.bloques() if 'name="Diagrama 3014"' in d.doc[s:e]]
assert len(bloques) == 1, len(bloques)
s, e = bloques[0]
viejo = d.doc[s:e]
assert "Columnas para XGBoost en cada horizonte" in viejo and "1.861 derivadas" in viejo
d.doc = d.doc[:s] + dw.flujo() + d.doc[e:]

d.cambiar_texto("Flujo de los datos, de la descarga a los paneles que usan los modelos.",
                "Flujo de los datos, de la descarga a la comparación de los modelos.")
assert d.doc.count('name="Diagrama 3014"') == 1 and "SARIMAX: 2" not in d.doc
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
d.guardar(SALIDA)
print("ok", SALIDA)
