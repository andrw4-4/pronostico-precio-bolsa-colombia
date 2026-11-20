"""Pasa las pruebas estadísticas de SARIMAX al anexo A, quita las figuras y tablas que repetían lo mismo y deja
colores más sencillos.

1. Anexo A. Las pruebas OCSB, KPSS y el AICc, con la tabla de órdenes por hora; el preblanqueo y su figura; la
   prueba t, y la prueba de Ljung-Box con la figura de los residuos. En la sección 3.4 queda un párrafo corto de
   cada una, con el resultado y la remisión al anexo. Las ecuaciones del anexo van de (A1) a (A9), y su tabla y sus
   figuras son A1 y A2.
2. Repetidas. La figura 4 queda solo con el cambio diario del logaritmo, porque el precio en pesos ya está en la
   figura 2. Sale la figura de la validación de SARIMAX, que repetía la tabla de la validación, y sale la tabla de
   variables por paso, que repetía la figura de las etapas y el texto.
3. Colores. Las gráficas cambian de imagen, con la paleta sin violeta ni amarillo de estilo_graficas.py; en los
   diagramas de Word solo cambian los rellenos, para no perder lo que se haya editado en Word.
4. Numeración. Se renumeran las figuras, tablas y ecuaciones del cuerpo, y todas sus referencias en el texto.
Uso: python s_anexo_sarimax.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

from docx_final import Docx, esc, runs

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"

d = Docx(ENTRADA)
assert "Anexo A. " not in d.doc, "el anexo A ya está"

# ----------------------------------------------------------------------------- 1. gráficas con los colores nuevos
GRAFICAS = {"Figura 2001": "f01_precio_embalses_nino.png", "Figura 2013": "f13_precio_y_cambio.png",
            "Figura 2003": "f03_diseno_pronostico.png", "Figura 2015": "f15_ciclos_precio.png",
            "Figura 2016": "f16_autocorrelacion.png", "Figura 2018": "f18_sarimax_preblanqueo.png",
            "Figura 2020": "f20_sarimax_residuos.png", "Figura 2022": "f22_xgboost_columnas.png",
            "Figura 2023": "f23_xgboost_importancia.png", "Figura 2026": "f26_lstm_importancia.png"}
for dibujo, png in GRAFICAS.items():
    d.cambiar_imagen(d.media_de(dibujo), FIG / png)

# rellenos de los diagramas: el amarillo y el violeta pasan a verde, rojo claro o un neutro suave
RELLENOS = {"Diagrama 3012": {"FAE8BF": "D9ECD9", "F6D080": "B8DCB8", "B2DAB2": "94CB94", "E7E5F9": "EEEDE8",
                              "D0CAF3": "F9D7D7"},
            "Diagrama 3014": {"F9DEA6": "EEEDE8"},
            "Diagrama 3025": {"F9DEA6": "EEEDE8"}}
for dibujo, cambios in RELLENOS.items():
    (s, e), = [(s, e) for s, e in d.bloques() if f'name="{dibujo}"' in d.doc[s:e]]
    x = d.doc[s:e]
    for viejo in cambios:
        assert re.search(viejo, x, re.I), f"{dibujo} no tiene el color {viejo}"
    x = re.sub("|".join(cambios), lambda m: cambios[m.group(0).upper()], x, flags=re.I)
    d.doc = d.doc[:s] + x + d.doc[e:]

# ----------------------------------------------------------------------------- 2. bloques del cuerpo
B = d.bloques()
piezas = [d.doc[s:e] for s, e in B]
huecos = [d.doc[B[i][1]:B[i + 1][0]] for i in range(len(B) - 1)]


def texto(x):
    return d.texto(x) if "txbxContent" not in x else ""


def uno(condicion, que):
    i = [k for k, x in enumerate(piezas) if condicion(x)]
    assert len(i) == 1, f"hay {len(i)} bloques con {que}"
    return i[0]


def p(inicio, contiene=""):
    """El párrafo de primer nivel que empieza con `inicio` (y que contiene `contiene`)."""
    return uno(lambda x: x.startswith("<w:p") and texto(x).startswith(inicio) and contiene in texto(x), inicio)


def ec(n):
    """La tabla de la ecuación con el número (n)."""
    return uno(lambda x: x.startswith("<w:tbl") and "<m:oMath" in x and f"<w:t>({n})</w:t>" in x, f"la ecuación ({n})")


def dibujo(nombre):
    return uno(lambda x: f'name="{nombre}"' in x, nombre)


def tabla(inicio):
    return uno(lambda x: x.startswith("<w:tbl") and texto(x).startswith(inicio), inicio)


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
    """El mismo párrafo, con su formato de párrafo, pero con el texto `nuevo`. Sin los identificadores de Word
    (w14:paraId), que no pueden repetirse."""
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", x, re.S)
    return "<w:p>" + (ppr.group(0) if ppr else "") + runs(nuevo) + "</w:p>"


def leyenda_nueva(x, nuevo):
    """La misma leyenda numerada (con su campo SEQ), con otro texto después de 'Figura N. '."""
    m = re.match(r'.*?<w:fldChar w:fldCharType="end"/></w:r><w:r>(?:<w:rPr>.*?</w:rPr>)?'
                 r'<w:t xml:space="preserve">\. </w:t></w:r>', x, re.S)
    assert m, "la leyenda no tiene la forma esperada"
    return m.group(0) + runs(nuevo) + "</w:p>"


def leyenda_anexo(x, etiqueta, nuevo):
    """Leyenda del anexo: 'Figura A1.' con el número escrito, sin campo SEQ, para no mover la numeración del
    cuerpo."""
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", x, re.S).group(0)
    return (f'<w:p>{ppr}<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">{esc(etiqueta)}. </w:t></w:r>'
            f"{runs(nuevo)}</w:p>")


# índices, buscados por su contenido
i = {
    "titulo": uno(lambda x: "Ttulo2" in x and texto(x) == "3.4 SARIMAX", "3.4 SARIMAX"),
    "ordenes": p("Órdenes de cada hora."), "ocsb": p("Primero, la prueba OCSB"), "ec23": ec(23),
    "ocsb2": p("donde y", "es el logaritmo del precio de la hora"), "kpss": p("Después, la prueba KPSS"), "ec24": ec(24), "kpss2": p("donde T es el número"),
    "aicc": p("Por último, el criterio AICc"), "ec25": ec(25), "aicc2": p("donde L", "es la verosimilitud del modelo"),
    "resultado": p("Las dos pruebas dieron"), "t5": p("Tabla 5."), "t5b": tabla("OrdenHoras"),
    "t5c": None, "candidatas": p("Variables candidatas."), "rezago": p("Como se pronostica hasta nueve días"),
    "pre": p("Primer filtro: preblanqueo."), "ec26": ec(26), "pre2": p("donde los polinomios son los de"),
    "ec27": ec(27), "pre3": p("Los residuos u"), "ec28": ec(28), "pre4": p("mide si la variable de nueve días"),
    "ec29": ec(29), "pre5": p("donde z es el cuantil"), "pre6": p("La figura 10a muestra"),
    "f10": dibujo("Figura 2018"), "f10c": p("Figura 10."),
    "aicc_sel": p("Segundo filtro: selección hacia adelante"), "t": p("Tercer filtro: prueba t."), "ec30": ec(30),
    "t2": p("donde ee("), "t6texto": p("La tabla 6 resume"), "t6": p("Tabla 6."), "t6b": tabla("PasoDatosSalen"),
    "t6c": None, "val": p("Validación. En 2020-2022"), "t7": p("Tabla 7."), "val2": p("Dar a cada hora su propio"),
    "f11": dibujo("Figura 2019"), "f11c": p("Figura 11."), "final": p("Modelo final. El modelo final es SARIMAX"), "ec31": ec(31),
    "final2": p("donde F", "vale 1 si el día"), "res": p("Diagnóstico de los residuos."), "ec33": ec(33), "res2": p("Bajo la hipótesis nula de que los residuos"),
    "f12": dibujo("Figura 2020"), "f12c": p("Figura 12."), "mensual": p("En la validación y en la prueba, los coeficientes"),
    "xgb": uno(lambda x: "Ttulo2" in x and texto(x) == "3.5 XGBoost", "3.5 XGBoost"),
    "anexos": uno(lambda x: "Ttulo1" in x and texto(x) == "Anexos", "Anexos"),
}
# las fuentes de las tablas 5 y 6 van justo después de cada tabla
i["t5c"], i["t6c"] = i["t5b"] + 1, i["t6b"] + 1
assert texto(piezas[i["t5c"]]).startswith("Fuente") and texto(piezas[i["t6c"]]).startswith("Fuente")
# ningún hueco entre bloques de la parte que se reordena
assert all(h == "" for h in huecos[i["titulo"]:i["xgb"]]), "hay algo entre los bloques de la sección 3.4"
# el orden encontrado es el esperado
orden = ["titulo", "ordenes", "ocsb", "ec23", "ocsb2", "kpss", "ec24", "kpss2", "aicc", "ec25", "aicc2", "resultado",
         "t5", "t5b", "t5c", "candidatas", "rezago", "pre", "ec26", "pre2", "ec27", "pre3", "ec28", "pre4", "ec29", "pre5",
         "pre6", "f10", "f10c", "aicc_sel", "t", "ec30", "t2", "t6texto", "t6", "t6b", "t6c", "val", "t7"]
assert [i[k] for k in orden] == sorted(i[k] for k in orden), "el orden de la sección 3.4 cambió"
P = {k: piezas[v] for k, v in i.items()}
M = {k: marcado(P[k]) for k in ("pre", "t", "t2", "ordenes", "val2", "final2")}

# ----------------------------------------------------------------------------- 3. la sección 3.4, más corta
CUERPO = {
    "ordenes": "*Órdenes de cada hora.* Con los datos de 2015-2019, la función auto.arima eligió el orden de cada hora "
               "en tres pasos (Hyndman y Khandakar, 2008): la prueba OCSB (Osborn et al., 1988) decide si hace falta "
               "una diferencia estacional, *D*; la prueba KPSS (Kwiatkowski et al., 1992) decide *d*, y el criterio "
               "AICc (Hurvich y Tsai, 1989) elige *p*, *q*, *P* y *Q* entre los modelos con hasta 5 rezagos en la "
               "parte regular y hasta 2 en la estacional. El anexo A presenta las dos pruebas y el criterio con sus "
               "ecuaciones.",
    "pre": "*Primer filtro: preblanqueo.* El precio y muchas variables del sistema tienen ciclos semanales y anuales "
           "y cambian lentamente. Dos series así pueden parecer correlacionadas aunque una no ayude a pronosticar la "
           "otra, solo porque las dos suben y bajan con la misma inercia. El preblanqueo quita esa parte común antes "
           "de medir la relación (Box et al., 2015): el modelo de cada hora, ya estimado, filtra el precio y la "
           "variable, y se mide la correlación entre lo que queda de los dos, con la variable de nueve días antes. "
           "Una variable pasa si esa correlación es significativa al 5% en al menos 12 de las 24 horas, con la "
           "corrección de Bonferroni (Dunn, 1961) porque se prueban 122 variables a la vez. Sin el filtro, la "
           "correlación media de las 122 variables con el precio, en valor absoluto, es de 0,34; con el filtro baja "
           "a 0,025, así que casi toda la relación aparente venía de la inercia común. Solo pasó una variable: la "
           "holgura de la curva de oferta, que es la capacidad ofertada menos la demanda, como fracción de la "
           "demanda, significativa en exactamente 12 horas. El anexo A detalla el filtro, el umbral y el resultado "
           "de cada variable (figura A1).",
    "t": "*Tercer filtro: prueba t.* En el modelo de cada hora con la holgura, una prueba *t* revisa si su "
         "coeficiente es distinto de cero (anexo A). La variable sale si no tiene *p* < 0,05 en al menos 12 horas. "
         "La holgura fue significativa en 17 de las 24, con un *p* mediano de 0,006, así que se mantuvo.",
    "t6texto": "Dentro de 2015-2019, la holgura pasó los tres filtros (figura 9). Pero los tres miden el ajuste en "
               "los mismos datos con que se estima el modelo, y lo que importa es si mejora el pronóstico en años "
               "que el modelo no vio. Eso lo decide la validación.",
    "res": "*Diagnóstico de los residuos.* Si el modelo recoge toda la estructura del precio, sus residuos no "
           "deberían tener autocorrelación. Con los residuos de 2015-2019, la prueba de Ljung y Box (1978) con 14 "
           "rezagos no rechazó al 5% que fueran ruido blanco en 17 de las 24 horas. La autocorrelación que queda "
           "está en los rezagos 21 y 28, de 0,088 y 0,075: las dos medias móviles semanales recogen la relación con "
           "el mismo día de una y dos semanas antes, pero no la de tres y cuatro semanas. Es lo que se cede a cambio "
           "de un modelo más simple que pronostica igual. La prueba y el resultado de cada hora están en el anexo A "
           "(figura A2).",
}
nuevo = {k: rehacer(P[k], v) for k, v in CUERPO.items()}
# la sección, de su título al de XGBoost, con los párrafos cortos en lugar de las pruebas
cuerpo = piezas[i["titulo"]:i["ordenes"]] + [nuevo["ordenes"], P["resultado"], P["candidatas"], P["rezago"],
                                             nuevo["pre"], P["aicc_sel"], nuevo["t"], nuevo["t6texto"]]
# sin la figura de la validación, que repetía la tabla
for k in ("val2", "final2"):
    assert M[k].count(" (figura 11)") == 1
    nuevo[k] = rehacer(P[k], M[k].replace(" (figura 11)", ""))
cuerpo += piezas[i["val"]:i["val2"]] + [nuevo["val2"], P["final"], P["ec31"], nuevo["final2"], nuevo["res"],
                                        P["mensual"]]
assert i["val2"] == i["t7"] + 3 and i["ec31"] == i["final"] + 1 and i["final2"] == i["ec31"] + 1
assert i["res"] == i["final2"] + 1
assert i["f11c"] == i["f11"] + 1 and i["final"] == i["f11c"] + 1 and i["mensual"] == i["f12c"] + 1
assert i["xgb"] == i["mensual"] + 1

# ----------------------------------------------------------------------------- 4. el anexo A
titulo2 = re.search(r"<w:pPr>.*?</w:pPr>", P["titulo"], re.S).group(0)
normal = '<w:p>{}</w:p>'
anexo = [
    f"<w:p>{titulo2}{runs('Anexo A. Pruebas estadísticas de SARIMAX')}</w:p>",
    normal.format(runs("Este anexo presenta las pruebas y los criterios estadísticos con que se construyó SARIMAX "
                       "(sección 3.4): las pruebas que eligen el orden de cada hora, el preblanqueo de las variables "
                       "candidatas, la prueba *t* del coeficiente de la holgura y la prueba de Ljung-Box de los "
                       "residuos.")),
    rehacer(P["ordenes"], M["ordenes"]),
    P["ocsb"], P["ec23"], P["ocsb2"], P["kpss"], P["ec24"], P["kpss2"], P["aicc"], P["ec25"], P["aicc2"],
    normal.format(runs("Con los datos de 2015-2019, las dos pruebas dieron *D* = 0 y *d* = 1 en las 24 horas, y el "
                       "AICc eligió doce órdenes distintos (tabla A1).")),
    leyenda_anexo(P["t5"], "Tabla A1", "Órdenes elegidos por el AICc en cada hora, 2015-2019."),
    P["t5b"], P["t5c"],
    rehacer(P["pre"], "*Preblanqueo.* " + M["pre"][M["pre"].index("Para cada hora"):].replace("tabla 5", "tabla A1")),
    P["ec26"], P["pre2"], P["ec27"], P["pre3"], P["ec28"], P["pre4"], P["ec29"], P["pre5"], P["pre6"], P["f10"],
    leyenda_anexo(P["f10c"], "Figura A1",
                  "Preblanqueo de las 122 variables candidatas, 2015-2019. a) Correlación de cada variable, con nueve "
                  "días de rezago, con el logaritmo del precio, en valor absoluto y promediada sobre las 24 horas, "
                  "antes y después del filtro; la línea roja es la holgura de la oferta. b) Número de horas en que la "
                  "correlación preblanqueada supera el umbral de la ecuación (A7), para las 16 variables que lo "
                  "superan en alguna hora. Fuente: elaboración propia con datos de XM (2026)."),
    rehacer(P["t"], "*Prueba t.* " + M["t"][M["t"].index("En el modelo"):]),
    P["ec30"],
    rehacer(P["t2"], M["t2"][:M["t2"].index("deberse al azar.") + len("deberse al azar.")]),
    P["res"], P["ec33"], P["res2"], P["f12"],
    leyenda_anexo(P["f12c"], "Figura A2",
                  "Diagnóstico de los residuos del modelo final, 2015-2019. a) Valor *p* de la prueba de Ljung-Box "
                  "con 14 rezagos en cada hora; las barras rojas son las horas en que se rechaza al 5%. b) "
                  "Autocorrelación de los residuos, promedio de las 24 horas; los rezagos múltiplos de siete van en un "
                  "verde más intenso, los que se salen de la banda van en rojo y la franja sombreada es la banda de "
                  "95%. Fuente: elaboración propia con datos de XM (2026)."),
]
assert "Tercer filtro" not in M["t"][M["t"].index("En el modelo"):]

# ----------------------------------------------------------------------------- 5. el documento nuevo
def unir(a, b):
    return "".join(piezas[k] + huecos[k] for k in range(a, b))


antes = d.doc[:B[0][0]] + unir(0, i["titulo"])
medio = "".join(cuerpo) + unir(i["xgb"], i["anexos"] + 1)
despues = "".join(anexo) + unir(i["anexos"] + 1, len(B) - 1) + piezas[-1] + d.doc[B[-1][1]:]
d.doc = antes + medio + despues

# sección 2.1: el precio en pesos ya está en la figura 2; la figura 4 queda solo con el cambio
(s, e), = [(s, e) for s, e in d.bloques() if d.texto(d.doc[s:e]).startswith("Dos consecuencias importan")]
x = d.doc[s:e]
viejo = ("La figura 4 lo muestra: en pesos, los picos de 2015-2016 y 2023-2024 dominan la serie, mientras que el "
         "cambio diario del logaritmo oscila alrededor de cero en toda la muestra, aunque con más variabilidad desde "
         "2023 (una desviación estándar de 0,19 en 2023-2025, frente a 0,13 en 2015-2019).")
nuevo81 = ("En pesos, los picos de 2015-2016 y 2023-2024 dominan la serie (figura 2), mientras que el cambio diario "
           "del logaritmo oscila alrededor de cero en toda la muestra, aunque con más variabilidad desde 2023 "
           "(figura 4): su desviación estándar es de 0,19 en 2023-2025, frente a 0,13 en 2015-2019.")
assert marcado(x).count(viejo) == 1
d.doc = d.doc[:s] + rehacer(x, marcado(x).replace(viejo, nuevo81)) + d.doc[e:]

LEYENDAS = {
    "Figura 4.": "Cambio diario del logaritmo del precio de bolsa promedio del día, del 1 de enero de 2015 al 6 de "
                 "octubre de 2026. Las franjas de color marcan los periodos de selección, validación y prueba "
                 "(sección 3.3). Fuente: elaboración propia con datos de XM (2026).",
    "Figura 8.": "Autocorrelación y autocorrelación parcial del cambio diario del logaritmo del precio, promedio de "
                 "las 24 horas, 2015-2019. Los rezagos múltiplos de siete van en rojo intenso; la franja sombreada es "
                 "la banda de 95% de una serie sin autocorrelación. Fuente: elaboración propia con datos de XM (2026).",
}
for inicio, texto_nuevo in LEYENDAS.items():
    (s, e), = [(s, e) for s, e in d.bloques() if d.texto(d.doc[s:e]).startswith(inicio)]
    d.doc = d.doc[:s] + leyenda_nueva(d.doc[s:e], texto_nuevo) + d.doc[e:]

# ----------------------------------------------------------------------------- 6. numeración
FIGURAS = {10: "A1", 12: "A2", 13: "10", 14: "11", 15: "12", 16: "13", 17: "14", 18: "15"}
TABLAS = {5: "A1", 7: "5", 8: "6", 9: "7", 10: "8", 11: "9", 12: "10", 13: "11", 14: "12", 15: "13"}
ECUACIONES = {23: "A1", 24: "A2", 25: "A3", 26: "A4", 27: "A5", 28: "A6", 29: "A7", 30: "A8", 31: "23", 32: "24",
              33: "A9", 34: "25", 35: "26", 36: "27", 37: "28", 38: "29", 39: "30", 40: "31", 41: "32", 42: "33"}
REF = re.compile(r"\b(figuras?|tablas?)( )(\d+)|\b(ecuaci(?:ón|ones))( \(?)(\d+)", re.I)
QUITADAS = {"figura": {11}, "tabla": {6}}


def nueva_ref(m):
    if m.group(1):
        n, tabla_ = int(m.group(3)), m.group(1).lower().startswith("tabla")
        assert n not in QUITADAS["tabla" if tabla_ else "figura"], f"queda una referencia a {m.group(0)}"
        return m.group(1) + m.group(2) + (TABLAS if tabla_ else FIGURAS).get(n, str(n))
    return m.group(4) + m.group(5) + ECUACIONES.get(int(m.group(6)), m.group(6))


# las referencias deben estar enteras dentro de un mismo run, si no, no se pueden cambiar con seguridad
for s, e in d.bloques():
    x = d.doc[s:e]
    if "txbxContent" in x:
        continue
    t = d.texto(x)
    if "SEQ Figura" in x or "SEQ Tabla" in x:   # la etiqueta 'Figura N.' es un campo, no una referencia
        t = t[t.index(". ") + 2:]
    en_texto = len(REF.findall(t))
    en_runs = sum(len(REF.findall(t)) for t in re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))
    assert en_texto == en_runs, f"una referencia está partida entre runs: {d.texto(x)[:120]}"
d.doc = re.sub(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)", lambda m: m.group(1) + REF.sub(nueva_ref, m.group(2)) + m.group(3),
               d.doc)
# el número de cada ecuación, a la derecha de su tabla
partes = []
ultimo = 0
for s, e in d.bloques():
    x = d.doc[s:e]
    if x.startswith("<w:tbl") and "<m:oMath" in x:
        x = re.sub(r"<w:t>\((\d+)\)</w:t>", lambda m: f"<w:t>({ECUACIONES.get(int(m.group(1)), m.group(1))})</w:t>", x)
    partes.append(d.doc[ultimo:s] + x)
    ultimo = e
d.doc = "".join(partes) + d.doc[ultimo:]
d.renumerar()

# comprobaciones: números seguidos en el cuerpo y en el anexo, y ninguna referencia a algo que no existe
etiquetas = [n for s, e in d.bloques() if d.doc[s:e].startswith("<w:tbl") and "<m:oMath" in d.doc[s:e]
             for n in re.findall(r"<w:t>\((A?\d+)\)</w:t>", d.doc[s:e])]
eqs = [int(n) for n in etiquetas if not n.startswith("A")]
assert eqs == list(range(1, 34)), eqs
assert [n for n in etiquetas if n.startswith("A")] == [f"A{k}" for k in range(1, 10)], etiquetas
nfig, ntab = d.doc.count("SEQ Figura "), d.doc.count("SEQ Tabla ")
assert (nfig, ntab) == (15, 13), (nfig, ntab)
for tipo, n in (("figura", nfig), ("tabla", ntab)):
    refs = {int(x) for x in re.findall(rf"\b{tipo}s? (\d+)", d.texto(d.doc), re.I)}
    assert refs <= set(range(1, n + 1)), (tipo, sorted(refs))
# la imagen de la figura que salió ya no la usa nadie: se quita del paquete
rels = d.archivos["word/_rels/document.xml.rels"].decode("utf8")
for m in re.finditer(r'<Relationship Id="([^"]+)" Type="[^"]+/image" Target="media/([^"]+)"/>', rels):
    if f'"{m.group(1)}"' not in d.doc:
        rels = rels.replace(m.group(0), "")
        d.archivos.pop("word/media/" + m.group(2))
        print("imagen sin uso, quitada:", m.group(2))
d.archivos["word/_rels/document.xml.rels"] = rels.encode("utf8")
d.guardar(SALIDA)
print("ok", SALIDA, f"{nfig} figuras y {ntab} tablas en el cuerpo, ecuaciones 1 a {max(eqs)} y A1 a A9")
