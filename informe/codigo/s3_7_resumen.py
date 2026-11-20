"""Escribe la sección 3.7, Resumen de los modelos: un párrafo y una tabla con los tres modelos lado a lado. Todo lo que
dice la tabla ya está en las secciones 3.4, 3.5 y 3.6 (y en las tablas 5, 6, 7 y 11); aquí solo se junta.
La tabla nueva queda antes del capítulo IV, así que las tablas 14, 15 y 16 de ese capítulo pasan a ser 15, 16 y 17, y
se corrigen sus remisiones en el texto. La tabla puede seguir en la página siguiente, con el encabezado
repetido, para no dejar media página en blanco. Va después de s4_resultados.py.
Uso: python s3_7_resumen.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, leyenda, par, runs, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'


def fuente(texto):
    rpr = '<w:sz w:val="20"/>'
    texto = runs(texto).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace(
        "<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'{texto}</w:p>')


P = [
    "Los tres modelos pronostican lo mismo, el cambio en logaritmo de la ecuación (21) para los días *t* + 3 a "
    "*t* + 9, se diseñaron con datos hasta 2022 y se evalúan en las mismas filas y con el mismo criterio "
    "(sección 3.3). Se diferencian en la forma del modelo, en la información que reciben y en cómo se eligió cada "
    "parte. La tabla 14 los resume.",
]

TABLA = tabla([
    ["", "SARIMAX", "XGBoost", "LSTM"],
    ["Tipo de modelo", "Estadístico lineal", "Árboles con boosting de gradiente", "Red neuronal recurrente"],
    ["Estructura", "24 modelos, uno por hora, sobre la serie diaria del logaritmo del precio",
     "7 modelos directos, uno por horizonte, con las 24 horas juntas",
     "Una red codificador-decodificador para las 24 horas y los 7 días"],
    ["Cómo pronostica la semana", "De forma recursiva, 9 pasos desde *t*; se usan del 3 al 9",
     "Cada modelo pronostica su día", "Los 168 cambios a la vez"],
    ["Información de entrada", "Precio de la hora y festivo",
     "Precio del día *t*, 16 columnas de calendario y 10 o 20 columnas elegidas, con datos hasta el día *t*",
     "Precio, calendario, 4 variables del despacho de hoy y 5 del estado hidrológico, cada una desde el día en que "
     "se publica"],
    ["Elección de la información", "Preblanqueo, AICc y prueba *t*; la única variable que pasó no mejoró la "
     "validación", "Limpieza, SHAP frente a columnas de ruido y regla de un error estándar",
     "Selección hacia adelante por bloques, con Diebold-Mariano"],
    ["Elección de la configuración", "Un orden común, (1,1,2)(0,0,2)_{7}, que en la validación pronosticó igual "
     "que un orden por hora", "Búsqueda al azar de 30 combinaciones y regla de un error estándar (tabla 7)",
     "Búsqueda bayesiana de 30 configuraciones y evaluación con tres semillas (tabla 11)"],
    ["Tamaño", "6 coeficientes por hora, 144 en total", "De 100 a 300 árboles por modelo, con profundidad de 3 a 6",
     "183.576 parámetros"],
    ["Reentrenamiento", "Coeficientes cada mes; dentro del mes se actualiza con los precios nuevos",
     "Cada mes, con *h* + 1 días entre el entrenamiento y el periodo evaluado",
     "Cada mes, cuatro épocas, con el promedio de tres semillas"],
    ["Validación, 2020-2022", "4,7% en *h* = 3 a 9", "De 18,4% en *h* = 3 a 8,3% en *h* = 7",
     "14,6% en *h* = 3 a 9"],
    ["Software", "R, paquete forecast", "Python, librería xgboost", "Python, librería Keras"],
], [3.2, 4.1, 4.1, 4.1], junta=False)

NOTA = ("Nota: la validación es la reducción del RMSE en logaritmo frente al mejor de los dos ingenuos, con "
        "reentrenamiento mensual. En XGBoost, *h* = 8 y 9 usan la configuración de *h* = 7 y no tuvieron validación "
        "propia (sección 3.5). Fuente: elaboración propia.")

S37 = ("".join(par(t) for t in P)
       + leyenda("Tabla", "Resumen de los tres modelos.", ppr=ANTES_TABLA)
       + TABLA + fuente(NOTA))


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


d = Docx(ENTRADA)
B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]
i = [k for k, t in enumerate(T) if t == "3.7 Resumen de los modelos" and "Ttulo2" in d.doc[B[k][0]:B[k][1]]]
assert len(i) == 1, i
assert T[i[0] + 1] == "" and T[i[0] + 2] == "IV. Resultados", "la 3.7 ya tiene contenido"

# remisiones del capítulo IV a sus tablas, que suben un número; se cambian nodo por nodo de texto
cap4 = d.doc.find(">IV. Resultados<", B[i[0]][1])
assert cap4 > 0
cola = d.doc[cap4:]
antes = re.findall(r"\btablas? (1[4-6])\b", texto(cola))
assert sorted(antes) == ["14", "15", "16"], antes
cola = re.sub(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)",
              lambda mm: mm.group(1) + re.sub(r"\b(tablas? )(1[4-6])\b", lambda r: r.group(1) + str(int(r.group(2)) + 1),
                                               mm.group(2)) + mm.group(3), cola)
assert sorted(re.findall(r"\btablas? (1[5-7])\b", texto(cola))) == ["15", "16", "17"]
d.doc = d.doc[:cap4] + cola

s, e = B[i[0] + 1]
d.doc = d.doc[:s] + S37 + d.doc[e:]
d.renumerar()
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
for x in re.findall(r"\btablas? (\d+)", texto(d.doc), re.I):
    assert int(x) <= 17, x
d.guardar(SALIDA)
print("ok", SALIDA)
