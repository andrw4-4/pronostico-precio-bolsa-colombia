"""Figuras de la sección 3.5, XGBoost: cuántas columnas usar y qué columnas usa cada modelo. Las etapas de la
construcción ahora están hechas con formas de Word (diagramas_word.py).
Los datos salen de paneles/panel_horario_modelo_validacion.csv y panel_horario_modelo_columnas.csv, que
escribió 2d_seleccion_variables.py."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from estilo_graficas import COLORES, TENUE, TINTA, aplicar, claro

aplicar()
RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "informe" / "figuras"
PANELES = RAIZ / "paneles"
NARANJA = COLORES["XGBoost"]

NOMBRES = {
    "lp": "Precio del día t",
    "dlp_dia": "Precio frente a la media de su día",
    "dlp_ultima": "Precio frente a la última hora del día",
    "dlp_ma7d_mh": "Precio frente a su media de 7 días",
    "dlp_ma30d_mh": "Precio frente a su media de 30 días",
    "dlp_ma168h": "Precio frente a la media de 168 horas",
    "dlp_max_24h": "Distancia al máximo de 24 horas",
    "dlp_max_7d": "Distancia al máximo de 7 días",
    "dlp_l7d": "Cambio frente a hace 7 días",
    "dlp_l14d": "Cambio frente a hace 14 días",
    "dlp_l28d": "Cambio frente a hace 28 días",
    "dia_semana_h3": "Día de la semana pronosticado",
    "es_festivo_h7": "Festivo el día pronosticado",
    "margen_ofertado_l3d": "Margen ofertado, hace 3 días",
    "aportes_pct_sistema_delta_7d": "Aportes hídricos, cambio en 7 días",
    "aportes_pct_sistema_l0d": "Aportes hídricos, hoy",
    "presion_hidro_horaria_ultima": "Presión sobre el agua",
    "frac_gen_carbon_ma30d": "Generación con carbón, media de 30 días",
    "margen_decl_pron_l14d": "Margen declarado, hace 14 días",
    "demanda_l14d": "Demanda, hace 14 días",
    "brecha_escasez_l0h": "Distancia al precio de escasez",
    "co2_liquidos_frac_sd168h": "Emisiones de líquidos, variabilidad",
    "disp_decl_despacho_central_rel_sd30d": "Disponibilidad declarada, variabilidad",
}


# ----------------------------------------------------------------------------- cuántas columnas
def columnas():
    v = pd.read_csv(PANELES / "panel_horario_modelo_validacion.csv")
    fig, ejes = plt.subplots(1, 5, figsize=(7.6, 2.7), sharey=True, gridspec_kw=dict(wspace=0.12))
    for ax, h in zip(ejes, range(3, 8)):
        d = v[v.h == h].reset_index(drop=True)
        x = np.arange(len(d))
        mejor = d.loc[d.mejor]
        limite = np.sqrt(mejor.mse_log.iloc[0] + mejor.ee.iloc[0])
        ax.axhline(d.rmse_log_ingenuo.iloc[0], color=COLORES["Ingenuo del día"], **{"lw": 1.2, "ls": "--"})
        ax.axhline(limite, color=TINTA, lw=1.0, ls=":")
        ax.plot(x, d.rmse_log, color=claro(NARANJA, 0.55), lw=1.2, zorder=2)
        ax.scatter(x, d.rmse_log, s=16, color=claro(NARANJA, 0.55), zorder=3)
        e = d.index[d.elegido][0]
        ax.scatter([e], [d.rmse_log[e]], s=40, color=NARANJA, zorder=4)
        ax.set_xticks(x, d.k.astype(int).astype(str), fontsize=7)
        ax.set_title(f"h = {h}", fontsize=9.5)
        ax.set_xlabel("k", fontsize=8)
    ejes[0].set_ylabel("RMSE en logaritmo, 2020-2022")
    ejes[0].plot([], [], color=COLORES["Ingenuo del día"], lw=1.2, ls="--", label="Ingenuo del día")
    ejes[0].plot([], [], color=TINTA, lw=1.0, ls=":", label="Mejor más un error estándar")
    ejes[0].scatter([], [], s=40, color=NARANJA, label="Elegido")
    fig.legend(*ejes[0].get_legend_handles_labels(), loc="lower center", ncol=3, fontsize=7.5,
               bbox_to_anchor=(0.5, -0.1))
    fig.savefig(FIG / "f22_xgboost_columnas.png")
    plt.close(fig)
    print(v[v.h.between(3, 7)][["h", "k", "rmse_log", "rmse_log_ingenuo", "elegido"]].round(3).to_string(index=False))


# ----------------------------------------------------------------------------- importancia de las columnas
def importancia():
    c = pd.read_csv(PANELES / "panel_horario_modelo_columnas.csv")
    fig, ejes = plt.subplots(1, 2, figsize=(7.6, 3.6), gridspec_kw=dict(wspace=1.25))
    for ax, h in zip(ejes, [3, 7]):
        x = c[c[f"entra_h{h}"]].nlargest(12, f"importancia_h{h}").iloc[::-1]
        color = [COLORES["Precio real"] if (t == "precio" or n == "lp") else claro(NARANJA, 0.4) if t == "fija"
                 else NARANJA for n, t in zip(x.columna, x.tipo)]
        ax.barh(range(len(x)), x[f"importancia_h{h}"], color=color, height=0.7)
        ax.set_yticks(range(len(x)), [NOMBRES.get(n, n) for n in x.columna], fontsize=6.8)
        ax.set_title(f"{'a' if h == 3 else 'b'}) h = {h}", loc="left", fontsize=10)
        ax.set_xlabel("Promedio de |SHAP|", fontsize=8)
        ax.tick_params(axis="x", labelsize=7)
    fig.legend(handles=[Patch(color=COLORES["Precio real"], label="Precio"), Patch(color=NARANJA, label="Sistema"),
                        Patch(color=claro(NARANJA, 0.4), label="Calendario")],
               loc="lower center", ncol=3, fontsize=7.5, bbox_to_anchor=(0.55, -0.06))
    fig.savefig(FIG / "f23_xgboost_importancia.png")
    plt.close(fig)
    falta = {n for h in [3, 7] for n in c[c[f"entra_h{h}"]].nlargest(12, f"importancia_h{h}").columna} - set(NOMBRES)
    print("sin nombre:", falta)


if __name__ == "__main__":
    columnas()
    importancia()
