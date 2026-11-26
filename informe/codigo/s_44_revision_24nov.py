"""Revisión completa del informe (24 de noviembre de 2026): corrige lo que quedó desalineado entre versiones,
sin cambiar la estructura. Cada cambio se comprobó contra el repositorio:
- 3.3: los 7 rezagos de Newey-West salen de la regla automática con los unos 1.750 días de 2015-2019, cuando se
  fijó la selección de XGBoost (2d_seleccion_variables.py y docs/REFERENCIAS.md); se aclara de qué días se trata.
- 3.4: la tabla 5 no se citaba en el texto.
- Tabla 12 y tabla 14: el ingenuo del día da 0,2888 en la validación de la LSTM y 0,2943 en la de SARIMAX (tabla 5)
  porque la LSTM evalúa cada año solo con los orígenes cuya semana termina en ese año (1.069 días frente a 1.093,
  comprobado con resultados/modelo_sarimax/etapa4_comun.csv.gz). Las notas lo dicen.
- Tabla 11 y figura 18: habían perdido su fuente en una edición; todas las demás la tienen.
- Figura 7: dice "los pasos del repositorio" pero el informe no daba el enlace.
- Figura 11: "Reen trenamiento" llevaba un espacio dentro de la palabra; pasa a un guion opcional.
- Anexo A: "simplificación del autor" pasa a "simplificación", como el resto del texto.
- Referencias: Künsch (1989) no se cita (era del bootstrap de la 4.2 anterior), y había dos entradas
  "XM S.A. E.S.P. (2026)" para la misma fuente; quedan en una, con la sigla XM, y la cita de 1.1 queda como las demás.
Uso: python s_44_revision_24nov.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, reemplazar_en_bloque

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
REPO = "https://github.com/andrw4-4/pronostico-precio-bolsa-colombia"

CAMBIOS = [
    # 3.3
    ("y 7 por la regla automática de Newey y West (1994) con unos 1.750 días.",
     "y 7 por la regla automática de Newey y West (1994), calculada al fijar la selección de XGBoost con los unos "
     "1.750 días de 2015-2019; el mismo número se usó después en todas las comparaciones."),
    # 3.4
    ("Dar a cada hora su propio orden no mejoró el pronóstico:",
     "Dar a cada hora su propio orden no mejoró el pronóstico (tabla 5):"),
    # nota de la tabla 12
    ("Nota: el RMSE del ingenuo del día en el mismo periodo es 0,2888.",
     "Nota: el RMSE del ingenuo del día en las mismas filas es 0,2888. Es menor que el de la tabla 5 porque en la "
     "LSTM cada año se evalúa solo con los orígenes cuya semana pronosticada termina dentro de ese año."),
    # nota de la tabla 14
    ("SARIMAX y XGBoost se reentrenaron cada mes y la LSTM una vez por año (sección 3.6).",
     "SARIMAX y XGBoost se reentrenaron cada mes; la LSTM, una vez por año, y se evaluó solo con los orígenes cuya "
     "semana pronosticada termina dentro del mismo año (sección 3.6 y tabla 12). Por eso esta fila no sirve para "
     "comparar los modelos entre sí; esa comparación es la de las pruebas (sección 4.1)."),
    # leyenda de la figura 18
    ("con los precios conocidos hasta el 6 de octubre.",
     "con los precios conocidos hasta el 6 de octubre. Fuente: elaboración propia con datos de XM (2026)."),
    # leyenda de la figura 7
    ("Los números son los pasos del repositorio.",
     f"Los números son los pasos del repositorio del proyecto, {REPO}, donde están también los scripts y "
     "notebooks que se citan en este informe."),
    # anexo A
    ("es una simplificación del autor, para", "es una simplificación, para"),
    # 1.1: la cita de XM como en el resto del informe
    ("(XM S.A. E.S.P., 2026)", "(XM, 2026)"),
]


def bloques(d):
    """(inicio, fin, texto) de cada bloque del cuerpo, sin el índice."""
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def uno(d, cond, que):
    k = [(s, e) for s, e, t in bloques(d) if cond(t)]
    assert len(k) == 1, f"hay {len(k)} bloques con {que}"
    return k[0]


def cambiar(d, viejo, nuevo):
    s, e = uno(d, lambda t: viejo in t, repr(viejo[:60]))
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


d = Docx(ENTRADA)
antes = [t for _, _, t in bloques(d)]

for viejo, nuevo in CAMBIOS:
    cambiar(d, viejo, nuevo)

# referencias: sale Künsch (1989), y las dos de XM (2026) quedan en una
for inicio in ("Künsch, H. R. (1989).", "XM S.A. E.S.P. (2026). Datos del mercado de energía mayorista"):
    s, e = uno(d, lambda t: t.startswith(inicio), inicio)
    assert d.doc[s:e].startswith("<w:p")
    d.doc = d.doc[:s] + d.doc[e:]
cambiar(d, "XM S.A. E.S.P. (2026). ", "XM S.A. E.S.P. [XM]. (2026). ")
cambiar(d, "API de XM y SIMEM, consultada con la librería pydataxm",
        "Datos del mercado de energía mayorista: API de XM y de SIMEM, consultadas con la librería pydataxm")

# tabla 11: la misma línea de fuente que la tabla 9, después de la tabla
fuente = [d.doc[s:e] for s, e, t in bloques(d) if t == "Fuente: elaboración propia."]
assert fuente, "no hay una línea 'Fuente: elaboración propia.' para copiar"
fuente = re.sub(r' w14:(paraId|textId)="[^"]*"', "", fuente[0])
B = bloques(d)
i = next(k for k, (_, _, t) in enumerate(B) if t.startswith("Tabla 11."))
s, e, _ = B[i + 1]
assert d.doc[s:e].startswith("<w:tbl") and B[i + 2][2].startswith("Evaluación con tres semillas.")
d.doc = d.doc[:e] + fuente + d.doc[e:]

# figura 11: el espacio dentro de "Reentrenamiento" pasa a guion opcional (en el dibujo y en su copia VML)
patron = re.compile(r'(<w:t>Reen</w:t></w:r><w:r[^>]*><w:rPr>(?:(?!</w:rPr>).)*</w:rPr>)<w:t xml:space="preserve"> </w:t>')
assert len(patron.findall(d.doc)) == 2
d.doc = patron.sub(r"\1<w:softHyphen/>", d.doc)

# comprobaciones
despues = [t for _, _, t in bloques(d)]
assert len(despues) == len(antes) - 2 + 1
todo = " ".join(despues)
for x in ("Künsch", "simplificación del autor", "Reen trenamiento", "con unos 1.750 días.", "XM S.A. E.S.P., 2026",
          "en el mismo periodo es 0,2888"):
    assert x not in todo, x
assert todo.count("XM S.A. E.S.P. [XM]. (2026).") == 1 and todo.count("XM S.A. E.S.P. (2026)") == 0
assert "(tabla 5)" in todo and REPO in todo
assert sum(t == "Fuente: elaboración propia." for t in despues) == sum(t == "Fuente: elaboración propia." for t in antes) + 1
assert "Reentrenamiento mensual" in next(t for t in despues if t.startswith("1. Columnas2015-2022"))
# lo que dicen las notas nuevas ya está en el texto o en las tablas
assert "0,2943" in todo and "0,2888" in todo

cambiados = [t for t in despues if t not in antes]
print(len(cambiados), "bloques nuevos o cambiados:")
for t in cambiados:
    print(" -", t[:150], "...", t[-110:] if len(t) > 260 else "")
d.guardar(SALIDA)
print("ok", SALIDA)
