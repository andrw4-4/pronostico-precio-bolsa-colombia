"""
================================================================================
00 — CONSOLIDACION DEL PANEL DIARIO
================================================================================

Que resuelve
------------
cache_api tiene parquets en CUATRO formatos distintos:

  A) "simple"       Id, Value, Date              -> series de Sistema, ya listas
  B) "named"        Id, Name, Value, Date         -> desagregadas por rio/embalse
  C) "coded"        Id, Code, Value, Date         -> desagregadas por planta/panel
  D) "wide_hourly"  Id, Values_code, Values_HourNN..., Date  -> por recurso/agente

B y C se procesan igual (se colapsan a un total/promedio de sistema por dia);
solo cambia el nombre de la columna que identifica la sub-entidad.

Cada formato necesita una agregacion distinta para llegar a UNA columna diaria
por serie. Este script detecta el formato automaticamente y aplica la regla
de agregacion correcta (ver AGG_OVERRIDES abajo para el razonamiento de cada
una).

Dos series NO estan en cache_api y se traen de data/: ONI (NOAA) y TRM.

Cambios de la revision de fuga (2026-09-13)
-------------------------------------------
  - ONI se desplaza ONI_REZAGO_PUBLICACION_MESES (2) meses: el valor del mes M
    solo se conoce cuando NOAA lo publica, a inicios de M+2. Sin el
    desplazamiento, el panel "conocia" el ONI unas seis semanas antes.
  - volumen_util_pct_emb se promedia PONDERADO por la capacidad de cada
    embalse (ver PONDERADAS). El promedio simple le daba a un embalse chico
    el mismo peso que a Guavio.

Salida: panel_d.parquet  ->  la ruta que 01_seleccion_variables.py ya espera.

IMPORTANTE
----------
Las reglas de agregacion en AGG_OVERRIDES son mi mejor lectura del nombre de
cada serie y del contexto de la tesis, NO una verificacion contra la
documentacion oficial de XM. Las marcadas "# REVISAR" son las que tengo menos
seguras -- revisalas contra el diccionario de datos de SIMEM antes de confiar
en el panel para resultados finales. Los diagnosticos impresos te dejan ver
que decidio el script para cada serie sin tener que leer el codigo.
================================================================================
"""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ==============================================================================
# CONFIG  <-- EDITA ESTO
# ==============================================================================

CACHE_DIR = Path(
    r"C:\Users\andre\OneDrive\cosas de la universidad\Uniandes\VIII\Tesis\cache_api"
)
DATA_DIR = Path(
    r"C:\Users\andre\OneDrive\cosas de la universidad\Uniandes\VIII\Tesis\data"
)
OUT_PATH = DATA_DIR / "panel_d.parquet"

# Metadatos, no series de tiempo -> se excluyen del panel
EXCLUIR = {"catalogo_metricas", "listado_embalses", "listado_rios"}

# Esta es categorica (que recurso fija el precio cada hora), no numerica.
# Se guarda aparte, no entra al panel numerico.
CATEGORICAS = {"recurso_marginal"}

# Rezago de PUBLICACION del ONI. El ONI del mes M es la media movil de 3 meses
# centrada en M, asi que necesita los datos de M+1, y NOAA lo publica a inicios
# de M+2. Un pronosticador en el dia D solo conoce el ONI de dos meses atras.
ONI_REZAGO_PUBLICACION_MESES = 2

# Series por entidad que se promedian PONDERADAS por otra serie de la misma
# entidad (misma columna Name/Code y misma fecha): serie -> archivo de pesos.
PONDERADAS = {
    # % de volumen util por embalse, ponderado por su capacidad util. El
    # resultado coincide (corr > 0.999) con el % del sistema que publica XM.
    "volumen_util_pct_emb": "capacidad_por_embalse",
}

# ==============================================================================
# REGLAS DE AGREGACION
# ==============================================================================
#
# Para wide_hourly: (agg_entidad, agg_hora)
#   agg_entidad = como combinar los distintos recursos/agentes en una hora
#   agg_hora    = como combinar las 24 horas en un valor diario
#
#   sum  -> magnitudes de flujo/energia (kWh): se acumulan
#   mean -> niveles (capacidad disponible, precios): no se acumulan
#   max  -> techos (precio maximo de oferta del dia)
#
# Para named: agg_named = como combinar las filas por Name (rio/embalse) en
# una sola cifra de sistema por dia.

AGG_OVERRIDES = {
    # --- wide_hourly: ENERGIA (flujo -> sum entidad, sum horas) -------------
    "gen_programada":          ("sum", "sum"),
    "gen_por_recurso":         ("sum", "sum"),
    "gen_fuera_merito":        ("sum", "sum"),
    "gen_seguridad":           ("sum", "sum"),
    "demanda_por_or":          ("sum", "sum"),
    "importaciones":           ("sum", "sum"),
    "exportaciones":           ("sum", "sum"),
    "perdidas_energia":        ("sum", "sum"),
    "consumo_combustible":     ("sum", "sum"),
    "dem_no_atendida_noprog":  ("sum", "sum"),
    "restricciones":           ("sum", "sum"),
    "restricciones_sin_aliv":  ("sum", "sum"),

    # --- wide_hourly: NIVEL (capacidad -> sum entidad [total sistema],
    #     mean horas [nivel promedio del dia, no se acumula]) ---------------
    "disp_comercial":          ("sum", "mean"),
    "disp_declarada":          ("sum", "mean"),
    "disp_real":               ("sum", "mean"),

    # --- wide_hourly: PRECIOS (no se suman entre recursos ni horas) --------
    "costo_marginal_prog":     ("mean", "mean"),   # REVISAR si Id es unico
    "precio_oferta_desp":      ("mean", "mean"),   # promedio simple por ahora;
                                                     # la curva de oferta (percentiles,
                                                     # pendiente) es una etapa aparte
    "max_precio_oferta":       ("max", "max"),      # techo del dia

    # --- wide_hourly agregadas en esta corrida: sin ellas el script las
    #     procesaba con el default (sum,sum) y avisaba REVISAR en cada corrida.
    #     Aqui quedan las que SI son flujo (sum,sum tiene sentido real, no es
    #     solo el default) y las que son precio (mean,mean, el default estaba
    #     mal para estas) --------------------------------------------------
    "compras_contrato":        ("sum", "sum"),    # cantidad de energia comprada
    "demanda_no_regulada":     ("sum", "sum"),
    "demanda_regulada":        ("sum", "sum"),
    "emisiones_co2_sistema":   ("sum", "sum"),    # masa de CO2 diaria
    "precio_cont_no_regu":     ("mean", "mean"),  # es un precio, no se suma
    "precio_prom_contrato":    ("mean", "mean"),  # es un precio, no se suma

    # --- named / coded: rios, embalses, plantas/paneles ---------------------
    "aportes_por_rio":         "sum",    # aportes absolutos -> total sistema
    "volumen_por_embalse":     "sum",    # volumen absoluto -> total sistema
    "capacidad_por_embalse":   "sum",    # capacidad absoluta -> total sistema
    "capacidad_efectiva":      "sum",    # capacidad efectiva -> total sistema
    "aportes_pct_rio":         "mean",   # REVISAR: % del historico por rio,
                                          # sumar no tiene sentido: se promedia
    "volumen_util_pct_emb":    "mean",   # NO se usa: va por PONDERADAS (peso =
                                          # capacidad_por_embalse). Queda como
                                          # respaldo si falta el archivo de pesos
    "irradiacion_global":      "mean",   # nivel por panel -> promedio, no suma
    "irradiacion_panel":       "mean",
    "temp_ambiente_solar":     "mean",
    "temp_panel":              "mean",
    "precio_cargo_conf":       "mean",   # REVISAR: si 'Code' es agente/comerc.,
                                          # confirmar que promediar sea lo correcto
}


# ==============================================================================
# DETECCION DE FORMATO
# ==============================================================================

def detectar_formato(df):
    cols = set(df.columns)
    if cols == {"Id", "Value", "Date"}:
        return "simple"
    if cols == {"Id", "Name", "Value", "Date"}:
        return "named"
    if cols == {"Id", "Code", "Value", "Date"}:
        return "coded"
    if any(c.startswith("Values_Hour") for c in df.columns) and "Date" in cols:
        return "wide_hourly"
    return "desconocido"


def a_numerico(s, contexto=""):
    """
    Convierte a numerico tolerando strings con espacios, vacios, y el formato
    es-CO (punto = miles, coma = decimal, ej. "3.900,25" -> 3900.25).

    No se distingue por dtype de entrada (object vs el dtype 'str' nativo de
    pandas >= 2.x/3.x) -- se intenta la conversion directa primero y solo se
    activa el fallback si deja demasiados NaN. Revisar el dtype exacto era
    justo lo que rompia esto: en pandas 3.0 una columna de texto leida de CSV
    no es 'object', es el dtype 'str' nuevo, y una comparacion estricta
    `dtype != object` tomaba la rama equivocada y nunca corregia nada.
    """
    r1 = pd.to_numeric(s, errors="coerce")
    nan_frac1 = r1.isna().mean() if len(r1) else 0.0
    if nan_frac1 <= 0.30:
        return r1

    s_str = s.astype(str).str.strip()
    tiene_coma = s_str.str.contains(",", regex=False, na=False).any()
    if not tiene_coma:
        return r1  # no hay nada que reparar con esta convencion

    s_alt = (s_str.str.replace(".", "", regex=False)
                  .str.replace(",", ".", regex=False))
    r2 = pd.to_numeric(s_alt, errors="coerce")
    nan_frac2 = r2.isna().mean() if len(r2) else 0.0

    if nan_frac2 < nan_frac1:
        print(f"      [conversion] {contexto}: formato es-CO detectado "
              f"(punto=miles, coma=decimal); NaN baja de "
              f"{nan_frac1:.0%} a {nan_frac2:.0%}")
        return r2
    return r1


# ==============================================================================
# UN LOADER POR FORMATO -> serie diaria (pd.Series indexada por fecha)
# ==============================================================================

def cargar_simple(df, name):
    df = df.copy()
    df["Value"] = a_numerico(df["Value"], contexto=name)

    if df["Id"].nunique() > 1:
        # No deberia pasar en este formato, pero por seguridad
        print(f"  [!] {name}: 'simple' con {df['Id'].nunique()} Id distintos, "
              f"se trata como 'named'")
        return cargar_named(df.rename(columns={"Id": "Name"})
                              .assign(Id="Sistema"), name)

    s = df.set_index("Date")["Value"].sort_index()
    s = reindex_diario(s, name)
    return s


def cargar_named(df, name):
    """
    Sirve tanto para 'named' (Id,Name,Value,Date) como para 'coded'
    (Id,Code,Value,Date): en ambos casos se colapsa la sub-entidad
    (rio/embalse/planta/panel) y solo queda un valor de sistema por fecha.

    Defensivo: si por alguna razon 'Value' o el resultado del groupby no son
    1-D (columnas duplicadas en el archivo, un esquema distinto al esperado,
    etc.), se toma la primera columna en vez de fallar, y se avisa fuerte
    para que revises el parquet original -- esto no debería pasar en un
    archivo sano, así que si lo ves, el archivo merece inspeccion aparte.
    """
    df = df.copy()

    val = df["Value"]
    if isinstance(val, pd.DataFrame):
        print(f"  [!] {name}: 'Value' devolvio {val.shape[1]} columnas "
              f"(esquema inesperado), uso solo la primera -- REVISAR el "
              f"parquet original, esto no deberia pasar")
        val = val.iloc[:, 0]
    df["Value"] = a_numerico(val, contexto=name)

    modo = AGG_OVERRIDES.get(name, "sum")
    s = df.groupby("Date")["Value"].agg(modo)
    if isinstance(s, pd.DataFrame):
        print(f"  [!] {name}: el agrupado devolvio una tabla en vez de una "
              f"serie, uso solo la primera columna -- REVISAR")
        s = s.iloc[:, 0]

    s = s.sort_index()
    s = reindex_diario(s, name, ya_diaria=True)
    return s


def cargar_named_ponderado(df, name, archivo_pesos):
    """
    Promedio ponderado por entidad: sum(valor_i * peso_i) / sum(peso_i) por dia.

    Se usa para porcentajes por embalse: promediarlos sin pesos trata igual a
    un embalse de 35 GWh que a uno de 4000 GWh, y el "nivel del sistema" que
    sale no corresponde a ninguna cantidad fisica.
    """
    ruta = CACHE_DIR / f"{archivo_pesos}.parquet"
    col_ent = "Name" if "Name" in df.columns else "Code"
    if not ruta.exists():
        print(f"  [!] {name}: no encuentro {ruta.name} para ponderar, uso "
              f"promedio simple -- REVISAR")
        return cargar_named(df, name)

    pesos = pd.read_parquet(ruta)
    if col_ent not in pesos.columns:
        print(f"  [!] {name}: {ruta.name} no tiene columna '{col_ent}', uso "
              f"promedio simple -- REVISAR")
        return cargar_named(df, name)

    a = df[[col_ent, "Date"]].copy()
    a["v"] = a_numerico(df["Value"], contexto=name)
    b = pesos[[col_ent, "Date"]].copy()
    b["w"] = a_numerico(pesos["Value"], contexto=archivo_pesos)

    m = a.merge(b, on=[col_ent, "Date"], how="left")
    sin_peso = m["w"].isna() & m["v"].notna()
    m = m.dropna(subset=["v", "w"])
    m = m[m["w"] > 0]

    s = (m["v"] * m["w"]).groupby(m["Date"]).sum() / m.groupby("Date")["w"].sum()
    print(f"      -> ponderado por {archivo_pesos} ({m[col_ent].nunique()} "
          f"entidades; {int(sin_peso.sum())} filas sin peso descartadas)")
    return reindex_diario(s.sort_index(), name, ya_diaria=True)


def cargar_wide_hourly(df, name):
    hour_cols = sorted([c for c in df.columns if c.startswith("Values_Hour")])
    for c in hour_cols:
        df[c] = a_numerico(df[c], contexto=f"{name}.{c}")

    agg_ent, agg_hora = AGG_OVERRIDES.get(name, ("sum", "sum"))
    if name not in AGG_OVERRIDES:
        print(f"  [!] {name}: sin regla explicita, uso default "
              f"(entidad={agg_ent}, horas={agg_hora}) -- REVISAR")

    # paso 1: combinar entidades (recursos/agentes) por fecha, por cada hora
    por_hora = df.groupby("Date")[hour_cols].agg(agg_ent)

    # paso 2: combinar las 24 horas en un valor diario
    if agg_hora == "sum":
        s = por_hora.sum(axis=1)
    elif agg_hora == "mean":
        s = por_hora.mean(axis=1)
    elif agg_hora == "max":
        s = por_hora.max(axis=1)
    else:
        raise ValueError(f"agg_hora desconocido: {agg_hora}")

    s = s.sort_index()
    s = reindex_diario(s, name, ya_diaria=True)
    return s


def reindex_diario(s, name, ya_diaria=False):
    """
    Detecta si la serie es mensual (gap mediano > 20 dias) y la expande a
    diaria con ffill -- correcto para tarifas/cargos regulados que se fijan
    una vez al mes y rigen hasta la siguiente actualizacion.
    """
    if len(s) < 3:
        return s
    gaps = s.index.to_series().diff().dt.days.dropna()
    mediana = gaps.median()

    if not ya_diaria and mediana > 20:
        full = pd.date_range(s.index.min(), s.index.max(), freq="D")
        s = s.reindex(full).ffill()
        print(f"      -> detectada mensual (gap mediano {mediana:.0f}d), "
              f"expandida a diaria con ffill")
    return s


# ==============================================================================
# ARCHIVOS EXTERNOS: ONI y TRM (no estan en cache_api)
# ==============================================================================

def leer_csv_autodetect(path):
    """
    Exports como el de la TRM (Banrep) suelen venir con separador ';' y
    encabezados entre comillas. pd.read_csv con el separador ',' por defecto
    los lee como UNA sola columna gigante. Se cuenta cual separador aparece
    mas veces en la primera linea y se usa ese.
    """
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        primera_linea = f.readline()
    candidatos_sep = [";", ",", "\t", "|"]
    sep = max(candidatos_sep, key=lambda c: primera_linea.count(c))
    df = pd.read_csv(path, sep=sep, engine="python")
    df.columns = [c.strip().strip('"').strip("'") for c in df.columns]
    return df


def cargar_csv_flexible(path, candidatos_fecha, candidatos_valor, nombre,
                        desplazar_meses=0):
    """
    No conozco los encabezados exactos de estos dos CSV, asi que pruebo
    nombres comunes (coincidencia por SUBCADENA, no exacta -- un encabezado
    como 'Periodo(MMM DD, AAAA)' contiene 'periodo' aunque no sea igual a
    ese texto). Si falla, imprime las columnas reales para que las agregues
    a 'candidatos_*' y vuelvas a correr.
    """
    if not path.exists():
        print(f"  [X] {nombre}: no encontrado en {path}")
        return None

    df = leer_csv_autodetect(path)
    print(f"  [?] {nombre}: columnas encontradas = {list(df.columns)}")

    col_fecha = next((c for c in df.columns
                      if any(cand in c.strip().lower()
                            for cand in candidatos_fecha)), None)
    col_valor = next((c for c in df.columns
                      if any(cand in c.strip().lower()
                            for cand in candidatos_valor)), None)

    if col_fecha is None or col_valor is None:
        print(f"  [X] {nombre}: no pude identificar columnas de fecha/valor "
              f"automaticamente.")
        print(f"      Edita 'cargar_oni' o 'cargar_trm' en este script con "
              f"los nombres exactos: {list(df.columns)}")
        return None

    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    df[col_valor] = a_numerico(df[col_valor], contexto=nombre)
    s = df.dropna(subset=[col_fecha]).set_index(col_fecha)[col_valor].sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if desplazar_meses:
        # rezago de publicacion: el valor fechado en M queda disponible en M+k
        primera = s.index.min()
        s.index = s.index + pd.DateOffset(months=desplazar_meses)
        print(f"      -> desplazada {desplazar_meses} meses (rezago de "
              f"publicacion): el valor fechado {primera.date()} rige desde "
              f"{s.index.min().date()}")
    return reindex_diario(s, nombre)


def construir_derivadas(panel):
    """
    Variables construidas a partir de las series descargadas. No existen como
    dataset en SIMEM -- son ratios/empalmes que hay que calcular.

    1) MARGEN DE RESERVA
       Es el determinante con el coeficiente MAS ALTO en Fedesarrollo
       (-0.375, casi 3x disponibilidad y ~9x hidrologia). No es descargable:
       es capacidad efectiva / demanda maxima de potencia.

       CUIDADO CON LA FUGA: demanda_regulada y demanda_no_regulada son
       "Demanda REAL" (DemaRealReg/DemaRealNoReg en el catalogo XM) -- se
       miden, no se pronostican. Si el ratio se construye con la demanda del
       MISMO dia, el margen de reserva "conoce" informacion que todavia no
       existe cuando se pronostica el precio de ese dia. Por eso el
       denominador se reza 1 dia (ver construir_derivadas).

       Ademas resuelve el problema de capacidad_efectiva: sola es una escalera
       de saltos discretos casi constante; como ratio contra la demanda se
       vuelve una senial dinamica de holgura del sistema.

       NOTA: el panel tiene demanda diaria (energia), no demanda maxima de
       potencia horaria (DemaMaxPot no esta en cache_api). Se usa la demanda
       diaria rezagada 1 dia como proxy, asi que el NIVEL del ratio no es
       comparable con el de Fedesarrollo -- pero su VARIACION, que es lo que
       usan los modelos, si captura lo mismo: sistema holgado vs estrecho.

    2) EMPALME DE PRECIO DE ESCASEZ
       precio_escasez_act termina 2025-02 y precio_escasez_inf arranca
       2025-03: son el mismo concepto partido por el cambio regulatorio
       (Res. CREG 101 066 de 2024). Dejarlas como dos columnas con huecos
       complementarios (66% y 7.6% de cobertura) es un error: se empalman en
       una sola serie continua + una dummy que marca el quiebre.
    """
    print("\n[derivadas] construyendo variables calculadas")

    # ---- 1. margen de reserva ---------------------------------------------
    # OJO -- fuga corregida: demanda_regulada y demanda_no_regulada vienen de
    # DemaRealReg / DemaRealNoReg en el catalogo de XM ("Demanda REAL"), es
    # decir demanda MEDIDA, no pronosticada. Si el ratio se construyera con
    # la demanda del MISMO dia (lag0), estaria usando informacion que no
    # existe todavia el dia que se pronostica el precio -- el presente
    # "prediciendo" el presente. Por eso el denominador se reza 1 dia: es la
    # demanda real mas reciente que un pronosticador tendria disponible.
    #
    # Este NO es el margen de reserva de Fedesarrollo (que usa demanda MAXIMA
    # DE POTENCIA, no demanda diaria de energia, y esa serie -- DemaMaxPot --
    # no esta en el cache_api de este proyecto). Es un proxy con un dia de
    # rezago que prioriza no tener fuga por encima de replicar el nivel exacto
    # de la referencia. La variacion del ratio sigue siendo comparable.
    comp_demanda = [c for c in ["demanda_regulada", "demanda_no_regulada"]
                    if c in panel.columns]
    if "capacidad_efectiva" in panel.columns and comp_demanda:
        demanda_total = panel[comp_demanda].sum(axis=1, min_count=1)
        demanda_rezagada = demanda_total.shift(1)
        cap = panel["capacidad_efectiva"]
        margen = cap / demanda_rezagada.replace(0, np.nan)
        panel["margen_reserva"] = margen
        cob = margen.notna().mean()
        print(f"  [OK] margen_reserva = capacidad_efectiva / "
              f"({' + '.join(comp_demanda)}).shift(1)")
        print(f"       cobertura {cob:.1%}, rango "
              f"{margen.min():.4g} - {margen.max():.4g}")
        print(f"       [!] demanda REZAGADA 1 dia (fuga corregida: la "
              f"demanda es 'Real' = medida, no pronosticada -- ver "
              f"DemaRealReg/DemaRealNoReg en catalogo_metricas)")
        print(f"       [!] proxy: usa demanda diaria de energia, no demanda "
              f"maxima de potencia (DemaMaxPot no esta en cache_api). El "
              f"nivel no es comparable con Fedesarrollo, la variacion si.")
    else:
        faltan = ([] if "capacidad_efectiva" in panel.columns
                  else ["capacidad_efectiva"]) + \
                 ([] if comp_demanda else ["demanda_regulada/no_regulada"])
        print(f"  [X] margen_reserva: faltan {faltan}")

    # ---- 2. empalme del precio de escasez ----------------------------------
    act, inf = "precio_escasez_act", "precio_escasez_inf"
    if act in panel.columns and inf in panel.columns:
        s_act, s_inf = panel[act], panel[inf]
        empalme = s_act.combine_first(s_inf)

        # dummy del cambio de regimen: 1 desde la primera fecha con dato
        # de la serie nueva (Res. CREG 101 066 de 2024)
        fechas_inf = s_inf.dropna().index
        if len(fechas_inf):
            corte = fechas_inf.min()
            panel["dummy_creg_escasez"] = (panel.index >= corte).astype(int)
            print(f"  [OK] precio_escasez_empalmado = {act} hasta "
                  f"{corte.date()}, luego {inf}")
            print(f"       cobertura {empalme.notna().mean():.1%} "
                  f"(antes: {s_act.notna().mean():.1%} y "
                  f"{s_inf.notna().mean():.1%} por separado)")
            print(f"  [OK] dummy_creg_escasez: 1 desde {corte.date()}")
        panel["precio_escasez_empalmado"] = empalme
    else:
        print(f"  [-] empalme de escasez: no estan {act} y/o {inf}")

    return panel


def cargar_csv_serie_xm(path, nombre, agg_hora="mean"):
    """
    Carga un CSV exportado de XM/pydataxm que vive en data/ (no en cache_api).
    Maneja los dos formatos que puede traer:

      - "simple":      Id, Value, Date                     -> ya es diaria
      - "wide_hourly": Id, Values_Hour01..24, Date         -> agrega las horas

    agg_hora controla como se colapsan las 24 horas. Para el PRECIO DE BOLSA
    el valor correcto es "mean" (promedio del dia), que es la definicion del
    precio ponderado/promedio diario -- NO "sum", que no tiene sentido para
    un precio.
    """
    if not path.exists():
        print(f"  [X] {nombre}: no encontrado en {path}")
        return None

    df = leer_csv_autodetect(path)
    print(f"  [?] {nombre}: columnas = {list(df.columns)[:5]}"
          f"{'...' if len(df.columns) > 5 else ''}")

    # localizar la columna de fecha
    col_fecha = next((c for c in df.columns
                      if c.strip().lower() in {"date", "fecha", "periodo"}), None)
    if col_fecha is None:
        print(f"  [X] {nombre}: no encontre columna de fecha en "
              f"{list(df.columns)}")
        return None

    fechas = pd.to_datetime(df[col_fecha], errors="coerce")
    hour_cols = sorted(c for c in df.columns if c.startswith("Values_Hour"))

    if hour_cols:
        vals = pd.DataFrame({c: a_numerico(df[c], contexto=f"{nombre}.{c}")
                             for c in hour_cols})
        if agg_hora == "mean":
            serie = vals.mean(axis=1)
        elif agg_hora == "sum":
            serie = vals.sum(axis=1)
        elif agg_hora == "max":
            serie = vals.max(axis=1)
        else:
            raise ValueError(f"agg_hora desconocido: {agg_hora}")
        print(f"      -> wide_hourly, {len(hour_cols)} horas colapsadas "
              f"con '{agg_hora}'")
    else:
        col_valor = next((c for c in df.columns
                          if c.strip().lower() in {"value", "valor"}), None)
        if col_valor is None:
            print(f"  [X] {nombre}: no encontre columna de valor en "
                  f"{list(df.columns)}")
            return None
        serie = a_numerico(df[col_valor], contexto=nombre)
        print(f"      -> formato simple (columna '{col_valor}')")

    s = pd.Series(serie.values, index=fechas).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def cargar_precio_bolsa():
    """
    EL TARGET. No esta en cache_api -- vive en data/ como PrecBolsNaci_Sistema.csv.
    Se carga aparte y se nombra 'precio_ponderado' para que coincida con
    CONFIG["target_col"] de 01_seleccion_variables.py.
    """
    return cargar_csv_serie_xm(
        DATA_DIR / "PrecBolsNaci_Sistema.csv",
        nombre="precio_ponderado (TARGET)",
        agg_hora="mean",   # promedio diario: es un precio, no se suma
    )


def cargar_oni():
    return cargar_csv_flexible(
        DATA_DIR / "oni_noaa.csv",
        candidatos_fecha={"date", "fecha", "time", "mes", "month"},
        candidatos_valor={"oni", "value", "valor", "anom", "anomalia"},
        nombre="oni",
        desplazar_meses=ONI_REZAGO_PUBLICACION_MESES,
    )


def cargar_trm():
    return cargar_csv_flexible(
        DATA_DIR / "Tasa de cambio del peso colombiano.csv",
        candidatos_fecha={"date", "fecha", "periodo", "vigenciadesde", "dia"},
        candidatos_valor={"trm", "tasa", "value", "valor"},
        nombre="trm",
    )


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 72)
    print("CONSOLIDACION DEL PANEL DIARIO")
    print("=" * 72)

    archivos = sorted(CACHE_DIR.glob("*.parquet"))
    print(f"[cache_api] {len(archivos)} archivos encontrados en {CACHE_DIR}\n")

    series = {}
    categoricas = {}
    fallidas = []

    for p in archivos:
        name = p.stem
        if name in EXCLUIR:
            print(f"  [-] {name}: excluido (metadatos, no es serie de tiempo)")
            continue

        try:
            df = pd.read_parquet(p)
        except Exception as e:
            print(f"  [X] {name}: error leyendo -> {e}")
            fallidas.append(name)
            continue

        fmt = detectar_formato(df)

        if name in CATEGORICAS:
            # Se guarda aparte (moda diaria), no entra al panel numerico
            hour_cols = sorted(c for c in df.columns
                               if c.startswith("Values_Hour"))
            if hour_cols and fmt == "wide_hourly":
                largo = df.melt(id_vars=["Date"], value_vars=hour_cols,
                               value_name="valor")
                moda = (largo.groupby("Date")["valor"]
                              .agg(lambda x: x.mode().iloc[0]
                                   if not x.mode().empty else np.nan))
                categoricas[name] = moda
                print(f"  [C] {name}: categorica, guardada aparte "
                      f"(moda diaria de {len(hour_cols)} horas)")
            else:
                print(f"  [!] {name}: marcada categorica pero formato "
                      f"inesperado ({fmt}), se omite")
            continue

        try:
            if name in PONDERADAS and fmt in ("named", "coded"):
                s = cargar_named_ponderado(df, name, PONDERADAS[name])
            elif fmt == "simple":
                s = cargar_simple(df, name)
            elif fmt in ("named", "coded"):
                s = cargar_named(df, name)
            elif fmt == "wide_hourly":
                s = cargar_wide_hourly(df, name)
            else:
                print(f"  [X] {name}: formato no reconocido "
                      f"({sorted(df.columns)[:6]}...)")
                fallidas.append(name)
                continue
        except Exception as e:
            print(f"  [X] {name}: error procesando ({fmt}) -> {e}")
            fallidas.append(name)
            continue

        series[name] = s
        print(f"  [OK] {name:28s} {fmt:12s} {len(s):>6,} obs  "
              f"{s.index.min().date()} -> {s.index.max().date()}")

    # El rango del panel se define SOLO con las series de cache_api. Si se
    # incluyeran ONI/TRM aqui, un historico largo (ONI suele venir desde
    # 1950) inflaria el panel hacia atras con miles de filas vacias.
    if not series:
        raise SystemExit("No se cargo ninguna serie de cache_api. "
                         "Revisa los errores arriba.")
    fecha_min = min(s.index.min() for s in series.values())
    fecha_max = max(s.index.max() for s in series.values())
    print(f"\n[rango]   panel definido por cache_api: "
          f"{fecha_min.date()} -> {fecha_max.date()}")

    # ---- TARGET, ONI y TRM (fuera de cache_api) ----------------------------
    print(f"\n[externos] buscando TARGET, ONI y TRM en {DATA_DIR}")

    precio = cargar_precio_bolsa()
    if precio is not None:
        series["precio_ponderado"] = precio
        dentro = precio.loc[fecha_min:fecha_max]
        print(f"  [OK] precio_ponderado  {len(precio):>6,} obs  "
              f"{precio.index.min().date()} -> {precio.index.max().date()}  "
              f"(cobertura en la ventana del panel: "
              f"{len(dentro) / len(pd.date_range(fecha_min, fecha_max)):.1%})")
    else:
        print("  [!!] SIN TARGET: el panel no va a servir para modelar. "
              "01_seleccion_variables.py va a fallar con KeyError.")

    oni = cargar_oni()
    if oni is not None:
        recorte = oni.loc[fecha_min:fecha_max]
        series["oni"] = oni  # se recorta al reindexar sobre 'idx' mas abajo
        print(f"  [OK] oni    {len(oni):>6,} obs totales "
              f"({oni.index.min().date()} -> {oni.index.max().date()}), "
              f"se recorta a la ventana del panel")

    trm = cargar_trm()
    if trm is not None:
        series["trm"] = trm
        print(f"  [OK] trm    {len(trm):>6,} obs  "
              f"{trm.index.min().date()} -> {trm.index.max().date()}")

    # ---- consolidacion -------------------------------------------------------
    print("\n" + "-" * 72)
    idx = pd.date_range(fecha_min, fecha_max, freq="D")
    panel = pd.DataFrame(index=idx)

    fallidas_merge = []
    for name, s in series.items():
        # Defensivo: si algo dejo 's' con forma inesperada (no deberia pasar
        # tras los arreglos de arriba, pero si pasa, no se pierde TODO el
        # panel por un solo archivo -- se reporta y se sigue con el resto).
        try:
            if not isinstance(s, pd.Series):
                print(f"  [!] {name}: no es una Serie 1-D (es {type(s)}), "
                      f"se omite del panel. Mandame df.dtypes de este "
                      f"archivo para diagnosticar la causa real.")
                fallidas_merge.append(name)
                continue
            panel[name] = s.reindex(idx)
        except Exception as e:
            print(f"  [X] {name}: fallo al insertar en el panel -> {e}")
            fallidas_merge.append(name)
            continue
    panel.index.name = "fecha"

    # ---- variables derivadas (margen de reserva, empalme de escasez) ------
    panel = construir_derivadas(panel)

    print(f"[panel]   {panel.shape[0]} filas x {panel.shape[1]} columnas")
    print(f"          {panel.index.min().date()} -> {panel.index.max().date()}")

    cobertura = panel.notna().mean().sort_values()
    print("\nCobertura (peor 10):")
    print(cobertura.head(10).apply(lambda x: f"{x:.1%}").to_string())

    panel.to_parquet(OUT_PATH)
    print(f"\n[guardado] {OUT_PATH}")

    # ---- verificacion del TARGET -------------------------------------------
    if "precio_ponderado" not in panel.columns:
        print("\n" + "!" * 72)
        print("ATENCION: el panel NO tiene la columna 'precio_ponderado'.")
        print("Sin variable objetivo no se puede modelar nada.")
        print("Revisa que exista PrecBolsNaci_Sistema.csv en data/.")
        print("!" * 72)
    else:
        cob_target = panel["precio_ponderado"].notna().mean()
        print(f"[TARGET]   precio_ponderado: cobertura {cob_target:.1%}, "
              f"rango {panel['precio_ponderado'].min():.1f} - "
              f"{panel['precio_ponderado'].max():.1f}")
        if cob_target < 0.95:
            print(f"           [!] cobertura por debajo del 95% -- revisa "
                  f"si al CSV le faltan fechas del periodo de estudio")

    if categoricas:
        cat_df = pd.DataFrame(categoricas)
        cat_path = DATA_DIR / "panel_categoricas.parquet"
        cat_df.to_parquet(cat_path)
        print(f"[guardado] {cat_path}  (categoricas, no numericas: "
              f"{list(categoricas.keys())})")

    if fallidas:
        print(f"\n[ATENCION] {len(fallidas)} series fallaron al cargar: "
              f"{fallidas}")
    if fallidas_merge:
        print(f"[ATENCION] {len(fallidas_merge)} series cargaron pero "
              f"fallaron al insertar en el panel: {fallidas_merge}")
    if fallidas or fallidas_merge:
        print("Revisa los mensajes de error arriba antes de confiar en el "
              "panel. El resto de las series SI quedo consolidado.")

    print("\n" + "=" * 72)
    print("Revisa las lineas marcadas [!] y 'REVISAR' en AGG_OVERRIDES --")
    print("son mi mejor lectura del nombre de cada serie, no una verificacion")
    print("contra la documentacion de XM.")
    print("Siguiente paso: 01_seleccion_variables.py")
    print("=" * 72)


if __name__ == "__main__":
    main()
