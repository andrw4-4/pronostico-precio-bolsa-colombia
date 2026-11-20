"""Correcciones del 20 de noviembre de 2026, pedidas por Andrés, sobre su propia versión del informe.
1. Se quita del texto la frase "decisión del autor". Las decisiones se mantienen; solo sale la frase. Donde iba
   entre paréntesis, sale el paréntesis; "El umbral de 5% es decisión del autor." sale entera, porque la frase
   anterior ya dice cuál es el umbral; y en la regla del bloque 6 de la LSTM el paréntesis se cambia por la razón
   de la regla.
2. Se arreglan los espacios que quedaron al borrar a mano esa frase en Word ("igual .", "semillas . Cada",
   "La regla, era que", "épocas.Ese").
3. Correcciones de texto revisadas en la conversación:
   - 3.5: qué quiere decir que el error de validación sea optimista.
   - 3.6: el calendario no se estandariza ni se recorta (ecuación 25); por qué el bloque 6 depende del 4; "las cinco
     primeras" eran cuatro (tabla 12, resultados/modelo_lstm_bloques/evaluacion_tres_semillas.csv); la nota de la
     tabla 10 aclara que las filas no son acumulativas (seleccion.csv: los bloques 5 y 6 se agregaron por separado).
   - 3.7: la nota de la tabla 14 dice qué es la fila de validación. Además corrige un error: la validación de la
     LSTM (14,6%) se entrenó una vez por año, no cada mes (sección 3.6, "entrenando una vez por año").
   - 4.1: la columna de mejora de la tabla 17 dice que es en pesos.
4. Figura nueva al final de la 4.1, con la semana del 9 al 15 de octubre de 2026 (fig_semana_final.py), citada en el
   párrafo de esa semana. Es la última figura numerada, así que no se corre ninguna referencia.
Cada texto viejo debe estar una sola vez; si no está, el script falla sin guardar.
Uso: python s_correcciones_20nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

from docx_final import Docx, figura, reemplazar_en_bloque, runs

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"


def texto(x):
    return Docx.texto(x)


def es_indice(x):
    return 'w:val="TDC' in x[:400]


def bloque_con(d, trozo):
    """El único bloque del cuerpo, fuera del índice, cuyo texto contiene `trozo`."""
    B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
    k = [(s, e) for s, e in B if trozo in texto(d.doc[s:e])]
    assert len(k) == 1, f"hay {len(k)} bloques con {trozo!r}"
    return k[0]


def cambiar(d, viejo, nuevo):
    s, e = bloque_con(d, viejo)
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def runs_nota(t):
    """Runs en letra de 10 puntos, como las demás notas de tablas."""
    r = runs(t).replace("<w:r><w:rPr><w:i/><w:iCs/></w:rPr>", '<w:r><w:rPr><w:i/><w:iCs/><w:sz w:val="20"/></w:rPr>')
    return r.replace("<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')


def cambiar_nota(d, inicio, nuevo):
    """Cambia todo el texto de la nota que empieza con `inicio`, conservando el formato del párrafo."""
    B = [(s, e) for s, e in d.bloques() if texto(d.doc[s:e]).startswith(inicio)]
    assert len(B) == 1, f"hay {len(B)} notas que empiezan con {inicio!r}"
    s, e = B[0]
    x = d.doc[s:e]
    assert set(re.findall(r"<w:rPr>.*?</w:rPr>", x, re.S)) <= {
        '<w:rPr><w:sz w:val="20"/></w:rPr>', '<w:rPr><w:i/><w:iCs/><w:sz w:val="20"/></w:rPr>'}, "otro formato"
    apertura = re.match(r"<w:p(?:\s[^>]*)?>", x).group(0)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", x, re.S)
    d.doc = d.doc[:s] + apertura + (ppr.group(0) if ppr else "") + runs_nota(nuevo) + "</w:p>" + d.doc[e:]


NOTA_10 = ("Nota: cada fila agrega un bloque a la referencia del momento, no a la fila anterior. Con la configuración "
           "fija, los bloques 5 y 6 se agregaron por separado a los bloques 1 a 4. Con la configuración 2, el bloque 5 "
           "se agregó a los bloques 1 a 3, y el 6 no se probó porque no entró el 4. La configuración 2 tiene dos "
           "capas, 192 unidades, capa de entrada de 128, dropout de 0,5, tasa de aprendizaje de 0,0028, lotes de 64 y "
           "ventana de 14 días. Fuente: elaboración propia con datos de XM (2026).")
NOTA_14 = ("Nota: la fila de validación es la mejora del RMSE en logaritmo frente al mejor de los dos ingenuos en "
           "2020-2022, la misma medida de la tabla 15, con la configuración final de cada modelo y antes de abrir la "
           "prueba. SARIMAX y XGBoost se reentrenaron cada mes y la LSTM una vez por año (sección 3.6). En XGBoost "
           "cada horizonte se validó por separado, de ahí el rango de *h* = 3 a *h* = 7; *h* = 8 y 9 usan la "
           "configuración de *h* = 7 y no tuvieron validación propia (sección 3.5). Fuente: elaboración propia.")
LEYENDA = ("Precio real y pronósticos de la semana del 9 al 15 de octubre de 2026, hora por hora, con los precios "
           "conocidos hasta el 6 de octubre. Fuente: elaboración propia con datos de XM (2026).")

# ----------------------------------------------------------------------------- cambios
d = Docx(ENTRADA)
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 17
assert "f29_semana_final" not in d.doc and "rIdFig29" not in d.archivos["word/_rels/document.xml.rels"].decode()
n_bloques = len(d.bloques())

# 1. la frase "decisión del autor"
cambiar(d, "El umbral de 5% es decisión del autor. ", "")
cambiar(d, "y el 6 solo se prueba si entró el 4 (decisión del autor).",
        "y el 6 solo se prueba si entró el 4, porque el clima afecta el precio a través del agua de los embalses.")
while True:
    B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e]) and "(decisión del autor)" in texto(d.doc[s:e])]
    if not B:
        break
    s, e = B[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], " (decisión del autor)", "") + d.doc[e:]

# 2. espacios que quedaron al borrar la frase a mano
cambiar(d, "no se comportan igual .", "no se comportan igual.")
cambiar(d, "La regla, era que", "La regla era que")
cambiar(d, "épocas.Ese número", "épocas. Ese número")

# 3. correcciones de texto
cambiar(d, "El error de validación es algo optimista, porque",
        "El error de validación es algo optimista, es decir, puede ser menor que el que tendría el modelo con datos "
        "nuevos, porque")
cambiar(d, "y promedia tres semillas . Cada columna del vector del día se estandariza y se recorta:",
        "y promedia tres semillas. Cada columna del vector del día, salvo las del calendario, se estandariza y se "
        "recorta:")
cambiar(d, "Las cinco primeras usan los bloques 1 a 4", "Las cuatro primeras usan los bloques 1 a 4")
cambiar_nota(d, "Nota: la configuración 2 tiene dos capas", NOTA_10)
cambiar_nota(d, "Nota: la validación es la reducción del RMSE", NOTA_14)

# encabezado de la tabla 17: la mejora es en pesos
B = d.bloques()
i = [k for k, (s, e) in enumerate(B) if texto(d.doc[s:e]).startswith("Tabla 17. ")]
assert len(i) == 1
s, e = B[i[0] + 1]
tb = d.doc[s:e]
assert tb.startswith("<w:tbl") and tb.count(">Mejora (%)</w:t>") == 1
d.doc = d.doc[:s] + tb.replace(">Mejora (%)</w:t>", ">Mejora en pesos (%)</w:t>") + d.doc[e:]

# 4. figura de la semana final, después del párrafo que la comenta y citada en él
cambiar(d, "antes de que XM publicara esos precios.", "antes de que XM publicara esos precios (figura 18).")
s, e = bloque_con(d, "Por último, con los precios conocidos hasta el 6 de octubre de 2026")
PNG = FIG / "f29_semana_final.png"
d.agregar_imagen(PNG, "rIdFig29")
d.doc = d.doc[:e] + figura(PNG, "rIdFig29", 2029, 15.5, LEYENDA) + d.doc[e:]

# ----------------------------------------------------------------------------- comprobaciones
d.renumerar()
cuerpo = [texto(d.doc[s:e]) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
todo = " ".join(cuerpo)
assert "decisión del autor" not in todo
parrafos = " | ".join(texto(d.doc[s:e]) for s, e in d.bloques()
                      if not es_indice(d.doc[s:e]) and not d.doc[s:e].startswith("<w:tbl"))
suelto = re.search(r".{0,40}(\w \.|\w ,|[a-záéíóúñ]\.[A-ZÁÉÍÓÚ]).{0,40}", parrafos)
assert not suelto, suelto.group(0)
for t in ["es decir, puede ser menor que el que tendría el modelo con datos nuevos",
          "salvo las del calendario", "a través del agua de los embalses", "Las cuatro primeras",
          "no a la fila anterior", "la LSTM una vez por año", "Mejora en pesos (%)", "(figura 18)",
          "Figura 18. Precio real y pronósticos de la semana"]:
    assert todo.count(t) == 1, t
assert len(d.bloques()) == n_bloques + 2
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 18
d.guardar(SALIDA)
print("ok", SALIDA)
