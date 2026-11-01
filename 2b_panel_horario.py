"""
Paso 2b. Panel horario: una fila por día y hora.

    python 2b_panel_horario.py

Usa los archivos de datos/xm y datos/simem que bajó el paso 1; no descarga
nada. Deja paneles/panel_horario.csv.gz con 24 filas por día (hora 1 = de 0:00 a
1:00, como lo publica XM).

Solo trae lo que cambia dentro del día. El script deja también
paneles/panel_horario_completo.csv.gz, que agrega las variables que solo
existen por día (embalses, aportes, El Niño, lluvia, cargos regulados,
pronóstico del IDEAM...), repetidas en las 24 horas de su día. Del panel diario
no copia nada que se pueda calcular con las columnas horarias (ver NO_COPIAR).

Qué se sabe y cuándo está en docs/PANEL_HORARIO.md. Lo importante: casi todo se
conoce después de que pasa la hora, así que entra al modelo rezagado. Lo que
se conoce antes es el calendario, la disponibilidad declarada, el pronóstico de
demanda del CND, el costo marginal del despacho programado y la proyección de
reserva.
"""

import importlib.util
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "paneles" / "panel_horario.csv.gz"
SALIDA_COMPLETA = BASE / "paneles" / "panel_horario_completo.csv.gz"
PANEL_DIARIO = BASE / "paneles" / "panel_diario.csv"

# Del panel diario no se copia nada que se pueda calcular con las columnas
# horarias de este mismo panel: sería la misma información dos veces.
NO_COPIAR = [
    # las mismas que se dejan fuera del horario: el despacho (está como
    # cmg_despacho y en la curva de mérito) y los dos saldos con Ecuador
    "costo_marginal_prog", "precio_oferta_desp", "tie_merito", "tie_fuera_merito",
    # la misma variable sumada o promediada en el día
    "precio_bolsa", "demanda_regulada", "demanda_no_regulada", "demanda_real",
    "demanda_real_reg", "demanda_real_no_reg", "disp_declarada", "disp_comercial",
    "disp_real", "disp_decl_hidraulica", "disp_decl_termica", "gen_por_recurso",
    "gen_total_sistema", "gen_programada", "gen_prog_redespacho", "gen_seguridad",
    "gen_fuera_merito", "gen_hidraulica", "gen_termica", "gen_solar", "gen_eolica",
    "gen_cogenerador", "frac_hidraulica", "frac_termica", "frac_fncer", "gen_ideal",
    "co2_por_combustible", "consumo_combustible", "restricciones",
    "restricciones_sin_aliv", "perdidas_energia", "importaciones", "exportaciones",
    "compras_tie", "compras_contrato", "precio_prom_contrato", "precio_cont_no_regu",
    # la curva de mérito del día: aquí está hora por hora
    "cap_bajo_200", "cap_bajo_500", "oferta_marginal", "margen_ofertado",
    "escalon_siguiente", "oferta_capacidad_total", "holgura_gwh",
    # se calculan con las columnas horarias (el perfil del día y la
    # participación solar y eólica)
    "frac_solar", "frac_eolica", "gen_fncer", "precio_max_dia", "precio_min_dia",
    "precio_spread_intradia", "precio_cv_intradia", "hora_precio_max",
    "ratio_pico_valle", "demanda_pico", "factor_carga",
]

# las funciones de lectura son las del paso 2 (su nombre empieza por un número,
# así que se carga por la ruta)
_spec = importlib.util.spec_from_file_location("paso2", BASE / "2_construir_panel.py")
paso2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(paso2)

# Cómo se juntan las plantas o agentes dentro de cada hora. Las energías y
# capacidades se suman; los precios se promedian.
#
# Lo que no está en esta lista y por qué:
#   - costo_marginal_prog: es el mismo dato que cmg_despacho de SIMEM (coinciden
#     al 100%), que entra más abajo con el de redespacho.
#   - precio_oferta_desp: entra a través de la curva de mérito.
#   - ventas_tie: es igual a compras_tie en todas las horas (a nivel de sistema,
#     lo que se compra en la bolsa con Ecuador es lo que se vende).
#   - los saldos con Ecuador por mérito: no tienen datos en 2026.
SERIES = {
    "precio_bolsa":         "mean",
    "demanda_comercial":    "sum",
    "demanda_regulada":     "sum",
    "demanda_no_regulada":  "sum",
    "demanda_real":         "sum",
    "demanda_real_reg":     "sum",
    "demanda_real_no_reg":  "sum",
    "disp_declarada":       "sum",
    "disp_comercial":       "sum",
    "disp_real":            "sum",
    "gen_por_recurso":      "sum",
    "gen_programada":       "sum",
    "gen_prog_redespacho":  "sum",
    "gen_seguridad":        "sum",
    "gen_fuera_merito":     "sum",
    "consumo_combustible":  "sum",
    "restricciones":        "sum",
    "restricciones_sin_aliv": "sum",
    "perdidas_energia":     "sum",
    "importaciones":        "sum",
    "exportaciones":        "sum",
    "compras_tie":          "sum",
    "compras_contrato":     "sum",
    "precio_prom_contrato": "mean",
    "precio_cont_no_regu":  "mean",
}

# Se pasan a MWh para que los números sean legibles. XM publica kWh por hora
# (y kW de capacidad, que en una hora es lo mismo). Las restricciones no son
# energía sino dinero (pesos): una hora de 176 millones no puede ser kWh, con una
# demanda de unos 8.500 MWh. Van en millones de pesos.
EN_PESOS = ["restricciones", "restricciones_sin_aliv"]
EN_MWH = [s for s, regla in SERIES.items()
          if regla == "sum" and s not in ["consumo_combustible"] + EN_PESOS]

NO_SE_USAN_POR_AHORA = [
    "holgura_arriba", "arranques", "paradas",
    "reserva_hidraulica", "reserva_termica", "reserva_requisito", "reserva_holgura",
    "reserva_caliente_termica", "reserva_caliente_hidraulica",
]

# Igual que en el panel diario: si no hay fila, el evento no pasó.
EVENTOS = ["importaciones", "exportaciones", "compras_tie"]

TECNOLOGIAS = ["HIDRAULICA", "TERMICA", "SOLAR", "EOLICA", "COGENERADOR"]


def matriz(df, regla):
    """Día x hora (24 columnas) de una serie de XM, juntando plantas o agentes."""
    horas = paso2.horas_numericas(df)
    agrupado = horas.groupby(df["Date"])
    m = agrupado.sum(min_count=1) if regla == "sum" else agrupado.mean()
    m.columns = range(1, 25)
    return m


def a_largo(m, nombre):
    s = m.stack(dropna=False)
    s.index.names = ["fecha", "hora"]
    return s.rename(nombre)


def por_tecnologia(nombre, listado, prefijo):
    """Una serie horaria por tecnología, con el listado de plantas de PARATEC."""
    df = paso2.leer_xm(nombre).merge(listado, left_on="Values_code", right_on="codigo", how="left")
    horas = paso2.horas_numericas(df)
    horas[["Date", "tecnologia"]] = df[["Date", "tecnologia"]]
    g = horas.groupby(["Date", "tecnologia"]).sum(min_count=1)
    salida = {}
    for tec in TECNOLOGIAS:
        if tec in g.index.get_level_values("tecnologia"):
            m = g.xs(tec, level="tecnologia")
            m.columns = range(1, 25)
            salida[f"{prefijo}_{tec.lower()}"] = a_largo(m, f"{prefijo}_{tec.lower()}") / 1000
    return salida


# ---------------------------------------------------------------------------
# Curva de mérito hora por hora
# ---------------------------------------------------------------------------
#
# Cada planta oferta una vez al día, con un solo precio para las 24 horas (CREG
# 025 de 1995, numeral 3.1), y declara su disponibilidad hora por hora; el precio
# de bolsa es horario (CREG 055 de 1994, art. 14) porque en cada hora queda al
# margen una planta distinta.
#
# Para cada hora se ordenan las plantas por su oferta de esa hora, se acumula su
# disponibilidad de esa hora y se ve cuál queda al margen frente a la demanda de
# esa hora. Hoy la oferta es la misma en las 24 horas (se comprobó en todo el
# archivo), pero se usa la de cada hora: la Resolución CREG 101 113 de 2026
# cambió la redacción del art. 6 de la CREG 055 y, si las ofertas empiezan a
# variar por hora, la curva sigue siendo correcta.
#
# Ojo: la oferta del día t es lo que fija el precio del día t, y XM la publica
# con unos nueve días de atraso. En el modelo solo puede entrar rezagada.

def curva_horaria(demanda):
    # Fuente: CREG 055 de 1994, art. 14, y CREG 025 de 1995, numeral 3.1 (ver
    # docs/REFERENCIAS.md)
    horas = list(range(1, 25))
    o = paso2.leer_xm("precio_oferta_desp")
    oferta = paso2.horas_numericas(o)
    # si a una planta le falta el precio de alguna hora se toma el de las otras
    # horas de su mismo día
    oferta = oferta.bfill(axis=1).ffill(axis=1)
    oferta.columns = [f"p{h}" for h in horas]
    oferta[["Date", "Values_code"]] = o[["Date", "Values_code"]]
    d = paso2.leer_xm("disp_declarada")
    disp = paso2.horas_numericas(d) / 1000                      # MW en la hora
    disp.columns = [f"c{h}" for h in horas]
    disp[["Date", "Values_code"]] = d[["Date", "Values_code"]]
    plantas = oferta.merge(disp, on=["Date", "Values_code"], how="inner")

    filas = []
    for fecha, dia in plantas.groupby("Date"):
        P = dia[[f"p{h}" for h in horas]].to_numpy(dtype=float)          # plantas x 24
        C = np.nan_to_num(dia[[f"c{h}" for h in horas]].to_numpy(dtype=float))
        dem = demanda.reindex(pd.MultiIndex.from_product([[fecha], horas])).to_numpy()
        for j, h in enumerate(horas):
            validas = P[:, j] > 0
            orden = np.argsort(P[validas, j], kind="quicksort")
            precio = P[validas, j][orden]
            cap = C[validas, j][orden]
            if len(precio) == 0:
                continue
            acumulada = np.cumsum(cap)
            total = acumulada[-1]
            r = {"fecha": fecha, "hora": h,
                 "oferta_cap_total": total,
                 "cap_bajo_200": cap[precio <= 200].sum(),
                 "cap_bajo_500": cap[precio <= 500].sum()}
            if np.isfinite(dem[j]) and dem[j] > 0:
                i = int(np.searchsorted(acumulada, dem[j]))
                if i < len(precio):
                    r["oferta_marginal"] = precio[i]
                    r["escalon_siguiente"] = precio[i + 1] - precio[i] if i + 1 < len(precio) else np.nan
                    r["holgura_mw"] = total - dem[j]
                    r["margen_ofertado"] = total / dem[j]
            filas.append(r)
    return pd.DataFrame(filas).set_index(["fecha", "hora"])


# ---------------------------------------------------------------------------
# Generación ideal, combustible y recurso marginal
# ---------------------------------------------------------------------------
#
# Las tres vienen de la API de XM con 24 columnas por día, como las demás.
#
#   gen_ideal       lo que se despacharía sin las restricciones de la red. La
#                   diferencia con la generación real es lo que cuestan las
#                   restricciones.
#   co2_*           toneladas de CO2 por combustible. Es más fino que la mezcla
#                   por tecnología: separa gas, carbón y líquidos, que tienen
#                   costos muy distintos.
#   marg_*          qué tecnología fijó el precio en esa hora. XM marca una sola
#                   planta como marginal en cada hora (en los 11 años no hay una
#                   hora sin ella ni con dos).

GRUPOS_COMBUSTIBLE_CO2 = {
    "gas":      ["GAS", "GAS NI"],
    "carbon":   ["CARBON"],
    "liquidos": ["ACPM", "COMBUSTOLEO", "QUEROSENE", "CRUDO", "GLP"],
}


def bloque_api_nuevo(listado, indice):
    salida = {}

    # generación ideal, total y por tecnología (en MWh)
    gi = por_tecnologia("gen_ideal", listado, "gen_ideal")
    salida.update({k: v for k, v in gi.items() if k.endswith(("hidraulica", "termica"))})
    total = a_largo(matriz(paso2.leer_xm("gen_ideal"), "sum"), "gen_ideal_total") / 1000
    salida["gen_ideal_total"] = total

    # CO2 por grupo de combustible
    co2 = paso2.leer_xm("co2_por_combustible")
    horas = paso2.horas_numericas(co2)
    for grupo, combustibles in GRUPOS_COMBUSTIBLE_CO2.items():
        sel = co2["Values_code"].isin(combustibles)
        m = horas[sel].groupby(co2.loc[sel, "Date"]).sum(min_count=1)
        m.columns = range(1, 25)
        salida[f"co2_{grupo}"] = a_largo(m, f"co2_{grupo}")

    # recurso marginal: tecnología y combustible de la planta que fija el precio
    marg = paso2.leer_xm("recurso_marginal").merge(
        listado, left_on="Values_code", right_on="codigo", how="left")
    horas = paso2.horas_numericas(marg).notna().astype(float)
    horas[["Date", "tecnologia", "combustible"]] = marg[["Date", "tecnologia", "combustible"]]
    for tec in ("HIDRAULICA", "TERMICA"):
        m = horas[horas["tecnologia"] == tec].drop(columns=["tecnologia", "combustible"]) \
                 .groupby("Date").sum()
        m.columns = range(1, 25)
        salida[f"marg_{tec.lower()}"] = a_largo(m, f"marg_{tec.lower()}")
    for grupo, lista in paso2.COMBUSTIBLES.items():
        if grupo == "biomasa":
            continue
        sel = horas["combustible"].isin(lista)
        m = horas[sel].drop(columns=["tecnologia", "combustible"]).groupby("Date").sum()
        m.columns = range(1, 25)
        salida[f"marg_{grupo}"] = a_largo(m, f"marg_{grupo}")

    out = pd.DataFrame(salida).reindex(indice)

    # Un combustible sin fila en una hora no emitió: es un 0, no un dato que
    # falta. Se rellena solo en los días que tienen datos de CO2.
    co2_cols = [f"co2_{g}" for g in GRUPOS_COMBUSTIBLE_CO2]
    dia_co2 = out[co2_cols].notna().any(axis=1).groupby(level="fecha").transform("any")
    out.loc[dia_co2, co2_cols] = out.loc[dia_co2, co2_cols].fillna(0)
    out["co2_total"] = out[co2_cols].sum(axis=1, min_count=1)

    # el recurso marginal solo tiene fila los días publicados; en esos días una
    # tecnología sin marca en una hora es un 0 (no fue la marginal)
    dia_marg = out[["marg_hidraulica", "marg_termica"]].notna().any(axis=1) \
                  .groupby(level="fecha").transform("any")
    cols = [c for c in out if c.startswith("marg_")]
    out.loc[dia_marg, cols] = out.loc[dia_marg, cols].fillna(0)
    return out


# ---------------------------------------------------------------------------
# Series de SIMEM
# ---------------------------------------------------------------------------
#
# Hora. SIMEM marca cada registro con el instante en que EMPIEZA la hora
# (FechaHora = 04:00 es de 4:00 a 5:00), mientras que XM numera las horas de 1
# a 24 (la hora 5 es de 4:00 a 5:00). Se comprobó con el costo marginal de
# junio de 2025: con hora = FechaHora.hour + 1 coinciden las 240 horas; con
# otra regla quedan desfasadas.

CARPETA_SIMEM = BASE / "datos" / "simem"


def leer_simem(nombre):
    # Fuente: la regla de la hora es propia y comprobada (240 horas de costo
    # marginal coinciden con XM), ver el comentario de arriba
    ruta = CARPETA_SIMEM / f"{nombre}.csv.gz"
    if not ruta.exists():
        return None
    d = pd.read_csv(ruta, dtype=str)
    t = pd.to_datetime(d["FechaHora"])
    d["fecha"] = t.dt.normalize()
    d["hora"] = t.dt.hour + 1
    return d


def a_indice(serie, indice):
    return serie.reindex(indice)


def bloque_simem(indice):
    s = {}

    # pronóstico de demanda del CND: suma de los mercados de comercialización.
    # En 70 días (2019, 2020 y 2024) SIMEM trae además un "mercado" MC-SIN, que
    # es el total nacional (vale lo mismo que la suma de los demás, cociente
    # mediano 1,0015); si se suma, el pronóstico sale al doble. Se deja fuera.
    d = leer_simem("pron_demanda_cnd")
    if d is not None:
        d = d[d["MercadoComercializacionOperativo"] != "MC-SIN"].copy()
        d["v"] = d["PronDem"].astype(float) / 1000                         # MWh
        s["pron_demanda_cnd"] = d.groupby(["fecha", "hora"])["v"].sum(min_count=1)

    # costo marginal programado (despacho) y de redespacho, COP/kWh
    for nombre, col in [("cmg_despacho", "CostoMarginalDespacho"),
                        ("cmg_redespacho", "CostoMarginalRedespacho")]:
        d = leer_simem(nombre)
        if d is not None:
            d["v"] = d[col].astype(float)
            s[nombre] = d.groupby(["fecha", "hora"])["v"].mean()

    # holgura horaria superior: cuánto podría subir cada planta en esa hora
    # (solo trae 18 plantas y solo la holgura hacia arriba)
    d = leer_simem("holgura_horaria")
    if d is not None:
        d = ultima_version(d, ["fecha", "hora", "CodigoPlanta", "CodigoVariable"])
        d["v"] = d["Valor"].astype(float) / 1000                            # MWh
        s["holgura_arriba"] = d.groupby(["fecha", "hora"])["v"].sum(min_count=1)

    # arranques y paradas: cuántas plantas arrancaron o pararon en la hora
    for nombre, col in [("bandera_arranque", "arranques"), ("bandera_parada", "paradas")]:
        d = leer_simem(nombre)
        if d is None:
            continue
        d = ultima_version(d, ["fecha", "hora", "CodigoPlanta", "CodigoVariable"])
        # el 0 es "nada"; el 1 es el evento y, en unas pocas filas, viene una
        # letra (A en arranques, P en paradas) que marca lo mismo
        d["v"] = (d["ValorTexto"] != "0").astype(float)
        s[col] = d.groupby(["fecha", "hora"])["v"].sum()

    out = pd.DataFrame(s)
    out.index.names = ["fecha", "hora"]
    out = out.reindex(indice)

    # un contador sin fila en una hora de un día que sí tiene datos es un 0
    for col in ("arranques", "paradas"):
        if col in out:
            hay = out[col].notna().groupby(level="fecha").transform("any")
            out.loc[hay, col] = out.loc[hay, col].fillna(0)

    reserva = bloque_reserva(indice)
    return out.join(reserva) if reserva is not None else out


ORDEN_VERSION = {"TXR": 0, **{f"TX{i}": i for i in range(1, 9)}, "TXF": 9}


def ultima_version(d, clave):
    """
    Fuente: convención de liquidación de XM (ver docs/REFERENCIAS.md).

    XM publica cada dato en versiones: TXR es la preliminar, TX1 a TX8 las
    reliquidaciones sucesivas y TXF la final. Se deja la más reciente.
    """
    d = d.assign(_v=d["Version"].map(ORDEN_VERSION).fillna(-1))
    return d.sort_values("_v").drop_duplicates(clave, keep="last")


def bloque_reserva(indice):
    """
    Proyección de la reserva de generación, que el CND corre cada domingo. Cada
    ejecución trae dos semanas: la que empieza al día siguiente (la proyección,
    que mira hacia adelante) y la que acaba de terminar, recalculada. La marca
    EsProyeccion no sirve para separarlas: viene en true para la semana pasada
    y en false para la que viene. Lo que cuenta es la fecha: una hora es
    proyección si es posterior a la ejecución.

    Para cada hora se toma la proyección más reciente hecha antes de ese día y
    se promedian los casos (escenarios). Así el dato es lo que se sabía de
    antemano: una ejecución del domingo no entra en las horas del domingo ni en
    las anteriores.
    """
    d = leer_simem("reserva_caliente")
    if d is None:
        return None
    d = d.copy()
    d["ejecucion"] = pd.to_datetime(d["FechaEjecucion"])
    d["v"] = d["Valor"].astype(float) / 1000                                # MWh
    # solo ejecuciones hechas antes del día de la hora que proyectan
    d = d[d["ejecucion"] < d["fecha"]]

    # la más reciente por hora
    ultima = d.groupby(["fecha", "hora"])["ejecucion"].transform("max")
    d = d[d["ejecucion"] == ultima]

    out = {}
    for var, tipo, nombre in [("ReservaGeneracionSINEnergia", "Hidraulica", "reserva_hidraulica"),
                              ("ReservaGeneracionSINEnergia", "Termica", "reserva_termica"),
                              ("ReservaGeneracionSINEnergia", "RequisitoReserva", "reserva_requisito"),
                              ("ReservaCalienteEnergia", "Termica", "reserva_caliente_termica"),
                              ("ReservaCalienteEnergia", "Hidraulica", "reserva_caliente_hidraulica")]:
        sel = d[(d["CodigoVariable"] == var) & (d["TipoGeneracion"] == tipo)]
        if len(sel):
            out[nombre] = sel.groupby(["fecha", "hora"])["v"].mean()
    r = pd.DataFrame(out)
    r.index.names = ["fecha", "hora"]
    r = r.reindex(indice)
    if {"reserva_hidraulica", "reserva_termica", "reserva_requisito"} <= set(r):
        r["reserva_holgura"] = (r["reserva_hidraulica"] + r["reserva_termica"]
                                - r["reserva_requisito"])
    return r


def main():
    print("1. Series horarias de XM")
    columnas = {}
    for nombre, regla in SERIES.items():
        columnas[nombre] = a_largo(matriz(paso2.leer_xm(nombre), regla), nombre)
    panel = pd.concat(columnas.values(), axis=1)

    # índice completo: todos los días del panel diario por 24 horas
    dias = pd.date_range(panel.index.get_level_values("fecha").min(),
                         panel.index.get_level_values("fecha").max(), freq="D")
    indice = pd.MultiIndex.from_product([dias, range(1, 25)], names=["fecha", "hora"])
    panel = panel.reindex(indice)
    panel[EN_MWH] = panel[EN_MWH] / 1000
    panel[EN_PESOS] = panel[EN_PESOS] / 1e6                     # millones de pesos
    panel = panel.rename(columns={"gen_por_recurso": "gen_total"})

    # la demanda de los días publicados a medias queda vacía (la regla está en
    # el paso 2); va antes de todo lo que se calcula con ella
    incompletos = paso2.dias_demanda_incompleta()
    demandas = [c for c in paso2.DEMANDAS if c in panel.columns]
    panel.loc[panel.index.get_level_values("fecha").isin(incompletos), demandas] = np.nan

    # eventos: en un día con datos, una hora sin fila es una hora sin el evento.
    # El día "con datos" se mira por la generación, no por la demanda, que puede
    # haber quedado vacía por publicarse a medias.
    hay_dia = panel["gen_total"].groupby(level="fecha").transform("count") > 0
    for c in EVENTOS:
        panel.loc[hay_dia & panel[c].isna(), c] = 0.0

    print("2. Generación y disponibilidad por tecnología")
    listado = paso2.leer_listado()
    tec = {**por_tecnologia("gen_por_recurso", listado, "gen"),
           **por_tecnologia("disp_declarada", listado, "disp_decl")}
    tec = pd.DataFrame(tec).reindex(indice)
    # una tecnología sin fila en una hora con generación es cero (ej.: solar de noche)
    hay_gen = panel["gen_total"].notna()
    tec[hay_gen.values] = tec[hay_gen.values].fillna(0)
    tec = tec.drop(columns=[c for c in tec if c.startswith("disp_decl_") and
                            not c.endswith(("hidraulica", "termica"))])
    panel = panel.join(tec)

    gen = panel["gen_total"].replace(0, np.nan)
    panel["frac_hidraulica"] = panel["gen_hidraulica"] / gen
    panel["frac_termica"] = panel["gen_termica"] / gen
    panel["frac_fncer"] = (panel["gen_solar"] + panel["gen_eolica"]) / gen
    # cuánta capacidad declarada hay por cada MWh de demanda en esa hora
    panel["margen_declarado"] = panel["disp_declarada"] / panel["demanda_comercial"].replace(0, np.nan)

    print("3. Curva de mérito hora por hora (tarda unos minutos)")
    panel = panel.join(curva_horaria(panel["demanda_comercial"]))

    print("3b. Generación ideal, combustible y recurso marginal (API de XM)")
    panel = panel.join(bloque_api_nuevo(listado, indice))
    print("3c. Series de SIMEM: pronóstico de demanda, costo marginal, holgura, "
          "arranques, paradas y reserva")
    panel = panel.join(bloque_simem(indice))

    # diferencias que dicen cuánto se equivocó el programa o cuánto costaron las
    # restricciones; se conocen después de la hora, así que entran rezagadas
    panel["error_pron_demanda"] = panel["demanda_comercial"] - panel["pron_demanda_cnd"]
    panel["ajuste_cmg"] = panel["cmg_redespacho"] - panel["cmg_despacho"]
    panel["gen_restricciones"] = panel["gen_total"] - panel["gen_ideal_total"]

    # Por ahora no se usan: empiezan en 2021 (holgura, arranques y paradas) o en
    # 2024 y 2025 (reserva), y un modelo que arranca en 2015 no las puede usar.
    # Los datos siguen en datos/simem y el código que las arma sigue aquí; para
    # volver a incluirlas basta con vaciar esta lista.
    panel = panel.drop(columns=[c for c in NO_SE_USAN_POR_AHORA if c in panel.columns])

    print("4. Calendario")
    fechas = panel.index.get_level_values("fecha")
    festivos = holidays.Colombia(years=range(fechas.year.min(), fechas.year.max() + 1))
    panel.insert(0, "fecha_hora", fechas + pd.to_timedelta(panel.index.get_level_values("hora") - 1, unit="h"))
    panel.insert(1, "dia_semana", fechas.dayofweek)          # 0 = lunes
    panel.insert(2, "es_festivo", fechas.map(lambda f: f in festivos).astype(int))

    panel = panel.reset_index()
    panel.to_csv(SALIDA, index=False, compression="gzip", float_format="%.6g")
    precio = panel.dropna(subset=["precio_bolsa"])
    print(f"\n{SALIDA.name}: {len(panel):,} filas x {panel.shape[1]} columnas, "
          f"{SALIDA.stat().st_size / 1e6:.1f} MB")
    print(f"precio horario del {precio['fecha'].min().date()} al {precio['fecha'].max().date()}")

    print("\n5. Unión con el panel diario")
    completo = unir_con_diario(panel)
    completo.to_csv(SALIDA_COMPLETA, index=False, compression="gzip", float_format="%.6g")
    print(f"{SALIDA_COMPLETA.name}: {len(completo):,} filas x {completo.shape[1]} columnas, "
          f"{SALIDA_COMPLETA.stat().st_size / 1e6:.1f} MB")


def unir_con_diario(horario):
    """
    Repite en las 24 horas de su día las variables diarias que no se pueden
    calcular con lo horario (hidrología, clima, El Niño, IDEAM, regulatorias,
    mezcla por combustible, concentración del mercado, forma de la curva de
    ofertas). Las que sí se pueden calcular están en NO_COPIAR.
    """
    diario = pd.read_csv(PANEL_DIARIO, parse_dates=["fecha"])
    diario = diario.drop(columns=[c for c in NO_COPIAR if c in diario.columns])
    repetidas = set(diario.columns) & set(horario.columns) - {"fecha"}
    assert not repetidas, f"columnas del diario que ya están por hora: {sorted(repetidas)}"
    return horario.merge(diario, on="fecha", how="left")


if __name__ == "__main__":
    main()
