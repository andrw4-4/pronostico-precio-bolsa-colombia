"""Revisión del informe por los comentarios de la asesora del 26 de noviembre de 2026 (primera parte).
Aplica al texto los puntos 2.1 a 2.10 de Comentarios_Andres_2026-11-26.pdf, con las cifras de resultados/revision/
(ver resultados/revision/RESULTADOS.md). No cambia el título ni la estructura de capítulos.
- Resumen, 1.1, 1.2 y 1.3: la ventaja de la LSTM viene de la información; seis limitaciones (2.1, 2.2, 2.4, 2.5).
- 3.1 y 3.3: una sola definición del atraso, con su fuente; regla de los orígenes; corrección de Harvey et al. (2.5, 2.10).
- 3.4, 3.5 y 3.6: día de la semana en SARIMAX, alcance de XGBoost, "Versión anterior" de la LSTM, estandarización.
- 3.7 nueva: modelos agregados después de abrir las pruebas (LEAR, XGBoost alineado, LSTM con bloques 1 y 2,
  combinaciones y SARIMAX con día de la semana). El resumen de los modelos pasa a ser la 3.8.
- 4.1: tabla 15 ampliada, tabla de dos por dos, periodo limpio, atraso de tres días, episodios y regímenes, oráculo,
  semana final (2.2 a 2.7 y 2.10). 4.2: experimento de decisión (2.9). Capítulo V reescrito.
- Anexos C (diseño de 30 días) y D (oráculo). Referencias nuevas.
Quedan para la segunda parte: literatura (2.11), capítulo propio de mercado y datos, resumen en inglés y el mapa de
calor de Diebold-Mariano.
Uso: python s_46_revision_26nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, leyenda, reemplazar_en_bloque, runs, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
REV = Path(__file__).resolve().parents[2] / "resultados" / "revision"
LIMPIO = Path(__file__).resolve().parents[2] / "resultados" / "periodo_limpio"


# ------------------------------------------------------------------ utilidades
def cuerpo(d):
    """(inicio, fin, texto) de cada bloque del cuerpo, sin el índice."""
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def uno(d, inicio):
    k = [(s, e) for s, e, t in cuerpo(d) if t.startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return k[0]


def rep(d, inicio, texto):
    """Cambia todo el texto del párrafo que empieza con `inicio`, conservando su formato de párrafo."""
    s, e = uno(d, inicio)
    p = d.doc[s:e]
    assert p.startswith("<w:p") and not p.startswith("<w:tbl")
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
    apertura = re.match(r"<w:p(?:\s[^>]*)?>", p).group(0)
    d.doc = d.doc[:s] + apertura + (ppr.group(0) if ppr else "") + runs(texto) + "</w:p>" + d.doc[e:]


def cambiar(d, viejo, nuevo, con=""):
    """Cambia `viejo` por `nuevo` en el único bloque que lo tiene (y que además tiene `con`, si se da)."""
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t and con in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def tras(d, inicio, xml):
    s, e = uno(d, inicio)
    d.doc = d.doc[:e] + xml + d.doc[e:]


def antes(d, inicio, xml):
    s, e = uno(d, inicio)
    d.doc = d.doc[:s] + xml + d.doc[s:]


def borrar(d, inicio):
    s, e = uno(d, inicio)
    d.doc = d.doc[:s] + d.doc[e:]


def p(t):
    return f"<w:p>{runs(t)}</w:p>"


def nota(t):
    x = runs(t).replace("<w:r><w:rPr>", '<w:r><w:rPr><w:sz w:val="20"/>').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{x}</w:p>'


def cap(texto):
    return leyenda("Tabla", texto, ppr='<w:keepNext/><w:spacing w:before="240"/>')


def cap_anexo(nombre, texto):
    return ('<w:p><w:pPr><w:pStyle w:val="Descripcin"/><w:keepNext/><w:spacing w:before="240"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">{nombre}. </w:t></w:r>{runs(texto)}</w:p>')


def n(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",").replace("-", "−")


def pv(x):
    return "< 0,001" if x < 0.0005 else n(x, 3)


FUENTE = "Fuente: elaboración propia con datos de XM (2026)."

d = Docx(ENTRADA)
todo_antes = " ".join(t for _, _, t in cuerpo(d))
assert "3.7 " not in todo_antes.replace("3.7 Resumen de los modelos", ""), "ya hay referencias a la sección 3.7"

# =================================================================== Resumen
cambiar(d, "Como XM publica el precio con dos días de atraso, la semana pronosticada corresponde a los horizontes "
           "de 3 a 9 días.",
        "Como el precio se conoce con dos o tres días de atraso, la semana pronosticada corresponde a los horizontes "
        "de 3 a 9 días, y los resultados se comprueban también con los de 4 a 10.")
rep(d, "Se comparan tres modelos: SARIMAX, con un modelo para cada hora;",
    "Se comparan tres modelos: SARIMAX, con un modelo para cada hora; XGBoost, con un modelo por horizonte y "
    "variables elegidas entre 1.861 columnas, y una red LSTM codificador-decodificador que recibe cada dato desde el "
    "día en que se publica. Para separar el efecto del modelo del efecto de la información se agregan, como "
    "referencia, el modelo lineal LEAR, un XGBoost con la misma información de la LSTM, una LSTM con solo el precio "
    "y el calendario, y dos combinaciones de pronósticos.")
rep(d, "Los tres se reentrenan cada mes y se prueban una sola vez",
    "Los modelos se reentrenan cada mes y se evalúan en 2023-2025 y en 2026, contra la regla de repetir el último "
    "precio conocido. Un modelo se considera útil si reduce el RMSE en logaritmo al menos 5% frente a esa regla y la "
    "prueba de Diebold-Mariano da *p* < 0,05. Esas pruebas no son del todo independientes del diseño: la LSTM se "
    "diseñó después de que una primera versión pasara por ellas, y el alcance de una semana de XGBoost se eligió "
    "viendo la de 2026. Por eso se evalúan también los días del 7 de octubre al 20 de noviembre de 2026, que ninguna "
    "decisión usó.")
rep(d, "Los tres modelos cumplen el criterio. La LSTM es la mejor:",
    "Los tres modelos cumplen el criterio. De los tres, la LSTM, con la información alineada a su publicación, tuvo "
    "el menor error: lo reduce 14,9% en 2023-2025 y 19,7% en 2026. XGBoost lo reduce 11,6% y 10,0%, y SARIMAX 6,4% y "
    "5,6%. Esa ventaja viene de la información y no de la red: con los mismos datos, como el despacho programado, que "
    "se conoce antes que el precio, XGBoost reduce el error 18,5% y 22,4%, y LEAR, 21,3% y 24,8%, mientras que la "
    "LSTM con solo el precio y el calendario lo reduce 6,1% y 8,8%. En los días posteriores al 6 de octubre todos "
    "los modelos tienen menos error que el ingenuo, pero con 45 días ninguna diferencia es significativa. Los modelos "
    "pierden su ventaja en el déficit de aportes de agosto a noviembre de 2024, cuando el precio llegó a su máximo "
    "con el índice de El Niño en valores neutros, y no durante El Niño de 2023-2024. En pesos, las mejoras son "
    "menores y en 2023-2025 solo la de SARIMAX es significativa. En un experimento sencillo de decisión, los modelos "
    "capturan entre 32% y 55% del ahorro posible al elegir los dos días más baratos de la semana, frente a 20% y 24% "
    "de repetir la semana anterior; para elegir las horas más baratas de cada día, repetir la semana anterior "
    "captura tanto como los modelos.")
cambiar(d, "SARIMAX, XGBoost, LSTM, Diebold-Mariano, walk-forward.",
        "SARIMAX, XGBoost, LSTM, LEAR, Diebold-Mariano, walk-forward.")

# =================================================================== I. Introducción
cambiar(d, "el volumen útil de los embalses cayó por debajo de 40% y el precio superó los 1.000 COP/kWh (figura 2).",
        "el volumen útil de los embalses cayó por debajo de 40% y el precio superó los 1.000 COP/kWh (figura 2). "
        "Pero el precio no depende solo de El Niño ni del nivel de los embalses: el máximo de la muestra, el 30 de "
        "septiembre de 2024, ocurrió con el índice ONI cerca de cero, durante un déficit de aportes (sección 4.1).")
cambiar(d, "en octubre de 2026 el índice ONI, con el que la NOAA sigue a El Niño, llegó a 2,2 °C, un valor",
        "el índice ONI, con el que la NOAA sigue a El Niño, fue de 2,2 °C en el trimestre de julio a septiembre de "
        "2026, el último publicado en octubre, un valor")
cambiar(d, "como el despacho programado de cada día, que sale esa misma madrugada,",
        "como el despacho programado de cada día, que el operador entrega la víspera (CREG, 1995),")
cambiar(d, "(SARIMAX, XGBoost y una red LSTM) en las mismas condiciones y juzga",
        "(SARIMAX, XGBoost y una red LSTM) en las mismas filas y juzga")
cambiar(d, "Además, revisa en la literatura para qué decisiones sirve un pronóstico del precio y qué indican los "
           "resultados sobre esos usos (sección 4.2).",
        "Además, separa cuánto de la diferencia entre los modelos viene de la información que recibe cada uno "
        "(sección 4.1), y mide con un experimento sencillo cuánto del ahorro posible captura cada pronóstico en dos "
        "decisiones de un consumidor (sección 4.2).")
cambiar(d, "seleccionados con datos hasta 2022 y evaluados una sola vez entre 2023 y 2026.",
        "seleccionados con datos hasta 2022 y evaluados entre 2023 y 2026.")

rep(d, "Este trabajo pronostica el precio de bolsa nacional, hora por hora,",
    "Este trabajo pronostica el precio de bolsa nacional, hora por hora, para los siete días siguientes: 168 precios "
    "en cada pronóstico. El precio de cada día se conoce con dos o tres días de atraso (sección 3.1). El diseño "
    "supone dos, así que esos siete días quedan entre tres y nueve días después del último precio conocido "
    "(*h* = 3 a 9), y la sección 4.1 repite la evaluación con tres (*h* = 4 a 10). Se usan solo datos públicos, de "
    "marzo de 2015 al 6 de octubre de 2026, de XM, la NOAA, ERA5, el IDEAM y la tasa representativa del mercado "
    "(sección 3.1). Una segunda descarga, del 26 de noviembre de 2026, se usa solo para evaluar los días "
    "posteriores.")
rep(d, "Se comparan tres modelos: SARIMAX, XGBoost y una red LSTM. Cada uno se diseña",
    "Se comparan tres modelos: SARIMAX, XGBoost y una red LSTM. Cada uno se diseña y se ajusta con datos hasta 2022, "
    "y se evalúa en dos periodos de prueba: de 2023 a 2025, y 2026 hasta el 6 de octubre. Un modelo se considera "
    "útil si reduce al menos 5% la raíz del error cuadrático medio (RMSE) del logaritmo del precio frente al mejor "
    "de dos pronósticos de referencia, y si la diferencia es significativa según la prueba de Diebold y Mariano "
    "(1995) (sección 3.3). El error también se mide en pesos, como complemento (sección 4.1). Después de abrir esas "
    "pruebas se agregaron, como referencia, el modelo LEAR, versiones de XGBoost y de la LSTM con la información "
    "cambiada y dos combinaciones de pronósticos (sección 3.7), y todos los modelos se evaluaron en un tercer "
    "periodo, del 7 de octubre al 20 de noviembre de 2026.")
rep(d, "El trabajo tiene cuatro limitaciones principales.",
    "El trabajo tiene seis limitaciones principales. Primera, las pruebas de 2023-2025 y de 2026 no son una "
    "evaluación del todo independiente del diseño. La LSTM de este informe se diseñó después de que una primera "
    "versión pasara por esas pruebas, el 2 de noviembre de 2026, y después de conocer los errores de XGBoost en "
    "ellas (sección 3.6). En XGBoost, el alcance inicial era de 30 días y se redujo a una semana después de ver la "
    "prueba de 2026, porque más allá del séptimo día su ventaja dependía del periodo (anexo C). El criterio de "
    "evaluación se fijó antes de las pruebas y ninguna configuración se cambió después de verlas, pero esas dos "
    "decisiones sí las usaron. La única evaluación que ninguna decisión tocó es la de los días posteriores al 6 de "
    "octubre de 2026, y es corta: 45 días de origen (sección 4.1).")
rep(d, "Segunda, la información que más mejoraría el pronóstico, las ofertas de los generadores,",
    "Segunda, las ofertas de los generadores, de las que sale directamente el precio, se publican unos diez días "
    "tarde, cuando la semana que se quiere pronosticar ya pasó. Ningún modelo las puede usar a tiempo, y eso pone "
    "un límite a la precisión que se puede alcanzar (sección 4.1).")
rep(d, "Tercera, los tres modelos no usan exactamente la misma información.",
    "Tercera, los tres modelos no usan la misma información. XGBoost usa datos que se cortan en el día del último "
    "precio conocido, salvo el costo marginal del despacho programado del día siguiente (sección 3.1); SARIMAX usa "
    "solo el precio y el calendario, y la LSTM recibe cada dato el día en que se publica, lo que le permite usar "
    "datos más recientes, como el despacho programado. Para separar las dos diferencias, la sección 4.1 compara "
    "XGBoost y la LSTM con cada tipo de información; los modelos adicionales que eso exige se agregaron después de "
    "abrir las pruebas.")
rep(d, "Cuarta, en el periodo de prueba los precios fueron mucho más altos",
    "Cuarta, en el periodo de prueba los precios fueron mucho más altos que en el de entrenamiento: el promedio "
    "diario pasó de 219 COP/kWh entre 2015 y 2021 a 492 COP/kWh entre 2023 y 2025, un periodo que incluye El Niño "
    "de 2023-2024 y el déficit de aportes de agosto a noviembre de 2024. Los resultados muestran cómo se comportan "
    "los modelos en ese contexto y podrían ser distintos en otro.")
tras(d, "Cuarta, en el periodo de prueba los precios fueron mucho más altos",
     p("Quinta, el atraso con que se conoce el precio no tiene un plazo oficial. La regulación fija la hora de las "
       "ofertas y la del despacho programado (CREG, 1995), pero no un plazo para publicar el precio de bolsa, que "
       "sale del despacho ideal, calculado después de la operación real (CREG, 2009). En tres consultas a la API de "
       "XM, el último precio disponible tenía tres, dos y tres días de atraso (sección 3.1).")
     + p("Sexta, XM corrige los precios después de publicarlos. Entre la descarga del 9 de octubre y la del 26 de "
         "noviembre de 2026 cambiaron los precios de las 744 horas de los 31 días anteriores al 6 de octubre: la "
         "mitad, menos de 2 COP/kWh, pero 19 horas cambiaron más de 100 COP/kWh, y una, 823. Quien pronostica en la "
         "práctica parte de un precio provisional, mientras que los modelos se entrenaron y se evaluaron con el "
         "precio ya corregido, salvo en el último mes de cada descarga."))

# =================================================================== III. Metodología
rep(d, "Atraso de publicación. Cada fuente publica sus datos con un atraso distinto",
    "*Atraso de publicación.* Cada fuente publica sus datos con un atraso distinto (tabla 2). Para medirlo, se "
    "consultaron todas las series el 9 y el 10 de octubre de 2026 y se tomó, para cada una, la fecha del último dato "
    "disponible; cuando las dos consultas no coincidían, se tomó el atraso mayor. El precio de bolsa es la "
    "excepción: tenía tres días de atraso el 9 de octubre, dos el 10 de octubre y tres en una tercera consulta, el "
    "26 de noviembre. No hay un plazo oficial con el cual compararlo: el precio sale del despacho ideal, que se "
    "calcula después de la operación real (CREG, 2009), y la regulación no fija cuándo se publica. El diseño supone "
    "dos días: el día en que se hace el pronóstico, que se llama aquí *R*, el último precio conocido es el del día "
    "*t* = *R* − 2. La sección 4.1 repite la evaluación con tres. El despacho programado sí tiene plazo: el operador "
    "lo entrega antes de las 17:00 de la víspera (CREG, 1995), así que el del día *R* ya se conoce ese día. Las "
    "ofertas solo se conocen diez días después (figura 6).")
cambiar(d, "y cada modelo pasa por ellas una sola vez, después de quedar fijo.",
        "y cada modelo quedó fijo antes de pasar por ellas y no se cambió después. No todas las decisiones fueron "
        "anteriores a las pruebas: la LSTM se diseñó después de que una primera versión pasara por ellas "
        "(sección 3.6), y el alcance de XGBoost se eligió viendo la de 2026 (sección 3.5). Por eso se agregó un "
        "tercer periodo, el periodo limpio, con los días de origen del 7 de octubre al 20 de noviembre de 2026, que "
        "salen de una descarga posterior a todas las decisiones.")
tras(d, "Evaluación con origen móvil. En validación y en prueba,",
     p("*Orígenes de cada periodo.* Para los tres modelos vale la misma regla: un día de origen *t* pertenece a un "
       "periodo, en el horizonte *h*, si *t* y el día pronosticado *t* + *h* caen dentro de él. Así, 2023-2025 tiene "
       "1.093 orígenes en *h* = 3 y 1.087 en *h* = 9, y 2026 hasta el 6 de octubre, 276 y 270. Los de *h* = 9 son "
       "los que tienen la semana completa dentro del periodo. Sumados sobre los siete horizontes y las 24 horas dan "
       "las 183.120 y 45.864 filas de cada prueba. El periodo limpio tiene 45 orígenes en *h* = 3 y 39 con la "
       "semana completa."))
tras(d, "Para la prueba de Diebold y Mariano, la diferencia de pérdidas",
     p("Con pocas observaciones, la prueba rechaza de más. Por eso los valores *p* de la tabla 15 y de los análisis "
       "que se agregaron en la revisión de este informe llevan la corrección de Harvey et al. (1997): el estadístico "
       "se multiplica por la raíz cuadrada de (*T* + 1 − 2*h* + *h*(*h* − 1)/*T*)/*T*, con *h* = 9 para la semana "
       "completa, y se compara con una distribución *t* de Student con *T* − 1 grados de libertad. Con los más de "
       "270 orígenes de cada prueba la corrección cambia un solo veredicto de los tres modelos, el de XGBoost en "
       "*h* = 8 a 9 en 2026 (sección 4.1)."))

cambiar(d, "El día de la semana no se incluye, porque lo recoge la parte estacional.",
        "El día de la semana no se incluyó, con el argumento de que lo recoge la parte estacional; el diagnóstico de "
        "los residuos mostró después que no del todo (sección 3.7).")
cambiar(d, "Es lo que se cede a cambio de un modelo más simple que pronostica igual.",
        "Con 21 rezagos, la prueba solo deja de rechazar en 6 de las 24 horas. Un patrón que se repite igual todas "
        "las semanas, como el domingo más barato, es una componente fija que dos medias móviles semanales "
        "representan solo en parte; la sección 3.7 lo corrige con indicadores del día de la semana.",
        con="La prueba y el resultado de cada hora están en el anexo A")
cambiar(d, "Los modelos no se reentrenaron ni se ajustaron por eso (capítulo IV).",
        "Los modelos no se reentrenaron ni se ajustaron por eso, pero para XGBoost la prueba de 2026 dejó de ser "
        "independiente de esa decisión. El anexo C presenta los cuatro bloques del diseño de 30 días en las dos "
        "pruebas, incluidos los que no cumplen el criterio.")

# 3.6: versión anterior de la LSTM
tras(d, "Figura 14. Etapas de la construcción de la LSTM.",
     p("*Versión anterior.* La LSTM de esta sección es la segunda. La primera, del notebook 6_modelo_lstm.ipynb, se "
       "corrió el 2 de noviembre de 2026 y ese mismo día pasó por las pruebas de 2023-2025 y de 2026. Seguía la "
       "arquitectura de Salazar-Peña et al. (2025): tres capas LSTM apiladas, de 330, 210 y 150 unidades, con "
       "dropout de 0,2, 0,3 y 0,3, y una capa densa con las 168 salidas de la semana, entrenada con Adam y con el "
       "error absoluto medio como pérdida. Recibía los últimos 7 días, hora por hora, con el logaritmo del precio, "
       "14 columnas de calendario y cinco variables elegidas con un XGBoost de prueba: el costo marginal del "
       "despacho programado, su diferencia con el último precio, la disponibilidad declarada frente a la demanda, "
       "la distancia al precio de escasez y la presión de la demanda sobre el agua, cada una alineada a su fecha de "
       "publicación. Los hiperparámetros salieron de una búsqueda bayesiana de 10 combinaciones, entrenando hasta "
       "2021 y midiendo en 2022, y en la prueba se reentrenó cada mes, con 6 épocas y una sola semilla.")
     + p("En las pruebas cumplió el criterio en los cuatro bloques de horizontes: redujo el RMSE de la semana 12,0% "
         "en 2023-2025 y 12,9% en 2026 frente al ingenuo del día (tabla 15). De esa corrida quedaron el notebook "
         "ejecutado y sus tablas, en la carpeta resultados/modelo_lstm_v1/ del repositorio. Los pronósticos fila por "
         "fila se perdieron al cerrar la sesión de Colab, así que esta versión no entra en las comparaciones entre "
         "modelos.")
     + p("Al revisar una semana de la prueba, la del pronóstico del 25 de septiembre de 2026, se vieron tres "
         "defectos: la red repetía casi la misma forma del día en toda la semana, con el mismo pico de la tarde el "
         "sábado y el domingo; se quedaba corta de noche y en la mañana, y no anticipó el salto del precio del 2 de "
         "octubre. Con eso, y con el error de XGBoost en octubre de 2024, un mes de la prueba en el que subestimó "
         "el precio promedio en 670 COP/kWh en *h* = 6, se diseñó el 5 y el 6 de noviembre la LSTM que se describe a "
         "continuación (docs/LSTM_DISENO.md): codificador-decodificador con el calendario de cada día pronosticado, "
         "error cuadrático como pérdida, ventana de varias semanas, tres semillas y bloques de variables, entre "
         "ellos el del estado hidrológico. Esta segunda LSTM pasó una sola vez por las pruebas, pero su diseño ya "
         "había usado información de ellas. Por eso su resultado de 2023-2026 no es una evaluación independiente; "
         "la que sí lo es, la del periodo limpio, está en la sección 4.1."))
cambiar(d, "son su media y su desviación estándar en los días de entrenamiento, desde marzo de 2015.",
        "son su media y su desviación estándar en los días de entrenamiento, desde marzo de 2015. Se calculan de "
        "nuevo en cada reentrenamiento, solo con esos días, de modo que ningún dato posterior al corte entra en la "
        "escala.")
cambiar(d, "el 14 de noviembre de 2026, antes de abrir el test.",
        "el 14 de noviembre de 2026, antes de abrir el test de esta versión.")

# 3.7 nueva; el resumen pasa a 3.8
cambiar(d, "3.7 Resumen de los modelos", "3.8 Resumen de los modelos")
titulo_37 = d.titulo_como("3.8 Resumen de los modelos", "3.7 Modelos agregados después de abrir las pruebas")
S37 = [
    "Los modelos de esta sección se agregaron el 26 de noviembre de 2026, después de abrir las pruebas, para "
    "responder tres preguntas que la comparación de los tres modelos dejaba abiertas: si le ganan a una referencia "
    "más fuerte que el ingenuo, cuánto de la ventaja de la LSTM viene de la red y cuánto de la información, y si "
    "una combinación sencilla de pronósticos mejora a los modelos que combina. Ninguno tuvo búsqueda de "
    "hiperparámetros ni selección de variables, y los tres modelos de las secciones 3.4 a 3.6 no se cambiaron. Sus "
    "resultados de 2023-2025 y de 2026 son exploratorios, porque se agregaron conociendo esas pruebas; los de "
    "2020-2022 y los del periodo limpio no tienen ese problema. El código está en los scripts 9a a 9g del "
    "repositorio y en el notebook 6f_lstm_revision.ipynb.",

    "*LEAR.* Es la referencia que proponen Lago et al. (2021): una regresión lineal con regularización LASSO, que "
    "encoge los coeficientes y deja en cero los de las variables que no aportan. Aquí hay un modelo por cada "
    "horizonte y cada hora, 168 en total, con el objetivo de la ecuación (20). Las variables son los 24 logaritmos "
    "del precio de los días *t*, *t* − 1, *t* − 2 y *t* − 6, y el festivo y el día de la semana del día "
    "pronosticado. El parámetro de regularización se elige con el criterio de información de Akaike en cada "
    "recalibración mensual, como en la librería de Lago et al. (2021); las variables se estandarizan solo con los "
    "datos de entrenamiento, y se deja la misma separación de *h* + 1 días de XGBoost. Una segunda versión, LEAR "
    "alineado, agrega las nueve variables de los bloques 3 y 4 de la LSTM (tabla 9), con el valor del día "
    "*R* − *L*.",

    "*XGBoost alineado.* Es el XGBoost de la sección 3.5, con las mismas columnas y los mismos hiperparámetros de la "
    "tabla 7, al que se le agregan las nueve variables de los bloques 3 y 4 con el valor del día *R* − *L*, como "
    "entran a la LSTM, y sus valores de los dos días anteriores: 27 columnas más. Lo único que cambia es la "
    "información.",

    "*LSTM con solo el precio y el calendario.* Es la red de la sección 3.6 con los bloques 1 y 2, es decir, con la "
    "información cortada en el día *t*, entrenada con el procedimiento del test: cuatro épocas, tres semillas y "
    "reentrenamiento mensual. Con estos dos modelos y los dos de las secciones 3.5 y 3.6 se arma una comparación de "
    "dos por dos, modelo por información (sección 4.1). Para esa comparación, la LSTM de la sección 3.6 se corrió "
    "también en 2020-2022 con reentrenamiento mensual.",

    "*Combinaciones.* Se calculan dos combinaciones que no tienen parámetros que elegir (Bates y Granger, 1969). La "
    "primera es el promedio simple de los pronósticos en logaritmo de SARIMAX, XGBoost y la LSTM. La segunda suma el "
    "nivel del día que pronostica la LSTM y la forma del día que pronostica XGBoost: al pronóstico de XGBoost de "
    "cada hora se le resta el promedio de sus 24 horas y se le suma el promedio de las 24 horas de la LSTM.",

    "*SARIMAX con día de la semana.* Al modelo de la sección 3.4 se le agregaron seis indicadores del día de la "
    "semana, junto al festivo, con el mismo orden. En la validación de 2020-2022, con la regla de la tabla 5, la "
    "versión nueva le ganó a la fijada: el RMSE de la semana pasó de 0,2805 a 0,2776 (Diebold-Mariano *p* < 0,001), "
    "y la mejora frente al ingenuo del día, de 4,7% a 5,7%. Con los residuos de 2015-2019, las horas en que la "
    "prueba de Ljung-Box no rechaza pasaron de 17 a 20 con 14 rezagos, de 6 a 17 con 21 y de 6 a 15 con 28. Como "
    "ganó en la validación, en las pruebas se reportan las dos: la que solo lleva el festivo, que es la que se fijó "
    "antes de abrirlas, y esta, como una corrección posterior.",
]
antes(d, "3.8 Resumen de los modelos", titulo_37 + "".join(p(t) for t in S37))

# =================================================================== IV. Resultados
rep(d, "Esta sección compara los tres modelos con los dos ingenuos de la sección 2.4",
    "Esta sección compara los tres modelos con los dos ingenuos de la sección 2.4 en las dos pruebas, 2023-2025 y "
    "2026 hasta el 6 de octubre. Cada modelo se evaluó con su configuración fija y reentrenado cada mes, en las "
    "mismas 228.984 filas (sección 3.3). La tabla 15 resume la semana completa, *h* = 3 a 9, con las medidas de la "
    "sección 2.4 y el criterio de la sección 3.3. Trae también la primera versión de la LSTM (sección 3.6) y los "
    "modelos que se agregaron después de abrir las pruebas (sección 3.7), cuyos resultados en estos dos periodos "
    "son exploratorios.")

# tabla 15 ampliada
t15 = pd.read_csv(REV / "tabla15_ampliada.csv")
NOMBRES = {"LSTM, primera versión": "LSTM, primera versión", "LSTM bloques 1 y 2": "LSTM con bloques 1 y 2",
           "Nivel LSTM y forma XGBoost": "Nivel de la LSTM y forma de XGBoost"}
TESIS = ["Ingenuo del día", "Ingenuo semanal", "SARIMAX", "XGBoost", "LSTM"]
filas = [["Pronóstico", "RMSE", "MAE", "Mejora (%) semana", "*p*", "Mejora (%) *h* = 3", "Mejora (%) *h* = 3 a 7",
          "Mejora (%) *h* = 8 a 9"]]
for periodo in ("2023-2025", "2026"):
    g = t15[t15["periodo"] == periodo].set_index("pronostico")
    for grupo, nombres in ((f"*Prueba {periodo}*", TESIS),
                           ("*Versión anterior y modelos agregados*", [m for m in g.index if m not in TESIS])):
        filas.append([grupo] + [""] * 7)
        for m in nombres:
            r = g.loc[m]
            if m.startswith("Ingenuo"):
                filas.append([m, n(r["rmse"], 3), n(r["mae"], 3)] + ["—"] * 5)
                continue
            pp = r["p_sin_correccion"] if pd.isna(r["p_hln"]) else r["p_hln"]
            filas.append([NOMBRES.get(m, m), n(r["rmse"], 3), "—" if pd.isna(r["mae"]) else n(r["mae"], 3),
                          n(r["mejora"]), pv(pp), n(r["mejora_h3"]), n(r["mejora_h3_7"]), n(r["mejora_h8_9"])])
s, e = uno(d, "PronósticoRMSEMAEMejora (%) semana")
assert d.doc[s:e].startswith("<w:tbl")
d.doc = d.doc[:s] + tabla(filas, [4.3, 1.3, 1.3, 1.7, 1.5, 1.7, 1.8, 1.8], tam=18) + d.doc[e:]
s, e = uno(d, "Nota: RMSE y MAE del error en logaritmo (ecuaciones 13 y 14)")
d.doc = d.doc[:s] + nota(
    "Nota: RMSE y MAE del error en logaritmo (ecuaciones 13 y 14), en *h* = 3 a 9. La mejora es la reducción del "
    "RMSE frente al ingenuo del día (ecuación 17), que fue el mejor de los dos ingenuos en todos los bloques, y *p* "
    "es el valor de la prueba de Diebold-Mariano contra ese ingenuo en la semana completa, con la corrección de "
    "Harvey et al. (1997). Con esa corrección, XGBoost no cumple el criterio en *h* = 8 a 9 en 2026 (*p* = 0,056); "
    "todas las demás pruebas por bloque dan *p* < 0,05. Para XGBoost, la prueba de 2026 sirvió además para elegir "
    "el alcance de una semana (sección 3.5). La LSTM se diseñó después de conocer el resultado de su primera "
    "versión, de la que solo quedaron las métricas, sin MAE y con el valor *p* sin corrección (sección 3.6). Los "
    "modelos agregados son los de la sección 3.7. " + FUENTE) + d.doc[e:]

rep(d, "Los tres modelos cumplen el criterio en las dos pruebas y en los cuatro bloques de horizontes:",
    "Los tres modelos cumplen el criterio en la semana completa en las dos pruebas: reducen el RMSE en logaritmo más "
    "de 5% frente al mejor ingenuo, que en todos los casos fue el del día, y la prueba de Diebold-Mariano da "
    "*p* < 0,05. Por bloques de horizontes también lo cumplen, salvo XGBoost en *h* = 8 a 9 en 2026, donde la "
    "corrección para muestras pequeñas lleva el valor *p* de 0,047 a 0,056. De los tres, la LSTM, con la información "
    "alineada a su publicación, es la que más reduce el error en la semana completa, 14,9% en 2023-2025 y 19,7% en "
    "2026; le siguen XGBoost, con 11,6% y 10,0%, y SARIMAX, con 6,4% y 5,6%. El orden es el mismo con el MAE. La "
    "primera versión de la LSTM había mejorado 12,0% y 12,9%, cerca de XGBoost. El ingenuo semanal tuvo un RMSE "
    "10,4% mayor que el del día en 2023-2025 y 12,7% mayor en 2026: repetir la semana anterior respeta el ciclo "
    "semanal, pero usa un precio más viejo.")
tras(d, "Los tres modelos cumplen el criterio en la semana completa en las dos pruebas:",
     p("Los modelos agregados cambian la lectura de ese orden. LEAR, una regresión lineal con solo el precio y el "
       "calendario, mejora 9,9% y 14,0%: queda entre SARIMAX y XGBoost en 2023-2025 y por encima de XGBoost en "
       "2026. Con las nueve variables de los bloques 3 y 4 alineadas a su publicación, LEAR mejora 21,3% y 24,8%, y "
       "XGBoost, 18,5% y 22,4%; los dos tienen menos error que la LSTM. De las combinaciones, el promedio simple "
       "mejora 15,6% y 17,3%: supera a la LSTM en 2023-2025 y no en 2026. El nivel de la LSTM con la forma de "
       "XGBoost mejora 18,0% y 22,9%, más que cualquiera de los tres modelos en las dos pruebas. SARIMAX con el día "
       "de la semana mejora 7,2% y 6,6%, cerca de un punto más que la versión fijada. Más adelante, la tabla 18 "
       "separa cuánto de estas diferencias viene del modelo y cuánto de la información."))

rep(d, "Esto se relaciona con la información que recibe cada modelo (secciones 1.3 y 3.6).",
    "Esto se relaciona con la información que recibe cada modelo (secciones 1.3 y 3.6). La LSTM recibe el despacho "
    "programado del día *R*, que se conoce antes que el precio y fue el bloque que más aportó en su selección "
    "(tabla 10), y es en el nivel del día donde le gana a XGBoost. XGBoost, cuyas columnas más importantes son del "
    "propio precio (sección 3.5), es el que mejor pronostica la forma del día. La comparación con la misma "
    "información, más adelante en esta sección (tabla 18), muestra que la ventaja de la LSTM sobre XGBoost viene "
    "de esa información y no de la red.")
rep(d, "Aun así, el nivel sigue siendo la mayor parte del error:",
    "Aun así, el nivel sigue siendo la mayor parte del error: 66% del error cuadrático de la LSTM en 2023-2025. Un "
    "ejercicio de diagnóstico con XGBoost en la validación de 2020-2022 (diagnosticos/oraculo.py, anexo D) muestra "
    "cuánto se ganaría con mejor información. Si el modelo recibiera los valores futuros reales de la demanda y de "
    "la hidrología, su mejora en *h* = 7 solo pasaría de 8,3% a 11,1%: a una semana, conocer a la perfección esos "
    "fundamentales agrega menos de tres puntos. Con las ofertas futuras de los generadores pasaría a 39,5%, pero "
    "esa cifra es una cota casi circular, porque el precio de bolsa es la oferta de la planta marginal "
    "(sección 2.1) y darle al modelo las ofertas futuras es casi darle el precio. Lo que el ejercicio muestra es "
    "que el nivel del precio a una semana depende sobre todo de cómo van a ofertar los generadores, algo que ni la "
    "demanda ni la hidrología conocidas de antemano resuelven.")

# ---- bloques nuevos, después del párrafo de Duan y antes de la semana final
dxd = pd.read_csv(REV / "dos_por_dos.csv").set_index(["modelo", "informacion", "periodo"])["mejora"]
tc = pd.read_csv(REV / "todos_criterio.csv")
lear = tc[tc["bloque"] == "h = 3 a 9"].set_index(["modelo", "periodo"])["mejora"]
PER = ["2020-2022", "2023-2025", "2026"]
f18 = [["Modelo", "Información", "2020-2022", "2023-2025", "2026"]]
for modelo, info, etiqueta in (("XGBoost", "cortada en t", "Cortada en el día *t* (sección 3.5)"),
                               ("XGBoost", "alineada", "Alineada a su publicación (sección 3.7)"),
                               ("LSTM", "cortada en t", "Cortada en el día *t*, bloques 1 y 2 (sección 3.7)"),
                               ("LSTM", "alineada", "Alineada a su publicación (sección 3.6)")):
    f18.append([modelo, etiqueta] + [n(dxd[(modelo, info, q)]) for q in PER])
f18.append(["LEAR", "Cortada en el día *t* (sección 3.7)"] + [n(lear[("LEAR", q)]) for q in PER])
f18.append(["LEAR", "Alineada a su publicación (sección 3.7)"] + [n(lear[("LEAR alineado", q)]) for q in PER])
assert f18[1][2:] == ["11,6", "11,6", "10,0"] and f18[4][2:] == ["17,1", "14,9", "19,7"], f18

cl = pd.read_csv(LIMPIO / "criterio.csv")
cl = cl[cl["grupo"] == "desde el 7 de octubre"]
sem = cl[cl["bloque"] == "h = 3 a 9"].set_index("modelo")
h3 = cl[cl["bloque"] == "h = 3"].set_index("modelo")
assert (sem["origenes"] == 45).all() and (sem["ingenuo"] == "semanal").all() and h3["cumple_hln"].all()
f19 = [["Pronóstico", "RMSE", "Mejora (%) semana", "*p*", "Mejora (%) *h* = 3"],
       ["Ingenuo semanal", n(sem["rmse_ingenuo"].iloc[0], 3), "—", "—", "—"]]
for m in sem.sort_values("mejora", ascending=False).index:
    f19.append([{"LSTM bloques 1 y 2": "LSTM con bloques 1 y 2", "Nivel LSTM y forma XGBoost":
                 "Nivel de la LSTM y forma de XGBoost"}.get(m, m), n(sem.loc[m, "rmse"], 3), n(sem.loc[m, "mejora"]),
                n(sem.loc[m, "dm_p_hln"], 2), n(h3.loc[m, "mejora"])])
assert f19[2][0] == "XGBoost alineado" and f19[2][2] == "18,6" and f19[-1][0] == "LSTM" and f19[-1][2] == "8,3"

ep = pd.read_csv(REV / "episodios.csv").rename(columns={"episodio": "caso"})
rg = pd.read_csv(REV / "regimenes.csv").rename(columns={"regimen": "caso"})
f20 = [["Caso", "Orígenes", "SARIMAX", "XGBoost", "LSTM"]]
for etiqueta, tabla_, caso in (
        ("El Niño, septiembre de 2023 a abril de 2024", ep, "El Niño 2023-2024"),
        ("Déficit de aportes, agosto a noviembre de 2024", ep, "Déficit de aportes de 2024"),
        ("Resto de 2023-2025", ep, "Resto de 2023-2025"),
        ("Aportes bajos, menos de 80%", rg, "aportes bajos (menos de 80%)"),
        ("Aportes normales, de 80% a 110%", rg, "aportes normales (80% a 110%)"),
        ("Aportes altos, más de 110%", rg, "aportes altos (más de 110%)")):
    g = tabla_[tabla_["caso"] == caso].set_index("modelo")
    assert len(g) == 3, caso
    f20.append([etiqueta, f"{int(g['origenes'].iloc[0]):,}".replace(",", ".")]
               + [f"{n(g.loc[m, 'mejora'])} ({pv(g.loc[m, 'dm_p_hln'])})" for m in ("SARIMAX", "XGBoost", "LSTM")])
assert f20[2][4].startswith("1,6") and f20[1][4].startswith("18,6"), f20

NUEVO_41 = (
    p("*Modelo e información.* La tabla 18 compara XGBoost y la LSTM con los dos tipos de información: cortada en "
      "el día *t*, como la recibe el XGBoost de la sección 3.5, y alineada a la publicación de cada dato, como la "
      "recibe la LSTM de la sección 3.6. Las otras dos celdas son los modelos de la sección 3.7. Con cualquiera de "
      "los dos modelos, pasar de la información cortada a la alineada baja el error en los tres periodos, siempre "
      "con *p* < 0,01. Con la misma información, en cambio, la LSTM no le gana a XGBoost. Con la información "
      "cortada, XGBoost tiene menos error en 2020-2022 y en 2023-2025 (*p* < 0,002), y en 2026 no se distinguen "
      "(*p* = 0,55). Con la alineada, XGBoost tiene menos error en los tres periodos, con una diferencia que solo "
      "es significativa en 2023-2025 (*p* = 0,32, 0,04 y 0,26). LEAR alineado, un modelo lineal, queda por encima "
      "de los dos. La ventaja de la LSTM sobre XGBoost en la tabla 15 venía, entonces, de la información y no de la "
      "red. El resultado de 2020-2022 no depende de las pruebas; los de 2023-2025 y 2026 son exploratorios.")
    + cap("Mejora del RMSE en logaritmo de la semana frente al ingenuo del día, según el modelo y la información "
          "que recibe.")
    + tabla(f18, [2.2, 7.4, 1.9, 1.9, 1.9])
    + nota("Nota: mejora en porcentaje, en *h* = 3 a 9, con reentrenamiento mensual. Todas son significativas frente "
           "al ingenuo del día (*p* < 0,01). Los valores *p* del texto son de la prueba de Diebold-Mariano entre "
           "dos celdas, con la corrección de Harvey et al. (1997). " + FUENTE)
    + p("*Periodo limpio.* Con la descarga del 26 de noviembre de 2026, que trae el precio hasta el 23 de noviembre, "
        "se evaluaron todos los modelos en los 45 días de origen del 7 de octubre al 20 de noviembre, sin cambiar "
        "ninguna configuración; 39 tienen la semana completa. Son días que ningún modelo ni ninguna decisión había "
        "visto. En este periodo el mejor ingenuo en la semana fue el semanal (tabla 19). Todos los modelos tuvieron "
        "menos error que él, entre 8,3% y 18,6%, pero ninguna diferencia es significativa: con 45 orígenes la prueba "
        "tiene poca potencia. En *h* = 3, contra el ingenuo del día, todos cumplen el criterio. El orden coincide "
        "con el de la tabla 18 en que XGBoost alineado tuvo el menor error, y difiere en que la LSTM de la sección "
        "3.6 tuvo la menor mejora, por debajo de su versión con solo el precio y el calendario. Solo 9 orígenes "
        "tienen su semana después del 14 de noviembre, la fecha de la última decisión, y de ellos 3 tienen la semana "
        "completa; no alcanzan para una prueba. Este periodo confirma que los modelos reducen el error frente al "
        "ingenuo, pero es muy corto para ordenarlos.")
    + cap("Resultados en el periodo limpio, con los orígenes del 7 de octubre al 20 de noviembre de 2026.")
    + tabla(f19, [6.4, 1.8, 2.6, 1.6, 2.6])
    + nota("Nota: RMSE en logaritmo en *h* = 3 a 9. La mejora de la semana es frente al ingenuo semanal, el mejor de "
           "los dos en ese bloque, y *p* es el valor de la prueba de Diebold-Mariano con la corrección de Harvey et "
           "al. (1997). En *h* = 3 el mejor ingenuo es el del día. " + FUENTE)
    + p("*Atraso de tres días.* Si el precio se conociera siempre con tres días de atraso, el primer día "
        "pronosticable sería *t* + 4 y la semana, *h* = 4 a 10. Para SARIMAX y XGBoost esos pronósticos salen de los "
        "mismos modelos, con un día más de horizonte; para la LSTM se armó de nuevo el panel con el precio un día "
        "más atrasado y se entrenó otra vez con la misma configuración. Los tres siguen cumpliendo el criterio en la "
        "semana completa: SARIMAX mejora 6,5% en 2023-2025 y 5,8% en 2026; XGBoost, 11,2% y 8,7%, y la LSTM, 18,8% y "
        "23,3%. Solo XGBoost deja de cumplirlo en un bloque, *h* = 9 a 10 en 2026 (7,1%, *p* = 0,07). La LSTM gana "
        "más que con dos días, porque el despacho programado queda todavía más reciente frente al precio. Los "
        "resultados no dependen, entonces, de que el atraso sea de dos o de tres días.")
    + p("*Episodios y regímenes.* El año 2024 mezcla dos episodios distintos. El Niño de 2023-2024, de septiembre de "
        "2023 a abril de 2024, llevó el volumen útil de los embalses a 31% en abril de 2024. Los precios más altos "
        "llegaron después, entre agosto y noviembre de 2024, con el ONI en valores neutros y con aportes de entre "
        "58% y 65% de su media histórica hasta octubre, el mes en que el precio promedio fue de 1.529 COP/kWh. Ya en "
        "septiembre y octubre de 2023 el precio había pasado de 1.000 COP/kWh con los embalses por encima de 72%, "
        "pero con aportes de 56% y 59% de la media. El precio responde más a los aportes y a lo que se espera del "
        "agua que al nivel del embalse. La tabla 20 separa el error de los modelos por episodio y por régimen de "
        "aportes, definido con información conocida el día *t*: el promedio de los aportes de los 30 días "
        "anteriores, como fracción de su media histórica.")
    + cap("Mejora del RMSE en logaritmo frente al ingenuo del día por episodio y por régimen de aportes, "
          "*h* = 3 a 9.")
    + tabla(f20, [5.5, 1.7, 2.7, 2.7, 2.7])
    + nota("Nota: mejora en porcentaje y, entre paréntesis, el valor *p* de Diebold-Mariano con la corrección de "
           "Harvey et al. (1997). Los episodios se definen por la fecha de origen dentro de 2023-2025; los regímenes "
           "usan los orígenes de las dos pruebas. " + FUENTE)
    + p("En El Niño la LSTM mantuvo su ventaja, con 18,6%, mientras que XGBoost y SARIMAX no se distinguieron del "
        "ingenuo. En el déficit de aportes de 2024 ningún modelo se distinguió del ingenuo: la LSTM mejoró 1,6% y "
        "XGBoost 4,0%, y los tres quedaron por debajo del precio real. Es ahí, y no en El Niño, donde los modelos "
        "pierden su ventaja. Por régimen, la mejora de los tres modelos es menor con aportes bajos que con aportes "
        "normales. Además, en un día típico la ventaja es menor que la que muestra el RMSE: en 2023-2025, la mediana "
        "del error absoluto en logaritmo de SARIMAX y de XGBoost fue 8,8% y 10,9% mayor que la del ingenuo del día, "
        "y la de la LSTM, 0,7% menor; en 2026 la de la LSTM fue 15,0% menor, y las de los otros dos, casi iguales a "
        "la del ingenuo. Los modelos bajan el RMSE sobre todo porque recortan los errores grandes."))
tras(d, "Como prueba de robustez, se intentó corregir ese sesgo con el estimador de Duan (1983),", NUEVO_41)

rep(d, "Por último, con los precios conocidos hasta el 6 de octubre de 2026, los tres modelos pronosticaron",
    "Por último, con los precios conocidos hasta el 6 de octubre de 2026 se pronosticó con los tres modelos la "
    "semana del 9 al 15 de octubre (figura 18). No es un pronóstico hecho antes de conocer esos precios: las "
    "configuraciones se fijaron el 1 de noviembre (XGBoost) y el 14 de noviembre (LSTM), cuando ya estaban "
    "publicados. Es una demostración que respeta la información disponible el 6 de octubre. En esa semana el orden "
    "fue otro: XGBoost tuvo el menor error, con un RMSE en logaritmo de 0,201, seguido de SARIMAX, con 0,218, y del "
    "ingenuo del día, con 0,234; la LSTM tuvo 0,252. Una sola semana no cambia el resultado de las pruebas, pero "
    "muestra que la ventaja promedio no se cumple todas las semanas.")

# ---- 4.2: experimento de decisión
dec = pd.read_csv(REV / "decision.csv")
cap_ = dec[dec["caso"].isin(["2023-2025", "2026"])].set_index(["decision", "pronostico", "caso"])["captura"]
f21 = [["Pronóstico", "Elegir días, 2023-2025", "Elegir días, 2026", "Elegir horas, 2023-2025", "Elegir horas, 2026"]]
for m in ("Ingenuo semanal", "Ingenuo del día", "SARIMAX", "XGBoost", "LSTM", "LEAR"):
    f21.append([m] + [n(100 * cap_[(dc, m, q)], 0) if (dc, m, q) in cap_.index else "—"
                      for dc in ("Elegir días", "Elegir horas") for q in ("2023-2025", "2026")])
assert f21[1][1:] == ["20", "24", "81", "83"] and f21[5][1:] == ["35", "55", "78", "76"], f21

rep(d, "Los resultados de la sección 4.1 no miden el valor del pronóstico para ninguna de esas decisiones,",
    "Los resultados de la sección 4.1 ya indican para qué podría servir mejor cada modelo: la LSTM tuvo el menor "
    "error en el nivel del día, que es lo que importa para elegir en qué días concentrar un consumo, y XGBoost en "
    "la forma, que importa para elegir en qué horas. También muestran dos límites. En pesos los tres modelos "
    "quedan, en promedio, por debajo del precio real (tabla 17), de modo que un comercializador que estimara con "
    "ellos el costo de su exposición a la bolsa lo subestimaría. Y los pronósticos son puntuales, mientras que para "
    "gestionar el riesgo hace falta saber también qué tan grande puede ser el error (sección 1.3).")
rep(d, "Por eso este trabajo no afirma cuánto ahorraría un participante del mercado con estos pronósticos.",
    "Este trabajo no afirma, entonces, cuánto ahorraría un participante del mercado con estos pronósticos. Medirlo "
    "exige, como en Zareipour et al. (2010) y Kath y Ziel (2018), simular la decisión de un usuario concreto, con "
    "sus contratos, sus restricciones y el costo de cambiar su operación. Esa evaluación queda como trabajo futuro "
    "(sección 5.2).")
tras(d, "Los resultados de la sección 4.1 ya indican para qué podría servir mejor cada modelo:",
     p("Para medirlo se hizo un experimento sencillo, con las reglas escritas antes de calcular nada "
       "(docs/EXPERIMENTO_DECISION.md en el repositorio). Un consumidor toma dos decisiones con cada pronóstico. En "
       "la primera, elegir días, debe ubicar dos días de consumo plano dentro de la semana pronosticada y escoge los "
       "dos de menor precio medio pronosticado; su costo es el precio medio real de esos dos días. En la segunda, "
       "elegir horas, escoge en cada día pronosticado las cuatro horas más baratas según el pronóstico, y su costo "
       "es el precio real medio de esas horas. Las referencias son elegir al azar, cuyo costo esperado es el precio "
       "medio de la semana, y elegir con información perfecta. La medida es la fracción del ahorro posible que "
       "captura cada pronóstico: el costo al azar menos el costo con el pronóstico, dividido por el costo al azar "
       "menos el costo con información perfecta. Las diferencias se prueban con una prueba pareada sobre el costo "
       "de cada día de origen, con la varianza de la sección 3.3. No es el ahorro de ningún participante real: no "
       "hay contratos, restricciones ni costos de mover el consumo.")
     + cap("Fracción del ahorro posible que captura cada pronóstico en el experimento de decisión, en porcentaje.")
     + tabla(f21, [3.4, 3.0, 3.0, 3.0, 3.0])
     + nota("Nota: orígenes con la semana completa, 1.087 en 2023-2025 y 270 en 2026. El ingenuo del día pronostica "
            "el mismo nivel para los siete días, así que solo sirve para elegir horas. LEAR se agregó después de "
            "abrir las pruebas (sección 3.7). " + FUENTE)
     + p("Al elegir días, los tres modelos capturan más que el ingenuo semanal (tabla 21): entre 32% y 35% del "
         "ahorro posible en 2023-2025, frente a 20%, y en 2026 la LSTM captura 55%, frente a 32% de XGBoost, 35% de "
         "SARIMAX y 24% del ingenuo; en 2026 solo la diferencia de la LSTM con el ingenuo es significativa. La LSTM "
         "le gana a XGBoost en 2026 (*p* < 0,001), pero en 2023-2025 no se distinguen (*p* = 0,51). Al elegir horas "
         "todos capturan mucho más, entre 76% y 83%, porque la forma del día se repite. XGBoost le gana a la LSTM en "
         "2023-2025 (*p* < 0,001) y no en 2026 (*p* = 0,32), y el ingenuo semanal captura tanto como los modelos: en "
         "2026, más que XGBoost y que la LSTM (*p* < 0,01). LEAR captura tanto o más que los tres modelos al elegir "
         "días, y fue el mejor al elegir horas en 2023-2025.")
     + p("La recomendación de usar la LSTM para elegir días y XGBoost para elegir horas queda, entonces, respaldada "
         "solo en parte: cada mitad se cumple en una de las dos pruebas. Lo que el experimento sí muestra es que "
         "para decidir en qué días consumir, un pronóstico aporta frente a repetir la semana anterior, y que para "
         "decidir en qué horas basta el perfil de la semana anterior. En 2024 la captura al elegir días cayó a cerca "
         "de 20% en los tres modelos, igual que su ventaja en el error (tabla 16)."))

# =================================================================== V. Conclusiones
rep(d, "Este trabajo buscaba saber si modelos estadísticos y de aprendizaje automático pronostican",
    "Este trabajo buscaba saber si modelos estadísticos y de aprendizaje automático pronostican el precio de bolsa "
    "horario de Colombia a una semana con menor error que un pronóstico ingenuo, usando solo la información "
    "publicada al momento de pronosticar (sección 1.2). La respuesta es sí. SARIMAX, XGBoost y la LSTM cumplieron el "
    "criterio de la sección 3.3 en la semana completa en las dos pruebas, 2023-2025 y 2026: redujeron el RMSE en "
    "logaritmo más de 5% frente al ingenuo del día, con diferencias significativas según la prueba de "
    "Diebold-Mariano. De los tres, la LSTM fue la que más lo redujo, 14,9% y 19,7%, seguida de XGBoost, con 11,6% y "
    "10,0%, y de SARIMAX, con 6,4% y 5,6% (tabla 15). En los 45 días posteriores al 6 de octubre de 2026, que "
    "ninguna decisión usó, todos tuvieron menos error que el mejor ingenuo, entre 8% y 19%, aunque sin diferencias "
    "significativas (tabla 19).")
rep(d, "El primer objetivo, construir una base de datos en la que cada dato entra en la fecha en que se publica,",
    "El hallazgo principal es que lo que más mejora el pronóstico es la información y no el tipo de modelo. "
    "Construir una base de datos en la que cada dato entra en la fecha en que se publica, el primer objetivo, "
    "mostró que no toda la información llega con el atraso del precio: el despacho programado de cada día se conoce "
    "desde la víspera, cuando el último precio es de dos o tres días antes. Con la información cortada en el día "
    "del último precio, XGBoost mejoró 11,6% y 10,0%, y la LSTM, 6,1% y 8,8%; con cada dato alineado a su "
    "publicación, 18,5% y 22,4%, y 14,9% y 19,7% (tabla 18). Con la misma información, la red no le ganó a XGBoost "
    "en ningún periodo, y un modelo lineal con regularización, LEAR, tuvo el menor error de todos, con 21,3% y "
    "24,8%. La ventaja de la LSTM de este trabajo sobre XGBoost venía de los datos que recibía.")
rep(d, "El segundo objetivo se cumplió con un mismo diseño para los tres modelos:",
    "El segundo objetivo se cumplió con un mismo diseño para los tres modelos: los 168 precios de los días *t* + 3 "
    "a *t* + 9, las configuraciones elegidas con datos hasta 2022 y la evaluación en las mismas filas, con el "
    "criterio fijado antes de las pruebas (sección 3.3). Dos decisiones, sin embargo, se tomaron conociendo las "
    "pruebas: la LSTM se diseñó después de que una primera versión pasara por ellas, y el alcance de una semana de "
    "XGBoost se eligió viendo la de 2026 (sección 1.3). Los resultados se mantienen si el precio se conoce con tres "
    "días de atraso en vez de dos (sección 4.1).")
rep(d, "La comparación del tercer objetivo muestra, además, que la ventaja no es la misma en todos los periodos.",
    "La comparación del tercer objetivo muestra, además, que la ventaja no es la misma en todos los periodos. Los "
    "modelos la pierden en el déficit de aportes de agosto a noviembre de 2024, cuando el precio llegó a su máximo "
    "de la muestra con el ONI en valores neutros: ninguno se distinguió del ingenuo, y la LSTM mejoró 1,6%. En El "
    "Niño de 2023-2024, en cambio, la LSTM mejoró 18,6% (tabla 20). En un día típico la ventaja también es menor: "
    "en 2023-2025 la mediana del error absoluto de SARIMAX y de XGBoost fue mayor que la del ingenuo del día. Y en "
    "la semana del 9 al 15 de octubre de 2026 XGBoost tuvo el menor error y la LSTM más que el ingenuo del día "
    "(figura 18). Lo que se sostiene es que los modelos le ganan al ingenuo en el promedio de varios años, no en "
    "cada episodio ni en cada semana.")
rep(d, "La mayor parte del error que queda está en el nivel del día, es decir,",
    "La mayor parte del error que queda está en el nivel del día, es decir, en el promedio de sus 24 horas: 66% del "
    "error cuadrático de la LSTM en 2023-2025 (sección 4.1). La forma del día, con sus horas caras y baratas, se "
    "repite de un día a otro y tiene menos error; el nivel depende de cómo van a ofertar los generadores. El "
    "ejercicio de diagnóstico de la sección 4.1 muestra que conocer de antemano la demanda y la hidrología de la "
    "semana agregaría menos de tres puntos de mejora en *h* = 7. Así, el límite del pronóstico a una semana parece "
    "estar más en la información que se conoce a tiempo que en el modelo.")
rep(d, "En pesos, que es lo que paga quien compra o vende energía, las mejoras son menores:",
    "En pesos, que es lo que paga quien compra o vende energía, las mejoras son menores: en 2023-2025, 7,1% con la "
    "LSTM, 5,8% con SARIMAX y 3,7% con XGBoost, y solo la de SARIMAX es significativa; en 2026 lo son las tres "
    "(tabla 17). La otra parte del tercer objetivo, el valor del pronóstico para la toma de decisiones, se midió "
    "con un experimento sencillo (sección 4.2). Para elegir los dos días más baratos de la semana, los modelos "
    "capturaron entre 32% y 55% del ahorro posible, frente a 20% y 24% del ingenuo semanal. Para elegir las cuatro "
    "horas más baratas de cada día, el ingenuo semanal capturó tanto como los modelos, cerca de 80%. El experimento "
    "no mide el ahorro de un participante real, que depende de sus contratos y restricciones (Zareipour et al., "
    "2010; Kath y Ziel, 2018).")
rep(d, "De estos resultados salen tres recomendaciones para quien use un pronóstico",
    "De estos resultados salen cuatro recomendaciones para quien use un pronóstico del precio de bolsa a una "
    "semana. Primera, usar cada dato desde el día en que se publica, en especial el despacho programado: fue lo que "
    "más redujo el error, con cualquier modelo. Segunda, comparar con el ingenuo del día y con un modelo lineal "
    "como LEAR antes de usar un modelo más complejo: con la información alineada, LEAR tuvo menos error que la red. "
    "Tercera, combinar pronósticos: el nivel de la LSTM con la forma de XGBoost tuvo menos error que cualquiera de "
    "los tres modelos en las dos pruebas. Cuarta, al usar el pronóstico en pesos, tener en cuenta que los tres "
    "modelos quedaron en promedio por debajo del precio real, entre 15 y 46 COP/kWh en 2023-2025 (sección 4.1).")

rep(d, "Estas conclusiones están sujetas a las cuatro limitaciones de la sección 1.3:",
    "Estas conclusiones están sujetas a las seis limitaciones de la sección 1.3: las pruebas no son del todo "
    "independientes del diseño, las ofertas se publican tarde, los tres modelos no reciben la misma información, el "
    "periodo de prueba tuvo precios mucho más altos que el de entrenamiento, el atraso del precio no tiene un plazo "
    "oficial y XM corrige los precios después de publicarlos. Los resultados agregan cuatro más. LEAR, las "
    "combinaciones y los modelos que separan el efecto de la información se agregaron después de abrir las pruebas, "
    "así que sus cifras de 2023-2026 son exploratorias. El periodo limpio tiene 45 orígenes y no alcanza para "
    "ordenar los modelos. En pesos, las mejoras son menores que en logaritmo y los pronósticos quedan por debajo "
    "del precio real; corregir ese sesgo con el estimador de Duan (1983) no bajó el error en pesos (sección 4.1). Y "
    "el experimento de decisión es una simplificación (sección 4.2). Con eso en cuenta, quedan seis líneas de "
    "trabajo.")
rep(d, "La misma información para todos los modelos. Entrenar XGBoost con el panel de la LSTM,",
    "*Seguir evaluando con datos nuevos.* Cada semana que pasa agrega orígenes al periodo limpio. Repetir la "
    "evaluación de la tabla 19 con varios meses, sin cambiar ninguna configuración, diría cuál de los modelos con "
    "la información alineada es mejor, que es lo que 45 orígenes no permiten decidir. El ONI publicado en octubre "
    "de 2026 fue de 2,2 °C (sección 1.1), así que ese periodo puede incluir un episodio de El Niño.")
rep(d, "Información sobre las ofertas. Las ofertas de los generadores son lo que más mueve el precio",
    "*Información sobre las ofertas.* El nivel del precio a una semana depende de cómo ofertan los generadores, y "
    "las ofertas se conocen tarde. Un trabajo futuro podría pronosticar primero las ofertas de las plantas que más "
    "pesan en el precio, con sus ofertas pasadas y el estado de sus embalses, y usar ese pronóstico como entrada "
    "del modelo del precio. Sería un modelo de la oferta, que este trabajo dejó por fuera (sección 1.3).")
rep(d, "Combinar los pronósticos. La LSTM tuvo el menor error de nivel y XGBoost el menor error de forma",
    "*El atraso real de cada dato.* El atraso del precio se midió con tres consultas. Registrar cada día, a la "
    "misma hora, el último dato disponible de cada serie daría la distribución del atraso, y guardar el precio tal "
    "como se publica permitiría evaluar los modelos con el precio provisional, que es el que se conoce al "
    "pronosticar.")
rep(d, "Pronósticos con incertidumbre. Los tres modelos dan un solo valor por hora.",
    "*Pronósticos con incertidumbre.* Los modelos dan un solo valor por hora. Para gestionar el riesgo, como al "
    "decidir cuánta energía cubrir con contratos, sirve más un rango o una distribución del precio, una de las "
    "direcciones que señala Weron (2014).")
rep(d, "El valor del pronóstico en una decisión. Siguiendo a Zareipour et al. (2010) y a Kath y Ziel (2018),",
    "*El valor del pronóstico en una decisión.* El experimento de la sección 4.2 usa un consumidor sin contratos ni "
    "restricciones. Siguiendo a Zareipour et al. (2010) y a Kath y Ziel (2018), se puede simular la decisión de un "
    "participante concreto, como la compra en bolsa de un comercializador, con sus contratos y restricciones, para "
    "medir en pesos cuánto vale pasar del ingenuo a cada modelo.")
rep(d, "Seguir probando los modelos. En octubre de 2026 el índice ONI llegó a 2,2 °C",
    "*Los periodos de déficit de aportes.* Los modelos perdieron su ventaja entre agosto y noviembre de 2024. "
    "Variables que anticipen el agua de las semanas siguientes, como los pronósticos de aportes hechos por "
    "terceros, que este trabajo dejó por fuera (sección 1.3), podrían ayudar en esos periodos.")

# =================================================================== Anexos C y D
d30 = pd.read_csv(REV / "diseno_30_dias.csv")
fc = [["Periodo", "Bloque", "Orígenes", "Mejor ingenuo", "Mejora (%)", "*p*", "Cumple"]]
for _, r in d30.iterrows():
    fc.append([r["periodo"], r["bloque"].replace("h =", "*h* ="), f"{int(r['origenes']):,}".replace(",", "."),
               r["ingenuo"].capitalize(), n(r["mejora"]), pv(r["dm_p_hln"]), "Sí" if r["cumple_hln"] else "No"])
assert fc[7][4] == "6,4" and fc[8][4] == "−7,2" and fc[8][6] == "No", fc
fd = [["Lo que recibe el modelo", "*h* = 3", "*h* = 7"], ["Lo que tiene al pronosticar", "18,4", "8,3"],
      ["Más la demanda futura", "19,5", "8,5"], ["Más la hidrología futura", "19,0", "11,1"],
      ["Más la demanda y la hidrología futuras", "20,2", "11,1"], ["Más las ofertas futuras", "35,8", "39,5"],
      ["Más todo lo anterior", "35,0", "40,3"]]
ANEXOS = (
    d.titulo_como("Anexo B. Medidas y criterios de XGBoost", "Anexo C. Diseño original de 30 días de XGBoost")
    + p("XGBoost se diseñó para pronosticar hasta 30 días, con cuatro bloques de horizontes: *h* = 3, *h* = 3 a 7, "
        "*h* = 8 a 14 y *h* = 15 a 30. El alcance se redujo a una semana después de ver la prueba de 2026 "
        "(secciones 1.3 y 3.5). La tabla C1 presenta los cuatro bloques en las dos pruebas, con el criterio de la "
        "sección 3.3. En 2023-2025 los cuatro lo cumplen. En 2026 los dos bloques más lejanos no: en *h* = 8 a 14 la "
        "mejora no es significativa, y en *h* = 15 a 30 el modelo tuvo más error que el ingenuo semanal.")
    + cap_anexo("Tabla C1", "Criterio de la sección 3.3 en los cuatro bloques del diseño original de XGBoost.")
    + tabla(fc, [2.2, 2.4, 2.0, 2.6, 2.0, 1.8, 1.6])
    + nota("Nota: mejora del RMSE en logaritmo frente al mejor de los dos ingenuos en cada bloque; *p* es el valor "
           "de la prueba de Diebold-Mariano con la corrección de Harvey et al. (1997). " + FUENTE)
    + d.titulo_como("Anexo B. Medidas y criterios de XGBoost", "Anexo D. Ejercicio de diagnóstico con información "
                                                                "futura")
    + p("Este ejercicio le da a XGBoost valores reales del día pronosticado, que nadie tiene al pronosticar, para "
        "medir cuánto mejoraría con mejor información (sección 4.1). Se hizo en la validación de 2020-2022, con la "
        "configuración final y el script diagnosticos/oraculo.py. La tabla D1 muestra la mejora del RMSE frente al "
        "ingenuo del día en *h* = 3 y *h* = 7. La demanda y la hidrología futuras agregan menos de tres puntos. Las "
        "ofertas futuras agregan mucho más, pero esa fila es una cota casi circular: el precio de bolsa es la oferta "
        "de la planta marginal, así que conocer las ofertas es casi conocer el precio.")
    + cap_anexo("Tabla D1", "Mejora del RMSE en logaritmo de XGBoost frente al ingenuo del día, en porcentaje, "
                            "según la información futura que recibe, 2020-2022.")
    + tabla(fd, [8.0, 2.4, 2.4])
    + nota(FUENTE))
ultimo = d.bloques()[-1][1]
d.doc = d.doc[:ultimo] + ANEXOS + d.doc[ultimo:]

# =================================================================== Referencias
d.referencias([
    "Bates, J. M., y Granger, C. W. J. (1969). The combination of forecasts. *Operational Research Quarterly*, "
    "*20*(4), 451-468. https://doi.org/10.1057/jors.1969.103",
    "Comisión de Regulación de Energía y Gas [CREG]. (2009). Resolución CREG 051 de 2009, del 7 de mayo de 2009, que "
    "modifica las resoluciones CREG 024 y 025 de 1995. Gestor normativo de la CREG.",
    "Harvey, D., Leybourne, S., y Newbold, P. (1997). Testing the equality of prediction mean squared errors. "
    "*International Journal of Forecasting*, *13*(2), 281-291. https://doi.org/10.1016/S0169-2070(96)00719-4",
])
d.renumerar()

# =================================================================== comprobaciones
B = cuerpo(d)
todo = " ".join(t for _, _, t in B)
for x in ("La LSTM es la mejor", "una sola vez en 2023-2025", "esa misma madrugada", "antes de que XM publicara",
          "cuatro limitaciones", "crisis como la de El Niño de 2024", "lo que más mueve el precio a una semana es",
          "en las mismas condiciones", "Seguir probando los modelos", "tres recomendaciones"):
    assert x not in todo, x
# cada tabla y sección que se cita existe
caps = [t for _, _, t in B if re.match(r"Tabla \d+\.", t)]
assert [int(re.match(r"Tabla (\d+)", t).group(1)) for t in caps] == list(range(1, 22)), [t[:12] for t in caps]
assert caps[17].startswith("Tabla 18. Mejora del RMSE en logaritmo de la semana frente al ingenuo del día, según")
assert caps[18].startswith("Tabla 19. Resultados en el periodo limpio")
assert caps[19].startswith("Tabla 20. Mejora del RMSE en logaritmo frente al ingenuo del día por episodio")
assert caps[20].startswith("Tabla 21. Fracción del ahorro posible")
assert caps[16].startswith("Tabla 17. Resultados de las pruebas con el error en pesos")
for sec in ("3.7 Modelos agregados después de abrir las pruebas", "3.8 Resumen de los modelos",
            "Anexo C. Diseño original de 30 días de XGBoost",
            "Anexo D. Ejercicio de diagnóstico con información futura"):
    assert sum(t == sec for _, _, t in B) == 1, sec
for ref in ("Bates, J. M., y Granger", "Harvey, D., Leybourne", "[CREG]. (2009)"):
    assert todo.count(ref) == 1, ref
print(len(B), "bloques;", len(todo) - len(todo_antes), "caracteres más")
d.guardar(SALIDA)
print("ok", SALIDA)
