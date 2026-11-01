"""
Paso 1: descargar los datos.

Baja todas las series que usa el proyecto y las guarda en la carpeta datos/.
La primera vez se demora varias horas, porque son más de diez años de datos
por planta y por hora. Después solo pide los días que faltan, así que se puede
volver a correr cuando se quiera tener el dato más reciente.

De dónde sale cada cosa:

    XM (API de SIMEM, librería pydataxm)   precio de bolsa, hidrología, generación,
                                           ofertas, demanda, contratos
    SIMEM (servicio público de datos)      pronóstico de demanda, costo marginal
                                           programado, holgura, arranques y paradas
    NOAA (Climate Prediction Center)       temperatura del Pacífico (El Niño)
    Open-Meteo (reanálisis ERA5)           lluvia diaria sobre las cuencas
    datos.gov.co                           TRM

El único archivo que no se baja solo es el listado de plantas de generación
(datos/Listado_Recursos_Generacion.xlsx), que se descarga a mano de PARATEC en
la página de XM. La API tiene un listado parecido, pero solo trae las plantas
que siguen activas: sin las retiradas se pierde, por ejemplo, Jepírachi, que
fue la única planta eólica del país hasta 2023.

Uso:
    python 1_descargar.py
"""

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

CARPETA = Path(__file__).resolve().parent / "datos"
CARPETA_XM = CARPETA / "xm"
CARPETA_NOAA = CARPETA / "noaa"

INICIO = date(2015, 1, 1)

# XM corrige los datos de los últimos días durante varias semanas (liquidaciones
# provisionales). Por eso, al actualizar, se vuelve a pedir el último mes.
REPASO_DIAS = 30


# ---------------------------------------------------------------------------
# Series de XM: nombre del archivo -> (métrica, entidad) en la API.
#
# Los códigos de las métricas están en el catálogo de la API. Se comprobaron
# uno por uno pidiendo una ventana de días que ya estaba descargada y viendo
# que los valores coincidieran exactamente.
# ---------------------------------------------------------------------------
SERIES_XM = {
    # Precio de bolsa (lo que se quiere pronosticar) y demanda, hora a hora
    "precio_bolsa":           ("PrecBolsNaci", "Sistema"),
    "demanda_comercial":      ("DemaCome", "Sistema"),

    # Hidrología del sistema
    "aportes_pct_sistema":    ("PorcApor", "Sistema"),
    "aportes_media_hist":     ("AporEnerMediHist", "Sistema"),
    "volumen_util_pct":       ("PorcVoluUtilDiar", "Sistema"),
    "vertimientos":           ("VertEner", "Sistema"),

    # Hidrología por río y por embalse
    "aportes_por_rio":        ("AporEner", "Rio"),
    "aportes_pct_rio":        ("PorcApor", "Rio"),
    "volumen_por_embalse":    ("VoluUtilDiarEner", "Embalse"),
    "capacidad_por_embalse":  ("CapaUtilDiarEner", "Embalse"),
    "volumen_util_pct_emb":   ("PorcVoluUtilDiar", "Embalse"),

    # Oferta: lo que genera, declara y ofrece cada planta
    "gen_por_recurso":        ("Gene", "Recurso"),
    "gen_programada":         ("GeneProgDesp", "Recurso"),
    "gen_seguridad":          ("GeneSeguridad", "Recurso"),
    "gen_fuera_merito":       ("GeneFueraMerito", "Recurso"),
    "disp_declarada":         ("DispoDeclarada", "Recurso"),
    "disp_comercial":         ("DispoCome", "Recurso"),
    "disp_real":              ("DispoReal", "Recurso"),
    "capacidad_efectiva":     ("CapEfecNeta", "Recurso"),
    "consumo_combustible":    ("ConsCombustibleMBTU", "Recurso"),
    "precio_oferta_desp":     ("PrecOferDesp", "Recurso"),
    "costo_marginal_prog":    ("CostMargDesp", "Sistema"),

    # Demanda, intercambios internacionales y red
    "demanda_regulada":       ("DemaComeReg", "Sistema"),
    "demanda_no_regulada":    ("DemaComeNoReg", "Sistema"),
    "demanda_upme_alto":      ("EscDemUPMEAlto", "Sistema"),
    "demanda_upme_medio":     ("EscDemUPMEMedio", "Sistema"),
    "demanda_upme_bajo":      ("EscDemUPMEBajo", "Sistema"),
    "importaciones":          ("ImpoEner", "Sistema"),
    "exportaciones":          ("ExpoEner", "Sistema"),
    "perdidas_energia":       ("PerdidasEner", "Sistema"),
    "restricciones":          ("RestAliv", "Sistema"),
    "restricciones_sin_aliv": ("RestSinAliv", "Sistema"),

    # Contratos
    "compras_contrato":       ("CompContEner", "Sistema"),
    "precio_prom_contrato":   ("PrecPromContRegu", "Sistema"),
    "precio_cont_no_regu":    ("PrecPromContNoRegu", "Sistema"),

    # Regulación: cargo por confiabilidad y precio de escasez
    "enficc":                 ("ENFICC", "Sistema"),
    "precio_cargo_conf":      ("PrecCargConf", "Recurso"),
    "precio_escasez":         ("PrecEsca", "Sistema"),
    "cee":                    ("CEE", "Sistema"),
    "cere":                   ("CERE", "Sistema"),
    "mc":                     ("MC", "Sistema"),

    # Operación de los embalses: lo que el operador decide hacer con el agua.
    # Las de arriba dicen cuánta agua hay; estas, cuánta se usa y cómo.
    "descargas_embalse":      ("DescMasa", "Embalse"),
    "turbinado_embalse":      ("VolTurbMasa", "Embalse"),
    "vertido_embalse":        ("VertMasa", "Embalse"),

    # Aportes medidos en caudal, que es como los reporta la hidrología
    "aportes_caudal":         ("AporCaudal", "Rio"),
    "aportes_caudal_medio":   ("AporCaudalMediHist", "Rio"),

    # Redespacho: lo que cambia después de publicado el despacho
    "gen_prog_redespacho":    ("GeneProgRedesp", "Recurso"),

    # Demanda real (la comercial de arriba es otra medición) y el pico de potencia
    "demanda_real":           ("DemaReal", "Sistema"),
    "demanda_real_reg":       ("DemaRealReg", "Sistema"),
    "demanda_real_no_reg":    ("DemaRealNoReg", "Sistema"),
    "demanda_max_potencia":   ("DemaMaxPot", "Sistema"),
    "demanda_no_atendida":    ("DemaNoAtenProg", "Area"),
    "dem_no_atendida_nop":    ("DemaNoAtenNoProg", "Area"),

    # Intercambios con Ecuador, separados de las importaciones totales
    "compras_tie":            ("CompBolsaTIEEner", "Sistema"),
    "ventas_tie":             ("VentBolsaTIEEner", "Sistema"),
    "tie_merito":             ("SnTIEMerito", "Sistema"),
    "tie_fuera_merito":       ("SnTIEFueraMerito", "Sistema"),

    # Variantes del precio de escasez: se publican antes del despacho
    "precio_esca_marg":       ("PrecEscaMarg", "Sistema"),
    "precio_esca_sup":        ("PrecEscaSup", "Sistema"),
    "precio_esca_inf":        ("PrecEscaInf", "Sistema"),
    "precio_esca_act":        ("PrecEscaAct", "Sistema"),

    # Compromiso de energía en firme de cada planta
    "oblig_energia_firme":    ("ObligEnerFirme", "Recurso"),

    # Qué se despacharía sin restricciones de la red, y qué planta quedó al
    # margen y de qué combustible vino la energía, hora a hora. La generación
    # ideal por planta también está en SIMEM, pero allí pesa unos 17 GB y
    # arranca en 2021; esta es la misma variable desde 2015.
    "gen_ideal":              ("GeneIdea", "Recurso"),
    "recurso_marginal":       ("IndRecMargina", "Recurso"),
    "co2_por_combustible":    ("EmisionesCO2", "RecursoComb"),
}

# ---------------------------------------------------------------------------
# Series de SIMEM (el portal de datos abiertos de XM): nombre -> (conjunto,
# desde cuándo).
#
# La API de XM no trae estas. Se piden por el servicio público de SIMEM y se
# guardan tal como llegan, sin juntar plantas ni mercados; eso lo hace el paso 2.
#
#   pron_demanda_cnd   pronóstico de demanda del Centro Nacional de Despacho,
#                      por mercado de comercialización y hora
#   cmg_despacho       costo marginal del despacho económico (programado)
#   cmg_redespacho     costo marginal del redespacho (se ajusta durante el día)
#   holgura_horaria    holgura superior e inferior de cada planta en cada hora
#   bandera_arranque   1 si la planta arrancó en esa hora
#   bandera_parada     1 si la planta paró en esa hora
#   reserva_caliente   proyección semanal de la reserva de corto plazo; solo
#                      existe desde agosto de 2024
#
# La holgura, las banderas y la reserva se bajan, pero por ahora el panel horario
# no las usa porque empiezan tarde (ver NO_SE_USAN_POR_AHORA en el paso 2b).
# ---------------------------------------------------------------------------
# Fuente: es el servicio que usa por dentro pydataxm.pydatasimem; su catálogo
# es el conjunto e007fb (ver docs/REFERENCIAS.md)
SIMEM_URL = "https://www.simem.co/backend-files/api/PublicData"
CARPETA_SIMEM = CARPETA / "simem"
SERIES_SIMEM = {
    "pron_demanda_cnd":  ("68300e", INICIO),
    "cmg_despacho":      ("29f060", INICIO),
    "cmg_redespacho":    ("03e35f", INICIO),
    "holgura_horaria":   ("897043", date(2021, 1, 1)),
    "bandera_arranque":  ("1237df", date(2021, 1, 1)),
    "bandera_parada":    ("39726d", date(2021, 1, 1)),
    "reserva_caliente":  ("f62164", date(2024, 8, 1)),
}

# Archivos de NOAA. wksst9120 trae la temperatura semanal del mar en las cuatro
# regiones Niño; el ONI y el RONI son los índices mensuales oficiales.
ARCHIVOS_NOAA = {
    "wksst9120.for":  "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for",
    "oni.ascii.txt":  "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "RONI.ascii.txt": "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt",
}

# Un punto aproximado en la cuenca de cada uno de los ocho embalses más grandes.
# Entre los ocho suman el 85% de la capacidad útil del país.
CUENCAS = {
    "penol":     (6.28, -75.10),
    "bogota":    (4.95, -73.95),
    "guavio":    (4.82, -73.48),
    "esmeralda": (4.92, -73.35),
    "quimbo":    (2.50, -75.62),
    "topocoro":  (6.80, -73.42),
    "chuza":     (4.58, -73.72),
    "riogrande": (6.55, -75.45),
}

# La lluvia se baja desde 2000 porque 2000-2014 se usa como "año normal" para
# saber si una semana llovió más o menos de lo habitual.
INICIO_LLUVIA = date(2000, 1, 1)


def pedir_url(url, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=120).read()
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(3)


# ---------------------------------------------------------------------------
# XM
# ---------------------------------------------------------------------------

def bajar_xm(api, metrica, entidad, desde, hasta):
    """Pide una métrica por tramos de 30 días, que es lo que acepta la API."""
    partes = []
    inicio = desde
    while inicio <= hasta:
        fin = min(inicio + timedelta(days=29), hasta)
        for intento in range(3):
            try:
                d = api.request_data(metrica, entidad, inicio, fin)
                if d is not None and len(d):
                    partes.append(d)
                break
            except Exception as e:
                if intento == 2:
                    print(f"    no se pudo bajar {inicio} a {fin}: {type(e).__name__}")
                time.sleep(3)
        time.sleep(0.3)
        inicio = fin + timedelta(days=1)

    if not partes:
        return None
    d = pd.concat(partes, ignore_index=True)
    d["Date"] = pd.to_datetime(d["Date"]).dt.strftime("%Y-%m-%d")
    # las series mensuales salen repetidas cuando el mes cae en dos tramos
    return d.drop_duplicates()


def actualizar_xm(api, nombre, metrica, entidad, hoy):
    """
    Si el archivo no existe lo baja completo. Si existe, pide desde un mes antes
    del último día guardado y reemplaza esos días por la versión nueva.
    """
    ruta = CARPETA_XM / f"{nombre}.csv.gz"
    viejo = pd.read_csv(ruta, dtype=str) if ruta.exists() else None

    if viejo is None or viejo.empty:
        desde = INICIO
    else:
        ultimo = pd.Timestamp(viejo["Date"].max())
        desde = (ultimo - pd.Timedelta(days=REPASO_DIAS)).date()

    nuevo = bajar_xm(api, metrica, entidad, desde, hoy)
    if nuevo is None:
        return viejo

    if viejo is not None:
        # se reemplazan solo los días que llegaron de nuevo; si un tramo falló,
        # se conserva lo que ya estaba
        viejo = viejo[~viejo["Date"].isin(nuevo["Date"].unique())]
        nuevo = nuevo.reindex(columns=viejo.columns)
        datos = pd.concat([viejo, nuevo], ignore_index=True)
    else:
        datos = nuevo

    datos = datos.sort_values("Date", kind="stable")
    datos.to_csv(ruta, index=False,
                 compression={"method": "gzip", "compresslevel": 6})
    return datos


# ---------------------------------------------------------------------------
# SIMEM
# ---------------------------------------------------------------------------

def pedir_simem(conjunto, desde, hasta, intentos=4):
    """Un tramo de un conjunto de SIMEM. Devuelve una lista de registros, o None si falla."""
    for intento in range(intentos):
        try:
            r = requests.get(SIMEM_URL, timeout=120,
                             params={"startdate": desde.isoformat(), "enddate": hasta.isoformat(),
                                     "datasetId": conjunto})
            if r.status_code == 200:
                return r.json()["result"].get("records", [])
        except Exception:
            pass
        time.sleep(3 * (intento + 1))
    return None


def bajar_simem(conjunto, desde, hasta):
    """Pide el conjunto por tramos de 30 días, varios a la vez."""
    tramos, inicio = [], desde
    while inicio <= hasta:
        fin = min(inicio + timedelta(days=29), hasta)
        tramos.append((inicio, fin))
        inicio = fin + timedelta(days=1)

    with ThreadPoolExecutor(max_workers=6) as pool:
        resultados = list(pool.map(lambda t: pedir_simem(conjunto, *t), tramos))

    partes = []
    for (ini, fin), registros in zip(tramos, resultados):
        if registros is None:
            print(f"    no se pudo bajar {ini} a {fin}")
        elif registros:
            partes.append(pd.DataFrame(registros))
    return pd.concat(partes, ignore_index=True) if partes else None


def actualizar_simem(nombre, conjunto, desde, hoy):
    """Igual que actualizar_xm: baja lo que falta y repasa el último mes."""
    CARPETA_SIMEM.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_SIMEM / f"{nombre}.csv.gz"
    viejo = pd.read_csv(ruta, dtype=str) if ruta.exists() else None

    if viejo is None or viejo.empty:
        inicio = desde
    else:
        ultimo = pd.Timestamp(viejo["FechaHora"].max()).date()
        inicio = ultimo - timedelta(days=REPASO_DIAS)

    nuevo = bajar_simem(conjunto, inicio, hoy)
    if nuevo is None:
        return viejo
    nuevo = nuevo.astype(str)

    if viejo is not None:
        # se descarta lo viejo desde la fecha que se volvió a pedir
        corte = pd.Timestamp(inicio)
        viejo = viejo[pd.to_datetime(viejo["FechaHora"]) < corte]
        nuevo = nuevo.reindex(columns=viejo.columns)
        datos = pd.concat([viejo, nuevo], ignore_index=True)
    else:
        datos = nuevo

    datos = datos.drop_duplicates().sort_values("FechaHora", kind="stable")
    datos.to_csv(ruta, index=False, compression={"method": "gzip", "compresslevel": 6})
    return datos


# ---------------------------------------------------------------------------
# Clima y TRM
# ---------------------------------------------------------------------------

def bajar_noaa():
    for archivo, url in ARCHIVOS_NOAA.items():
        (CARPETA_NOAA / archivo).write_bytes(pedir_url(url))
        print(f"  {archivo}")


def bajar_lluvia(hoy):
    """Precipitación diaria de ERA5 para cada cuenca, en mm."""
    columnas = {}
    for nombre, (lat, lon) in CUENCAS.items():
        consulta = urllib.parse.urlencode({
            "latitude": lat, "longitude": lon,
            "start_date": INICIO_LLUVIA.isoformat(), "end_date": hoy.isoformat(),
            "daily": "precipitation_sum", "timezone": "America/Bogota",
        })
        d = json.loads(pedir_url("https://archive-api.open-meteo.com/v1/archive?" + consulta))
        columnas[nombre] = pd.Series(d["daily"]["precipitation_sum"],
                                     index=pd.to_datetime(d["daily"]["time"]),
                                     dtype="float64")
        time.sleep(0.5)

    lluvia = pd.DataFrame(columnas)
    lluvia.index.name = "fecha"
    # ERA5 sale con unos cinco días de atraso: los últimos días vienen vacíos y
    # se quitan para que no se confundan con días sin lluvia
    lluvia = lluvia.loc[: lluvia.dropna(how="all").index.max()]
    lluvia.to_csv(CARPETA / "lluvia_cuencas.csv")
    print(f"  lluvia de {len(CUENCAS)} cuencas hasta {lluvia.index.max().date()}")


def bajar_trm():
    """
    La TRM de datos.gov.co viene como 'rige desde' y 'rige hasta' (la del viernes
    vale todo el fin de semana). Se pasa a un valor por cada día.
    """
    url = ("https://www.datos.gov.co/resource/32sa-8pi3.json"
           "?$limit=100000&$order=vigenciadesde")
    d = pd.DataFrame(json.loads(pedir_url(url)))
    d["desde"] = pd.to_datetime(d["vigenciadesde"])
    d["hasta"] = pd.to_datetime(d["vigenciahasta"])
    d["trm"] = pd.to_numeric(d["valor"])

    dias = [(f, r.trm) for r in d.itertuples() for f in pd.date_range(r.desde, r.hasta)]
    trm = pd.Series(dict(dias), name="trm").sort_index()
    trm.index.name = "fecha"
    trm.to_csv(CARPETA / "trm.csv")
    print(f"  TRM hasta {trm.index.max().date()}")


def conectar_xm(pydataxm, intentos=10):
    """El servidor de XM se cae a ratos; se reintenta antes de rendirse."""
    for i in range(intentos):
        try:
            return pydataxm.ReadDB()
        except Exception as e:
            print(f"  XM no responde ({type(e).__name__}), intento {i + 1} de {intentos}")
            time.sleep(10)
    raise RuntimeError("XM no respondió. Se puede reintentar más tarde.")


def main():
    CARPETA_XM.mkdir(parents=True, exist_ok=True)
    CARPETA_NOAA.mkdir(parents=True, exist_ok=True)
    hoy = date.today()

    if not (CARPETA / "Listado_Recursos_Generacion.xlsx").exists():
        print("Falta datos/Listado_Recursos_Generacion.xlsx. Se descarga de PARATEC")
        print("(XM > Generación > Listado de recursos) y se guarda en datos/.\n")

    from pydataxm import pydataxm
    api = conectar_xm(pydataxm)

    print(f"XM: {len(SERIES_XM)} series hasta {hoy}")
    for nombre, (metrica, entidad) in SERIES_XM.items():
        t = time.time()
        datos = actualizar_xm(api, nombre, metrica, entidad, hoy)
        if datos is None:
            print(f"  {nombre:24s} sin datos")
        else:
            print(f"  {nombre:24s} {len(datos):9,d} filas, hasta {datos['Date'].max()}"
                  f"  ({time.time() - t:.0f} s)")

    print(f"\nSIMEM: {len(SERIES_SIMEM)} conjuntos")
    for nombre, (conjunto, desde) in SERIES_SIMEM.items():
        t = time.time()
        datos = actualizar_simem(nombre, conjunto, desde, hoy)
        if datos is None:
            print(f"  {nombre:20s} sin datos")
        else:
            print(f"  {nombre:20s} {len(datos):10,d} filas, hasta {datos['FechaHora'].max()[:10]}"
                  f"  ({time.time() - t:.0f} s)")

    print("\nNOAA")
    bajar_noaa()
    print("\nOpen-Meteo")
    bajar_lluvia(hoy)
    print("\ndatos.gov.co")
    bajar_trm()

    print("\nListo. Siguiente paso: python 2_construir_panel.py")


if __name__ == "__main__":
    main()
