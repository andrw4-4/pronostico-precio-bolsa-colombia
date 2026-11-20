"""Ajusta las tres frases que apuntaban a secciones que Andrés dejó sin texto a propósito el 20 de noviembre de 2026
(el cuerpo de la 4.2 y de la 5.1 y la 5.2; los títulos siguen):
- 2.4: el párrafo "Por último, un menor error no siempre se traduce en mejores decisiones. Por eso la sección 4.2
  evalúa..." sale entero, porque solo anunciaba la 4.2.
- 3.6: el séptimo bloque "queda como trabajo futuro", sin remitir a la 5.2.
- 4.1: la frase sobre el error en pesos termina en "viene con un sesgo hacia abajo", sin remitir a la 4.2.
Uso: python s_referencias_20nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, reemplazar_en_bloque

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
PARRAFO_24 = ("Por último, un menor error no siempre se traduce en mejores decisiones. Por eso la sección 4.2 evalúa "
              "los pronósticos también por su valor para un consumidor y para un comercializador.")
CAMBIOS = [
    ("pero no se probó y queda como trabajo futuro (sección 5.2).", "pero no se probó y queda como trabajo futuro."),
    ("y viene con un sesgo hacia abajo; la sección 4.2 muestra lo que eso significa para un comercializador.",
     "y viene con un sesgo hacia abajo."),
]


def cuerpo(d):
    """(inicio, fin, texto) de cada bloque del cuerpo, sin el índice."""
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


d = Docx(ENTRADA)
n_bloques = len(d.bloques())

# 2.4: el párrafo sale entero
k = [(s, e) for s, e, t in cuerpo(d) if t == PARRAFO_24]
assert len(k) == 1 and d.doc[k[0][0]:k[0][1]].startswith("<w:p"), "el párrafo de la 2.4 no está igual"
d.doc = d.doc[:k[0][0]] + d.doc[k[0][1]:]

# 3.6 y 4.1: se quita solo la remisión
for viejo, nuevo in CAMBIOS:
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]

# ninguna frase del cuerpo remite ya a la 4.2, la 5.1 o la 5.2
todo = " ".join(t for _, _, t in cuerpo(d))
assert not re.search(r"secci[oó]n(es)? [^.;]*?(4\.2|5\.1|5\.2)", todo)
assert len(d.bloques()) == n_bloques - 1
d.guardar(SALIDA)
print("ok", SALIDA)
