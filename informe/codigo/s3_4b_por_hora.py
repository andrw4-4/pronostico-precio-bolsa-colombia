"""Agrega a la sección 3.4 por qué SARIMAX tiene un modelo por cada hora del día.
Uso: python s3_4b_por_hora.py ENTRADA.docx SALIDA.docx"""
import re
import sys

from docx_final import Docx

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]
sin_formato = lambda t: re.sub(r"\*+", "", t)

PRIMERA = ("En este trabajo hay un modelo por cada hora del día: 24 modelos, cada uno sobre la serie diaria del "
           "logaritmo del precio de su hora, con *s* = 7 por el ciclo semanal de la sección 3.2.")
NUEVA = (" Separar las horas convierte el precio horario, que tiene un ciclo diario y otro semanal, en 24 series "
         "diarias con un solo ciclo, el semanal, que SARIMAX puede representar con su único periodo estacional. Además, "
         "los generadores ofertan una vez al día para las 24 horas, así que la información nueva llega por días "
         "(Weron, 2014; Hyndman y Athanasopoulos, 2021).")
RESTO = (" Todos llevan como variable explicativa un indicador de si el día es festivo, que se conoce con anticipación "
         "para cualquier día pronosticado. El día de la semana no se incluye, porque lo recoge la parte estacional. Cada "
         "modelo pronostica de forma recursiva desde el día *t* (sección 3.3).")

d = Docx(ENTRADA)
textos = [d.texto(p) for _, _, p in d.parrafos()]
assert sin_formato(PRIMERA + RESTO) in textos, "el párrafo cambió en Word o la frase ya está"
d.reemplazar_parrafo("En este trabajo hay un modelo por cada hora", PRIMERA + NUEVA + RESTO)
d.guardar(SALIDA)
print("ok", SALIDA)
