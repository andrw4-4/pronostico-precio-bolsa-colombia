"""
Paso 2g (exploratorio): ¿sirve saber cuánta térmica quedó programada para hoy?

    python 2g_termica_programada.py

El panel 2e solo usa el total de la generación programada. Aquí se separa por
planta con datos que ya están descargados: una planta es térmica si aparece en
el consumo de combustible de XM, y su combustible principal es el que más
consumió en toda la historia. Ser térmica o no es un dato fijo de la planta, así
que usar toda la historia para clasificarla no trae información del futuro.

Variables, del despacho del día R = t + D (se publica la víspera, L = 0):
    frac_termica_prog   generación térmica programada / total programado
    frac_liquidos_prog  lo mismo, solo plantas a ACPM, combustóleo, crudo,
                        queroseno o GLP, las más caras

Se miden como en el paso 3 del 2f (XGBoost proxy, walk-forward anual 2020-2022,
Diebold-Mariano) sobre las 5 variables finales. Como la selección del 2f ya se
hizo con 2020-2022, este resultado es exploratorio: no cambia el panel de la
LSTM por sí solo.

Salida: paneles/panel_lstm_termica.csv
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
XM = BASE / "datos" / "xm"


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, BASE / archivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


f2 = cargar("paso_2f", "2f_datos_lstm.py")
D = f2.D
FINALES = ["cmg_hoy_vs_precio", "cmg_despacho", "disp_decl_hoy_rel", "brecha_escasez",
           "presion_hidro_horaria"]
LIQUIDOS = {"ACPM", "COMBUSTOLEO", "CRUDO", "QUEROSENE", "GLP"}
HORAS = [f"Values_Hour{i:02d}" for i in range(1, 25)]


def combustible_principal():
    c = pd.read_csv(XM / "consumo_combustible.csv.gz")
    c["total"] = c[HORAS].sum(axis=1)
    return c.groupby(["Values_code", "Values_Name"])["total"].sum().groupby(level=0).idxmax().str[1]


def termica_por_hora():
    g = pd.read_csv(XM / "gen_programada.csv.gz")
    comb = combustible_principal()
    g["comb"] = g["Values_code"].map(comb)
    largo = g.melt(id_vars=["Date", "comb"], value_vars=HORAS, var_name="hora", value_name="mwh")
    largo["hora"] = largo["hora"].str[-2:].astype(int)
    largo["fecha"] = pd.to_datetime(largo["Date"])
    tot = largo.groupby(["fecha", "hora"])["mwh"].sum()
    ter = largo[largo["comb"].notna()].groupby(["fecha", "hora"])["mwh"].sum()
    liq = largo[largo["comb"].isin(LIQUIDOS)].groupby(["fecha", "hora"])["mwh"].sum()
    return pd.DataFrame({"frac_termica_prog": ter.reindex(tot.index, fill_value=0) / tot,
                         "frac_liquidos_prog": liq.reindex(tot.index, fill_value=0) / tot})


def main():
    panel, info = f2.leer()
    nuevas = termica_por_hora()
    lado = panel[["fecha", "hora"]].merge(nuevas.reset_index(), on=["fecha", "hora"], how="left")
    for v in nuevas.columns:
        # en la fila t va el despacho del día R = t + D
        panel[v] = lado[v].shift(-24 * D).to_numpy()
    print(panel.groupby(panel["fecha"].dt.year)[list(nuevas.columns)].mean().round(3).to_string())

    extra = pd.DataFrame({"tipo": "horaria"}, index=list(nuevas.columns))
    sub = pd.concat([info.loc[["lp"] + FINALES], extra])
    R, de = f2.resumen(panel, sub)
    F = panel["fecha"].to_numpy("datetime64[D]")

    def medir(vars_):
        err = {}
        for h in f2.HS:
            y = panel[f"y_h{h}"].to_numpy(float)
            A = pd.concat([f2.base(panel, h), R[[c for v in vars_ for c in de[v]]]], axis=1)
            A = A.to_numpy(np.float32)
            err[h] = pd.concat([f2.errores_por_dia(F, y, A, *f2.filas(F, y, h, año - 1, año))
                                for año in f2.AÑOS_VALIDACION])
        return err

    ref = medir(FINALES)
    res = []
    for nombre, vars_ in [("las 5 finales", FINALES),
                          ("+ frac_termica_prog", FINALES + ["frac_termica_prog"]),
                          ("+ frac_liquidos_prog", FINALES + ["frac_liquidos_prog"]),
                          ("+ las dos", FINALES + list(nuevas.columns))]:
        err = ref if vars_ is FINALES else medir(vars_)
        f = dict(conjunto=nombre)
        for h in f2.HS:
            f[f"mejora_h{h}"] = 100 * (1 - f2.rmse(err[h]) / f2.rmse(err[h], "i2"))
            if vars_ is not FINALES:
                f[f"t_h{h}"], f[f"p_h{h}"] = f2.diebold_mariano(err[h]["e2"], ref[h]["e2"], h)
        res.append(f)
        print(f"   {nombre}: listo", flush=True)

    res = pd.DataFrame(res)
    res.to_csv(BASE / "paneles" / "panel_lstm_termica.csv", index=False)
    print(res.round(3).to_string(index=False))

    # la que pasa la regla del 2f se agrega al panel de la LSTM (corre después del 2f)
    ruta = BASE / "paneles" / f"panel_lstm_modelo{f2.SUFIJO}.csv.gz"
    modelo = pd.read_csv(ruta, parse_dates=["fecha"]).drop(columns="frac_termica_prog", errors="ignore")
    modelo = modelo.merge(panel[["fecha", "hora", "frac_termica_prog"]], on=["fecha", "hora"],
                          how="left", validate="one_to_one")
    modelo.to_csv(ruta, index=False, compression="gzip", float_format="%.6g")
    print(f"{ruta.name}: {modelo.shape[0]:,} filas x {modelo.shape[1]} columnas")


if __name__ == "__main__":
    main()
