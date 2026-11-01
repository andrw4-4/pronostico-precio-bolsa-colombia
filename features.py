"""
Ingeniería de características.

Convierte el panel diario (paneles/panel_diario.csv) en la matriz de variables que usan
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
docs/DOCUMENTACION.md.
"""

import warnings
from pathlib import Path

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
    # las variantes del precio de escasez y la energía en firme se publican
    # antes del despacho, igual que el precio de escasez de arriba
    "precio_esca_marg", "precio_esca_sup", "precio_esca_inf", "precio_esca_act",
    "oblig_energia_firme",
    # la predicción climática del IDEAM es un pronóstico: el día que aparece en
    # el panel es el día en que se publicó, así que se puede usar ese mismo día
    "pred_lluvia_andina", "pred_lluvia_caribe", "pred_lluvia_pacifica",
    "pred_lluvia_orinoquia", "pred_lluvia_amazonia",
    "pred_deficit", "pred_prob_max", "pred_enos",
]

# Variables de eventos. XM no publica fila cuando el evento no ocurre: en once
# años no hay un solo cero en estas series. Un día sin dato es un día en que no
# hubo vertimiento, ni importación, ni generación solar.
EVENTOS = [
    "vertimientos", "importaciones", "exportaciones",
    "gen_solar", "frac_solar", "gen_eolica", "frac_eolica", "gen_liquidos",
    # el vertimiento por embalse, el racionamiento y el intercambio con Ecuador
    # tampoco tienen fila los días que no pasan: ninguna publica un cero
    "vertido_embalse", "demanda_no_atendida", "dem_no_atendida_nop",
    "compras_tie", "ventas_tie", "tie_merito", "tie_fuera_merito",
]

MAX_FALTANTE = 0.15
# Una variable que empieza después de esta fecha obliga a recortar el inicio de
# toda la muestra (el modelo necesita todas las columnas el mismo día).
INICIO_MAXIMO = pd.Timestamp("2015-03-01")

LAGS = [1, 2, 3, 7, 14, 30]
VENTANAS = [7, 30]


def ruta_panel(nombre):
    """
    Los paneles viven en paneles/. En Colab se suben sueltos junto al notebook,
    así que si la carpeta no está se buscan en la carpeta de trabajo.
    """
    en_carpeta = Path(__file__).resolve().parent / "paneles" / nombre
    return en_carpeta if en_carpeta.exists() else Path(nombre)


def leer_panel(ruta=None):
    ruta = ruta_panel("panel_diario.csv") if ruta is None else ruta
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
    # Fuente: imputación por valor arbitrario, Galli sección 5 (ver docs/REFERENCIAS.md)
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
    # Fuente: transformación logarítmica, Galli sección 11
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
        # Fuente: diferencia frente a una variable de referencia, Galli sección 17
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
    # Fuente: variables de fecha, Galli sección 15
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
    # Fuente: Complete-Feature-Selection, cuadernos 1 (constantes) y 2
    # (correlación). El filtro de rango es propio (ver docs/REFERENCIAS.md)
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


# ===========================================================================
# Panel horario: catálogo de columnas derivadas
# ===========================================================================
#
# El paso 2c_caracteristicas_horarias.py deja las variables base (una columna
# por variable, ya transformada) en paneles/panel_caracteristicas.csv.gz, y su
# diccionario en paneles/panel_caracteristicas_variables.csv. Las columnas
# derivadas (rezagos, medias móviles, tendencia y variabilidad) se arman aquí,
# en memoria, cuando se necesitan: todas juntas son unas 1.900 columnas y unos
# 800 MB, así que no se guardan en disco.
#
# La regla es la del panel: la fila (día t, hora H) se para al cierre del día t,
# así que usa las 24 horas del día t y todo lo anterior. Ninguna columna mira más
# adelante, salvo las _manana de las cuatro variables que se deciden antes de
# que empiece el día t+1.
#
# Fuente de cada familia (ver docs/REFERENCIAS.md):
#   - rezagos del precio: las 24 horas del día y los días 1, 2, 3 y 7 del modelo
#     LEAR (Lago et al., 2021), más 14, 21 y 28 por la autocorrelación parcial
#     del precio en 2015-2019;
#   - medias móviles de día, semana y mes: modelo HAR (Corsi, 2009);
#   - rampa del día, tendencia (media de 7 menos media de 30) y memoria de picos:
#     decisión propia del plan de variables, para que el modelo vea la forma del
#     día, si la variable viene subiendo o bajando, y si hubo un pico reciente.

REZAGOS_HORAS_PRECIO = list(range(1, 24))
REZAGOS_DIAS_PRECIO = [1, 2, 3, 7, 14, 21, 28]
REZAGOS_HORAS = [0, 1, 2, 3]
REZAGOS_DIAS = [1, 2, 3, 7, 14]
REZAGOS_DIAS_DIARIAS = [0, 1, 2, 7]
VENTANAS_DIAS = [7, 30]              # medias y variabilidad a la misma hora (o por día)
VENTANAS_MEDIA_HORAS = [168, 720]    # medias de todas las horas: 7 y 30 días
VENTANAS_SD_HORAS = [24, 168]        # variabilidad de todas las horas: 1 y 7 días
# Fracción mínima de datos en una ventana para calcularla: así un hueco suelto
# no borra un mes entero de medias.
MIN_EN_VENTANA = 0.75
# Se deciden antes de que empiece el día t+1 (despacho programado y
# disponibilidad declarada): tienen además la columna _manana.
DE_ANTEMANO = ["cmg_despacho", "pron_demanda", "margen_decl_pron", "disp_termica_frac"]
INICIO_HORARIO = pd.Timestamp("2015-03-01")


def leer_panel_caracteristicas(ruta=None, ruta_variables=None):
    """
    Devuelve (base, info): el panel de variables base con índice (fecha, hora),
    en la grilla completa de 24 horas, y el diccionario de las variables que
    entran (una fila por variable, con su tipo: precio, horaria o diaria).
    """
    ruta = ruta_panel("panel_caracteristicas.csv.gz") if ruta is None else ruta
    if ruta_variables is None:
        ruta_variables = ruta_panel("panel_caracteristicas_variables.csv")
    base = pd.read_csv(ruta, parse_dates=["fecha"]).set_index(["fecha", "hora"]).sort_index()
    dias = base.index.get_level_values("fecha").unique()
    base = base.reindex(pd.MultiIndex.from_product([dias, range(1, 25)], names=["fecha", "hora"]))
    info = pd.read_csv(ruta_variables, index_col="variable")
    return base, info[info["entra"]]


def _minimo(n):
    return max(2, int(np.ceil(MIN_EN_VENTANA * n)))


def _atras(x, k):
    """El valor de k filas atrás (k > 0) o adelante (k < 0)."""
    out = np.full(len(x), np.nan)
    if k > 0:
        out[k:] = x[:-k]
    elif k < 0:
        out[:k] = x[-k:]
    else:
        out[:] = x
    return out


def _misma_hora(x, d, como):
    """Media, desviación estándar o máximo de la misma hora en los últimos d días, con el día t."""
    ventana = pd.DataFrame(x.reshape(-1, 24)).rolling(d, min_periods=_minimo(d))
    return getattr(ventana, como)().to_numpy().ravel()


def _ultimas_horas(x, k, como):
    """Lo mismo sobre las últimas k horas seguidas, hasta la de la fila."""
    ventana = pd.Series(x).rolling(k, min_periods=_minimo(k))
    return getattr(ventana, como)().to_numpy()


def _del_dia(x, como):
    """La hora 24, el promedio o la rampa (máximo - mínimo) del día t, en sus 24 horas."""
    m = x.reshape(-1, 24)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # días sin ningún dato
        if como == "ultima":
            v = pd.DataFrame(m).ffill(axis=1).to_numpy()[:, -1]
        elif como == "media":
            v = np.nanmean(m, axis=1)
        else:
            v = np.nanmax(m, axis=1) - np.nanmin(m, axis=1)
    return np.repeat(v, 24)


def _columnas_precio(lp):
    """43 columnas. Los rezagos y medias van como diferencia frente a lp (dlp_...)."""
    c = {}
    for k in REZAGOS_HORAS_PRECIO:
        c[f"dlp_l{k}h"] = lp - _atras(lp, k)
    for d in REZAGOS_DIAS_PRECIO:
        c[f"dlp_l{d}d"] = lp - _atras(lp, 24 * d)
    c["dlp_ultima"] = lp - _del_dia(lp, "ultima")
    c["dlp_dia"] = lp - _del_dia(lp, "media")
    c["lp_rampa"] = _del_dia(lp, "rampa")
    for d in VENTANAS_DIAS:
        c[f"dlp_ma{d}d_mh"] = lp - _misma_hora(lp, d, "mean")
    for k in VENTANAS_MEDIA_HORAS:
        c[f"dlp_ma{k}h"] = lp - _ultimas_horas(lp, k, "mean")
    # la variabilidad a la misma hora va sobre el cambio frente a ayer, no sobre
    # el nivel, que sube y baja con el año hidrológico
    cambio = lp - _atras(lp, 24)
    for d in VENTANAS_DIAS:
        c[f"lp_sd{d}d_mh"] = _misma_hora(cambio, d, "std")
    for k in VENTANAS_SD_HORAS:
        c[f"lp_sd{k}h"] = _ultimas_horas(lp, k, "std")
    # memoria de picos: cuánto más alto estuvo el precio hace poco
    c["dlp_max_24h"] = _ultimas_horas(lp, 24, "max") - lp
    c["dlp_max_7d"] = _misma_hora(lp, 7, "max") - lp
    return c


def _columnas_horaria(n, x):
    """21 columnas (22 si se conoce de antemano)."""
    c = {}
    for k in REZAGOS_HORAS:
        c[f"{n}_l{k}h"] = _atras(x, k)
    for d in REZAGOS_DIAS:
        c[f"{n}_l{d}d"] = _atras(x, 24 * d)
    c[f"{n}_ultima"] = _del_dia(x, "ultima")
    c[f"{n}_dia"] = _del_dia(x, "media")
    c[f"{n}_rampa"] = _del_dia(x, "rampa")
    medias = {}
    for d in VENTANAS_DIAS:
        medias[d] = _misma_hora(x, d, "mean")
        c[f"{n}_ma{d}d_mh"] = medias[d]
    for k in VENTANAS_MEDIA_HORAS:
        c[f"{n}_ma{k}h"] = _ultimas_horas(x, k, "mean")
    corta, larga = VENTANAS_DIAS
    c[f"{n}_ma{corta}_menos_ma{larga}"] = medias[corta] - medias[larga]
    for d in VENTANAS_DIAS:
        c[f"{n}_sd{d}d_mh"] = _misma_hora(x, d, "std")
    for k in VENTANAS_SD_HORAS:
        c[f"{n}_sd{k}h"] = _ultimas_horas(x, k, "std")
    if n in DE_ANTEMANO:
        c[f"{n}_manana"] = _atras(x, -24)
    return c


def _columnas_diaria(n, x):
    """10 columnas. La variable vale lo mismo en las 24 horas: se trabaja día a día."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        s = pd.Series(np.nanmean(x.reshape(-1, 24), axis=1))
    c = {}
    for d in REZAGOS_DIAS_DIARIAS:
        c[f"{n}_l{d}d"] = s.shift(d)
    medias = {}
    for d in VENTANAS_DIAS:
        medias[d] = s.rolling(d, min_periods=_minimo(d)).mean()
        c[f"{n}_ma{d}d"] = medias[d]
    corta, larga = VENTANAS_DIAS
    c[f"{n}_delta_{corta}d"] = s - s.shift(corta)
    c[f"{n}_ma{corta}_menos_ma{larga}"] = medias[corta] - medias[larga]
    for d in VENTANAS_DIAS:
        c[f"{n}_sd{d}d"] = s.rolling(d, min_periods=_minimo(d)).std()
    return {k: np.repeat(v.to_numpy(), 24) for k, v in c.items()}


def columnas_de(nombre, base, info):
    """Las columnas derivadas de una variable base, como diccionario de arreglos float32."""
    if nombre == "lp":
        c = _columnas_precio(base["lp"].to_numpy(float))
    elif info.loc[nombre, "tipo"] == "horaria":
        c = _columnas_horaria(nombre, base[nombre].to_numpy(float))
    else:
        c = _columnas_diaria(nombre, base[nombre].to_numpy(float))
    return {k: np.where(np.isfinite(v), v, np.nan).astype(np.float32) for k, v in c.items()}


def _fijas(base, info):
    """Las columnas que van tal cual: identificación, calendario, objetivos y lp."""
    return [c for c in base.columns if c == "lp" or c not in info.index]


def _filas(base, desde):
    """Las filas que van a la tabla: desde `desde` y solo las horas con precio."""
    fechas = base.index.get_level_values("fecha")
    return (fechas >= pd.Timestamp(desde)) & base["precio"].notna().to_numpy()


def _a_tabla(base, columnas, filas, fijas):
    """
    Un solo DataFrame con las columnas fijas y las derivadas. Las derivadas van a
    una matriz float32 creada de una vez y llenada columna por columna (orden F),
    vaciando el diccionario a medida que se llena: así no están dos veces en
    memoria. Nada de concat en ciclo, que copia todo en cada paso.
    """
    nombres = list(columnas)
    matriz = np.empty((int(filas.sum()), len(nombres)), dtype=np.float32, order="F")
    for j, nombre in enumerate(nombres):
        matriz[:, j] = columnas.pop(nombre)[filas]
    derivadas = pd.DataFrame(matriz, index=base.index[filas], columns=nombres, copy=False)
    if not fijas:
        return derivadas
    return pd.concat([base.loc[filas, fijas], derivadas], axis=1, copy=False)


def armar_todas(base, info, desde=INICIO_HORARIO, con_fijas=True):
    """
    Todas las columnas derivadas, desde `desde` y solo las horas con precio.
    Con con_fijas=True van antes las columnas fijas (fecha y hora en el índice,
    bloque, precio, lp, calendario y objetivos).
    """
    columnas = {}
    for nombre in info.index:
        columnas.update(columnas_de(nombre, base, info))
    fijas = _fijas(base, info) if con_fijas else []
    return _a_tabla(base, columnas, _filas(base, desde), fijas)


def variable_de(nombre, info):
    """
    La variable base de la que sale una columna derivada, o None si la columna
    no es derivada (lp, calendario, objetivos). Se prueba primero el nombre más
    largo, para que demanda_max_potencia_rel_l0d no se tome como de demanda.
    """
    if nombre.startswith(("dlp_", "lp_")):
        return "lp"
    return next((v for v in sorted(info.index, key=len, reverse=True)
                 if nombre.startswith(v + "_")), None)


def armar(base, info, nombres, desde=INICIO_HORARIO):
    """
    Arma solo las columnas pedidas, por su nombre. Las fijas se toman tal cual.
    Sirve para dejar en el panel final solo las columnas elegidas, o para probar
    otra en Colab.
    """
    por_variable, fijas = {}, []
    for nombre in nombres:
        if nombre in _fijas(base, info):
            fijas.append(nombre)
            continue
        var = variable_de(nombre, info)
        if var is None:
            raise KeyError(f"no sé de qué variable sale la columna {nombre}")
        por_variable.setdefault(var, []).append(nombre)
    columnas = {}
    for var, pedidas in por_variable.items():
        todas = columnas_de(var, base, info)
        faltan = set(pedidas) - set(todas)
        if faltan:
            raise KeyError(f"columnas que el catálogo no arma: {sorted(faltan)}")
        columnas.update({n: todas[n] for n in pedidas})
    return _a_tabla(base, columnas, _filas(base, desde), fijas)[list(nombres)]
