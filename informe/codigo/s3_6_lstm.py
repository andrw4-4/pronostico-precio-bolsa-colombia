"""Escribe la sección 3.6, LSTM: la arquitectura, el entrenamiento, los bloques de variables, la selección, la búsqueda
de hiperparámetros, la evaluación con tres semillas, el procedimiento del test y el modelo final.
Las cifras salen de docs/LSTM_DISENO.md, de 6c_lstm_seleccion.ipynb, de 6d_lstm_busqueda_y_test.ipynb y de
resultados/modelo_lstm_bloques/ (seleccion.csv, seleccion_repetida.csv, control_todas.csv, control_todas_repetida.csv,
busqueda_control.csv, busqueda.csv, evaluacion_tres_semillas.csv, validacion_criterio.csv, importancia_grupos.csv y
configuracion_final.json). Los conteos de frescura salen de paneles/panel_lstm_variables.csv. Las figuras salen de
fig_lstm.py.
Uso: python s3_6_lstm.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import Docx, acento, ecuacion, figura, frac, leyenda, m, mr, par, paren, runs, sub, suma, sup, tabla

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
Y_HAT = sub(acento(m("y")), m("i,h,H"))
EC40 = (m("L=") + frac(m("1"), m("168B")) + suma(m("i=1"), m("B"), suma(m("h=3"), m("9"), suma(
    m("H=1"), m("24"), sup(paren(s("y", "i,h,H") + m("−") + Y_HAT), m("2"))))))
EC41 = (sub(acento(m("x"), "̃"), m("d,j")) + m("=") + mr("mín") + paren(
    m("8, ") + mr("máx") + paren(m("−8, ") + frac(s("x", "d,j") + m("−") + s("μ", "j"), s("σ", "j")), "{", "}"),
    "{", "}"))
EC42 = (s("I", "g") + m("=100") + paren(frac(sub(mr("RMSE"), m("g")), mr("RMSE")) + m("−1")))

# ----------------------------------------------------------------------------- tablas
TABLA_BLOQUES = tabla([
    ["Bloque", "Qué le dice al modelo", "Variables", "Frescura frente al precio"],
    ["1. Precio", "Su propia historia", "Logaritmo del precio, 24 horas", "Igual"],
    ["2. Calendario", "Fines de semana y festivos", "Día de la semana y festivo del día *t* y de cada día pronosticado",
     "Se conoce de antemano"],
    ["3. Despacho de hoy", "Cómo viene el sistema",
     "Costo marginal del despacho programado; su diferencia con el último precio; disponibilidad declarada frente a "
     "la demanda; fracción térmica de la generación programada", "2 días más fresca"],
    ["4. Estado hidrológico", "Si el agua alcanza",
     "Volumen útil de los embalses; media histórica de los aportes; días de autonomía; demanda frente a los aportes; "
     "distancia al precio de escasez", "Volumen y aportes, 1 día más fresca; las demás, igual"],
    ["5. Despacho de ayer", "Cuánto se corrigió lo programado",
     "Costo marginal del redespacho; error del costo marginal del despacho; redespacho frente a lo programado",
     "Hasta 1 día más fresca"],
    ["6. Clima que viene", "Si va a llover menos",
     "Índice ONI; anomalía de temperatura en Niño 3.4; anomalía de lluvia de 30 días; predicción de déficit del IDEAM",
     "2 días más fresca"],
], [3.0, 3.0, 6.4, 3.2])

TABLA_SELECCION = tabla([
    ["Paso", "Configuración fija", "¿Entra?", "Configuración 2", "¿Entra?"],
    ["Bloques 1 y 2 (referencia)", "4,2%", "", "6,2%", ""],
    ["+ 3, despacho de hoy", "12,6%", "Sí", "13,0%", "Sí"],
    ["+ 4, estado hidrológico", "16,7%", "Sí", "14,2%", "No"],
    ["+ 5, despacho de ayer", "11,5%", "No", "11,9%", "No"],
    ["+ 6, clima que viene", "11,9%", "No", "No se probó", ""],
    ["Todas las variables (control)", "9,0%", "", "11,6%", ""],
], [5.4, 2.8, 1.6, 2.8, 1.6])

TABLA_HIPER = tabla([
    ["Hiperparámetro", "Configuración fija", "Rango de búsqueda", "Final"],
    ["Capas LSTM, en el codificador y en el decodificador", "1", "1 a 3", "1"],
    ["Unidades por capa", "128", "32, 64, 128, 192, 256 o 360", "128"],
    ["Capa densa de entrada", "64", "32, 64, 128 o 256", "64"],
    ["Dropout", "0,2", "0,2 a 0,5", "0,2"],
    ["Tasa de aprendizaje", "0,001", "10^{−5} a 10^{−2}, escala logarítmica", "0,001"],
    ["Tamaño del lote", "32", "32 o 64", "32"],
    ["Ventana de historia (días)", "28", "14, 28 o 56", "28"],
    ["Bloques", "", "1 a 3 o 1 a 4", "1 a 4"],
    ["Épocas", "Hasta 100, con parada temprana", "Hasta 100, con parada temprana", "4, sin parada temprana"],
], [5.0, 3.3, 4.3, 3.0])

TABLA_TRES = tabla([
    ["Candidata", "Bloques", "Capas", "Unidades", "Densa", "Dropout", "Tasa", "Lote", "Ventana", "RMSE", "Mejora"],
    ["Configuración fija", "1 a 4", "1", "128", "64", "0,2", "0,0010", "32", "28", "0,2405", "16,7%"],
    ["Búsqueda, prueba 01", "1 a 4", "1", "192", "128", "0,3", "0,0025", "64", "56", "0,2446", "15,3%"],
    ["Configuración 2", "1 a 4", "2", "192", "128", "0,5", "0,0028", "64", "14", "0,2476", "14,2%"],
    ["Búsqueda, prueba 25", "1 a 4", "2", "360", "32", "0,3", "0,0006", "64", "14", "0,2489", "13,8%"],
    ["Búsqueda, prueba 00", "1 a 3", "2", "256", "128", "0,2", "0,0007", "64", "14", "0,2497", "13,5%"],
    ["Configuración 2", "1 a 3", "2", "192", "128", "0,5", "0,0028", "64", "14", "0,2512", "13,0%"],
    ["Búsqueda, prueba 20", "1 a 3", "2", "192", "128", "0,3", "0,0034", "64", "14", "0,2524", "12,6%"],
    ["Configuración fija", "1 a 3", "1", "128", "64", "0,2", "0,0010", "32", "28", "0,2524", "12,6%"],
    ["Búsqueda, prueba 23", "1 a 3", "2", "192", "128", "0,2", "0,0006", "64", "14", "0,2530", "12,4%"],
], [2.75, 1.3, 1.1, 1.55, 1.2, 1.45, 1.25, 1.0, 1.45, 1.25, 1.3], tam=16)

TABLA_ENSAYO = tabla([
    ["Procedimiento", "*h* = 3 a 9", "*h* = 3", "*h* = 3 a 7", "*h* = 8 a 9"],
    ["Parada temprana", "16,6%", "23,5%", "18,2%", "14,0%"],
    ["Como en el test: 4 épocas, con todos los datos", "14,6%", "23,4%", "16,4%", "11,6%"],
], [6.6, 2.2, 1.8, 2.2, 2.2])

# ----------------------------------------------------------------------------- texto
S36 = (
    bloque([
        "La LSTM se construyó en cinco etapas, todas con datos hasta 2022 (figura 16): armar el panel por bloques de "
        "variables, elegir los bloques con una selección hacia adelante, buscar los hiperparámetros, evaluar las mejores "
        "candidatas con tres semillas junto con un ensayo del procedimiento del test, y fijar el modelo final. El panel "
        "sale del script 2h_panel_lstm_bloques.py, la selección está en el notebook 6c_lstm_seleccion.ipynb y lo demás "
        "en 6d_lstm_busqueda_y_test.ipynb. La red se programó con Keras (Chollet et al., 2015) y se entrenó en Google "
        "Colab, con GPU.",
    ])
    + figura(FIG / "f24_lstm_construccion.png", "rIdFig24", 2024, 15,
             "Etapas de la construcción de la LSTM. Fuente: elaboración propia.")
    + bloque([
        "*El modelo.* Es una sola red para las 24 horas y los siete días, con la arquitectura codificador-decodificador "
        "de la sección 2.3 (figura 17). Cada ejemplo de entrenamiento es un día de origen *t*. El codificador lee los "
        "últimos 28 días hasta *t*, uno por paso. Cada día entra como un vector con las 24 horas del logaritmo del "
        "precio, las 24 horas de cada variable horaria, el valor de cada variable diaria y el calendario de ese día. "
        "Una capa densa comprime primero ese vector a 64 números, y una LSTM de 128 unidades lo recorre día por día. De "
        "ella solo pasa al decodificador su estado final: la memoria *c*_{t} y la salida *h*_{t}.",

        "El decodificador es otra LSTM de 128 unidades, con sus propios pesos. Arranca con ese estado y da siete pasos, "
        "uno por cada día pronosticado, de *t* + 3 a *t* + 9. En cada paso recibe solo el calendario de ese día: siete "
        "indicadores del día de la semana y uno de festivo. Una capa densa convierte su salida en las 24 horas del día. "
        "Así, la red entrega a la vez los 168 cambios de la ecuación (21), y cada día se pronostica sabiendo qué día de "
        "la semana es y si es festivo. El decodificador no recibe sus propios pronósticos de los días anteriores, de "
        "modo que un error en el primer día no entra como dato al segundo; lo que pasa de un día al siguiente es solo "
        "su estado.",
    ])
    + figura(FIG / "f25_lstm_arquitectura.png", "rIdFig25", 2025, 15.5,
             "Arquitectura de la LSTM, desplegada en el tiempo. El codificador lee los 28 días hasta *t*; el "
             "decodificador parte de su estado final y pronostica los días *t* + 3 a *t* + 9, cada uno con su "
             "calendario. Fuente: elaboración propia con base en Sutskever et al. (2014).")
    + bloque([
        "El calendario va con indicadores y no con funciones seno y coseno, porque el efecto del fin de semana y de los "
        "festivos no es una onda (decisión del autor). La capa densa de entrada mantiene la red casi del mismo tamaño "
        "con cualquier conjunto de variables. Tiene 174.168 parámetros con solo el precio y el calendario, 183.576 con "
        "las variables del modelo final y 252.056 con todas las variables, y la diferencia está solo en esa capa. Así, "
        "al comparar conjuntos de variables, la diferencia viene de la información y no del tamaño de la red.",

        "González Pérez y Urbano Buriticá (2022) eligieron una LSTM para cada hora del día. Aquí, en cambio, una sola "
        "red pronostica las 24 horas, como XGBoost, y comparte entre ellas lo que aprende. Salazar-Peña et al. (2025) "
        "apilan tres capas LSTM y entregan todo el pronóstico con una sola capa de salida. Aquí se usa el "
        "codificador-decodificador porque los días de la semana no se comportan igual (decisión del autor).",

        "*Entrenamiento.* La pérdida es el error cuadrático medio de los 168 cambios de cada día,",
    ])
    + ecuacion(EC40, 40)
    + bloque([
        "donde *B* es el número de días del lote. Se minimiza con Adam (Kingma y Ba, 2015), y se usa el error "
        "cuadrático porque el criterio de la tesis es el RMSE en logaritmo.",

        "Para evitar el sobreajuste se usan dos herramientas. La primera es dropout, después de la capa densa de entrada "
        "y antes de la de salida. La segunda es parada temprana (Goodfellow et al., 2016): se entrena hasta 100 épocas "
        "y se mide el error en el último 10% de los días de entrenamiento, en orden de fechas. El entrenamiento para "
        "cuando lleva 10 épocas sin mejorar, y se conservan los pesos de la mejor época. Entre los días de ajuste, los "
        "de parada y los evaluados se dejan nueve días, para que ningún precio objetivo se comparta entre ellos (López "
        "de Prado, 2018). Cada configuración se entrena con tres semillas, que cambian los pesos iniciales y el orden de "
        "los lotes, y se promedian sus pronósticos.",

        "Los ejemplos son pocos para una red de este tamaño. Cada uno es un día: hay unos 1.700 al entrenar hasta 2019 "
        "y unos 2.400 hasta 2021, cada uno con 168 objetivos. Por eso la configuración inicial tiene una sola capa, "
        "dropout y parada temprana, y promedia tres semillas (decisión del autor). Cada columna del vector del día se "
        "estandariza y se recorta:",
    ])
    + ecuacion(EC41, 41)
    + bloque([
        "donde *x*_{d,j} es la columna *j* del día *d*, y μ_{j} y σ_{j} son su media y su desviación estándar en los "
        "días de entrenamiento, desde marzo de 2015. El recorte evita que un valor extremo, como un pico del precio, "
        "domine los pesos de la red (decisión del autor).",

        "*Información de entrada.* La red usa el panel de la LSTM de la sección 3.1, en el que cada variable toma el "
        "valor del día *R* − *L*, con *L* su atraso de publicación. Las filas son las mismas de XGBoost y SARIMAX, pero "
        "la información no. De las 136 variables del panel, 45 llegan dos días más frescas que el precio, porque se "
        "conocen el mismo día *R*, como el despacho programado; 18 llegan un día más frescas, como los aportes y el "
        "volumen de los embalses; 43 llegan con el mismo atraso del precio, y 30 llegan más atrasadas, la mayoría "
        "ofertas y datos de la curva de mérito, con ocho días más. González Pérez y Urbano Buriticá (2022) ya ajustaron "
        "sus modelos a la información disponible en la operación real del mercado, al pronosticar el día D con datos "
        "hasta D − 2. La sección 4.2 vuelve sobre lo que esta diferencia de información significa para la comparación "
        "entre modelos.",

        "*Bloques de variables.* Elegir una por una entre 136 variables con una red que es ruidosa de una corrida a "
        "otra no es confiable. Por eso las variables se agruparon en seis bloques según su papel en la formación del "
        "precio (decisión del autor; tabla 11). La agrupación se apoyó en una prueba previa por grupos de variables con "
        "un XGBoost sencillo, en la que el despacho del día fue el grupo más fuerte. A diferencia de XGBoost, las "
        "variables entran sin rezagos ni resúmenes hechos a mano: la red recibe la secuencia de 28 días y construye "
        "sola esa información.",
    ])
    + leyenda("Tabla", "Bloques de variables de la LSTM.", ppr=ANTES_TABLA)
    + TABLA_BLOQUES
    + fuente("Fuente: elaboración propia.")
    + bloque([
        "Quedaron fuera de los bloques la demanda, que la explica el calendario; las ofertas y la curva de mérito, que "
        "llegan con ocho días más de atraso; la generación y la mezcla por planta; la red y los contratos, y el resto de "
        "las variables del sistema, que repiten lo del despacho (decisión del autor). La prueba de control revisa si "
        "alguna de ellas hacía falta. Se planeó también un séptimo bloque con los pronósticos de XGBoost y SARIMAX, "
        "para que la red aprendiera a cuál creerle según la situación, pero no se probó y queda como trabajo futuro "
        "(sección 5.2).",

        "*Selección hacia adelante (2020-2022).* Los bloques se eligieron con la LSTM misma, en tres pliegues anuales: "
        "se entrena con los datos desde 2015 hasta el año anterior y se mide en 2020, en 2021 y en 2022. El modelo de "
        "referencia tiene solo los bloques 1 y 2. Luego se agrega el bloque 3 y se entrena un modelo nuevo desde cero. "
        "Si le gana a la referencia, pasa a ser la nueva referencia; si no, el bloque sale. Se hace lo mismo con los "
        "bloques 4 y 5, y el 6 solo se prueba si entró el 4 (decisión del autor).",

        "Un bloque entra si le gana a la referencia con Diebold-Mariano *p* < 0,05 en al menos uno de los horizontes "
        "*h* = 3, 6 y 9, y no pierde con *p* < 0,05 en ninguno de ellos, con los errores de los tres años juntos y la "
        "varianza de la sección 3.3. Se compara contra la referencia del momento y no siempre contra los bloques 1 y 2, "
        "porque los bloques se repiten entre sí: importa si agregan algo a lo que ya entró. Durante la selección, los "
        "hiperparámetros quedan fijos en valores comunes para una red de este tamaño, dentro de los rangos de "
        "Salazar-Peña et al. (2025) (tabla 13). Así, un bloque gana por sus variables y no por una red distinta "
        "(decisión del autor).",

        "Con esta configuración fija entraron los bloques 3 y 4 (tabla 12). El despacho de hoy subió la mejora frente "
        "al ingenuo del día, el mejor de los dos en 2020-2022, de 4,2% a 12,6%, con *p* < 0,01 en *h* = 3 y 6. El "
        "estado hidrológico la subió a 16,7%: no cambió el error en *h* = 3 (*p* = 0,38), pero lo bajó en *h* = 6 y 9 "
        "(*p* = 0,03 y 0,04). Los bloques 5 y 6 empeoraron el error en los tres horizontes, con *p* < 0,01.",
    ])
    + leyenda("Tabla", "Selección hacia adelante de los bloques: mejora del RMSE de la semana frente al ingenuo del "
                       "día, 2020-2022, con tres semillas.", ppr=ANTES_TABLA)
    + TABLA_SELECCION
    + fuente("Nota: la configuración 2 tiene dos capas, 192 unidades, capa de entrada de 128, dropout de 0,5, tasa de "
             "aprendizaje de 0,0028, lotes de 64 y ventana de 14 días. Con ella, el bloque 6 no se probó porque no "
             "entró el 4. " + FUENTE_XM)
    + bloque([
        "*Prueba de control.* Aparte, se entrenó la misma red con las 136 variables. Su mejora fue de 9,0%, menor que "
        "la de los bloques 1 a 4. Con ese modelo ya entrenado se midió la importancia de cada grupo de variables por "
        "permutación (Breiman, 2001): en los días evaluados se desordenan las columnas de un grupo completo y se mide "
        "cuánto sube el RMSE,",
    ])
    + ecuacion(EC42, 42)
    + bloque([
        "donde RMSE_{g} es el error con el grupo *g* desordenado. Se desordena por grupo y no por variable porque "
        "muchas variables dicen lo mismo: si se desordena solo una de las 21 de lluvia, la red usa las demás y parece "
        "que ninguna importa (decisión del autor). Cada bloque se desordenó junto con todos los grupos de donde salió, "
        "y la medida se repitió tres veces con cada semilla en cada año.",

        "La regla, decisión del autor, era que un grupo de fuera de los bloques importaba si subía el error más que el "
        "menos importante de los bloques que entraron. No pasó con ninguno (figura 18). Los bloques 3 y 4 subieron el "
        "RMSE en 9,3% y 6,2% en promedio, y el grupo de fuera más importante, la generación, en 2,1%. Los bloques 5 y 6 "
        "casi no movieron el error, lo que coincide con la selección.",
    ])
    + figura(FIG / "f26_lstm_importancia.png", "rIdFig26", 2026, 15,
             "Importancia por permutación de cada grupo de variables (ecuación 42) en la red con todas las variables: "
             "promedio de 2020 a 2022, de tres semillas y de tres repeticiones. Los puntos son el promedio de cada año, "
             "y el número entre paréntesis, la cantidad de variables del grupo. " + FUENTE_XM)
    + bloque([
        "*Búsqueda de control y selección repetida.* Para comprobar que la configuración fija no sesgaba la selección, "
        "se hizo una búsqueda corta de control. Se probaron 10 configuraciones al azar dentro de los rangos de la tabla "
        "13, las mismas en dos casos: con solo los bloques 1 y 2, y con todas las variables. Cada una se midió con una "
        "semilla. La regla, fijada antes, era que la configuración fija quedaba respaldada en un caso si ninguna de las "
        "10 le ganaba con Diebold-Mariano *p* < 0,05 en el error de la semana (decisión del autor).",

        "No quedó respaldada en ninguno de los dos casos. Con solo el precio y el calendario le ganaron 6 de las 10, "
        "aunque en buena parte por la semilla: con la semilla de la búsqueda, la configuración fija tuvo un RMSE de "
        "0,297, y con las otras dos, 0,277, lo mismo que las que le ganaron. Con todas las variables la diferencia sí "
        "fue clara: dos configuraciones con dos capas, dropout de 0,5 y lotes de 64 bajaron el RMSE de 0,272 a 0,256. "
        "Con muchas entradas, la configuración fija regulariza poco, y eso pudo castigar a los bloques 5 y 6.",

        "Por eso, después de ver estos resultados y antes de abrir el test, se repitió la selección completa con la "
        "configuración de control que le ganó a la fija en los dos casos, la configuración 2 de la tabla 12 (decisión "
        "del autor). Con ella entró solo el bloque 3. El bloque 4 subió la mejora de 13,0% a 14,2%, pero no pasó la "
        "regla (*p* entre 0,28 y 0,58).",

        "Las dos selecciones coinciden en el despacho de hoy y difieren en el estado del agua: con las dos "
        "configuraciones mejora el promedio, sobre todo en *h* = 9, pero la diferencia solo es significativa con la "
        "fija. Seguir la regla al pie de la letra dejaba solo el bloque 3, y elegir la primera selección porque salió "
        "mejor habría sido decidir al ver el resultado. Por eso, antes de la búsqueda de hiperparámetros, se decidió que "
        "los dos conjuntos, bloques 1 a 3 y bloques 1 a 4, compitieran en ella como un hiperparámetro más (decisión del "
        "autor).",

        "*Búsqueda de hiperparámetros.* Se hizo una búsqueda bayesiana (Snoek et al., 2012) con KerasTuner (O'Malley "
        "et al., 2019). Fueron 30 configuraciones: las 10 primeras al azar y las demás elegidas con un modelo del error "
        "de las anteriores. Los rangos están en la tabla 13; los del dropout y la tasa de aprendizaje son los de "
        "Salazar-Peña et al. (2025). Cada configuración se midió en los tres años con una semilla, con el RMSE de toda "
        "la semana. Compitieron también, sin volver a entrenarse, las cuatro combinaciones de conjunto y configuración "
        "de las dos selecciones.",

        "La mejor fue la prueba 01. Usa los bloques 1 a 4, una capa, 192 unidades, capa de entrada de 128, dropout de "
        "0,3, lotes de 64 y ventana de 56 días. Su RMSE fue 0,2439, frente a 0,2460 de la configuración fija con los "
        "mismos bloques.",
    ])
    + leyenda("Tabla", "Hiperparámetros de la LSTM.", ppr=ANTES_TABLA)
    + TABLA_HIPER
    + fuente("Fuente: elaboración propia.")
    + bloque([
        "*Evaluación con tres semillas.* Una sola corrida de la red es ruidosa. En una primera corrida, la misma "
        "configuración, con la misma semilla, dio 15,5% de mejora en la búsqueda y 11,7% al repetirla. La causa es que "
        "los cálculos en la GPU no son del todo deterministas, y eso cambia la época en que para el entrenamiento. Esa "
        "variación, de unos 4 puntos, es mayor que la diferencia entre las mejores configuraciones.",

        "Por eso la búsqueda solo propuso candidatas. Se evaluaron con tres semillas las cinco mejores de la búsqueda, "
        "junto con las cuatro combinaciones de las dos selecciones, y ganó la de menor RMSE de la semana (decisión del "
        "autor). Ganó la más simple, los bloques 1 a 4 con la configuración fija, con 16,7% de mejora (tabla 14). La "
        "segunda, la prueba 01, quedó en 15,3%, y la diferencia entre las dos no es significativa (Diebold-Mariano "
        "*t* = −1,82, *p* = 0,068). Las cinco primeras usan los bloques 1 a 4, lo que respalda la primera selección.",

        "Elegir la mejor de nueve candidatas favorece a la que tuvo suerte. Por eso la ganadora se entrenó otra vez con "
        "tres semillas: dio 16,6%, casi lo mismo, así que su cifra no depende de una corrida en particular.",
    ])
    + leyenda("Tabla", "Evaluación de las candidatas con tres semillas, 2020-2022, *h* = 3 a 9.", ppr=ANTES_TABLA)
    + TABLA_TRES
    + fuente("Nota: el RMSE del ingenuo del día en el mismo periodo es 0,2888. " + FUENTE_XM)
    + bloque([
        "*Procedimiento del test.* La parada temprana aparta el último 10% de los días de entrenamiento, así que el "
        "modelo no aprende de los meses más recientes. En el test, en cambio, cada modelo mensual se entrena con todos "
        "los días cuyo precio objetivo ya se conoce, sin parada temprana, durante un número fijo de épocas (decisión del "
        "autor). Ese número es la mediana de la mejor época de la ganadora en los tres años y las tres semillas. Las "
        "mejores épocas fueron 2, 2, 3, 3, 4, 4, 4, 7 y 13, y su mediana, 4.",

        "Antes de abrir el test se ensayó este procedimiento en 2020-2022, entrenando una vez por año. La regla se fijó "
        "antes del ensayo: si salía peor que la parada temprana con Diebold-Mariano *p* < 0,05 en el error de la "
        "semana, el test no se abría. El ensayo dio 14,6% de mejora, dos puntos menos que la parada temprana, sin "
        "diferencia significativa (*t* = 1,73, *p* = 0,083). Las dos versiones cumplen el criterio en los cuatro "
        "bloques de horizontes (tabla 15), así que se usó el procedimiento del test.",
    ])
    + leyenda("Tabla", "Mejora del RMSE en logaritmo frente al ingenuo del día con los dos procedimientos de "
                       "entrenamiento, 2020-2022.", ppr=ANTES_TABLA)
    + TABLA_ENSAYO
    + fuente("Nota: en todos los casos, Diebold-Mariano contra el ingenuo del día da *p* < 0,01. " + FUENTE_XM)
    + bloque([
        "*Modelo final.* Es una red codificador-decodificador con los bloques 1 a 4: el precio, el calendario, las "
        "cuatro variables del despacho de hoy y las cinco del estado hidrológico, en total 179 números por día. Tiene "
        "una capa LSTM de 128 unidades en el codificador y otra en el decodificador, capa de entrada de 64, dropout de "
        "0,2, tasa de aprendizaje de 0,001, lotes de 32 y ventana de 28 días, con 183.576 parámetros. Se entrena cuatro "
        "épocas con tres semillas, cuyos pronósticos se promedian, y se reentrena el primer día de cada mes con todos "
        "los datos anteriores.",

        "En la validación de 2020-2022 redujo el RMSE de la semana 16,6% frente al ingenuo del día con parada temprana, "
        "y 14,6% con el procedimiento del test. La configuración se guardó en configuracion_final.json el 14 de "
        "noviembre de 2026, antes de abrir el test.",

        "Hay dos advertencias. La primera es que el error de validación es optimista. El periodo 2020-2022 se usó "
        "también para armar el panel, elegir los bloques y buscar los hiperparámetros, y el procedimiento cambió tres "
        "veces después de ver resultados de validación, aunque siempre antes de abrir el test. Por eso la selección de "
        "bloques se reporta como exploratoria. La segunda es que, como los cálculos en la GPU no son del todo "
        "deterministas, volver a correr los notebooks no da exactamente las mismas cifras. Con una semilla, una corrida "
        "puede variar unos 4 puntos de mejora; con el promedio de tres, la ganadora dio 16,7% y 16,6% en dos corridas.",
    ])
)

REFS = [
    "Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5-32. https://doi.org/10.1023/A:1010933404324",
]

d = Docx(ENTRADA)
assert "f24_lstm_construccion" not in d.doc, "la 3.6 ya está"
textos = [d.texto(p) for _, _, p in d.parrafos()]
assert not any(t.strip() in {f"({n})" for n in range(40, 43)} for t in textos), "ya hay ecuaciones de la 40 a la 42"
for f in ["f24_lstm_construccion", "f25_lstm_arquitectura", "f26_lstm_importancia"]:
    d.agregar_imagen(FIG / f"{f}.png", "rIdFig" + f[1:3])
d.reemplazar_vacio_tras("3.6 LSTM", S36)
d.referencias(REFS)
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
