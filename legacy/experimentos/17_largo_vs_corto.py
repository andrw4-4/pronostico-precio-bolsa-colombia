"""
================================================================================
¿SIRVE LA HISTORIA LARGA? — 2000-2026 contra 2015-2026, a 7 dias
================================================================================

LA PREGUNTA
-----------
El modelo a mediano plazo falla porque ha visto pocas transiciones de regimen.
El panel largo agrega 15 anios y unas 7 transiciones ENSO mas. ¿Alcanza con eso,
o el cambio estructural del sistema (140 plantas en 2000 contra 500 hoy, sin
renovables, sin cargo por confiabilidad) pesa mas y lo empeora?

EL DISENIO
----------
Todo identico al del panel corto salvo UNA cosa: de donde salen los datos de
entrenamiento. Mismas ventanas, mismos hiperparametros, mismas semillas, mismo
metodo de seleccion, misma escalera de k.

  SELECCION   hasta 2019-12-31   ordenar variables (Lasso + ganancia XGBoost)
  VALIDACION  2020-2022          elegir k
  PRUEBA A    2023-2025
  PRUEBA B    2026               medicion final

La unica diferencia: el panel LARGO empieza en 2000 y el CORTO en 2015, asi que
la ventana de seleccion y el entrenamiento son 2,4 veces mas grandes.

Si el largo gana, la historia extra sirvio. Si pierde, el cambio estructural
pesa mas que los eventos ENSO adicionales, y eso tambien es un resultado.

Uso
---
  python 17_largo_vs_corto.py
================================================================================
"""

import importlib.util
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salidas_horizontes"

PANELES = {
    "CORTO (2015-2026)": BASE / "panel_diario_ampliado_2026.csv",
    "LARGO (2000-2026)": BASE / "panel_largo_2000_2026.csv",
}

H = 7
SEMILLAS = [42, 7, 123, 2024, 99]
ESCALERA = [5, 12, 20, 30, 50, 100, 200, None]

FIN_SELECCION = pd.Timestamp("2019-12-31")
INI_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
INI_PRUEBA = pd.Timestamp("2023-01-01")
INI_2026 = pd.Timestamp("2026-01-01")

_spec = importlib.util.spec_from_file_location("h10", BASE / "10_horizontes.py")
h10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h10)

# sin datos en 2026, o sin datos antes de 2015: fuera en los dos paneles, para
# que la comparacion no dependa de que variables existen en cada uno
EXCLUIR = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or",
           "gen_solar", "frac_solar", "vol_pct_el_quimbo"]


def ranquear(X_sel, y_sel):
    tscv = TimeSeriesSplit(n_splits=3, gap=H)
    Xs = StandardScaler().fit_transform(X_sel)
    lasso = LassoCV(cv=tscv, max_iter=20000, random_state=42, n_jobs=-1).fit(Xs, y_sel)
    r1 = pd.Series(np.abs(lasso.coef_), index=X_sel.columns).rank(ascending=False)
    mod = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.03,
                           subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
                           reg_lambda=3.0, random_state=42, n_jobs=-1,
                           tree_method="hist").fit(X_sel, y_sel)
    r2 = pd.Series(mod.feature_importances_, index=X_sel.columns).rank(ascending=False)
    return ((r1 + r2) / 2).sort_values()


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


def correr(etiqueta, ruta, params):
    print("\n" + "=" * 82)
    print(etiqueta)
    print("=" * 82)

    df = pd.read_csv(ruta, parse_dates=["fecha"], index_col="fecha").sort_index().asfreq("D")
    df = df.drop(columns=[c for c in EXCLUIR if c in df.columns])
    print(f"  panel: {df.shape[0]} dias x {df.shape[1]} variables, "
          f"desde {df.index.min().date()}")

    X, precio, log_precio = h10.construir_features(df)
    COLUMNAS = h10.limpiar(X.loc[:FIN_SELECCION].dropna())

    y_h = (log_precio.shift(-H) - log_precio).rename("y")
    datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

    sel = datos.loc[:FIN_SELECCION]
    print(f"  seleccion: {len(sel)} obs ({sel.index.min().date()} a "
          f"{sel.index.max().date()}), {len(COLUMNAS)} variables")

    t = time.time()
    orden = ranquear(sel[COLUMNAS], sel["y"])
    print(f"  ranking listo [{time.time()-t:.0f}s]")

    # --- elegir k en validacion ---------------------------------------------
    ent_val = datos.loc[:INI_VALIDACION - pd.Timedelta(days=H + 1)]
    val = datos.loc[INI_VALIDACION:FIN_VALIDACION]
    mejores = []
    for k in ESCALERA:
        cols = list(orden.index) if k is None else list(orden.index[:k])
        r = evaluar(predecir(ent_val, val, cols, params), val, precio)
        mejores.append({"k": len(cols), **r})
        print(f"    val k={len(cols):3d}  {r['mejora_%']:+6.2f}%  "
              f"dir {r['Direccion_%']:5.1f}%", flush=True)
    tv = pd.DataFrame(mejores)
    K = int(tv.loc[tv["mejora_%"].idxmin(), "k"])
    cols = list(orden.index[:K]) if K < len(orden) else list(orden.index)
    print(f"  ==> k elegido por validacion: {K}")

    # --- medir ---------------------------------------------------------------
    filas = []
    for etapa, ini, fin in [("2023-2025", INI_PRUEBA, INI_2026 - pd.Timedelta(days=1)),
                            ("2026", INI_2026, datos.index.max())]:
        entrena = datos.loc[:ini - pd.Timedelta(days=H + 1)]
        prueba = datos.loc[ini:fin]
        r = evaluar(predecir(entrena, prueba, cols, params), prueba, precio)
        r.update({"panel": etiqueta, "etapa": etapa, "k": K,
                  "n_entrena": len(entrena)})
        filas.append(r)
        print(f"  {etapa}: entrena {len(entrena)} obs  ->  "
              f"{r['mejora_%']:+.2f}%  MAPE {r['MAPE_%']:.2f}% vs {r['MAPE_ing_%']:.2f}%  "
              f"dir {r['Direccion_%']:.1f}%  p={r['p_DM']:.4f}")
    return filas, K


def main():
    print("=" * 82)
    print(f"HISTORIA LARGA vs CORTA — horizonte de {H} dias")
    print("=" * 82)
    params = json.loads((SALIDA / "hiperparametros.json").read_text(encoding="utf-8"))[str(H)]
    print(f"hiperparametros (iguales para los dos): {params}")

    todo = []
    for etiqueta, ruta in PANELES.items():
        if not ruta.exists():
            print(f"[!] falta {ruta.name}")
            continue
        filas, _ = correr(etiqueta, ruta, params)
        todo += filas

    tabla = pd.DataFrame(todo)
    tabla.to_csv(SALIDA / f"largo_vs_corto_h{H}.csv", index=False)

    print("\n" + "=" * 82)
    print("COMPARACION")
    print("=" * 82)
    for etapa in ["2023-2025", "2026"]:
        s = tabla[tabla["etapa"] == etapa]
        if s.empty:
            continue
        print(f"\n--- {etapa} ---")
        print(s[["panel", "n_entrena", "k", "mejora_%", "MAPE_%", "MAPE_ing_%",
                 "Direccion_%", "p_DM"]].round(3).to_string(index=False))

    dos = tabla[tabla["etapa"] == "2026"]
    if len(dos) == 2:
        c = dos[dos["panel"].str.startswith("CORTO")].iloc[0]
        l = dos[dos["panel"].str.startswith("LARGO")].iloc[0]
        print("\n" + "=" * 82)
        print("VEREDICTO EN 2026")
        print("=" * 82)
        print(f"  entrenamiento: {c['n_entrena']} obs (corto) vs "
              f"{l['n_entrena']} obs (largo), x{l['n_entrena']/c['n_entrena']:.1f}")
        print(f"  mejora vs ingenuo: {c['mejora_%']:+.2f}% -> {l['mejora_%']:+.2f}%")
        print(f"  MAPE:              {c['MAPE_%']:.2f}% -> {l['MAPE_%']:.2f}%")
        print(f"  direccion:         {c['Direccion_%']:.1f}% -> {l['Direccion_%']:.1f}%")
        print(f"  p-valor:           {c['p_DM']:.4f} -> {l['p_DM']:.4f}")
        if l["mejora_%"] < c["mejora_%"]:
            print("\n  ==> la historia larga AYUDA")
        else:
            print("\n  ==> la historia larga NO ayuda: el cambio estructural del")
            print("      sistema pesa mas que las transiciones ENSO adicionales")

    print(f"\n[salida] {SALIDA/f'largo_vs_corto_h{H}.csv'}")


if __name__ == "__main__":
    main()
