"""Pone en el informe los diagramas hechos con formas de Word y las gráficas con los colores nuevos.

Los diagramas (figuras 3, 6, 9, 13, 16 y 17) reemplazan a las imágenes que hacía matplotlib; se pueden editar en
Word como cualquier forma. Las gráficas de datos cambian de imagen y conservan su ancho; el alto se ajusta a la
proporción de la imagen nueva. La numeración no cambia; las leyendas que nombraban un color se ajustan a los
colores nuevos. También corrige el subíndice de SARIMAX(p, d, q)(P, D, Q)s, que había quedado con asteriscos.
Uso: python s_figuras_color.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

import diagramas_word as dw
from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"

DIAGRAMAS = {"f12_mercado_corto_plazo.png": dw.mercado, "f14_flujo_datos.png": dw.flujo,
             "f17_sarimax_construccion.png": dw.etapas_sarimax, "f21_xgboost_construccion.png": dw.etapas_xgboost,
             "f24_lstm_construccion.png": dw.etapas_lstm, "f25_lstm_arquitectura.png": dw.arquitectura}
# nombre de la imagen dentro del documento -> imagen nueva
GRAFICAS = {"image2.png": "f00_orden_merito.png", "image3.png": "f01_precio_embalses_nino.png",
            "image5.png": "f03_diseno_pronostico.png"}
GRAFICAS.update({f"{f}.png": f"{f}.png" for f in [
    "f13_precio_y_cambio", "f15_ciclos_precio", "f16_autocorrelacion", "f18_sarimax_preblanqueo",
    "f19_sarimax_validacion", "f20_sarimax_residuos", "f22_xgboost_columnas", "f23_xgboost_importancia",
    "f26_lstm_importancia"]})

d = Docx(ENTRADA)
assert "Diagrama 3012" not in d.doc, "los diagramas ya están"
for imagen, funcion in DIAGRAMAS.items():
    d.reemplazar_parrafo_con_imagen(imagen, funcion())
for media, png in GRAFICAS.items():
    d.cambiar_imagen(media, FIG / png)

# leyendas que nombraban los colores de antes
LEYENDAS = [
    ("Las líneas punteadas separan los periodos", "Las franjas de color marcan los periodos"),
    ("Los rezagos múltiplos de siete van en negro; la franja gris es la banda",
     "Los rezagos múltiplos de siete van en rojo; la franja amarilla es la banda"),
    ("la línea negra es la holgura de la oferta", "la línea violeta es la holgura de la oferta"),
    ("las barras claras son las horas en que se rechaza al 5%", "las barras rojas son las horas en que se rechaza al 5%"),
    ("los rezagos múltiplos de siete van en negro y la franja gris es la banda de 95%",
     "los rezagos múltiplos de siete van en un verde más intenso, los que se salen de la banda van en rojo y la "
     "franja amarilla es la banda de 95%"),
]
for viejo, nuevo in LEYENDAS:
    d.cambiar_texto(viejo, nuevo)
# el subíndice s de SARIMAX ya está en cursiva; sobran los asteriscos
assert d.doc.count(">*s*</w:t>") == 1
d.doc = d.doc.replace(">*s*</w:t>", ">s</w:t>")
d.guardar(SALIDA)
print("ok", SALIDA)
