"""
================================================================================
AMPLIACION DEL PANEL — variables nuevas a partir de fuentes ya descargadas
================================================================================

Parte del panel diario existente (data/panel_d.parquet, 58 variables) y le agrega
variables que estaban disponibles en la cache de la API pero que el consolidador
original colapsaba a totales del sistema.

La idea central: `cache_api/gen_por_recurso.parquet` trae generacion POR PLANTA y
POR HORA (785 mil filas), y `data/Listado_Recursos_Generacion.xlsx` mapea cada
planta a su tecnologia, combustible, tipo de despacho y clasificacion. Cruzar esas
dos cosas da la mezcla de generacion, que el panel original no tenia.

Cada variable creada queda documentada en DICCIONARIO_VARIABLES.md.

Uso
---
  python 00b_ampliar_panel.py
================================================================================
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE = BASE / "cache_api"
DATOS = BASE / "data"

SALIDA_CSV = BASE / "panel_diario_ampliado.csv"
SALIDA_MD = BASE / "DICCIONARIO_VARIABLES.md"

HORAS = [f"Values_Hour{h:02d}" for h in range(1, 25)]

# Registro de lo que se va creando, para el diccionario
REGISTRO = []


def anotar(nombre, grupo, unidad, significado, fuente, calculo, aviso=""):
    REGISTRO.append({"variable": nombre, "grupo": grupo, "unidad": unidad,
                     "significado": significado, "fuente": fuente,
                     "calculo": calculo, "aviso": aviso})


# ==============================================================================
# 1. CATALOGO DE PLANTAS
# ==============================================================================

def cargar_recursos():
    """Listado de recursos de generacion: planta -> tecnologia, combustible, etc."""
    raw = pd.read_excel(DATOS / "Listado_Recursos_Generacion.xlsx", header=None)
    rec = raw.iloc[4:].copy()
    rec.columns = raw.iloc[3].tolist()
    rec = rec[rec["Código SIC"].notna()].reset_index(drop=True)

    rec = rec.rename(columns={
        "Código SIC": "codigo",
        "Capacidad Efectiva Neta [MW]": "capacidad_mw",
        "Tipo Generación": "tecnologia",
        "Combustible por Defecto": "combustible",
        "Tipo Despacho": "despacho",
        "Clasificación": "clasificacion",
        "Departamento": "departamento",
    })
    rec["capacidad_mw"] = pd.to_numeric(rec["capacidad_mw"], errors="coerce")
    return rec[["codigo", "capacidad_mw", "tecnologia", "combustible",
                "despacho", "clasificacion", "departamento"]]


def leer_horario(ruta, columna_codigo="Values_code"):
    """
    Lee un parquet horario y lo pasa a total diario por planta.

    Las columnas horarias vienen como texto en la cache de la API, asi que hay que
    forzarlas a numero antes de sumar: sin esto la suma concatena cadenas.
    """
    d = pd.read_parquet(ruta)
    d["Date"] = pd.to_datetime(d["Date"])
    horas = d[HORAS].apply(pd.to_numeric, errors="coerce")
    d["total_dia"] = horas.sum(axis=1, min_count=1)
    return d[["Date", columna_codigo, "total_dia"]].rename(
        columns={columna_codigo: "codigo"})


# ==============================================================================
# 2. MEZCLA DE GENERACION
# ==============================================================================

def mezcla_generacion(rec):
    gen = leer_horario(CACHE / "gen_por_recurso.parquet")
    gen = gen.merge(rec, on="codigo", how="left")

    # kWh -> GWh
    gen["gwh"] = gen["total_dia"] / 1e6
    total_dia = gen.groupby("Date")["gwh"].sum().rename("gen_total_sistema")

    salida = {"gen_total_sistema": total_dia}

    # --- por tecnologia ---
    mapa_tec = {"HIDRAULICA": "hidraulica", "TERMICA": "termica",
                "SOLAR": "solar", "EOLICA": "eolica", "COGENERADOR": "cogenerador"}
    for etiqueta, sufijo in mapa_tec.items():
        s = (gen[gen["tecnologia"] == etiqueta].groupby("Date")["gwh"].sum()
             .rename(f"gen_{sufijo}"))
        salida[f"gen_{sufijo}"] = s
        anotar(f"gen_{sufijo}", "Mezcla de generacion", "GWh/dia",
               f"Energia generada por las plantas de tipo {etiqueta}.",
               "XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), "
               "cruzada con el Listado de Recursos de Generacion de XM.",
               "Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.")

    # --- fracciones (la mezcla es lo que importa, no el nivel) ---
    for sufijo in ["hidraulica", "termica", "solar", "eolica"]:
        salida[f"frac_{sufijo}"] = (salida[f"gen_{sufijo}"] / total_dia).rename(f"frac_{sufijo}")
        anotar(f"frac_{sufijo}", "Mezcla de generacion", "fraccion (0-1)",
               f"Participacion de {sufijo} en la generacion total del dia.",
               "Derivada de gen_* y gen_total_sistema.",
               f"gen_{sufijo} / gen_total_sistema.",
               "Es la variable interesante para el precio: lo que importa no es "
               "cuanto genera la hidraulica sino que tanto del sistema depende de ella.")

    # FNCER = solar + eolica (no convencionales)
    fncer = (salida["gen_solar"].reindex(total_dia.index).fillna(0)
             + salida["gen_eolica"].reindex(total_dia.index).fillna(0))
    salida["gen_fncer"] = fncer.rename("gen_fncer")
    salida["frac_fncer"] = (fncer / total_dia).rename("frac_fncer")
    anotar("gen_fncer", "Mezcla de generacion", "GWh/dia",
           "Generacion de fuentes no convencionales de energia renovable (solar + eolica).",
           "Derivada de gen_solar + gen_eolica.", "Suma de solar y eolica.")
    anotar("frac_fncer", "Mezcla de generacion", "fraccion (0-1)",
           "Penetracion de renovables no convencionales en la generacion del dia.",
           "Derivada.", "gen_fncer / gen_total_sistema.",
           "Practicamente cero antes de 2021: la capacidad solar del pais era marginal.")

    # --- por combustible (detalle del bloque termico) ---
    combustibles = {
        "gas": ["GAS", "MEZCLA GAS - CARBÓN", "MEZCLA GAS-FUEL OIL (ACPM O COMBUSTOLEO)"],
        "carbon": ["CARBON"],
        "liquidos": ["ACPM", "COMBUSTOLEO", "CRUDO", "DIESEL MAR"],
        "biomasa": ["BAGAZO", "BIOMASA", "BIOGAS"],
    }
    for sufijo, lista in combustibles.items():
        s = (gen[gen["combustible"].isin(lista)].groupby("Date")["gwh"].sum()
             .rename(f"gen_{sufijo}"))
        salida[f"gen_{sufijo}"] = s
        anotar(f"gen_{sufijo}", "Generacion por combustible", "GWh/dia",
               f"Energia generada quemando {sufijo} ({', '.join(lista)}).",
               "XM API Gene por Recurso + columna 'Combustible por Defecto' del "
               "Listado de Recursos.",
               "Suma diaria de las plantas cuyo combustible por defecto esta en la lista.",
               "Es el combustible POR DEFECTO declarado, no el realmente quemado ese "
               "dia: una planta dual puede estar operando con el otro combustible.")

    termica = salida["gen_termica"].reindex(total_dia.index)
    salida["frac_gas_en_termica"] = (
        salida["gen_gas"].reindex(total_dia.index) / termica.replace(0, np.nan)
    ).rename("frac_gas_en_termica")
    anotar("frac_gas_en_termica", "Generacion por combustible", "fraccion (0-1)",
           "Que parte del parque termico en operacion esta quemando gas frente a "
           "carbon o liquidos.",
           "Derivada.", "gen_gas / gen_termica.",
           "Proxy del costo marginal termico: los liquidos son mucho mas caros que "
           "el gas, asi que si esta fraccion cae, el termico marginal se encarecio.")

    # --- despacho central vs no despachado ---
    # Solo las plantas de despacho centralizado (DC) entran al orden de merito que
    # forma el precio de bolsa. Las ND (menores, autogeneradores, distribuida)
    # generan pero no ofertan.
    for etiqueta, sufijo in [("DC", "despacho_central"), ("ND", "no_despachado")]:
        s = (gen[gen["despacho"] == etiqueta].groupby("Date")["gwh"].sum()
             .rename(f"gen_{sufijo}"))
        salida[f"gen_{sufijo}"] = s
        anotar(f"gen_{sufijo}", "Estructura del despacho", "GWh/dia",
               f"Energia generada por plantas con tipo de despacho {etiqueta} "
               f"({'centralizado, participan en el orden de merito' if etiqueta == 'DC' else 'no despachadas centralmente'}).",
               "XM API Gene por Recurso + columna 'Tipo Despacho' del Listado de Recursos.",
               "Suma diaria por tipo de despacho.")

    salida["frac_despacho_central"] = (
        salida["gen_despacho_central"] / total_dia).rename("frac_despacho_central")
    anotar("frac_despacho_central", "Estructura del despacho", "fraccion (0-1)",
           "Parte del sistema que se forma en el mercado centralizado.",
           "Derivada.", "gen_despacho_central / gen_total_sistema.",
           "Solo las plantas DC ofertan precio, asi que esta fraccion mide que "
           "tanto del sistema pasa por el mecanismo que fija el precio de bolsa.")

    # --- filo de agua: hidraulica que NO puede almacenar ---
    filo = ["FILO DE AGUA", "FILO AGUA ESPECIAL"]
    s = gen[gen["clasificacion"].isin(filo)].groupby("Date")["gwh"].sum().rename("gen_filo_agua")
    salida["gen_filo_agua"] = s
    hidro = salida["gen_hidraulica"].reindex(total_dia.index)
    salida["frac_filo_en_hidro"] = (
        s.reindex(total_dia.index) / hidro.replace(0, np.nan)).rename("frac_filo_en_hidro")
    anotar("gen_filo_agua", "Hidrologia estructural", "GWh/dia",
           "Generacion de plantas hidraulicas a filo de agua, que no tienen embalse "
           "y deben turbinar el caudal que llega o perderlo.",
           "XM API Gene por Recurso + columna 'Clasificacion' del Listado de Recursos.",
           "Suma diaria de las plantas clasificadas FILO DE AGUA o FILO AGUA ESPECIAL.")
    anotar("frac_filo_en_hidro", "Hidrologia estructural", "fraccion (0-1)",
           "Parte de la generacion hidraulica que no es almacenable.",
           "Derivada.", "gen_filo_agua / gen_hidraulica.",
           "Distincion economica real: el agua embalsada tiene valor de opcion "
           "(se puede guardar para cuando el precio suba); la de filo de agua no.")

    # --- concentracion del mercado ---
    part = gen.copy()
    part["part"] = part["gwh"] / part.groupby("Date")["gwh"].transform("sum")
    hhi = (part.groupby("Date")["part"].apply(lambda x: (x ** 2).sum() * 10000)
           .rename("hhi_generacion"))
    salida["hhi_generacion"] = hhi
    anotar("hhi_generacion", "Concentracion de mercado", "indice 0-10.000",
           "Indice Herfindahl-Hirschman de la generacion diaria por planta. "
           "Mide que tan concentrada esta la generacion del dia.",
           "Derivada de XM API Gene por Recurso.",
           "Suma de los cuadrados de las participaciones de cada planta, x10.000.",
           "Por encima de 2.500 se considera un mercado concentrado. Dias de alta "
           "concentracion implican mas poder de mercado y, en teoria, precios mas altos.")

    top5 = (part.sort_values("gwh", ascending=False).groupby("Date")["part"]
            .apply(lambda x: x.head(5).sum()).rename("gen_top5_pct"))
    salida["gen_top5_pct"] = top5
    anotar("gen_top5_pct", "Concentracion de mercado", "fraccion (0-1)",
           "Participacion de las cinco plantas mas grandes del dia en la generacion total.",
           "Derivada de XM API Gene por Recurso.",
           "Suma de las 5 participaciones mas altas de cada dia.")

    n_plantas = (gen[gen["gwh"] > 0].groupby("Date")["codigo"].nunique()
                 .rename("n_plantas_activas"))
    salida["n_plantas_activas"] = n_plantas
    anotar("n_plantas_activas", "Concentracion de mercado", "conteo",
           "Numero de plantas que generaron algo ese dia.",
           "Derivada de XM API Gene por Recurso.",
           "Conteo de codigos de planta con generacion diaria mayor que cero.",
           "Crece mucho a lo largo del periodo por la entrada de solares pequenias, "
           "asi que tiene tendencia: usar en diferencias o como choque.")

    return pd.DataFrame(salida)


# ==============================================================================
# 3. DISPONIBILIDAD POR TECNOLOGIA
# ==============================================================================

def disponibilidad_por_tecnologia(rec):
    disp = leer_horario(CACHE / "disp_declarada.parquet")
    disp = disp.merge(rec, on="codigo", how="left")
    disp["gwh"] = disp["total_dia"] / 1e6

    salida = {}
    for etiqueta, sufijo in [("HIDRAULICA", "hidraulica"), ("TERMICA", "termica")]:
        s = (disp[disp["tecnologia"] == etiqueta].groupby("Date")["gwh"].sum()
             .rename(f"disp_decl_{sufijo}"))
        salida[f"disp_decl_{sufijo}"] = s
        anotar(f"disp_decl_{sufijo}", "Disponibilidad por tecnologia", "GWh/dia",
               f"Disponibilidad declarada por las plantas {etiqueta}.",
               "XM API, metrica DispoDeclarada por Recurso "
               "(cache_api/disp_declarada.parquet) + Listado de Recursos.",
               "Suma de las 24 horas declaradas por cada planta del tipo.",
               "Es ex ante: se declara antes del despacho, asi que puede entrar con "
               "rezago 0 sin fuga.")

    s_dc = (disp[disp["despacho"] == "DC"].groupby("Date")["gwh"].sum()
            .rename("disp_decl_despacho_central"))
    salida["disp_decl_despacho_central"] = s_dc
    anotar("disp_decl_despacho_central", "Disponibilidad por tecnologia", "GWh/dia",
           "Disponibilidad declarada por las plantas de despacho centralizado, "
           "que son las que realmente compiten por fijar el precio.",
           "XM API DispoDeclarada por Recurso + Tipo Despacho del Listado.",
           "Suma diaria de las plantas DC.")

    return pd.DataFrame(salida)


# ==============================================================================
# 4. HIDROLOGIA DESAGREGADA
# ==============================================================================

def hidrologia_desagregada():
    salida = {}

    ap = pd.read_parquet(CACHE / "aportes_por_rio.parquet")
    ap["Date"] = pd.to_datetime(ap["Date"])
    ap["Value"] = pd.to_numeric(ap["Value"], errors="coerce")

    part = ap.copy()
    part["part"] = part["Value"] / part.groupby("Date")["Value"].transform("sum")

    salida["hhi_aportes_rios"] = (part.groupby("Date")["part"]
                                  .apply(lambda x: (x ** 2).sum() * 10000)
                                  .rename("hhi_aportes_rios"))
    anotar("hhi_aportes_rios", "Hidrologia desagregada", "indice 0-10.000",
           "Concentracion de los aportes hidricos entre los 47 rios del sistema.",
           "XM API, metrica AporEner por Rio (cache_api/aportes_por_rio.parquet).",
           "Herfindahl sobre la participacion de cada rio en el aporte total del dia.",
           "Un valor alto significa que el sistema depende de pocas cuencas ese dia, "
           "que es una fragilidad que el agregado del sistema no muestra.")

    salida["aportes_top3_pct"] = (part.sort_values("Value", ascending=False)
                                  .groupby("Date")["part"]
                                  .apply(lambda x: x.head(3).sum())
                                  .rename("aportes_top3_pct"))
    anotar("aportes_top3_pct", "Hidrologia desagregada", "fraccion (0-1)",
           "Parte del aporte hidrico total que viene de las tres cuencas mas "
           "caudalosas del dia.",
           "XM API AporEner por Rio.", "Suma de las 3 participaciones mas altas.")

    salida["n_rios_aportando"] = (ap[ap["Value"] > 0].groupby("Date")["Name"].nunique()
                                  .rename("n_rios_aportando"))
    anotar("n_rios_aportando", "Hidrologia desagregada", "conteo",
           "Numero de rios con aporte positivo reportado ese dia.",
           "XM API AporEner por Rio.", "Conteo de rios con Value > 0.")

    # --- volumen util por embalse principal ---
    vol = pd.read_parquet(CACHE / "volumen_por_embalse.parquet")
    cap = pd.read_parquet(CACHE / "capacidad_por_embalse.parquet")
    for d in (vol, cap):
        d["Date"] = pd.to_datetime(d["Date"])
        d["Value"] = pd.to_numeric(d["Value"], errors="coerce")

    # Los cinco embalses de mayor capacidad media concentran la regulacion del pais
    mayores = (cap.groupby("Name")["Value"].mean().sort_values(ascending=False)
               .head(5).index.tolist())

    v = vol.pivot_table(index="Date", columns="Name", values="Value", aggfunc="sum")
    c = cap.pivot_table(index="Date", columns="Name", values="Value", aggfunc="sum")

    for nombre in mayores:
        clave = ("vol_pct_" + nombre.lower().replace(" ", "_")
                 .replace(".", "").replace("-", "_"))
        serie = (v[nombre] / c[nombre].replace(0, np.nan)).rename(clave)
        salida[clave] = serie
        anotar(clave, "Hidrologia desagregada", "fraccion (0-1)",
               f"Nivel del embalse {nombre} como fraccion de su capacidad util.",
               "XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner "
               "por Embalse (cache_api/volumen_por_embalse.parquet y "
               "capacidad_por_embalse.parquet).",
               f"volumen_util({nombre}) / capacidad_util({nombre}).",
               "Este embalse esta entre los cinco de mayor capacidad del pais. El "
               "agregado nacional esconde que un embalse grande y regulador puede "
               "estar critico mientras el promedio se ve normal. "
               "Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM "
               "reporta volumen por encima de la capacidad util declarada cuando el "
               "embalse esta rebosando. No se recorta a 1 a proposito, porque ese "
               "exceso es informacion real (embalse lleno, vertimiento probable).")

    hhi_vol = (v.div(v.sum(axis=1), axis=0) ** 2).sum(axis=1) * 10000
    salida["hhi_volumen_embalses"] = hhi_vol.rename("hhi_volumen_embalses")
    anotar("hhi_volumen_embalses", "Hidrologia desagregada", "indice 0-10.000",
           "Concentracion del agua almacenada entre los 24 embalses del sistema.",
           "XM API VoluUtilDiarEner por Embalse.",
           "Herfindahl sobre la participacion de cada embalse en el volumen total.")

    return pd.DataFrame(salida)


# ==============================================================================
# 5. PERFIL INTRADIARIO DEL PRECIO Y DE LA DEMANDA
# ==============================================================================

def perfil_intradiario():
    salida = {}

    pr = pd.read_csv(DATOS / "PrecBolsNaci_Sistema.csv")
    pr["Date"] = pd.to_datetime(pr["Date"])
    H = pr[HORAS].apply(pd.to_numeric, errors="coerce")
    pr = pr.set_index("Date")
    H.index = pr.index

    salida["precio_max_dia"] = H.max(axis=1).rename("precio_max_dia")
    salida["precio_min_dia"] = H.min(axis=1).rename("precio_min_dia")
    salida["precio_spread_intradia"] = (H.max(axis=1) - H.min(axis=1)).rename("precio_spread_intradia")
    salida["precio_cv_intradia"] = (H.std(axis=1) / H.mean(axis=1).replace(0, np.nan)
                                    ).rename("precio_cv_intradia")
    salida["hora_precio_max"] = (H.values.argmax(axis=1) + 1)
    salida["hora_precio_max"] = pd.Series(salida["hora_precio_max"], index=H.index,
                                          name="hora_precio_max")
    salida["ratio_pico_valle"] = (H.max(axis=1) / H.min(axis=1).replace(0, np.nan)
                                  ).rename("ratio_pico_valle")

    for nombre, desc, calc in [
        ("precio_max_dia", "Precio de bolsa mas alto del dia entre las 24 horas.",
         "Maximo de las 24 columnas horarias."),
        ("precio_min_dia", "Precio de bolsa mas bajo del dia.",
         "Minimo de las 24 columnas horarias."),
        ("precio_spread_intradia", "Diferencia entre la hora mas cara y la mas barata del dia.",
         "precio_max_dia - precio_min_dia."),
        ("precio_cv_intradia", "Coeficiente de variacion del precio dentro del dia.",
         "desviacion estandar horaria / media horaria."),
        ("hora_precio_max", "Hora del dia (1 a 24) en que el precio alcanzo su maximo.",
         "Indice de la columna horaria con el valor mas alto."),
        ("ratio_pico_valle", "Cuantas veces mas caro fue el pico frente al valle. "
         "Vale exactamente 1 en los dias en que el precio fue plano las 24 horas, "
         "que son dias en que una sola planta quedo marginal todo el dia o en que el "
         "precio toco el techo de escasez (paso 15 veces entre 2015 y 2025, tres de "
         "ellas en 2024 con el precio pegado en ~2.460 COP/kWh).",
         "precio_max_dia / precio_min_dia."),
    ]:
        anotar(nombre, "Perfil intradiario del precio",
               "COP/kWh" if "precio" in nombre and "cv" not in nombre and "ratio" not in nombre
               else ("hora 1-24" if nombre == "hora_precio_max" else "razon"),
               desc,
               "XM API, metrica PrecBolsNaci por Sistema, version horaria "
               "(data/PrecBolsNaci_Sistema.csv).", calc,
               "CUIDADO: se calcula a partir del precio del mismo dia, asi que es "
               "informacion ex post. Solo puede usarse con rezago de al menos 1 dia. "
               "El pipeline la rezagara como cualquier otra variable medida durante el dia.")

    dm = pd.read_csv(DATOS / "DemaCome_Sistema.csv")
    dm["Date"] = pd.to_datetime(dm["Date"])
    HD = dm[HORAS].apply(pd.to_numeric, errors="coerce")
    HD.index = dm["Date"]

    salida["demanda_pico"] = (HD.max(axis=1) / 1e6).rename("demanda_pico")
    salida["factor_carga"] = (HD.mean(axis=1) / HD.max(axis=1).replace(0, np.nan)
                              ).rename("factor_carga")

    anotar("demanda_pico", "Perfil intradiario de la demanda", "GWh en la hora pico",
           "Demanda comercial de la hora de mayor consumo del dia.",
           "XM API, metrica DemaCome por Sistema, version horaria "
           "(data/DemaCome_Sistema.csv).", "Maximo de las 24 horas, pasado a GWh.",
           "El precio se forma en el margen: lo que estresa el sistema es la hora "
           "pico, no el promedio del dia.")
    anotar("factor_carga", "Perfil intradiario de la demanda", "fraccion (0-1)",
           "Que tan plana es la curva de demanda del dia.",
           "XM API DemaCome por Sistema horaria.", "demanda media / demanda pico.",
           "Un factor de carga bajo significa un pico pronunciado, que exige "
           "encender plantas caras solo unas horas.")

    return pd.DataFrame(salida)


# ==============================================================================
# 6. COSTO DE COMBUSTIBLE (gas vehicular como proxy)
# ==============================================================================

def precio_gas():
    ruta = next(DATOS.glob("Consulta_Precios_Promedio_de_Gas_Natural*.csv"), None)
    if ruta is None:
        print("[!] No encuentro el CSV de precios de gas, se omite")
        return pd.DataFrame()

    g = pd.read_csv(ruta)
    g["fecha"] = pd.to_datetime(g["FECHA_PRECIO"], format="%Y-%m-%d", errors="coerce")
    g["precio"] = pd.to_numeric(
        g["PRECIO_PROMEDIO_PUBLICADO"].astype(str).str.replace(",", "", regex=False),
        errors="coerce")

    s = g.groupby("fecha")["precio"].median().rename("precio_gncv")
    s.index.name = "Date"

    anotar("precio_gncv", "Costo de combustible", "COP/m3",
           "Precio promedio publicado del gas natural comprimido vehicular, "
           "mediana nacional entre estaciones de servicio.",
           "Ministerio de Minas y Energia / datos abiertos, consulta de precios "
           "promedio de GNCV (data/Consulta_Precios_Promedio_de_Gas_Natural_"
           "Comprimido_Vehicular_(AUTOMATIZADO)_20260912.csv).",
           "Mediana de PRECIO_PROMEDIO_PUBLICADO por fecha, sobre todas las "
           "estaciones del pais. Se usa mediana y no media porque hay estaciones "
           "con precios atipicos.",
           "LIMITACION IMPORTANTE: solo hay 57 fechas entre 2022 y 2026 (es una "
           "serie mensual, no diaria) y empieza en 2022, asi que queda vacia en la "
           "ventana de seleccion. Ademas es gas VEHICULAR, no el gas industrial que "
           "compran las termicas: sirve como proxy de la tendencia del costo del "
           "gas, no como su precio real. Tratarla con desconfianza.")
    return s.to_frame()


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 72)
    print("AMPLIACION DEL PANEL")
    print("=" * 72)

    base = pd.read_parquet(BASE / "data" / "panel_d.parquet").sort_index()
    base.index = pd.to_datetime(base.index)
    base.index.name = "fecha"
    print(f"[base]    panel original: {base.shape[0]} dias x {base.shape[1]} variables")

    rec = cargar_recursos()
    print(f"[plantas] {len(rec)} recursos en el listado de XM")

    piezas = []
    for nombre, fn in [("mezcla de generacion", lambda: mezcla_generacion(rec)),
                       ("disponibilidad por tecnologia", lambda: disponibilidad_por_tecnologia(rec)),
                       ("hidrologia desagregada", hidrologia_desagregada),
                       ("perfil intradiario", perfil_intradiario),
                       ("precio del gas", precio_gas)]:
        try:
            p = fn()
            if len(p.columns):
                p.index = pd.to_datetime(p.index)
                piezas.append(p)
                print(f"[nuevo]   {nombre}: {len(p.columns)} variables")
        except Exception as e:
            print(f"[ERROR]   {nombre}: {type(e).__name__}: {e}")

    nuevas = pd.concat(piezas, axis=1)
    nuevas = nuevas[~nuevas.index.duplicated()]

    panel = base.join(nuevas, how="left")
    panel = panel.loc[base.index.min():base.index.max()]

    panel.to_csv(SALIDA_CSV, encoding="utf-8")
    print(f"\n[salida]  {SALIDA_CSV.name}: {panel.shape[0]} dias x {panel.shape[1]} "
          f"variables (+{panel.shape[1] - base.shape[1]} nuevas)")
    print(f"          {SALIDA_CSV.stat().st_size / 1e6:.2f} MB")

    escribir_diccionario(panel, base)
    print(f"[salida]  {SALIDA_MD.name}: {len(REGISTRO)} variables documentadas")

    print("\nCobertura de las variables nuevas:")
    cob = panel[[r["variable"] for r in REGISTRO if r["variable"] in panel.columns]].notna().mean()
    for v, c in cob.sort_values().items():
        marca = "  " if c > 0.9 else ("!!" if c < 0.5 else " ~")
        print(f"  {marca} {v:34s} {c:6.1%}")


def escribir_diccionario(panel, base):
    cob = panel.notna().mean()
    rango = {}
    for r in REGISTRO:
        v = r["variable"]
        if v in panel.columns:
            s = panel[v].dropna()
            rango[v] = (s.index.min(), s.index.max()) if len(s) else (None, None)

    lineas = [
        "# Diccionario de variables — panel ampliado",
        "",
        f"Generado por `00b_ampliar_panel.py`. Panel resultante: "
        f"**{panel.shape[0]} días × {panel.shape[1]} variables** "
        f"({base.shape[1]} del panel original + {panel.shape[1] - base.shape[1]} nuevas), "
        f"del {panel.index.min().date()} al {panel.index.max().date()}.",
        "",
        "Archivo de datos: `panel_diario_ampliado.csv`",
        "",
        "## Cómo leer este documento",
        "",
        "Cada variable nueva lleva: qué significa, **de dónde salió** (fuente "
        "primaria y archivo concreto), cómo se calculó, y una advertencia cuando hay "
        "algo que puede llevar a un error de interpretación o a fuga de información.",
        "",
        "**Ninguna variable de este panel está rezagada.** Tal como están, la mayoría "
        "son información que se conoce al cierre del día y usarlas sin rezago sería "
        "fuga. El rezago lo aplica el notebook, no este archivo.",
        "",
        "---",
        "",
        "## Fuentes primarias",
        "",
        "| Fuente | Qué aporta | Acceso |",
        "|---|---|---|",
        "| **XM API (`servapibi.xm.com.co`)** | generación, disponibilidad, aportes, "
        "volúmenes, precios, demanda | `pydataxm`, cacheado en `cache_api/` |",
        "| **Listado de Recursos de Generación (XM)** | planta → tecnología, "
        "combustible, tipo de despacho, clasificación, departamento | "
        "`data/Listado_Recursos_Generacion.xlsx` |",
        "| **Ministerio de Minas / datos abiertos** | precios de GNCV | "
        "`data/Consulta_Precios_Promedio_de_Gas_Natural_*.csv` |",
        "| **NOAA CPC** | índice ONI de El Niño | `data/oni_noaa.csv` (ya en el panel base) |",
        "| **Banco de la República** | TRM | `data/Tasa de cambio del peso colombiano.csv` (ya en el panel base) |",
        "",
        "---",
        "",
    ]

    grupos = {}
    for r in REGISTRO:
        grupos.setdefault(r["grupo"], []).append(r)

    for grupo, items in grupos.items():
        lineas += [f"## {grupo}", ""]
        for r in items:
            v = r["variable"]
            c = cob.get(v, float("nan"))
            ini, fin = rango.get(v, (None, None))
            lineas += [
                f"### `{v}`",
                "",
                f"**{r['significado']}**",
                "",
                f"- **Unidad:** {r['unidad']}",
                f"- **Fuente:** {r['fuente']}",
                f"- **Cálculo:** {r['calculo']}",
            ]
            if ini is not None:
                lineas.append(f"- **Cobertura:** {c:.1%} de los días "
                              f"({ini.date()} a {fin.date()})")
            if r["aviso"]:
                lineas += ["", f"> **Advertencia.** {r['aviso']}"]
            lineas += [""]
        lineas += ["---", ""]

    lineas += [
        "## Variables de XM que NO se descargaron",
        "",
        "El catálogo de la API (`cache_api/catalogo_metricas.parquet`, 193 métricas, "
        "98 a nivel de Sistema) tiene más series que podrían agregarse. Las que "
        "parecen más prometedoras para el pronóstico del precio:",
        "",
        "| MetricId | Qué es | Por qué podría servir |",
        "|---|---|---|",
        "| `DemaMaxPot` | Demanda máxima de potencia (kW) | el pico de potencia es "
        "lo que agota la capacidad disponible |",
        "| `VolTurbMasa` | Volumen turbinado (m³) | uso real del agua, no solo el "
        "nivel almacenado |",
        "| `CompNetArranPara` | Compras netas de arranque y parada (COP) | costo de "
        "encender térmicas, señal de rigidez del parque |",
        "| `DeltaNal` / `DeltaInt` | Delta de incremento nacional / internacional | "
        "componentes del precio, se conocen por regulación |",
        "| `RentasCongestRestr` | Rentas de congestión (COP) | congestión de la red, "
        "que separa precios regionales |",
        "| `CompBolsNaciEner` / `VentBolsNaciEner` | energía comprada y vendida en "
        "bolsa (kWh) | volumen transado, mide liquidez del mercado spot |",
        "| `PrecEscaSup` | Precio de escasez superior | falta esta variante; el panel "
        "ya tiene inferior, activación, ponderado y marginal |",
        "| `RemuRealIndiv` | Remuneración real individual diaria (COP) | ingreso por "
        "cargo por confiabilidad |",
        "| `SnTIEMerito` / `SnTIEFueraMerito` | saldo neto de transacciones "
        "internacionales | intercambio con Ecuador |",
        "| `GeneIdea` | Generación ideal (sin restricciones de red) | la brecha contra "
        "la generación real mide cuánto cuesta la red |",
        "",
        "Para bajarlas hay que extender `00_consolidar_panel.py` con el `MetricId` y "
        "la entidad correspondientes. El costo es una llamada más a la API por métrica.",
        "",
        "### Fuentes externas que valdría explorar",
        "",
        "- **Precio del gas natural industrial** (no el vehicular): es el costo "
        "marginal real de las térmicas a gas. Lo publica la Bolsa Mercantil de "
        "Colombia y en los informes de la CREG; no está en la API de XM.",
        "- **Henry Hub** (referencia internacional de gas): el panel base tiene un "
        "prefijo `henry_hub` previsto en la configuración pero la serie no está "
        "descargada. Fuente: EIA de Estados Unidos.",
        "- **Caudales del IDEAM**: aportes medidos en estación, con más resolución "
        "espacial que los agregados de XM por río.",
        "- **Índices ENSO alternativos** (SOI, Niño 3.4, MEI): el panel usa solo ONI. "
        "Fuente: NOAA CPC.",
        "",
    ]

    SALIDA_MD.write_text("\n".join(lineas), encoding="utf-8")


if __name__ == "__main__":
    main()
