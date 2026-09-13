"""
================================================================================
ETAPA 3 — BLOQUES CANDIDATOS Y MODELOS COMBINADOS
================================================================================

Dos preguntas que la etapa 2 dejo abiertas
------------------------------------------

1) COMBUSTIBLE: ¿aporta el precio de escasez por su cuenta?
   En la etapa 2, el bloque REGULATORIO se probo con cee, cere y mc, que son
   cargos tarifarios menores. El precio de escasez NUNCA se probo solo, y hay
   dos razones mecanicas para probarlo:
     - es el TECHO del precio de bolsa (define cuando se hacen exigibles las
       entregas de los generadores con cargo por confiabilidad)
     - esta INDEXADO al New York Harbor Residual Fuel Oil spot del mes
       anterior, y el gas regulado de la Guajira se indexa semestralmente a
       ese mismo valor (ACOLGEN). O sea: es el canal por el que el costo
       internacional de combustibles entra al mercado electrico colombiano.
   Como el precio del gas (iGas-D) no se consiguio en serie diaria, este es
   el mejor proxy disponible -- y tiene cobertura 100% desde 2015.

2) ADITIVIDAD: HIDRO y OFERTA ganaron por separado. ¿Sus aportes se suman o
   se solapan? margen_reserva y el nivel de embalses podrian estar capturando
   parte de la misma seniale de escasez.

Ademas se agrega la TRANSFORMACION CONVEXA de reservas (1/volumen_util_pct):
el EDA encontro que la sensibilidad del precio es mucho mayor a niveles bajos
de embalse. RF y XGBoost aproximan esa convexidad con particiones, pero un
modelo lineal (SARIMAX) no puede representarla sin la transformacion explicita.

CORRECCION POR MULTIPLICIDAD
---------------------------
Se prueban varios modelos contra la misma base, asi que los p-valores de DM
se corrigen con Benjamini-Hochberg -- el mismo criterio que se aplico a
Granger en la etapa 1. Sin esto, probar 8 modelos garantiza ~1 "significativo"
por azar.

VENTANA Y SALIDA
----------------
Todo se evalua sobre VALIDACION (2020-2022). La prueba 2023-2025 no se toca.
Cada modelo se contrasta tambien contra el pronostico ingenuo (precio de
ayer). El modelo ganador se escribe en modelo_final.json, que es lo que leen
los notebooks 04 y 05: asi las features del modelo final salen del pipeline
y no de una lista copiada a mano.

Uso
---
  python 03_bloques_candidatos.py
================================================================================
"""

import json
import time
import warnings
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")

_e1 = import_module("01_seleccion_variables")
_e2 = import_module("02_evaluacion_bloques")
CONFIG = _e1.CONFIG
NOMBRE_INGENUO = _e2.NOMBRE_INGENUO


# ==============================================================================
# CONFIG
# ==============================================================================

EVAL3 = {
    # Ventana de VALIDACION compartida con 01 y 02. No es la prueba.
    "eval_start": CONFIG["validation_start"],
    "eval_end": CONFIG["validation_end"],
    "refit_every": 30,
    "min_train": 730,
    "horizon": 1,
    "n_estimators": 300,
    "verbose": True,
    "fdr_alpha": 0.05,
    "out_dir": CONFIG["out_dir"],

    # Nombre de un modelo de MODELOS para fijarlo a mano como modelo final
    # (por ejemplo por justificacion teorica). None = regla automatica:
    # menor MAPE entre los que mejoran la base AR con DM < 0 y p_FDR < alpha.
    "modelo_forzado": None,
}


# ==============================================================================
# BLOQUES (definidos a mano, no leidos del CSV de seleccion)
# ==============================================================================
#
# Se listan por NOMBRE DE FEATURE ya rezagada, tal como las construye
# construir_features() de la etapa 1. Si alguna no existe en tu panel el
# script la reporta y la omite en vez de fallar.

BLOQUES = {
    "AR": [
        "log_precio_lag1",
        "log_precio_ma30",
        "log_precio_sd7",
    ],
    "OFERTA": [
        # Disponibilidad DECLARADA del mismo dia: va en la oferta del dia
        # anterior. Reemplaza a disp_comercial_lag0, que XM ajusta con la
        # operacion real y por tanto no se conoce antes del despacho.
        "disp_declarada_lag0",
        "margen_reserva_lag0",
        "margen_reserva_lag7",
        "disp_declarada_d7",
        "gen_programada_lag7",
    ],
    "HIDRO": [
        "aportes_pct_sistema_lag1",
        "aportes_por_rio_lag2",
        "aportes_media_hist_lag30",
        "volumen_util_pct_lag1",
        "inv_volumen_util_pct_lag1",   # transformacion convexa (ver abajo)
        "volumen_util_pct_emb_d7",
        "oni_lag1",                    # el panel ya trae el rezago de
                                       # publicacion de NOAA (2 meses)
    ],
    # EL BLOQUE NUEVO: precio de escasez como proxy de costo de combustible
    "COMBUSTIBLE": [
        "precio_escasez_lag0",
        "precio_escasez_d7",
        "precio_marg_escasez_lag1",
        "dummy_creg_escasez_lag0",
    ],
    "DEMANDA": [
        "demanda_no_regulada_lag7",
        "demanda_por_or_lag14",
        "demanda_upme_medio_lag14",
    ],
}

# Modelos a comparar. Cada uno es una lista de bloques; AR siempre va incluido.
MODELOS = {
    "AR":                        ["AR"],
    "AR+COMBUSTIBLE":            ["AR", "COMBUSTIBLE"],
    "AR+HIDRO":                  ["AR", "HIDRO"],
    "AR+OFERTA":                 ["AR", "OFERTA"],
    "AR+HIDRO+OFERTA":           ["AR", "HIDRO", "OFERTA"],
    "AR+HIDRO+OFERTA+COMB":      ["AR", "HIDRO", "OFERTA", "COMBUSTIBLE"],
    "AR+HIDRO+OFERTA+DEM":       ["AR", "HIDRO", "OFERTA", "DEMANDA"],
    "COMPLETO":                  ["AR", "HIDRO", "OFERTA", "COMBUSTIBLE",
                                  "DEMANDA"],
}


# ==============================================================================
# TRANSFORMACION CONVEXA DE RESERVAS
# ==============================================================================

def agregar_convexa(df, cfg):
    """
    1 / volumen_util_pct.

    El EDA encontro que la relacion reservas-precio es CONVEXA: la sensibilidad
    marginal del precio es mucho mayor a niveles bajos de embalse. El inverso
    es la forma funcional mas simple que captura eso: crece lentamente cuando
    el embalse esta lleno y se dispara cuando se vacia.

    Sin esta columna, SARIMAX (lineal) no puede representar esa relacion en
    absoluto. Los arboles la aproximan con particiones, pero le cuesta mas
    datos llegar ahi.

    Se acota el denominador por abajo para que el inverso no explote si el
    porcentaje se acerca a cero.
    """
    col = "volumen_util_pct"
    if col not in df.columns:
        print(f"  [X] no encuentro '{col}', no se crea la convexa")
        return df

    v = pd.to_numeric(df[col], errors="coerce")

    # El panel guarda el nivel como fraccion (0-1). Si viniera en 0-100 el
    # inverso cambia de escala pero no de forma; se detecta para avisar.
    escala = "fraccion (0-1)" if v.max() <= 1.5 else "porcentaje (0-100)"
    piso = 0.02 if v.max() <= 1.5 else 2.0

    df["inv_volumen_util_pct"] = 1.0 / v.clip(lower=piso)
    print(f"  [OK] inv_volumen_util_pct = 1 / {col}  "
          f"[escala detectada: {escala}, piso {piso}]")
    print(f"       rango {df['inv_volumen_util_pct'].min():.3f} - "
          f"{df['inv_volumen_util_pct'].max():.3f}")
    return df


# ==============================================================================
# ELECCION DEL MODELO FINAL
# ==============================================================================

def elegir_modelo_final(res, alpha, base="AR", forzado=None):
    """
    Regla: entre los modelos que mejoran la base AR con DM < 0 y p_FDR < alpha,
    el de menor MAPE en validacion. Si ninguno la mejora, se queda la base.
    """
    if forzado:
        if forzado not in res.index:
            raise SystemExit(f"modelo_forzado='{forzado}' no esta entre los "
                             f"modelos evaluados: {list(res.index)}")
        return forzado, "fijado a mano en EVAL3['modelo_forzado']"

    signif = res["signif_FDR"].fillna(False).astype(bool)
    cand = res[(~res.index.isin([base, NOMBRE_INGENUO])) &
               (res["DM"] < 0) & signif]
    if cand.empty:
        return base, (f"ningun modelo mejora la base {base} con DM<0 y "
                      f"p_FDR<{alpha}; se queda la base")
    return cand["MAPE_niv"].idxmin(), (
        f"menor MAPE en validacion entre los modelos que mejoran la base "
        f"{base} con DM<0 y p_FDR<{alpha}")


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    cfg = CONFIG
    out = Path(EVAL3["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    _e2.validar_ventana(EVAL3)

    print("=" * 72)
    print("ETAPA 3 — BLOQUES CANDIDATOS Y MODELOS COMBINADOS (VALIDACION)")
    print("=" * 72)

    df = _e1.cargar_panel(cfg)
    print(f"[carga]   panel {df.shape[0]} filas x {df.shape[1]} cols")

    print("\n[convexa] transformacion de reservas")
    df = agregar_convexa(df, cfg)

    X, y = _e1.construir_features(df, cfg)
    print(f"\n[feats]   {X.shape[1]} features construidas")

    # ---- validar que las features de cada bloque existan -------------------
    bloques_ok, faltantes_total = {}, []
    for nombre, feats in BLOQUES.items():
        presentes = [f for f in feats if f in X.columns]
        faltan = [f for f in feats if f not in X.columns]
        if faltan:
            faltantes_total.extend(faltan)
            print(f"  [!] {nombre}: faltan {faltan}")
        if presentes:
            bloques_ok[nombre] = presentes

    if faltantes_total:
        print(f"\n  Nota: las features faltantes se omiten. Si son muchas, "
              f"revisa que el panel tenga las columnas base correspondientes.")

    print(f"\n[bloques] " + ", ".join(f"{k}={len(v)}"
                                      for k, v in bloques_ok.items()))

    # ---- ventana de evaluacion ---------------------------------------------
    eval_idx = X.loc[EVAL3["eval_start"]:EVAL3["eval_end"]].index
    n_refits = len(range(0, len(eval_idx), EVAL3["refit_every"]))
    print(f"[eval]    {eval_idx.min().date()} -> {eval_idx.max().date()} "
          f"({len(eval_idx)} dias)")
    print(f"          prueba {cfg['test_start']} -> {cfg['test_end']} NO se toca")
    print(f"          {len(MODELOS)} modelos x {n_refits} reentrenamientos "
          f"= {len(MODELOS) * n_refits} ajustes")
    print("-" * 72)

    y_prev = y.shift(EVAL3["horizon"])

    # ---- pronostico ingenuo -------------------------------------------------
    err_ing, pred_ing = _e2.pronostico_ingenuo(y, eval_idx, EVAL3["horizon"])
    m_ing = _e2.metricas(y.loc[eval_idx], pred_ing, cfg["log_target"], y_prev)
    print(f"{NOMBRE_INGENUO}: MAPE {m_ing['MAPE_niv']:.2f}%  "
          f"RMSE_log {m_ing['RMSE_log']:.4f}")

    # ---- correr cada modelo -------------------------------------------------
    t0 = time.time()
    resultados, errores, columnas = {}, {}, {}

    for nombre, lista_bloques in MODELOS.items():
        cols = []
        for b in lista_bloques:
            if b in bloques_ok:
                cols.extend(bloques_ok[b])
        cols = list(dict.fromkeys(cols))  # dedup preservando orden

        if not cols:
            print(f"\n{nombre}: sin features disponibles, se omite")
            continue

        print(f"\n{nombre}  ({len(cols)} feats)")
        err, pred = _e2.walk_forward(X, y, cols, eval_idx, cfg=EVAL3,
                                     etiqueta=nombre)
        m = _e2.metricas(y.loc[eval_idx], pred, cfg["log_target"], y_prev)
        errores[nombre] = err
        resultados[nombre] = m
        columnas[nombre] = cols
        print(f"  MAPE {m['MAPE_niv']:.2f}%  RMSE_log {m['RMSE_log']:.4f}  "
              f"DA {m['DA_pct']:.1f}%  (n={m['n']})")

    # ---- Diebold-Mariano contra la base y contra el ingenuo ----------------
    base = "AR"
    if base not in errores:
        raise SystemExit("No se pudo entrenar el modelo base AR.")

    filas = [{"modelo": NOMBRE_INGENUO, **m_ing, "DM": np.nan,
              "p_DM": np.nan, "p_FDR": np.nan, "DM_ingenuo": np.nan,
              "p_ingenuo": np.nan, "mejora_MAPE_pp": np.nan}]
    pvals, nombres_test = [], []
    for nombre, m in resultados.items():
        DMi, pi = _e2.diebold_mariano(errores[nombre], err_ing,
                                      h=EVAL3["horizon"], power=2)
        if nombre == base:
            filas.append({"modelo": nombre, **m, "DM": np.nan,
                          "p_DM": np.nan, "p_FDR": np.nan,
                          "DM_ingenuo": DMi, "p_ingenuo": pi,
                          "mejora_MAPE_pp": 0.0})
            continue
        DM, p = _e2.diebold_mariano(errores[nombre], errores[base],
                                    h=EVAL3["horizon"], power=2)
        filas.append({
            "modelo": nombre, **m, "DM": DM, "p_DM": p, "p_FDR": np.nan,
            "DM_ingenuo": DMi, "p_ingenuo": pi,
            "mejora_MAPE_pp": resultados[base]["MAPE_niv"] - m["MAPE_niv"],
        })
        if np.isfinite(p):
            pvals.append(p)
            nombres_test.append(nombre)

    res = pd.DataFrame(filas).set_index("modelo")

    # ---- correccion FDR -----------------------------------------------------
    if pvals:
        rej, p_adj, _, _ = multipletests(pvals, alpha=EVAL3["fdr_alpha"],
                                         method="fdr_bh")
        for nombre, pa in zip(nombres_test, p_adj):
            res.loc[nombre, "p_FDR"] = pa
    res["signif_FDR"] = (res["p_FDR"] < EVAL3["fdr_alpha"]).fillna(False)

    res = res.sort_values("MAPE_niv")
    res["ventana"] = f"{eval_idx.min().date()}_{eval_idx.max().date()}"
    res.to_csv(out / "bloques_candidatos.csv")

    print(f"\n[tiempo]  {time.time() - t0:.0f}s")
    print("=" * 72)
    cols_show = ["n", "MAPE_niv", "RMSE_log", "DA_pct", "DM", "p_DM",
                 "p_FDR", "signif_FDR", "DM_ingenuo", "p_ingenuo",
                 "mejora_MAPE_pp"]
    cols_show = [c for c in cols_show if c in res.columns]
    print(res[cols_show].round(4).to_string())
    print("=" * 72)

    # ---- lectura ------------------------------------------------------------
    print("\nLECTURA")
    ganadores = res[res["signif_FDR"] & (res["DM"] < 0)].index.tolist()
    print(f"  Mejoran la base con significancia tras FDR al "
          f"{EVAL3['fdr_alpha']:.0%}: "
          f"{ganadores if ganadores else 'ninguno'}")
    le_ganan = res[(res["DM_ingenuo"] < 0) &
                   (res["p_ingenuo"] < 0.05)].index.tolist()
    print(f"  Le ganan al pronostico ingenuo al 5%: "
          f"{le_ganan if le_ganan else 'ninguno'}")

    if "AR+COMBUSTIBLE" in res.index:
        r = res.loc["AR+COMBUSTIBLE"]
        sig = bool(r["signif_FDR"])
        if r["DM"] < 0 and sig:
            veredicto = "APORTA"
            nota = ("Tienes proxy de costo de combustible con cobertura 100% "
                    "sin necesitar el iGas-D.")
        elif r["DM"] > 0 and sig:
            veredicto = "PERJUDICA (significativo)"
            nota = ("El bloque EMPEORA el pronostico de forma significativa. "
                    "Probable causa: el precio de escasez es un precio "
                    "regulado casi monotono creciente, asi que funciona como "
                    "tendencia temporal y no como seniale de costo. "
                    "Excluir; el iGas-D sigue siendo la ruta correcta.")
        else:
            veredicto = "no concluyente"
            nota = ("Sin evidencia suficiente en este periodo.")
        print(f"\n  1) COMBUSTIBLE (precio de escasez solo): {veredicto}")
        print(f"     DM {r['DM']:+.3f}, p crudo {r['p_DM']:.4f}, "
              f"p FDR {r['p_FDR']:.4f}")
        print(f"     {nota}")

    if {"AR+HIDRO", "AR+OFERTA", "AR+HIDRO+OFERTA"} <= set(res.index):
        m_h = resultados["AR+HIDRO"]["MAPE_niv"]
        m_o = resultados["AR+OFERTA"]["MAPE_niv"]
        m_b = resultados["AR"]["MAPE_niv"]
        m_ho = resultados["AR+HIDRO+OFERTA"]["MAPE_niv"]
        aporte_sep = (m_b - m_h) + (m_b - m_o)
        aporte_jun = m_b - m_ho
        solape = aporte_sep - aporte_jun
        print(f"\n  2) ADITIVIDAD de HIDRO y OFERTA")
        print(f"     Aporte por separado (sumado): {aporte_sep:+.3f} pp")
        print(f"     Aporte juntos:                {aporte_jun:+.3f} pp")
        if aporte_sep > 0:
            frac = solape / aporte_sep
            print(f"     Solape: {solape:+.3f} pp ({frac:.0%} del aporte "
                  f"separado)")
            if frac > 0.40:
                print(f"     Solape ALTO: los bloques capturan seniales "
                      f"parecidas; considera simplificar.")
            elif frac < 0.25:
                print(f"     Solape BAJO: los aportes son mayormente "
                      f"ADITIVOS -- capturan determinantes distintos.")
            else:
                print(f"     Solape moderado.")

    # ---- modelo final para los notebooks -----------------------------------
    ganador, criterio = elegir_modelo_final(
        res, EVAL3["fdr_alpha"], base=base, forzado=EVAL3["modelo_forzado"])
    info = {
        "generado": pd.Timestamp.now().isoformat(timespec="seconds"),
        "modelo": ganador,
        "criterio": criterio,
        "selection_cutoff": cfg["selection_cutoff"],
        "ventana_validacion": [str(eval_idx.min().date()),
                               str(eval_idx.max().date())],
        "test_start": cfg["test_start"],
        "test_end": cfg["test_end"],
        "bloques": {b: bloques_ok[b] for b in MODELOS[ganador]
                    if b in bloques_ok},
        "features": columnas[ganador],
        "metricas_validacion": {
            k: _num(res.loc[ganador, k])
            for k in ["n", "MAPE_niv", "RMSE_log", "DA_pct", "DM", "p_DM",
                      "p_FDR", "DM_ingenuo", "p_ingenuo"]
        },
    }
    ruta_json = out / "modelo_final.json"
    ruta_json.write_text(json.dumps(info, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(f"\n  3) MODELO FINAL para los notebooks 04/05: {ganador}")
    print(f"     criterio: {criterio}")
    print(f"     {len(info['features'])} features: {info['features']}")

    print(f"\n[salida]  {out / 'bloques_candidatos.csv'}")
    print(f"          {ruta_json}")
    print("\nRecuerda: 'no concluyente' NO prueba que el bloque sea inutil.")
    print("Un bloque con justificacion teorica documentada puede incluirse")
    print("igual (EVAL3['modelo_forzado']), declarando que no alcanzo")
    print("significancia individual.")


if __name__ == "__main__":
    main()
