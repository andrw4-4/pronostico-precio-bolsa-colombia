"""Escribe la sección 3.5, XGBoost: la selección de columnas, la búsqueda de hiperparámetros, la validación,
las variantes y el modelo final, con la fórmula de cada criterio.
Las cifras salen de 2d_seleccion_variables.py (paneles/panel_horario_modelo_columnas.csv y
panel_horario_modelo_validacion.csv), de 4_modelo_xgboost.ipynb y de resultados/modelo_xgboost/ (RESULTADOS.md,
configuracion_final.json, etapa2 a etapa4). Las figuras salen de fig_xgboost.py.
Uso: python s3_5_xgboost.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import (Docx, acento, barra, ecuacion, figura, frac, leyenda, m, mr, par, paren, raiz, runs, sub,
                        suma, sup, tabla)

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'
FUENTE_XM = "Fuente: elaboración propia con datos de XM (2026)."


def fuente(texto):
    # runs() pone las cursivas; aquí solo se baja el tamaño a 10 puntos, como en tabla()
    rpr = '<w:sz w:val="20"/>'
    texto = runs(texto).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace(
        "<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'{texto}</w:p>')


def bloque(textos):
    return "".join(par(t) for t in textos)


# ----------------------------------------------------------------------------- ecuaciones
s = lambda base, i: sub(m(base), m(i))
EC34 = (s("ρ", "S") + m("=1−") + frac(m("6") + suma(m("i"), "", sup(s("d", "i"), m("2"))),
                                       m("n") + paren(sup(m("n"), m("2")) + m("−1"))))
EC35 = (s("φ", "j") + paren(m("x")) + m("=") + suma(m("S⊆F∖{j}"), "",
        frac(m("|S|!") + paren(m("|F|−|S|−1")) + m("!"), m("|F|!"))
        + paren(m("f") + paren(m("S∪{j}")) + m("−f") + paren(m("S")), "[", "]")))
EC36 = (s("I", "j") + m("=") + frac(m("1"), m("N")) + suma(m("i=1"), m("N"),
        paren(s("φ", "j") + paren(s("x", "i")), "|", "|")))
MSE = lambda i: sub(mr("MSE"), i)
EC37 = (sup(m("k"), m("*")) + m("=") + mr("mín ") + paren(m("k: ") + MSE(m("k")) + m("≤") + MSE(mr("mín")) + m("+")
        + mr("ee") + paren(MSE(mr("mín"))), "{", "}"))
EC38 = (s("L", "δ") + paren(m("e")) + m("=") + sup(m("δ"), m("2"))
        + paren(raiz(m("1+") + sup(paren(frac(m("e"), m("δ"))), m("2"))) + m("−1"), "[", "]") + m(",   δ=0,2"))
EC39 = (sub(sup(acento(m("y")), m("c")), m("t,h,H")) + m("=") + sub(acento(m("y")), m("t,h,H")) + m("−")
        + sub(barra(m("e")), m("t")))

# ----------------------------------------------------------------------------- tablas
TABLA_COLUMNAS = tabla([
    ["Paso", "*h* = 3", "*h* = 4", "*h* = 5", "*h* = 6", "*h* = 7"],
    ["Columnas candidatas", "1.861", "1.861", "1.861", "1.861", "1.861"],
    ["Después de la limpieza", "1.289", "1.290", "1.291", "1.290", "1.289"],
    ["Le ganan al ruido en los dos cortes", "15", "43", "89", "99", "117"],
    ["Regla de un error estándar", "10", "20", "10", "10", "20"],
], [5.4, 1.8, 1.8, 1.8, 1.8, 1.8])

TABLA_HIPER = tabla([
    ["*h*", "Profundidad máxima", "Peso mínimo por hoja", "Árboles", "Fracción de filas", "Fracción de columnas",
     "*λ*"],
    ["3", "4", "50", "200", "0,75", "0,82", "8,39"],
    ["4", "5", "240", "200", "0,71", "0,79", "1,50"],
    ["5", "3", "50", "300", "0,72", "0,75", "8,46"],
    ["6", "4", "240", "200", "0,88", "0,74", "5,36"],
    ["7, 8 y 9", "6", "50", "100", "0,74", "0,54", "3,80"],
], [1.6, 2.3, 2.3, 1.7, 2.4, 2.4, 1.6])

TABLA_VARIANTES = tabla([
    ["*h*", "Base", "Pseudo-Huber", "Últimos 3 años", "Corrección del sesgo", "Error estándar de la base"],
    ["3", "0,0384", "0,0385", "0,0386", "0,0418", "0,0037"],
    ["4", "0,0477", "0,0483", "0,0480", "0,0543", "0,0052"],
    ["5", "0,0580", "0,0578", "0,0567", "0,0674", "0,0066"],
    ["6", "0,0707", "0,0715", "0,0714", "0,0879", "0,0078"],
    ["7", "0,0771", "0,0779", "0,0787", "0,0999", "0,0091"],
], [1.2, 2.0, 2.4, 2.6, 3.0, 3.4])

# ----------------------------------------------------------------------------- texto
S35 = (
    bloque([
        "XGBoost se construyó en cinco etapas, todas con datos hasta 2022 (figura 13): elegir las columnas de cada "
        "horizonte, buscar los hiperparámetros, validarlos con reentrenamiento mensual, probar variantes del "
        "entrenamiento y fijar la configuración final. La primera etapa está en el script 2d_seleccion_variables.py, "
        "que quedó fijo el 1 de noviembre de 2026, y las demás en el notebook 4_modelo_xgboost.ipynb, con la librería "
        "xgboost de Python (Chen y Guestrin, 2016).",
    ])
    + figura(FIG / "f21_xgboost_construccion.png", "rIdFig21", 2021, 15,
             "Etapas de la construcción de XGBoost. Fuente: elaboración propia.")
    + bloque([
        "*El modelo.* Hay un modelo directo para cada horizonte (sección 2.3): siete modelos, de *h* = 3, el primer "
        "día pronosticado, a *h* = 9, el séptimo. Cada uno se entrena por separado, con su propio objetivo, el cambio "
        "en logaritmo de la ecuación (21) a *h* días, y puede quedar con columnas e hiperparámetros distintos. Cada "
        "fila de entrenamiento es un día *t* con una hora *H*: las 24 horas van en el mismo modelo y la hora entra "
        "como una variable más. Así, el modelo comparte lo que aprende entre horas, y un árbol puede separar la "
        "madrugada de la punta con un solo corte, sin necesitar un modelo por hora como SARIMAX. En todos los "
        "horizontes, la pérdida es el error cuadrático de la ecuación (4) y la tasa de aprendizaje es 0,03.",

        "La selección y la búsqueda se hicieron cuando el alcance era de 30 días, solo en algunos horizontes: *h* = 1 "
        "a 7, 14 y 30. Cada horizonte intermedio usa las columnas y los hiperparámetros del más cercano, así que "
        "*h* = 8 y 9, los días 6 y 7 de la semana pronosticada, usan los de *h* = 7 (decisión del autor). Se entrenan "
        "aparte, con su propio objetivo y con el calendario de su día, pero no tuvieron selección ni validación "
        "propias. Por eso las tablas y figuras de las etapas de construcción llegan hasta *h* = 7.",

        "*Columnas candidatas.* De las 134 variables base (sección 3.2) se construyeron 1.861 columnas, entre 10 y "
        "43 por variable: rezagos del precio, como en el modelo LEAR (Lago et al., 2021), medias móviles de varios "
        "plazos, como en el modelo HAR (Corsi, 2009), tendencias, medidas de variabilidad y la memoria de los picos "
        "recientes. El volumen útil de los embalses, por ejemplo, da diez columnas: su valor de hoy, de ayer, de "
        "hace dos y de hace siete días, sus medias de 7 y 30 días, su cambio en 7 días, la diferencia entre esas dos "
        "medias y su variabilidad en 7 y 30 días. Además, siempre entran, sin pasar por la selección, el precio del "
        "día *t* y 16 columnas de calendario, del día *t* y del día que se pronostica. Con tantas columnas, un modelo "
        "de árboles termina usando algunas por azar; por eso se eligieron para cada horizonte con un embudo de tres "
        "pasos.",

        "*Primer paso: limpieza (2015-2019).* Salieron 10 columnas casi constantes, 106 inestables, de 18 variables, "
        "y 12 con niveles que siguen al dólar, de las que solo se conservó su cambio, con las mismas reglas de la "
        "sección 3.4. A diferencia de SARIMAX, aquí la limpieza es por columna y no por variable: el nivel de la "
        "demanda, por ejemplo, crece con los años y sale como inestable, pero su cambio en 7 días se queda.",

        "Después salieron las columnas redundantes. Cuando dos columnas se mueven casi igual, el árbol reparte entre "
        "ellas lo que aprende y ninguna aporta más que una sola. Se midió con la correlación de Spearman (1904),",
    ])
    + ecuacion(EC34, 34)
    + bloque([
        "donde *d*_{i} es la diferencia entre la posición de la observación *i* en el orden de una columna y en el de "
        "la otra, y *n* es el número de observaciones. Al usar posiciones y no valores, mide si dos columnas suben y "
        "bajan juntas aunque la relación no sea lineal, y la afectan menos los picos. De cada grupo de columnas con "
        "ρ_{S} > 0,95 entre sí quedó la que más se correlaciona con el objetivo del horizonte. Salieron 444, y "
        "quedaron unas 1.290.",

        "*Segundo paso: importancia frente a columnas de ruido (2015-2019).* Para medir cuánto usa el modelo cada "
        "columna se usó el valor SHAP (Lundberg y Lee, 2017). Este reparte el pronóstico de cada fila *x* entre las "
        "columnas, según cuánto cambia el pronóstico cuando una columna se agrega a las demás:",
    ])
    + ecuacion(EC35, 35)
    + bloque([
        "donde *F* es el conjunto de columnas, *S* un subconjunto que no incluye la columna *j* y *f*(*S*) el "
        "pronóstico del modelo con solo las columnas de *S*. El valor φ_{j} promedia el aporte de *j* sobre todos los "
        "órdenes posibles en que se pueden agregar las columnas; para árboles se calcula de forma exacta y rápida "
        "(Lundberg et al., 2020). La importancia de una columna es el promedio de su valor absoluto sobre las *N* "
        "filas,",
    ])
    + ecuacion(EC36, 36)
    + bloque([
        "y se calculó en dos cortes: entrenando con 2015-2017 y midiendo en 2018, y entrenando con 2015-2018 y "
        "midiendo en 2019, para medir cuánto usa el modelo la columna con datos que no vio. Al modelo se le agregaron "
        "10 columnas de ruido, copias de columnas reales con los días barajados, que por construcción no dicen nada del "
        "objetivo. Una columna siguió solo si su importancia superó la del mejor ruido en los dos cortes, como en el "
        "método Boruta (Kursa y Rudnicki, 2010). Pasaron 15 columnas en *h* = 3, 43 en *h* = 4, 89 en *h* = 5, 99 en "
        "*h* = 6 y 117 en *h* = 7, ordenadas por su importancia media.",

        "*Tercer paso: cuántas columnas (2020-2022).* Con las primeras *k* columnas del orden, con *k* = 10, 20, 40, "
        "80, 160 o todas las que pasaron, se entrenó con 2015-2019 y se midió el error en 2020-2022. Se eligió con la "
        "regla de un error estándar (Hastie et al., 2009),",
    ])
    + ecuacion(EC37, 37)
    + bloque([
        "es decir, el número más pequeño de columnas cuyo error no supera al mínimo en más de un error estándar. El "
        "MSE es el promedio del error cuadrático de cada día, y su error estándar se calcula con Newey y West, como en "
        "la sección 3.3. Entre dos modelos que no se distinguen del azar, se prefiere el más simple. Quedaron 10 "
        "columnas en *h* = 3, 5 y 6, y 20 en *h* = 4 y 7 (tabla 8 y figura 14). Entre todos los horizontes son 37 "
        "columnas, del precio y de otras 17 variables base.",
    ])
    + leyenda("Tabla", "Columnas que quedan en cada paso de la selección de XGBoost.", ppr=ANTES_TABLA)
    + TABLA_COLUMNAS
    + fuente("Nota: a las columnas elegidas se suman siempre el precio del día *t* y 16 columnas de calendario. "
             "*h* = 8 y 9 usan las columnas de *h* = 7 y no tuvieron selección propia. " + FUENTE_XM)
    + bloque([
        "La figura 14 muestra también el caso *k* = 0, con solo el precio y el calendario. Con eso, XGBoost pierde "
        "contra el ingenuo del día en todos los horizontes: en *h* = 3 su RMSE es 0,252, frente a 0,240 del ingenuo, y "
        "con las 10 columnas elegidas baja a 0,206. Lo que le permite ganarle al ingenuo es la información de las "
        "columnas, no la forma del modelo.",
    ])
    + figura(FIG / "f22_xgboost_columnas.png", "rIdFig22", 2022, 15,
             "RMSE en logaritmo en 2020-2022 según el número *k* de columnas, con el modelo entrenado en 2015-2019, "
             "para los horizontes con selección propia. *k* = 0 es el modelo con solo el precio y el calendario. "
             + FUENTE_XM)
    + bloque([
        "Las columnas elegidas cambian con el horizonte (figura 15). Las más importantes son del propio precio: el "
        "precio de la hora frente a la media de su día y frente a sus medias de 7 y 30 días, y su distancia a los "
        "máximos de las últimas 24 horas y de la última semana; cuatro de ellas están en los cinco horizontes. En "
        "*h* = 3 se suman el margen ofertado de hace tres días, los aportes hídricos y su cambio semanal, y la "
        "presión sobre el agua, que cambian rápido. En *h* = 7 pesan más columnas de medio plazo: la generación con "
        "carbón en los últimos 30 días, el margen declarado y la demanda de hace 14 días, y la distancia al precio de "
        "escasez.",
    ])
    + figura(FIG / "f23_xgboost_importancia.png", "rIdFig23", 2023, 15,
             "Las 12 columnas más importantes de los modelos de *h* = 3 y *h* = 7, según el promedio del valor "
             "absoluto de SHAP (ecuación 36) en los años 2018 y 2019. " + FUENTE_XM)
    + bloque([
        "*Separación entre entrenamiento y evaluación.* En todas las etapas que siguen, un modelo que se evalúa desde "
        "el corte *c* se entrena solo con las filas *t* ≤ *c* − (*h* + 1), para que ningún objetivo del "
        "entrenamiento caiga en el periodo evaluado (López de Prado, 2018).",

        "*Búsqueda de hiperparámetros.* Para cada horizonte se probaron 30 combinaciones al azar (Bergstra y Bengio, "
        "2012): profundidad máxima de 3 a 8; peso mínimo por hoja de 10, 50 o 240 horas, donde 240 horas obligan a "
        "cada hoja a tener al menos el equivalente a diez días; fracción de filas por árbol entre 0,7 y 0,9; "
        "fracción de columnas por árbol entre 0,5 y 0,9, y *λ* de la ecuación (5) entre 1 y 10, en escala "
        "logarítmica. Cada combinación se evaluó en tres pliegues anuales: entrenar con todo lo anterior y medir en "
        "2020, en 2021 y en 2022. El número de árboles no se buscó aparte: cada modelo se entrenó con hasta 1.200 "
        "árboles y, de su curva de error, se tomó cada 50 árboles el número con menor error medio en los tres "
        "pliegues.",

        "*Validación con reentrenamiento mensual.* Las tres mejores combinaciones de cada horizonte pasaron a una "
        "evaluación más cercana al uso real: se reentrenaron el primer día de cada mes de 2020 a 2022 y pronosticaron "
        "desde cada día del mes. Esta evaluación cuesta 36 entrenamientos por combinación, frente a 3 en la búsqueda; "
        "por eso solo se hizo con las finalistas. Se eligió con la regla de un error estándar de la ecuación (37): "
        "entre las combinaciones a menos de un error estándar de la mejor, la más simple, es decir, la de menor "
        "profundidad, hojas más grandes y menos árboles. En *h* = 3 y 4 quedó la primera de la búsqueda. En *h* = 7 "
        "quedó la segunda, con profundidad 6 en vez de 8, que además tuvo el menor error con reentrenamiento mensual. "
        "En *h* = 5 quedó la tercera, con profundidad 3, aunque otra tenía un error algo menor: las tres estaban a "
        "menos de un error estándar. La tabla 9 muestra la configuración final.",
    ])
    + leyenda("Tabla", "Hiperparámetros finales de XGBoost por horizonte.", ppr=ANTES_TABLA)
    + TABLA_HIPER
    + fuente("Nota: en todos los horizontes la tasa de aprendizaje es 0,03 y la pérdida es el error cuadrático. "
             "Fuente: elaboración propia.")
    + bloque([
        "*Variantes.* Sobre la configuración elegida se probaron tres cambios, y una variante se adoptaba solo si "
        "bajaba el error en más de un error estándar. El primero fue la pérdida pseudo-Huber, para que los picos "
        "pesen menos al entrenar:",
    ])
    + ecuacion(EC38, 38)
    + bloque([
        "Para errores pequeños se parece al error cuadrático, *e*^{2}/2, y para errores grandes crece de forma lineal, "
        "como el valor absoluto. El segundo fue entrenar solo con los últimos tres años, por si los años viejos ya no "
        "se parecen al mercado actual. El tercero fue corregir el sesgo, que fue el problema que más se repitió al "
        "revisar los errores de *h* = 7 en 2021:",
    ])
    + ecuacion(EC39, 39)
    + bloque([
        "donde ē_{t} es el error medio de los últimos 30 días cuyo objetivo ya se conoce el día *t*, es decir, los "
        "orígenes hasta *t* − *h*.",

        "Ninguna variante se adoptó (tabla 10). La pseudo-Huber y la ventana de tres años quedaron muy cerca de la "
        "base; en *h* = 5 la ventana corta bajó el error, pero menos de un error estándar. La corrección del sesgo "
        "empeoró todos los horizontes: el sesgo cambia de un mes a otro, y corregirlo con el del mes anterior agrega "
        "error. También se comparó reentrenar cada semana contra cada mes en 2022, en *h* = 3 y 7, y la diferencia "
        "fue mínima, así que se mantuvo el reentrenamiento mensual.",
    ])
    + leyenda("Tabla", "Error cuadrático medio en logaritmo de las variantes de XGBoost, 2020-2022.", ppr=ANTES_TABLA)
    + TABLA_VARIANTES
    + fuente("Nota: *h* = 8 y 9 usan la configuración de *h* = 7 y no tuvieron variantes propias. " + FUENTE_XM)
    + bloque([
        "*Modelo final.* Son siete modelos, con las columnas de la tabla 8 y los hiperparámetros de la tabla 9, que "
        "se reentrenan el primer día de cada mes con todos los datos anteriores. En la validación de 2020-2022, frente "
        "al mejor de los dos ingenuos, redujeron el RMSE 18,4% en *h* = 3, 16,9% en *h* = 4, 13,4% en *h* = 5, 8,9% "
        "en *h* = 6 y 8,3% en *h* = 7. La mejora cae con el horizonte, porque cuanto más lejos está el día "
        "pronosticado, menos dice lo que se sabe hoy. La configuración se guardó en configuracion_final.json antes de "
        "abrir la prueba.",

        "Hay dos advertencias. El error de validación es algo optimista, porque el umbral de estabilidad y la regla de "
        "las columnas en dólares se definieron después de mirar 2020-2022. Y el alcance de una semana se decidió "
        "después de abrir la prueba: la de 2026 mostró que el modelo de 30 días solo cumplía el criterio hasta "
        "*h* = 7. Los modelos no se reentrenaron ni se ajustaron por eso (capítulo 4).",
    ])
)

REFS = [
    "Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, "
    "N., y Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature "
    "Machine Intelligence, 2*(1), 56-67. https://doi.org/10.1038/s42256-019-0138-9",
    "Spearman, C. (1904). The proof and measurement of association between two things. *The American Journal of "
    "Psychology, 15*(1), 72-101. https://doi.org/10.2307/1412159",
]

d = Docx(ENTRADA)
assert "f21_xgboost_construccion" not in d.doc, "la 3.5 ya está"
textos = [d.texto(p) for _, _, p in d.parrafos()]
assert not any(t.strip() in {f"({n})" for n in range(34, 40)} for t in textos), "ya hay ecuaciones de la 34 a la 39"
for f in ["f21_xgboost_construccion", "f22_xgboost_columnas", "f23_xgboost_importancia"]:
    d.agregar_imagen(FIG / f"{f}.png", "rIdFig" + f[1:3])
d.reemplazar_vacio_tras("3.5 XGBoost", S35)
d.referencias(REFS)
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
