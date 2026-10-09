"""
================================================================================
HORIZONTES MULTIPLES — XGBoost a 1, 7, 15, 30, 60 y 90 dias
================================================================================

Pregunta: hasta que horizonte sirve el modelo, y a partir de cual deja de
ganarle al ingenuo.

A un dia el precio tiene tanta memoria que "manana = hoy" es casi imbatible. A
medida que crece el horizonte esa memoria se agota y la estructura del sistema
(hidrologia, mezcla de generacion, concentracion) deberia empezar a pesar. Este
script mide donde esta ese cruce.

OBJETIVO PARA EL HORIZONTE h
----------------------------
    y_t^(h) = log P(t+h) - log P(t)

Es el cambio ACUMULADO en h dias, no el cambio diario de dentro de h dias. Para
planeacion tactica (mantenimientos, gestion de embalses, coberturas) lo que
importa es el nivel del precio dentro de h dias, y eso se reconstruye como

    P_hat(t+h) = P(t) * exp(y_hat)

El ingenuo correspondiente es y_hat = 0, es decir "el precio dentro de h dias
sera el de hoy" (caminata aleatoria).

DOS TRAMPAS QUE ESTE SCRIPT RESUELVE
------------------------------------
1. FUGA POR EL OBJETIVO. El objetivo en t usa P(t+h). Si el desarrollo termina
   el 2022-12-31 y h=90, ese objetivo mira hasta marzo de 2023, que es periodo
   de prueba. Por eso el desarrollo se recorta a (inicio_prueba - h - 1).

2. VENTANAS SOLAPADAS. Con h=90 dos observaciones consecutivas comparten 89
   dias, asi que los errores estan autocorrelacionados. La validacion cruzada
   usa gap=h entre entrenamiento y validacion, y el Diebold-Mariano usa h
   rezagos de Newey-West.

Uso
---
  python 10_horizontes.py
================================================================================
"""

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
PANEL = BASE / "panel_diario_ampliado.csv"
SALIDA = BASE / "salidas_horizontes"
SALIDA.mkdir(exist_ok=True)

# Corte de datos. Sirve para reafinar hiperparametros sobre el panel que ya
# incluye 2026 SIN dejar que 2026 entre: se trunca antes de hacer nada.
# None = usar todo lo que haya.
FIN_DATOS = None

OBJETIVO = "precio_ponderado"
FIN_SELECCION = pd.Timestamp("2019-12-31")
INI_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
INI_PRUEBA = pd.Timestamp("2023-01-01")

HORIZONTES = [1, 7, 15, 30, 60, 90]
SEMILLA = 42
N_BUSQUEDA = 15          # configuraciones de hiperparametros por horizonte
N_SPLITS_BUSQUEDA = 3    # folds en la busqueda (mas folds = mas lento)

LAGS = [1, 2, 3, 7, 14, 30]
VENTANAS = [7, 30]

ESPACIO = {
    "n_estimators":     [200, 400, 600, 900],
    "max_depth":        [2, 3, 4, 5],
    "learning_rate":    [0.01, 0.02, 0.05, 0.1],
    "subsample":        [0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "min_child_weight": [1, 5, 10, 20],
    "reg_lambda":       [0.5, 1.0, 3.0, 10.0],
}

DESPACHO = ["costo_marginal_prog", "precio_oferta_desp", "max_precio_oferta"]
EX_ANTE = ["precio_escasez", "precio_marg_escasez", "precio_escasez_empalmado",
           "disp_declarada", "enficc", "precio_cargo_conf", "cee", "cere", "mc",
           "margen_reserva", "dummy_creg_escasez",
           "disp_decl_hidraulica", "disp_decl_termica", "disp_decl_despacho_central"]
EVENTOS = ["vertimientos", "demanda_no_atendida", "dem_no_atendida_noprog",
           "importaciones", "exportaciones",
           "gen_solar", "frac_solar", "gen_eolica", "frac_eolica", "gen_liquidos"]
MAX_FALTANTE = 0.15
INICIO_MAXIMO = pd.Timestamp("2015-03-01")


# ==============================================================================
# CARACTERISTICAS  (identicas a las del notebook 09)
# ==============================================================================

def construir_features(df):
    precio = df[OBJETIVO]
    log_precio = np.log(precio)

    panel = df.copy()
    ev = [c for c in EVENTOS if c in panel.columns]
    panel[ev] = panel[ev].fillna(0)

    arranque = panel.apply(lambda s: s.first_valid_index())
    tardias = [c for c in panel.columns
               if arranque[c] is not None and arranque[c] > INICIO_MAXIMO
               and panel[c].isna().mean() <= MAX_FALTANTE]

    faltan = panel.isna().mean()
    candidatas = [c for c in panel.columns
                  if c != OBJETIVO and c not in DESPACHO and c not in tardias
                  and faltan[c] <= MAX_FALTANTE]

    base = panel[candidatas].ffill()
    base["inv_volumen_util_pct"] = 1 / base["volumen_util_pct"].clip(lower=0.02)

    ex_ante = [c for c in base.columns if c in EX_ANTE]
    ex_post = [c for c in base.columns if c not in EX_ANTE]

    piezas = {}
    dlog = log_precio.diff()
    for k in LAGS:
        piezas[f"dlog_lag{k}"] = dlog.shift(k)
    for w in VENTANAS:
        piezas[f"dlog_sd{w}"] = dlog.shift(1).rolling(w).std()
        piezas[f"precio_choque{w}"] = (log_precio.shift(1)
                                       - log_precio.shift(1).rolling(w).mean())

    for col in ex_ante:
        for k in [0] + LAGS:
            piezas[f"{col}_lag{k}"] = base[col].shift(k)
    for col in ex_post:
        for k in LAGS:
            piezas[f"{col}_lag{k}"] = base[col].shift(k)
    for col in base.columns:
        for w in VENTANAS:
            piezas[f"{col}_choque{w}"] = (base[col].shift(1)
                                          - base[col].shift(1).rolling(w).mean())
            piezas[f"{col}_ma{w}"] = base[col].shift(1).rolling(w).mean()

    X = pd.DataFrame(piezas, index=df.index)
    X["es_lunes"] = (df.index.dayofweek == 0).astype(int)
    X["es_sabado"] = (df.index.dayofweek == 5).astype(int)
    X["es_domingo"] = (df.index.dayofweek == 6).astype(int)

    print(f"[features] {X.shape[1]} caracteristicas construidas "
          f"({len(tardias)} variables descartadas por arranque tardio)")
    return X, precio, log_precio


def limpiar(X_sel):
    """Constantes, redundantes y combinaciones lineales exactas."""
    no_const = X_sel.columns[X_sel.std() > 0]
    Xc = X_sel[no_const]

    corr = Xc.corr().abs()
    quitar = set()
    for i, a in enumerate(Xc.columns):
        if a in quitar:
            continue
        for b in Xc.columns[i + 1:]:
            if corr.loc[a, b] > 0.95:
                quitar.add(b)
    no_red = [c for c in Xc.columns if c not in quitar]

    Z = ((Xc[no_red] - Xc[no_red].mean()) / Xc[no_red].std()).values
    elegidas = []
    for i, _ in enumerate(no_red):
        if np.linalg.matrix_rank(Z[:, elegidas + [i]]) > len(elegidas):
            elegidas.append(i)
    return [no_red[i] for i in elegidas]


# ==============================================================================
# EVALUACION
# ==============================================================================

def metricas(y_real, pred, precio_hoy, precio_futuro):
    pred = pd.Series(np.ravel(pred), index=y_real.index)
    nivel = precio_hoy * np.exp(pred)
    direccion = (np.nan if (pred == 0).all()
                 else 100 * np.mean(np.sign(pred) == np.sign(y_real)))
    return {
        "RMSE_log": float(np.sqrt(np.mean((y_real - pred) ** 2))),
        "MAE_log": float(np.mean(np.abs(y_real - pred))),
        "Direccion_%": direccion,
        "MAPE_nivel_%": float(100 * np.mean(np.abs(nivel - precio_futuro) / precio_futuro)),
    }


def diebold_mariano(e1, e2, h=1):
    """h rezagos de Newey-West: obligatorio con ventanas solapadas."""
    d = (e1 ** 2 - e2 ** 2).dropna()
    n = len(d)
    if n < 20:
        return np.nan, np.nan
    d_barra = d.mean()
    gamma = [d.var(ddof=0)] + [np.cov(d[k:], d[:n - k])[0, 1] for k in range(1, h)]
    var_d = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var_d <= 0:
        return np.nan, np.nan
    dm = d_barra / np.sqrt(var_d)
    correccion = np.sqrt(max(1e-9, (n + 1 - 2 * h + h * (h - 1) / n) / n))
    dm *= correccion
    return float(dm), float(2 * (1 - stats.t.cdf(abs(dm), df=n - 1)))


def buscar_hiperparametros(X, y, h, rng):
    """Busqueda aleatoria con gap=h entre entrenamiento y validacion."""
    tscv = TimeSeriesSplit(n_splits=N_SPLITS_BUSQUEDA, gap=h)
    Xv, yv = X.values, y.values
    mejor, mejor_rmse = None, np.inf

    for _ in range(N_BUSQUEDA):
        p = {k: rng.choice(v).item() for k, v in ESPACIO.items()}
        errores = []
        for tr, va in tscv.split(Xv):
            m = xgb.XGBRegressor(**p, random_state=SEMILLA, n_jobs=-1,
                                 tree_method="hist")
            m.fit(Xv[tr], yv[tr])
            errores.append(np.sqrt(np.mean((yv[va] - m.predict(Xv[va])) ** 2)))
        rmse = float(np.mean(errores))
        if rmse < mejor_rmse:
            mejor, mejor_rmse = p, rmse

    return mejor, mejor_rmse


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 74)
    print("HORIZONTES MULTIPLES")
    print("=" * 74)

    df = pd.read_csv(PANEL, parse_dates=["fecha"], index_col="fecha").sort_index().asfreq("D")
    if FIN_DATOS is not None:
        df = df.loc[:FIN_DATOS]
        print(f"[corte]    datos truncados en {FIN_DATOS} (lo posterior queda fuera)")
    print(f"[panel]    {df.shape[0]} dias x {df.shape[1]} variables")

    X, precio, log_precio = construir_features(df)

    # La limpieza se hace UNA vez, con la ventana de seleccion del horizonte mas
    # corto. Repetirla por horizonte cambiaria el conjunto de candidatas y haria
    # incomparables los resultados entre horizontes.
    X_sel_ref = X.loc[:FIN_SELECCION].dropna()
    COLUMNAS = limpiar(X_sel_ref)
    print(f"[limpieza] {X.shape[1]} -> {len(COLUMNAS)} caracteristicas\n")

    rng = np.random.default_rng(SEMILLA)
    filas, params_por_h, predicciones = [], {}, {}

    for h in HORIZONTES:
        t0 = time.time()
        print("-" * 74)
        print(f"HORIZONTE h = {h} dia(s)")

        # --- objetivo: cambio acumulado a h dias ---------------------------
        y_h = (log_precio.shift(-h) - log_precio).rename("y")

        datos = pd.concat([X[COLUMNAS], y_h], axis=1).dropna()

        # --- FUGA POR EL OBJETIVO: el desarrollo se recorta h dias ----------
        # El objetivo en t mira hasta t+h, asi que el ultimo t de desarrollo
        # debe cumplir t + h < inicio_prueba.
        fin_dev = INI_PRUEBA - pd.Timedelta(days=h + 1)
        dev = datos.loc[:fin_dev]
        prueba = datos.loc[INI_PRUEBA:]

        print(f"  desarrollo {dev.index.min().date()} a {dev.index.max().date()} "
              f"({len(dev)} obs; se recortaron {h} dias por el objetivo)")
        print(f"  prueba     {prueba.index.min().date()} a {prueba.index.max().date()} "
              f"({len(prueba)} obs)")

        # --- busqueda de hiperparametros con gap=h --------------------------
        params, rmse_cv = buscar_hiperparametros(dev[COLUMNAS], dev["y"], h, rng)
        params_por_h[h] = params
        print(f"  mejor RMSE en CV (gap={h}): {rmse_cv:.5f}")

        # --- entrenamiento y prueba ----------------------------------------
        modelo = xgb.XGBRegressor(**params, random_state=SEMILLA, n_jobs=-1,
                                  tree_method="hist")
        modelo.fit(dev[COLUMNAS], dev["y"])
        pred = pd.Series(modelo.predict(prueba[COLUMNAS]), index=prueba.index)
        predicciones[h] = pred

        precio_hoy = precio.reindex(prueba.index)
        precio_futuro = precio.reindex(prueba.index + pd.Timedelta(days=h))
        precio_futuro.index = prueba.index

        m_modelo = metricas(prueba["y"], pred, precio_hoy, precio_futuro)
        m_ingenuo = metricas(prueba["y"], np.zeros(len(prueba)), precio_hoy, precio_futuro)

        e_mod = prueba["y"] - pred
        e_ing = prueba["y"]
        dm, p_dm = diebold_mariano(e_mod, e_ing, h=h)

        mejora = 100 * (m_modelo["RMSE_log"] / m_ingenuo["RMSE_log"] - 1)
        veredicto = ("gana el modelo" if p_dm < 0.05 and dm < 0
                     else "gana el ingenuo" if p_dm < 0.05 else "sin diferencia")

        print(f"  RMSE log   modelo {m_modelo['RMSE_log']:.4f}  "
              f"ingenuo {m_ingenuo['RMSE_log']:.4f}  ({mejora:+.1f}%)")
        print(f"  MAPE nivel modelo {m_modelo['MAPE_nivel_%']:.2f}%  "
              f"ingenuo {m_ingenuo['MAPE_nivel_%']:.2f}%")
        print(f"  Direccion  {m_modelo['Direccion_%']:.1f}%")
        print(f"  DM = {dm:.3f}  p = {p_dm:.4f}  ->  {veredicto}   "
              f"[{time.time()-t0:.0f}s]")

        filas.append({"h": h, "n_dev": len(dev), "n_prueba": len(prueba),
                      "rmse_cv": rmse_cv,
                      "RMSE_modelo": m_modelo["RMSE_log"],
                      "RMSE_ingenuo": m_ingenuo["RMSE_log"],
                      "mejora_%": mejora,
                      "MAPE_modelo_%": m_modelo["MAPE_nivel_%"],
                      "MAPE_ingenuo_%": m_ingenuo["MAPE_nivel_%"],
                      "Direccion_%": m_modelo["Direccion_%"],
                      "DM": dm, "p_DM": p_dm, "veredicto": veredicto})

        # --- que variables usa este horizonte -------------------------------
        imp = pd.Series(modelo.feature_importances_, index=COLUMNAS)
        imp.sort_values(ascending=False).head(15).to_csv(
            SALIDA / f"importancia_h{h:02d}.csv")

    tabla = pd.DataFrame(filas).set_index("h")
    tabla.to_csv(SALIDA / "resumen_horizontes.csv")
    (SALIDA / "hiperparametros.json").write_text(
        json.dumps({str(k): v for k, v in params_por_h.items()}, indent=2),
        encoding="utf-8")
    pd.DataFrame(predicciones).to_csv(SALIDA / "predicciones_por_horizonte.csv")

    print("\n" + "=" * 74)
    print("RESUMEN")
    print("=" * 74)
    print(tabla[["RMSE_modelo", "RMSE_ingenuo", "mejora_%", "MAPE_modelo_%",
                 "MAPE_ingenuo_%", "Direccion_%", "p_DM", "veredicto"]].round(4).to_string())
    print(f"\n[salida] {SALIDA}")
    print("  resumen_horizontes.csv, hiperparametros.json,")
    print("  predicciones_por_horizonte.csv, importancia_h*.csv")
    print("\nLos hiperparametros guardados son los que usara el test de 2026:")
    print("se reentrena con TODO hasta 2025 y se prueba solo en 2026.")


if __name__ == "__main__":
    main()
