import pandas as pd
from pathlib import Path

# Suponiendo que la carpeta de datos es "data/" dentro del repositorio
# (El script original la busca en una ruta absoluta de OneDrive,
# pero aquí usaremos una local si es posible, o buscaremos el archivo).

data_path = Path("data/panel_d.parquet")

if not data_path.exists():
    print(f"Error: No se encontró el archivo en {data_path}.")
    print("Buscando en directorios cercanos...")

    # Intenta buscar en otros lugares comunes
    encontrado = False
    for path in Path('.').rglob('panel_d.parquet'):
        print(f"¡Archivo encontrado en: {path}!")
        data_path = path
        encontrado = True
        break

    if not encontrado:
        print("No se encontró el archivo panel_d.parquet en ninguna parte.")
        print("Asegúrate de haber ejecutado 00_consolidar_panel.py primero.")
        exit(1)

try:
    print(f"\n--- Cargando: {data_path} ---")
    df = pd.read_parquet(data_path)

    print(f"\nDimensiones del panel: {df.shape[0]} filas x {df.shape[1]} columnas")

    print("\n1. Primeras 5 filas:")
    print(df.head())

    print("\n2. Información General:")
    df.info()

    print("\n3. Estadísticas descriptivas de las primeras 5 columnas (y margen de reserva si existe):")
    cols_to_show = list(df.columns[:5])
    if 'margen_reserva' in df.columns and 'margen_reserva' not in cols_to_show:
         cols_to_show.append('margen_reserva')
    if 'precio_ponderado' in df.columns and 'precio_ponderado' not in cols_to_show:
         cols_to_show.append('precio_ponderado')

    print(df[cols_to_show].describe())

except Exception as e:
    print(f"Ocurrió un error al cargar o procesar el archivo: {e}")
