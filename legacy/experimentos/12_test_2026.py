"""
================================================================================
TEST FINAL SOBRE 2026 — datos que el modelo nunca vio, de un anio que no existia
================================================================================

Protocolo, tal como se definio:

  1. Los hiperparametros ya se eligieron con datos hasta 2025 (10_horizontes.py
     los busco por validacion cruzada en desarrollo y se midieron en 2023-2025).
     Aqui NO se vuelve a buscar nada: se leen de salidas_horizontes/.
  2. Se reentrena cada modelo con TODO lo disponible hasta 2025.
  3. Se prueba UNA sola vez contra 2026.

Esto es una prueba fuera de muestra en el sentido fuerte: cuando se eligieron los
hiperparametros, los datos de 2026 no existian todavia.

CONTEXTO DEL ANIO DE PRUEBA
---------------------------
2026 es un anio de El Nino: el indice ONI llego a 1,39 en junio y el precio de
escasez esta en ~906 COP/kWh. Es un anio atipico, que es justo donde los modelos
se rompen. Leer el resultado con eso en mente.

VARIABLES SIN DATOS EN 2026
---------------------------
Tres series de la cache no se pudieron mapear a una metrica de la API
(demanda_no_atendida, dem_no_atendida_noprog, demanda_por_or), asi que no tienen
datos de 2026. Se EXCLUYEN del conjunto de caracteristicas en vez de rellenarlas
hacia adelante con el ultimo valor de 2025: nueve meses de relleno con un valor
fijo meteria una constante disfrazada de variable.

Uso
---
  python 12_test_2026.py
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
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL_2026 = BASE / "panel_diario_ampliado_2026.csv"
INI_2026 = pd.Timestamp("2026-01-01")
SEMILLA = 42

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

SIN_2026 = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]


def main():
    print("=" * 76)
    print("TEST FINAL SOBRE 2026")
    print("=" * 76)

    df = pd.read_csv(PANEL_2026, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    print(f"[panel]  {df.shape[0]} dias x {df.shape[1]} variables, "
          f"{df.index.min().date()} a {df.index.max().date()}")

    # Se sacan del panel ANTES de construir caracteristicas, para que no generen
    # rezagos ni choques a partir de un relleno hacia adelante de nueve meses.
    presentes = [c for c in SIN_2026 if c in df.columns]
    df = df.drop(columns=presentes)
    print(f"[excluir] {presentes} (sin datos en 2026)")

    X, precio, log_precio = h10.construir_features(df)
    X_ref = X.loc[:h10.FIN_SELECCION].dropna()
    COLUMNAS = h10.limpiar(X_ref)
    print(f"[limpieza] {X.shape[1]} -> {len(COLUMNAS)} caracteristicas")

    params_por_h = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))
    print(f"[params]  leidos de hiperparametros.json "
          f"(elegidos con datos hasta 2025, sin ver 2026)\n")

    obj_2026 = precio[precio.index >= INI_2026].dropna()
    print(f"[2026]    {len(obj_2026)} dias con precio observado, "
          f"{obj_2026.index.min().date()} a {obj_2026.index.max().date()}")
    print(f"          media {obj_2026.mean():.1f}  min {obj_2026.min():.1f}  "
          f"max {obj_2026.max():.1f} COP/kWh")
    ref = precio[(precio.index >= "2023-01-01") & (precio.index < INI_2026)]
    print(f"          para comparar, 2023-2025: media {ref.mean():.1f}\n")

    filas, predicciones = [], {}

    for h_txt, params in params_por_h.items():
        h = int(h_txt)
        y_h = (log_precio.shift(-h) - log_precio).rename("y")
        datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

        # Entrenamiento: todo aquel cuyo objetivo cae ANTES de 2026.
        fin_entrena = INI_2026 - pd.Timedelta(days=h + 1)
        entrena = datos.loc[:fin_entrena]
        prueba = datos.loc[INI_2026:]

        if len(prueba) < 20:
            print(f"h={h:3d}  prueba demasiado corta ({len(prueba)}), se omite")
            continue

        modelo = xgb.XGBRegressor(**params, random_state=SEMILLA, n_jobs=-1,
                                  tree_method="hist")
        modelo.fit(entrena[COLUMNAS], entrena["y"])
        pred = pd.Series(modelo.predict(prueba[COLUMNAS]), index=prueba.index)
        predicciones[h] = pred

        precio_hoy = precio.reindex(prueba.index)
        precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=h))
        precio_fut.index = prueba.index
        ok = precio_fut.notna()

        m = h10.metricas(prueba["y"][ok], pred[ok], precio_hoy[ok], precio_fut[ok])
        i = h10.metricas(prueba["y"][ok], np.zeros(int(ok.sum())),
                         precio_hoy[ok], precio_fut[ok])
        dm, p = h10.diebold_mariano((prueba["y"] - pred)[ok], prueba["y"][ok], h=h)

        mejora = 100 * (m["RMSE_log"] / i["RMSE_log"] - 1)
        ver = ("gana el modelo" if p < 0.05 and dm < 0
               else "gana el ingenuo" if p < 0.05 else "sin diferencia")

        print(f"h={h:3d}  entrena hasta {entrena.index.max().date()} "
              f"({len(entrena)} obs)  prueba {int(ok.sum())} dias")
        print(f"      RMSE {m['RMSE_log']:.4f} vs {i['RMSE_log']:.4f} ({mejora:+.1f}%)   "
              f"MAPE {m['MAPE_nivel_%']:.1f}% vs {i['MAPE_nivel_%']:.1f}%   "
              f"dir {m['Direccion_%']:.1f}%   p={p:.4f}  {ver}")

        filas.append({"h": h, "n": int(ok.sum()), "n_entrena": len(entrena),
                      "RMSE_modelo": m["RMSE_log"], "RMSE_ingenuo": i["RMSE_log"],
                      "mejora_%": mejora,
                      "MAPE_modelo_%": m["MAPE_nivel_%"],
                      "MAPE_ingenuo_%": i["MAPE_nivel_%"],
                      "Direccion_%": m["Direccion_%"],
                      "DM": dm, "p_DM": p, "veredicto": ver})

    tabla = pd.DataFrame(filas).set_index("h")
    tabla.to_csv(SALIDA / "test_2026.csv")

    print("\n" + "=" * 76)
    print("RESULTADO EN 2026")
    print("=" * 76)
    print(tabla.round(4).to_string())

    comparar(tabla)
    graficar(predicciones, precio, tabla)

    print(f"\n[salida] {SALIDA/'test_2026.csv'}, {SALIDA/'test_2026.png'}")


def comparar(tabla_2026):
    """2026 contra lo que dio 2023-2025, para ver si el modelo aguanto."""
    ruta = SALIDA / "resumen_horizontes.csv"
    if not ruta.exists():
        return
    viejo = pd.read_csv(ruta, index_col="h")

    comp = pd.DataFrame({
        "MAPE 2023-25": viejo["MAPE_modelo_%"],
        "MAPE 2026": tabla_2026["MAPE_modelo_%"],
        "mejora% 2023-25": viejo["mejora_%"],
        "mejora% 2026": tabla_2026["mejora_%"],
        "dir 2023-25": viejo["Direccion_%"],
        "dir 2026": tabla_2026["Direccion_%"],
    })
    print("\n" + "=" * 76)
    print("2026 CONTRA 2023-2025")
    print("=" * 76)
    print(comp.round(2).to_string())
    comp.to_csv(SALIDA / "comparacion_2026_vs_2023_2025.csv")


def graficar(predicciones, precio, tabla):
    horizontes = sorted(predicciones)
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))

    for ax, h in zip(axes.ravel(), horizontes):
        pred = predicciones[h]
        objetivo = pred.index + pd.Timedelta(days=h)
        real = precio.reindex(objetivo)
        nivel = precio.reindex(pred.index).values * np.exp(pred.values)

        ax.plot(objetivo, real.values, color="k", lw=1, label="real")
        ax.plot(objetivo, nivel, color="tab:red", lw=1, label="pronostico")
        ax.plot(objetivo, precio.reindex(pred.index).values, color="tab:blue",
                lw=0.8, ls="--", label="ingenuo")
        fila = tabla.loc[h]
        ax.set_title(f"h = {h} dias   MAPE {fila['MAPE_modelo_%']:.0f}% "
                     f"vs {fila['MAPE_ingenuo_%']:.0f}%", fontsize=10)
        ax.set_ylabel("COP/kWh")
        ax.legend(fontsize=7)
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)

    plt.suptitle("Pronostico sobre 2026 (datos que no existian al elegir el modelo)")
    plt.tight_layout()
    plt.savefig(SALIDA / "test_2026.png", dpi=110)


if __name__ == "__main__":
    main()
