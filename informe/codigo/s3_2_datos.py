"""Arma la sección 3.2, Descarga, limpieza y análisis de los datos, y deja los títulos del resto del capítulo III.
Pasa a la 3.2 los dos párrafos de la 3.1 que hablaban del panel y de las variables base.
Las cifras salen de resumen_modelos_hallazgos/0_datos_limpieza_y_estructura.ipynb y 0b_datos_analisis.ipynb,
de docs/DOCUMENTACION.md y de fig_datos.py, que hace las figuras.
Uso: python s3_2_datos.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

from docx_final import Docx, figura, leyenda, par, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'
sin_formato = lambda t: re.sub(r"\*+", "", t)


def fuente(texto):
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>')


def bloque(textos):
    return "".join(par(t) for t in textos)


# ---------------------------------------------------------------- lo que cambia en la 3.1
FUENTES_VIEJO = ("De XM, el operador del sistema y administrador del mercado, se descargaron 41 series con la librería "
                 "pydataxm, que consulta su API y la de SIMEM (XM, 2026)")
FUENTES_NUEVO = ("De XM, el operador del sistema y administrador del mercado, se descargaron 72 series, 65 de XM y 7 de "
                 "SIMEM, con la librería pydataxm, que consulta las dos API (XM, 2026)")
PANEL_31 = ("Con estas fuentes se armó un panel horario de 103.200 filas, 24 por día, del 1 de enero de 2015 al 9 de "
            "octubre de 2026, que incluye el despacho programado de los días siguientes al último precio. El precio va "
            "hasta el 6 de octubre de 2026. Se sigue la convención de XM, en la que la hora 1 va de las 0:00 a la 1:00. "
            "Cuando una serie está por planta o por hora y se necesita para todo el sistema o para el día, las energías "
            "se suman, las capacidades se suman entre plantas y se promedian entre horas, y los precios se promedian. Los "
            "datos que faltan de forma aislada se llenan con la misma hora del día anterior, hasta tres días seguidos; "
            "los eventos sin registro en XM, como las importaciones de un día sin intercambios, se toman como cero.")
VARIABLES_31 = ("A partir del panel se construyeron 134 variables base: el logaritmo del precio, 44 variables horarias y "
                "89 diarias. Cada una sigue una regla fija según su tipo, para que su escala no dependa del nivel del "
                "sistema (decisión del autor): las cantidades se expresan como fracción de la demanda o de la "
                "generación, los precios y las ofertas en logaritmo, y las cantidades diarias se dividen por la demanda "
                "promedio de los últimos siete días. Se agregaron además cuatro variables que resumen el estado del "
                "sistema: la distancia entre el precio y el precio de escasez, la presión de la demanda sobre el agua "
                "disponible en cada hora, los días que alcanzaría el agua embalsada y el error del costo marginal del "
                "despacho programado frente al precio.")

# ---------------------------------------------------------------- 3.2
TABLA_FALTANTES = tabla([
    ["Tipo", "Series", "Qué ocurre", "Tratamiento"],
    ["Completa", "42", "No le falta ningún día", "Ninguno"],
    ["Eventos", "10", "XM no publica fila los días en que el evento no ocurre, como un día sin vertimientos o sin "
     "importaciones", "El día sin dato se toma como cero"],
    ["Mensual", "6", "Un valor por mes, vigente hasta que sale el siguiente", "Se repite en cada día del mes"],
    ["Huecos sueltos", "6", "De uno a siete días sin dato", "El valor de la misma hora del día anterior, hasta tres "
     "días seguidos"],
    ["Empieza tarde", "8", "La serie empieza entre 2017 y 2024", "No se usa"],
], [2.8, 1.5, 6.0, 5.4])

TABLA_PRUEBAS = tabla([
    ["Prueba", "Hipótesis nula", "Nivel", "Cambio diario"],
    ["Dickey-Fuller aumentada", "La serie tiene raíz unitaria", "7", "24"],
    ["KPSS", "La serie es estacionaria", "24", "0"],
], [4.6, 5.0, 2.6, 3.2])

S32 = (
    bloque([
        "*Descarga.* Las series de XM y SIMEM se descargaron con la librería pydataxm, en tramos de 30 días, y las de "
        "las demás fuentes con sus servicios públicos de datos (tabla 2). Los códigos de las métricas de XM se "
        "comprobaron uno por uno: se pidieron a la API días que ya estaban descargados y se verificó que los valores "
        "coincidieran. Al actualizar los datos se vuelve a pedir el último mes, porque XM corrige las liquidaciones "
        "provisionales durante varias semanas. El listado de plantas de PARATEC, con la tecnología y el combustible de "
        "cada una, se descargó a mano, porque el de la API solo trae las plantas activas: sin las retiradas se "
        "perderían 34 plantas, entre ellas Jepírachi, que fue la única planta eólica del país hasta 2023.",

        "*Cobertura y faltantes.* Después de la descarga se revisó cada serie: desde qué día y hasta qué día llega, y "
        "cuántos días le faltan. Los faltantes no son todos iguales, y cada tipo se trató de una forma distinta (tabla "
        "3). Para las series de eventos se comprobó el supuesto: en once años, ninguna de ellas vale cero en un día "
        "publicado, así que un día sin dato es un día en que el evento no ocurrió. Los huecos sueltos se llenan con un "
        "valor anterior, que no trae información del futuro. Las series que empiezan tarde, como las variantes del "
        "precio de escasez, no se usan: llenarlas con la media o con valores cercanos equivaldría a inventarles una "
        "historia que no existió (decisión del autor).",
    ])
    + leyenda("Tabla", "Tipos de faltantes en las 72 series de XM y SIMEM y su tratamiento.", ppr=ANTES_TABLA)
    + TABLA_FALTANTES
    + fuente("Fuente: elaboración propia con la revisión de la descarga del 9 de octubre de 2026.")
    + bloque([
        "*Paneles.* Con las series limpias se armó primero un panel diario, con 4.300 días del 1 de enero de 2015 al 9 "
        "de octubre de 2026, y luego un panel horario de 103.200 filas, 24 por día, que incluye el despacho programado "
        "de los días siguientes al último precio (figura 6). El precio va hasta el 6 de octubre de 2026. Se sigue la "
        "convención de XM, en la que la hora 1 va de las 0:00 a la 1:00. Cuando una serie está por planta o por hora y "
        "se necesita para todo el sistema o para el día, las energías se suman, las capacidades se suman entre plantas "
        "y se promedian entre horas, y los precios se promedian. El ONI de un mes se corre dos meses, porque se publica "
        "cuando ya se conoce el mes siguiente, que cierra su promedio de tres meses. La demanda de los últimos días "
        "llega incompleta mientras XM recibe las mediciones, así que un día cuya demanda es menos de la mitad de la "
        "mediana de los 28 días anteriores se deja vacío; en toda la muestra solo ocurrió el 5 y el 6 de octubre de "
        "2026. En el panel horario se corrigieron además dos problemas de SIMEM: su hora empieza una hora antes que la "
        "de XM, y en 70 días traía el total nacional como si fuera un mercado más.",

        "*Variables base.* A partir del panel se construyeron 134 variables base: el logaritmo del precio, 44 "
        "variables horarias y 89 diarias. Cada una sigue una regla fija según su tipo, para que su escala no dependa "
        "del nivel del sistema (decisión del autor): las cantidades se expresan como fracción de la demanda o de la "
        "generación, los precios y las ofertas en logaritmo, y las cantidades diarias se dividen por la demanda "
        "promedio de los últimos siete días. Quedaron fuera las variables con más de 1% de días sin dato desde marzo de "
        "2015, como el volumen del embalse de El Quimbo, y las que no varían. Se agregaron además cuatro variables que "
        "resumen el estado del sistema: la distancia entre el precio y el precio de escasez, la presión de la demanda "
        "sobre el agua disponible en cada hora, los días que alcanzaría el agua embalsada y el error del costo marginal "
        "del despacho programado frente al precio. Cada fila trae también el calendario del día *t* y del día "
        "pronosticado: el día de la semana y si es festivo.",
    ])
    + figura(FIG / "f14_flujo_datos.png", "rIdFig14", 2014, 15,
             "Flujo de los datos, de la descarga a los paneles que usan los modelos. Los números son los pasos del "
             "repositorio. Fuente: elaboración propia.")
    + bloque([
        "*Análisis exploratorio.* Antes de construir los modelos se analizaron el precio y su relación con las demás "
        "variables. La descripción de los ciclos usa toda la muestra; los análisis que sirvieron para tomar decisiones "
        "usan solo los datos de selección, 2015-2019, o los de selección y validación, 2015-2022.",

        "El precio tiene los tres ciclos descritos en la sección 2.1 (figura 7). Para medirlos sin el efecto del nivel "
        "de cada año, cada hora se comparó con el promedio de su día, cada día con la media de los siete días centrada "
        "en él y cada mes con la media de los 365 días centrada en él, siempre en logaritmo. La hora 20, de 7 a 8 de la "
        "noche, es la más cara: en la mediana está 14,5% por encima del promedio de su día, y la hora 4, la más barata, "
        "11,6% por debajo. El domingo es 8,6% más barato que su semana y un festivo entre semana, 5,7%. En el año, el "
        "precio es más alto de diciembre a marzo, la temporada seca, y más bajo de mayo a agosto.",
    ])
    + figura(FIG / "f15_ciclos_precio.png", "rIdFig15", 2015, 15,
             "Ciclos del precio de bolsa, de marzo de 2015 a octubre de 2026. a) Cada hora frente al promedio de su "
             "día. b) Cada día frente a la media de siete días centrada en él; F es un festivo entre semana. c) Cada "
             "mes frente a la media de 365 días centrada en él, en la mediana. Fuente: elaboración propia con datos de "
             "XM (2026).")
    + bloque([
        "Con los datos de 2015-2019 se revisó si el logaritmo del precio de cada hora es estacionario, con dos pruebas "
        "de hipótesis opuestas: la de Dickey-Fuller aumentada, cuya hipótesis nula es que la serie tiene raíz unitaria "
        "(Dickey y Fuller, 1979), y la KPSS, cuya hipótesis nula es que la serie es estacionaria (Kwiatkowski et al., "
        "1992). En el nivel, la primera rechaza la raíz unitaria al 5% solo en 7 de las 24 horas, y la segunda rechaza "
        "la estacionariedad en todas. En el cambio diario ocurre lo contrario: la primera rechaza en las 24 horas y la "
        "segunda en ninguna (tabla 4). El nivel se comporta como una serie no estacionaria y su cambio como una "
        "estacionaria, lo que respalda pronosticar el cambio y diferenciar una vez en SARIMAX.",
    ])
    + leyenda("Tabla", "Pruebas de estacionariedad del logaritmo del precio de cada hora, 2015-2019: número de "
              "horas, de 24, en que se rechaza la hipótesis nula al 5%.", ppr=ANTES_TABLA)
    + TABLA_PRUEBAS
    + fuente("Nota: la KPSS de statsmodels reporta valores p entre 0,01 y 0,10. Fuente: elaboración propia con datos "
             "de XM (2026).")
    + bloque([
        "La autocorrelación del cambio diario, promediada sobre las 24 horas, muestra qué tanto se parece cada día a "
        "los anteriores (figura 8; Hyndman y Athanasopoulos, 2021). En el rezago 1 es negativa, de −0,28: un salto del "
        "precio tiende a devolverse al día siguiente. En los rezagos 7, 14, 21 y 28 es positiva, entre 0,08 y 0,09, "
        "por fuera de la banda de 95% de una serie sin autocorrelación, que va de −0,047 a 0,047. El precio de un día "
        "se parece al del mismo día de las semanas anteriores; por eso SARIMAX tiene un periodo estacional de siete "
        "días, y entre las columnas candidatas de XGBoost están los rezagos del precio de 7, 14, 21 y 28 días.",
    ])
    + figura(FIG / "f16_autocorrelacion.png", "rIdFig16", 2016, 15,
             "Autocorrelación y autocorrelación parcial del cambio diario del logaritmo del precio, promedio de las 24 "
             "horas, 2015-2019. Los rezagos múltiplos de siete van en negro; la franja gris es la banda de 95% de una "
             "serie sin autocorrelación. Fuente: elaboración propia con datos de XM (2026).")
    + bloque([
        "Lo que más pesa en el pronóstico a una semana es el nivel del día. El cambio en logaritmo que se pronostica "
        "(sección 3.3) se puede partir en el cambio del promedio de las 24 horas y el cambio de la forma del día. Entre 2015 y 2022, el "
        "promedio del día explica 56% del error cuadrático medio del ingenuo del día en *h* = 3 y 75% en *h* = 9, y "
        "ese error, el RMSE en logaritmo, pasa de 0,26 a 0,35. El ingenuo semanal tiene más error en todos los "
        "horizontes salvo en *h* = 7, donde los dos pronostican lo mismo.",

        "Por último, con promedios mensuales de 2015 a 2022, la correlación de Spearman entre el logaritmo del precio "
        "y los aportes hídricos, como porcentaje de su media histórica, es de −0,55 en el mismo mes y de −0,57 con los "
        "del mes anterior, y desaparece hacia los seis meses. La de la anomalía de temperatura de la región Niño 3.4, "
        "en cambio, crece con la distancia: es de 0,26 en el mismo mes y de 0,52 seis meses antes. A pocos días, lo "
        "que más se relaciona con el cambio del precio es el despacho programado: la diferencia entre el costo "
        "marginal programado del día *R* y el último precio conocido tiene una correlación de Spearman de 0,60 con el "
        "cambio a tres días, mientras que ninguna variable hidrológica pasa de 0,2 en valor absoluto. Las variables "
        "de XGBoost y de la LSTM se eligieron con procedimientos propios (secciones 3.5 y 3.6), pero estas "
        "relaciones ayudan a leer lo que eligieron.",
    ])
)

TITULOS = ["3.3 Diseño del pronóstico", "3.4 SARIMAX", "3.5 XGBoost", "3.6 LSTM", "3.7 Resumen de los modelos"]

d = Docx(ENTRADA)
assert "f14_flujo_datos" not in d.doc, "la 3.2 nueva ya está"
for f in ["f14_flujo_datos", "f15_ciclos_precio", "f16_autocorrelacion"]:
    d.agregar_imagen(FIG / f"{f}.png", "rIdFig" + f[1:3])

# la 3.1 debe estar como la dejó s3_metodologia.py
textos = [d.texto(p) for _, _, p in d.parrafos()]
for t in (PANEL_31, VARIABLES_31):
    assert t in textos, f"cambió en Word: {t[:60]}"
d.cambiar_texto(FUENTES_VIEJO, FUENTES_NUEVO)
d.borrar_parrafo("Con estas fuentes se armó un panel horario")
d.borrar_parrafo("A partir del panel se construyeron 134 variables base")
d.cambiar_texto("diez días después (figura 3).", "diez días después (figura 5).")

# el título de la 3.2 cambia de nombre y su contenido va justo después
nuevo = d.titulo_como("3.2 Diseño del pronóstico", "3.2 Descarga, limpieza y análisis de los datos")
i = d.buscar_titulo("3.2 Diseño del pronóstico")
a, b, _ = d.parrafos()[i]
vacio = "<w:p/>"
resto = "".join(d.titulo_como("3.2 Diseño del pronóstico", t) + vacio for t in TITULOS)
d.doc = d.doc[:a] + nuevo + S32 + resto + d.doc[b:]

d.referencias([
    "Dickey, D. A., y Fuller, W. A. (1979). Distribution of the estimators for autoregressive time series with a "
    "unit root. *Journal of the American Statistical Association, 74*(366), 427-431. "
    "https://doi.org/10.1080/01621459.1979.10482531",
])
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
