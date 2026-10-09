"""
================================================================================
LLUVIA SOBRE LAS CUENCAS — el motor fisico que el panel nunca vio
================================================================================

QUE FALTA HOY
-------------
El panel ve los APORTES: el agua que ya llego al embalse. Nunca ve la LLUVIA que
los produce. Y la lluvia cae sobre la cuenca varios dias antes de convertirse en
aporte, asi que contiene informacion sobre aportes que todavia no se observaron.

Ademas los aportes vienen agregados al sistema (o por rio, sin peso). La lluvia
da detalle ESPACIAL: si llueve sobre Antioquia pero no sobre el Guavio, el
agregado nacional no lo distingue y el precio si.

QUE SE USA Y POR QUE NO ES UN PRONOSTICO
----------------------------------------
Se uso el reanalisis ERA5 (Open-Meteo Archive API), que es lluvia OBSERVADA, no
pronosticada. Se evaluo usar pronosticos reales y se descarto:

  Previous Runs API  da el pronostico emitido N dias antes (vintage correcto),
                     pero el archivo arranca en enero de 2024: 21 meses, muy
                     poco para entrenar.
  Historical Forecast API  llega a 2017 pero archiva las horas iniciales de cada
                     corrida, o sea calidad de analisis. Usarla como si fuera
                     pronostico a 7 dias seria FUGA.

ERA5 cubre 1940 en adelante, asi que encaja con el panel largo 2000-2026.

ANTI-FUGA
---------
ERA5 se publica con unos 5 dias de rezago. Se aplican 5 dias, y encima el
pipeline de caracteristicas pone sus propios rezagos. La climatologia se calcula
con 2000-2014, un periodo de referencia fijo anterior a la ventana de modelado
original (2015+).

LAS CUENCAS
-----------
Los 8 embalses mayores concentran el 84,5% de la capacidad util del pais. Las
coordenadas son centroides APROXIMADOS de cada cuenca, no promedios de area
real: es una simplificacion documentada, no una medicion exacta.

Uso
---
  python 00h_lluvia_cuencas.py
================================================================================
"""

import json
import time
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
PANEL = BASE / "panel_diario_ampliado_2026.csv"
CACHE_LLUVIA = BASE / "data" / "lluvia_cuencas.csv"

API = "https://archive-api.open-meteo.com/v1/archive"
INI, FIN = "2000-01-01", "2026-09-20"

REZAGO_ERA5_DIAS = 5
CLIMA_INI, CLIMA_FIN = "2000-01-01", "2014-12-31"

# embalse -> (lat, lon, capacidad util media en GWh)
CUENCAS = {
    "penol":       (6.28, -75.10, 4111.9),
    "bogota":      (4.95, -73.95, 3890.3),
    "guavio":      (4.82, -73.48, 1950.4),
    "esmeralda":   (4.92, -73.35, 1117.1),
    "quimbo":      (2.50, -75.62, 1089.8),
    "topocoro":    (6.80, -73.42,  999.3),
    "chuza":       (4.58, -73.72,  987.8),
    "riogrande":   (6.55, -75.45,  542.3),
}

VENTANAS = [3, 7, 15, 30, 60, 90]


def bajar_cuenca(lat, lon):
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "start_date": INI, "end_date": FIN,
        "daily": "precipitation_sum",
        "timezone": "America/Bogota",
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    s = pd.Series(d["daily"]["precipitation_sum"],
                  index=pd.to_datetime(d["daily"]["time"]), dtype="float64")
    return s


def descargar():
    if CACHE_LLUVIA.exists():
        print(f"[cache]   ya existe {CACHE_LLUVIA.name}")
        return pd.read_csv(CACHE_LLUVIA, parse_dates=["fecha"], index_col="fecha")

    series = {}
    for nombre, (lat, lon, _) in CUENCAS.items():
        t = time.time()
        series[nombre] = bajar_cuenca(lat, lon)
        print(f"  {nombre:12s} {len(series[nombre])} dias  [{time.time()-t:.1f}s]", flush=True)
        time.sleep(0.5)

    d = pd.DataFrame(series)
    d.index.name = "fecha"
    CACHE_LLUVIA.parent.mkdir(exist_ok=True)
    d.to_csv(CACHE_LLUVIA)
    return d


def climatologia(s):
    """
    Media por dia del anio, suavizada con ventana de 15 dias.

    Sin suavizar, el 3 de marzo tendria su propia media de 15 observaciones y
    seria puro ruido. Con la ventana, cada dia se estima con ~225 observaciones.
    """
    ref = s.loc[CLIMA_INI:CLIMA_FIN]
    doy = ref.groupby(ref.index.dayofyear).mean()
    # circular: el 31 de diciembre es vecino del 1 de enero
    ext = pd.concat([doy.iloc[-15:], doy, doy.iloc[:15]])
    suave = ext.rolling(15, center=True, min_periods=5).mean().iloc[15:-15]
    return suave


def construir(lluvia, indice):
    lluvia = lluvia.shift(REZAGO_ERA5_DIAS)   # rezago de publicacion de ERA5

    pesos = pd.Series({k: v[2] for k, v in CUENCAS.items()})
    pesos = pesos / pesos.sum()

    salida = {}

    # --- lluvia del sistema, ponderada por capacidad --------------------------
    sistema = (lluvia * pesos).sum(axis=1)
    salida["lluvia_sistema"] = sistema

    for w in VENTANAS:
        salida[f"lluvia_sistema_acum{w}"] = sistema.rolling(w).sum()

    # --- anomalia contra la climatologia: la variable que de verdad informa ----
    # La lluvia cruda esta dominada por el ciclo estacional, que el modelo ya
    # saca del calendario. Lo que informa es cuanto se APARTA de lo normal.
    clima = climatologia(sistema)
    esperada = pd.Series(sistema.index.dayofyear, index=sistema.index).map(clima)
    salida["lluvia_anomalia"] = sistema - esperada

    for w in [30, 90]:
        acum_real = sistema.rolling(w).sum()
        acum_esp = esperada.rolling(w).sum()
        salida[f"lluvia_anom_acum{w}"] = acum_real - acum_esp
        # razon: util cuando el nivel absoluto varia mucho entre cuencas
        salida[f"lluvia_razon{w}"] = acum_real / acum_esp.replace(0, np.nan)

    # --- detalle por cuenca: solo las cuatro mayores ---------------------------
    # Con las ocho se duplicarian las columnas sin aportar: las pequenias pesan
    # poco en el agregado y estan muy correlacionadas con sus vecinas.
    for nombre in ["penol", "bogota", "guavio", "quimbo"]:
        s = lluvia[nombre]
        salida[f"lluvia_{nombre}_acum30"] = s.rolling(30).sum()
        cl = climatologia(s)
        esp = pd.Series(s.index.dayofyear, index=s.index).map(cl)
        salida[f"lluvia_{nombre}_anom30"] = (s.rolling(30).sum()
                                             - esp.rolling(30).sum())

    # --- gradiente norte-sur ---------------------------------------------------
    # Antioquia y el alto Magdalena responden distinto a El Nino. Si una cuenca
    # se seca y la otra no, el agregado nacional lo esconde.
    salida["lluvia_gradiente_ns"] = (
        lluvia[["penol", "riogrande"]].mean(axis=1)
        - lluvia[["quimbo"]].mean(axis=1)
    ).rolling(30).mean()

    return pd.DataFrame(salida).reindex(indice)


def main():
    print("=" * 74)
    print("LLUVIA SOBRE LAS CUENCAS")
    print("=" * 74)

    print(f"[descarga] {len(CUENCAS)} cuencas, ERA5 {INI} a {FIN}")
    lluvia = descargar()
    print(f"[lluvia]   {lluvia.shape[0]} dias x {lluvia.shape[1]} cuencas, "
          f"{lluvia.index.min().date()} a {lluvia.index.max().date()}")

    panel = pd.read_csv(PANEL, parse_dates=["fecha"], index_col="fecha").sort_index()
    nuevas = construir(lluvia, panel.index)

    previas = [c for c in nuevas.columns if c in panel.columns]
    if previas:
        panel = panel.drop(columns=previas)
    panel = panel.join(nuevas)
    panel.to_csv(PANEL, encoding="utf-8")

    print(f"\n[nuevas]   {len(nuevas.columns)} variables de lluvia:")
    for c in nuevas.columns:
        s = nuevas[c].dropna()
        print(f"  {c:30s} cob {nuevas[c].notna().mean():6.1%}  "
              f"[{s.min():8.1f}, {s.max():8.1f}]")

    print(f"\n[salida]   {PANEL.name}: {panel.shape[1]} variables")

    # --- la relacion que motiva todo esto -------------------------------------
    print("\n" + "=" * 74)
    print("LLUVIA vs APORTES vs PRECIO (correlaciones en 2015-2026)")
    print("=" * 74)
    sub = panel[panel.index >= "2015-01-01"]
    obj = np.log(sub["precio_ponderado"]).diff(7).shift(-7)   # cambio a 7 dias
    for c in ["lluvia_anom_acum30", "lluvia_anom_acum90", "lluvia_razon90",
              "lluvia_sistema_acum30", "aportes_pct_sistema"]:
        if c in sub.columns:
            r = sub[c].corr(obj)
            print(f"  {c:26s} corr con el cambio de precio a 7 dias: {r:+.3f}")

    print("\n2026, mes a mes:")
    comp = pd.DataFrame({
        "lluvia_anom_acum90": panel["lluvia_anom_acum90"],
        "lluvia_razon90": panel["lluvia_razon90"],
        "aportes_pct": panel["aportes_pct_sistema"],
        "precio": panel["precio_ponderado"],
    })
    print(comp[comp.index >= "2025-11-01"].resample("MS").mean().round(2).to_string())


if __name__ == "__main__":
    main()
