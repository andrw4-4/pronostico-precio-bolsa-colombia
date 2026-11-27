"""Lo que faltaba de los puntos 2.11 y 2.12 de los comentarios del 26 de noviembre.

2.11  La lista de la asesora pide Trespalacios et al. (2023) y Marcjasz et al. (2018), que no estaban: el informe
      citaba otro trabajo de Trespalacios (2025) y otro de Marcjasz (2019). Se agregan los dos, con su DOI
      verificado en Crossref, en el texto de la 2.2 y como filas de la tabla 1. Marcjasz et al. (2018) también va en
      el trabajo futuro, como forma de mejorar LEAR.
2.12  El ONI del trimestre de agosto a octubre de 2026 (2,46, publicado a comienzos de noviembre), junto al de julio
      a septiembre, en la sección 1.1 (archivo oni.ascii.txt de la NOAA).

Uso: python s_52_referencias_26nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, reemplazar_en_bloque, tabla


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


d = Docx(sys.argv[1])
assert "Trespalacios et al. (2023)" not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- texto de la 2.2
cambiar(d, "promediar los dos mejora, y Marcjasz et al. (2019) encontraron que un comité de redes NARX",
        "promediar los dos mejora; Marcjasz et al. (2018) concluyeron, con datos de tres mercados, que elegir de "
        "antemano una sola ventana de calibración es riesgoso y que promediar los pronósticos de varias ventanas es más "
        "robusto, y Marcjasz et al. (2019) encontraron que un comité de redes NARX")
cambiar(d, "Trespalacios et al. (2025) compararon métodos de aprendizaje profundo",
        "Trespalacios et al. (2023) modelaron el precio spot colombiano con reversión a la media, cambio de régimen y "
        "distribuciones semiparamétricas, y encontraron que en las temporadas de escasez suben la media, la varianza y "
        "el riesgo del precio. Trespalacios et al. (2025) compararon métodos de aprendizaje profundo")

# ---------------------------------------------------------------- tabla 1: dos filas nuevas
k = [(s, e) for s, e in d.bloques() if d.doc[s:e].startswith("<w:tbl")
     and "Trespalacios et al. (2025)" in Docx.texto(d.doc[s:e])]
assert len(k) == 1
s, e = k[0]
filas = [[Docx.texto(c) for c in re.findall(r"<w:tc>.*?</w:tc>", f, re.S)]
         for f in re.findall(r"<w:tr[ >].*?</w:tr>", d.doc[s:e], re.S)]
assert len(filas) == 21 and all(len(f) == 8 for f in filas)
nombres = [f[0] for f in filas]
marcjasz = ["Marcjasz et al. (2018)", "Tres mercados", "Horaria", "Día siguiente",
            "Cuatro modelos autorregresivos expertos con varias ventanas de calibración", "Una sola ventana", "—",
            "Elegir una ventana de antemano es riesgoso; promediar varias ventanas es más robusto."]
trespalacios = ["Trespalacios et al. (2023)", "Colombia", "—", "—",
                "Reversión a la media con cambio de régimen y distribuciones semiparamétricas",
                "Modelos con distribución normal", "—",
                "En escasez suben la media, la varianza y el riesgo del precio; el modelo de cambio de régimen supera "
                "a los tradicionales."]
filas.insert(nombres.index("Marcjasz et al. (2019)"), marcjasz)
filas.insert([f[0] for f in filas].index("Trespalacios et al. (2025)"), trespalacios)
d.doc = d.doc[:s] + tabla(filas, [2.1, 1.6, 1.7, 1.6, 2.2, 1.7, 1.9, 2.7], tam=16, junta=False) + d.doc[e:]

# ---------------------------------------------------------------- trabajo futuro
cambiar(d, "Faltan otros que la literatura usa como referencia: un modelo autorregresivo experto",
        "Faltan otros que la literatura usa como referencia: LEAR con el promedio de varias ventanas de calibración "
        "(Marcjasz et al., 2018); un modelo autorregresivo experto")

# ---------------------------------------------------------------- 2.12: ONI de agosto a octubre
cambiar(d, "fue de 2,2 °C en el trimestre de julio a septiembre de 2026, el último publicado en octubre, un valor "
           "parecido al de los meses previos a la crisis de 2015-2016",
        "fue de 2,2 °C en el trimestre de julio a septiembre de 2026, el último publicado en octubre, y de 2,5 °C en "
        "el de agosto a octubre, publicado a comienzos de noviembre, valores parecidos a los de los meses previos a la "
        "crisis de 2015-2016")

d.referencias([
    "Marcjasz, G., Serafin, T., y Weron, R. (2018). Selection of calibration windows for day-ahead electricity price "
    "forecasting. *Energies*, *11*(9), 2364. https://doi.org/10.3390/en11092364",
    "Trespalacios, A., Cortés, L. M., y Perote, J. (2023). The impact of the El Niño phenomenon on electricity prices "
    "in hydrologic-based production systems: A switching regime semi-nonparametric approach. *Energy Science & "
    "Engineering*, *11*(5), 1564-1578. https://doi.org/10.1002/ese3.1414",
])

texto = Docx.texto(d.doc)
for x in ("Marcjasz et al. (2018) concluyeron", "(Marcjasz et al., 2018)", "Trespalacios et al. (2023) modelaron",
          "Marcjasz, G., Serafin, T.", "Trespalacios, A., Cortés, L. M.", "2,5 °C en el de agosto a octubre"):
    assert x in texto, x
assert texto.count("Trespalacios et al. (2023)Colombia") == 1 and texto.count("Marcjasz et al. (2018)Tres") == 1
d.guardar(sys.argv[2])
print("listo")
