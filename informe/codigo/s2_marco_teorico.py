"""Escribe el capítulo II, Marco teórico (secciones 2.1 a 2.4), con ecuaciones editables y la tabla de antecedentes.
Uso: python s2_marco_teorico.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import (Docx, acento, barra, ecuacion, frac, funcion, leyenda, m, mr, par, paren, raiz, sub,
                        subsup, suma, sup, tabla)

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]


def bloque(textos):
    return "".join(par(t) for t in textos)


# ------------------------------------------------------------------ 2.1 El mercado eléctrico y el precio de bolsa
S21 = bloque([
    "El mercado eléctrico colombiano actual nace con las leyes 142 y 143 de 1994, que separaron las actividades de "
    "generación, transmisión, distribución y comercialización, y abrieron a la competencia la generación y la "
    "comercialización (Congreso de la República de Colombia, 1994a, 1994b). La regulación quedó a cargo de la "
    "Comisión de Regulación de Energía y Gas (CREG), y la operación del sistema y la administración del mercado "
    "mayorista, a cargo de XM, filial del grupo ISA. En el mercado mayorista los generadores venden energía y los "
    "comercializadores la compran para atender a los usuarios finales.",

    "Como se describió en la sección 1.1, cada día los generadores ofertan un precio para las 24 horas del día "
    "siguiente y declaran su disponibilidad hora por hora (CREG, 1995). Con esas ofertas, XM calcula tres despachos "
    "distintos. El despacho programado se hace antes del día de operación, tiene en cuenta las restricciones de la "
    "red y dice qué plantas deben generar en cada hora. El despacho real es lo que ocurre durante el día, con los "
    "ajustes que exige la operación. El despacho ideal se calcula después del día, sin restricciones de red: atiende "
    "la demanda real con las plantas en orden de mérito, y el precio de bolsa de cada hora es la oferta de la planta "
    "marginal de ese despacho (CREG, 1994). Las diferencias entre el despacho ideal y el real se liquidan aparte, "
    "como reconciliaciones, y no cambian el precio de bolsa.",

    "La regulación define además un precio de escasez, dentro del cargo por confiabilidad. Cuando el precio de bolsa "
    "lo supera, se activan las obligaciones de energía firme, con las que los generadores se comprometen a entregar "
    "energía en condiciones críticas de abastecimiento (CREG, 2006). Por eso, la distancia entre el precio de bolsa "
    "y el precio de escasez indica qué tan cerca está el sistema de una situación crítica.",

    "El precio de bolsa tiene los rasgos que la literatura describe para los precios de la electricidad: "
    "estacionalidad en varias escalas, reversión a la media, alta volatilidad y picos (Weron, 2014). Se repite un "
    "ciclo diario, con los precios más altos en las horas de mayor demanda, al comienzo de la noche; un ciclo "
    "semanal, con precios más bajos los domingos y festivos, y un ciclo anual, ligado a las temporadas de lluvias y "
    "de sequía. A eso se suma lo propio de un sistema hidráulico: el nivel del precio puede cambiar durante meses "
    "según el agua disponible, como se ve en la figura 2.",

    "Dos consecuencias importan para pronosticarlo. Primera, como el precio cambia de escala, de 61 a casi 2.500 "
    "COP/kWh en promedio diario, conviene modelar su logaritmo, que estabiliza la varianza y reduce el peso de los "
    "picos (Uniejewski et al., 2018). Segunda, el precio depende de las ofertas, que son decisiones de los "
    "generadores y se publican tarde (sección 1.1). Un modelo de pronóstico solo puede aproximarlas a partir de lo "
    "que sí se observa a tiempo: la hidrología, la demanda, el despacho programado y la historia del propio precio.",
])

# ------------------------------------------------------------------ 2.2 Antecedentes
TABLA_ANTECEDENTES = tabla([
    ["Trabajo", "Programa", "Modelos", "Qué pronostica"],
    ["Cárdenas Paredes (2005)", "Maestría, Ingeniería Eléctrica", "Autorregresivos y lógica difusa",
     "Precio de bolsa"],
    ["Velásquez Rojas y Gracia (2015)", "Pregrado", "Red neuronal", "Precio de bolsa"],
    ["Rojas Ardila (2018)", "Pregrado, Ingeniería Eléctrica", "BSTS, BVAR, ARIMA y ARIMAX",
     "Precio horario, de un día a seis meses"],
    ["Cárdenas Cárdenas (2021)", "Pregrado, Ingeniería Industrial", "NNAR y ARIMA",
     "Precio promedio diario, semana siguiente"],
    ["González Pérez y Urbano Buriticá (2022)", "Maestría, Inteligencia Analítica", "SARIMAX, Prophet y LSTM",
     "Precio horario, día siguiente"],
    ["Este trabajo", "Pregrado, Ingeniería Industrial", "SARIMAX, XGBoost y LSTM",
     "Precio horario, de tres a nueve días"],
], [4.2, 3.6, 3.8, 4.0])

S22 = (
    bloque([
        "Weron (2014) clasifica los métodos de pronóstico del precio de la electricidad en cinco grupos: modelos "
        "multiagente, fundamentales, de forma reducida, estadísticos y de inteligencia computacional. Este trabajo "
        "usa los dos últimos: SARIMAX es un modelo estadístico, y XGBoost y la LSTM son de aprendizaje automático. La "
        "misma revisión distingue el corto plazo, de horas a unos días, del mediano plazo, de días a meses. El "
        "horizonte de este trabajo, de tres a nueve días, queda entre los dos, mientras que la mayor parte de la "
        "literatura se concentra en el mercado del día siguiente (Lago et al., 2021).",

        "Lago et al. (2018) compararon modelos de aprendizaje profundo con modelos estadísticos y de aprendizaje "
        "automático en el mercado belga, y encontraron que los de aprendizaje automático, en especial una red "
        "neuronal profunda, tenían menor error que los estadísticos. Después, Lago et al. (2021) revisaron el estado "
        "del arte y propusieron prácticas para que los estudios sean comparables: evaluar en periodos largos, de al "
        "menos un año; comparar contra modelos de referencia bien establecidos, y usar pruebas estadísticas, como la "
        "de Diebold y Mariano, para decidir si una diferencia es significativa. En la Universidad de los Andes, "
        "Salazar-Peña et al. (2025) compararon modelos de aprendizaje profundo, entre ellos redes LSTM y "
        "Transformer, para pronosticar la generación solar del día y participar en el mercado intradiario. Su forma "
        "de presentar los resultados es la que sigue el capítulo IV.",

        "En la misma universidad, el precio de bolsa se ha pronosticado desde hace dos décadas (tabla 1). Cárdenas "
        "Paredes (2005) usó modelos autorregresivos y lógica difusa, y Velásquez Rojas y Gracia (2015, citado en "
        "Rojas Ardila, 2018) implementaron una red neuronal. Rojas Ardila (2018) comparó modelos bayesianos (BSTS y "
        "BVAR) con ARIMA y ARIMAX en horizontes de un día a seis meses: los bayesianos funcionaron bien a uno y a "
        "siete días, y a seis meses el ARIMA tuvo el menor error. Cárdenas Cárdenas (2021) comparó redes neuronales "
        "autorregresivas (NNAR) con ARIMA para el precio promedio diario, y su mejor modelo fue una NNAR con la "
        "demanda y el precio promedio de oferta como variables externas. González Pérez y Urbano Buriticá (2022) "
        "compararon SARIMAX, Prophet y redes LSTM para el precio horario del día siguiente, y eligieron una LSTM con "
        "un modelo para cada hora del día. Por fuera del pronóstico, Hidalgo Bastidas (2020) analizó el efecto de la "
        "entrada de las fuentes no convencionales de energía renovable sobre el precio.",
    ])
    + leyenda("Tabla", "Trabajos de la Universidad de los Andes que pronostican el precio de bolsa.",
              ppr='<w:keepNext/><w:spacing w:before="240"/>')
    + TABLA_ANTECEDENTES
    + ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
       '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>Fuente: elaboración propia con base en los trabajos '
       'citados.</w:t></w:r></w:p>')
    + par("Estos trabajos muestran que en el precio de bolsa se han probado modelos estadísticos y de aprendizaje "
          "automático, con resultados que dependen del horizonte, del periodo y de cómo se evalúan. Este trabajo "
          "sigue esa línea: compara un modelo estadístico, uno de árboles y una red recurrente con el mismo diseño, "
          "en un horizonte de una semana y con las prácticas de evaluación de Lago et al. (2021).")
)

# ------------------------------------------------------------------ 2.3 Modelos de pronóstico
B, t = m("B"), m("t")


def lineal(k):
    """W_k x_t + U_k h_(t−1) + b_k"""
    return sub(m("W"), m(k)) + sub(m("x"), t) + m("+") + sub(m("U"), m(k)) + sub(m("h"), m("t−1")) + m("+") \
        + sub(m("b"), m(k))


EC = {
    1: sub(m("φ"), m("p")) + paren(B) + sub(m("Φ"), m("P")) + paren(sup(B, m("s")))
       + sup(paren(m("1−B")), m("d")) + sup(paren(m("1−") + sup(B, m("s"))), m("D")) + sub(m("η"), t)
       + m("=") + sub(m("θ"), m("q")) + paren(B) + sub(m("Θ"), m("Q")) + paren(sup(B, m("s"))) + sub(m("ε"), t),
    2: sub(m("y"), t) + m("=") + sub(m("β"), m("0")) + m("+")
       + suma(m("j=1"), m("k"), sub(m("β"), m("j")) + sub(m("x"), m("j,t"))) + m("+") + sub(m("η"), t),
    3: sub(acento(m("y")), m("i")) + m("=") + suma(m("k=1"), m("K"), sub(m("f"), m("k")) + paren(sub(m("x"), m("i")))),
    4: m("ℒ=") + suma(m("i"), None, m("l") + paren(sub(m("y"), m("i")) + m(",") + sub(acento(m("y")), m("i"))))
       + m("+") + suma(m("k"), None, m("Ω") + paren(sub(m("f"), m("k")))),
    5: m("Ω") + paren(m("f")) + m("=γT+") + frac(m("1"), m("2")) + m("λ")
       + suma(m("j=1"), m("T"), subsup(m("w"), m("j"), m("2"))),
    6: sub(m("f"), t) + m("=σ") + paren(lineal("f")),
    7: sub(m("i"), t) + m("=σ") + paren(lineal("i")),
    8: sub(m("o"), t) + m("=σ") + paren(lineal("o")),
    9: sub(acento(m("c"), "̃"), t) + m("=") + funcion("tanh", paren(lineal("c"))),
    10: sub(m("c"), t) + m("=") + sub(m("f"), t) + m("⊙") + sub(m("c"), m("t−1")) + m("+") + sub(m("i"), t)
        + m("⊙") + sub(acento(m("c"), "̃"), t),
    11: sub(m("h"), t) + m("=") + sub(m("o"), t) + m("⊙") + funcion("tanh", paren(sub(m("c"), t))),
}

S23 = (
    par("Hay tres formas de pronosticar varios pasos adelante (Ben Taieb et al., 2012): de forma recursiva, usando "
        "cada pronóstico como dato para el siguiente; de forma directa, con un modelo distinto para cada horizonte, o "
        "con un solo modelo que entrega todos los horizontes a la vez. Los tres modelos de este trabajo usan una forma "
        "distinta cada uno: SARIMAX es recursivo, XGBoost es directo y la LSTM entrega la semana completa.")

    # SARIMAX
    + par("*SARIMAX.* Un modelo ARIMA describe una serie por su relación con sus propios valores pasados (la parte "
          "autorregresiva, de orden *p*) y con sus errores de pronóstico pasados (la media móvil, de orden *q*), "
          "después de diferenciarla *d* veces para que sea estacionaria (Box et al., 2015). La versión estacional, "
          "SARIMA, agrega los mismos términos con un rezago *s*, el periodo del ciclo, con órdenes *P*, *D* y *Q*. "
          "Con el operador de rezago *B*, que cumple *By*_{t} = *y*_{t−1}, el modelo para una serie *η*_{t} es")
    + ecuacion(EC[1], 1)
    + par("donde *φ*_{p}, *Φ*_{P}, *θ*_{q} y *Θ*_{Q} son polinomios en *B* de grados *p*, *P*, *q* y *Q*, y *ε*_{t} es ruido "
          "blanco. SARIMAX agrega variables explicativas: la serie *y*_{t} se escribe como una regresión cuyos errores "
          "*η*_{t} siguen el modelo (1) (Hyndman y Athanasopoulos, 2021),")
    + ecuacion(EC[2], 2)
    + par("Los órdenes de diferenciación se eligen con pruebas de raíz unitaria, como KPSS (Kwiatkowski et al., "
          "1992) para *d* y OCSB (Osborn et al., 1988) para *D*, y los demás con el criterio de información de Akaike "
          "corregido, AICc (Hurvich y Tsai, 1989). SARIMAX es lineal y tiene un solo periodo estacional. Por eso, con "
          "datos horarios es común estimar un modelo para cada hora del día, con la serie diaria de esa hora "
          "(Weron, 2014).")

    # XGBoost
    + par("*XGBoost.* Un árbol de regresión divide el espacio de las variables con reglas del tipo *x*_{j} ≤ *c* y "
          "asigna a cada región, u hoja, un valor constante (Hastie et al., 2009). Un solo árbol es inestable y poco "
          "preciso; el boosting de gradiente suma muchos árboles pequeños, cada uno ajustado para corregir el error "
          "que dejan los anteriores (Friedman, 2001). XGBoost es una implementación de esa idea (Chen y Guestrin, "
          "2016) en la que el pronóstico es la suma de *K* árboles,")
    + ecuacion(EC[3], 3)
    + par("y cada árbol nuevo se elige para reducir una pérdida con penalización,")
    + ecuacion(EC[4], 4)
    + ecuacion(EC[5], 5)
    + par("donde *l* mide el error (aquí, el error cuadrático), *T* es el número de hojas del árbol, *w*_{j} es el "
          "valor de la hoja *j*, y *γ* y *λ* controlan qué tan complejo puede ser cada árbol. Para encontrar cada "
          "árbol, XGBoost usa una aproximación de segundo orden de la pérdida. Sus hiperparámetros principales son la "
          "tasa de aprendizaje, que reduce la contribución de cada árbol, la profundidad máxima y el peso mínimo de "
          "cada hoja. Los árboles capturan relaciones no lineales e interacciones entre variables sin que haya que "
          "especificarlas. A cambio, como cada hoja tiene un valor constante, el pronóstico no sale del rango de "
          "valores que el modelo vio al entrenarse. Por eso conviene pronosticar una respuesta cuya escala no cambie "
          "con el nivel del precio, como su cambio en logaritmo (sección 3.2).")

    # LSTM
    + par("*Redes LSTM.* Las redes neuronales recurrentes procesan una secuencia paso a paso y guardan un estado que "
          "resume lo visto hasta ese momento (Goodfellow et al., 2016). Al entrenarlas con secuencias largas, los "
          "gradientes tienden a desvanecerse y la red olvida lo lejano. La celda LSTM (Hochreiter y Schmidhuber, "
          "1997) resuelve este problema con un estado de memoria *c*_{t} y compuertas que deciden qué olvidar, qué "
          "agregar y qué entregar (Gers et al., 2000). En cada paso *t*, con la entrada *x*_{t} y la salida anterior "
          "*h*_{t−1},")
    + "".join(ecuacion(EC[k], k) for k in range(6, 12))
    + par("donde *σ* es la función logística, ⊙ es el producto elemento a elemento, y *W*, *U* y *b* son los pesos que "
          "se aprenden. La compuerta de olvido *f*_{t} decide cuánto de la memoria anterior se conserva; la de entrada "
          "*i*_{t}, cuánto de la información nueva se agrega, y la de salida *o*_{t}, qué parte de la memoria se entrega "
          "como *h*_{t}.")
    + par("Para pronosticar una secuencia completa se usa una arquitectura codificador-decodificador (Sutskever et "
          "al., 2014): una LSTM, el codificador, lee la historia y la resume en su estado final, y otra, el "
          "decodificador, parte de ese estado y genera los pasos de la salida, en este caso los días de la semana. La "
          "red se entrena minimizando el error cuadrático medio con el optimizador Adam (Kingma y Ba, 2015). Para "
          "evitar el sobreajuste se usan dropout, que apaga al azar una fracción de las neuronas durante el "
          "entrenamiento (Srivastava et al., 2014), y parada temprana, que detiene el entrenamiento cuando el error "
          "en un conjunto de validación deja de bajar (Goodfellow et al., 2016).")
)

# ------------------------------------------------------------------ 2.4 Evaluación de pronósticos
P_ = lambda a: m("P") + paren(m(a))
Ph = lambda a: acento(m("P")) + paren(m(a))

EC.update({
    12: sub(m("e"), m("t,h,H")) + m("=") + funcion("log", P_("t+h,H")) + m("−") + funcion("log", Ph("t+h,H")),
    13: mr("RMSE") + m("=") + raiz(frac(m("1"), m("N")) + suma(m("i=1"), m("N"), subsup(m("e"), m("i"), m("2")))),
    14: mr("MAE") + m("=") + frac(m("1"), m("N")) + suma(m("i=1"), m("N"), paren(sub(m("e"), m("i")), "|", "|")),
    15: mr("MAPE") + m("=") + frac(m("100 %"), m("N"))
        + suma(m("i=1"), m("N"), frac(paren(sub(m("P"), m("i")) + m("−") + sub(acento(m("P")), m("i")), "|", "|"),
                                     sub(m("P"), m("i")))),
    16: Ph("t+h,H") + m("=") + P_("t,H"),
    17: Ph("t+h,H") + m("=") + P_("t+h−7k,H") + m(",  k=") + paren(frac(m("h"), m("7")), "⌈", "⌉"),
    18: mr("Mejora") + m("=100") + paren(m("1−") + frac(sub(mr("RMSE"), mr("modelo")), sub(mr("RMSE"), mr("ref")))),
    19: sub(m("d"), t) + m("=") + subsup(m("e"), m("1,t"), m("2")) + m("−") + subsup(m("e"), m("2,t"), m("2")),
    20: mr("DM") + m("=") + frac(barra(m("d")), raiz(frac(sup(acento(m("σ")), m("2")), m("T")))),
})

S24 = (
    par("Un pronóstico se evalúa comparándolo con lo que de verdad ocurrió, en datos que el modelo no usó para "
        "ajustarse. En series de tiempo eso exige respetar el orden: se usa una evaluación con origen móvil, en la que "
        "el modelo se ajusta con los datos hasta un día, pronostica desde ese día y el origen avanza (Hyndman y "
        "Athanasopoulos, 2021). Así, cada pronóstico se hace como se haría en la práctica. Cuando la respuesta de un "
        "día solo se conoce *h* días después, además hay que dejar un espacio de *h* días entre los datos de ajuste "
        "y los de evaluación, para que el modelo no se entrene con información del periodo que pronostica (López de "
        "Prado, 2018).")
    + par("Si *P*(*t* + *h*, *H*) es el precio de la hora *H* del día *t* + *h*, y *P̂*(*t* + *h*, *H*) es su "
          "pronóstico hecho el día *t*, el error en logaritmo es")
    + ecuacion(EC[12], 12)
    + par("Con *N* errores, las medidas más usadas son la raíz del error cuadrático medio (RMSE), el error absoluto "
          "medio (MAE) y el error porcentual absoluto medio (MAPE), este último calculado con los precios en pesos "
          "(Hyndman y Athanasopoulos, 2021):")
    + ecuacion(EC[13], 13) + ecuacion(EC[14], 14) + ecuacion(EC[15], 15)
    + par("El RMSE castiga más los errores grandes, lo que importa en un mercado donde los costos se concentran en "
          "los picos. Medido en logaritmo, un error de 10% pesa lo mismo con precios de 200 o de 2.000 COP/kWh. El "
          "MAPE se reporta porque es la medida que usan los trabajos anteriores (sección 2.2), aunque se vuelve "
          "inestable cuando los precios son bajos (Hyndman y Athanasopoulos, 2021).")
    + par("Una medida de error dice poco por sí sola: hay que compararla con la de un pronóstico de referencia. El "
          "más sencillo es el ingenuo, que repite un valor ya conocido (Hyndman y Athanasopoulos, 2021). En este "
          "trabajo se usan dos. El ingenuo del día repite, para cada hora, el precio del último día conocido,")
    + ecuacion(EC[16], 16)
    + par("y el ingenuo semanal repite el precio de la misma hora y el mismo día de la semana en la última semana "
          "conocida,")
    + ecuacion(EC[17], 17)
    + par("El primero sigue el nivel más reciente del precio; el segundo respeta el ciclo semanal, que el primero "
          "ignora. La mejora de un modelo frente a la referencia se mide como la reducción porcentual de su RMSE "
          "(Lago et al., 2021):")
    + ecuacion(EC[18], 18)
    + par("Que un modelo tenga menor error en una muestra no garantiza que sea mejor, porque la diferencia puede "
          "deberse al azar. La prueba de Diebold y Mariano (1995) compara dos pronósticos a partir de la diferencia "
          "de sus pérdidas,")
    + ecuacion(EC[19], 19)
    + par("Bajo la hipótesis nula de que los dos son igual de precisos, el valor esperado de *d*_{t} es cero, y el "
          "estadístico")
    + ecuacion(EC[20], 20)
    + par("se distribuye aproximadamente como una normal estándar, donde *d̄* es el promedio de las *T* diferencias "
          "y *σ̂*^{2} es un estimado de la varianza de largo plazo de *d*_{t}. Como los pronósticos a *h* pasos se "
          "traslapan, *d*_{t} está autocorrelacionado hasta el rezago *h* − 1, así que la varianza se estima con el "
          "método de Newey y West (1987), que corrige por esa autocorrelación. Un valor negativo y significativo "
          "indica que el primer pronóstico es más preciso.")
    + par("Por último, un menor error no siempre se traduce en mejores decisiones. Por eso la sección 4.4 evalúa los "
          "pronósticos también por su valor en una decisión concreta.")
)

REFS = [
    "Ben Taieb, S., Bontempi, G., Atiya, A. F., y Sorjamaa, A. (2012). A review and comparison of strategies for "
    "multi-step ahead time series forecasting based on the NN5 forecasting competition. *Expert Systems with "
    "Applications, 39*(8), 7067-7083. https://doi.org/10.1016/j.eswa.2012.01.039",
    "Box, G. E. P., Jenkins, G. M., Reinsel, G. C., y Ljung, G. M. (2015). *Time series analysis: Forecasting and "
    "control* (5.ª ed.). Wiley.",
    "Chen, T., y Guestrin, C. (2016). XGBoost: A scalable tree boosting system. En *Proceedings of the 22nd ACM "
    "SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785-794). "
    "https://doi.org/10.1145/2939672.2939785",
    "Comisión de Regulación de Energía y Gas [CREG]. (2006). *Resolución CREG 071 de 2006: Metodología para la "
    "remuneración del cargo por confiabilidad en el mercado mayorista de energía*. Gestor normativo de la CREG.",
    "Congreso de la República de Colombia. (1994a). *Ley 142 de 1994: Por la cual se establece el régimen de los "
    "servicios públicos domiciliarios y se dictan otras disposiciones*. Diario Oficial 41.433.",
    "Congreso de la República de Colombia. (1994b). *Ley 143 de 1994: Por la cual se establece el régimen para la "
    "generación, interconexión, transmisión, distribución y comercialización de electricidad en el territorio "
    "nacional*. Diario Oficial 41.434.",
    "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. *The Annals of Statistics, "
    "29*(5), 1189-1232. https://doi.org/10.1214/aos/1013203451",
    "Gers, F. A., Schmidhuber, J., y Cummins, F. (2000). Learning to forget: Continual prediction with LSTM. "
    "*Neural Computation, 12*(10), 2451-2471. https://doi.org/10.1162/089976600300015015",
    "Goodfellow, I., Bengio, Y., y Courville, A. (2016). *Deep learning*. MIT Press.",
    "Hastie, T., Tibshirani, R., y Friedman, J. (2009). *The elements of statistical learning: Data mining, "
    "inference, and prediction* (2.ª ed.). Springer.",
    "Hidalgo Bastidas, C. D. (2020). *Impacto en el precio de la energía eléctrica en Colombia debido a la "
    "incorporación de fuentes no convencionales de energía renovable* (Documentos de Trabajo Escuela de Gobierno "
    "Alberto Lleras Camargo, n.º 77). Universidad de los Andes.",
    "Hochreiter, S., y Schmidhuber, J. (1997). Long short-term memory. *Neural Computation, 9*(8), 1735-1780. "
    "https://doi.org/10.1162/neco.1997.9.8.1735",
    "Hurvich, C. M., y Tsai, C.-L. (1989). Regression and time series model selection in small samples. "
    "*Biometrika, 76*(2), 297-307. https://doi.org/10.1093/biomet/76.2.297",
    "Hyndman, R. J., y Athanasopoulos, G. (2021). *Forecasting: Principles and practice* (3.ª ed.). OTexts. "
    "https://otexts.com/fpp3/",
    "Kingma, D. P., y Ba, J. (2015). Adam: A method for stochastic optimization. En *3rd International Conference "
    "on Learning Representations (ICLR)*. https://arxiv.org/abs/1412.6980",
    "Kwiatkowski, D., Phillips, P. C. B., Schmidt, P., y Shin, Y. (1992). Testing the null hypothesis of "
    "stationarity against the alternative of a unit root. *Journal of Econometrics, 54*(1-3), 159-178. "
    "https://doi.org/10.1016/0304-4076(92)90104-Y",
    "Lago, J., De Ridder, F., y De Schutter, B. (2018). Forecasting spot electricity prices: Deep learning "
    "approaches and empirical comparison of traditional algorithms. *Applied Energy, 221*, 386-405. "
    "https://doi.org/10.1016/j.apenergy.2018.02.069",
    "López de Prado, M. (2018). *Advances in financial machine learning*. Wiley.",
    "Newey, W. K., y West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation "
    "consistent covariance matrix. *Econometrica, 55*(3), 703-708. https://doi.org/10.2307/1913610",
    "Osborn, D. R., Chui, A. P. L., Smith, J. P., y Birchenhall, C. R. (1988). Seasonality and the order of "
    "integration for consumption. *Oxford Bulletin of Economics and Statistics, 50*(4), 361-377.",
    "Rojas Ardila, J. S. (2018). *Pronóstico del precio en bolsa de la energía eléctrica en Colombia, utilizando "
    "inferencia bayesiana* [Trabajo de grado de pregrado, Universidad de los Andes].",
    "Salazar-Peña, N., Palma-Vergara, A., Montes-Vera, M., Vargas-Torres, M. A., Hernández Vanegas, R., Amador, M., "
    "Rojas, B., Salinas, A., Velasco, A., Tabares, A., y González-Mancera, A. (2025). *Intra-day solar and power "
    "forecast for optimization of intraday market participation* [Preprint]. arXiv. "
    "https://arxiv.org/abs/2501.09551",
    "Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I., y Salakhutdinov, R. (2014). Dropout: A simple way "
    "to prevent neural networks from overfitting. *Journal of Machine Learning Research, 15*(56), 1929-1958.",
    "Sutskever, I., Vinyals, O., y Le, Q. V. (2014). Sequence to sequence learning with neural networks. *Advances "
    "in Neural Information Processing Systems, 27*, 3104-3112.",
    "Uniejewski, B., Weron, R., y Ziel, F. (2018). Variance stabilizing transformations for electricity spot price "
    "forecasting. *IEEE Transactions on Power Systems, 33*(2), 2219-2229. https://doi.org/10.1109/TPWRS.2017.2734563",
    "Weron, R. (2014). Electricity price forecasting: A review of the state-of-the-art with a look into the future. "
    "*International Journal of Forecasting, 30*(4), 1030-1081. https://doi.org/10.1016/j.ijforecast.2014.08.008",
]

d = Docx(ENTRADA)
assert "xmlns:m=" in d.doc[:3000], "el documento no declara el espacio de nombres de las ecuaciones"
d.reemplazar_vacio_tras("2.1 El mercado eléctrico y el precio de bolsa", S21)
d.reemplazar_vacio_tras("2.2 Antecedentes", S22)
d.reemplazar_vacio_tras("2.3 Modelos de pronóstico", S23)
d.reemplazar_vacio_tras("2.4 Evaluación de pronósticos", S24)
d.referencias(REFS)
d.guardar(SALIDA)
print("ok", SALIDA)
