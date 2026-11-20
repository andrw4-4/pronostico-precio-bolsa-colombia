import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from docx_lib import *  # noqa

BASE = Path(sys.argv[1])
FIG = BASE / "informe" / "figuras"
RES = BASE / "resultados"
SALIDA = BASE / "informe" / "Informe_avance_tesis.docx"

C = []  # cuerpo
a = C.append


def P(t):
    a(p(t))


def nota(t):
    a(p(t, estilo="Nota"))


# ------------------------------------------------------------------ portada
a(p("", espacio=(1800, 0)))
a(p("Pronóstico horario del precio de bolsa de energía en Colombia a una semana", estilo="Title"))
a(p("Informe de avance de tesis: datos, variables, XGBoost, SARIMAX y plan de la red LSTM", estilo="Subtitle"))
a(p("", espacio=(600, 0)))
a(p("Andrés David Arismendi", espacio=(0, 40)))
a(p("Universidad de los Andes", espacio=(0, 40)))
a(p("6 de noviembre de 2026", espacio=(0, 40)))
a(p("", espacio=(2400, 0)))
a(p("Repositorio: github.com/andrw4-4/pronostico-precio-bolsa-colombia. Cada cifra de este informe sale "
    "de los archivos de resultados del repositorio; la fuente de cada parte del código está en docs/REFERENCIAS.md.",
    estilo="Caption"))
a(salto())
a(toc())

# ------------------------------------------------------------------ resumen
a(h1("Resumen"))
P("El precio de bolsa es el precio al que se transa cada hora la energía en el mercado de corto plazo colombiano. "
  "Esta tesis pronostica los 168 precios horarios de la semana siguiente con datos públicos, y los compara contra "
  "la regla más simple posible: repetir el último precio conocido de esa hora.")
P("Como XM publica el precio con dos días de atraso, la semana que se pronostica corresponde a los horizontes h = 3 a 9 "
  "contados desde el último precio conocido. Hasta ahora hay dos modelos terminados, con selección, prueba y comparación: "
  "XGBoost, con 7 modelos directos y variables elegidas de un panel de 1.861 columnas, y SARIMAX, con 24 modelos, uno "
  "por hora. Un modelo funciona si baja el RMSE en logaritmo al menos 5% frente al mejor ingenuo y la prueba de "
  "Diebold y Mariano da p < 0,05.")
a(tabla([["", "XGBoost", "SARIMAX"],
         ["Mejora en 2023-2025 (h = 3 a 9)", "11,6%", "6,4%"],
         ["Mejora en 2026, hasta el 6 de octubre", "10,0%", "5,6%"],
         ["Diebold-Mariano contra el ingenuo", "p < 0,001 y p = 0,001", "p < 0,001 en los dos"],
         ["Pasa el criterio", "Sí, en los dos periodos", "Sí, en los dos periodos"],
         ["Criterio de una semana fijado antes de su prueba", "No (ver sección 6.4)", "Sí"]],
        anchos=[4, 3, 3], alinear_num=False))
P("Los dos modelos le ganan al ingenuo, pero ninguno anticipa bien el nivel del precio en una crisis como la de El Niño "
  "de 2024. XGBoost es mejor en el día típico y en la forma del día; SARIMAX es más estable entre años y casi no tiene "
  "sesgo. Los diagnósticos indican que buena parte del límite está en la información pública disponible: lo que más "
  "mueve el precio son las ofertas de los generadores, que se publican diez días tarde. También muestran que alinear "
  "cada dato al día en que de verdad se publica (el despacho programado de hoy sale antes que el precio) mejora mucho "
  "el pronóstico, y esa es la base de la red LSTM que sigue.")

# ------------------------------------------------------------------ 1. introducción
a(h1("1. Introducción"))
a(h2("1.1 El precio de bolsa"))
P("En Colombia, cada planta de generación hace una oferta de precio al día y declara cuánta energía puede entregar en "
  "cada hora (CREG 025 de 1995, numeral 3.1). XM, el operador del mercado, ordena las plantas de la más barata a la más "
  "cara y las despacha hasta cubrir la demanda de cada hora. El precio de bolsa de la hora es, en esencia, el de la "
  "última planta que hace falta para atender la demanda (CREG 055 de 1994, art. 14). Como en cada hora queda al margen "
  "una planta distinta, el precio es horario aunque la oferta sea diaria.")
P("Si se ordenan las ofertas de menor a mayor, el precio de la hora H se puede escribir como el menor precio de oferta "
  "con el que la capacidad disponible alcanza la demanda:")
a(ec(e(sub(r("P"), r("H")), r("="), tx("min"), par(e(r("p"), r(" : "), suma(r("i"), "", e(sub(r("q"), r("i,H")), r("·"), tx("1"), par(e(sub(r("p"), r("i")), r("≤"), r("p")), "[", "]"))), r("≥"), sub(r("D"), r("H"))), "{", "}"))))
P("donde $p_i$ es el precio que ofertó la planta i, $q_{i,H}$ su disponibilidad en la hora H y $D_H$ la demanda. Esta "
  "reconstrucción de la curva de mérito reproduce el precio de bolsa con correlación de 0,94 a nivel horario. Entre 65% y "
  "86% de la energía de cada año entre 2015 y 2025 fue hidráulica, así que el precio depende sobre todo de cuánta agua "
  "hay en los embalses y de cuánta va a llegar, y por eso es tan sensible a El Niño (figura 1).")
a(figura(FIG / "f01_precio_embalses_nino.png",
         "Precio de bolsa promedio del día (escala logarítmica), volumen útil de los embalses e índice ONI. Las franjas "
         "marcan los dos episodios fuertes de El Niño de la muestra. Fuente: panel del paso 2c, con datos de XM y NOAA.",
         13.5))
P("La figura muestra tres rasgos que guían todo el trabajo. El precio cambia de nivel por meses, con subidas grandes "
  "cuando los embalses bajan (2015-2016, 2020, 2024). Se mueve en un rango muy amplio, de unos 70 a más de 2.000 COP/kWh, "
  "lo que obliga a trabajar en logaritmo. Y desde 2022 es más alto y más volátil que en los años anteriores, así que el "
  "periodo de prueba es más difícil que el de entrenamiento.")

a(h2("1.2 Pregunta y alcance"))
P("La pregunta de la tesis es si, con datos públicos, se puede pronosticar el precio de bolsa de cada hora de la semana "
  "siguiente mejor que repitiendo el último precio conocido, y con qué tipo de modelo.")
a(lista(["Se pronostican 168 precios: las 24 horas de los próximos 7 días.",
         "El precio se publica con dos días de atraso. Si t es el último día con precio, el pronóstico se hace el día "
         "R = t + 2 y cubre los días t + 3 a t + 9: los horizontes h = 3 a 9.",
         "El alcance empezó en 30 días. Se redujo a una semana después de ver la prueba de 2026 de XGBoost, porque más "
         "allá de h = 7 el resultado dependía del periodo (sección 6.4).",
         "Modelos: XGBoost y SARIMAX, terminados; una red LSTM, diseñada y en construcción."]))

a(h2("1.3 Contenido del informe"))
P("La sección 2 resume la teoría de los modelos y de la evaluación. Las secciones 3 y 4 cuentan el proceso de datos: "
  "descarga, construcción de los paneles, limpieza, cuándo se conoce cada dato, variables y selección. La sección 5 fija "
  "el diseño del pronóstico. Las secciones 6 y 7 presentan XGBoost y SARIMAX, la 8 los compara y la 9 los compara con la "
  "tesis de referencia de González y Urbano (2022). La 10 resume los diagnósticos sobre el límite del pronóstico, la 11 "
  "el plan de la LSTM y la 12 los puntos de mejora. La figura 2 resume el flujo completo.")
a(figura(FIG / "f10_flujo.png", "Flujo del proyecto. Cada paso es un archivo del repositorio (1_descargar.py, "
         "2_construir_panel.py, 2b a 2g, y los notebooks 4 y 5 de los modelos).", 16))

# ------------------------------------------------------------------ 2. teoría
a(h1("2. Marco teórico"))
a(h2("2.1 Pronóstico directo e ingenuos de referencia"))
P("Hay dos formas de pronosticar varios días adelante. La recursiva usa un modelo de un paso y realimenta sus propios "
  "pronósticos; la directa entrena un modelo distinto para cada horizonte. XGBoost usa la estrategia directa: un modelo "
  "para h = 3, otro para h = 4, y así. SARIMAX, por su naturaleza, es recursivo dentro de cada hora. En ambos casos lo "
  "que se pronostica es el cambio en logaritmo frente a la misma hora del último día conocido:")
a(ec(e(sub(r("y"), r("h")), par(e(r("t"), r(","), r("H"))), r("="), tx("ln "), r("P"), par(e(r("t"), r("+"), r("h"), r(","), r("H"))), r("−"), tx("ln "), r("P"), par(e(r("t"), r(","), r("H"))))))
P("y el pronóstico en pesos se recupera con la exponencial:")
a(ec(e(gorro(r("P")), par(e(r("t"), r("+"), r("h"), r(","), r("H"))), r("="), r("P"), par(e(r("t"), r(","), r("H"))), r("·"), tx("exp"), par(e(sub(gorro(r("y")), r("h")), par(e(r("t"), r(","), r("H"))))))))
P("Trabajar en logaritmo tiene dos ventajas: vuelve comparables los errores de años con precios bajos y altos, y quita la "
  "asimetría de la distribución del precio (figura 3). Con este objetivo, el pronóstico ingenuo del día es simplemente "
  "ŷ = 0. Se usan dos ingenuos:")
a(ec(e(subsup(gorro(r("P")), r("t+h,H"), tx("día")), r("="), sub(r("P"), r("t,H")), r(",      "), subsup(gorro(r("P")), r("t+h,H"), tx("semanal")), r("="), sub(r("P"), e(r("t+h−7"), r("⌈h/7⌉"), r(",H"))))))
P("El ingenuo semanal repite el precio de la misma hora y el mismo día de la semana en la última semana conocida. "
  "Es más exigente que el del día cuando el día de la semana pesa mucho, pero en la práctica el del día fue el mejor "
  "ingenuo en todos los bloques de la prueba.")
a(figura(FIG / "f02_distribucion_log.png", "Distribución del precio horario y de su logaritmo, marzo de 2015 a octubre de "
         "2026. El precio tiene una cola larga a la derecha; el logaritmo es mucho más simétrico.", 15))

a(h2("2.2 XGBoost"))
P("XGBoost (Chen y Guestrin, 2016) es un modelo de árboles de decisión potenciados por gradiente. El pronóstico es la "
  "suma de K árboles, y cada árbol nuevo se ajusta a lo que los anteriores no explicaron:")
a(ec(e(sub(gorro(r("y")), r("i")), r("="), suma(e(r("k"), r("="), r("1")), r("K"), e(sub(r("f"), r("k")), par(sub(r("x"), r("i"))))))))
P("Los árboles se eligen minimizando una pérdida con regularización, que castiga los árboles con muchas hojas (T) y "
  "con pesos de hoja grandes (w):")
a(ec(e(r("ℒ"), r("="), suma(r("i"), "", e(r("l"), par(e(sub(r("y"), r("i")), r(","), sub(gorro(r("y")), r("i")))))), r("+"), suma(r("k"), "", e(r("Ω"), par(sub(r("f"), r("k"))))), r(",     "), r("Ω"), par(r("f")), r("="), r("γT"), r("+"), frac(r("1"), r("2")), r("λ"), sup(r("‖w‖"), r("2")))))
P("Con pérdida cuadrática, l es el error cuadrático. Los hiperparámetros que controlan qué tan flexible es el modelo "
  "son la profundidad máxima de cada árbol, el peso mínimo por hoja (min_child_weight, que aquí se cuenta en horas), la "
  "fracción de filas y de columnas que ve cada árbol (subsample y colsample_bytree), la regularización λ y el número de "
  "árboles. Un árbol no extrapola: todo valor que supere el máximo visto en entrenamiento cae en la misma hoja. Por eso "
  "en la selección se quitan las variables cuyo nivel se corre con los años (sección 4.3).")
P("Para medir cuánto usa el modelo cada variable se usan los valores SHAP (Lundberg y Lee, 2017), que reparten el "
  "pronóstico de cada fila entre las variables, de modo que la suma de las contribuciones da el pronóstico:")
a(ec(e(r("f"), par(r("x")), r("="), sub(r("φ"), r("0")), r("+"), suma(e(r("j"), r("="), r("1")), r("M"), sub(r("φ"), r("j"))))))
P("La importancia de una variable es el promedio de $|φ_j|$ en un año que el modelo no vio en el entrenamiento.")

a(h2("2.3 SARIMA y SARIMAX"))
P("Un modelo SARIMA$(p,d,q)(P,D,Q)_s$ describe una serie con su propia historia: una parte autorregresiva, diferencias para "
  "volverla estacionaria y una media móvil de los choques pasados, cada una con su versión estacional (Box et al., 2015; "
  "Hyndman y Athanasopoulos, 2021). Con el operador de rezago B ($By_t=y_{t−1}$):")
a(ec(e(sub(r("φ"), r("p")), par(r("B")), sub(r("Φ"), r("P")), par(sup(r("B"), r("s"))), sup(par(e(r("1"), r("−"), r("B"))), r("d")), sup(par(e(r("1"), r("−"), sup(r("B"), r("s")))), r("D")), sub(r("η"), r("t")), r("="), sub(r("θ"), r("q")), par(r("B")), sub(r("Θ"), r("Q")), par(sup(r("B"), r("s"))), sub(r("ε"), r("t")))))
P("SARIMAX agrega variables externas como una regresión cuyos errores siguen ese proceso: $y_t=β'x_t+η_t$. Aquí la "
  "serie de cada modelo es el logaritmo del precio de una hora fija, un dato por día, y el ciclo estacional es la semana "
  "(s = 7). El orden de diferenciación se elige con pruebas: KPSS (Kwiatkowski et al., 1992) para d y OCSB (Osborn et al., "
  "1988) para D. Los órdenes p, q, P y Q se eligen con el criterio de Akaike corregido, que castiga los parámetros en "
  "muestras pequeñas (Hurvich y Tsai, 1989):")
a(ec(e(tx("AICc"), r("="), r("−2"), tx("ln"), r("L"), r("+"), r("2k"), r("+"), frac(e(r("2k"), par(e(r("k"), r("+"), r("1")))), e(r("n"), r("−"), r("k"), r("−"), r("1"))))))
P("Para revisar si los residuos quedan sin autocorrelación se usa la prueba de Ljung y Box (1978), con m rezagos:")
a(ec(e(r("Q"), r("="), r("n"), par(e(r("n"), r("+"), r("2"))), suma(e(r("k"), r("="), r("1")), r("m"), frac(sup(sub(gorro(r("ρ")), r("k")), r("2")), e(r("n"), r("−"), r("k")))))))

a(h2("2.4 Redes LSTM"))
P("Una red LSTM (Hochreiter y Schmidhuber, 1997) procesa una secuencia paso a paso y guarda un estado de memoria $c_t$. "
  "Tres compuertas deciden qué olvidar, qué agregar y qué mostrar en cada paso:")
sig = lambda nombre, W_: e(sub(r(nombre), r("t")), r("="), r("σ"), par(e(sub(r("W"), r(W_)), par(e(sub(r("h"), r("t−1")), r(","), sub(r("x"), r("t"))), "[", "]"), r("+"), sub(r("b"), r(W_)))))
a(ec(e(sig("f", "f"), r(",   "), sig("i", "i"), r(",   "), sig("o", "o"))))
a(ec(e(sub(r("c"), r("t")), r("="), sub(r("f"), r("t")), r("⊙"), sub(r("c"), r("t−1")), r("+"), sub(r("i"), r("t")), r("⊙"), tx("tanh"), par(e(sub(r("W"), r("c")), par(e(sub(r("h"), r("t−1")), r(","), sub(r("x"), r("t"))), "[", "]"), r("+"), sub(r("b"), r("c")))), r(",    "), sub(r("h"), r("t")), r("="), sub(r("o"), r("t")), r("⊙"), tx("tanh"), par(sub(r("c"), r("t"))))))
P("La ventaja frente a XGBoost es que la red ve la secuencia completa de varias semanas, en lugar de resúmenes hechos a "
  "mano (rezagos y medias), y puede aprovechar variables lentas como el nivel de los embalses. En un esquema "
  "codificador-decodificador (Sutskever et al., 2014), una LSTM resume el pasado en su estado final y otra genera la "
  "semana siguiente día por día a partir de ese estado.")

a(h2("2.5 Evaluación"))
P("Sea $e_{t,H}$ el error en logaritmo del pronóstico hecho desde el día t para la hora H. Las métricas principales son:")
a(ec(e(tx("RMSE"), r("="), raiz(e(frac(r("1"), r("N")), suma(r("t,H"), "", sup(sub(r("e"), r("t,H")), r("2"))))), r(",    "), tx("Mejora"), r("="), r("1"), r("−"), frac(sub(tx("RMSE"), tx("modelo")), sub(tx("RMSE"), tx("ingenuo"))))))
P("También se reportan, en COP/kWh, el MAE, el MAPE, el sesgo medio (MBE, pronóstico menos real) y el nRMSE (RMSE "
  "dividido por el precio medio), como en Salazar-Peña et al. (2025). Para decidir si una mejora es real o suerte se usa "
  "la prueba de Diebold y Mariano (1995). Como las 24 horas de un día comparten el estado del sistema, la prueba se hace "
  "sobre el error cuadrático promedio de cada día:")
a(ec(e(sub(r("d"), r("t")), r("="), sub(barra(sup(r("e"), r("2"))), e(r("t"), r(","), tx("modelo"))), r("−"), sub(barra(sup(r("e"), r("2"))), e(r("t"), r(","), tx("ingenuo"))), r(",     "), tx("DM"), r("="), frac(barra(r("d")), raiz(frac(gorro(r("V")), r("T")))))))
P("Los objetivos de días seguidos se traslapan (dos pronósticos a 9 días comparten 8 días), así que los $d_t$ están "
  "autocorrelacionados. Por eso la varianza se estima con Newey y West (1987), con pesos de Bartlett y L = h − 1 + 7 "
  "rezagos: h − 1 por el traslape y 7 por la regla automática de Newey y West (1994) con unos 1.750 días:")
a(ec(e(gorro(r("V")), r("="), sub(gorro(r("γ")), r("0")), r("+"), r("2"), suma(e(r("k"), r("="), r("1")), r("L"), e(par(e(r("1"), r("−"), frac(r("k"), e(r("L"), r("+"), r("1"))))), sub(gorro(r("γ")), r("k")))))))
P("Por último, para entender de dónde viene el error, cada error diario se parte en el nivel del día (el promedio de "
  "las 24 horas) y la forma (cómo se reparte dentro del día). Las dos partes suman exactamente el error cuadrático:")
a(ec(e(frac(r("1"), r("24")), suma(e(r("H"), r("="), r("1")), r("24"), sup(sub(r("e"), r("t,H")), r("2"))), r("="), sup(sub(barra(r("e")), r("t")), r("2")), r("+"), frac(r("1"), r("24")), suma(e(r("H"), r("="), r("1")), r("24"), sup(par(e(sub(r("e"), r("t,H")), r("−"), sub(barra(r("e")), r("t")))), r("2"))))))

# ------------------------------------------------------------------ 3. datos
a(h1("3. Datos"))
a(h2("3.1 Descarga (paso 1)"))
P("El script 1_descargar.py baja todo a la carpeta datos/. La primera vez tarda varias horas, porque hay más de diez "
  "años de datos por planta y por hora; después solo actualiza lo nuevo en unos cinco minutos.")
a(titulo_tabla("Fuentes de datos."))
a(tabla([["Fuente", "Qué trae", "Cómo se baja"],
         ["XM (API, librería pydataxm)", "Precio, demanda, generación real y programada, disponibilidad, ofertas, hidrología, contratos, restricciones, intercambios, cargos regulados", "Por tramos de 30 días"],
         ["SIMEM (XM)", "Costo marginal del despacho y del redespacho, pronóstico de demanda del CND, generación ideal, CO2, planta marginal", "API de SIMEM"],
         ["NOAA, Climate Prediction Center", "Temperatura semanal del Pacífico en las regiones Niño 1+2, 3, 3.4 y 4; ONI y RONI", "Archivos de texto"],
         ["Open-Meteo, reanálisis ERA5", "Lluvia diaria en ocho puntos, uno por cuenca de los embalses grandes, desde 2000", "API de archivo histórico"],
         ["IDEAM", "Predicción de lluvia por región y fase de El Niño", "Boletines en PDF (paso 1b)"],
         ["datos.gov.co", "Tasa de cambio (TRM)", "Conjunto 32sa-8pi3"],
         ["XM, PARATEC", "Listado de plantas con tecnología, combustible y tipo de despacho", "A mano"]],
        anchos=[2.3, 5, 2]))
P("Algunas decisiones de la descarga:")
a(lista(["Los códigos de métrica de XM se comprobaron uno por uno: se pidió una ventana ya descargada y se verificó que los "
         "valores coincidieran exactamente. El ONI y la TRM automáticos también se compararon con los archivos que antes se "
         "bajaban a mano, con diferencia cero.",
         "Al actualizar se vuelve a pedir el último mes, porque XM corrige los datos recientes durante varias semanas "
         "(liquidaciones provisionales).",
         "El listado de plantas se baja a mano porque el de la API solo trae las activas: sin las retiradas desaparecen "
         "34 plantas, entre ellas Jepírachi, la única eólica del país hasta 2023.",
         "Todo se guarda en CSV comprimido. Los datos crudos no se suben al repositorio; se regeneran con el paso 1.",
         "Se dejaron por fuera series que empiezan entre 2018 y 2025 o que faltan en más de 15% de los días (irradiación "
         "solar, variantes del precio de escasez), porque un modelo que entrena desde 2015 no las puede usar."]))

a(h2("3.2 Del dato crudo a los paneles (pasos 2 y 2b)"))
P("XM entrega cada serie en uno de tres formatos: un valor por día para el sistema, un valor por día para cada río, "
  "embalse o planta, o 24 valores por día para cada planta. Para juntarlas hay que decidir cómo se suman las plantas y "
  "las horas según lo que mide cada serie:")
a(titulo_tabla("Regla de agregación según lo que mide cada serie."))
a(tabla([["Qué mide", "Entre plantas", "Entre horas", "Ejemplos"],
         ["Energía (un flujo)", "suma", "suma", "generación, demanda, importaciones"],
         ["Capacidad o disponibilidad (un nivel)", "suma", "promedio", "disponibilidad declarada"],
         ["Precio", "promedio", "promedio", "costo marginal, precio de contratos"],
         ["Porcentaje por embalse", "promedio ponderado por capacidad", "", "volumen útil por embalse"]],
        anchos=[3, 2.2, 1.5, 3.3], alinear_num=False))
P("El paso 2 arma el panel diario y el paso 2b el panel horario: 4.300 días por 24 horas, 103.200 filas del 1 de enero "
  "de 2015 al 9 de octubre de 2026. El precio horario llega hasta el 6 de octubre y no tiene huecos. Hay dos versiones: "
  "una con las 66 columnas que cambian dentro del día y otra con 178, que suma 112 variables que solo existen por día "
  "(hidrología, lluvia, El Niño, IDEAM, cargos regulados, forma de la curva de ofertas), repetidas en las 24 horas.")
P("Además se reconstruye la curva de mérito de cada hora a partir de las ofertas y la disponibilidad de cada planta: "
  "cuánta capacidad se ofrece por debajo de 200 y 500 COP/kWh, el precio de la planta que queda al margen, el salto a "
  "la siguiente y la holgura entre capacidad y demanda. El precio de esa planta marginal tiene correlación de 0,94 con el "
  "precio de la hora, así que solo puede entrar rezagado.")

a(h2("3.3 Limpieza y datos faltantes"))
P("Durante la construcción de los paneles aparecieron varios problemas de los datos, que se corrigieron así:")
a(titulo_tabla("Problemas encontrados en los datos y cómo se trataron."))
a(tabla([["Problema", "Tratamiento"],
         ["La hora de SIMEM empieza una hora antes que la de XM", "Se corrige el desfase; se comprobó con 240 horas de costo marginal, que coinciden al 100%"],
         ["En 70 días de 2019, 2020 y 2024 SIMEM trae un “mercado” MC-SIN que es el total nacional; el pronóstico de demanda salía al doble en 1.680 horas", "Se deja fuera MC-SIN"],
         ["El 5 y el 6 de octubre de 2026 XM publicó la demanda incompleta (22% de lo normal)", "Un día cuya demanda es menos de la mitad de la mediana de los 28 días anteriores queda con la demanda vacía; ningún otro día desde 2015 cumple la regla"],
         ["Eventos sin fila: vertimientos, importaciones, generación por combustible", "Se llenan con 0; en once años ninguna de esas series trae un cero, lo que indica que XM no publica fila cuando el evento no ocurre"],
         ["Huecos de uno a tres días (festivos, fallas de publicación)", "Último valor conocido, a la misma hora del día anterior; solo mira al pasado"],
         ["Variables que no existían al empezar (El Quimbo, predicción del Pacífico del IDEAM)", "Salen si tienen más de 1% de faltantes desde marzo de 2015; imputarlas sería inventar historia"],
         ["Alertas del IDEAM con ceros falsos en 2019-2021", "No se usan"],
         ["Pérdidas negativas en 270 horas y generación solar de noche desde 2025 (probablemente baterías)", "Se conservan; son ajustes de liquidación o datos reales pequeños"]],
        anchos=[4.5, 5.5], alinear_num=False))
P("Las técnicas de imputación del curso de Feature Engineering de Galli (media, mediana, KNN) están pensadas para huecos "
  "al azar en datos sin orden en el tiempo. Aquí se usa el último valor conocido porque nunca mira al futuro. Los paneles "
  "pasan además varias comprobaciones: el promedio de las 24 horas reproduce el precio diario (diferencia máxima de 0,004 "
  "COP/kWh), las sumas horarias de demanda y generación programada reproducen los totales diarios, cada hora tiene "
  "exactamente una planta marginal y el CO2 por combustible suma el total.")

a(h2("3.4 Cuándo se conoce cada dato"))
P("Es lo que más importa al pronosticar. Un dato solo puede entrar al pronóstico desde el día en que se publica, no "
  "desde el día al que se refiere. Los atrasos se midieron consultando las fuentes, no se supusieron.")
a(lista(["El precio: el 10 de octubre de 2026 el último precio publicado era del 8, y el 2 de noviembre (festivo) era del "
         "30 de octubre. Es decir, dos o tres días de atraso.",
         "Las demás series: con dos sondeos de toda la API (9 y 10 de octubre de 2026), guardados en datos/sondeos/.",
         "El despacho programado: con una consulta automática cada hora en GitHub Actions. El despacho del día aparece "
         "esa misma madrugada (no estaba a la 1:02 y sí a las 9:22) y nunca está la noche anterior. Por eso el despacho "
         "de mañana no se usa."]))
a(figura(FIG / "f04_atrasos_publicacion.png", "Hasta qué día se conoce cada grupo de datos el día R en que se hace el "
         "pronóstico. El despacho programado de hoy está dos días más al día que el precio; las ofertas, diez días atrás.", 16))
P("La consecuencia más importante se descubrió tarde. Los paneles 2c y 2d, que usan XGBoost y SARIMAX, paran todo en el "
  "día t del último precio, aunque el despacho programado de hoy y la hidrología de ayer ya se conocen en R = t + 2. "
  "Es una regla conservadora: no mete información del futuro, pero desperdicia dos días de información fresca. El panel "
  "de la LSTM (paso 2e) corrige esto alineando cada dato a su publicación, y la sección 10.3 muestra cuánto vale.")

a(h2("3.5 Exploración de la serie"))
P("Además del cambio de nivel por meses (figura 1), el precio tiene una forma de día muy marcada (figura 5). Entre "
  "semana el pico de las 19 a las 21 horas sube a más de 1,6 veces el promedio del día, y la madrugada queda 20% por "
  "debajo. Los sábados, domingos y festivos el pico es menor y la madrugada no baja tanto. Por eso el día de la semana y "
  "los festivos del día pronosticado entran siempre a los modelos.")
a(figura(FIG / "f03_perfil_horario.png", "Forma promedio del día en 2023-2026: precio de cada hora dividido por el "
         "promedio de su día, según el tipo de día.", 14.5))

# ------------------------------------------------------------------ 4. variables
a(h1("4. Variables y selección"))
a(h2("4.1 Variables base (paso 2c)"))
P("El paso 2c guarda 134 variables base, una columna por variable, ya transformada y sin rezagos: el logaritmo del "
  "precio, 44 horarias y 89 diarias. Este paso no mira el objetivo ni hace pruebas estadísticas: cada variable se "
  "transforma con una regla fija según lo que mide.")
a(titulo_tabla("Grupos de variables base."))
a(tabla([["Grupo", "Cuántas", "Ejemplos y regla"],
         ["Precio", "1", "lp = ln(precio)"],
         ["Horarias del sistema", "44", "Demanda, disponibilidad, generación por tecnología, despacho y redespacho, curva de mérito, restricciones; cantidades sobre la demanda o la generación de la hora, precios en logaritmo"],
         ["Aportes", "7", "Porcentaje del sistema, caudal sobre su media histórica, concentración entre ríos"],
         ["Embalses", "10", "Volumen útil del sistema y de los embalses grandes; días de autonomía = volumen útil / demanda media de 7 días"],
         ["Lluvia (ERA5)", "21", "Acumulados, anomalías frente a 2000-2014, por cuenca, contraste norte-sur"],
         ["El Niño (NOAA)", "11", "Anomalías de las 4 regiones, tendencias de 4 y 12 semanas, ONI, RONI"],
         ["IDEAM", "7", "Predicción de lluvia por región, déficit, fase de El Niño"],
         ["Mezcla por planta", "13", "Gas, carbón, líquidos y filo de agua como fracción de la generación; concentración"],
         ["Curva de ofertas del día", "10", "Percentiles del precio de oferta, pendiente, capacidad barata"],
         ["Sistema y regulación", "10", "Capacidad efectiva, energía en firme, margen de reserva, cargo por confiabilidad, precio de escasez, TRM"]],
        anchos=[2.4, 1, 6.6]))
P("Las cantidades diarias del sistema se dividen por la media móvil de 7 días de la demanda, que solo mira hacia atrás "
  "y no mete el ruido de domingos y festivos. Tres variables nuevas salen de cómo se forma el precio (decisión del autor): "
  "error_cmg_despacho, cuánto se equivocó el despacho programado frente al precio; brecha_escasez, la distancia al "
  "precio de escasez regulatorio, y presion_hidro_horaria, la demanda de la hora por cada MWh de agua que entra.")
P("El calendario se codifica además con seno y coseno, para que la hora 24 quede junto a la hora 1 y el domingo junto "
  "al lunes (Galli, sección 15):")
a(ec(e(sub(tx("hora"), tx("sen")), r("="), tx("sen"), par(frac(e(r("2π"), r("H")), r("24"))), r(",     "), sub(tx("hora"), tx("cos")), r("="), tx("cos"), par(frac(e(r("2π"), r("H")), r("24"))))))

a(h2("4.2 Columnas derivadas"))
P("De cada variable base, features.py arma en memoria rezagos, medias móviles, tendencia y variabilidad. Los rezagos "
  "del precio salen del modelo LEAR (Lago et al., 2021), con 14, 21 y 28 días por el ciclo semanal; las medias de día, "
  "semana y mes, del modelo HAR (Corsi, 2009). Todo usa horas que ya pasaron al cierre del día t, y una ventana solo se "
  "calcula si tiene al menos 75% de sus datos.")
a(titulo_tabla("Catálogo de columnas derivadas."))
a(tabla([["Familia", "Precio", "Cada horaria", "Cada diaria"],
         ["Rezagos en horas", "1 a 23", "0 a 3", "—"],
         ["Misma hora, días antes", "1, 2, 3, 7, 14, 21, 28", "1, 2, 3, 7, 14", "días 0, 1, 2, 7"],
         ["Resumen del día t", "hora 24, promedio, rampa", "igual", "—"],
         ["Media móvil a la misma hora", "7 y 30 días", "igual", "7 y 30 días"],
         ["Tendencia", "—", "media de 7 menos media de 30", "cambio en 7 días y media de 7 menos de 30"],
         ["Variabilidad", "desviación de 7 y 30 días; de 24 y 168 horas", "igual", "igual"],
         ["Memoria de picos", "máximo de 24 horas y de 7 días menos lp", "—", "—"],
         ["Columnas por variable", "43", "21", "10"]],
        anchos=[2.6, 3, 2.4, 2.4], alinear_num=False))
P("En total son 1.861 columnas derivadas sobre 101.712 filas (desde marzo de 2015), unos 800 MB. Una prueba de fuga "
  "corre cada vez que se arma el panel: se alteran los datos crudos posteriores a una fecha y se reconstruye todo; las "
  "filas anteriores no cambian.")

a(h2("4.3 Selección de columnas (paso 2d)"))
P("Con 1.861 columnas y unos 1.750 días de entrenamiento hay que elegir. La selección se hizo por horizonte, en tres "
  "etapas, y desde el 1 de noviembre de 2026 está congelada:")
a(lista(["Limpieza, con 2015-2019. Salen 10 columnas casi constantes (un mismo valor en 99% de las horas), 106 "
         "inestables (más de 25% de sus valores de 2018-2019 quedan fuera del rango de 2015-2017, como los precios de "
         "contratos en pesos) y 12 niveles del cargo por confiabilidad y la TRM, que siguen al dólar y no al mercado "
         "(CREG 071 de 2006, art. 29). De cada grupo con correlación de Spearman mayor a 0,95 queda la más correlacionada "
         "con el objetivo. Quedan unas 1.290.",
         "Orden, con 2015-2019. Se entrena XGBoost con 2015-2017 y se mide en 2018, y con 2015-2018 y se mide en 2019, "
         "con 10 columnas de ruido (copias de columnas al azar con los días barajados). Sigue la columna cuyo |SHAP| "
         "promedio le gana al mejor ruido en los dos años; es la idea de Boruta (Kursa y Rudnicki, 2010).",
         "Cuántas, con 2020-2022. Con las primeras k del orden (10, 20, 40, 80, 160 o todas) se entrena con 2015-2019 y "
         "se mide en 2020-2022. Entra el k más chico cuyo error no pasa el del mejor más un error estándar (Hastie et al., "
         "2009, sección 7.10)."], ordenada=True))
a(figura(FIG / "f05_embudo_seleccion.png", "Cuántas columnas quedan en cada etapa de la selección, para h = 3.", 14))
a(titulo_tabla("Resultado de la selección por horizonte. La mejora es del RMSE en log frente al ingenuo del día en 2020-2022, con el modelo de prueba del paso 2d."))
a(tabla([["h", "Tras la limpieza", "Le ganan al ruido", "Entran", "RMSE log modelo / ingenuo", "Mejora"],
         ["1", "1.291", "40", "20", "0,133 / 0,175", "24,2%"],
         ["2", "1.291", "13", "10", "0,166 / 0,212", "21,7%"],
         ["3", "1.289", "15", "10", "0,206 / 0,240", "14,2%"],
         ["4", "1.290", "43", "20", "0,233 / 0,263", "11,4%"],
         ["5", "1.291", "89", "10", "0,259 / 0,278", "6,8%"],
         ["6", "1.290", "99", "10", "0,282 / 0,292", "3,3%"],
         ["7", "1.289", "117", "20", "0,308 / 0,302", "−1,9%"],
         ["14", "1.288", "77", "10", "0,382 / 0,386", "0,9%"],
         ["30", "1.290", "105", "10", "0,458 / 0,500", "8,2%"]],
        anchos=[0.6, 1.6, 1.6, 1.1, 2.4, 1.2]))
P("En total entran 57 columnas de 32 variables: 14 del precio, 23 de variables horarias y 20 de diarias. Lo que más "
  "pesa es el propio precio, en particular cuánto se aparta el precio de hoy de sus medias de 7 y 30 días a esa hora "
  "(reversión a la media), que entra en los nueve horizontes. A un día manda lo ya decidido para mañana (costo marginal "
  "programado, pronóstico de demanda). Con el horizonte, el peso pasa a la hidrología y el clima: de h = 1 a h = 30 la "
  "lluvia pasa de 4% a 12% de la importancia y los embalses de 2% a 12%. Solo con el precio y el calendario el modelo "
  "pierde contra el ingenuo en ocho de los nueve horizontes.")
nota("Tres decisiones de esta etapa se tomaron mirando 2020-2022: cuántas columnas entran (por diseño), el umbral del "
     "filtro de estabilidad y la regla del dólar. Por eso los errores de validación de la tabla son optimistas y 2020-2022 "
     "no sirve para estimar el error futuro.")

# ------------------------------------------------------------------ 5. diseño
a(h1("5. Diseño del pronóstico"))
a(h2("5.1 Regla de información y partición"))
P("Cada fila es un par (día t, hora H) y se para al cierre del día t. El objetivo es la ecuación (2) para h = 3 a 9. "
  "Entre entrenamiento y evaluación se dejan h + 1 días de purga, para que ningún objetivo del entrenamiento caiga en el "
  "periodo evaluado, y se parte siempre por fechas, nunca por filas.")
a(titulo_tabla("Uso de cada periodo."))
a(tabla([["Periodo", "Uso"],
         ["2015-2019", "Entrenamiento y primeras selecciones (limpieza, orden de variables, órdenes de SARIMAX, exógenas)"],
         ["2020-2022", "Validación: cuántas variables, hiperparámetros de XGBoost, versión final de SARIMAX"],
         ["2023-2025", "Prueba principal, usada una sola vez"],
         ["2026, hasta el 6 de octubre", "Segunda prueba, usada una sola vez"],
         ["9 al 15 de octubre de 2026", "Semana de demostración: pronóstico guardado antes de bajar el precio real"]],
        anchos=[2.5, 7.5], alinear_num=False))
P("En la prueba, los modelos se reentrenan el 1 de cada mes con todo lo anterior (walk-forward; Hyndman y "
  "Athanasopoulos, 2021, sección 5.10) y pronostican desde todos los días del mes. Los dos modelos se evalúan en "
  "exactamente las mismas filas: 228.984 pronósticos por modelo en 2023-2025.")
a(h2("5.2 Criterio para decir que un modelo funciona"))
P("Se fijó el 1 de noviembre de 2026, antes de abrir la prueba de XGBoost. Un modelo funciona en un bloque de horizontes "
  "si cumple dos condiciones:")
a(lista(["El RMSE en logaritmo baja al menos 5% frente al mejor de los dos ingenuos en ese bloque. El umbral de 5% es "
         "decisión del autor.",
         "La prueba de Diebold y Mariano contra ese mismo ingenuo da p < 0,05."], ordenada=True))
P("Los bloques originales eran h = 3, 3 a 7, 8 a 14 y 15 a 30. Después de ver la prueba de 2026 de XGBoost el alcance "
  "se redujo a una semana, y el bloque h = 3 a 9 quedó fijo antes de la prueba de SARIMAX. h = 1 y h = 2 se reportan "
  "pero no cuentan, porque el primer pronóstico real es h = 3.")

# ------------------------------------------------------------------ 6. XGBoost
cfg = json.loads((RES / "modelo_xgboost/configuracion_final.json").read_text(encoding="utf-8"))
a(h1("6. XGBoost"))
a(h2("6.1 Diseño"))
P("Un modelo directo por horizonte. Cada modelo junta las 24 horas, con la hora como columna, y recibe las 10 o 20 "
  "columnas elegidas para su horizonte, el logaritmo del precio, el calendario del día t y el del día objetivo (día de la "
  "semana y festivo). Los modelos de h = 3 a 7 tienen hiperparámetros propios; h = 8 y 9 usan los de h = 7 y no tuvieron "
  "validación propia.")
a(h2("6.2 Hiperparámetros"))
P("Se eligieron solo con 2020-2022, en tres etapas (notebook 4):")
a(lista(["Búsqueda: 30 combinaciones al azar, las mismas para cada horizonte, en tres pliegues anuales (entrenar con todo "
         "lo anterior y medir en 2020, 2021 y 2022). El número de árboles se lee de la curva de error cada 50 árboles, sin "
         "volver a entrenar. Fuente de los parámetros: ML Zoomcamp, módulo de árboles.",
         "Walk-forward mensual: las 3 mejores combinaciones de cada horizonte, reentrenando el 1 de cada mes de 2020 a 2022. "
         "Queda la más simple de las que están a un error estándar de la mejor: menos profundidad y hojas más grandes.",
         "Variantes contra la elegida: pérdida pseudo-Huber por los picos, entrenar solo con los últimos 3 años y restar "
         "el sesgo de los últimos 30 días ya conocidos. Ninguna bajó el error más de un error estándar, así que todos los "
         "horizontes quedaron con la versión base. También se comparó reentrenar cada mes contra cada semana en 2022."],
        ordenada=True))
a(titulo_tabla("Configuración congelada (resultados/modelo_xgboost/configuracion_final.json)."))
filas = [["h", "Profundidad", "Mín. horas por hoja", "Árboles", "Subsample", "Colsample", "λ"]]
for h in ("3", "4", "5", "6", "7"):
    q = cfg[h]["parametros"]
    filas.append([h if h != "7" else "7 (y 8, 9)", q["max_depth"], q["min_child_weight"], q["n_estimators"],
                  f'{q["subsample"]:.2f}'.replace(".", ","), f'{q["colsample_bytree"]:.2f}'.replace(".", ","),
                  f'{q["reg_lambda"]:.2f}'.replace(".", ",")])
a(tabla(filas, anchos=[1.4, 1.2, 1.7, 1, 1.1, 1.1, 0.8]))
P("min_child_weight se cuenta en horas: 240 obliga a que cada hoja tenga el equivalente a 10 días. Las configuraciones "
  "elegidas son árboles poco profundos (3 a 6 niveles) con mucha regularización, lo que tiene sentido con datos tan "
  "ruidosos.")

a(h2("6.3 Resultados con el criterio original (30 días)"))
a(titulo_tabla("Veredicto de XGBoost con los bloques fijados antes de la prueba. El mejor ingenuo fue el del día en todos los bloques salvo h = 15 a 30 en 2026 (semanal)."))
a(tabla([["Bloque", "Mejora 2023-2025", "DM p", "Mejora 2026", "DM p", "Funciona"],
         ["h = 3", "17,9%", "< 0,001", "19,5%", "< 0,001", "Sí, en los dos"],
         ["h = 3 a 7", "12,5%", "< 0,001", "11,6%", "< 0,001", "Sí, en los dos"],
         ["h = 8 a 14", "10,7%", "0,007", "6,4%", "0,096", "Solo en 2023-2025"],
         ["h = 15 a 30", "13,1%", "0,016", "−7,2%", "0,361", "Solo en 2023-2025"]],
        anchos=[1.6, 1.6, 1.1, 1.4, 1.1, 2.2]))
a(figura(RES / "modelo_xgboost/mejora_por_horizonte.png", "Mejora del RMSE en log de XGBoost en 2023-2025, por "
         "horizonte, frente a los dos ingenuos. La línea vertical marca h = 3, el primer pronóstico real.", 15.5))
P("En 2023-2025 XGBoost le gana al mejor ingenuo en los 30 horizontes y en los tres años. Pero en 2026, el año de mayor "
  "variabilidad del panel (la mediana del precio pasó de 164 a 385 COP/kWh), solo pasa hasta h = 7: en h = 8 a 14 la "
  "mejora no es significativa y en h = 15 a 30 pierde contra el ingenuo semanal. Reentrenar cada mes no cambió nada "
  "frente a un modelo entrenado una sola vez con 2015-2025.")

a(h2("6.4 Alcance final: una semana"))
nota("El alcance de una semana se eligió después de ver la prueba de 2026. Los modelos son los mismos y no se reentrenó "
     "nada, pero el bloque h = 3 a 9 no hacía parte del criterio fijado antes de la prueba de XGBoost, así que sus números "
     "salen algo favorecidos.")
a(titulo_tabla("XGBoost en la semana h = 3 a 9."))
a(tabla([["Periodo", "RMSE log", "Ingenuo del día", "Mejora", "DM t", "DM p"],
         ["2023-2025", "0,443", "0,502", "11,6%", "−4,82", "< 0,001"],
         ["2026, hasta el 6 de octubre", "0,392", "0,435", "10,0%", "−3,29", "0,001"],
         ["2023", "0,474", "0,544", "12,9%", "−3,32", "0,001"],
         ["2024", "0,470", "0,508", "7,6%", "−1,65", "0,100"],
         ["2025", "0,379", "0,447", "15,3%", "−4,75", "< 0,001"]],
        anchos=[2.6, 1.2, 1.6, 1.1, 1, 1.1]))
P("En 2024 no pasa por la crisis de El Niño de septiembre y octubre, cuando el precio subió más rápido de lo que el "
  "modelo podía anticipar. La ventaja de XGBoost está sobre todo en los errores grandes: en MAE la mejora es menor "
  "(13,2% en h = 3 y 6,4% en h = 3 a 7) y en la mediana del error absoluto el ingenuo gana en h = 3 y h = 7.")

a(h2("6.5 Semana de demostración"))
P("Con datos hasta el 6 de octubre de 2026 se pronosticó la semana del 9 al 15 de octubre y se guardó el pronóstico "
  "antes de bajar el precio real. RMSE en log de 0,201 contra 0,234 del ingenuo del día (14,1% menos) y MAPE de 15,9%. "
  "Fue mejor que los dos ingenuos en 5 de 7 días; subestimó los picos del viernes y el sábado y sobrestimó los del "
  "martes y el miércoles. Fue una semana más fácil que lo normal: el 79% de los cortes de 2026 tuvo más error. Una sola "
  "semana es una demostración, no una medida del modelo.")
a(figura(RES / "modelo_xgboost/semana_final.png", "Semana del 9 al 15 de octubre de 2026: pronóstico de XGBoost hecho "
         "con datos hasta el 6 de octubre, contra el precio real.", 15.5))

# ------------------------------------------------------------------ 7. SARIMAX
a(h1("7. SARIMAX"))
P("SARIMAX es el modelo lineal de referencia. Sirve para responder una pregunta concreta: si un modelo más simple "
  "tampoco anticipa el nivel del precio, el límite está en la información y no en XGBoost. Se hizo en R con el paquete "
  "forecast (Hyndman y Athanasopoulos, 2021). Todas sus decisiones se tomaron con datos hasta 2022, sin mirar los "
  "resultados de XGBoost en la prueba.")
a(h2("7.1 Diseño"))
P("Son 24 modelos, uno por hora. Cada uno modela la serie diaria del logaritmo del precio de esa hora, con ciclo semanal "
  "(s = 7) y el indicador de festivo del día objetivo como regresor. El día de la semana ya lo cubre el ciclo de 7 días. "
  "Desde cada día t se pronostican 9 pasos y se usan h = 3 a 9. Los coeficientes se reestiman el 1 de cada mes; dentro "
  "del mes solo se actualiza el estado del modelo con los datos nuevos, sin reestimar.")
a(h2("7.2 Órdenes"))
P("Con 2015-2019, KPSS y OCSB dieron d = 1 y D = 0 en las 24 horas. Con AICc salieron 12 órdenes distintos entre horas; "
  "el más frecuente fue $(1,1,2)(0,0,2)_7$. En validación, un orden distinto por hora no le ganó a ese orden común "
  "(sección 7.4), así que el modelo final de cada hora H es:")
a(ec(e(sub(r("y"), r("t")), r("="), r("β"), r("·"), sub(tx("festivo"), r("t")), r("+"), sub(r("η"), r("t")), r(",    "), par(e(r("1"), r("−"), sub(r("φ"), r("1")), r("B"))), par(e(r("1"), r("−"), r("B"))), sub(r("η"), r("t")), r("="), par(e(r("1"), r("+"), sub(r("θ"), r("1")), r("B"), r("+"), sub(r("θ"), r("2")), sup(r("B"), r("2")))), par(e(r("1"), r("+"), sub(r("Θ"), r("1")), sup(r("B"), r("7")), r("+"), sub(r("Θ"), r("2")), sup(r("B"), r("14")))), sub(r("ε"), r("t")))))
P("donde $y_t$ es el logaritmo del precio de la hora H el día t. La prueba de Ljung-Box a 14 rezagos, en 2015-2019, no "
  "rechaza ruido blanco en los residuos de 17 de las 24 horas; en las otras 7 el orden común deja algo sin explicar.")
a(h2("7.3 Variables externas"))
P("Para que se conozcan en t en todos los horizontes, las variables externas solo podían entrar con rezago de 9 días. Las "
  "candidatas fueron todas las variables base sin vacíos en 2015-2019 que pasan la limpieza del paso 2d: 122 de 133. "
  "Pasaron por tres filtros seguidos:")
a(titulo_tabla("Filtros de variables externas de SARIMAX, 2015-2019."))
a(tabla([["Filtro", "Resultado"],
         ["Preblanqueo (Box et al., 2015): correlación cruzada en el rezago 9 entre lp y la variable, filtradas con el ARIMA de cada hora, significativa al 5% con Bonferroni en al menos 12 horas", "Pasa 1 de 122: holgura_rel (holgura entre capacidad ofertada y demanda), en justo 12 horas"],
         ["Selección hacia adelante con AICc sumado en las 24 horas", "La acepta: de −23.215 a −23.462"],
         ["Prueba t del coeficiente", "La acepta: p < 0,05 en 17 de 24 horas"]],
        anchos=[6, 4], alinear_num=False))
a(h2("7.4 Validación"))
P("En walk-forward mensual de 2020-2022, una versión más compleja entraba solo si le ganaba a la anterior con "
  "Diebold-Mariano p < 0,05:")
a(titulo_tabla("Validación de SARIMAX, h = 3 a 9, 2020-2022."))
a(tabla([["Versión", "RMSE log", "DM p contra la anterior", "Queda"],
         ["Un solo orden, sin exógenas", "0,2805", "", "Sí"],
         ["Un orden por hora", "0,2806", "0,865", "No"],
         ["Con holgura_rel", "0,2806", "0,970", "No"]],
        anchos=[4, 1.6, 2.6, 1.2]))
P("holgura_rel pasó las tres pruebas dentro de la muestra y no mejoró el pronóstico fuera de ella. El modelo final no "
  "tiene variables externas, y ese también es un resultado. El ingenuo del día en esa ventana da 0,2943: la mejora fue "
  "de 4,7% (p = 0,018), un poco por debajo del umbral.")
a(h2("7.5 Resultados en la prueba"))
a(titulo_tabla("Veredicto de SARIMAX. El bloque h = 3 a 9 se fijó antes de su prueba."))
a(tabla([["Bloque", "Mejora 2023-2025", "p", "Mejora 2026", "p", "Funciona"],
         ["h = 3 a 9 (principal)", "6,4%", "< 0,001", "5,6%", "< 0,001", "Sí, en los dos"],
         ["h = 3", "7,7%", "< 0,001", "6,5%", "< 0,001", "Sí, en los dos"],
         ["h = 3 a 7", "6,4%", "< 0,001", "5,6%", "< 0,001", "Sí, en los dos"],
         ["h = 8 a 9", "6,4%", "< 0,001", "5,6%", "0,001", "Sí, en los dos"]],
        anchos=[2.4, 1.6, 1.1, 1.4, 1.1, 1.8]))
P("La mejora es menor que la de XGBoost, pero casi no cambia con el horizonte ni con el año (figuras 9 y 10). El "
  "intervalo de 80% queda algo estrecho: cubre 71,1% de los precios en 2023-2025 (62,4% en 2023) y 75,4% en 2026. En la "
  "semana del 9 al 15 de octubre de 2026 el MAPE fue 17,9%.")

# ------------------------------------------------------------------ 8. comparación
a(h1("8. Comparación entre XGBoost y SARIMAX"))
P("Los dos modelos se evalúan en las mismas 228.984 filas, con el mismo objetivo y los mismos ingenuos. Las funciones "
  "de evaluación en R reproducen los resultados de XGBoost en Python (11,638% y t = −4,824).")
a(h2("8.1 En logaritmo"))
a(figura(FIG / "f06_mejora_log_por_horizonte.png", "Mejora del RMSE en log frente al ingenuo del día por horizonte. "
         "La línea punteada es el umbral de 5%.", 16))
a(figura(FIG / "f07_mejora_por_ano.png", "Mejora por año en la semana h = 3 a 9. Para SARIMAX en 2023-2025 se calculó "
         "con los RMSE por año redondeados a tres cifras.", 13.5))
a(titulo_tabla("Comparación en logaritmo, h = 3 a 9."))
a(tabla([["Modelo", "Periodo", "RMSE", "MAE", "Mediana del error", "Error del nivel", "Error de la forma"],
         ["XGBoost", "2023-2025", "0,443", "0,318", "0,225", "0,385", "0,221"],
         ["SARIMAX", "2023-2025", "0,470", "0,327", "0,221", "0,402", "0,243"],
         ["Ingenuo del día", "2023-2025", "0,502", "0,333", "0,203", "0,415", "0,282"],
         ["XGBoost", "2026", "0,392", "0,289", "0,212", "0,341", "0,193"],
         ["SARIMAX", "2026", "0,411", "0,301", "0,215", "0,356", "0,205"],
         ["Ingenuo del día", "2026", "0,435", "0,311", "0,215", "0,363", "0,240"]],
        anchos=[2, 1.5, 1, 1, 1.5, 1.4, 1.5]))
a(titulo_tabla("Diebold-Mariano entre los dos modelos, h = 3 a 9."))
a(tabla([["Periodo", "RMSE SARIMAX", "RMSE XGBoost", "DM p", "Lectura"],
         ["2023-2025", "0,470", "0,443", "0,011", "XGBoost mejor"],
         ["2026", "0,411", "0,392", "0,062", "Sin diferencia al 5%"],
         ["2023", "0,521", "0,474", "0,003", "XGBoost mejor"],
         ["2024", "0,478", "0,470", "0,707", "Sin diferencia"],
         ["2025", "0,401", "0,379", "0,070", "Sin diferencia al 5%"]],
        anchos=[1.6, 1.6, 1.6, 1.1, 2.6]))
P("XGBoost tiene menor error en todos los periodos, pero la diferencia solo es significativa en 2023-2025 y en 2023. En "
  "2024 quedan empatados y SARIMAX tiene mejor MAE. En el día típico no hay ventaja real: la mediana del error de los dos "
  "es casi igual y, en 2023-2025, peor que la del ingenuo.")

a(h2("8.2 Nivel y forma del día"))
a(figura(FIG / "f08_nivel_forma.png", "Error del nivel del día y de la forma dentro del día (ecuación 16), 2023-2025.", 13.5))
P("Los dos modelos mejoran mucho más la forma que el nivel. Frente al ingenuo, SARIMAX mejora el nivel 3,1% y XGBoost "
  "7,2%; la forma, 13,8% y 21,6%. Según el diagnóstico de XGBoost, 75% del error cuadrático es nivel. Acertar cuánto "
  "costará en promedio la energía de la semana siguiente es lo difícil, y ninguno lo logra en las crisis.")

a(h2("8.3 En pesos y el sesgo"))
P("Salazar-Peña et al. (2025) reportan los resultados en las unidades del precio. Con ese formato la comparación cambia:")
a(titulo_tabla("Semana h = 3 a 9 en COP/kWh, 2023-2025. Skill score = 1 − RMSE / RMSE del ingenuo del día."))
a(tabla([["Modelo", "MAE", "RMSE", "nRMSE", "MBE", "MAPE", "Skill"],
         ["XGBoost", "148,6", "247,5", "50,4%", "−46,4", "36,2%", "3,7%"],
         ["SARIMAX", "148,8", "242,1", "49,3%", "−15,3", "39,0%", "5,8%"],
         ["Ingenuo del día", "150,1", "257,1", "52,3%", "1,3", "40,1%", ""],
         ["Ingenuo semanal", "172,1", "286,3", "58,2%", "1,8", "46,8%", "−11,4%"]],
        anchos=[2.4, 1, 1, 1, 1, 1, 1]))
a(figura(RES / "comparacion/error_por_horizonte_2023_2025.png", "MAE, RMSE y sesgo (MBE) por horizonte en COP/kWh, "
         "2023-2025, con intervalo de 95%.", 16.5))
P("En pesos, XGBoost gana de h = 3 a 5 y SARIMAX de h = 6 a 9. La razón es el sesgo: XGBoost pronostica en promedio 46 "
  "COP/kWh por debajo del precio real, y el sesgo crece con el horizonte (−23 en h = 3, −75 en h = 9). Tiene dos causas. "
  "La primera es la vuelta del logaritmo a pesos: si el logaritmo del precio fuera normal con media μ y varianza σ², la "
  "exponencial del pronóstico daría la mediana y no la media,")
a(ec(e(r("E"), par(r("P"), "[", "]"), r("="), tx("exp"), par(e(r("μ"), r("+"), frac(sup(r("σ"), r("2")), r("2")))), r("="), tx("mediana"), par(r("P")), r("·"), tx("exp"), par(frac(sup(r("σ"), r("2")), r("2"))))))
P("y con un error en log de unos 0,44 la media queda cerca de 10% por encima de la mediana. La segunda es que XGBoost "
  "también se queda corto en logaritmo en h = 7 a 9, cerca de 5%, y casi todo eso se concentra en la crisis de octubre "
  "de 2024 (figura 13): ese mes, en h = 6, el sesgo mensual fue de −670 COP/kWh para XGBoost, −320 para SARIMAX y −180 "
  "para el ingenuo. Aun así, el sesgo explica solo 3,5% del error cuadrático medio de XGBoost; el resto es varianza.")
a(figura(RES / "comparacion/sesgo_en_el_tiempo.png", "Precio mensual y sesgo mensual de cada modelo en h = 6. El sesgo "
         "se concentra en los meses de precio alto, sobre todo en la crisis de 2024.", 15))
a(figura(RES / "modelo_sarimax/semana_comparacion.png", "Los dos modelos contra el precio real en la última semana "
         "completa del panel, con el pronóstico del 25 de septiembre de 2026. No es una semana típica: el 71% de los "
         "cortes de 2026 tuvo más error.", 16))

a(h2("8.4 Valor económico"))
P("Maciejowska et al. (2025) muestran que el RMSE no siempre refleja el valor económico de un pronóstico y proponen "
  "medirlo con una batería que compra energía en la hora que el pronóstico marca como más barata y la vende en la más "
  "cara. Con una batería de una hora y el pronóstico a h = 3, en 2023-2025, XGBoost captura 85% de la ganancia máxima "
  "posible (la de conocer el precio real), SARIMAX 77%, el ingenuo semanal 73% y el ingenuo del día 62%. Con una batería "
  "de tres horas: 89%, 81%, 83% y 73%. Esta métrica premia acertar la forma del día, que es donde XGBoost es mejor. Es "
  "un análisis exploratorio, hecho después de la prueba.")

# ------------------------------------------------------------------ 9. tesis de referencia
a(h1("9. Comparación con la tesis de referencia"))
P("González Pérez y Urbano Buriticá (2022), en su tesis de la Maestría en Inteligencia Analítica para la Toma de "
  "Decisiones de Uniandes, pronostican el precio de bolsa horario del día siguiente con datos de XM desde 2020. Prueban "
  "ARIMA, SARIMAX (con ciclo de 24 horas), Prophet y redes LSTM, y miden con MAPE. Sus mejores resultados son SARIMAX con "
  "variables exógenas (11,58%) y su mejor LSTM (13,89%).")
P("Las cifras no se pueden comparar directamente con las de esta tesis por tres razones:")
a(lista(["Pronostican un día adelante; aquí se pronostica de 3 a 9 días, porque el precio se conoce con dos días de atraso.",
         "No comparan contra un ingenuo, y el MAPE depende mucho del periodo: el ingenuo de un día tiene MAPE de 11,3% en "
         "2022 y de 18,3% en 2023-2025.",
         "No queda claro qué se supone conocido del día pronosticado, y eso cambia mucho el resultado."]))
P("Para ponerlas en la misma escala se entrenó XGBoost a un día con datos desde 2020, una sola división y prueba en 2022. "
  "Es exploratorio y no toca 2023-2026.")
a(titulo_tabla("Un día adelante, prueba en 2022 (MAPE)."))
a(tabla([["Modelo", "h = 1", "h = 2"],
         ["Ingenuo (misma hora, h días antes)", "11,3%", "15,4%"],
         ["XGBoost, precio y calendario, datos desde 2020", "11,3%", "14,7%"],
         ["XGBoost, precio y calendario, datos desde 2015", "11,0%", ""],
         ["XGBoost con variables hasta el día t", "12,2%", ""],
         ["XGBoost con el despacho del día objetivo (no factible)", "10,0%", "9,4%"],
         ["González y Urbano: SARIMAX con exógenas", "11,58%", ""],
         ["González y Urbano: mejor LSTM", "13,89%", ""]],
        anchos=[6, 1.5, 1.5]))
P("En 2022 el ingenuo de un día ya tiene 11,3%: su LSTM no le gana y su SARIMAX queda en el mismo nivel. XGBoost tampoco "
  "le gana con claridad a un día. Solo baja con claridad si se le da el despacho del día pronosticado (8,9% entrenando "
  "desde 2015), que no se publica a tiempo. La lección para esta tesis es doble: el ingenuo es una vara exigente a uno y "
  "dos días, y cualquier variable del día pronosticado tiene que estar publicada antes del pronóstico.")

# ------------------------------------------------------------------ 10. diagnósticos
a(h1("10. Dónde está el límite del pronóstico"))
a(h2("10.1 Dónde falla XGBoost"))
a(titulo_tabla("Diagnóstico de los errores de XGBoost, h = 3 a 9, 2023-2026 (exploratorio, con datos de prueba)."))
a(tabla([["Qué se midió", "Resultado"],
         ["Nivel del día contra forma", "75% del error cuadrático es nivel y 25% forma"],
         ["Movimientos grandes (más de 0,7 en log)", "14% de las filas y 57% del error"],
         ["Caídas fuertes", "Real −1,08 en promedio; pronóstico −0,20"],
         ["Subidas fuertes", "Real +1,03 en promedio; pronóstico +0,32"],
         ["Hora del pico", "Exacta 41% de los días; con ±1 hora, 70%"],
         ["Madrugada, horas 1 a 6", "32% del error en log"]],
        anchos=[4.5, 5.5], alinear_num=False))
P("El modelo es demasiado conservador ante los movimientos grandes: los anticipa en la dirección correcta pero con un "
  "tercio o menos de su tamaño.")
a(h2("10.2 Oráculo: qué información falta"))
P("Para medir qué información le falta al modelo se le dieron valores futuros reales del día objetivo, que nadie tendría "
  "al pronosticar (2020-2022, configuración congelada).")
a(figura(FIG / "f09_oraculo.png", "Mejora de XGBoost frente al ingenuo del día cuando recibe datos futuros reales. "
         "Saber las ofertas es casi saber el precio, así que esa barra es un techo teórico, no una meta.", 14.5))
P("Conocer la demanda y la hidrología del futuro casi no ayuda en h = 3 y sube h = 7 de 8,3% a 11,1%. Conocer las ofertas "
  "lo sube a 39,5%. Las ofertas se publican unos 10 días tarde y se intentó pronosticarlas: se pueden pronosticar "
  "(correlación de 0,84 a 0,92 para la oferta marginal), pero casi no ayudan al precio (h = 3 pasa de 17,6% a 18,4%), "
  "porque lo pronosticable sale de los mismos datos que el modelo ya tiene. Lo que mueve el precio es la sorpresa en "
  "cómo oferta cada generador.")
a(h2("10.3 Información más fresca"))
P("El hallazgo más útil para mejorar salió del panel de la LSTM (pasos 2e y 2f). Allí cada dato entra el día en que se "
  "publica: el despacho programado de R, los aportes de R − 1 y el precio de t = R − 2. Con un XGBoost de prueba y "
  "2020-2022, agregando grupos de variables en orden y dejando entrar uno solo si gana con Diebold-Mariano:")
a(titulo_tabla("Mejora frente al ingenuo del día con información alineada a su publicación, 2020-2022 (exploratorio)."))
a(tabla([["Conjunto", "Variables", "h = 3", "h = 6", "h = 9", "Entra"],
         ["Precio y calendario", "0", "9,6%", "0,5%", "3,5%", ""],
         ["+ despacho de hoy", "3", "27,7%", "13,1%", "9,5%", "Sí"],
         ["+ aportes", "9", "29,0%", "12,8%", "8,5%", "No"],
         ["+ despacho de ayer", "6", "28,5%", "14,2%", "10,8%", "No"],
         ["+ escasez y presión hídrica", "5", "24,8%", "17,5%", "13,1%", "Sí"],
         ["Las 5 finales, llevadas al día t (sin frescura)", "5", "8,4%", "9,0%", "10,8%", "referencia"],
         ["+ fracción térmica del despacho de hoy (paso 2g)", "6", "27,0%", "17,9%", "12,9%", "Sí (h = 3, p = 0,001)"]],
        anchos=[4, 1.1, 1, 1, 1, 1.9]))
P("Con las mismas 5 variables, llevarlas al día t como en el panel de XGBoost hace caer h = 3 de 24,8% a 8,4%. La "
  "ganancia viene de los datos, no del modelo: el despacho programado de hoy resume las ofertas de los generadores y se "
  "conoce dos días antes que el precio. Como 2020-2022 ya se había usado para decidir, estos números son optimistas y "
  "exploratorios.")

# ------------------------------------------------------------------ 11. LSTM
a(h1("11. Trabajo en curso: la red LSTM"))
P("Hay una primera LSTM, con el diseño de Salazar-Peña et al. (2025), que repite la misma forma de día en toda la semana: "
  "pone el mismo pico los fines de semana y se queda corta de noche, porque no sabe qué día es cada uno de los 7 que "
  "pronostica. Además, sus variables las eligió un XGBoost que veía cada variable resumida en tres números. La versión "
  "nueva corrige las dos cosas. Su diseño quedó fijado antes de construirla (docs/LSTM_DISENO.md).")
a(h2("11.1 Variables por bloques"))
P("Cada variable entra como una columna alineada a su fecha de publicación, sin rezagos hechos a mano: la red recibe la "
  "secuencia de los últimos 28 días. Los bloques salen de cómo se forma el precio (decisión del autor).")
a(titulo_tabla("Bloques de variables de la LSTM."))
a(tabla([["Bloque", "Qué le dice al modelo", "Variables"],
         ["1. Precio", "Su propia historia", "lp, 24 horas por día"],
         ["2. Calendario", "Fines de semana y festivos", "Día de la semana y festivo de cada uno de los 7 días; hora"],
         ["3. Despacho de hoy", "Cómo viene el sistema, dos días antes que el precio", "cmg_hoy_vs_precio, cmg_despacho, disp_decl_hoy_rel, frac_termica_prog"],
         ["4. Estado hidrológico", "Si el agua alcanza", "volumen_util_pct, aportes, presión hídrica, brecha de escasez, días de autonomía"],
         ["5. Despacho de ayer", "Cuánto se corrigió lo programado", "cmg_redespacho, error del despacho, redespacho frente a lo programado"],
         ["6. Clima que viene", "Si va a llover menos", "ONI, Niño 3.4, lluvia acumulada, déficit pronosticado"],
         ["7. Pronósticos de XGBoost y SARIMAX", "Qué dicen los otros modelos y cuál viene acertando", "Sus 168 pronósticos y sus errores recientes ya conocidos"]],
        anchos=[2.3, 3, 4.7], alinear_num=False, tam=18))
P("La apuesta principal es el bloque 4: lo que mantiene el precio alto varias semanas, como en octubre de 2024, es el "
  "estado del agua, y una red que ve la secuencia completa puede aprovechar esas variables lentas.")
a(h2("11.2 Selección de bloques"))
P("Selección hacia adelante con la LSTM misma, no con XGBoost. Se empieza con los bloques 1 y 2 y se agrega un bloque a "
  "la vez; entra si le gana a la referencia del momento con Diebold-Mariano p < 0,05 en al menos un horizonte (h = 3, 6 o "
  "9) y no pierde en ninguno. Se valida con walk-forward anual (entrenar hasta 2019 y medir en 2020, hasta 2020 y medir en "
  "2021, hasta 2021 y medir en 2022) con 3 semillas. Aparte, un modelo con todas las variables y permutación por grupos "
  "comprueba que no haya quedado afuera un grupo importante.")
P("El bloque 7 es un apilamiento de pronósticos: la red aprende a cuál modelo creerle según la situación. Para que no "
  "aprenda a creerle a pronósticos perfectos, necesita pronósticos hechos como en la vida real (walk-forward) desde 2017. "
  "Además tiene que ganarle al promedio simple de los dos modelos, que en la literatura suele ser difícil de superar "
  "(Smith y Wallis, 2009; Timmermann, 2006). Se reporta aparte, como modelo combinado.")
a(h2("11.3 Arquitectura e hiperparámetros"))
a(figura(FIG / "f11_arquitectura_lstm.png", "Arquitectura codificador-decodificador de la LSTM nueva.", 15.5))
P("El decodificador genera la semana día por día sabiendo qué día es cada uno, que es lo que fallaba en la primera "
  "versión. La salida es el mismo cambio en logaritmo de XGBoost y la pérdida es MSE, porque el criterio es el RMSE en "
  "logaritmo. La capa Dense(64) de entrada comprime cada día al mismo tamaño, sean 30 números o unos 2.400, para que las "
  "versiones con más variables no tengan una red más grande.")
a(titulo_tabla("Hiperparámetros de la LSTM."))
a(tabla([["Hiperparámetro", "Selección de bloques (fijo)", "Búsqueda bayesiana (rango)"],
         ["Capas LSTM", "1 en el codificador y 1 en el decodificador", "1 a 3"],
         ["Neuronas por capa", "128", "32 a 360"],
         ["Capa de entrada (Dense)", "64", "32 a 256"],
         ["Dropout", "0,2", "0,2 a 0,5"],
         ["Tasa de aprendizaje (Adam)", "0,001", "1e-5 a 1e-2, escala logarítmica"],
         ["Tamaño del lote", "32", "32 o 64"],
         ["Ventana de historia", "28 días", "14, 28 o 56"],
         ["Épocas", "Hasta 100, parada temprana con paciencia 10", "Igual"]],
        anchos=[2.8, 3.6, 3.6], alinear_num=False))
P("Durante la selección los hiperparámetros quedan fijos, para que si un bloque gana sea por sus variables y no por una "
  "red distinta. Con los bloques elegidos se hace una búsqueda bayesiana de unas 20 configuraciones dentro de los rangos "
  "de Salazar-Peña et al. (2025). El modelo final pasa una sola vez por 2023-2025 y 2026, en las mismas filas y con el "
  "mismo criterio que XGBoost y SARIMAX.")

# ------------------------------------------------------------------ 12. mejoras
a(h1("12. Puntos de mejora"))
P("Lo que sigue son propuestas, ordenadas por cuánto podrían mover el resultado según la evidencia de este informe. "
  "Ninguna se ha probado en la prueba; todo lo que se decida con 2020-2022 se reportará como exploratorio.")
a(h2("12.1 En los datos"))
a(lista(["Usar la información fresca en XGBoost y SARIMAX. Es la mejora con más evidencia: con el despacho programado de "
         "hoy alineado a su publicación, el modelo de prueba pasa de 9,6% a 27,7% en h = 3 (sección 10.3). Además, así la "
         "LSTM se compararía con los otros dos en igualdad de información. El costo es que habría que volver a congelar "
         "esos modelos sin mirar la prueba otra vez.",
         "Confirmar el atraso del precio. En dos de tres consultas fueron tres días y no dos. El panel de la LSTM ya tiene "
         "una versión con tres días (h = 4 a 10); conviene reportar los dos escenarios.",
         "Completar los festivos de octubre a diciembre de 2026, que faltan en el calendario.",
         "Variables por planta: hoy el despacho entra como total. El paso 2g mostró que la fracción térmica del despacho de "
         "hoy ayuda en h = 3; otras partes del despacho por planta (por ejemplo, las plantas que suelen quedar al margen) "
         "podrían ayudar igual."]))
a(h2("12.2 En los modelos"))
a(lista(["Corregir la vuelta a pesos. Un factor de Duan (1983), el promedio de exp(residuo) estimado en entrenamiento para "
         "cada modelo, quitaría parte del sesgo en COP/kWh. No sirve un factor común: el promedio de 11% sobrecorrige a "
         "SARIMAX.",
         "Combinar pronósticos. Como los dos modelos se equivocan distinto (XGBoost mejor en h = 3 a 5, SARIMAX en h = 6 a 9 "
         "en pesos), un promedio simple es una referencia barata y, según Smith y Wallis (2009), difícil de superar.",
         "Pronósticos probabilísticos. Los intervalos de SARIMAX son estrechos (71% de cobertura para un 80% nominal). Una "
         "regresión por cuantiles o intervalos conformales calibrados en validación darían rangos más honestos, útiles "
         "para quien opera con el pronóstico.",
         "Regímenes de crisis. Los dos modelos fallan en el mismo tipo de episodio (El Niño de 2024). Una variable que "
         "marque el régimen (embalses bajo un umbral, precio cerca del de escasez) o un modelo que vea la secuencia "
         "hidrológica, como la LSTM, apuntan a ese problema.",
         "h = 8 y 9 de XGBoost usan la configuración de h = 7 sin validación propia; vale la pena validarlos.",
         "Un modelo lineal regularizado tipo LEAR (Lago et al., 2021), el estándar en la literatura de pronóstico del "
         "precio de electricidad, sería una tercera referencia entre SARIMAX y XGBoost."]))
a(h2("12.3 En la evaluación"))
a(lista(["Más pliegues y semillas en la validación. La selección del paso 2d usó un solo periodo y una sola semilla, y "
         "la curva del error contra el número de columnas es irregular: diferencias de 2 puntos entre corridas no son "
         "evidencia de nada.",
         "Métricas de forma y de valor. Además del RMSE, reportar la correlación diaria entre pronóstico y real y la ganancia "
         "de la batería (sección 8.4), que capturan lo que el RMSE no ve.",
         "Separar resultados por régimen hidrológico (años secos y húmedos), para no promediar crisis con años tranquilos."]))

# ------------------------------------------------------------------ 13. limitaciones
a(h1("13. Limitaciones y próximos pasos"))
a(h2("13.1 Limitaciones"))
a(lista(["El alcance de una semana se eligió después de ver la prueba de 2026 de XGBoost. El resultado de XGBoost en "
         "h = 3 a 9 tiene esa salvedad; el de SARIMAX no.",
         "2020-2022 se usó varias veces para decidir (variables, hiperparámetros, órdenes, el panel de la LSTM). Las "
         "decisiones nuevas tomadas con esos años son exploratorias.",
         "La prueba no está intacta del todo: experimentos anteriores (carpeta legacy/) ya habían evaluado en 2023-2026 con "
         "una selección lineal. Nada de eso se usó para decidir los modelos de este informe.",
         "Ningún modelo anticipa el nivel del precio en una crisis como la de 2024; en ese año XGBoost no pasa el criterio.",
         "Los pronósticos en pesos están sesgados hacia abajo, sobre todo los de XGBoost.",
         "Los diagnósticos del oráculo usan 2 horizontes y pocas variables; no descartan lo que podría lograr un modelo de "
         "la curva de ofertas completa por planta."]))
a(h2("13.2 Próximos pasos"))
a(lista(["Generar los pronósticos walk-forward de XGBoost y SARIMAX para 2017-2022, con su configuración final, para el "
         "bloque 7 de la LSTM.",
         "Armar el panel de los siete bloques y el notebook de selección para Colab.",
         "Correr la selección de bloques, la prueba de control y la búsqueda bayesiana.",
         "Probar la LSTM una vez en 2023-2026 y compararla con XGBoost y SARIMAX con las mismas métricas.",
         "Decidir con la profesora si XGBoost y SARIMAX se rehacen con la información fresca (sección 12.1).",
         "Escribir los capítulos de metodología y resultados."], ordenada=True))

# ------------------------------------------------------------------ referencias
a(h1("Referencias"))
refs = [
    "Box, G., Jenkins, G., Reinsel, G. y Ljung, G. (2015). *Time Series Analysis: Forecasting and Control*, 5.ª ed. Wiley.",
    "Chen, T. y Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD Conference*, 785-794.",
    "Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*, 7(2), 174-196.",
    "CREG. Resolución 055 de 1994; Resolución 025 de 1995; Resolución 071 de 2006. Gestor normativo de la CREG.",
    "Diebold, F. y Mariano, R. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3), 253-263.",
    "Duan, N. (1983). Smearing estimate: a nonparametric retransformation method. *Journal of the American Statistical Association*, 78(383), 605-610.",
    "Galli, S. Feature Engineering for Machine Learning (curso en línea).",
    "González Pérez, L. F. y Urbano Buriticá, S. N. (2022). *Proyección de corto plazo para el precio de bolsa de energía en el mercado colombiano*. Tesis de Maestría en Inteligencia Analítica para la Toma de Decisiones, Universidad de los Andes.",
    "Hastie, T., Tibshirani, R. y Friedman, J. (2009). *The Elements of Statistical Learning*, 2.ª ed. Springer.",
    "Hochreiter, S. y Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.",
    "Hurvich, C. y Tsai, C.-L. (1989). Regression and time series model selection in small samples. *Biometrika*, 76(2), 297-307.",
    "Hyndman, R. y Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*, 3.ª ed. OTexts.",
    "Kursa, M. B. y Rudnicki, W. R. (2010). Feature selection with the Boruta package. *Journal of Statistical Software*, 36(11), 1-13.",
    "Kwiatkowski, D., Phillips, P., Schmidt, P. y Shin, Y. (1992). Testing the null hypothesis of stationarity against the alternative of a unit root. *Journal of Econometrics*, 54(1-3), 159-178.",
    "Lago, J., Marcjasz, G., De Schutter, B. y Weron, R. (2021). Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark. *Applied Energy*, 293, 116983.",
    "Ljung, G. y Box, G. (1978). On a measure of lack of fit in time series models. *Biometrika*, 65(2), 297-303.",
    "Lundberg, S. M. y Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30, 4765-4774.",
    "Maciejowska, K., Lipiecki, A. y Uniejewski, B. (2025). Statistical and economic evaluation of forecasts in electricity markets: beyond RMSE and MAE. Preprint, arXiv:2511.13616v2.",
    "Newey, W. y West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708.",
    "Newey, W. y West, K. (1994). Automatic lag selection in covariance matrix estimation. *Review of Economic Studies*, 61(4), 631-653.",
    "Osborn, D., Chui, A., Smith, J. y Birchenhall, C. (1988). Seasonality and the order of integration for consumption. *Oxford Bulletin of Economics and Statistics*, 50(4), 361-377.",
    "Salazar-Peña, N., Palma-Vergara, A., Montes-Vera, M., Vargas-Torres, M. A., Hernández Vanegas, R., Amador, M., Rojas, B., Salinas, A., Velasco, A., Tabares, A. y González-Mancera, A. (2025). Intra-day Solar and Power Forecast for Optimization of Intraday Market Participation. Preprint, arXiv:2501.09551v3.",
    "Smith, J. y Wallis, K. (2009). A simple explanation of the forecast combination puzzle. *Oxford Bulletin of Economics and Statistics*, 71(3), 331-355.",
    "Sutskever, I., Vinyals, O. y Le, Q. (2014). Sequence to sequence learning with neural networks. *Advances in Neural Information Processing Systems*, 27.",
    "Timmermann, A. (2006). Forecast combinations. En G. Elliott, C. Granger y A. Timmermann (Eds.), *Handbook of Economic Forecasting*, vol. 1, 135-196.",
]
for ref in refs:
    a(f'<w:p><w:pPr><w:ind w:left="440" w:hanging="440"/><w:spacing w:after="80"/><w:jc w:val="left"/></w:pPr>{rich(ref)}</w:p>')

# ------------------------------------------------------------------ anexo
a(h1("Anexo. Archivos del repositorio"))
a(tabla([["Archivo", "Qué hace"],
         ["1_descargar.py, 1b_ideam.py", "Descarga de XM, SIMEM, NOAA, ERA5, TRM y boletines del IDEAM"],
         ["2_construir_panel.py, 2b_panel_horario.py", "Panel diario y panel horario"],
         ["2c_caracteristicas_horarias.py, features.py", "Variables base, calendario, objetivos y catálogo de columnas derivadas"],
         ["2d_seleccion_variables.py", "Selección congelada de columnas por horizonte"],
         ["2e_panel_lstm.py, 2f_datos_lstm.py, 2g_termica_programada.py", "Panel de la LSTM con cada dato alineado a su publicación"],
         ["4_modelo_xgboost.ipynb", "XGBoost: búsqueda, walk-forward, variantes, prueba y semana final"],
         ["5_modelo_sarimax.ipynb", "SARIMAX en R: órdenes, exógenas, validación, prueba y comparación"],
         ["7_resultados.ipynb", "Resultados de todos los modelos con el formato de Salazar-Peña et al. (2025)"],
         ["diagnosticos/", "Dónde falla el modelo, oráculo y pronóstico de las ofertas"],
         ["docs/", "Documentación del panel, diseño de la LSTM y fuente de cada parte del código"]],
        anchos=[4.5, 5.5], alinear_num=False))

guardar(SALIDA, "".join(C))
print("ok", SALIDA, "figuras", CONT)
