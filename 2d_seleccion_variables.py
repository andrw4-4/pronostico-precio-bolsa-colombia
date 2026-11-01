"""
Paso 2d: la selección de variables. El panel horario para modelar, con las
columnas del paso 2c que elige, para cada horizonte, un embudo de tres etapas.

    python 2d_seleccion_variables.py

Toma las variables base del paso 2c (paneles/panel_caracteristicas.csv.gz) y
arma con features.armar_todas() sus 1.861 columnas derivadas. De ahí elige.

Salidas, en paneles/:
    panel_horario_modelo.csv.gz            la tabla para modelar: identificación,
                                           calendario, objetivos y toda columna
                                           que entra en algún horizonte
    panel_horario_modelo_columnas.csv      cada columna: qué le pasó en la
                                           limpieza y, por horizonte, su
                                           importancia, su orden, si entra y si
                                           está en la lista corta
    panel_horario_modelo_validacion.csv    el error en 2020-2022 con las
                                           primeras k columnas del orden
    panel_horario_modelo_variables.csv     la importancia sumada por variable,
                                           para la tesis

Selección congelada el 1 de noviembre de 2026. Varias reglas de este paso se
decidieron mirando 2020-2022 (la lista está en docs/PANEL_HORARIO.md), así que
no se les cambia nada más. La prueba se usa una sola vez, con el modelo final.

La versión anterior, que elegía con pruebas lineales (Granger y Wald con
errores de Driscoll-Kraay), está en legacy/seleccion_lineal/ junto con sus
salidas: con ellas se corrieron los experimentos de legacy/experimentos_xgboost/.

Ventanas
--------
Las columnas se eligen solo con la ventana de selección (marzo de 2015 a
diciembre de 2019) y cuántas entran, con la de validación (2020-2022). La
prueba (2023-2026) no se usa como columna: matriz() se niega a leer esas filas.
La respuesta sí alcanza a cruzar: los objetivos de los últimos h días de 2022
caen en enero de 2023 (0,6% de las filas de validación en h = 7, 2,7% en
h = 30). Quedó así porque la selección está congelada. Entre
entrenamiento y evaluación se dejan h+1 días, para que ningún objetivo del
entrenamiento caiga en el periodo evaluado.

Siempre entran, sin pasar por el embudo, lp (el precio del día t, que es la
base del objetivo) y el calendario: el del día t, tal cual y en seno y coseno,
y el del día que se pronostica.

El embudo
---------
1. Limpieza.
   a. Salen las columnas constantes o casi constantes (un mismo valor en 99%
      de las horas o más). No mira el objetivo y es igual para todos los
      horizontes.
   b. Salen las inestables: las que tienen más de 25% de sus valores de
      2018-2019 fuera del rango de 2015-2017 (percentiles 1 a 99). Son niveles
      que se corren con el tiempo (precios en pesos que suben con la inflación,
      la participación solar, el número de plantas), y un árbol no extrapola:
      todo lo que pasa del máximo que vio cae en la misma hoja. El corrimiento
      dentro de 2015-2019 anticipa el de 2020-2022. Tampoco mira el objetivo.
   c. Salen los niveles que siguen al dólar. El cargo por confiabilidad se fija
      en dólares (CREG 071 de 2006, art. 29) y en pesos se mueve con la TRM.
      De esas dos variables quedan solo las columnas de cambio: delta_7d,
      ma7_menos_ma30 y variabilidad.
   d. Salen las redundantes. De cada grupo de columnas con correlación de
      Spearman mayor a 0,95 entre sí queda la que más se correlaciona (en valor
      absoluto) con el objetivo del horizonte. Para eso se recorren las
      columnas de mayor a menor correlación con el objetivo, y una se queda
      solo si su correlación con todas las que ya quedaron es de 0,95 o menos.
      lp va primero y siempre se queda.

2. Orden, con XGBoost y columnas de ruido. Hay dos cortes: entrenar con
   2015-2017 y medir en 2018, y entrenar con 2015-2018 y medir en 2019. En
   cada uno se entrena XGBoost con lo que pasó la limpieza más 10 columnas de
   ruido (copias de columnas al azar con los días barajados, que no dicen nada
   del objetivo). Luego se calcula el valor SHAP de cada columna en el año que
   el modelo no vio. La importancia es el promedio de |SHAP|. Una columna sigue
   si su importancia le gana a la del mejor ruido en los dos cortes, y se
   ordena por el promedio de los dos. SHAP en el año no visto mide cuánto usa
   el modelo la columna con datos nuevos, no si baja el error: eso lo decide la
   etapa 3.

3. Cuántas, con la validación. Con las primeras k columnas del orden (k = 10,
   20, 40, 80, 160 y todas las que pasaron) se entrena con 2015-2019 y se mide
   en 2020-2022. El error es el promedio por día del error cuadrático en log, y
   su error estándar sale de Newey-West con h - 1 + 7 rezagos, porque los días
   seguidos se parecen y los objetivos se traslapan. Se queda el k más chico
   cuyo error no pasa el del mejor más un error estándar (regla de un error
   estándar). También se mide k = 0 (solo lp y calendario), como referencia.

La lista corta (corta_h) son las primeras 20 del orden, o las k elegidas si
son menos. Es para SARIMAX o una LSTM, que sufren con muchas columnas.

XGBoost aquí solo sirve para ordenar columnas: va con una configuración fija y
no se ajusta. Los modelos de pronóstico van aparte.

Fuentes (ver docs/REFERENCIAS.md):
    - constantes y correlación: Complete-Feature-Selection, cuadernos 1 y 2;
    - importancia con árboles: SLDA, clase 15; XGBoost: ML Zoomcamp, módulo 6;
    - SHAP: Lundberg y Lee (2017) y, para árboles, Lundberg et al. (2020);
    - columnas de ruido como umbral: Boruta (Kursa y Rudnicki, 2010);
    - regla de un error estándar: SLDA, clases 7 y 8; Hastie et al. (2009), 7.10;
    - error estándar: Newey y West (1987); purga de h+1 días: López de Prado (2018).
"""

import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

import features as fe

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "paneles" / "panel_horario_modelo.csv.gz"
COLUMNAS = BASE / "paneles" / "panel_horario_modelo_columnas.csv"
VALIDACION = BASE / "paneles" / "panel_horario_modelo_validacion.csv"
VARIABLES = BASE / "paneles" / "panel_horario_modelo_variables.csv"

# de 1 a 7 días, dos semanas y un mes
HORIZONTES = [1, 2, 3, 4, 5, 6, 7, 14, 30]
FIN_SELECCION = pd.Timestamp("2019-12-31")
INICIO_VALIDACION = pd.Timestamp("2020-01-01")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
# etapa 2: el año que se mide; se entrena con todo lo anterior
CORTES = [(pd.Timestamp("2018-01-01"), pd.Timestamp("2018-12-31")),
          (pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31"))]

CASI_CONSTANTE = 0.99
# estabilidad: 2018-2019 contra el rango de 2015-2017
FIN_REFERENCIA = pd.Timestamp("2017-12-31")
MAX_FUERA_DE_RANGO = 0.25
# su nivel en pesos sigue al dólar: solo entran como cambio
SOLO_CAMBIO = tuple(f"{v}_" for v in ("precio_cargo_conf", "trm"))
SUFIJOS_DE_CAMBIO = ("_delta_7d", "_ma7_menos_ma30", "_sd7d", "_sd30d")
MAX_CORRELACION = 0.95
N_RUIDO = 10
TAMANOS = [10, 20, 40, 80, 160]
N_CORTA = 20

CALENDARIO_DIA = ["hora", "dia_semana", "mes", "es_festivo", "hora_sin", "hora_cos",
                  "dia_semana_sin", "dia_semana_cos", "dia_ano_sin", "dia_ano_cos",
                  "mes_sin", "mes_cos"]

# La configuración del medio de la rejilla de legacy/experimentos_xgboost/
# (Fuente: ML Zoomcamp, 06-trees/08-xgb-tuning.md). Con GPU entrena en ella.
DISPOSITIVO = "cuda" if shutil.which("nvidia-smi") else "cpu"
PARAMETROS = dict(max_depth=5, learning_rate=0.05, n_estimators=600, min_child_weight=10,
                  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                  tree_method="hist", device=DISPOSITIVO, n_jobs=-1, random_state=0)


def fijas(h):
    """Lo que entra siempre en el horizonte h: el precio del día t y el calendario."""
    return (["lp"] + CALENDARIO_DIA
            + [f"dia_semana_h{h}", f"es_festivo_h{h}", f"dia_semana_h{h}_sin", f"dia_semana_h{h}_cos"])


def todas_las_fijas():
    return list(dict.fromkeys(c for h in HORIZONTES for c in fijas(h)))


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def leer():
    """Todas las columnas del catálogo (desde marzo de 2015, horas con precio)."""
    base, info = fe.leer_panel_caracteristicas()
    X = fe.armar_todas(base, info)
    derivadas = [c for c in X.columns if fe.variable_de(c, info) is not None]
    return X, info, derivadas


def matriz(X, filas, cols):
    """
    Las columnas pedidas, en float32, para las filas de la máscara. No lee filas de la
    prueba: es la garantía de que la selección no la mira.
    """
    fechas = X.index.get_level_values("fecha")
    assert fechas[filas].max() <= FIN_VALIDACION, "la selección no puede mirar la prueba"
    horas = X.index.get_level_values("hora").to_numpy()
    M = np.empty((int(filas.sum()), len(cols)), dtype=np.float32, order="F")
    for j, c in enumerate(cols):
        M[:, j] = horas[filas] if c == "hora" else X[c].to_numpy()[filas]
    return M


def ajustar(A, y):
    return xgb.XGBRegressor(**PARAMETROS).fit(A, y)


def media_y_error_estandar(d, L):
    """
    Promedio de una serie diaria y su error estándar de Newey-West con L
    rezagos. Fuente: Newey y West (1987), como en el Diebold-Mariano de
    4_modelo_xgboost.ipynb.
    """
    u = d - d.mean()
    v = (u * u).mean()
    for l in range(1, min(L, len(d) - 1) + 1):
        v += 2 * (1 - l / (L + 1)) * (u[l:] * u[:-l]).mean()
    return d.mean(), np.sqrt(v / len(d))


# ---------------------------------------------------------------------------
# Etapa 1: limpieza
# ---------------------------------------------------------------------------

def rangos_estandarizados(M):
    """
    Rangos de cada columna, centrados y con norma 1 (un faltante queda en 0, el
    rango medio): así Z.T @ Z es la matriz de correlación de Spearman.
    """
    Z = np.empty_like(M)
    for j in range(0, M.shape[1], 200):
        Z[:, j:j + 200] = pd.DataFrame(M[:, j:j + 200]).rank().to_numpy(np.float32)
    Z -= np.nanmean(Z, axis=0)
    np.nan_to_num(Z, copy=False, nan=0.0)
    norma = np.linalg.norm(Z, axis=0)
    Z /= np.where(norma > 0, norma, 1.0)
    return Z


def limpieza(X, derivadas):
    """
    Devuelve las que salen sin mirar el objetivo (casi constantes, inestables y
    niveles que siguen al dólar, con su motivo) y, por horizonte, las candidatas que quedan, la correlación
    de Spearman de cada columna con el objetivo y qué le pasó a cada una. Todo
    con 2015-2019.

    Fuente: Complete-Feature-Selection, cuadernos 1 (constantes) y 2
    (correlación). Allá una columna sale si se parece a cualquiera anterior en
    el orden de la tabla; aquí el orden es la correlación con el objetivo, para
    que de cada grupo quede la que más se relaciona con la respuesta (decisión
    del autor), y solo se compara con las que ya quedaron, para no botar una
    por parecerse a otra que ya salió. Spearman en vez de Pearson, para que no
    la muevan los picos del precio (decisión propia). El filtro de estabilidad
    y la regla del dólar son propios y salieron de mirar 2020-2022: el
    diagnóstico de h = 7, donde las columnas que más empeoraban eran las que se
    salían del rango de entrenamiento, y la caída de h = 14 por el nivel del
    cargo por confiabilidad.
    """
    sel = X.index.get_level_values("fecha") <= FIN_SELECCION
    referencia = X.index.get_level_values("fecha")[sel] <= FIN_REFERENCIA
    nombres = ["lp"] + derivadas
    M = matriz(X, sel, nombres)

    fuera = {}
    for j, c in enumerate(derivadas, start=1):
        if c.startswith(SOLO_CAMBIO) and not c.endswith(SUFIJOS_DE_CAMBIO):
            fuera[c] = "nivel que sigue al dólar"
            continue
        x = M[:, j]
        x = x[~np.isnan(x)]
        _, n = np.unique(x, return_counts=True)
        if len(n) <= 1 or n.max() / len(x) >= CASI_CONSTANTE:
            fuera[c] = "casi constante"
            continue
        a, b = M[referencia, j], M[~referencia, j]
        a, b = a[~np.isnan(a)], b[~np.isnan(b)]
        bajo, alto = np.percentile(a, [1, 99])
        corrido = np.mean((b < bajo) | (b > alto))
        if corrido > MAX_FUERA_DE_RANGO:
            fuera[c] = f"inestable: {100 * corrido:.0f}% de 2018-2019 fuera del rango de 2015-2017"

    Z = rangos_estandarizados(M)
    del M
    Zy = rangos_estandarizados(matriz(X, sel, [f"y_h{h}" for h in HORIZONTES]))
    Cy = Z.T @ Zy                                  # cada columna contra cada objetivo
    C = np.abs(Z.T @ Z)                            # cada columna contra las demás
    del Z

    res = {}
    for i, h in enumerate(HORIZONTES):
        cy = Cy[1:, i]
        motivo = dict(fuera)
        quedan = [0]
        for j in np.argsort(-np.abs(cy), kind="stable") + 1:
            c = nombres[j]
            if c in fuera:
                continue
            r = C[j, quedan]
            k = int(r.argmax())
            if r[k] > MAX_CORRELACION:
                motivo[c] = f"correlación {r[k]:.3f} con {nombres[quedan[k]]}"
            else:
                quedan.append(j)
                motivo[c] = "pasa"
        res[h] = dict(candidatas=[nombres[j] for j in quedan[1:]], motivo=motivo,
                      corr_y=dict(zip(derivadas, cy)))
    return fuera, res


# ---------------------------------------------------------------------------
# Etapa 2: orden con XGBoost, SHAP y columnas de ruido
# ---------------------------------------------------------------------------

def columnas_de_ruido(X, candidatas, rng):
    """
    Copias de N_RUIDO columnas al azar con los días barajados: conservan su
    distribución y su forma dentro del día, pero no dicen nada del objetivo.
    Fuente: las columnas sombra de Boruta (Kursa y Rudnicki, 2010); aquí son
    unas pocas y no una por columna, para que alcance el tiempo.
    """
    sel = X.index.get_level_values("fecha") <= FIN_SELECCION
    n_dias = int(sel.sum()) // 24
    assert n_dias * 24 == sel.sum(), "la ventana de selección tiene que tener días completos"
    elegidas = [candidatas[i] for i in rng.choice(len(candidatas), N_RUIDO, replace=False)]
    M = matriz(X, sel, elegidas)
    R = np.empty_like(M)
    for j in range(N_RUIDO):
        R[:, j] = M[:, j].reshape(n_dias, 24)[rng.permutation(n_dias)].ravel()
    return R, elegidas


def ordenar(X, candidatas, h, R):
    """
    Importancia (promedio de |SHAP| en el año no visto) de las fijas y las
    candidatas en cada corte, y cuáles le ganan al mejor ruido en los dos.
    """
    sel = X.index.get_level_values("fecha") <= FIN_SELECCION
    f = X.index.get_level_values("fecha")[sel]
    y = X[f"y_h{h}"].to_numpy()[sel]
    A = np.concatenate([matriz(X, sel, fijas(h) + candidatas), R], axis=1)
    imps = []
    for inicio, fin in CORTES:
        tr = (f <= inicio - pd.offsets.Day(h + 1)) & ~np.isnan(y)
        ev = (f >= inicio) & (f <= fin) & ~np.isnan(y)
        m = ajustar(A[tr], y[tr])
        shap = m.get_booster().predict(xgb.DMatrix(A[ev]), pred_contribs=True)
        imps.append(np.abs(shap[:, :-1]).mean(axis=0))      # la última es el sesgo
    imp = np.vstack(imps)
    n_f, n_c = len(fijas(h)), len(candidatas)
    umbral = imp[:, n_f + n_c:].max(axis=1)
    pasa = (imp[:, n_f:n_f + n_c] > umbral[:, None]).all(axis=0)
    return imp.mean(axis=0)[:n_f + n_c], pasa, umbral


# ---------------------------------------------------------------------------
# Etapa 3: cuántas, con la validación
# ---------------------------------------------------------------------------

def cuantas(X, orden, h):
    """Error en 2020-2022 con las primeras k columnas del orden, y el k elegido."""
    f = X.index.get_level_values("fecha")
    y = X[f"y_h{h}"].to_numpy()
    tr = (f <= INICIO_VALIDACION - pd.offsets.Day(h + 1)) & ~np.isnan(y)
    ev = (f >= INICIO_VALIDACION) & (f <= FIN_VALIDACION) & ~np.isnan(y)
    n = len(orden)
    tamanos = [0] + sorted({k for k in TAMANOS if k < n} | ({n} if n else set()))
    cols = fijas(h) + orden[:max(tamanos)]
    A_tr, A_ev = matriz(X, tr, cols), matriz(X, ev, cols)
    n_f = len(fijas(h))
    filas = []
    for k in tamanos:
        m = ajustar(A_tr[:, :n_f + k], y[tr])
        e = y[ev] - m.predict(A_ev[:, :n_f + k])
        d = pd.Series(e ** 2).groupby(f[ev]).mean().to_numpy()
        mse, ee = media_y_error_estandar(d, h - 1 + 7)
        filas.append(dict(h=h, k=k, mse_log=mse, ee=ee, rmse_log=np.sqrt(mse),
                          rmse_log_ingenuo=np.sqrt(np.mean(y[ev] ** 2)),
                          elegible=k > 0 or n == 0))
    r = pd.DataFrame(filas)
    el = r[r["elegible"]]
    mejor = el.loc[el["mse_log"].idxmin()]
    k_elegido = int(el.loc[el["mse_log"] <= mejor["mse_log"] + mejor["ee"], "k"].min())
    r["mejor"] = r["k"] == mejor["k"]
    r["elegido"] = r["k"] == k_elegido
    return r, k_elegido


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------

def tabla_de_columnas(info, derivadas, limp, res):
    fijas_ = todas_las_fijas()
    t = pd.DataFrame(index=pd.Index(fijas_ + derivadas, name="columna"))
    var = [fe.variable_de(c, info) for c in t.index]
    t["variable"] = [v or "" for v in var]
    t["tipo"] = ["fija" if v is None else info.loc[v, "tipo"] for v in var]
    for h, r in res.items():
        t[f"corr_y_h{h}"] = pd.Series(limp[h]["corr_y"]).reindex(t.index)
        t[f"limpieza_h{h}"] = [limp[h]["motivo"].get(c, "fija") for c in t.index]
        t[f"importancia_h{h}"] = pd.Series(r["importancia"]).reindex(t.index)
        t[f"orden_h{h}"] = pd.Series({c: i + 1 for i, c in enumerate(r["orden"])}).reindex(t.index).astype("Int64")
        es_fija = t.index.isin(fijas(h))
        t[f"entra_h{h}"] = es_fija | (t[f"orden_h{h}"] <= r["k"]).fillna(False).to_numpy(bool)
        t[f"corta_h{h}"] = es_fija | (t[f"orden_h{h}"] <= min(N_CORTA, r["k"])).fillna(False).to_numpy(bool)
    return t


def tabla_de_variables(info, t, res):
    """
    Por variable: su peso en cada horizonte (suma de la importancia de sus
    columnas, en % del total de las candidatas) y cuántas de sus columnas entran.
    """
    d = t[t["tipo"] != "fija"]
    v = pd.DataFrame({"grupo": info["grupo"], "tipo": info["tipo"]})
    v["columnas"] = d.groupby("variable").size()
    for h in res:
        imp = d.groupby("variable")[f"importancia_h{h}"].sum()
        v[f"importancia_pct_h{h}"] = 100 * imp / imp.sum()
        v[f"entran_h{h}"] = d[d[f"entra_h{h}"]].groupby("variable").size()
    v = v.fillna({c: 0 for c in v.columns if c.startswith("entran")})
    v.insert(3, "importancia_pct_media", v[[f"importancia_pct_h{h}" for h in res]].mean(axis=1))
    return v.sort_values("importancia_pct_media", ascending=False)


def main():
    t0 = time.time()
    print("1. Columnas del paso 2c")
    X, info, derivadas = leer()
    print(f"   {len(X):,} filas x {len(derivadas)} columnas derivadas; XGBoost en {DISPOSITIVO}")

    print("2. Limpieza (2015-2019)")
    fuera, limp = limpieza(X, derivadas)
    conteo = pd.Series(fuera).str.split().str[0].value_counts()
    print(f"   salen {conteo.get('casi', 0)} casi constantes, {conteo.get('inestable:', 0)} inestables "
          f"y {conteo.get('nivel', 0)} niveles que siguen al dólar; "
          f"de las redundantes queda la más "
          f"correlacionada con el objetivo: quedan "
          + ", ".join(f"h{h} {len(limp[h]['candidatas'])}" for h in HORIZONTES)
          + f" [{time.time() - t0:.0f} s]")

    R, ruido = columnas_de_ruido(X, [c for c in derivadas if c not in fuera],
                                 np.random.default_rng(0))
    print(f"   ruido: copias barajadas de {', '.join(ruido)}")

    print("3. Orden con XGBoost y cuántas entran, por horizonte")
    res, validacion = {}, []
    for h in HORIZONTES:
        t1 = time.time()
        candidatas = limp[h]["candidatas"]
        importancia, pasa, umbral = ordenar(X, candidatas, h, R)
        n_f = len(fijas(h))
        imp_c = importancia[n_f:]
        idx = np.flatnonzero(pasa)
        orden = [candidatas[i] for i in idx[np.argsort(-imp_c[idx], kind="stable")]]
        val, k = cuantas(X, orden, h)
        validacion.append(val)
        res[h] = dict(importancia=dict(zip(fijas(h) + candidatas, importancia)), orden=orden, k=k)
        fila = val[val["elegido"]].iloc[0]
        print(f"   h={h:>2}: {len(orden)} le ganan al ruido; entran {k} "
              f"(RMSE log {fila['rmse_log']:.4f}, ingenuo {fila['rmse_log_ingenuo']:.4f}) "
              f"[{time.time() - t1:.0f} s]")

    print("4. Guardar")
    t = tabla_de_columnas(info, derivadas, limp, res)
    entran = [c for c in derivadas if t.loc[c, [f"entra_h{h}" for h in HORIZONTES]].any()]
    objetivos = [f"y_h{h}" for h in HORIZONTES]
    cols = ["bloque", "precio"] + [c for c in todas_las_fijas() if c != "hora"] + objetivos + entran
    tabla = X[cols].reset_index()
    tabla.to_csv(SALIDA, index=False, compression="gzip", float_format="%.6g")
    t.to_csv(COLUMNAS, float_format="%.6g")
    pd.concat(validacion).to_csv(VALIDACION, index=False, float_format="%.6g")
    tabla_de_variables(info, t, res).to_csv(VARIABLES, float_format="%.4g")

    print(f"\n{SALIDA.name}: {len(tabla):,} filas x {tabla.shape[1]} columnas "
          f"({len(entran)} columnas elegidas en algún horizonte), "
          f"{SALIDA.stat().st_size / 1e6:.1f} MB [{(time.time() - t0) / 60:.0f} min en total]")


if __name__ == "__main__":
    main()
