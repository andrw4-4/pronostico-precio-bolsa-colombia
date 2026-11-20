"""Utilidad del pronóstico para un comercializador (sección 4.2). Un comercializador compra en bolsa la energía
que sus contratos no cubren; con el pronóstico de la semana estima cuánto le va a costar. Para un bloque plano,
la misma energía en las 168 horas, ese costo depende del precio promedio de la semana (decisión del autor).
No entrena nada ni repite ninguna prueba: usa los pronósticos guardados y las funciones de fig_resultados.py.
Para cada día de origen t con los 168 pronósticos, el precio promedio pronosticado de la semana, en pesos con la
ecuación (21), se compara con el real. También se mide si el pronóstico acierta la dirección cuando la semana
sube o baja más de 10% frente al último día conocido, algo que el ingenuo del día no puede anticipar porque
pronostica un cambio de cero.
Salida: informe/figuras/datos_resultados_comercializador.csv."""
import numpy as np
import pandas as pd

import fig_resultados as fr

L = max(fr.HS) - 1 + 7          # los mismos rezagos de Newey y West que en la semana completa
UMBRAL = 0.10                   # una semana "se mueve" si su precio promedio cambia más de 10% (decisión del autor)


def intervalo(acierto, bloque=28, repeticiones=2000):
    """Intervalo de 95% de la tasa de acierto con un bootstrap de bloques móviles de 28 días de origen, como en la
    sección 4.2 (Künsch, 1989). `acierto` tiene un valor por semana, en orden, y NaN en las que no se mueven."""
    v = np.asarray(acierto, dtype=float)
    rng = np.random.default_rng(0)
    n = len(v)
    tasas = [np.nanmean(np.concatenate([v[i:i + bloque] for i in rng.integers(0, n - bloque, n // bloque)]))
             for _ in range(repeticiones)]
    return 100 * np.percentile(tasas, 2.5), 100 * np.percentile(tasas, 97.5)


d = fr.cargar()
d = d[d["h"].isin(fr.HS)]
PRON = fr.INGENUOS + fr.MODELOS
d = d.assign(real=d["precio_t"] * np.exp(d["y"]), **{mo: d["precio_t"] * np.exp(d[mo]) for mo in PRON})
semana = d.groupby(["periodo", "fecha"]).agg(n=("real", "size"), real=("real", "mean"),
                                             **{mo: (mo, "mean") for mo in PRON},
                                             hoy=("precio_t", "mean")).reset_index()
semana = semana[semana["n"] == 168]
prueba = semana[semana["periodo"] == "2023-2025"]
casos = {p: g for p, g in semana.groupby("periodo")} | {str(a): g for a, g in prueba.groupby(prueba["fecha"].dt.year)}

filas = []
for caso, g in casos.items():
    ref = g["Ingenuo del día"] - g["real"]
    sube = (g["real"] / g["hoy"] - 1)
    mueve = sube.abs() > UMBRAL
    for mo in PRON:
        e = g[mo] - g["real"]
        rel = e / g["real"]
        fila = {"caso": caso, "pronostico": mo, "semanas": len(g), "precio semana": g["real"].mean(),
                "RMSE": fr.rmse(e), "MAE": float(np.mean(np.abs(e))), "sesgo": float(np.mean(e)),
                "MAE %": 100 * float(np.mean(np.abs(e))) / g["real"].mean(),
                "error mayor a 20%": 100 * float((rel.abs() > 0.2).mean()),
                "por debajo": 100 * float((e < 0).mean()),
                "semanas que se mueven": 100 * float(mueve.mean()),
                "acierta direccion": np.nan, "direccion inf": np.nan, "direccion sup": np.nan,
                "mejora": np.nan, "t": np.nan, "p": np.nan}
        if mo != "Ingenuo del día":
            cambio = g[mo] / g["hoy"] - 1
            acierto = (np.sign(cambio) == np.sign(sube)).astype(float).where(mueve)
            fila["acierta direccion"] = 100 * float(acierto.mean())
            fila["direccion inf"], fila["direccion sup"] = intervalo(acierto)
        if mo in fr.MODELOS:
            t, p = fr.diebold_mariano(e.to_numpy(), ref.to_numpy(), g["fecha"], L)
            fila.update(mejora=100 * (1 - fr.rmse(e) / fr.rmse(ref)), t=t, p=p)
        filas.append(fila)
r = pd.DataFrame(filas)
r.to_csv(fr.FIG / "datos_resultados_comercializador.csv", index=False)
pd.set_option("display.width", 250)
print(r.round(3).to_string())
