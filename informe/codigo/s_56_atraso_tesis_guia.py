"""Atraso de dos días: de dónde sale el supuesto, sin el sondeo de diez días (comentarios del 26 de noviembre,
punto 2.5, paso 2).

La asesora pidió repetir la consulta a la API durante diez días hábiles para conocer la distribución del atraso.
No hubo tiempo antes de la entrega, así que el informe dice de forma explícita que con tres consultas esa
distribución no se conoce, que el supuesto de dos días se tomó de González Pérez y Urbano Buriticá (2022) y que la
prueba con tres días acota el riesgo. El registro diario queda en el trabajo futuro, con los diez días hábiles.

Uso: python s_56_atraso_tesis_guia.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, reemplazar_en_bloque


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


d = Docx(sys.argv[1])
assert "no de una medición sistemática" not in Docx.texto(d.doc), "este script ya se aplicó"

# limitaciones (1.3)
cambiar(d, "En tres consultas a la API de XM, el último precio disponible tenía tres, dos y tres días de atraso "
           "(sección 3.2).",
        "En tres consultas a la API de XM, el último precio disponible tenía tres, dos y tres días de atraso "
        "(sección 3.2). Con tan pocas consultas no se sabe con qué frecuencia llega con dos o con tres días, así que "
        "el supuesto de dos días se tomó de González Pérez y Urbano Buriticá (2022), y no de una medición "
        "sistemática. Para acotar ese riesgo, la sección 5.1 repite la evaluación con tres días, y las conclusiones "
        "se mantienen.")

# datos (3.2)
cambiar(d, "y la regulación no fija cuándo se publica. El diseño supone dos días, el mismo atraso",
        "y la regulación no fija cuándo se publica. Con tres consultas tampoco se conoce la distribución del atraso. "
        "El diseño supone dos días, el mismo atraso")

# trabajo futuro (6.2)
cambiar(d, "Registrar cada día, a la misma hora, el último dato disponible de cada serie daría la distribución del "
           "atraso",
        "Registrar cada día, a la misma hora y durante al menos diez días hábiles, el último dato disponible de cada "
        "serie daría la distribución del atraso")

texto = Docx.texto(d.doc)
for x in ("no de una medición sistemática", "tampoco se conoce la distribución del atraso",
          "durante al menos diez días hábiles"):
    assert texto.count(x) == 1, x
d.guardar(sys.argv[2])
print("listo")
