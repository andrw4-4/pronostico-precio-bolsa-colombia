"""
================================================================================
PANEL LARGO 2000-2026 — 26 anios, ~10 transiciones ENSO
================================================================================

POR QUE
-------
El modelo a mediano plazo falla porque no ha visto suficientes cambios de
regimen: entre 2015 y 2025 hay dos o tres transiciones ENSO. Extender a 2000
suma los Nino de 2002-03, 2004-05, 2006-07 y 2009-10 y las Nina de 2007-08,
2010-11 y 2011-12.

EL COMPROMISO QUE HAY QUE ACEPTAR
---------------------------------
Solo 17 series de XM existen de forma continua desde 2000. Las demas nacen
despues (precio de escasez y ENFICC con la reforma de 2006, solares y eolicas
desde 2019). Asi que el panel largo es ANCHO EN TIEMPO y ESTRECHO EN VARIABLES,
al reves del panel de 2015-2026.

No es un defecto del diseno, es la unica forma de evitar la trampa que ya nos
costo diez meses con vol_pct_el_quimbo: si se exige que todas las variables
tengan dato el mismo dia, la que empieza mas tarde manda sobre todas.

Se construyen DOS paneles y se comparan, en vez de suponer cual es mejor:

  panel_largo_2000_2026.csv     26 anios, pocas variables
  panel_diario_ampliado_2026.csv (ya existe)  11 anios, 135 variables

ADVERTENCIA SOBRE EL CAMBIO ESTRUCTURAL
---------------------------------------
El sistema de 2000 no es el de 2026: 140 plantas contra 500, sin renovables no
convencionales, sin cargo por confiabilidad, con la mitad de demanda. Que haya
mas datos no garantiza que ayuden. Es una hipotesis a probar, no una mejora
dada por hecha.

Uso
---
  python 00j_panel_largo.py
================================================================================
"""

import importlib.util
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE = BASE / "cache_api"
CACHE_HIST = BASE / "cache_historico"
CACHE_2026 = BASE / "cache_2026"
CACHE_TODO = BASE / "cache_todo"
DATA = BASE / "data"

TARGET_LARGO = DATA / "PrecBolsNaci_Sistema_largo.csv"
DEMANDA_LARGO = DATA / "DemaCome_Sistema_largo.csv"
PANEL_PARQUET = DATA / "panel_d_largo.parquet"
SALIDA = BASE / "panel_largo_2000_2026.csv"


def unir_csv_target():
    """Junta las tres epocas del precio de bolsa horario en un solo CSV."""
    partes = []
    for f in ["PrecBolsNaci_Sistema_historico.csv",   # 2000-2014
              "PrecBolsNaci_Sistema_2026.csv"]:        # 2015-2026 (ya incluye todo)
        p = DATA / f
        if p.exists():
            d = pd.read_csv(p)
            d["Date"] = pd.to_datetime(d["Date"])
            partes.append(d)
    if not partes:
        raise SystemExit("No encuentro los CSV del precio de bolsa.")

    cols = set(partes[0].columns)
    for p in partes[1:]:
        cols &= set(p.columns)
    cols = [c for c in partes[0].columns if c in cols]

    todo = (pd.concat([p[cols] for p in partes], ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last").sort_values("Date"))
    todo.to_csv(TARGET_LARGO, index=False)
    print(f"[target]  {len(todo)} dias  {todo['Date'].min().date()} a "
          f"{todo['Date'].max().date()}")


def unir_csv_demanda():
    partes = []
    for f in ["DemaCome_Sistema_historico.csv", "DemaCome_Sistema_2026.csv",
              "DemaCome_Sistema.csv"]:
        p = DATA / f
        if p.exists():
            d = pd.read_csv(p)
            d["Date"] = pd.to_datetime(d["Date"])
            partes.append(d)
    if not partes:
        print("[demanda] no hay CSV horarios, el perfil intradiario quedara vacio")
        return False
    cols = set(partes[0].columns)
    for p in partes[1:]:
        cols &= set(p.columns)
    cols = [c for c in partes[0].columns if c in cols]
    todo = (pd.concat([p[cols] for p in partes], ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last").sort_values("Date"))
    todo.to_csv(DEMANDA_LARGO, index=False)
    print(f"[demanda] {len(todo)} dias  {todo['Date'].min().date()} a "
          f"{todo['Date'].max().date()}")
    return True


def unir_caches():
    """
    cache_historico + cache_api + cache_2026 -> cache_todo

    Solo se conservan las series que existen en la cache HISTORICA: son las que
    cubren los 26 anios. Las demas se dejan fuera a proposito.
    """
    if CACHE_TODO.exists():
        shutil.rmtree(CACHE_TODO)
    CACHE_TODO.mkdir()

    nucleo = sorted(p.stem for p in CACHE_HIST.glob("*.parquet"))
    print(f"[nucleo]  {len(nucleo)} series continuas desde 2000")

    for nombre in nucleo:
        partes = []
        for carpeta in (CACHE_HIST, CACHE, CACHE_2026):
            p = carpeta / f"{nombre}.parquet"
            if p.exists():
                partes.append(pd.read_parquet(p))
        if not partes:
            continue
        cols = set(partes[0].columns)
        for p in partes[1:]:
            cols &= set(p.columns)
        cols = [c for c in partes[0].columns if c in cols]
        d = pd.concat([p[cols] for p in partes], ignore_index=True)
        if "Date" in d.columns:
            d["Date"] = pd.to_datetime(d["Date"])
            d = d.sort_values("Date")
        d = d.drop_duplicates()
        d.to_parquet(CACHE_TODO / f"{nombre}.parquet", index=False)

    # metadatos que el consolidador necesita
    for extra in ("catalogo_metricas", "listado_embalses", "listado_rios"):
        p = CACHE / f"{extra}.parquet"
        if p.exists():
            shutil.copy(p, CACHE_TODO / p.name)

    print(f"[cache]   {CACHE_TODO}")


def consolidar():
    spec = importlib.util.spec_from_file_location("cons", BASE / "00_consolidar_panel.py")
    cons = importlib.util.module_from_spec(spec)
    sys.modules["cons"] = cons
    spec.loader.exec_module(cons)

    cons.CACHE_DIR = CACHE_TODO
    cons.OUT_PATH = PANEL_PARQUET
    cons.cargar_precio_bolsa = lambda: cons.cargar_csv_serie_xm(
        TARGET_LARGO, nombre="precio_ponderado (TARGET largo)", agg_hora="mean")
    cons.main()


def ampliar(hay_demanda):
    spec = importlib.util.spec_from_file_location("amp", BASE / "00b_ampliar_panel.py")
    amp = importlib.util.module_from_spec(spec)
    sys.modules["amp"] = amp
    spec.loader.exec_module(amp)

    amp.CACHE = CACHE_TODO
    amp.REGISTRO.clear()

    base = pd.read_parquet(PANEL_PARQUET).sort_index()
    base.index = pd.to_datetime(base.index)
    base.index.name = "fecha"
    print(f"[base]    {base.shape[0]} dias x {base.shape[1]} variables")

    rec = amp.cargar_recursos()
    piezas = []
    tareas = [("mezcla de generacion", lambda: amp.mezcla_generacion(rec)),
              ("disponibilidad por tecnologia", lambda: amp.disponibilidad_por_tecnologia(rec)),
              ("hidrologia desagregada", amp.hidrologia_desagregada)]
    for nombre, fn in tareas:
        try:
            p = fn()
            if len(p.columns):
                p.index = pd.to_datetime(p.index)
                piezas.append(p)
                print(f"[nuevo]   {nombre}: {len(p.columns)} variables")
        except Exception as e:
            print(f"[ERROR]   {nombre}: {type(e).__name__}: {e}")

    if hay_demanda:
        piezas.append(perfil_intradiario())

    nuevas = pd.concat(piezas, axis=1)
    nuevas = nuevas[~nuevas.index.duplicated()]
    return base.join(nuevas, how="left")


def perfil_intradiario():
    """Perfil del precio y de la demanda dentro del dia, sobre los CSV largos."""
    HORAS = [f"Values_Hour{h:02d}" for h in range(1, 25)]
    salida = {}

    pr = pd.read_csv(TARGET_LARGO)
    pr["Date"] = pd.to_datetime(pr["Date"])
    H = pr[HORAS].apply(pd.to_numeric, errors="coerce"); H.index = pr["Date"]
    salida["precio_max_dia"] = H.max(axis=1)
    salida["precio_min_dia"] = H.min(axis=1)
    salida["precio_spread_intradia"] = H.max(axis=1) - H.min(axis=1)
    salida["precio_cv_intradia"] = H.std(axis=1) / H.mean(axis=1).replace(0, np.nan)
    salida["ratio_pico_valle"] = H.max(axis=1) / H.min(axis=1).replace(0, np.nan)

    dm = pd.read_csv(DEMANDA_LARGO)
    dm["Date"] = pd.to_datetime(dm["Date"])
    HD = dm[HORAS].apply(pd.to_numeric, errors="coerce"); HD.index = dm["Date"]
    salida["demanda_pico"] = HD.max(axis=1) / 1e6
    salida["factor_carga"] = HD.mean(axis=1) / HD.max(axis=1).replace(0, np.nan)

    d = pd.DataFrame(salida)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    print(f"[nuevo]   perfil intradiario: {len(d.columns)} variables")
    return d


def bloques_climaticos(panel):
    """ENSO semanal (desde 1981) y lluvia ERA5 (desde 2000). Cubren todo."""
    for archivo, etiqueta in [("00f_enso_semanal.py", "ENSO"),
                              ("00h_lluvia_cuencas.py", "lluvia")]:
        spec = importlib.util.spec_from_file_location("mod", BASE / archivo)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        try:
            if etiqueta == "ENSO":
                nuevas = mod.construir(mod.leer_semanal(), mod.leer_roni(), panel.index)
            else:
                nuevas = mod.construir(mod.descargar(), panel.index)
            panel = panel.drop(columns=[c for c in nuevas.columns if c in panel.columns])
            panel = panel.join(nuevas)
            print(f"[nuevo]   {etiqueta}: {len(nuevas.columns)} variables")
        except Exception as e:
            print(f"[ERROR]   {etiqueta}: {type(e).__name__}: {e}")
    return panel


def main():
    print("=" * 78)
    print("PANEL LARGO 2000-2026")
    print("=" * 78)

    unir_csv_target()
    hay_demanda = unir_csv_demanda()
    unir_caches()

    print("\n" + "-" * 78 + "\nCONSOLIDACION\n" + "-" * 78)
    consolidar()

    print("\n" + "-" * 78 + "\nAMPLIACION\n" + "-" * 78)
    panel = ampliar(hay_demanda)

    print("\n" + "-" * 78 + "\nBLOQUES CLIMATICOS\n" + "-" * 78)
    panel = bloques_climaticos(panel)

    panel.to_csv(SALIDA, encoding="utf-8")

    print("\n" + "=" * 78)
    print("RESULTADO")
    print("=" * 78)
    print(f"{SALIDA.name}: {panel.shape[0]} dias x {panel.shape[1]} variables")
    print(f"  {panel.index.min().date()} a {panel.index.max().date()}  "
          f"({SALIDA.stat().st_size/1e6:.1f} MB)")

    print("\nCobertura por epoca (fraccion de celdas con dato):")
    for ini, fin, et in [("2000-01-01", "2004-12-31", "2000-2004"),
                         ("2005-01-01", "2009-12-31", "2005-2009"),
                         ("2010-01-01", "2014-12-31", "2010-2014"),
                         ("2015-01-01", "2019-12-31", "2015-2019"),
                         ("2020-01-01", "2025-12-31", "2020-2025"),
                         ("2026-01-01", "2026-12-31", "2026")]:
        t = panel.loc[ini:fin]
        if len(t):
            print(f"  {et}  {len(t):5d} dias  cobertura {t.notna().mean().mean():6.1%}")

    obj = panel["precio_ponderado"].dropna()
    print(f"\nObjetivo: {len(obj)} dias con precio, "
          f"{obj.index.min().date()} a {obj.index.max().date()}")

    vacias = panel.columns[panel.loc[:"2014-12-31"].notna().mean() == 0]
    if len(vacias):
        print(f"\nSin datos antes de 2015 ({len(vacias)}): {list(vacias)[:15]}")


if __name__ == "__main__":
    main()
