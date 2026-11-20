"""Escribe la sección 1.2 Objetivos del informe final.
Uso: python s1_2_objetivos.py ENTRADA.docx SALIDA.docx"""
import sys

from docx_final import Docx, par, runs

ENTRADA, SALIDA = sys.argv[1], sys.argv[2]


def item(n, texto, ultimo=False):
    """Objetivo numerado con sangría francesa: el número queda afuera y el texto alineado."""
    espacio = '<w:spacing w:after="160"/>' if ultimo else ""
    return ('<w:p><w:pPr><w:pStyle w:val="Prrafodelista"/>'
            f'{espacio}<w:ind w:left="567" w:hanging="567"/></w:pPr>'
            f'<w:r><w:t>{n}.</w:t></w:r><w:r><w:tab/></w:r>{runs(texto)}</w:p>')


SUBTITULO = '<w:keepNext/><w:spacing w:after="60"/>'

xml = (
    par("*Objetivo general*", ppr=SUBTITULO)
    + par("Evaluar si modelos estadísticos y de aprendizaje automático pronostican el precio de bolsa horario de "
          "Colombia a una semana con menor error que un pronóstico ingenuo, usando solo la información publicada "
          "en el momento de pronosticar.")
    + par("*Objetivos específicos*", ppr=SUBTITULO)
    + item(1, "Construir una base de datos diaria y horaria con el precio de bolsa y sus posibles determinantes "
              "(hidrología, demanda, combustibles, clima y calendario), en la que cada dato entra en la fecha en "
              "que se publica.")
    + item(2, "Estimar tres modelos de pronóstico, SARIMAX, XGBoost y una red LSTM, con un mismo diseño: los 168 "
              "precios de la semana, de tres a nueve días después del último dato conocido, seleccionados con "
              "datos hasta 2022 y evaluados una sola vez entre 2023 y 2026.")
    + item(3, "Comparar el desempeño de los tres modelos con el de dos pronósticos ingenuos y el de tesis "
              "anteriores, tanto en error de pronóstico como en valor para la toma de decisiones.", ultimo=True)
)

d = Docx(ENTRADA)
d.reemplazar_vacio_tras("1.2 Objetivos", xml)
d.guardar(SALIDA)
print("ok", SALIDA)
