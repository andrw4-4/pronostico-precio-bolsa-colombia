"""
================================================================================
¿CUANTO DEL PODER PREDICTIVO ES SOLO AUTOCORRELACION?
================================================================================

La sospecha: a un dia el modelo acierta porque el precio de hoy se parece al de
ayer, no porque entienda el sistema electrico. Si es asi, el modelo no sirve para
decidir nada: para cuando te enteras, ya no hay holgura para actuar.

El experimento separa las caracteristicas en dos familias y entrena por separado:

  PRECIO     rezagos del propio precio, su volatilidad y sus choques
             (dlog_lag*, dlog_sd*, precio_choque*)
  SISTEMA    todo lo demas: hidrologia, oferta, demanda, generacion,
             concentracion, calendario, perfil intradiario
  TODO       las dos juntas

Si PRECIO solo ya alcanza el desempeno de TODO, la respuesta es que si: el modelo
es un autorregresivo con adornos. Si SISTEMA aporta algo por encima, entonces hay
informacion real del sistema y la pregunta pasa a ser a que horizonte sobrevive.

Se prueba en 2023-2025 y en 2026 por separado, porque 2026 fue un cambio de
regimen y ahi es donde la distincion importa.

Uso
---
  python 13_cuanto_es_autocorrelacion.py
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
SEMILLA = 42

HORIZONTES = [1, 7, 30, 90]
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

SIN_2026 = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]

# Prefijos de las caracteristicas derivadas del propio precio
PREF_PRECIO = ("dlog_lag", "dlog_sd", "precio_choque")


def familia(col):
    return "PRECIO" if col.startswith(PREF_PRECIO) else "SISTEMA"


def evaluar(modelo, prueba, columnas, precio, h):
    pred = pd.Series(modelo.predict(prueba[columnas]), index=prueba.index)
    precio_hoy = precio.reindex(prueba.index)
    precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=h))
    precio_fut.index = prueba.index
    ok = precio_fut.notna()
    m = h10.metricas(prueba["y"][ok], pred[ok], precio_hoy[ok], precio_fut[ok])
    i = h10.metricas(prueba["y"][ok], np.zeros(int(ok.sum())),
                     precio_hoy[ok], precio_fut[ok])
    return m, i, int(ok.sum())


def main():
    print("=" * 78)
    print("CUANTO DEL PODER PREDICTIVO ES SOLO AUTOCORRELACION")
    print("=" * 78)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in SIN_2026 if c in df.columns])

    X, precio, log_precio = h10.construir_features(df)
    X_ref = X.loc[:h10.FIN_SELECCION].dropna()
    COLUMNAS = h10.limpiar(X_ref)

    grupos = {"PRECIO": [c for c in COLUMNAS if familia(c) == "PRECIO"],
              "SISTEMA": [c for c in COLUMNAS if familia(c) == "SISTEMA"],
              "TODO": COLUMNAS}
    print(f"[grupos]  PRECIO {len(grupos['PRECIO'])} caracteristicas | "
          f"SISTEMA {len(grupos['SISTEMA'])} | TODO {len(grupos['TODO'])}")
    print(f"          PRECIO son: {grupos['PRECIO']}\n")

    params_por_h = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))
    filas = []

    for h in HORIZONTES:
        params = params_por_h[str(h)]
        y_h = (log_precio.shift(-h) - log_precio).rename("y")
        datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

        for etapa, ini, fin_entrena in [
            ("2023-2025", INI_PRUEBA, INI_PRUEBA - pd.Timedelta(days=h + 1)),
            ("2026", INI_2026, INI_2026 - pd.Timedelta(days=h + 1)),
        ]:
            entrena = datos.loc[:fin_entrena]
            prueba = datos.loc[ini:] if etapa == "2026" else \
                     datos.loc[ini:INI_2026 - pd.Timedelta(days=1)]
            if len(prueba) < 30:
                continue

            for grupo, cols in grupos.items():
                modelo = xgb.XGBRegressor(**params, random_state=SEMILLA,
                                          n_jobs=-1, tree_method="hist")
                modelo.fit(entrena[cols], entrena["y"])
                m, i, n = evaluar(modelo, prueba, cols, precio, h)
                filas.append({"h": h, "etapa": etapa, "grupo": grupo, "n": n,
                              "RMSE": m["RMSE_log"], "RMSE_ingenuo": i["RMSE_log"],
                              "mejora_%": 100 * (m["RMSE_log"] / i["RMSE_log"] - 1),
                              "MAPE_%": m["MAPE_nivel_%"],
                              "Direccion_%": m["Direccion_%"]})
                print(f"  h={h:3d}  {etapa:10s} {grupo:8s} n={n:4d}  "
                      f"RMSE {m['RMSE_log']:.4f}  "
                      f"({100*(m['RMSE_log']/i['RMSE_log']-1):+6.1f}% vs ingenuo)  "
                      f"MAPE {m['MAPE_nivel_%']:5.1f}%  dir {m['Direccion_%']:.1f}%",
                      flush=True)
            print()

    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / "autocorrelacion_vs_sistema.csv", index=False)

    print("=" * 78)
    print("RESUMEN: mejora sobre el ingenuo (%), menos es mejor")
    print("=" * 78)
    for etapa in ["2023-2025", "2026"]:
        sub = tabla[tabla["etapa"] == etapa]
        if sub.empty:
            continue
        piv = sub.pivot_table(index="h", columns="grupo", values="mejora_%")
        print(f"\n--- {etapa} ---")
        print(piv[["PRECIO", "SISTEMA", "TODO"]].round(2).to_string())

    print("\n" + "=" * 78)
    print("LECTURA")
    print("=" * 78)
    print("Si PRECIO ~ TODO, el modelo es un autorregresivo y no aporta")
    print("informacion del sistema: no da holgura para decidir.")
    print("Si SISTEMA mejora sobre el ingenuo por si solo, ahi si hay senal")
    print("aprovechable con antelacion.")
    print(f"\n[salida] {SALIDA/'autocorrelacion_vs_sistema.csv'}")


if __name__ == "__main__":
    main()
