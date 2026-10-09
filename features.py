"""
Ingeniería de características.

Convierte el panel diario (panel_diario.csv) en la matriz de variables que usan
los modelos. El notebook importa este archivo, así que hay una sola versión de
cada transformación.

Tres pasos:
    preparar_panel      qué variables entran y cómo se llenan los huecos
    construir_features  rezagos, medias móviles, choques y calendario
    limpiar_matriz      quita constantes, redundantes y combinaciones exactas

La regla que manda en todo el archivo: para pronosticar el día t solo se puede
usar información que ya se conocía antes de ese día. Por eso casi todo entra
rezagado al menos un día.

La justificación de cada decisión y su relación con las guías del curso está en
DOCUMENTACION.md.
"""

import numpy as np
import pandas as pd

OBJETIVO = "precio_bolsa"

# El precio de bolsa es el costo marginal del despacho, así que estas dos
# variables son casi el mismo precio con otro nombre (correlación de 0,97 con
# el costo marginal). Si entraran, el modelo las copiaría y no aprendería nada
# del sistema eléctrico. Se dejan fuera.
DESPACHO = ["costo_marginal_prog", "precio_oferta_desp"]

# Variables que se conocen antes del día que se pronostica: se declaran o se
# fijan con anticipación. Pueden entrar sin rezago (rezago 0).
EX_ANTE = [
    "precio_escasez", "enficc", "precio_cargo_conf", "cee", "cere", "mc",
    "margen_reserva", "disp_declarada",
    "disp_decl_hidraulica", "disp_decl_termica", "disp_decl_despacho_central",
]

# Variables de eventos. XM no publica fila cuando el evento no ocurre: en once
# años no hay un solo cero en estas series. Un día sin dato es un día en que no
# hubo vertimiento, ni importación, ni generación solar.
EVENTOS = [
    "vertimientos", "importaciones", "exportaciones",
    "gen_solar", "frac_solar", "gen_eolica", "frac_eolica", "gen_liquidos",
]

MAX_FALTANTE = 0.15
# Una variable que empieza después de esta fecha obliga a recortar el inicio de
# toda la muestra (el modelo necesita todas las columnas el mismo día).
INICIO_MAXIMO = pd.Timestamp("2015-03-01")

LAGS = [1, 2, 3, 7, 14, 30]
VENTANAS = [7, 30]


def leer_panel(ruta="panel_diario.csv"):
    panel = pd.read_csv(ruta, parse_dates=["fecha"], index_col="fecha")
    return panel.sort_index().asfreq("D")


def preparar_panel(panel):
    """
    Decide qué variables pasan y llena los huecos que quedan.

    Hay tres tipos de dato faltante y cada uno se trata distinto:
      - eventos: el hueco es un cero real, se llena con 0
      - variables que arrancan tarde: se descartan, porque rellenar años antes
        de que existieran sería inventar datos
      - huecos de uno o dos días (festivos, fallas de publicación): se llenan con
        el último valor conocido, que solo mira hacia atrás

    Devuelve las variables listas y un resumen de lo que se descartó.
    """
    panel = panel.copy()
    eventos = [c for c in EVENTOS if c in panel.columns]
    panel[eventos] = panel[eventos].fillna(0)

    arranque = panel.apply(lambda s: s.first_valid_index())
    faltante = panel.isna().mean()
    tardias = [c for c in panel.columns
               if arranque[c] is not None and arranque[c] > INICIO_MAXIMO
               and faltante[c] <= MAX_FALTANTE]
    con_huecos = [c for c in panel.columns if c != OBJETIVO and faltante[c] > MAX_FALTANTE]

    entran = [c for c in panel.columns
              if c != OBJETIVO and c not in DESPACHO and c not in tardias
              and faltante[c] <= MAX_FALTANTE]
    base = panel[entran].ffill()

    # Con embalses bajos el precio sube mucho más que proporcionalmente. El
    # inverso del volumen útil le da al modelo esa forma sin tener que buscarla.
    base["inv_volumen_util_pct"] = 1 / base["volumen_util_pct"].clip(lower=0.02)

    descartes = {
        "despacho": [c for c in DESPACHO if c in panel.columns],
        "arrancan tarde": tardias,
        "muchos faltantes": con_huecos,
    }
    return base, descartes


def construir_features(panel):
    """
    Arma la matriz de características. Devuelve (X, precio, log_precio).

    Para cada variable x se crean tres tipos de columna, todas con información
    hasta ayer:
      x_lagk     el valor de hace k días
      x_maw      la media de los últimos w días (el nivel "normal")
      x_choquew  cuánto se alejó ayer de esa media (positivo = por encima de lo normal)

    Las ex ante tienen además x_lag0, el valor del mismo día.
    """
    precio = panel[OBJETIVO]
    log_precio = np.log(precio)
    dlog = log_precio.diff()

    base, _ = preparar_panel(panel)
    ex_ante = [c for c in base.columns if c in EX_ANTE]
    ex_post = [c for c in base.columns if c not in EX_ANTE]

    col = {}

    # dinámica del propio precio
    for k in LAGS:
        col[f"dlog_lag{k}"] = dlog.shift(k)
    for w in VENTANAS:
        # shift(1) ANTES del rolling: la ventana termina ayer. Una ventana que
        # incluyera el día t usaría el dato que se quiere pronosticar.
        col[f"dlog_sd{w}"] = dlog.shift(1).rolling(w).std()
        col[f"precio_choque{w}"] = log_precio.shift(1) - log_precio.shift(1).rolling(w).mean()

    for c in ex_ante:
        for k in [0] + LAGS:
            col[f"{c}_lag{k}"] = base[c].shift(k)
    for c in ex_post:
        for k in LAGS:
            col[f"{c}_lag{k}"] = base[c].shift(k)

    for c in base.columns:
        ayer = base[c].shift(1)
        for w in VENTANAS:
            media = ayer.rolling(w).mean()
            col[f"{c}_choque{w}"] = ayer - media
            col[f"{c}_ma{w}"] = media

    X = pd.DataFrame(col, index=panel.index)

    # el precio baja los fines de semana y sube los lunes
    X["es_lunes"] = (panel.index.dayofweek == 0).astype(int)
    X["es_sabado"] = (panel.index.dayofweek == 5).astype(int)
    X["es_domingo"] = (panel.index.dayofweek == 6).astype(int)
    return X, precio, log_precio


def limpiar_matriz(X_sel, umbral=0.95):
    """
    Se calcula solo con la ventana de selección (hasta 2019). Tres filtros:

      1. constantes: una columna que no varía no explica nada
      2. redundantes: si dos columnas correlacionan más de 0,95 se deja la
         primera (los rezagos de una misma variable se parecen mucho)
      3. combinaciones exactas: por construcción x_choque7 = x_lag1 - x_ma7, y
         con las tres juntas la regresión no puede separar sus efectos. Una
         columna se queda solo si aumenta el rango de la matriz.

    Devuelve la lista de columnas que sobreviven, en su orden original.
    """
    no_constantes = X_sel.columns[X_sel.std() > 0]
    Xc = X_sel[no_constantes]

    corr = Xc.corr().abs()
    quitar = set()
    for i, a in enumerate(Xc.columns):
        if a in quitar:
            continue
        for b in Xc.columns[i + 1:]:
            if corr.loc[a, b] > umbral:
                quitar.add(b)
    sin_redundantes = [c for c in Xc.columns if c not in quitar]

    Z = ((Xc[sin_redundantes] - Xc[sin_redundantes].mean()) / Xc[sin_redundantes].std()).values
    elegidas = []
    for i in range(len(sin_redundantes)):
        if np.linalg.matrix_rank(Z[:, elegidas + [i]]) > len(elegidas):
            elegidas.append(i)
    return [sin_redundantes[i] for i in elegidas]


def objetivo(log_precio, h):
    """Cambio del log del precio a h días: log P(t+h) - log P(t)."""
    return (log_precio.shift(-h) - log_precio).rename("y")
