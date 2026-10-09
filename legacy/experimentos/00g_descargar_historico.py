"""
================================================================================
DESCARGA HISTORICA 2000-2014 — mas transiciones ENSO para aprender
================================================================================

POR QUE
-------
El modelo falla a mediano plazo porque no sabe anticipar cambios de regimen, y no
los sabe anticipar porque casi no los ha visto: entre 2015 y 2025 hay solo dos o
tres transiciones ENSO completas. Con dos ejemplos ningun modelo aprende a
reconocer el tercero.

Extender hasta 2000 agrega, entre otros:

  2002-03  El Nino moderado
  2004-05  El Nino debil
  2006-07  El Nino debil
  2007-08  La Nina fuerte
  2009-10  El Nino moderado
  2010-11  La Nina fuerte
  2011-12  La Nina

Pasa de ~3 eventos a ~10, que es la diferencia entre no poder aprender el
mecanismo y quiza poder.

QUE SE DESCARGA Y QUE NO
------------------------
Solo el NUCLEO que existe de forma continua desde 2000, comprobado consultando
la API anio por anio. Se dejan fuera a proposito:

  PrecEsca, ENFICC, PrecCargConf   nacen con la reforma de 2006 y la API solo
                                   los sirve desde 2010
  RestAliv                         desde 2003
  solares y eolicas                no existian en el pais

Meterlas obligaria a elegir entre perder las variables o perder los anios, que es
la misma trampa de vol_pct_el_quimbo pero a escala de una decada.

La API de XM no tiene nada antes del 2000 (comprobado: 1996-1999 devuelven error).

Uso
---
  python 00g_descargar_historico.py --verificar
  python 00g_descargar_historico.py --descargar
================================================================================
"""

import argparse
import datetime as dt
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE = BASE / "cache_api"
CACHE_HIST = BASE / "cache_historico"

DESC_INI = dt.date(2000, 1, 1)
DESC_FIN = dt.date(2014, 12, 31)   # 2015 en adelante ya esta en cache_api

PAUSA = 0.35
DIAS_TRAMO = 30

# Nucleo continuo desde 2000: archivo -> (MetricId, Entity)
NUCLEO = {
    # precio y despacho
    "costo_marginal_prog": ("CostMargDesp", "Sistema"),
    # hidrologia
    "aportes_pct_sistema": ("PorcApor", "Sistema"),
    "aportes_media_hist":  ("AporEnerMediHist", "Sistema"),
    "volumen_util_pct":    ("PorcVoluUtilDiar", "Sistema"),
    "vertimientos":        ("VertEner", "Sistema"),
    "aportes_por_rio":     ("AporEner", "Rio"),
    "aportes_pct_rio":     ("PorcApor", "Rio"),
    "volumen_por_embalse":   ("VoluUtilDiarEner", "Embalse"),
    "capacidad_por_embalse": ("CapaUtilDiarEner", "Embalse"),
    "volumen_util_pct_emb":  ("PorcVoluUtilDiar", "Embalse"),
    # demanda
    "demanda_regulada":    ("DemaComeReg", "Sistema"),
    "demanda_no_regulada": ("DemaComeNoReg", "Sistema"),
    # generacion y oferta (por planta: alimentan la mezcla y el HHI)
    "gen_por_recurso":     ("Gene", "Recurso"),
    "gen_programada":      ("GeneProgDesp", "Recurso"),
    "disp_declarada":      ("DispoDeclarada", "Recurso"),
    "disp_comercial":      ("DispoCome", "Recurso"),
    "capacidad_efectiva":  ("CapEfecNeta", "Recurso"),
}

# El target va aparte: no vive en cache_api sino en data/
TARGET = ("PrecBolsNaci", "Sistema")


def abrir_api():
    from pydataxm import pydataxm
    return pydataxm.ReadDB()


def verificar(api):
    """Comprueba que cada metrica responda en los extremos del rango."""
    print(f"{'archivo':24s} {'metrica':22s} {'2000':>8s} {'2007':>8s} {'2014':>8s}")
    ok = []
    for arch, (mid, ent) in NUCLEO.items():
        marcas = []
        bien = True
        for a in (2000, 2007, 2014):
            try:
                d = api.request_data(mid, ent, dt.date(a, 6, 1), dt.date(a, 6, 3))
                n = 0 if d is None or d.empty else len(d)
                marcas.append(f"{n:>8d}")
                bien &= n > 0
            except Exception:
                marcas.append(f"{'ERR':>8s}")
                bien = False
            time.sleep(PAUSA)
        print(f"{arch:24s} {mid+'/'+ent[:3]:22s} " + " ".join(marcas))
        if bien:
            ok.append(arch)
    print(f"\ncontinuas en todo el rango: {len(ok)} de {len(NUCLEO)}")
    faltan = [a for a in NUCLEO if a not in ok]
    if faltan:
        print(f"con huecos: {faltan}")
    return ok


def descargar_serie(api, mid, ent, ini, fin):
    trozos, actual = [], ini
    while actual <= fin:
        hasta = min(actual + dt.timedelta(days=DIAS_TRAMO - 1), fin)
        try:
            d = api.request_data(mid, ent, actual, hasta)
            if d is not None and not d.empty:
                trozos.append(d)
        except Exception as e:
            print(f"      [!] {actual}: {type(e).__name__}", flush=True)
        time.sleep(PAUSA)
        actual = hasta + dt.timedelta(days=1)
    if not trozos:
        return None
    d = pd.concat(trozos, ignore_index=True)
    d["Date"] = pd.to_datetime(d["Date"])
    return d.drop_duplicates()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--descargar", action="store_true")
    args = ap.parse_args()
    if not (args.verificar or args.descargar):
        args.verificar = True

    print("=" * 78)
    print(f"DESCARGA HISTORICA {DESC_INI} a {DESC_FIN}")
    print("=" * 78)

    api = abrir_api()
    ok = verificar(api)

    if not args.descargar:
        print("\nSolo verificacion. Corre con --descargar para traer 2000-2014.")
        return

    CACHE_HIST.mkdir(exist_ok=True)
    print(f"\nDescargando {len(ok)} series + el target...")
    t0 = time.time()

    # --- target -------------------------------------------------------------
    destino = BASE / "data" / "PrecBolsNaci_Sistema_historico.csv"
    if destino.exists():
        print(f"  {'precio de bolsa':24s} ya existe")
    else:
        d = descargar_serie(api, *TARGET, DESC_INI, DESC_FIN)
        if d is not None:
            d.to_csv(destino, index=False)
            print(f"  {'precio de bolsa':24s} {len(d):8d} filas  "
                  f"{d['Date'].min().date()} a {d['Date'].max().date()}  "
                  f"[{time.time()-t0:.0f}s]", flush=True)

    # --- resto --------------------------------------------------------------
    resumen = []
    for arch in ok:
        salida = CACHE_HIST / f"{arch}.parquet"
        if salida.exists():
            print(f"  {arch:24s} ya existe", flush=True)
            continue
        mid, ent = NUCLEO[arch]
        d = descargar_serie(api, mid, ent, DESC_INI, DESC_FIN)
        if d is None:
            print(f"  {arch:24s} sin datos", flush=True)
            continue
        d.to_parquet(salida, index=False)
        resumen.append({"archivo": arch, "filas": len(d),
                        "desde": d["Date"].min().date(), "hasta": d["Date"].max().date()})
        print(f"  {arch:24s} {len(d):8d} filas  {d['Date'].min().date()} "
              f"a {d['Date'].max().date()}  [{time.time()-t0:.0f}s]", flush=True)

    if resumen:
        pd.DataFrame(resumen).to_csv(BASE / "salidas_horizontes" / "descarga_historico.csv",
                                     index=False)
    print(f"\n[salida] {CACHE_HIST}  ({(time.time()-t0)/60:.1f} min)")
    print("cache_api/ y cache_2026/ no se tocaron.")


if __name__ == "__main__":
    main()
