"""Figuras de la sección 3.2: los ciclos del precio y su autocorrelación. El flujo de los datos ahora está
hecho con formas de Word (diagramas_word.py).
Los cálculos son los de resumen_modelos_hallazgos/0b_datos_analisis.ipynb (secciones 3 y 4)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf
import warnings

from estilo_graficas import BANDA, EXTRA, TENUE, TINTA, aplicar, claro

# la KPSS solo da valores p entre 0,01 y 0,10, y avisa cuando el estadístico se sale de ese rango
warnings.filterwarnings("ignore")
aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
ROJO, VERDE = EXTRA["rojo"], EXTRA["verde"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def pct(x):
    return 100 * (np.exp(x) - 1)


# ----------------------------------------------------------------------------- ciclos y autocorrelación
def leer():
    h = pd.read_csv(RAIZ / "paneles" / "panel_horario_modelo.csv.gz", parse_dates=["fecha"],
                    usecols=["fecha", "hora", "lp", "es_festivo"])
    LP = h.pivot(index="fecha", columns="hora", values="lp").loc["2015-03-01":"2026-10-06"]
    festivo = h.groupby("fecha")["es_festivo"].first().astype(bool).reindex(LP.index)
    return LP, festivo


def ciclos(LP, festivo):
    lp_dia = LP.mean(axis=1)
    perfil = pct(LP.sub(lp_dia, axis=0).quantile([0.25, 0.5, 0.75])).T
    semana = lp_dia - lp_dia.rolling(7, center=True).mean()
    dia = pd.Series(lp_dia.index.dayofweek, index=lp_dia.index)
    por_dia = pct(semana[~festivo].groupby(dia[~festivo]).mean())
    festivo_semana = pct(semana[festivo & (dia < 5)].mean())
    anual = lp_dia - lp_dia.rolling(365, center=True, min_periods=300).mean()
    por_mes = pct(anual.groupby(anual.index.month).median())

    fig, ejes = plt.subplots(1, 3, figsize=(7.6, 2.6), gridspec_kw=dict(width_ratios=[1.3, 1, 1.3], wspace=0.35))
    ax = ejes[0]
    ax.fill_between(perfil.index, perfil[0.25], perfil[0.75], color=claro(VERDE, 0.2), lw=0, label="Cuartiles")
    ax.plot(perfil.index, perfil[0.5], color=VERDE, lw=1.8, label="Mediana")
    ax.axhline(0, color=TENUE, lw=0.6)
    ax.set_xticks([1, 6, 12, 18, 24])
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("% frente a la referencia")
    ax.set_title("a) Hora", loc="left", fontsize=10)
    ax.legend(fontsize=7, loc="upper left")
    ax = ejes[1]
    # sobre la referencia en rojo, debajo en verde; el festivo más claro
    ax.bar(range(7), por_dia, color=[ROJO if v > 0 else VERDE for v in por_dia], width=0.7)
    ax.bar(7.3, festivo_semana, color=claro(ROJO if festivo_semana > 0 else VERDE, 0.45), width=0.7)
    ax.axhline(0, color=TENUE, lw=0.6)
    ax.set_xticks(list(range(7)) + [7.3], [d[0].upper() for d in DIAS] + ["F"])
    ax.set_title("b) Día de la semana", loc="left", fontsize=10)
    ax = ejes[2]
    ax.bar(range(12), por_mes, color=[ROJO if v > 0 else VERDE for v in por_mes], width=0.7)
    ax.axhline(0, color=TENUE, lw=0.6)
    ax.set_xticks(range(12), [m[0].upper() for m in MESES])
    ax.set_title("c) Mes", loc="left", fontsize=10)
    fig.savefig(FIG / "f15_ciclos_precio.png")
    plt.close(fig)
    print("hora:", perfil[0.5].idxmax(), round(perfil[0.5].max(), 1), perfil[0.5].idxmin(), round(perfil[0.5].min(), 1))
    print("días:", por_dia.round(1).set_axis(DIAS).to_dict(), "festivo:", round(festivo_semana, 1))
    print("meses:", por_mes.round(1).set_axis(MESES).to_dict())


def autocorrelacion(LP):
    sel = LP.loc[:"2019-12-31"]
    filas = []
    for hora in sel.columns:
        nivel, cambio = sel[hora], sel[hora].diff().dropna()
        filas.append([adfuller(nivel, autolag="AIC")[1], kpss(nivel, nlags="auto")[1],
                      adfuller(cambio, autolag="AIC")[1], kpss(cambio, nlags="auto")[1]])
    p = pd.DataFrame(filas, columns=["ADF nivel", "KPSS nivel", "ADF cambio", "KPSS cambio"])
    print("horas con p < 0,05:", (p < 0.05).sum().to_dict(), "p mediano:", p.median().round(3).to_dict())

    cambio = sel.diff().dropna()
    k = 35
    fac = np.array([acf(cambio[h], nlags=k) for h in cambio.columns]).mean(axis=0)
    facp = np.array([pacf(cambio[h], nlags=k) for h in cambio.columns]).mean(axis=0)
    banda = 1.96 / np.sqrt(len(cambio))
    r = np.arange(1, k + 1)
    colores = [ROJO if x % 7 == 0 else claro(ROJO, 0.4) for x in r]
    fig, ejes = plt.subplots(1, 2, figsize=(7.4, 2.6), sharey=True, gridspec_kw=dict(wspace=0.1))
    for ax, v, titulo in zip(ejes, [fac, facp], ["a) Autocorrelación", "b) Autocorrelación parcial"]):
        ax.axhspan(-banda, banda, color=BANDA, lw=0, zorder=0)
        ax.bar(r, v[1:], color=colores, width=0.7, zorder=2)
        ax.axhline(0, color=TENUE, lw=0.6)
        ax.set_xticks([1, 7, 14, 21, 28, 35])
        ax.set_xlabel("Rezago (días)")
        ax.set_title(titulo, loc="left", fontsize=10)
    fig.savefig(FIG / "f16_autocorrelacion.png")
    plt.close(fig)
    print("fac 1, 7, 14, 21, 28:", fac[[1, 7, 14, 21, 28]].round(3), "banda:", round(banda, 3), "n:", len(cambio))


if __name__ == "__main__":
    LP, festivo = leer()
    ciclos(LP, festivo)
    autocorrelacion(LP)
