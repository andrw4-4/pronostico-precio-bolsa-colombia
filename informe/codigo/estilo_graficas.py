"""Paleta y estilo comunes para todas las figuras del informe final.

Cada modelo tiene siempre el mismo color: el azul, el naranja y el verde agua significan siempre LSTM,
XGBoost y SARIMAX. Lo demás usa solo rojo y verde (EXTRA), tintes claros de esos colores y, para bandas y
elementos de fondo, un tono neutro suave; los ingenuos van en gris. Los tres colores de los modelos
se validaron sobre fondo blanco: se distinguen con visión normal (ΔE OKLab mínimo 24) y con
daltonismo (9,2). El verde de SARIMAX tiene contraste de 2,8:1 con el blanco, así que toda
gráfica con SARIMAX lleva leyenda o etiqueta junto a la línea."""
import matplotlib as mpl

COLORES = {"Precio real": "#0b0b0b", "LSTM": "#2a78d6", "XGBoost": "#eb6834", "SARIMAX": "#1baf7a",
           "Ingenuo del día": "#898781", "Ingenuo semanal": "#52514e"}
LINEAS = {"Precio real": dict(lw=2.4), "LSTM": dict(lw=1.8), "XGBoost": dict(lw=1.8), "SARIMAX": dict(lw=1.8),
          "Ingenuo del día": dict(lw=1.4, ls="--"), "Ingenuo semanal": dict(lw=1.4, ls=":")}
# Colores para lo que no es un modelo. Pocos y sencillos: cada gráfica usa el color de su modelo, o rojo y
# verde si no tiene modelo, y lo secundario va en un tinte claro del mismo color (claro()). Sin violeta ni
# amarillo, salvo que el contexto lo pida. Junto al naranja de XGBoost no va el rojo, porque se confunden; ahí
# lo secundario es naranja claro o negro.
# Cuando se comparan modelos, los ingenuos siguen en gris, porque el rojo se confunde con el naranja.
EXTRA = {"rojo": "#e34948", "verde": "#008300"}
BANDA = "#eeede8"  # bandas de confianza y fondos, un neutro suave


def claro(color, a):
    """El color mezclado con blanco: a = 1 es el color, a = 0 es blanco."""
    c = [int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(255 - a * (255 - x)):02x}" for x in c)


def oscuro(color, a):
    """El color mezclado con negro: a = 1 es el color, a = 0 es negro."""
    c = [int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(a * x):02x}" for x in c)


# Tintes claros de cada modelo, para rellenos de diagramas
TINTE = {"LSTM": "#dceafb", "XGBoost": "#fbe1d6", "SARIMAX": "#d3f1e6"}
# Los periodos del diseño (sección 3.3), siempre con los mismos colores
PERIODOS = {"Ajuste": EXTRA["verde"], "Validación": "#6db36d", "Prueba": EXTRA["rojo"],
            "Prueba 2026": oscuro(EXTRA["rojo"], 0.7)}
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGENTE = ["#e34948", "#f0efec", "#2a78d6"]  # negativo, cero, positivo
GRISES = {"oscuro": "#52514e", "medio": "#898781", "claro": "#c3c2b7", "muy claro": "#e1e0d9"}
TINTA, TENUE, CUADRICULA = "#2b2b2b", "#77766f", "#e6e5e0"


def aplicar():
    mpl.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
        "text.color": TINTA, "axes.labelcolor": TINTA, "axes.edgecolor": TENUE,
        "xtick.color": TENUE, "ytick.color": TENUE,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "grid.color": CUADRICULA, "grid.linewidth": 0.8,
        "legend.frameon": False,
    })
