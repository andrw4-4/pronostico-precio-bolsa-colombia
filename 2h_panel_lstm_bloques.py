"""
Paso 2h: el panel de la LSTM por bloques.

    python 2h_panel_lstm_bloques.py

Junta en un solo archivo lo que necesita 6c_lstm_seleccion.ipynb en Colab: el
panel 2e completo (cada variable alineada a su fecha de publicación, con el
precio a 2 días) y frac_termica_prog del paso 2g. Aparte deja una tabla que dice
a qué bloque pertenece cada variable. Los bloques son los de
docs/LSTM_DISENO.md; las variables que no están en ningún bloque solo se usan en
la prueba de control con todas.

Este paso no elige nada ni mira el objetivo. Corre después del 2e, el 2f y el 2g.

Salidas, en paneles/:
    panel_lstm_bloques.csv.gz          fecha, hora, precio, lp, calendario del día
                                       t y de los 7 días objetivo, objetivos y
                                       las variables
    panel_lstm_bloques_variables.csv   una fila por variable: tipo, grupo del 2f,
                                       bloque y días frente al precio
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
PANELES = BASE / "paneles"
_spec = importlib.util.spec_from_file_location("paso_2f", BASE / "2f_datos_lstm.py")
f2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f2)
assert f2.D == 2, "el panel por bloques va con el precio a 2 días, como XGBoost y SARIMAX"

# Los bloques 1 (precio) y 2 (calendario) entran siempre y no llevan variables de esta tabla.
# El 7 (pronósticos de XGBoost y SARIMAX) se arma aparte, al final.
BLOQUES = {
    3: ("despacho de hoy", ["cmg_hoy_vs_precio", "cmg_despacho", "disp_decl_hoy_rel",
                            "frac_termica_prog"]),
    4: ("estado hidrológico", ["volumen_util_pct", "aportes_media_hist", "presion_hidro_horaria",
                               "brecha_escasez", "dias_autonomia"]),
    5: ("despacho de ayer", ["cmg_redespacho", "error_cmg_despacho", "redespacho_vs_programa"]),
    6: ("clima que viene", ["oni", "nino34_anom", "lluvia_anom_acum30", "pred_deficit"]),
}
FIJAS = (["fecha", "hora", "precio", "lp", "dia_semana", "es_festivo"]
         + [f"{c}_k{k}" for k in range(1, 8) for c in ("dia_semana", "es_festivo")]
         + [f"y_h{h}" for h in range(3, 10)])


def main():
    panel, info = f2.leer()
    grupo = {v: g for g, lista in f2.grupos(info).items() for v in lista}

    modelo = pd.read_csv(PANELES / "panel_lstm_modelo.csv.gz", parse_dates=["fecha"],
                         usecols=["fecha", "hora", "cmg_despacho", "frac_termica_prog"])
    junto = panel.merge(modelo, on=["fecha", "hora"], how="left", validate="one_to_one",
                        suffixes=("", "_2g"))
    # el 2g guardó su variable sobre este mismo panel: una columna en común tiene que coincidir
    assert np.allclose(junto["cmg_despacho"], junto["cmg_despacho_2g"], equal_nan=True, atol=1e-5)
    panel["frac_termica_prog"] = junto["frac_termica_prog"].to_numpy()

    variables = [v for v in info.index if v != "lp"] + ["frac_termica_prog"]
    tabla = pd.DataFrame({
        "tipo": [info["tipo"].get(v, "horaria") for v in variables],
        "grupo": [grupo.get(v, "despacho_de_hoy") for v in variables],
        "dias_frente_al_precio": [info["dias_frente_al_precio"].get(v, -2) for v in variables],
    }, index=pd.Index(variables, name="variable"))
    tabla["bloque"] = 0
    for b, (_, lista) in BLOQUES.items():
        assert set(lista) <= set(variables), f"bloque {b}: faltan {set(lista) - set(variables)}"
        tabla.loc[lista, "bloque"] = b
    tabla["nombre_bloque"] = tabla["bloque"].map({b: n for b, (n, _) in BLOQUES.items()}).fillna("solo control")

    # Huecos sueltos: se repite el último valor conocido de esa misma hora, que no trae futuro
    ultimo = panel.loc[panel["lp"].notna(), "fecha"].max()
    ventana = (panel["fecha"] >= pd.Timestamp(f2.INICIO)) & (panel["fecha"] <= ultimo)
    antes = int(panel.loc[ventana, variables].isna().sum().sum())
    panel[variables] = panel.groupby("hora")[variables].ffill()
    assert not panel.loc[ventana, variables].isna().any().any()

    diarias = tabla.index[tabla["tipo"] == "diaria"]
    por_dia = panel.loc[ventana].groupby("fecha")[diarias]
    assert ((por_dia.max() - por_dia.min()).abs().max() < 1e-9).all(), "una variable diaria cambia dentro del día"

    ruta = PANELES / "panel_lstm_bloques.csv.gz"
    panel[FIJAS + variables].to_csv(ruta, index=False, compression="gzip", float_format="%.6g")
    tabla.to_csv(PANELES / "panel_lstm_bloques_variables.csv")

    print(tabla[tabla["bloque"] > 0].sort_values("bloque")[["nombre_bloque", "tipo", "grupo",
                                                            "dias_frente_al_precio"]].to_string())
    print(f"\nvalores rellenados entre {pd.Timestamp(f2.INICIO).date()} y {ultimo.date()}: {antes}")
    print(f"{ruta.name}: {len(panel):,} filas x {len(FIJAS) + len(variables)} columnas, "
          f"{len(variables)} variables ({int((tabla['bloque'] > 0).sum())} en bloques), "
          f"{ruta.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
