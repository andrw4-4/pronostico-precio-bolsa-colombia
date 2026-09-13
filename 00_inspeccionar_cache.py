"""
Inspeccion rapida de cache_api. Corre esto localmente (donde tengas pandas
y pyarrow) y pegame la salida completa. Con eso armo el consolidador.
"""
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(r"C:\Users\andre\OneDrive\cosas de la universidad\Uniandes\VIII\Tesis\cache_api")

# Representativos: uno de sistema, uno por-recurso pequeno, uno por-recurso
# gigante, y uno de los "raros" (embalse/rio)
MUESTRA = [
    "volumen_util_pct.parquet",
    "cee.parquet",
    "precio_escasez.parquet",
    "gen_programada.parquet",
    "disp_comercial.parquet",       # el mas pesado, 119 MB
    "demanda_por_or.parquet",        # 25 MB, por agente
    "aportes_por_rio.parquet",       # por rio
    "volumen_por_embalse.parquet",   # por embalse
    "demanda_upme_medio.parquet",    # mensual, formato distinto
    "catalogo_metricas.parquet",     # probablemente NO es una serie de tiempo
]

for name in MUESTRA:
    p = CACHE_DIR / name
    if not p.exists():
        print(f"\n=== {name}  -> NO EXISTE ===")
        continue
    try:
        df = pd.read_parquet(p)
    except Exception as e:
        print(f"\n=== {name}  -> ERROR leyendo: {e} ===")
        continue

    print(f"\n=== {name} ===")
    print(f"shape: {df.shape}")
    print(f"columnas: {list(df.columns)}")
    print(f"dtypes:\n{df.dtypes}")
    print("primeras filas:")
    print(df.head(3).to_string())
    print("-" * 70)
