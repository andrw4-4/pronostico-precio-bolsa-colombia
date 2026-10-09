"""
================================================================================
BLOQUE ENSO SEMANAL — la senal climatica con semanas de rezago, no meses
================================================================================

El panel trae una sola variable climatica: `oni`. Es la peor version posible de
la senal para pronosticar, porque le caen tres retrasos encima:

  1. es una media movil de TRES MESES (por definicion va ~1,5 meses atras);
  2. se publica una vez al MES;
  3. el consolidador le suma 2 meses de rezago de publicacion.

Entre los tres, el modelo ve el estado del Pacifico con cuatro o cinco meses de
atraso. En 2026 eso fue fatal: el ONI del panel marcaba -0,60 (La Nina) en
febrero, cuando el Pacifico oriental ya se estaba calentando.

Este script agrega el mismo fenomeno medido SEMANALMENTE:

  Febrero 2026    Nino 1+2 semanal  +0,88   <- ya senalaba El Nino
                  ONI del panel     -0,60   <- todavia decia La Nina
  Mayo 2026       el precio se dispara de 269 a 505 COP/kWh

Tres meses de holgura para decidir, que es justo lo que el ONI no daba.

POR QUE NINO 1+2 Y NO SOLO NINO 3.4
-----------------------------------
Nino 1+2 es la franja costera frente a Ecuador y Peru: la region oceanica mas
cercana a Colombia. Nino 3.4, el indice estandar, esta en el Pacifico central, a
miles de kilometros. En los Nino costeros el 1+2 se adelanta, y eso fue
exactamente lo que paso en 2026 (+0,88 contra -0,20 en febrero).

FUENTES (todas publicas y legibles por maquina, verificadas)
------------------------------------------------------------
  wksst9120.for     SST y anomalias SEMANALES de Nino 1+2, 3, 3.4 y 4,
                    desde 1981-09. Climatologia 1991-2020.
                    (el archivo wksst8110.for esta descontinuado: termina
                     en enero de 2021)
  RONI.ascii.txt    ONI relativo: el ONI menos el calentamiento medio del
                    tropico. Corrige el sesgo que introduce el cambio
                    climatico en el ONI clasico.

ANTI-FUGA
---------
Las anomalias semanales se publican los lunes siguientes a la semana medida. Se
aplica un rezago de 7 dias, y encima de eso el pipeline de caracteristicas les
pone sus propios rezagos (minimo 1 dia mas). Al RONI se le aplican los mismos
2 meses que el consolidador le aplica al ONI.

Uso
---
  python 00f_enso_semanal.py
================================================================================
"""

import re
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
PANEL = BASE / "panel_diario_ampliado_2026.csv"
SALIDA = BASE / "panel_diario_ampliado_2026.csv"   # se actualiza en el sitio

URL_SEMANAL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
URL_RONI = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"

REZAGO_SEMANAL_DIAS = 7      # la semana centrada en t se publica ~t+7
REZAGO_RONI_MESES = 2        # mismo criterio que el ONI en 00_consolidar_panel.py

SEAS_A_MES = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
              "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")


def leer_semanal():
    """Anomalias semanales de las cuatro regiones Nino."""
    texto = bajar(URL_SEMANAL)
    filas = []
    for linea in texto.split("\n"):
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)$", linea)
        if not m:
            continue
        nums = re.findall(r"(-?\d+\.\d)", m.group(2))
        if len(nums) >= 8:
            filas.append([pd.to_datetime(m.group(1), format="%d%b%Y")]
                         + [float(x) for x in nums[:8]])

    d = pd.DataFrame(filas, columns=["fecha", "n12", "n12a", "n3", "n3a",
                                     "n34", "n34a", "n4", "n4a"])
    d = d.set_index("fecha").sort_index()
    print(f"[semanal] {len(d)} semanas, {d.index.min().date()} a {d.index.max().date()}")
    return d


def leer_roni():
    texto = bajar(URL_RONI)
    filas = []
    for linea in texto.split("\n"):
        p = linea.split()
        if len(p) == 3 and p[0] in SEAS_A_MES:
            try:
                filas.append((pd.Timestamp(int(p[1]), SEAS_A_MES[p[0]], 1), float(p[2])))
            except ValueError:
                continue
    s = pd.Series(dict(filas)).sort_index().rename("roni")
    print(f"[roni]    {len(s)} meses, {s.index.min().date()} a {s.index.max().date()}")
    return s


def construir(semanal, roni, indice):
    """
    Pasa todo a diario sobre el indice del panel, con los rezagos de publicacion
    ya aplicados. Nada aqui puede ver el futuro.
    """
    # --- anomalias semanales, rezagadas y llevadas a diario --------------------
    sem = semanal[["n12a", "n3a", "n34a", "n4a"]].copy()
    sem.index = sem.index + pd.Timedelta(days=REZAGO_SEMANAL_DIAS)
    diario = sem.reindex(sem.index.union(indice)).ffill().reindex(indice)
    diario.columns = ["nino12_anom", "nino3_anom", "nino34_anom", "nino4_anom"]

    salida = diario.copy()

    # --- tendencias: el indicador adelantado de verdad -------------------------
    # No es el nivel lo que avisa de una transicion, es la VELOCIDAD. En enero de
    # 2026 Nino 1+2 seguia negativo pero ya subia rapido.
    for col, base in [("nino12", "nino12_anom"), ("nino34", "nino34_anom")]:
        salida[f"{col}_tend4s"] = diario[base] - diario[base].shift(28)
        salida[f"{col}_tend12s"] = diario[base] - diario[base].shift(84)

    # --- gradiente costa-centro ------------------------------------------------
    # Positivo = el calentamiento esta en la costa suramericana (Nino costero),
    # que es el que afecta la hidrologia colombiana mas directo y mas rapido.
    salida["nino_gradiente_costa"] = diario["nino12_anom"] - diario["nino34_anom"]

    # --- RONI ------------------------------------------------------------------
    r = roni.copy()
    r.index = r.index + pd.DateOffset(months=REZAGO_RONI_MESES)
    salida["roni"] = r.reindex(r.index.union(indice)).ffill().reindex(indice)

    return salida


def main():
    print("=" * 74)
    print("BLOQUE ENSO SEMANAL")
    print("=" * 74)

    panel = pd.read_csv(PANEL, parse_dates=["fecha"], index_col="fecha").sort_index()
    print(f"[panel]   {panel.shape[0]} dias x {panel.shape[1]} variables")

    semanal = leer_semanal()
    roni = leer_roni()
    nuevas = construir(semanal, roni, panel.index)

    previas = [c for c in nuevas.columns if c in panel.columns]
    if previas:
        panel = panel.drop(columns=previas)
    panel = panel.join(nuevas)

    panel.to_csv(SALIDA, encoding="utf-8")

    print(f"\n[nuevas]  {len(nuevas.columns)} variables ENSO:")
    for c in nuevas.columns:
        s = nuevas[c].dropna()
        print(f"  {c:26s} cobertura {nuevas[c].notna().mean():6.1%}  "
              f"rango [{s.min():+.2f}, {s.max():+.2f}]")

    print(f"\n[salida]  {SALIDA.name}: {panel.shape[1]} variables")

    # --- la comparacion que motiva todo esto -----------------------------------
    print("\n" + "=" * 74)
    print("2026: lo que veia el modelo antes y lo que ve ahora")
    print("=" * 74)
    comp = pd.DataFrame({
        "oni_viejo": panel["oni"],
        "nino12_anom": panel["nino12_anom"],
        "nino34_anom": panel["nino34_anom"],
        "nino12_tend12s": panel["nino12_tend12s"],
        "precio": panel["precio_ponderado"],
    })
    comp = comp[comp.index >= "2025-11-01"].resample("MS").mean().round(2)
    print(comp.to_string())

    cruce_viejo = panel.loc[panel.index >= "2026-01-01", "oni"]
    cruce_nuevo = panel.loc[panel.index >= "2026-01-01", "nino12_anom"]
    pv = cruce_viejo[cruce_viejo > 0]
    pn = cruce_nuevo[cruce_nuevo > 0]
    if len(pv) and len(pn):
        print(f"\nPrimer dia de 2026 con senal positiva:")
        print(f"  oni (el que usaba el modelo): {pv.index.min().date()}")
        print(f"  nino12 semanal:               {pn.index.min().date()}")
        print(f"  holgura ganada:               "
              f"{(pv.index.min() - pn.index.min()).days} dias")


if __name__ == "__main__":
    main()
