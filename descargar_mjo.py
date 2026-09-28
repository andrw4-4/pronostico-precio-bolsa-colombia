"""
Descarga el indice MJO en tiempo real ROMI (Real-time OLR MJO Index, NOAA PSL)
y lo guarda en data/mjo_romi.csv. Es diario, 1991 -> presente.

Por que ROMI y no las alternativas:
  - RMM del Bureau of Meteorology: dejo de actualizarse el 2024-02-24 y deja
    sin dato el 62% del periodo de prueba.
  - OMI (la version no real-time): filtra con una ventana CENTRADA, asi que el
    valor del dia t usa radiacion de semanas posteriores. Es fuga.
  - ROMI solo usa datos pasados: es lo que un pronosticador tendria ese dia.

pc1 y pc2 son las dos componentes principales del OMI. No son las mismas que
rmm1/rmm2 (otro metodo), pero cumplen el mismo papel: juntas ubican el pulso
convectivo sobre el tropico.
"""

import io
from pathlib import Path

import pandas as pd
import requests

URL = "https://psl.noaa.gov/mjo/mjoindex/romi.cpcolr.1x.txt"
SALIDA = Path(__file__).resolve().parent / "data" / "mjo_romi.csv"


def main():
    texto = requests.get(URL, timeout=60).text
    df = pd.read_csv(io.StringIO(texto), sep=r"\s+", header=None,
                     names=["y", "m", "d", "hora", "pc1", "pc2", "amplitud"])
    df["Date"] = pd.to_datetime(dict(year=df["y"], month=df["m"], day=df["d"]))

    mjo = (df[["Date", "pc1", "pc2", "amplitud"]]
           .dropna().sort_values("Date").reset_index(drop=True))

    mjo.to_csv(SALIDA, index=False)
    print(mjo.tail(5).to_string(index=False))
    print(f"\n{len(mjo)} dias, {mjo['Date'].min().date()} -> "
          f"{mjo['Date'].max().date()}")
    print(f"guardado en {SALIDA}")


if __name__ == "__main__":
    main()
