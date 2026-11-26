"""Revisión del informe por los comentarios de la asesora del 26 de noviembre de 2026 (segunda parte).
Aplica los puntos 2.3 (mapa de calor), 2.6 (tabla mensual), 2.11 y 2.12 de Comentarios_Andres_2026-11-26.pdf:
- Resumen: "con la misma información alineada a su publicación"; resumen en inglés después de las palabras clave.
- 2.2 Antecedentes reescrita: literatura internacional, mercados hidráulicos, Colombia y la hidroclimatología, con la
  tabla 1 ampliada a 20 filas y un párrafo final con la contribución. Lago et al. (2021) como modelo del capítulo IV.
- Una sola convención de signo: el sesgo de la tabla 17 pasa a real menos pronóstico, como la ecuación (12).
- Definición del precio de bolsa: CREG 024 de 1995 (1995a), modificada por CREG 051 de 2009; el Código de Operación
  pasa a ser CREG 1995b. Sale la cita a CREG 055 de 1994.
- Anexo E: mapa de calor de Diebold-Mariano entre todos los pares (resultados/revision/dm_pares_*.png).
- Anexo F: promedios mensuales de 2023-2025 (resultados/revision/meses_2023_2025.csv).
Queda pendiente el capítulo propio de mercado y datos.
Uso: python s_47_revision_26nov_b.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, figura, leyenda, reemplazar_en_bloque, runs, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
RAIZ = Path(__file__).resolve().parents[2]
REV = RAIZ / "resultados" / "revision"


# ------------------------------------------------------------------ utilidades (las mismas de s_46)
def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def uno(d, inicio):
    k = [(s, e) for s, e, t in cuerpo(d) if t.startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return k[0]


def rep(d, inicio, texto):
    s, e = uno(d, inicio)
    p = d.doc[s:e]
    assert p.startswith("<w:p") and not p.startswith("<w:tbl")
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
    apertura = re.match(r"<w:p(?:\s[^>]*)?>", p).group(0)
    d.doc = d.doc[:s] + apertura + (ppr.group(0) if ppr else "") + runs(texto) + "</w:p>" + d.doc[e:]


def cambiar(d, viejo, nuevo, con=""):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t and con in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def cambiar_todos(d, viejo, nuevo, minimo=1):
    """Cambia `viejo` por `nuevo` en todos los bloques del cuerpo que lo tengan (de atrás hacia adelante)."""
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) >= minimo, f"hay {len(k)} bloques con {viejo!r}"
    for s, e in reversed(k):
        d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def tras(d, inicio, xml):
    s, e = uno(d, inicio)
    d.doc = d.doc[:e] + xml + d.doc[e:]


def borrar(d, inicio):
    s, e = uno(d, inicio)
    d.doc = d.doc[:s] + d.doc[e:]


def p(t):
    return f"<w:p>{runs(t)}</w:p>"


def nota(t):
    x = runs(t).replace("<w:r><w:rPr>", '<w:r><w:rPr><w:sz w:val="20"/>').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{x}</w:p>'


def cap_anexo(nombre, texto):
    return ('<w:p><w:pPr><w:pStyle w:val="Descripcin"/><w:keepNext/><w:spacing w:before="240"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">{nombre}. </w:t></w:r>{runs(texto)}</w:p>')


def cap_fig(nombre, texto):
    """Leyenda fija de una figura de anexo, sin keepNext, para que la figura siguiente pueda quedar en otra página."""
    return ('<w:p><w:pPr><w:pStyle w:val="Descripcin"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">{nombre}. </w:t></w:r>{runs(texto)}</w:p>')


def n(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",").replace("-", "−")


def imagen(ruta, rid, id_dibujo, ancho_cm):
    """Solo el párrafo de la imagen de figura(), sin su leyenda numerada (los anexos llevan leyenda fija)."""
    x = figura(ruta, rid, id_dibujo, ancho_cm, "")
    return x[:x.index('<w:p><w:pPr><w:pStyle w:val="Descripcin"/>')]


FUENTE = "Fuente: elaboración propia con datos de XM (2026)."

d = Docx(ENTRADA)
todo_antes = " ".join(t for _, _, t in cuerpo(d))
assert "Abstract" not in todo_antes and "Anexo E" not in todo_antes, "la segunda parte ya está aplicada"

# =================================================================== Resumen y abstract
cambiar(d, "Esa ventaja viene de la información y no de la red: con los mismos datos, como el despacho programado, "
           "que se conoce antes que el precio,",
        "Esa ventaja viene de la información y no de la red: con la misma información alineada a su publicación, "
        "como el despacho programado, que se conoce antes que el precio,")

ABSTRACT = [
    "The spot price (precio de bolsa) is the hourly price at which energy is traded in the Colombian wholesale "
    "market. Between 65% and 86% of each year's generation is hydroelectric, so the price depends on the water "
    "available and changes a great deal from one week to the next, which makes it hard to decide in advance when to "
    "buy or consume energy. This project forecasts the 168 hourly prices of the following week with public data "
    "from XM, SIMEM, NOAA, ERA5 and IDEAM between 2015 and 2026. Since the price becomes known with a delay of two or "
    "three days, the forecast week corresponds to horizons of 3 to 9 days, and the results are also checked for "
    "horizons of 4 to 10.",

    "Three models are compared: SARIMAX, with one model per hour; XGBoost, with one model per horizon and variables "
    "chosen among 1,861 columns; and an encoder-decoder LSTM network that receives each datum from the day it is "
    "published. To separate the effect of the model from the effect of the information, four references are added: "
    "the linear LEAR model, an XGBoost with the same information as the LSTM, an LSTM with only the price and the "
    "calendar, and two forecast combinations.",

    "The models are retrained every month and evaluated in 2023-2025 and in 2026 against the rule of repeating the "
    "last known price. A model is considered useful if it reduces the RMSE in logarithms by at least 5% against that "
    "rule and the Diebold-Mariano test gives p < 0.05. These tests are not fully independent of the design: the LSTM "
    "was designed after a first version had gone through them, and the one-week scope of XGBoost was chosen after "
    "seeing the 2026 test. For that reason the days from 7 October to 20 November 2026, which no decision used, are "
    "evaluated as well.",

    "The three models meet the criterion. Of the three, the LSTM, with the information aligned to its publication, "
    "had the lowest error: it reduces it by 14.9% in 2023-2025 and 19.7% in 2026. XGBoost reduces it by 11.6% and "
    "10.0%, and SARIMAX by 6.4% and 5.6%. That advantage comes from the information and not from the network: with "
    "the same information aligned to its publication, such as the scheduled dispatch, which is known before the "
    "price, XGBoost reduces the error by 18.5% and 22.4%, and LEAR by 21.3% and 24.8%, while the LSTM with only the "
    "price and the calendar reduces it by 6.1% and 8.8%. In the days after 6 October all models have less error than "
    "the naive rule, but with 45 days no difference is significant. The models lose their advantage during the "
    "inflow deficit of August to November 2024, when the price reached its maximum with the El Niño index at "
    "neutral values, and not during the 2023-2024 El Niño. In pesos the improvements are smaller, and in 2023-2025 "
    "only that of SARIMAX is significant. In a simple decision experiment, the models capture between 32% and 55% "
    "of the possible saving when choosing the two cheapest days of the week, against 20% and 24% for repeating the "
    "previous week; for choosing the cheapest hours of each day, repeating the previous week captures as much as the "
    "models.",
]
titulo_abstract = d.titulo_como("Resumen", "Abstract")
tras(d, "Palabras clave:", titulo_abstract + "".join(p(t) for t in ABSTRACT)
     + p("**Keywords:** spot price, forecasting, Colombian electricity market, SARIMAX, XGBoost, LSTM, LEAR, "
         "Diebold-Mariano, walk-forward."))

# =================================================================== CREG: definición del precio de bolsa
cambiar_todos(d, "(CREG, 1995)", "(CREG, 1995b)", minimo=4)
cambiar(d, "CREG (1995).", "CREG (1995b).", con="Formación del precio de bolsa en una hora")
cambiar(d, "lo que realmente generó o consumió (CREG, 1994)", "lo que realmente generó o consumió (CREG, 1995a)")
cambiar(d, "el precio de bolsa de cada hora es la oferta de la planta marginal de ese despacho (CREG, 1994)",
        "el precio de bolsa de cada hora es la oferta de la planta marginal de ese despacho, es decir, el mayor "
        "precio de oferta entre las plantas despachadas en el despacho ideal (CREG, 1995a, modificada por CREG, 2009)")
cambiar(d, "Comisión de Regulación de Energía y Gas [CREG]. (1995). Resolución CREG 025 de 1995: Código de redes.",
        "Comisión de Regulación de Energía y Gas [CREG]. (1995b). Resolución CREG 025 de 1995, del 13 de julio de "
        "1995: Código de redes, que incluye el Código de Operación.")
borrar(d, "Comisión de Regulación de Energía y Gas [CREG]. (1994). Resolución CREG 055 de 1994.")

# =================================================================== convención de signo: sesgo = real − pronóstico
s, e = uno(d, "PronósticoRMSEMAESesgoMejora en pesos")
t17 = d.doc[s:e]
for viejo, nuevo in [("1,3", "−1,3"), ("1,8", "−1,8"), ("−15,3", "15,3"), ("−46,4", "46,4"), ("−33,1", "33,1"),
                     ("−8,3", "8,3"), ("−13,0", "13,0"), ("−29,2", "29,2"), ("−38,0", "38,0"), ("−30,6", "30,6")]:
    patron = re.compile(r"(<w:t[^>]*>)" + re.escape(viejo) + r"(</w:t>)")
    assert len(patron.findall(t17)) == 1, viejo
    t17 = patron.sub(lambda m: m.group(1) + nuevo + m.group(2), t17, count=1)
d.doc = d.doc[:s] + t17 + d.doc[e:]
cambiar(d, "El sesgo es el promedio del precio pronosticado menos el real; es negativo cuando el pronóstico queda por "
           "debajo.",
        "El sesgo es el promedio del error en pesos, el precio real menos el pronosticado, con el mismo signo de la "
        "ecuación (12); es positivo cuando el pronóstico queda por debajo.")
cambiar(d, "su sesgo en 2023-2025 pasó de −15,3 a 7,0 COP/kWh", "su sesgo en 2023-2025 pasó de 15,3 a −7,0 COP/kWh")

# =================================================================== 2.2 Antecedentes
rep(d, "Weron (2014) clasifica los métodos de pronóstico",
    "Weron (2014) clasifica los métodos de pronóstico del precio de la electricidad en cinco grupos: modelos "
    "multiagente, fundamentales, de forma reducida, estadísticos y de inteligencia computacional. Este trabajo usa "
    "los dos últimos: SARIMAX es un modelo estadístico, y XGBoost y la LSTM son de aprendizaje automático. La misma "
    "revisión distingue el corto plazo, de horas a unos días, del mediano plazo, de días a meses. El horizonte de "
    "este trabajo, de tres a nueve días, queda entre los dos, mientras que la mayor parte de la literatura se "
    "concentra en el mercado del día siguiente (Lago et al., 2021). Nowotarski y Weron (2018) revisan además el "
    "pronóstico probabilístico, que entrega un rango o una distribución del precio en lugar de un solo valor.")
rep(d, "Lago et al. (2018) compararon modelos de aprendizaje profundo",
    "Los primeros trabajos del día siguiente usaron modelos estadísticos. Contreras et al. (2003) pronosticaron el "
    "precio horario de España y California con modelos ARIMA, con errores medios cercanos a 10% y 5%, y Conejo et "
    "al. (2005) redujeron el error del ARIMA en España al descomponer antes la serie con la transformada wavelet. "
    "Weron y Misiorek (2008) compararon en California y en Nord Pool modelos autorregresivos, de umbral, de cambio "
    "de régimen y semiparamétricos, y encontraron que los semiparamétricos que reciben la demanda prevista dan los "
    "mejores pronósticos puntuales y de intervalo. Kristiansen (2012) pronosticó con un modelo autorregresivo el "
    "precio del día siguiente de Nord Pool, el mercado nórdico de base hidráulica. El grupo de Weron estudió después la construcción del modelo: "
    "Uniejewski et al. (2018) mostraron en varios mercados que estabilizar la varianza del precio con una "
    "transformación, como el seno hiperbólico inverso, mejora el pronóstico; Ziel y Weron (2018) compararon modelos "
    "univariados y multivariados de alta dimensión con LASSO en doce conjuntos de datos, sin que ninguno de los dos marcos "
    "dominara, y mostraron que promediar los dos mejora, y Marcjasz et al. (2019) encontraron que un comité de redes "
    "NARX con la componente estacional de largo plazo supera a los modelos lineales con la misma información.")
rep(d, "En la misma universidad, el precio de bolsa se ha pronosticado desde hace dos décadas",
    "Con el aprendizaje profundo, Lago et al. (2018) compararon 27 métodos en el mercado belga y encontraron que las "
    "redes profundas tenían el menor error y que, en general, los métodos de aprendizaje automático superaban a los "
    "estadísticos. Lago et al. (2021) revisaron luego el estado del arte en cinco mercados, Nord Pool, PJM, Bélgica, "
    "Francia y Alemania, con dos modelos de referencia, el lineal LEAR y una red profunda, y propusieron prácticas "
    "para que los estudios sean comparables: evaluar en periodos largos, de al menos un año; comparar contra "
    "referencias bien establecidas, y usar pruebas estadísticas, como la de Diebold y Mariano entre todos los pares "
    "de modelos, presentada como un mapa de calor. En esos mercados LEAR quedó cerca de la red profunda. Olivares et "
    "al. (2023) mejoraron esas referencias hasta 5% con NBEATSx, una red con variables exógenas. El capítulo IV "
    "sigue la forma de presentar los resultados de Lago et al. (2021): el error de cada modelo por periodo, la "
    "prueba contra el ingenuo y la prueba entre pares (anexo E). En la Universidad de los Andes, Salazar-Peña et al. "
    "(2025) compararon redes LSTM y Transformer para pronosticar la generación solar del día y participar en el "
    "mercado intradiario.")
tras(d, "Con el aprendizaje profundo, Lago et al. (2018) compararon 27 métodos",
     p("En Colombia la literatura es más corta. Velásquez Henao et al. (2007) analizan las dificultades que "
       "encuentran investigadores y profesionales al pronosticar el precio de la electricidad en mercados "
       "competitivos. Lira et al. (2009) pronosticaron a corto plazo el precio del mercado colombiano, y Barrientos et al. (2012) modelaron el precio de "
       "largo plazo con vectores de corrección de errores y redes neuronales, con la demanda y la oferta como "
       "determinantes. Trespalacios et al. (2025) compararon métodos de aprendizaje profundo con la estructura ARIMA "
       "de Box y Jenkins para el precio spot colombiano: las redes siguen la tendencia fuera de muestra, pero no "
       "superan al modelo lineal. El papel del agua tiene su propia literatura: Poveda (2004) sintetiza la "
       "hidroclimatología de Colombia desde la escala interdecadal hasta la diurna, y Poveda et al. (2011) revisan "
       "cómo El Niño reduce la lluvia y los caudales en los Andes colombianos y La Niña los aumenta. Esa es la razón "
       "por la que el índice ONI y los aportes entran en los modelos de este trabajo (sección 3.1).")
     + p("En la misma universidad, el precio de bolsa se ha pronosticado desde hace dos décadas (tabla 1). Cárdenas "
         "Paredes (2005) usó modelos autorregresivos y lógica difusa, y Velásquez Rojas (2016) implementó una red "
         "neuronal dentro de un aplicativo web. Rojas Ardila (2018) comparó modelos bayesianos (BSTS y BVAR) con "
         "ARIMA y ARIMAX en horizontes de un día a seis meses: los bayesianos funcionaron bien a uno y a siete días, "
         "y a seis meses el ARIMA tuvo el menor error. Cárdenas Cárdenas (2021) comparó redes neuronales "
         "autorregresivas (NNAR) con ARIMA para el precio promedio diario, y su mejor modelo fue una NNAR con la "
         "demanda y el precio promedio de oferta como variables externas. González Pérez y Urbano Buriticá (2022) "
         "compararon SARIMAX, Prophet y redes LSTM para el precio horario del día siguiente, y eligieron una LSTM "
         "con un modelo para cada hora del día. Por fuera del pronóstico, Hidalgo Bastidas (2020) analizó el efecto "
         "de la entrada de las fuentes no convencionales de energía renovable sobre el precio."))
# solo el texto después del número, para no romper el campo SEQ de la leyenda
cambiar(d, "Trabajos de la Universidad de los Andes que pronostican el precio de bolsa.",
        "Trabajos que pronostican el precio de la electricidad: estudios internacionales, colombianos y de la "
        "Universidad de los Andes.", con="Tabla ")
ENC = ["Trabajo", "Mercado", "Resolución", "Horizonte", "Modelos", "Referencia", "Información exógena", "Hallazgo"]
FILAS_1 = [ENC,
    ["Contreras et al. (2003)", "España y California", "Horaria", "Día siguiente", "ARIMA", "Ninguna", "Ninguna",
     "Errores medios cercanos a 10% en España y 5% en California."],
    ["Conejo et al. (2005)", "España", "Horaria", "Día siguiente", "Wavelet y ARIMA", "ARIMA", "Ninguna",
     "La descomposición wavelet reduce el error del ARIMA."],
    ["Weron y Misiorek (2008)", "California y Nord Pool", "Horaria", "Día siguiente",
     "AR, de umbral, de cambio de régimen y semiparamétricos", "AR", "Demanda prevista",
     "Los semiparamétricos con la demanda dan los mejores pronósticos puntuales y de intervalo."],
    ["Kristiansen (2012)", "Nord Pool", "Horaria", "Día siguiente", "Autorregresivo", "—", "—",
     "Modelo autorregresivo para el precio del día siguiente en un mercado de base hidráulica."],
    ["Uniejewski et al. (2018)", "Varios mercados", "Horaria", "Día siguiente",
     "ARX con 16 transformaciones del precio", "ARX sin transformar", "Demanda prevista",
     "Estabilizar la varianza, por ejemplo con el seno hiperbólico inverso, mejora el pronóstico."],
    ["Ziel y Weron (2018)", "Doce conjuntos de datos", "Horaria", "Día siguiente",
     "AR univariados y multivariados con LASSO", "Ingenuo y AR", "Historia del precio",
     "Ningún marco domina; promediar los dos mejora."],
    ["Marcjasz et al. (2019)", "Varios mercados", "Horaria", "Día siguiente",
     "Redes NARX con componente estacional de largo plazo", "Modelos lineales SCAR", "Las mismas del modelo lineal",
     "Un comité de redes supera a los lineales con la misma información."],
    ["Lago et al. (2018)", "Bélgica", "Horaria", "Día siguiente", "27 métodos, cuatro de aprendizaje profundo",
     "Estadísticos y de aprendizaje automático", "Demanda y generación previstas; precios de Francia",
     "Las redes profundas tienen el menor error; el aprendizaje automático supera a los estadísticos."],
    ["Lago et al. (2021)", "Nord Pool, PJM, Bélgica, Francia y Alemania", "Horaria", "Día siguiente",
     "LEAR y red profunda", "LEAR", "Demanda y renovables previstas",
     "LEAR queda cerca de la red; fija prácticas de evaluación y una base de comparación abierta."],
    ["Olivares et al. (2023)", "Los cinco de Lago et al. (2021)", "Horaria", "Día siguiente", "NBEATSx",
     "LEAR y red profunda", "Demanda y renovables previstas", "Mejora hasta 5% frente a LEAR y la red."],
    ["Velásquez Henao et al. (2007)", "Colombia", "—", "—", "Reseña", "—", "—",
     "Analiza por qué es difícil pronosticar el precio en mercados competitivos."],
    ["Lira et al. (2009)", "Colombia", "—", "Corto plazo", "—", "—", "—",
     "Pronóstico de corto plazo del precio colombiano."],
    ["Barrientos et al. (2012)", "Colombia", "—", "Largo plazo", "Vectores de corrección de errores y redes neuronales",
     "—", "Demanda y oferta", "Tendencia al alza del precio de largo plazo."],
    ["Trespalacios et al. (2025)", "Colombia", "—", "—", "Aprendizaje profundo", "ARIMA (Box y Jenkins)", "—",
     "Las redes siguen la tendencia fuera de muestra, pero no superan al ARIMA."],
    ["Cárdenas Paredes (2005), Uniandes", "Colombia", "—", "—", "Autorregresivos y lógica difusa", "—", "—",
     "Tesis de maestría en Ingeniería Eléctrica."],
    ["Velásquez Rojas (2016), Uniandes", "Colombia", "—", "—", "Red neuronal", "—", "—",
     "Red dentro de un aplicativo web; pregrado en Ingeniería Eléctrica."],
    ["Rojas Ardila (2018), Uniandes", "Colombia", "Horaria", "De un día a seis meses", "BSTS, BVAR, ARIMA y ARIMAX",
     "ARIMA", "—", "Los bayesianos funcionan a uno y siete días; a seis meses gana ARIMA."],
    ["Cárdenas Cárdenas (2021), Uniandes", "Colombia", "Diaria", "Semana siguiente", "NNAR y ARIMA", "ARIMA",
     "Demanda y precio promedio de oferta", "La mejor fue una NNAR con variables externas."],
    ["González Pérez y Urbano Buriticá (2022), Uniandes", "Colombia", "Horaria", "Día siguiente",
     "SARIMAX, Prophet y LSTM", "—", "—", "Eligen una LSTM por hora del día."],
    ["Este trabajo", "Colombia", "Horaria", "De tres a nueve días",
     "SARIMAX, XGBoost y LSTM; LEAR y combinaciones", "Ingenuos del día y semanal; LEAR",
     "Despacho programado, hidrología, demanda y clima, alineados a su publicación",
     "La ventaja viene de la información alineada a su publicación, no del modelo."]]
assert len(FILAS_1) == 21
s, e = uno(d, "TrabajoProgramaModelos")
d.doc = d.doc[:s] + tabla(FILAS_1, [2.1, 1.6, 1.7, 1.6, 2.2, 1.7, 1.9, 2.7], tam=16, junta=False) + d.doc[e:]
cambiar(d, "Fuente: elaboración propia con base en los trabajos citados.",
        "Nota: la referencia es el modelo contra el que cada estudio compara; la raya indica que el trabajo no lo "
        "reporta o no aplica. Fuente: elaboración propia con base en los trabajos citados.")
rep(d, "Estos trabajos muestran que en el precio de bolsa se han probado",
    "La tabla 1 muestra lo que no se ha hecho. Casi toda la literatura internacional pronostica el día siguiente, "
    "con la demanda y las renovables previstas como información exógena, y en los mercados hidráulicos el agua entra "
    "de forma indirecta. Los trabajos colombianos han probado modelos estadísticos, difusos y redes neuronales, con "
    "resultados que dependen del horizonte, del periodo y de cómo se evalúan, pero ninguno pronostica la semana "
    "completa desde el último precio conocido, ninguno alinea cada dato con el día en que se publica y ninguno "
    "compara los modelos en las mismas filas con una prueba estadística y contra una referencia establecida. La "
    "contribución de este trabajo está ahí: mide el atraso con que se publica cada dato y arma el panel con esa "
    "alineación; compara un modelo estadístico, uno de árboles y una red recurrente con el mismo diseño, en un "
    "horizonte de tres a nueve días y con las prácticas de evaluación de Lago et al. (2021), incluido LEAR como "
    "referencia, y separa cuánto de la diferencia entre modelos viene del modelo y cuánto de la información.")

# =================================================================== erratas de la lectura completa
cambiar(d, "Por eso se agregó un tercer periodo, el periodo limpio,",
        "Por eso se agregó un tercer periodo de prueba, el periodo limpio,")

# =================================================================== punteros a los anexos nuevos
cambiar(d, "Más adelante, la tabla 18 separa cuánto de estas diferencias viene del modelo y cuánto de la información.",
        "Más adelante, la tabla 18 separa cuánto de estas diferencias viene del modelo y cuánto de la información. La "
        "prueba de Diebold-Mariano entre todos los pares de modelos, como mapa de calor, está en el anexo E.")
cambiar(d, "La tabla 20 separa el error de los modelos por episodio y por régimen de aportes,",
        "Los promedios mensuales de precio, embalse, aportes y ONI de 2023 a 2025 están en el anexo F. La tabla 20 "
        "separa el error de los modelos por episodio y por régimen de aportes,")

# =================================================================== Anexos E y F
for i, per in enumerate(("2020_2022", "2023_2025", "2026")):
    d.agregar_imagen(REV / f"dm_pares_{per}.png", f"rIdDm{i}")
mes = pd.read_csv(REV / "meses_2023_2025.csv")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
ff = [["Mes", "Precio (COP/kWh)", "Embalse (%)", "Aportes (% de la media)", "ONI"]]
for _, r in mes.iterrows():
    a, m_ = r["mes"].split("-")
    ff.append([f"{MESES[int(m_) - 1].capitalize()} de {a}", n(r["precio_cop_kwh"], 0), n(r["embalse_pct"], 0),
               n(r["aportes_pct_media"], 0), n(r["oni"], 2)])
assert len(ff) == 37
anexos = (
    d.titulo_como("Anexo B. Medidas y criterios de XGBoost", "Anexo E. Prueba de Diebold-Mariano entre pares de modelos")
    + p("Las figuras E1 a E3 presentan la prueba de Diebold-Mariano entre todos los pares de pronósticos, como en "
        "Lago et al. (2021). Cada celda es el valor *p* de la hipótesis de que el modelo de la columna tiene menos "
        "error cuadrático que el de la fila, en la semana completa (*h* = 3 a 9), con la varianza de la sección 3.3 "
        "y la corrección de Harvey et al. (1997); los valores menores de 0,10 van en verde y los mayores en blanco. "
        "En 2020-2022 los modelos corrieron con reentrenamiento mensual; en 2023-2025 y 2026 son las pruebas de la "
        "tabla 15, y las cifras de los modelos agregados son exploratorias (sección 3.7). Los modelos con la "
        "información alineada a su publicación, LEAR alineado, XGBoost alineado y la LSTM, tienen menos error que todos los que "
        "usan la información cortada en el día *t*: LEAR alineado y XGBoost alineado, con *p* < 0,01 en los tres "
        "periodos, y la LSTM con *p* de 0,05 o menos, salvo frente a XGBoost en 2023-2025 y frente a LEAR en 2026, "
        "donde queda en el límite. Entre LEAR alineado y XGBoost alineado no hay diferencia significativa en "
        "ningún periodo. Los valores de las figuras son de una cola; los del texto del capítulo IV, de dos.")
    + imagen(REV / "dm_pares_2020_2022.png", "rIdDm0", 9001, 12.5)
    + cap_fig("Figura E1", "Valor *p* de Diebold-Mariano entre pares de pronósticos, 2020-2022, *h* = 3 a 9. "
                + FUENTE)
    + imagen(REV / "dm_pares_2023_2025.png", "rIdDm1", 9002, 12.5)
    + cap_fig("Figura E2", "Valor *p* de Diebold-Mariano entre pares de pronósticos, prueba de 2023-2025, "
                "*h* = 3 a 9. " + FUENTE)
    + imagen(REV / "dm_pares_2026.png", "rIdDm2", 9003, 12.5)
    + cap_fig("Figura E3", "Valor *p* de Diebold-Mariano entre pares de pronósticos, prueba de 2026, *h* = 3 a 9. "
                + FUENTE)
    + d.titulo_como("Anexo B. Medidas y criterios de XGBoost", "Anexo F. Promedios mensuales de 2023 a 2025")
    + p("La tabla F1 presenta, para cada mes de 2023 a 2025, el precio de bolsa promedio, el volumen útil de los "
        "embalses como porcentaje de la capacidad útil, los aportes hídricos como porcentaje de su media histórica y "
        "el índice ONI tal como entra al panel, es decir, el último publicado en ese mes (sección 3.2). Es la base de los episodios de la sección 4.1: El Niño "
        "de septiembre de 2023 a abril de 2024, y el déficit de aportes de agosto a noviembre de 2024, cuando el "
        "precio llegó a su máximo con el ONI en valores neutros.")
    + cap_anexo("Tabla F1", "Promedios mensuales del precio de bolsa, el embalse, los aportes y el ONI, 2023-2025.")
    + tabla(ff, [3.4, 3.0, 2.6, 3.8, 1.8], tam=18, junta=False)
    + nota("Fuente: elaboración propia con datos de XM (2026) y de la NOAA (2026)."))
fin = d.doc.rfind("<w:sectPr")
d.doc = d.doc[:fin] + anexos + d.doc[fin:]

# =================================================================== referencias
d.referencias([
    "Barrientos, J., Rodas, E., Velilla, E., Lopera, M., y Villada, F. (2012). Modelo para el pronóstico del precio de "
    "la energía eléctrica en Colombia. *Lecturas de Economía*, (77), 91-127. https://doi.org/10.17533/udea.le.n77a14771",
    "Comisión de Regulación de Energía y Gas [CREG]. (1995a). Resolución CREG 024 de 1995, del 13 de julio de 1995: "
    "Reglamento de aspectos comerciales del mercado mayorista de energía en el sistema interconectado nacional. "
    "Gestor normativo de la CREG.",
    "Conejo, A. J., Plazas, M. A., Espínola, R., y Molina, A. B. (2005). Day-ahead electricity price forecasting using "
    "the wavelet transform and ARIMA models. *IEEE Transactions on Power Systems*, 20(2), 1035-1042. "
    "https://doi.org/10.1109/TPWRS.2005.846054",
    "Contreras, J., Espínola, R., Nogales, F. J., y Conejo, A. J. (2003). ARIMA models to predict next-day electricity "
    "prices. *IEEE Transactions on Power Systems*, 18(3), 1014-1020. https://doi.org/10.1109/TPWRS.2002.804943",
    "Kristiansen, T. (2012). Forecasting Nord Pool day-ahead prices with an autoregressive model. *Energy Policy*, 49, "
    "328-332. https://doi.org/10.1016/j.enpol.2012.06.028",
    "Lira, F., Muñoz, C., Núñez, F., y Cipriano, A. (2009). Short-term forecasting of electricity prices in the "
    "Colombian electricity market. *IET Generation, Transmission & Distribution*, 3(11), 980-986. "
    "https://doi.org/10.1049/iet-gtd.2009.0218",
    "Marcjasz, G., Uniejewski, B., y Weron, R. (2019). On the importance of the long-term seasonal component in "
    "day-ahead electricity price forecasting with NARX neural networks. *International Journal of Forecasting*, "
    "35(4), 1520-1532. https://doi.org/10.1016/j.ijforecast.2017.11.009",
    "Nowotarski, J., y Weron, R. (2018). Recent advances in electricity price forecasting: A review of probabilistic "
    "forecasting. *Renewable and Sustainable Energy Reviews*, 81, 1548-1568. https://doi.org/10.1016/j.rser.2017.05.234",
    "Olivares, K. G., Challu, C., Marcjasz, G., Weron, R., y Dubrawski, A. (2023). Neural basis expansion analysis "
    "with exogenous variables: Forecasting electricity prices with NBEATSx. *International Journal of Forecasting*, "
    "39(2), 884-900. https://doi.org/10.1016/j.ijforecast.2022.03.001",
    "Poveda, G. (2004). La hidroclimatología de Colombia: una síntesis desde la escala inter-decadal hasta la escala "
    "diurna. *Revista de la Academia Colombiana de Ciencias Exactas, Físicas y Naturales*, 28(107), 201-221.",
    "Poveda, G., Álvarez, D. M., y Rueda, Ó. A. (2011). Hydro-climatic variability over the Andes of Colombia "
    "associated with ENSO: A review of climatic processes and their impact on one of the Earth's most important "
    "biodiversity hotspots. *Climate Dynamics*, 36(11-12), 2233-2249. https://doi.org/10.1007/s00382-010-0931-y",
    "Trespalacios, A., Franco Ceballos, L. E., y Palacios Palacios, F. Y. (2025). Aproximación tipo aprendizaje "
    "profundo al precio spot de la electricidad en Colombia. *Revista Colombiana de Computación*, 26(2), 1-15. "
    "https://doi.org/10.29375/25392115.4587",
    "Velásquez Henao, J. D., Dyner Rezonzew, I., y Castro Souza, R. (2007). ¿Por qué es tan difícil obtener buenos "
    "pronósticos de los precios de la electricidad en mercados competitivos? *Cuadernos de Administración*, 20(34), "
    "259-282.",
    "Weron, R., y Misiorek, A. (2008). Forecasting spot electricity prices: A comparison of parametric and "
    "semiparametric time series models. *International Journal of Forecasting*, 24(4), 744-763. "
    "https://doi.org/10.1016/j.ijforecast.2008.08.004",
    "Ziel, F., y Weron, R. (2018). Day-ahead electricity price forecasting with high-dimensional structures: "
    "Univariate vs. multivariate modeling frameworks. *Energy Economics*, 70, 396-420. "
    "https://doi.org/10.1016/j.eneco.2017.12.016",
])
d.renumerar()

# =================================================================== comprobaciones
todo = " ".join(t for _, _, t in cuerpo(d))
assert "CREG, 1994" not in todo and "(CREG, 1995)" not in todo
for frase in ("Abstract", "Keywords:", "Anexo E. Prueba de Diebold-Mariano", "Anexo F. Promedios mensuales",
              "Figura E3", "Tabla F1", "Kristiansen (2012)", "Poveda et al. (2011)", "anexo E", "anexo F"):
    assert frase in todo, frase
for frase in ("Su forma de presentar los resultados es la que sigue el capítulo IV",
              "El sesgo es el promedio del precio pronosticado menos el real"):
    assert frase not in todo, frase
titulos = [t for s_, e_, t in cuerpo(d) if "Ttulo" in d.doc[s_:e_][:400]]
assert titulos.index("Abstract") == titulos.index("Resumen") + 1
d.guardar(SALIDA)
print("listo:", SALIDA)
