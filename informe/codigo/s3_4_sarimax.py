"""Escribe la sección 3.4, SARIMAX: cómo se construyó el modelo, con cada prueba estadística y su fórmula.
Las cifras salen de 5_modelo_sarimax.ipynb y de resultados/modelo_sarimax/ (RESULTADOS.md y los etapa*.csv).
Las del preblanqueo sin filtrar y las de los residuos salen de fig_sarimax_datos.R, y las figuras de fig_sarimax.py.
Uso: python s3_4_sarimax.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

from docx_final import (Docx, acento, barra, ecuacion, figura, frac, funcion, leyenda, m, mr, par, paren, raiz,
                        sub, suma, sup, tabla)

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'
FUENTE_XM = "Fuente: elaboración propia con datos de XM (2026)."


def fuente(texto):
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>')


def bloque(textos):
    return "".join(par(t) for t in textos)


# ----------------------------------------------------------------------------- ecuaciones
s = lambda base, i: sub(m(base), m(i))
D1D7 = s("Δ", "1") + s("Δ", "7")
EC23 = (D1D7 + s("y", "t") + m("=") + s("β", "1") + s("Δ", "7") + s("y", "t−1") + m("+") + s("β", "2") + s("Δ", "1")
        + s("y", "t−7") + m("+") + suma(m("i=1"), m("k"), s("α", "i") + D1D7 + s("y", "t−i")) + m("+") + s("ε", "t"))
EC24 = (mr("KPSS") + m("=") + frac(m("1"), sup(m("T"), m("2")) + sup(acento(m("σ")), m("2")))
        + suma(m("t=1"), m("T"), sup(s("S", "t"), m("2"))) + m(",   ") + s("S", "t") + m("=")
        + suma(m("j=1"), m("t"), sub(acento(m("e")), m("j"))))
EC25 = (mr("AICc") + m("=−2") + funcion("log", acento(m("L"))) + m("+2k+")
        + frac(m("2k") + paren(m("k+1")), m("T−k−1")))
PI = sub(acento(m("π")), m("H")) + paren(m("B"))
EC26 = (PI + m("=") + frac(acento(m("φ")) + paren(m("B")) + acento(m("Φ")) + paren(sup(m("B"), m("7"))) + paren(m("1−B")),
                           acento(m("θ")) + paren(m("B")) + acento(m("Θ")) + paren(sup(m("B"), m("7")))))
EC27 = (s("u", "t") + m("=") + PI + funcion("log", m("P") + paren(m("t,H"))) + m(",   ") + s("v", "t") + m("=") + PI
        + s("x", "t−9,H"))
U, V = paren(s("u", "t") + m("−") + barra(m("u"))), paren(s("v", "t") + m("−") + barra(m("v")))
EC28 = (s("r", "H") + m("=") + frac(suma(m("t"), "", U + V),
                                    raiz(suma(m("t"), "", sup(U, m("2"))) + suma(m("t"), "", sup(V, m("2"))))))
EC29 = (paren(s("r", "H"), "|", "|") + m(">") + frac(s("z", "1−α/(2m)"), raiz(m("n"))) + m("=")
        + frac(m("3,53"), raiz(m("1.767"))) + m("=0,084"))
B_ = acento(m("β"))
EC30 = (m("t=") + frac(B_, mr("ee") + paren(B_)) + m(",   p=2 ") + mr("Pr") + paren(m("Z>") + paren(m("t"), "|", "|")))
EC31 = (m("Q=T") + paren(m("T+2")) + suma(m("k=1"), m("14"), frac(sup(sub(acento(m("ρ")), m("k")), m("2")), m("T−k"))))
EC32 = (funcion("log", m("P") + paren(m("t,H"))) + m("=") + s("β", "H") + s("F", "t") + m("+") + s("η", "t,H"))
EC33 = (paren(m("1−") + s("φ", "1") + m("B")) + paren(m("1−B")) + s("η", "t,H") + m("=")
        + paren(m("1+") + s("θ", "1") + m("B+") + s("θ", "2") + sup(m("B"), m("2")))
        + paren(m("1+") + s("Θ", "1") + sup(m("B"), m("7")) + m("+") + s("Θ", "2") + sup(m("B"), m("14")))
        + s("ε", "t,H"))

# ----------------------------------------------------------------------------- tablas
TABLA_ORDENES = tabla([
    ["Orden", "Horas"],
    ["(1,1,2)(0,0,2)_{7}", "9, 10, 14, 16 y 19"],
    ["(1,1,2)(0,0,1)_{7}", "1, 3 y 4"],
    ["(2,1,1)(0,0,2)_{7}", "7, 8 y 15"],
    ["(1,1,3)(0,0,2)_{7}", "13, 17 y 18"],
    ["(1,1,1)(0,0,0)_{7}", "2, 5 y 21"],
    ["Otros siete órdenes, uno por hora", "6, 11, 12, 20, 22, 23 y 24"],
], [6.0, 6.0])

TABLA_VARIABLES = tabla([
    ["Paso", "Datos", "Salen", "Quedan"],
    ["Variables base distintas del precio", "", "", "133"],
    ["Niveles que siguen al dólar", "", "2", "131"],
    ["Con vacíos", "2015-2019", "0", "131"],
    ["Casi constantes", "2015-2019", "1", "130"],
    ["Inestables", "2015-2019", "8", "122"],
    ["Preblanqueo, al menos 12 de 24 horas", "2015-2019", "121", "1"],
    ["Selección hacia adelante con el AICc", "2015-2019", "0", "1"],
    ["Prueba *t*, al menos 12 de 24 horas", "2015-2019", "0", "1"],
    ["Validación con Diebold-Mariano", "2020-2022", "1", "0"],
], [7.6, 2.6, 1.7, 1.7])

TABLA_VALIDACION = tabla([
    ["Versión", "RMSE en logaritmo", "Diebold-Mariano *p* contra la anterior", "Se mantiene"],
    ["Un solo orden, (1,1,2)(0,0,2)_{7}", "0,2805", "", "Sí"],
    ["Un orden por hora", "0,2806", "0,865", "No"],
    ["Un solo orden con la holgura", "0,2806", "0,970", "No"],
    ["Ingenuo del día (referencia)", "0,2943", "", ""],
], [5.6, 2.8, 4.2, 2.2])

# ----------------------------------------------------------------------------- texto
S34 = (
    bloque([
        "SARIMAX es el modelo lineal de referencia del trabajo. Su construcción tuvo cuatro etapas, todas con datos "
        "hasta 2022 (figura 9): elegir el orden del modelo de cada hora, elegir las variables explicativas, comparar "
        "versiones del modelo en la validación y fijar el modelo final. Todo el proceso está en el notebook "
        "5_modelo_sarimax.ipynb, escrito en R con el paquete forecast (Hyndman y Khandakar, 2008).",
    ])
    + figura(FIG / "f17_sarimax_construccion.png", "rIdFig17", 2017, 15,
             "Etapas de la construcción de SARIMAX. Fuente: elaboración propia.")
    + bloque([
        "*El modelo y sus parámetros.* Como se vio en la sección 2.3, un SARIMAX es una regresión cuyos errores siguen "
        "un modelo SARIMA (ecuaciones 1 y 2). Se escribe SARIMAX(*p*, *d*, *q*)(*P*, *D*, *Q*)_{s}. El orden *d* es "
        "cuántas veces se diferencia la serie: con *d* = 0 se modela el nivel y con *d* = 1, el cambio de un día al "
        "siguiente. El orden *p* es cuántos valores pasados de la serie entran en la parte autorregresiva, y *q*, "
        "cuántos errores de pronóstico pasados entran en la parte de media móvil. *P*, *D* y *Q* cumplen el mismo papel "
        "con rezagos de *s* días, el periodo del ciclo estacional.",

        "En este trabajo hay un modelo por cada hora del día: 24 modelos, cada uno sobre la serie diaria del logaritmo "
        "del precio de su hora, con *s* = 7 por el ciclo semanal de la sección 3.2. Todos llevan como variable "
        "explicativa un indicador de si el día es festivo, que se conoce con anticipación para cualquier día "
        "pronosticado. El día de la semana no se incluye, porque lo recoge la parte estacional. Cada modelo pronostica "
        "de forma recursiva desde el día *t* (sección 3.3).",

        "*Órdenes de cada hora.* Con los datos de 2015-2019, la función auto.arima eligió el orden de cada hora en "
        "tres pasos: una prueba decide *D*, otra decide *d* y un criterio de información elige *p*, *q*, *P* y *Q* "
        "(Hyndman y Khandakar, 2008).",

        "Primero, la prueba OCSB (Osborn et al., 1988) decide si hace falta una diferencia estacional, es decir, si el "
        "precio de un día debe modelarse como cambio frente al mismo día de la semana anterior. Con Δ_{1} = 1 − *B* y "
        "Δ_{7} = 1 − *B*^{7}, estima la regresión",
    ])
    + ecuacion(EC23, 23)
    + bloque([
        "donde *y*_{t} es el logaritmo del precio de la hora, β_{1}, β_{2} y α_{i} son coeficientes y los *k* rezagos "
        "de la suma recogen la autocorrelación que queda. Si la serie tiene una raíz unitaria estacional, su cambio "
        "frente a la semana anterior se comporta como una caminata aleatoria, el nivel de hace una semana no ayuda a "
        "explicarlo y β_{2} = 0. La prueba compara el estadístico *t* de β_{2} con un valor crítico: si es "
        "suficientemente negativo, se rechaza la raíz unitaria estacional y *D* = 0.",

        "Después, la prueba KPSS (Kwiatkowski et al., 1992) decide *d*. A la serie se le resta su media, "
        "ê_{t} = *y*_{t} − ȳ, y esos residuos se acumulan:",
    ])
    + ecuacion(EC24, 24)
    + bloque([
        "donde *T* es el número de días y σ̂^{2} es un estimado de la varianza de largo plazo de los residuos. Si la "
        "serie es estacionaria, vuelve siempre a su media, los residuos se compensan entre sí y la suma acumulada "
        "*S*_{t} se queda cerca de cero. Si tiene raíz unitaria, la serie se aleja de su media por periodos largos, "
        "*S*_{t} crece y el estadístico también. La hipótesis nula es que la serie es estacionaria; si se rechaza al "
        "5%, la serie se diferencia una vez y la prueba se repite, hasta *d* = 1 como máximo.",

        "Por último, el criterio AICc (Hurvich y Tsai, 1989) elige *p*, *q*, *P* y *Q* entre los modelos con hasta 5 "
        "rezagos en la parte regular y hasta 2 en la estacional:",
    ])
    + ecuacion(EC25, 25)
    + bloque([
        "donde L̂ es la verosimilitud del modelo estimado y *k* el número de parámetros. El primer término premia el "
        "ajuste y los otros dos castigan cada parámetro adicional; el tercero es la corrección para muestras pequeñas, "
        "que tiende a cero cuando *T* crece. Se elige el modelo con el menor AICc. La búsqueda es por pasos: parte de "
        "unos modelos sencillos y cambia un orden a la vez mientras el AICc baje (Hyndman y Khandakar, 2008). Como "
        "diferenciar cambia la serie que se ajusta, el AICc solo compara modelos con los mismos *d* y *D*; por eso "
        "estos se fijan antes.",

        "Las dos pruebas dieron *D* = 0 y *d* = 1 en las 24 horas, lo mismo que mostraron las pruebas de "
        "estacionariedad de la sección 3.2: el nivel del precio no es estacionario y su cambio sí. El AICc, en cambio, "
        "eligió doce órdenes distintos (tabla 5). El más frecuente, (1,1,2)(0,0,2)_{7}, salió en cinco horas. Los "
        "órdenes se eligieron antes que las variables explicativas, porque el primer filtro de variables usa el modelo "
        "de cada hora.",
    ])
    + leyenda("Tabla", "Órdenes elegidos por el AICc en cada hora, 2015-2019.", ppr=ANTES_TABLA)
    + TABLA_ORDENES
    + fuente(FUENTE_XM)
    + bloque([
        "*Variables candidatas.* Las candidatas fueron las 133 variables base distintas del precio (sección 3.2). Antes "
        "de los filtros estadísticos se quitaron las que no sirven en un modelo estimado con años anteriores, con las "
        "mismas reglas de limpieza que se usaron para XGBoost (sección 3.5). Primero salieron los 2 niveles que siguen "
        "al dólar, el cargo por confiabilidad y la TRM, y quedaron 131. No había variables con vacíos en 2015-2019. "
        "Luego salió 1 variable casi constante, con un mismo valor en 99% o más de los días, y quedaron 130. Por "
        "último salieron 8 inestables, con más de 25% de sus valores de 2018-2019 fuera del rango entre los "
        "percentiles 1 y 99 de 2015-2017, como el número de plantas activas, el precio de los contratos o el número de "
        "ríos con aportes. Quedaron 122.",

        "Como se pronostica hasta nueve días adelante, cada variable entra con nueve días de rezago: el valor del día "
        "*t* + *h* − 9 ya se conoce el día *t* para cualquier día de la semana pronosticada (decisión del autor).",

        "*Primer filtro: preblanqueo.* El precio y muchas variables del sistema tienen ciclos semanales y anuales y "
        "cambian lentamente. Dos series así pueden parecer correlacionadas aunque una no ayude a pronosticar la otra, "
        "solo porque las dos suben y bajan con la misma inercia. El preblanqueo quita esa parte común antes de medir la "
        "relación (Box et al., 2015). Para cada hora *H*, el modelo de la tabla 5, ya estimado, se usa al revés: como "
        "un filtro que convierte la serie en sus errores de pronóstico a un paso. Ese filtro es",
    ])
    + ecuacion(EC26, 26)
    + par("donde los polinomios son los de la ecuación (1) con los coeficientes estimados para esa hora. Con él se "
          "filtran el precio y la variable candidata *x*, con los mismos coeficientes:")
    + ecuacion(EC27, 27)
    + par("Los residuos *u*_{t} son la parte del precio que su propio pasado no explica, y *v*_{t} es lo que queda de la "
          "variable después de pasarla por el mismo filtro. Ya no tienen la inercia ni los ciclos del precio, así que "
          "su correlación,")
    + ecuacion(EC28, 28)
    + bloque([
        "mide si la variable de nueve días antes dice algo sobre el precio que el precio no supiera ya. Si no hay "
        "relación, *r*_{H} se distribuye aproximadamente normal, con media cero y desviación 1/√*n* (Box et al., "
        "2015), donde *n* = 1.767 es el número de días entre el 1 de marzo de 2015 y el 31 de diciembre de 2019. Al 5%, "
        "la correlación sería significativa si pasa de 1,96/√*n* = 0,047 en valor absoluto. Pero se prueban 122 "
        "variables, y con tantas pruebas algunas pasarían por azar: unas seis de cada 122, aunque ninguna sirviera. La "
        "corrección de Bonferroni (Dunn, 1961) reparte el nivel α = 0,05 entre las *m* = 122 pruebas, y la regla "
        "queda",
    ])
    + ecuacion(EC29, 29)
    + bloque([
        "donde *z* es el cuantil de la normal estándar. Una variable pasa el filtro si cumple esta regla en al menos 12 "
        "de las 24 horas. Filtrar la variable con el modelo del precio y no con uno propio es una simplificación del "
        "autor, para no ajustar un modelo por cada variable y cada hora.",

        "La figura 10a muestra el efecto del filtro. Sin preblanqueo, es decir, entre los niveles de las dos series, "
        "la correlación media en valor absoluto de las 122 variables con el precio es de 0,34, y 80% de los pares de "
        "variable y hora pasan el umbral. Con preblanqueo, la correlación media baja a 0,025 y solo 2% de los pares lo "
        "pasan: casi toda la relación aparente venía de la inercia común. De las 122 variables, 106 no fueron "
        "significativas en ninguna hora, 16 lo fueron en al menos una, 7 en cuatro o más y 4 en seis o más (figura "
        "10b). Solo una llegó a 12: la holgura de la curva de oferta, que es la capacidad ofertada menos la demanda, "
        "como fracción de la demanda. Su correlación bajó de 0,30 a 0,07 con el filtro, y aun así superó el umbral en "
        "exactamente la mitad de las horas. Las que más se acercaron fueron el precio de oferta de la planta marginal, "
        "en 7 horas, y la capacidad ofertada por debajo de 500 COP/kWh y las obligaciones de energía firme, en 6 horas "
        "cada una.",
    ])
    + figura(FIG / "f18_sarimax_preblanqueo.png", "rIdFig18", 2018, 15,
             "Preblanqueo de las 122 variables candidatas, 2015-2019. a) Correlación de cada variable, con nueve días "
             "de rezago, con el logaritmo del precio, en valor absoluto y promediada sobre las 24 horas, antes y "
             "después del filtro; la línea negra es la holgura de la oferta. b) Número de horas en que la correlación "
             "preblanqueada supera el umbral de la ecuación (29), para las 16 variables que lo superan en alguna "
             "hora. " + FUENTE_XM)
    + bloque([
        "*Segundo filtro: selección hacia adelante con el AICc.* Partiendo del modelo con solo el festivo, en cada paso "
        "se agrega la variable que más baja el AICc de la ecuación (25), sumado en las 24 horas, y el proceso para "
        "cuando ninguna lo baja o cuando hay seis variables. Como los órdenes no cambian, el AICc compara modelos "
        "estimados sobre los mismos datos. Con una sola variable disponible, la pregunta era si entraba o no: la "
        "holgura bajó el AICc total de −23.215 a −23.462, así que entró.",

        "*Tercer filtro: prueba t.* En el modelo de cada hora con la holgura, se prueba si su coeficiente es distinto "
        "de cero con",
    ])
    + ecuacion(EC30, 30)
    + bloque([
        "donde ee(β̂) es el error estándar estimado del coeficiente y *Z* es una normal estándar. Un valor *p* pequeño "
        "indica que el coeficiente está demasiado lejos de cero para deberse al azar. La variable sale si no tiene "
        "*p* < 0,05 en al menos 12 horas. La holgura fue significativa en 17 de las 24, con un *p* mediano de 0,006, "
        "así que se mantuvo.",

        "La tabla 6 resume cuántas variables quedaron en cada paso. Dentro de 2015-2019, la holgura pasó los tres "
        "filtros. Pero los tres miden el ajuste en los mismos datos con que se estima el modelo, y lo que importa es si "
        "mejora el pronóstico en años que el modelo no vio. Eso lo decide la validación.",
    ])
    + leyenda("Tabla", "Variables que quedan en cada paso de la selección de SARIMAX.", ppr=ANTES_TABLA)
    + TABLA_VARIABLES
    + fuente(FUENTE_XM)
    + bloque([
        "*Validación.* En 2020-2022 se compararon tres versiones, de la más simple a la más compleja, con origen móvil "
        "y reestimación mensual (sección 3.3), en la semana completa, *h* = 3 a 9: un solo orden para las 24 horas, el "
        "más frecuente de la tabla 5; el orden propio de cada hora, y la mejor de las dos anteriores con la holgura. "
        "Una versión más compleja solo reemplazaba a la anterior si le ganaba en la prueba de Diebold y Mariano de las "
        "ecuaciones (19) y (20) con *p* < 0,05, es decir, si la diferencia entre sus errores era tan sistemática que no "
        "podía atribuirse al azar.",
    ])
    + leyenda("Tabla", "Validación de las versiones de SARIMAX, 2020-2022, *h* = 3 a 9.", ppr=ANTES_TABLA)
    + TABLA_VALIDACION
    + fuente(FUENTE_XM)
    + bloque([
        "Dar a cada hora su propio orden no mejoró el pronóstico: el RMSE quedó igual a cuatro decimales y la prueba de "
        "Diebold y Mariano dio *p* = 0,865. Los doce órdenes de la tabla 5 se diferencian en detalles que el AICc "
        "premia dentro de la muestra, pero que no cambian lo que el modelo pronostica a una semana. La holgura tampoco "
        "mejoró el pronóstico (*p* = 0,970), aunque había pasado los tres filtros dentro de la muestra: ayuda un poco "
        "en *h* = 3 y 4, pierde en *h* = 6 a 8 y el total queda igual (figura 11). Por eso salió, y de las 133 "
        "variables candidatas no quedó ninguna.",
    ])
    + figura(FIG / "f19_sarimax_validacion.png", "rIdFig19", 2019, 13,
             "Mejora del RMSE en logaritmo frente al ingenuo del día (ecuación 18) de las tres versiones de SARIMAX, "
             "por horizonte, en la validación de 2020-2022. " + FUENTE_XM)
    + par("*Modelo final.* El modelo final es SARIMAX(1,1,2)(0,0,2)_{7} en las 24 horas, con el festivo como única "
          "variable explicativa. Cada hora *H* tiene sus propios coeficientes:")
    + ecuacion(EC32, 31)
    + ecuacion(EC33, 32)
    + bloque([
        "donde *F*_{t} vale 1 si el día *t* es festivo y 0 si no, y ε_{t,H} es ruido blanco. La ecuación (32) es el "
        "caso particular de la ecuación (1) con un rezago autorregresivo, una diferencia, dos rezagos de media móvil y "
        "dos de media móvil semanal. En 2020-2022, el modelo redujo 4,7% el RMSE frente al ingenuo del día, con "
        "*p* = 0,018; la mejora va de 6,6% en *h* = 3 a 2,7% en *h* = 7 (figura 11). Queda un poco por debajo del 5% "
        "del criterio. Aun así, se mantiene como el modelo lineal de referencia, y la evaluación que cuenta es la de la "
        "prueba (capítulo 4).",

        "*Diagnóstico de los residuos.* Si el modelo recoge toda la estructura del precio, sus residuos no deberían "
        "tener autocorrelación. La prueba de Ljung y Box (1978) lo revisa con las autocorrelaciones ρ̂_{k} de los "
        "residuos en los primeros 14 rezagos:",
    ])
    + ecuacion(EC31, 33)
    + bloque([
        "Bajo la hipótesis nula de que los residuos son ruido blanco, *Q* sigue una distribución ji cuadrado con "
        "14 − 5 = 9 grados de libertad, porque se restan los cinco coeficientes ARMA estimados. Un *Q* grande indica "
        "que quedan autocorrelaciones que el modelo no explica. Con los residuos de 2015-2019, la prueba no rechazó al "
        "5% en 17 de las 24 horas, y rechazó en las horas 3, 6, 7, 15, 16, 17 y 22 (figura 12a). La autocorrelación de "
        "los residuos, promediada sobre las 24 horas, muestra dónde queda lo que falta (figura 12b): los rezagos 1 a "
        "20 están dentro de la banda de 95%, y solo se salen los rezagos 21 y 28, con 0,088 y 0,075. Las dos medias "
        "móviles semanales recogen la relación con el mismo día de una y dos semanas antes, pero no la de tres y "
        "cuatro semanas. Es lo que se cede a cambio de un modelo más simple que pronostica igual.",
    ])
    + figura(FIG / "f20_sarimax_residuos.png", "rIdFig20", 2020, 15,
             "Diagnóstico de los residuos del modelo final, 2015-2019. a) Valor p de la prueba de Ljung-Box con 14 "
             "rezagos en cada hora; las barras claras son las horas en que se rechaza al 5%. b) Autocorrelación de los "
             "residuos, promedio de las 24 horas; los rezagos múltiplos de siete van en negro y la franja gris es la "
             "banda de 95%. " + FUENTE_XM)
    + bloque([
        "En la validación y en la prueba, los coeficientes se reestiman el primer día de cada mes con los precios hasta "
        "el último día del mes anterior, y dentro del mes el modelo solo se actualiza cada día con los precios nuevos, "
        "sin reestimar. La estimación convergió en todos los meses y en todas las horas. Con esto, el modelo quedó fijo "
        "antes de abrir la prueba.",
    ])
)

d = Docx(ENTRADA)
assert "f17_sarimax_construccion" not in d.doc, "la 3.4 ya está"
textos = [d.texto(p) for _, _, p in d.parrafos()]
assert not any(t.strip() in {f"({n})" for n in range(23, 34)} for t in textos), "ya hay ecuaciones de la 23 a la 33"
for f in ["f17_sarimax_construccion", "f18_sarimax_preblanqueo", "f19_sarimax_validacion", "f20_sarimax_residuos"]:
    d.agregar_imagen(FIG / f"{f}.png", "rIdFig" + f[1:3])
d.reemplazar_vacio_tras("3.4 SARIMAX", S34)
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
