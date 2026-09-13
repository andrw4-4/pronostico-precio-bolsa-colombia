"""
================================================================================
CORRER TODO EL PIPELINE EN ORDEN
================================================================================

Para que las cifras de la tesis salgan de UNA sola corrida:

  00 panel -> 01 seleccion -> 02 bloques -> 03 candidatos -> 06 auditoria
  -> notebook 04 (XGBoost en nivel) -> notebook 05 (XGBoost en diferencia)

Se detiene en el primer paso que falle. Si la auditoria reporta algun FAIL,
se detiene antes de los notebooks (usa --ignorar-auditoria para seguir).

Los notebooks se ejecutan con nbconvert y quedan guardados CON sus salidas
(--inplace), asi que al abrirlos ves los resultados de esta corrida.

Al final escribe salidas_modelos/corrida.json con la hora de cada paso.

Uso
---
  python correr_pipeline.py
  python correr_pipeline.py --desde 02          # retoma desde un paso
  python correr_pipeline.py --ignorar-auditoria
================================================================================
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent

PASOS = [
    ("00", "script", "00_consolidar_panel.py"),
    ("01", "script", "01_seleccion_variables.py"),
    ("02", "script", "02_evaluacion_bloques.py"),
    ("03", "script", "03_bloques_candidatos.py"),
    ("06", "script", "06_auditoria.py"),
    ("04", "notebook", "04_xgboost.ipynb"),
    ("05", "notebook", "05_xgboost_diferencia.ipynb"),
]


def comando(tipo, archivo):
    if tipo == "script":
        return [sys.executable, archivo]
    return [sys.executable, "-m", "nbconvert", "--to", "notebook",
            "--execute", "--inplace",
            "--ExecutePreprocessor.timeout=-1",
            "--ExecutePreprocessor.kernel_name=python3", archivo]


def fallas_auditoria():
    ruta = BASE / "salidas_seleccion" / "auditoria.csv"
    if not ruta.exists():
        return ["no se genero salidas_seleccion/auditoria.csv"]
    res = pd.read_csv(ruta)
    return [f"{r.codigo} {r.titulo}" for r in res.itertuples()
            if r.estado == "FAIL"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="00",
                    choices=[p[0] for p in PASOS],
                    help="codigo del paso desde el que se retoma")
    ap.add_argument("--ignorar-auditoria", action="store_true",
                    help="seguir con los notebooks aunque 06 reporte FAIL")
    args = ap.parse_args()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    codigos = [p[0] for p in PASOS]
    pasos = PASOS[codigos.index(args.desde):]
    registro = {"inicio": pd.Timestamp.now().isoformat(timespec="seconds"),
                "python": sys.version.split()[0], "pasos": []}
    t_total = time.time()

    for codigo, tipo, archivo in pasos:
        print("\n" + "#" * 78)
        print(f"# PASO {codigo}: {archivo}")
        print("#" * 78, flush=True)
        t0 = time.time()
        r = subprocess.run(comando(tipo, archivo), cwd=BASE, env=env)
        seg = round(time.time() - t0, 1)
        registro["pasos"].append({"paso": codigo, "archivo": archivo,
                                  "segundos": seg, "codigo_salida": r.returncode,
                                  "fin": pd.Timestamp.now().isoformat(
                                      timespec="seconds")})
        if r.returncode != 0:
            print(f"\n[X] El paso {codigo} ({archivo}) fallo con codigo "
                  f"{r.returncode}. Corrige y retoma con:")
            print(f"    python correr_pipeline.py --desde {codigo}")
            sys.exit(r.returncode)
        print(f"\n[OK] paso {codigo} en {seg:.0f}s")

        if codigo == "06":
            fallas = fallas_auditoria()
            if fallas:
                print("\n[!] La auditoria reporto FAIL:")
                for f in fallas:
                    print(f"    {f}")
                if not args.ignorar_auditoria:
                    print("\nSe detiene antes de los notebooks. Corrige, o "
                          "sigue igual con --desde 04 --ignorar-auditoria.")
                    sys.exit(2)

    registro["fin"] = pd.Timestamp.now().isoformat(timespec="seconds")
    registro["minutos_total"] = round((time.time() - t_total) / 60, 1)
    out = BASE / "salidas_modelos"
    out.mkdir(exist_ok=True)
    (out / "corrida.json").write_text(
        json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 78)
    print(f"PIPELINE COMPLETO en {registro['minutos_total']} min")
    print(f"Registro: {out / 'corrida.json'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
