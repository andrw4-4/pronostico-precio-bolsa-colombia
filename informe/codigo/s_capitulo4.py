"""Capítulo IV con dos secciones: los tres modelos frente a los dos ingenuos (4.1) y el valor para la toma de
decisiones (4.2). Sale la comparación con tesis anteriores y la comparación entre modelos queda dentro de la 4.1.
También se ajustan el objetivo 3 y las frases que remitían a las secciones viejas.

Uso: python s_capitulo4.py ENTRADA SALIDA
"""
import re
import sys

from docx_final import Docx


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


def cambiar(d, viejo, nuevo, veces=1):
    n = d.doc.count(viejo)
    assert n == veces, f"{viejo!r} aparece {n} veces"
    d.doc = d.doc.replace(viejo, nuevo)


d = Docx(sys.argv[1])
B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]


def indice(t):
    ii = [i for i, x in enumerate(T) if x.startswith(t)]
    assert len(ii) == 1, (t, ii)
    return ii[0]


# párrafos que salen: las entradas del índice y los títulos de 4.2 y 4.3, cada título con su párrafo vacío
toc42, toc43 = indice("4.2 Comparación entre modelos2"), indice("4.3 Comparación con tesis anteriores2")
titulos = [i for i, x in enumerate(T) if x in ("4.2 Comparación entre modelos", "4.3 Comparación con tesis anteriores")]
assert len(titulos) == 2 and titulos[1] == titulos[0] + 2, titulos
assert T[titulos[0] + 1] == "" and T[titulos[1] + 1] == "", "se esperaba un párrafo vacío tras cada título"
assert T[titulos[1] + 2] == "4.4 Valor para la toma de decisiones"
borrar = [toc42, toc43, titulos[0], titulos[0] + 1, titulos[1], titulos[1] + 1]
for i in sorted(borrar, reverse=True):
    s, e = B[i]
    d.doc = d.doc[:s] + d.doc[e:]

# los marcadores de los títulos que salieron no deben quedar citados en ningún lado
for marca in ("_Toc245724683", "_Toc245724684"):
    assert marca not in d.doc, marca

# títulos que quedan, en el cuerpo y en el índice
cambiar(d, "<w:t>4.1 Desempeño frente al ingenuo</w:t>", "<w:t>4.1 Desempeño frente a los ingenuos</w:t>", 2)
cambiar(d, "<w:t>4.4 Valor para la toma de decisiones</w:t>", "<w:t>4.2 Valor para la toma de decisiones</w:t>", 2)

# remisiones en el texto
d.cambiar_texto(" La sección 4.3 compara en detalle los resultados de este trabajo con los de esas tesis.", "")
d.cambiar_texto("con el de dos pronósticos ingenuos y el de tesis anteriores, tanto en error",
                "con el de dos pronósticos ingenuos, tanto en error")
d.cambiar_texto("La comparación entre modelos (sección 4.2)", "La comparación entre modelos (sección 4.1)")
d.cambiar_texto("Por eso la sección 4.4 evalúa", "Por eso la sección 4.2 evalúa")
d.cambiar_texto("La sección 4.2 vuelve sobre lo que esta diferencia", "La sección 4.1 vuelve sobre lo que esta diferencia")
# el capítulo se nombra con romanos, como en la sección 2.2
cambiar(d, "(capítulo 4)", "(capítulo IV)", 2)

# comprobaciones finales
todo = texto(d.doc)
# (sin contar cifras como 4.300)
assert not re.search(r"(?<!\d)4\.[34](?!\d)", todo), "quedó una remisión a 4.3 o 4.4"
assert "tesis anteriores" not in todo
T2 = [texto(d.doc[s:e]) for s, e in d.bloques()]
cap = T2[T2.index("IV. Resultados"):T2.index("V. Conclusiones")]
assert [x for x in cap if x] == ["IV. Resultados", "4.1 Desempeño frente a los ingenuos",
                                 "4.2 Valor para la toma de decisiones"], cap
d.guardar(sys.argv[2])
print("ok:", [x for x in cap if x])
