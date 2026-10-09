"""
================================================================================
PANEL 2026 — reconstruye el panel completo incluyendo el anio en curso
================================================================================

Toma lo descargado por 00c_descargar_2026.py (cache_2026/), lo une con la cache
historica (cache_api/) y vuelve a correr la consolidacion y la ampliacion para
producir un panel que llega hasta hoy.

Lo que hace, en orden:
  1. Descarga el TARGET de 2026 (PrecBolsNaci), que no estaba en la descarga
     anterior porque no vive en cache_api sino en data/.
  2. Une cache_api/ + cache_2026/ en una carpeta nueva, sin tocar ninguna de las
     dos originales.
  3. Corre 00_consolidar_panel.py apuntando a la carpeta unida, sobrescribiendo
     sus constantes de modulo en vez de editar el archivo.
  4. Corre la ampliacion de 00b_ampliar_panel.py sobre el panel resultante.

Salida: panel_diario_ampliado_2026.csv (2015 hasta hoy)

NADA se sobrescribe: data/panel_d.parquet y panel_diario_ampliado.csv quedan
intactos. Los archivos nuevos llevan el sufijo _2026.

Uso
---
  python 00d_panel_2026.py
================================================================================
"""

import datetime as dt
import shutil
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
CACHE_UNIDA = BASE / "cache_unida"
DATA = BASE / "data"

TARGET_CSV_2026 = DATA / "PrecBolsNaci_Sistema_2026.csv"
PANEL_PARQUET = DATA / "panel_d_2026.parquet"
SALIDA_CSV = BASE / "panel_diario_ampliado_2026.csv"

DESC_INI = dt.date(2026, 1, 1)
DESC_FIN = dt.date.today()


# ==============================================================================
# 1. TARGET DE 2026
# ==============================================================================

def descargar_target():
    """
    El precio de bolsa (PrecBolsNaci horario por Sistema). El consolidador lo
    lee de data/PrecBolsNaci_Sistema.csv y promedia las 24 horas.
    """
    if TARGET_CSV_2026.exists():
        print(f"[target]  ya existe {TARGET_CSV_2026.name}, no se vuelve a bajar")
        return

    from pydataxm import pydataxm
    api = pydataxm.ReadDB()

    trozos, actual = [], DESC_INI
    while actual <= DESC_FIN:
        fin = min(actual + dt.timedelta(days=29), DESC_FIN)
        try:
            d = api.request_data("PrecBolsNaci", "Sistema", actual, fin)
            if d is not None and not d.empty:
                trozos.append(d)
        except Exception as e:
            print(f"    [!] {actual} a {fin}: {type(e).__name__}")
        time.sleep(0.4)
        actual = fin + dt.timedelta(days=1)

    if not trozos:
        raise SystemExit("No se pudo descargar el precio de bolsa de 2026.")

    nuevo = pd.concat(trozos, ignore_index=True)
    nuevo["Date"] = pd.to_datetime(nuevo["Date"])

    viejo = pd.read_csv(DATA / "PrecBolsNaci_Sistema.csv")
    viejo["Date"] = pd.to_datetime(viejo["Date"])

    todo = (pd.concat([viejo, nuevo], ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last")
            .sort_values("Date"))
    todo.to_csv(TARGET_CSV_2026, index=False)
    print(f"[target]  {len(nuevo)} dias nuevos -> {todo['Date'].min().date()} "
          f"a {todo['Date'].max().date()}")


# ==============================================================================
# 2. UNIR LAS DOS CACHES
# ==============================================================================

def unir_caches():
    if CACHE_UNIDA.exists():
        shutil.rmtree(CACHE_UNIDA)
    CACHE_UNIDA.mkdir()

    nuevos = {p.stem: p for p in CACHE_2026.glob("*.parquet")}
    unidos, copiados = 0, 0

    for viejo in sorted(CACHE.glob("*.parquet")):
        d = pd.read_parquet(viejo)
        if viejo.stem in nuevos:
            n = pd.read_parquet(nuevos[viejo.stem])
            # Alinear columnas antes de concatenar: si la API cambio el esquema
            # una concatenacion ciega crearia columnas fantasma llenas de NaN.
            comunes = [c for c in d.columns if c in n.columns]
            if set(comunes) != set(d.columns):
                faltan = set(d.columns) - set(comunes)
                print(f"    [!] {viejo.stem}: la descarga no trae {sorted(faltan)}")
            d = pd.concat([d, n[comunes]], ignore_index=True)
            if "Date" in d.columns:
                d["Date"] = pd.to_datetime(d["Date"])
                d = d.sort_values("Date")
            d = d.drop_duplicates()
            unidos += 1
        else:
            copiados += 1
        d.to_parquet(CACHE_UNIDA / viejo.name, index=False)

    print(f"[cache]   {unidos} series extendidas con 2026, {copiados} sin cambios")
    print(f"          -> {CACHE_UNIDA}")


# ==============================================================================
# 3. CONSOLIDAR  (reusando el script original, sin editarlo)
# ==============================================================================

def consolidar():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cons", BASE / "00_consolidar_panel.py")
    cons = importlib.util.module_from_spec(spec)
    sys.modules["cons"] = cons
    spec.loader.exec_module(cons)

    # Se apunta a la cache unida y al target extendido, y se escribe a un
    # parquet nuevo. El script original no se modifica.
    cons.CACHE_DIR = CACHE_UNIDA
    cons.OUT_PATH = PANEL_PARQUET

    original = cons.cargar_precio_bolsa

    def target_2026():
        return cons.cargar_csv_serie_xm(TARGET_CSV_2026,
                                        nombre="precio_ponderado (TARGET 2026)",
                                        agg_hora="mean")

    cons.cargar_precio_bolsa = target_2026
    try:
        cons.main()
    finally:
        cons.cargar_precio_bolsa = original


# ==============================================================================
# 4. AMPLIAR
# ==============================================================================

def ampliar():
    import importlib.util
    spec = importlib.util.spec_from_file_location("amp", BASE / "00b_ampliar_panel.py")
    amp = importlib.util.module_from_spec(spec)
    sys.modules["amp"] = amp
    spec.loader.exec_module(amp)

    amp.CACHE = CACHE_UNIDA
    amp.SALIDA_CSV = SALIDA_CSV
    amp.SALIDA_MD = BASE / "DICCIONARIO_VARIABLES_2026.md"
    amp.REGISTRO.clear()

    base = pd.read_parquet(PANEL_PARQUET).sort_index()
    base.index = pd.to_datetime(base.index)
    base.index.name = "fecha"
    print(f"[base]    panel consolidado: {base.shape[0]} dias x {base.shape[1]} variables")

    rec = amp.cargar_recursos()
    piezas = []
    for nombre, fn in [("mezcla de generacion", lambda: amp.mezcla_generacion(rec)),
                       ("disponibilidad por tecnologia",
                        lambda: amp.disponibilidad_por_tecnologia(rec)),
                       ("hidrologia desagregada", amp.hidrologia_desagregada),
                       ("perfil intradiario", amp.perfil_intradiario),
                       ("precio del gas", amp.precio_gas)]:
        try:
            p = fn()
            if len(p.columns):
                p.index = pd.to_datetime(p.index)
                piezas.append(p)
                print(f"[nuevo]   {nombre}: {len(p.columns)} variables")
        except Exception as e:
            print(f"[ERROR]   {nombre}: {type(e).__name__}: {e}")

    nuevas = pd.concat(piezas, axis=1)
    nuevas = nuevas[~nuevas.index.duplicated()]

    panel = base.join(nuevas, how="left")
    panel.to_csv(SALIDA_CSV, encoding="utf-8")
    return panel


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 74)
    print("PANEL 2026")
    print("=" * 74)

    descargar_target()
    unir_caches()

    print("\n" + "-" * 74)
    print("CONSOLIDACION")
    print("-" * 74)
    consolidar()

    print("\n" + "-" * 74)
    print("AMPLIACION")
    print("-" * 74)
    panel = ampliar()

    print("\n" + "=" * 74)
    print("RESULTADO")
    print("=" * 74)
    print(f"{SALIDA_CSV.name}: {panel.shape[0]} dias x {panel.shape[1]} variables")
    print(f"  {panel.index.min().date()} a {panel.index.max().date()}")
    print(f"  {SALIDA_CSV.stat().st_size / 1e6:.2f} MB")

    d26 = panel[panel.index >= "2026-01-01"]
    print(f"\nFilas de 2026: {len(d26)}")
    if len(d26):
        obj = d26["precio_ponderado"].dropna()
        print(f"  precio_ponderado: {len(obj)} dias con dato "
              f"({obj.index.min().date()} a {obj.index.max().date()})")
        print(f"    media {obj.mean():.1f}  min {obj.min():.1f}  max {obj.max():.1f} COP/kWh")
        cob = d26.notna().mean()
        print(f"  variables con cobertura >= 80% en 2026: "
              f"{(cob >= 0.8).sum()} de {len(cob)}")
        flojas = cob[(cob < 0.8) & (cob > 0)].sort_values()
        if len(flojas):
            print(f"  cobertura parcial: {list(flojas.index[:12])}")
        vacias = cob[cob == 0]
        if len(vacias):
            print(f"  SIN datos en 2026 ({len(vacias)}): {list(vacias.index[:12])}")

    print(f"\nNo se modifico data/panel_d.parquet ni panel_diario_ampliado.csv")


if __name__ == "__main__":
    main()
