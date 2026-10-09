"""
================================================================================
ETAPA 2 — EVALUACION POR BLOQUES (walk-forward + Diebold-Mariano)
================================================================================

Por que esta etapa existe
-------------------------
Significancia in-sample y valor predictivo out-of-sample son cosas distintas.
Una variable puede tener p < 0.001 y AUN ASI empeorar el pronostico por
sobreajuste. La pregunta que de verdad importa es:

    "¿Agregar este BLOQUE reduce el error en walk-forward?"

Por bloques y no variable por variable, por tres razones:
  - resuelve la multicolinealidad (los 4 lags del precio son UNA decision)
  - reduce las comparaciones de ~40 a ~6 (menos multiplicidad)
  - da estructura narrativa: "el bloque hidrologico aporta X% de reduccion de
    MAPE" es un resultado mucho mas defendible que una tabla de 40 p-valores

Diseno
------
Modelo base = solo bloque AR (lags del propio precio). Luego se agrega un
bloque a la vez y se contrasta contra la base con Diebold-Mariano usando la
correccion de Harvey-Leybourne-Newbold (necesaria con muestras finitas).

Todo modelo se contrasta ademas contra el PRONOSTICO INGENUO (precio de
ayer). Con una serie casi de caminata aleatoria, ganarle a la base AR no
basta: hay que mostrar que se le gana al pronostico mas simple posible.

Ventana
-------
Se evalua sobre VALIDACION (CONFIG["validation_start"] -> "validation_end",
2020-2022). La prueba 2023-2025 NO se toca aqui: si la eleccion de bloques se
hiciera sobre la prueba, las metricas finales de los notebooks quedarian
optimistas.

Uso
---
  python 02_evaluacion_bloques.py
================================================================================
"""

import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings("ignore")

# Reutiliza la config y las funciones de la etapa 1
from importlib import import_module
_e1 = import_module("01_seleccion_variables")
CONFIG = _e1.CONFIG

NOMBRE_INGENUO = "INGENUO (precio ayer)"


# ==============================================================================
# CONFIG DE LA ETAPA 2
# ==============================================================================

EVAL = {
    "sel_csv": Path(CONFIG["out_dir"]) / "features_seleccionadas.csv",

    # Ventana de VALIDACION, compartida con la etapa 1. NO es el periodo de
    # prueba: ese queda intacto para los notebooks 04/05.
    "eval_start": CONFIG["validation_start"],
    "eval_end": CONFIG["validation_end"],

    # Walk-forward: re-entrena cada 'refit_every' dias con ventana expansiva
    "refit_every": 30,
    "min_train": 730,      # 2 anios minimos de entrenamiento
    "horizon": 1,          # pronostico a 1 dia

    "block_base": "AR",    # el bloque que SIEMPRE esta presente

    # Arboles por modelo. 300 es solido; bajar a 150 corta el tiempo a la
    # mitad con poca perdida de precision, util para una primera pasada.
    "n_estimators": 300,

    # Muestra el progreso de cada walk-forward (sin esto el script parece
    # colgado durante minutos)
    "verbose": True,

    "out_dir": CONFIG["out_dir"],
}


def validar_ventana(cfg_eval, cfg=CONFIG):
    """
    Falla fuerte si la ventana de evaluacion toca el periodo de prueba o se
    traslapa con el periodo de seleccion de variables.
    """
    ini = pd.Timestamp(cfg_eval["eval_start"])
    fin = pd.Timestamp(cfg_eval["eval_end"])
    corte = pd.Timestamp(cfg["selection_cutoff"])
    test = pd.Timestamp(cfg["test_start"])
    if fin >= test:
        raise SystemExit(
            f"[FUGA] La evaluacion termina {fin.date()}, dentro del periodo de "
            f"prueba (desde {test.date()}). Usa la ventana de validacion.")
    if ini <= corte:
        raise SystemExit(
            f"[FUGA] La evaluacion empieza {ini.date()}, antes o en el corte de "
            f"seleccion ({corte.date()}): los bloques se evaluarian con los "
            f"mismos datos con que se seleccionaron.")


# ==============================================================================
# DIEBOLD-MARIANO (con correccion Harvey-Leybourne-Newbold)
# ==============================================================================

def diebold_mariano(e1, e2, h=1, power=2):
    """
    H0: los dos modelos tienen la misma precision predictiva.

    e1, e2 : errores de pronostico (modelo 1 y modelo 2)
    h      : horizonte del pronostico
    power  : 2 = perdida cuadratica (MSE), 1 = perdida absoluta (MAE)

    Devuelve (estadistico DM, p-valor a dos colas).
    Un DM < 0 significa que el modelo 1 tiene MENOR perdida (es mejor).

    La correccion HLN (Harvey, Leybourne & Newbold, 1997) ajusta el estadistico
    y usa distribucion t en lugar de normal. Sin ella, DM sobre-rechaza en
    muestras finitas -- que es justo el caso aqui (~1000 dias).
    """
    e1, e2 = np.asarray(e1, float), np.asarray(e2, float)
    ok = np.isfinite(e1) & np.isfinite(e2)
    e1, e2 = e1[ok], e2[ok]
    T = len(e1)
    if T < 20:
        return np.nan, np.nan

    d = np.abs(e1) ** power - np.abs(e2) ** power
    d_bar = d.mean()

    # varianza de largo plazo con autocovarianzas hasta h-1
    gamma0 = np.sum((d - d_bar) ** 2) / T
    gammas = [np.sum((d[k:] - d_bar) * (d[:-k] - d_bar)) / T
              for k in range(1, h)]
    V_d = (gamma0 + 2 * sum(gammas)) / T
    if V_d <= 0:
        return np.nan, np.nan

    DM = d_bar / np.sqrt(V_d)

    # correccion HLN
    hln = np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    DM_hln = DM * hln
    p = 2 * (1 - stats.t.cdf(abs(DM_hln), df=T - 1))
    return DM_hln, p


# ==============================================================================
# WALK-FORWARD
# ==============================================================================

def walk_forward(X, y, cols, eval_idx, cfg=EVAL, seed=42, etiqueta=""):
    """
    Ventana expansiva, re-entrenando cada refit_every dias.
    Devuelve una serie de errores alineada con eval_idx.

    Nota: el escalado / normalizacion se ajusta DENTRO de cada fold. Si se
    ajustara sobre toda la serie, se colaria informacion del futuro.
    """
    Xc = X[cols]
    preds = pd.Series(index=eval_idx, dtype=float)

    dates = list(eval_idx)
    bloques_refit = list(range(0, len(dates), cfg["refit_every"]))
    t0 = time.time()

    for j, i in enumerate(bloques_refit):
        chunk = dates[i:i + cfg["refit_every"]]
        cutoff = chunk[0] - pd.Timedelta(days=cfg["horizon"])

        tr = pd.concat([Xc.loc[:cutoff], y.loc[:cutoff]], axis=1).dropna()
        if len(tr) < cfg["min_train"]:
            continue

        model = RandomForestRegressor(
            n_estimators=cfg.get("n_estimators", 300),
            min_samples_leaf=5, n_jobs=-1, random_state=seed
        ).fit(tr[cols].values, tr[y.name].values)

        te = Xc.loc[chunk].dropna()
        if not te.empty:
            preds.loc[te.index] = model.predict(te.values)

        # progreso: sin esto el script parece colgado durante minutos
        if cfg.get("verbose", True):
            frac = (j + 1) / len(bloques_refit)
            transcurrido = time.time() - t0
            eta = transcurrido / frac - transcurrido if frac > 0 else 0
            print(f"\r    {etiqueta:16s} [{j+1:>3}/{len(bloques_refit)}] "
                  f"{frac:5.0%}  ETA {eta:4.0f}s", end="", flush=True)

    if cfg.get("verbose", True):
        print(f"\r    {etiqueta:16s} [{len(bloques_refit)}/"
              f"{len(bloques_refit)}] 100%  "
              f"({time.time()-t0:.0f}s)          ")

    err = (y.loc[eval_idx] - preds).rename("error")
    return err, preds


def pronostico_ingenuo(y, eval_idx, horizon=1):
    """
    Pronostico ingenuo: el valor de hoy es el ultimo observado,
    y_hat(t) = y(t - horizon). Es la referencia minima obligatoria para una
    serie casi de caminata aleatoria.
    """
    pred = y.shift(horizon).reindex(eval_idx).rename("pred")
    err = (y.reindex(eval_idx) - pred).rename("error")
    return err, pred


def metricas(y_true, y_pred, log_space=True, y_prev=None):
    """
    Metricas en la escala del modelo y MAPE en niveles.

    Acierto direccional (DA): UNA sola definicion en todo el proyecto (etapas
    02/03 y notebooks 04/05):

        signo(y(t) - y(t-1)) == signo(pred(t) - y(t-1))

    donde y(t-1) es el valor OBSERVADO de ayer. Es la pregunta que importa
    para decidir: "¿el modelo acierta si manana sube o baja respecto a hoy?".
    La version anterior comparaba pred(t) - pred(t-1), que mide si la
    TRAYECTORIA pronosticada se parece a la real y castiga a los modelos en
    nivel frente a los de diferencia.

    Si no se pasa y_prev, DA queda NaN. Si el modelo nunca predice un cambio
    (pronostico ingenuo), DA tambien es NaN: no hay direccion que evaluar.
    """
    d = pd.concat([y_true.rename("real"), y_pred.rename("pred")],
                  axis=1).dropna()
    if d.empty:
        return {}
    a, p = d["real"], d["pred"]

    # de vuelta a niveles para que el MAPE sea interpretable en COP/kWh
    if log_space:
        a_n, p_n = np.exp(a), np.exp(p)
    else:
        a_n, p_n = a, p

    out = {
        "n": len(d),
        "RMSE_log": float(np.sqrt(((a - p) ** 2).mean())),
        "MAE_log": float((a - p).abs().mean()),
        "MAPE_niv": float((((a_n - p_n) / a_n).abs()).mean() * 100),
        "DA_pct": np.nan,
    }
    if y_prev is not None:
        prev = y_prev.reindex(d.index)
        ok = prev.notna()
        mov_pred = (p - prev)[ok]
        if len(mov_pred) and (mov_pred.abs() > 1e-12).any():
            mov_real = (a - prev)[ok]
            out["DA_pct"] = float(
                (np.sign(mov_real) == np.sign(mov_pred)).mean() * 100)
    return out


def veredicto_dm(DM, p, alpha=0.05):
    if not (np.isfinite(DM) and np.isfinite(p)):
        return "no calculable"
    if p >= alpha:
        return "no concluyente"
    return "AGREGA" if DM < 0 else "EMPEORA"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    cfg, e2 = CONFIG, EVAL
    out = Path(e2["out_dir"]); out.mkdir(parents=True, exist_ok=True)
    validar_ventana(e2)

    print("=" * 72)
    print("ETAPA 2 — EVALUACION POR BLOQUES (ventana de VALIDACION)")
    print("=" * 72)

    df = _e1.cargar_panel(cfg)
    X, y = _e1.construir_features(df, cfg)

    sel = pd.read_csv(e2["sel_csv"], index_col=0)
    bloques = {b: [c for c in g.index if c in X.columns]
               for b, g in sel.groupby("bloque")}
    bloques = {b: c for b, c in bloques.items() if c}

    base_name = e2["block_base"]
    if base_name not in bloques:
        raise SystemExit(f"Falta el bloque base '{base_name}' en la seleccion.")

    base_cols = bloques[base_name]
    otros = {b: c for b, c in bloques.items() if b != base_name}

    print(f"[bloques] base = {base_name} ({len(base_cols)} feats)")
    for b, c in otros.items():
        print(f"          + {b}: {len(c)} feats")

    eval_idx = X.loc[e2["eval_start"]:e2["eval_end"]].index
    n_modelos = 1 + len(otros)
    n_refits = len(range(0, len(eval_idx), e2["refit_every"]))
    print(f"[eval]    {eval_idx.min().date()} -> {eval_idx.max().date()} "
          f"({len(eval_idx)} dias), refit cada {e2['refit_every']}d")
    print(f"          prueba {cfg['test_start']} -> {cfg['test_end']} NO se toca")
    print(f"          {n_modelos} modelos x {n_refits} reentrenamientos "
          f"= {n_modelos * n_refits} ajustes de Random Forest")
    print(f"          Esto toma varios minutos. Baja 'n_estimators' a 150 o "
          f"sube 'refit_every' a 60 si quieres una pasada rapida.")
    print("-" * 72)

    y_prev = y.shift(e2["horizon"])

    # ---- pronostico ingenuo -------------------------------------------------
    err_ing, pred_ing = pronostico_ingenuo(y, eval_idx, e2["horizon"])
    m_ing = metricas(y.loc[eval_idx], pred_ing, cfg["log_target"], y_prev)
    print(f"{NOMBRE_INGENUO}: MAPE {m_ing['MAPE_niv']:.2f}%  "
          f"RMSE_log {m_ing['RMSE_log']:.4f}")

    # ---- modelo base --------------------------------------------------------
    t_total = time.time()
    print(f"\nEntrenando base ({base_name})...")
    err_base, pred_base = walk_forward(X, y, base_cols, eval_idx,
                                       etiqueta=base_name)
    m_base = metricas(y.loc[eval_idx], pred_base, cfg["log_target"], y_prev)
    DMi, pi = diebold_mariano(err_base, err_ing, h=e2["horizon"], power=2)
    print(f"  MAPE {m_base['MAPE_niv']:.2f}%  RMSE_log {m_base['RMSE_log']:.4f}"
          f"  DA {m_base['DA_pct']:.1f}%")
    print(f"  vs ingenuo: DM {DMi:+.3f}  p={pi:.4f}  -> "
          f"{veredicto_dm(DMi, pi)}")

    filas = [
        {"modelo": NOMBRE_INGENUO, **m_ing, "DM": np.nan, "p_DM": np.nan,
         "DM_ingenuo": np.nan, "p_ingenuo": np.nan, "mejora_MAPE_pp": np.nan},
        {"modelo": base_name, **m_base, "DM": np.nan, "p_DM": np.nan,
         "DM_ingenuo": DMi, "p_ingenuo": pi, "mejora_MAPE_pp": 0.0},
    ]

    # ---- base + cada bloque ------------------------------------------------
    for b, cols in otros.items():
        print(f"\nEntrenando {base_name} + {b}...")
        cols_b = base_cols + cols
        err_b, pred_b = walk_forward(X, y, cols_b, eval_idx,
                                     etiqueta=f"{base_name}+{b}")
        m_b = metricas(y.loc[eval_idx], pred_b, cfg["log_target"], y_prev)

        # DM(modelo_con_bloque, base): DM < 0 y p < 0.05 => el bloque AYUDA
        DM, p = diebold_mariano(err_b, err_base, h=e2["horizon"], power=2)
        DMi, pi = diebold_mariano(err_b, err_ing, h=e2["horizon"], power=2)
        mejora = m_base["MAPE_niv"] - m_b["MAPE_niv"]

        print(f"  MAPE {m_b['MAPE_niv']:.2f}% ({mejora:+.2f} pp)  "
              f"DM {DM:+.3f}  p={p:.4f}  -> {veredicto_dm(DM, p)}")
        print(f"  vs ingenuo: DM {DMi:+.3f}  p={pi:.4f}  -> "
              f"{veredicto_dm(DMi, pi)}")

        filas.append({"modelo": f"{base_name}+{b}", **m_b, "DM": DM,
                      "p_DM": p, "DM_ingenuo": DMi, "p_ingenuo": pi,
                      "mejora_MAPE_pp": mejora})

    res = pd.DataFrame(filas).set_index("modelo")
    res["ventana"] = f"{eval_idx.min().date()}_{eval_idx.max().date()}"
    res.to_csv(out / "evaluacion_bloques.csv")

    print(f"\n[tiempo]  {time.time() - t_total:.0f}s en total")
    print("=" * 72)
    print(res.drop(columns="ventana").round(4).to_string())
    print("=" * 72)

    ganadores = res[(res["DM"] < 0) & (res["p_DM"] < 0.05)].index.tolist()
    print(f"\nBloques con aporte significativo al 5%: "
          f"{ganadores if ganadores else 'ninguno'}")
    le_ganan = res[(res["DM_ingenuo"] < 0) &
                   (res["p_ingenuo"] < 0.05)].index.tolist()
    print(f"Modelos que le ganan al pronostico ingenuo al 5%: "
          f"{le_ganan if le_ganan else 'ninguno'}")
    print("\nLECTURA: DM < 0 con p < 0.05 => el bloque reduce el error de forma")
    print("estadisticamente significativa. p >= 0.05 no prueba que sea inutil;")
    print("prueba que no hay evidencia suficiente con esta muestra.")
    print(f"\n[salida]  {out/'evaluacion_bloques.csv'}")


if __name__ == "__main__":
    main()
