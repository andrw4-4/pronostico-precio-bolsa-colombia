"""
Paso 1 de 3: descargar los datos.

Baja todas las series que usa el proyecto y las guarda en la carpeta datos/.
La primera vez se demora varias horas, porque son más de diez años de datos
por planta y por hora. Después solo pide los días que faltan, así que se puede
volver a correr cuando se quiera tener el dato más reciente.

De dónde sale cada cosa:

    XM (API de SIMEM, librería pydataxm)   precio de bolsa, hidrología, generación,
                                           ofertas, demanda, contratos
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
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

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


def main():
    CARPETA_XM.mkdir(parents=True, exist_ok=True)
    CARPETA_NOAA.mkdir(parents=True, exist_ok=True)
    hoy = date.today()

    if not (CARPETA / "Listado_Recursos_Generacion.xlsx").exists():
        print("Falta datos/Listado_Recursos_Generacion.xlsx. Se descarga de PARATEC")
        print("(XM > Generación > Listado de recursos) y se guarda en datos/.\n")

    from pydataxm import pydataxm
    api = pydataxm.ReadDB()

    print(f"XM: {len(SERIES_XM)} series hasta {hoy}")
    for nombre, (metrica, entidad) in SERIES_XM.items():
        t = time.time()
        datos = actualizar_xm(api, nombre, metrica, entidad, hoy)
        if datos is None:
            print(f"  {nombre:24s} sin datos")
        else:
            print(f"  {nombre:24s} {len(datos):9,d} filas, hasta {datos['Date'].max()}"
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
