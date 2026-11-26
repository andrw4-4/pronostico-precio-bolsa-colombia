"""Corrige la redacción de la frase de Newey-West que dejó s_44_revision_24nov.py (24 de noviembre de 2026).
Decía "con los unos 1.750 días de 2015-2019"; queda "con los días de 2015-2019, unos 1.750".
Uso: python s_45_ajuste_24nov.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, reemplazar_en_bloque

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
VIEJO = "con los unos 1.750 días de 2015-2019;"
NUEVO = "con los días de 2015-2019, unos 1.750;"


def cuerpo(d):
    """(inicio, fin, texto) de cada bloque del cuerpo, sin el índice."""
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


d = Docx(ENTRADA)
antes = [t for _, _, t in cuerpo(d)]
k = [(s, e) for s, e, t in cuerpo(d) if VIEJO in t]
assert len(k) == 1, f"hay {len(k)} bloques con la frase"
s, e = k[0]
d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], VIEJO, NUEVO) + d.doc[e:]
despues = [t for _, _, t in cuerpo(d)]
assert len(antes) == len(despues)
cambiados = [i for i, (a, b) in enumerate(zip(antes, despues)) if a != b]
assert len(cambiados) == 1, cambiados
assert "unos 1.750 días" not in " ".join(despues) and NUEVO in despues[cambiados[0]]
print("DESPUÉS:", despues[cambiados[0]][-300:])
d.guardar(SALIDA)
print("ok", SALIDA)
