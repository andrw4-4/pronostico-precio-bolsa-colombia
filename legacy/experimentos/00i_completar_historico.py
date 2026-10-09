"""
Dos arreglos sobre la descarga historica antes de armar el panel largo:

  1. aportes_por_rio perdio el tramo 2000-01-01 a 2000-01-30 por un error
     transitorio de DNS. Se vuelve a pedir y se concatena.
  2. Falta DemaCome horaria de 2000-2014. Se necesita para factor_carga y
     demanda_pico, que estaban entre las variables mas usadas por el modelo.
"""

import datetime as dt
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE_HIST = BASE / "cache_historico"
DATA = BASE / "data"

INI, FIN = dt.date(2000, 1, 1), dt.date(2014, 12, 31)


def api():
    from pydataxm import pydataxm
    return pydataxm.ReadDB()


def por_tramos(a, mid, ent, ini, fin, dias=30, reintentos=3):
    trozos, actual = [], ini
    while actual <= fin:
        hasta = min(actual + dt.timedelta(days=dias - 1), fin)
        for intento in range(reintentos):
            try:
                d = a.request_data(mid, ent, actual, hasta)
                if d is not None and not d.empty:
                    trozos.append(d)
                break
            except Exception as e:
                if intento == reintentos - 1:
                    print(f"    [!] {actual} falló tras {reintentos}: {type(e).__name__}")
                else:
                    time.sleep(2)
        time.sleep(0.35)
        actual = hasta + dt.timedelta(days=1)
    if not trozos:
        return None
    d = pd.concat(trozos, ignore_index=True)
    d["Date"] = pd.to_datetime(d["Date"])
    return d.drop_duplicates()


def main():
    a = api()

    # --- 1. el mes que falta de aportes_por_rio ------------------------------
    ruta = CACHE_HIST / "aportes_por_rio.parquet"
    d = pd.read_parquet(ruta)
    d["Date"] = pd.to_datetime(d["Date"])
    print(f"[rio]     antes: {len(d)} filas desde {d['Date'].min().date()}")

    if d["Date"].min() > pd.Timestamp("2000-01-02"):
        falta = por_tramos(a, "AporEner", "Rio", INI,
                           (d["Date"].min() - pd.Timedelta(days=1)).date())
        if falta is not None:
            d = pd.concat([falta, d], ignore_index=True).drop_duplicates()
            d = d.sort_values("Date")
            d.to_parquet(ruta, index=False)
            print(f"[rio]     ahora: {len(d)} filas desde {d['Date'].min().date()}")
    else:
        print("[rio]     ya estaba completo")

    # --- 2. demanda comercial horaria ----------------------------------------
    destino = DATA / "DemaCome_Sistema_historico.csv"
    if destino.exists():
        print(f"[demanda] ya existe {destino.name}")
    else:
        print("[demanda] descargando DemaCome 2000-2014 (para factor_carga)...")
        t = time.time()
        dm = por_tramos(a, "DemaCome", "Sistema", INI, FIN)
        if dm is not None:
            dm.to_csv(destino, index=False)
            print(f"[demanda] {len(dm)} filas  {dm['Date'].min().date()} a "
                  f"{dm['Date'].max().date()}  [{time.time()-t:.0f}s]")


if __name__ == "__main__":
    main()
