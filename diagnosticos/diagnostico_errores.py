"""Dónde falla el modelo a una semana, con los pronósticos guardados. Solo lectura."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 100)
R = "resultados/modelo_xgboost/"
HS = list(range(3, 10))

t = pd.concat([pd.read_csv(R + f"prueba_h{h}.csv.gz", parse_dates=["fecha"]) for h in HS])
m = pd.read_csv(R + "prueba2026_mensual.csv.gz", parse_dates=["fecha"])
d = pd.concat([t.assign(periodo="2023-2025"), m[m["h"].isin(HS)].assign(periodo="2026")], ignore_index=True)
d["e"] = d["y"] - d["y_hat"]
d["objetivo"] = d["fecha"] + pd.to_timedelta(d["h"], unit="D")
d["año"] = d["fecha"].dt.year
r = lambda x: float(np.sqrt(np.mean(np.square(x))))
print("filas", len(d), "| orígenes", d["fecha"].nunique())

p = pd.read_csv("paneles/panel_horario_modelo.csv.gz", usecols=["fecha", "hora", "precio"], parse_dates=["fecha"])
lp = np.log(p.pivot(index="fecha", columns="hora", values="precio"))

# 1. un ingenuo más exigente: promedios de días recientes, a la misma hora
m7 = lp.rolling(7).mean()
largo = m7.stack().rename("m7").reset_index()
d = d.merge(largo, on=["fecha", "hora"], how="left")
d["lp_t"] = np.log(d["precio_t"])
d["e_m7"] = d["y"] - (d["m7"] - d["lp_t"])
d["e_sem"] = d["y"] - d["y_semanal"]
# promedio de las últimas 4 semanas conocidas, mismo día de la semana y hora
lp_l = lp.stack().rename("v").reset_index()
idx = lp_l.set_index(["fecha", "hora"])["v"]
k0 = np.ceil(d["h"] / 7).astype(int)
s = 0
for k in range(4):
    c = pd.MultiIndex.from_arrays([d["objetivo"] - pd.to_timedelta(7 * (k0 + k), unit="D"), d["hora"]])
    s = s + idx.reindex(c).to_numpy()
d["e_m4s"] = d["y"] - (s / 4 - d["lp_t"])

print("\n=== 1. ingenuos más exigentes, RMSE")
filas = []
for n, g in list(d.groupby("periodo")) + [("todo", d)]:
    filas.append(dict(periodo=n, modelo=r(g["e"]), del_dia=r(g["y"]), semanal=r(g["e_sem"]), media_7d=r(g["e_m7"]), media_4sem=r(g["e_m4s"])))
print(pd.DataFrame(filas).round(3).to_string(index=False))
print("por h:"); print(d.groupby("h").apply(lambda g: pd.Series(dict(modelo=r(g["e"]), del_dia=r(g["y"]), media_7d=r(g["e_m7"]), media_4sem=r(g["e_m4s"])))).round(3).T.to_string())

print("\n=== 2. nivel del día contra forma dentro del día")
dia = d.groupby(["fecha", "h"])["e"].transform("mean")
print(f"parte del error cuadrático que es nivel del día: {100 * (dia ** 2).mean() / (d['e'] ** 2).mean():.0f}%; forma: {100 * ((d['e'] - dia) ** 2).mean() / (d['e'] ** 2).mean():.0f}%")
for c, n in (("y", "del día"), ("e_m7", "media 7d")):
    x = d.groupby(["fecha", "h"])[c].transform("mean")
    print(f"  {n}: RMSE nivel {r(x):.3f}, forma {r(d[c] - x):.3f}")
print(f"  modelo: RMSE nivel {r(dia):.3f}, forma {r(d['e'] - dia):.3f}")

print("\n=== 3. por franja horaria")
fr = pd.cut(d["hora"], [0, 6, 12, 17, 21, 24], labels=["1-6", "7-12", "13-17", "18-21", "22-24"])
x = d.groupby(fr).apply(lambda g: pd.Series(dict(modelo=r(g["e"]), del_dia=r(g["y"]), media_7d=r(g["e_m7"]), sesgo=g["e"].mean(), parte_mse=100 * (g["e"] ** 2).sum() / (d["e"] ** 2).sum())))
print(x.round(3).to_string())

print("\n=== 4. el modelo se atreve poco: encogimiento")
b = np.polyfit(d["y_hat"], d["y"], 1)
print(f"pendiente de y sobre y_hat {b[0]:.2f}, intercepto {b[1]:.3f} | sd(y_hat) {d['y_hat'].std():.3f} sd(y) {d['y'].std():.3f} | corr {np.corrcoef(d['y'], d['y_hat'])[0, 1]:.3f} | R2 frente a 0: {1 - (d['e'] ** 2).mean() / (d['y'] ** 2).mean():.3f}")
for a, c in ((-9, -0.7), (-0.7, -0.3), (-0.3, 0.3), (0.3, 0.7), (0.7, 9)):
    g = d[(d["y"] > a) & (d["y"] <= c)]
    print(f"  y en ({a}, {c}]: {100 * len(g) / len(d):4.1f}% filas, {100 * (g['e'] ** 2).sum() / (d['e'] ** 2).sum():4.1f}% del error, y medio {g['y'].mean():+.2f}, y_hat medio {g['y_hat'].mean():+.2f}")

print("\n=== 5. el día base: un día raro en t arrastra el pronóstico")
d["dev"] = d["lp_t"] - d["m7"]
print(f"corr(e, dev) {np.corrcoef(d['e'], d['dev'])[0, 1]:.3f} | corr(y, dev) {np.corrcoef(d['y'], d['dev'])[0, 1]:.3f} | corr(y_hat, dev) {np.corrcoef(d['y_hat'], d['dev'])[0, 1]:.3f}")
print(f"pendiente de y sobre dev {np.polyfit(d['dev'], d['y'], 1)[0]:.2f} | de y_hat sobre dev {np.polyfit(d['dev'], d['y_hat'], 1)[0]:.2f} | de e sobre dev {np.polyfit(d['dev'], d['e'], 1)[0]:.2f}")
q = pd.qcut(d["dev"], [0, .05, .25, .75, .95, 1], labels=["muy bajo", "bajo", "normal", "alto", "muy alto"])
print(d.groupby(q).apply(lambda g: pd.Series(dict(modelo=r(g["e"]), media_7d=r(g["e_m7"]), del_dia=r(g["y"]), sesgo=g["e"].mean()))).round(3).to_string())

print("\n=== 6. por nivel de precio en t")
q = pd.cut(d["precio_t"], [0, 200, 400, 800, 1e6], labels=["<200", "200-400", "400-800", ">800"])
print(d.groupby(q).apply(lambda g: pd.Series(dict(filas=100 * len(g) / len(d), modelo=r(g["e"]), del_dia=r(g["y"]), media_7d=r(g["e_m7"]), sesgo=g["e"].mean()))).round(3).to_string())

print("\n=== 7. sesgo por trimestre y su persistencia")
tri = d.groupby(d["fecha"].dt.to_period("Q")).apply(lambda g: pd.Series(dict(sesgo=g["e"].mean(), rmse=r(g["e"]), del_dia=r(g["y"]), media_7d=r(g["e_m7"]))))
print(tri.round(3).to_string())
e_d = d.groupby("fecha")["e"].mean()
print("autocorrelación del error medio por origen, rezagos 1, 7, 14:", [round(e_d.autocorr(k), 3) for k in (1, 7, 14)])

print("\n=== 8. día de la semana objetivo y festivos")
print(d.groupby(d["objetivo"].dt.dayofweek).apply(lambda g: pd.Series(dict(modelo=r(g["e"]), del_dia=r(g["y"]), semanal=r(g["e_sem"]), media_4sem=r(g["e_m4s"]), sesgo=g["e"].mean()))).round(3).T.to_string())

print("\n=== 9. picos: la hora máxima del día")
g = d.assign(pron=d["precio_t"] * np.exp(d["y_hat"]), real=d["precio_t"] * np.exp(d["y"]))
a = g.groupby(["fecha", "h"])
top = pd.DataFrame(dict(hora_real=g.loc[a["real"].idxmax(), ["fecha", "h", "hora"]].set_index(["fecha", "h"])["hora"],
                        hora_pron=g.loc[a["pron"].idxmax(), ["fecha", "h", "hora"]].set_index(["fecha", "h"])["hora"],
                        max_real=a["real"].max(), max_pron=a["pron"].max()))
print(f"misma hora del pico: {100 * (top['hora_real'] == top['hora_pron']).mean():.0f}% | a una hora o menos: {100 * ((top['hora_real'] - top['hora_pron']).abs() <= 1).mean():.0f}%")
print(f"razón pico pronosticado/real, mediana {(top['max_pron'] / top['max_real']).median():.2f}, p10 {(top['max_pron'] / top['max_real']).quantile(.1):.2f}, p90 {(top['max_pron'] / top['max_real']).quantile(.9):.2f}")
print(f"días con el pico real más de 1,5 veces el pronosticado: {100 * (top['max_real'] / top['max_pron'] > 1.5).mean():.0f}%")

print("\n=== 10. horas seguidas con el mismo precio real (escalones)")
v = p.sort_values(["fecha", "hora"])
print(f"filas iguales a la hora anterior del mismo día: {100 * (v.groupby('fecha')['precio'].diff() == 0).mean():.0f}%")
print(v[v["fecha"] >= "2023-01-01"].groupby(v["fecha"].dt.year)["precio"].apply(lambda x: round(100 * (x.diff() == 0).mean(), 0)).to_dict())
