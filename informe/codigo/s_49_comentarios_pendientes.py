"""Cierra lo que quedaba de los comentarios del 17 y del 26 de noviembre que se puede resolver con texto.

1. Punto 2.7 del 26 nov.: el hallazgo del ejercicio de diagnóstico es que la demanda y la hidrología conocidas
   de antemano agregan poco; la fila de las ofertas queda solo como cota casi circular (4.1, 5.1 y 5.2).
2. Punto 2.10.1 del 26 nov. y 3.1 del 17 nov.: tabla de la mediana del error absoluto por año y modelo.
3. Comentarios del 17 nov.: lista explícita del trabajo pendiente en la 5.2 (intervalos, más modelos de
   referencia, aporte de la hidrología, semillas de XGBoost) y las referencias que se pueden citar con sentido.

Uso: python s_49_comentarios_pendientes.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, leyenda, reemplazar_en_bloque, runs, tabla

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = "Fuente: elaboración propia con datos de XM (2026)."


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def uno(d, inicio):
    k = [(s, e) for s, e, t in cuerpo(d) if t.startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return k[0]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def tras(d, inicio, xml):
    s, e = uno(d, inicio)
    d.doc = d.doc[:e] + xml + d.doc[e:]


def p(t):
    return f"<w:p>{runs(t)}</w:p>"


def nota(t):
    x = runs(t).replace("<w:r><w:rPr>", '<w:r><w:rPr><w:sz w:val="20"/>').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{x}</w:p>'


def cap(texto):
    return leyenda("Tabla", texto, ppr='<w:keepNext/><w:spacing w:before="240"/>')


def n(x, dec=3):
    return f"{x:.{dec}f}".replace(".", ",")


d = Docx(sys.argv[1])
assert "Mediana del error absoluto en logaritmo" not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- 1. punto 2.7: demanda e hidrología primero
cambiar(d, "Lo que el ejercicio muestra es que el nivel del precio a una semana depende sobre todo de cómo van a "
           "ofertar los generadores, algo que ni la demanda ni la hidrología conocidas de antemano resuelven.",
        "El resultado que importa es el primero: aun conocidas a la perfección, la demanda y la hidrología de la "
        "semana dejan casi igual el error del nivel del día. La fila de las ofertas solo indica que lo que falta "
        "está en información que no se publica a tiempo.")
cambiar(d, "La forma del día, con sus horas caras y baratas, se repite de un día a otro y tiene menos error; el "
           "nivel depende de cómo van a ofertar los generadores. El ejercicio de diagnóstico de la sección 4.1 "
           "muestra que conocer de antemano la demanda y la hidrología",
        "La forma del día, con sus horas caras y baratas, se repite de un día a otro y tiene menos error. El "
        "ejercicio de diagnóstico de la sección 4.1 muestra que conocer de antemano y a la perfección la demanda "
        "y la hidrología")
cambiar(d, "El nivel del precio a una semana depende de cómo ofertan los generadores, y las ofertas se conocen tarde.",
        "La demanda y la hidrología conocidas de antemano reducen poco el error del nivel del día (anexo D), y el "
        "precio sale de las ofertas de los generadores, que se conocen tarde.")

# ---------------------------------------------------------------- 2. tabla de la mediana del error por año
# La tabla nueva va antes de la del experimento de decisión, así que esa pasa de 21 a 22.
k = [(s, e) for s, e, t in cuerpo(d) if "tabla 21" in t]
assert len(k) == 1
s, e = k[0]
d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], "tabla 21", "tabla 22") + d.doc[e:]

med = pd.read_csv(RAIZ / "resultados" / "revision" / "mediana_error.csv").set_index(["caso", "pronostico"])
casos = ["2023", "2024", "2025", "2023-2025", "2026"]
filas = [["Pronóstico"] + casos]
for mo in ["Ingenuo del día", "Ingenuo semanal", "SARIMAX", "XGBoost", "LSTM"]:
    filas.append([mo] + [n(med.loc[(c, mo), "mediana_log"]) for c in casos])
# lo que dice el texto, comprobado contra los datos
for a in ("2024", "2025"):
    assert all(med.loc[(a, m), "mediana_log"] > med.loc[(a, "Ingenuo del día"), "mediana_log"]
               for m in ("SARIMAX", "XGBoost", "LSTM"))
assert med.loc[("2023", "LSTM"), "mediana_log"] < med.loc[("2023", "Ingenuo del día"), "mediana_log"]
assert all(med.loc[("2023", m), "mediana_log"] > med.loc[("2023", "Ingenuo del día"), "mediana_log"]
           for m in ("SARIMAX", "XGBoost"))

cambiar(d, "Además, en un día típico la ventaja es menor que la que muestra el RMSE: en 2023-2025,",
        "Además, en un día típico la ventaja es menor que la que muestra el RMSE (tabla 21): en 2023-2025,")
cambiar(d, "Los modelos bajan el RMSE sobre todo porque recortan los errores grandes.",
        "Por años, en 2024 y 2025 el ingenuo del día tuvo menor mediana que los tres modelos, y en 2023 solo la "
        "LSTM la tuvo menor que él. Los modelos bajan el RMSE sobre todo porque recortan los errores grandes: en "
        "un día típico el ingenuo del día acierta casi igual o mejor, y la ventaja de los modelos está en los días "
        "en que el precio cambia mucho.")
tras(d, "En El Niño la LSTM mantuvo su ventaja",
     cap("Mediana del error absoluto en logaritmo por año, *h* = 3 a 9.")
     + tabla(filas, [3.6, 2.0, 2.0, 2.0, 2.4, 2.0])
     + nota("Nota: mediana del valor absoluto del error en logaritmo de los 168 precios de cada pronóstico; el año "
            "es el del día de origen. Un valor menor que el del ingenuo del día indica que el modelo acierta más en "
            "un día típico. " + FUENTE))

# ---------------------------------------------------------------- 3. trabajo futuro y referencias
cambiar(d, "Con eso en cuenta, quedan seis líneas de trabajo.", "Con eso en cuenta, quedan nueve líneas de trabajo.")
cambiar(d, "sirve más un rango o una distribución del precio, una de las direcciones que señala Weron (2014).",
        "sirve más un rango o una distribución del precio, una de las direcciones que señala Weron (2014). El "
        "paso siguiente es construir intervalos de 80% para el mejor modelo, con los cuantiles empíricos de los "
        "errores recientes o con regresión cuantílica sobre los pronósticos (Nowotarski y Weron, 2015), y "
        "evaluarlos por año con su cobertura y con la pérdida pinball, una regla de puntuación propia (Gneiting y "
        "Raftery, 2007). Un intervalo de 80% sirve si cubre cerca de 80% de los precios en cada año, y no solo en "
        "el promedio de los cuatro.")
tras(d, "Pronósticos con incertidumbre.",
     p("*Más modelos de referencia.* La comparación tiene un modelo estadístico, uno lineal con regularización, uno "
       "de boosting y una red recurrente. Faltan otros que la literatura usa como referencia: un modelo "
       "autorregresivo experto con variables exógenas, como los de Ziel y Weron (2018); un modelo de cambio de "
       "régimen (Hamilton, 1989), que Janczura y Weron (2010) compararon en precios de la electricidad y que podría "
       "captar el paso entre los regímenes de aportes de la tabla 20; la red densa del punto de referencia abierto "
       "de Lago et al. (2021); otro boosting, como LightGBM (Ke et al., 2017), y redes más recientes, como NBEATSx "
       "(Olivares et al., 2023) o el Temporal Fusion Transformer (Lim et al., 2021). Todos deberían seguir el mismo "
       "diseño de la sección 3.3, con la configuración elegida con datos hasta 2022 y evaluados en el periodo "
       "limpio.")
     + p("*El aporte de la hidrología.* La comparación de la tabla 18 agrega a la vez los bloques 3 y 4, el "
         "despacho de hoy y el estado hidrológico. Correr XGBoost con y sin el embalse, los aportes, el ONI y la "
         "distancia al precio de escasez, con la prueba de Diebold-Mariano entre las dos versiones en cada año, "
         "mediría cuánto aporta la hidrología por sí sola y en qué años.")
     + p("*La variación entre semillas.* La LSTM se evaluó con tres semillas (sección 3.6), pero XGBoost, que toma "
         "en cada árbol una fracción de las filas y de las columnas (tabla 7) y por eso también depende de su "
         "semilla, se corrió con una sola. Repetirlo con varias semillas y reportar la desviación del RMSE entre "
         "ellas diría si las diferencias entre modelos de la tabla 15 son mayores que esa variación."))

# Referencias en el texto donde tienen sentido
cambiar(d, "Nowotarski y Weron (2018) revisan además el pronóstico probabilístico, que entrega un rango o una "
           "distribución del precio en lugar de un solo valor.",
        "Nowotarski y Weron (2018) revisan además el pronóstico probabilístico, que entrega un rango o una "
        "distribución del precio en lugar de un solo valor, y Hong et al. (2020) hacen un balance más amplio del "
        "pronóstico en energía, que incluye la demanda y la generación renovable.")
cambiar(d, "y con ese modelo se pronostica desde cada día del mes (Hyndman y Athanasopoulos, 2021).",
        "y con ese modelo se pronostica desde cada día del mes (Tashman, 2000; Hyndman y Athanasopoulos, 2021).")
cambiar(d, "Por último, el pronóstico en pesos de la ecuación (21) es siempre positivo.",
        "Por último, el pronóstico en pesos de la ecuación (21) es siempre positivo. Otra transformación usada en "
        "precios de la electricidad es el seno hiperbólico inverso, que admite precios cero o negativos "
        "(Uniejewski et al., 2018); el precio de bolsa colombiano no tuvo ninguno de los dos en la muestra, así que "
        "el logaritmo basta.")

d.referencias([
    "Gneiting, T., y Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *Journal of "
    "the American Statistical Association*, *102*(477), 359-378. https://doi.org/10.1198/016214506000001437",
    "Hamilton, J. D. (1989). A new approach to the economic analysis of nonstationary time series and the business "
    "cycle. *Econometrica*, *57*(2), 357-384. https://doi.org/10.2307/1912559",
    "Hong, T., Pinson, P., Wang, Y., Weron, R., Yang, D., y Zareipour, H. (2020). Energy forecasting: A review and "
    "outlook. *IEEE Open Access Journal of Power and Energy*, *7*, 376-388. https://doi.org/10.1109/OAJPE.2020.3029979",
    "Janczura, J., y Weron, R. (2010). An empirical comparison of alternate regime-switching models for electricity "
    "spot prices. *Energy Economics*, *32*(5), 1059-1073. https://doi.org/10.1016/j.eneco.2010.05.008",
    "Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., y Liu, T.-Y. (2017). LightGBM: A highly "
    "efficient gradient boosting decision tree. En *Advances in Neural Information Processing Systems 30* "
    "(pp. 3146-3154).",
    "Lim, B., Arık, S. Ö., Loeff, N., y Pfister, T. (2021). Temporal Fusion Transformers for interpretable "
    "multi-horizon time series forecasting. *International Journal of Forecasting*, *37*(4), 1748-1764. "
    "https://doi.org/10.1016/j.ijforecast.2021.03.012",
    "Nowotarski, J., y Weron, R. (2015). Computing electricity spot price prediction intervals using quantile "
    "regression and forecast averaging. *Computational Statistics*, *30*(3), 791-803. "
    "https://doi.org/10.1007/s00180-014-0523-0",
    "Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International "
    "Journal of Forecasting*, *16*(4), 437-450. https://doi.org/10.1016/S0169-2070(00)00065-0",
])
d.renumerar()

texto = Docx.texto(d.doc)
for x in ("(Gneiting y Raftery, 2007)", "(Hamilton, 1989)", "Hong et al. (2020)", "Janczura y Weron (2010)",
          "(Ke et al., 2017)", "(Lim et al., 2021)", "(Nowotarski y Weron, 2015)", "(Tashman, 2000;",
          "(Uniejewski et al., 2018)", "Gneiting, T.", "Hamilton, J. D.", "Hong, T.", "Janczura, J.", "Ke, G.",
          "Lim, B.", "Nowotarski, J., y Weron, R. (2015)", "Tashman, L. J.", "nueve líneas de trabajo"):
    assert x in texto, x
assert "depende sobre todo de cómo van a ofertar" not in texto
assert "el nivel depende de cómo van a ofertar" not in texto
assert "depende de cómo ofertan los generadores" not in texto
d.guardar(sys.argv[2])
print("listo")
