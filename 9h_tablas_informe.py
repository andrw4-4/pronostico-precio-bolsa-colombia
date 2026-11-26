"""
Paso 9h: tablas del informe revisado que no estaban en un solo archivo.

    python 9h_tablas_informe.py

No entrena nada. Con los pronósticos guardados escribe en resultados/revision/:

    tabla15_ampliada.csv   la tabla 15 del informe con los modelos agregados en la revisión: RMSE y MAE en
                           logaritmo de la semana, mejora frente al mejor ingenuo y su valor p, y mejora en
                           h = 3, 3 a 7 y 8 a 9. Incluye SARIMAX con día de la semana (9d) y la primera LSTM,
                           de la que solo quedaron las métricas (resultados/modelo_lstm_v1/).

Comprueba que las filas de los tres modelos de la tesis reproducen la tabla 15 del Informe 1.
Los valores p llevan la corrección de Harvey et al. (1997).
"""
import sys
import warnings

import numpy as np
import pandas as pd

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
SALIDA = ev.RES / "revision"
ORDEN = ["Ingenuo del día", "Ingenuo semanal", "SARIMAX", "XGBoost", "LSTM", "LSTM, primera versión",
         "SARIMAX con día de la semana", "LEAR", "LSTM bloques 1 y 2", "LEAR alineado", "XGBoost alineado",
         "Promedio de los tres", "Nivel LSTM y forma XGBoost"]
# tabla 15 del Informe 1 (etiqueta informe-1): RMSE, MAE y mejora de la semana
INFORME_1 = {("2023-2025", "SARIMAX"): (0.470, 0.327, 6.4), ("2023-2025", "XGBoost"): (0.443, 0.318, 11.6),
             ("2023-2025", "LSTM"): (0.427, 0.298, 14.9), ("2026", "SARIMAX"): (0.411, 0.301, 5.6),
             ("2026", "XGBoost"): (0.392, 0.289, 10.0), ("2026", "LSTM"): (0.350, 0.255, 19.7),
             ("2023-2025", "Ingenuo del día"): (0.502, 0.333, None), ("2026", "Ingenuo del día"): (0.435, 0.311, None)}


def main():
    filas = []
    v1 = pd.read_csv(ev.RES / "modelo_lstm_v1" / "prueba_criterio.csv")
    for periodo in ("2023-2025", "2026"):
        suf = periodo.replace("-", "_")
        d = ev.tabla_modelos(periodo)
        d = ev.agregar(d, ev.RES / "modelo_sarimax_dia_semana" / f"dia_semana_{suf}.csv.gz", "lp_hat",
                       "SARIMAX con día de la semana")
        d["SARIMAX con día de la semana"] -= np.log(d["precio_t"])
        for m in [x for x in ORDEN if x in d.columns]:
            e = d["y"] - d[m]
            fila = {"periodo": periodo, "pronostico": m, "rmse": ev.rmse(e), "mae": float(e.abs().mean())}
            if not m.startswith("Ingenuo"):
                c = ev.criterio(d, m)
                fila |= {"mejora": c.loc["h = 3 a 9", "mejora"], "p_hln": c.loc["h = 3 a 9", "dm_p_hln"],
                         "ingenuo": c.loc["h = 3 a 9", "ingenuo"],
                         "mejora_h3": c.loc["h = 3", "mejora"], "mejora_h3_7": c.loc["h = 3 a 7", "mejora"],
                         "mejora_h8_9": c.loc["h = 8 a 9", "mejora"],
                         "cumple_hln": bool(c["cumple_hln"].all())}
            filas.append(fila)
        # la primera LSTM: solo quedaron sus métricas, sin MAE y con el valor p sin corrección
        g = v1[v1["periodo"] == suf].set_index("bloque")
        filas.append({"periodo": periodo, "pronostico": "LSTM, primera versión", "rmse": g.loc["h = 3 a 9", "rmse_log"],
                      "mae": np.nan, "mejora": g.loc["h = 3 a 9", "mejora"], "p_hln": np.nan,
                      "p_sin_correccion": g.loc["h = 3 a 9", "dm_p"], "ingenuo": "del día",
                      "mejora_h3": g.loc["h = 3", "mejora"], "mejora_h3_7": g.loc["h = 3 a 7", "mejora"],
                      "mejora_h8_9": g.loc["h = 8 a 9", "mejora"], "cumple_hln": bool(g["funciona"].all())})
    t = pd.DataFrame(filas)
    t["orden"] = t["pronostico"].map({m: i for i, m in enumerate(ORDEN)})
    t = t.sort_values(["periodo", "orden"]).drop(columns="orden")
    for (periodo, m), (rmse, mae, mejora) in INFORME_1.items():
        r = t[(t["periodo"] == periodo) & (t["pronostico"] == m)].iloc[0]
        assert round(r["rmse"], 3) == rmse and round(r["mae"], 3) == mae, (periodo, m)
        assert mejora is None or round(r["mejora"], 1) == mejora, (periodo, m)
    t.to_csv(SALIDA / "tabla15_ampliada.csv", index=False, float_format="%.6g")
    print(t.round(4).to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
