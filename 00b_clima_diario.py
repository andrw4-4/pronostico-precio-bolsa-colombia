"""
Junta las fuentes de clima en variables diarias 2015-2025 y las guarda en
data/clima_diario.parquet, que 01_seleccion_variables.py pega al panel.

Fuentes (cada una es opcional: si falta su archivo, se omite):
  HURDAT      data/clima/hurdat_huracanes.csv  tormentas en el Caribe
  SOI         data/soi_noaa.csv                descargar_soi.py
  MJO         data/mjo_bom.csv                 descargar_mjo.py
  Open-Meteo  data/openmeteo_diario.csv        descargar_openmeteo.py

ERA5 y MERRA2 de data/clima/ no entran: cubren solo 2020.
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
DATA = RAIZ / "data"
SALIDA = DATA / "clima_diario.parquet"

DIAS = pd.date_range("2015-01-01", "2025-12-31", freq="D", name="fecha")

# caja del Caribe: frente a la costa colombiana, Centroamerica y las Antillas
LAT, LON = (8, 20), (-85, -65)


def hurdat():
    ruta = DATA / "clima" / "hurdat_huracanes.csv"
    if not ruta.exists():
        return None
    h = pd.read_csv(ruta, usecols=["storm_id", "date", "latitude",
                                   "longitude", "max_sustained_wind_knots"])
    h["date"] = pd.to_datetime(h["date"])
    ultimo = h["date"].max()

    caribe = h[h["latitude"].between(*LAT) & h["longitude"].between(*LON)]
    out = caribe.groupby("date").agg(
        tormenta_caribe_n=("storm_id", "nunique"),
        tormenta_caribe_viento_max=("max_sustained_wind_knots", "max"),
    ).reindex(DIAS)

    # sin fila = no hubo tormenta -> 0; despues del ultimo registro no se sabe
    conocido = out.index <= ultimo
    out.loc[conocido] = out.loc[conocido].fillna(0)
    out["tormenta_caribe_activa"] = (out["tormenta_caribe_n"] > 0).astype(float)
    out.loc[~conocido, "tormenta_caribe_activa"] = float("nan")
    print(f"  HURDAT      hasta {ultimo.date()}")
    return out


def soi():
    ruta = DATA / "soi_noaa.csv"
    if not ruta.exists():
        return None
    s = pd.read_csv(ruta, parse_dates=["Date"])
    # el SOI de un mes se publica al terminar ese mes: se fecha el dia 1 del
    # mes siguiente para que el modelo no lo "conozca" antes de tiempo
    s["Date"] = s["Date"] + pd.DateOffset(months=1)
    serie = s.set_index("Date")["SOI"].reindex(DIAS, method="ffill")
    print(f"  SOI         mensual, rezagado 1 mes y arrastrado a diario")
    return serie.rename("soi").to_frame()


def mjo():
    ruta = DATA / "mjo_bom.csv"
    if not ruta.exists():
        return None
    m = pd.read_csv(ruta, parse_dates=["Date"]).set_index("Date")
    # la fase (1-8) es circular: rmm1/rmm2 ya codifican la posicion
    out = m[["rmm1", "rmm2", "amplitud"]].add_prefix("mjo_").reindex(DIAS)
    print(f"  MJO         hasta {m.index.max().date()}")
    return out


def openmeteo():
    ruta = DATA / "openmeteo_diario.csv"
    if not ruta.exists():
        return None
    om = pd.read_csv(ruta, index_col=0, parse_dates=True).reindex(DIAS)

    def media(prefijo, puntos=None):
        cols = [c for c in om.columns if c.startswith(prefijo)
                and (puntos is None or c.split("_", 1)[1] in puntos)]
        return om[cols].mean(axis=1)

    caribe = ["barranquilla", "cartagena"]
    andina = ["medellin", "bogota", "cali"]

    out = pd.DataFrame(index=DIAS)
    out["precip_cuencas"] = media("precip_")
    # la lluvia de un solo dia es ruido; lo que llena embalses es la acumulada
    out["precip_cuencas_acum30"] = out["precip_cuencas"].rolling(30, min_periods=20).sum()
    out["evap_cuencas"] = media("evap_")
    out["temp_caribe_max"] = media("tmax_", caribe)
    out["temp_andina_med"] = media("tmed_", andina)
    out["humedad_caribe"] = media("humedad_", caribe)
    out["viento_guajira_100m"] = media("viento100_")
    out["radiacion_cesar"] = media("radiacion_")
    print(f"  Open-Meteo  {out.shape[1]} variables agregadas")
    return out


def main():
    print("fuentes:")
    partes = [p for p in (hurdat(), soi(), mjo(), openmeteo()) if p is not None]
    clima = pd.concat(partes, axis=1)
    clima.to_parquet(SALIDA)

    print(f"\n{clima.shape[1]} variables, {len(clima)} dias")
    print("cobertura en 2015-2019 (seleccion):")
    cob = clima.loc[:"2019-12-31"].notna().mean().sort_values()
    print(cob.to_string(float_format=lambda v: f"{v:6.1%}"))
    print(f"\nguardado en {SALIDA}")


if __name__ == "__main__":
    main()
