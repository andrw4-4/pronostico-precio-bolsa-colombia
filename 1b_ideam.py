"""
Paso 1b (opcional): los boletines del IDEAM.

Es una descarga más, como el paso 1, pero va aparte porque la fuente es otra
(PDF del IDEAM, no una API), tarda mucho más y el proyecto corre sin ella: si
falta el CSV, el paso 2 deja esas columnas vacías.

El IDEAM publica dos cosas que el panel no tiene y que vienen de una fuente
distinta a XM:

    predicción climática   mensual; pronóstico de lluvia por región para los
                           tres meses siguientes. Es lo único que mira hacia
                           adelante en todo el proyecto.
    informe técnico diario alertas del día por niveles bajos de los ríos,
                           crecientes, incendios y deslizamientos.

Los dos tienen archivo desde 2011, así que cubren todas las ventanas.

No hay API: toca recorrer el listado de cada repositorio para sacar los
enlaces y las fechas de publicación, bajar los PDF y leerlos. Los PDF no se
guardan porque entre los dos pesan cerca de 20 GB; se bajan, se leen y se
descartan. Lo que queda son dos CSV con las variables ya extraídas.

Como los boletines son texto libre y el formato cambió varias veces en quince
años, lo que se extrae es deliberadamente grueso: categorías y niveles, no
milímetros. Lo que no se logra leer queda vacío y el panel lo rellena.

Uso:
    python 1b_ideam.py prediccion     # unos 130 PDF, 400 MB de tráfico
    python 1b_ideam.py alertas        # unos 4.000 PDF, varias horas

Las alertas solo se pueden leer hasta 2019: desde 2020 los informes marcan el
nivel de alerta con íconos en vez de palabras y el texto no lo trae. Esos días
quedan vacíos (no en 0) y la columna leido vale 0. Si datos/ideam_alertas.csv
existe, el paso 2 lo usa; datos/ideam_alertas_PARCIAL_NO_USAR.csv es una
descarga anterior que no se usa.
"""

import io
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
CARPETA = BASE / "datos"
INICIO = pd.Timestamp("2014-01-01")   # un año antes del panel, para tener rezagos

SITIO = "https://www.ideam.gov.co"
REPOSITORIOS = {
    "prediccion": "/sala-de-prensa/boletines/Boletín-de-predicción-climática",
    "alertas": ("/sala-de-prensa/boletines/Informe-Técnico-Diario-de-Condiciones-"
                "Hidrometeorológicas,-Alertas-y-Pronósticos-(ITD)"),
}
SALIDAS = {"prediccion": CARPETA / "ideam_prediccion.csv",
           "alertas": CARPETA / "ideam_alertas.csv"}

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
         "diciembre": 12}

CABECERA = {"User-Agent": "Mozilla/5.0 (tesis precio de bolsa; uso académico)"}


def sin_tildes(texto):
    """Compara sin depender de tildes ni mayúsculas, que varían entre boletines."""
    plano = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in plano if unicodedata.category(c) != "Mn")


def pedir(url, intentos=4, espera=5):
    for i in range(intentos):
        try:
            r = requests.get(url, headers=CABECERA, timeout=180)
            if r.status_code == 200:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(espera * (i + 1))
    return None


# ===========================================================================
# Listado de cada repositorio
# ===========================================================================
#
# Cada página del listado trae diez archivos, cada uno con su enlace y su fecha
# de publicación. Esa fecha es la que importa: es el día en que el boletín
# estuvo disponible, así que marca a partir de cuándo se puede usar.

FILA = re.compile(
    r'href="(/file-download/download/public/\d+)"[^>]*>\s*([^<]+?\.(?:pdf|zip))\s*<'
    r'.*?(\d{1,2})\s+(\w+),\s+(\d{4})',
    re.DOTALL | re.IGNORECASE)


def listar(repositorio):
    """Recorre el listado completo y devuelve archivo, enlace y fecha."""
    filas, pagina, vistos = [], 0, set()
    while True:
        html = pedir(f"{SITIO}{REPOSITORIOS[repositorio]}?page={pagina}")
        if html is None:
            break
        encontrados = FILA.findall(html.decode("utf-8", "replace"))
        nuevos = [f for f in encontrados if f[0] not in vistos]
        if not nuevos:
            break
        for enlace, archivo, dia, mes, anio in nuevos:
            vistos.add(enlace)
            m = MESES.get(sin_tildes(mes))
            if m is None:
                continue
            filas.append({"archivo": archivo.strip(), "url": SITIO + enlace,
                          "fecha": pd.Timestamp(int(anio), m, int(dia))})
        pagina += 1
        if pagina > 400:            # tope de seguridad
            break
    return pd.DataFrame(filas).drop_duplicates("url")


def texto_de_pdf(contenido):
    """Texto en modo layout: conserva las columnas, que es como se lee la página."""
    try:
        lector = PdfReader(io.BytesIO(contenido))
        return "\n".join((p.extract_text(extraction_mode="layout") or "")
                         for p in lector.pages)
    except Exception:
        return ""


# ===========================================================================
# 1. Predicción climática mensual
# ===========================================================================
#
# El boletín dice, en prosa, qué categoría de lluvia se espera en cada región:
#
#   "La categoría por debajo de lo normal se proyecta en amplias extensiones
#    de las regiones Caribe y Andina, con probabilidades superiores al 70%"
#
# Se parte el texto en oraciones, se mira si cada una habla de "por debajo" o
# de "por encima", y se anota la región que nombra. Así no importa en qué
# página ni con qué diseño esté: lo que se busca es la frase.

REGIONES = {
    "andina": ["andina"],
    "caribe": ["caribe"],
    "pacifica": ["pacifica", "pacifico", "choco"],
    "orinoquia": ["orinoquia", "orinoquía"],
    "amazonia": ["amazonia", "amazonica"],
}
BAJO = "por debajo de lo normal"
ALTO = "por encima de lo normal"


def leer_prediccion(contenido):
    """Categoría esperada de lluvia por región: -1 por debajo, +1 por encima."""
    plano = re.sub(r"\s+", " ", sin_tildes(texto_de_pdf(contenido)))
    oraciones = re.split(r"(?<=[.;])\s+", plano)

    fila = {f"pred_lluvia_{r}": pd.NA for r in REGIONES}
    for oracion in oraciones:
        tiene_bajo, tiene_alto = BAJO in oracion, ALTO in oracion
        if tiene_bajo == tiene_alto:      # ninguna de las dos, o las dos: ambigua
            continue
        signo = -1 if tiene_bajo else 1
        for region, nombres in REGIONES.items():
            if any(n in oracion for n in nombres):
                clave = f"pred_lluvia_{region}"
                # la primera frase que la nombra manda; el resto suele ser detalle
                if pd.isna(fila[clave]):
                    fila[clave] = signo

    # Resumen que no depende de que las regiones se nombren bien: cuántas veces
    # el boletín habla de déficit frente a cuántas habla de exceso.
    n_bajo, n_alto = plano.count(BAJO), plano.count(ALTO)
    fila["pred_deficit"] = (n_bajo - n_alto) / max(1, n_bajo + n_alto)

    # La probabilidad más alta que se menciona da una idea de qué tan seguro está.
    probs = [int(p) for p in re.findall(r"(\d{2})\s*%", plano) if 30 <= int(p) <= 100]
    fila["pred_prob_max"] = max(probs) if probs else pd.NA

    # Fase del ENOS tal como la describe el propio boletín. "El Niño" aparece
    # también en nombres de entidades (el CIIFEN, por ejemplo), así que se mira
    # cuál de las dos fases domina y si el texto insiste en la neutralidad.
    n_nino, n_nina = plano.count("el nino"), plano.count("la nina")
    neutral = plano.count("neutral")
    if neutral >= 2 and abs(n_nino - n_nina) <= 2:
        fila["pred_enos"] = 0
    else:
        fila["pred_enos"] = 1 if n_nino > n_nina else -1 if n_nina > n_nino else 0
    return fila


# ===========================================================================
# 2. Alertas del informe técnico diario
# ===========================================================================
#
# La página de alertas tiene los niveles en una columna y las viñetas al lado:
#
#   ALERTA        Por alta posibilidad de incendios ... región Caribe.
#      ROJA       Por deslizamientos de tierra ... Antioquia, Boyacá.
#   ALERTA        Por niveles bajos en la cuenca baja del Magdalena y Cauca.
#  NARANJA        Por crecientes súbitas en ríos y quebradas ...
#
# La etiqueta del color va al lado de su bloque, no encima, así que el orden de
# lectura no dice a cuál pertenece cada viñeta: "ROJA" puede quedar a la altura
# de la segunda o la tercera. Lo que sí lo dice es la altura en la página, de
# modo que se leen las coordenadas y cada viñeta se asigna al color que tenga
# más cerca verticalmente.

NIVELES = {"roja": 3, "naranja": 2, "amarilla": 1}
TIPOS = {
    "niveles_bajos": ["niveles bajos", "nivel bajo", "descenso de niveles"],
    "crecientes": ["crecientes subitas", "creciente subita", "desbordamiento"],
    "incendios": ["incendios de la cobertura"],
    "deslizamientos": ["deslizamientos"],
}


def renglones_con_altura(pagina):
    """Renglones de una página con su altura, juntando los trozos de cada línea."""
    trozos = []

    def visitante(texto, cm, tm, fuente, tam):
        if texto.strip():
            trozos.append((round(tm[5], 1), tm[4], texto))

    try:
        # Fuente: documentación de pypdf, extracción de texto con visitor_text
        pagina.extract_text(visitor_text=visitante)
    except Exception:
        return []

    por_altura = {}
    for y, x, t in trozos:
        por_altura.setdefault(y, []).append((x, t))
    renglones = [(y, re.sub(r"\s+", " ", "".join(t for _, t in sorted(v))).strip())
                 for y, v in por_altura.items()]
    return sorted(renglones, key=lambda r: -r[0])      # de arriba hacia abajo


def leer_alertas(contenido):
    """
    Nivel más alto de alerta vigente por tipo (0 si la página de alertas está y
    ese tipo no aparece).

    Si no se encuentra la página de alertas, todo queda vacío, no en 0: no se
    sabe si hubo alerta. Pasa desde 2020, cuando el nivel viene en íconos y el
    texto del PDF no lo trae. La columna leido dice si se encontró la página
    (1) o no (0).
    """
    vacia = {**{f"alerta_{t}": pd.NA for t in TIPOS}, "lluvia_max_municipio": pd.NA, "leido": 0}
    fila = {f"alerta_{t}": 0 for t in TIPOS}
    try:
        lector = PdfReader(io.BytesIO(contenido))
    except Exception:
        return vacia

    lluvia = pd.NA
    encontrada = False
    for pagina in lector.pages:
        renglones = [(y, sin_tildes(t)) for y, t in renglones_con_altura(pagina)]
        # La frase se parte en varios renglones, así que se busca sobre el texto
        # de la página con los saltos de línea aplanados.
        plano = re.sub(r"\s+", " ", " ".join(t for _, t in renglones))

        # La etiqueta son dos palabras: "ALERTA" encima del color. El par queda
        # centrado frente a su bloque, así que el punto medio es la referencia.
        alturas_alerta = [y for y, t in renglones if t == "alerta"]
        etiquetas = []
        for y, t in renglones:
            for nombre, valor in NIVELES.items():
                if re.fullmatch(rf"(alerta\s+)?{nombre}", t):
                    encima = [a for a in alturas_alerta if a > y]
                    centro = (min(encima) + y) / 2 if encima else y
                    etiquetas.append((centro, valor))
        if not etiquetas:
            continue      # esta página no es la de alertas
        encontrada = True

        # En la misma página va el bloque de lluvias, que cierra diciendo cuánto
        # llovió en el municipio más lluvioso: "... con 83.0 mm". Si la frase no
        # sale, se toma el mayor valor plausible: en un día un municipio no pasa
        # de unos cientos de milímetros, y en la página hay otras cifras en mm.
        m = re.search(r"\bcon\s+(\d+(?:\.\d+)?)\s*mm", plano)
        if m:
            lluvia = float(m.group(1))
        else:
            mm = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*mm", plano)]
            mm = [v for v in mm if v <= 500]
            if mm:
                lluvia = max(mm)

        inicios = [i for i, (_, t) in enumerate(renglones)
                   if t.lstrip("-• ").startswith("por ")]
        for n, i in enumerate(inicios):
            fin = inicios[n + 1] if n + 1 < len(inicios) else len(renglones)
            vineta = " ".join(t for _, t in renglones[i:fin])
            y = renglones[i][0]
            nivel = min(etiquetas, key=lambda e: abs(e[0] - y))[1]
            for tipo, claves in TIPOS.items():
                if any(c in vineta for c in claves):
                    fila[f"alerta_{tipo}"] = max(fila[f"alerta_{tipo}"], nivel)

    if not encontrada:
        return vacia
    # El bloque de lluvias dice cuánto llovió en el municipio más lluvioso.
    fila["lluvia_max_municipio"] = lluvia
    fila["leido"] = 1
    return fila


# ===========================================================================
# Descarga y actualización
# ===========================================================================

def fecha_de_archivo(nombre, fecha_listado):
    """
    En los ZIP mensuales cada PDF trae su fecha en el nombre
    (4_IDA_ABRIL_10_2016.pdf). Si no se entiende, se usa la del listado.
    """
    plano = sin_tildes(nombre)
    m = re.search(r"(" + "|".join(MESES) + r")[_\s-]+(\d{1,2})[_\s-]+(\d{4})", plano)
    if m:
        try:
            return pd.Timestamp(int(m.group(3)), MESES[m.group(1)], int(m.group(2)))
        except ValueError:
            pass
    m = re.search(r"(\d{2})(\d{2})(\d{4})", plano)      # ..._01072024.pdf
    if m:
        try:
            return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return fecha_listado


def procesar(contenido, archivo, fecha, leer):
    """Un PDF suelto, o un ZIP mensual con un PDF por día."""
    if archivo.lower().endswith(".zip"):
        filas = []
        try:
            z = zipfile.ZipFile(io.BytesIO(contenido))
        except zipfile.BadZipFile:
            return filas
        for nombre in z.namelist():
            if not nombre.lower().endswith(".pdf"):
                continue
            filas.append({"fecha": fecha_de_archivo(nombre, fecha),
                          **leer(z.read(nombre))})
        return filas
    return [{"fecha": fecha, **leer(contenido)}]


def actualizar(repositorio):
    """Baja lo que falte, lo lee y lo agrega al CSV. Se puede cortar y seguir."""
    leer = leer_prediccion if repositorio == "prediccion" else leer_alertas
    salida = SALIDAS[repositorio]
    CARPETA.mkdir(parents=True, exist_ok=True)

    hechos = set()
    if salida.exists():
        previo = pd.read_csv(salida, parse_dates=["fecha"])
        hechos = set(previo["origen"].dropna()) if "origen" in previo else set()
        if repositorio == "alertas":
            releer = origenes_por_releer(previo)
            if releer:
                print(f"[alertas] {len(releer)} archivos leídos con la versión anterior "
                      "del lector se vuelven a leer", flush=True)
            hechos -= releer
    else:
        previo = pd.DataFrame()

    print(f"[{repositorio}] leyendo el listado del IDEAM...", flush=True)
    catalogo = listar(repositorio)
    catalogo = catalogo[catalogo["fecha"] >= INICIO].sort_values("fecha")
    pendientes = catalogo[~catalogo["url"].isin(hechos)]
    print(f"[{repositorio}] {len(catalogo)} archivos desde {INICIO.date()}, "
          f"{len(pendientes)} por bajar", flush=True)

    nuevas, desde_guardado = [], 0
    for i, fila in enumerate(pendientes.itertuples(), 1):
        contenido = pedir(fila.url)
        if contenido is None:
            print(f"  no se pudo bajar {fila.archivo}", flush=True)
            continue
        extraidas = procesar(contenido, fila.archivo, fila.fecha, leer)
        for f in extraidas:
            f["origen"] = fila.url
        nuevas.extend(extraidas)
        desde_guardado += 1
        if desde_guardado >= 10 or i == len(pendientes):
            guardar(previo, nuevas, salida)
            previo = pd.read_csv(salida, parse_dates=["fecha"])
            nuevas, desde_guardado = [], 0
            print(f"  {i}/{len(pendientes)}  {fila.fecha.date()}  "
                  f"({len(previo)} filas)", flush=True)
    print(f"[{repositorio}] listo: {salida}", flush=True)


def origenes_por_releer(previo):
    """
    Archivos de alertas que hay que volver a leer. La versión anterior del
    lector guardaba 0 en todas las alertas cuando no encontraba la página, así
    que una fila sin la columna leido, con las alertas en 0 y sin lluvia, pudo
    no haberse leído. Se vuelven a leer una vez: con el lector nuevo quedan
    marcadas y no se repiten.
    """
    alertas = [f"alerta_{t}" for t in TIPOS]
    if "origen" not in previo or not set(alertas) <= set(previo.columns):
        return set()
    sin_marca = previo["leido"].isna() if "leido" in previo else pd.Series(True, index=previo.index)
    en_cero = (previo[alertas].fillna(0) == 0).all(axis=1)
    sin_lluvia = previo["lluvia_max_municipio"].isna()
    return set(previo.loc[sin_marca & en_cero & sin_lluvia, "origen"].dropna())


def guardar(previo, nuevas, salida):
    if not nuevas:
        return
    todo = pd.concat([previo, pd.DataFrame(nuevas)], ignore_index=True)
    todo = (todo.dropna(subset=["fecha"]).sort_values("fecha")
                .drop_duplicates("fecha", keep="last"))
    todo.to_csv(salida, index=False)


if __name__ == "__main__":
    cuales = sys.argv[1:] or ["prediccion", "alertas"]
    for c in cuales:
        actualizar(c)
