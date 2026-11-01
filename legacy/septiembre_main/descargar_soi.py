"""
Descarga el SOI (Southern Oscillation Index) estandarizado de NOAA CPC y lo
guarda en data/soi_noaa.csv.

El archivo trae dos tablas (ANOMALY y STANDARDIZED). Se usa la segunda.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL = "https://www.cpc.ncep.noaa.gov/data/indices/soi"
SALIDA = Path(__file__).resolve().parent / "data" / "soi_noaa.csv"


def main():
    lines = requests.get(URL, timeout=30).text.splitlines()

    # arrancar despues del encabezado de la tabla estandarizada
    inicio = next(i for i, l in enumerate(lines) if "STANDARDIZED" in l.upper())

    filas = []
    for line in lines[inicio:]:
        if not line[:4].isdigit():
            continue
        # ancho fijo: 4 caracteres el anio, 6 cada mes. Con split() los
        # faltantes pegados ("-1.8-999.9") se funden en un solo token.
        anio = int(line[:4])
        for mes in range(12):
            campo = line[4 + 6 * mes: 10 + 6 * mes].strip()
            valor = float(campo) if campo else np.nan
            filas.append((pd.Timestamp(anio, mes + 1, 1), valor))

    soi = pd.DataFrame(filas, columns=["Date", "SOI"])
    soi["SOI"] = soi["SOI"].replace(-999.9, np.nan)
    soi = soi.dropna().sort_values("Date").reset_index(drop=True)

    soi.to_csv(SALIDA, index=False)
    print(soi.tail(6).to_string(index=False))
    print(f"\n{len(soi)} meses, {soi['Date'].min().date()} -> "
          f"{soi['Date'].max().date()}")
    print(f"guardado en {SALIDA}")


if __name__ == "__main__":
    main()
