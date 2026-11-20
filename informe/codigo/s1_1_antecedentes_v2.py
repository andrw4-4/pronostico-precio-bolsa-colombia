"""Cambia el párrafo de antecedentes de la 1.1 por la versión de tono más suave que eligió Andrés.
Uso: python s1_1_antecedentes_v2.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]

NUEVO = (
    "En la Universidad de los Andes hay trabajos previos sobre el pronóstico del precio de bolsa. Cárdenas Paredes "
    "(2005) usó modelos autorregresivos y lógica difusa; Cárdenas Cárdenas (2021) comparó redes neuronales "
    "autorregresivas con modelos ARIMA para el precio promedio diario de la semana siguiente, y González Pérez y "
    "Urbano Buriticá (2022) compararon SARIMAX, Prophet y redes LSTM para el precio horario del día siguiente. Este "
    "proyecto parte de esos trabajos y agrega dos prácticas que la literatura recomienda al evaluar pronósticos del "
    "precio de la electricidad (Lago et al., 2021): comparar cada modelo con un pronóstico de referencia sencillo, "
    "como repetir el último precio conocido, y probar si la diferencia es estadísticamente significativa. Además, "
    "cada dato de entrada se usa solo desde la fecha en que se publica, como ocurriría al pronosticar en la práctica. "
    "La referencia sencilla es exigente: en 2022, repetir el precio de la misma hora del día anterior tuvo un error "
    "porcentual absoluto medio (MAPE) cercano a 11%. La sección 4.3 compara en detalle los resultados de este "
    "trabajo con los de esas tesis."
)

d = Docx(ENTRADA)
d.reemplazar_parrafo("En la Universidad de los Andes hay trabajos previos", NUEVO)
d.guardar(SALIDA)
print("ok", SALIDA)
