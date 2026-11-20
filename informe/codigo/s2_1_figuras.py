"""Agrega a la sección 2.1 el esquema del mercado de corto plazo (adaptado de Guzmán Feria, 2024) y la figura del
precio con el cambio diario de su logaritmo. Las figuras salen de fig_marco_teorico.py.
Uso: python s2_1_figuras.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

from docx_final import Docx, figura

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
sin_formato = lambda t: re.sub(r"\*+", "", t)

DESPACHOS = (
    "Como se describió en la sección 1.1, cada día los generadores ofertan un precio para las 24 horas del día "
    "siguiente y declaran su disponibilidad hora por hora (CREG, 1995). Con esas ofertas, XM calcula tres despachos "
    "distintos. El despacho programado se hace antes del día de operación, tiene en cuenta las restricciones de la "
    "red y dice qué plantas deben generar en cada hora. El despacho real es lo que ocurre durante el día, con los "
    "ajustes que exige la operación. El despacho ideal se calcula después del día, sin restricciones de red: atiende "
    "la demanda real con las plantas en orden de mérito, y el precio de bolsa de cada hora es la oferta de la planta "
    "marginal de ese despacho (CREG, 1994). Las diferencias entre el despacho ideal y el real se liquidan aparte, "
    "como reconciliaciones, y no cambian el precio de bolsa.")

CONSECUENCIAS = (
    "Dos consecuencias importan para pronosticarlo. Primera, como el precio cambia de escala, de 61 a casi 2.500 "
    "COP/kWh en promedio diario, conviene modelar su logaritmo, que estabiliza la varianza y reduce el peso de los "
    "picos (Uniejewski et al., 2018).")
CONSECUENCIAS_RESTO = (
    " Segunda, el precio depende de las ofertas, que son decisiones de los "
    "generadores y se publican tarde (sección 1.1). Un modelo de pronóstico solo puede aproximarlas a partir de lo "
    "que sí se observa a tiempo: la hidrología, la demanda, el despacho programado y la historia del propio precio.")
FIGURA_4 = (
    " La figura 4 lo muestra: en pesos, los picos de 2015-2016 y 2023-2024 dominan la serie, mientras que el cambio "
    "diario del logaritmo oscila alrededor de cero en toda la muestra, aunque con más variabilidad desde 2023 (una "
    "desviación estándar de 0,19 en 2023-2025, frente a 0,13 en 2015-2019).")

d = Docx(ENTRADA)
assert "f12_mercado_corto_plazo" not in d.doc, "las figuras de la 2.1 ya están"
d.agregar_imagen(FIG / "f12_mercado_corto_plazo.png", "rIdFig12")
d.agregar_imagen(FIG / "f13_precio_y_cambio.png", "rIdFig13")

# los dos párrafos deben estar como los dejó s2_marco_teorico.py, para no pisar cambios hechos en Word
textos = [d.texto(p) for _, _, p in d.parrafos()]
assert sin_formato(DESPACHOS) in textos, "el párrafo de los despachos cambió en Word"
assert sin_formato(CONSECUENCIAS + CONSECUENCIAS_RESTO) in textos, "el párrafo de las consecuencias cambió en Word"

d.reemplazar_parrafo("Como se describió en la sección 1.1", DESPACHOS + " La figura 3 resume estas etapas.")
d.insertar_tras("Como se describió en la sección 1.1",
                figura(FIG / "f12_mercado_corto_plazo.png", "rIdFig12", 2012, 15,
                       "Esquema del mercado de energía de corto plazo. Fuente: adaptado de Guzmán Feria (2024)."))
d.reemplazar_parrafo("Dos consecuencias importan", CONSECUENCIAS + FIGURA_4 + CONSECUENCIAS_RESTO)
d.insertar_tras("Dos consecuencias importan",
                figura(FIG / "f13_precio_y_cambio.png", "rIdFig13", 2013, 15,
                       "Precio de bolsa promedio del día y cambio diario de su logaritmo, del 1 de enero de 2015 al "
                       "6 de octubre de 2026. Las líneas punteadas separan los periodos de selección, validación y "
                       "prueba (sección 3.3). Fuente: elaboración propia con datos de XM (2026)."))
d.referencias([
    "Guzmán Feria, J. D. (2024). *Metodología de detección de señales de poder de mercado en el mercado eléctrico "
    "colombiano de corto plazo* [Tesis de maestría, Universidad de los Andes].",
])
d.renumerar()
d.guardar(SALIDA)
print("ok", SALIDA)
