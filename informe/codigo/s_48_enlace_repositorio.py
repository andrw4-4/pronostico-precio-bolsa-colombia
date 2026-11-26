"""Agrega el enlace al repositorio del proyecto al final de la sección 1.3 y como referencia.

Uso: python s_48_enlace_repositorio.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, runs



def uno(d, inicio):
    k = [(s, e) for s, e in d.bloques() if Docx.texto(d.doc[s:e]).startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return k[0]


URL = "https://github.com/andrw4-4/pronostico-precio-bolsa-colombia"

d = Docx(sys.argv[1])
assert "(Arismendi Rodriguez, 2026)" not in Docx.texto(d.doc), "el enlace ya estaba"

# Párrafo nuevo con el mismo formato que el último de la sección 1.3
s, e = uno(d, "Sexta, XM corrige los precios")
ppr = re.search(r"<w:pPr>.*?</w:pPr>", d.doc[s:e], re.S)
nuevo = ("<w:p>" + (ppr.group(0) if ppr else "") + runs(
    "El código, los datos procesados y los resultados de este trabajo están en el repositorio del proyecto "
    f"(Arismendi Rodriguez, 2026), {URL}. Los nombres de scripts, notebooks y carpetas que se citan en este "
    "informe se refieren a ese repositorio.") + "</w:p>")
d.doc = d.doc[:e] + nuevo + d.doc[e:]

d.referencias([
    "Arismendi Rodriguez, A. D. (2026). *Pronóstico horario del precio de bolsa en Colombia a una semana* "
    f"[Repositorio de código]. GitHub. {URL}",
])

texto = Docx.texto(d.doc)
assert texto.count("(Arismendi Rodriguez, 2026)") == 1
assert "Arismendi Rodriguez, A. D. (2026)." in texto
d.guardar(sys.argv[2])
print("listo")
