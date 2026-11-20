"""Escribe el capítulo V, Conclusiones, en sus dos secciones: 5.1 Hallazgos principales, que responde el objetivo
general y los tres específicos de la sección 1.2, y 5.2 Limitaciones y trabajo futuro.
No trae cifras nuevas: cada número sale de los capítulos I, III y IV, y antes de escribir se comprueba que cada cifra
con decimales o con porcentaje ya esté en el documento. Va después de s3_7_resumen.py.
Uso: python s5_conclusiones.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, par

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

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
    "toda la información llega con el atraso del precio: el despacho programado de cada día se publica ese mismo "
    "día, cuando el último precio conocido es de dos días antes, y las ofertas de los generadores se conocen diez "
    "días tarde. "
    "La LSTM, que recibe cada dato desde el día en que se publica, fue la que más redujo el error, y le ganó a "
    "XGBoost sobre todo en el nivel del día, donde aporta el despacho programado (sección 4.1). Por eso su ventaja "
    "no se puede atribuir solo a la red.",

    "La ventaja de los modelos no es la misma en todos los periodos. En 2024, el año en que el precio llegó a su "
    "máximo de la muestra, XGBoost y la LSTM mejoraron menos de 10% y sin diferencia significativa, y solo SARIMAX "
    "cumplió el criterio (tabla 16). Entre modelos, la LSTM tuvo menos error que SARIMAX en las dos pruebas, pero "
    "frente a XGBoost la diferencia solo fue significativa en 2026. Y en la semana del 9 al 15 de octubre de 2026, "
    "pronosticada antes de que se publicaran sus precios, la LSTM tuvo más error que el ingenuo del día. Lo que se "
    "sostiene es que los modelos le ganan al ingenuo en el promedio de varios años, no en cada año ni en cada "
    "semana, y que el orden entre la LSTM y XGBoost depende del periodo.",

    "La mayor parte del error que queda está en el nivel del día, es decir, en el promedio de sus 24 horas: 66% del "
    "error cuadrático de la LSTM en 2023-2025 (sección 4.1). La forma del día, con sus horas caras y baratas, se "
    "repite de un día a otro y tiene menos error; el nivel depende del agua y de cómo ofertan los generadores. El "
    "ejercicio de diagnóstico de la sección 4.1 sugiere que lo que más falta son las ofertas, que se publican "
    "cuando la semana pronosticada ya pasó. Así, el límite del pronóstico a una semana parece estar más en la "
    "información que se conoce a tiempo que en el modelo.",

    "El tercer objetivo era medir el valor del pronóstico para una decisión. Al elegir el día más barato de la "
    "semana para un bloque de consumo de 24 horas, la LSTM ahorró 42,6 COP/kWh en 2023-2025 y 50,8 COP/kWh en 2026 "
    "frente a consumir un día cualquiera de esa semana, más del doble que el ingenuo semanal y entre 42% y 61% de "
    "lo que ahorraría quien conociera los precios reales (tabla 17). El orden de los modelos en esta decisión no fue "
    "el mismo que en el error: SARIMAX ahorró más que XGBoost en 2023-2025, aunque su RMSE fue mayor, y los "
    "intervalos de los tres modelos se cruzan. Para elegir el día no importa acertar cada hora, sino ordenar bien "
    "los días, así que conviene evaluar un pronóstico también con la decisión para la que se va a usar.",

    "De estos resultados salen tres recomendaciones para quien use un pronóstico del precio de bolsa a una semana. "
    "Primera, compararlo con el ingenuo del día, que es una referencia exigente: repetir el último precio conocido "
    "tuvo menos error que repetir la semana anterior en todos los bloques y en todos los años. Segunda, para decidir "
    "en qué días concentrar un consumo, de los tres modelos el más útil fue la LSTM; si lo que importa es el perfil "
    "de las horas dentro del día, XGBoost tuvo el menor error de forma. Tercera, al usar el pronóstico en pesos, "
    "tener en cuenta que los tres modelos quedaron en promedio por debajo del precio real, entre 15 y 46 COP/kWh "
    "en 2023-2025 (sección 4.1).",
]

S52 = [
    "Estas conclusiones están sujetas a las cuatro limitaciones de la sección 1.3: el horizonte de una semana se "
    "eligió después de ver la prueba de XGBoost, las ofertas se publican tarde, los tres modelos no reciben la "
    "misma información y el periodo de prueba tuvo precios mucho más altos que el de entrenamiento. Los resultados "
    "agregan tres más. La validación de la LSTM es optimista, porque el periodo 2020-2022 se usó también para armar "
    "su panel, elegir sus bloques y buscar sus hiperparámetros (sección 3.6). En pesos, las mejoras son menores que "
    "en logaritmo y los pronósticos quedan por debajo del precio real (sección 4.1). Y el ejercicio de decisión "
    "supone que el consumidor paga el precio de bolsa sin contratos, que mover su consumo no cuesta nada y que su "
    "consumo no cambia el precio (sección 4.2). Con eso en cuenta, quedan seis líneas de trabajo.",

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
    "de la LSTM y la forma de XGBoost; otra, promediar los modelos con pesos elegidos en la validación. Combinar "
    "pronósticos es una de las direcciones que la literatura del precio de la electricidad propone explorar "
    "(Weron, 2014).",

    "*Pronósticos con incertidumbre.* Los tres modelos dan un solo valor por hora. Para decisiones con riesgo, como "
    "cuánta energía cubrir con contratos, sirve más un rango o una distribución del precio, otra de las direcciones "
    "que señala Weron (2014). Con esos rangos, el ejercicio de la sección 4.2 se podría extender a una decisión con "
    "contratos y con un costo por mover el consumo.",

    "*Corregir el sesgo en pesos.* Como los modelos pronostican el logaritmo, al pasar a pesos el pronóstico queda "
    "cerca de la mediana del precio. Multiplicarlo por el promedio de la exponencial de los errores de la "
    "validación, el estimador de Duan (1983), podría corregir buena parte de ese sesgo sin cambiar los modelos.",

    "*Seguir probando los modelos.* En octubre de 2026 el índice ONI llegó a 2,2 °C (sección 1.1). Pronosticar las "
    "próximas semanas con la configuración fija y el mismo reentrenamiento mensual daría una tercera prueba en un "
    "posible episodio de El Niño, el tipo de periodo en el que, como mostró 2024, la ventaja de los modelos se "
    "reduce.",
]


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


d = Docx(ENTRADA)
todo = texto(d.doc)

# cada cifra con decimales o porcentaje del capítulo V ya está en el documento
nuevo = " ".join(S51 + S52)
cifras = set(re.findall(r"\d+,\d+|\d+%", nuevo)) | {"15 COP/kWh", "46 COP/kWh", "66%", "2,2 °C"}
for c in sorted(cifras):
    assert re.search(r"(?<![\d,])" + re.escape(c), todo), c
# las remisiones apuntan a lo que dicen
assert "La tabla 15 resume la semana completa" in todo and "Por años el resultado es menos claro (tabla 16)" in todo
assert "(tabla 17). Es más del doble" in todo and "Tabla 2." in todo
assert "Weron, R. (2014)" in todo and "Duan, N. (1983)" in todo
assert nuevo.count("**") == 0


def llenar(titulo, parrafos):
    B = d.bloques()
    T = [texto(d.doc[s:e]) for s, e in B]
    i = [k for k, t in enumerate(T) if t == titulo and "Ttulo2" in d.doc[B[k][0]:B[k][1]]]
    assert len(i) == 1, (titulo, i)
    k = i[0] + 1
    assert T[k] == "" and "<w:tbl>" not in d.doc[B[k][0]:B[k][1]], f"{titulo} ya tiene contenido"
    s, e = B[k]
    d.doc = d.doc[:s] + "".join(par(p) for p in parrafos) + d.doc[e:]


llenar("5.1 Hallazgos principales", S51)
llenar("5.2 Limitaciones y trabajo futuro", S52)

B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]
i = T.index("V. Conclusiones")
j = max(k for k, t in enumerate(T) if t == "Referencias")
assert T[i + 1] == "5.1 Hallazgos principales" and T[i + 1 + len(S51) + 1] == "5.2 Limitaciones y trabajo futuro"
assert j == i + 1 + len(S51) + 1 + len(S52) + 1, (i, j)
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
d.guardar(SALIDA)
print("ok", SALIDA)
