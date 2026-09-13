"""
================================================================================
ETAPA 1 — SELECCION DE VARIABLES  (Tesis: pronostico del precio de bolsa)
================================================================================

Filosofia del script
--------------------
El pipeline usa TRES periodos que no se traslapan (ver CONFIG):

  seleccion   2015-2019  -> esta etapa (tamizaje de variables)
  validacion  2020-2022  -> etapas 02 y 03 (eleccion de bloques con DM)
  prueba      2023-2025  -> SOLO la medicion final de los notebooks 04/05

Toda la seleccion se hace SOLO con datos hasta selection_cutoff. Si la
seleccion viera 2020-2022, la comparacion de bloques de las etapas 02/03
estaria sesgada a favor de lo seleccionado; si 02/03 vieran 2023-2025, las
metricas finales quedarian optimistas.

Produce cuatro senales por variable, con criterios distintos, y las combina
en un conteo de "votos". Ninguna senal sola descarta una variable:

  1. Higiene        -> NaN, varianza casi nula, duplicados
  2. Estacionariedad -> ADF (necesario para SARIMAX y para Granger)
  3. Lineal          -> Granger (con correccion FDR de Benjamini-Hochberg)
  4. No lineal       -> Informacion mutua rezagada
  5. Embedded        -> Lasso + importancia por permutacion en Random Forest

Salida: tabla ordenada en CSV + resumen en consola.

Uso
---
  1. Edita el bloque CONFIG.
  2. python 01_seleccion_variables.py
================================================================================
"""

import contextlib
import io
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

warnings.filterwarnings("ignore")

# Carpeta donde vive ESTE archivo -- las salidas se guardan siempre ahi,
# sin importar desde que carpeta se invoque el script. Si "out_dir" fuera
# una ruta relativa ("./salidas_seleccion"), dependeria del directorio de
# trabajo de la terminal (cwd), que en VS Code no siempre coincide con la
# carpeta del proyecto -- ese desajuste es justo lo que causaba el
# FileNotFoundError al correr 02_evaluacion_bloques.py desde otra carpeta.
BASE_DIR = Path(__file__).resolve().parent

# ==============================================================================
# CONFIG  <-- EDITA ESTO
# ==============================================================================

CONFIG = {
    # Ruta al panel diario ya construido (csv o parquet)
    "panel_path": r"C:\Users\andre\OneDrive\cosas de la universidad\Uniandes\VIII\Tesis\data\panel_d.parquet",
    "date_col": "fecha",
    "target_col": "precio_ponderado",

    # El target se modela en log. Si ya viene en log, pon False.
    "log_target": True,

    # PERIODOS DEL PIPELINE (compartidos por 02, 03, 06 y los notebooks).
    # CORTE DE SELECCION. Nada despues de esta fecha entra a este script.
    "selection_cutoff": "2019-12-31",
    # Validacion: aqui se eligen los bloques (etapas 02 y 03)
    "validation_start": "2020-01-01",
    "validation_end":   "2022-12-31",
    # Prueba: intacta hasta la medicion final (notebooks 04 y 05)
    "test_start":       "2023-01-01",
    "test_end":         "2025-12-31",

    # Rezagos a construir para cada feature exogena.
    # El rezago minimo debe ser >= 1 para cualquier variable de estado o ex-post.
    "lags": [1, 2, 3, 7, 14, 30],

    # Ventanas para medias/volatilidades moviles (siempre con shift(1) antes)
    "rolling_windows": [7, 30],

    # Variables ex-ante puras: pueden entrar con lag 0 (se conocen antes de D)
    "ex_ante_cols": [
        "precio_escasez", "precio_marg_escasez", "precio_escasez_empalmado",
        # disp_comercial SALIO de esta lista: XM la describe como la
        # declaracion "modificada cuando se presentan cambios en las unidades
        # de generacion en operacion real", es decir, se ajusta DESPUES del
        # despacho. Su lag0 correlaciona con el cambio de precio del mismo dia
        # (-0.23) pero casi nada con el del dia siguiente (-0.02). Se usa la
        # disponibilidad DECLARADA, que va en la oferta del dia anterior.
        # Volver a agregarla solo si XM confirma que se publica antes del
        # despacho.
        "disp_declarada", "enficc", "precio_cargo_conf",
        "cee", "cere", "mc",
        # margen_reserva SI puede llevar lag0 porque el rezago del
        # denominador (demanda) ya quedo incorporado en construir_derivadas()
        # del consolidador -- es capacidad_efectiva(t) / demanda(t-1), no
        # capacidad(t) / demanda(t). Sin ese rezago interno, lag0 aqui seria
        # fuga (la demanda es "Demanda Real", medida, no pronosticada -- ver
        # DemaRealReg/DemaRealNoReg en catalogo_metricas). Si alguna vez se
        # reconstruye margen_reserva sin el shift(1) del denominador, esta
        # entrada DEBE salir de ex_ante_cols.
        "margen_reserva",
        "gen_programada_total", "frac_fncer_programada",
        # Las dummies regulatorias se conocen de antemano por definicion:
        # la resolucion se publica antes de entrar en vigencia.
        "dummy_creg_escasez",
    ],

    # Umbral de correlacion para agrupar features redundantes
    "corr_threshold": 0.90,

    # Rezagos maximos para la prueba de Granger
    "granger_maxlag": 7,

    # Nivel de FDR
    "fdr_alpha": 0.10,

    # Bloques tematicos: PREFIJO de columna -> nombre del bloque.
    # El match es por PREFIJO REAL (startswith), no por subcadena: con
    # subcadena, "es_" capturaba exportacion(es_)lag30, restriccion(es_)...,
    # importacion(es_)d7 -- plurales en espaniol -- y los metia en CALENDARIO.
    "blocks": {
        "AR":          ["log_precio", "precio_pond"],
        "HIDRO":       ["volumen_util", "aportes", "anomalia_hidro", "oni",
                        "hhi_embalse", "vertimientos", "capacidad_por_embalse",
                        "volumen_por_embalse"],
        "OFERTA":      ["disp_", "gen_programada", "frac_fncer",
                        "margen_reserva", "capacidad_efectiva"],

        # EX-POST va ANTES que DEMANDA a proposito: la asignacion se resuelve
        # en orden, y "demanda_" (DEMANDA) engloba a "demanda_no_atendida"
        # (EXPOST). Si DEMANDA fuera primero, la demanda no atendida -- que es
        # ex-post -- quedaria clasificada como demanda normal y se trataria
        # como inocua. Se conocen DESPUES de que el precio se formo; entran
        # solo rezagadas y aun asi con cuidado, por eso son bloque aparte:
        # asi la etapa 2 mide su aporte por separado con DM.
        "EXPOST":      ["restricciones", "importaciones", "exportaciones",
                        "perdidas_energia", "gen_fuera_merito",
                        "gen_por_recurso", "gen_seguridad",
                        "consumo_combustible", "emisiones_co2",
                        "demanda_no_atendida", "dem_no_atendida"],

        "DEMANDA":     ["demanda_"],
        "REGULATORIO": ["precio_escasez", "precio_marg_escasez", "enficc",
                        "precio_cargo_conf", "cee", "cere", "mc",
                        "dummy_creg"],
        "CONTRATOS":   ["precio_prom_contrato", "precio_cont_no_regu",
                        "compras_contrato"],
        "COSTO":       ["trm", "igas", "precio_gas", "henry_hub"],
        "CALENDARIO":  ["es_", "dow_", "doy_"],

        # DESPACHO: casi-identidad con el precio de bolsa.
        # Se separa a proposito para poder excluirlo (ver excluir_despacho).
        "DESPACHO":    ["costo_marginal_prog", "precio_oferta_desp",
                        "max_precio_oferta", "recurso_marginal"],
    },

    # El precio de bolsa ES el costo marginal del despacho ideal. Meter
    # costo_marginal_prog como feature da un MAPE espectacular sin decir nada:
    # el SHAP se lo lleva todo y los bloques hidrologico y FNCER -- que son el
    # aporte de la tesis -- quedan invisibles.
    #   True  -> se excluye del panel de seleccion (recomendado)
    #   False -> entra, para usarlo como BENCHMARK SUPERIOR ("techo" de
    #            precision alcanzable con informacion de despacho)
    "excluir_despacho": True,

    "out_dir": str(BASE_DIR / "salidas_seleccion"),
}


# ==============================================================================
# 0. CARGA
# ==============================================================================

def cargar_panel(cfg):
    p = Path(cfg["panel_path"])
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p)

    date_col = cfg["date_col"]

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    elif df.index.name == date_col:
        # 00_consolidar_panel.py guarda la fecha como INDICE, no como
        # columna (index.name == "fecha"). pd.read_parquet preserva ese
        # indice tal cual, asi que no hay nada que mover -- solo asegurar
        # que sea datetime.
        df.index = pd.to_datetime(df.index)
    else:
        raise KeyError(
            f"No encuentro '{date_col}' ni como columna ni como indice del "
            f"panel. Columnas disponibles: {list(df.columns)[:10]}... "
            f"Indice actual: '{df.index.name}'."
        )

    df = df.sort_index()
    df = df.asfreq("D")  # expone huecos de calendario como NaN explicitos
    return df


# ==============================================================================
# 1. CONSTRUCCION DE FEATURES (leakage-safe)
# ==============================================================================

def construir_features(df, cfg):
    """
    Regla de oro: toda estadistica movil se calcula con shift(1) ANTES del
    rolling. Nunca centrada. Asi el valor en t solo usa informacion <= t-1.
    """
    y_raw = df[cfg["target_col"]]
    y = np.log(y_raw.clip(lower=1e-6)) if cfg["log_target"] else y_raw
    y.name = "y"

    exog = df.drop(columns=[cfg["target_col"]])
    feats = {}

    # --- Bloque autorregresivo del target -----------------------------------
    for L in cfg["lags"]:
        feats[f"log_precio_lag{L}"] = y.shift(L)
    for w in cfg["rolling_windows"]:
        feats[f"log_precio_ma{w}"] = y.shift(1).rolling(w, min_periods=w // 2).mean()
        feats[f"log_precio_sd{w}"] = y.shift(1).rolling(w, min_periods=w // 2).std()

    # --- Features exogenas ---------------------------------------------------
    for col in exog.columns:
        s = pd.to_numeric(exog[col], errors="coerce")

        # lag 0 solo para ex-ante puras
        if col in cfg["ex_ante_cols"]:
            feats[f"{col}_lag0"] = s

        for L in cfg["lags"]:
            feats[f"{col}_lag{L}"] = s.shift(L)

        # tasa de cambio a 7d: captura si el sistema se seca o se recupera
        feats[f"{col}_d7"] = s.shift(1) - s.shift(8)

    X = pd.DataFrame(feats, index=df.index)
    return X, y


# ==============================================================================
# 2. HIGIENE
# ==============================================================================

def higiene(X, max_nan_frac=0.30, min_std=1e-8):
    rep = []
    drop = []

    nan_frac = X.isna().mean()
    for c in X.columns:
        if nan_frac[c] > max_nan_frac:
            drop.append(c); rep.append((c, f"NaN {nan_frac[c]:.0%}"))

    keep = [c for c in X.columns if c not in drop]
    stds = X[keep].std()
    for c in keep:
        if not np.isfinite(stds[c]) or stds[c] < min_std:
            drop.append(c); rep.append((c, "varianza ~0"))

    keep = [c for c in X.columns if c not in drop]
    # duplicados exactos
    vistos = {}
    for c in keep:
        h = pd.util.hash_pandas_object(X[c].fillna(-9e9)).sum()
        if h in vistos:
            drop.append(c); rep.append((c, f"duplicado de {vistos[h]}"))
        else:
            vistos[h] = c

    keep = [c for c in X.columns if c not in drop]
    print(f"[higiene] {len(X.columns)} -> {len(keep)} features "
          f"({len(drop)} descartadas)")
    for c, r in rep[:15]:
        print(f"           - {c}: {r}")
    if len(rep) > 15:
        print(f"           ... y {len(rep)-15} mas")
    return X[keep]


# ==============================================================================
# 3. ESTACIONARIEDAD (ADF)
# ==============================================================================

def test_adf(X, alpha=0.05):
    """
    Necesario para dos cosas: (a) los regresores exogenos del SARIMAX deben
    ser razonablemente estacionarios, (b) Granger sobre series con tendencia
    produce regresion espuria.
    """
    out = {}
    for c in X.columns:
        s = X[c].dropna()
        if len(s) < 50:
            out[c] = (np.nan, False); continue
        try:
            p = adfuller(s, autolag="AIC")[1]
            out[c] = (p, p < alpha)
        except Exception:
            out[c] = (np.nan, False)
    res = pd.DataFrame(out, index=["adf_pvalue", "estacionaria"]).T
    n_est = int(res["estacionaria"].sum())
    print(f"[ADF]     {n_est}/{len(res)} features estacionarias al {alpha:.0%}")
    return res


def estacionarizar(X, adf_res):
    """Diferencia las no estacionarias (solo para las pruebas lineales)."""
    Xs = X.copy()
    for c in X.columns:
        if not adf_res.loc[c, "estacionaria"]:
            Xs[c] = X[c].diff()
    return Xs


# ==============================================================================
# 4. AGRUPAMIENTO POR CORRELACION
# ==============================================================================

def agrupar_correlacionadas(X, threshold=0.90):
    """
    Los lags del precio, las reservas y los aportes van a estar altisimamente
    correlacionados. Eso no rompe los arboles, pero SI distorsiona SHAP: el
    credito se reparte arbitrariamente entre features redundantes.

    Agrupa con clustering jerarquico sobre distancia = 1 - |rho_Spearman|.
    """
    Xc = X.dropna()
    if Xc.shape[0] < 100:
        Xc = X.fillna(X.median())

    rho = Xc.corr(method="spearman").fillna(0).values
    dist = 1.0 - np.abs(rho)
    np.fill_diagonal(dist, 0.0)
    dist = (dist + dist.T) / 2

    Z = linkage(squareform(dist, checks=False), method="average")
    labels = fcluster(Z, t=1.0 - threshold, criterion="distance")

    grupos = pd.Series(labels, index=X.columns, name="grupo_corr")
    n_g = grupos.nunique()
    print(f"[corr]    {len(X.columns)} features -> {n_g} grupos "
          f"(|rho| > {threshold})")
    return grupos


# ==============================================================================
# 5. INFORMACION MUTUA (senal NO lineal)
# ==============================================================================

def info_mutua(X, y, random_state=42, min_obs=200):
    """
    Captura dependencia no lineal. Critico en este caso: la relacion
    reservas-precio es convexa, asi que la correlacion de Pearson SUBESTIMA
    la utilidad del bloque hidrologico. La MI no.

    Se calcula POR PARES (cada feature contra el target, con su propio
    dropna) en vez de con un dropna conjunto sobre las 300+ features.
    Con dropna conjunto basta que unas pocas series tengan huecos dispersos
    para exigir que TODAS tengan dato el mismo dia, y la muestra colapsa
    (se llego a perder >80% de las observaciones). Por pares, cada feature
    se evalua con toda la informacion que realmente tiene.
    """
    res = {}
    n_obs = {}
    for c in X.columns:
        d = pd.concat([X[c], y], axis=1).dropna()
        if len(d) < min_obs:
            res[c] = np.nan
            n_obs[c] = len(d)
            continue
        mi = mutual_info_regression(d[[c]].values, d["y"].values,
                                    random_state=random_state)
        res[c] = float(mi[0])
        n_obs[c] = len(d)

    s = pd.Series(res, name="mi")
    obs = pd.Series(n_obs, name="mi_n_obs")

    validas = s.notna().sum()
    print(f"[MI]      {validas}/{len(s)} features evaluadas "
          f"(pairwise, mediana {int(obs.median())} obs c/u)")
    print(f"          Top 5: {list(s.dropna().sort_values(ascending=False).head(5).index)}")
    if (obs < min_obs).any():
        pocas = int((obs < min_obs).sum())
        print(f"          [!] {pocas} features con < {min_obs} obs, sin MI")

    return pd.concat([s, obs], axis=1)


# ==============================================================================
# 6. GRANGER + CORRECCION FDR (senal LINEAL)
# ==============================================================================

def granger_fdr(Xs, y_s, maxlag=7, alpha=0.10):
    """
    Prueba si los rezagos de X reducen el error de prediccion de y MAS ALLA
    de lo que ya logran los rezagos de y. Es la prueba canonica y citable.

    LIMITE: es una prueba LINEAL. No rechazar NO significa que la variable sea
    inutil -> nunca descartes solo por Granger.

    FDR (Benjamini-Hochberg) en vez de Bonferroni: con ~200 features altamente
    correlacionadas, Bonferroni es demasiado conservadora.
    """
    pvals, cols = [], []
    _sink = io.StringIO()  # versiones viejas imprimen cada prueba
    for c in Xs.columns:
        d = pd.concat([y_s, Xs[c]], axis=1).dropna()
        if len(d) < maxlag * 10:
            continue
        try:
            arr = d[["y", c]].values
            # statsmodels >= 0.15 elimino el kwarg 'verbose'
            with contextlib.redirect_stdout(_sink):
                try:
                    r = grangercausalitytests(arr, maxlag=maxlag)
                except TypeError:
                    r = grangercausalitytests(arr, maxlag=maxlag,
                                              verbose=False)
            p = min(r[L][0]["ssr_ftest"][1] for L in range(1, maxlag + 1))
            if np.isfinite(p):
                pvals.append(p); cols.append(c)
        except Exception:
            continue

    if not pvals:
        return pd.DataFrame(columns=["granger_p", "granger_p_fdr",
                                     "granger_signif"])

    rej, p_adj, _, _ = multipletests(pvals, alpha=alpha, method="fdr_bh")
    res = pd.DataFrame({"granger_p": pvals, "granger_p_fdr": p_adj,
                        "granger_signif": rej}, index=cols)
    frac = rej.mean()
    print(f"[Granger] {int(rej.sum())}/{len(cols)} significativas "
          f"tras FDR al {alpha:.0%}  ({frac:.0%})")
    if frac > 0.50:
        print(f"          [!] Tasa de rechazo muy alta. Con series casi-raiz-")
        print(f"              unitaria y features altamente correlacionadas,")
        print(f"              Granger sobre-rechaza. NO lo tomes como prueba")
        print(f"              de utilidad: el arbitro es la etapa 2 (DM).")
    return res


# ==============================================================================
# 7. METODOS EMBEDDED (Lasso + permutacion en RF)
# ==============================================================================

def embedded(X, y, random_state=42, min_cobertura=0.80):
    """
    Lasso + importancia por permutacion. A diferencia de la MI, estos SI
    necesitan casos completos (evaluan las features en conjunto).

    Para no colapsar la muestra: se descartan primero las features con
    cobertura baja dentro de la ventana, y los NaN dispersos que quedan se
    imputan con la mediana. La imputacion se calcula SOLO con datos de la
    ventana de seleccion (todo lo que entra aqui es pre-cutoff), asi que no
    introduce fuga del periodo de prueba.
    """
    cobertura = X.notna().mean()
    cols_ok = cobertura[cobertura >= min_cobertura].index.tolist()
    n_drop = len(X.columns) - len(cols_ok)

    if len(cols_ok) < 2:
        print("[embed]   muy pocas features con cobertura suficiente, se omite")
        return pd.DataFrame(index=X.columns)

    Xe = X[cols_ok]
    d = pd.concat([Xe, y], axis=1).dropna(subset=["y"])
    if len(d) < 200:
        print("[embed]   muy pocas obs, se omite")
        return pd.DataFrame(index=X.columns)

    Xd_raw = d[cols_ok]
    medianas = Xd_raw.median()
    Xd = Xd_raw.fillna(medianas).values
    yd = d["y"].values

    n_imputados = int(Xd_raw.isna().sum().sum())
    print(f"[embed]   {len(cols_ok)} features (descartadas {n_drop} con "
          f"cobertura < {min_cobertura:.0%}), {len(d)} obs, "
          f"{n_imputados} celdas imputadas con mediana")

    tscv = TimeSeriesSplit(n_splits=5)

    # --- Lasso (esparsidad L1, especifico a modelos lineales) ---------------
    sc = StandardScaler().fit(Xd)
    # scikit-learn >= 1.8 renombro 'n_alphas' a 'alphas' (que acepta un int
    # con la cantidad de alphas a probar, o un array explicito).
    try:
        lasso = LassoCV(cv=tscv, random_state=random_state, alphas=50,
                        max_iter=5000).fit(sc.transform(Xd), yd)
    except TypeError:
        lasso = LassoCV(cv=tscv, random_state=random_state, n_alphas=50,
                        max_iter=5000).fit(sc.transform(Xd), yd)
    coef = pd.Series(np.abs(lasso.coef_), index=cols_ok, name="lasso_abs")
    n_nz = int((coef > 0).sum())

    # --- Importancia por PERMUTACION en RF ----------------------------------
    # NO se usa feature_importances_ (impureza Gini): esta sesgada hacia
    # variables continuas de alta cardinalidad.
    n_tr = int(len(d) * 0.8)
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                               n_jobs=-1, random_state=random_state)
    rf.fit(Xd[:n_tr], yd[:n_tr])
    pi = permutation_importance(rf, Xd[n_tr:], yd[n_tr:], n_repeats=10,
                               random_state=random_state, n_jobs=-1)
    perm = pd.Series(pi.importances_mean, index=cols_ok, name="perm_imp")

    print(f"          Lasso conservo {n_nz}/{len(cols_ok)} features; "
          f"RF permutacion OK")
    return pd.concat([coef, perm], axis=1).reindex(X.columns)


# ==============================================================================
# 8. AGREGACION Y RANKING
# ==============================================================================

def asignar_bloque(col, blocks):
    """
    Match por PREFIJO REAL (startswith), no por subcadena.

    Con subcadena, "es_" capturaba exportacion(es_)lag30 y restriccion(es_)...
    -- cualquier plural espaniol -- y los clasificaba como CALENDARIO. Ademas
    de ser una etiqueta incorrecta, eso metia variables EX-POST en un bloque
    que se trata como inocuo, saltandose el control de fuga.
    """
    for bloque, prefijos in blocks.items():
        if any(col.startswith(p) for p in prefijos):
            return bloque
    return "OTRO"


def consolidar(X, adf_res, grupos, mi, granger_res, emb, cfg):
    t = pd.DataFrame(index=X.columns)
    t["bloque"] = [asignar_bloque(c, cfg["blocks"]) for c in X.columns]
    t["grupo_corr"] = grupos
    t = t.join(adf_res).join(mi).join(granger_res).join(emb)

    # rankings normalizados (1 = mejor)
    for col, new in [("mi", "r_mi"), ("lasso_abs", "r_lasso"),
                     ("perm_imp", "r_perm")]:
        if col in t.columns:
            t[new] = t[col].rank(pct=True, ascending=True)

    # votos: cada senal aporta uno
    t["voto_granger"] = t.get("granger_signif", False).fillna(False).astype(int)
    t["voto_mi"] = (t.get("r_mi", 0) > 0.70).astype(int)
    t["voto_lasso"] = (t.get("lasso_abs", 0) > 0).astype(int)
    t["voto_perm"] = (t.get("r_perm", 0) > 0.70).astype(int)
    t["votos"] = t[["voto_granger", "voto_mi", "voto_lasso",
                    "voto_perm"]].sum(axis=1)

    # score continuo para desempatar dentro de cada grupo de correlacion
    t["score"] = t[["r_mi", "r_lasso", "r_perm"]].mean(axis=1).fillna(0)

    t = t.sort_values(["votos", "score"], ascending=False)
    return t


def elegir_representantes(tabla, max_por_bloque=8, min_votos=2,
                          excluir_bloques=("OTRO",)):
    """
    Tres filtros, en este orden:

      1. min_votos: al menos 2 de 4 senales independientes. SIN este filtro
         la cuota por bloque se llena con lo que haya, incluido ruido puro:
         una variable aleatoria puede sacar 1/4 votos por azar (el Lasso le
         deja un coeficiente diminuto, o cae en el decil alto de MI por
         ruido de estimacion). Exigir 2 senales distintas mata casi todo eso.

      2. Un representante por grupo de correlacion (el de mayor score), para
         que los 6 lags de la misma variable sean UNA decision y no seis.

      3. Tope por bloque tematico, para no desbalancear el modelo hacia el
         bloque que mas columnas tenga.

    'OTRO' se excluye por defecto: si una variable no encaja en ningun bloque
    tematico, o falta un prefijo en CONFIG['blocks'], o no deberia estar ahi.
    """
    t = tabla[~tabla["bloque"].isin(excluir_bloques)]
    t = t[t["votos"] >= min_votos]

    reps = (t.sort_values("score", ascending=False)
             .groupby("grupo_corr", sort=False).head(1))
    sel = (reps.sort_values(["votos", "score"], ascending=False)
                .groupby("bloque", sort=False).head(max_por_bloque))

    n_out = len(tabla) - len(t)
    print(f"[filtro]  {n_out} descartadas por < {min_votos} votos o "
          f"bloque excluido")
    return sel


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    cfg = CONFIG
    out = Path(cfg["out_dir"]); out.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("ETAPA 1 — SELECCION DE VARIABLES")
    print("=" * 72)

    df = cargar_panel(cfg)
    print(f"[carga]   panel {df.shape[0]} filas x {df.shape[1]} cols, "
          f"{df.index.min().date()} -> {df.index.max().date()}")

    X_all, y_all = construir_features(df, cfg)
    print(f"[feats]   {X_all.shape[1]} features construidas")

    # ---- exclusion del bloque de DESPACHO ----------------------------------
    if cfg.get("excluir_despacho", True):
        pref_desp = cfg["blocks"].get("DESPACHO", [])
        cols_desp = [c for c in X_all.columns
                     if any(c.startswith(p) for p in pref_desp)]
        if cols_desp:
            X_all = X_all.drop(columns=cols_desp)
            print(f"[fuga]    {len(cols_desp)} features de DESPACHO excluidas "
                  f"(costo_marginal_prog, precio_oferta_desp, ...)")
            print(f"          El precio de bolsa ES el costo marginal del "
                  f"despacho: incluirlas da MAPE bajo sin aporte cientifico.")
            print(f"          Pon excluir_despacho=False para usarlas como "
                  f"benchmark superior.")

    # ---- EL CORTE. Nada de aqui en adelante ve el periodo de prueba. -------
    cut = pd.Timestamp(cfg["selection_cutoff"])
    X, y = X_all.loc[:cut], y_all.loc[:cut]
    print(f"[corte]   seleccion usa SOLO hasta {cut.date()} "
          f"({len(X)} obs). Validacion {cfg['validation_start']} -> "
          f"{cfg['validation_end']} y prueba {cfg['test_start']} -> "
          f"{cfg['test_end']} intactas.")
    print("-" * 72)

    X = higiene(X)
    adf_res = test_adf(X)
    Xs = estacionarizar(X, adf_res)
    y_s = y.diff().rename("y")   # el log-precio necesita d=1

    grupos = agrupar_correlacionadas(X, cfg["corr_threshold"])
    mi = info_mutua(X, y)
    granger_res = granger_fdr(Xs, y_s, cfg["granger_maxlag"], cfg["fdr_alpha"])
    emb = embedded(X, y)

    print("-" * 72)
    tabla = consolidar(X, adf_res, grupos, mi, granger_res, emb, cfg)

    # Diagnostico: si algo cae en OTRO es que falta un prefijo en
    # CONFIG["blocks"] -- vale revisarlo, porque OTRO se excluye por defecto
    # y una variable util podria estar quedandose fuera en silencio.
    sin_bloque = tabla[tabla["bloque"] == "OTRO"]
    if len(sin_bloque):
        ejemplos = list(sin_bloque.index[:8])
        print(f"[bloques] [!] {len(sin_bloque)} features sin bloque asignado "
              f"(van a 'OTRO' y se excluyen):")
        print(f"              {ejemplos}")
        print(f"              Si alguna deberia entrar, agrega su prefijo a "
              f"CONFIG['blocks'].")

    sel = elegir_representantes(tabla)

    tabla.to_csv(out / "ranking_completo.csv")
    sel.to_csv(out / "features_seleccionadas.csv")

    print(f"\n[salida]  {len(tabla)} evaluadas -> {len(sel)} seleccionadas")
    print(f"          {out/'ranking_completo.csv'}")
    print(f"          {out/'features_seleccionadas.csv'}")

    print("\nSeleccionadas por bloque:")
    for b, g in sel.groupby("bloque"):
        print(f"\n  {b}  ({len(g)})")
        for c, r in g.iterrows():
            print(f"    {r['votos']}/4 votos  score={r['score']:.2f}  {c}")

    print("\n" + "=" * 72)
    print("SIGUIENTE: 02_evaluacion_bloques.py")
    print("Granger y MI son tamizaje. El arbitro real es si el BLOQUE reduce")
    print("el error en walk-forward (Diebold-Mariano). Eso es la etapa 2.")
    print("=" * 72)


if __name__ == "__main__":
    main()
