"""
Paso 9c: todos los modelos en las mismas filas, combinaciones y Diebold-Mariano entre pares.

    python 9c_comparacion_revision.py

No entrena nada. Junta los pronósticos de los tres modelos de la tesis con los que se agregaron en
la revisión del 26 de noviembre de 2026 (LEAR, XGBoost con la información alineada, la LSTM con
solo precio y calendario) y dos combinaciones sin parámetros:

    Promedio de los tres          promedio simple de SARIMAX, XGBoost y la LSTM, en logaritmo
    Nivel LSTM y forma XGBoost    el promedio de las 24 horas de la LSTM más la forma de XGBoost

Escribe en resultados/revision/:
    todos_criterio.csv         el criterio de la tesis para cada modelo, periodo y bloque
    todos_nivel_forma.csv      el error partido en nivel del día y forma
    todos_pares.csv            Diebold-Mariano entre todos los pares, con la corrección de Harvey et al.
    dos_por_dos.csv            modelo (XGBoost o LSTM) por información (cortada en t o alineada)
    dm_pares_<periodo>.png     el mapa de valores p, como en Lago et al. (2021)

Fuentes: Bates y Granger (1969); Diebold y Mariano (1995); Harvey et al. (1997); Lago et al. (2021).
"""
import sys
import warnings
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
SALIDA = ev.RES / "revision"
SALIDA.mkdir(parents=True, exist_ok=True)
L, H = max(ev.HS) - 1 + 7, max(ev.HS)
# las cuatro celdas de la comparación entre modelo e información
CELDAS = {("XGBoost", "cortada en t"): "XGBoost", ("XGBoost", "alineada"): "XGBoost alineado",
          ("LSTM", "cortada en t"): "LSTM bloques 1 y 2", ("LSTM", "alineada"): "LSTM"}
ORDEN = ["SARIMAX", "LEAR", "XGBoost", "LSTM bloques 1 y 2", "LEAR alineado", "XGBoost alineado", "LSTM",
         "Promedio de los tres", "Nivel LSTM y forma XGBoost"]


def mapa(pares, modelos, periodo):
    """Valor p de que el modelo de la columna tenga menos error que el de la fila (una cola), como en Lago et al."""
    n = len(modelos)
    P = np.full((n, n), np.nan)
    for _, r in pares.iterrows():
        i, j = modelos.index(r["a"]), modelos.index(r["b"])
        una_cola = r["p_hln"] / 2 if r["t_hln"] < 0 else 1 - r["p_hln"] / 2      # H1: a tiene menos error que b
        P[j, i], P[i, j] = una_cola, 1 - una_cola
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    im = ax.imshow(np.clip(P, 0, 0.10), cmap="Greens_r", vmin=0, vmax=0.10)
    ax.set_xticks(range(n), modelos, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n), modelos, fontsize=8)
    for i in range(n):
        for j in range(n):
            if i != j:
                ax.text(j, i, f"{P[i, j]:.2f}".replace(".", ","), ha="center", va="center", fontsize=7,
                        color="white" if P[i, j] < 0.05 else "black")
    ax.set_title(f"Diebold-Mariano entre modelos, {periodo}\n"
                 "valor p de que el modelo de la columna tenga menos error que el de la fila", fontsize=9, loc="left")
    fig.colorbar(im, ax=ax, fraction=0.04, label="valor p (0,10 o más en blanco)")
    fig.tight_layout()
    fig.savefig(SALIDA / f"dm_pares_{periodo.replace('-', '_')}.png", dpi=200)
    plt.close(fig)


def main():
    criterios, formas, todos_pares, celdas = [], [], [], []
    for periodo in ev.PERIODOS:
        d = ev.tabla_modelos(periodo)
        modelos = [m for m in ORDEN if m in d.columns]
        for m in modelos:
            criterios.append(ev.criterio(d, m).assign(periodo=periodo, modelo=m))
            nivel, forma = ev.nivel_y_forma(d, m)
            formas.append({"periodo": periodo, "modelo": m, "rmse": ev.rmse(d["y"] - d[m]), "nivel": nivel, "forma": forma,
                           "mediana_abs": float((d["y"] - d[m]).abs().median())})
        nivel, forma = ev.nivel_y_forma(d, "Ingenuo del día")
        formas.append({"periodo": periodo, "modelo": "Ingenuo del día", "rmse": ev.rmse(d["y"]), "nivel": nivel,
                       "forma": forma, "mediana_abs": float(d["y"].abs().median())})
        pares = []
        for a, b in combinations(modelos, 2):
            dm = ev.diebold_mariano(d["y"] - d[a], d["y"] - d[b], d["fecha"], L, h=H)
            pares.append({"periodo": periodo, "a": a, "b": b, "t": dm["t"], "p": dm["p"], "t_hln": dm["t_hln"],
                          "p_hln": dm["p_hln"], "menor_error": a if dm["t"] < 0 else b})
        pares = pd.DataFrame(pares)
        todos_pares.append(pares)
        mapa(pares, modelos, periodo)
        for (modelo, informacion), columna in CELDAS.items():
            if columna in d.columns:
                c = ev.criterio(d, columna, {"h = 3 a 9": ev.HS}).iloc[0]
                celdas.append({"periodo": periodo, "modelo": modelo, "informacion": informacion, "rmse": c["rmse"],
                               "mejora": c["mejora"], "dm_p_hln_ingenuo": c["dm_p_hln"]})
    crit = pd.concat(criterios).reset_index().set_index(["periodo", "modelo", "bloque"])
    crit.to_csv(SALIDA / "todos_criterio.csv", float_format="%.6g")
    pd.DataFrame(formas).to_csv(SALIDA / "todos_nivel_forma.csv", index=False, float_format="%.6g")
    pares = pd.concat(todos_pares, ignore_index=True)
    pares.to_csv(SALIDA / "todos_pares.csv", index=False, float_format="%.6g")
    semana = crit.xs("h = 3 a 9", level="bloque")
    print(semana[["origenes", "rmse", "rmse_ingenuo", "mejora", "dm_p_hln", "cumple_hln"]].round(4).to_string())
    print(pd.DataFrame(formas).round(4).to_string(index=False))
    if celdas:
        c = pd.DataFrame(celdas)
        # Diebold-Mariano entre celdas de la misma fila y de la misma columna
        filas = []
        for periodo, g in c.groupby("periodo"):
            for (m1, i1), (m2, i2) in combinations(list(CELDAS), 2):
                if (m1 == m2 or i1 == i2) and {CELDAS[(m1, i1)], CELDAS[(m2, i2)]} <= set(pares.loc[pares["periodo"] == periodo, ["a", "b"]].to_numpy().ravel()):
                    a, b = CELDAS[(m1, i1)], CELDAS[(m2, i2)]
                    r = pares[(pares["periodo"] == periodo) & (((pares["a"] == a) & (pares["b"] == b)) | ((pares["a"] == b) & (pares["b"] == a)))].iloc[0]
                    filas.append({"periodo": periodo, "comparacion": f"{a} y {b}", "menor_error": r["menor_error"],
                                  "p_hln": r["p_hln"]})
        c.to_csv(SALIDA / "dos_por_dos.csv", index=False, float_format="%.6g")
        pd.DataFrame(filas).to_csv(SALIDA / "dos_por_dos_pares.csv", index=False, float_format="%.6g")
        print(c.round(4).to_string(index=False))
        print(pd.DataFrame(filas).round(4).to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
