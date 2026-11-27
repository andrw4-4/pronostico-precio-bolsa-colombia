"""La semana del 9 al 15 de octubre de 2026 (figura 18) se llama pronóstico pseudo fuera de muestra, como pidió la
asesora en los comentarios del 17 de noviembre: el panel se cortó el 6 de octubre, así que no hay fuga, pero las
configuraciones se fijaron en noviembre, con esos precios ya publicados, y no es un pronóstico en tiempo real.

Uso: python s_59_pseudo_fuera_de_muestra.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, reemplazar_en_bloque

VIEJO = "Es una demostración que respeta la información disponible el 6 de octubre."
NUEVO = "Es una demostración pseudo fuera de muestra, que respeta la información disponible el 6 de octubre."

d = Docx(sys.argv[1])
assert "pseudo fuera de muestra" not in Docx.texto(d.doc), "este script ya se aplicó"
k = [(s, e) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400] and VIEJO in Docx.texto(d.doc[s:e])]
assert len(k) == 1, len(k)
s, e = k[0]
d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], VIEJO, NUEVO) + d.doc[e:]
assert Docx.texto(d.doc).count("pseudo fuera de muestra") == 1
d.guardar(sys.argv[2])
print("listo")
