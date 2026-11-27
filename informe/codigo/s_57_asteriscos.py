"""Quita los asteriscos que quedaron escritos alrededor de la p del valor p en dos párrafos: el del periodo limpio
(sección 5.1) y el del experimento de decisión (sección 5.2).

Los asteriscos de la tabla 2 son la marca de su nota y se dejan.

Uso: python s_57_asteriscos.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, reemplazar_en_bloque

CAMBIOS = [("no se reporta su valor *p*.", "no se reporta su valor p."),
           ("capturó más que elegir al azar (*p* < 0,05).", "capturó más que elegir al azar (p < 0,05).")]

d = Docx(sys.argv[1])
for viejo, nuevo in CAMBIOS:
    k = [(s, e) for s, e in d.bloques() if viejo in Docx.texto(d.doc[s:e])]
    assert len(k) == 1, (viejo, len(k))
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]
texto = Docx.texto(d.doc)
assert "*p*" not in texto and texto.count("*") == 5, texto.count("*")
d.guardar(sys.argv[2])
print("listo")
