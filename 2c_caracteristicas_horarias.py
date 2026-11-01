"""
Paso 2c: las características del panel horario.

    python 2c_caracteristicas_horarias.py

Toma el panel horario completo (paso 2b) y deja las variables base: una columna
por variable, ya transformada y sin rezagos. Las columnas derivadas (rezagos,
medias móviles, tendencia y variabilidad) las arma features.py cuando se
necesitan, con features.armar_todas() o features.armar().

Salidas, en paneles/:
    panel_caracteristicas.csv.gz          variables base, calendario y objetivos
    panel_caracteristicas_variables.csv   una fila por variable: grupo, tipo, de
                                          qué columnas sale, regla, faltantes, si
                                          se conoce de antemano, atraso extra y
                                          cuántas columnas derivadas tiene

Reglas
------
- Este paso no mira el objetivo ni hace pruebas estadísticas. Cada variable se
  transforma con una regla fija según lo que mide. La elección de variables
  queda para el paso 2d.
- Las cantidades que crecen con el sistema van como fracción. Las horarias, de
  la demanda o la generación de esa hora. Las diarias, de la media móvil de 7
  días de la demanda diaria, para que los domingos y festivos no metan ruido.
  Precios y ofertas en logaritmo; porcentajes, índices y clima, tal cual.
- Ninguna normalización usa promedios fijos de una ventana: todas miran solo
  hacia atrás.
- La fila (día t, hora H) se para al cierre del día t. Las variables que XM
  publica después que el precio entran con ese atraso adicional (ATRASO_EXTRA,
  medido en datos/sondeos/publicacion_metricas_horarias.csv).
- Filtro de calidad: queda fuera la variable con más de 1% de faltantes desde
  marzo de 2015, o sin variación.

Qué se tomó del plan de variables y qué se ajustó con los datos:
docs/PANEL_HORARIO.md.
"""

import time
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

import features as fe

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "paneles" / "panel_horario_completo.csv.gz"
SALIDA = BASE / "paneles" / "panel_caracteristicas.csv.gz"
VARIABLES = BASE / "paneles" / "panel_caracteristicas_variables.csv"

# de 1 a 7 días, dos semanas y un mes
HORIZONTES = [1, 2, 3, 4, 5, 6, 7, 14, 30]
INICIO = fe.INICIO_HORARIO
FIN_SELECCION = pd.Timestamp("2019-12-31")
FIN_VALIDACION = pd.Timestamp("2022-12-31")
FIN_PRUEBA_A = pd.Timestamp("2025-12-31")
MAX_FALTANTE = 0.01

# Días que cada columna se publica después del precio (que va a 2 días).
ATRASO_EXTRA = {
    # ofertas, curva de mérito e indicador de recurso marginal: unos 10 días
    "oferta_cap_total": 8, "cap_bajo_200": 8, "cap_bajo_500": 8,
    "oferta_marginal": 8, "escalon_siguiente": 8, "holgura_mw": 8,
    "margen_ofertado": 8,
    "marg_hidraulica": 8, "marg_termica": 8, "marg_gas": 8, "marg_carbon": 8,
    "marg_liquidos": 8,
    "oferta_p25": 8, "oferta_p50": 8, "oferta_p75": 8, "oferta_min": 8,
    "oferta_max": 8, "oferta_dispersion": 8, "pendiente_curva": 8,
    "cap_bajo_100": 8, "cap_bajo_300": 8, "cap_bajo_1000": 8,
    # contratos, pérdidas, restricciones aliviadas e intercambios con Ecuador: 5 días
    "compras_contrato": 3, "precio_prom_contrato": 3, "precio_cont_no_regu": 3,
    "perdidas_energia": 3, "restricciones": 3, "compras_tie": 3,
}

LLUVIA = ["lluvia_sistema", "lluvia_sistema_acum3", "lluvia_sistema_acum7",
          "lluvia_sistema_acum15", "lluvia_sistema_acum30", "lluvia_sistema_acum60",
          "lluvia_sistema_acum90", "lluvia_anomalia", "lluvia_anom_acum30",
          "lluvia_razon30", "lluvia_anom_acum90", "lluvia_razon90",
          "lluvia_penol_acum30", "lluvia_penol_anom30", "lluvia_bogota_acum30",
          "lluvia_bogota_anom30", "lluvia_guavio_acum30", "lluvia_guavio_anom30",
          "lluvia_quimbo_acum30", "lluvia_quimbo_anom30", "lluvia_gradiente_ns"]
NINO = ["nino12_anom", "nino3_anom", "nino34_anom", "nino4_anom", "nino12_tend4s",
        "nino12_tend12s", "nino34_tend4s", "nino34_tend12s", "nino_gradiente_costa",
        "oni", "roni"]
IDEAM = ["pred_lluvia_andina", "pred_lluvia_caribe", "pred_lluvia_pacifica",
         "pred_lluvia_orinoquia", "pred_lluvia_amazonia", "pred_deficit",
         "pred_prob_max", "pred_enos"]


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
    """Rellena huecos (solo hacia atrás) y aplica el atraso de publicación."""
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

def log_pos(s):
    """Logaritmo para precios que a veces valen 0 (el costo marginal, unas pocas horas)."""
    return np.log(s.clip(lower=1.0))


def a_horas(diaria, indice):
    """Una serie por día, repetida en las 24 horas de su día."""
    return pd.Series(diaria.reindex(indice.get_level_values("fecha")).to_numpy(), index=indice)


def suma_dia(s):
    """Total de las 24 horas del día de la fila; vacío si el día no tiene datos."""
    return a_horas(s.groupby(level="fecha").sum(min_count=1), s.index)


def media_dias(s, d):
    """Media de los últimos d días (con el día t) de una serie que vale lo mismo en todo el día."""
    diaria = s.groupby(level="fecha").first()
    return a_horas(diaria.rolling(d, min_periods=int(np.ceil(0.75 * d))).mean(), s.index)


def evento(s, hay_dia):
    """En un día con datos, el hueco de una serie de eventos es un 0 (no pasó)."""
    return s.mask(hay_dia & s.isna(), 0.0)


# ---------------------------------------------------------------------------
# Variables base
# ---------------------------------------------------------------------------

def variables_base(p):
    """
    Lista de variables base: cada una es un diccionario con la serie y lo que
    va al diccionario de salida (grupo, tipo, de qué columnas sale y regla).
    """
    v = []

    def agregar(nombre, serie, tipo, grupo, fuente, regla):
        v.append(dict(variable=nombre, serie=serie.replace([np.inf, -np.inf], np.nan),
                      tipo=tipo, grupo=grupo, fuente=fuente, regla=regla))

    def h(nombre, serie, grupo, fuente, regla):
        agregar(nombre, serie, "horaria", grupo, fuente, regla)

    def d(nombre, serie, grupo, fuente, regla):
        agregar(nombre, serie, "diaria", grupo, fuente, regla)

    def r(a, b):
        return a / b.replace(0, np.nan)

    dem, gen, pron = p["demanda_comercial"], p["gen_total"], p["pron_demanda_cnd"]
    lp = np.log(p["precio_bolsa"])
    agregar("lp", lp, "precio", "precio", "precio_bolsa", "log")

    # --- horarias: las 41 que ya se usaban, con la misma definición
    h("demanda", np.log(dem), "demanda", "demanda_comercial", "log")
    h("pron_demanda", np.log(pron), "demanda", "pron_demanda_cnd", "log")
    h("error_pron_demanda", r(p["error_pron_demanda"], pron), "demanda",
      "error_pron_demanda, pron_demanda_cnd", "error / pronóstico")
    h("dem_no_regulada_frac", r(p["demanda_no_regulada"], dem), "demanda",
      "demanda_no_regulada, demanda_comercial", "fracción de la demanda")
    h("margen_declarado", p["margen_declarado"], "disponibilidad", "margen_declarado",
      "disponibilidad / demanda")
    h("margen_decl_pron", r(p["disp_declarada"], pron), "disponibilidad",
      "disp_declarada, pron_demanda_cnd", "disponibilidad / demanda pronosticada")
    h("disp_real_vs_decl", r(p["disp_real"], p["disp_declarada"]), "disponibilidad",
      "disp_real, disp_declarada", "real / declarada")
    h("disp_termica_frac", r(p["disp_decl_termica"], p["disp_declarada"]), "disponibilidad",
      "disp_decl_termica, disp_declarada", "fracción térmica de la disponibilidad")
    for t in ("termica", "hidraulica", "fncer"):
        h(f"frac_{t}", p[f"frac_{t}"], "generacion", f"frac_{t}", "fracción de la generación")
    for n, col in [("gen_seguridad_rel", "gen_seguridad"), ("gen_fuera_merito_rel", "gen_fuera_merito"),
                   ("gen_restricciones_rel", "gen_restricciones")]:
        h(n, r(p[col], gen), "generacion", f"{col}, gen_total", "fracción de la generación")
    h("redespacho_vs_programa", r(p["gen_prog_redespacho"] - p["gen_programada"], dem), "generacion",
      "gen_prog_redespacho, gen_programada, demanda_comercial", "(redespacho - programa) / demanda")
    h("gen_ideal_termica_frac", r(p["gen_ideal_termica"], p["gen_ideal_total"]), "generacion",
      "gen_ideal_termica, gen_ideal_total", "fracción térmica del despacho ideal")
    h("consumo_por_mwh_termico", r(p["consumo_combustible"], p["gen_termica"]), "generacion",
      "consumo_combustible, gen_termica", "MBTU por MWh térmico")
    h("co2_por_mwh", r(p["co2_total"], gen), "generacion", "co2_total, gen_total", "toneladas por MWh")
    for c in ("gas", "carbon", "liquidos"):
        h(f"co2_{c}_frac", r(p[f"co2_{c}"], p["co2_total"]), "generacion",
          f"co2_{c}, co2_total", "fracción del CO2")
    for n, col in [("restricciones_rel", "restricciones"),
                   ("restricciones_sin_aliv_rel", "restricciones_sin_aliv"),
                   ("perdidas_rel", "perdidas_energia")]:
        h(n, r(p[col], dem), "red_y_contratos", f"{col}, demanda_comercial", "sobre la demanda")
    h("intercambio_neto_rel", r(p["importaciones"] - p["exportaciones"], dem), "red_y_contratos",
      "importaciones, exportaciones, demanda_comercial", "(importaciones - exportaciones) / demanda")
    h("contrato_frac", r(p["compras_contrato"], dem), "red_y_contratos",
      "compras_contrato, demanda_comercial", "fracción de la demanda")
    h("precio_contrato", log_pos(p["precio_prom_contrato"]), "red_y_contratos",
      "precio_prom_contrato", "log")
    h("precio_contrato_no_reg", log_pos(p["precio_cont_no_regu"]), "red_y_contratos",
      "precio_cont_no_regu", "log")
    h("cmg_despacho", log_pos(p["cmg_despacho"]), "costo_marginal", "cmg_despacho", "log")
    h("cmg_redespacho", log_pos(p["cmg_redespacho"]), "costo_marginal", "cmg_redespacho", "log")
    h("ajuste_cmg", log_pos(p["cmg_redespacho"]) - log_pos(p["cmg_despacho"]), "costo_marginal",
      "cmg_redespacho, cmg_despacho", "log(redespacho) - log(despacho)")
    h("oferta_marginal", log_pos(p["oferta_marginal"]), "curva_de_merito", "oferta_marginal", "log")
    h("margen_ofertado", p["margen_ofertado"], "curva_de_merito", "margen_ofertado",
      "capacidad ofertada / demanda")
    for n, col in [("cap_bajo_200_rel", "cap_bajo_200"), ("cap_bajo_500_rel", "cap_bajo_500"),
                   ("holgura_rel", "holgura_mw")]:
        h(n, r(p[col], dem), "curva_de_merito", f"{col}, demanda_comercial", "sobre la demanda")
    h("escalon_siguiente", np.log1p(p["escalon_siguiente"].clip(lower=0)), "curva_de_merito",
      "escalon_siguiente", "log(1 + x)")
    for t in ("termica", "gas", "carbon", "liquidos"):
        h(f"marg_{t}", p[f"marg_{t}"], "planta_marginal", f"marg_{t}", "1 si fijó el precio")

    # --- horarias nuevas (plan de variables)
    h("error_cmg_despacho", lp - log_pos(p["cmg_despacho"]), "interaccion",
      "precio_bolsa, cmg_despacho", "lp - log(costo marginal programado): el error del operador")
    h("brecha_escasez", lp - log_pos(p["precio_escasez"]), "interaccion",
      "precio_bolsa, precio_escasez", "lp - log(precio de escasez): distancia al techo")
    h("presion_hidro_horaria", r(dem, p["aportes_por_rio"] / 1000 / 24), "interaccion",
      "demanda_comercial, aportes_por_rio", "demanda de la hora / aportes del día por hora")

    # --- diarias. Para normalizarlas: la demanda y la generación del día (GWh)
    dem_dia = suma_dia(dem) / 1000
    dem7 = media_dias(dem_dia, 7)
    gen_dia = suma_dia(gen) / 1000
    hay_hidro = p["volumen_util_pct"].notna()
    hay_gen = gen_dia.notna()
    sobre_dem7 = "sobre la media de 7 días de la demanda diaria"

    def gwh(col):
        return p[col] / 1e6                                          # kWh -> GWh

    # aportes
    for c in ("aportes_pct_sistema", "aportes_pct_rio"):
        d(c, p[c], "aportes", c, "porcentaje, tal cual")
    d("aportes_caudal_pct", r(p["aportes_caudal"], p["aportes_caudal_medio"]), "aportes",
      "aportes_caudal, aportes_caudal_medio", "caudal / caudal medio histórico de XM")
    d("aportes_media_hist", gwh("aportes_media_hist"), "aportes", "aportes_media_hist",
      "media histórica de XM, en GWh (referencia estacional)")
    for c in ("hhi_aportes_rios", "aportes_top3_pct", "n_rios_aportando"):
        d(c, p[c], "aportes", c, "tal cual")

    # embalses
    for c in ("volumen_util_pct", "volumen_util_pct_emb", "vol_pct_penol", "vol_pct_agregado_bogota",
              "vol_pct_guavio", "vol_pct_esmeralda", "vol_pct_el_quimbo", "hhi_volumen_embalses"):
        d(c, p[c], "embalses", c, "tal cual")
    d("dias_autonomia", gwh("volumen_por_embalse") / dem7, "embalses",
      "volumen_por_embalse, demanda_comercial", "volumen útil (GWh) " + sobre_dem7)
    d("capacidad_util_dias", gwh("capacidad_por_embalse") / dem7, "embalses",
      "capacidad_por_embalse, demanda_comercial", "capacidad útil (GWh) " + sobre_dem7)
    d("vertimientos_rel", evento(gwh("vertimientos"), hay_hidro) / dem7, "embalses",
      "vertimientos, demanda_comercial", "vertimientos (GWh, 0 si no hubo) " + sobre_dem7)

    # clima e IDEAM
    for c in LLUVIA:
        d(c, p[c], "lluvia", c, "tal cual")
    for c in NINO:
        d(c, p[c], "el_nino", c, "tal cual")
    for c in IDEAM:
        d(c, p[c], "ideam", c, "tal cual")

    # mezcla por planta (generación del día en GWh)
    for c in ("gen_gas", "gen_carbon", "gen_liquidos", "gen_biomasa", "gen_no_despachado", "gen_filo_agua"):
        d(f"frac_{c}", evento(p[c], hay_gen) / gen_dia, "mezcla_por_planta",
          f"{c}, gen_total", "fracción de la generación del día (0 si no hubo)")
    for c in ("frac_gas_en_termica", "frac_despacho_central", "frac_filo_en_hidro",
              "hhi_generacion", "gen_top5_pct", "n_plantas_activas"):
        d(c, p[c], "mezcla_por_planta", c, "tal cual")
    d("disp_decl_despacho_central_rel", p["disp_decl_despacho_central"] / dem7, "mezcla_por_planta",
      "disp_decl_despacho_central, demanda_comercial", "disponibilidad (GWh) " + sobre_dem7)

    # curva de ofertas del día
    for c in ("oferta_p25", "oferta_p50", "oferta_p75", "oferta_min", "oferta_max"):
        d(c, log_pos(p[c]), "curva_del_dia", c, "log")
    for c in ("oferta_dispersion", "pendiente_curva"):
        d(c, p[c], "curva_del_dia", c, "tal cual")
    for c in ("cap_bajo_100", "cap_bajo_300", "cap_bajo_1000"):
        d(f"{c}_rel", p[c] / dem7, "curva_del_dia", f"{c}, demanda_comercial", "GWh " + sobre_dem7)

    # sistema y regulación
    d("capacidad_efectiva_rel", p["capacidad_efectiva"] * 24 / 1e6 / dem7, "sistema",
      "capacidad_efectiva, demanda_comercial", "capacidad (kW x 24 h, en GWh) " + sobre_dem7)
    d("enficc_rel", gwh("enficc") / dem7, "sistema", "enficc, demanda_comercial", "GWh " + sobre_dem7)
    d("oblig_energia_firme_rel", gwh("oblig_energia_firme") / dem7, "sistema",
      "oblig_energia_firme, demanda_comercial", "GWh " + sobre_dem7)
    d("margen_reserva", p["margen_reserva"], "sistema", "margen_reserva", "tal cual")
    d("precio_cargo_conf", log_pos(p["precio_cargo_conf"]), "sistema", "precio_cargo_conf", "log")
    d("precio_escasez", log_pos(p["precio_escasez"]), "sistema", "precio_escasez", "log")
    d("trm", np.log(p["trm"]), "sistema", "trm", "log")
    d("demanda_max_potencia_rel", (p["demanda_max_potencia"] / 1000) / (dem7 * 1000 / 24), "sistema",
      "demanda_max_potencia, demanda_comercial", "potencia máxima (MW) / demanda media por hora")
    for c in ("demanda_no_atendida", "dem_no_atendida_nop"):
        d(f"{c}_rel", evento(gwh(c), hay_hidro) / dem7, "sistema", f"{c}, demanda_comercial",
          "GWh (0 si no hubo) " + sobre_dem7)
    return v


# ---------------------------------------------------------------------------
# Calendario, objetivos y bloque
# ---------------------------------------------------------------------------

def ciclico(valor, periodo):
    """Seno y coseno: así la hora 24 queda junto a la 1 y diciembre junto a enero."""
    angulo = 2 * np.pi * np.asarray(valor, dtype=float) / periodo
    return np.sin(angulo), np.cos(angulo)


def calendario(indice):
    """
    Calendario del día t, tal cual y cíclico, y el del día que se pronostica en
    cada horizonte. Se conoce de antemano. Fuente de la forma cíclica: Galli,
    Section-15-Date-Time-Features, 03-periodic-features.ipynb.
    """
    fechas = indice.get_level_values("fecha")
    horas = indice.get_level_values("hora")
    festivos = holidays.Colombia(years=range(fechas.year.min(), fechas.year.max() + 2))
    cal = pd.DataFrame(index=indice)
    cal["dia_semana"] = fechas.dayofweek
    cal["mes"] = fechas.month
    cal["es_festivo"] = [int(f in festivos) for f in fechas]
    cal["hora_sin"], cal["hora_cos"] = ciclico(horas - 1, 24)
    cal["dia_semana_sin"], cal["dia_semana_cos"] = ciclico(fechas.dayofweek, 7)
    cal["dia_ano_sin"], cal["dia_ano_cos"] = ciclico(fechas.dayofyear - 1, 365.25)
    cal["mes_sin"], cal["mes_cos"] = ciclico(fechas.month - 1, 12)
    for h in HORIZONTES:
        objetivo = fechas.shift(h, freq="D")
        cal[f"dia_semana_h{h}"] = objetivo.dayofweek
        cal[f"es_festivo_h{h}"] = [int(f in festivos) for f in objetivo]
        cal[f"dia_semana_h{h}_sin"], cal[f"dia_semana_h{h}_cos"] = ciclico(objetivo.dayofweek, 7)
    return cal


def objetivos(lp):
    """y_h = log P(t+h, H) - log P(t, H)."""
    return pd.DataFrame({f"y_h{h}": lp.shift(-24 * h) - lp for h in HORIZONTES})


def bloque(fechas):
    return np.select(
        [fechas <= FIN_SELECCION, fechas <= FIN_VALIDACION, fechas <= FIN_PRUEBA_A],
        ["seleccion", "validacion", "prueba_A"], "prueba_B")


# ---------------------------------------------------------------------------
# Armado del panel
# ---------------------------------------------------------------------------

def armar_base(p, vars_, entran):
    """Columnas fijas (identificación, calendario, objetivos) y las variables base que entran."""
    lp = np.log(p["precio_bolsa"])
    fijas = pd.DataFrame({"bloque": bloque(p.index.get_level_values("fecha")),
                          "precio": p["precio_bolsa"], "lp": lp}, index=p.index)
    base = pd.concat([fijas, calendario(p.index), objetivos(lp)], axis=1)
    serie = {x["variable"]: x["serie"] for x in vars_}
    return pd.concat([base, pd.DataFrame({n: serie[n] for n in entran if n != "lp"})], axis=1)


def calidad(vars_, p):
    """Faltantes y variación de cada variable desde marzo de 2015 hasta el último precio."""
    fechas = p.index.get_level_values("fecha")
    ultimo = p["precio_bolsa"].dropna().index.get_level_values("fecha").max()
    ventana = (fechas >= INICIO) & (fechas <= ultimo)
    filas = []
    for x in vars_:
        s = x["serie"][ventana]
        falt = float(s.isna().mean())
        quieta = bool(s.nunique() <= 1)
        motivo = ("más de 1% de faltantes" if falt > MAX_FALTANTE else
                  "sin variación" if quieta else "")
        fuente = [c.strip() for c in x["fuente"].split(",")]
        filas.append(dict(variable=x["variable"], grupo=x["grupo"], tipo=x["tipo"],
                          fuente=x["fuente"], regla=x["regla"],
                          faltante_pct=round(100 * falt, 3), entra=motivo == "",
                          motivo=motivo or "entra",
                          de_antemano=x["variable"] in fe.DE_ANTEMANO,
                          atraso_extra_dias=max(ATRASO_EXTRA.get(c, 0) for c in fuente)))
    return pd.DataFrame(filas).set_index("variable")


def contar_columnas(info, columnas):
    """Cuántas columnas derivadas le tocan a cada variable."""
    cuenta = dict.fromkeys(info.index, 0)
    for c in columnas:
        v = fe.variable_de(c, info)
        if v is not None:
            cuenta[v] += 1
    return pd.Series(cuenta)


# ---------------------------------------------------------------------------
# Prueba de fuga, sobre todo el flujo
# ---------------------------------------------------------------------------

def comprobar_sin_fuga(crudo, info, D=pd.Timestamp("2021-06-15")):
    """
    Altera los datos crudos posteriores al día D y vuelve a correr todo: el
    relleno, las variables base (con sus normalizaciones móviles) y el catálogo
    de columnas derivadas. Nada de los días <= D puede cambiar, salvo las
    columnas _manana del día D, que usan lo que se decide para D+1.

    Corre sobre una ventana de 400 días antes de D y 60 después, que cubre todas
    las ventanas del catálogo (la más larga es de 30 días) sin tener en memoria
    el catálogo completo dos veces. Devuelve las columnas derivadas de la ventana.
    """
    fechas = crudo.index.get_level_values("fecha")
    ventana = crudo[(fechas > D - pd.offsets.Day(400)) & (fechas <= D + pd.offsets.Day(60))]
    despues = ventana.index.get_level_values("fecha") > D
    num = [c for c in ventana.columns if c not in ("dia_semana", "es_festivo")]
    alterado = ventana.copy()
    alterado.loc[despues, num] = alterado.loc[despues, num] * 1.7 + 3

    def todo(crudo_):
        p_ = preparar(crudo_)
        base_ = armar_base(p_, variables_base(p_), list(info.index))
        return fe.armar_todas(base_, info, con_fijas=False)

    X, X2 = todo(ventana), todo(alterado)
    hasta = X.index.get_level_values("fecha") <= D
    a, b = X[hasta].to_numpy(), X2[hasta].to_numpy()
    dif = (a != b) & ~(np.isnan(a) & np.isnan(b))
    cols = sorted(X.columns[dif.any(axis=0)])
    dias = set(X.index[hasta][dif.any(axis=1)].get_level_values("fecha"))
    assert all(c.endswith("_manana") for c in cols), f"fuga en {cols}"
    assert dias <= {D}, f"fuga en días anteriores a {D.date()}: {sorted(dias)[:5]}"
    print(f"   sin fuga: al alterar todo lo posterior al {D.date()} solo cambian "
          f"{len(cols)} columnas ({', '.join(cols)}), y solo en ese día")
    return X


# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print("1. Lectura y limpieza")
    crudo = leer()
    p = preparar(crudo)

    print("2. Variables base")
    vars_ = variables_base(p)
    info = calidad(vars_, p)
    entran = info.index[info["entra"]].tolist()
    por_tipo = info.groupby("tipo")["entra"].agg(["size", "sum"])
    print(f"   {len(info)} variables: " + ", ".join(
        f"{t} {int(f['sum'])} de {int(f['size'])}" for t, f in por_tipo.iterrows()))
    for v, f in info[~info["entra"]].iterrows():
        print(f"   fuera: {v} ({f['motivo']}, {f['faltante_pct']}% de faltantes)")

    print("3. Panel de características")
    base = armar_base(p, vars_, entran)

    print("4. Prueba de fuga y columnas derivadas")
    info_entran = info[info["entra"]]
    X = comprobar_sin_fuga(crudo, info_entran)
    cuenta = contar_columnas(info_entran, X.columns)
    info["columnas_derivadas"] = cuenta.reindex(info.index).fillna(0).astype(int)

    print("5. Guardar")
    base.reset_index().to_csv(SALIDA, index=False, compression="gzip", float_format="%.6g")
    info.to_csv(VARIABLES)

    fijas = [c for c in base.columns if c == "lp" or c not in info_entran.index]
    filas = int(fe._filas(base, INICIO).sum())
    print(f"\n{SALIDA.name}: {base.shape[0]:,} filas x {base.shape[1] + 2} columnas "
          f"({len(fijas) + 2} fijas, con fecha y hora, y {base.shape[1] - len(fijas)} variables base), "
          f"{SALIDA.stat().st_size / 1e6:.1f} MB")
    print(f"armar_todas() dará {filas:,} filas x {X.shape[1] + len(fijas) + 2} columnas "
          f"({X.shape[1]} derivadas, unos {filas * X.shape[1] * 4 / 1e6:.0f} MB en float32) "
          f"[{time.time() - t0:.0f} s en total]")


if __name__ == "__main__":
    main()
