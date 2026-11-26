"""
Paso 9f: paneles para el periodo limpio (días posteriores al 6 de octubre de 2026).

    python 9f_paneles_periodo_limpio.py

El panel de la tesis termina el 6 de octubre de 2026 y todas las decisiones se tomaron con él. Los
días posteriores son los únicos que ningún modelo ni ninguna decisión tocó. Este paso arma los
mismos paneles con la descarga actualizada, sin cambiar nada más, en la carpeta periodo_limpio/,
para no pisar los paneles congelados:

1. Copia a periodo_limpio/ los pasos 2, 2b, 2c y 2e tal como están y los corre ahí, sobre
   periodo_limpio/datos/ (la descarga actualizada con 1_descargar.py).
2. Arma panel_horario_modelo.csv.gz con las mismas columnas del panel congelado. No repite la
   selección del paso 2d: toma los nombres de las columnas ya elegidas.
3. Arma panel_lstm_bloques.csv.gz con las nueve variables de los bloques 3 y 4, como el paso 2h.
4. Comprueba que, hasta agosto de 2026, los paneles nuevos coinciden con los congelados. XM corrige
   los datos de las últimas semanas, así que cerca del 6 de octubre puede haber diferencias; se
   reportan.

Salidas: periodo_limpio/paneles/ y periodo_limpio/comprobacion_paneles.csv.
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
LIMPIO = RAIZ / "periodo_limpio"
PAN_NUEVO, PAN_VIEJO = LIMPIO / "paneles", RAIZ / "paneles"
PASOS = ["2_construir_panel.py", "2b_panel_horario.py", "2c_caracteristicas_horarias.py", "2e_panel_lstm.py"]
APOYO = ["features.py", "2f_datos_lstm.py", "2g_termica_programada.py"]
BLOQUES = ["cmg_despacho", "disp_decl_hoy_rel", "cmg_hoy_vs_precio", "frac_termica_prog", "brecha_escasez",
           "presion_hidro_horaria", "aportes_media_hist", "volumen_util_pct", "dias_autonomia"]
FIJAS_LSTM = (["fecha", "hora", "precio", "lp", "dia_semana", "es_festivo"]
              + [f"{c}_k{k}" for k in range(1, 8) for c in ("dia_semana", "es_festivo")]
              + [f"y_h{h}" for h in range(3, 10)])
HASTA_IGUAL = "2026-08-31"


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, LIMPIO / archivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def comparar(nuevo, viejo, claves, nombre):
    """Diferencia máxima por columna entre el panel nuevo y el congelado, antes y después de HASTA_IGUAL."""
    j = viejo.merge(nuevo, on=claves, how="left", suffixes=("", "_n"), validate="one_to_one")
    filas = []
    for c in [c for c in viejo.columns if c not in claves and pd.api.types.is_numeric_dtype(viejo[c])]:
        d = (j[c] - j[c + "_n"]).abs()
        vacio = j[c].isna() != j[c + "_n"].isna()
        antes = j["fecha"] <= HASTA_IGUAL
        filas.append({"panel": nombre, "columna": c, "dif_max_hasta_agosto": d[antes].max(),
                      "vacios_distintos_hasta_agosto": int(vacio[antes].sum()),
                      "dif_max_despues": d[~antes].max(), "vacios_distintos_despues": int(vacio[~antes].sum())})
    return pd.DataFrame(filas)


def main():
    PAN_NUEVO.mkdir(parents=True, exist_ok=True)
    for a in PASOS + APOYO:
        shutil.copy(RAIZ / a, LIMPIO / a)
    for paso in PASOS:
        print(f"== {paso}", flush=True)
        subprocess.run([sys.executable, paso], cwd=LIMPIO, check=True)

    # ------------------------------------------------------------------ panel de XGBoost, SARIMAX y LEAR
    sys.path.insert(0, str(LIMPIO))
    fe = cargar("features_limpio", "features.py")
    base, info = fe.leer_panel_caracteristicas(PAN_NUEVO / "panel_caracteristicas.csv.gz",
                                               PAN_NUEVO / "panel_caracteristicas_variables.csv")
    viejo = pd.read_csv(PAN_VIEJO / "panel_horario_modelo.csv.gz", parse_dates=["fecha"])
    columnas = [c for c in viejo.columns if c not in ("fecha", "hora")]
    tabla = fe.armar(base, info, columnas).reset_index()[["fecha", "hora"] + columnas]
    tabla.to_csv(PAN_NUEVO / "panel_horario_modelo.csv.gz", index=False, compression="gzip", float_format="%.6g")
    shutil.copy(PAN_VIEJO / "panel_horario_modelo_columnas.csv", PAN_NUEVO / "panel_horario_modelo_columnas.csv")
    print(f"panel_horario_modelo: {len(tabla):,} filas, del {tabla['fecha'].min().date()} al {tabla['fecha'].max().date()}")
    comprobacion = [comparar(tabla, viejo, ["fecha", "hora"], "panel_horario_modelo")]

    # ------------------------------------------------------------------ panel de la LSTM por bloques
    g2 = cargar("paso_2g_limpio", "2g_termica_programada.py")          # lee periodo_limpio/datos y el panel 2e nuevo
    panel, info_l = g2.f2.leer()
    assert g2.D == 2
    nuevas = g2.termica_por_hora()
    lado = panel[["fecha", "hora"]].merge(nuevas.reset_index(), on=["fecha", "hora"], how="left")
    panel["frac_termica_prog"] = lado["frac_termica_prog"].shift(-24 * g2.D).to_numpy()   # el despacho del día t + 2
    ultimo = panel.loc[panel["lp"].notna(), "fecha"].max()
    panel[BLOQUES] = panel.groupby("hora")[BLOQUES].ffill()
    ventana = (panel["fecha"] >= "2015-03-01") & (panel["fecha"] <= ultimo)
    assert not panel.loc[ventana, BLOQUES].isna().any().any()
    bloques = panel[FIJAS_LSTM + BLOQUES]
    bloques.to_csv(PAN_NUEVO / "panel_lstm_bloques.csv.gz", index=False, compression="gzip", float_format="%.6g")
    shutil.copy(PAN_VIEJO / "panel_lstm_bloques_variables.csv", PAN_NUEVO / "panel_lstm_bloques_variables.csv")
    print(f"panel_lstm_bloques: {len(bloques):,} filas; último día con precio {ultimo.date()}")
    viejo_l = pd.read_csv(PAN_VIEJO / "panel_lstm_bloques.csv.gz", usecols=FIJAS_LSTM + BLOQUES, parse_dates=["fecha"])
    comprobacion.append(comparar(bloques, viejo_l, ["fecha", "hora"], "panel_lstm_bloques"))

    c = pd.concat(comprobacion, ignore_index=True)
    c.to_csv(LIMPIO / "comprobacion_paneles.csv", index=False, float_format="%.6g")
    print(c.groupby("panel")[["dif_max_hasta_agosto", "vacios_distintos_hasta_agosto", "dif_max_despues",
                              "vacios_distintos_despues"]].max().to_string())
    print(c.sort_values("dif_max_hasta_agosto", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
