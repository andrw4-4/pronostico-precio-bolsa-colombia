"""Correcciones de la revisión del informe contra el repositorio (26 de noviembre de 2026).

La sección 4.1 dice que los valores p de las pruebas llevan la corrección de Harvey et al. (1997), pero las tablas
16 y 17 y el párrafo de las pruebas entre pares de la sección 5.1 tenían todavía el valor p sin corregir. Ningún
veredicto cambia: con la corrección, la mejora en pesos de la LSTM en 2026 queda en p = 0,049. Además:

    - tabla 15: el valor p de SARIMAX en 2026 es 0,0007, que se escribe < 0,001, y no 0,001;
    - tabla 20: lo mismo para SARIMAX con aportes bajos;
    - sección 4.1: dice qué valores p llevan la corrección y cuáles no (los de la validación del capítulo IV,
      que son los que se usaron al decidir);
    - sección 1.3: los 31 días con precios corregidos por XM van del 6 de septiembre al 6 de octubre, ambos
      incluidos (se comprueba con los dos paneles del repositorio);
    - resumen, abstract y sección 6.1: el rango de captura de 32% a 55% es el de los tres modelos, no el de
      todos, porque LEAR capturó 41% y 56%.

Cada cifra nueva sale de un archivo del repositorio, y el script comprueba que la cifra vieja era la que daba el
valor p sin corregir del mismo archivo.

Uso: python s_58_revision_contra_repo.py ENTRADA.docx SALIDA.docx"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from docx_final import Docx, reemplazar_en_bloque

RAIZ = Path(__file__).resolve().parents[2]
REV, FIG = RAIZ / "resultados" / "revision", RAIZ / "informe" / "figuras"
H = 9


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


def hln(t, T, h=H):
    """Valor p de dos colas con la corrección de Harvey et al. (1997), como en la sección 4.1."""
    t2 = t * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return 2 * stats.t.sf(abs(t2), T - 1)


def celdas(d, marca, cambios):
    """Cambia celdas de la tabla que contiene `marca`. `cambios` es una lista de (primera celda de la fila, número de
    la aparición de esa fila, columna, texto viejo, texto nuevo); el texto viejo debe ser el de la celda completa."""
    k = [(s, e) for s, e in d.bloques() if d.doc[s:e].startswith("<w:tbl") and marca in Docx.texto(d.doc[s:e])]
    assert len(k) == 1, marca
    s, e = k[0]
    tabla = d.doc[s:e]
    for fila, vez, col, viejo, nuevo in cambios:
        trs = [m for m in re.finditer(r"<w:tr[ >].*?</w:tr>", tabla, re.S)
               if Docx.texto(re.search(r"<w:tc>.*?</w:tc>", m.group(0), re.S).group(0)) == fila]
        tr = trs[vez]
        tcs = list(re.finditer(r"<w:tc>.*?</w:tc>", tr.group(0), re.S))
        tc = tcs[col]
        assert Docx.texto(tc.group(0)) == viejo, (fila, vez, col, Docx.texto(tc.group(0)), viejo)
        tc_nuevo = reemplazar_en_bloque(tc.group(0), viejo, nuevo)
        a, b = tr.start() + tc.start(), tr.start() + tc.end()
        tabla = tabla[:a] + tc_nuevo + tabla[b:]
    d.doc = d.doc[:s] + tabla + d.doc[e:]


# ---------------------------------------------------------------- cifras
crit = pd.read_csv(REV / "criterio_hln.csv", dtype={"caso": str})
semana = crit[crit["bloque"] == "h = 3 a 9"].set_index(["caso", "modelo"])
T = {c: int(g["origenes"].iloc[0]) for c, g in semana.groupby(level="caso")}
assert T == {"2023-2025": 1093, "2026": 276, "2023": 365, "2024": 366, "2025": 362}, T
# la función hln reproduce la corrección del archivo, salvo el redondeo del estadístico a seis cifras
for (c, mo), r in semana.iterrows():
    assert abs(hln(r["dm_t"], T[c]) - r["dm_p_hln"]) < 1e-5, (c, mo)

t15 = pd.read_csv(REV / "tabla15_ampliada.csv").set_index(["periodo", "pronostico"])
reg = pd.read_csv(REV / "regimenes.csv").set_index(["regimen", "modelo"])
pesos = pd.read_csv(FIG / "datos_resultados_pesos.csv", dtype={"caso": str}).set_index(["caso", "pronostico"])
pesos_pares = pd.read_csv(FIG / "datos_resultados_pesos_pares.csv", dtype={"caso": str})
pares_anio = pd.read_csv(FIG / "datos_resultados_pares.csv", dtype={"caso": str})
pares = pd.read_csv(REV / "todos_pares.csv", dtype={"periodo": str}).set_index(["periodo", "a", "b"])

d = Docx(sys.argv[1])
assert "anexos C y E llevan la corrección" not in Docx.texto(d.doc), "este script ya se aplicó"

# ---------------------------------------------------------------- tabla 15: SARIMAX en 2026
p = t15.loc[("2026", "SARIMAX"), "p_hln"]
celdas(d, "LSTM, primera versión repetida", [("SARIMAX", 1, 4, "0,001", valor_p(p))])

# ---------------------------------------------------------------- tabla 16: por año, con la corrección
cambios = []
for mo in ("SARIMAX", "XGBoost", "LSTM"):
    for j, anio in enumerate(("2023", "2024", "2025", "2026"), start=1):
        r = semana.loc[(anio, mo)]
        viejo = f"{n(r['mejora'])} ({valor_p(r['dm_p'])})"
        nuevo = f"{n(r['mejora'])} ({valor_p(r['dm_p_hln'])})"
        assert bool(r["cumple"]) == bool(r["cumple_hln"]), (anio, mo)
        cambios.append((mo, 0, j, viejo, nuevo))
celdas(d, "Modelo2023202420252026", [c for c in cambios if c[3] != c[4]])
cambiar(d, "el valor p de Diebold-Mariano. El ingenuo del día fue el mejor de los dos en todos los años",
        "el valor p de Diebold-Mariano con la corrección de Harvey et al. (1997). El ingenuo del día fue el mejor de "
        "los dos en todos los años")

# ---------------------------------------------------------------- tabla 17 y texto: error en pesos
pp = {}
for caso in ("2023-2025", "2026", "2023", "2024", "2025"):
    for mo in ("SARIMAX", "XGBoost", "LSTM"):
        r = pesos.loc[(caso, mo)]
        pp[(caso, mo)] = hln(r["t"], T[caso])
cambios = []
for vez, caso in enumerate(("2023-2025", "2026")):
    for mo in ("SARIMAX", "XGBoost", "LSTM"):
        viejo, nuevo = valor_p(pesos.loc[(caso, mo), "p"]), valor_p(pp[(caso, mo)])
        if viejo != nuevo:
            cambios.append((mo, vez, 5, viejo, nuevo))
celdas(d, "Mejora en pesos (%)", cambios)
cambiar(d, "con el error cuadrático en pesos, con la misma varianza de la sección 4.1.",
        "con el error cuadrático en pesos, con la misma varianza de la sección 4.1 y la corrección de Harvey et al. "
        "(1997).")
# lo que dice el texto se sigue cumpliendo con la corrección
assert pp[("2023-2025", "SARIMAX")] < 0.05 < min(pp[("2023-2025", "XGBoost")], pp[("2023-2025", "LSTM")])
assert max(pp[("2026", mo)] for mo in ("SARIMAX", "XGBoost", "LSTM")) < 0.05
assert min(pp[(a, mo)] for a in ("2023", "2024") for mo in ("SARIMAX", "XGBoost", "LSTM")) > 0.05
assert max(pp[("2025", mo)] for mo in ("SARIMAX", "XGBoost", "LSTM")) < 0.01
for _, r in pesos_pares[pesos_pares["caso"].isin(["2023-2025", "2026"])].iterrows():
    assert hln(r["t"], T[r["caso"]]) > 0.05, r["par"]
# este párrafo usa espacios duros alrededor del signo igual
IG = "\xa0=\xa0"
cambiar(d, f"en 2023-2025 solo la mejora de SARIMAX es significativa (p{IG}0,010), no las de XGBoost ni la LSTM "
           f"(p{IG}0,508 y p{IG}0,297)",
        f"en 2023-2025 solo la mejora de SARIMAX es significativa (p{IG}{valor_p(pp[('2023-2025', 'SARIMAX')])}), no "
        f"las de XGBoost ni la LSTM (p{IG}{valor_p(pp[('2023-2025', 'XGBoost')])} y "
        f"p{IG}{valor_p(pp[('2023-2025', 'LSTM')])})")

# ---------------------------------------------------------------- pruebas entre pares de modelos (sección 5.1)
def pp_par(periodo, a, b):
    return valor_p(pares.loc[(periodo, a, b), "p_hln"])


assert pares.loc[("2026", "SARIMAX", "XGBoost"), "p_hln"] > 0.05 > pares.loc[("2026", "XGBoost", "LSTM"), "p_hln"]
assert pares.loc[("2023-2025", "XGBoost", "LSTM"), "p_hln"] > 0.05
for _, r in pares_anio[pares_anio["caso"].isin(["2023", "2024", "2025"])].iterrows():
    p = hln(r["t"], T[r["caso"]])
    assert (p < 0.05) == (r["caso"] == "2023"), (r["caso"], r["par"], p)
cambiar(d, "Con la prueba de Diebold-Mariano entre cada par de modelos, con la misma varianza de la sección 4.1, la "
           "LSTM tiene menos error que SARIMAX en las dos pruebas (p = 0,007 y p = 0,011), y XGBoost menos que "
           "SARIMAX en 2023-2025 (p = 0,011), pero no en 2026 (p = 0,062). Entre la LSTM y XGBoost la diferencia no "
           "es significativa en 2023-2025 (p = 0,107) y sí lo es en 2026 (p = 0,033).",
        "Con la prueba de Diebold-Mariano entre cada par de modelos, con la misma varianza de la sección 4.1 y la "
        "corrección de Harvey et al. (1997), la LSTM tiene menos error que SARIMAX en las dos pruebas "
        f"(p = {pp_par('2023-2025', 'SARIMAX', 'LSTM')} y p = {pp_par('2026', 'SARIMAX', 'LSTM')}), y XGBoost menos "
        f"que SARIMAX en 2023-2025 (p = {pp_par('2023-2025', 'SARIMAX', 'XGBoost')}), pero no en 2026 "
        f"(p = {pp_par('2026', 'SARIMAX', 'XGBoost')}). Entre la LSTM y XGBoost la diferencia no es significativa en "
        f"2023-2025 (p = {pp_par('2023-2025', 'XGBoost', 'LSTM')}) y sí lo es en 2026 "
        f"(p = {pp_par('2026', 'XGBoost', 'LSTM')}).")

# ---------------------------------------------------------------- tabla 20: SARIMAX con aportes bajos
r = reg.loc[("aportes bajos (menos de 80%)", "SARIMAX")]
celdas(d, "Aportes bajos, menos de 80%",
       [("Aportes bajos, menos de 80%", 0, 2, f"{n(r['mejora'])} (0,001)", f"{n(r['mejora'])} ({valor_p(r['dm_p_hln'])})")])

# ---------------------------------------------------------------- sección 4.1: alcance de la corrección
cambiar(d, "Por eso los valores p de la tabla 15 y de los análisis que se agregaron en la revisión de este informe "
           "llevan la corrección de Harvey et al. (1997):",
        "Por eso los valores p de la prueba de Diebold-Mariano del capítulo V y de los anexos C y E llevan la "
        "corrección de Harvey et al. (1997):")
factor = np.sqrt((1090 + 1 - 2 * H + H * (H - 1) / 1090) / 1090)
assert round(factor, 2) == 0.99
cambiar(d, "el de XGBoost en h = 8 a 9 en 2026 (sección 5.1).",
        "el de XGBoost en h = 8 a 9 en 2026 (sección 5.1). Los del capítulo IV, de la validación de 2020-2022, van "
        "sin ella, porque son los que se usaron para tomar cada decisión; con tres años de orígenes, la corrección "
        "multiplica el estadístico por cerca de 0,99 y casi no los cambia.")

# ---------------------------------------------------------------- sección 1.3: precios corregidos por XM
viejo_p = pd.read_csv(RAIZ / "paneles" / "panel_horario_modelo.csv.gz", usecols=["fecha", "hora", "precio"])
nuevo_p = pd.read_csv(RAIZ / "periodo_limpio" / "paneles" / "panel_horario_modelo.csv.gz",
                      usecols=["fecha", "hora", "precio"])
j = viejo_p.merge(nuevo_p, on=["fecha", "hora"], suffixes=("", "_nuevo"))
j = j[(j["fecha"] >= "2026-09-06") & (j["fecha"] <= "2026-10-06")]
dif = (j["precio_nuevo"] - j["precio"]).abs()
assert len(j) == 744 and (dif > 0).all() and dif.median() < 2 and (dif > 100).sum() == 19 and round(dif.max()) == 823
cambiar(d, "cambiaron los precios de las 744 horas de los 31 días anteriores al 6 de octubre:",
        "cambiaron los precios de las 744 horas de los 31 días del 6 de septiembre al 6 de octubre:")

# ---------------------------------------------------------------- captura al elegir días: los tres modelos
dec = (pd.read_csv(REV / "decision.csv").drop_duplicates(["caso", "decision", "pronostico"])
       .query("decision == 'Elegir días' and caso in ['2023-2025', '2026']").set_index(["caso", "pronostico"]))
tres = [round(100 * dec.loc[(c, mo), "captura"]) for c in ("2023-2025", "2026") for mo in ("SARIMAX", "XGBoost", "LSTM")]
assert (min(tres), max(tres)) == (32, 55), tres
assert round(100 * dec.loc[("2026", "LEAR"), "captura"]) == 56
cambiar(d, "En un experimento sencillo de decisión, los modelos capturan entre 32% y 55%",
        "En un experimento sencillo de decisión, los tres modelos capturan entre 32% y 55%")
cambiar(d, "In a simple decision experiment, the models capture between 32% and 55%",
        "In a simple decision experiment, the three models capture between 32% and 55%")
cambiar(d, "Para elegir los dos días más baratos de la semana, los modelos capturaron entre 32% y 55%",
        "Para elegir los dos días más baratos de la semana, los tres modelos capturaron entre 32% y 55%")

texto = Docx.texto(d.doc)
for x in ("anexos C y E llevan la corrección", "del 6 de septiembre al 6 de octubre", "the three models capture",
          "corrección de Harvey et al. (1997), la LSTM tiene menos error que SARIMAX"):
    assert texto.count(x) == 1, x
d.guardar(sys.argv[2])
print("listo")
