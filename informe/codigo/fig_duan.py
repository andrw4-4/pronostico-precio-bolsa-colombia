"""Prueba de robustez de la sección 4.1: corregir el sesgo en pesos con el estimador de Duan (1983). El pronóstico en
pesos de cada horizonte se multiplica por el promedio de exp(error en logaritmo) de errores ya conocidos al
pronosticar. Dos variantes:
- factor fijo de la validación 2020-2022, solo para SARIMAX, el único modelo con esos errores guardados fila por fila
  (resultados/modelo_sarimax/etapa4_comun.csv.gz, la versión elegida);
- factor recalculado el primer día de cada mes con todos los errores cuyo precio ya se conocía (día objetivo hasta
  dos días antes del inicio del mes): para SARIMAX, validación y prueba; para XGBoost y la LSTM, solo la prueba,
  así que en el primer mes no se corrige.
No entrena nada ni cambia los pronósticos guardados; se hizo después de ver la prueba y es solo un complemento.
Salida: informe/figuras/datos_resultados_duan.csv."""
import numpy as np
import pandas as pd

import fig_resultados as fr

L = max(fr.HS) - 1 + 7

d = fr.cargar()
d = d[d["h"].isin(fr.HS)].copy()
d["objetivo"] = d["fecha"] + pd.to_timedelta(d["h"], unit="D")
d["mes"] = d["fecha"].dt.to_period("M")

v = pd.read_csv(fr.RES / "modelo_sarimax" / "etapa4_comun.csv.gz", parse_dates=["fecha"])
p = pd.read_csv(fr.RAIZ / "paneles" / "panel_horario_modelo.csv.gz", parse_dates=["fecha"],
                usecols=["fecha", "hora", "lp"])
v["objetivo"] = v["fecha"] + pd.to_timedelta(v["h"], unit="D")
v = v.merge(p.rename(columns={"fecha": "objetivo", "lp": "lp_real"}), on=["objetivo", "hora"], how="left")
v = v[v["h"].isin(fr.HS)].dropna(subset=["lp_real"])
v["e"] = v["lp_real"] - v["lp_hat"]
fijo = v.groupby("h")["e"].apply(lambda e: float(np.mean(np.exp(e))))


def factor_mensual(mo, previo=None):
    """Factor de cada fila: el de su mes y su horizonte, con los errores conocidos al empezar el mes."""
    e = d[["objetivo", "h"]].assign(e=d["y"] - d[mo])
    if previo is not None:
        e = pd.concat([previo[["objetivo", "h", "e"]], e])
    f = pd.Series(1.0, index=d.index)
    for m in sorted(d["mes"].unique()):
        conocido = e[e["objetivo"] <= m.to_timestamp() - pd.Timedelta(days=2)]
        por_h = conocido.groupby("h")["e"].apply(lambda x: float(np.mean(np.exp(x))))
        filas = d["mes"] == m
        f[filas] = d.loc[filas, "h"].map(por_h).fillna(1.0)
    return f


filas = []


def medir(mo, variante, pron):
    for per, g in d.groupby("periodo"):
        real = g["precio_t"] * np.exp(g["y"])
        ref = g["precio_t"] - real                      # el ingenuo del día repite el precio del día t
        e = pron.loc[g.index] - real
        t, pv = fr.diebold_mariano(e, ref, g["fecha"], L)
        filas.append({"periodo": per, "pronostico": mo, "variante": variante, "RMSE pesos": fr.rmse(e),
                      "sesgo pesos": float(np.mean(e)), "mejora": 100 * (1 - fr.rmse(e) / fr.rmse(ref)), "p": pv})


for mo in fr.MODELOS:
    base = d["precio_t"] * np.exp(d[mo])
    medir(mo, "sin corregir", base)
    if mo == "SARIMAX":
        medir(mo, "factor fijo de validacion", base * d["h"].map(fijo))
        medir(mo, "factor mensual", base * factor_mensual(mo, previo=v))
    else:
        medir(mo, "factor mensual", base * factor_mensual(mo))
r = pd.DataFrame(filas)
r.to_csv(fr.FIG / "datos_resultados_duan.csv", index=False)
pd.set_option("display.width", 200)
print(r.round(3).to_string())
