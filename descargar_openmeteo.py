"""
Descarga clima diario 2015-2025 de Open-Meteo (reanalisis ERA5, sin clave) en
puntos elegidos por su papel en el sistema electrico, y lo guarda en
data/openmeteo_diario.csv (una columna por variable y punto).

Es reanalisis (modelo ajustado a observaciones), no medicion de estacion: la
alternativa medida es IDEAM.
"""

import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://archive-api.open-meteo.com/v1/archive"
SALIDA = Path(__file__).resolve().parent / "data" / "openmeteo_diario.csv"
CACHE = Path(__file__).resolve().parent / "data" / "openmeteo_cache"
INICIO, FIN = "2015-01-01", "2025-12-31"

# grupo -> (variables diarias, {punto: (lat, lon)})
GRUPOS = {
    # embalses: lluvia y evapotranspiracion en las cuencas que generan
    "cuenca": (
        {"precipitation_sum": "precip", "et0_fao_evapotranspiration": "evap"},
        {"guavio": (4.68, -73.48), "chivor": (4.93, -73.33),
         "penol": (6.22, -75.18), "san_carlos": (6.21, -74.84),
         "porce": (6.93, -75.13), "ituango": (7.13, -75.66),
         "urra": (7.87, -76.21), "betania": (2.68, -75.43)},
    ),
    # centros de carga: temperatura y humedad empujan la demanda
    "ciudad": (
        {"temperature_2m_max": "tmax", "temperature_2m_mean": "tmed",
         "relative_humidity_2m_mean": "humedad"},
        {"barranquilla": (10.96, -74.80), "cartagena": (10.39, -75.51),
         "medellin": (6.25, -75.56), "bogota": (4.71, -74.07),
         "cali": (3.45, -76.53)},
    ),
    # FNCER: viento en La Guajira, radiacion en la zona solar del Cesar
    "eolica": (
        {"wind_speed_10m_mean": "viento10", "wind_speed_100m_mean": "viento100"},
        {"jepirachi": (12.08, -72.03), "uribia": (11.70, -72.40)},
    ),
    "solar": (
        {"shortwave_radiation_sum": "radiacion"},
        {"el_paso": (9.66, -73.75)},
    ),
}


def descargar_punto(nombre, lat, lon, variables, intentos=6):
    """Un punto por consulta, cacheado en disco: la conexion es lenta y se
    corta a mitad de respuesta, asi que se reintenta y no se pierde avance."""
    cache = CACHE / f"{nombre}.csv"
    if cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True)

    # en tramos de 2 anios: pedir 2015-2025 de una vez hace que el servidor
    # corte con "timeoutReached" en algunos puntos
    tramos = []
    for anio in range(int(INICIO[:4]), int(FIN[:4]) + 1, 2):
        ini = f"{anio}-01-01"
        fin = min(f"{anio + 1}-12-31", FIN)
        params = {"latitude": lat, "longitude": lon,
                  "start_date": ini, "end_date": fin,
                  "daily": ",".join(variables), "timezone": "America/Bogota"}
        for i in range(1, intentos + 1):
            try:
                datos = requests.get(URL, params=params, timeout=300).json()
                if isinstance(datos, dict) and "daily" in datos:
                    break
                raise requests.RequestException(str(datos)[:80])
            except requests.RequestException as e:
                print(f"    {ini[:4]} intento {i} fallo: {e}"[:110], flush=True)
                if i == intentos:
                    raise
                time.sleep(30 * i)

        tramos.append(pd.DataFrame(
            {f"{corto}_{nombre}": datos["daily"][var_api]
             for var_api, corto in variables.items()},
            index=pd.to_datetime(datos["daily"]["time"])))

    df = pd.concat(tramos)
    df.to_csv(cache)
    return df


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    partes = []
    for grupo, (variables, puntos) in GRUPOS.items():
        for nombre, (lat, lon) in puntos.items():
            print(f"{grupo:7s} {nombre}...", flush=True)
            partes.append(descargar_punto(nombre, lat, lon, variables))

    clima = pd.concat(partes, axis=1)
    clima.index.name = "fecha"
    clima.to_csv(SALIDA)

    print(f"\n{clima.shape[1]} columnas, {len(clima)} dias, "
          f"{clima.index.min().date()} -> {clima.index.max().date()}")
    print(f"nulos: {clima.isna().mean().max():.1%} en la peor columna")
    print(f"guardado en {SALIDA}")


if __name__ == "__main__":
    main()
