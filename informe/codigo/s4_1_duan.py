"""Sección 4.1: prueba de robustez con la corrección de Duan (1983) del sesgo en pesos, pedida por Andrés el 19 de
noviembre de 2026. Va como un párrafo corto después del que explica por qué las ventajas son menores en pesos. La
línea de trabajo futuro de la 5.2 decía que esa corrección podría quitar buena parte del sesgo; como ya se probó, ahora
dice lo que pasó y propone un factor que dependa de la variabilidad reciente del precio.
Las cifras salen de datos_resultados_duan.csv (fig_duan.py) y datos_resultados_por_anio.csv; cada una se comprueba
antes de escribir.
Uso: python s4_1_duan.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, par

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
D = pd.read_csv(FIG / "datos_resultados_duan.csv").set_index(["periodo", "pronostico", "variante"])
ANIO = pd.read_csv(FIG / "datos_resultados_por_anio.csv", dtype={"año": str}).set_index(["año", "modelo"])
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]
P = "2023-2025"


def x(mo, var, col):
    return float(D.loc[(P, mo, var), col])


def num(v, dec=1):
    s = f"{abs(v):.{dec}f}".replace(".", ",")
    return ("−" if v < 0 and float(s.replace(",", ".")) > 0 else "") + s


# lo que dice el texto, comprobado contra los datos
assert num(x("SARIMAX", "sin corregir", "sesgo pesos")) == "−15,3"
assert num(x("SARIMAX", "factor fijo de validacion", "sesgo pesos")) == "7,0"
assert num(x("SARIMAX", "sin corregir", "RMSE pesos")) == "242,1"
assert num(x("SARIMAX", "factor fijo de validacion", "RMSE pesos")) == "245,4"
mens = {mo: x(mo, "factor mensual", "sesgo pesos") for mo in MODELOS}
assert all(v > 0 for v in mens.values()) and (round(min(mens.values())), round(max(mens.values()))) == (17, 29)
assert all(x(mo, "factor mensual", "RMSE pesos") > x(mo, "sin corregir", "RMSE pesos") for mo in MODELOS)
assert num(x("LSTM", "sin corregir", "RMSE pesos")) == "238,9" and num(x("LSTM", "factor mensual", "RMSE pesos")) == "251,9"
for mo in MODELOS:
    assert min(ANIO.loc[("2023", mo), "RMSE"], ANIO.loc[("2024", mo), "RMSE"]) > ANIO.loc[("2025", mo), "RMSE"]

ROBUSTEZ = (
    "Como prueba de robustez, se intentó corregir ese sesgo con el estimador de Duan (1983), que multiplica el "
    "pronóstico en pesos de cada horizonte por el promedio de la exponencial de los errores en logaritmo ya conocidos "
    "al pronosticar. Con el factor fijo de la validación de SARIMAX, el único modelo con esos errores guardados, su "
    f"sesgo en 2023-2025 pasó de {num(x('SARIMAX', 'sin corregir', 'sesgo pesos'))} a "
    f"{num(x('SARIMAX', 'factor fijo de validacion', 'sesgo pesos'))} COP/kWh, pero su RMSE en pesos subió de "
    f"{num(x('SARIMAX', 'sin corregir', 'RMSE pesos'))} a {num(x('SARIMAX', 'factor fijo de validacion', 'RMSE pesos'))}. "
    "Con un factor recalculado cada mes con todos los errores ya conocidos, en 2023-2025 los tres modelos pasan a "
    f"sobreestimar el precio, entre {round(min(mens.values()))} y {round(max(mens.values()))} COP/kWh, y su RMSE en "
    f"pesos sube; el de la LSTM, de {num(x('LSTM', 'sin corregir', 'RMSE pesos'))} a "
    f"{num(x('LSTM', 'factor mensual', 'RMSE pesos'))}. El factor depende del tamaño de los errores pasados, que "
    "fueron mayores en 2023 y 2024 que en 2025 (tabla 16), así que corrige de más cuando el precio se calma. Por eso "
    "los resultados en pesos usan el pronóstico sin corregir. Este ejercicio se hizo después de ver la prueba y es "
    "solo un complemento.")

VIEJO_52 = ("Multiplicarlo por el promedio de la exponencial de los errores de la validación, el estimador de Duan "
            "(1983), podría corregir buena parte de ese sesgo sin cambiar los modelos.")
NUEVO_52 = ("El estimador de Duan (1983), con un factor fijo o recalculado cada mes, quitó el sesgo pero corrigió de "
            "más y no redujo el error en pesos (sección 4.1). Un factor que dependa de la variabilidad reciente del "
            "precio podría corregirlo mejor sin cambiar los modelos.")


def texto(xml):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", xml))


d = Docx(ENTRADA)
assert "Como prueba de robustez" not in texto(d.doc)
B = d.bloques()
k = [i for i, (s, e) in enumerate(B) if texto(d.doc[s:e]).startswith("Hay dos razones. En pesos, los días caros")]
assert len(k) == 1
fin = B[k[0]][1]
d.doc = d.doc[:fin] + par(ROBUSTEZ) + d.doc[fin:]
d.cambiar_texto(VIEJO_52, NUEVO_52)
todo = texto(d.doc)
assert todo.count("Como prueba de robustez") == 1 and "corrigió de más y no redujo el error en pesos" in todo
assert d.doc.count("SEQ Tabla ") == 20 and d.doc.count("SEQ Figura ") == 17
d.guardar(SALIDA)
print("ok", SALIDA)
