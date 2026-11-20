"""Los diagramas del informe, hechos con formas de Word en lugar de imágenes: el mercado de corto plazo (sección 2.1),
el flujo de los datos (3.2), las etapas de cada modelo (3.4, 3.5 y 3.6) y la arquitectura de la LSTM (3.6).
Cada función devuelve el párrafo con el grupo de formas; s_figuras_color.py los pone en el informe.
El contenido es el mismo de las figuras que antes hacían fig_marco_teorico.py, fig_datos.py, fig_sarimax.py,
fig_xgboost.py y fig_lstm.py. Las medidas van en centímetros."""
from estilo_graficas import BANDA, COLORES, EXTRA, TINTE, claro, oscuro
from formas_word import Dibujo, etapas, parrafo


def h(color):
    return color.lstrip("#").upper()


TINTA, TENUE, LINEA = "2B2B2B", "77766F", "C3C2B7"
AZUL, NARANJA, AGUA = h(COLORES["LSTM"]), h(COLORES["XGBoost"]), h(COLORES["SARIMAX"])
ROJO, VERDE, NEUTRO = h(EXTRA["rojo"]), h(EXTRA["verde"]), h(BANDA)


def caja_titulo(d, x, y, w, ht, titulo, texto, relleno, tinta=TINTA, borde=None, tam=8):
    """Caja con un título, una raya debajo y el texto."""
    ps = [parrafo(titulo, 9, tinta, negrita=True, linea=TENUE if tinta == TINTA else "FFFFFF"),
          parrafo(texto, tam, tinta, antes=4)]
    d.caja(x, y, w, ht, ps, relleno, borde=borde, grosor=1.25)


# ----------------------------------------------------------------------------- figura 3: mercado de corto plazo
def mercado():
    """Las tres etapas del mercado (CREG 025 de 1995 y CREG 055 de 1994), en tres columnas."""
    d = Dibujo(15.0, 7.7, 3012)
    # encabezados de las tres etapas y sus separadores
    for x0, x1, titulo, sub in [(0.0, 4.5, "Día anterior", "Programa de despacho"),
                                (4.7, 8.1, "Día de operación", "Operación del sistema"),
                                (8.3, 15.0, "Días siguientes", "Proceso comercial")]:
        d.texto(x0, 0.0, x1 - x0, 0.9, [parrafo(titulo, 10, TINTA, negrita=True),
                                        parrafo(sub, 9, TENUE, antes=1)], ancla="t")
    for x in (4.6, 8.2):
        d.linea([(x, 0.15), (x, 7.6)], color=LINEA, grosor=0.75, guion=True)

    # la operación en verde, cada vez más intenso; el precio en rojo y lo que no lo cambia en neutro
    ant1, ant2 = h(claro(EXTRA["verde"], 0.15)), h(claro(EXTRA["verde"], 0.28))
    ope = h(claro(EXTRA["verde"], 0.42))
    sig1, sig2 = NEUTRO, h(claro(EXTRA["rojo"], 0.22))
    caja_titulo(d, 0.0, 2.6, 1.95, 2.4, "Entradas", "Ofertas de precio y declaración de disponibilidad", ant1)
    caja_titulo(d, 2.3, 1.45, 2.05, 4.7, "Despacho programado",
                "Plantas que atienden la demanda esperada al menor costo, con las restricciones de la red", ant2)
    caja_titulo(d, 5.35, 2.6, 2.05, 2.4, "Despacho real", "Redespachos, generación real y demanda real", ope)
    caja_titulo(d, 8.55, 1.2, 2.55, 5.0, "Despacho ideal",
                "Plantas que atienden la demanda real al menor costo, sin las restricciones de la red y con la "
                "disponibilidad real", sig2)
    caja_titulo(d, 11.95, 1.15, 3.0, 1.85, "Precio de bolsa", "Oferta de la planta marginal del despacho ideal",
                ROJO, tinta="FFFFFF")
    caja_titulo(d, 11.95, 3.3, 3.0, 1.85, "Reconciliaciones", "Diferencias entre la generación real y la ideal", sig1)
    caja_titulo(d, 11.95, 5.45, 3.0, 1.85, "Liquidación", "Compras y ventas en bolsa y contratos", sig1)

    y = 3.8
    d.flecha(1.97, y, 2.28, y, grosor=1.25)
    d.flecha(4.37, y, 5.33, y, grosor=1.25)
    d.flecha(7.42, y, 8.53, y, grosor=1.25)
    for yc in (2.07, 4.22, 6.37):
        d.flecha(11.12, y + (yc - y) * 0.35, 11.93, yc, grosor=1.25)
    return d.xml()


# ----------------------------------------------------------------------------- figura 6: flujo de los datos
def flujo():
    """De la descarga a la comparación (pasos 1 a 2h y notebooks de los modelos). De las variables base del 2c salen
    tres caminos: SARIMAX las toma como candidatas tal cual; XGBoost, con las 1.861 columnas derivadas y la
    selección del 2d; la LSTM, con su propio panel (2e a 2h), en el que cada variable entra desde el día en que se
    publica. Los tres modelos se comparan en las mismas filas (capítulo IV)."""
    hl, g = 1.9, 0.2                                    # alto de cada carril y espacio entre carriles
    H = 3 * hl + 2 * g
    d = Dibujo(15.0, H, 3014)
    panel = h(claro(EXTRA["verde"], 0.25))
    yc = [k * (hl + g) + hl / 2 for k in range(3)]      # centro de cada carril: SARIMAX, XGBoost y LSTM
    x0, x1, x2, x3, x4, x5 = 0.0, 2.55, 5.1, 7.75, 10.65, 12.8
    w0, w1, w2, w3, w4, w5 = 2.2, 2.2, 2.2, 2.6, 1.85, 2.2
    alto = 3.4

    def titulo(t, color=TINTA):
        return parrafo(t, 9, color, negrita=True)

    d.caja(x0, (H - alto) / 2, w0, alto, [titulo("1. Descarga"), parrafo("XM, SIMEM, NOAA, ERA5, IDEAM y TRM", antes=4),
                                         parrafo("72 series de XM y SIMEM", antes=4)], NEUTRO, ancla="ctr")
    d.caja(x1, (H - alto) / 2, w1, alto, [titulo("2 y 2b. Paneles"), parrafo("Diario: 4.300 días", antes=4),
                                         parrafo("Horario: 103.200 filas, 24 por día", antes=4)], panel, ancla="ctr")
    d.caja(x2, 0, w2, H, [titulo("2c. Variables base"),
                          parrafo("134 variables, cada una con una regla fija según su tipo", antes=4)], panel,
           ancla="ctr")
    d.flecha(x0 + w0 + 0.03, H / 2, x1 - 0.03, H / 2, grosor=1.25)
    d.flecha(x1 + w1 + 0.03, H / 2, x2 - 0.03, H / 2, grosor=1.25)

    # SARIMAX toma las variables base sin derivar; XGBoost y la LSTM pasan antes por sus propios pasos
    d.texto(x3, yc[0] - 0.42, w3, 0.34, [parrafo("133 candidatas", 7.5, TENUE)], ancla="b")
    d.caja(x3, yc[1] - hl / 2, w3, hl, [titulo("2d. Selección"),
                                        parrafo("Por horizonte, 10 o 20 de 1.861 columnas derivadas", antes=3)],
           h(TINTE["XGBoost"]), ancla="ctr")
    d.caja(x3, yc[2] - hl / 2, w3, hl, [titulo("2e a 2h. LSTM"),
                                        parrafo("Variables base desde el día en que se publican", antes=3)],
           h(TINTE["LSTM"]), ancla="ctr")
    d.flecha(x2 + w2 + 0.03, yc[0], x4 - 0.03, yc[0], grosor=1.25)
    for y in yc[1:]:
        d.flecha(x2 + w2 + 0.03, y, x3 - 0.03, y, grosor=1.25)
        d.flecha(x3 + w3 + 0.03, y, x4 - 0.03, y, grosor=1.25)

    # los modelos, cada uno en su color, y la comparación en las mismas filas
    for y, nombre, color in zip(yc, ["SARIMAX", "XGBoost", "LSTM"], [AGUA, NARANJA, AZUL]):
        d.caja(x4, y - 0.5, w4, 1.0, [parrafo(nombre, 9, "FFFFFF", negrita=True)], color, ancla="ctr", margen=0.03)
        d.flecha(x4 + w4 + 0.03, y, x5 - 0.03, y, grosor=1.25)
    d.caja(x5, 0, w5, H, [titulo("Comparación"), parrafo("Mismas filas y mismo criterio", antes=4),
                          parrafo("Capítulo IV", antes=4)], "FFFFFF", borde=TINTA, grosor=1.0, ancla="ctr",
           margen=0.08)
    return d.xml()


# ----------------------------------------------------------------------------- figuras 9, 13 y 16: etapas
def etapas_sarimax():
    cajas = [("1. Órdenes", "2015-2019", ["Un modelo por hora", "KPSS: *d* = 1\nOCSB: *D* = 0\nAICc: *p*, *q*, *P* y *Q*",
                                          "12 órdenes distintos en 24 horas"]),
             ("2. Variables", "2015-2019", ["133 candidatas\nLimpieza: 122\nPreblanqueo: 1\nAICc: 1\nPrueba *t*: 1",
                                            "Queda la holgura de la oferta"]),
             ("3. Validación", "2020-2022", ["Un orden común contra un orden por hora y contra la holgura",
                                             "Diebold-Mariano *p* < 0,05"]),
             ("4. Modelo final", "Fijo antes de la prueba", ["(1,1,2)(0,0,2) con *s* = 7 en las 24 horas",
                                                             "Festivo como única variable explicativa",
                                                             "Reestimación mensual"])]
    return etapas(3017, cajas, AGUA, h(TINTE["SARIMAX"]), alto=4.1)


def etapas_xgboost():
    cajas = [("1. Columnas", "2015-2022", ["1.861 candidatas\nLimpieza: 1.290", "SHAP contra ruido: 15 a 117",
                                           "Un error estándar: 10 o 20"]),
             ("2. Búsqueda", "2020, 2021 y 2022", ["30 combinaciones al azar", "Tres pliegues anuales",
                                                   "Pasan las 3 mejores"]),
             ("3. Validación", "2020-2022", ["Reentrenamiento mensual", "La más simple a un error estándar de la mejor"]),
             ("4. Variantes", "2020-2022", ["Pseudo-Huber\nÚltimos 3 años\nCorrección del sesgo",
                                            "Ninguna mejora más de un error estándar"]),
             ("5. Modelo final", "Queda fijo", ["7 modelos directos, *h* = 3 a 9", "*h* = 8 y 9 usan la de *h* = 7",
                                                "Reentrenamiento mensual"])]
    return etapas(3021, cajas, NARANJA, h(TINTE["XGBoost"]), alto=4.1)


def etapas_lstm():
    cajas = [("1. Bloques", "Hasta 2022", ["136 variables, cada una desde el día en que se publica",
                                           "6 bloques según cómo se forma el precio"]),
             ("2. Selección", "2020, 2021 y 2022", ["Hacia adelante, bloque por bloque",
                                                    "Diebold-Mariano en *h* = 3, 6 y 9",
                                                    "Control con todas las variables"]),
             ("3. Búsqueda", "2020, 2021 y 2022", ["Bayesiana, 30 configuraciones con una semilla",
                                                   "Los bloques compiten como un hiperparámetro"]),
             ("4. Tres semillas", "2020-2022", ["9 candidatas", "Gana la de menor RMSE de la semana",
                                                "Ensayo del procedimiento del test"]),
             ("5. Modelo final", "Queda fijo", ["Bloques 1 a 4, una capa de 128 unidades", "4 épocas y 3 semillas",
                                                "Reentrenamiento mensual"])]
    return etapas(3024, cajas, AZUL, h(TINTE["LSTM"]), alto=4.1)


# ----------------------------------------------------------------------------- figura 17: arquitectura de la LSTM
def arquitectura():
    """Codificador y decodificador desplegados en el tiempo (Sutskever et al., 2014), con la configuración final."""
    d = Dibujo(15.5, 6.55, 3025)
    entrada, densa, salida = h(TINTE["LSTM"]), h(claro(COLORES["LSTM"], 0.45)), h(oscuro(COLORES["LSTM"], 0.6))
    calendario = NEUTRO
    wc, we = 1.65, 1.85                         # ancho de las capas y de las entradas
    y_out, y_d24, y_lstm, y_d64, y_in = 1.15, 2.35, 3.5, 4.65, 5.55   # borde de arriba de cada fila
    h_out, h_d, h_lstm, h_in = 0.8, 0.55, 0.75, 0.95

    def capa(x, y, alto, ancho, texto, color, tinta="FFFFFF", tam=8, negrita=False):
        d.caja(x - ancho / 2, y, ancho, alto, [parrafo(texto, tam, tinta, negrita=negrita)], color, ancla="ctr",
               margen=0.04)

    def puntos(x, y, alto):
        d.texto(x - 0.3, y, 0.6, alto, [parrafo("…", 12, TENUE)])

    def flechas_fila(xs, medio, y):
        d.flecha(xs[0] + wc / 2 + 0.03, y, xs[1] - wc / 2 - 0.03, y)
        d.flecha(xs[1] + wc / 2 + 0.03, y, medio - 0.3, y)
        d.flecha(medio + 0.3, y, xs[2] - wc / 2 - 0.03, y)

    # codificador: 28 pasos, se dibujan 3 y los puntos suspensivos
    xs = [0.95, 2.95, 5.65]
    for x, dia in zip(xs, ["*t* − 27", "*t* − 26", "*t*"]):
        capa(x, y_in, h_in, we, f"Día {dia}:\nprecio, variables y calendario", entrada, TINTA, tam=7)
        capa(x, y_d64, h_d, wc, "Densa (64)", densa, TINTA)
        capa(x, y_lstm, h_lstm, wc, "LSTM (128)", AZUL, negrita=True)
        d.flecha(x, y_in - 0.03, x, y_d64 + h_d + 0.03)
        d.flecha(x, y_d64 - 0.03, x, y_lstm + h_lstm + 0.03)
    medio = (xs[1] + xs[2]) / 2
    puntos(medio, y_lstm, h_lstm)
    puntos(medio, y_in, h_in)
    flechas_fila(xs, medio, y_lstm + h_lstm / 2)

    # el estado final pasa al decodificador
    xd = [9.05, 11.05, 14.55]
    yc = y_lstm + h_lstm / 2
    d.flecha(xs[2] + wc / 2 + 0.03, yc, xd[0] - wc / 2 - 0.03, yc, color=TINTA, grosor=1.5)
    d.texto(xs[2] + wc / 2, yc - 0.85, xd[0] - xs[2] - wc, 0.75,
            [parrafo("estado final", 7.5, TINTA), parrafo("(*h*, *c*) del día *t*", 7.5, TINTA)], ancla="b")

    # decodificador: 7 pasos, se dibujan 3 y los puntos suspensivos
    for x, dia in zip(xd, ["*t* + 3", "*t* + 4", "*t* + 9"]):
        capa(x, y_in, h_in, we, f"Calendario\nde {dia}", calendario, TINTA, tam=7)
        capa(x, y_lstm, h_lstm, wc, "LSTM (128)", AZUL, negrita=True)
        capa(x, y_d24, h_d, wc, "Densa (24)", densa, TINTA)
        capa(x, y_out, h_out, we, f"24 horas\nde {dia}", salida, tam=7.5)
        d.flecha(x, y_in - 0.03, x, y_lstm + h_lstm + 0.03)
        d.flecha(x, y_lstm - 0.03, x, y_d24 + h_d + 0.03)
        d.flecha(x, y_d24 - 0.03, x, y_out + h_out + 0.03)
    medio = (xd[1] + xd[2]) / 2
    for y, alto in [(y_lstm, h_lstm), (y_out, h_out), (y_in, h_in)]:
        puntos(medio, y, alto)
    flechas_fila(xd, medio, yc)

    # llaves con el nombre de cada parte
    for x0, x1, texto in [(0.0, 6.6, "Codificador: lee los 28 días hasta *t*"),
                          (8.1, 15.5, "Decodificador: pronostica los 7 días, de *t* + 3 a *t* + 9")]:
        d.linea([(x0, 0.85), (x0, 0.65), (x1, 0.65), (x1, 0.85)], color=TINTA, grosor=0.9)
        d.texto(x0, 0.0, x1 - x0, 0.6, [parrafo(texto, 8.5, TINTA)], ancla="b")
    return d.xml()
