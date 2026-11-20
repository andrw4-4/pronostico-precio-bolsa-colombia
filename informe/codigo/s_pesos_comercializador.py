"""El precio en pesos, por qué se pronostica el cambio en logaritmo, el error en pesos en el cuerpo y la utilidad
para un comercializador. Pedido de Andrés del 19 de noviembre de 2026:
1. Sección 1.1: figura nueva con el precio en COP/kWh, sin logaritmo (fig_precio_pesos.py). Pasa a ser la figura 3
   y las siguientes se corren un número. La 1.1 y la 1.3 dicen que el error se mide también en pesos y que el valor
   del pronóstico se mide con dos casos. La 1.3 citaba el criterio en la sección 3.2; está en la 3.3.
2. Sección 3.3: por qué la respuesta es el cambio en logaritmo y no el precio, su logaritmo ni el cambio porcentual
   simple, con las cifras de datos_respuesta.csv (2015-2022) y Tsay (2010) para la suma de los cambios.
3. Sección 4.1: la tabla del error en pesos pasa del anexo C al cuerpo (tabla 17, después de la de años, con la
   mejora en logaritmo al lado para comparar), y el anexo C se quita porque su texto queda en la 4.1.
4. Sección 4.2: un segundo caso, el comercializador que estima el costo de la semana (tabla 19), con las cifras de
   datos_resultados_comercializador.csv (fig_comercializador.py).
5. Resumen, 2.4, 5.1 y 5.2: una frase cada uno sobre lo nuevo.
Nada se entrena ni se repite ninguna prueba: todo sale de los pronósticos guardados. Cada cifra del texto se
comprueba contra los CSV antes de escribir.
Uso: python s_pesos_comercializador.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, figura, leyenda, par, par_referencia, runs, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]
INGENUOS = ["Ingenuo del día", "Ingenuo semanal"]
NBSP = chr(0xA0)                # espacio que no se corta, para que "p = 0,508" no quede partido entre dos líneas
ANTES_TABLA = '<w:keepNext/><w:spacing w:before="240"/>'
FUENTE_XM = "Fuente: elaboración propia con datos de XM (2026)."


def num(x, dec=1):
    s = f"{abs(x):.{dec}f}".replace(".", ",")
    return ("−" if x < 0 and float(s.replace(",", ".")) > 0 else "") + s


def pval(p):
    return "< 0,001" if p < 0.001 else num(p, 3)


def miles(x):
    return f"{x:,.0f}".replace(",", ".")


def p_igual(p):
    return f"*p*{NBSP}={NBSP}{pval(p)}" if p >= 0.001 else f"*p*{NBSP}<{NBSP}0,001"


# ----------------------------------------------------------------------------- datos
RESP = pd.read_csv(FIG / "datos_respuesta.csv").set_index("medida")["valor"]
PESOS = pd.read_csv(FIG / "datos_resultados_pesos.csv", dtype={"caso": str}).set_index(["caso", "pronostico"])
PARES = pd.read_csv(FIG / "datos_resultados_pesos_pares.csv", dtype={"caso": str})
CRIT = pd.read_csv(FIG / "datos_resultados_criterio.csv").query("bloque == 'h = 3 a 9'").set_index(["periodo", "modelo"])
COM = pd.read_csv(FIG / "datos_resultados_comercializador.csv", dtype={"caso": str}).set_index(["caso", "pronostico"])


def pp(caso, mo):
    return float(PESOS.loc[(caso, mo), "p"])


def c(caso, mo, col):
    return float(COM.loc[(caso, mo), col])


# lo que dicen los textos, comprobado contra los datos
assert round(RESP["minimo dia"]) == 61 and round(RESP["maximo dia"]) == 2499
assert round(RESP["promedio 2015-2021"]) == 219 and round(RESP["promedio 2023-2025"]) == 492
assert num(RESP["simple h3 min"], 0) == "−88" and num(RESP["simple h3 max"], 0) == "623"
assert num(RESP["log h3 min"], 2) == "−2,11" and num(RESP["log h3 max"], 2) == "1,98"
assert num(RESP["simple h3 asimetria"], 2) == "2,74" and num(RESP["log h3 asimetria"], 2) == "−0,11"
sig = {k: [mo for mo in MODELOS if pp(k, mo) < 0.05] for k in ["2023-2025", "2026", "2023", "2024", "2025"]}
assert sig["2023-2025"] == ["SARIMAX"] and sig["2026"] == MODELOS
assert sig["2023"] == [] and sig["2024"] == [] and sig["2025"] == MODELOS
assert max(pp("2025", mo) for mo in MODELOS) < 0.01
assert (PARES[PARES["caso"].isin(["2023-2025", "2026"])]["p"] > 0.05).all()
mej = {(k, mo): num(PESOS.loc[(k, mo), "mejora"]) for k in ["2023-2025", "2026"] for mo in MODELOS}
assert [mej[("2023-2025", mo)] for mo in ["LSTM", "SARIMAX", "XGBoost"]] == ["7,1", "5,8", "3,7"]
assert [mej[("2026", mo)] for mo in ["LSTM", "SARIMAX", "XGBoost"]] == ["8,8", "6,4", "6,8"]
assert round(-PESOS.loc[("2023-2025", "SARIMAX"), "sesgo pesos"]) == 15
assert round(-PESOS.loc[("2023-2025", "XGBoost"), "sesgo pesos"]) == 46
assert abs(PESOS.loc[("2023-2025", "Ingenuo del día"), "sesgo pesos"]) < 2
# comercializador
assert [round(c("2023-2025", mo, "MAE %")) for mo in ["LSTM", "SARIMAX", "XGBoost", "Ingenuo del día"]] == [22, 25, 25, 24]
assert all(c("2023-2025", mo, "p") > 0.05 for mo in MODELOS)
assert max(MODELOS, key=lambda mo: c("2023-2025", mo, "mejora")) == "LSTM"
assert num(c("2023-2025", "LSTM", "mejora")) == "9,8" and pval(c("2023-2025", "LSTM", "p")) == "0,381"
assert c("2023-2025", "XGBoost", "mejora") < 0
assert num(c("2026", "LSTM", "mejora")) == "16,1" and pval(c("2026", "LSTM", "p")) == "0,057"
assert round(c("2023-2025", "LSTM", "MAE") * 168_000 / 1e6) == 18
assert round(c("2023-2025", "Ingenuo del día", "MAE") * 168_000 / 1e6) == 20
assert round(-c("2023-2025", "SARIMAX", "sesgo")) == 15 and round(-c("2023-2025", "XGBoost", "sesgo")) == 47
assert all(c("2023-2025", mo, "sesgo") < 0 for mo in MODELOS)
assert round(c("2023-2025", "LSTM", "semanas que se mueven")) == 72
assert [round(c("2023-2025", mo, "acierta direccion")) for mo in ["LSTM", "XGBoost", "SARIMAX", "Ingenuo semanal"]] \
    == [74, 65, 60, 54]
assert (round(c("2023-2025", "LSTM", "direccion inf")), round(c("2023-2025", "LSTM", "direccion sup"))) == (68, 79)
assert (round(c("2023-2025", "Ingenuo semanal", "direccion inf")),
        round(c("2023-2025", "Ingenuo semanal", "direccion sup"))) == (48, 61)
assert c("2023-2025", "LSTM", "direccion inf") > c("2023-2025", "Ingenuo semanal", "direccion sup")
assert round(c("2026", "LSTM", "acierta direccion")) == 81
assert int(c("2023-2025", "LSTM", "semanas")) == 1087 and int(c("2026", "LSTM", "semanas")) == 270

# ----------------------------------------------------------------------------- textos nuevos
LEYENDA_F3 = ("Precio de bolsa promedio del día en COP/kWh, de 2015 a octubre de 2026. Las líneas rojas marcan el "
              "promedio de 2015-2021 y el de 2023-2025. Fuente: elaboración propia con datos de XM (2026).")

S33 = [
    "Se pronostica el cambio en logaritmo, y no el precio ni su logaritmo, por tres razones. Primera, el precio en "
    f"pesos cambia de escala: su promedio diario fue de {round(RESP['minimo dia'])} a "
    f"{miles(RESP['maximo dia'])} COP/kWh (figura 3), y con un error cuadrático en pesos los días de precios muy "
    "altos pesarían mucho más que los demás en el ajuste. El logaritmo estabiliza la varianza y reduce el peso de "
    "esos picos (Uniejewski et al., 2018). Segunda, el logaritmo corrige la escala, pero su nivel cambia durante "
    "meses y no es estacionario, mientras que su cambio diario sí lo es (sección 3.2). Al pronosticar el cambio "
    "frente al día *t*, cada modelo parte del último precio conocido y solo tiene que pronosticar cuánto se aleja de "
    "él; el ingenuo del día de la ecuación (15) equivale a pronosticar un cambio de cero. Tercera, los tres modelos "
    "pronostican la misma cantidad, lo que permite compararlos directamente.",

    "Se usa el cambio en logaritmo y no el cambio porcentual simple, *P*(*t* + *h*, *H*)/*P*(*t*, *H*) − 1, porque "
    "el primero es simétrico: duplicar el precio es un cambio de 0,69 y reducirlo a la mitad, de −0,69, mientras que "
    "en porcentaje son +100% y −50%. Con los datos de 2015 a 2022, el cambio de cada hora a tres días fue de "
    f"{num(RESP['simple h3 min'], 0)}% a +{num(RESP['simple h3 max'], 0)}% en porcentaje, con una asimetría de "
    f"{num(RESP['simple h3 asimetria'], 2)}, y de {num(RESP['log h3 min'], 2)} a {num(RESP['log h3 max'], 2)} en "
    f"logaritmo, con una asimetría de {num(RESP['log h3 asimetria'], 2)}. Además, los cambios en logaritmo se suman: "
    "el cambio de *t* a *t* + *h* es la suma de los cambios de cada día (Tsay, 2010), y por eso la diferencia de "
    "orden uno de SARIMAX lleva a la misma cantidad que pronostican XGBoost y la LSTM. Por último, el pronóstico en "
    "pesos de la ecuación (21) es siempre positivo. El costo de esta elección es que, al volver a pesos, el "
    "pronóstico queda cerca de la mediana del precio y no de su media (Duan, 1983); por eso la sección 4.1 mide el "
    "error también en pesos.",
]

S41_A = (
    "El criterio de la sección 3.3 mide el error en logaritmo, pero quien compra o vende energía paga en pesos. Por "
    "eso la tabla 17 repite la comparación con el error en COP/kWh, la diferencia entre el precio pronosticado con la "
    "ecuación (21) y el real. No es parte del criterio, que se fijó antes de abrir la prueba, pero muestra sus "
    "límites. En pesos las ventajas son menores: frente al ingenuo del día, el RMSE baja "
    f"{mej[('2023-2025', 'LSTM')]}% con la LSTM, {mej[('2023-2025', 'SARIMAX')]}% con SARIMAX y "
    f"{mej[('2023-2025', 'XGBoost')]}% con XGBoost en 2023-2025, y {mej[('2026', 'LSTM')]}%, "
    f"{mej[('2026', 'SARIMAX')]}% y {mej[('2026', 'XGBoost')]}% en 2026. Con la prueba de Diebold-Mariano sobre el "
    "error en pesos, en 2023-2025 solo la mejora de SARIMAX es significativa "
    f"({p_igual(pp('2023-2025', 'SARIMAX'))}), no las de XGBoost ni la LSTM ({p_igual(pp('2023-2025', 'XGBoost'))} "
    f"y {p_igual(pp('2023-2025', 'LSTM'))}); en 2026 lo son las tres. Por años, ninguna mejora en pesos es "
    f"significativa en 2023 ni en 2024, y las tres lo son en 2025 (*p*{NBSP}<{NBSP}0,01). Entre modelos, ninguna "
    "diferencia en pesos es significativa en las dos pruebas.")

S41_B = (
    "Hay dos razones. En pesos, los días caros pesan mucho más, porque el error se eleva al cuadrado en COP/kWh: un "
    "error de 10% es de 20 COP/kWh con un precio de 200 y de 200 COP/kWh con uno de 2.000 (figura 3). Así, la "
    "diferencia de pérdidas entre dos pronósticos varía más de un día a otro y la prueba distingue menos. Y los tres "
    "modelos pronostican el logaritmo: al pasar a pesos con la ecuación (21), el pronóstico queda cerca de la mediana "
    "del precio y no de su media (Duan, 1983). Por eso los tres quedan, en promedio, por debajo del precio real, "
    f"entre {round(-PESOS.loc[('2023-2025', 'SARIMAX'), 'sesgo pesos'])} COP/kWh (SARIMAX) y "
    f"{round(-PESOS.loc[('2023-2025', 'XGBoost'), 'sesgo pesos'])} COP/kWh (XGBoost) en 2023-2025, mientras el "
    "ingenuo del día casi no tiene sesgo. Para quien usa el pronóstico en pesos, entonces, la ventaja de los modelos "
    "es menor que la de la tabla 15 y viene con un sesgo hacia abajo; la sección 4.2 muestra lo que eso significa "
    "para un comercializador.")

NOTA_PESOS = ("Nota: RMSE, MAE y sesgo del error en pesos, en COP/kWh, en *h* = 3 a 9. El sesgo es el promedio del "
              "precio pronosticado menos el real; es negativo cuando el pronóstico queda por debajo. La mejora es la "
              "reducción del RMSE en pesos frente al ingenuo del día, y *p* es el valor de la prueba de "
              "Diebold-Mariano con el error cuadrático en pesos, con la misma varianza de la sección 3.3. La última "
              "columna repite, para comparar, la mejora en logaritmo de la tabla 15. " + FUENTE_XM)

S42_A = (
    "El segundo caso es el de un comercializador, que compra en bolsa la energía que sus contratos no cubren "
    "(sección 1.1) y necesita estimar cuánto le va a costar la semana siguiente. Si esa energía es la misma en las "
    "168 horas, un bloque plano, el costo de la semana depende solo de su precio promedio (decisión del autor). La "
    "tabla 19 compara, para cada día de origen *t*, el precio promedio de los días *t* + 3 a *t* + 9 pronosticado en "
    "pesos con la ecuación (21) con el real.")

S42_B = (
    "Para estimar ese costo, los modelos ayudan poco. En 2023-2025, el error absoluto medio del precio de la semana "
    f"fue de {round(c('2023-2025', 'LSTM', 'MAE %'))}% del precio promedio con la LSTM, "
    f"{round(c('2023-2025', 'SARIMAX', 'MAE %'))}% con SARIMAX y XGBoost y "
    f"{round(c('2023-2025', 'Ingenuo del día', 'MAE %'))}% con el ingenuo del día, y ninguna mejora del RMSE frente "
    f"al ingenuo fue significativa: la mayor fue la de la LSTM, {num(c('2023-2025', 'LSTM', 'mejora'))}% "
    f"({p_igual(c('2023-2025', 'LSTM', 'p'))}), y XGBoost no lo mejoró. En 2026 la LSTM lo redujo "
    f"{num(c('2026', 'LSTM', 'mejora'))}%, sin llegar a ser significativa ({p_igual(c('2026', 'LSTM', 'p'))}). Para "
    "un bloque de 1 MW, 168 MWh por semana, el error absoluto medio de la LSTM en 2023-2025 equivale a unos "
    f"{round(c('2023-2025', 'LSTM', 'MAE') * 168_000 / 1e6)} millones de pesos por semana, frente a "
    f"{round(c('2023-2025', 'Ingenuo del día', 'MAE') * 168_000 / 1e6)} millones con el ingenuo del día. Además, "
    "los tres modelos subestiman el costo: su precio promedio de la semana quedó, en promedio, entre "
    f"{round(-c('2023-2025', 'SARIMAX', 'sesgo'))} y {round(-c('2023-2025', 'XGBoost', 'sesgo'))} COP/kWh por "
    "debajo del real en 2023-2025, por el sesgo que describe la sección 4.1.")

S42_C = (
    f"Lo que sí aportan es la dirección. En {round(c('2023-2025', 'LSTM', 'semanas que se mueven'))}% de las semanas "
    "de 2023-2025, el precio promedio cambió más de 10% frente al del último día conocido, y el ingenuo del día no "
    "anticipa esos cambios, porque pronostica un cambio de cero. La LSTM acertó si el precio subía o bajaba en "
    f"{round(c('2023-2025', 'LSTM', 'acierta direccion'))}% de esas semanas (intervalo de 95%: "
    f"{round(c('2023-2025', 'LSTM', 'direccion inf'))}% a {round(c('2023-2025', 'LSTM', 'direccion sup'))}%), "
    f"XGBoost en {round(c('2023-2025', 'XGBoost', 'acierta direccion'))}% y SARIMAX en "
    f"{round(c('2023-2025', 'SARIMAX', 'acierta direccion'))}%, frente a "
    f"{round(c('2023-2025', 'Ingenuo semanal', 'acierta direccion'))}% del ingenuo semanal "
    f"({round(c('2023-2025', 'Ingenuo semanal', 'direccion inf'))}% a "
    f"{round(c('2023-2025', 'Ingenuo semanal', 'direccion sup'))}%); en 2026 la LSTM acertó en "
    f"{round(c('2026', 'LSTM', 'acierta direccion'))}%. El umbral de 10% es decisión del autor, y los intervalos "
    "salen del mismo bootstrap de bloques de 28 días. Para un comercializador, eso sirve de alerta antes de una "
    "semana cara o barata, aunque el monto del costo siga siendo incierto.")

NOTA_COM = ("Nota: error del precio promedio pronosticado de los días *t* + 3 a *t* + 9, en pesos con la ecuación "
            "(21), frente al real, en COP/kWh, para cada día de origen *t* con sus 168 precios: "
            f"{miles(c('2023-2025', 'LSTM', 'semanas'))} semanas en 2023-2025 y {int(c('2026', 'LSTM', 'semanas'))} "
            "en 2026. La mejora es la reducción del RMSE frente al ingenuo del día, y *p* es el valor de la prueba de "
            "Diebold-Mariano con el error cuadrático de cada semana, con la misma varianza de la sección 3.3. La "
            "dirección es el porcentaje de semanas en que el pronóstico acierta si el precio promedio sube o baja "
            "frente al del día *t*, entre las que cambian más de 10%; el ingenuo del día pronostica un cambio de "
            "cero. " + FUENTE_XM)

TSAY = "Tsay, R. S. (2010). *Analysis of financial time series* (3.ª ed.). Wiley."

CAMBIOS = [
    # 1.1
    ("a 2.499 COP/kWh, el 30 de septiembre de 2024.", "a 2.499 COP/kWh, el 30 de septiembre de 2024 (figura 3)."),
    ("con un criterio fijado antes de la prueba.",
     "con un criterio fijado antes de la prueba. Por la escala de la figura 3, los modelos no pronostican el precio en "
     "pesos sino su cambio en logaritmo frente al último precio conocido, y el error se mide en logaritmo y también "
     "en pesos (secciones 3.3 y 4.1)."),
    ("Además, traduce la mejora del pronóstico a una decisión concreta, elegir el día más barato de la semana, para "
     "medir cuánto vale en pesos.",
     "Además, traduce la mejora del pronóstico a dos casos concretos, elegir el día más barato de la semana para un "
     "consumidor y estimar el costo de la semana para un comercializador, para medir cuánto vale en pesos."),
    # 1.3
    ("Diebold y Mariano (1995) (sección 3.2).",
     "Diebold y Mariano (1995) (sección 3.3). El error también se mide en pesos, como complemento (sección 4.1)."),
    ("El valor del pronóstico se mide con una decisión sencilla, elegir el día más barato de la semana, y no con una "
     "estrategia de contratación o de operación de una planta.",
     "El valor del pronóstico se mide con dos casos sencillos, elegir el día más barato de la semana y estimar el "
     "costo de la semana para un comercializador, y no con una estrategia de contratación o de operación de una "
     "planta."),
    # 2.4
    ("Por eso la sección 4.2 evalúa los pronósticos también por su valor en una decisión concreta.",
     "Por eso la sección 4.2 evalúa los pronósticos también por su valor para un consumidor y para un "
     "comercializador."),
    # 4.2
    ("Para medir cuánto vale cada pronóstico se usa una decisión sencilla: un consumidor",
     "Para medir cuánto vale cada pronóstico se usan dos casos sencillos. El primero es una decisión: un consumidor"),
    # resumen
    ("Es más del doble de lo que ahorra el ingenuo semanal.",
     "Es más del doble de lo que ahorra el ingenuo semanal. En pesos, las mejoras son menores y en 2023-2025 solo la "
     "de SARIMAX es significativa. Para estimar el costo de la semana de un comercializador, ningún modelo mejora de "
     "forma significativa, aunque la LSTM acierta si el precio de la semana sube o baja en "
     f"{round(c('2023-2025', 'LSTM', 'acierta direccion'))}% de las semanas en que cambia más de 10%."),
    # 5.1
    ("conviene evaluar un pronóstico también con la decisión para la que se va a usar.",
     "conviene evaluar un pronóstico también con la decisión para la que se va a usar. Para un comercializador que "
     "estima el costo de la semana, en cambio, ninguna mejora fue significativa en 2023-2025, aunque la LSTM acertó "
     f"si el precio subía o bajaba en {round(c('2023-2025', 'LSTM', 'acierta direccion'))}% de las semanas en que "
     "cambió más de 10% (sección 4.2)."),
    # 5.2
    ("y los pronósticos quedan por debajo del precio real (sección 4.1 y anexo C).",
     "y los pronósticos quedan por debajo del precio real (sección 4.1); para el costo de la semana de un "
     "comercializador, ninguna mejora es significativa en 2023-2025 (sección 4.2)."),
    ("Y el ejercicio de decisión supone que el consumidor paga el precio de bolsa sin contratos, que mover su consumo "
     "no cuesta nada y que su consumo no cambia el precio (sección 4.2).",
     "Y los dos casos de la sección 4.2 son sencillos: el consumidor paga el precio de bolsa sin contratos, mover su "
     "consumo no cuesta nada y su consumo no cambia el precio, y el comercializador compra un bloque plano, sin "
     "contar el error en el pronóstico de su propia demanda."),
]


# ----------------------------------------------------------------------------- piezas
def fuente(texto):
    rpr = '<w:sz w:val="20"/>'
    texto = runs(texto).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace(
        "<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
    return ('<w:p><w:pPr><w:spacing w:before="60" w:after="240"/><w:ind w:firstLine="0"/></w:pPr>'
            f'{texto}</w:p>')


def filas_pesos():
    filas = [["Pronóstico", "RMSE", "MAE", "Sesgo", "Mejora (%)", "*p*", "Mejora en logaritmo (%)"]]
    for caso, titulo in [("2023-2025", "*Prueba 2023-2025*"), ("2026", "*Prueba 2026*")]:
        filas.append([titulo] + [""] * 6)
        for mo in INGENUOS + MODELOS:
            r = PESOS.loc[(caso, mo)]
            es = mo in MODELOS
            filas.append([mo, num(r["RMSE pesos"]), num(r["MAE pesos"]), num(r["sesgo pesos"]),
                          num(r["mejora"]) if es else "—", pval(r["p"]) if es else "—",
                          num(CRIT.loc[(caso, mo), "mejora"]) if es else "—"])
    return filas


def filas_com():
    filas = [["Pronóstico", "RMSE", "MAE", "Sesgo", "Mejora (%)", "*p*", "Dirección (%)"]]
    for caso, titulo in [("2023-2025", "*Prueba 2023-2025*"), ("2026", "*Prueba 2026*")]:
        filas.append([titulo] + [""] * 6)
        for mo in INGENUOS + MODELOS:
            es = mo in MODELOS
            filas.append([mo, num(c(caso, mo, "RMSE")), num(c(caso, mo, "MAE")), num(c(caso, mo, "sesgo")),
                          num(c(caso, mo, "mejora")) if es else "—", pval(c(caso, mo, "p")) if es else "—",
                          num(c(caso, mo, "acierta direccion")) if mo != "Ingenuo del día" else "—"])
    return filas


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


def correr(t, desde_fig=3, desde_tabla=17):
    """Corre un número las referencias en el texto a las figuras desde la 3 y a las tablas desde la 17."""
    t = re.sub(r"\bfigura (\d+)", lambda m: f"figura {int(m.group(1)) + (int(m.group(1)) >= desde_fig)}", t)
    return re.sub(r"\btabla (\d+)", lambda m: f"tabla {int(m.group(1)) + (int(m.group(1)) >= desde_tabla)}", t)


def bloque_que_empieza(d, inicio):
    B = d.bloques()
    k = [i for i, (s, e) in enumerate(B) if texto(d.doc[s:e]).startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return B[k[0]]


# ----------------------------------------------------------------------------- cambios
d = Docx(ENTRADA)
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
assert "Anexo C." in d.doc and "f28_precio_pesos" not in d.doc
assert not re.search(r"\b(figuras|tablas) \d", texto(d.doc)), "hay referencias en plural; correr() no las cubre"

# 1. las referencias a figuras y tablas, en cada texto de Word; luego se comprueba bloque por bloque que ninguna
#    quedó partida entre dos textos
antes = [texto(d.doc[s:e]) for s, e in d.bloques()]
d.doc = re.sub(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)", lambda m: m.group(1) + correr(m.group(2)) + m.group(3), d.doc)
despues = [texto(d.doc[s:e]) for s, e in d.bloques()]
assert len(antes) == len(despues) and all(correr(a) == b for a, b in zip(antes, despues))
d.cambiar_texto("dominan la serie (figura 2)", "dominan la serie (figura 3)")

# 2. se quita el anexo C: su título, dos párrafos, la leyenda de la tabla C1, la tabla y la nota
B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]
i = T.index("Anexo C. Resultados de la prueba en pesos")
assert T[i + 3].startswith("Tabla C1. ") and T[i + 5].startswith("Nota: RMSE, MAE y sesgo del error en pesos")
assert not any(t.strip() for t in T[i + 6:]), "hay texto después del anexo C"
d.doc = d.doc[:B[i][0]] + d.doc[B[i + 5][1]:]

# 3. textos cambiados (cada texto viejo está una vez y en un solo run)
for viejo, nuevo in CAMBIOS:
    d.cambiar_texto(viejo, nuevo.replace("*p* = ", f"*p*{NBSP}={NBSP}"))

# 4. figura nueva después del párrafo del rango de variación
PNG = FIG / "f28_precio_pesos.png"
d.agregar_imagen(PNG, "rIdFig28")
s, e = bloque_que_empieza(d, "El rango de variación es muy amplio")
d.doc = d.doc[:e] + figura(PNG, "rIdFig28", 2028, 15.5, LEYENDA_F3) + d.doc[e:]

# 5. sección 3.3: la justificación de la respuesta reemplaza al párrafo que la resumía
s, e = bloque_que_empieza(d, "Con esta respuesta, el pronóstico ingenuo del día")
d.doc = d.doc[:s] + "".join(par(t) for t in S33) + d.doc[e:]

# 6. sección 4.1: el párrafo de pesos, que va después de la tabla de años, se vuelve dos, con la tabla 17 entre ellos
s, e = bloque_que_empieza(d, "En pesos las ventajas son menores.")
d.doc = (d.doc[:s] + par(S41_A)
         + leyenda("Tabla", "Resultados de las pruebas con el error en pesos, *h* = 3 a 9.", ppr=ANTES_TABLA)
         + tabla(filas_pesos(), [3.3, 1.9, 1.9, 1.9, 2.0, 1.9, 2.6]) + fuente(NOTA_PESOS) + par(S41_B) + d.doc[e:])

# 7. sección 4.2: el caso del comercializador, al final
s, e = bloque_que_empieza(d, "El ejercicio supone que el consumidor paga el precio de bolsa")
d.doc = (d.doc[:e] + par(S42_A)
         + leyenda("Tabla", "Error del precio promedio de la semana pronosticado para un bloque plano.",
                   ppr=ANTES_TABLA)
         + tabla(filas_com(), [3.3, 1.9, 1.9, 1.9, 2.0, 1.9, 2.4]) + fuente(NOTA_COM)
         + par(S42_B) + par(S42_C) + d.doc[e:])

# 8. referencia nueva, en su lugar alfabético
s, e = bloque_que_empieza(d, "Uniejewski, B., Weron, R., y Ziel, F. (2018).")
d.doc = d.doc[:s] + par_referencia(TSAY) + d.doc[s:]

d.renumerar()
# el índice (estilos TDC) todavía nombra el anexo C; se rehace al actualizar el índice en Word
todo = "".join(texto(d.doc[s:e]) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e])
assert d.doc.count("SEQ Tabla ") == 19 and d.doc.count("SEQ Figura ") == 17
assert "Anexo C" not in todo and "anexo C" not in todo and "Tabla C1" not in todo
assert max(int(n) for n in re.findall(r"\bfigura (\d+)", todo)) == 17
assert max(int(n) for n in re.findall(r"\btabla (\d+)", todo)) == 19
for n in range(15, 20):
    assert f"tabla {n}" in todo, n
assert "(Tsay, 2010)" in todo and "Tsay, R. S. (2010)." in todo
d.guardar(SALIDA)
print("ok", SALIDA)
