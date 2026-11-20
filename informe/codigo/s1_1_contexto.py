"""Sección 1.1 Contexto y justificación.
Uso: python s1_1_contexto.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import Docx, figura, par

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"

P = [
    "En Colombia, la energía eléctrica se transa en el mercado mayorista de dos formas: con contratos bilaterales, "
    "en los que el precio se pacta de antemano, y en la bolsa de energía, donde se liquidan cada hora las diferencias "
    "entre lo que cada agente contrató y lo que realmente generó o consumió (CREG, 1994). El precio de esa transacción "
    "es el precio de bolsa. Cada día, las plantas de generación ofertan un precio para las 24 horas y declaran cuánta "
    "energía pueden entregar en cada una; XM, el operador del mercado, las ordena de la más barata a la más cara y "
    "despacha las necesarias para cubrir la demanda (CREG, 1995). El precio de bolsa de cada hora corresponde, en "
    "esencia, a la oferta de la última planta que hace falta en esa hora.",

    "Entre 2015 y 2025, entre 65% y 86% de la energía generada cada año fue hidráulica (XM S.A. E.S.P., 2026), así que "
    "el precio depende sobre todo del agua: de cuánta hay en los embalses y de cuánta va a llegar. Con poca agua, las "
    "plantas hidráulicas ofertan más caro para conservarla y entran más plantas térmicas, que son más costosas. Por eso "
    "el precio cambia de nivel durante meses y responde a El Niño. En los dos episodios fuertes de la muestra, en "
    "2015-2016 y 2023-2024, el volumen útil de los embalses cayó por debajo de 40% y el precio superó los "
    "1.000 COP/kWh (figura 1).",
]
LEYENDA = ("Precio de bolsa promedio del día (escala logarítmica), volumen útil de los embalses e índice ONI, de 2015 a "
           "octubre de 2026. Las franjas marcan los episodios fuertes de El Niño de 2015-2016 y 2023-2024. Fuente: "
           "elaboración propia con datos de XM y NOAA.")
P2 = [
    "El rango de variación es muy amplio: el precio promedio del día ha ido de 61 COP/kWh, en diciembre de 2016, a "
    "2.499 COP/kWh, el 30 de septiembre de 2024. Además, desde 2023 el precio es más alto y más variable que antes: el "
    "promedio diario fue de 219 COP/kWh entre 2015 y 2021 y de 492 COP/kWh entre 2023 y 2025. Y la situación puede "
    "repetirse pronto: en octubre de 2026 el índice ONI, con el que la NOAA sigue a El Niño, llegó a 2,2 °C, un valor "
    "parecido al de los meses previos a la crisis de 2015-2016 (NOAA Climate Prediction Center, 2026).",

    "Quienes compran o venden energía en la bolsa quedan expuestos a esas variaciones: los comercializadores, que "
    "compran en bolsa la energía que sus contratos no cubren; los generadores, que deciden cuánta agua usar y a qué "
    "precio ofertar, y los grandes consumidores, en especial los que tienen contratos atados al precio de bolsa o "
    "pueden mover su consumo de un día a otro. Para ellos, saber con una semana de anticipación qué días van a ser "
    "caros sirve para decisiones concretas: cuándo comprar energía, cuándo programar un mantenimiento o en qué días "
    "concentrar la producción que más energía consume.",

    "Pronosticar esa semana tiene una dificultad que no siempre se tiene en cuenta: no todos los datos se conocen el "
    "día en que se necesita el pronóstico. XM publica el precio de bolsa con dos o tres días de atraso, de modo que, si "
    "el último precio conocido es el del día t, la semana siguiente corresponde a los días t + 3 a t + 9. Otros datos "
    "se conocen antes, como el despacho programado de cada día, que sale esa misma madrugada, y otros después, como "
    "las ofertas de los generadores, que se publican unos diez días tarde (sección 3.1).",

    "En la Universidad de los Andes hay trabajos previos sobre el pronóstico del precio de bolsa. Cárdenas Paredes "
    "(2005) usó modelos autorregresivos y lógica difusa; Cárdenas Cárdenas (2021) comparó redes neuronales "
    "autorregresivas con modelos ARIMA para el precio promedio diario de la semana siguiente, y González Pérez y Urbano "
    "Buriticá (2022) compararon SARIMAX, Prophet y redes LSTM para el precio horario del día siguiente. Ninguno de los "
    "tres compara sus resultados contra un pronóstico ingenuo, como repetir el último precio conocido, ni prueba si "
    "la diferencia es significativa, dos prácticas que la literatura recomienda al evaluar pronósticos del precio de "
    "la electricidad (Lago et al., 2021). Tampoco aclaran si los datos de entrada estarían publicados al momento de "
    "pronosticar. Sin esa comparación no se sabe si un modelo aporta algo: en 2022, repetir el precio de la misma "
    "hora del día anterior tenía un error porcentual absoluto medio (MAPE) cercano a 11%, menor que el de la mejor "
    "LSTM de González Pérez y Urbano Buriticá (13,89%) y parecido al de su SARIMAX (11,58%).",

    "Este proyecto busca cubrir ese vacío. Pronostica los 168 precios horarios de la semana siguiente usando solo "
    "datos publicados antes del pronóstico, compara tres tipos de modelos (SARIMAX, XGBoost y una red LSTM) en las "
    "mismas condiciones y juzga cada uno contra el pronóstico ingenuo, con un criterio fijado antes de la prueba. "
    "Además, traduce la mejora del pronóstico a una decisión concreta, elegir el día más barato de la semana, para "
    "medir cuánto vale en pesos.",
]
REFS = [
    "Cárdenas Cárdenas, J. E. (2021). *Empleo de modelos predictivos en el precio de bolsa de la energía en Colombia* "
    "[Trabajo de grado de pregrado, Universidad de los Andes].",
    "Cárdenas Paredes, L. E. (2005). *Pronóstico de precios de la bolsa de energía colombiana usando lógica difusa* "
    "[Tesis de maestría, Universidad de los Andes].",
    "Comisión de Regulación de Energía y Gas [CREG]. (1994). *Resolución CREG 055 de 1994*. Gestor normativo de la CREG.",
    "Comisión de Regulación de Energía y Gas [CREG]. (1995). *Resolución CREG 025 de 1995: Código de redes*. "
    "Gestor normativo de la CREG.",
    "González Pérez, L. F., y Urbano Buriticá, S. N. (2022). *Proyección de corto plazo para el precio de bolsa de "
    "energía en el mercado colombiano* [Tesis de maestría, Universidad de los Andes].",
    "Lago, J., Marcjasz, G., De Schutter, B., y Weron, R. (2021). Forecasting day-ahead electricity prices: A review "
    "of state-of-the-art algorithms, best practices and an open-access benchmark. *Applied Energy, 293*, 116983. "
    "https://doi.org/10.1016/j.apenergy.2021.116983",
    "NOAA Climate Prediction Center. (2026). *Oceanic Niño Index (ONI)* [Conjunto de datos]. "
    "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "XM S.A. E.S.P. (2026). *Datos del mercado de energía mayorista* [Conjunto de datos, API consultada con la "
    "librería pydataxm]. https://servapibi.xm.com.co",
]

d = Docx(ENTRADA)
d.agregar_imagen(FIG / "f01_precio_embalses_nino.png", "rIdFig01")
xml = ("".join(par(t) for t in P)
       + figura(FIG / "f01_precio_embalses_nino.png", "rIdFig01", 2001, 15, LEYENDA)
       + "".join(par(t) for t in P2))
d.reemplazar_vacio_tras("1.1 Contexto y justificación", xml)
d.referencias(REFS)
d.guardar(SALIDA)
print("ok", SALIDA)
