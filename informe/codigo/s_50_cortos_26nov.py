"""Puntos cortos de los comentarios del 26 de noviembre que faltaban.

2.9    captura del experimento de decisión por año (tabla nueva en la 4.2).
2.4.5  cifras de los orígenes cuya semana empieza después del 14 de noviembre.
2.6    el caso de septiembre y octubre de 2023 también en el análisis del precio (sección 3.2).
2.10.6 nota de que las cifras de SARIMAX de la tabla 15 se comprobaron con el archivo de resultados.

Uso: python s_50_cortos_26nov.py ENTRADA.docx SALIDA.docx"""
import sys
from pathlib import Path

import pandas as pd

from docx_final import Docx, leyenda, reemplazar_en_bloque, runs, tabla

RAIZ = Path(__file__).resolve().parents[2]
RES = RAIZ / "resultados"
FUENTE = "Fuente: elaboración propia con datos de XM (2026)."


def cuerpo(d):
    return [(s, e, Docx.texto(d.doc[s:e])) for s, e in d.bloques() if 'w:val="TDC' not in d.doc[s:e][:400]]


def uno(d, inicio):
    k = [(s, e) for s, e, t in cuerpo(d) if t.startswith(inicio)]
    assert len(k) == 1, f"hay {len(k)} bloques que empiezan con {inicio!r}"
    return k[0]


def cambiar(d, viejo, nuevo):
    k = [(s, e) for s, e, t in cuerpo(d) if viejo in t]
    assert len(k) == 1, f"hay {len(k)} bloques con {viejo[:60]!r}"
    s, e = k[0]
    d.doc = d.doc[:s] + reemplazar_en_bloque(d.doc[s:e], viejo, nuevo) + d.doc[e:]


def tras(d, inicio, xml):
    s, e = uno(d, inicio)
    d.doc = d.doc[:e] + xml + d.doc[e:]


def nota(t):
    x = runs(t).replace("<w:r><w:rPr>", '<w:r><w:rPr><w:sz w:val="20"/>').replace(
        "<w:r><w:t", '<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t')
    return f'<w:p><w:pPr><w:spacing w:before="60" w:after="240"/></w:pPr>{x}</w:p>'


def cap(texto):
    return leyenda("Tabla", texto, ppr='<w:keepNext/><w:spacing w:before="240"/>')


def n(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",").replace("-", "−")


d = Docx(sys.argv[1])
assert "por año, en porcentaje" not in Docx.texto(d.doc), "este script ya se aplicó"
assert "tabla 23" not in Docx.texto(d.doc).lower()

# ---------------------------------------------------------------- 2.9: captura por año
dec = pd.read_csv(RES / "revision" / "decision.csv")
modelos = ["Ingenuo semanal", "Ingenuo del día", "SARIMAX", "XGBoost", "LSTM", "LEAR"]
anios = ["2023", "2024", "2025", "2026"]
cap_ = dec.pivot_table(index=["decision", "pronostico"], columns="caso", values="captura") * 100
pval = dec.pivot_table(index=["decision", "pronostico"], columns="caso", values="p_contra_azar")
filas = [["Pronóstico"] + [f"Días, {a}" for a in anios] + [f"Horas, {a}" for a in anios]]
for m in modelos:
    fila = [m]
    for dd in ("Elegir días", "Elegir horas"):
        for a in anios:
            fila.append("—" if (dd, m) not in cap_.index or pd.isna(cap_.loc[(dd, m), a])
                        else f"{cap_.loc[(dd, m), a]:.0f}")
    filas.append(fila)
# lo que dice el texto, comprobado contra los datos
tres = ["SARIMAX", "XGBoost", "LSTM"]
assert all(17 <= cap_.loc[("Elegir días", m), "2024"] <= 23 for m in tres)
assert all(48 <= cap_.loc[("Elegir días", m), "2025"] <= 56 for m in tres)
for m in tres + ["Ingenuo semanal", "Ingenuo del día"]:
    h = cap_.loc[("Elegir horas", m)]
    assert h["2024"] < h["2023"] and h["2024"] < h["2025"], m
assert (pval[anios].max().max()) < 0.05

cambiar(d, "En 2024 la captura al elegir días cayó a cerca de 20% en los tres modelos, igual que su ventaja en el "
           "error (tabla 16).",
        "Por años (tabla 23), la captura al elegir días cayó en 2024 a cerca de 20% en los tres modelos, igual que su "
        "ventaja en el error (tabla 16), y subió en 2025 a entre 48% y 56%. Al elegir horas, los tres modelos y los "
        "dos ingenuos capturaron menos en 2024 que en 2023 y 2025. En todos los años, cada pronóstico capturó más que "
        "elegir al azar (*p* < 0,05).")
tras(d, "La recomendación de usar la LSTM para elegir días",
     cap("Fracción del ahorro posible que captura cada pronóstico en el experimento de decisión, por año, en "
         "porcentaje.")
     + tabla(filas, [3.0, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55, 1.55], tam=18)
     + nota("Nota: orígenes con la semana completa; el año es el del día de origen. El ingenuo del día solo sirve para "
            "elegir horas. LEAR se agregó después de abrir las pruebas (sección 3.7). " + FUENTE))

# ---------------------------------------------------------------- 2.4.5: orígenes después del 14 de noviembre
cl = pd.read_csv(RES / "periodo_limpio" / "criterio.csv")
cl = cl[(cl["grupo"] == "después de las decisiones") & (cl["bloque"] == "h = 3 a 9")].set_index("modelo")
assert (cl["origenes"] == 9).all() and (cl["semanas_completas"] == 3).all()
assert (cl["ingenuo"] == "del día").all() and (cl["mejora"] > 0).all()
mx, mn = cl["mejora"].idxmax(), cl["mejora"].idxmin()
assert (mx, mn) == ("Nivel LSTM y forma XGBoost", "SARIMAX")
cambiar(d, "Solo 9 orígenes tienen su semana después del 14 de noviembre, la fecha de la última decisión, y de ellos "
           "3 tienen la semana completa; no alcanzan para una prueba.",
        "Solo 9 orígenes, del 12 al 20 de noviembre, tienen su semana después del 14 de noviembre, la fecha de la "
        "última decisión, y de ellos 3 tienen la semana completa; sus pronósticos cubren solo los precios del 15 al "
        f"23 de noviembre. En ellos todos los modelos tuvieron menos error que el ingenuo del día, desde "
        f"{n(cl.loc['SARIMAX', 'mejora'])}% de SARIMAX hasta {n(cl.loc[mx, 'mejora'])}% del nivel de la LSTM con la "
        f"forma de XGBoost; la LSTM mejoró {n(cl.loc['LSTM', 'mejora'])}%, XGBoost alineado "
        f"{n(cl.loc['XGBoost alineado', 'mejora'])}% y LEAR alineado {n(cl.loc['LEAR alineado', 'mejora'])}%. Es lo "
        "contrario de lo que pasó en los 45 orígenes, donde la LSTM tuvo la menor mejora, y muestra lo poco que dicen "
        "tan pocos días. Con 9 orígenes la varianza de la prueba de Diebold-Mariano no se puede estimar con la "
        "ventana de la sección 3.3, así que no se reporta su valor *p*.")

# ---------------------------------------------------------------- 2.6: septiembre de 2023 en el análisis del precio
mes = pd.read_csv(RES / "revision" / "meses_2023_2025.csv").set_index("mes")
sep, oct_ = mes.loc["2023-09"], mes.loc["2023-10"]
assert sep["precio_cop_kwh"] > 1000 and oct_["precio_cop_kwh"] > 1000
cambiar(d, "y desaparece hacia los seis meses.",
        "y desaparece hacia los seis meses. Un caso de la prueba muestra que pesan más los aportes que el nivel del "
        f"embalse: en septiembre y octubre de 2023 el precio promedio pasó de 1.000 COP/kWh con el embalse en "
        f"{sep['embalse_pct']:.0f}% y {oct_['embalse_pct']:.0f}% de su volumen útil, porque los aportes fueron de "
        f"{sep['aportes_pct_media']:.0f}% y {oct_['aportes_pct_media']:.0f}% de su media histórica (anexo F).")

# ---------------------------------------------------------------- 2.10.6: cifras de SARIMAX en la tabla 15
sc = pd.read_csv(RES / "modelo_sarimax" / "prueba_criterio.csv")
a = sc[sc["periodo"] == "2023-2025"].set_index("bloque")["mejora"]
b = sc[sc["periodo"] == "2026"].set_index("bloque")["mejora"]
bl = ["h = 3 a 9", "h = 3 a 7", "h = 8 a 9"]
assert {round(a[x], 1) for x in bl} == {6.4} and {round(b[x], 1) for x in bl} == {5.6}
cambiar(d, "Los modelos agregados son los de la sección 3.7. Fuente:",
        "Los modelos agregados son los de la sección 3.7. Que SARIMAX tenga la misma mejora en tres bloques se "
        f"comprobó con su archivo de resultados: {n(a['h = 3 a 9'], 2)}%, {n(a['h = 3 a 7'], 2)}% y "
        f"{n(a['h = 8 a 9'], 2)}% en 2023-2025, y {n(b['h = 3 a 9'], 2)}%, {n(b['h = 3 a 7'], 2)}% y "
        f"{n(b['h = 8 a 9'], 2)}% en 2026; su mejora casi no cambia con el horizonte (figura 17). Fuente:")

d.renumerar()
texto = Docx.texto(d.doc)
for x in ("(tabla 23)", "del 12 al 20 de noviembre", "anexo F).", "comprobó con su archivo de resultados"):
    assert x in texto, x
d.guardar(sys.argv[2])
print("listo")
