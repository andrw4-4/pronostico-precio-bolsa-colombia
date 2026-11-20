"""Quita el MAPE del informe y pasa las fórmulas de XGBoost a un anexo B.

1. MAPE. Sale la ecuación (15) y la frase de la sección 2.4 que lo justificaba por los trabajos anteriores; en su
   lugar queda una frase que dice por qué no se usa. Sale la columna del MAPE de la tabla 15 y su mención en la nota
   y en el texto de la sección 4.1. La semana final de la sección 4.1 se da con el RMSE en logaritmo, que tiene el
   mismo orden (resultados/comparacion/semana_final_tres_modelos.csv). En la sección 1.1, el MAPE de 11% del ingenuo
   de un día se cambia por un resultado propio: con solo el precio y el calendario, XGBoost no le ganó al ingenuo.
2. Anexo B. Las seis fórmulas de la sección 3.5 (Spearman, las dos del valor SHAP, la regla de un error estándar, la
   pérdida pseudo-Huber y la corrección del sesgo) pasan al anexo B como (B1) a (B6). En la sección 3.5 queda cada
   idea en palabras, con la remisión al anexo.
3. Numeración. Las ecuaciones del cuerpo pasan de 1-34 a 1-27, y se cambian todas sus referencias en el texto.
Va después de s5_conclusiones.py. Uso: python s_mape_anexo_b.py ENTRADA.docx SALIDA.docx"""
import csv
import re
import sys
from pathlib import Path

from docx_final import Docx, esc, runs

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
RAIZ = Path(__file__).resolve().parents[2]

d = Docx(ENTRADA)
assert "Anexo B. " not in d.doc, "el anexo B ya está"
B = d.bloques()
piezas = [d.doc[s:e] for s, e in B]


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x)).replace("&lt;", "<").replace("&gt;", ">") \
        .replace("&amp;", "&")


def uno(condicion, que):
    i = [k for k, x in enumerate(piezas) if condicion(x)]
    assert len(i) == 1, f"hay {len(i)} bloques con {que}"
    return i[0]


def p(inicio, contiene=""):
    return uno(lambda x: x.startswith("<w:p") and texto(x).startswith(inicio) and contiene in texto(x), inicio)


def ec(n):
    return uno(lambda x: x.startswith("<w:tbl") and "<m:oMath" in x and f"<w:t>({n})</w:t>" in x, f"la ecuación ({n})")


def marcado(x):
    """Texto de un párrafo con el formato de runs(): *cursiva*, _{subíndice}, ^{superíndice}."""
    trozos = []
    for r in re.finditer(r"<w:r(?:\s[^>]*)?>(.*?)</w:r>", x, re.S):
        rpr = re.search(r"<w:rPr>(.*?)</w:rPr>", r.group(1), re.S)
        rpr = rpr.group(1) if rpr else ""
        t = "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", r.group(1)))
        t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        f = "sub" if 'w:val="subscript"' in rpr else "sup" if 'w:val="superscript"' in rpr else \
            "i" if "<w:i/>" in rpr else ""
        if t:
            if trozos and trozos[-1][0] == f:
                trozos[-1][1] += t
            else:
                trozos.append([f, t])
    envoltura = {"": "{}", "i": "*{}*", "sub": "_{{{}}}", "sup": "^{{{}}}"}
    return "".join(envoltura[f].format(t) for f, t in trozos)


def rehacer(x, nuevo):
    """El mismo párrafo, con su formato de párrafo, pero con el texto `nuevo` y sin el w14:paraId de Word."""
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", x, re.S)
    return "<w:p>" + (ppr.group(0) if ppr else "") + runs(nuevo) + "</w:p>"


def cambiar(viejo, nuevo):
    assert d.doc.count(viejo) == 1, "el trozo a cambiar no está una sola vez"
    d.doc = d.doc.replace(viejo, nuevo)


def quitar_frase(k, vieja, nueva=""):
    m = marcado(piezas[k])
    assert m.count(vieja) == 1, vieja
    return rehacer(piezas[k], m.replace(vieja, nueva))


# ----------------------------------------------------------------------------- índices, por su contenido
i = {
    "intro": p("En la Universidad de los Andes hay trabajos previos"),
    "medidas": p("Con N errores, las medidas más usadas"), "ec13": ec(13), "rmse": p("El RMSE castiga más"),
    "spearman": p("Después salieron las columnas redundantes."), "ec25": ec(25), "spearman2": p("donde d", "Salieron 444"),
    "shap": p("Segundo paso: importancia frente a columnas de ruido"), "ec26": ec(26), "shap2": p("donde F es el conjunto"),
    "ec27": ec(27), "shap3": p("y se calculó en dos cortes"),
    "k": p("Tercer paso: cuántas columnas"), "ec28": ec(28), "k2": p("es decir, el número más pequeño de columnas"),
    "var": p("Variantes. Sobre la configuración elegida"), "ec29": ec(29), "var2": p("Para errores pequeños se parece"),
    "ec30": ec(30), "var3": p("donde ē"),
    "t15": uno(lambda x: x.startswith("<w:tbl") and texto(x).startswith("PronósticoRMSEMAEMAPE"), "la tabla 15"),
    "nota15": p("Nota: RMSE y MAE del error en logaritmo"), "cumplen": p("Los tres modelos cumplen el criterio en las dos"),
    "semana": p("Por último, con los precios conocidos hasta el 6 de octubre"),
    "anexoA": uno(lambda x: "Ttulo2" in x and texto(x).startswith("Anexo A."), "Anexo A"),
    "figA2": p("Figura A2."),
}
for a, b in [("medidas", "ec13"), ("ec13", "rmse"), ("spearman", "ec25"), ("ec25", "spearman2"), ("shap", "ec26"),
             ("ec26", "shap2"), ("shap2", "ec27"), ("ec27", "shap3"), ("k", "ec28"), ("ec28", "k2"), ("var", "ec29"),
             ("ec29", "var2"), ("var2", "ec30"), ("ec30", "var3"), ("t15", "nota15")]:
    assert i[b] == i[a] + 1, f"{b} no sigue a {a}"
assert i["figA2"] == len(piezas) - 2 and texto(piezas[-1]) == "", "el anexo A ya no es lo último del documento"
P = {k: piezas[v] for k, v in i.items()}
M = {k: marcado(P[k]) for k in P if P[k].startswith("<w:p")}

# ----------------------------------------------------------------------------- 1. MAPE
cambiar(P["intro"], quitar_frase(
    i["intro"], "La referencia sencilla es exigente: en 2022, repetir el precio de la misma hora del día anterior tuvo "
                "un error porcentual absoluto medio (MAPE) cercano a 11%.",
    "La referencia sencilla es exigente: con solo el precio y el calendario, XGBoost tuvo más error que ella en "
    "2020-2022 (sección 3.5)."))
cambiar(P["medidas"], rehacer(P["medidas"], "Con *N* errores, las dos medidas que se usan en este trabajo son la raíz "
                                            "del error cuadrático medio, RMSE, y el error absoluto medio, MAE (Hyndman "
                                            "y Athanasopoulos, 2021):"))
filas = re.findall(r"<w:tr[ >].*?</w:tr>", P["ec13"], re.S)
assert len(filas) == 3 and "<w:t>(15)</w:t>" in filas[2] and "MAPE" in "".join(re.findall(r"<m:t[^>]*>([^<]*)</m:t>", filas[2]))
cambiar(P["ec13"], P["ec13"].replace(filas[2], ""))
cambiar(P["rmse"], quitar_frase(
    i["rmse"], "El MAPE se reporta porque es la medida que usan los trabajos anteriores (sección 2.2), aunque se vuelve "
               "inestable cuando los precios son bajos (Hyndman y Athanasopoulos, 2021).",
    "No se usa el error porcentual absoluto medio, MAPE, porque se vuelve inestable cuando los precios son bajos "
    "(Hyndman y Athanasopoulos, 2021)."))

# tabla 15 sin la columna del MAPE; su ancho se reparte entre las demás
x = P["t15"]
grid = [int(w) for w in re.findall(r'<w:gridCol w:w="(\d+)"/>', x)]
assert len(grid) == 9
resto = grid[:3] + grid[4:]
anchos = [round(w * sum(grid) / sum(resto)) for w in resto]
anchos[0] += sum(grid) - sum(anchos)
nueva = x.replace(re.search(r"<w:tblGrid>.*?</w:tblGrid>", x).group(0),
                  "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in anchos) + "</w:tblGrid>")
for fila in re.findall(r"<w:tr[ >].*?</w:tr>", x, re.S):
    celdas = re.findall(r"<w:tc>.*?</w:tc>", fila, re.S)
    assert len(celdas) == 9 and "gridSpan" not in fila
    quedan = celdas[:3] + celdas[4:]
    quedan = [re.sub(r'<w:tcW w:w="\d+"', f'<w:tcW w:w="{w}"', c, count=1) for c, w in zip(quedan, anchos)]
    inicio, fin = fila.index(celdas[0]), fila.rindex(celdas[-1]) + len(celdas[-1])
    nueva = nueva.replace(fila, fila[:inicio] + "".join(quedan) + fila[fin:], 1)
assert "MAPE" not in texto(nueva) and texto(nueva).startswith("PronósticoRMSEMAEMejora (%)")
cambiar(x, nueva)
def letra_10(x):
    """La nota de una tabla va en 10 puntos, como estaba: se agrega el tamaño a cada run."""
    assert "vertAlign" not in x
    return x.replace("</w:rPr><w:t", '<w:sz w:val="20"/></w:rPr><w:t').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')


assert '<w:sz w:val="20"/>' in P["nota15"]
cambiar(P["nota15"], letra_10(quitar_frase(i["nota15"], "(ecuaciones 13 y 14) y MAPE con los precios en pesos "
                                                        "(ecuación 15),", "(ecuaciones 13 y 14),")))
cambiar(P["cumplen"], quitar_frase(i["cumplen"], "El orden es el mismo con el MAE y con el MAPE.",
                                   "El orden es el mismo con el MAE."))

# semana final, con el RMSE en logaritmo
with open(RAIZ / "resultados" / "comparacion" / "semana_final_tres_modelos.csv", encoding="utf-8") as f:
    final = {fila["modelo"]: float(fila["RMSE log"]) for fila in csv.DictReader(f)}
orden = sorted(final, key=final.get)
assert orden == ["XGBoost", "SARIMAX", "Ingenuo del día", "LSTM"], orden
r = {k: f"{v:.3f}".replace(".", ",") for k, v in final.items()}
cambiar(P["semana"], quitar_frase(
    i["semana"], "XGBoost tuvo el menor error, con un MAPE de 15,9%, seguido de SARIMAX, con 17,9%, y del ingenuo del "
                 "día, con 18,7%; la LSTM tuvo 23,2%.",
    f"XGBoost tuvo el menor error, con un RMSE en logaritmo de {r['XGBoost']}, seguido de SARIMAX, con "
    f"{r['SARIMAX']}, y del ingenuo del día, con {r['Ingenuo del día']}; la LSTM tuvo {r['LSTM']}."))

# ----------------------------------------------------------------------------- 2. sección 3.5, sin fórmulas
CUERPO_SPEARMAN = (
    "Después salieron las columnas redundantes. Cuando dos columnas se mueven casi igual, el árbol reparte entre "
    "ellas lo que aprende y ninguna aporta más que una sola. Se midió con la correlación de Spearman (1904), que "
    "compara el orden de las observaciones y no sus valores: mide si dos columnas suben y bajan juntas aunque la "
    "relación no sea lineal, y la afectan menos los picos (anexo B). De cada grupo de columnas con una correlación "
    "mayor que 0,95 entre sí quedó la que más se correlaciona con el objetivo del horizonte. Salieron 444, y quedaron "
    "unas 1.290.")
CUERPO_SHAP = (
    "*Segundo paso: importancia frente a columnas de ruido (2015-2019).* Para medir cuánto usa el modelo cada columna "
    "se usó el valor SHAP (Lundberg y Lee, 2017), que reparte el pronóstico de cada fila entre las columnas según "
    "cuánto cambia cuando una columna se agrega a las demás; para árboles se calcula de forma exacta y rápida "
    "(Lundberg et al., 2020). La importancia de una columna es el promedio del valor absoluto de su SHAP en todas las "
    "filas (anexo B).")
assert M["shap3"].startswith("y se calculó en dos cortes:")
CUERPO_SHAP2 = "S" + M["shap3"][3:]
assert M["k2"].count("Entre dos modelos que no se distinguen del azar") == 1
CUERPO_K = (
    M["k"][:M["k"].index("Se eligió con la regla")]
    + "Se eligió con la regla de un error estándar (Hastie et al., 2009): el número más pequeño de columnas cuyo "
      "error no supera al mínimo en más de un error estándar, calculado con Newey y West como en la sección 3.3 "
      "(anexo B). " + M["k2"][M["k2"].index("Entre dos modelos que no se distinguen del azar"):])
CUERPO_VAR = (
    "*Variantes.* Sobre la configuración elegida se probaron tres cambios, y una variante se adoptaba solo si bajaba "
    "el error en más de un error estándar. El primero fue la pérdida pseudo-Huber, que para errores pequeños se "
    "parece al error cuadrático y para errores grandes crece de forma lineal, como el valor absoluto, para que los "
    "picos pesen menos al entrenar. El segundo fue entrenar solo con los últimos tres años, por si los años viejos ya "
    "no se parecen al mercado actual. El tercero fue corregir el sesgo, que fue el problema que más se repitió al "
    "revisar los errores de *h* = 7 en 2021, con el error medio de los últimos 30 días cuyo objetivo ya se conoce. El "
    "anexo B presenta las dos fórmulas.")
cambiar(P["spearman"] + P["ec25"] + P["spearman2"], rehacer(P["spearman"], CUERPO_SPEARMAN))
cambiar(P["shap"] + P["ec26"] + P["shap2"] + P["ec27"] + P["shap3"],
        rehacer(P["shap"], CUERPO_SHAP) + rehacer(P["shap3"], CUERPO_SHAP2))
cambiar(P["k"] + P["ec28"] + P["k2"], rehacer(P["k"], CUERPO_K))
cambiar(P["var"] + P["ec29"] + P["var2"] + P["ec30"] + P["var3"], rehacer(P["var"], CUERPO_VAR))

# ----------------------------------------------------------------------------- 3. anexo B
def normal(t):
    return f"<w:p>{runs(t)}</w:p>"


titulo2 = re.search(r"<w:pPr>.*?</w:pPr>", P["anexoA"], re.S).group(0)
s2 = M["spearman2"]
fin_umbral = s2.index("Salieron 444")
k2 = M["k2"]
ANEXO = [
    f"<w:p>{titulo2}{runs('Anexo B. Medidas y criterios de XGBoost')}</w:p>",
    normal("Este anexo presenta las fórmulas con que se construyó XGBoost (sección 3.5): la correlación de Spearman, "
           "que quitó las columnas redundantes; el valor SHAP, que midió la importancia de cada columna; la regla de "
           "un error estándar, que eligió el número de columnas y los hiperparámetros, y dos de las variantes del "
           "entrenamiento que se probaron sin adoptarse, la pérdida pseudo-Huber y la corrección del sesgo."),
    normal("*Correlación de Spearman.* Para quitar las columnas redundantes se midió cuánto se mueven juntas dos "
           "columnas con la correlación de Spearman (1904),"),
    P["ec25"],
    normal(s2[:fin_umbral].rstrip()),
    normal("*Valor SHAP.* El valor SHAP (Lundberg y Lee, 2017) reparte el pronóstico de cada fila *x* entre las "
           "columnas, según cuánto cambia el pronóstico cuando una columna se agrega a las demás:"),
    P["ec26"],
    normal(M["shap2"].rstrip(",") + ":"),
    P["ec27"],
    normal("Con esta importancia se ordenaron las columnas en el segundo paso de la selección, y es la que muestra la "
           "figura 12."),
    normal("*Regla de un error estándar.* Para elegir el número de columnas, entre las primeras *k* del orden, se usó "
           "la regla de un error estándar (Hastie et al., 2009),"),
    P["ec28"],
    normal(k2[:k2.index("Entre dos modelos que no se distinguen del azar")].rstrip()
           + " La misma regla eligió los hiperparámetros en la validación con reentrenamiento mensual y decidió si se "
             "adoptaba cada variante (sección 3.5)."),
    normal("*Pérdida pseudo-Huber.* La primera variante cambió la pérdida del entrenamiento por la pseudo-Huber, para "
           "que los picos pesen menos:"),
    P["ec29"],
    normal(M["var2"][:M["var2"].index(" El segundo fue")]),
    normal("*Corrección del sesgo.* La tercera variante corrigió cada pronóstico con el error medio reciente:"),
    P["ec30"],
    normal(M["var3"]),
]
cambiar(P["figA2"], P["figA2"] + "".join(ANEXO))

# ----------------------------------------------------------------------------- 4. numeración de las ecuaciones
MAPA = {n: str(n) for n in range(1, 15)}
MAPA |= {n: str(n - 1) for n in range(16, 25)} | {25 + k: f"B{k + 1}" for k in range(6)}
MAPA |= {n: str(n - 7) for n in range(31, 35)}
REF = re.compile(r"(ecuaci(?:ón|ones) )(\(?\d+\)?(?:(?:,| y| a| o) \(?\d+\)?)*)")
PRINCIPIO = re.compile(r"ecuaci(?:ón|ones) \(?\d")

# cada referencia debe estar entera dentro de un mismo nodo de texto
for s, e in d.bloques():
    x = d.doc[s:e]
    if "txbxContent" in x:
        continue
    nodos = re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x)
    assert len(PRINCIPIO.findall("".join(nodos))) == sum(len(PRINCIPIO.findall(t)) for t in nodos), texto(x)[:120]


def renumerar_ref(m):
    def uno_(n):
        assert int(n.group(0)) in MAPA, f"referencia a una ecuación que ya no está: {m.group(0)}"
        return MAPA[int(n.group(0))]
    return m.group(1) + re.sub(r"\d+", uno_, m.group(2))


d.doc = re.sub(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)",
               lambda m: m.group(1) + REF.sub(renumerar_ref, m.group(2)) + m.group(3), d.doc)
partes, ultimo = [], 0
for s, e in d.bloques():
    x = d.doc[s:e]
    if x.startswith("<w:tbl") and "<m:oMath" in x:
        x = re.sub(r"<w:t>\((\d+)\)</w:t>", lambda m: f"<w:t>({MAPA[int(m.group(1))]})</w:t>", x)
    partes.append(d.doc[ultimo:s] + x)
    ultimo = e
d.doc = "".join(partes) + d.doc[ultimo:]

# ----------------------------------------------------------------------------- comprobaciones
etiquetas = [n for s, e in d.bloques() if d.doc[s:e].startswith("<w:tbl") and "<m:oMath" in d.doc[s:e]
             for n in re.findall(r"<w:t>\(([AB]?\d+)\)</w:t>", d.doc[s:e])]
cuerpo = [n for n in etiquetas if n.isdigit()]
assert cuerpo == [str(k) for k in range(1, 28)], cuerpo
assert [n for n in etiquetas if not n.isdigit()] == [f"A{k}" for k in range(1, 10)] + [f"B{k}" for k in range(1, 7)]
todo = texto(d.doc)
for m in REF.finditer(todo):
    for n in re.findall(r"[AB]?\d+", m.group(2)):
        assert n in etiquetas, f"referencia a la ecuación {n}, que no existe"
assert todo.count("MAPE") == 1 and "No se usa el error porcentual absoluto medio, MAPE" in todo
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
for x in ("(ecuación B3)", "de la ecuación (B4)", "ecuación (20)", "ecuación (27), en COP/kWh", "(ecuación 17)",
          "ecuaciones (18) y (19)", "ecuación 26) en la red", "ecuación (23) es el caso particular"):
    assert x in todo, x
d.guardar(SALIDA)
print("ok", SALIDA, "| ecuaciones 1 a 27, A1 a A9 y B1 a B6 | semana final:", r)
