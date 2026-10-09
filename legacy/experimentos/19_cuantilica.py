"""
================================================================================
PRONOSTICO PROBABILISTICO — cambiar la pregunta por una que si tiene respuesta
================================================================================

EL PROBLEMA CON EL PRONOSTICO PUNTUAL
-------------------------------------
A 30 dias la incertidumbre dominante son los aportes hidrologicos, y nadie sabe
cuanto va a llover en junio. Pedir un numero exacto es perseguir algo que no
existe: por eso el MAPE a 30 dias es del 45% y el modelo no le gana al ingenuo.

Pero para decidir no hace falta el numero. Para programar un mantenimiento sirve
saber:

    "hay 70% de probabilidad de que el precio supere 500 COP/kWh en abril"

Eso si es contestable, y es lo que produce un modelo cuantilico.

QUE SE MIDE Y CONTRA QUE
------------------------
El rival no es el ingenuo puntual sino su version probabilistica: la
CLIMATOLOGIA, es decir "el precio dentro de h dias sera el de hoy multiplicado
por un cambio sacado al azar de la distribucion historica de cambios a h dias".
Es el analogo probabilistico de la caminata aleatoria y es un rival duro.

  perdida pinball   regla de puntuacion propia para cuantiles: penaliza
                    asimetricamente segun el cuantil. Es la metrica correcta,
                    no el RMSE.
  cobertura         ¿el intervalo del 80% contiene el 80% de los casos? Un
                    intervalo que dice 80% y cubre 50% es peor que inutil:
                    da falsa confianza.
  Brier             para P(precio > umbral): mide si las probabilidades estan
                    bien calibradas, no solo si aciertan.

PROTOCOLO
---------
Identico al de los scripts anteriores: seleccion hasta 2019, k elegido en
2020-2022, medicion en 2023-2025 y en 2026. Nada se elige mirando la prueba.

Uso
---
  python 19_cuantilica.py
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

HORIZONTES = [7, 30]
CUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]
ESCALERA = [12, 30, 50, 100, 200, None]
SEMILLA = 42

FIN_SELECCION = pd.Timestamp("2019-12-31")
INI_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

EXCLUIR = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]


def pinball(y, pred, q):
    d = y - pred
    return float(np.mean(np.maximum(q * d, (q - 1) * d)))


def ranquear(X, y, h):
    tscv = TimeSeriesSplit(n_splits=3, gap=h)
    Xs = StandardScaler().fit_transform(X)
    la = LassoCV(cv=tscv, max_iter=20000, random_state=SEMILLA, n_jobs=-1).fit(Xs, y)
    r1 = pd.Series(np.abs(la.coef_), index=X.columns).rank(ascending=False)
    mo = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.03,
                          subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
                          reg_lambda=3.0, random_state=SEMILLA, n_jobs=-1,
                          tree_method="hist").fit(X, y)
    r2 = pd.Series(mo.feature_importances_, index=X.columns).rank(ascending=False)
    return ((r1 + r2) / 2).sort_values()


def ajustar_cuantiles(entrena, prueba, cols, params):
    """Un modelo por cuantil. Devuelve un DataFrame cuantil -> prediccion."""
    out = {}
    for q in CUANTILES:
        p = dict(params)
        p.pop("objective", None)
        m = xgb.XGBRegressor(objective="reg:quantileerror", quantile_alpha=q,
                             random_state=SEMILLA, n_jobs=-1, tree_method="hist", **p)
        m.fit(entrena[cols], entrena["y"])
        out[q] = m.predict(prueba[cols])
    d = pd.DataFrame(out, index=prueba.index)
    # los cuantiles pueden cruzarse; se ordenan fila a fila para que sean validos
    d.values.sort(axis=1)
    return d


def climatologia(entrena, prueba):
    """Rival: distribucion historica de cambios a h dias, anclada en hoy."""
    hist = entrena["y"].values
    qs = {q: np.quantile(hist, q) for q in CUANTILES}
    return pd.DataFrame({q: np.full(len(prueba), v) for q, v in qs.items()},
                        index=prueba.index)


def evaluar(qpred, qclim, prueba, precio, h):
    y = prueba["y"]
    r = {}

    # --- perdida pinball, modelo y climatologia -----------------------------
    pin_m = np.mean([pinball(y, qpred[q], q) for q in CUANTILES])
    pin_c = np.mean([pinball(y, qclim[q], q) for q in CUANTILES])
    r["pinball_modelo"] = pin_m
    r["pinball_clima"] = pin_c
    r["mejora_pinball_%"] = 100 * (pin_m / pin_c - 1)

    # --- cobertura del intervalo del 80% ------------------------------------
    dentro_m = ((y >= qpred[0.10]) & (y <= qpred[0.90])).mean()
    dentro_c = ((y >= qclim[0.10]) & (y <= qclim[0.90])).mean()
    r["cobertura80_modelo"] = float(dentro_m)
    r["cobertura80_clima"] = float(dentro_c)

    # ancho medio del intervalo, en proporcion del precio
    r["ancho80_modelo"] = float(np.mean(np.exp(qpred[0.90]) - np.exp(qpred[0.10])))
    r["ancho80_clima"] = float(np.mean(np.exp(qclim[0.90]) - np.exp(qclim[0.10])))

    # --- P(precio > umbral): lo que de verdad se usa para decidir ------------
    precio_hoy = precio.reindex(prueba.index)
    precio_fut = precio.reindex(prueba.index + pd.Timedelta(days=h))
    precio_fut.index = prueba.index
    ok = precio_fut.notna()

    for umbral in UMBRALES:
        # se interpola la probabilidad a partir de los cuantiles predichos
        objetivo = np.log(umbral) - np.log(precio_hoy)
        pm = probabilidad_supera(qpred, objetivo)
        pc = probabilidad_supera(qclim, objetivo)
        real = (precio_fut > umbral).astype(float)
        r[f"brier_modelo_{umbral}"] = float(np.mean((pm[ok] - real[ok]) ** 2))
        r[f"brier_clima_{umbral}"] = float(np.mean((pc[ok] - real[ok]) ** 2))
    return r


def probabilidad_supera(q, objetivo):
    """P(y > objetivo) interpolando entre los cuantiles predichos."""
    qs = np.array(CUANTILES)
    M = q[CUANTILES].values
    obj = np.asarray(objetivo, dtype=float)
    p = np.empty(len(obj))
    for i in range(len(obj)):
        p[i] = 1.0 - np.interp(obj[i], M[i], qs, left=0.0, right=1.0)
    return pd.Series(p, index=q.index)


UMBRALES = [300, 500, 800]


def main():
    print("=" * 80)
    print("PRONOSTICO PROBABILISTICO")
    print("=" * 80)

    df = pd.read_csv(PANEL, parse_dates=["fecha"],
                     index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in EXCLUIR if c in df.columns])
    X, precio, log_precio = h10.construir_features(df)
    COLUMNAS = h10.limpiar(X.loc[:FIN_SELECCION].dropna())
    print(f"[panel]   {df.shape[1]} variables -> {len(COLUMNAS)} caracteristicas")

    todos = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))
    resultados = []

    for h in HORIZONTES:
        print("\n" + "=" * 80)
        print(f"HORIZONTE h = {h} DIAS")
        print("=" * 80)
        params = {k: v for k, v in todos[str(h)].items()}

        y_h = (log_precio.shift(-h) - log_precio).rename("y")
        datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

        orden = ranquear(datos.loc[:FIN_SELECCION, COLUMNAS],
                         datos.loc[:FIN_SELECCION, "y"], h)

        # --- elegir k en validacion, por perdida pinball ---------------------
        ent_v = datos.loc[:INI_VALIDACION - pd.Timedelta(days=h + 1)]
        val = datos.loc[INI_VALIDACION:FIN_VALIDACION]
        mejor_k, mejor_pin = None, np.inf
        for k in ESCALERA:
            cols = list(orden.index) if k is None else list(orden.index[:k])
            qp = ajustar_cuantiles(ent_v, val, cols, params)
            pin = np.mean([pinball(val["y"], qp[q], q) for q in CUANTILES])
            print(f"  val k={len(cols):3d}  pinball {pin:.5f}", flush=True)
            if pin < mejor_pin:
                mejor_k, mejor_pin = len(cols), pin
        cols = list(orden.index[:mejor_k]) if mejor_k < len(orden) else list(orden.index)
        print(f"  ==> k elegido: {mejor_k}")

        for etapa, ini, fin in [("2023-2025", INI_PRUEBA, INI_2026 - pd.Timedelta(days=1)),
                                ("2026", INI_2026, datos.index.max())]:
            entrena = datos.loc[:ini - pd.Timedelta(days=h + 1)]
            prueba = datos.loc[ini:fin]
            if len(prueba) < 30:
                continue
            qp = ajustar_cuantiles(entrena, prueba, cols, params)
            qc = climatologia(entrena, prueba)
            r = evaluar(qp, qc, prueba, precio, h)
            r.update({"h": h, "etapa": etapa, "k": mejor_k, "n": len(prueba)})
            resultados.append(r)

            print(f"\n  --- {etapa} ({len(prueba)} dias) ---")
            print(f"    pinball    modelo {r['pinball_modelo']:.5f}  "
                  f"clima {r['pinball_clima']:.5f}  ({r['mejora_pinball_%']:+.1f}%)")
            print(f"    cobertura 80%   modelo {r['cobertura80_modelo']:.1%}  "
                  f"clima {r['cobertura80_clima']:.1%}   (ideal 80%)")
            print(f"    ancho del 80%   modelo {r['ancho80_modelo']:.2f}  "
                  f"clima {r['ancho80_clima']:.2f}  (menor = mas informativo)")
            for u in UMBRALES:
                bm, bc = r[f"brier_modelo_{u}"], r[f"brier_clima_{u}"]
                print(f"    Brier P(>{u:4d})  modelo {bm:.4f}  clima {bc:.4f}  "
                      f"({100*(bm/bc-1):+.1f}%)")

            if etapa == "2026" and h == 30:
                graficar(qp, prueba, precio, h)

    t = pd.DataFrame(resultados)
    t.to_csv(SALIDA / "cuantilica.csv", index=False)
    print(f"\n[salida] {SALIDA/'cuantilica.csv'}")


def graficar(qp, prueba, precio, h):
    hoy = precio.reindex(prueba.index)
    fut = prueba.index + pd.Timedelta(days=h)
    real = precio.reindex(fut)

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.fill_between(fut, hoy.values * np.exp(qp[0.10]), hoy.values * np.exp(qp[0.90]),
                    alpha=0.25, color="tab:red", label="intervalo 80%")
    ax.fill_between(fut, hoy.values * np.exp(qp[0.25]), hoy.values * np.exp(qp[0.75]),
                    alpha=0.35, color="tab:red", label="intervalo 50%")
    ax.plot(fut, hoy.values * np.exp(qp[0.50]), color="tab:red", lw=1.2, label="mediana")
    ax.plot(fut, real.values, color="k", lw=1.2, label="real")
    ax.set_title(f"Pronostico probabilistico a {h} dias — 2026")
    ax.set_ylabel("COP/kWh"); ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(SALIDA / f"cuantilica_h{h}_2026.png", dpi=110)


if __name__ == "__main__":
    main()
