"""
Una consulta a la API de XM: cuál es el último día publicado del despacho
programado. La corre GitHub Actions cada hora para saber a qué hora sale el
despacho de mañana. Agrega una fila por métrica al CSV que recibe.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pydataxm import pydataxm

SALIDA = Path(sys.argv[1])
METRICAS = [("CostMargDesp", "Sistema"), ("GeneProgDesp", "Recurso"), ("DispoDeclarada", "Recurso")]

ahora = datetime.now(ZoneInfo("America/Bogota"))
hoy = ahora.date()
api = pydataxm.ReadDB()
filas = []
for metrica, entidad in METRICAS:
    try:
        d = api.request_data(metrica, entidad, hoy, hoy + timedelta(days=2))
        ultimo = "" if d is None or not len(d) else pd.to_datetime(d["Date"]).max().strftime("%Y-%m-%d")
    except Exception as e:
        ultimo = f"error {type(e).__name__}"
    filas.append({"consulta": ahora.strftime("%Y-%m-%d %H:%M"), "metrica": metrica, "ultimo": ultimo})

pd.DataFrame(filas).to_csv(SALIDA, mode="a", header=not SALIDA.exists(), index=False)
print(pd.DataFrame(filas).to_string(index=False))
