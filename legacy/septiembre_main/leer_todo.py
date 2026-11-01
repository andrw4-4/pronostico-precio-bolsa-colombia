"""
Lee TODOS los archivos de datos del proyecto y los deja en UN solo DataFrame
diario (una fila por fecha, una columna por serie).

Fuentes que cubre:
  - cache_api/*.parquet   (56 series, en 4 formatos distintos)
  - data/*.csv            (series _Sistema, ONI, TRM, gas natural)
  - Datos que usare/      (historico horario de precio de bolsa)

Formatos que detecta solo:
  A) simple       Id, Value, Date
  B) named        Id, Name, Value, Date          -> colapsa por fecha
  C) coded        Id, Code, Value, Date          -> colapsa por fecha
  D) wide_hourly  Id, Values_code, Values_HourNN -> colapsa horas y entidades

OJO: las reglas de agregacion aqui son un default razonable (flujos se suman,
precios/porcentajes se promedian), NO las reglas auditadas por serie que tiene
00_consolidar_panel.py. Para modelado final usa data/panel_d.parquet.
"""

import warnings
from functools import reduce
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent
CACHE_DIR = RAIZ / "cache_api"
DATA_DIR = RAIZ / "data"
# el nombre real de la carpeta trae acento y doble espacio
HORARIO_DIR = next(RAIZ.glob("Datos que*usar*"), None)

# Catalogos y listados: no son series de tiempo, no entran al panel
EXCLUIR = {"catalogo_metricas", "listado_embalses", "listado_rios"}

# Series de texto (que recurso fija el precio), no numericas
CATEGORICAS = {"recurso_marginal"}

# Series que se PROMEDIAN al colapsar entidades/horas (niveles, no flujos).
# El resto se suma entre entidades y se promedia entre horas.
PALABRAS_PROMEDIO = ("precio", "costo", "pct", "temp", "irradiacion",
                     "media_hist", "enficc", "cee", "cere", "mc")


def _es_promedio(nombre: str) -> bool:
    return any(p in nombre.lower() for p in PALABRAS_PROMEDIO)


def _a_serie_diaria(df: pd.DataFrame, nombre: str) -> pd.Series:
    """Colapsa cualquiera de los 4 formatos a una serie diaria."""
    fechas = pd.to_datetime(df["Date"]).dt.normalize()
    agg_entidad = "mean" if _es_promedio(nombre) else "sum"

    cols_hora = [c for c in df.columns if c.startswith("Values_Hour")]
    if cols_hora:
        valores = df[cols_hora].apply(pd.to_numeric, errors="coerce")
        # promedio entre las 24 horas -> valor diario por entidad
        por_fila = valores.mean(axis=1)
    elif "Value" in df.columns:
        por_fila = pd.to_numeric(df["Value"], errors="coerce")
    else:
        raise ValueError(f"estructura no reconocida en {nombre}")

    tmp = pd.DataFrame({"Date": fechas, nombre: por_fila})
    return tmp.groupby("Date")[nombre].agg(agg_entidad)


def leer_cache() -> list[pd.Series]:
    series = []
    for archivo in sorted(CACHE_DIR.glob("*.parquet")):
        nombre = archivo.stem
        if nombre in EXCLUIR or nombre in CATEGORICAS:
            print(f"  skip  {nombre}")
            continue
        try:
            s = _a_serie_diaria(pd.read_parquet(archivo), nombre)
            series.append(s)
            print(f"  ok    {nombre:26s} {len(s):6d} dias")
        except Exception as e:
            print(f"  ERROR {nombre}: {e}")
    return series


def leer_data_csv() -> list[pd.Series]:
    series = []
    for archivo in sorted(DATA_DIR.glob("*.csv")):
        nombre = archivo.stem
        try:
            if nombre.startswith("Tasa de cambio"):
                df = pd.read_csv(archivo, sep=";", decimal=",",
                                 encoding="utf-8-sig")
                df.columns = ["Date", "trm"]
                s = (df.assign(Date=pd.to_datetime(df["Date"],
                                                   format="%Y/%m/%d"))
                       .groupby("Date")["trm"].mean())
            elif nombre.startswith("Consulta_Precios_Promedio_de_Gas"):
                df = pd.read_csv(archivo, decimal=",")
                s = (df.assign(Date=pd.to_datetime(df["FECHA_PRECIO"],
                                                   errors="coerce"))
                       .groupby("Date")["PRECIO_PROMEDIO_PUBLICADO"]
                       .mean().rename("precio_gncv"))
            elif nombre == "oni_noaa":
                df = pd.read_csv(archivo)
                s = (df.assign(Date=pd.to_datetime(df["Date"]))
                       .groupby("Date")["oni"].mean())
            else:
                s = _a_serie_diaria(pd.read_csv(archivo), f"{nombre}_csv")
            series.append(s)
            print(f"  ok    {s.name:26s} {len(s):6d} dias")
        except Exception as e:
            print(f"  ERROR {nombre}: {e}")
    return series


def leer_horario() -> list[pd.Series]:
    series = []
    if HORARIO_DIR is None or not HORARIO_DIR.exists():
        return series
    for archivo in sorted(HORARIO_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(archivo, encoding="utf-8-sig")
            s = (df.assign(Date=pd.to_datetime(df["FechaHora"]).dt.normalize())
                   .groupby("Date")["Valor"].mean()
                   .rename("precio_bolsa_horario_prom"))
            series.append(s)
            print(f"  ok    {s.name:26s} {len(s):6d} dias")
        except Exception as e:
            print(f"  ERROR {archivo.name}: {e}")
    return series


def construir_panel() -> pd.DataFrame:
    print("cache_api/")
    series = leer_cache()
    print("data/")
    series += leer_data_csv()
    print("Datos que usare/")
    series += leer_horario()

    df = reduce(lambda a, b: a.join(b, how="outer"),
                [s.to_frame() for s in series])
    return df.sort_index()


if __name__ == "__main__":
    df = construir_panel()
    print("-" * 72)
    print(f"panel completo: {df.shape[0]} fechas x {df.shape[1]} series")
    print(f"rango: {df.index.min().date()} -> {df.index.max().date()}")
    salida = DATA_DIR / "panel_todo.parquet"
    df.to_parquet(salida)
    print(f"guardado en: {salida}")
