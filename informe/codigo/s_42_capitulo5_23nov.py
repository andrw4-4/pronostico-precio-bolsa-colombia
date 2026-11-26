"""Escribe la 4.2 y el capítulo V del informe final, pedidos por Andrés el 23 de noviembre de 2026.
- 4.2 Valor para la toma de decisiones: para qué sirve un pronóstico del precio de la electricidad, según la
  literatura (Weron, 2014; Zareipour et al., 2010; Kath y Ziel, 2018) y la regulación colombiana (CREG, 2015), y qué
  dicen los resultados de la 4.1 sobre esos usos. No mide el valor en pesos de ninguna decisión: eso queda como
  trabajo futuro.
- 5.1 Hallazgos principales: responde el objetivo general y los tres específicos de la sección 1.2.
- 5.2 Limitaciones y trabajo futuro.
- Agrega a las referencias CREG (2015), Kath y Ziel (2018) y Zareipour et al. (2010), en su lugar alfabético y sin
  mover las demás.
No trae cifras nuevas: antes de guardar se comprueba que cada cifra ya esté en el documento y que cada tabla, figura y
sección citada exista.
Uso: python s_42_capitulo5_23nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys
import unicodedata

from docx_final import Docx, par, runs

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

S42 = [
    "Un pronóstico del precio tiene valor en la medida en que alguien lo use para decidir. Weron (2014) señala que "
    "la volatilidad de los precios de la electricidad, mucho mayor que la de otras materias primas y activos "
    "financieros, llevó a los participantes del mercado a cubrirse no solo del riesgo de cantidad sino también del "
    "de precio, y que por eso el pronóstico del precio se volvió una entrada de las decisiones de las empresas del "
    "sector. El uso depende del horizonte: los pronósticos de corto plazo, de horas a unos días, sirven para la "
    "operación diaria del mercado, como preparar las ofertas, y los de mediano plazo, de días a meses, para el "
    "balance financiero, la gestión del riesgo y la valoración de derivados (Weron, 2014). El horizonte de este "
    "trabajo, de tres a nueve días, queda entre los dos (sección 2.2).",

    "En el mercado colombiano, esos usos corresponden a los participantes de la sección 1.1. Un comercializador "
    "compra en bolsa la energía que sus contratos no cubren; con el precio de la semana siguiente puede estimar "
    "cuánto le costará esa parte y decidir si le conviene cubrir más con contratos. Un generador hidráulico oferta "
    "cada día y decide cuánta agua usar; lo que espera del precio en los días siguientes le ayuda a decidir si le "
    "conviene generar ahora o guardar el agua. Un gran consumidor que puede mover su producción de un día a otro "
    "puede concentrarla en los días más baratos. La regulación ofrece, además, una forma directa de usar el "
    "pronóstico: en el programa de respuesta de la demanda, los usuarios, representados por un comercializador, "
    "ofrecen reducir su consumo cuando el precio de bolsa supera el precio de escasez de activación (CREG, 2015). "
    "Saber con una semana de anticipación si el precio se acerca a ese umbral les da tiempo para preparar la "
    "reducción.",

    "Que un pronóstico tenga menos error no dice, por sí solo, cuánto vale para cada uno de ellos. Zareipour et al. "
    "(2010) señalaron que no se había estudiado el impacto económico de los errores del pronóstico del precio para "
    "quien lo usa, y lo midieron con dos cargas industriales de naturaleza distinta: programaron su operación del "
    "día siguiente con el precio pronosticado y compararon su costo con el que habrían tenido con los precios "
    "reales. Kath y Ziel (2018) hacen la misma advertencia: la mayoría de los estudios evalúan solo la precisión, y "
    "un pronóstico preciso no tiene valor práctico si no hay una decisión en que usarlo. Al simular estrategias de "
    "compra y venta con sus pronósticos del mercado alemán, encontraron que incluso estrategias sencillas generan un "
    "beneficio económico importante cuando se combinan con un buen pronóstico, y que la estrategia más simple dio "
    "más beneficio que una optimización de portafolio más compleja, aunque esta tuvo menos riesgo.",

    "Los resultados de la sección 4.1 no miden el valor del pronóstico para ninguna de esas decisiones, pero sí "
    "indican para cuáles sirve mejor cada modelo. Primero, la diferencia entre los modelos está sobre todo en el "
    "nivel del día, que la LSTM pronostica mejor, mientras que XGBoost pronostica mejor la forma de las horas dentro "
    "del día. Para elegir en qué días de la semana concentrar un consumo importa más el nivel; para elegir en qué "
    "horas, la forma. Segundo, la LSTM y XGBoost ganan más en los primeros días de la semana pronosticada "
    "(figura 17), así que las decisiones más cercanas se apoyan en un pronóstico más confiable. Tercero, en pesos "
    "las mejoras son menores y los tres modelos quedan, en promedio, por debajo del precio real (tabla 17): un "
    "comercializador que estimara con ellos el costo de su exposición a la bolsa lo subestimaría. Cuarto, en 2024, "
    "el año del precio más alto, XGBoost y la LSTM no tuvieron una mejora significativa (tabla 16), y es en esos "
    "periodos cuando la exposición a la bolsa pesa más. Por último, los pronósticos son puntuales, y para gestionar "
    "el riesgo hace falta saber también qué tan grande puede ser el error (sección 1.3).",

    "Por eso este trabajo no afirma cuánto ahorraría un participante del mercado con estos pronósticos. Medirlo "
    "exige, como en Zareipour et al. (2010) y Kath y Ziel (2018), simular la decisión de un usuario concreto, con "
    "sus contratos, sus restricciones y el costo de cambiar su operación, y comparar el resultado con el que "
    "obtendría con el pronóstico ingenuo o conociendo los precios reales. Esa evaluación queda como trabajo futuro "
    "(sección 5.2).",
]

S51 = [
    "Este trabajo buscaba saber si modelos estadísticos y de aprendizaje automático pronostican el precio de bolsa "
    "horario de Colombia a una semana con menor error que un pronóstico ingenuo, usando solo la información "
    "publicada al momento de pronosticar (sección 1.2). La respuesta es sí. SARIMAX, XGBoost y la LSTM cumplieron el "
    "criterio de la sección 3.3 en las dos pruebas, 2023-2025 y 2026, en la semana completa y en los cuatro bloques "
    "de horizontes: redujeron el RMSE en logaritmo más de 5% frente al ingenuo del día, con diferencias "
    "significativas según la prueba de Diebold-Mariano. La LSTM fue la que más lo redujo, 14,9% en 2023-2025 y "
    "19,7% en 2026, seguida de XGBoost, con 11,6% y 10,0%, y de SARIMAX, con 6,4% y 5,6% (tabla 15).",

    "El primer objetivo, construir una base de datos en la que cada dato entra en la fecha en que se publica, "
    "resultó tan importante como la elección del modelo. Medir el atraso de cada fuente (tabla 2) mostró que no "
    "toda la información llega con el atraso del precio: el despacho programado de cada día sale esa misma "
    "madrugada, cuando el último precio conocido es de dos o tres días antes, y las ofertas de los generadores se "
    "conocen unos diez días tarde. La LSTM, que recibe cada dato desde el día en que se publica, fue la que más "
    "redujo el error, y le ganó a XGBoost sobre todo en el nivel del día, donde aporta el despacho programado "
    "(sección 4.1). Por eso su ventaja no se puede atribuir solo a la red.",

    "El segundo objetivo se cumplió con un mismo diseño para los tres modelos: los 168 precios de los días t + 3 a "
    "t + 9, todas las decisiones con datos hasta 2022 y una sola evaluación en las mismas filas, con el criterio "
    "fijado antes de la prueba (sección 3.3). Los tres llegan a la semana de formas distintas, recursiva en SARIMAX, "
    "directa en XGBoost y con la semana completa a la vez en la LSTM (sección 2.3), y aun así los tres le ganaron "
    "al ingenuo. Esa referencia es exigente: con solo el precio y el calendario, XGBoost tuvo más error que el "
    "ingenuo del día en 2020-2022 (sección 3.5).",

    "La comparación del tercer objetivo muestra, además, que la ventaja no es la misma en todos los periodos. En "
    "2024, el año en que el precio llegó a su máximo de la muestra, XGBoost y la LSTM mejoraron 7,6% y 9,7%, sin "
    "diferencia significativa, y solo SARIMAX cumplió el criterio (tabla 16). Entre modelos, la LSTM tuvo menos "
    "error que SARIMAX en las dos pruebas, pero frente a XGBoost la diferencia solo fue significativa en 2026. Y en "
    "la semana del 9 al 15 de octubre de 2026, pronosticada antes de que se publicaran sus precios, XGBoost tuvo el "
    "menor error y la LSTM más que el ingenuo del día (figura 18). Lo que se sostiene es que los modelos le ganan "
    "al ingenuo en el promedio de varios años, no en cada año ni en cada semana, y que el orden entre la LSTM y "
    "XGBoost depende del periodo.",

    "La mayor parte del error que queda está en el nivel del día, es decir, en el promedio de sus 24 horas: 66% del "
    "error cuadrático de la LSTM en 2023-2025 (sección 4.1). La forma del día, con sus horas caras y baratas, se "
    "repite de un día a otro y tiene menos error; el nivel depende del agua y de cómo ofertan los generadores. El "
    "ejercicio de diagnóstico de la sección 4.1 sugiere que lo que más falta son las ofertas, que se publican "
    "cuando la semana pronosticada ya pasó. Así, el límite del pronóstico a una semana parece estar más en la "
    "información que se conoce a tiempo que en el modelo.",

    "En pesos, que es lo que paga quien compra o vende energía, las mejoras son menores: en 2023-2025, 7,1% con la "
    "LSTM, 5,8% con SARIMAX y 3,7% con XGBoost, y solo la de SARIMAX es significativa; en 2026 lo son las tres "
    "(tabla 17). La otra parte del tercer objetivo, el valor del pronóstico para la toma de decisiones, se revisó en "
    "la sección 4.2 a partir de la literatura y no con una medición propia: el pronóstico sirve a comercializadores, "
    "generadores y grandes consumidores, y al programa de respuesta de la demanda, pero cuánto vale depende de la "
    "decisión en que se use (Zareipour et al., 2010; Kath y Ziel, 2018). Este trabajo muestra que los modelos "
    "pronostican mejor que el ingenuo, no cuánto vale esa mejora para una decisión concreta.",

    "De estos resultados salen tres recomendaciones para quien use un pronóstico del precio de bolsa a una semana. "
    "Primera, compararlo con el ingenuo del día, que es una referencia exigente: repetir el último precio conocido "
    "tuvo menos error que repetir la semana anterior en todos los bloques de horizontes y en todos los años. "
    "Segunda, elegir el modelo según la decisión: para saber qué días de la semana serán más caros, el más útil fue "
    "la LSTM, que tuvo el menor error de nivel; para el perfil de las horas dentro del día, XGBoost, que tuvo el "
    "menor error de forma (sección 4.1). Tercera, al usar el pronóstico en pesos, tener en cuenta que los tres "
    "modelos quedaron en promedio por debajo del precio real, entre 15 y 46 COP/kWh en 2023-2025 (sección 4.1).",
]

S52 = [
    "Estas conclusiones están sujetas a las cuatro limitaciones de la sección 1.3: el horizonte de una semana se "
    "eligió después de ver la prueba de XGBoost, las ofertas se publican tarde, los tres modelos no reciben la "
    "misma información y el periodo de prueba tuvo precios mucho más altos que el de entrenamiento. Los resultados "
    "agregan tres más. La ventaja de los modelos cambia de un año a otro y fue menor en 2024 (tabla 16). En pesos, "
    "las mejoras son menores que en logaritmo y los pronósticos quedan por debajo del precio real; corregir ese "
    "sesgo con el estimador de Duan (1983) no bajó el error en pesos (sección 4.1). Y el valor económico del "
    "pronóstico no se midió (sección 4.2). Con eso en cuenta, quedan seis líneas de trabajo.",

    "*La misma información para todos los modelos.* Entrenar XGBoost con el panel de la LSTM, en el que cada dato "
    "entra desde el día en que se publica, permitiría separar cuánto de la ventaja de la LSTM viene de la red y "
    "cuánto de la información más reciente. Es la principal pregunta que deja abierta la comparación de la "
    "sección 4.1.",

    "*Información sobre las ofertas.* Las ofertas de los generadores son lo que más mueve el precio a una semana, y "
    "se conocen tarde. Un trabajo futuro podría pronosticar primero las ofertas de las plantas que más pesan en el "
    "precio, con sus ofertas pasadas y el estado de sus embalses, y usar ese pronóstico como entrada del modelo del "
    "precio. Sería un modelo de la oferta, que este trabajo dejó por fuera (sección 1.3).",

    "*Combinar los pronósticos.* La LSTM tuvo el menor error de nivel y XGBoost el menor error de forma (sección "
    "4.1). Como el pronóstico de cada día se puede separar en esas dos partes, una opción directa es sumar el nivel "
    "de la LSTM y la forma de XGBoost; otra es el séptimo bloque de la sección 3.6, que le daría a la red los "
    "pronósticos de XGBoost y SARIMAX. Combinar pronósticos es una de las direcciones que propone la literatura del "
    "precio de la electricidad (Weron, 2014).",

    "*Pronósticos con incertidumbre.* Los tres modelos dan un solo valor por hora. Para gestionar el riesgo, como al "
    "decidir cuánta energía cubrir con contratos, sirve más un rango o una distribución del precio, otra de las "
    "direcciones que señala Weron (2014).",

    "*El valor del pronóstico en una decisión.* Siguiendo a Zareipour et al. (2010) y a Kath y Ziel (2018), se "
    "puede simular la decisión de un participante concreto, como la compra en bolsa de un comercializador o la "
    "programación de un consumo que se puede mover entre días, con sus contratos y restricciones, para medir en "
    "pesos cuánto vale pasar del ingenuo a cada modelo.",

    "*Seguir probando los modelos.* En octubre de 2026 el índice ONI llegó a 2,2 °C (sección 1.1). Pronosticar las "
    "próximas semanas con la configuración fija y el mismo reentrenamiento mensual daría una tercera prueba en un "
    "posible episodio de El Niño, el tipo de periodo en el que, como mostró 2024, la ventaja de los modelos se "
    "reduce.",
]

REFS = [
    "Comisión de Regulación de Energía y Gas [CREG]. (2015). *Resolución CREG 011 de 2015: Por la cual se regula el "
    "programa de respuesta de la demanda para el mercado diario en condición crítica*. Gestor normativo de la CREG.",
    "Kath, C., y Ziel, F. (2018). The value of forecasts: Quantifying the economic gains of accurate quarter-hourly "
    "electricity price forecasts. *Energy Economics*, *76*, 411-423. https://doi.org/10.1016/j.eneco.2018.10.005",
    "Zareipour, H., Cañizares, C. A., y Bhattacharya, K. (2010). Economic impact of electricity market price "
    "forecasting errors: A demand-side analysis. *IEEE Transactions on Power Systems*, *25*(1), 254-262. "
    "https://doi.org/10.1109/TPWRS.2009.2030380",
]


def texto(x):
    return Docx.texto(x)


def es_indice(x):
    return 'w:val="TDC' in x[:400]


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


d = Docx(ENTRADA)
n_bloques = len(d.bloques())
antes = texto(d.doc)

# ----------------------------------------------------------------------------- comprobaciones del texto nuevo
nuevo = " ".join(S42 + S51 + S52)
# cada cifra con decimales o porcentaje, y las demás cifras del texto, ya están en el documento
cifras = set(re.findall(r"\d+,\d+|\d+%", nuevo)) | {"15 COP/kWh", "46 COP/kWh", "2,2 °C", "dos o tres días",
                                                     "unos diez días", "tres a nueve días"}
for c in sorted(cifras):
    assert re.search(r"(?<![\d,])" + re.escape(c), antes), c
# las tablas, figuras y secciones citadas existen y dicen lo que se les atribuye
for n in re.findall(r"tabla (\d+)", nuevo):
    assert f"Tabla {n}. " in antes, n
for n in re.findall(r"figura (\d+)", nuevo):
    assert f"Figura {n}. " in antes, n
for s in set(re.findall(r"secci[oó]n (\d\.\d)", nuevo)):
    assert re.search(rf"{re.escape(s)} [A-ZÁÉÍÓÚ]", antes), s
for t in ["La tabla 15 resume la semana completa", "Por años el resultado es menos claro (tabla 16)",
          "la tabla 17 repite la comparación con el error en COP/kWh", "La ventaja cambia con el horizonte (figura 17)",
          "antes de que XM publicara esos precios (figura 18)", "Los pronósticos son puntuales",
          "con solo el precio y el calendario, XGBoost tuvo más error", "Se planeó también un séptimo bloque",
          "66% del error cuadrático de la LSTM", "Tabla 2. Fuentes de datos y atraso de publicación",
          "SARIMAX es recursivo, XGBoost es directo y la LSTM entrega la semana completa",
          "los comercializadores, que compran en bolsa", "La misma revisión distingue el corto plazo"]:
    assert t in antes, t
# las citas del texto nuevo están en las referencias (las que ya estaban, o las que se agregan aquí)
for c in ["Weron, R. (2014)", "Duan, N. (1983)"]:
    assert c in antes, c
assert "decisión del autor" not in nuevo and "**" not in nuevo


# ----------------------------------------------------------------------------- 4.2 y capítulo V
def llenar(titulo, parrafos):
    """Pone los párrafos justo después del título, que debe estar vacío (el bloque siguiente es otro título)."""
    B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
    k = [i for i, (s, e) in enumerate(B) if texto(d.doc[s:e]) == titulo and 'w:val="Ttulo2"' in d.doc[s:e]]
    assert len(k) == 1, (titulo, k)
    s, e = B[k[0]]
    sig = d.doc[B[k[0] + 1][0]:B[k[0] + 1][1]]
    assert re.search(r'w:val="Ttulo[12]"', sig[:600]), f"{titulo} ya tiene contenido"
    d.doc = d.doc[:e] + "".join(par(p) for p in parrafos) + d.doc[e:]


llenar("4.2 Valor para la toma de decisiones", S42)
llenar("5.1 Hallazgos principales", S51)
llenar("5.2 Limitaciones y trabajo futuro", S52)

# ----------------------------------------------------------------------------- referencias, sin mover las demás
B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
T = [texto(d.doc[s:e]) for s, e in B]
i = T.index("Referencias")
j = T.index("Anexos")
lista = [(B[k], T[k]) for k in range(i + 1, j) if T[k].strip()]
orden_antes = [t for _, t in lista]
modelo = d.doc[lista[0][0][0]:lista[0][0][1]]
ppr = re.search(r"<w:pPr>.*?</w:pPr>", modelo, re.S).group(0)
for ref in REFS:
    clave = sin_tildes(texto(runs(ref)))
    assert all(sin_tildes(t) != clave for t in orden_antes), ref[:40]
    B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
    T = [texto(d.doc[s:e]) for s, e in B]
    i, j = T.index("Referencias"), T.index("Anexos")
    sig = [k for k in range(i + 1, j) if T[k].strip() and sin_tildes(T[k]) > clave]
    pos = B[sig[0]][0] if sig else B[j][0]
    d.doc = d.doc[:pos] + f"<w:p>{ppr}{runs(ref)}</w:p>" + d.doc[pos:]

# ----------------------------------------------------------------------------- comprobaciones finales
B = [(s, e) for s, e in d.bloques() if not es_indice(d.doc[s:e])]
T = [texto(d.doc[s:e]) for s, e in B]
i, j = T.index("Referencias"), T.index("Anexos")
refs = [t for t in T[i + 1:j] if t.strip()]
assert [t for t in refs if t in orden_antes] == orden_antes, "cambió el orden de las referencias que ya estaban"
assert len(refs) == len(orden_antes) + 3
for c, a in [("CREG, 2015", "[CREG]. (2015)"), ("Kath y Ziel (2018)", "Kath, C., y Ziel, F. (2018)"),
             ("Zareipour et al. (2010)", "Zareipour, H., Cañizares, C. A., y Bhattacharya, K. (2010)")]:
    assert c in nuevo and any(r.startswith(a) or a in r for r in refs), c
k42 = T.index("4.2 Valor para la toma de decisiones")
assert T[k42 + 1] == S42[0].replace("*", "") and T[k42 + len(S42) + 1] == "V. Conclusiones"
k51 = T.index("5.1 Hallazgos principales")
assert T[k51 + len(S51) + 1] == "5.2 Limitaciones y trabajo futuro"
assert T[k51 + len(S51) + 1 + len(S52) + 1] == "Referencias"
assert len(d.bloques()) == n_bloques + len(S42) + len(S51) + len(S52) + 3
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 18
d.guardar(SALIDA)
print("ok", SALIDA, "| palabras: 4.2 =", len(" ".join(S42).split()), ", 5.1 =", len(" ".join(S51).split()),
      ", 5.2 =", len(" ".join(S52).split()))
