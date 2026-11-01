"""
Paso 2d: la selección de variables. El panel horario para modelar, con las
variables y los rezagos elegidos por pruebas estadísticas.

    python 2d_seleccion_variables.py

Pendiente: por ahora arma sus propias candidatas a partir del panel completo.
En la etapa siguiente pasará a tomarlas del panel de características del paso
2c (2c_caracteristicas_horarias.py), con features.armar().

Salidas, en paneles/:
    panel_horario_modelo.csv.gz            la tabla para modelar
    panel_horario_modelo_columnas.csv      cada característica, en qué horizontes
                                           entra y con qué estadístico t
    panel_horario_modelo_variables.csv     cada variable: calidad,
                                           estacionariedad, transformación y
                                           en qué orden entró en cada horizonte

La regla de información
-----------------------
Cada fila es (día t, hora H) y se para al cierre del día t: se conocen las 24
horas del día t y todo lo anterior. El objetivo es

    y_h = log P(t+h, H) - log P(t, H),     h = 1, ..., 7, 14 y 30

y el ingenuo (y = 0) es "a esa hora, igual que hoy". Como la base del objetivo
es el precio del día t, el día t entra completo en la información; por eso
valen los rezagos de horas (la hora anterior, dos horas antes, ...).

Lo único que mira más allá del día t son las columnas *_manana, de las cuatro
variables que se deciden antes de que empiece el día t+1 (despacho programado,
pronóstico de demanda y disponibilidad declarada). Que se publiquen antes del
cierre del día t es una suposición: el despacho del día siguiente se publica
la víspera, pero no se verificó la hora.

XM publica el precio con 2 días de atraso: con datos hasta t, el pronóstico real
de mañana es h = 3. Las variables que salen todavía más tarde entran con ese
atraso adicional (ATRASO_EXTRA, medido el 10 de octubre de 2026 en
datos/sondeos/publicacion_metricas_horarias.csv).

Cómo se eligen
--------------
Todo con la ventana de selección (marzo de 2015 a diciembre de 2019).

0. Calidad. Cada variable con máximo 1% de faltantes desde marzo de 2015 y que
   no sea casi constante (un valor en 99% de las horas o más).

1. Estacionariedad. Prueba ADF (Dickey-Fuller aumentada, rezagos por AIC) sobre
   el promedio diario de cada variable. Si no se rechaza la raíz unitaria al 5%,
   la variable entra como su desviación frente al promedio de los últimos 28
   días a la misma hora. Una variable con raíz unitaria contra un objetivo
   estacionario da pruebas que no valen (regresión desbalanceada). Se reporta
   también KPSS, solo como información.

2. Rezagos del precio. Candidatos: el precio de la misma hora y de 1 a 23 horas
   antes, de la misma hora 1 a 7, 14, 21 y 28 días antes, la hora 24 del día t,
   el promedio del día t y los promedios de 7 y 30 días a esa hora. Se eligen
   por selección hacia adelante: en cada paso entra el candidato con mayor
   estadístico t condicional a lo ya elegido y al calendario, si su valor p es
   menor que 0,01 dividido por el número de candidatos que quedan (Bonferroni).
   Es la versión condicional de la autocorrelación parcial (PACF): cada rezago
   tiene que aportar algo que los anteriores no tienen.

3. Rezagos de cada variable. Los mismos candidatos (las diarias solo por días:
   0, 1, 2, 3, 7, 14 y 28, y los promedios de 7 y 30), con la misma selección
   hacia adelante, ahora condicional al calendario y a los rezagos del precio.
   Es la idea de causalidad de Granger (1969): una variable sirve si sus
   rezagos predicen el cambio del precio más allá de lo que ya dice el propio
   precio.

4. Variables con más poder predictivo. Con el bloque de rezagos de cada
   variable, selección hacia adelante por bloques con una prueba de Wald
   conjunta: entra la variable con menor valor p condicional a todo lo ya
   elegido, si es menor que 0,01 entre el número de variables que quedan. Así
   dos variables que dicen lo mismo (la participación térmica y la
   hidráulica) no entran las dos.

Los pasos 2 a 4 se hacen para cada horizonte por separado.

Errores estándar. Las 24 horas de un día comparten el estado del sistema, y
con h días de horizonte los objetivos de días seguidos se traslapan. Por eso
los estadísticos t y de Wald usan errores de Driscoll y Kraay (1998): se suman
las contribuciones de las 24 horas de cada día y a esa serie diaria se le
aplica Newey-West (1987) con h - 1 + 7 rezagos (h - 1 por el traslape y 7 por
la regla habitual de Newey-West para unos 1.750 días).

Las pruebas usan puntajes normales (el rango de cada columna llevado a la
normal) en vez de los valores: así miden relaciones monótonas y no las mueven
los picos del precio.

Límite: las pruebas son lineales en los puntajes normales. Una variable que
solo sirve en interacción con otra (lo que XGBoost sí aprovecha) puede quedar
por fuera.
"""

import warnings
from pathlib import Path

import holidays
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

# KPSS avisa cuando el valor p cae fuera de su tabla (menor que 0,01 o mayor que 0,1)
warnings.filterwarnings("ignore", category=InterpolationWarning)

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "paneles" / "panel_horario_completo.csv.gz"
SALIDA = BASE / "paneles" / "panel_horario_modelo.csv.gz"
COLUMNAS = BASE / "paneles" / "panel_horario_modelo_columnas.csv"
VARIABLES = BASE / "paneles" / "panel_horario_modelo_variables.csv"

# de 1 a 7 días, dos semanas y un mes
HORIZONTES = [1, 2, 3, 4, 5, 6, 7, 14, 30]
CORTOS = [h for h in HORIZONTES if h <= 7]
INICIO = pd.Timestamp("2015-03-01")
FIN_SELECCION = pd.Timestamp("2019-12-31")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
FIN_PRUEBA_A = pd.Timestamp("2025-12-31")

ALFA = 0.01
MAX_FALTANTE = 0.01
MAX_REZAGOS_PRECIO = 12
MAX_REZAGOS = 6
VENTANA_DESVIACION = 28

REZAGOS_HORAS = list(range(24))                       # 0 = la misma hora del día t
REZAGOS_DIAS = [1, 2, 3, 4, 5, 6, 7, 14, 21, 28]       # misma hora, d días antes
REZAGOS_DIARIAS = [0, 1, 2, 3, 7, 14, 28]
VENTANAS = [7, 30]

# Días que cada columna se publica después del precio (que va a 2 días).
ATRASO_EXTRA = {
    "oferta_cap_total": 8, "cap_bajo_200": 8, "cap_bajo_500": 8,
    "oferta_marginal": 8, "escalon_siguiente": 8, "holgura_mw": 8,
    "margen_ofertado": 8,
    "marg_hidraulica": 8, "marg_termica": 8, "marg_gas": 8, "marg_carbon": 8,
    "marg_liquidos": 8,
    "oferta_p50": 8, "oferta_dispersion": 8, "pendiente_curva": 8,
    "compras_contrato": 3, "precio_prom_contrato": 3, "precio_cont_no_regu": 3,
    "perdidas_energia": 3, "restricciones": 3, "compras_tie": 3,
}

# Se deciden antes de que empiece el día t+1: tienen además la columna *_manana.
EX_ANTE = {"cmg_despacho", "pron_demanda", "margen_decl_pron", "disp_termica_frac"}


# ---------------------------------------------------------------------------
# Lectura y limpieza
# ---------------------------------------------------------------------------

def leer():
    p = pd.read_csv(ENTRADA, parse_dates=["fecha"])
    p = p.drop(columns=["fecha_hora"]).set_index(["fecha", "hora"]).sort_index()
    dias = pd.date_range(p.index.get_level_values("fecha").min(),
                         p.index.get_level_values("fecha").max(), freq="D")
    # los desplazamientos en horas suponen la grilla completa de 24 horas
    return p.reindex(pd.MultiIndex.from_product([dias, range(1, 25)], names=["fecha", "hora"]))


def rellenar(s, dias=3):
    """Hueco suelto = el valor de la misma hora del día anterior, hasta `dias` días."""
    m = s.unstack("hora").ffill(limit=dias)
    return m.stack(future_stack=True).reindex(s.index)


def preparar(p):
    """Rellena huecos y aplica el atraso de publicación de cada columna."""
    p = p.copy()
    for c in p.columns:
        if c in ("dia_semana", "es_festivo"):
            continue
        if c != "precio_bolsa":
            p[c] = rellenar(p[c])
        if c in ATRASO_EXTRA:
            p[c] = p[c].shift(24 * ATRASO_EXTRA[c])
    return p


# ---------------------------------------------------------------------------
# Operaciones que solo miran hasta el cierre del día t
# ---------------------------------------------------------------------------

def media_dia(s):
    return s.groupby(level="fecha").transform("mean")


def suma_dia(s):
    """Total de las 24 horas del día de la fila; vacío si el día no tiene datos."""
    total = s.groupby(level="fecha").sum(min_count=1)
    return pd.Series(total.reindex(s.index.get_level_values("fecha")).to_numpy(), index=s.index)


def ultima_hora(s):
    return s.groupby(level="fecha").transform("last")


def misma_hora_media(s, d):
    """Promedio de la misma hora en los últimos d días, incluido el día t."""
    return pd.concat([s.shift(24 * k) for k in range(d)], axis=1).mean(axis=1)


def log_pos(s):
    """Logaritmo para precios que a veces valen 0 (el costo marginal, unas pocas horas)."""
    return np.log(s.clip(lower=1.0))


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

def variables(p):
    """
    nombre -> (serie, tipo). tipo 'h' cambia por hora; 'd' es una por día.

    Las cantidades en MWh van como fracción de la demanda o de la generación
    (la demanda crece unos puntos por año y la solar se multiplicó desde 2023)
    y los precios en logaritmo.
    """
    v = {}

    def h(nombre, serie):
        v[nombre] = (serie, "h")

    def d(nombre, serie):
        v[nombre] = (serie, "d")

    def r(a, b):
        return a / b.replace(0, np.nan)

    dem, gen, pron = p["demanda_comercial"], p["gen_total"], p["pron_demanda_cnd"]

    # demanda
    h("demanda", np.log(dem))
    h("pron_demanda", np.log(pron))
    h("error_pron_demanda", r(p["error_pron_demanda"], pron))
    h("dem_no_regulada_frac", r(p["demanda_no_regulada"], dem))
    # disponibilidad
    h("margen_declarado", p["margen_declarado"])
    h("margen_decl_pron", r(p["disp_declarada"], pron))          # ex ante
    h("disp_real_vs_decl", r(p["disp_real"], p["disp_declarada"]))
    h("disp_termica_frac", r(p["disp_decl_termica"], p["disp_declarada"]))
    # generación
    for t in ("termica", "hidraulica", "fncer"):
        h(f"frac_{t}", p[f"frac_{t}"])
    h("gen_seguridad_rel", r(p["gen_seguridad"], gen))
    h("gen_fuera_merito_rel", r(p["gen_fuera_merito"], gen))
    h("gen_restricciones_rel", r(p["gen_restricciones"], gen))
    h("redespacho_vs_programa", r(p["gen_prog_redespacho"] - p["gen_programada"], dem))
    h("gen_ideal_termica_frac", r(p["gen_ideal_termica"], p["gen_ideal_total"]))
    h("consumo_por_mwh_termico", r(p["consumo_combustible"], p["gen_termica"]))
    h("co2_por_mwh", r(p["co2_total"], gen))
    for c in ("gas", "carbon", "liquidos"):
        h(f"co2_{c}_frac", r(p[f"co2_{c}"], p["co2_total"]))
    # red, intercambios y contratos
    h("restricciones_rel", r(p["restricciones"], dem))
    h("restricciones_sin_aliv_rel", r(p["restricciones_sin_aliv"], dem))
    h("perdidas_rel", r(p["perdidas_energia"], dem))
    h("intercambio_neto_rel", r(p["importaciones"] - p["exportaciones"], dem))
    h("contrato_frac", r(p["compras_contrato"], dem))
    h("precio_contrato", log_pos(p["precio_prom_contrato"]))
    h("precio_contrato_no_reg", log_pos(p["precio_cont_no_regu"]))
    # costo marginal programado
    h("cmg_despacho", log_pos(p["cmg_despacho"]))                 # ex ante
    h("cmg_redespacho", log_pos(p["cmg_redespacho"]))
    h("ajuste_cmg", log_pos(p["cmg_redespacho"]) - log_pos(p["cmg_despacho"]))
    # curva de mérito y planta marginal
    h("oferta_marginal", log_pos(p["oferta_marginal"]))
    h("margen_ofertado", p["margen_ofertado"])
    h("cap_bajo_200_rel", r(p["cap_bajo_200"], dem))
    h("cap_bajo_500_rel", r(p["cap_bajo_500"], dem))
    h("holgura_rel", r(p["holgura_mw"], dem))
    h("escalon_siguiente", np.log1p(p["escalon_siguiente"].clip(lower=0)))
    for t in ("termica", "gas", "carbon", "liquidos"):
        h(f"marg_{t}", p[f"marg_{t}"])

    # diarias
    d("volumen_util", p["volumen_util_pct"])
    d("aportes_pct", p["aportes_pct_sistema"])
    # vertimientos es un evento: un día sin fila es un día sin vertimiento. Va
    # sobre la demanda real del día (sumando las horas, en kWh como el vertimiento)
    vert = p["vertimientos"].where(p["volumen_util_pct"].isna(), p["vertimientos"].fillna(0))
    d("vertimientos_rel", r(vert, 1000 * suma_dia(p["demanda_real"])))
    for c in ("lluvia_anom_acum30", "lluvia_anom_acum90", "oni", "nino34_anom", "roni",
              "pred_deficit", "pred_enos", "pred_lluvia_andina",
              "hhi_generacion", "gen_top5_pct", "frac_gas_en_termica", "n_plantas_activas",
              "oferta_dispersion", "pendiente_curva"):
        d(c, p[c])
    # perfil del día t, con sus 24 horas (se conocen al cierre del día)
    precio = p["precio_bolsa"].groupby(level="fecha")
    d("precio_cv_intradia", precio.transform("std") / precio.transform("mean"))
    d("ratio_pico_valle", precio.transform("max") / precio.transform("min").replace(0, np.nan))
    demanda = dem.groupby(level="fecha")
    d("factor_carga", demanda.transform("mean") / demanda.transform("max").replace(0, np.nan))
    d("precio_escasez", log_pos(p["precio_escasez"]))
    d("trm", np.log(p["trm"]))
    d("oferta_p50", log_pos(p["oferta_p50"]))
    return v


def rezagos(nombre, s, tipo):
    """Todos los rezagos candidatos de una variable ya transformada."""
    c = {}
    if tipo == "h":
        for k in REZAGOS_HORAS:
            c[f"{nombre}_l{k}h"] = s.shift(k)
        for k in REZAGOS_DIAS:
            c[f"{nombre}_l{k}d"] = s.shift(24 * k)
        c[f"{nombre}_ultima"] = ultima_hora(s)          # la hora 24 del día t
        c[f"{nombre}_dia"] = media_dia(s)               # el promedio del día t
    else:
        for k in REZAGOS_DIARIAS:
            c[f"{nombre}_l{k}d"] = s.shift(24 * k)
    for w in VENTANAS:
        c[f"{nombre}_ma{w}d"] = misma_hora_media(s, w)
    if nombre in EX_ANTE:
        c[f"{nombre}_manana"] = s.shift(-24)
    return pd.DataFrame(c).replace([np.inf, -np.inf], np.nan)


def transformar(s, transformacion):
    # Fuente: diferencia frente a una referencia, Galli sección 17
    return s if transformacion == "nivel" else s - misma_hora_media(s, VENTANA_DESVIACION)


# ---------------------------------------------------------------------------
# Calidad y estacionariedad
# ---------------------------------------------------------------------------

def probar_estacionariedad(s):
    # Fuente: Dickey y Fuller (1979) con statsmodels; KPSS (Kwiatkowski et al.,
    # 1992) solo se reporta. Ver docs/REFERENCIAS.md
    diaria = s.groupby(level="fecha").mean().loc[INICIO:FIN_SELECCION].dropna()
    adf_p = adfuller(diaria, autolag="AIC")[1]
    kpss_p = kpss(diaria, regression="c", nlags="auto")[1]
    return adf_p, kpss_p


def calidad_y_transformacion(vars_):
    """Qué variables pasan la calidad y cómo entra cada una. Devuelve (tabla, transformaciones)."""
    filas, trans = [], {}
    for nombre, (s, tipo) in vars_.items():
        s = s.replace([np.inf, -np.inf], np.nan)
        desde = s.loc[INICIO:]
        falt = desde.isna().mean()
        comun = desde.value_counts(normalize=True).iloc[0] if desde.notna().any() else 1.0
        fila = {"variable": nombre, "tipo": "horaria" if tipo == "h" else "diaria",
                "faltante_pct": round(100 * falt, 2), "valor_mas_comun": round(comun, 3)}
        if falt > MAX_FALTANTE:
            fila["motivo"] = "faltantes"
        elif comun >= 0.99:
            fila["motivo"] = "casi constante"
        else:
            adf_p, kpss_p = probar_estacionariedad(s)
            fila.update(adf_p=adf_p, kpss_p=kpss_p)
            trans[nombre] = "nivel" if adf_p < 0.05 else f"desviacion_{VENTANA_DESVIACION}d"
            fila["transformacion"] = trans[nombre]
            if trans[nombre] != "nivel":
                fila["adf_p_transformada"] = probar_estacionariedad(transformar(s, trans[nombre]))[0]
        filas.append(fila)
    return pd.DataFrame(filas).set_index("variable"), trans


def candidatos(p, trans):
    """Todos los candidatos: los rezagos del precio y de cada variable que pasó la calidad."""
    vars_ = variables(p)
    cand = {"lp": rezagos("lp", np.log(p["precio_bolsa"]), "h")}
    for nombre, t in trans.items():
        s, tipo = vars_[nombre]
        cand[nombre] = rezagos(nombre, transformar(s.replace([np.inf, -np.inf], np.nan), t), tipo)
    return cand


# ---------------------------------------------------------------------------
# Pruebas con errores de Driscoll-Kraay
# ---------------------------------------------------------------------------

def puntajes_normales(M):
    """
    El rango de cada columna llevado a la normal; un faltante queda en 0 (la media).
    Fuente: Beasley, Erickson y Allison (2009).
    """
    df = pd.DataFrame(M)
    z = stats.norm.ppf((df.rank() - 0.5) / df.count())
    return np.nan_to_num(z, nan=0.0)


def sumas_por_dia(S, dia, n_dias):
    out = np.zeros((n_dias, S.shape[1]))
    np.add.at(out, dia, S)
    return out


def t_driscoll_kraay(X, y, dia, n_dias, L):
    """
    Estadístico t de cada columna de X (ya residualizada) al explicar y, una por una.
    Fuente: Driscoll y Kraay (1998): las contribuciones se suman por día y a esa
    serie se le aplica Newey y West (1987) con L rezagos.
    """
    sxx = (X * X).sum(0)
    b = (X * y[:, None]).sum(0) / sxx
    e = y[:, None] - X * b
    S = sumas_por_dia(X * e, dia, n_dias)
    om = (S * S).sum(0)
    for l in range(1, L + 1):
        om += 2 * (1 - l / (L + 1)) * (S[l:] * S[:-l]).sum(0)
    return b * sxx / np.sqrt(om)


def wald_driscoll_kraay(X, y, dia, n_dias, L):
    """
    Prueba de Wald conjunta de las columnas de X; devuelve (estadístico, valor p).
    Fuente: la misma covarianza de Driscoll y Kraay (1998).
    """
    Q = X.T @ X
    b = np.linalg.solve(Q, X.T @ y)
    e = y - X @ b
    S = sumas_por_dia(X * e[:, None], dia, n_dias)
    om = S.T @ S
    for l in range(1, L + 1):
        G = S[l:].T @ S[:-l]
        om += (1 - l / (L + 1)) * (G + G.T)
    Qi = np.linalg.inv(Q)
    V = Qi @ om @ Qi
    W = float(b @ np.linalg.solve(V, b))
    return W, stats.chi2.sf(W, X.shape[1])


def quitar(Q, M):
    """
    Residuo de M después de proyectar sobre las columnas ortonormales de Q.
    Fuente: teorema de Frisch-Waugh-Lovell; probar una variable con los residuos
    da el mismo coeficiente que meterla en la regresión completa.
    """
    return M - Q @ (Q.T @ M)


def adelante(X, y, nombres, dia, n_dias, L, max_k, forzadas=()):
    """
    Fuente: selección hacia adelante de SLDA, clase 5 (ahí con regsubsets);
    el criterio para parar es Bonferroni (Dunn, 1961). Ver docs/REFERENCIAS.md.

    Selección hacia adelante con el estadístico t de Driscoll-Kraay. X y y ya
    vienen sin el efecto de lo que se controla. Devuelve la lista de
    (nombre, t, p) y la base ortonormal de lo elegido.
    """
    X, y = X.copy(), y.copy()
    norma0 = np.sqrt((X * X).sum(0))
    restantes = list(range(X.shape[1]))
    elegidas, base = [], []

    def agregar(k, t, p):
        q = X[:, k] / np.linalg.norm(X[:, k])
        X[:] = X - np.outer(q, q @ X)
        y[:] = y - q * (q @ y)
        restantes.remove(k)
        elegidas.append((nombres[k], t, p))
        base.append(q)

    for nombre in forzadas:
        k = nombres.index(nombre)
        t = t_driscoll_kraay(X[:, [k]], y, dia, n_dias, L)[0]
        agregar(k, t, 2 * stats.norm.sf(abs(t)))

    while len(elegidas) < max_k + len(forzadas) and restantes:
        # lo que ya quedó explicado en 99% o más por lo elegido es redundante
        vivos = [k for k in restantes if np.linalg.norm(X[:, k]) > 0.1 * norma0[k]]
        if not vivos:
            break
        t = t_driscoll_kraay(X[:, vivos], y, dia, n_dias, L)
        j = int(np.argmax(np.abs(t)))
        p = 2 * stats.norm.sf(abs(t[j]))
        if p >= ALFA / len(vivos):
            break
        agregar(vivos[j], t[j], p)
    return elegidas, (np.column_stack(base) if base else np.zeros((len(y), 0)))


# ---------------------------------------------------------------------------
# Objetivo y calendario
# ---------------------------------------------------------------------------

def objetivos(lp):
    return pd.DataFrame({f"y_h{h}": lp.shift(-24 * h) - lp for h in HORIZONTES})


def calendario(indice):
    fechas = indice.get_level_values("fecha")
    festivos = holidays.Colombia(years=range(fechas.year.min(), fechas.year.max() + 2))
    cal = pd.DataFrame(index=indice)
    cal["dia_semana"] = fechas.dayofweek
    cal["mes"] = fechas.month
    cal["es_festivo"] = [int(f in festivos) for f in fechas]
    for h in HORIZONTES:
        obj = fechas + pd.Timedelta(days=h)
        cal[f"dia_semana_h{h}"] = obj.dayofweek
        cal[f"es_festivo_h{h}"] = [int(f in festivos) for f in obj]
    return cal.astype("int8")


def matriz_calendario(cal, horas, h):
    """Variables indicadoras del calendario para la regresión, con intercepto."""
    partes = [np.ones((len(cal), 1)),
              pd.get_dummies(horas, drop_first=True).to_numpy(float),
              pd.get_dummies(cal["dia_semana"], drop_first=True).to_numpy(float),
              pd.get_dummies(cal["mes"], drop_first=True).to_numpy(float),
              cal[["es_festivo", f"es_festivo_h{h}"]].to_numpy(float)]
    if h % 7:      # con h = 7 el día de la semana pronosticado es el mismo del día t
        partes.append(pd.get_dummies(cal[f"dia_semana_h{h}"], drop_first=True).to_numpy(float))
    return np.hstack(partes)


def bloque(fechas):
    return np.select(
        [fechas <= FIN_SELECCION, fechas <= FIN_VALIDACION, fechas <= FIN_PRUEBA_A],
        ["seleccion", "validacion", "prueba_A"], "prueba_B")


# ---------------------------------------------------------------------------
# Selección
# ---------------------------------------------------------------------------

def seleccionar(cand, Y, cal):
    """Pasos 2 a 4 para cada horizonte. Devuelve (por_columna, por_variable)."""
    fechas = Y.index.get_level_values("fecha")
    base = (fechas >= INICIO) & cand["lp"]["lp_l0h"].notna().to_numpy()
    nombres = {n: list(df.columns) for n, df in cand.items()}
    exogenas = [n for n in cand if n != "lp"]
    cache = {}

    def filas(h):
        """
        Las filas de la ventana de selección cuyo objetivo no sale de 2019. Los
        siete horizontes cortos usan las mismas filas; 14 y 30 días cortan antes.
        """
        tope = 7 if h <= 7 else h
        if tope not in cache:
            ys = [f"y_h{k}" for k in CORTOS] + ([f"y_h{h}"] if h > 7 else [])
            en = (base & (fechas <= FIN_SELECCION - pd.Timedelta(days=tope))
                  & Y[ys].notna().all(axis=1).to_numpy())
            dia = (fechas[en] - fechas[en].min()).days.to_numpy()
            z = {n: puntajes_normales(df.to_numpy()[en]) for n, df in cand.items()}
            print(f"   filas para h hasta {tope}: {en.sum():,} ({len(np.unique(dia)):,} días)")
            cache[tope] = (en, dia, dia.max() + 1, Y.index.get_level_values("hora")[en], cal[en], z)
        return cache[tope]

    por_col, por_var = [], []
    for h in HORIZONTES:
        en, dia, n_dias, horas, cal_en, z = filas(h)
        L = h - 1 + 7
        y = puntajes_normales(Y[f"y_h{h}"].to_numpy()[en][:, None])[:, 0]
        Qc, _ = np.linalg.qr(matriz_calendario(cal_en, horas, h))
        y_c = quitar(Qc, y)

        # paso 2: el precio, con el precio del día t siempre adentro (es la base del objetivo)
        eleg, Qp = adelante(quitar(Qc, z["lp"]), y_c, nombres["lp"], dia, n_dias, L,
                            MAX_REZAGOS_PRECIO, forzadas=("lp_l0h",))
        for orden, (c, t, pv) in enumerate(eleg, 1):
            por_col.append(dict(columna=c, variable="lp", h=h, orden=orden, t=t, p=pv, entra=True))
        Q0 = np.hstack([Qc, Qp])
        y0 = quitar(Qp, y_c)

        # paso 3: los rezagos de cada variable, condicional al calendario y al precio
        # Fuente: causalidad de Granger (1969)
        bloques = {}
        for nombre in exogenas:
            el, _ = adelante(quitar(Q0, z[nombre]), y0, nombres[nombre], dia, n_dias, L, MAX_REZAGOS)
            if el:
                bloques[nombre] = el

        # paso 4: variables por bloques, con Wald conjunto
        Xb = {n: quitar(Q0, z[n][:, [nombres[n].index(c) for c, _, _ in el]])
              for n, el in bloques.items()}
        yb = y0.copy()
        restantes, orden = list(bloques), 0
        while restantes:
            prueba = {n: wald_driscoll_kraay(Xb[n], yb, dia, n_dias, L) for n in restantes}
            mejor = min(prueba, key=lambda n: prueba[n][1])
            W, pv = prueba[mejor]
            if pv >= ALFA / len(restantes):
                break
            orden += 1
            por_var.append(dict(variable=mejor, h=h, orden=orden, wald=W, p=pv))
            Qn, _ = np.linalg.qr(Xb[mejor])
            restantes.remove(mejor)
            for n in restantes:
                Xb[n] = quitar(Qn, Xb[n])
            yb = quitar(Qn, yb)

        entran = {r["variable"] for r in por_var if r["h"] == h}
        for nombre, el in bloques.items():
            for k, (c, t, pv) in enumerate(el, 1):
                por_col.append(dict(columna=c, variable=nombre, h=h, orden=k, t=t, p=pv,
                                    entra=nombre in entran))
        print(f"   h={h}: {len(eleg)} rezagos del precio, {len(bloques)} variables con algún "
              f"rezago significativo, {len(entran)} entran por Wald")
    return pd.DataFrame(por_col), pd.DataFrame(por_var)


# ---------------------------------------------------------------------------
# Columnas finales
# ---------------------------------------------------------------------------

def nombre_final(c):
    """Para el precio, los rezagos van como diferencia frente al precio del día t (dlp_...)."""
    if c == "lp_l0h":
        return "lp"
    return "d" + c if c.startswith("lp_") else c


def construir(cand, elegidas):
    out = {}
    lp = cand["lp"]["lp_l0h"]
    for c in elegidas:
        var = "lp" if c.startswith("lp_") else next(n for n in cand if n != "lp" and c in cand[n])
        serie = cand[var][c]
        if var == "lp" and c != "lp_l0h":
            serie = lp - serie
        out[nombre_final(c)] = serie
    return pd.DataFrame(out).astype("float32")


# ---------------------------------------------------------------------------
# Prueba de fuga
# ---------------------------------------------------------------------------

def comprobar_sin_fuga(crudo, trans, elegidas, X):
    """
    Altera todos los datos después del día D y reconstruye las columnas
    elegidas. Las de los días <= D no pueden cambiar, salvo las *_manana del
    día D.
    """
    D = pd.Timestamp("2021-06-15")
    fechas = crudo.index.get_level_values("fecha")
    num = [c for c in crudo.columns if c not in ("dia_semana", "es_festivo")]
    alterado = crudo.copy()
    alterado.loc[fechas > D, num] = alterado.loc[fechas > D, num] * 1.7 + 3
    Xb = construir(candidatos(preparar(alterado), trans), elegidas)
    hasta = X.index.get_level_values("fecha") <= D
    a, b = X[hasta], Xb[hasta]
    dif = (a != b) & ~(a.isna() & b.isna())
    cols = sorted(dif.columns[dif.any()])
    filas = dif.any(axis=1)
    assert all(c.endswith("_manana") for c in cols), f"fuga en {cols}"
    assert (filas[filas].index.get_level_values("fecha") == D).all(), "fuga en días anteriores a D"
    print(f"   sin fuga: al alterar todo lo posterior al {D.date()} solo cambian "
          f"{len(cols)} columnas *_manana, y solo en ese día")


# ---------------------------------------------------------------------------

def main():
    print("1. Lectura y limpieza")
    crudo = leer()
    p = preparar(crudo)
    lp = np.log(p["precio_bolsa"])
    Y = objetivos(lp)
    cal = calendario(p.index)

    print("2. Calidad y estacionariedad (ADF)")
    tabla_var, trans = calidad_y_transformacion(variables(p))
    n_nivel = sum(t == "nivel" for t in trans.values())
    print(f"   {len(tabla_var)} variables, {len(trans)} pasan la calidad: "
          f"{n_nivel} en nivel y {len(trans) - n_nivel} como desviación de 28 días")

    print("3. Selección de rezagos y de variables")
    cand = candidatos(p, trans)
    por_col, por_var = seleccionar(cand, Y, cal)

    entra = por_col[por_col["entra"]]
    elegidas = list(dict.fromkeys(entra["columna"]))
    X = construir(cand, elegidas)
    col_h = {h: [nombre_final(c) for c in entra.loc[entra["h"] == h, "columna"]] for h in HORIZONTES}

    print("4. Prueba de fuga")
    comprobar_sin_fuga(crudo, trans, elegidas, X)

    print("5. Tabla final")
    fechas = X.index.get_level_values("fecha")
    tabla = pd.concat([cal, X, Y.astype("float32")], axis=1)
    tabla.insert(0, "bloque", bloque(fechas))
    tabla.insert(0, "precio", p["precio_bolsa"].astype("float32"))
    tabla = tabla[(fechas >= INICIO) & p["precio_bolsa"].notna().to_numpy()].reset_index()
    tabla.to_csv(SALIDA, index=False, compression="gzip", float_format="%.6g")

    # por columna: en qué horizontes entra y con qué t
    por_col["columna_final"] = por_col["columna"].map(nombre_final)
    dic = (por_col[por_col["entra"]]
           .pivot_table(index=["columna_final", "variable"], columns="h", values="t", aggfunc="first"))
    dic.columns = [f"t_h{h}" for h in dic.columns]
    dic["horizontes"] = dic.notna().sum(axis=1)
    dic = dic.reset_index().rename(columns={"columna_final": "columna"})
    dic.sort_values(["variable", "horizontes"], ascending=[True, False]).round(2).to_csv(COLUMNAS, index=False)

    # por variable: orden de entrada en cada horizonte
    if len(por_var):
        orden = por_var.pivot_table(index="variable", columns="h", values="orden")
        orden.columns = [f"orden_h{h}" for h in orden.columns]
        tabla_var = tabla_var.join(orden)
    tabla_var["horizontes"] = tabla_var.filter(like="orden_h").notna().sum(axis=1)
    tabla_var.sort_values("horizontes", ascending=False).to_csv(VARIABLES, float_format="%.4g")

    print(f"\n{SALIDA.name}: {len(tabla):,} filas x {tabla.shape[1]} columnas, "
          f"{SALIDA.stat().st_size / 1e6:.1f} MB")
    print(f"   {X.shape[1]} características en total; por horizonte:",
          {h: len(c) for h, c in col_h.items()})


if __name__ == "__main__":
    main()
