"""Escribe el capítulo IV: la 4.1, los tres modelos frente a los dos ingenuos, y la 4.2, el valor para la toma de
decisiones. Las cifras salen de informe/figuras/datos_resultados_*.csv, que escribe fig_resultados.py con los
pronósticos guardados de cada prueba, y la figura es f27_error_por_horizonte.png. El ejercicio del oráculo de la 4.1
está en diagnosticos/RESULTADOS.md y la semana final en resultados/comparacion/semana_final_tres_modelos.csv.
Las cifras que van en el texto se comprueban contra los archivos antes de escribir.
Uso: python s4_resultados.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, acento, barra, ecuacion, figura, frac, leyenda, m, par, runs, sub, suma, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'
FUENTE_XM = "Fuente: elaboración propia con datos de XM (2026)."
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]


def fuente(texto):
    rpr = '<w:sz w:val="20"/>'
    texto = runs(texto).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace(
        "<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'{texto}</w:p>')


def bloque(textos):
    return "".join(par(t) for t in textos)


def n(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def pv(p):
    return "< 0,001" if p < 0.001 else n(p, 3)


# ----------------------------------------------------------------------------- cifras
leer = lambda nombre: pd.read_csv(FIG / f"datos_resultados_{nombre}.csv")
crit = leer("criterio").set_index(["periodo", "modelo", "bloque"]).sort_index()
med = leer("medidas").set_index(["periodo", "pronostico"])
anio = leer("por_anio").astype({"año": str}).set_index(["año", "modelo"])
pares = leer("pares").set_index(["caso", "par"])
nf = leer("nivel_forma").set_index(["periodo", "pronostico"])
hz = leer("por_horizonte").pivot_table(index=["periodo", "h"], columns="pronostico", values="RMSE")
celdas = leer("mejor_celda")
dec = leer("decision").set_index(["periodo", "pronostico"])
final = pd.read_csv(RAIZ / "resultados" / "comparacion" / "semana_final_tres_modelos.csv").set_index("modelo")

# todos los modelos cumplen en los dos periodos y los cuatro bloques, siempre contra el ingenuo del día
assert crit["cumple"].all() and (crit["ingenuo"] == "del día").all()
mejora_h = {mo: 100 * (1 - hz[mo] / hz[["Ingenuo del día", "Ingenuo semanal"]].min(axis=1)) for mo in MODELOS}
pesos = {(p, mo): 100 * (1 - med.loc[(p, mo), "RMSE pesos"] / med.loc[(p, "Ingenuo del día"), "RMSE pesos"])
         for p in ("2023-2025", "2026") for mo in MODELOS}
gana = celdas.groupby(["periodo", "mejor"]).size()

# cifras del texto que se comprueban contra los archivos
COMPROBAR = {
    "LSTM 2023-2025": (crit.loc[("2023-2025", "LSTM", "h = 3 a 9"), "mejora"], "14,9"),
    "LSTM 2026": (crit.loc[("2026", "LSTM", "h = 3 a 9"), "mejora"], "19,7"),
    "XGBoost 2023-2025": (crit.loc[("2023-2025", "XGBoost", "h = 3 a 9"), "mejora"], "11,6"),
    "XGBoost 2026": (crit.loc[("2026", "XGBoost", "h = 3 a 9"), "mejora"], "10,0"),
    "SARIMAX 2023-2025": (crit.loc[("2023-2025", "SARIMAX", "h = 3 a 9"), "mejora"], "6,4"),
    "SARIMAX 2026": (crit.loc[("2026", "SARIMAX", "h = 3 a 9"), "mejora"], "5,6"),
    "semanal 2023-2025": (100 * (med.loc[("2023-2025", "Ingenuo semanal"), "RMSE"]
                                 / med.loc[("2023-2025", "Ingenuo del día"), "RMSE"] - 1), "10,4"),
    "semanal 2026": (100 * (med.loc[("2026", "Ingenuo semanal"), "RMSE"]
                            / med.loc[("2026", "Ingenuo del día"), "RMSE"] - 1), "12,7"),
    "LSTM h3": (mejora_h["LSTM"][("2023-2025", 3)], "24,5"),
    "XGBoost h3": (mejora_h["XGBoost"][("2023-2025", 3)], "17,9"),
    "LSTM h9": (mejora_h["LSTM"][("2023-2025", 9)], "10,2"),
    "XGBoost h9": (mejora_h["XGBoost"][("2023-2025", 9)], "10,8"),
    "SARIMAX mín 2023-2025": (mejora_h["SARIMAX"]["2023-2025"].min(), "4,7"),
    "SARIMAX máx 2023-2025": (mejora_h["SARIMAX"]["2023-2025"].max(), "7,7"),
    "SARIMAX mín 2026": (mejora_h["SARIMAX"]["2026"].min(), "4,2"),
    "SARIMAX máx 2026": (mejora_h["SARIMAX"]["2026"].max(), "6,5"),
    "LSTM h9 2026": (mejora_h["LSTM"][("2026", 9)], "16,6"),
    "XGBoost h9 2026": (mejora_h["XGBoost"][("2026", 9)], "6,9"),
    "LSTM 2023": (anio.loc[("2023", "LSTM"), "mejora"], "21,6"),
    "XGBoost 2023": (anio.loc[("2023", "XGBoost"), "mejora"], "12,9"),
    "XGBoost 2024": (anio.loc[("2024", "XGBoost"), "mejora"], "7,6"),
    "LSTM 2024": (anio.loc[("2024", "LSTM"), "mejora"], "9,7"),
    "SARIMAX 2024": (anio.loc[("2024", "SARIMAX"), "mejora"], "6,1"),
    "XGBoost 2025": (anio.loc[("2025", "XGBoost"), "mejora"], "15,3"),
    "pesos LSTM": (pesos[("2023-2025", "LSTM")], "7,1"),
    "pesos SARIMAX": (pesos[("2023-2025", "SARIMAX")], "5,8"),
    "pesos XGBoost": (pesos[("2023-2025", "XGBoost")], "3,7"),
    "pesos LSTM 2026": (pesos[("2026", "LSTM")], "8,8"),
    "pesos SARIMAX 2026": (pesos[("2026", "SARIMAX")], "6,4"),
    "pesos XGBoost 2026": (pesos[("2026", "XGBoost")], "6,8"),
    "nivel en el error de la LSTM": (100 * nf.loc[("2023-2025", "LSTM"), "nivel"] ** 2
                                     / nf.loc[("2023-2025", "LSTM"), "RMSE"] ** 2, "66,1"),
    "ahorro LSTM": (dec.loc[("2023-2025", "LSTM"), "ahorro"], "42,6"),
    "ahorro LSTM 2026": (dec.loc[("2026", "LSTM"), "ahorro"], "50,8"),
    "ahorro semanal": (dec.loc[("2023-2025", "Ingenuo semanal"), "ahorro"], "19,4"),
    "ahorro semanal 2026": (dec.loc[("2026", "Ingenuo semanal"), "ahorro"], "22,1"),
    "ahorro SARIMAX": (dec.loc[("2023-2025", "SARIMAX"), "ahorro"], "39,8"),
    "ahorro XGBoost": (dec.loc[("2023-2025", "XGBoost"), "ahorro"], "36,2"),
    "LSTM del oráculo": (dec.loc[("2023-2025", "LSTM"), "del oraculo %"], "41,5"),
    "LSTM del oráculo 2026": (dec.loc[("2026", "LSTM"), "del oraculo %"], "61,3"),
    "LSTM % del precio": (dec.loc[("2023-2025", "LSTM"), "ahorro %"], "8,7"),
    "LSTM % del precio 2026": (dec.loc[("2026", "LSTM"), "ahorro %"], "10,4"),
    "semanal sup": (dec.loc[("2023-2025", "Ingenuo semanal"), "sup"], "29,1"),
    "semanal inf": (dec.loc[("2023-2025", "Ingenuo semanal"), "inf"], "9,8"),
    "LSTM inf": (dec.loc[("2023-2025", "LSTM"), "inf"], "32,5"),
    "LSTM sup": (dec.loc[("2023-2025", "LSTM"), "sup"], "53,9"),
}
for nombre, (valor, texto) in COMPROBAR.items():
    assert n(valor) == texto, (nombre, valor, texto)
assert dec.loc[("2023-2025", "Ingenuo semanal"), "sup"] < dec.loc[("2023-2025", "LSTM"), "inf"]
assert dec.loc[("2026", "Ingenuo semanal"), "sup"] > dec.loc[("2026", "LSTM"), "inf"]
assert [n(dec.loc[(p, "Oráculo"), "precio semana"], 0) for p in ("2023-2025", "2026")] == ["492", "486"]
assert list(dec.loc[(slice(None), "Oráculo"), "semanas"]) == [1087, 270]
PARES_TEXTO = {("2023-2025", "LSTM y SARIMAX"): "0,007", ("2026", "LSTM y SARIMAX"): "0,011",
               ("2023-2025", "XGBoost y SARIMAX"): "0,011", ("2026", "XGBoost y SARIMAX"): "0,062",
               ("2023-2025", "LSTM y XGBoost"): "0,107", ("2026", "LSTM y XGBoost"): "0,033"}
for clave, texto_p in PARES_TEXTO.items():
    assert pv(pares.loc[clave, "p"]) == texto_p and pares.loc[clave, "menor"] == clave[1].split(" y ")[0], clave
assert (pares.loc[["2024", "2025"], "p"] > 0.05).all() and (pares.loc["2023", "p"] < 0.05).all()
assert pares.loc[("2025", "LSTM y XGBoost"), "menor"] == "XGBoost"
# el patrón de nivel y forma: la LSTM tiene el menor error de nivel y XGBoost el menor de forma, en los dos periodos
for p in ("2023-2025", "2026"):
    assert nf.loc[p].loc[MODELOS, "nivel"].idxmin() == "LSTM" and nf.loc[p].loc[MODELOS, "forma"].idxmin() == "XGBoost"
assert [n(nf.loc[("2023-2025", x), c], 3) for x, c in [("Ingenuo del día", "nivel"), ("Ingenuo del día", "forma"),
        ("LSTM", "nivel"), ("XGBoost", "nivel"), ("SARIMAX", "nivel"), ("XGBoost", "forma"), ("SARIMAX", "forma"),
        ("LSTM", "forma")]] == ["0,415", "0,282", "0,347", "0,385", "0,402", "0,221", "0,243", "0,249"]
assert [n(-med.loc[("2023-2025", x), "sesgo pesos"], 0) for x in ("SARIMAX", "XGBoost")] == ["15", "46"]
assert gana[("2023-2025", "LSTM")] == 136 and gana[("2026", "LSTM")] == 166 and gana[("2023-2025", "XGBoost")] == 29
assert [n(final.loc[x, "MAPE (%)"]) for x in ["XGBoost", "SARIMAX", "Ingenuo del día", "LSTM"]] == \
    ["15,9", "17,9", "18,7", "23,2"]

# ----------------------------------------------------------------------------- tablas
filas = [["Pronóstico", "RMSE", "MAE", "MAPE (%)", "Mejora (%)", "*p*", "*h* = 3", "*h* = 3 a 7", "*h* = 8 a 9"]]
for p, nombre in [("2023-2025", "Prueba 2023-2025"), ("2026", "Prueba 2026")]:
    filas.append([f"*{nombre}*"] + [""] * 8)
    for mo in ["Ingenuo del día", "Ingenuo semanal"] + MODELOS:
        r = med.loc[(p, mo)]
        fila = [mo, n(r["RMSE"], 3), n(r["MAE"], 3), n(r["MAPE"])]
        if mo in MODELOS:
            c = crit.loc[(p, mo)]
            fila += [n(c.loc["h = 3 a 9", "mejora"]), pv(c.loc["h = 3 a 9", "p"])]
            fila += [n(c.loc[b, "mejora"]) for b in ("h = 3", "h = 3 a 7", "h = 8 a 9")]
        else:
            fila += ["—"] * 5
        filas.append(fila)
TABLA_PRUEBA = tabla(filas, [3.0, 1.4, 1.4, 1.6, 1.7, 1.6, 1.4, 1.6, 1.7])

filas = [["Modelo", "2023", "2024", "2025", "2026"]]
for mo in MODELOS:
    filas.append([mo] + [f"{n(anio.loc[(a, mo), 'mejora'])} ({pv(anio.loc[(a, mo), 'p'])})"
                         for a in ("2023", "2024", "2025", "2026")])
TABLA_ANIOS = tabla(filas, [3.6, 3.0, 3.0, 3.0, 3.0])

filas = [["Pronóstico", "Ahorro (COP/kWh)", "Intervalo de 95%", "Ahorro (% del precio)", "Parte del oráculo (%)"]]
for p, nombre in [("2023-2025", "Prueba 2023-2025"), ("2026", "Prueba 2026")]:
    filas.append([f"*{nombre}*"] + [""] * 4)
    for s in ["Oráculo", "LSTM", "XGBoost", "SARIMAX", "Ingenuo semanal"]:
        r = dec.loc[(p, s)]
        filas.append([s, n(r["ahorro"]), f"{n(r['inf'])} a {n(r['sup'])}", n(r["ahorro %"]),
                      "100" if s == "Oráculo" else n(r["del oraculo %"], 0)])
TABLA_DECISION = tabla(filas, [3.4, 3.0, 3.4, 3.0, 2.8])

# ----------------------------------------------------------------------------- ecuación 34: el ahorro
P_BAR = lambda i: sub(barra(m("P")), i)
H_T = sub(acento(m("h")), m("t"))
EC34 = (sub(m("A"), m("t")) + m("=") + frac(m("1"), m("7")) + suma(m("h=3"), m("9"), P_BAR(m("t+h")))
        + m("−") + P_BAR(m("t+") + H_T))

# ----------------------------------------------------------------------------- 4.1
P41 = [
    "Esta sección compara los tres modelos con los dos ingenuos de la sección 2.4 en las dos pruebas, 2023-2025 y "
    "2026 hasta el 6 de octubre. Cada modelo se evaluó una sola vez, con su configuración fija y reentrenado cada mes, "
    "en las mismas 228.984 filas (sección 3.3). La tabla 14 resume la semana completa, *h* = 3 a 9, con las medidas de "
    "la sección 2.4 y el criterio de la sección 3.3.",
]
NOTA_PRUEBA = (
    "Nota: RMSE y MAE del error en logaritmo (ecuaciones 13 y 14) y MAPE con los precios en pesos (ecuación 15), en "
    "*h* = 3 a 9. La mejora es la reducción del RMSE frente al ingenuo del día (ecuación 18), que fue el mejor de los "
    "dos ingenuos en todos los bloques, y *p* es el valor de la prueba de Diebold-Mariano contra ese ingenuo en la "
    "semana completa. En los bloques *h* = 3, 3 a 7 y 8 a 9, todas las pruebas dan *p* < 0,05. " + FUENTE_XM)
P41b = [
    "Los tres modelos cumplen el criterio en las dos pruebas y en los cuatro bloques de horizontes: reducen el RMSE en "
    "logaritmo más de 5% frente al mejor ingenuo, que en todos los casos fue el del día, y la prueba de Diebold-Mariano "
    "da *p* < 0,05. La LSTM es la que más lo reduce en la semana completa, 14,9% en 2023-2025 y 19,7% en 2026; le "
    "siguen XGBoost, con 11,6% y 10,0%, y SARIMAX, con 6,4% y 5,6%. El orden es el mismo con el MAE y con el MAPE. El "
    "ingenuo semanal tuvo un RMSE 10,4% mayor que el del día en 2023-2025 y 12,7% mayor en 2026: repetir la semana "
    "anterior respeta el ciclo semanal, pero usa un precio más viejo.",

    "La ventaja cambia con el horizonte (figura 16). La LSTM y XGBoost ganan más en los primeros días de la semana: en "
    "2023-2025, la LSTM reduce el RMSE 24,5% en *h* = 3 y XGBoost 17,9%, y en *h* = 9, 10,2% y 10,8%. SARIMAX mejora "
    "casi lo mismo en todos los horizontes, entre 4,7% y 7,7% en 2023-2025 y entre 4,2% y 6,5% en 2026. En 2026 la LSTM "
    "mantiene su ventaja hasta el final de la semana: 16,6% en *h* = 9, frente a 6,9% de XGBoost. En *h* = 7 los dos "
    "ingenuos pronostican lo mismo, porque los dos repiten el día *t*; desde *h* = 8 el semanal repite el mismo día de "
    "la semana de dos semanas antes, y su error salta.",
]
LEYENDA_F16 = ("RMSE en logaritmo de los tres modelos y de los dos ingenuos en cada horizonte, en las dos pruebas. "
               + FUENTE_XM)
P41c = [
    "Por hora del día, la LSTM tiene el menor RMSE en 136 de las 168 combinaciones de horizonte y hora de 2023-2025, y "
    "en 166 de las de 2026. XGBoost gana en 29 de 2023-2025, sobre todo en el pico de la noche, de las 19 a las 21 "
    "horas, entre *h* = 3 y 7, y en buena parte de *h* = 9.",

    "Por años el resultado es menos claro (tabla 15). En 2023 la LSTM redujo el error 21,6% y XGBoost 12,9%, mientras "
    "SARIMAX no llegó al 5%. En 2024, el año en que el precio llegó a su máximo de la muestra (sección 1.1), XGBoost y "
    "la LSTM mejoraron 7,6% y 9,7%, pero sin diferencia significativa, y solo SARIMAX cumplió el criterio, con 6,1%. "
    "En 2025 cumplieron los tres, y el de mayor mejora fue XGBoost, con 15,3%.",
]
NOTA_ANIOS = ("Nota: mejora en porcentaje y, entre paréntesis, el valor *p* de Diebold-Mariano. El ingenuo del día fue "
              "el mejor de los dos en todos los años, y el año es el del día de origen del pronóstico. " + FUENTE_XM)
P41d = [
    "Que un modelo tenga menor RMSE que otro no basta para decir que es mejor. Con la prueba de Diebold-Mariano entre "
    "cada par de modelos, con la misma varianza de la sección 3.3, la LSTM tiene menos error que SARIMAX en las dos "
    "pruebas (*p* = 0,007 y *p* = 0,011), y XGBoost menos que SARIMAX en 2023-2025 (*p* = 0,011), pero no en 2026 "
    "(*p* = 0,062). Entre la LSTM y XGBoost la diferencia no es significativa en 2023-2025 (*p* = 0,107) y sí lo es en "
    "2026 (*p* = 0,033). Por años, los tres pares solo se distinguen en 2023; en 2024 y 2025 ninguna diferencia es "
    "significativa, y en 2025 XGBoost tuvo un RMSE algo menor que la LSTM.",

    "La diferencia entre los modelos está sobre todo en el nivel del día. Como en la sección 3.2, el error de cada día "
    "pronosticado se separa en el error del promedio de sus 24 horas, el nivel, y el de cada hora frente a ese "
    "promedio, la forma; el cuadrado del RMSE es la suma de los cuadrados de las dos partes. En 2023-2025, el ingenuo "
    "del día tiene un error de nivel de 0,415 y de forma de 0,282. La LSTM bajó el nivel a 0,347, XGBoost a 0,385 y "
    "SARIMAX a 0,402. En la forma, en cambio, el mejor fue XGBoost, con 0,221, frente a 0,243 de SARIMAX y 0,249 de la "
    "LSTM. En 2026 se repite el mismo patrón.",

    "Esto se relaciona con la información que recibe cada modelo (secciones 1.3 y 3.6). La LSTM recibe el despacho "
    "programado del día *R*, que se publica antes que el precio y fue el bloque que más aportó en su selección "
    "(tabla 10), y es en el nivel del día donde le gana a XGBoost. Por eso la ventaja de la LSTM sobre XGBoost no se "
    "puede atribuir solo a la red: buena parte viene de usar información más reciente. XGBoost, cuyas columnas más "
    "importantes son del propio precio (sección 3.5), sigue siendo el que mejor pronostica la forma del día.",

    "Aun así, el nivel sigue siendo la mayor parte del error: 66% del error cuadrático de la LSTM en 2023-2025. Un "
    "ejercicio de diagnóstico con XGBoost en la validación de 2020-2022 (diagnosticos/oraculo.py) muestra qué "
    "información falta. Si el modelo recibiera los valores futuros reales de la demanda y de la hidrología, su mejora "
    "en *h* = 7 pasaría de 8,3% a 11,1%; si recibiera las ofertas futuras de los generadores, pasaría a 39,5%. Ese "
    "ejercicio usa datos que nadie tiene al pronosticar, así que es un techo y no una meta, pero muestra que lo que más "
    "mueve el precio a una semana es cómo ofertan los generadores, y eso se publica unos diez días tarde (sección 1.3).",

    "En pesos las ventajas son menores. Frente al ingenuo del día, el RMSE en COP/kWh baja 7,1% con la LSTM, 5,8% con "
    "SARIMAX y 3,7% con XGBoost en 2023-2025, y 8,8%, 6,4% y 6,8% en 2026. Hay dos razones. En pesos pesan más los "
    "errores de los meses caros. Y los tres modelos pronostican el logaritmo: al pasar a pesos con la ecuación (22), "
    "el pronóstico queda cerca de la mediana del precio y no de su media (Duan, 1983). Por eso los tres quedan, en "
    "promedio, por debajo del precio real, entre 15 COP/kWh (SARIMAX) y 46 COP/kWh (XGBoost) en 2023-2025, mientras "
    "el ingenuo del día casi no tiene sesgo.",

    "Por último, con los precios conocidos hasta el 6 de octubre de 2026, los tres modelos pronosticaron la semana del "
    "9 al 15 de octubre antes de que XM publicara esos precios. En esa semana el orden fue otro: XGBoost tuvo el menor "
    "error, con un MAPE de 15,9%, seguido de SARIMAX, con 17,9%, y del ingenuo del día, con 18,7%; la LSTM tuvo 23,2%. "
    "Una sola semana no cambia el resultado de las pruebas, pero muestra que la ventaja promedio no se cumple todas "
    "las semanas.",
]

S41 = (bloque(P41)
       + leyenda("Tabla", "Resultados de las pruebas en la semana completa y mejora por bloque de horizontes.",
                 ppr=ANTES_TABLA)
       + TABLA_PRUEBA + fuente(NOTA_PRUEBA)
       + bloque(P41b)
       + figura(FIG / "f27_error_por_horizonte.png", "rIdFig27", 2027, 15.5, LEYENDA_F16)
       + bloque(P41c)
       + leyenda("Tabla", "Mejora del RMSE en logaritmo frente al ingenuo del día por año, *h* = 3 a 9.",
                 ppr=ANTES_TABLA)
       + TABLA_ANIOS + fuente(NOTA_ANIOS)
       + bloque(P41d))

# ----------------------------------------------------------------------------- 4.2
P42 = [
    "Un menor error no siempre lleva a mejores decisiones (sección 2.4). Para medir cuánto vale cada pronóstico se usa "
    "una decisión sencilla: un consumidor que compra su energía a precio de bolsa puede mover un bloque de consumo de "
    "24 horas, como un proceso que gasta mucha energía, a cualquier día de la semana siguiente, y lo programa el día "
    "con el menor precio pronosticado (decisión del autor). Cada día *t* elige, entre *t* + 3 y *t* + 9, el día "
    "*t* + *ĥ*_{t} con el menor promedio de los 24 precios pronosticados, y el ahorro frente a consumir un día "
    "cualquiera de esa semana es",
]
P42b = [
    "donde *P̄*_{t+h} es el precio real promedio del día *t* + *h*. El ahorro de cada pronóstico se compara con el de "
    "un oráculo que conoce los precios reales y elige siempre el día más barato, que es el máximo posible. El ingenuo "
    "del día no entra en la comparación: pronostica el mismo precio para los siete días, así que no sirve para "
    "elegir. El intervalo de 95% del ahorro promedio se calculó con un bootstrap de bloques móviles de 28 días de "
    "origen (Künsch, 1989), porque las semanas de días de origen seguidos se traslapan; el tamaño del bloque es "
    "decisión del autor.",
]
NOTA_DECISION = ("Nota: ahorro promedio de la ecuación (34), en COP/kWh y como porcentaje del precio promedio de la "
                 "semana, que fue 492 COP/kWh en 2023-2025 y 486 COP/kWh en 2026, con 1.087 y 270 semanas. "
                 + FUENTE_XM)
P42c = [
    "La LSTM es la que más ahorra en las dos pruebas: 42,6 COP/kWh en 2023-2025 y 50,8 COP/kWh en 2026, 8,7% y 10,4% "
    "del precio promedio de la semana (tabla 16). Es más del doble de lo que ahorra el ingenuo semanal, 19,4 y "
    "22,1 COP/kWh, y equivale a 42% y 61% del ahorro del oráculo. Para una carga de 1 MW durante las 24 horas del día "
    "elegido, el ahorro de la LSTM en 2023-2025 equivale a cerca de un millón de pesos por semana.",

    "El orden de los modelos no es el mismo que el de su error. En 2023-2025, SARIMAX ahorró más que XGBoost, 39,8 "
    "frente a 36,2 COP/kWh, aunque su RMSE fue mayor: para esta decisión no importa acertar el precio de cada hora, "
    "sino ordenar bien los días de la semana. Los intervalos de los tres modelos se cruzan, así que entre ellos no hay "
    "diferencias claras; con el ingenuo semanal sí la hay en 2023-2025, cuando su intervalo queda por debajo del de la "
    "LSTM.",

    "El ejercicio supone que el consumidor paga el precio de bolsa sin contratos, que puede mover el bloque sin costo "
    "y que su consumo no cambia el precio. Aun así, muestra que la LSTM, el modelo con menor error, también es el que "
    "más ahorra.",
]

S42 = (bloque(P42) + ecuacion(EC34, 34) + bloque(P42b)
       + leyenda("Tabla", "Ahorro de elegir el día más barato de la semana con cada pronóstico.", ppr=ANTES_TABLA)
       + TABLA_DECISION + fuente(NOTA_DECISION)
       + bloque(P42c))

REFS = [
    "Duan, N. (1983). Smearing estimate: A nonparametric retransformation method. *Journal of the American "
    "Statistical Association, 78*(383), 605-610. https://doi.org/10.1080/01621459.1983.10478017",
    "Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *The Annals of "
    "Statistics, 17*(3), 1217-1241. https://doi.org/10.1214/aos/1176347265",
]


# ----------------------------------------------------------------------------- escritura
def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


def llenar(d, titulo, xml):
    """Cambia el párrafo vacío que sigue al título por xml. Usa los bloques de primer nivel del cuerpo."""
    B = d.bloques()
    T = [texto(d.doc[s:e]) for s, e in B]
    i = [k for k, t in enumerate(T) if t == titulo and "Ttulo2" in d.doc[B[k][0]:B[k][1]]]
    assert len(i) == 1, (titulo, i)
    s, e = B[i[0] + 1]
    vacio = d.doc[s:e]
    assert vacio.startswith("<w:p") and not T[i[0] + 1].strip() and "w:drawing" not in vacio, \
        f"la sección {titulo!r} ya tiene contenido"
    d.doc = d.doc[:s] + xml + d.doc[e:]


d = Docx(ENTRADA)
assert 'name="Figura 2027"' not in d.doc and "(34)" not in texto(d.doc)
d.agregar_imagen(FIG / "f27_error_por_horizonte.png", "rIdFig27")
llenar(d, "4.2 Valor para la toma de decisiones", S42)
llenar(d, "4.1 Desempeño frente a los ingenuos", S41)
d.referencias(REFS)
d.renumerar()

# comprobaciones: 16 figuras y 16 tablas numeradas en el cuerpo, la ecuación 34 y las remisiones dentro de rango
assert d.doc.count("SEQ Figura ") == 16 and d.doc.count("SEQ Tabla ") == 16
todo = texto(d.doc)
for tipo, maximo in (("figura", 16), ("tabla", 16)):
    for x in re.findall(rf"\b{tipo}s? (\d+)", todo, re.I):
        assert int(x) <= maximo, (tipo, x)
d.guardar(SALIDA)
print("ok", SALIDA)
