"""Corrige la cita de Velásquez Rojas en la 2.2 con la ficha del repositorio de Uniandes
(https://hdl.handle.net/1992/18699): es de 2016, de un solo autor (García Suárez fue asesor, no coautor)
y del pregrado en Ingeniería Eléctrica. Rojas Ardila (2018) la citaba como Velasquez Rojas y Gracia (2015).
Uso: python s2_velasquez.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

d = Docx(ENTRADA)
d.cambiar_texto("y Velásquez Rojas y Gracia (2015, citado en Rojas Ardila, 2018) implementaron una red neuronal",
                "y Velásquez Rojas (2016) implementó una red neuronal dentro de un aplicativo web")

# la fila de la tabla 1
# Word guarda las filas con atributos (<w:tr w:rsidR=...>), así que el patrón los admite
filas = [x for x in re.finditer(r"<w:tr[ >].*?</w:tr>", d.doc, re.S)
         if "Velásquez Rojas y Gracia (2015)" in d.texto(x.group(0)) or "Velásquez Rojas y Gracia" in x.group(0)]
assert len(filas) == 1, f"hay {len(filas)} filas de Velásquez"
fila = filas[0].group(0)
assert "Velásquez Rojas y Gracia (2015)" in fila, "el nombre quedó partido en varios runs"
assert fila.count(">Pregrado<") == 1, "la celda Pregrado quedó partida en varios runs"
nueva = (fila.replace("Velásquez Rojas y Gracia (2015)", "Velásquez Rojas (2016)")
             .replace(">Pregrado<", ">Pregrado, Ingeniería Eléctrica<"))
d.doc = d.doc.replace(fila, nueva)

d.referencias([
    "Velásquez Rojas, J. S. (2016). *Implementación de red neuronal para pronóstico de precio en Bolsa de la "
    "Energía Eléctrica en Colombia en un aplicativo web* [Trabajo de grado de pregrado, Universidad de los Andes]. "
    "https://hdl.handle.net/1992/18699",
])
d.guardar(SALIDA)
print("ok", SALIDA)
