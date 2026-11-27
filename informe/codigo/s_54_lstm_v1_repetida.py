"""La primera LSTM, repetida para recuperar sus pronósticos (comentarios del 26 de noviembre, punto 2.1, paso 2).

La corrida original del 2 de noviembre solo dejó sus métricas: los pronósticos se perdieron al cerrar la sesión de
Colab. El paso 9j la repitió el 26 de noviembre con el mismo código, el mismo panel, la misma configuración y la
misma semilla. Este script agrega a la tabla 15 una fila con la repetición, con todas las columnas (MAE y valor p
con la corrección de Harvey et al. incluidos), y explica la repetición en la sección 4.4, en la nota de la
tabla y en el capítulo V.

Las cifras salen de resultados/revision/tabla15_ampliada.csv (paso 9h) y de
resultados/modelo_lstm_v1/validacion_2022_repeticion.csv (paso 9j).

Uso: python s_54_lstm_v1_repetida.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, esc, reemplazar_en_bloque

RAIZ = Path(__file__).resolve().parents[2]
RES = RAIZ / "resultados"
NOMBRE = "LSTM, primera versión repetida"


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def n(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",").replace("-", "−")


def valor_p(p):
    return "< 0,001" if p < 0.001 else n(p, 3)


_WT = re.compile(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)")


def celda_con(tc, texto):
    """La misma celda con otro texto: queda en el primer <w:t>, con su formato, y los demás se vacían."""
    ms = list(_WT.finditer(tc))
    assert ms, tc[:200]
    partes, ultimo = [], 0
    for i, m in enumerate(ms):
        partes.append(tc[ultimo:m.start()] + m.group(1) + (esc(texto) if i == 0 else "") + m.group(3))
        ultimo = m.end()
    return "".join(partes) + tc[ultimo:]


def fila_con(tr, textos):
    tcs = list(re.finditer(r"<w:tc>.*?</w:tc>", tr, re.S))
    assert len(tcs) == len(textos)
    partes, ultimo = [], 0
    for m, t in zip(tcs, textos):
        partes.append(tr[ultimo:m.start()] + celda_con(m.group(0), t))
        ultimo = m.end()
    return "".join(partes) + tr[ultimo:]


t15 = pd.read_csv(RES / "revision" / "tabla15_ampliada.csv").set_index(["periodo", "pronostico"])
val = pd.read_csv(RES / "modelo_lstm_v1" / "validacion_2022_repeticion.csv", index_col=0)
original = {p: t15.loc[(p, "LSTM, primera versión")] for p in ("2023-2025", "2026")}
rep = {p: t15.loc[(p, NOMBRE)] for p in ("2023-2025", "2026")}
lstm = {p: t15.loc[(p, "LSTM")] for p in ("2023-2025", "2026")}
xgb = {p: t15.loc[(p, "XGBoost")] for p in ("2023-2025", "2026")}
assert (round(original["2023-2025"]["mejora"], 1), round(original["2026"]["mejora"], 1)) == (12.0, 12.9)

d = Docx(sys.argv[1])
assert NOMBRE not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- tabla 15: una fila por periodo
k = [(s, e) for s, e in d.bloques() if d.doc[s:e].startswith("<w:tbl") and "LSTM, primera versión" in
     Docx.texto(d.doc[s:e])]
assert len(k) == 1
s, e = k[0]
tabla = d.doc[s:e]
filas = list(re.finditer(r"<w:tr[ >].*?</w:tr>", tabla, re.S))
v1 = [m for m in filas if Docx.texto(m.group(0)).startswith("LSTM, primera versión")]
assert len(v1) == 2
nueva_tabla, ultimo = [], 0
for m, periodo in zip(v1, ("2023-2025", "2026")):
    r = rep[periodo]
    textos = [NOMBRE, n(r["rmse"], 3), n(r["mae"], 3), n(r["mejora"]), valor_p(r["p_hln"]), n(r["mejora_h3"]),
              n(r["mejora_h3_7"]), n(r["mejora_h8_9"])]
    nueva_tabla.append(tabla[ultimo:m.end()] + fila_con(m.group(0), textos))
    ultimo = m.end()
d.doc = d.doc[:s] + "".join(nueva_tabla) + tabla[ultimo:] + d.doc[e:]

cambiar(d, "La LSTM se diseñó después de conocer el resultado de su primera versión, de la que solo quedaron las "
           "métricas, sin MAE y con el valor p sin corrección (sección 4.4).",
        "La LSTM se diseñó después de conocer el resultado de su primera versión. De la corrida original solo "
        "quedaron las métricas, sin MAE y con el valor p sin corrección; la repetida es la misma red, corrida otra vez "
        "el 26 de noviembre de 2026 con la misma semilla para recuperar sus pronósticos (sección 4.4).")

# ---------------------------------------------------------------- sección 4.4: la repetición
a, b = rep["2023-2025"], rep["2026"]
assert bool(a["cumple_hln"]) and bool(b["cumple_hln"])
epoca = int(val["mejor_epoca"].iloc[0])
mejora_val = val.loc["h = 3 a 9", "mejora"]
mae_lstm = lstm["2023-2025"]["mae"]
assert a["mae"] < mae_lstm, "la frase del MAE supone que la repetición queda por debajo de la LSTM en 2023-2025"
cambiar(d, "Los pronósticos fila por fila se perdieron al cerrar la sesión de Colab, así que esta versión no entra en "
           "las comparaciones entre modelos.",
        "Los pronósticos fila por fila se perdieron al cerrar la sesión de Colab. Para recuperarlos, el 26 de "
        "noviembre de 2026 se repitió la corrida con el mismo código, el mismo panel, la misma configuración y la "
        "misma semilla, sin repetir la búsqueda (9j_lstm_v1_repeticion.py), y sus pronósticos quedaron en la misma "
        f"carpeta. La repetición mejoró {n(a['mejora'])}% en 2023-2025 y {n(b['mejora'])}% en 2026, con MAE de "
        f"{n(a['mae'], 3)} y {n(b['mae'], 3)}, y cumplió el criterio en los cuatro bloques en las dos pruebas, también "
        "con la corrección de Harvey et al. (1997) (tabla 15). Las cifras no son idénticas a las de la corrida "
        "original porque esta se corrió en otra GPU, una T4 en vez de la L4, y porque en la GPU el entrenamiento no "
        "es del todo determinista, pero la conclusión es la misma. La "
        "diferencia se ve más en la validación de 2022, la que en la corrida original llevó a las 6 épocas: esta vez la "
        f"parada temprana se detuvo en la época {epoca} y la mejora fue de {n(mejora_val)}%, frente a 15,0%. Con una "
        "sola semilla, el resultado de una red de este tamaño depende bastante de la corrida, y por eso la LSTM de esta "
        f"sección promedia tres. Con el MAE, la repetición queda por debajo de la LSTM en 2023-2025 ({n(a['mae'], 3)} "
        f"contra {n(mae_lstm, 3)}), algo esperable en una red entrenada con el error absoluto como pérdida. Como la "
        "corrida original, esta versión no entra en las comparaciones entre modelos.")

# ---------------------------------------------------------------- capítulo V
cambiar(d, "La primera versión de la LSTM había mejorado 12,0% y 12,9%, cerca de XGBoost.",
        f"La primera versión de la LSTM había mejorado 12,0% y 12,9%, cerca de XGBoost, y su repetición, "
        f"{n(a['mejora'])}% y {n(b['mejora'])}%.")

texto = Docx.texto(d.doc)
assert texto.count(NOMBRE) == 2 and "9j_lstm_v1_repeticion.py" in texto
d.guardar(sys.argv[2])
print("listo")
