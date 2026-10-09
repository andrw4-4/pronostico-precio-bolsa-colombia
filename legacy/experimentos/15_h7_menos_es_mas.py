"""
================================================================================
HORIZONTE DE 7 DIAS — ¿menos variables es mas?
================================================================================

Tres veces seguidas agregar informacion no mejoro nada:

  58 -> 104 variables        RMSE 0.1641 -> 0.1642
  + bloque ENSO (a 7 dias)   sin cambio
  + bloque de lluvia         sin cambio, MAPE levemente peor

Y las importancias del modelo a 7 dias estan planas: de 0,0127 a 0,0089
repartidas entre 458 variables. El sintoma es de DILUCION, no de falta de
informacion.

Este script prueba lo contrario de todo lo que hicimos hasta ahora: en vez de
sumar variables, quitarlas. Se recorre una escalera de tamanios (5, 10, 15, ...
hasta todas) y se mide donde esta el optimo.

COMO SE ELIGEN LAS VARIABLES
----------------------------
Con el objetivo a 7 DIAS (no a 1, que es como se habia hecho), y usando SOLO la
ventana de seleccion (2015-2019). Dos criterios complementarios que se promedian
por rango:

  Lasso      penalizacion L1 con validacion cruzada temporal y gap=7. Ordena por
             magnitud del coeficiente. Es lineal, asi que ve senal lineal.
  XGBoost    ganancia acumulada de un modelo entrenado en la misma ventana.
             Captura no linealidades e interacciones.

Promediar los rangos evita quedarse con los sesgos de uno solo: el Lasso ignora
interacciones, la ganancia de XGBoost premia variables continuas.

ANTI-FUGA
---------
La seleccion ve SOLO hasta 2019-12-31. El entrenamiento llega hasta h dias antes
del inicio de cada periodo de prueba. 2026 no se toca hasta la medicion final.

Uso
---
  python 15_h7_menos_es_mas.py
================================================================================
"""

import importlib.util
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

H = 7
SEMILLAS = [42, 7, 123, 2024, 99]
ESCALERA = [3, 5, 8, 12, 20, 30, 50, 100, 200, None]   # None = todas
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

SIN_2026 = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]


def ranquear(X_sel, y_sel, semilla=42):
    """Ordena las variables combinando Lasso y ganancia de XGBoost."""
    tscv = TimeSeriesSplit(n_splits=3, gap=H)

    esc = StandardScaler().fit(X_sel)
    Xs = esc.transform(X_sel)

    t = time.time()
    lasso = LassoCV(cv=tscv, max_iter=20000, random_state=semilla, n_jobs=-1).fit(Xs, y_sel)
    r_lasso = pd.Series(np.abs(lasso.coef_), index=X_sel.columns).rank(ascending=False)
    print(f"  lasso: alpha={lasso.alpha_:.5f}, "
          f"{int((lasso.coef_ != 0).sum())} no nulos  [{time.time()-t:.0f}s]", flush=True)

    t = time.time()
    mod = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.03,
                           subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
                           reg_lambda=3.0, random_state=semilla, n_jobs=-1,
                           tree_method="hist").fit(X_sel, y_sel)
    r_xgb = pd.Series(mod.feature_importances_, index=X_sel.columns).rank(ascending=False)
    print(f"  xgboost: ganancia calculada  [{time.time()-t:.0f}s]", flush=True)

    combinado = ((r_lasso + r_xgb) / 2).sort_values()
    return combinado, r_lasso, r_xgb


def evaluar(pred, prueba, precio, h):
    precio_hoy = precio.reindex(prueba.index)
    precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=h))
    precio_fut.index = prueba.index
    ok = precio_fut.notna()
    m = h10.metricas(prueba["y"][ok], pred[ok], precio_hoy[ok], precio_fut[ok])
    i = h10.metricas(prueba["y"][ok], np.zeros(int(ok.sum())),
                     precio_hoy[ok], precio_fut[ok])
    dm, p = h10.diebold_mariano((prueba["y"] - pred)[ok], prueba["y"][ok], h=h)
    return {"n": int(ok.sum()), "RMSE": m["RMSE_log"], "RMSE_ing": i["RMSE_log"],
            "mejora_%": 100 * (m["RMSE_log"] / i["RMSE_log"] - 1),
            "MAPE_%": m["MAPE_nivel_%"], "MAPE_ing_%": i["MAPE_nivel_%"],
            "Direccion_%": m["Direccion_%"], "DM": dm, "p_DM": p}


def main():
    print("=" * 82)
    print(f"h = {H} DIAS — ¿menos variables es mas?")
    print("=" * 82)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in SIN_2026 if c in df.columns])

    X, precio, log_precio = h10.construir_features(df)
    X_ref = X.loc[:h10.FIN_SELECCION].dropna()
    COLUMNAS = h10.limpiar(X_ref)
    print(f"[limpieza] {X.shape[1]} -> {len(COLUMNAS)} caracteristicas")

    y_h = (log_precio.shift(-H) - log_precio).rename("y")
    datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

    # --- seleccion: SOLO la ventana hasta 2019 --------------------------------
    sel = datos.loc[:h10.FIN_SELECCION]
    print(f"[seleccion] {len(sel)} obs, hasta {sel.index.max().date()} "
          f"(objetivo a {H} dias)")
    orden, r_lasso, r_xgb = ranquear(sel[COLUMNAS], sel["y"])

    print(f"\n[top 20 para h={H}]")
    for i, v in enumerate(orden.index[:20], 1):
        print(f"  {i:2d}. {v:34s} (lasso #{int(r_lasso[v]):3d}, xgb #{int(r_xgb[v]):3d})")

    orden.to_csv(SALIDA / f"h{H}_ranking_variables.csv")
    params = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))[str(H)]

    filas = []
    for etapa, ini, fin in [
        ("2023-2025", INI_PRUEBA, INI_2026 - pd.Timedelta(days=1)),
        ("2026", INI_2026, datos.index.max()),
    ]:
        fin_entrena = ini - pd.Timedelta(days=H + 1)
        entrena = datos.loc[:fin_entrena]
        prueba = datos.loc[ini:fin]
        if len(prueba) < 30:
            continue
        print(f"\n--- {etapa}: entrena {len(entrena)} obs, prueba {len(prueba)} ---")

        for k in ESCALERA:
            cols = list(orden.index) if k is None else list(orden.index[:k])
            preds = []
            for s in SEMILLAS:
                mod = xgb.XGBRegressor(**params, random_state=s, n_jobs=-1,
                                       tree_method="hist")
                mod.fit(entrena[cols], entrena["y"])
                preds.append(mod.predict(prueba[cols]))
            pred = pd.Series(np.mean(preds, axis=0), index=prueba.index)

            r = evaluar(pred, prueba, precio, H)
            r.update({"etapa": etapa, "k": len(cols)})
            filas.append(r)
            print(f"  k={len(cols):3d}  RMSE {r['RMSE']:.4f} ({r['mejora_%']:+6.2f}%)  "
                  f"MAPE {r['MAPE_%']:5.2f}% vs {r['MAPE_ing_%']:5.2f}%  "
                  f"dir {r['Direccion_%']:5.1f}%  p={r['p_DM']:.4f}", flush=True)

    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / f"h{H}_escalera.csv", index=False)

    print("\n" + "=" * 82)
    print("RESUMEN: mejora sobre el ingenuo (%) segun numero de variables")
    print("=" * 82)
    piv = tabla.pivot_table(index="k", columns="etapa", values="mejora_%")
    dirp = tabla.pivot_table(index="k", columns="etapa", values="Direccion_%")
    pp = tabla.pivot_table(index="k", columns="etapa", values="p_DM")
    res = pd.concat([piv.add_prefix("mejora "), dirp.add_prefix("dir "),
                     pp.add_prefix("p ")], axis=1)
    print(res.round(3).to_string())

    graficar(tabla)
    print(f"\n[salida] {SALIDA/f'h{H}_escalera.csv'}, {SALIDA/f'h{H}_escalera.png'}")


def graficar(tabla):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for etapa, color in [("2023-2025", "tab:blue"), ("2026", "tab:red")]:
        s = tabla[tabla["etapa"] == etapa].sort_values("k")
        if s.empty:
            continue
        ax[0].plot(s["k"], s["mejora_%"], marker="o", color=color, label=etapa)
        ax[1].plot(s["k"], s["Direccion_%"], marker="o", color=color, label=etapa)
        ax[2].plot(s["k"], s["p_DM"], marker="o", color=color, label=etapa)
    ax[0].axhline(0, color="k", lw=0.8, ls="--")
    ax[0].set_ylabel("mejora sobre el ingenuo (%)\nmenos es mejor")
    ax[1].axhline(50, color="k", lw=0.8, ls="--")
    ax[1].set_ylabel("acierto de direccion (%)")
    ax[2].axhline(0.05, color="k", lw=0.8, ls="--")
    ax[2].set_ylabel("p-valor Diebold-Mariano")
    for a in ax:
        a.set_xscale("log")
        a.set_xlabel("numero de variables")
        a.legend(fontsize=8)
    plt.suptitle(f"h = {H} dias: ¿cuantas variables conviene usar?")
    plt.tight_layout()
    plt.savefig(SALIDA / f"h{H}_escalera.png", dpi=110)


if __name__ == "__main__":
    main()
