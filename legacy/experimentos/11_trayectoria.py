"""
================================================================================
TRAYECTORIA DIARIA — el precio de CADA dia del horizonte, no solo el ultimo
================================================================================

El script 10_horizontes.py entrena un modelo por horizonte: el de h=30 dice cual
sera el precio del dia t+30, pero no dice nada de los 29 dias intermedios. Para
planeacion tactica (programar un mantenimiento, decidir cuando comprar cobertura)
hace falta la TRAYECTORIA completa: el precio de cada dia.

ESTRATEGIA: el horizonte como variable del modelo
-------------------------------------------------
En vez de entrenar 90 modelos, se entrena UNO solo sobre datos apilados. Cada
fila de entrenamiento es:

    (caracteristicas en t,  h)  ->  log P(t+h) - log P(t)

con h recorriendo una rejilla. El modelo aprende como cambia la relacion con el
horizonte, en vez de tratar cada h como un problema sin relacion con el anterior.
Para pronosticar la trayectoria parado en t, se evalua el modelo con h = 1, 2,
..., H y se reconstruyen los niveles:

    P_hat(t+h) = P(t) * exp(y_hat(t, h))

Cada punto es el precio de un DIA CONCRETO, no un promedio del periodo.

POR QUE NO RECURSIVO
--------------------
La alternativa clasica es predecir t+1, realimentar y predecir t+2. Aqui no
sirve: acumula error y exigiria pronosticar tambien las 458 variables exogenas,
que es un problema mas dificil que el original.

FUGA
----
Igual que en 10_horizontes.py, con dos cuidados adicionales porque las filas
apiladas comparten fecha de origen:
  - el desarrollo se recorta H_MAX dias (el objetivo del horizonte mas largo es
    el que mas lejos mira);
  - la particion entre desarrollo y prueba se hace por la fecha de ORIGEN t, y
    ninguna fila de desarrollo puede tener t+h dentro de la prueba.

Uso
---
  python 11_trayectoria.py
================================================================================
"""

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
SALIDA.mkdir(exist_ok=True)

# Rejilla de horizontes para ENTRENAR. No hace falta 1..90 completo: basta que
# cubra bien el rango para que el modelo aprenda la forma de la curva, y luego
# se puede evaluar en cualquier h intermedio.
REJILLA = [1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60, 75, 90]
H_MAX = max(REJILLA)

INI_PRUEBA = pd.Timestamp("2023-01-01")
SEMILLA = 42

# Se reutiliza toda la maquinaria de 10_horizontes.py
import importlib.util
_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)


def apilar(X, log_precio, columnas, horizontes):
    """
    Construye la matriz apilada: una fila por (fecha, horizonte).

    Se agrega 'h' como columna. Tambien se agrega log(h), porque el deterioro
    del pronostico con el horizonte es aproximadamente logaritmico y darselo
    explicito le ahorra al arbol tener que aproximarlo con cortes.
    """
    piezas = []
    for h in horizontes:
        y = (log_precio.shift(-h) - log_precio).rename("y")
        d = pd.concat([X[columnas], y], axis=1).dropna()
        d["h"] = h
        d["log_h"] = np.log(h)
        d["fecha_origen"] = d.index
        d["fecha_objetivo"] = d.index + pd.Timedelta(days=h)
        piezas.append(d)
    return pd.concat(piezas, ignore_index=True)


def main():
    print("=" * 74)
    print("TRAYECTORIA DIARIA")
    print(f"rejilla de entrenamiento: {REJILLA}")
    print("=" * 74)

    df = pd.read_csv(h10.PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    X, precio, log_precio = h10.construir_features(df)

    X_ref = X.loc[:h10.FIN_SELECCION].dropna()
    COLUMNAS = h10.limpiar(X_ref)
    print(f"[limpieza] {X.shape[1]} -> {len(COLUMNAS)} caracteristicas")

    apilado = apilar(X, log_precio, COLUMNAS, REJILLA)
    print(f"[apilado]  {len(apilado):,} filas "
          f"({len(REJILLA)} horizontes x ~{len(apilado)//len(REJILLA):,} fechas)")

    # --- particion sin fuga --------------------------------------------------
    # Una fila de desarrollo no puede tener su fecha OBJETIVO dentro de la prueba.
    dev = apilado[apilado["fecha_objetivo"] < INI_PRUEBA]
    prueba = apilado[apilado["fecha_origen"] >= INI_PRUEBA]

    print(f"[dev]      {len(dev):,} filas, origen hasta "
          f"{dev['fecha_origen'].max().date()} (objetivo siempre < {INI_PRUEBA.date()})")
    print(f"[prueba]   {len(prueba):,} filas, origen desde "
          f"{prueba['fecha_origen'].min().date()}")

    entrada = COLUMNAS + ["h", "log_h"]

    # --- busqueda de hiperparametros ----------------------------------------
    # El orden importa: se ordena por fecha de origen para que TimeSeriesSplit
    # siga separando pasado de futuro. El gap es H_MAX porque es el solapamiento
    # maximo entre una fila de entrenamiento y una de validacion.
    dev_ord = dev.sort_values("fecha_origen").reset_index(drop=True)
    tscv = TimeSeriesSplit(n_splits=3, gap=H_MAX * len(REJILLA))

    rng = np.random.default_rng(SEMILLA)
    mejor, mejor_rmse = None, np.inf
    Xv, yv = dev_ord[entrada].values, dev_ord["y"].values

    t0 = time.time()
    for i in range(12):
        p = {k: rng.choice(v).item() for k, v in h10.ESPACIO.items()}
        err = []
        for tr, va in tscv.split(Xv):
            m = xgb.XGBRegressor(**p, random_state=SEMILLA, n_jobs=-1,
                                 tree_method="hist")
            m.fit(Xv[tr], yv[tr])
            err.append(np.sqrt(np.mean((yv[va] - m.predict(Xv[va])) ** 2)))
        r = float(np.mean(err))
        if r < mejor_rmse:
            mejor, mejor_rmse = p, r
        print(f"  [{i+1:2d}/12] mejor RMSE CV: {mejor_rmse:.5f}  "
              f"({time.time()-t0:.0f}s)", flush=True)

    print(f"\n[hiperparametros] {mejor}")

    modelo = xgb.XGBRegressor(**mejor, random_state=SEMILLA, n_jobs=-1,
                              tree_method="hist").fit(dev_ord[entrada], dev_ord["y"])

    # --- evaluacion por horizonte en la prueba ------------------------------
    prueba = prueba.copy()
    prueba["pred"] = modelo.predict(prueba[entrada])
    prueba["precio_hoy"] = precio.reindex(prueba["fecha_origen"]).values
    prueba["precio_real"] = precio.reindex(prueba["fecha_objetivo"]).values
    prueba = prueba.dropna(subset=["precio_real"])
    prueba["nivel_pred"] = prueba["precio_hoy"] * np.exp(prueba["pred"])

    filas = []
    for h, g in prueba.groupby("h"):
        rmse_m = float(np.sqrt(np.mean((g["y"] - g["pred"]) ** 2)))
        rmse_i = float(np.sqrt(np.mean(g["y"] ** 2)))
        mape_m = float(100 * np.mean((g["nivel_pred"] - g["precio_real"]).abs()
                                     / g["precio_real"]))
        mape_i = float(100 * np.mean((g["precio_hoy"] - g["precio_real"]).abs()
                                     / g["precio_real"]))
        dm, p = h10.diebold_mariano(g["y"] - g["pred"], g["y"], h=int(h))
        filas.append({"h": int(h), "n": len(g), "RMSE_modelo": rmse_m,
                      "RMSE_ingenuo": rmse_i,
                      "mejora_%": 100 * (rmse_m / rmse_i - 1),
                      "MAPE_modelo_%": mape_m, "MAPE_ingenuo_%": mape_i,
                      "Direccion_%": float(100 * np.mean(
                          np.sign(g["pred"]) == np.sign(g["y"]))),
                      "DM": dm, "p_DM": p})

    tabla = pd.DataFrame(filas).set_index("h")
    tabla.to_csv(SALIDA / "trayectoria_por_horizonte.csv")
    (SALIDA / "hiperparametros_trayectoria.json").write_text(
        json.dumps(mejor, indent=2), encoding="utf-8")
    modelo.save_model(SALIDA / "modelo_trayectoria.json")

    print("\n" + "=" * 74)
    print("DESEMPENO POR HORIZONTE (un solo modelo)")
    print("=" * 74)
    print(tabla.round(4).to_string())

    # --- ejemplo de trayectoria ---------------------------------------------
    # Parado en una fecha concreta, el precio de cada uno de los 90 dias siguientes.
    graficar_ejemplos(modelo, X, precio, log_precio, COLUMNAS, entrada)

    print(f"\n[salida] {SALIDA}")
    print("  trayectoria_por_horizonte.csv, modelo_trayectoria.json,")
    print("  hiperparametros_trayectoria.json, trayectorias_ejemplo.png")


def graficar_ejemplos(modelo, X, precio, log_precio, columnas, entrada):
    """Trayectoria diaria completa desde cuatro fechas de la prueba."""
    fechas = [pd.Timestamp(f) for f in
              ["2023-04-01", "2023-10-01", "2024-04-01", "2024-10-01"]]
    dias = np.arange(1, H_MAX + 1)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    guardar = []

    for ax, t in zip(axes.ravel(), fechas):
        if t not in X.index or X.loc[t, columnas].isna().any():
            ax.axis("off")
            continue

        base = X.loc[t, columnas]
        rejilla = pd.DataFrame([base.values] * len(dias), columns=columnas)
        rejilla["h"] = dias
        rejilla["log_h"] = np.log(dias)

        pred = modelo.predict(rejilla[entrada])
        nivel = precio.loc[t] * np.exp(pred)
        objetivo = t + pd.to_timedelta(dias, unit="D")
        real = precio.reindex(objetivo)

        ax.plot(objetivo, real.values, color="k", lw=1.2, label="real")
        ax.plot(objetivo, nivel, color="tab:red", lw=1.4, label="pronostico")
        ax.axhline(precio.loc[t], color="tab:blue", ls="--", lw=1,
                   label="ingenuo (precio de hoy)")
        ax.set_title(f"Parado el {t.date()}: los {H_MAX} dias siguientes", fontsize=10)
        ax.legend(fontsize=8)
        ax.set_ylabel("COP/kWh")

        guardar.append(pd.DataFrame({"origen": t, "fecha": objetivo, "h": dias,
                                     "pronostico": nivel, "real": real.values,
                                     "ingenuo": precio.loc[t]}))

    plt.tight_layout()
    plt.savefig(SALIDA / "trayectorias_ejemplo.png", dpi=110)
    if guardar:
        pd.concat(guardar).to_csv(SALIDA / "trayectorias_ejemplo.csv", index=False)


if __name__ == "__main__":
    main()
