"""Escribe el capítulo III, Metodología (3.1 Datos, 3.2 Diseño del pronóstico y 3.3 Construcción de los modelos).
Las cifras salen de docs/DOCUMENTACION.md, docs/PANEL_HORARIO.md, docs/LSTM_DISENO.md, docs/REFERENCIAS.md,
resultados/modelo_sarimax/, resultados/modelo_xgboost/ y 4_modelo_xgboost.ipynb (criterio y Diebold-Mariano).
Uso: python s3_metodologia.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import Docx, acento, ecuacion, figura, funcion, leyenda, m, mr, par, paren, sub, sup, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"


def bloque(textos):
    return "".join(par(t) for t in textos)


def fuente(texto):
    """Línea 'Fuente:' bajo una tabla, en letra más pequeña."""
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>')


ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'

# ------------------------------------------------------------------ 3.1 Datos
TABLA_FUENTES = tabla([
    ["Datos", "Fuente", "Atraso (días)"],
    ["Despacho programado (costo marginal y generación), disponibilidad declarada y obligaciones de energía firme",
     "XM", "0"],
    ["Aportes hídricos, embalses y redespacho", "XM", "1"],
    ["Precio de bolsa, demanda, generación real y precio de escasez", "XM", "2"],
    ["Capacidad efectiva y margen de reserva", "XM", "2"],
    ["Contratos, pérdidas, restricciones y cargo por confiabilidad", "XM", "5"],
    ["Ofertas, curva de mérito y pronóstico de demanda del CND", "XM y SIMEM", "10"],
    ["Series mensuales (proyecciones de la UPME, demanda máxima de potencia, entre otras)", "XM", "9 a 40"],
    ["Temperatura del mar en las regiones de El Niño, ONI y RONI", "NOAA", "0*"],
    ["Lluvia diaria en ocho puntos de las cuencas", "ERA5 (Open-Meteo)", "0*"],
    ["Boletines de predicción climática", "IDEAM", "0*"],
    ["Tasa representativa del mercado (TRM)", "datos.gov.co", "0*"],
], [9.6, 3.4, 2.4])

S31 = (
    bloque([
        "Los datos provienen de fuentes públicas (tabla 2). De XM, el operador del sistema y administrador del "
        "mercado, se descargaron 41 series con la librería pydataxm, que consulta su API y la de SIMEM (XM, 2026): "
        "precio de bolsa, demanda, generación, disponibilidad, despacho programado, aportes, embalses, contratos, "
        "restricciones y ofertas. La tecnología de cada planta sale del listado de PARATEC. Del Centro de Predicción "
        "Climática de la NOAA se tomaron las temperaturas semanales del mar en las regiones Niño 1+2, 3, 3.4 y 4, y "
        "los índices ONI y RONI (NOAA, 2026); de ERA5, a través de Open-Meteo, la lluvia diaria en ocho puntos de las "
        "cuencas que alimentan los embalses (Hersbach et al., 2020; Zippenfenig, 2023); del IDEAM, sus boletines de "
        "predicción climática, y de datos.gov.co, la TRM.",

        "Con estas fuentes se armó un panel horario de 103.200 filas, 24 por día, del 1 de enero de 2015 al 9 de "
        "octubre de 2026, que incluye el despacho programado de los días siguientes al último precio. El precio va "
        "hasta el 6 de octubre de 2026. Se sigue la convención de XM, en la que la hora 1 va de las 0:00 a la 1:00. "
        "Cuando una serie está por planta o por hora y se necesita para todo el sistema o para el día, las energías "
        "se suman, las capacidades se suman entre plantas y se promedian entre horas, y los precios se promedian. Los "
        "datos que faltan de forma aislada se llenan con la misma hora del día anterior, hasta tres días seguidos; "
        "los eventos sin registro en XM, como las importaciones de un día sin intercambios, se toman como cero.",

        "A partir del panel se construyeron 134 variables base: el logaritmo del precio, 44 variables horarias y 89 "
        "diarias. Cada una sigue una regla fija según su tipo, para que su escala no dependa del nivel del sistema "
        "(decisión del autor): las cantidades se expresan como fracción de la demanda o de la generación, los precios "
        "y las ofertas en logaritmo, y las cantidades diarias se dividen por la demanda promedio de los últimos siete "
        "días. Se agregaron además cuatro variables que resumen el estado del sistema: la distancia entre el precio y "
        "el precio de escasez, la presión de la demanda sobre el agua disponible en cada hora, los días que alcanzaría "
        "el agua embalsada y el error del costo marginal del despacho programado frente al precio.",
    ])
    + leyenda("Tabla", "Fuentes de datos y atraso de publicación de cada grupo.", ppr=ANTES_TABLA)
    + TABLA_FUENTES
    + fuente("Nota: el atraso se cuenta en días antes del día en que se hace el pronóstico. * Estas fuentes se "
             "fechan el día en que se publican, así que su atraso ya está incluido. Fuente: elaboración propia con "
             "base en consultas a las fuentes del 9 y el 10 de octubre de 2026.")
    + bloque([
        "*Atraso de publicación.* Cada fuente publica sus datos con un atraso distinto (tabla 2). Para medirlo, se "
        "consultaron todas las series el 9 y el 10 de octubre de 2026 y se tomó, para cada una, la fecha del último "
        "dato disponible; cuando las dos consultas no coincidían, se tomó el atraso mayor. El precio de bolsa se "
        "publica con dos días de atraso: el día en que se hace el pronóstico, que se llama aquí *R*, el último precio "
        "conocido es el del día *t* = *R* − 2. En cambio, el despacho programado de *R* ya está publicado ese mismo "
        "día, y las ofertas solo se conocen diez días después (figura 3).",

        "Ningún dato entra a un modelo antes de su publicación, pero los modelos lo aplican de dos maneras. En el "
        "panel que usan XGBoost y SARIMAX, la fila del día *t* y la hora *H* llega hasta el cierre del día *t*, el del "
        "último precio, y las variables que se publican después que el precio entran con un rezago adicional: ocho "
        "días más la curva de mérito y tres días más los contratos, las pérdidas y las restricciones. La única "
        "excepción es el costo marginal del despacho programado del día *t* + 1, que se supone publicado la víspera. "
        "En el panel de la LSTM, en cambio, cada variable toma el valor del día *R* − *L*, donde *L* es su atraso de "
        "publicación. Así, la LSTM usa el despacho programado de *R* y los aportes de *R* − 1, que en el otro panel "
        "quedan cortados en el día *t*. Para comprobar que no hay fuga de información, se alteraron los datos que "
        "todavía no se habían publicado en una fecha dada y se construyó de nuevo el panel: ninguna fila anterior "
        "cambió.",
    ])
    + figura(FIG / "f03_diseno_pronostico.png", "rIdFig03", 2003, 15,
             "Diseño del pronóstico en el tiempo. a) Periodos de ajuste, validación y prueba. b) Último dato "
             "publicado de cada grupo el día *R* en que se pronostica, con los atrasos del panel de la LSTM; la "
             "semana pronosticada va de *t* + 3 a *t* + 9. Fuente: elaboración propia.")
)

# ------------------------------------------------------------------ 3.2 Diseño del pronóstico
P_ = lambda a: m("P") + paren(m(a))
EC = {
    21: sub(m("y"), m("t,h,H")) + m("=") + funcion("log", P_("t+h,H")) + m("−") + funcion("log", P_("t,H"))
        + m(",  h=3,…,9"),
    22: acento(m("P")) + paren(m("t+h,H")) + m("=") + P_("t,H") + m("·")
        + funcion("exp", paren(sub(acento(m("y")), m("t,h,H")))),
}

S32 = (
    par("Cada pronóstico se hace con los datos hasta el día *t* y cubre los siete días siguientes al día *R* = "
        "*t* + 2, es decir, los días *t* + 3 a *t* + 9. Como en XGBoost un árbol no pronostica fuera del rango que vio "
        "al entrenarse (sección 2.3), los modelos no pronostican el precio sino su cambio en logaritmo frente al mismo "
        "día y hora del último precio conocido,")
    + ecuacion(EC[21], 21)
    + par("y el pronóstico en pesos se recupera como")
    + ecuacion(EC[22], 22)
    + par("Con esta respuesta, el pronóstico ingenuo del día de la ecuación (16) equivale a pronosticar un cambio "
          "de cero, y los tres modelos pronostican la misma cantidad, lo que permite compararlos directamente.")
    + bloque([
        "*Periodos.* Los datos se dividen en cuatro periodos (figura 3a). Con 2015-2019 se eligen las variables y "
        "los órdenes de los modelos. Con 2020-2022 se validan: se eligen los hiperparámetros y se decide entre "
        "versiones de cada modelo. Las pruebas son 2023-2025 y 2026 hasta el 6 de octubre, y cada modelo pasa por "
        "ellas una sola vez, después de quedar fijo. La prueba de 2026 se agregó después de abrir la de 2023-2025 de "
        "XGBoost; para SARIMAX y la LSTM ya estaba prevista antes de sus pruebas.",

        "*Evaluación con origen móvil.* En validación y en prueba, cada modelo se vuelve a entrenar el primer día de "
        "cada mes con todos los datos anteriores, y con ese modelo se pronostica desde cada día del mes (Hyndman y "
        "Athanasopoulos, 2021). Entre los datos de entrenamiento y el primer día pronosticado se dejan *h* + 1 días, "
        "para que ningún objetivo del entrenamiento se traslape con el periodo evaluado (López de Prado, 2018). Los "
        "tres modelos se evalúan en exactamente las mismas filas: 228.984 pronósticos, de los cuales 183.120 son de "
        "2023-2025 y 45.864 de 2026, y la comparación verifica que coincidan antes de calcular cualquier métrica.",

        "*Criterio.* Un modelo se considera útil en un bloque de horizontes si cumple dos condiciones: reduce al "
        "menos 5% el RMSE en logaritmo frente al mejor de los dos ingenuos de la sección 2.4 en ese bloque, y la "
        "prueba de Diebold y Mariano contra ese mismo ingenuo da *p* < 0,05. El umbral de 5% es decisión del autor. "
        "El bloque principal es la semana completa, *h* = 3 a 9, y se reportan también *h* = 3, *h* = 3 a 7 y "
        "*h* = 8 a 9. El criterio se fijó el 1 de noviembre de 2026, antes de abrir la prueba de XGBoost, cuando "
        "el alcance era de 30 días, y se mantuvo igual al reducir el horizonte a una semana.",

        "Para la prueba de Diebold y Mariano, la diferencia de pérdidas *d*_{t} de la ecuación (19) se calcula con "
        "el error cuadrático promedio de cada día de origen *t*, sobre las 24 horas y los horizontes del bloque. Así, "
        "las 24 horas de un mismo día, que comparten la mayor parte de su error, cuentan como una sola observación. "
        "La varianza se estima con Newey y West (1987) con *h*_{máx} − 1 + 7 rezagos: *h*_{máx} − 1 por el "
        "traslape de los objetivos, y 7 por la regla automática de Newey y West (1994) con unos 1.750 días.",
    ])
)

# ------------------------------------------------------------------ 3.3 Construcción de los modelos
B, t = m("B"), m("t")
EC.update({
    23: funcion("log", P_("t,H")) + m("=") + sub(m("β"), m("H")) + sub(m("F"), t) + m("+") + sub(m("η"), m("t,H")),
    24: paren(m("1−") + sub(m("φ"), m("1")) + B) + paren(m("1−B")) + sub(m("η"), m("t,H")) + m("=")
        + paren(m("1+") + sub(m("θ"), m("1")) + B + m("+") + sub(m("θ"), m("2")) + sup(B, m("2")))
        + paren(m("1+") + sub(m("Θ"), m("1")) + sup(B, m("7")) + m("+") + sub(m("Θ"), m("2")) + sup(B, m("14")))
        + sub(m("ε"), m("t,H")),
})

TABLA_XGB = tabla([
    ["*h*", "Profundidad máxima", "Peso mínimo por hoja", "Árboles", "Submuestra de filas",
     "Fracción de columnas", "*λ*"],
    ["3", "4", "50", "200", "0,75", "0,82", "8,39"],
    ["4", "5", "240", "200", "0,71", "0,79", "1,50"],
    ["5", "3", "50", "300", "0,72", "0,75", "8,46"],
    ["6", "4", "240", "200", "0,88", "0,74", "5,36"],
    ["7, 8 y 9", "6", "50", "100", "0,74", "0,54", "3,80"],
], [1.6, 2.3, 2.3, 1.7, 2.4, 2.4, 1.6])

TABLA_RESUMEN = tabla([
    ["", "SARIMAX", "XGBoost", "LSTM"],
    ["Modelos", "24, uno por hora", "7, uno por horizonte", "1 para toda la semana"],
    ["Estrategia (sección 2.3)", "Recursiva", "Directa", "Toda la semana a la vez"],
    ["Información", "Precio y festivos", "Precio, calendario y 57 columnas de 32 variables, cortadas en el día *t*",
     "Precio, calendario, despacho de hoy y estado hidrológico, cada uno a su fecha de publicación"],
    ["Reentrenamiento mensual", "Coeficientes; el estado se actualiza cada día", "Modelo completo",
     "Modelo completo, promedio de 3 semillas"],
    ["Programa", "R, paquete forecast", "Python, xgboost", "Python, Keras"],
], [3.4, 3.6, 4.2, 4.2])

S33 = (
    par("Los tres modelos se construyeron con las mismas reglas: las decisiones se tomaron con datos hasta 2022, "
        "con la secuencia de la sección 3.2, y cada uno quedó fijo antes de su prueba. La tabla 4, al final de esta "
        "sección, resume sus diferencias.")

    # SARIMAX
    + par("*SARIMAX.* Se estimaron 24 modelos, uno por hora, cada uno sobre la serie diaria del logaritmo del precio "
          "de esa hora, con periodo estacional *s* = 7 para el ciclo semanal, usando el paquete forecast de R "
          "(Hyndman y Khandakar, 2008). Todos incluyen como regresor un indicador *F*_{t} de si el día es festivo; "
          "el día de la semana ya lo recoge la parte estacional. Con 2015-2019, las pruebas KPSS y OCSB indicaron "
          "*d* = 1 y *D* = 0 en las 24 horas, y el AICc eligió doce órdenes distintos. El más frecuente, "
          "(1,1,2)(0,0,2)_{7}, fue el elegido en cinco horas.")
    + par("Las variables explicativas candidatas fueron las variables base sin vacíos en 2015-2019 que pasaron la "
          "limpieza descrita más adelante para XGBoost: 122 de 133. Como se pronostica hasta nueve días adelante, "
          "cada variable entra con nueve días de rezago, de modo que su valor ya se conoce al pronosticar cualquier "
          "día de la semana (decisión del autor). Se aplicaron tres filtros seguidos. Primero, el preblanqueo de Box "
          "et al. (2015): se filtran el precio y la variable con el ARIMA de cada hora y se mide su correlación "
          "cruzada en el rezago 9; pasa la variable significativa al 5%, con la corrección de Bonferroni (Dunn, "
          "1961), en al menos la mitad de las horas. Solo pasó la holgura relativa de la curva de oferta, la "
          "capacidad ofertada menos la demanda, como fracción de la demanda, y lo hizo en exactamente 12 horas. "
          "Segundo, la selección hacia adelante con el AICc sumado en las 24 horas la aceptó, y tercero, su "
          "coeficiente fue significativo al 5% en 17 de las 24 horas.")
    + par("En la validación de 2020-2022 se compararon tres versiones, con la regla de que una versión más compleja "
          "solo entra si le gana a la más simple con Diebold-Mariano *p* < 0,05. Un solo orden para todas las horas "
          "tuvo un RMSE de 0,2805; un orden por hora, 0,2806 (*p* = 0,865), y el orden único con la holgura, 0,2806 "
          "(*p* = 0,970). Ninguna de las versiones complejas mejoró, así que el modelo final usa el orden "
          "(1,1,2)(0,0,2)_{7} en todas las horas y no tiene variables explicativas. Para cada hora *H*,")
    + ecuacion(EC[23], 23)
    + ecuacion(EC[24], 24)
    + par("con coeficientes propios de cada hora. La prueba de Ljung y Box (1978) con 14 rezagos no rechazó que los "
          "residuos fueran ruido blanco en 17 de las 24 horas. Los coeficientes se reestiman el primer día de cada "
          "mes; dentro del mes solo se actualiza el estado del modelo con los precios nuevos, sin reestimar. Desde "
          "cada día se pronostican nueve pasos y se usan los pasos 3 a 9, de modo que SARIMAX pronostica de forma "
          "recursiva. La estimación convergió en todos los meses.")

    # XGBoost
    + par("*XGBoost.* Se entrenó un modelo directo para cada horizonte, *h* = 3 a 9, con las 24 horas juntas y la "
          "hora como una variable más. A partir de las 134 variables base se construyeron 1.861 columnas candidatas: "
          "rezagos del precio como en el modelo LEAR (Lago et al., 2021), medias móviles de varios plazos como en el "
          "modelo HAR (Corsi, 2009), tendencias, medidas de variabilidad y la memoria de los picos recientes. Las "
          "columnas se eligieron en tres etapas, con el procedimiento que quedó fijo el 1 de noviembre de 2026.")
    + par("En la primera etapa, con 2015-2019, salieron las columnas casi constantes (10), las inestables (106), es "
          "decir, aquellas con más de 25% de sus valores de 2018-2019 fuera del rango de 2015-2017, y 12 columnas "
          "con niveles que siguen al dólar, como el cargo por confiabilidad, que se fija en dólares (CREG, 2006); de "
          "estas solo quedó su cambio. Entre columnas con correlación de Spearman mayor que 0,95 se dejó una sola. "
          "Quedaron unas 1.290. En la segunda etapa, las columnas se ordenaron por su importancia SHAP (Lundberg y "
          "Lee, 2017) en un año que el modelo no vio, entrenando hasta 2017 para medir 2018 y hasta 2018 para medir "
          "2019, y se compararon con diez columnas de ruido, como en el método Boruta (Kursa y Rudnicki, 2010). En "
          "la tercera, con 2020-2022, se eligió cuántas columnas usar con la regla de un error estándar (Hastie et "
          "al., 2009): el número más pequeño cuyo error no supera al mínimo en más de un error estándar. Cada "
          "horizonte quedó con 10 o 20 columnas, además del precio y 16 columnas de calendario; en total son 57 "
          "columnas de 32 variables base. El umbral de estabilidad y la regla de las columnas en dólares se "
          "definieron después de mirar 2020-2022, así que el error de validación de XGBoost es algo optimista.")
    + par("Los hiperparámetros se buscaron con 30 combinaciones al azar (Bergstra y Bengio, 2012) para cada "
          "horizonte, cada una evaluada en tres pliegues anuales, 2020, 2021 y 2022. Los rangos fueron: profundidad "
          "máxima de 3 a 8; peso mínimo por hoja de 10, 50 o 240 horas; fracción de filas entre 0,7 y 0,9; fracción "
          "de columnas entre 0,5 y 0,9, y *λ* entre 1 y 10, en escala logarítmica. La tasa de aprendizaje quedó fija "
          "en 0,03 y el número de árboles se leyó de la curva de error, cada 50 árboles. Las tres mejores pasaron a "
          "una validación con reentrenamiento mensual en 2020-2022, y entre ellas se eligió la más simple dentro de "
          "un error estándar de la mejor. Se probaron también una pérdida de Huber, entrenar solo con los últimos "
          "tres años y una corrección del sesgo; ninguna mejoró lo suficiente para adoptarse. La selección y la "
          "búsqueda se hicieron para *h* = 1 a 7; los horizontes 8 y 9 usan las columnas y la configuración de "
          "*h* = 7. La tabla 3 muestra la configuración final.")
    + leyenda("Tabla", "Hiperparámetros finales de XGBoost por horizonte.", ppr=ANTES_TABLA)
    + TABLA_XGB
    + fuente("Nota: en todos los horizontes la tasa de aprendizaje es 0,03 y la pérdida es el error cuadrático. "
             "Fuente: elaboración propia.")

    # LSTM
    + par("*LSTM.* La red tiene una arquitectura codificador-decodificador (figura 4), implementada con Keras "
          "(Chollet et al., 2015). El codificador lee los últimos 28 días: cada día entra como un vector con las 24 "
          "horas de cada variable horaria, el valor de cada variable diaria y el calendario, pasa por una capa densa "
          "de 64 neuronas y luego por una LSTM de 128. El estado final de esa LSTM es el estado inicial del "
          "decodificador, otra LSTM de 128 que da siete pasos, uno por día de la semana pronosticada. En cada paso "
          "recibe solo el calendario de ese día, ocho indicadores para el día de la semana y el festivo, y no sus "
          "propios pronósticos, para que un error del primer día no se arrastre al resto de la semana. Una capa "
          "densa convierte cada paso en los 24 cambios de la ecuación (21). Según las variables de entrada, la red "
          "tiene entre 174.000 y 188.000 parámetros. Las entradas se estandarizan con la media y la desviación de "
          "los datos de entrenamiento.")
    + figura(FIG / "f04_arquitectura_lstm.png", "rIdFig04", 2004, 15,
             "Arquitectura de la red LSTM. Fuente: elaboración propia.")
    + par("Las variables se agruparon en bloques según su papel en la formación del precio (decisión del autor): "
          "el precio, el calendario, el despacho de hoy (el costo marginal programado y la disponibilidad declarada "
          "de *R*, entre otras), el estado hidrológico (volumen útil de los embalses, aportes frente a su media "
          "histórica, presión sobre el agua, distancia al precio de escasez y días de autonomía), el despacho de ayer "
          "y el clima de las próximas semanas. Los bloques se eligieron con selección hacia adelante: partiendo del "
          "precio y el calendario, un bloque entra si le gana al modelo anterior con Diebold-Mariano *p* < 0,05 en "
          "alguno de los horizontes 3, 6 o 9, sin perder en ninguno. Cada versión se evaluó en 2020, 2021 y 2022, "
          "entrenando hasta el año anterior, con tres semillas, con una configuración fija: una capa, 128 neuronas, "
          "densa de 64, dropout de 0,2, tasa de aprendizaje de 0,001, lotes de 32 y ventana de 28 días.")
    + par("La primera selección eligió el despacho de hoy y el estado hidrológico. Como una búsqueda de control "
          "mostró que otra configuración era mejor en algunos casos, la selección se repitió con ella, y esa vez solo "
          "entró el despacho de hoy. Ambos conjuntos compitieron entonces en una búsqueda bayesiana de 30 "
          "configuraciones con keras_tuner (O'Malley et al., 2019; Snoek et al., 2012): de una a tres capas, de 32 a "
          "360 neuronas, densa de 32 a 256, dropout de 0,2 a 0,5, tasa de aprendizaje de 10^{−5} a 10^{−2}, lotes de "
          "32 o 64 y ventanas de 14, 28 o 56 días. Como la GPU no es determinista, una misma configuración puede "
          "variar unos cuatro puntos de mejora entre corridas, más que la diferencia entre las mejores. Por eso la "
          "búsqueda solo propuso candidatas, que se evaluaron de nuevo con tres semillas. Ganó la combinación más "
          "simple: los bloques de precio, calendario, despacho de hoy y estado hidrológico, con la configuración "
          "fija.")
    + par("La red se entrena con el error cuadrático medio y el optimizador Adam. En la validación se usa parada "
          "temprana con el último 10% del periodo de entrenamiento y paciencia de 10 épocas. En la prueba, en "
          "cambio, cada modelo mensual se entrena con todos los días cuyos objetivos ya se conocen, durante cuatro "
          "épocas, la mediana de la mejor época en la validación, y el pronóstico es el promedio de tres semillas. "
          "Antes de abrir la prueba se ensayó ese procedimiento en 2020-2022, y no fue significativamente peor que "
          "la parada temprana (Diebold-Mariano, *p* = 0,083). Por el no determinismo de la GPU, al volver a correr "
          "el modelo las cifras cambian un poco, aunque no las conclusiones.")
    + leyenda("Tabla", "Resumen de los tres modelos.", ppr=ANTES_TABLA)
    + TABLA_RESUMEN
    + fuente("Fuente: elaboración propia.")
)

REFS = [
    "Bergstra, J., y Bengio, Y. (2012). Random search for hyper-parameter optimization. *Journal of Machine "
    "Learning Research, 13*, 281-305.",
    "Chollet, F., et al. (2015). *Keras* [Software]. https://keras.io",
    "Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial "
    "Econometrics, 7*(2), 174-196. https://doi.org/10.1093/jjfinec/nbp001",
    "Dunn, O. J. (1961). Multiple comparisons among means. *Journal of the American Statistical Association, "
    "56*(293), 52-64. https://doi.org/10.1080/01621459.1961.10482090",
    "Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz-Sabater, J., et al. (2020). The ERA5 "
    "global reanalysis. *Quarterly Journal of the Royal Meteorological Society, 146*(730), 1999-2049. "
    "https://doi.org/10.1002/qj.3803",
    "Hyndman, R. J., y Khandakar, Y. (2008). Automatic time series forecasting: The forecast package for R. "
    "*Journal of Statistical Software, 27*(3), 1-22. https://doi.org/10.18637/jss.v027.i03",
    "Kursa, M. B., y Rudnicki, W. R. (2010). Feature selection with the Boruta package. *Journal of Statistical "
    "Software, 36*(11), 1-13. https://doi.org/10.18637/jss.v036.i11",
    "Ljung, G. M., y Box, G. E. P. (1978). On a measure of lack of fit in time series models. *Biometrika, "
    "65*(2), 297-303. https://doi.org/10.1093/biomet/65.2.297",
    "Lundberg, S. M., y Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in "
    "Neural Information Processing Systems, 30*, 4765-4774.",
    "National Oceanic and Atmospheric Administration [NOAA]. (2026). *Weekly ENSO indices and Oceanic Niño Index "
    "(ONI)* [Conjunto de datos]. Climate Prediction Center. https://www.cpc.ncep.noaa.gov/",
    "Newey, W. K., y West, K. D. (1994). Automatic lag selection in covariance matrix estimation. *The Review of "
    "Economic Studies, 61*(4), 631-653. https://doi.org/10.2307/2297912",
    "O'Malley, T., Bursztein, E., Long, J., Chollet, F., Jin, H., Invernizzi, L., et al. (2019). *KerasTuner* "
    "[Software]. https://github.com/keras-team/keras-tuner",
    "Snoek, J., Larochelle, H., y Adams, R. P. (2012). Practical Bayesian optimization of machine learning "
    "algorithms. *Advances in Neural Information Processing Systems, 25*, 2951-2959.",
    "XM S.A. E.S.P. (2026). *API de XM y SIMEM, consultada con la librería pydataxm* [Conjunto de datos]. "
    "https://www.xm.com.co/",
    "Zippenfenig, P. (2023). *Open-Meteo.com Weather API* [Software]. Zenodo. "
    "https://doi.org/10.5281/zenodo.7970649",
]

d = Docx(ENTRADA)
d.agregar_imagen(FIG / "f03_diseno_pronostico.png", "rIdFig03")
d.agregar_imagen(FIG / "f04_arquitectura_lstm.png", "rIdFig04")
d.reemplazar_vacio_tras("3.1 Datos", S31)
d.reemplazar_vacio_tras("3.2 Diseño del pronóstico", S32)
d.reemplazar_vacio_tras("3.3 Construcción de los modelos", S33)
d.referencias(REFS)
d.guardar(SALIDA)
print("ok", SALIDA)
