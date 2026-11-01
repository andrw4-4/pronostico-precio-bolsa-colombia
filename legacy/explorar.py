"""
Análisis exploratorio de las variables que más pesan en el pronóstico.

    streamlit run explorar.py

No descarga nada. Lee paneles/panel_diario.csv (paso 2) y, para el perfil por horas,
el archivo horario del precio que dejó el paso 1.

Qué es una "variable importante": la misma medida que usa 3_modelos.ipynb para
elegir variables. Se ordenan las características con Lasso y con la ganancia de
XGBoost sobre la ventana de selección (2015-2019) y se promedian los dos
puestos. Como cada variable del panel genera varias características (rezagos,
medias, choques), aquí se agrupan: una variable vale lo que vale su mejor
característica.

La primera vez tarda un par de minutos (armar la matriz y ordenar); después
queda guardado en la caché de Streamlit.
"""

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import xgboost as xgb
from plotly.subplots import make_subplots
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

# El Lasso avisa que no converge del todo en algunos valores de la penalización;
# pasa igual en el notebook y no cambia el orden de las variables.
warnings.filterwarnings("ignore", category=ConvergenceWarning)

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))
import features as fe  # noqa: E402

PANEL = CARPETA / "paneles" / "panel_diario.csv"
PRECIO_HORARIO = CARPETA / "datos" / "xm" / "precio_bolsa.csv.gz"
FIN_SELECCION = pd.Timestamp("2019-12-31")
SEMILLA = 42

VENTANAS = [("2015-01-01", "2019-12-31", "Selección", "rgba(31,95,153,0.07)"),
            ("2020-01-01", "2022-12-31", "Validación", "rgba(194,87,26,0.07)"),
            ("2023-01-01", "2025-12-31", "Prueba A", "rgba(60,122,70,0.07)"),
            ("2026-01-01", "2026-12-31", "Prueba B", "rgba(194,87,26,0.14)")]
AZUL, NARANJA, NAVY, GRIS = "#1f5f99", "#c2571a", "#14213d", "#8a93a3"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Nombres legibles para las variables que más aparecen. Las que no estén aquí
# se muestran con su nombre de columna.
NOMBRES = {
    "precio (su propia dinámica)": "Cambios y volatilidad pasados del precio",
    "calendario": "Día de la semana (lunes, sábado, domingo)",
    "volumen_util_pct": "Volumen útil de los embalses (%)",
    "inv_volumen_util_pct": "1 / volumen útil",
    "aportes_pct_sistema": "Aportes hídricos (% de la media histórica)",
    "aportes_media_hist": "Aportes medios históricos",
    "aportes_por_rio": "Aportes de los ríos (energía)",
    "aportes_pct_rio": "Aportes por río (% de la media)",
    "aportes_caudal": "Aportes de los ríos (caudal)",
    "aportes_caudal_medio": "Caudal medio histórico de los ríos",
    "volumen_por_embalse": "Volumen embalsado (energía)",
    "capacidad_por_embalse": "Capacidad útil de los embalses",
    "volumen_util_pct_emb": "Volumen útil ponderado por embalse",
    "descargas_embalse": "Descargas de los embalses",
    "turbinado_embalse": "Volumen turbinado",
    "vertido_embalse": "Vertimientos por embalse",
    "vertimientos": "Vertimientos del sistema",
    "hhi_volumen_embalses": "Concentración del agua embalsada",
    "hhi_aportes_rios": "Concentración de los aportes",
    "vol_pct_penol": "Nivel del embalse Peñol",
    "vol_pct_guavio": "Nivel del embalse Guavio",
    "vol_pct_esmeralda": "Nivel del embalse Esmeralda",
    "vol_pct_agregado_bogota": "Nivel de los embalses de Bogotá",
    "demanda_regulada": "Demanda regulada",
    "demanda_no_regulada": "Demanda no regulada",
    "demanda_real": "Demanda real",
    "demanda_max_potencia": "Demanda máxima de potencia",
    "demanda_pico": "Demanda en la hora pico",
    "factor_carga": "Factor de carga (media / pico)",
    "demanda_upme_alto": "Proyección de demanda UPME (alta)",
    "demanda_upme_medio": "Proyección de demanda UPME (media)",
    "demanda_upme_bajo": "Proyección de demanda UPME (baja)",
    "gen_programada": "Generación programada",
    "gen_prog_redespacho": "Generación programada en redespacho",
    "gen_por_recurso": "Generación total",
    "gen_hidraulica": "Generación hidráulica",
    "gen_termica": "Generación térmica",
    "gen_solar": "Generación solar",
    "frac_hidraulica": "Participación hidráulica",
    "frac_termica": "Participación térmica",
    "frac_fncer": "Participación solar y eólica",
    "gen_gas": "Generación a gas",
    "gen_carbon": "Generación a carbón",
    "gen_liquidos": "Generación con líquidos",
    "gen_seguridad": "Generación de seguridad",
    "gen_fuera_merito": "Generación fuera de mérito",
    "hhi_generacion": "Concentración de la generación",
    "consumo_combustible": "Consumo de combustible",
    "disp_declarada": "Disponibilidad declarada",
    "disp_real": "Disponibilidad real",
    "disp_comercial": "Disponibilidad comercial",
    "disp_decl_hidraulica": "Disponibilidad declarada hidráulica",
    "disp_decl_termica": "Disponibilidad declarada térmica",
    "capacidad_efectiva": "Capacidad efectiva neta",
    "margen_reserva": "Margen de reserva",
    "oblig_energia_firme": "Obligaciones de energía en firme",
    "compras_contrato": "Compras en contratos",
    "precio_prom_contrato": "Precio promedio de contratos regulados",
    "precio_cont_no_regu": "Precio promedio de contratos no regulados",
    "precio_escasez": "Precio de escasez",
    "precio_cargo_conf": "Precio del cargo por confiabilidad",
    "enficc": "ENFICC",
    "restricciones": "Restricciones",
    "importaciones": "Importaciones",
    "exportaciones": "Exportaciones",
    "precio_max_dia": "Precio máximo del día",
    "precio_min_dia": "Precio mínimo del día",
    "precio_spread_intradia": "Diferencia máximo - mínimo del día",
    "precio_cv_intradia": "Dispersión del precio dentro del día",
    "ratio_pico_valle": "Precio pico / valle",
    "hora_precio_max": "Hora del precio máximo",
    "cap_bajo_100": "Capacidad ofertada bajo 100 COP/kWh",
    "cap_bajo_200": "Capacidad ofertada bajo 200 COP/kWh",
    "cap_bajo_300": "Capacidad ofertada bajo 300 COP/kWh",
    "cap_bajo_500": "Capacidad ofertada bajo 500 COP/kWh",
    "cap_bajo_1000": "Capacidad ofertada bajo 1.000 COP/kWh",
    "oferta_marginal": "Oferta de la planta marginal",
    "oferta_dispersion": "Dispersión de las ofertas",
    "oferta_capacidad_total": "Capacidad total ofertada",
    "oferta_min": "Oferta más barata",
    "oferta_max": "Oferta más cara",
    "oferta_p25": "Percentil 25 de las ofertas",
    "oferta_p50": "Mediana de las ofertas",
    "oferta_p75": "Percentil 75 de las ofertas",
    "margen_ofertado": "Capacidad ofertada sobre la demanda",
    "escalon_siguiente": "Salto de precio a la siguiente planta",
    "n_plantas_activas": "Número de plantas generando",
    "gen_top5_pct": "Participación de las 5 plantas más grandes",
    "gen_filo_agua": "Generación a filo de agua",
    "frac_gas_en_termica": "Participación del gas en la térmica",
    "aportes_top3_pct": "Participación de los 3 ríos que más aportan",
    "n_rios_aportando": "Número de ríos aportando",
    "pendiente_curva": "Pendiente de la curva de mérito",
    "holgura_gwh": "Holgura de la curva frente a la demanda",
    "nino12_anom": "Anomalía Niño 1+2 (semanal)",
    "nino34_anom": "Anomalía Niño 3.4 (semanal)",
    "nino3_anom": "Anomalía Niño 3 (semanal)",
    "nino4_anom": "Anomalía Niño 4 (semanal)",
    "nino_gradiente_costa": "Gradiente costa - Pacífico central",
    "oni": "ONI",
    "roni": "RONI",
    "trm": "Tasa de cambio (TRM)",
    "lluvia_sistema": "Lluvia sobre las cuencas (día)",
    "lluvia_anomalia": "Anomalía de lluvia sobre las cuencas",
    "lluvia_anom_acum30": "Anomalía de lluvia acumulada 30 días",
    "lluvia_anom_acum90": "Anomalía de lluvia acumulada 90 días",
    "pred_deficit": "IDEAM: déficit de lluvia pronosticado",
    "pred_enos": "IDEAM: fase del ENOS según el boletín",
    "pred_prob_max": "IDEAM: probabilidad máxima del boletín",
    "pred_lluvia_andina": "IDEAM: lluvia pronosticada región Andina",
    "pred_lluvia_caribe": "IDEAM: lluvia pronosticada región Caribe",
    "pred_lluvia_orinoquia": "IDEAM: lluvia pronosticada Orinoquía",
    "pred_lluvia_amazonia": "IDEAM: lluvia pronosticada Amazonía",
}

# Bloque al que pertenece cada variable, por el comienzo de su nombre. El
# orden importa: gana el primero que coincida.
BLOQUES = [
    ("Precio", ("precio (",)),
    ("Calendario", ("calendario",)),
    ("Perfil del día", ("precio_max_dia", "precio_min_dia", "precio_spread", "precio_cv",
                        "hora_precio", "ratio_pico", "factor_carga", "demanda_pico")),
    ("Pronóstico IDEAM", ("pred_",)),
    ("Lluvia (ERA5)", ("lluvia_",)),
    ("El Niño", ("nino", "oni", "roni")),
    ("Curva de mérito", ("oferta_", "cap_bajo", "margen_ofertado", "escalon", "holgura",
                         "pendiente_curva")),
    ("Hidrología", ("aportes", "volumen", "vol_pct", "inv_volumen", "capacidad_por_embalse",
                    "vertim", "vertido", "descargas", "turbinado", "hhi_aportes",
                    "hhi_volumen", "n_rios")),
    ("Red e intercambios", ("import", "export", "perdidas", "restricc", "tie_",
                            "compras_tie", "ventas_tie")),
    ("Contratos", ("compras_contrato", "precio_prom_contrato", "precio_cont")),
    ("Regulación", ("enficc", "precio_cargo", "precio_esca", "cee", "cere", "mc")),
    ("Disponibilidad", ("disp_", "capacidad_efectiva", "margen_reserva", "oblig_energia")),
    ("Generación", ("gen_", "frac_", "hhi_gen", "n_plantas", "consumo_combustible")),
    ("Demanda", ("demanda", "dem_")),
    ("Economía", ("trm",)),
]


def nombre(v):
    return NOMBRES.get(v, v.replace("_", " "))


def bloque(v):
    for b, prefijos in BLOQUES:
        if v.startswith(prefijos):
            return b
    return "Otras"


def variable_base(caracteristica):
    """De 'aportes_pct_sistema_choque7' a 'aportes_pct_sistema'."""
    if caracteristica.startswith(("dlog_", "precio_choque")):
        return "precio (su propia dinámica)"
    if caracteristica in ("es_lunes", "es_sabado", "es_domingo"):
        return "calendario"
    return re.sub(r"_(lag\d+|ma\d+|choque\d+)$", "", caracteristica)


def forma(caracteristica):
    """Cómo entra la variable: 'rezago 1 d', 'choque 7 d', 'media 30 d'."""
    m = re.search(r"_(lag|ma|choque|sd)(\d+)$", caracteristica)
    if not m:
        return caracteristica.replace("_", " ")
    tipo, k = m.groups()
    if tipo == "lag":
        return "mismo día" if k == "0" else f"rezago {k} d"
    return {"ma": "media", "choque": "choque", "sd": "volatilidad"}[tipo] + f" {k} d"


def sombrear_ventanas(fig):
    for a, b, texto, color in VENTANAS:
        fig.add_vrect(x0=a, x1=b, fillcolor=color, line_width=0, layer="below",
                      annotation_text=texto, annotation_position="top left",
                      annotation_font_size=11, annotation_font_color=GRIS)
    return fig


# ===========================================================================
# Datos (todo con caché: el panel cambia solo cuando se corre el paso 2)
# ===========================================================================

def version_panel():
    """La fecha de modificación del panel invalida la caché cuando cambia."""
    return PANEL.stat().st_mtime


@st.cache_data
def cargar_panel(_version):
    panel = fe.leer_panel(PANEL)
    base, descartes = fe.preparar_panel(panel)
    return panel, base, descartes


@st.cache_data(persist="disk", show_spinner="Armando la matriz de características...")
def cargar_matriz(_version):
    panel, _, _ = cargar_panel(_version)
    X, precio, log_precio = fe.construir_features(panel)
    columnas = fe.limpiar_matriz(X.loc[:FIN_SELECCION].dropna())
    return X[columnas], log_precio, X.shape[1]


@st.cache_data(persist="disk",
               show_spinner="Ordenando las variables con Lasso y XGBoost (un par de minutos)...")
def ranking(h, _version):
    """El mismo ranquear() de 3_modelos.ipynb, sobre la ventana de selección."""
    X, log_precio, _ = cargar_matriz(_version)
    datos = pd.concat([X, fe.objetivo(log_precio, h)], axis=1).dropna()
    sel = datos.loc[:FIN_SELECCION]
    Xs, y = sel.drop(columns="y"), sel["y"]

    lasso = LassoCV(cv=TimeSeriesSplit(n_splits=3, gap=h), max_iter=20000,
                    random_state=SEMILLA, n_jobs=-1).fit(StandardScaler().fit_transform(Xs), y)
    puesto_lasso = pd.Series(np.abs(lasso.coef_), index=Xs.columns).rank(ascending=False)
    arboles = xgb.XGBRegressor(n_estimators=500, max_depth=3, learning_rate=0.03,
                               subsample=0.8, colsample_bytree=0.8, min_child_weight=10,
                               reg_lambda=3.0, random_state=SEMILLA, n_jobs=-1,
                               tree_method="hist").fit(Xs, y)
    puesto_xgb = pd.Series(arboles.feature_importances_, index=Xs.columns).rank(ascending=False)
    puesto = ((puesto_lasso + puesto_xgb) / 2).sort_values()

    # Una variable vale lo que vale su mejor característica.
    caract = pd.DataFrame({"caracteristica": puesto.index, "puesto": puesto.values})
    caract["variable"] = caract["caracteristica"].map(variable_base)
    caract["top100"] = caract["puesto"].rank() <= 100
    por_variable = (caract.sort_values("puesto")
                          .groupby("variable", sort=False)
                          .agg(mejor_puesto=("puesto", "first"),
                               mejor_forma=("caracteristica", "first"),
                               en_top100=("top100", "sum"))
                          .reset_index())
    return por_variable, caract, len(sel)


@st.cache_data
def perfil_horario():
    if not PRECIO_HORARIO.exists():
        return None
    d = pd.read_csv(PRECIO_HORARIO)
    horas = [f"Values_Hour{h:02d}" for h in range(1, 25)]
    m = d[horas].apply(pd.to_numeric, errors="coerce").groupby(pd.to_datetime(d["Date"])).mean()
    m = m[m.index < "2026-01-01"]
    relativo = m.div(m.mean(axis=1), axis=0)
    tabla = relativo.groupby(relativo.index.month).mean()
    tabla.index = [MESES[i - 1] for i in tabla.index]
    tabla.columns = range(1, 25)
    return tabla


def serie(v, panel, base):
    """La serie original de una variable: del panel, o de la base si es derivada."""
    if v in panel.columns:
        return panel[v]
    if v in base.columns:
        return base[v]
    return None


# ===========================================================================
# Página
# ===========================================================================

st.set_page_config(page_title="Exploración del precio de bolsa", layout="wide")
st.title("Exploración de las variables del precio de bolsa")

if not PANEL.exists():
    st.error("No encuentro panel_diario.csv. Se arma con: python 2_construir_panel.py")
    st.stop()

version = version_panel()
panel, base, descartes = cargar_panel(version)
precio = panel[fe.OBJETIVO]
log_precio = np.log(precio)

with st.sidebar:
    st.header("Opciones")
    h = st.radio("Horizonte del pronóstico", [1, 7], format_func=lambda x: f"{x} día" + ("s" if x > 1 else ""),
                 help="La importancia se calcula para el cambio del precio a este horizonte.")
    n_top = st.slider("Cuántas variables mostrar", 10, 40, 20, step=5)
    desde, hasta = st.select_slider(
        "Periodo de las gráficas", options=list(range(2015, 2027)), value=(2015, 2026))
    st.caption(f"Panel: {panel.shape[0]:,} días × {panel.shape[1]} columnas, "
               f"del {panel.index.min().date()} al {panel.index.max().date()}. "
               f"Entran al modelo {base.shape[1]}.")

rango = (panel.index.year >= desde) & (panel.index.year <= hasta)

tab_precio, tab_rank, tab_var, tab_corr, tab_datos = st.tabs(
    ["El precio", "Variables más importantes", "Una variable", "Correlaciones", "Calidad de los datos"])

# ---------------------------------------------------------------- el precio
with tab_precio:
    p = precio[rango].dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Último precio", f"{p.iloc[-1]:,.0f} COP/kWh", help=str(p.index[-1].date()))
    c2.metric("Mediana del periodo", f"{p.median():,.0f}")
    c3.metric("Mínimo", f"{p.min():,.0f}", help=str(p.idxmin().date()))
    c4.metric("Máximo", f"{p.max():,.0f}", help=str(p.idxmax().date()))

    fig = go.Figure(go.Scatter(x=p.index, y=p.values, line=dict(color=NAVY, width=1), name="precio"))
    sombrear_ventanas(fig)
    fig.update_layout(height=380, margin=dict(t=30, b=10), yaxis_title="COP/kWh",
                      title="Precio de bolsa diario y ventanas de la tesis")
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Año por año**")
    anual = pd.DataFrame({
        "media": p.groupby(p.index.year).mean(),
        "mediana": p.groupby(p.index.year).median(),
        "mínimo": p.groupby(p.index.year).min(),
        "máximo": p.groupby(p.index.year).max(),
        "volatilidad diaria (%)": 100 * np.log(p).diff().groupby(p.index.year).std(),
    }).round(1)
    anual.index.name = "año"
    st.dataframe(anual, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(p, nbins=80, color_discrete_sequence=[AZUL])
        fig.update_layout(height=320, showlegend=False, title="Nivel: muy sesgado a la derecha",
                          xaxis_title="COP/kWh", yaxis_title="días", margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
    with c2:
        cambio = np.log(p).diff(h).dropna().clip(-1.5, 1.5)
        fig = px.histogram(cambio, nbins=100, color_discrete_sequence=[NARANJA])
        fig.update_layout(height=320, showlegend=False,
                          title=f"Cambio del log a {h} día{'s' if h > 1 else ''}: lo que predice el modelo",
                          xaxis_title="log P(t+h) − log P(t)", yaxis_title="días", margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")

    tabla = perfil_horario()
    if tabla is not None:
        fig = px.imshow(tabla, color_continuous_scale="YlOrBr", aspect="auto",
                        labels=dict(x="hora (1 = de 0:00 a 1:00)", y="mes", color="hora / día"))
        fig.update_layout(height=380, margin=dict(t=40, b=10),
                          title="Precio de cada hora frente al promedio del día (2015-2025)")
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- ranking
por_variable, caract, n_sel = ranking(h, version)
top = por_variable.head(n_top).copy()

with tab_rank:
    st.markdown(
        f"Ranking del pronóstico a **{h} día{'s' if h > 1 else ''}**, calculado como en el notebook: "
        f"Lasso y XGBoost sobre la ventana de selección ({n_sel:,} días de 2015-2019), promediando "
        "los dos puestos. Cada variable aparece con su mejor característica.")
    st.caption("Dos cuidados al leerlo. Como se calcula con 2015-2019, una variable que solo se "
               "volvió importante después puede quedar baja aunque hoy pese. Y cuando el Lasso deja "
               "muchas características en cero, todas empatan en puesto: diferencias de pocos puestos "
               "entre variables de la parte baja no significan nada.")

    top["etiqueta"] = top["variable"].map(nombre)
    top["bloque"] = top["variable"].map(bloque)
    top["forma"] = top["mejor_forma"].map(forma)
    fig = px.bar(top.iloc[::-1], x="mejor_puesto", y="etiqueta", color="bloque", orientation="h",
                 hover_data={"variable": True, "forma": True, "en_top100": True, "etiqueta": False},
                 labels={"mejor_puesto": "mejor puesto entre todas las características (menor = más importante)",
                         "etiqueta": ""})
    # con color por bloque Plotly agrupa las barras por bloque; se fuerza el
    # orden del ranking
    fig.update_yaxes(categoryorder="array", categoryarray=list(top["etiqueta"].iloc[::-1]))
    fig.update_layout(height=max(380, 26 * len(top)), margin=dict(t=10, b=10),
                      legend_title_text="bloque")
    st.plotly_chart(fig, width="stretch")

    # Las fechas van como texto: el calendario y la dinámica del precio no
    # tienen serie propia, y una columna que mezcla fechas y vacíos no se
    # puede mostrar.
    vista = top.assign(arranca=top["variable"].map(
        lambda v: (str(s.first_valid_index().date()) if (s := serie(v, panel, base)) is not None else "—")))
    vista = vista[["etiqueta", "variable", "bloque", "forma", "mejor_puesto", "en_top100", "arranca"]]
    vista.columns = ["variable", "columna", "bloque", "mejor forma", "mejor puesto",
                     "características en el top 100", "arranca"]
    vista.index = range(1, len(vista) + 1)
    st.dataframe(vista.round(1), width="stretch")

    st.markdown("**Qué bloques dominan**: cuántas de las 100 mejores características aporta cada uno")
    por_bloque = (caract[caract["top100"]].assign(bloque=lambda d: d["variable"].map(bloque))
                  .groupby("bloque").size().sort_values())
    fig = px.bar(por_bloque, orientation="h", color_discrete_sequence=[AZUL],
                 labels={"value": "características en el top 100", "bloque": ""})
    fig.update_layout(height=360, showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- una variable
with tab_var:
    solo_top = st.toggle("Elegir solo entre las más importantes", value=True)
    opciones = list(top["variable"]) if solo_top else sorted(
        set(por_variable["variable"]) | set(base.columns))
    # se abre en la primera que tenga serie propia (el calendario no la tiene)
    inicial = next((i for i, o in enumerate(opciones) if serie(o, panel, base) is not None), 0)
    v = st.selectbox("Variable", opciones, index=inicial,
                     format_func=lambda x: f"{nombre(x)}  ({x})")
    x = serie(v, panel, base)

    if v == "calendario":
        st.info("El calendario no es una serie: se ve como el cambio del precio según el día de la semana.")
        d = pd.DataFrame({"cambio": np.log(precio).diff(), "dia": precio.index.dayofweek})[rango].dropna()
        d["dia"] = d["dia"].map(dict(enumerate(["lun", "mar", "mié", "jue", "vie", "sáb", "dom"])))
        fig = px.box(d, x="dia", y="cambio", points=False, color_discrete_sequence=[AZUL],
                     category_orders={"dia": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]})
        fig.update_layout(height=420, yaxis_title="log P(t) − log P(t−1)", xaxis_title="")
        st.plotly_chart(fig, width="stretch")
    elif x is None:
        st.info("Esta es la dinámica del propio precio: sus cambios pasados. "
                "Se ve como la autocorrelación del cambio diario.")
        cambio = np.log(precio).diff()[rango]
        acf = pd.Series({k: cambio.autocorr(k) for k in range(1, 61)})
        fig = px.bar(acf, color_discrete_sequence=[AZUL],
                     labels={"index": "rezago (días)", "value": "autocorrelación"})
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    else:
        fila = por_variable.set_index("variable").reindex([v])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bloque", bloque(v))
        c2.metric("Arranca", str(x.first_valid_index().date()))
        c3.metric("Faltantes", f"{100 * x.isna().mean():.1f}%")
        if not fila["mejor_puesto"].isna().all():
            c4.metric("Mejor forma en el modelo", forma(fila["mejor_forma"].iloc[0]),
                      help=f"puesto {fila['mejor_puesto'].iloc[0]:.0f}")
        else:
            c4.metric("En el modelo", "no entra")

        xr, pr = x[rango], precio[rango]
        suavizar = st.toggle("Suavizar con la media de 30 días", value=False)
        xs = xr.rolling(30, min_periods=10).mean() if suavizar else xr

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=xs.index, y=xs.values, name=nombre(v),
                                 line=dict(color=AZUL, width=1.2)), secondary_y=False)
        fig.add_trace(go.Scatter(x=pr.index, y=pr.values, name="precio de bolsa",
                                 line=dict(color=NARANJA, width=1), opacity=0.7), secondary_y=True)
        sombrear_ventanas(fig)
        fig.update_yaxes(title_text=nombre(v), secondary_y=False)
        fig.update_yaxes(title_text="COP/kWh", secondary_y=True, showgrid=False)
        fig.update_layout(height=400, margin=dict(t=30, b=10), legend=dict(orientation="h", y=1.08),
                          title=f"{nombre(v)} y el precio")
        st.plotly_chart(fig, width="stretch")

        c1, c2 = st.columns(2)
        with c1:
            # lo que se sabía ayer frente al precio de hoy
            d = pd.DataFrame({"x": x.shift(1), "precio": precio})[rango].dropna()
            d["año"] = d.index.year.astype(str)
            fig = px.scatter(d, x="x", y="precio", color="año", log_y=True, opacity=0.45,
                             labels={"x": f"{nombre(v)} (ayer)", "precio": "precio de hoy (escala log)"})
            if d["x"].nunique() > 10:
                tramos = pd.qcut(d["x"], 15, duplicates="drop")
                med = d.groupby(tramos, observed=True).agg(x=("x", "median"), precio=("precio", "median"))
                fig.add_trace(go.Scatter(x=med["x"], y=med["precio"], mode="lines+markers",
                                         name="mediana por tramo", line=dict(color=NAVY, width=3)))
            fig.update_traces(marker=dict(size=4), selector=dict(mode="markers"))
            fig.update_layout(height=420, margin=dict(t=40, b=10),
                              title="Relación con el precio del día siguiente")
            st.plotly_chart(fig, width="stretch")
        with c2:
            # ¿cuánto anticipa? correlación de Spearman entre la variable de hoy y
            # el cambio del precio en los h días siguientes
            xx = x[rango]
            filas = []
            for k in [1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60, 90]:
                futuro = (log_precio.shift(-k) - log_precio)[rango]
                nivel = log_precio.shift(-k)[rango]
                filas.append({"días adelante": k,
                              "con el cambio del precio": xx.corr(futuro, method="spearman"),
                              "con el nivel del precio": xx.corr(nivel, method="spearman")})
            cc = pd.DataFrame(filas).set_index("días adelante")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=cc.index, y=cc["con el nivel del precio"], name="con el nivel",
                                     mode="lines+markers", line=dict(color=AZUL)))
            fig.add_trace(go.Scatter(x=cc.index, y=cc["con el cambio del precio"], name="con el cambio",
                                     mode="lines+markers", line=dict(color=NARANJA)))
            fig.add_hline(y=0, line_color=GRIS, line_width=1)
            fig.update_layout(height=420, margin=dict(t=40, b=10), yaxis_range=[-1, 1],
                              xaxis_title="días hacia adelante", yaxis_title="correlación de Spearman",
                              title="¿Cuánto anticipa? Valor de hoy frente al precio futuro",
                              legend=dict(orientation="h", y=1.08))
            st.plotly_chart(fig, width="stretch")
        st.caption("La correlación con el nivel dice si la variable acompaña al precio; la correlación "
                   "con el cambio dice si anticipa hacia dónde se mueve, que es lo que el modelo predice. "
                   "Que sea baja no quiere decir que no sirva: el modelo usa combinaciones de variables.")

        c1, c2 = st.columns(2)
        with c1:
            d = pd.DataFrame({"x": xr, "mes": xr.index.month}).dropna()
            d["mes"] = d["mes"].map(lambda m: MESES[m - 1])
            fig = px.box(d, x="mes", y="x", points=False, color_discrete_sequence=[AZUL],
                         category_orders={"mes": MESES}, labels={"x": nombre(v), "mes": ""})
            fig.update_layout(height=360, margin=dict(t=40, b=10), title="Estacionalidad por mes")
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = px.histogram(xr.dropna(), nbins=60, color_discrete_sequence=[AZUL])
            fig.update_layout(height=360, showlegend=False, margin=dict(t=40, b=10),
                              title="Distribución", xaxis_title=nombre(v), yaxis_title="días")
            st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- correlaciones
with tab_corr:
    vars_ = [v for v in top["variable"] if serie(v, panel, base) is not None]
    tabla = pd.DataFrame({nombre(v): serie(v, panel, base) for v in vars_})
    tabla.insert(0, "Precio de bolsa", precio)
    corr = tabla[rango].corr(method="spearman")
    fig = px.imshow(corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto",
                    text_auto=".2f")
    fig.update_layout(height=max(500, 34 * len(corr)), margin=dict(t=40, b=10),
                      title="Correlación de Spearman entre las variables más importantes")
    fig.update_traces(textfont_size=9)
    st.plotly_chart(fig, width="stretch")

    pares = (corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
                 .rename("correlación").reset_index())
    pares.columns = ["variable A", "variable B", "correlación"]
    pares = pares[pares["correlación"].abs() >= 0.8].sort_values("correlación", key=abs, ascending=False)
    st.markdown("**Pares muy parecidos** (|correlación| ≥ 0,8): dicen casi lo mismo")
    if len(pares):
        st.dataframe(pares.round(2), width="stretch", hide_index=True)
    else:
        st.write("Ninguno en este grupo.")

# ---------------------------------------------------------------- calidad
with tab_datos:
    filas = []
    for c in panel.columns:
        s = panel[c]
        ini = s.first_valid_index()
        fin = s.last_valid_index()
        filas.append({"columna": c, "bloque": bloque(c),
                      "arranca": str(ini.date()) if ini is not None else "—",
                      "último dato": str(fin.date()) if fin is not None else "—",
                      "atraso (días)": (panel.index.max() - fin).days if fin is not None else None,
                      "faltantes %": round(100 * s.isna().mean(), 1),
                      "entra al modelo": "sí" if c in base.columns else "no"})
    inv = pd.DataFrame(filas)

    resumen = inv.groupby("bloque").agg(columnas=("columna", "size"),
                                        entran=("entra al modelo", lambda s: (s == "sí").sum()),
                                        faltantes_medio=("faltantes %", "mean"),
                                        ultimo_dato=("último dato", "min")).round(1)
    st.markdown("**Por bloque**")
    st.dataframe(resumen.sort_values("columnas", ascending=False), width="stretch")

    X, _, n_creadas = cargar_matriz(version)
    c1, c2, c3 = st.columns(3)
    c1.metric("Columnas del panel", panel.shape[1])
    c2.metric("Entran al modelo", base.shape[1])
    c3.metric("Características limpias", X.shape[1], help=f"{n_creadas:,} creadas antes de limpiar")

    st.markdown("**Qué queda fuera y por qué**")
    for motivo, cols in descartes.items():
        st.write(f"- {motivo}: " + (", ".join(cols) if cols else "ninguna"))

    st.markdown("**Todas las columnas**")
    st.dataframe(inv.sort_values(["bloque", "columna"]), width="stretch", hide_index=True)
