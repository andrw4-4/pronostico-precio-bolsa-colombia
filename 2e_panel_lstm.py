"""
Paso 2e: el panel para la LSTM.

    python 2e_panel_lstm.py                  # el precio llega con 2 días de atraso
    ATRASO_PRECIO=3 python 2e_panel_lstm.py  # o con 3

Usa las mismas variables base del paso 2c, con una regla de información más
fiel a cómo se publican los datos. En el 2c todo se para en el día t del último
precio conocido, y las variables que salen después del precio entran con su
atraso extra. Pero el pronóstico se hace en el día R = t + D, cuando el precio
ya va D días atrasado, y hay datos que en R están más al día que el precio: el
despacho programado de R sale la víspera y los aportes de ayer ya están
publicados. El 2c los dejaba en t y perdía esos días.

Regla: la fila (día t, hora H) es lo que se sabe en R = t + D. Cada columna
cruda c trae el valor del día R - L(c), donde L(c) es su atraso de publicación
medido en los sondeos de datos/sondeos (9 y 10 de octubre de 2026; se toma el
mayor de los dos). El objetivo es la semana que empieza mañana:

    y_h = log P(t+h, H) - log P(t, H),     h = D+1 ... D+7

Con D = 2 son los mismos h = 3 a 9 de XGBoost y SARIMAX, en las mismas filas.

Salidas, en paneles/ (con D = 3 llevan el sufijo _atraso3):
    panel_lstm.csv.gz             variables base alineadas, calendario de t y
                                  de los 7 días objetivo, y objetivos
    panel_lstm_variables.csv      una fila por variable: grupo, fuente, regla,
                                  días de atraso frente a R y frente al precio,
                                  faltantes y si entra

Este paso no mira el objetivo ni elige variables.
"""

import importlib.util
import os
import time
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("paso_2c", BASE / "2c_caracteristicas_horarias.py")
c2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c2)

ATRASO_PRECIO = int(os.environ.get("ATRASO_PRECIO", "2"))
SUFIJO = "" if ATRASO_PRECIO == 2 else f"_atraso{ATRASO_PRECIO}"
SALIDA = BASE / "paneles" / f"panel_lstm{SUFIJO}.csv.gz"
VARIABLES = BASE / "paneles" / f"panel_lstm_variables{SUFIJO}.csv"
DIAS_OBJETIVO = range(1, 8)                 # de mañana (R+1) a R+7
INICIO = c2.INICIO

# ---------------------------------------------------------------------------
# Atraso de publicación de cada columna cruda, en días antes de R
# ---------------------------------------------------------------------------
#
# Medido en datos/sondeos/auditoria_cobertura.csv (descarga del 9 de octubre,
# entre las 15:28 y las 16:46) y publicacion_metricas_horarias.csv (10 de
# octubre, 10:14). El 9 el precio iba 3 días atrás y el 10 iba 2; las demás
# series se miden contra R, no contra el precio.

# Lo que XM publica con el precio (2 o 3 días): demanda, generación real y lo
# que sale de ella.
COMO_EL_PRECIO = [
    "precio_bolsa", "demanda_comercial", "demanda_regulada", "demanda_no_regulada",
    "demanda_real", "demanda_real_reg", "demanda_real_no_reg", "disp_comercial",
    "gen_total", "gen_seguridad", "gen_fuera_merito", "consumo_combustible",
    "importaciones", "exportaciones", "gen_hidraulica", "gen_termica", "gen_solar",
    "gen_eolica", "gen_cogenerador", "frac_hidraulica", "frac_termica", "frac_fncer",
    "margen_declarado", "gen_ideal_hidraulica", "gen_ideal_termica", "gen_ideal_total",
    "co2_gas", "co2_carbon", "co2_liquidos", "co2_total", "gen_restricciones",
    "gen_gas", "gen_carbon", "gen_liquidos", "gen_biomasa", "frac_gas_en_termica",
    "gen_despacho_central", "gen_no_despachado", "frac_despacho_central",
    "gen_filo_agua", "frac_filo_en_hidro", "hhi_generacion", "gen_top5_pct",
    "n_plantas_activas", "enficc", "precio_escasez", "precio_esca_act",
    "precio_esca_inf", "precio_esca_marg", "precio_esca_sup",
]
ATRASO = {
    # el despacho programado y la disponibilidad declarada de R salen la víspera
    "cmg_despacho": 0, "gen_programada": 0, "disp_declarada": 0,
    "disp_decl_hidraulica": 0, "disp_decl_termica": 0, "disp_decl_despacho_central": 0,
    "oblig_energia_firme": 0,
    # el sondeo los muestra el mismo día, pero cambian durante el día: se usa
    # el de ayer, que ya está completo
    "gen_prog_redespacho": 1, "cmg_redespacho": 1, "ajuste_cmg": 1, "disp_real": 1,
    "restricciones_sin_aliv": 1,
    # hidrología: el día anterior
    **dict.fromkeys([
        "aportes_caudal", "aportes_caudal_medio", "aportes_media_hist", "aportes_pct_rio",
        "aportes_pct_sistema", "aportes_por_rio", "capacidad_por_embalse",
        "descargas_embalse", "turbinado_embalse", "vertido_embalse", "vertimientos",
        "volumen_por_embalse", "volumen_util_pct", "volumen_util_pct_emb",
        "hhi_aportes_rios", "aportes_top3_pct", "n_rios_aportando", "vol_pct_penol",
        "vol_pct_agregado_bogota", "vol_pct_guavio", "vol_pct_esmeralda",
        "vol_pct_el_quimbo", "hhi_volumen_embalses"], 1),
    "capacidad_efectiva": 2, "dem_no_atendida_nop": 2, "margen_reserva": 2,
    "demanda_no_atendida": 4,
    # contratos, pérdidas, restricciones aliviadas, intercambio con Ecuador
    **dict.fromkeys([
        "restricciones", "perdidas_energia", "compras_tie", "compras_contrato",
        "precio_prom_contrato", "precio_cont_no_regu", "precio_cargo_conf"], 5),
    # ofertas, curva de mérito, planta marginal y el pronóstico de demanda de
    # SIMEM (que el 2c trataba como conocido la víspera)
    **dict.fromkeys([
        "oferta_cap_total", "cap_bajo_200", "cap_bajo_500", "oferta_marginal",
        "escalon_siguiente", "holgura_mw", "margen_ofertado", "marg_hidraulica",
        "marg_termica", "marg_gas", "marg_carbon", "marg_liquidos", "pron_demanda_cnd",
        "error_pron_demanda", "oferta_p25", "oferta_p50", "oferta_p75",
        "oferta_dispersion", "oferta_min", "oferta_max", "cap_bajo_100", "cap_bajo_300",
        "cap_bajo_1000", "pendiente_curva"], 10),
    # mensuales
    "cee": 9, "demanda_upme_alto": 9, "demanda_upme_bajo": 9, "demanda_upme_medio": 9,
    "cere": 39, "mc": 39, "demanda_max_potencia": 40,
    # El Niño, lluvia (ERA5), IDEAM y TRM: el paso 2 ya los fecha el día en que
    # se publican, así que el valor del día R se conoce en R
    **dict.fromkeys(c2.NINO + c2.LLUVIA + c2.IDEAM + [
        "trm", "alerta_niveles_bajos", "alerta_crecientes", "alerta_incendios",
        "alerta_deslizamientos", "lluvia_max_municipio"], 0),
}
CALENDARIO_CRUDO = ["dia_semana", "es_festivo"]


def atraso(col):
    """Días antes de R del último dato publicado de una columna cruda."""
    if col in COMO_EL_PRECIO:
        return ATRASO_PRECIO
    if col in ATRASO:
        return ATRASO[col]
    raise KeyError(f"{col} no tiene atraso de publicación asignado")


# ---------------------------------------------------------------------------
# Alineación
# ---------------------------------------------------------------------------

def rellenado(crudo):
    """Huecos sueltos con la misma hora del día anterior (hasta 3 días), por fecha del dato."""
    p0 = crudo.copy()
    for c in p0.columns:
        if c not in CALENDARIO_CRUDO and c != "precio_bolsa":
            p0[c] = c2.rellenar(p0[c])
    return p0


def en_fila(serie, dias):
    """Pone en la fila t el dato del día R - dias (R = t + D)."""
    return serie.shift(24 * (dias - ATRASO_PRECIO))


def alinear(p0):
    p = p0.copy()
    for c in p.columns:
        if c not in CALENDARIO_CRUDO:
            p[c] = en_fila(p0[c], atraso(c))
    return p


def variables(crudo):
    """
    Las variables base del 2c sobre las columnas alineadas, más los ajustes de
    las que mezclaban días distintos al alinear y tres nuevas.
    """
    p0 = rellenado(crudo)
    p = alinear(p0)
    vars_ = {x["variable"]: x for x in c2.variables_base(p)}

    def r(a, b):
        return a / b.replace(0, np.nan)

    def poner(nombre, serie, tipo, grupo, fuente, regla, dias):
        vars_[nombre] = dict(variable=nombre, serie=serie.replace([np.inf, -np.inf], np.nan),
                             tipo=tipo, grupo=grupo, fuente=fuente, regla=regla, dias=dias)

    lp = np.log(p0["precio_bolsa"])
    cmg = c2.log_pos(p0["cmg_despacho"])
    # En el 2c comparaban el mismo día; alineadas por separado quedarían de
    # días distintos, así que se arman con todas sus partes del mismo día.
    poner("error_cmg_despacho", lp - en_fila(cmg, ATRASO_PRECIO), "horaria", "interaccion",
          "precio_bolsa, cmg_despacho", "lp - log(costo marginal programado), ambos del día t",
          ATRASO_PRECIO)
    poner("ajuste_cmg", en_fila(c2.log_pos(p0["cmg_redespacho"]) - cmg, 1), "horaria",
          "costo_marginal", "cmg_redespacho, cmg_despacho",
          "log(redespacho) - log(despacho), ambos de ayer", 1)
    poner("redespacho_vs_programa",
          en_fila(r(p0["gen_prog_redespacho"] - p0["gen_programada"], p0["gen_programada"]), 1),
          "horaria", "generacion", "gen_prog_redespacho, gen_programada",
          "(redespacho - programa) / programa, ambos de ayer", 1)
    poner("disp_real_vs_decl", en_fila(r(p0["disp_real"], p0["disp_declarada"]), 1), "horaria",
          "disponibilidad", "disp_real, disp_declarada", "real / declarada, ambas de ayer", 1)
    # margen_decl_pron dividía la disponibilidad de hoy por un pronóstico de
    # demanda que SIMEM publica 10 días después; se reemplaza por la demanda
    # de la misma hora y el mismo día de la semana anterior, que ya se conoce
    vars_.pop("margen_decl_pron")
    dem_semana = en_fila(p0["demanda_comercial"], 7)
    poner("disp_decl_hoy_rel", r(en_fila(p0["disp_declarada"], 0), dem_semana), "horaria",
          "disponibilidad", "disp_declarada, demanda_comercial",
          "disponibilidad declarada de R / demanda de la misma hora de R - 7", 0)
    # nuevas: lo que el despacho de hoy dice del nivel del día
    poner("cmg_hoy_vs_precio", en_fila(cmg, 0) - lp, "horaria", "costo_marginal",
          "cmg_despacho, precio_bolsa", "log(costo marginal programado de R) - lp del día t", 0)
    poner("gen_programada_rel", r(en_fila(p0["gen_programada"], 0), dem_semana), "horaria",
          "demanda", "gen_programada, demanda_comercial",
          "generación programada de R / demanda de la misma hora de R - 7", 0)
    return list(vars_.values())


# ---------------------------------------------------------------------------
# Calendario, objetivos y diccionario
# ---------------------------------------------------------------------------

def calendario(indice):
    """El del día t (del 2c, sin sus columnas por horizonte) y el de los 7 días objetivo."""
    cal = c2.calendario(indice)
    cal = cal[[c for c in cal.columns if "_h" not in c]]
    fechas = indice.get_level_values("fecha")
    festivos = holidays.Colombia(years=range(fechas.year.min(), fechas.year.max() + 2))
    for k in DIAS_OBJETIVO:
        dia = fechas.shift(ATRASO_PRECIO + k, freq="D")
        cal[f"dia_semana_k{k}"] = dia.dayofweek
        cal[f"es_festivo_k{k}"] = [int(f in festivos) for f in dia]
    return cal


def objetivos(lp):
    hs = [ATRASO_PRECIO + k for k in DIAS_OBJETIVO]
    return pd.DataFrame({f"y_h{h}": lp.shift(-24 * h) - lp for h in hs})


def dias_de(x):
    """Días antes de R del dato más viejo que usa la variable."""
    if "dias" in x:
        return x["dias"]
    fuentes = [c.strip() for c in x["fuente"].split(",")]
    return max(atraso(c) for c in fuentes)


def diccionario(vars_, crudo):
    fechas = crudo.index.get_level_values("fecha")
    ultimo = crudo["precio_bolsa"].dropna().index.get_level_values("fecha").max()
    ventana = (fechas >= INICIO) & (fechas <= ultimo)
    filas = []
    for x in vars_:
        s = x["serie"][ventana]
        falt = float(s.isna().mean())
        motivo = ("más de 1% de faltantes" if falt > c2.MAX_FALTANTE else
                  "sin variación" if s.nunique() <= 1 else "entra")
        d = dias_de(x)
        filas.append(dict(variable=x["variable"], grupo=x["grupo"], tipo=x["tipo"],
                          fuente=x["fuente"], regla=x["regla"], dias_antes_de_R=d,
                          dias_frente_al_precio=d - ATRASO_PRECIO,
                          faltante_pct=round(100 * falt, 3), entra=motivo == "entra",
                          motivo=motivo))
    return pd.DataFrame(filas).set_index("variable")


def armar(crudo):
    vars_ = variables(crudo)
    info = diccionario(vars_, crudo)
    lp = np.log(crudo["precio_bolsa"])
    fijas = pd.DataFrame({"bloque": c2.bloque(crudo.index.get_level_values("fecha")),
                          "precio": crudo["precio_bolsa"], "lp": lp}, index=crudo.index)
    serie = {x["variable"]: x["serie"] for x in vars_}
    entran = [v for v in info.index[info["entra"]] if v != "lp"]
    panel = pd.concat([fijas, calendario(crudo.index), objetivos(lp),
                       pd.DataFrame({v: serie[v] for v in entran})], axis=1)
    return panel, info


# ---------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------

def comprobar_sin_fuga(crudo, info, t0=pd.Timestamp("2021-06-15")):
    """
    Para cada columna cruda se alteran los datos que todavía no se habían
    publicado en R0 = t0 + D (los del día R0 - L(c) en adelante, sin incluirlo)
    y se arma todo de nuevo. Ninguna fila hasta t0 puede cambiar.
    """
    fechas = crudo.index.get_level_values("fecha")
    ventana = crudo[(fechas > t0 - pd.offsets.Day(400)) & (fechas <= t0 + pd.offsets.Day(60))]
    f = ventana.index.get_level_values("fecha")
    r0 = t0 + pd.offsets.Day(ATRASO_PRECIO)
    alterado = ventana.copy()
    for c in alterado.columns:
        if c not in CALENDARIO_CRUDO:
            futuro = f > r0 - pd.offsets.Day(atraso(c))
            alterado.loc[futuro, c] = alterado.loc[futuro, c] * 1.7 + 3
    entran = [v for v in info.index[info["entra"]]]

    def base(crudo_):
        s = {x["variable"]: x["serie"] for x in variables(crudo_)}
        return pd.DataFrame({v: s[v] for v in entran})

    a, b = base(ventana), base(alterado)
    hasta = a.index.get_level_values("fecha") <= t0
    x, y = a[hasta].to_numpy(), b[hasta].to_numpy()
    dif = (x != y) & ~(np.isnan(x) & np.isnan(y))
    malas = sorted(a.columns[dif.any(axis=0)])
    assert not malas, f"fuga en {malas}"
    # y lo contrario: lo que sí se publicó en R0 tiene que llegar a la fila t0
    fila = a.loc[(t0, 19)]
    p0 = rellenado(ventana)
    assert np.isclose(fila["cmg_despacho"], c2.log_pos(p0["cmg_despacho"]).loc[(r0, 19)])
    assert np.isclose(fila["aportes_pct_sistema"], p0["aportes_pct_sistema"].loc[(r0 - pd.offsets.Day(1), 19)])
    print(f"   sin fuga: al alterar lo no publicado en R = t + {ATRASO_PRECIO} no cambia ninguna "
          f"fila hasta t; la fila t trae el costo marginal programado de R y los aportes de R - 1")


# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    print(f"1. Lectura (el precio llega con {ATRASO_PRECIO} días de atraso)")
    crudo = c2.leer()
    sin_atraso = [c for c in crudo.columns if c not in CALENDARIO_CRUDO
                  and c not in COMO_EL_PRECIO and c not in ATRASO]
    assert not sin_atraso, f"columnas sin atraso asignado: {sin_atraso}"

    print("2. Variables alineadas con su publicación")
    panel, info = armar(crudo)
    por_dias = info[info["entra"]].groupby("dias_frente_al_precio").size()
    print("   variables por días frente al precio (negativo = más recientes que el precio):")
    print("   " + ", ".join(f"{int(d):+d}: {n}" for d, n in por_dias.items()))
    for v, f in info[~info["entra"]].iterrows():
        print(f"   fuera: {v} ({f['motivo']}, {f['faltante_pct']}% de faltantes)")

    print("3. Prueba de fuga")
    comprobar_sin_fuga(crudo, info)

    print("4. Guardar")
    panel.reset_index().to_csv(SALIDA, index=False, compression="gzip", float_format="%.6g")
    info.to_csv(VARIABLES)
    n_var = int(info["entra"].sum()) - 1
    print(f"\n{SALIDA.name}: {panel.shape[0]:,} filas x {panel.shape[1] + 2} columnas "
          f"({n_var} variables base, {SALIDA.stat().st_size / 1e6:.1f} MB) "
          f"[{time.time() - t0:.0f} s]")


if __name__ == "__main__":
    main()
