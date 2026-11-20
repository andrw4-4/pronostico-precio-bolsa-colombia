"""Resultados de la prueba con el error medido en pesos (anexo C). No entrena nada ni repite ninguna prueba: usa los
mismos pronósticos guardados y las mismas funciones de fig_resultados.py, pero el error es el precio pronosticado
menos el real, en COP/kWh, con el pronóstico en pesos de la ecuación (21). No es parte del criterio de la sección
3.3, que se fijó en logaritmo antes de la prueba; es un complemento de la sección 4.1.
Salidas: informe/figuras/datos_resultados_pesos.csv (frente al ingenuo del día, por periodo y por año) y
datos_resultados_pesos_pares.csv (entre modelos)."""
import numpy as np
import pandas as pd

import fig_resultados as fr

L = max(fr.HS) - 1 + 7          # los mismos rezagos de Newey y West que en la semana completa


def en_pesos(g, pron):
    """Error en COP/kWh del pronóstico `pron` (un cambio en logaritmo) frente al precio real."""
    return g["precio_t"] * np.exp(g[pron]) - g["precio_t"] * np.exp(g["y"])


d = fr.cargar()
d = d[d["h"].isin(fr.HS)]
prueba = d[d["periodo"] == "2023-2025"]
casos = {p: g for p, g in d.groupby("periodo")} | {str(a): g for a, g in prueba.groupby(prueba["fecha"].dt.year)}

filas = []
for caso, g in casos.items():
    ref = en_pesos(g, "Ingenuo del día")
    for mo in fr.INGENUOS + fr.MODELOS:
        e = en_pesos(g, mo)
        fila = {"caso": caso, "pronostico": mo, "RMSE pesos": fr.rmse(e), "MAE pesos": float(np.mean(np.abs(e))),
                "sesgo pesos": float(np.mean(e)), "mejora": np.nan, "t": np.nan, "p": np.nan}
        if mo in fr.MODELOS:
            t, p = fr.diebold_mariano(e, ref, g["fecha"], L)
            fila.update(mejora=100 * (1 - fr.rmse(e) / fr.rmse(ref)), t=t, p=p)
        filas.append(fila)
pd.DataFrame(filas).to_csv(fr.FIG / "datos_resultados_pesos.csv", index=False)

filas = []
for caso, g in casos.items():
    for a, b in [("LSTM", "XGBoost"), ("LSTM", "SARIMAX"), ("XGBoost", "SARIMAX")]:
        t, p = fr.diebold_mariano(en_pesos(g, a), en_pesos(g, b), g["fecha"], L)
        filas.append({"caso": caso, "par": f"{a} y {b}", "t": t, "p": p, "menor": a if t < 0 else b})
pd.DataFrame(filas).to_csv(fr.FIG / "datos_resultados_pesos_pares.csv", index=False)
print("ok")
