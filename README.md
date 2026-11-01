# Pronóstico del precio de bolsa de energía en Colombia

Tesis de pregrado, Universidad de los Andes. Pronostica el precio de bolsa del mercado
eléctrico colombiano hora por hora, hasta 30 días adelante, con datos públicos de XM
(API y SIMEM), NOAA, ERA5, el IDEAM y la TRM.

El modelo terminado es XGBoost. SARIMAX y una LSTM vienen después, con el mismo diseño.

## El modelo en breve

- Desde un día de corte t se pronostican 720 precios: las 24 horas de los 30 días
  siguientes. Por el atraso de dos días del precio, el primer pronóstico real es h = 3.
- Son 30 modelos directos, uno por cada h. Cada uno predice
  `log P(t+h, H) − log P(t, H)`, con las 24 horas juntas y `hora` como columna.
- Las columnas salen de la selección congelada del paso 2d.
- Los hiperparámetros se ajustan con walk-forward en 2020-2022. El test se hace en
  2023-2025 y en 2026, reentrenando cada mes.

El criterio se fijó antes de abrir el test: el RMSE en log debe bajar al menos 5% frente
al mejor de dos ingenuos, con Diebold-Mariano p < 0,05. Mejora por bloque de horizontes:

| Bloque | 2023-2025 | 2026, hasta el 6 de octubre |
|---|---|---|
| h = 3 | 17,9%, funciona | 19,5%, funciona |
| h = 3 a 7 | 12,5%, funciona | 11,6%, funciona |
| h = 8 a 14 | 10,7%, funciona | 6,4%, no significativo |
| h = 15 a 30 | 13,1%, funciona | -7,2%, pierde contra el ingenuo |

XGBoost supera al ingenuo con claridad hasta h = 7; más allá, el resultado depende del
periodo. Su ventaja está sobre todo en los errores grandes: en 2023-2025 la mediana del
error fue peor que la del ingenuo en h = 3, 7 y 14.

## Por dónde empezar

1. `resultados/modelo_xgboost/RESULTADOS.md`: qué salió y cómo leerlo.
2. `4_modelo_xgboost.ipynb`: todo el flujo, etapa por etapa, ya ejecutado.
3. `docs/PANEL_HORARIO.md`: de dónde sale cada columna, cuándo se conoce y cómo se eligió.
4. `3_datos_y_caracteristicas.ipynb`: el precio, su transformación y las características.
5. `docs/REFERENCIAS.md`: de qué guía, curso o artículo sale cada parte del código.

## Cómo está organizado

```
1_descargar.py               paso 1: baja los datos de XM, SIMEM, NOAA, ERA5 y la TRM a datos/
1b_ideam.py                  paso 1b: lee los boletines PDF del IDEAM (opcional)
2_construir_panel.py         paso 2: panel diario
2b_panel_horario.py          paso 2b: panel horario (24 filas por día)
2c_caracteristicas_horarias.py  paso 2c: variables base por hora, calendario y objetivos
2d_seleccion_variables.py    paso 2d: elige, por horizonte, las columnas del 2c que van al modelo
features.py                  características: las del panel diario y el catálogo de rezagos,
                             medias móviles y variabilidad del panel horario
3_datos_y_caracteristicas.ipynb  análisis de la serie, transformación logarítmica y características
4_modelo_xgboost.ipynb       modelo XGBoost a 30 días, hora por hora: ajuste, test y mes final

paneles/                     lo que producen los pasos 2 a 2d
resultados/modelo_xgboost/   configuración congelada, pronósticos del test, gráficas y RESULTADOS.md
docs/
  DOCUMENTACION.md           explicación completa del panel diario y sus decisiones
  PANEL_HORARIO.md           los paneles horarios: columnas, cuándo se conoce cada cosa, selección
  REFERENCIAS.md             de qué guía, curso o artículo sale cada parte del código
datos/                       descargas (no está en git; se regenera con el paso 1)
  sondeos/                   consultas a las fuentes: atraso de publicación, catálogo de SIMEM, cobertura
legacy/                      versiones anteriores, experimentos y la app que explora el panel diario
material_de_apoyo/           repos guía, tesis de referencia y documentos personales (no está en git)
```

## Cómo se corre

```bash
pip install pandas numpy scipy scikit-learn statsmodels xgboost matplotlib joblib openpyxl holidays pypdf requests pydataxm
python 1_descargar.py               # la primera vez tarda horas; después solo baja lo nuevo
python 2_construir_panel.py         # paneles/panel_diario.csv
python 2b_panel_horario.py          # paneles/panel_horario.csv.gz y panel_horario_completo.csv.gz
python 2c_caracteristicas_horarias.py  # paneles/panel_caracteristicas.csv.gz (medio minuto)
python 2d_seleccion_variables.py    # paneles/panel_horario_modelo.csv.gz (unos 20 minutos)
```

Después se abren los notebooks. Solo leen `paneles/`, así que los pasos 1 a 2d no hacen
falta para verlos ni para correrlos. Los dos paneles que arma el paso 2b no están en git:
hacen falta solo para repetir los pasos 2c y 2d.

`4_modelo_xgboost.ipynb` reutiliza lo guardado en `resultados/modelo_xgboost/`, así que
correrlo no repite el ajuste ni el test. Las etapas de prueba se activan con una variable
de entorno: `CORRER_TEST=1` (2023-2025), `CORRER_2026=1` (2026) y `CORRER_FINAL=1` (mes
final, del 7 de octubre al 5 de noviembre de 2026).

El listado de plantas (`datos/Listado_Recursos_Generacion.xlsx`) se baja a mano de
PARATEC, en la página de XM.

**En Colab** se sube `3_datos_y_caracteristicas.ipynb` y, al correr la primera celda, ella
pide `features.py` y `panel_diario.csv`; para la parte horaria,
`panel_caracteristicas.csv.gz` y `panel_caracteristicas_variables.csv`.

## Dónde va el proyecto

- **Datos:** completos hasta el 6 de octubre de 2026 (el precio sale con dos días de
  atraso). La cobertura de cada archivo está en `datos/sondeos/auditoria_cobertura.csv`.
- **Panel de características:** 101.712 filas (día, hora) desde marzo de 2015, 9
  horizontes. Guarda 134 variables base (el precio, 44 horarias y 89 diarias) con reglas
  fijas, sin mirar el objetivo; `features.armar_todas()` arma de ellas 1.861 columnas de
  rezagos, medias móviles, tendencia y variabilidad (unos 800 MB).
- **Selección (paso 2d), congelada:** para cada horizonte, limpieza (columnas casi
  constantes, inestables y niveles que siguen al dólar; de cada grupo muy correlacionado
  queda la más correlacionada con el objetivo), orden con XGBoost y SHAP contra columnas
  de ruido (2015-2019), y cuántas con la regla de un error estándar en 2020-2022. Entran
  10 o 20 columnas por horizonte, 57 distintas de 32 variables.
- **XGBoost:** ajuste y test terminados, con la configuración congelada en
  `resultados/modelo_xgboost/configuracion_final.json`. Falta el mes final, que queda
  completo desde el 7 de noviembre de 2026.
- **Lo que sigue:** SARIMAX en R y una LSTM, con las mismas ventanas, ingenuos y criterio.

Los modelos diarios anteriores (un día puntual y siete días probabilístico) están en el
commit `a200127` y descritos en `docs/DOCUMENTACION.md`, secciones 6 y 7.
