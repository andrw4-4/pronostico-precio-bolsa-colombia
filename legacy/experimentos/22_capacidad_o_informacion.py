"""
================================================================================
¿EL MODELO ESTA LIMITADO POR CAPACIDAD O POR INFORMACION?
================================================================================

La pregunta detras: ¿serviria una red neuronal?

Una red neuronal aporta CAPACIDAD: puede representar funciones mas complejas.
Eso ayuda solo si el modelo actual se queda corto ajustando, no si el problema
es que la informacion no esta.

Dos diagnosticos que lo distinguen:

  1. BRECHA ENTRENAMIENTO-PRUEBA
     Si el modelo ajusta el entrenamiento mucho mejor que la prueba, sobra
     capacidad y falta senal: mas capacidad empeora. Si le va mal en AMBOS,
     esta sub-ajustando y mas capacidad podria ayudar.

  2. CURVA DE CAPACIDAD
     Se entrenan modelos desde muy simples hasta muy complejos y se mira si el
     error de prueba baja o sube. Es una prueba directa de la hipotesis: si
     duplicar la capacidad del arbol ya empeora, una red -que tiene mucha mas-
     empeoraria mas.

Se mide en h=1 (donde el modelo funciona) y h=7 (donde es marginal).

Uso
---
  python 22_capacidad_o_informacion.py
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
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")
SEMILLA = 42

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

EXCLUIR = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]

# de muy regularizado a muy flexible
CAPACIDADES = [
    ("muy simple",  dict(n_estimators=200,  max_depth=1, learning_rate=0.01,
                         reg_lambda=50.0, min_child_weight=50)),
    ("simple",      dict(n_estimators=400,  max_depth=2, learning_rate=0.01,
                         reg_lambda=10.0, min_child_weight=10)),
    ("media",       dict(n_estimators=600,  max_depth=4, learning_rate=0.05,
                         reg_lambda=1.0,  min_child_weight=5)),
    ("alta",        dict(n_estimators=1200, max_depth=6, learning_rate=0.1,
                         reg_lambda=0.1,  min_child_weight=2)),
    ("muy alta",    dict(n_estimators=2000, max_depth=10, learning_rate=0.2,
                         reg_lambda=0.0,  min_child_weight=1)),
]


def preparar(h):
    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in EXCLUIR if c in df.columns])
    X, precio, log_precio = h10.construir_features(df)
    COLS = h10.limpiar(X.loc[:h10.FIN_SELECCION].dropna())
    y = (log_precio.shift(-h) - log_precio).rename("y")
    return pd.concat([X[COLS], y], axis=1).dropna(), COLS, precio


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def main():
    print("=" * 78)
    print("¿CAPACIDAD O INFORMACION?")
    print("=" * 78)

    filas = []
    for h in (1, 7):
        datos, COLS, precio = preparar(h)
        entrena = datos.loc[:INI_2026 - pd.Timedelta(days=h + 1)]
        prueba = datos.loc[INI_2026:]

        # ingenuo: predecir 0 (el precio no cambia)
        rmse_ing_tr = rmse(entrena["y"], 0)
        rmse_ing_te = rmse(prueba["y"], 0)

        print(f"\n{'='*78}\nHORIZONTE h = {h}\n{'='*78}")
        print(f"entrena {len(entrena)} obs, prueba {len(prueba)} obs (2026)")
        print(f"ingenuo:  RMSE entrenamiento {rmse_ing_tr:.4f}   prueba {rmse_ing_te:.4f}\n")
        print(f"{'capacidad':12s} {'hojas':>7s} {'RMSE entr':>10s} {'RMSE prueba':>12s} "
              f"{'brecha':>8s} {'vs ingenuo':>11s}")
        print("-" * 68)

        for nombre, params in CAPACIDADES:
            m = xgb.XGBRegressor(**params, subsample=0.8, colsample_bytree=0.8,
                                 random_state=SEMILLA, n_jobs=-1, tree_method="hist")
            m.fit(entrena[COLS], entrena["y"])
            p_tr = m.predict(entrena[COLS])
            p_te = m.predict(prueba[COLS])
            r_tr, r_te = rmse(entrena["y"], p_tr), rmse(prueba["y"], p_te)
            hojas = sum(t.count("leaf") for t in m.get_booster().get_dump())
            mejora = 100 * (r_te / rmse_ing_te - 1)
            print(f"{nombre:12s} {hojas:7d} {r_tr:10.4f} {r_te:12.4f} "
                  f"{r_tr/r_te:8.2f} {mejora:+10.2f}%")
            filas.append({"h": h, "capacidad": nombre, "hojas": hojas,
                          "rmse_entrena": r_tr, "rmse_prueba": r_te,
                          "brecha": r_tr / r_te, "mejora_%": mejora})

    t = pd.DataFrame(filas)
    t.to_csv(SALIDA / "capacidad.csv", index=False)

    print("\n" + "=" * 78)
    print("LECTURA")
    print("=" * 78)
    for h in (1, 7):
        s = t[t.h == h]
        mejor = s.loc[s["mejora_%"].idxmin()]
        peor = s.loc[s["mejora_%"].idxmax()]
        simple = s[s.capacidad == "muy simple"].iloc[0]
        compleja = s[s.capacidad == "muy alta"].iloc[0]
        print(f"\nh={h}:")
        print(f"  mejor capacidad: '{mejor['capacidad']}' ({mejor['hojas']} hojas), "
              f"{mejor['mejora_%']:+.2f}% vs ingenuo")
        print(f"  al pasar de 'muy simple' a 'muy alta': "
              f"{simple['mejora_%']:+.2f}% -> {compleja['mejora_%']:+.2f}%")
        print(f"  brecha entrenamiento/prueba con capacidad alta: "
              f"{compleja['brecha']:.2f} "
              f"(1.0 = ajusta igual de bien ambos)")
        if compleja["mejora_%"] > mejor["mejora_%"] + 0.5:
            print("  ==> mas capacidad EMPEORA: el limite es la informacion, no el modelo")
        else:
            print("  ==> mas capacidad no empeora: podria valer la pena explorar")

    graficar(t)
    print(f"\n[salida] {SALIDA/'capacidad.csv'}, {SALIDA/'capacidad.png'}")


def graficar(t):
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
    for i, h in enumerate((1, 7)):
        s = t[t.h == h]
        ax[i].plot(s["hojas"], s["rmse_entrena"], marker="o",
                   label="error en entrenamiento")
        ax[i].plot(s["hojas"], s["rmse_prueba"], marker="o",
                   label="error en prueba (2026)")
        ax[i].set_xscale("log")
        ax[i].set_xlabel("hojas del modelo (capacidad)")
        ax[i].set_ylabel("RMSE Δlog")
        ax[i].set_title(f"h = {h} día(s)")
        ax[i].legend(fontsize=8)
    plt.suptitle("Si el error de prueba sube mientras el de entrenamiento baja,\n"
                 "el problema es falta de señal, no falta de capacidad")
    plt.tight_layout()
    plt.savefig(SALIDA / "capacidad.png", dpi=110)


if __name__ == "__main__":
    main()
