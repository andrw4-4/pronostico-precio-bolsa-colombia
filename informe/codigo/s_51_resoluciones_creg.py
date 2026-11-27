"""Tabla de las resoluciones del precio de escasez (comentarios del 17 de noviembre, sección 6.4, tarea 1).

Agrega el anexo G con la tabla G1 (CREG 071 de 2006, 140 de 2017 y 101 066 de 2024: número, fecha, qué cambió
y desde cuándo hay datos de XM) y corrige la sección 2.1: desde diciembre de 2017 las obligaciones de energía
firme se activan con el precio de escasez de activación, no con el precio de escasez de la CREG 071, que es la
variable PrecEsca del panel. La relación se comprueba aquí con los datos.

Fuentes: textos de las resoluciones en el gestor normativo de la CREG (fecha del encabezado y del Diario Oficial)
y descripción de las métricas en la API de XM.

Uso: python s_51_resoluciones_creg.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from docx_final import Docx, reemplazar_en_bloque, runs, tabla

RAIZ = Path(__file__).resolve().parents[2]


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def p(t):
    return f"<w:p>{runs(t)}</w:p>"


def nota(t):
    x = runs(t).replace("<w:r><w:rPr>", '<w:r><w:rPr><w:sz w:val="20"/>').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{x}</w:p>'


def cap_anexo(nombre, texto):
    return ('<w:p><w:pPr><w:pStyle w:val="Descripcin"/><w:keepNext/><w:spacing w:before="240"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">{nombre}. </w:t></w:r>{runs(texto)}</w:p>')


d = Docx(sys.argv[1])
assert "Anexo G" not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- comprobación con los datos
dia = pd.read_csv(RAIZ / "paneles" / "panel_diario.csv", parse_dates=["fecha"]).set_index("fecha")
dia = dia.loc[:"2026-10-06"]
esca, marg, inf, act = (dia[c] for c in ("precio_escasez", "precio_esca_marg", "precio_esca_inf", "precio_esca_act"))
assert marg.first_valid_index() == pd.Timestamp("2017-12-01") == act.first_valid_index()
assert inf.first_valid_index() == pd.Timestamp("2025-03-01") == dia["precio_esca_sup"].first_valid_index()
con = act.notna()
assert (abs(act[con] - np.fmax(np.fmax(esca, marg), inf)[con]) < 1).all()     # activación = el mayor de todos
assert (abs(dia["precio_esca_sup"] - marg)[dia["precio_esca_sup"].notna()] < 1).all()   # superior = marginal
hueco = act.loc["2017-12-01":][act.loc["2017-12-01":].isna()].index
assert (hueco.min(), hueco.max()) == (pd.Timestamp("2025-03-01"), pd.Timestamp("2026-04-30"))
umbral = np.fmax(np.fmax(esca, marg), inf).where(dia.index >= "2017-12-01", esca)   # activación, completa
razon = (umbral / esca).loc["2018":].mean()
assert round(100 * (razon - 1)) == 32
anio = dia.index.year
sobre_esca = (dia["precio_bolsa"] > esca).groupby(anio).sum()
sobre_act = (dia["precio_bolsa"] > umbral).groupby(anio).sum()
assert (sobre_esca[2023], sobre_esca[2024], sobre_act[2023], sobre_act[2024]) == (77, 102, 12, 54)
assert sobre_act.loc[2017:2022].sum() == 0 and sobre_act[2025] == 0 and sobre_act[2026] == 0
assert (sobre_esca[2020], sobre_esca[2026]) == (37, 60)
meses = sorted({f"{f:%Y-%m}" for f in dia.index[(dia["precio_bolsa"] > umbral) & (dia.index >= "2017-12-01")]})
assert meses == ["2023-10", "2024-04", "2024-09", "2024-10", "2024-11", "2024-12"], meses

# ---------------------------------------------------------------- sección 2.1
cambiar(d, "Cuando el precio de bolsa lo supera, se activan las obligaciones de energía firme, con las que los "
           "generadores se comprometen a entregar energía en condiciones críticas de abastecimiento (CREG, 2006). "
           "Por eso, la distancia entre el precio de bolsa y el precio de escasez indica qué tan cerca está el "
           "sistema de una situación crítica.",
        "Cuando el precio de bolsa supera ese umbral se hacen exigibles las obligaciones de energía firme, con las "
        "que los generadores se comprometen a entregar energía en condiciones críticas de abastecimiento (CREG, "
        "2006). Por eso, la distancia entre el precio de bolsa y el precio de escasez indica qué tan cerca está el "
        "sistema de una situación crítica. La forma de calcular el umbral cambió dos veces dentro del periodo de los "
        "datos (anexo G): desde diciembre de 2017 es el precio de escasez de activación, el mayor entre el precio de "
        "escasez de 2006 y un precio marginal de escasez (CREG, 2017), y desde 2025 entra además un precio de "
        "escasez inferior (CREG, 2024). La variable del panel es el precio de escasez de 2006, que XM sigue "
        "publicando; entre 2018 y 2026 el de activación fue en promedio 32% más alto, así que la distancia del "
        "panel es una medida aproximada de qué tan cerca está el umbral.")

# ---------------------------------------------------------------- anexo G
filas = [
    ["Resolución", "Expedición y publicación", "Qué definió", "Serie de XM"],
    ["CREG 071 de 2006",
     "3 de octubre de 2006; Diario Oficial 46.421, 14 de octubre de 2006",
     "Adoptó el cargo por confiabilidad, con un periodo de transición desde el 1 de diciembre de 2006. Definió el "
     "precio de escasez, actualizado cada mes con un índice de precios de combustibles; por encima de él se hacen "
     "exigibles las obligaciones de energía firme.",
     "PrecEsca; en el panel, desde el 1 de enero de 2015"],
    ["CREG 140 de 2017",
     "25 de septiembre de 2017; Diario Oficial 50.371, 29 de septiembre de 2017",
     "Definió el precio marginal de escasez, el costo variable de una planta de referencia elegida cada mes según su "
     "participación en las obligaciones de energía firme. El umbral pasó a ser el precio de escasez de activación, el "
     "mayor entre el de 2006 y el marginal, y las horas por encima se liquidan al precio de escasez ponderado. Se "
     "aplicó a las asignaciones nuevas y, si el generador lo elegía, a las vigentes.",
     "PrecEscaMarg y PrecEscaAct, desde el 1 de diciembre de 2017"],
    ["CREG 101 066 de 2024",
     "18 de noviembre de 2024; Diario Oficial 52.958, 2 de diciembre de 2024",
     "Separó dos precios de escasez: el superior, igual al precio marginal de 2017, para plantas que respaldan sus "
     "obligaciones con combustibles líquidos o gas, y el inferior, con un valor de referencia de 359 $/kWh, para "
     "plantas que las respaldan en más de 50% con recursos renovables o carbón. Se aplica a las asignaciones nuevas "
     "y, de forma voluntaria, a las vigentes.",
     "PrecEscaSup y PrecEscaInf, desde el 1 de marzo de 2025"],
]
anexo = (
    d.titulo_como("Anexo B. Medidas y criterios de XGBoost", "Anexo G. Resoluciones del precio de escasez")
    + p("La tabla G1 resume las tres resoluciones de la CREG que definen el precio de escasez dentro del periodo de "
        "los datos (sección 2.1). En los datos de XM, el precio de escasez de activación es igual, en todos los días "
        "desde diciembre de 2017, al mayor entre PrecEsca y PrecEscaMarg, y desde marzo de 2025 al mayor entre esos y "
        "PrecEscaInf; el precio superior es igual al marginal. Eso confirma que PrecEsca, la variable del panel, es "
        "el precio de escasez de la CREG 071 de 2006. XM no publica el de activación de marzo de 2025 a abril de "
        "2026; en esos meses se calculó como ese mayor valor. Entre 2018 y 2026 el precio de activación fue en "
        "promedio 32% más alto que el de 2006.")
    + p("El umbral que se use cambia la lectura de los episodios. Con el precio de 2006, el precio de bolsa promedio "
        "del día lo superó 37 días en 2020, 77 en 2023, 102 en 2024 y 60 en 2026. Con el de activación, solo 12 días "
        "en 2023 y 54 en 2024, y ninguno entre 2017 y 2022 ni en 2025 y 2026. Con el precio promedio del día, el "
        "umbral de las obligaciones de energía firme solo se superó en octubre de 2023 y abril de 2024, dentro de El "
        "Niño, y de septiembre a diciembre de 2024, con el déficit de aportes.")
    + cap_anexo("Tabla G1", "Resoluciones de la CREG que definen el precio de escasez, 2006-2024.")
    + tabla(filas, [2.4, 3.4, 7.6, 3.0], tam=18, junta=False)
    + nota("Nota: fechas del encabezado de cada resolución y de su publicación en el Diario Oficial. Las páginas del "
           "gestor normativo de la CREG incluyen modificaciones posteriores; la tabla describe lo que definió cada "
           "resolución al expedirse. Fuente: elaboración propia con base en CREG (2006, 2017, 2024) y en la "
           "descripción de las métricas de XM (2026)."))
fin = d.doc.rfind("<w:sectPr")
d.doc = d.doc[:fin] + anexo + d.doc[fin:]

d.referencias([
    "Comisión de Regulación de Energía y Gas [CREG]. (2017). Resolución CREG 140 de 2017, del 25 de septiembre de "
    "2017: Por la cual se define el precio marginal de escasez del Cargo por Confiabilidad, se hacen modificaciones a "
    "la Resolución CREG 071 de 2006 y a otras resoluciones. Gestor normativo de la CREG.",
    "Comisión de Regulación de Energía y Gas [CREG]. (2024). Resolución CREG 101 066 de 2024, del 18 de noviembre de "
    "2024: Por la cual se definen nuevos precios de escasez del Cargo por Confiabilidad, se hacen modificaciones a la "
    "Resolución CREG 071 de 2006 y a otras resoluciones. Gestor normativo de la CREG.",
])

texto = Docx.texto(d.doc)
for x in ("(CREG, 2017)", "(CREG, 2024)", "Anexo G. Resoluciones del precio de escasez", "Tabla G1",
          "Resolución CREG 140 de 2017, del 25", "Resolución CREG 101 066 de 2024, del 18"):
    assert x in texto, x
d.guardar(sys.argv[2])
print("listo")
