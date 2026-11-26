"""
Paso 9: análisis que pidió la revisión del 26 de noviembre de 2026, con los pronósticos guardados.

    python 9_analisis_revision.py

No entrena nada ni repite ninguna prueba. Lee los pronósticos de la prueba de SARIMAX, XGBoost y
la LSTM y los paneles, y escribe en resultados/revision/:

    origenes.csv               cuántos orígenes tiene cada periodo en cada horizonte (una sola regla)
    criterio_hln.csv           el criterio de la tesis con la corrección de Harvey et al. (1997)
    mediana_error.csv          mediana del error absoluto por año y por modelo, frente a los ingenuos
    meses_2023_2025.csv        precio, embalse, aportes y ONI de cada mes
    episodios.csv              error de cada modelo en El Niño 2023-2024 y en el déficit de aportes de 2024
    regimenes.csv              error de cada modelo según los aportes de los últimos 30 días
    diseno_30_dias.csv         los cuatro bloques del diseño original de XGBoost, en los dos periodos
    atraso3_xgboost.csv        XGBoost si el precio llegara con tres días de atraso (h = 4 a 10)

Fuentes: Diebold y Mariano (1995); Newey y West (1987); Harvey, Leybourne y Newbold (1997).
"""
import warnings

import numpy as np
import pandas as pd

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
SALIDA = ev.RES / "revision"
SALIDA.mkdir(parents=True, exist_ok=True)
MODELOS = ["SARIMAX", "XGBoost", "LSTM"]
INGENUOS = ["Ingenuo del día", "Ingenuo semanal"]
SEMANA = {"h = 3 a 9": ev.HS}

# Episodios de la prueba, por la fecha del origen. Los límites salen de meses_2023_2025.csv:
# El Niño (ONI de 0,5 o más) con aportes bajos, y el déficit de aportes con el ONI neutro.
EPISODIOS = {"El Niño 2023-2024": ("2023-09-01", "2024-04-30"),
             "Déficit de aportes de 2024": ("2024-08-01", "2024-11-30")}
# Régimen según los aportes de los 30 días que terminan en el origen, sobre su media histórica
REGIMENES = [("aportes bajos (menos de 80%)", -np.inf, 0.80), ("aportes normales (80% a 110%)", 0.80, 1.10),
             ("aportes altos (más de 110%)", 1.10, np.inf)]


def guardar(tabla, nombre, **kw):
    tabla.to_csv(SALIDA / nombre, float_format="%.6g", **kw)
    print(f"\n== {nombre}")
    print(tabla.round(4).to_string())


def casos_por_anio(d):
    t = d[d["periodo"] == "2023-2025"]
    return ({p: g for p, g in d.groupby("periodo")} | {str(a): g for a, g in t.groupby(t["fecha"].dt.year)})


def mejora_y_dm(g, modelo, ref="Ingenuo del día"):
    """Mejora del RMSE de la semana frente a un ingenuo y Diebold-Mariano con la corrección."""
    e, e_ref = g["y"] - g[modelo], g["y"] - g[ref]
    dm = ev.diebold_mariano(e, e_ref, g["fecha"], max(ev.HS) - 1 + 7, h=max(ev.HS))
    return {"origenes": dm["T"], "rmse": ev.rmse(e), "rmse_ingenuo": ev.rmse(e_ref),
            "mejora": 100 * (1 - ev.rmse(e) / ev.rmse(e_ref)), "dm_p": dm["p"], "dm_p_hln": dm["p_hln"]}


def main():
    precio = ev.precios()
    d = ev.prueba_tres_modelos()

    # ------------------------------------------------------------------ orígenes de cada periodo
    filas = []
    for nombre, (desde, hasta) in ev.PERIODOS.items():
        m = ev.marco(desde, hasta, precio=precio)
        por_h = m.groupby("h")["fecha"].nunique()
        dias = (pd.Timestamp(hasta) - pd.Timestamp(desde)).days + 1
        filas.append({"periodo": nombre, "dias_del_periodo": dias, **{f"h{h}": int(por_h[h]) for h in ev.HS},
                      "semana_completa": int(por_h[max(ev.HS)]), "dia_horizontes": int(por_h.sum()),
                      "filas": len(m)})
    guardar(pd.DataFrame(filas).set_index("periodo"), "origenes.csv")

    # ------------------------------------------------------------------ criterio con la corrección
    crit = pd.concat({(c, mo): ev.criterio(g, mo) for c, g in casos_por_anio(d).items() for mo in MODELOS},
                     names=["caso", "modelo"])
    guardar(crit, "criterio_hln.csv")
    cambia = crit[crit["cumple"] != crit["cumple_hln"]]
    print("\nfilas en que la corrección cambia el veredicto:", len(cambia))
    print(cambia[["mejora", "dm_p", "dm_p_hln"]].round(4).to_string())

    # ------------------------------------------------------------------ mediana del error absoluto
    real = d["precio_t"] * np.exp(d["y"])
    filas = []
    for caso, g in casos_por_anio(d).items():
        for mo in MODELOS + INGENUOS:
            e = (g["y"] - g[mo]).abs()
            e_pesos = (g["precio_t"] * np.exp(g[mo]) - real.loc[g.index]).abs()
            filas.append({"caso": caso, "pronostico": mo, "mediana_log": e.median(), "media_log": e.mean(),
                          "mediana_pesos": e_pesos.median(), "media_pesos": e_pesos.mean()})
    med = pd.DataFrame(filas)
    base = med[med["pronostico"] == "Ingenuo del día"].set_index("caso")["mediana_log"]
    med["frente_al_ingenuo_del_dia"] = 100 * (1 - med["mediana_log"] / med["caso"].map(base))
    guardar(med.set_index(["caso", "pronostico"]), "mediana_error.csv")

    # ------------------------------------------------------------------ meses de 2023 a 2025
    dia = pd.read_csv(ev.RAIZ / "paneles" / "panel_diario.csv", parse_dates=["fecha"],
                      usecols=["fecha", "precio_bolsa", "volumen_util_pct", "aportes_pct_sistema", "oni"])
    mes = dia.set_index("fecha").resample("MS").mean().loc["2023-01":"2025-12"]
    mes = pd.DataFrame({"precio_cop_kwh": mes["precio_bolsa"], "embalse_pct": 100 * mes["volumen_util_pct"],
                        "aportes_pct_media": 100 * mes["aportes_pct_sistema"], "oni": mes["oni"]})
    mes.index = mes.index.strftime("%Y-%m")
    guardar(mes.rename_axis("mes"), "meses_2023_2025.csv")

    # ------------------------------------------------------------------ episodios
    filas = []
    en_alguno = pd.Series(False, index=d.index)
    grupos = {}
    for nombre, (a, b) in EPISODIOS.items():
        m = d["fecha"].between(a, b)
        grupos[nombre], en_alguno = d[m], en_alguno | m
    grupos["Resto de 2023-2025"] = d[~en_alguno & (d["periodo"] == "2023-2025")]
    for nombre, g in grupos.items():
        precio_medio = float((g["precio_t"] * np.exp(g["y"])).mean())
        for mo in MODELOS:
            filas.append({"episodio": nombre, "modelo": mo, "precio_medio": precio_medio, **mejora_y_dm(g, mo),
                          "sesgo_log": float((g[mo] - g["y"]).mean())})
    guardar(pd.DataFrame(filas).set_index(["episodio", "modelo"]), "episodios.csv")

    # ------------------------------------------------------------------ regímenes de aportes
    ap = dia.set_index("fecha")["aportes_pct_sistema"].rolling(30, min_periods=30).mean()
    d["aportes_30d"] = d["fecha"].map(ap)
    assert d["aportes_30d"].notna().all()
    filas = []
    for nombre, lo, hi in REGIMENES:
        g = d[(d["aportes_30d"] >= lo) & (d["aportes_30d"] < hi)]
        for mo in MODELOS:
            filas.append({"regimen": nombre, "modelo": mo, **mejora_y_dm(g, mo),
                          "mediana_abs": float((g["y"] - g[mo]).abs().median()),
                          "mediana_abs_ingenuo": float(g["y"].abs().median())})
    guardar(pd.DataFrame(filas).set_index(["regimen", "modelo"]), "regimenes.csv")

    # ------------------------------------------------------------------ diseño original de 30 días
    X = ev.RES / "modelo_xgboost"
    todos = {"2023-2025": pd.concat([pd.read_csv(X / f"prueba_h{h}.csv.gz", parse_dates=["fecha"])
                                     for h in range(1, 31)], ignore_index=True),
             "2026": pd.read_csv(X / "prueba2026_mensual.csv.gz", parse_dates=["fecha"])}
    bloques30 = {"h = 3": [3], "h = 3 a 7": list(range(3, 8)), "h = 8 a 14": list(range(8, 15)),
                 "h = 15 a 30": list(range(15, 31))}
    d30 = pd.concat({p: ev.criterio(g.rename(columns={"y_hat": "XGBoost"}), "XGBoost", bloques30)
                     for p, g in todos.items()}, names=["periodo"])
    guardar(d30, "diseno_30_dias.csv")
    viejo = pd.concat([pd.read_csv(X / "prueba_criterio.csv").assign(periodo="2023-2025"),
                       pd.read_csv(X / "prueba2026_criterio.csv").query("plan == 'mensual'").assign(periodo="2026")])
    viejo = viejo.set_index(["periodo", "bloque"])
    assert np.allclose(d30["mejora"], viejo.loc[d30.index, "mejora"], atol=1e-3), "no coincide con lo guardado"
    assert np.allclose(d30["dm_p"], viejo.loc[d30.index, "dm_p"], atol=1e-4)

    # ------------------------------------------------------------------ precio con tres días de atraso
    # Con tres días de atraso el primer día pronosticable es t + 4. Los modelos de XGBoost para
    # h = 4 a 10 ya corrieron en la prueba del diseño de 30 días (h = 10 usa la configuración de h = 7).
    hs3 = list(range(4, 11))
    bloques3 = {"h = 4 a 10": hs3, "h = 4": [4], "h = 4 a 8": [4, 5, 6, 7, 8], "h = 9 a 10": [9, 10]}
    filas = []
    for p, g in todos.items():
        g = g[g["h"].isin(hs3)].rename(columns={"y_hat": "XGBoost"})
        m = ev.marco(*ev.PERIODOS[p], hs=hs3, precio=precio)
        j = m.merge(g[ev.CLAVES + ["XGBoost", "y"]], on=ev.CLAVES, validate="one_to_one", suffixes=("", "_g"))
        assert len(j) == len(m) == len(g) and np.allclose(j["y"], j["y_g"], atol=1e-5)
        filas.append(ev.criterio(j, "XGBoost", bloques3).assign(periodo=p, modelo="XGBoost"))
    guardar(pd.concat(filas).reset_index().set_index(["periodo", "modelo", "bloque"]), "atraso3_xgboost.csv")


if __name__ == "__main__":
    main()
