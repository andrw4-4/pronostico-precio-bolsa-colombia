"""
================================================================================
HORIZONTE DE 7 DIAS — ¿aporta el bloque de lluvia?
================================================================================

Se compara el mismo modelo con tres conjuntos de variables, cambiando UNA sola
cosa cada vez, y se mide en dos periodos: 2023-2025 y 2026 (fuera de muestra
puro).

  BASE      todo menos lluvia y menos ENSO semanal
  ENSO      BASE + bloque ENSO semanal
  COMPLETO  ENSO + bloque de lluvia sobre cuencas

Los hiperparametros se leen de salidas_horizontes/hiperparametros.json (elegidos
con datos hasta 2025) y NO se vuelven a buscar: cambiar hiperparametros y
variables a la vez haria imposible atribuir la diferencia.

Uso
---
  python 14_h7_con_lluvia.py
================================================================================
"""

import importlib.util
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

H = 7
SEMILLAS = [42, 7, 123, 2024, 99]     # se promedian: reduce varianza (solucion 4)
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

SIN_2026 = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]

PREF_LLUVIA = ("lluvia_",)
PREF_ENSO = ("nino12_", "nino3_", "nino34_", "nino4_", "nino_", "roni")


def grupo(col):
    if col.startswith(PREF_LLUVIA):
        return "lluvia"
    if col.startswith(PREF_ENSO):
        return "enso"
    return "base"


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
    print("=" * 80)
    print(f"HORIZONTE h = {H} DIAS — aporte del bloque de lluvia")
    print("=" * 80)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in SIN_2026 if c in df.columns])

    X, precio, log_precio = h10.construir_features(df)
    X_ref = X.loc[:h10.FIN_SELECCION].dropna()
    COLUMNAS = h10.limpiar(X_ref)

    g = pd.Series({c: grupo(c) for c in COLUMNAS})
    conjuntos = {
        "BASE":     [c for c in COLUMNAS if g[c] == "base"],
        "ENSO":     [c for c in COLUMNAS if g[c] in ("base", "enso")],
        "COMPLETO": COLUMNAS,
    }
    print(f"[grupos]  base {sum(g=='base')} | enso {sum(g=='enso')} | "
          f"lluvia {sum(g=='lluvia')}\n")

    params = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))[str(H)]
    print(f"[params]  {params}\n")

    y_h = (log_precio.shift(-H) - log_precio).rename("y")
    datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

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

        for nombre, cols in conjuntos.items():
            # promedio de varias semillas
            preds = []
            for s in SEMILLAS:
                mod = xgb.XGBRegressor(**params, random_state=s, n_jobs=-1,
                                       tree_method="hist")
                mod.fit(entrena[cols], entrena["y"])
                preds.append(mod.predict(prueba[cols]))
            pred = pd.Series(np.mean(preds, axis=0), index=prueba.index)

            r = evaluar(pred, prueba, precio, H)
            r.update({"etapa": etapa, "conjunto": nombre, "n_vars": len(cols)})
            filas.append(r)
            print(f"  {etapa:10s} {nombre:9s} ({len(cols):3d} vars)  "
                  f"RMSE {r['RMSE']:.4f} ({r['mejora_%']:+6.2f}%)  "
                  f"MAPE {r['MAPE_%']:5.2f}% vs {r['MAPE_ing_%']:5.2f}%  "
                  f"dir {r['Direccion_%']:5.1f}%  p={r['p_DM']:.4f}", flush=True)
        print()

    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / f"h{H}_comparacion_bloques.csv", index=False)

    print("=" * 80)
    print("APORTE DE CADA BLOQUE (cambio frente al conjunto anterior)")
    print("=" * 80)
    for etapa in ["2023-2025", "2026"]:
        sub = tabla[tabla["etapa"] == etapa].set_index("conjunto")
        if len(sub) < 3:
            continue
        print(f"\n--- {etapa} ---")
        print(f"  BASE      -> ENSO      MAPE {sub.loc['BASE','MAPE_%']:.2f} -> "
              f"{sub.loc['ENSO','MAPE_%']:.2f}   "
              f"dir {sub.loc['BASE','Direccion_%']:.1f} -> {sub.loc['ENSO','Direccion_%']:.1f}")
        print(f"  ENSO      -> COMPLETO  MAPE {sub.loc['ENSO','MAPE_%']:.2f} -> "
              f"{sub.loc['COMPLETO','MAPE_%']:.2f}   "
              f"dir {sub.loc['ENSO','Direccion_%']:.1f} -> "
              f"{sub.loc['COMPLETO','Direccion_%']:.1f}")

    print(f"\n[salida] {SALIDA/f'h{H}_comparacion_bloques.csv'}")


if __name__ == "__main__":
    main()
