"""Escribe la sección 3.3, Diseño del pronóstico: lo que comparten los tres modelos.
Parte del texto que tenía la antigua 3.2 (s3_metodologia.py) y agrega cómo llega SARIMAX a la misma cantidad
que XGBoost y la LSTM, según 5_modelo_sarimax.ipynb (funciones ajustar, pronosticar y una_hora).
Uso: python s3_3_diseno.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, acento, ecuacion, funcion, m, par, paren, sub

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]


def bloque(textos):
    return "".join(par(t) for t in textos)


P_ = lambda a: m("P") + paren(m(a))
EC21 = (sub(m("y"), m("t,h,H")) + m("=") + funcion("log", P_("t+h,H")) + m("−") + funcion("log", P_("t,H"))
        + m(",  h=3,…,9"))
EC22 = (acento(m("P")) + paren(m("t+h,H")) + m("=") + P_("t,H") + m("·")
        + funcion("exp", paren(sub(acento(m("y")), m("t,h,H")))))

S33 = (
    par("Cada pronóstico se hace con los datos hasta el día *t*, el del último precio conocido, y cubre los siete "
        "días siguientes al día *R* = *t* + 2 en que se pronostica, es decir, los días *t* + 3 a *t* + 9 (sección "
        "3.1). Los modelos no pronostican el precio sino su cambio en logaritmo frente a la misma hora *H* del día "
        "*t*,")
    + ecuacion(EC21, 21)
    + par("y el pronóstico en pesos se recupera como")
    + ecuacion(EC22, 22)
    + bloque([
        "Con esta respuesta, el pronóstico ingenuo del día de la ecuación (16) equivale a pronosticar un cambio de "
        "cero, el cambio es estacionario, a diferencia del nivel (sección 3.2), y los tres modelos pronostican la "
        "misma cantidad, lo que permite compararlos directamente.",

        "Cada modelo llega a esa cantidad de una forma distinta (sección 2.3). XGBoost tiene un modelo directo para "
        "cada horizonte, que pronostica el cambio de la ecuación (21); para él, además, pronosticar el cambio es "
        "necesario, porque un árbol no pronostica fuera del rango que vio al entrenarse. La LSTM es una sola red que "
        "pronostica a la vez los cambios de los siete días. SARIMAX, en cambio, modela el logaritmo del precio de cada "
        "hora como una serie diaria que termina en el día *t*, y su diferencia de orden uno cumple el papel de "
        "pronosticar el cambio. Desde el día *t* pronostica nueve pasos de forma recursiva y descarta los dos "
        "primeros, que son los días *t* + 1 y *R*, ya ocurridos pero sin precio publicado. Con los pasos 3 a 9 se "
        "calcula el cambio de la ecuación (21), restando el logaritmo del último precio conocido, y el pronóstico en "
        "pesos sale de la ecuación (22), como en los otros dos modelos.",

        "*Periodos.* Los datos se dividen en cuatro periodos (figura 5a). Con 2015-2019 se eligen las variables y "
        "los órdenes de los modelos. Con 2020-2022 se validan: se eligen los hiperparámetros y se decide entre "
        "versiones de cada modelo. Las pruebas son 2023-2025 y 2026 hasta el 6 de octubre, y cada modelo pasa por "
        "ellas una sola vez, después de quedar fijo. La prueba de 2026 se agregó después de abrir la de 2023-2025 de "
        "XGBoost; para SARIMAX y la LSTM ya estaba prevista antes de sus pruebas. Los datos se parten siempre por "
        "fechas y nunca por filas, porque las 24 horas de un día comparten el estado del sistema.",

        "*Evaluación con origen móvil.* En validación y en prueba, cada modelo se vuelve a entrenar el primer día de "
        "cada mes con todos los datos anteriores, y con ese modelo se pronostica desde cada día del mes (Hyndman y "
        "Athanasopoulos, 2021). En XGBoost y la LSTM, entre los datos de entrenamiento y el primer día pronosticado se "
        "dejan *h* + 1 días, para que ningún objetivo del entrenamiento se traslape con el periodo evaluado (López de "
        "Prado, 2018). SARIMAX no necesita esa separación, porque se estima sobre la serie del precio y no sobre "
        "cambios a varios días: sus coeficientes se reestiman con los precios hasta el último día del mes anterior, y "
        "dentro del mes el modelo se actualiza cada día con los precios hasta *t*, sin reestimar. Los tres modelos se "
        "evalúan en exactamente las mismas filas: 228.984 pronósticos, de los cuales 183.120 son de 2023-2025 y 45.864 "
        "de 2026, y la comparación verifica que coincidan antes de calcular cualquier métrica.",

        "*Criterio.* Un modelo se considera útil en un bloque de horizontes si cumple dos condiciones: reduce al menos "
        "5% el RMSE en logaritmo frente al mejor de los dos ingenuos de la sección 2.4 en ese bloque, y la prueba de "
        "Diebold y Mariano contra ese mismo ingenuo da *p* < 0,05. El umbral de 5% es decisión del autor. El bloque "
        "principal es la semana completa, *h* = 3 a 9, y se reportan también *h* = 3, *h* = 3 a 7 y *h* = 8 a 9. El "
        "criterio se fijó el 1 de noviembre de 2026, antes de abrir la prueba de XGBoost, cuando el alcance era de 30 "
        "días, y se mantuvo igual al reducir el horizonte a una semana.",

        "Para la prueba de Diebold y Mariano, la diferencia de pérdidas *d*_{t} de la ecuación (19) se calcula con el "
        "error cuadrático promedio de cada día de origen *t*, sobre las 24 horas y los horizontes del bloque. Así, las "
        "24 horas de un mismo día, que comparten la mayor parte de su error, cuentan como una sola observación. La "
        "varianza se estima con Newey y West (1987) con *h*_{máx} − 1 + 7 rezagos: *h*_{máx} − 1 por el traslape de "
        "los objetivos, y 7 por la regla automática de Newey y West (1994) con unos 1.750 días.",
    ])
)

REFS = [
    "Newey, W. K., y West, K. D. (1994). Automatic lag selection in covariance matrix estimation. *The Review of "
    "Economic Studies, 61*(4), 631-653. https://doi.org/10.2307/2297912",
]

d = Docx(ENTRADA)
d.reemplazar_vacio_tras("3.3 Diseño del pronóstico", S33)
d.referencias(REFS)
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
