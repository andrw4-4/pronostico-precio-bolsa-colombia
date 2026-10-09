"""
================================================================================
MODELO FINAL A 7 DIAS — protocolo limpio de punta a punta
================================================================================

En el script anterior elegi k=100 mirando la columna de 2026. Eso contamina el
conjunto de prueba: si se prueban diez valores de k y se reporta el mejor, el
"mejor" incluye la suerte de ese periodo.

Aqui cada decision se toma en una ventana que no se vuelve a usar:

  SELECCION   2015-2019   se ordenan las variables (Lasso + ganancia XGBoost)
                          con el objetivo a 7 dias
  VALIDACION  2020-2022   se elige k, el numero de variables
  PRUEBA A    2023-2025   primera medicion
  PRUEBA B    2026        medicion final, fuera de muestra puro

El valor de k sale de la validacion y no se vuelve a tocar. Lo que 2026 diga es
lo que hay.

Uso
---
  python 16_modelo_final_h7.py
================================================================================
"""

import importlib.util
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

H = 7
SEMILLAS = [42, 7, 123, 2024, 99]
ESCALERA = [5, 12, 20, 30, 50, 100, 200, None]

INI_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

SIN_2026 = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]


def predecir(entrena, prueba, cols, params):
    preds = []
    for s in SEMILLAS:
        m = xgb.XGBRegressor(**params, random_state=s, n_jobs=-1, tree_method="hist")
        m.fit(entrena[cols], entrena["y"])
        preds.append(m.predict(prueba[cols]))
    return pd.Series(np.mean(preds, axis=0), index=prueba.index)


def evaluar(pred, prueba, precio):
    precio_hoy = precio.reindex(prueba.index)
    precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=H))
    precio_fut.index = prueba.index
    ok = precio_fut.notna()
    m = h10.metricas(prueba["y"][ok], pred[ok], precio_hoy[ok], precio_fut[ok])
    i = h10.metricas(prueba["y"][ok], np.zeros(int(ok.sum())),
                     precio_hoy[ok], precio_fut[ok])
    dm, p = h10.diebold_mariano((prueba["y"] - pred)[ok], prueba["y"][ok], h=H)
    return {"n": int(ok.sum()), "RMSE": m["RMSE_log"], "RMSE_ing": i["RMSE_log"],
            "mejora_%": 100 * (m["RMSE_log"] / i["RMSE_log"] - 1),
            "MAPE_%": m["MAPE_nivel_%"], "MAPE_ing_%": i["MAPE_nivel_%"],
            "Direccion_%": m["Direccion_%"], "DM": dm, "p_DM": p}


def main():
    print("=" * 80)
    print(f"MODELO FINAL A {H} DIAS")
    print("=" * 80)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in SIN_2026 if c in df.columns])
    X, precio, log_precio = h10.construir_features(df)
    COLUMNAS = h10.limpiar(X.loc[:h10.FIN_SELECCION].dropna())

    y_h = (log_precio.shift(-H) - log_precio).rename("y")
    datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

    orden = pd.read_csv(SALIDA / f"h{H}_ranking_variables.csv",
                        index_col=0).iloc[:, 0].sort_values()
    params = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))[str(H)]

    # ================= PASO 1: elegir k en VALIDACION 2020-2022 =================
    print("\n" + "-" * 80)
    print("PASO 1 — elegir k en la validacion (2020-2022). 2023+ no se toca.")
    print("-" * 80)
    ent_val = datos.loc[:INI_VALIDACION - pd.Timedelta(days=H + 1)]
    val = datos.loc[INI_VALIDACION:FIN_VALIDACION]

    filas_val = []
    for k in ESCALERA:
        cols = list(orden.index) if k is None else list(orden.index[:k])
        r = evaluar(predecir(ent_val, val, cols, params), val, precio)
        r["k"] = len(cols)
        filas_val.append(r)
        print(f"  k={len(cols):3d}  RMSE {r['RMSE']:.4f} ({r['mejora_%']:+6.2f}%)  "
              f"MAPE {r['MAPE_%']:5.2f}%  dir {r['Direccion_%']:5.1f}%", flush=True)

    tabla_val = pd.DataFrame(filas_val)
    K = int(tabla_val.loc[tabla_val["mejora_%"].idxmin(), "k"])
    print(f"\n  ==> k elegido por la validacion: {K}")
    print("      (no se vuelve a cambiar)")

    cols = list(orden.index[:K]) if K < len(orden) else list(orden.index)

    print(f"\n  Las {min(15, K)} variables principales del modelo final:")
    for i, v in enumerate(cols[:15], 1):
        print(f"    {i:2d}. {v}")

    # ================= PASO 2: medir en 2023-2025 y en 2026 ====================
    print("\n" + "-" * 80)
    print("PASO 2 — medicion")
    print("-" * 80)

    filas = []
    for etapa, ini, fin in [("2023-2025", INI_PRUEBA, INI_2026 - pd.Timedelta(days=1)),
                            ("2026", INI_2026, datos.index.max())]:
        entrena = datos.loc[:ini - pd.Timedelta(days=H + 1)]
        prueba = datos.loc[ini:fin]
        pred = predecir(entrena, prueba, cols, params)
        r = evaluar(pred, prueba, precio)
        r.update({"etapa": etapa, "k": K, "n_entrena": len(entrena)})
        filas.append(r)
        print(f"\n  {etapa}  (entrena {len(entrena)} obs hasta "
              f"{entrena.index.max().date()}, prueba {r['n']} dias)")
        print(f"    RMSE Δlog      {r['RMSE']:.4f}  vs ingenuo {r['RMSE_ing']:.4f}"
              f"   ({r['mejora_%']:+.2f}%)")
        print(f"    MAPE nivel     {r['MAPE_%']:.2f}%  vs ingenuo {r['MAPE_ing_%']:.2f}%")
        print(f"    Direccion      {r['Direccion_%']:.1f}%")
        print(f"    Diebold-Mariano  DM={r['DM']:+.3f}  p={r['p_DM']:.4f}")
        if etapa == "2026":
            pred_2026, prueba_2026 = pred, prueba

    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / f"modelo_final_h{H}.csv", index=False)
    tabla_val.to_csv(SALIDA / f"modelo_final_h{H}_validacion.csv", index=False)

    # ================= PASO 3: ¿replico el efecto? =============================
    a = tabla[tabla["etapa"] == "2023-2025"].iloc[0]
    b = tabla[tabla["etapa"] == "2026"].iloc[0]
    print("\n" + "=" * 80)
    print("¿REPLICO EL EFECTO EN 2026?")
    print("=" * 80)
    dm_esp = a["DM"] * np.sqrt(b["n"] / a["n"])
    p_esp = 2 * (1 - stats.t.cdf(abs(dm_esp), df=b["n"] - 1))
    print(f"  Si el efecto de 2026 fuera IGUAL al de 2023-2025, con {b['n']:.0f} dias")
    print(f"  en vez de {a['n']:.0f} esperariamos DM={dm_esp:+.3f} (p={p_esp:.3f}).")
    print(f"  Observado en 2026: DM={b['DM']:+.3f} (p={b['p_DM']:.3f}).")
    veredicto = ("el efecto replico con igual o mayor fuerza"
                 if abs(b["DM"]) >= abs(dm_esp) else "el efecto fue mas debil")
    print(f"  ==> {veredicto}")

    graficar(pred_2026, prueba_2026, precio, tabla)
    print(f"\n[salida] {SALIDA/f'modelo_final_h{H}.csv'}, "
          f"{SALIDA/f'modelo_final_h{H}.png'}")


def graficar(pred, prueba, precio, tabla):
    objetivo = prueba.index + pd.Timedelta(days=H)
    real = precio.reindex(objetivo)
    hoy = precio.reindex(prueba.index)
    nivel = hoy.values * np.exp(pred.values)

    fig, ax = plt.subplots(2, 1, figsize=(13, 8))
    ax[0].plot(objetivo, real.values, color="k", lw=1.1, label="real")
    ax[0].plot(objetivo, nivel, color="tab:red", lw=1.1, label=f"pronostico a {H} dias")
    ax[0].plot(objetivo, hoy.values, color="tab:blue", lw=0.9, ls="--",
               label="ingenuo (precio de hoy)")
    f = tabla[tabla["etapa"] == "2026"].iloc[0]
    ax[0].set_title(f"2026 — MAPE {f['MAPE_%']:.1f}% vs {f['MAPE_ing_%']:.1f}% del ingenuo   "
                    f"direccion {f['Direccion_%']:.1f}%")
    ax[0].set_ylabel("COP/kWh"); ax[0].legend(fontsize=8)

    err_m = (real.values - nivel)
    err_i = (real.values - hoy.values)
    ax[1].plot(objetivo, pd.Series(np.abs(err_m)).rolling(21).mean().values,
               color="tab:red", label="error abs. del modelo (media 21d)")
    ax[1].plot(objetivo, pd.Series(np.abs(err_i)).rolling(21).mean().values,
               color="tab:blue", ls="--", label="error abs. del ingenuo")
    ax[1].set_ylabel("COP/kWh"); ax[1].legend(fontsize=8)
    ax[1].set_title("Cuando el modelo gana y cuando pierde")
    plt.tight_layout()
    plt.savefig(SALIDA / f"modelo_final_h{H}.png", dpi=110)


if __name__ == "__main__":
    main()
