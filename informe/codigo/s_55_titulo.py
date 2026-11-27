"""Título nuevo del informe (comentarios del 26 de noviembre, punto 2.2.6).

La asesora pidió ajustar el título según el resultado. El anterior nombraba los tres modelos; el nuevo pone
adelante lo que la revisión mostró que explica buena parte de los resultados: cada dato entra el día en que se
publica. El título solo está en la portada; la referencia al repositorio lleva el nombre del repositorio y no
cambia.

Uso: python s_55_titulo.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, reemplazar_en_bloque

VIEJO = "PRONÓSTICO HORARIO DEL PRECIO DE BOLSA DE ENERGÍA EN COLOMBIA A UNA SEMANA CON SARIMAX, XGBOOST Y REDES LSTM"
NUEVO = ("PRONÓSTICO HORARIO DEL PRECIO DE BOLSA DE ENERGÍA EN COLOMBIA A UNA SEMANA CON LA INFORMACIÓN PUBLICADA AL "
         "DÍA DEL PRONÓSTICO")

d = Docx(sys.argv[1])
k = [(s, e) for s, e in d.bloques() if Docx.texto(d.doc[s:e]) == VIEJO]
assert len(k) == 1, "este script ya se aplicó o la portada cambió"
s, e = k[0]
d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], VIEJO, NUEVO) + d.doc[e:]
texto = Docx.texto(d.doc)
assert NUEVO in texto and "REDES LSTM" not in texto
d.guardar(sys.argv[2])
print("listo")
