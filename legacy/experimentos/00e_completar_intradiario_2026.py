"""
================================================================================
COMPLETAR EL PERFIL INTRADIARIO DE 2026
================================================================================

00b_ampliar_panel.py calcula el perfil intradiario (precio maximo/minimo del dia,
spread, hora del pico, factor de carga) leyendo los CSV horarios de data/, que
terminan en 2025. Por eso el panel de 2026 quedo con esas ocho variables vacias.

Importa arreglarlo: factor_carga fue una de las variables elegidas por los seis
metodos de seleccion (6/6 votos), asi que sin ella el test de 2026 no evaluaria
el mismo modelo.

Este script baja la demanda comercial horaria de 2026, extiende los dos CSV y
vuelve a calcular solo el bloque intradiario, dejando el resto del panel igual.

Uso
---
  python 00e_completar_intradiario_2026.py
================================================================================
"""

import datetime as dt
import importlib.util
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PANEL = BASE / "panel_diario_ampliado_2026.csv"

DEMANDA_2026 = DATA / "DemaCome_Sistema_2026.csv"
PRECIO_2026 = DATA / "PrecBolsNaci_Sistema_2026.csv"

DESC_INI = dt.date(2026, 1, 1)
DESC_FIN = dt.date.today()

HORAS = [f"Values_Hour{h:02d}" for h in range(1, 25)]


def descargar_horario(metric, destino, csv_viejo):
    """Baja una metrica horaria de 2026 y la concatena con el CSV historico."""
    if destino.exists():
        print(f"[{metric}] ya existe {destino.name}")
        return

    from pydataxm import pydataxm
    api = pydataxm.ReadDB()

    trozos, actual = [], DESC_INI
    while actual <= DESC_FIN:
        fin = min(actual + dt.timedelta(days=29), DESC_FIN)
        try:
            d = api.request_data(metric, "Sistema", actual, fin)
            if d is not None and not d.empty:
                trozos.append(d)
        except Exception as e:
            print(f"    [!] {actual} a {fin}: {type(e).__name__}")
        time.sleep(0.4)
        actual = fin + dt.timedelta(days=1)

    if not trozos:
        raise SystemExit(f"No se pudo descargar {metric} de 2026.")

    nuevo = pd.concat(trozos, ignore_index=True)
    nuevo["Date"] = pd.to_datetime(nuevo["Date"])

    viejo = pd.read_csv(csv_viejo)
    viejo["Date"] = pd.to_datetime(viejo["Date"])

    comunes = [c for c in viejo.columns if c in nuevo.columns]
    todo = (pd.concat([viejo[comunes], nuevo[comunes]], ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last")
            .sort_values("Date"))
    todo.to_csv(destino, index=False)
    print(f"[{metric}] {len(nuevo)} dias nuevos -> {todo['Date'].min().date()} "
          f"a {todo['Date'].max().date()}")


def perfil(ruta_precio, ruta_demanda):
    """Recalcula el bloque intradiario, igual que en 00b pero con las fuentes 2026."""
    salida = {}

    pr = pd.read_csv(ruta_precio)
    pr["Date"] = pd.to_datetime(pr["Date"])
    H = pr[HORAS].apply(pd.to_numeric, errors="coerce")
    H.index = pr["Date"]

    salida["precio_max_dia"] = H.max(axis=1)
    salida["precio_min_dia"] = H.min(axis=1)
    salida["precio_spread_intradia"] = H.max(axis=1) - H.min(axis=1)
    salida["precio_cv_intradia"] = H.std(axis=1) / H.mean(axis=1).replace(0, np.nan)
    salida["hora_precio_max"] = pd.Series(H.values.argmax(axis=1) + 1, index=H.index)
    salida["ratio_pico_valle"] = H.max(axis=1) / H.min(axis=1).replace(0, np.nan)

    dm = pd.read_csv(ruta_demanda)
    dm["Date"] = pd.to_datetime(dm["Date"])
    HD = dm[HORAS].apply(pd.to_numeric, errors="coerce")
    HD.index = dm["Date"]

    salida["demanda_pico"] = HD.max(axis=1) / 1e6
    salida["factor_carga"] = HD.mean(axis=1) / HD.max(axis=1).replace(0, np.nan)

    out = pd.DataFrame(salida)
    return out[~out.index.duplicated(keep="last")].sort_index()


def main():
    print("=" * 74)
    print("COMPLETAR PERFIL INTRADIARIO DE 2026")
    print("=" * 74)

    descargar_horario("DemaCome", DEMANDA_2026, DATA / "DemaCome_Sistema.csv")
    if not PRECIO_2026.exists():
        raise SystemExit("Falta PrecBolsNaci_Sistema_2026.csv: corre 00d primero.")

    nuevo = perfil(PRECIO_2026, DEMANDA_2026)
    print(f"[perfil]  {len(nuevo)} dias, {nuevo.index.min().date()} "
          f"a {nuevo.index.max().date()}")

    panel = pd.read_csv(PANEL, parse_dates=["fecha"], index_col="fecha")
    antes = panel[panel.index >= "2026-01-01"][nuevo.columns].notna().mean().mean()

    # Se reemplazan las ocho columnas completas, no solo 2026: asi el calculo
    # queda hecho con una sola fuente y no mezcla dos versiones del mismo CSV.
    panel = panel.drop(columns=[c for c in nuevo.columns if c in panel.columns])
    panel = panel.join(nuevo.reindex(panel.index))

    despues = panel[panel.index >= "2026-01-01"][nuevo.columns].notna().mean().mean()
    panel.to_csv(PANEL, encoding="utf-8")

    print(f"[panel]   cobertura intradiaria en 2026: "
          f"{antes:.1%} -> {despues:.1%}")
    print(f"          {PANEL.name}: {panel.shape[0]} dias x {panel.shape[1]} variables")

    d26 = panel[panel.index >= "2026-01-01"]
    cob = d26.notna().mean()
    vacias = cob[cob == 0]
    print(f"\nVariables aun sin datos en 2026 ({len(vacias)}): {list(vacias.index)}")
    print(f"Variables con cobertura >= 80%: {(cob >= 0.8).sum()} de {len(cob)}")


if __name__ == "__main__":
    main()
