"""
Paso 9j: repetición de la primera LSTM (6_modelo_lstm.ipynb) para recuperar sus pronósticos.

La primera LSTM se corrió el 2 de noviembre de 2026 en Colab y pasó por la prueba ese día, pero sus
pronósticos fila por fila se perdieron al cerrar la sesión (resultados/modelo_lstm_v1/RESULTADOS.md).
Este script la vuelve a correr con el mismo código del notebook, el mismo panel, la misma configuración
(resultados/modelo_lstm_v1/configuracion.json) y la misma semilla, para guardar los pronósticos y
calcular las cifras que faltaban en la tabla 15: el MAE y el valor p con la corrección de Harvey et
al. (1997). No busca ni cambia nada: la búsqueda de hiperparámetros no se repite y se usan los que
eligió entonces. En GPU el entrenamiento no es determinista, así que las cifras no salen idénticas a
las de la corrida original; se comparan con ellas.

Se corre en Colab con GPU (el 26 de noviembre tardó 20 minutos en una T4):

    exec(open("/content/drive/MyDrive/tesis/9j_lstm_v1_repeticion.py", encoding="utf-8").read())

El panel se lee del repositorio público; es el mismo de la corrida original en las columnas que usa
la red (se comprobó contra la copia del 2 de noviembre). Cada mes se guarda apenas termina, y si la
sesión se cae, basta volver a correr. Los resultados quedan en tesis/modelo_lstm_v1_repeticion/ y
se copian a resultados/modelo_lstm_v1/: los pronósticos y prueba_criterio_repeticion.csv con el mismo
nombre, validacion_2022.csv como validacion_2022_repeticion.csv y corrida.json como
corrida_repeticion.json, para no tapar los archivos de la corrida original.
"""
import json
import time
from pathlib import Path

import keras
import numpy as np
import pandas as pd
from keras import layers
from scipy import stats

REPO = "https://raw.githubusercontent.com/andrw4-4/pronostico-precio-bolsa-colombia/main/paneles/"
SALIDA = Path("resultados/modelo_lstm_v1_repeticion")
try:
    from google.colab import drive
    drive.mount("/content/drive")
    SALIDA = Path("/content/drive/MyDrive/tesis/modelo_lstm_v1_repeticion")
except ImportError:
    pass
(SALIDA / "meses").mkdir(parents=True, exist_ok=True)

# configuración de la corrida original (resultados/modelo_lstm_v1/configuracion.json)
HP = {"unidades_1": 330, "dropout_1": 0.2, "unidades_2": 210, "dropout_2": 0.3, "unidades_3": 150,
      "dropout_3": 0.3, "tasa": 0.003697}
EPOCAS = 6
keras.utils.set_random_seed(0)

HS = list(range(3, 10))
DIAS_ENTRADA = 7
VARIABLES = ["cmg_hoy_vs_precio", "cmg_despacho", "disp_decl_hoy_rel", "brecha_escasez",
             "presion_hidro_horaria"]
CALENDARIO = ["hora_sin", "hora_cos", "dia_semana_sin", "dia_semana_cos", "es_festivo",
              "dia_ano_sin", "dia_ano_cos"] + [f"es_festivo_k{k}" for k in range(1, 8)]
COLUMNAS = ["lp"] + VARIABLES + CALENDARIO

INICIO = "2015-03-01"
FIN_ENTRENAMIENTO = "2021-12-31"
FIN_VALIDACION = "2022-12-31"
FIN_TEST = "2025-12-31"
FIN_2026 = "2026-10-06"
BLOQUES = {"h = 3 a 9": HS, "h = 3": [3], "h = 3 a 7": [3, 4, 5, 6, 7], "h = 8 a 9": [8, 9]}

# ----------------------------------------------------------------------------- datos (igual que el notebook)
local = Path("paneles/panel_lstm_modelo.csv.gz")
panel = pd.read_csv(local if local.exists() else REPO + "panel_lstm_modelo.csv.gz",
                    usecols=["fecha", "hora", "precio"] + COLUMNAS + [f"y_h{h}" for h in HS],
                    parse_dates=["fecha"]).sort_values(["fecha", "hora"]).reset_index(drop=True)
assert (panel.groupby("fecha").size() == 24).all()
assert len(panel) == 103200 and str(panel["fecha"].max().date()) == "2026-10-09"

f = pd.DatetimeIndex(panel["fecha"].drop_duplicates())
n_dias = len(f)
X_dia = panel[COLUMNAS].to_numpy(np.float32).reshape(n_dias, 24, len(COLUMNAS))
Y_dia = (panel[[f"y_h{h}" for h in HS]].to_numpy(np.float32)
         .reshape(n_dias, 24, len(HS)).transpose(0, 2, 1))

LP = panel["lp"].to_numpy(np.float32).reshape(n_dias, 24)
Y_sem = np.full_like(Y_dia, np.nan)
for j, h in enumerate(HS):
    k = 7 * int(np.ceil(h / 7)) - h
    Y_sem[k:, j] = LP[:n_dias - k] - LP[k:]

ok = np.zeros(n_dias, bool)
for i in range(DIAS_ENTRADA - 1, n_dias):
    ok[i] = not np.isnan(X_dia[i - DIAS_ENTRADA + 1:i + 1]).any()


def origenes(desde, hasta, completos=True):
    m = ok & (f >= pd.Timestamp(desde))
    if completos:
        m &= (f + pd.Timedelta(days=max(HS)) <= pd.Timestamp(hasta)) & ~np.isnan(Y_dia).any(axis=(1, 2))
    else:
        m &= f <= pd.Timestamp(hasta)
    return np.flatnonzero(m)


def ventanas(idx):
    X = np.stack([X_dia[i - DIAS_ENTRADA + 1:i + 1].reshape(-1, len(COLUMNAS)) for i in idx])
    return X, Y_dia[idx].reshape(len(idx), -1)


# ----------------------------------------------------------------------------- modelo (igual que el notebook)
def escala(X, Y):
    mx, sx = X.reshape(-1, X.shape[-1]).mean(0), X.reshape(-1, X.shape[-1]).std(0) + 1e-6
    my, sy = Y.mean(0), Y.std(0) + 1e-6
    return (lambda X_: (X_ - mx) / sx), (lambda Y_: (Y_ - my) / sy), (lambda Z: Z * sy + my)


def construir():
    modelo = keras.Sequential([keras.Input(shape=(DIAS_ENTRADA * 24, len(COLUMNAS)))])
    for capa in range(1, 4):
        modelo.add(layers.LSTM(HP[f"unidades_{capa}"], activation="tanh", return_sequences=capa < 3))
        modelo.add(layers.Dropout(HP[f"dropout_{capa}"]))
    modelo.add(layers.Dense(len(HS) * 24))
    modelo.compile(optimizer=keras.optimizers.Adam(learning_rate=HP["tasa"]), loss="mae")
    return modelo


def entrenar(idx, epocas, idx_val=None):
    X, Y = ventanas(idx)
    nx, ny, volver = escala(X, Y)
    modelo = construir()
    val, parar = None, []
    if idx_val is not None:
        Xv, Yv = ventanas(idx_val)
        val = (nx(Xv), ny(Yv))
        parar = [keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True)]
    hist = modelo.fit(nx(X), ny(Y), validation_data=val, epochs=epocas, batch_size=32,
                      callbacks=parar, verbose=0)
    return modelo, nx, volver, hist


def pronosticar(modelo, nx, volver, idx):
    X, _ = ventanas(idx)
    return volver(modelo.predict(nx(X), verbose=0)).reshape(len(idx), len(HS), 24)


def media_y_ee(d, L):
    n = len(d)
    u = d - d.mean()
    v = np.mean(u * u)
    for l in range(1, min(L, n - 1) + 1):
        v += 2 * (1 - l / (L + 1)) * np.mean(u[l:] * u[:-l])
    return d.mean(), np.sqrt(v / n)


def criterio(idx, pred, tope):
    # el del notebook original, con la normal; la corrección de Harvey et al. se calcula después
    y = Y_dia[idx].copy()
    fuera = (f[idx].to_numpy()[:, None] + np.array(HS, dtype="timedelta64[D]")) > np.datetime64(tope)
    y[fuera] = np.nan
    filas = []
    for nombre, hs in BLOQUES.items():
        j = [HS.index(h) for h in hs]
        e = y[:, j] - pred[:, j]
        ingenuos = {"del día": y[:, j], "semanal": y[:, j] - Y_sem[idx][:, j]}
        rmse = {k: np.sqrt(np.nanmean(v ** 2)) for k, v in ingenuos.items()}
        ref = min(rmse, key=rmse.get)
        d = np.nanmean((e ** 2 - ingenuos[ref] ** 2).reshape(len(idx), -1), axis=1)
        m, ee = media_y_ee(d[~np.isnan(d)], max(hs) - 1 + 7)
        r = np.sqrt(np.nanmean(e ** 2))
        mejora, p = 100 * (1 - r / rmse[ref]), 2 * stats.norm.sf(abs(m / ee))
        filas.append(dict(bloque=nombre, rmse_log=r, mejor_ingenuo=ref, rmse_ingenuo=rmse[ref],
                          mejora=mejora, dm_t=m / ee, dm_p=p, funciona=mejora >= 5 and p < 0.05))
    return pd.DataFrame(filas).set_index("bloque").round(4)


def a_filas(idx, pred, tope):
    n = len(idx)
    d = pd.DataFrame({"fecha": np.repeat(f[idx], len(HS) * 24),
                      "hora": np.tile(np.arange(1, 25), n * len(HS)),
                      "h": np.tile(np.repeat(HS, 24), n),
                      "y_hat": pred.reshape(-1)})
    return d[d["fecha"] + pd.to_timedelta(d["h"], unit="D") <= pd.Timestamp(tope)]


# ----------------------------------------------------------------------------- validación de 2022, como referencia
inicio_reloj = time.time()
idx_tr, idx_va = origenes(INICIO, FIN_ENTRENAMIENTO), origenes("2022-01-01", FIN_VALIDACION)
ruta_val = SALIDA / "validacion_2022.csv"
if not ruta_val.exists():
    modelo, nx, volver, hist = entrenar(idx_tr, 100, idx_va)
    mejor_epoca = int(np.argmin(hist.history["val_loss"]) + 1)
    val = criterio(idx_va, pronosticar(modelo, nx, volver, idx_va), FIN_VALIDACION)
    val.assign(mejor_epoca=mejor_epoca).to_csv(ruta_val)
    print(f"validación 2022: mejor época {mejor_epoca} (la original fue 6), "
          f"{time.time() - inicio_reloj:.0f} s", flush=True)
print(pd.read_csv(ruta_val, index_col=0), flush=True)


# ----------------------------------------------------------------------------- prueba, reentrenando cada mes
def walk_forward(nombre, desde, hasta):
    cortes = pd.date_range(desde, hasta, freq="MS")
    tope = pd.Timestamp(hasta)
    partes = []
    for k, c in enumerate(cortes):
        sig = cortes[k + 1] if k + 1 < len(cortes) else tope + pd.Timedelta(days=1)
        ev = origenes(c, min(sig - pd.Timedelta(days=1), tope - pd.Timedelta(days=min(HS))), completos=False)
        ruta = SALIDA / "meses" / f"{nombre}_{c:%Y_%m}.npy"
        if ruta.exists():
            pred = np.load(ruta)
        else:
            t0 = time.time()
            keras.backend.clear_session()
            tr = origenes(INICIO, c - pd.Timedelta(days=1))
            modelo, nx, volver, _ = entrenar(tr, EPOCAS)
            pred = pronosticar(modelo, nx, volver, ev)
            np.save(ruta, pred)
            print(f"{c.date()}: {len(tr)} días de entrenamiento, {time.time() - t0:.0f} s", flush=True)
        partes.append((ev, pred))
    return np.concatenate([p[0] for p in partes]), np.concatenate([p[1] for p in partes])


resultados = []
for nombre, desde, hasta in [("2023_2025", "2023-01-01", FIN_TEST), ("2026", "2026-01-01", FIN_2026)]:
    idx, pred = walk_forward(nombre, desde, hasta)
    a_filas(idx, pred, hasta).to_csv(SALIDA / f"prueba_{nombre}.csv.gz", index=False, float_format="%.6f")
    resultados.append(criterio(idx, pred, hasta).assign(periodo=nombre))
resultados = pd.concat(resultados)
resultados.to_csv(SALIDA / "prueba_criterio_repeticion.csv")
json.dump({**HP, "epocas": EPOCAS, "dias_entrada": DIAS_ENTRADA, "perdida": "mae", "semilla": 0,
           "reentrenar": "mensual", "keras": keras.__version__, "backend": keras.backend.backend(),
           "minutos": round((time.time() - inicio_reloj) / 60, 1)},
          open(SALIDA / "corrida.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(resultados)
