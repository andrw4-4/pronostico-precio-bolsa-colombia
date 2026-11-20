"""Figuras de la sección 3.4, SARIMAX: el preblanqueo, la validación y los residuos. Las etapas de la
construcción ahora están hechas con formas de Word (diagramas_word.py).
La validación sale de resultados/modelo_sarimax/etapa4_*.csv.gz, que guardó 5_modelo_sarimax.ipynb. El
preblanqueo y los residuos salen de fig_sarimax_datos.R, que repite esos cálculos del notebook con 2015-2019."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from estilo_graficas import BANDA, COLORES, EXTRA, TENUE, TINTA, aplicar, claro

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
SARIMAX = RAIZ / "resultados" / "modelo_sarimax"
VERDE, ROJO = COLORES["SARIMAX"], EXTRA["rojo"]
N_DIAS = 1767                                   # del 1 de marzo de 2015 al 31 de diciembre de 2019
UMBRAL = 3.5337 / np.sqrt(N_DIAS)               # z de Bonferroni con 122 candidatas, sobre raíz de n


# ----------------------------------------------------------------------------- preblanqueo
def preblanqueo():
    p = pd.read_csv(FIG / "datos_sarimax_preblanqueo.csv")
    cand = pd.read_csv(SARIMAX / "etapa3_candidatas.csv")
    por_var = p.groupby("variable").agg(cruda=("cruda", lambda s: s.abs().mean()),
                                        blanca=("preblanqueada", lambda s: s.abs().mean()))
    horas = cand.dropna(subset=["horas_signif"]).set_index("variable")["horas_signif"]
    horas = horas[horas > 0].sort_values()

    fig, ejes = plt.subplots(1, 2, figsize=(7.6, 3.4), gridspec_kw=dict(width_ratios=[1, 1.35], wspace=0.55))
    ax = ejes[0]
    for _, f in por_var.iterrows():
        ax.plot([0, 1], [f.cruda, f.blanca], color=claro(VERDE, 0.35), lw=0.6, zorder=1)
    ax.scatter(np.zeros(len(por_var)), por_var.cruda, s=9, color=VERDE, zorder=2, lw=0)
    ax.scatter(np.ones(len(por_var)), por_var.blanca, s=9, color=VERDE, zorder=2, lw=0)
    # la holgura, en rojo
    h = por_var.loc["holgura_rel"]
    ax.plot([0, 1], [h.cruda, h.blanca], color=ROJO, lw=1.6, zorder=3)
    ax.scatter([0, 1], [h.cruda, h.blanca], s=22, color=ROJO, zorder=4)
    ax.text(-0.07, h.cruda, "Holgura", fontsize=7.5, color=TINTA, va="center", ha="right")
    ax.axhline(UMBRAL, color=TENUE, lw=0.9, ls="--")
    ax.text(1.08, UMBRAL, "umbral\n0,084", fontsize=7, color=TENUE, ha="left", va="center")
    ax.set_xticks([0, 1], ["Sin\npreblanqueo", "Con\npreblanqueo"])
    ax.set_xlim(-0.55, 1.5)
    ax.set_ylim(0, 0.92)
    ax.set_ylabel("Correlación con el precio\n(valor absoluto, promedio de 24 horas)")
    ax.set_title("a) Las 122 candidatas", loc="left", fontsize=10)

    ax = ejes[1]
    nombres = {"holgura_rel": "Holgura de la oferta", "oferta_marginal": "Oferta de la planta marginal",
               "cap_bajo_500_rel": "Capacidad bajo 500 COP/kWh", "oblig_energia_firme_rel": "Obligaciones de energía firme",
               "margen_ofertado": "Margen ofertado", "demanda": "Demanda", "pron_demanda": "Pronóstico de demanda",
               "margen_decl_pron": "Margen declarado pronosticado", "lluvia_sistema_acum90": "Lluvia acumulada 90 días",
               "margen_declarado": "Margen declarado", "demanda_max_potencia_rel": "Demanda máxima de potencia",
               "restricciones_rel": "Restricciones", "dem_no_regulada_frac": "Demanda no regulada",
               "disp_termica_frac": "Disponibilidad térmica", "margen_reserva": "Margen de reserva",
               "cap_bajo_200_rel": "Capacidad bajo 200 COP/kWh"}
    colores = [ROJO if v == "holgura_rel" else claro(VERDE, 0.6) for v in horas.index]
    ax.barh(range(len(horas)), horas.values, color=colores, height=0.7)
    ax.set_yticks(range(len(horas)), [nombres.get(v, v) for v in horas.index], fontsize=7)
    ax.axvline(12, color=TENUE, lw=0.9, ls="--")
    ax.text(12.3, 0.2, "mínimo: 12", fontsize=7, color=TENUE, va="bottom")
    ax.set_xlim(0, 24)
    ax.set_xticks([0, 6, 12, 18, 24])
    ax.set_xlabel("Horas con correlación significativa")
    ax.set_title("b) Las 16 significativas en alguna hora", loc="left", fontsize=10)
    fig.savefig(FIG / "f18_sarimax_preblanqueo.png")
    plt.close(fig)
    print("correlación media sin y con preblanqueo:", por_var.mean().round(3).to_dict())
    print("pares variable-hora sobre el umbral, sin y con:", (p.cruda.abs() > UMBRAL).mean().round(3),
          (p.preblanqueada.abs() > UMBRAL).mean().round(3))
    print("holgura:", h.round(3).to_dict())


# ----------------------------------------------------------------------------- validación
def validacion():
    h = pd.read_csv(RAIZ / "paneles" / "panel_horario_modelo.csv.gz", usecols=["fecha", "hora", "lp"],
                    parse_dates=["fecha"])
    LP = h.pivot(index="fecha", columns="hora", values="lp")
    fila = {d: i for i, d in enumerate(LP.index)}
    A = LP.values
    versiones = {"comun": "Un solo orden (final)", "por_hora": "Un orden por hora", "exogenas": "Un solo orden con la holgura"}
    estilos = {"comun": dict(color=VERDE, lw=2.0, marker="o", ms=4),
               "por_hora": dict(color=EXTRA["rojo"], lw=1.3, ls="--", marker="s", ms=3.5),
               "exogenas": dict(color=TINTA, lw=1.3, ls=":", marker="^", ms=4)}
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for v, nombre in versiones.items():
        x = pd.read_csv(SARIMAX / f"etapa4_{v}.csv.gz", parse_dates=["fecha"])
        i, H, hh = x.fecha.map(fila).values, x.hora.values - 1, x.h.values
        lp_t = A[i, H]
        y = A[i + hh, H] - lp_t
        e = y - (x.lp_hat.values - lp_t)
        d = pd.DataFrame(dict(h=hh, e2=e ** 2, d2=y ** 2))
        g = d.groupby("h")[["e2", "d2"]].mean()
        mejora = 100 * (1 - np.sqrt(g.e2) / np.sqrt(g.d2))
        total = 100 * (1 - np.sqrt(d.e2.mean()) / np.sqrt(d.d2.mean()))
        ax.plot(mejora.index, mejora.values, label=nombre, **estilos[v])
        print(v, "RMSE", round(np.sqrt(d.e2.mean()), 4), "mejora total", round(total, 1), mejora.round(1).to_dict())
    ax.axhline(5, color=TENUE, lw=0.9, ls="--")
    ax.text(2.8, 5.15, "criterio: 5%", fontsize=7, color=TENUE, va="bottom")
    ax.axhline(0, color=TENUE, lw=0.6)
    ax.set_xticks(range(3, 10))
    ax.set_xlim(2.7, 9.3)
    ax.set_ylim(-0.5, 9)
    ax.set_xlabel("Horizonte h (días después del último precio conocido)")
    ax.set_ylabel("Mejora frente al\ningenuo del día (%)")
    ax.legend(fontsize=7.5, loc="upper right")
    fig.savefig(FIG / "f19_sarimax_validacion.png")
    plt.close(fig)


# ----------------------------------------------------------------------------- residuos del modelo final
def residuos():
    r = pd.read_csv(FIG / "datos_sarimax_residuos.csv")
    lb = r.groupby("hora")["ljung_box_p"].first()
    fac = r.groupby("rezago")["fac"].mean()
    banda = 1.96 / np.sqrt(N_DIAS - 1)

    fig, ejes = plt.subplots(1, 2, figsize=(7.6, 2.8), gridspec_kw=dict(width_ratios=[1.15, 1], wspace=0.3))
    ax = ejes[0]
    ax.bar(lb.index, lb.values, color=[ROJO if p < 0.05 else VERDE for p in lb], width=0.7)
    ax.legend(handles=[Patch(color=VERDE, label="p ≥ 0,05"), Patch(color=ROJO, label="p < 0,05")], fontsize=7,
              loc="upper right", handlelength=1.2)
    ax.axhline(0.05, color=TINTA, lw=0.9, ls="--")
    ax.text(24.6, 0.07, "0,05", fontsize=7, color=TINTA, va="bottom", ha="right")
    ax.set_xticks([1, 6, 12, 18, 24])
    ax.set_xlabel("Hora del día")
    ax.set_ylabel("Valor p")
    ax.set_title("a) Ljung-Box con 14 rezagos", loc="left", fontsize=10)
    ax = ejes[1]
    k = fac.index.values
    # los rezagos semanales en verde agua y los que se salen de la banda en rojo
    ax.axhspan(-banda, banda, color=BANDA, lw=0, zorder=0)
    ax.bar(k, fac.values, color=[ROJO if abs(v) > banda else VERDE if x % 7 == 0 else claro(VERDE, 0.45)
                                 for x, v in zip(k, fac.values)], width=0.7, zorder=2)
    ax.axhline(0, color=TENUE, lw=0.6)
    ax.set_xticks([1, 7, 14, 21, 28])
    ax.set_xlabel("Rezago (días)")
    ax.set_title("b) Autocorrelación de los residuos", loc="left", fontsize=10)
    fig.savefig(FIG / "f20_sarimax_residuos.png")
    plt.close(fig)
    print("Ljung-Box p < 0,05 en las horas:", lb[lb < 0.05].round(4).to_dict())
    print("fac media, rezagos 7, 14, 21, 28:", fac.loc[[7, 14, 21, 28]].round(3).to_dict(), "banda", round(banda, 3))
    print("rezagos fuera de la banda:", fac[fac.abs() > banda].round(3).to_dict())


if __name__ == "__main__":
    preblanqueo()
    validacion()
    residuos()
