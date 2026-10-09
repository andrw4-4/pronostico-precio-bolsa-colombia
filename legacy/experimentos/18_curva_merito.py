"""
================================================================================
CURVA DE MERITO — la estructura de la oferta, que el panel nunca vio
================================================================================

POR QUE
-------
El precio de bolsa ES el costo marginal del despacho: se forma cruzando la curva
de oferta (que planta pide cuanto) con la demanda. La correlacion entre el costo
marginal que publica XM y el precio es 0,970, asi que no es una analogia, es la
definicion.

El panel tiene el RESULTADO de ese cruce (el precio) y tiene insumos sueltos
(disponibilidad total, demanda), pero nunca ha visto la CURVA: como estan
repartidas las ofertas, que tan empinada esta cerca del punto de operacion,
cuanta capacidad barata queda antes de tener que encender algo caro.

Esa forma es informacion estructural que ningun rezago del precio contiene. Dos
dias con el mismo precio pueden tener curvas muy distintas: uno con holgura y
otro al borde de un escalon de 500 COP/kWh.

QUE SE CONSTRUYE
----------------
Para cada dia se arma la curva ordenando las plantas por precio de oferta y
acumulando su disponibilidad declarada. Sobre esa curva se miden:

  nivel        cuantiles de la oferta ponderados por capacidad
  dispersion   que tan separadas estan las ofertas baratas de las caras
  holgura      capacidad disponible por debajo de umbrales de precio
  pendiente    cuanto sube el precio por MWh adicional en el punto de operacion
  escalon      salto de precio a la siguiente planta despues de la marginal

LA OFERTA ES DIARIA
-------------------
Comprobado: el 100% de las filas tiene el mismo precio las 24 horas. En Colombia
el generador declara UN precio por planta y por dia, y la disponibilidad si
varia por hora. Asi que la curva diaria es exacta, no un promedio.

ANTI-FUGA
---------
Estas variables se calculan con los datos del dia t, pero el pipeline las trata
como ex-post: entran con rezago minimo de 1 dia. NO se usan con rezago 0, porque
la oferta del dia t es justamente lo que determina el precio del dia t y seria
circular.

Uso
---
  python 18_curva_merito.py
================================================================================
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
CACHE = BASE / "cache_api"
CACHE_2026 = BASE / "cache_2026"
PANELES = [BASE / "panel_diario_ampliado_2026.csv"]

HORAS = [f"Values_Hour{h:02d}" for h in range(1, 25)]
UMBRALES = [100, 200, 300, 500, 1000]


def leer(nombre):
    partes = []
    for carpeta in (CACHE, CACHE_2026):
        p = carpeta / f"{nombre}.parquet"
        if p.exists():
            partes.append(pd.read_parquet(p))
    d = pd.concat(partes, ignore_index=True)
    d["Date"] = pd.to_datetime(d["Date"])
    return d.drop_duplicates()


def preparar():
    """oferta diaria por planta y disponibilidad diaria por planta, en GWh."""
    o = leer("precio_oferta_desp")
    # la oferta es constante las 24h: basta la primera hora no nula
    o["oferta"] = o[HORAS].apply(pd.to_numeric, errors="coerce").bfill(axis=1).iloc[:, 0]
    oferta = o[["Date", "Values_code", "oferta"]].dropna()

    d = leer("disp_declarada")
    d["disp"] = d[HORAS].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1) / 1e6
    disp = d[["Date", "Values_code", "disp"]].dropna()

    j = oferta.merge(disp, on=["Date", "Values_code"], how="inner")
    j = j[(j["disp"] > 0) & (j["oferta"] > 0)]
    print(f"[curva]   {len(j)} pares planta-dia, "
          f"{j['Date'].min().date()} a {j['Date'].max().date()}, "
          f"{j['Values_code'].nunique()} plantas")
    return j


def metricas_dia(g, demanda):
    """Mide la forma de la curva de oferta de un dia."""
    g = g.sort_values("oferta")
    precio = g["oferta"].values
    cap = g["disp"].values
    acum = np.cumsum(cap)
    total = acum[-1]

    r = {"oferta_capacidad_total": total}

    # cuantiles ponderados por capacidad
    for q in (0.25, 0.5, 0.75):
        idx = np.searchsorted(acum, q * total)
        r[f"oferta_p{int(q*100)}"] = precio[min(idx, len(precio) - 1)]

    r["oferta_dispersion"] = (r["oferta_p75"] / r["oferta_p25"]
                              if r["oferta_p25"] > 0 else np.nan)
    r["oferta_min"] = precio[0]
    r["oferta_max"] = precio[-1]

    # capacidad disponible por debajo de cada umbral de precio
    for u in UMBRALES:
        r[f"cap_bajo_{u}"] = cap[precio <= u].sum()

    # --- punto de operacion: donde la curva acumulada cruza la demanda --------
    if demanda is not None and np.isfinite(demanda) and demanda > 0:
        i = int(np.searchsorted(acum, demanda))
        if i < len(precio):
            r["oferta_marginal"] = precio[i]
            r["margen_ofertado"] = total / demanda
            # escalon: cuanto mas cara es la siguiente planta
            r["escalon_siguiente"] = (precio[i + 1] - precio[i]
                                      if i + 1 < len(precio) else np.nan)
            # holgura: capacidad que queda por encima del punto de operacion
            r["holgura_gwh"] = total - demanda
            # pendiente local: COP/kWh por GWh, en una ventana de +-10% de demanda
            lo = max(0, int(np.searchsorted(acum, demanda * 0.9)))
            hi = min(len(precio) - 1, int(np.searchsorted(acum, demanda * 1.1)))
            if hi > lo and acum[hi] > acum[lo]:
                r["pendiente_curva"] = (precio[hi] - precio[lo]) / (acum[hi] - acum[lo])
    return r


def construir(j, demanda_diaria):
    filas = {}
    for fecha, g in j.groupby("Date"):
        filas[fecha] = metricas_dia(g, demanda_diaria.get(fecha, np.nan))
    d = pd.DataFrame(filas).T
    d.index = pd.to_datetime(d.index)
    return d.sort_index()


def main():
    print("=" * 74)
    print("CURVA DE MERITO")
    print("=" * 74)

    j = preparar()

    panel = pd.read_csv(PANELES[0], parse_dates=["fecha"], index_col="fecha").sort_index()
    demanda = (panel["demanda_regulada"].fillna(0)
               + panel["demanda_no_regulada"].fillna(0)) / 1e6   # kWh -> GWh
    demanda = demanda.replace(0, np.nan)
    print(f"[demanda] media {demanda.mean():.1f} GWh/dia")

    nuevas = construir(j, demanda.to_dict())
    print(f"[nuevas]  {len(nuevas.columns)} variables, {len(nuevas)} dias")

    for p in PANELES:
        pan = pd.read_csv(p, parse_dates=["fecha"], index_col="fecha").sort_index()
        pan = pan.drop(columns=[c for c in nuevas.columns if c in pan.columns])
        pan = pan.join(nuevas.reindex(pan.index))
        pan.to_csv(p, encoding="utf-8")
        print(f"[salida]  {p.name}: {pan.shape[1]} variables")

    pan = pd.read_csv(PANELES[0], parse_dates=["fecha"], index_col="fecha")
    print()
    for c in nuevas.columns:
        s = pan[c].dropna()
        print(f"  {c:26s} cob {pan[c].notna().mean():6.1%}  "
              f"[{s.min():9.2f}, {s.max():9.2f}]")

    # --- ¿reconstruye el precio? la validacion de que la curva esta bien ------
    print("\n" + "=" * 74)
    print("VALIDACION: ¿la curva reconstruye el precio observado?")
    print("=" * 74)
    sub = pan[["oferta_marginal", "precio_ponderado", "costo_marginal_prog"]].dropna()
    print(f"  oferta_marginal vs precio real     corr = "
          f"{sub['oferta_marginal'].corr(sub['precio_ponderado']):.4f}  (n={len(sub)})")
    print(f"  oferta_marginal vs costo marginal  corr = "
          f"{sub['oferta_marginal'].corr(sub['costo_marginal_prog']):.4f}")
    print("\n  Si la correlacion es alta, la curva esta bien reconstruida.")
    print("  OJO: por eso estas variables solo pueden usarse REZAGADAS.")

    print("\n" + "=" * 74)
    print("LO QUE APORTA LA FORMA (no el nivel): correlacion con el cambio a 7 dias")
    print("=" * 74)
    obj = np.log(pan["precio_ponderado"]).diff(7).shift(-7)
    for c in ["oferta_dispersion", "pendiente_curva", "escalon_siguiente",
              "margen_ofertado", "cap_bajo_200", "cap_bajo_500", "holgura_gwh"]:
        if c in pan.columns:
            print(f"  {c:22s} {pan[c].corr(obj):+.4f}")


if __name__ == "__main__":
    main()
