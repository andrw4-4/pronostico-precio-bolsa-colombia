"""Agrega los resultados de la prueba con el error en pesos, como complemento del criterio en logaritmo:
1. Sección 4.1: al párrafo de pesos, una frase con la prueba de Diebold-Mariano sobre el error en pesos.
2. Anexo C, después del anexo B: la tabla C1, que repite la tabla 15 con el error en COP/kWh, y lo que cambia por
   años y entre modelos.
3. Sección 5.2: la limitación de pesos dice también qué mejoras son significativas.
Las cifras salen de informe/figuras/datos_resultados_pesos*.csv, que escribe fig_pesos.py con los pronósticos
guardados; no se entrena ni se repite ninguna prueba. La etiqueta C1 va escrita, sin campo SEQ, como las de los
anexos A y B, para no mover la numeración del cuerpo.
Uso: python s_pesos_anexo_c.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, esc, runs, tabla

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
FIG = Path(__file__).resolve().parents[1] / "figuras"
R = pd.read_csv(FIG / "datos_resultados_pesos.csv", dtype={"caso": str}).set_index(["caso", "pronostico"])
PARES = pd.read_csv(FIG / "datos_resultados_pesos_pares.csv", dtype={"caso": str})
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]
NBSP = chr(0xA0)                # espacio que no se corta, para que "p = 0,508" no quede partido entre dos líneas


def num(x, dec=1):
    s = f"{abs(x):.{dec}f}".replace(".", ",")
    return ("−" if x < 0 and float(s.replace(",", ".")) > 0 else "") + s


def pval(p):
    return "< 0,001" if p < 0.001 else num(p, 3)


def p_de(caso, mo):
    return float(R.loc[(caso, mo), "p"])


# lo que dicen los textos, comprobado contra los datos
sig = {c: [mo for mo in MODELOS if p_de(c, mo) < 0.05] for c in ["2023-2025", "2026", "2023", "2024", "2025"]}
assert sig["2023-2025"] == ["SARIMAX"] and sig["2026"] == MODELOS
assert sig["2023"] == [] and sig["2024"] == [] and sig["2025"] == MODELOS
assert max(p_de("2025", mo) for mo in MODELOS) < 0.01
assert (PARES[PARES["caso"].isin(["2023-2025", "2026"])]["p"] > 0.05).all()
assert round(-R.loc[("2023-2025", "SARIMAX"), "sesgo pesos"]) == 15
assert round(-R.loc[("2023-2025", "XGBoost"), "sesgo pesos"]) == 46

FRASE_41 = (f" Con la prueba de Diebold-Mariano sobre el error en pesos, en 2023-2025 solo la mejora de SARIMAX es "
            f"significativa (*p* = {pval(p_de('2023-2025', 'SARIMAX'))}), no las de XGBoost ni la LSTM "
            f"(*p* = {pval(p_de('2023-2025', 'XGBoost'))} y *p* = {pval(p_de('2023-2025', 'LSTM'))}); en 2026 lo "
            f"son las tres (anexo C).").replace("*p* = ", f"*p*{NBSP}={NBSP}")

ANEXO_TEXTO = [
    "La tabla C1 repite la comparación de la tabla 15 con el error medido en pesos: la diferencia entre el precio "
    "pronosticado con la ecuación (21) y el precio real, en COP/kWh. No es parte del criterio de la sección 3.3, "
    "que se fijó en logaritmo antes de abrir la prueba; es un complemento de la sección 4.1.",
    "En pesos, los días de precios altos pesan mucho más que en logaritmo, porque el error se eleva al cuadrado en "
    "COP/kWh, y la diferencia de pérdidas entre dos pronósticos varía más de un día a otro. Por eso la prueba de "
    "Diebold-Mariano distingue menos. En 2023-2025 solo la mejora de SARIMAX es significativa; en 2026 lo son las "
    "tres. Por años, ningún modelo tiene una mejora significativa en 2023 ni en 2024, y los tres la tienen en 2025 "
    f"(*p*{NBSP}<{NBSP}0,01). Entre modelos, ninguna diferencia es significativa en las dos pruebas.",
]


def filas_tabla():
    filas = [["Pronóstico", "RMSE", "MAE", "Sesgo", "Mejora (%)", "*p*"]]
    for caso, titulo in [("2023-2025", "*Prueba 2023-2025*"), ("2026", "*Prueba 2026*")]:
        filas.append([titulo, "", "", "", "", ""])
        for mo in ["Ingenuo del día", "Ingenuo semanal"] + MODELOS:
            r = R.loc[(caso, mo)]
            modelo = mo in MODELOS
            filas.append([mo, num(r["RMSE pesos"]), num(r["MAE pesos"]), num(r["sesgo pesos"]),
                          num(r["mejora"]) if modelo else "—", pval(r["p"]) if modelo else "—"])
    return filas


NOTA = ("Nota: RMSE, MAE y sesgo del error en pesos, en COP/kWh, en *h* = 3 a 9. El sesgo es el promedio del precio "
        "pronosticado menos el real; es negativo cuando el pronóstico queda por debajo. La mejora es la reducción del "
        "RMSE en pesos frente al ingenuo del día y *p* es el valor de la prueba de Diebold-Mariano con el error "
        "cuadrático en pesos, con la misma varianza de la sección 3.3. Fuente: elaboración propia con datos de XM "
        "(2026).")


def texto(x):
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", x))


def nota(t):
    rpr = '<w:sz w:val="20"/>'
    r = runs(t).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace("<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{r}</w:p>'


d = Docx(ENTRADA)
assert "Anexo C." not in d.doc, "el anexo C ya está"

# 1. sección 4.1 y 2. sección 5.2 (cada texto viejo está una vez y en un solo run)
viejo = "y 8,8%, 6,4% y 6,8% en 2026. Hay dos razones."
assert d.doc.count(esc(viejo)) == 1
s = d.doc.index(esc(viejo))
a, b = d.doc.rindex("<w:r>", 0, s), d.doc.index("</w:r>", s) + len("</w:r>")
run = d.doc[a:b]
# un run de texto normal, sin formato propio, que contiene la frase completa
assert run.startswith("<w:r><w:t") and run.count("<w:t") == 1 and viejo in texto(run)
corte = run.index(esc("Hay dos razones."))
d.doc = d.doc[:a] + run[:corte].rstrip() + "</w:t></w:r>" + runs(FRASE_41) + \
    '<w:r><w:t xml:space="preserve"> ' + run[corte:] + d.doc[b:]
d.cambiar_texto("En pesos, las mejoras son menores que en logaritmo y los pronósticos quedan por debajo del precio "
                "real (sección 4.1).",
                "En pesos, las mejoras son menores que en logaritmo, en 2023-2025 solo la de SARIMAX es significativa y "
                "los pronósticos quedan por debajo del precio real (sección 4.1 y anexo C).")

# 3. anexo C, después del último párrafo del anexo B
B = d.bloques()
T = [texto(d.doc[s:e]) for s, e in B]
i_b = [k for k, t in enumerate(T) if t.startswith("Anexo B.") and "Ttulo2" in d.doc[B[k][0]:B[k][1]]]
assert len(i_b) == 1
ultimo = max(k for k, t in enumerate(T) if t.strip())
assert T[ultimo].startswith("donde ") and ultimo > i_b[0]
titulo2 = re.search(r"<w:pPr>.*?</w:pPr>", d.doc[B[i_b[0]][0]:B[i_b[0]][1]], re.S).group(0)
i_a1 = [k for k, t in enumerate(T) if t.startswith("Tabla A1. ")]
ppr_leyenda = re.search(r"<w:pPr>.*?</w:pPr>", d.doc[B[i_a1[0]][0]:B[i_a1[0]][1]], re.S).group(0)
assert "Descripcin" in ppr_leyenda
ANEXO = (f"<w:p>{titulo2}{runs('Anexo C. Resultados de la prueba en pesos')}</w:p>"
         + "".join(f"<w:p>{runs(t)}</w:p>" for t in ANEXO_TEXTO)
         + f'<w:p>{ppr_leyenda}<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Tabla C1. </w:t></w:r>'
         + runs("Resultados de las pruebas con el error en pesos, *h* = 3 a 9.") + "</w:p>"
         + tabla(filas_tabla(), [3.5, 2.4, 2.4, 2.4, 2.4, 2.29]) + nota(NOTA))
fin = B[ultimo][1]
d.doc = d.doc[:fin] + ANEXO + d.doc[fin:]

todo = texto(d.doc)
assert "en 2026 lo son las tres (anexo C). Hay dos razones." in todo
assert "solo la de SARIMAX es significativa y los pronósticos" in todo
assert todo.count("Anexo C. Resultados de la prueba en pesos") == 1 and "Tabla C1. " in todo
assert d.doc.count("SEQ Tabla ") == 17 and d.doc.count("SEQ Figura ") == 16
d.guardar(SALIDA)
print("ok", SALIDA)
