"""Capítulo propio para el mercado y los datos (comentarios del 26 de noviembre, punto 2.12) y fuente del supuesto
de dos días de atraso (punto 2.5).

Estructura anterior y nueva:

    II. Marco teórico            2.1 Mercado, 2.2 Antecedentes, 2.3 Modelos, 2.4 Evaluación
    III. Metodología             3.1 Datos, 3.2 Descarga y limpieza, 3.3 Diseño ... 3.8 Resumen
    IV. Resultados, V. Conclusiones

    II. Marco teórico            2.1 Antecedentes, 2.2 Modelos, 2.3 Evaluación
    III. El mercado eléctrico    3.1 Mercado, 3.2 Datos, 3.3 Descarga y limpieza
         y los datos
    IV. Metodología              4.1 Diseño ... 4.6 Resumen
    V. Resultados, VI. Conclusiones

La sección del mercado no tiene tablas ni ecuaciones, y sus figuras (4 y 5) quedan en el mismo orden respecto a
las demás, así que solo cambian los números de las secciones y de los capítulos. Cada número de sección se cambia
por otro del mismo largo, carácter por carácter, sin tocar el formato del texto.

El atraso de dos días se justifica con González Pérez y Urbano Buriticá (2022, p. 33), que pronosticaron el día D
con los datos disponibles hasta el día D-2 para ajustarse a la operación real del mercado.

Uso: python s_53_capitulo_mercado_datos.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx, reemplazar_en_bloque

SECCIONES = {"2.1": "3.1", "2.2": "2.1", "2.3": "2.2", "2.4": "2.3", "3.1": "3.2", "3.2": "3.3", "3.3": "4.1",
             "3.4": "4.2", "3.5": "4.3", "3.6": "4.4", "3.7": "4.5", "3.8": "4.6", "4.1": "5.1", "4.2": "5.2",
             "5.1": "6.1", "5.2": "6.2"}
_WT = re.compile(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)")
REF = re.compile(r"([Ss]ecci[oó]n(?:es)?\s+)(\d\.\d(?!\d)(?:(?:,\s*|\s+y\s+|\s+a\s+|\s+o\s+)\d\.\d(?!\d))*)")


def es_indice(x):
    return 'w:val="TDC' in x[:400]


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if not es_indice(d.doc[s:e])]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def mismo_largo(x, funcion):
    """Aplica `funcion` al texto de los <w:t> del bloque; el resultado debe tener el mismo largo, y cada carácter
    vuelve a su <w:t> original, así que el formato no cambia."""
    ms = list(_WT.finditer(x))
    plano = "".join(m.group(2) for m in ms)
    nuevo = funcion(plano)
    assert len(nuevo) == len(plano)
    if nuevo == plano:
        return x, 0
    partes, ultimo, base = [], 0, 0
    for m in ms:
        n = len(m.group(2))
        partes.append(x[ultimo:m.start()] + m.group(1) + nuevo[base:base + n] + m.group(3))
        base += n
        ultimo = m.end()
    return "".join(partes) + x[ultimo:], sum(a != b for a, b in zip(plano, nuevo))


def referencias(plano):
    return REF.sub(lambda m: m.group(1) + re.sub(r"\d\.\d", lambda n: SECCIONES.get(n.group(0), n.group(0)),
                                                 m.group(2)), plano)


def estilo(x):
    m = re.search(r'<w:pStyle w:val="([^"]+)"', x[:800])
    return m.group(1) if m else ""


d = Docx(sys.argv[1])
assert "III. El mercado eléctrico y los datos" not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- 2.5: de dónde sale el supuesto de dos días
cambiar(d, "El diseño supone dos días: el día en que se hace el pronóstico, que se llama aquí R, el último precio "
           "conocido es el del día t = R − 2.",
        "El diseño supone dos días, el mismo atraso que usaron González Pérez y Urbano Buriticá (2022), el trabajo de "
        "la Universidad de los Andes que sirvió de guía a este: para ajustar sus modelos a la operación real del "
        "mercado, pronosticaron cada día con los datos disponibles hasta dos días antes. Así, el día en que se hace el "
        "pronóstico, que se llama aquí R, el último precio conocido es el del día t = R − 2.")
cambiar(d, "El diseño supone dos, así que esos siete días",
        "El diseño supone dos, como González Pérez y Urbano Buriticá (2022), así que esos siete días")

# ---------------------------------------------------------------- mover las secciones
bl = [(s, e) for s, e in d.bloques()]


def inicio(texto, sty):
    k = [s for s, e in bl if estilo(d.doc[s:e]) == sty and Docx.texto(d.doc[s:e]).startswith(texto)
         and not es_indice(d.doc[s:e])]
    assert len(k) == 1, (texto, len(k))
    return k[0]


s21 = inicio("2.1 El mercado eléctrico y el precio de bolsa", "Ttulo2")
s22 = inicio("2.2 Antecedentes", "Ttulo2")
s_iii = inicio("III. Metodología", "Ttulo1")
s31 = inicio("3.1 Datos", "Ttulo2")
s33 = inicio("3.3 Diseño del pronóstico", "Ttulo2")
assert s21 < s22 < s_iii < s31 < s33
mercado, marco, cap_iii, datos = d.doc[s21:s22], d.doc[s22:s_iii], d.doc[s_iii:s31], d.doc[s31:s33]
for parte in (mercado, marco, cap_iii, datos):
    assert "<w:sectPr" not in parte
assert "SEQ Tabla" not in mercado and "<m:oMath" not in mercado and mercado.count("SEQ Figura") == 2
assert "SEQ Figura" not in marco
# el título del capítulo nuevo es una copia del de la metodología, sin sus marcadores del índice
titulo_iii = re.sub(r"<w:bookmark(Start|End)[^>]*/>", "", cap_iii)
titulo_iii = reemplazar_en_bloque(titulo_iii, "III. Metodología", "III. El mercado eléctrico y los datos")
cap_iv = reemplazar_en_bloque(cap_iii, "III. Metodología", "IV. Metodología")
d.doc = d.doc[:s21] + marco + titulo_iii + mercado + datos + cap_iv + d.doc[s33:]

# ---------------------------------------------------------------- números de capítulos, títulos y referencias
for viejo, nuevo in (("V. Conclusiones", "VI. Conclusiones"), ("IV. Resultados", "V. Resultados")):
    k = [(s, e) for s, e in d.bloques() if estilo(d.doc[s:e]) == "Ttulo1" and not es_indice(d.doc[s:e])
         and Docx.texto(d.doc[s:e]).startswith(viejo)]
    assert len(k) == 1, viejo
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]

cambios = 0
partes, ultimo = [], 0
for s, e in d.bloques():
    x = d.doc[s:e]
    if es_indice(x):
        continue
    if estilo(x) == "Ttulo2":
        t = Docx.texto(x)
        if t[:3] in SECCIONES and t[3] == " ":
            x, n = mismo_largo(x, lambda p: p.replace(t[:3], SECCIONES[t[:3]], 1))
            cambios += n
    x, n = mismo_largo(x, referencias)
    cambios += n
    partes.append(d.doc[ultimo:s] + x)
    ultimo = e
d.doc = "".join(partes) + d.doc[ultimo:]

# el capítulo IV de antes (resultados) es ahora el V
cambiar(d, "El capítulo IV sigue la forma de presentar", "El capítulo V sigue la forma de presentar")
cambiar(d, "la evaluación que cuenta es la de la prueba (capítulo IV)", "la evaluación que cuenta es la de la prueba "
                                                                       "(capítulo V)")
cambiar(d, "los del texto del capítulo IV, de dos", "los del texto del capítulo V, de dos")
k = [(s, e) for s, e, t in cuerpo(d) if "Capítulo IV" in t]
assert len(k) == 1
s, e = k[0]
x = d.doc[s:e]
assert x.count(">Capítulo IV<") >= 1
d.doc = d.doc[:s] + x.replace(">Capítulo IV<", ">Capítulo V<") + d.doc[e:]
d.renumerar()

# el índice crece una línea y su último párrafo, vacío, pasaba solo a la página siguiente, que quedaba en blanco
# porque la introducción empieza en página nueva; ese párrafo queda con una altura mínima
bl = d.bloques()
k = [j for j, (s, e) in enumerate(bl) if Docx.texto(d.doc[s:e]).startswith("I. Introducción")
     and estilo(d.doc[s:e]) == "Ttulo1"]
assert len(k) == 1
s, e = bl[k[0] - 1]
fin_indice = d.doc[s:e]
assert estilo(fin_indice) == "TDC1" and 'w:fldCharType="end"' in fin_indice and not Docx.texto(fin_indice).strip()
fin_indice = fin_indice.replace('<w:pPr><w:pStyle w:val="TDC1"/></w:pPr>',
                                '<w:pPr><w:pStyle w:val="TDC1"/><w:spacing w:before="0" w:after="0" w:line="20" '
                                'w:lineRule="exact"/><w:rPr><w:sz w:val="2"/></w:rPr></w:pPr>', 1)
assert 'w:line="20"' in fin_indice
d.doc = d.doc[:s] + fin_indice + d.doc[e:]

# ---------------------------------------------------------------- comprobaciones
titulos = [(estilo(d.doc[s:e]), Docx.texto(d.doc[s:e])) for s, e in d.bloques()
           if estilo(d.doc[s:e]) in ("Ttulo1", "Ttulo2") and not es_indice(d.doc[s:e])]
capitulos = [t for st, t in titulos if st == "Ttulo1" and re.match(r"[IVX]+\. ", t)]
assert capitulos == ["I. Introducción", "II. Marco teórico", "III. El mercado eléctrico y los datos",
                     "IV. Metodología", "V. Resultados", "VI. Conclusiones"], capitulos
numeros = [t.split(" ")[0] for st, t in titulos if st == "Ttulo2" and re.match(r"\d\.\d ", t)]
assert numeros == ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3", "4.1", "4.2", "4.3", "4.4", "4.5",
                   "4.6", "5.1", "5.2", "6.1", "6.2"], numeros
texto = " ".join(t for s, e, t in cuerpo(d))
existentes = set(numeros)
for m in REF.finditer(texto):
    for n in re.findall(r"\d\.\d", m.group(2)):
        assert n in existentes, (n, texto[m.start() - 60:m.end() + 20])
assert "Niño 3.4" in texto and "capítulo IV" not in texto and "Capítulo IV" not in texto
for x in ("los tres ciclos descritos en la sección 3.1", "Cada modelo llega a esa cantidad de una forma distinta "
          "(sección 2.2)", "González Pérez y Urbano Buriticá (2022), el trabajo de la Universidad de los Andes"):
    assert x in texto, x
print("caracteres cambiados:", cambios)
d.guardar(sys.argv[2])
print("listo")
