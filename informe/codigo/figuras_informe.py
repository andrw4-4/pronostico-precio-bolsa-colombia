import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

BASE = Path(sys.argv[1])
SAL = BASE / "informe" / "figuras"
SAL.mkdir(parents=True, exist_ok=True)

XGB, SAR, ING, REAL, ING2 = "#eb6834", "#1baf7a", "#898781", "#2a78d6", "#b9b7af"
TINTA, TENUE, FONDO = "#2b2b2b", "#77766f", "#ffffff"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": TENUE, "axes.labelcolor": TINTA,
                     "xtick.color": TENUE, "ytick.color": TENUE, "figure.facecolor": FONDO,
                     "axes.facecolor": FONDO, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
                     "axes.titlelocation": "left", "axes.titlesize": 11})


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(SAL / nombre, dpi=170)
    plt.close(fig)


# datos del panel
p = pd.read_csv(BASE / "paneles/panel_caracteristicas.csv.gz",
                usecols=["fecha", "hora", "precio", "lp", "dia_semana", "es_festivo",
                         "volumen_util_pct", "oni"])
p["fecha"] = pd.to_datetime(p["fecha"])
p = p[p.precio.notna()]
d = p.groupby("fecha").agg(precio=("precio", "mean"), vol=("volumen_util_pct", "first"),
                           oni=("oni", "first")).reset_index()

# 1. el precio con los embalses y El Niño pasó a fig_contexto.py, con la paleta del informe final

# 2. por qué el logaritmo
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.5, 3.2))
a1.hist(p.precio, bins=120, color=REAL, alpha=0.85)
a1.set_title("Precio horario (COP/kWh)")
a1.set_xlim(0, np.nanpercentile(p.precio, 99.7))
a1.set_ylabel("horas")
a2.hist(p.lp, bins=120, color=REAL, alpha=0.85)
a2.set_title("Logaritmo del precio")
guardar(fig, "f02_distribucion_log.png")

# 3. perfil del día
p["tipo"] = np.where(p.es_festivo == 1, "domingo o festivo",
                     np.where(p.dia_semana == 6, "domingo o festivo",
                              np.where(p.dia_semana == 5, "sábado", "lunes a viernes")))
q = p[p.fecha >= "2023-01-01"].copy()
q["rel"] = q.precio / q.groupby("fecha").precio.transform("mean")
r = q.groupby(["tipo", "hora"]).rel.mean().unstack(0)
fig, ax = plt.subplots(figsize=(7.5, 3.4))
for col, c in (("lunes a viernes", TINTA), ("sábado", XGB), ("domingo o festivo", SAR)):
    ax.plot(r.index, r[col], color=c, lw=2, label=col)
ax.axhline(1, color=TENUE, lw=0.8)
ax.set_xticks(range(1, 25, 2))
ax.set_xlabel("hora del día (convención de XM: la hora 1 va de 0:00 a 1:00)")
ax.set_ylabel("precio / promedio del día")
ax.set_title("Forma promedio del día, 2023-2026")
ax.legend(frameon=False)
guardar(fig, "f03_perfil_horario.png")

# 4. cuándo se conoce cada dato frente al día del pronóstico R
datos = [("Calendario de los días pronosticados", 7, "#9a9890"),
         ("Despacho programado de hoy (costo marginal, disponibilidad)", 0, SAR),
         ("Aportes, embalses, redespacho de ayer", 1, "#3b6fb6"),
         ("Precio de bolsa, demanda, generación real", 2, REAL),
         ("Contratos, pérdidas, restricciones", 5, "#b98a2e"),
         ("Ofertas, curva de mérito, planta marginal", 10, XGB)]
fig, ax = plt.subplots(figsize=(8.5, 3.3))
for i, (nom, atraso, c) in enumerate(datos[::-1]):
    if nom.startswith("Calendario"):
        ax.barh(i, 7, left=1, color=c, height=0.55)
        ax.text(4.5, i, "se conoce de antemano", va="center", ha="center", fontsize=8.5, color="white")
    else:
        ax.barh(i, 12 - atraso, left=-12, color=c, height=0.55)
        ax.text(-atraso + 0.2, i, f"último dato: R − {atraso}" if atraso else "último dato: R",
                va="center", fontsize=8.5, color=TINTA)
ax.set_yticks(range(len(datos)), [x[0] for x in datos[::-1]], fontsize=8.5)
ax.axvline(0, color=TINTA, lw=1.2)
ax.axvspan(0.5, 7.5, color="#eef4fb", lw=0, zorder=0)
ax.text(4, -0.9, "semana pronosticada:\nR+1 a R+7 (h = 3 a 9)", ha="center", va="center", fontsize=8.5, color=TINTA)
ax.set_xlim(-12, 9); ax.set_ylim(-1.3, len(datos) - 0.5)
ax.set_xlabel("días frente al día en que se pronostica (R = t + 2)")
ax.set_title("Hasta qué día se conoce cada dato al pronosticar")
ax.grid(axis="y", visible=False)
guardar(fig, "f04_atrasos_publicacion.png")

# 5. embudo de la selección
fig, ax = plt.subplots(figsize=(8, 3))
etapas = [("Columnas derivadas (paso 2c)", 1861), ("Tras la limpieza", 1290),
          ("Le ganan al ruido (h = 3)", 15), ("Entran al modelo (h = 3)", 10)]
for i, (n, v) in enumerate(etapas):
    w = np.log10(v + 1) / np.log10(1862)
    ax.barh(-i, w, left=(1 - w) / 2, color=[ING2, ING, "#3b6fb6", XGB][i], height=0.7)
    ax.text(0.5, -i, f"{n}: {v:,}".replace(",", "."), ha="center", va="center",
            color="white" if i else TINTA, fontsize=9.5, fontweight="bold")
ax.set_axis_off()
ax.set_title("Selección de columnas, paso 2d (ancho en escala logarítmica)")
guardar(fig, "f05_embudo_seleccion.png")

# 6. mejora por horizonte en log, los dos modelos
s23 = pd.read_csv(BASE / "resultados/modelo_sarimax/prueba_2023_2025.csv.gz")
s26 = pd.read_csv(BASE / "resultados/modelo_sarimax/prueba_2026.csv.gz")
x26 = pd.read_csv(BASE / "resultados/modelo_xgboost/prueba2026_mensual.csv.gz")
filas = []
for periodo, s, fx in (("2023-2025", s23, None), ("2026", s26, x26)):
    for h in range(3, 10):
        x = (pd.read_csv(BASE / f"resultados/modelo_xgboost/prueba_h{h}.csv.gz") if fx is None
             else fx[fx.h == h])
        m = x.merge(s[s.h == h][["fecha", "hora", "lp_hat"]], on=["fecha", "hora"])
        ys = m.lp_hat - np.log(m.precio_t)
        rm = lambda e: np.sqrt(np.mean(e ** 2))
        ing = rm(m.y)
        filas.append(dict(periodo=periodo, h=h, n=len(m), XGBoost=100 * (1 - rm(m.y - m.y_hat) / ing),
                          SARIMAX=100 * (1 - rm(m.y - ys) / ing)))
t = pd.DataFrame(filas)
t.to_csv(SAL / "mejora_log_por_horizonte.csv", index=False)
print(t.round(1).to_string(index=False))
fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.3), sharey=True)
for ax, per in zip(axs, ("2023-2025", "2026")):
    u = t[t.periodo == per]
    ax.axhline(0, color=TENUE, lw=0.8)
    ax.axhline(5, color=TENUE, lw=0.8, ls="--")
    ax.plot(u.h, u.XGBoost, color=XGB, lw=2, marker="o", ms=5, label="XGBoost")
    ax.plot(u.h, u.SARIMAX, color=SAR, lw=2, marker="o", ms=5, label="SARIMAX")
    ax.set_title(per)
    ax.set_xlabel("h (días desde el último precio)")
axs[0].set_ylabel("mejora del RMSE en log\nfrente al ingenuo del día (%)")
axs[0].text(3, 3.4, "umbral 5%", ha="left", fontsize=8, color=TENUE)
axs[0].legend(frameon=False)
guardar(fig, "f06_mejora_log_por_horizonte.png")

# 7. mejora por año, semana h = 3 a 9
anos = ["2023", "2024", "2025", "2026"]
mx = [12.9, 7.6, 15.3, 10.0]
ms = [100 * (1 - 0.521 / 0.544), 100 * (1 - 0.478 / 0.508), 100 * (1 - 0.401 / 0.447), 5.6]
fig, ax = plt.subplots(figsize=(7, 3.2))
xx = np.arange(4)
ax.bar(xx - 0.19, mx, 0.36, color=XGB, label="XGBoost")
ax.bar(xx + 0.19, ms, 0.36, color=SAR, label="SARIMAX")
for i in range(4):
    ax.text(i - 0.19, mx[i] + 0.3, f"{mx[i]:.1f}".replace(".", ","), ha="center", fontsize=8.5)
    ax.text(i + 0.19, ms[i] + 0.3, f"{ms[i]:.1f}".replace(".", ","), ha="center", fontsize=8.5)
ax.axhline(5, color=TENUE, lw=0.8, ls="--")
ax.set_xticks(xx, anos)
ax.set_ylabel("mejora del RMSE en log (%)")
ax.set_title("Mejora frente al ingenuo del día por año, semana h = 3 a 9")
ax.legend(frameon=False)
ax.grid(axis="x", visible=False)
guardar(fig, "f07_mejora_por_ano.png")

# 8. nivel y forma
fig, ax = plt.subplots(figsize=(7, 3))
mods = ["Ingenuo del día", "SARIMAX", "XGBoost"]
niv, forma = [0.415, 0.402, 0.385], [0.282, 0.243, 0.221]
yy = np.arange(3)
ax.barh(yy + 0.18, niv, 0.34, color="#3b6fb6", label="nivel del día")
ax.barh(yy - 0.18, forma, 0.34, color="#b98a2e", label="forma dentro del día")
for i in range(3):
    ax.text(niv[i] + 0.004, i + 0.18, f"{niv[i]:.3f}".replace(".", ","), va="center", fontsize=8.5)
    ax.text(forma[i] + 0.004, i - 0.18, f"{forma[i]:.3f}".replace(".", ","), va="center", fontsize=8.5)
ax.set_yticks(yy, mods)
ax.set_xlabel("RMSE en log, 2023-2025, h = 3 a 9")
ax.set_title("El error se parte en el nivel del día y la forma")
ax.set_xlim(0, 0.47)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2)
ax.grid(axis="y", visible=False)
guardar(fig, "f08_nivel_forma.png")

# 9. oráculo
fig, ax = plt.subplots(figsize=(7.5, 3.2))
cas = ["Lo que tiene hoy", "+ demanda futura", "+ hidrología futura", "+ demanda e hidrología",
       "+ ofertas futuras", "+ todo"]
h3 = [18.4, 19.5, 19.0, 20.2, 35.8, 35.0]
h7 = [8.3, 8.5, 11.1, 11.1, 39.5, 40.3]
yy = np.arange(len(cas))[::-1]
ax.barh(yy + 0.18, h3, 0.34, color=XGB, label="h = 3")
ax.barh(yy - 0.18, h7, 0.34, color="#a8461f", label="h = 7")
ax.set_yticks(yy, cas)
ax.set_xlabel("mejora del RMSE frente al ingenuo del día (%), 2020-2022")
ax.set_title("Oráculo: XGBoost con datos futuros reales que nadie tendría")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2)
ax.grid(axis="y", visible=False)
guardar(fig, "f09_oraculo.png")


# 10. diagramas: flujo del proyecto y arquitectura de la LSTM
def caja(ax, x, y, w, h, texto, color, fs=8.5, tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="none"))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, color=tc)


def flecha(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=TENUE, lw=1.2))


fig, ax = plt.subplots(figsize=(9, 3.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.set_axis_off()
pasos = [("1. Descarga\nXM, SIMEM, NOAA,\nERA5, IDEAM, TRM", "#5a5852"),
         ("2. Panel diario\ny 2b. panel horario\n103.200 filas", "#3b6fb6"),
         ("2c. Características\n134 variables base\n1.861 derivadas", "#3b6fb6"),
         ("2d. Selección\nlimpieza, SHAP\ncontra ruido, k", "#3b6fb6"),
         ("Modelos\nXGBoost (Python)\nSARIMAX (R)", XGB)]
for i, (txt, c) in enumerate(pasos):
    caja(ax, 0.1 + i * 2, 2.2, 1.7, 1.4, txt, c)
    if i:
        flecha(ax, i * 2 - 0.2, 2.9, i * 2 + 0.1, 2.9)
caja(ax, 4.1, 0.3, 1.7, 1.3, "2e-2g. Panel LSTM\ncada dato el día\nen que se publica", SAR)
caja(ax, 6.1, 0.3, 1.7, 1.3, "LSTM\n(en curso)", "#9a9890")
flecha(ax, 3.0, 2.2, 4.4, 1.6)
flecha(ax, 5.8, 0.95, 6.1, 0.95)
caja(ax, 8.1, 0.3, 1.7, 1.3, "Evaluación\nmismas filas,\ningenuos y criterio", "#e6e5e0", tc=TINTA)
flecha(ax, 7.8, 0.95, 8.1, 0.95)
flecha(ax, 9.0, 2.2, 9.0, 1.6)
guardar(fig, "f10_flujo.png")

fig, ax = plt.subplots(figsize=(9, 4))
ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.set_axis_off()
ax.text(2.2, 4.75, "CODIFICADOR: lo que pasó (28 días)", ha="center", fontsize=9.5, color=TINTA, fontweight="bold")
ax.text(7.5, 4.75, "DECODIFICADOR: la semana que viene (7 días)", ha="center", fontsize=9.5, color=TINTA, fontweight="bold")
caja(ax, 0.3, 3.5, 3.8, 0.9, "cada día: 24 horas de cada variable horaria\n+ las variables diarias", "#e6e5e0", tc=TINTA)
caja(ax, 1.2, 2.3, 2.0, 0.8, "Dense(64)", "#3b6fb6")
caja(ax, 1.2, 1.0, 2.0, 0.9, "LSTM(128)", SAR)
caja(ax, 5.6, 3.5, 3.8, 0.9, "cada día: su calendario (día, festivo)\n[+ bloque 7: pronósticos de XGBoost y SARIMAX]", "#e6e5e0", tc=TINTA)
caja(ax, 6.5, 2.3, 2.0, 0.8, "LSTM(128)", SAR)
caja(ax, 6.5, 1.0, 2.0, 0.8, "Dense(24) por día", "#3b6fb6")
caja(ax, 5.9, 0.0, 3.2, 0.6, "7 días × 24 horas = 168 pronósticos", XGB)
flecha(ax, 2.2, 3.5, 2.2, 3.1); flecha(ax, 2.2, 2.3, 2.2, 1.9)
flecha(ax, 7.5, 3.5, 7.5, 3.1); flecha(ax, 7.5, 2.3, 7.5, 1.8); flecha(ax, 7.5, 1.0, 7.5, 0.6)
flecha(ax, 3.2, 1.45, 6.5, 2.6)
ax.text(4.85, 1.75, "estado final", ha="center", fontsize=8.5, color=TENUE, rotation=19)
guardar(fig, "f11_arquitectura_lstm.png")
print("listo")
