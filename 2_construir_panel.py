"""
Paso 2 de 3: construir el panel diario.

Toma lo que bajó 1_descargar.py y arma una sola tabla con una fila por día y
una columna por variable: panel_diario.csv.

Aquí todavía no hay rezagos ni nada pensado para el modelo; eso lo hace
features.py. Este paso solo pone todas las fuentes en la misma escala (un
valor por día) y calcula algunas variables que no vienen hechas en ninguna
fuente: la mezcla de generación, la concentración del mercado, el perfil de
precios dentro del día o la forma de la curva de oferta.

Partes:
    1. Series de XM llevadas a un valor por día
    2. Precio de bolsa, ONI y TRM
    3. Margen de reserva
    4. Mezcla de generación y disponibilidad por tecnología
    5. Hidrología por río y por embalse
    6. Perfil del día (precio y demanda hora a hora)
    7. El Niño semanal
    8. Lluvia sobre las cuencas
    9. Curva de mérito

Uso:
    python 2_construir_panel.py
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CARPETA = BASE / "datos"
CARPETA_XM = CARPETA / "xm"
SALIDA = BASE / "panel_diario.csv"

HORAS = [f"Values_Hour{h:02d}" for h in range(1, 25)]


def leer_xm(nombre):
    columnas_texto = ("Id", "Name", "Code", "Values_code", "Values_Name")
    df = pd.read_csv(CARPETA_XM / f"{nombre}.csv.gz",
                     dtype={c: str for c in columnas_texto})
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def horas_numericas(df):
    return df[HORAS].apply(pd.to_numeric, errors="coerce")


# ===========================================================================
# 1. Series de XM llevadas a un valor por día
# ===========================================================================
#
# XM entrega cada serie en uno de tres formatos:
#   - un valor por día para todo el sistema (columna Value)
#   - un valor por día para cada río, embalse o planta (Name o Code + Value)
#   - 24 valores por día para cada planta o agente (Values_Hour01 ... 24)
#
# Para llegar a un solo número por día hay que decidir cómo se juntan las
# plantas y cómo se juntan las horas. La regla depende de qué mide la serie:
#   energía (kWh)             se suma: es un flujo que se acumula
#   capacidad o disponibilidad se suma entre plantas, pero se promedia entre
#                              horas: es un nivel, no se acumula en el día
#   precios                   se promedian

REGLA_HORARIA = {   # serie: (entre plantas, entre horas)
    "gen_por_recurso":        ("sum", "sum"),
    "gen_programada":         ("sum", "sum"),
    "gen_seguridad":          ("sum", "sum"),
    "gen_fuera_merito":       ("sum", "sum"),
    "consumo_combustible":    ("sum", "sum"),
    "demanda_regulada":       ("sum", "sum"),
    "demanda_no_regulada":    ("sum", "sum"),
    "importaciones":          ("sum", "sum"),
    "exportaciones":          ("sum", "sum"),
    "perdidas_energia":       ("sum", "sum"),
    "restricciones":          ("sum", "sum"),
    "restricciones_sin_aliv": ("sum", "sum"),
    "compras_contrato":       ("sum", "sum"),
    "disp_declarada":         ("sum", "mean"),
    "disp_comercial":         ("sum", "mean"),
    "disp_real":              ("sum", "mean"),
    "costo_marginal_prog":    ("mean", "mean"),
    "precio_oferta_desp":     ("mean", "mean"),
    "precio_prom_contrato":   ("mean", "mean"),
    "precio_cont_no_regu":    ("mean", "mean"),
}

REGLA_ENTIDAD = {   # serie por río, embalse o planta: cómo se junta el sistema
    "aportes_por_rio":       "sum",
    "volumen_por_embalse":   "sum",
    "capacidad_por_embalse": "sum",
    "capacidad_efectiva":    "sum",
    "aportes_pct_rio":       "mean",   # es un porcentaje, sumarlo no tiene sentido
    "precio_cargo_conf":     "mean",
}

# Estas dos son horarias pero no entran al panel tal cual: el precio de bolsa
# se arma en la parte 2 y la demanda se usa en el perfil del día (parte 6).
NO_VAN_DIRECTO = {"precio_bolsa", "demanda_comercial"}


def a_diario(nombre, df):
    if "Values_Hour01" in df.columns:
        entre_plantas, entre_horas = REGLA_HORARIA[nombre]
        por_hora = horas_numericas(df).groupby(df["Date"]).agg(entre_plantas)
        return getattr(por_hora, entre_horas)(axis=1)

    valor = pd.to_numeric(df["Value"], errors="coerce")

    if nombre == "volumen_util_pct_emb":
        return promedio_ponderado_embalses(df, valor)

    if "Name" in df.columns or "Code" in df.columns:
        return valor.groupby(df["Date"]).agg(REGLA_ENTIDAD[nombre])

    serie = pd.Series(valor.values, index=df["Date"]).sort_index()
    # Los cargos regulados (CEE, CERE, MC) y las proyecciones de la UPME son
    # mensuales: el valor de cada mes rige hasta que sale el siguiente.
    if serie.index.to_series().diff().dt.days.median() > 20:
        serie = serie.reindex(pd.date_range(serie.index.min(), serie.index.max())).ffill()
    return serie


def promedio_ponderado_embalses(df, valor):
    """
    Porcentaje de volumen útil del sistema, ponderando cada embalse por su
    capacidad. Un promedio simple le daría el mismo peso a un embalse de 35 GWh
    que a uno de 4.000 GWh.
    """
    cap = leer_xm("capacidad_por_embalse")
    a = pd.DataFrame({"Name": df["Name"], "Date": df["Date"], "v": valor})
    b = pd.DataFrame({"Name": cap["Name"], "Date": cap["Date"],
                      "w": pd.to_numeric(cap["Value"], errors="coerce")})
    m = a.merge(b, on=["Name", "Date"], how="left").dropna(subset=["v", "w"])
    m = m[m["w"] > 0]
    return (m["v"] * m["w"]).groupby(m["Date"]).sum() / m.groupby("Date")["w"].sum()


def series_xm():
    nombres = sorted(p.name[:-7] for p in CARPETA_XM.glob("*.csv.gz"))
    series = {}
    for nombre in nombres:
        if nombre in NO_VAN_DIRECTO:
            continue
        series[nombre] = a_diario(nombre, leer_xm(nombre))
    return series


# ===========================================================================
# 2. Precio de bolsa, ONI y TRM
# ===========================================================================

def precio_bolsa():
    """El precio del día es el promedio de las 24 horas, en COP/kWh."""
    p = leer_xm("precio_bolsa")
    serie = pd.Series(horas_numericas(p).mean(axis=1).values, index=p["Date"]).dropna()
    return serie[~serie.index.duplicated(keep="last")].sort_index()


TRIMESTRES = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
              "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def leer_indice_noaa(archivo, columna_valor):
    """
    Lee el ONI o el RONI. Cada valor es el promedio de tres meses (DJF, JFM...)
    y se fecha en el mes del medio.
    """
    filas = []
    for linea in (CARPETA / "noaa" / archivo).read_text().splitlines():
        p = linea.split()
        if p and p[0] in TRIMESTRES and len(p) > columna_valor:
            filas.append((pd.Timestamp(int(p[1]), TRIMESTRES[p[0]], 1),
                          float(p[columna_valor])))
    return pd.Series(dict(filas)).sort_index()


def oni():
    """
    El ONI del mes M se publica a comienzos de M+2 (necesita el mes siguiente
    para cerrar el promedio). Se corre dos meses para no usarlo antes de tiempo.
    """
    serie = leer_indice_noaa("oni.ascii.txt", columna_valor=3)
    serie.index = serie.index + pd.DateOffset(months=2)
    return serie.reindex(pd.date_range(serie.index.min(), serie.index.max())).ffill()


def trm():
    return pd.read_csv(CARPETA / "trm.csv", parse_dates=["fecha"], index_col="fecha")["trm"]


# ===========================================================================
# 3. Margen de reserva
# ===========================================================================

def margen_reserva(panel):
    """
    Capacidad efectiva del parque frente a la demanda. Es una medida de qué tan
    holgado está el sistema.

    La demanda que publica XM es demanda real (medida), así que la del mismo día
    no se conoce cuando se pronostica. Se usa la del día anterior.
    """
    demanda = panel[["demanda_regulada", "demanda_no_regulada"]].sum(axis=1, min_count=1)
    return panel["capacidad_efectiva"] / demanda.shift(1).replace(0, np.nan)


# ===========================================================================
# 4. Mezcla de generación y disponibilidad por tecnología
# ===========================================================================
#
# La generación viene por planta. Cruzándola con el listado de plantas se sabe
# cuánto puso cada tecnología, cada combustible, y cuánto pasó por el despacho
# central (solo esas plantas ofertan y fijan el precio de bolsa).

COMBUSTIBLES = {
    "gas":      ["GAS", "MEZCLA GAS - CARBÓN", "MEZCLA GAS-FUEL OIL (ACPM O COMBUSTOLEO)"],
    "carbon":   ["CARBON"],
    "liquidos": ["ACPM", "COMBUSTOLEO", "CRUDO", "DIESEL MAR"],
    "biomasa":  ["BAGAZO", "BIOMASA", "BIOGAS"],
}
FILO_DE_AGUA = ["FILO DE AGUA", "FILO AGUA ESPECIAL"]


def leer_listado():
    # el Excel de PARATEC trae unas filas de título antes de los encabezados
    crudo = pd.read_excel(CARPETA / "Listado_Recursos_Generacion.xlsx", header=None)
    listado = crudo.iloc[4:].copy()
    listado.columns = crudo.iloc[3].tolist()
    listado = listado[listado["Código SIC"].notna()]
    return listado.rename(columns={
        "Código SIC": "codigo",
        "Tipo Generación": "tecnologia",
        "Combustible por Defecto": "combustible",
        "Tipo Despacho": "despacho",
        "Clasificación": "clasificacion",
    })[["codigo", "tecnologia", "combustible", "despacho", "clasificacion"]]


def energia_por_planta(nombre, listado):
    """Total del día por planta, en GWh, con los datos de la planta pegados."""
    df = leer_xm(nombre)
    d = pd.DataFrame({"Date": df["Date"], "codigo": df["Values_code"],
                      "gwh": horas_numericas(df).sum(axis=1, min_count=1) / 1e6})
    return d.merge(listado, on="codigo", how="left")


def mezcla_generacion(listado):
    gen = energia_por_planta("gen_por_recurso", listado)
    total = gen.groupby("Date")["gwh"].sum()

    def suma(filtro):
        return gen[filtro].groupby("Date")["gwh"].sum()

    s = {"gen_total_sistema": total}
    for tec in ["HIDRAULICA", "TERMICA", "SOLAR", "EOLICA", "COGENERADOR"]:
        s[f"gen_{tec.lower()}"] = suma(gen["tecnologia"] == tec)
    for tec in ["hidraulica", "termica", "solar", "eolica"]:
        s[f"frac_{tec}"] = s[f"gen_{tec}"] / total

    # fuentes no convencionales (solar + eólica); antes de 2018 casi no había
    fncer = (s["gen_solar"].reindex(total.index).fillna(0)
             + s["gen_eolica"].reindex(total.index).fillna(0))
    s["gen_fncer"] = fncer
    s["frac_fncer"] = fncer / total

    for comb, lista in COMBUSTIBLES.items():
        s[f"gen_{comb}"] = suma(gen["combustible"].isin(lista))
    # cuando las térmicas dejan el gas y pasan a líquidos, el kWh marginal se
    # encarece; esta fracción lo registra
    s["frac_gas_en_termica"] = (s["gen_gas"].reindex(total.index)
                                / s["gen_termica"].reindex(total.index).replace(0, np.nan))

    s["gen_despacho_central"] = suma(gen["despacho"] == "DC")
    s["gen_no_despachado"] = suma(gen["despacho"] == "ND")
    s["frac_despacho_central"] = s["gen_despacho_central"] / total

    # las plantas a filo de agua no tienen embalse: turbinan lo que llega o lo pierden
    filo = suma(gen["clasificacion"].isin(FILO_DE_AGUA))
    s["gen_filo_agua"] = filo
    s["frac_filo_en_hidro"] = (filo.reindex(total.index)
                               / s["gen_hidraulica"].reindex(total.index).replace(0, np.nan))

    # concentración del mercado: índice Herfindahl-Hirschman (0 a 10.000)
    gen["part"] = gen["gwh"] / gen.groupby("Date")["gwh"].transform("sum")
    s["hhi_generacion"] = (gen["part"] ** 2).groupby(gen["Date"]).sum() * 10000
    s["gen_top5_pct"] = (gen.sort_values("gwh", ascending=False)
                            .groupby("Date").head(5).groupby("Date")["part"].sum())
    s["n_plantas_activas"] = gen[gen["gwh"] > 0].groupby("Date")["codigo"].nunique()
    return pd.DataFrame(s)


def disponibilidad_por_tecnologia(listado):
    """La disponibilidad se declara antes del despacho, así que se conoce el mismo día."""
    disp = energia_por_planta("disp_declarada", listado)

    def suma(filtro):
        return disp[filtro].groupby("Date")["gwh"].sum()

    return pd.DataFrame({
        "disp_decl_hidraulica": suma(disp["tecnologia"] == "HIDRAULICA"),
        "disp_decl_termica": suma(disp["tecnologia"] == "TERMICA"),
        "disp_decl_despacho_central": suma(disp["despacho"] == "DC"),
    })


# ===========================================================================
# 5. Hidrología por río y por embalse
# ===========================================================================
#
# El total nacional esconde situaciones distintas: el sistema puede depender
# de pocas cuencas, o un embalse grande puede estar bajo mientras el promedio
# se ve normal.

def hidrologia_desagregada():
    s = {}

    ap = leer_xm("aportes_por_rio")
    ap["v"] = pd.to_numeric(ap["Value"], errors="coerce")
    ap["part"] = ap["v"] / ap.groupby("Date")["v"].transform("sum")
    s["hhi_aportes_rios"] = (ap["part"] ** 2).groupby(ap["Date"]).sum() * 10000
    s["aportes_top3_pct"] = (ap.sort_values("v", ascending=False)
                               .groupby("Date").head(3).groupby("Date")["part"].sum())
    s["n_rios_aportando"] = ap[ap["v"] > 0].groupby("Date")["Name"].nunique()

    vol = leer_xm("volumen_por_embalse")
    cap = leer_xm("capacidad_por_embalse")
    for d in (vol, cap):
        d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    v = vol.pivot_table(index="Date", columns="Name", values="Value", aggfunc="sum")
    c = cap.pivot_table(index="Date", columns="Name", values="Value", aggfunc="sum")

    # nivel de los cinco embalses de mayor capacidad, cada uno por separado
    mayores = cap.groupby("Name")["Value"].mean().sort_values(ascending=False).head(5).index
    for nombre in mayores:
        col = "vol_pct_" + nombre.lower().replace(" ", "_").replace(".", "").replace("-", "_")
        s[col] = v[nombre] / c[nombre].replace(0, np.nan)

    s["hhi_volumen_embalses"] = (v.div(v.sum(axis=1), axis=0) ** 2).sum(axis=1) * 10000
    return pd.DataFrame(s)


# ===========================================================================
# 6. Perfil del día
# ===========================================================================
#
# El precio diario es un promedio. Dos días con el mismo promedio pueden ser
# muy distintos: uno plano y otro con un pico caro en la noche. Igual con la
# demanda: lo que estresa al sistema es la hora pico.

def perfil_del_dia():
    p = leer_xm("precio_bolsa")
    H = horas_numericas(p)
    H.index = p["Date"]
    d = leer_xm("demanda_comercial")
    D = horas_numericas(d)
    D.index = d["Date"]

    perfil = pd.DataFrame({
        "precio_max_dia": H.max(axis=1),
        "precio_min_dia": H.min(axis=1),
        "precio_spread_intradia": H.max(axis=1) - H.min(axis=1),
        "precio_cv_intradia": H.std(axis=1) / H.mean(axis=1).replace(0, np.nan),
        "hora_precio_max": pd.Series(H.values.argmax(axis=1) + 1, index=H.index),
        "ratio_pico_valle": H.max(axis=1) / H.min(axis=1).replace(0, np.nan),
    })
    demanda = pd.DataFrame({
        "demanda_pico": D.max(axis=1) / 1e6,
        "factor_carga": D.mean(axis=1) / D.max(axis=1).replace(0, np.nan),
    })
    perfil = perfil.join(demanda, how="outer")
    return perfil[~perfil.index.duplicated(keep="last")].sort_index()


# ===========================================================================
# 7. El Niño semanal
# ===========================================================================
#
# El ONI es un promedio de tres meses que sale con dos meses de rezago: el
# modelo ve el Pacífico con cuatro o cinco meses de atraso. NOAA publica la
# misma medición cada semana. En febrero de 2026, por ejemplo, Niño 1+2 ya
# estaba en +0,88 °C mientras el ONI todavía marcaba La Niña.
#
# Niño 1+2 es la franja frente a Ecuador y Perú, la más cercana a Colombia;
# Niño 3.4 es la del Pacífico central, la que usa el índice oficial.

def leer_semanal():
    filas = []
    for linea in (CARPETA / "noaa" / "wksst9120.for").read_text().splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)$", linea)
        if not m:
            continue
        numeros = re.findall(r"-?\d+\.\d", m.group(2))
        if len(numeros) >= 8:
            # cada región trae temperatura y anomalía; se guarda la anomalía
            filas.append([pd.to_datetime(m.group(1), format="%d%b%Y")]
                         + [float(numeros[i]) for i in (1, 3, 5, 7)])
    return pd.DataFrame(filas, columns=["fecha", "n12", "n3", "n34", "n4"]).set_index("fecha")


def nino_semanal(indice):
    # la semana se publica el lunes siguiente: se corre 7 días
    semanal = leer_semanal().shift(7, freq="D")
    d = semanal.reindex(semanal.index.union(indice)).ffill().reindex(indice)
    d.columns = ["nino12_anom", "nino3_anom", "nino34_anom", "nino4_anom"]

    s = d.copy()
    # lo que anticipa un cambio no es el nivel sino qué tan rápido sube
    for corto, col in [("nino12", "nino12_anom"), ("nino34", "nino34_anom")]:
        s[f"{corto}_tend4s"] = d[col] - d[col].shift(28)
        s[f"{corto}_tend12s"] = d[col] - d[col].shift(84)
    s["nino_gradiente_costa"] = d["nino12_anom"] - d["nino34_anom"]

    # RONI: el ONI descontando el calentamiento general del trópico
    roni = leer_indice_noaa("RONI.ascii.txt", columna_valor=2)
    roni.index = roni.index + pd.DateOffset(months=2)
    s["roni"] = roni.reindex(roni.index.union(indice)).ffill().reindex(indice)
    return s


# ===========================================================================
# 8. Lluvia sobre las cuencas
# ===========================================================================
#
# El panel ve los aportes (el agua que ya llegó a los embalses) pero no la
# lluvia que los produce. Se usa ERA5, que es lluvia observada, no pronosticada.

# capacidad útil media 2015-2025 de cada embalse, en GWh (sirve de peso)
CAPACIDAD_EMBALSE = {
    "penol": 4111.9, "bogota": 3890.3, "guavio": 1950.4, "esmeralda": 1117.1,
    "quimbo": 1089.8, "topocoro": 999.3, "chuza": 987.8, "riogrande": 542.3,
}
REZAGO_ERA5 = 5                      # ERA5 se publica con unos cinco días de atraso
CLIMA_INI, CLIMA_FIN = "2000-01-01", "2014-12-31"   # periodo de referencia


def climatologia(serie):
    """
    Lluvia esperada para cada día del año, promediando 2000-2014 con una ventana
    de 15 días para que no quede ruidosa.
    """
    ref = serie.loc[CLIMA_INI:CLIMA_FIN]
    por_dia = ref.groupby(ref.index.dayofyear).mean()
    # el 31 de diciembre es vecino del 1 de enero
    circular = pd.concat([por_dia.iloc[-15:], por_dia, por_dia.iloc[:15]])
    return circular.rolling(15, center=True, min_periods=5).mean().iloc[15:-15]


def lluvia_cuencas(indice):
    lluvia = pd.read_csv(CARPETA / "lluvia_cuencas.csv", parse_dates=["fecha"],
                         index_col="fecha").shift(REZAGO_ERA5)
    pesos = pd.Series(CAPACIDAD_EMBALSE) / sum(CAPACIDAD_EMBALSE.values())

    s = {}
    sistema = (lluvia * pesos).sum(axis=1)
    s["lluvia_sistema"] = sistema
    for w in [3, 7, 15, 30, 60, 90]:
        s[f"lluvia_sistema_acum{w}"] = sistema.rolling(w).sum()

    # la lluvia cruda la domina la estación del año; lo que informa es cuánto se
    # aparta de lo normal para esa época
    esperada = pd.Series(sistema.index.dayofyear, index=sistema.index).map(climatologia(sistema))
    s["lluvia_anomalia"] = sistema - esperada
    for w in [30, 90]:
        real = sistema.rolling(w).sum()
        normal = esperada.rolling(w).sum()
        s[f"lluvia_anom_acum{w}"] = real - normal
        s[f"lluvia_razon{w}"] = real / normal.replace(0, np.nan)

    for nombre in ["penol", "bogota", "guavio", "quimbo"]:
        x = lluvia[nombre]
        esp = pd.Series(x.index.dayofyear, index=x.index).map(climatologia(x))
        s[f"lluvia_{nombre}_acum30"] = x.rolling(30).sum()
        s[f"lluvia_{nombre}_anom30"] = x.rolling(30).sum() - esp.rolling(30).sum()

    # Antioquia y el alto Magdalena responden distinto a El Niño
    s["lluvia_gradiente_ns"] = (lluvia[["penol", "riogrande"]].mean(axis=1)
                                - lluvia[["quimbo"]].mean(axis=1)).rolling(30).mean()
    return pd.DataFrame(s).reindex(indice)


# ===========================================================================
# 9. Curva de mérito
# ===========================================================================
#
# El precio de bolsa sale de ordenar las plantas de la más barata a la más cara
# y ver dónde se cruza esa curva con la demanda. Cada planta ofrece un precio
# por día y declara cuánto puede generar. Con eso se reconstruye la curva y se
# mide su forma: cuánta capacidad barata queda, qué tan empinada está cerca de
# la demanda, cuánto salta el precio a la siguiente planta.
#
# Ojo: la oferta del día t es justamente lo que fija el precio del día t. Estas
# variables solo pueden entrar rezagadas; features.py se encarga de eso.

UMBRALES_PRECIO = [100, 200, 300, 500, 1000]


def forma_de_la_curva(dia, demanda):
    dia = dia.sort_values("oferta")
    precio = dia["oferta"].values
    capacidad = dia["disp"].values
    acumulada = np.cumsum(capacidad)
    total = acumulada[-1]

    r = {"oferta_capacidad_total": total}
    for q in (0.25, 0.5, 0.75):
        i = np.searchsorted(acumulada, q * total)
        r[f"oferta_p{int(q * 100)}"] = precio[min(i, len(precio) - 1)]
    r["oferta_dispersion"] = r["oferta_p75"] / r["oferta_p25"] if r["oferta_p25"] > 0 else np.nan
    r["oferta_min"] = precio[0]
    r["oferta_max"] = precio[-1]
    for u in UMBRALES_PRECIO:
        r[f"cap_bajo_{u}"] = capacidad[precio <= u].sum()

    if np.isfinite(demanda) and demanda > 0:
        i = int(np.searchsorted(acumulada, demanda))      # planta que queda al margen
        if i < len(precio):
            r["oferta_marginal"] = precio[i]
            r["margen_ofertado"] = total / demanda
            r["escalon_siguiente"] = precio[i + 1] - precio[i] if i + 1 < len(precio) else np.nan
            r["holgura_gwh"] = total - demanda
            # cuánto sube el precio por GWh adicional, entre 90% y 110% de la demanda
            lo = max(0, int(np.searchsorted(acumulada, demanda * 0.9)))
            hi = min(len(precio) - 1, int(np.searchsorted(acumulada, demanda * 1.1)))
            if hi > lo and acumulada[hi] > acumulada[lo]:
                r["pendiente_curva"] = (precio[hi] - precio[lo]) / (acumulada[hi] - acumulada[lo])
    return r


def curva_de_merito(panel):
    o = leer_xm("precio_oferta_desp")
    # la oferta es un solo precio por planta y por día (las 24 horas son iguales)
    o["oferta"] = horas_numericas(o).bfill(axis=1).iloc[:, 0]
    d = leer_xm("disp_declarada")
    d["disp"] = horas_numericas(d).sum(axis=1, min_count=1) / 1e6

    plantas = (o[["Date", "Values_code", "oferta"]].dropna()
               .merge(d[["Date", "Values_code", "disp"]].dropna(),
                      on=["Date", "Values_code"], how="inner"))
    plantas = plantas[(plantas["disp"] > 0) & (plantas["oferta"] > 0)]

    demanda = ((panel["demanda_regulada"].fillna(0) + panel["demanda_no_regulada"].fillna(0))
               / 1e6).replace(0, np.nan)

    filas = {fecha: forma_de_la_curva(dia, demanda.get(fecha, np.nan))
             for fecha, dia in plantas.groupby("Date")}
    return pd.DataFrame(filas).T.sort_index()


# ===========================================================================
# Todo junto
# ===========================================================================

def main():
    print("1. Series de XM")
    series = series_xm()
    inicio = min(s.index.min() for s in series.values())
    fin = max(s.index.max() for s in series.values())
    indice = pd.date_range(inicio, fin, freq="D", name="fecha")
    print(f"   {len(series)} series, {inicio.date()} a {fin.date()}")

    print("2. Precio de bolsa, ONI y TRM")
    series["precio_bolsa"] = precio_bolsa()
    series["oni"] = oni()
    series["trm"] = trm()
    panel = pd.DataFrame({nombre: s.reindex(indice) for nombre, s in series.items()})

    print("3. Margen de reserva")
    panel["margen_reserva"] = margen_reserva(panel)

    print("4. Mezcla de generación")
    listado = leer_listado()
    bloques = [mezcla_generacion(listado), disponibilidad_por_tecnologia(listado)]
    print("5. Hidrología por río y embalse")
    bloques.append(hidrologia_desagregada())
    print("6. Perfil del día")
    bloques.append(perfil_del_dia())
    print("7. El Niño semanal")
    bloques.append(nino_semanal(indice))
    print("8. Lluvia sobre las cuencas")
    bloques.append(lluvia_cuencas(indice))
    print("9. Curva de mérito")
    bloques.append(curva_de_merito(panel))

    for bloque in bloques:
        panel = panel.join(bloque.reindex(indice))

    panel.to_csv(SALIDA)
    precio = panel["precio_bolsa"].dropna()
    print(f"\npanel_diario.csv: {panel.shape[0]} días x {panel.shape[1]} variables")
    print(f"precio de bolsa del {precio.index.min().date()} al {precio.index.max().date()}")
    print("Siguiente paso: abrir 3_modelos.ipynb")


if __name__ == "__main__":
    main()
