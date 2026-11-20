"""Escribe la sección 1.3 Alcance y limitaciones del informe final.
Las cifras salen del README del repo (horizonte, fechas, criterio) y del análisis de la 1.1 (precios promedio).
Uso: python s1_3_alcance.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, par

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

P = [
    # alcance
    "Este trabajo pronostica el precio de bolsa nacional, hora por hora, para los siete días siguientes: 168 precios "
    "en cada pronóstico. El precio de cada día se publica con dos días de atraso, así que esos siete días quedan entre "
    "tres y nueve días después del último precio conocido (h = 3 a 9). Se usan solo datos públicos, de marzo de 2015 "
    "al 6 de octubre de 2026, de XM, la NOAA, ERA5, el IDEAM y la tasa representativa del mercado (sección 3.1).",

    "Se comparan tres modelos: SARIMAX, XGBoost y una red LSTM. Cada uno se diseña y se ajusta con datos hasta 2022, "
    "y se evalúa una sola vez en dos periodos de prueba: de 2023 a 2025, y 2026 hasta el 6 de octubre. Un modelo se "
    "considera útil si reduce al menos 5% la raíz del error cuadrático medio (RMSE) del logaritmo del precio frente al "
    "mejor de dos pronósticos de referencia, y si la diferencia es significativa según la prueba de Diebold y Mariano "
    "(1995) (sección 3.2).",

    # lo que queda por fuera
    "Varios temas quedan por fuera. Los pronósticos son puntuales: no se construyen intervalos para los tres modelos. "
    "No se modelan las ofertas de cada generador ni el despacho, sino el precio que resulta de ellos. Tampoco se usan "
    "pronósticos de clima o de hidrología hechos por terceros. El valor del pronóstico se mide con una decisión "
    "sencilla, elegir el día más barato de la semana, y no con una estrategia de contratación o de operación de una "
    "planta.",

    # limitaciones
    "El trabajo tiene cuatro limitaciones principales. Primera, el alcance inicial era de 30 días y se redujo a una "
    "semana después de ver la prueba de XGBoost, porque más allá del séptimo día su ventaja dependía del periodo. El "
    "criterio de evaluación se fijó antes de esa prueba, pero la elección del horizonte no. Para SARIMAX y la LSTM, en "
    "cambio, el horizonte de una semana se fijó antes de abrir sus pruebas.",

    "Segunda, la información que más mejoraría el pronóstico, las ofertas de los generadores, se publica unos diez "
    "días tarde, cuando la semana que se quiere pronosticar ya pasó. Ningún modelo la puede usar a tiempo, y eso pone "
    "un límite a la precisión que se puede alcanzar (sección 4.1).",

    "Tercera, los tres modelos no usan exactamente la misma información. XGBoost usa datos que se cortan en el día del "
    "último precio conocido; SARIMAX usa solo el precio y el calendario, y la LSTM recibe cada dato el día en que se "
    "publica, lo que le permite usar datos más recientes, como el despacho programado. La comparación entre modelos "
    "(sección 4.2) tiene en cuenta esta diferencia.",

    "Cuarta, en el periodo de prueba los precios fueron mucho más altos que en el de entrenamiento: el promedio diario "
    "pasó de 219 COP/kWh entre 2015 y 2021 a 492 COP/kWh entre 2023 y 2025, un periodo que incluye el fenómeno de El "
    "Niño de 2023-2024. Los resultados muestran cómo se comportan los modelos en ese contexto y podrían ser distintos "
    "en otro.",
]

REFS = [
    "Diebold, F. X., y Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic "
    "Statistics, 13*(3), 253-263. https://doi.org/10.1080/07350015.1995.10524599",
]

d = Docx(ENTRADA)
d.reemplazar_vacio_tras("1.3 Alcance y limitaciones", "".join(par(t) for t in P))
d.referencias(REFS)
d.guardar(SALIDA)
print("ok", SALIDA)
