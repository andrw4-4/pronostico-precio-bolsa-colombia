"""
Descarga el indice MJO (RMM de Wheeler-Hendon) del Bureau of Meteorology de
Australia y lo guarda en data/mjo_bom.csv. Es diario.

www.bom.gov.au no resuelve desde algunas redes; reg.bom.gov.au sirve el mismo
archivo.
"""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL = "https://reg.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt"
SALIDA = Path(__file__).resolve().parent / "data" / "mjo_bom.csv"


def main():
    texto = requests.get(URL, timeout=60,
                         headers={"User-Agent": "Mozilla/5.0"}).text

    df = pd.read_csv(io.StringIO(texto), sep=r"\s+", skiprows=2, header=None,
                     names=["y", "m", "d", "rmm1", "rmm2", "fase",
                            "amplitud", "metodo"])
    df["Date"] = pd.to_datetime(dict(year=df["y"], month=df["m"], day=df["d"]))

    cols = ["rmm1", "rmm2", "fase", "amplitud"]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    # faltantes marcados como 1.E36 o 999
    df[cols] = df[cols].where(df[cols].abs() < 999, np.nan)

    mjo = df[["Date"] + cols].dropna().reset_index(drop=True)
    mjo["fase"] = mjo["fase"].astype(int)

    mjo.to_csv(SALIDA, index=False)
    print(mjo.tail(5).to_string(index=False))
    print(f"\n{len(mjo)} dias, {mjo['Date'].min().date()} -> "
          f"{mjo['Date'].max().date()}")
    print(f"guardado en {SALIDA}")


if __name__ == "__main__":
    main()
