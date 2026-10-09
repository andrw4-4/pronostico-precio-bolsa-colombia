"""
================================================================================
DESCARGA DE 2026 — extiende el panel con datos frescos de la API de XM
================================================================================

En el repositorio no habia script de descarga: cache_api/ se lleno a mano y los
archivos no guardan a que metrica de la API corresponden. Este script reconstruye
ese mapeo y lo VERIFICA antes de descargar nada.

Como verifica
-------------
Para cada par (archivo, MetricId) descarga una ventana que YA esta en la cache y
compara los valores. Si coinciden, el mapeo es correcto y se puede confiar en lo
que se descargue de 2026. Si no coinciden, se reporta y no se descarga.

Sin este paso, un mapeo equivocado meteria una serie distinta con el nombre
correcto, que es el tipo de error que no se detecta despues.

Seguridad
---------
NO escribe en cache_api/. Los datos nuevos van a cache_2026/, y el panel se
arma leyendo de las dos carpetas. Asi la cache original queda intacta.

Uso
---
  python 00c_descargar_2026.py --verificar     # solo comprueba el mapeo
  python 00c_descargar_2026.py --descargar     # verifica y descarga 2026
================================================================================
"""

import argparse
import datetime as dt
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE = BASE / "cache_api"
CACHE_2026 = BASE / "cache_2026"

# Ventana que ya esta en la cache, para comprobar el mapeo
VERIF_INI = dt.date(2025, 6, 1)
VERIF_FIN = dt.date(2025, 6, 10)

# Lo que queremos traer
DESC_INI = dt.date(2026, 1, 1)
DESC_FIN = dt.date.today()

TOLERANCIA = 1e-6          # diferencia relativa aceptada en la verificacion
PAUSA = 0.4                # segundos entre llamadas, para no saturar la API

# archivo de cache -> (MetricId, Entity)
MAPEO = {
    # --- Sistema, diario -----------------------------------------------------
    "aportes_media_hist":   ("AporEnerMediHist", "Sistema"),
    "aportes_pct_sistema":  ("PorcApor", "Sistema"),
    "volumen_util_pct":     ("PorcVoluUtilDiar", "Sistema"),
    "cee":                  ("CEE", "Sistema"),
    "cere":                 ("CERE", "Sistema"),
    "mc":                   ("MC", "Sistema"),
    "enficc":               ("ENFICC", "Sistema"),
    "precio_escasez":       ("PrecEsca", "Sistema"),
    "precio_escasez_act":   ("PrecEscaAct", "Sistema"),
    "precio_escasez_inf":   ("PrecEscaInf", "Sistema"),
    "precio_escasez_pon":   ("PrecEscaPon", "Sistema"),
    "precio_marg_escasez":  ("PrecEscaMarg", "Sistema"),
    # La cache es horaria, asi que NO es PrecPromCont (que es diario): es el
    # precio de contratos del mercado REGULADO, que si viene por hora.
    "precio_prom_contrato": ("PrecPromContRegu", "Sistema"),
    "demanda_upme_alto":    ("EscDemUPMEAlto", "Sistema"),
    "demanda_upme_medio":   ("EscDemUPMEMedio", "Sistema"),
    "demanda_upme_bajo":    ("EscDemUPMEBajo", "Sistema"),
    "vertimientos":         ("VertEner", "Sistema"),

    # --- Sistema, horario ----------------------------------------------------
    "costo_marginal_prog":   ("CostMargDesp", "Sistema"),
    "max_precio_oferta":     ("MaxPrecOferNal", "Sistema"),
    "restricciones":         ("RestAliv", "Sistema"),
    "restricciones_sin_aliv": ("RestSinAliv", "Sistema"),
    "importaciones":         ("ImpoEner", "Sistema"),
    "exportaciones":         ("ExpoEner", "Sistema"),
    "perdidas_energia":      ("PerdidasEner", "Sistema"),
    "demanda_regulada":      ("DemaComeReg", "Sistema"),
    "demanda_no_regulada":   ("DemaComeNoReg", "Sistema"),
    "compras_contrato":      ("CompContEner", "Sistema"),
    "precio_cont_no_regu":   ("PrecPromContNoRegu", "Sistema"),
    "emisiones_co2_sistema": ("factorEmisionCO2e", "Sistema"),

    # --- Recurso (por planta) ------------------------------------------------
    "gen_por_recurso":     ("Gene", "Recurso"),
    "disp_declarada":      ("DispoDeclarada", "Recurso"),
    "disp_comercial":      ("DispoCome", "Recurso"),
    "disp_real":           ("DispoReal", "Recurso"),
    "gen_programada":      ("GeneProgDesp", "Recurso"),
    "gen_seguridad":       ("GeneSeguridad", "Recurso"),
    "gen_fuera_merito":    ("GeneFueraMerito", "Recurso"),
    "precio_oferta_desp":  ("PrecOferDesp", "Recurso"),
    "precio_cargo_conf":   ("PrecCargConf", "Recurso"),
    "capacidad_efectiva":  ("CapEfecNeta", "Recurso"),
    "irradiacion_global":  ("IrrGlobal", "Recurso"),
    "irradiacion_panel":   ("IrrPanel", "Recurso"),
    "temp_panel":          ("TempPanel", "Recurso"),
    "temp_ambiente_solar": ("TempAmbSolar", "Recurso"),
    "recurso_marginal":    ("IndRecMargina", "Recurso"),
    "consumo_combustible": ("ConsCombustibleMBTU", "Recurso"),

    # --- Rio -----------------------------------------------------------------
    "aportes_por_rio": ("AporEner", "Rio"),
    "aportes_pct_rio": ("PorcApor", "Rio"),

    # --- Embalse -------------------------------------------------------------
    "volumen_por_embalse":   ("VoluUtilDiarEner", "Embalse"),
    "capacidad_por_embalse": ("CapaUtilDiarEner", "Embalse"),
    "volumen_util_pct_emb":  ("PorcVoluUtilDiar", "Embalse"),
}

# Estas tres estan en la cache pero no se pudo identificar su metrica por nombre.
# Se listan aparte para que quede explicito que NO se van a actualizar.
SIN_MAPEO = ["demanda_no_atendida", "dem_no_atendida_noprog", "demanda_por_or"]

# Series que dejaron de publicarse o que no cubren la ventana por defecto, con
# una ventana alterna donde SI hay datos para comprobar el mapeo.
VENTANA_ALTERNA = {
    # XM dejo de publicar el precio de escasez de activacion el 2025-02-28
    "precio_escasez_act": (dt.date(2024, 6, 1), dt.date(2024, 6, 10)),
}


def abrir_api():
    from pydataxm import pydataxm
    return pydataxm.ReadDB()


def columnas_valor(df):
    """Devuelve las columnas numericas comparables de un df de la API."""
    horas = [c for c in df.columns if c.startswith("Values_Hour")]
    if horas:
        return horas
    return [c for c in ("Value",) if c in df.columns]


def clave_fila(df):
    """Columnas que identifican una fila (ademas de la fecha)."""
    for c in ("Values_code", "Name", "Values_Name"):
        if c in df.columns:
            return c
    return None


def verificar(api, archivo, metric, entidad):
    ruta = CACHE / f"{archivo}.parquet"
    if not ruta.exists():
        return "SIN_CACHE", "el archivo no existe en cache_api/"

    ini, fin = VENTANA_ALTERNA.get(archivo, (VERIF_INI, VERIF_FIN))

    cache = pd.read_parquet(ruta)
    cache["Date"] = pd.to_datetime(cache["Date"])
    trozo_cache = cache[(cache["Date"] >= pd.Timestamp(ini))
                        & (cache["Date"] <= pd.Timestamp(fin))]
    if trozo_cache.empty:
        return "SIN_SOLAPE", "la cache no cubre la ventana de verificacion"

    try:
        api_df = api.request_data(metric, entidad, ini, fin)
    except Exception as e:
        return "ERROR_API", f"{type(e).__name__}: {e}"

    if api_df is None or api_df.empty:
        return "VACIO", "la API no devolvio datos"

    api_df["Date"] = pd.to_datetime(api_df["Date"])

    cols = columnas_valor(trozo_cache)
    if not cols or not set(cols).issubset(api_df.columns):
        return "FORMATO", f"columnas distintas: cache={list(trozo_cache.columns)[:4]} "\
                          f"api={list(api_df.columns)[:4]}"

    llave = clave_fila(trozo_cache)
    idx = ["Date"] + ([llave] if llave and llave in api_df.columns else [])

    a = trozo_cache.groupby(idx)[cols].first().apply(pd.to_numeric, errors="coerce")
    b = api_df.groupby(idx)[cols].first().apply(pd.to_numeric, errors="coerce")
    comun = a.index.intersection(b.index)
    if len(comun) == 0:
        return "SIN_FILAS", "no hay filas comparables"

    a, b = a.loc[comun], b.loc[comun]
    denom = a.abs().replace(0, np.nan)
    rel = ((a - b).abs() / denom).stack().dropna()
    if len(rel) == 0:
        iguales = bool(np.allclose(a.fillna(0), b.fillna(0)))
        return ("OK", f"{len(comun)} filas identicas") if iguales else \
               ("DIFIERE", "valores distintos (todo cero en cache)")

    peor = float(rel.max())
    if peor <= TOLERANCIA:
        return "OK", f"{len(comun)} filas, error relativo max {peor:.2e}"
    return "DIFIERE", f"error relativo max {peor:.3f} en {len(comun)} filas"


def descargar(api, archivo, metric, entidad):
    """Descarga 2026 por tramos de 30 dias y guarda en cache_2026/."""
    trozos, actual = [], DESC_INI
    while actual <= DESC_FIN:
        fin = min(actual + dt.timedelta(days=29), DESC_FIN)
        try:
            d = api.request_data(metric, entidad, actual, fin)
            if d is not None and not d.empty:
                trozos.append(d)
        except Exception as e:
            print(f"      [!] {actual} a {fin}: {type(e).__name__}")
        time.sleep(PAUSA)
        actual = fin + dt.timedelta(days=1)

    if not trozos:
        return 0, None

    todo = pd.concat(trozos, ignore_index=True)
    todo["Date"] = pd.to_datetime(todo["Date"])
    todo = todo.drop_duplicates()

    CACHE_2026.mkdir(exist_ok=True)
    todo.to_parquet(CACHE_2026 / f"{archivo}.parquet", index=False)
    return len(todo), (todo["Date"].min().date(), todo["Date"].max().date())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--descargar", action="store_true")
    args = ap.parse_args()
    if not (args.verificar or args.descargar):
        args.verificar = True

    print("=" * 76)
    print("DESCARGA DE 2026")
    print(f"verificacion contra cache: {VERIF_INI} a {VERIF_FIN}")
    if args.descargar:
        print(f"descarga:                  {DESC_INI} a {DESC_FIN}")
    print("=" * 76)

    api = abrir_api()
    resultados = []

    for archivo, (metric, entidad) in MAPEO.items():
        estado, detalle = verificar(api, archivo, metric, entidad)
        marca = {"OK": "  OK  "}.get(estado, f"{estado:6s}"[:6])
        print(f"[{marca}] {archivo:24s} <- {metric:20s} ({entidad:8s}) {detalle}")
        resultados.append({"archivo": archivo, "metric": metric, "entidad": entidad,
                           "estado": estado, "detalle": detalle})
        time.sleep(PAUSA)

    res = pd.DataFrame(resultados)
    res.to_csv(BASE / "salidas_horizontes" / "verificacion_mapeo.csv", index=False)

    ok = res[res["estado"] == "OK"]
    print()
    print("=" * 76)
    print(f"VERIFICADAS: {len(ok)} de {len(res)}")
    for estado, g in res[res["estado"] != "OK"].groupby("estado"):
        print(f"  {estado}: {list(g['archivo'])}")
    print(f"  sin mapeo conocido: {SIN_MAPEO}")
    print("=" * 76)

    if not args.descargar:
        print("\nSolo verificacion. Corre con --descargar para traer 2026.")
        return

    print(f"\nDescargando 2026 para las {len(ok)} verificadas...")
    filas = []
    for _, r in ok.iterrows():
        n, rango = descargar(api, r["archivo"], r["metric"], r["entidad"])
        txt = f"{rango[0]} a {rango[1]}" if rango else "sin datos"
        print(f"  {r['archivo']:24s} {n:7d} filas   {txt}")
        filas.append({"archivo": r["archivo"], "filas": n,
                      "desde": rango[0] if rango else None,
                      "hasta": rango[1] if rango else None})

    pd.DataFrame(filas).to_csv(BASE / "salidas_horizontes" / "descarga_2026.csv",
                               index=False)
    print(f"\n[salida] {CACHE_2026}")
    print("Los datos de 2026 quedaron aparte: cache_api/ no se modifico.")


if __name__ == "__main__":
    main()
