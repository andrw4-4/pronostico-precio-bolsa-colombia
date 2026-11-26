"""
Paso 9e: experimento de decisión.

    python 9e_decision.py

Las reglas están en docs/EXPERIMENTO_DECISION.md y se escribieron antes de calcular nada. No
entrena ni cambia ningún pronóstico: con los pronósticos guardados de la prueba mide qué tanto del
ahorro posible captura cada uno en dos decisiones.

    Elegir días    ubicar dos días de consumo plano en la semana pronosticada (t + 3 a t + 9)
    Elegir horas   en cada día pronosticado, las cuatro horas más baratas

    captura = (C_azar - C_modelo) / (C_azar - C_perfecto), con el costo en COP/kWh

Salidas, en resultados/revision/: decision.csv y decision_pares.csv.
"""
import sys
import warnings
from itertools import combinations

import numpy as np
import pandas as pd

import evaluacion as ev

warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")
SALIDA = ev.RES / "revision"
SALIDA.mkdir(parents=True, exist_ok=True)
N_DIAS, N_HORAS = 2, 4
L, H = max(ev.HS) - 1 + 7, max(ev.HS)
SOLO_HORAS = {"Ingenuo del día"}          # pronostica el mismo nivel para los siete días


def cubo(d, columna):
    """De filas (origen, hora, h) a [origen, día de la semana pronosticada, hora]."""
    t = d.pivot_table(index="fecha", columns=["h", "hora"], values=columna, aggfunc="first").sort_index(axis=1)
    return t.to_numpy().reshape(len(t), len(ev.HS), 24), t.index


def costos(real, pron):
    """Costo de cada origen en las dos decisiones, con el precio real de lo que eligió el pronóstico."""
    dias = np.argsort(pron.mean(axis=2), axis=1, kind="stable")[:, :N_DIAS]
    c_dias = np.take_along_axis(real.mean(axis=2), dias, axis=1).mean(axis=1)
    horas = np.argsort(pron, axis=2, kind="stable")[:, :, :N_HORAS]
    c_horas = np.take_along_axis(real, horas, axis=2).mean(axis=(1, 2))
    return {"Elegir días": c_dias, "Elegir horas": c_horas}


def main():
    filas, pares = [], []
    for periodo in ("2023-2025", "2026"):
        d = ev.tabla_modelos(periodo)
        # solo los orígenes con la semana completa dentro del periodo
        completos = d.groupby("fecha")["h"].transform("nunique") == len(ev.HS)
        d = d[completos].copy()
        modelos = ev.modelos_de(d) + ["Ingenuo semanal", "Ingenuo del día"]
        d["real"] = d["precio_t"] * np.exp(d["y"])
        real, fechas = cubo(d, "real")
        assert not np.isnan(real).any()
        C = {}
        for m in modelos:
            d["pron"] = d["precio_t"] * np.exp(d[m])
            C[m] = costos(real, cubo(d, "pron")[0])
        perfecto = costos(real, real)
        azar = real.mean(axis=(1, 2))                 # el precio medio de la semana, en las dos decisiones
        casos = {periodo: np.ones(len(fechas), bool)}
        if periodo == "2023-2025":
            casos |= {str(a): fechas.year == a for a in (2023, 2024, 2025)}
        for caso, m_caso in casos.items():
            for decision in ("Elegir días", "Elegir horas"):
                posible = (azar - perfecto[decision])[m_caso]
                for m in modelos:
                    if decision == "Elegir días" and m in SOLO_HORAS:
                        continue
                    ahorro = (azar - C[m][decision])[m_caso]
                    p = ev.prueba_pareada(ahorro, L, H)
                    filas.append({"caso": caso, "decision": decision, "pronostico": m, "origenes": int(m_caso.sum()),
                                  "costo_azar": azar[m_caso].mean(), "costo": C[m][decision][m_caso].mean(),
                                  "costo_perfecto": perfecto[decision][m_caso].mean(),
                                  "ahorro": ahorro.mean(), "ahorro_posible": posible.mean(),
                                  "captura": ahorro.sum() / posible.sum(), "p_contra_azar": p["p_hln"]})
        for decision in ("Elegir días", "Elegir horas"):
            usables = [m for m in modelos if not (decision == "Elegir días" and m in SOLO_HORAS)]
            for a, b in combinations(usables, 2):
                p = ev.prueba_pareada(C[a][decision] - C[b][decision], L, H)
                pares.append({"periodo": periodo, "decision": decision, "a": a, "b": b, "diferencia_costo": p["media"],
                              "p_hln": p["p_hln"], "menor_costo": a if p["media"] < 0 else b})
    r = pd.DataFrame(filas)
    r.to_csv(SALIDA / "decision.csv", index=False, float_format="%.6g")
    pd.DataFrame(pares).to_csv(SALIDA / "decision_pares.csv", index=False, float_format="%.6g")
    for decision, g in r.groupby("decision"):
        print("\n==", decision)
        print(g.pivot(index="pronostico", columns="caso", values="captura").round(3).to_string())
        print(g[g["caso"].isin(["2023-2025", "2026"])][["caso", "pronostico", "costo_azar", "costo", "costo_perfecto",
                                                         "captura", "p_contra_azar"]].round(3).to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
