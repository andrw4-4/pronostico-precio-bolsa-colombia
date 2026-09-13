"""
================================================================================
06 — AUDITORIA DEL PIPELINE
================================================================================

Convierte "creo que esta bien" en "el script confirma que esta bien".

No interpreta resultados ni juzga si el modelo es bueno. Solo verifica
mecanicamente que no haya fuga de informacion ni inconsistencias entre etapas
-- que es lo unico que invalidaria todo lo demas.

Cada chequeo imprime PASS / FAIL / WARN y explica que significa. Al final da
un veredicto global.

  PASS  el chequeo se cumple
  WARN  algo que revisar a mano, no necesariamente un error
  FAIL  fuga o inconsistencia real -- hay que corregir antes de seguir

Los chequeos estan agrupados por el tipo de pregunta que responden:

  A. TEMPORALIDAD    ¿alguna feature usa informacion del futuro?
  B. SPLIT           ¿seleccion, validacion y prueba quedaron separadas?
  C. CONSTRUCCION    ¿las ventanas moviles se calcularon con shift(1)?
  D. COHERENCIA      ¿las etapas usan las mismas features y periodos?
  E. DATOS           ¿el panel tiene problemas silenciosos?

Uso
---
  python 06_auditoria.py
================================================================================
"""

import json
import sys
import warnings
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

_e1 = import_module("01_seleccion_variables")
CONFIG = _e1.CONFIG


# ==============================================================================
# INFRAESTRUCTURA DE REPORTE
# ==============================================================================

RESULTADOS = []


def chequeo(codigo, titulo, estado, detalle="", explicacion=""):
    RESULTADOS.append({"codigo": codigo, "titulo": titulo, "estado": estado})
    simbolo = {"PASS": "[ OK ]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[estado]
    print(f"{simbolo} {codigo}  {titulo}")
    if detalle:
        for linea in str(detalle).split("\n"):
            print(f"         {linea}")
    if explicacion and estado != "PASS":
        print(f"         -> {explicacion}")


def seccion(titulo):
    print("\n" + "=" * 74)
    print(titulo)
    print("=" * 74)


# ==============================================================================
# A. TEMPORALIDAD -- la pregunta central: ¿se usa informacion del futuro?
# ==============================================================================

# Series que el catalogo de XM describe como MEDIDAS (no pronosticadas).
# Usarlas con lag 0 es fuga, salvo que el consolidador ya les haya aplicado
# un rezago interno (caso de margen_reserva).
SERIES_MEDIDAS = {
    "demanda_regulada", "demanda_no_regulada", "demanda_por_or",
    "gen_por_recurso", "gen_fuera_merito", "gen_seguridad",
    "restricciones", "restricciones_sin_aliv", "perdidas_energia",
    "importaciones", "exportaciones", "consumo_combustible",
    "emisiones_co2_sistema", "demanda_no_atendida", "dem_no_atendida_noprog",
    "disp_real", "volumen_util_pct", "volumen_util_pct_emb",
    # disp_comercial: XM la ajusta con la operacion real (ver catalogo), asi
    # que su valor del dia D no se conoce antes del despacho de D
    "disp_comercial",
    "aportes_pct_sistema", "aportes_por_rio", "aportes_pct_rio",
    "aportes_media_hist", "volumen_por_embalse", "capacidad_por_embalse",
    "vertimientos", "precio_prom_contrato", "precio_cont_no_regu",
    "compras_contrato",
}

# Variables que el consolidador construye con rezago interno: su lag0 ya
# incorpora un shift, asi que es legitimo.
REZAGO_INTERNO = {"margen_reserva"}

# Casi-identidades con el target. Nunca deberian estar en el modelo final.
SERIES_DESPACHO = {
    "costo_marginal_prog", "precio_oferta_desp", "max_precio_oferta",
    "recurso_marginal",
}


def auditar_temporalidad(X, cfg, ya_excluido=False):
    seccion("A. TEMPORALIDAD — ¿alguna feature usa informacion del futuro?")

    # --- A1: lag0 sobre series medidas -------------------------------------
    lag0 = [c for c in X.columns if c.endswith("_lag0")]
    sospechosas, justificadas = [], []
    for c in lag0:
        base = c[:-5]
        if base in REZAGO_INTERNO:
            justificadas.append(c)
        elif base in SERIES_MEDIDAS:
            sospechosas.append(c)

    if sospechosas:
        chequeo("A1", "lag0 sobre series medidas (no pronosticadas)", "FAIL",
                f"{len(sospechosas)} features: {sospechosas}",
                "Estas series se MIDEN, no se pronostican: su valor del dia D "
                "no existe cuando se pronostica el precio de D. Rezagalas o "
                "sacalas de ex_ante_cols en CONFIG.")
    else:
        det = f"{len(lag0)} features con lag0, ninguna sobre serie medida"
        if justificadas:
            det += f"\ncon rezago interno (OK): {justificadas}"
        chequeo("A1", "lag0 sobre series medidas (no pronosticadas)", "PASS", det)

    # --- A2: bloque DESPACHO fuera ------------------------------------------
    # Se audita X DESPUES de aplicar la misma exclusion que hace main() en la
    # etapa 01. construir_features() genera las 421 features crudas y main()
    # elimina las de despacho despues; auditar el estado intermedio reportaria
    # fuga donde el pipeline real si las excluye.
    desp = [c for c in X.columns
            if any(c.startswith(p) for p in SERIES_DESPACHO)]
    quiere_excluir = cfg.get("excluir_despacho", True)

    if not quiere_excluir:
        chequeo("A2", "Bloque DESPACHO excluido", "WARN",
                f"excluir_despacho=False, {len(desp)} features de despacho "
                f"entrarian al modelo",
                "Solo valido si lo usas explicitamente como benchmark "
                "superior, reportando la diferencia contra el modelo sin "
                "despacho.")
    elif desp:
        chequeo("A2", "Bloque DESPACHO excluido", "FAIL",
                f"{len(desp)} features sobrevivieron la exclusion: {desp[:6]}",
                "El precio de bolsa ES el costo marginal del despacho. "
                "Revisa que los prefijos de SERIES_DESPACHO coincidan con "
                "CONFIG['blocks']['DESPACHO'].")
    else:
        n_esperadas = len(SERIES_DESPACHO)
        chequeo("A2", "Bloque DESPACHO excluido", "PASS",
                f"exclusion aplicada; ninguna feature de costo marginal, "
                f"precio de oferta o recurso marginal ({n_esperadas} series "
                f"vigiladas)")

    # --- A3: correlacion sospechosamente alta con el target -----------------
    return lag0


def auditar_correlacion_target(X, y, cfg, umbral=0.97):
    """
    Una feature casi perfectamente correlacionada con el target suele ser
    el target disfrazado. No prueba fuga por si sola (los lags del precio
    correlacionan mucho por construccion), pero merece revision.
    """
    alertas = []
    for c in X.columns:
        d = pd.concat([X[c], y], axis=1).dropna()
        if len(d) < 100:
            continue
        r = abs(d.corr().iloc[0, 1])
        if np.isfinite(r) and r > umbral:
            alertas.append((c, r))

    esperadas = ("log_precio_lag1", "log_precio_ma")
    inesperadas = [(c, r) for c, r in alertas
                   if not any(c.startswith(e) for e in esperadas)]

    if inesperadas:
        det = "\n".join(f"{c}: rho={r:.4f}" for c, r in inesperadas)
        chequeo("A3", f"Correlacion con el target > {umbral}", "WARN", det,
                "Revisa la definicion de estas series en catalogo_metricas. "
                "Una correlacion casi perfecta suele ser el target disfrazado.")
    else:
        det = f"{len(alertas)} features sobre el umbral, todas son lags/medias "
        det += "del propio precio (esperado por construccion)"
        chequeo("A3", f"Correlacion con el target > {umbral}", "PASS", det)


def auditar_oni(df, rezago_esperado=2):
    """
    El ONI del mes M lo publica NOAA a inicios de M+2. El panel debe tenerlo
    desplazado rezago_esperado meses: se reconstruye desde el CSV crudo con 0,
    1 y 2 meses de desplazamiento y se ve cual coincide con el panel.
    """
    ruta = BASE_DIR / "data" / "oni_noaa.csv"
    if "oni" not in df.columns or not ruta.exists():
        chequeo("A4", "ONI con rezago de publicacion", "WARN",
                "falta la columna 'oni' en el panel o el CSV crudo")
        return

    raw = pd.read_csv(ruta)
    col_f = raw.columns[0]
    col_v = next((c for c in raw.columns if "oni" in c.lower()),
                 raw.columns[-1])
    s = pd.Series(pd.to_numeric(raw[col_v], errors="coerce").values,
                  index=pd.to_datetime(raw[col_f], errors="coerce"))
    s = s[s.index.notna()].dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    panel = pd.to_numeric(df["oni"], errors="coerce")

    difs = {}
    for meses in sorted({0, 1, rezago_esperado}):
        t = s.copy()
        t.index = t.index + pd.DateOffset(months=meses)
        fin = max(t.index.max(), panel.index.max())
        diaria = t.reindex(pd.date_range(t.index.min(), fin, freq="D")).ffill()
        d = pd.concat([panel, diaria.reindex(panel.index)], axis=1).dropna()
        difs[meses] = (float((d.iloc[:, 0] - d.iloc[:, 1]).abs().max())
                       if len(d) else np.inf)

    if difs[rezago_esperado] < 1e-9:
        chequeo("A4", "ONI con rezago de publicacion", "PASS",
                f"el panel coincide con el ONI desplazado {rezago_esperado} "
                f"meses")
    elif difs[0] < 1e-9:
        chequeo("A4", "ONI con rezago de publicacion", "FAIL",
                "el panel usa el ONI del mismo mes, sin rezago de publicacion",
                "El modelo conoce el ONI unas seis semanas antes de que NOAA "
                "lo publique. Vuelve a correr 00_consolidar_panel.py.")
    else:
        resumen = ", ".join(f"{k}m={v:.2e}" for k, v in difs.items())
        chequeo("A4", "ONI con rezago de publicacion", "WARN",
                f"no coincide con ningun desplazamiento probado ({resumen})",
                "Revisa como se construye 'oni' en 00_consolidar_panel.py.")


# ==============================================================================
# B. SPLIT -- ¿seleccion, validacion y prueba quedaron separadas?
# ==============================================================================

def auditar_split(X, cfg):
    seccion("B. SPLIT — ¿seleccion, validacion y prueba quedaron separadas?")

    corte = pd.Timestamp(cfg["selection_cutoff"])
    val_ini = pd.Timestamp(cfg["validation_start"])
    val_fin = pd.Timestamp(cfg["validation_end"])
    test_ini = pd.Timestamp(cfg["test_start"])
    test_fin = pd.Timestamp(cfg["test_end"])

    # --- B1: los tres periodos no se traslapan -----------------------------
    det = (f"seleccion <= {corte.date()} | validacion {val_ini.date()} -> "
           f"{val_fin.date()} | prueba {test_ini.date()} -> {test_fin.date()}")
    if corte < val_ini <= val_fin < test_ini <= test_fin:
        chequeo("B1", "Seleccion, validacion y prueba no se traslapan",
                "PASS", det)
    else:
        chequeo("B1", "Seleccion, validacion y prueba no se traslapan",
                "FAIL", det,
                "Algun periodo se traslapa con el siguiente. La eleccion de "
                "variables o de bloques vio datos que despues se usan para "
                "medir. Corrige los periodos en CONFIG de la etapa 01.")

    # --- B2: gap suficiente para las ventanas mas largas --------------------
    max_ventana = max(max(cfg["lags"]), max(cfg["rolling_windows"]))
    gap = (val_ini - corte).days
    if gap >= max_ventana:
        chequeo("B2", "Gap seleccion->validacion cubre la ventana mas larga",
                "PASS", f"gap {gap}d >= ventana maxima {max_ventana}d")
    else:
        chequeo("B2", "Gap seleccion->validacion cubre la ventana mas larga",
                "WARN", f"gap {gap}d < ventana maxima {max_ventana}d",
                "Las primeras observaciones de validacion usan ventanas que "
                "tocan el periodo de seleccion. Es informacion PASADA "
                "(legitimo para pronostico), pero conviene declararlo.")

    # --- B3: tamaño del periodo de prueba -----------------------------------
    n_dev = len(X.loc[:val_fin])
    n_test = len(X.loc[test_ini:test_fin])
    frac = n_test / (n_dev + n_test)
    if 0.15 <= frac <= 0.40:
        chequeo("B3", "Proporcion desarrollo/prueba razonable", "PASS",
                f"desarrollo {n_dev} d ({1-frac:.0%}), prueba {n_test} d "
                f"({frac:.0%})")
    else:
        chequeo("B3", "Proporcion desarrollo/prueba razonable", "WARN",
                f"prueba = {frac:.0%} del total",
                "Fuera del rango habitual 15-40%.")

    # --- B4: las etapas 02 y 03 evaluan SOLO sobre validacion ---------------
    problemas, detalles = [], []
    for modulo, nombre_cfg in [("02_evaluacion_bloques", "EVAL"),
                               ("03_bloques_candidatos", "EVAL3")]:
        try:
            ev = getattr(import_module(modulo), nombre_cfg)
        except Exception as e:
            problemas.append(f"{modulo}: no se pudo importar ({e})")
            continue
        e_ini = pd.Timestamp(ev["eval_start"])
        e_fin = pd.Timestamp(ev["eval_end"])
        detalles.append(f"{modulo}: {e_ini.date()} -> {e_fin.date()}")
        if e_fin >= test_ini:
            problemas.append(f"{modulo} evalua hasta {e_fin.date()}, dentro "
                             f"de la prueba")
        if e_ini <= corte:
            problemas.append(f"{modulo} empieza {e_ini.date()}, dentro del "
                             f"periodo de seleccion")
    if problemas:
        chequeo("B4", "Etapas 02/03 evaluan solo sobre validacion", "FAIL",
                "\n".join(problemas + detalles),
                "La eleccion de bloques con Diebold-Mariano no puede usar la "
                "prueba ni el periodo de seleccion.")
    else:
        chequeo("B4", "Etapas 02/03 evaluan solo sobre validacion", "PASS",
                "\n".join(detalles))

    # --- B5: el modelo final de los notebooks salio de validacion -----------
    ruta = Path(cfg["out_dir"]) / "modelo_final.json"
    if not ruta.exists():
        chequeo("B5", "modelo_final.json elegido sin tocar la prueba", "WARN",
                f"no existe {ruta.name}",
                "Corre 03_bloques_candidatos.py: los notebooks 04/05 leen "
                "las features de ese archivo.")
    else:
        info = json.loads(ruta.read_text(encoding="utf-8"))
        v_fin = pd.Timestamp(info["ventana_validacion"][1])
        det = (f"modelo {info['modelo']} con {len(info['features'])} features,"
               f" validacion {info['ventana_validacion'][0]} -> "
               f"{info['ventana_validacion'][1]}")
        if v_fin >= test_ini:
            chequeo("B5", "modelo_final.json elegido sin tocar la prueba",
                    "FAIL", det,
                    "El modelo final se eligio con datos de prueba. Vuelve a "
                    "correr 03 con la ventana de validacion.")
        else:
            chequeo("B5", "modelo_final.json elegido sin tocar la prueba",
                    "PASS", det)


# ==============================================================================
# C. CONSTRUCCION -- ¿las ventanas moviles usan shift(1)?
# ==============================================================================

def auditar_construccion(df, X, y, cfg):
    seccion("C. CONSTRUCCION — ¿las ventanas moviles se calcularon con shift(1)?")

    # --- C1: prueba empirica de las medias moviles del target ---------------
    # Si log_precio_ma30 usara el dia t (sin shift), su correlacion con y(t)
    # seria mayor que la de la version correcta. Se reconstruyen ambas y se
    # compara cual coincide con la columna del panel.
    col = "log_precio_ma30"
    if col in X.columns:
        correcta = y.shift(1).rolling(30, min_periods=15).mean()
        con_fuga = y.rolling(30, min_periods=15).mean()

        d = pd.concat([X[col].rename("real"),
                       correcta.rename("ok"),
                       con_fuga.rename("fuga")], axis=1).dropna()
        dif_ok = float((d["real"] - d["ok"]).abs().max())
        dif_fuga = float((d["real"] - d["fuga"]).abs().max())

        if dif_ok < 1e-9:
            chequeo("C1", "Medias moviles del target usan shift(1)", "PASS",
                    f"{col} coincide exactamente con la version shift(1) "
                    f"(dif max {dif_ok:.2e})")
        elif dif_fuga < 1e-9:
            chequeo("C1", "Medias moviles del target usan shift(1)", "FAIL",
                    f"{col} coincide con la version SIN shift",
                    "La media movil incluye el dia que se quiere predecir. "
                    "Corrige construir_features() en 01.")
        else:
            chequeo("C1", "Medias moviles del target usan shift(1)", "WARN",
                    f"no coincide con ninguna version "
                    f"(dif_ok={dif_ok:.2e}, dif_fuga={dif_fuga:.2e})",
                    "Revisa manualmente como se construye esta feature.")
    else:
        chequeo("C1", "Medias moviles del target usan shift(1)", "WARN",
                f"{col} no esta en X, no se pudo verificar")

    # --- C2: los lags realmente desplazan ------------------------------------
    col = "log_precio_lag1"
    if col in X.columns:
        d = pd.concat([X[col].rename("feat"), y.rename("y")], axis=1).dropna()
        # feat(t) debe ser igual a y(t-1)
        esperado = y.shift(1).reindex(d.index)
        dif = float((d["feat"] - esperado).abs().max())
        if dif < 1e-9:
            chequeo("C2", "Los lags del target desplazan correctamente", "PASS",
                    f"{col}(t) == log_precio(t-1) exactamente")
        else:
            chequeo("C2", "Los lags del target desplazan correctamente", "FAIL",
                    f"{col} no coincide con y.shift(1), dif max {dif:.2e}",
                    "El lag no esta desplazando. Fuga directa del target.")

    # --- C3: margen_reserva con rezago interno ------------------------------
    if "margen_reserva" in df.columns and \
       {"capacidad_efectiva", "demanda_regulada"} <= set(df.columns):
        comp = [c for c in ["demanda_regulada", "demanda_no_regulada"]
                if c in df.columns]
        dem = df[comp].sum(axis=1, min_count=1)
        cap = df["capacidad_efectiva"]

        sin_rezago = cap / dem.replace(0, np.nan)
        con_rezago = cap / dem.shift(1).replace(0, np.nan)
        real = df["margen_reserva"]

        d0 = float((real - sin_rezago).abs().max())
        d1 = float((real - con_rezago).abs().max())

        if d1 < 1e-9:
            chequeo("C3", "margen_reserva usa demanda REZAGADA", "PASS",
                    "coincide con capacidad(t) / demanda(t-1)")
        elif d0 < 1e-9:
            chequeo("C3", "margen_reserva usa demanda REZAGADA", "FAIL",
                    "coincide con capacidad(t) / demanda(t) -- SIN rezago",
                    "La demanda es 'Demanda Real' (medida, no pronosticada). "
                    "Sin rezago, el presente predice el presente. "
                    "Corrige construir_derivadas() en 00.")
        else:
            chequeo("C3", "margen_reserva usa demanda REZAGADA", "WARN",
                    f"no coincide con ninguna version "
                    f"(sin_rezago={d0:.2e}, con_rezago={d1:.2e})",
                    "Puede estar construida con otra formula. Revisa a mano.")


# ==============================================================================
# D. COHERENCIA ENTRE ETAPAS
# ==============================================================================

def auditar_coherencia(cfg):
    seccion("D. COHERENCIA — ¿las etapas usan las mismas features y periodos?")

    out = Path(cfg["out_dir"])

    # --- D1: out_dir absoluto ------------------------------------------------
    if out.is_absolute():
        chequeo("D1", "out_dir es ruta absoluta", "PASS", str(out))
    else:
        chequeo("D1", "out_dir es ruta absoluta", "FAIL", str(out),
                "Una ruta relativa depende de la carpeta de la terminal. "
                "Las etapas 02/03 fallan si se invocan desde otro sitio.")

    # --- D2: archivos de salida existen -------------------------------------
    esperados = {
        "features_seleccionadas.csv": "salida de la etapa 01",
        "ranking_completo.csv": "salida de la etapa 01",
        "evaluacion_bloques.csv": "salida de la etapa 02",
        "bloques_candidatos.csv": "salida de la etapa 03",
    }
    faltan = [f for f in esperados if not (out / f).exists()]
    if not faltan:
        chequeo("D2", "Salidas de todas las etapas presentes", "PASS",
                f"{len(esperados)} archivos en {out.name}/")
    else:
        chequeo("D2", "Salidas de todas las etapas presentes", "WARN",
                f"faltan: {faltan}",
                "Corre las etapas en orden 00 -> 01 -> 02 -> 03.")

    # --- D3: la seleccion es mas nueva que el panel -------------------------
    panel = Path(cfg["panel_path"])
    sel = out / "features_seleccionadas.csv"
    if panel.exists() and sel.exists():
        t_panel = panel.stat().st_mtime
        t_sel = sel.stat().st_mtime
        if t_sel >= t_panel:
            chequeo("D3", "La seleccion refleja el panel actual", "PASS",
                    "features_seleccionadas.csv es mas nuevo que panel_d.parquet")
        else:
            dif_h = (t_panel - t_sel) / 3600
            chequeo("D3", "La seleccion refleja el panel actual", "FAIL",
                    f"el panel es {dif_h:.1f} h mas nuevo que la seleccion",
                    "Cambiaste el panel despues de seleccionar. Vuelve a correr "
                    "01 antes de 02/03, o estaras evaluando features viejas.")
    else:
        chequeo("D3", "La seleccion refleja el panel actual", "WARN",
                "falta el panel o la seleccion, no se pudo comparar")

    # --- D4: prefijos de bloque ambiguos ------------------------------------
    # Un solape no es malo por si mismo: la asignacion se resuelve en orden,
    # asi que si el bloque MAS ESPECIFICO va primero, el mas general no lo
    # roba. Solo se marca cuando el orden esta al reves.
    bloques = cfg.get("blocks", {})
    nombres = list(bloques)
    peligrosos, resueltos = [], []
    for i, b1 in enumerate(nombres):
        for j, b2 in enumerate(nombres):
            if i >= j:
                continue
            for p1 in bloques[b1]:
                for p2 in bloques[b2]:
                    if p1 == p2:
                        peligrosos.append(f"{b1} y {b2} comparten '{p1}'")
                    elif p2.startswith(p1):
                        # b1 (mas general) va ANTES que b2 (mas especifico)
                        peligrosos.append(
                            f"'{p1}' ({b1}) engloba a '{p2}' ({b2}), "
                            f"y {b1} va primero -> {b2} nunca se asigna")
                    elif p1.startswith(p2):
                        # b2 (mas general) va DESPUES: el orden ya protege
                        resueltos.append(f"'{p2}' ({b2}) engloba a '{p1}' "
                                         f"({b1}), pero {b1} va primero: OK")

    if peligrosos:
        chequeo("D4", "Prefijos de bloque sin ambiguedad", "FAIL",
                "\n".join(peligrosos[:5]),
                "Reordena el diccionario: el bloque mas ESPECIFICO debe ir "
                "antes que el mas general.")
    elif resueltos:
        chequeo("D4", "Prefijos de bloque sin ambiguedad", "PASS",
                f"{len(bloques)} bloques; {len(resueltos)} solape(s) "
                f"resuelto(s) por el orden:\n" + "\n".join(resueltos[:3]))
    else:
        chequeo("D4", "Prefijos de bloque sin ambiguedad", "PASS",
                f"{len(bloques)} bloques, prefijos disjuntos")


# ==============================================================================
# E. DATOS -- problemas silenciosos del panel
# ==============================================================================

def auditar_datos(df, cfg):
    seccion("E. DATOS — ¿el panel tiene problemas silenciosos?")

    # --- E1: target presente y con rango plausible --------------------------
    tgt = cfg["target_col"]
    if tgt not in df.columns:
        chequeo("E1", "Target presente", "FAIL", f"falta '{tgt}'",
                "Sin variable objetivo no se puede modelar.")
        return
    s = pd.to_numeric(df[tgt], errors="coerce")
    cob = s.notna().mean()
    det = (f"cobertura {cob:.1%}, rango {s.min():.1f} - {s.max():.1f} COP/kWh")
    if cob > 0.95 and s.min() > 0:
        chequeo("E1", "Target presente y con rango plausible", "PASS", det)
    else:
        chequeo("E1", "Target presente y con rango plausible", "WARN", det,
                "Cobertura baja o valores no positivos (rompen el log).")

    # --- E2: columnas constantes ---------------------------------------------
    num = df.select_dtypes(include=[np.number])
    const = [c for c in num.columns if num[c].nunique(dropna=True) <= 1]
    if const:
        chequeo("E2", "Sin columnas constantes", "WARN", f"{const}",
                "No aportan informacion; ocupan espacio y ensucian el ranking.")
    else:
        chequeo("E2", "Sin columnas constantes", "PASS",
                f"{len(num.columns)} columnas numericas, todas con variacion")

    # --- E3: fechas duplicadas o desordenadas -------------------------------
    dup = int(df.index.duplicated().sum())
    ordenado = df.index.is_monotonic_increasing
    if dup == 0 and ordenado:
        chequeo("E3", "Indice de fechas limpio", "PASS",
                f"{len(df)} filas, sin duplicados, ordenado")
    else:
        chequeo("E3", "Indice de fechas limpio", "FAIL",
                f"duplicados: {dup}, ordenado: {ordenado}",
                "Fechas duplicadas o desordenadas rompen los lags y el "
                "walk-forward de forma silenciosa.")

    # --- E4: series que parecen tendencia pura ------------------------------
    # Una serie casi monotona funciona como proxy del tiempo: el modelo la usa
    # para memorizar el año en vez de aprender una relacion. Fue el caso de
    # precio_escasez (bloque COMBUSTIBLE, DM +4.36).
    tendencia = []
    for c in num.columns:
        v = num[c].dropna()
        if len(v) < 500 or c == tgt:
            continue
        r = abs(np.corrcoef(np.arange(len(v)), v.values)[0, 1])
        if np.isfinite(r) and r > 0.95:
            tendencia.append((c, r))
    if tendencia:
        det = "\n".join(f"{c}: |corr con el tiempo| = {r:.3f}"
                        for c, r in sorted(tendencia, key=lambda x: -x[1])[:8])
        chequeo("E4", "Sin series que sean tendencia pura", "WARN", det,
                "Casi monotonas: el modelo las usa como proxy del año. "
                "Considera diferenciarlas o excluirlas.")
    else:
        chequeo("E4", "Sin series que sean tendencia pura", "PASS",
                "ninguna serie con |corr con el tiempo| > 0.95")

    # --- E5: % de embalses ponderado por capacidad --------------------------
    # El promedio ponderado por capacidad reproduce el % del sistema de XM
    # (corr > 0.999). El promedio simple por embalse no (corr ~ 0.92).
    par = ["volumen_util_pct_emb", "volumen_util_pct"]
    if set(par) <= set(df.columns):
        r = df[par].apply(pd.to_numeric, errors="coerce").corr().iloc[0, 1]
        if np.isfinite(r) and r > 0.99:
            chequeo("E5", "% de volumen por embalse ponderado por capacidad",
                    "PASS", f"corr con el % del sistema = {r:.4f}")
        else:
            chequeo("E5", "% de volumen por embalse ponderado por capacidad",
                    "WARN", f"corr con el % del sistema = {r:.4f}",
                    "Parece un promedio simple por embalse. Revisa PONDERADAS "
                    "en 00_consolidar_panel.py y vuelve a correrlo.")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    cfg = CONFIG
    print("=" * 74)
    print("AUDITORIA DEL PIPELINE")
    print("=" * 74)
    print("Verifica fuga de informacion y coherencia entre etapas.")
    print("NO evalua si el modelo es bueno -- solo si el proceso es valido.")

    try:
        df = _e1.cargar_panel(cfg)
    except Exception as e:
        print(f"\n[FAIL] No se pudo cargar el panel: {e}")
        print(f"       Revisa CONFIG['panel_path'] en 01_seleccion_variables.py")
        return

    print(f"\n[panel]   {df.shape[0]} filas x {df.shape[1]} cols  "
          f"{df.index.min().date()} -> {df.index.max().date()}")

    X, y = _e1.construir_features(df, cfg)
    print(f"[feats]   {X.shape[1]} features construidas")

    # Replica la exclusion de DESPACHO que hace main() en la etapa 01, para
    # auditar el MISMO conjunto de features que realmente entra al modelo.
    if cfg.get("excluir_despacho", True):
        pref = cfg["blocks"].get("DESPACHO", [])
        cols_desp = [c for c in X.columns if any(c.startswith(p) for p in pref)]
        if cols_desp:
            X = X.drop(columns=cols_desp)
            print(f"[fuga]    {len(cols_desp)} features de DESPACHO excluidas "
                  f"(igual que en la etapa 01)")
    print(f"[audita]  {X.shape[1]} features efectivas")

    auditar_temporalidad(X, cfg)
    auditar_correlacion_target(X, y, cfg)
    auditar_oni(df)
    auditar_split(X, cfg)
    auditar_construccion(df, X, y, cfg)
    auditar_coherencia(cfg)
    auditar_datos(df, cfg)

    # ---- veredicto ----------------------------------------------------------
    seccion("VEREDICTO")
    res = pd.DataFrame(RESULTADOS)
    n_fail = int((res["estado"] == "FAIL").sum())
    n_warn = int((res["estado"] == "WARN").sum())
    n_pass = int((res["estado"] == "PASS").sum())

    print(f"  {n_pass} PASS   {n_warn} WARN   {n_fail} FAIL\n")

    if n_fail:
        print("  HAY FUGA O INCONSISTENCIA REAL. Corrige antes de seguir:")
        for _, r in res[res["estado"] == "FAIL"].iterrows():
            print(f"    {r['codigo']}  {r['titulo']}")
        print("\n  Mientras estos fallen, las metricas no son defendibles.")
    elif n_warn:
        print("  Sin fugas detectadas. Revisa los WARN a mano:")
        for _, r in res[res["estado"] == "WARN"].iterrows():
            print(f"    {r['codigo']}  {r['titulo']}")
        print("\n  Un WARN no invalida el pipeline, pero conviene poder "
              "explicarlo si preguntan.")
    else:
        print("  Todos los chequeos pasaron. El pipeline no tiene fuga "
              "temporal\n  detectable ni inconsistencias entre etapas.")

    out = Path(cfg["out_dir"]); out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "auditoria.csv", index=False)
    print(f"\n[salida]  {out / 'auditoria.csv'}")

    print("\nLIMITES DE ESTA AUDITORIA")
    print("  - Verifica lo mecanico (fechas, shifts, rutas, prefijos).")
    print("  - NO puede saber si una serie de XM es pronosticada o medida")
    print("    mas alla de la lista SERIES_MEDIDAS de este archivo: si")
    print("    agregas variables nuevas, agregalas ahi tambien.")
    print("  - NO juzga si el modelo predice bien. Eso es la etapa 02/03.")


if __name__ == "__main__":
    main()
