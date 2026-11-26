# Pronóstico del precio de bolsa de energía en Colombia

Tesis de pregrado, Universidad de los Andes. Pronostica el precio de bolsa del mercado
eléctrico colombiano para la próxima semana, hora por hora, con datos públicos de XM
(API y SIMEM), NOAA, ERA5, el IDEAM y la TRM.

Los tres modelos de la tesis están terminados y probados: SARIMAX, XGBoost y una red LSTM
codificador-decodificador. El informe final está en `informe/Imforme 1.docx` y en PDF, y los
scripts que lo escriben, en `informe/codigo/`.

## El diseño en breve

- Se pronostican 168 precios: las 24 horas de los próximos 7 días. El precio sale con dos
  días de atraso, así que esos días son h = 3 a h = 9 desde el último precio conocido.
- Los tres modelos pronostican el cambio `log P(t+h, H) − log P(t, H)` frente al último precio
  conocido a la misma hora.
- SARIMAX: 24 modelos, uno por hora, sobre la serie diaria de cada hora, (1,1,2)(0,0,2) con
  s = 7 y el festivo como única variable explicativa (`5_modelo_sarimax.ipynb`, en R).
- XGBoost: 7 modelos directos, uno por día, con las 24 horas juntas y `hora` como columna. Las
  columnas salen de la selección congelada del paso 2d (`4_modelo_xgboost.ipynb`).
- LSTM: una sola red codificador-decodificador para las 24 horas y los 7 días, con el precio, el
  calendario, el despacho programado de hoy y el estado hidrológico, cada dato desde el día en que
  se publica (paso 2h, `6c_lstm_seleccion.ipynb` y `6d_lstm_busqueda_y_test.ipynb`).
- Todo se decide con datos hasta 2022: selección en 2015-2019 y validación en 2020-2022. El test
  se hace una sola vez en 2023-2025 y en 2026 hasta el 6 de octubre, reentrenando cada mes, en las
  mismas filas para los tres.
- Un modelo funciona si baja el RMSE en logaritmo al menos 5% frente al mejor de los dos
  ingenuos (repetir el último día o la última semana) y Diebold-Mariano da p < 0,05.

## Resultados

En h = 3 a 9, RMSE en logaritmo y, entre paréntesis, la mejora frente al ingenuo del día, que
fue el mejor de los dos ingenuos en todos los casos
(`resultados/modelo_lstm_bloques/comparacion_criterio.csv`):

| | 2023-2025 | 2026, hasta el 6 de octubre |
|---|---|---|
| Ingenuo del día | 0,502 | 0,435 |
| SARIMAX | 0,470 (6,4%) | 0,411 (5,6%) |
| XGBoost | 0,443 (11,6%) | 0,392 (10,0%) |
| LSTM | 0,427 (14,9%) | 0,350 (19,7%) |

Los tres cumplen el criterio en los dos periodos y en los cuatro bloques de horizontes. Entre
modelos (Diebold-Mariano, `comparacion_pares.csv`), la LSTM le gana a SARIMAX en los dos periodos
(p = 0,007 y 0,011); frente a XGBoost la diferencia solo es significativa en 2026 (p = 0,107 en
2023-2025 y 0,033 en 2026). XGBoost le gana a SARIMAX en 2023-2025 (p = 0,011), pero no en 2026
(p = 0,062).

- La ventaja de la LSTM está en el nivel del día, donde aporta el despacho programado de hoy: su
  error de nivel en 2023-2025 es 0,347, contra 0,385 de XGBoost y 0,415 del ingenuo. En la forma
  de las horas dentro del día el mejor es XGBoost (0,221, contra 0,249 de la LSTM).
- Por años cambia: en 2024 XGBoost y la LSTM no se distinguen del ingenuo (p = 0,100 y 0,098) y
  solo SARIMAX cumple el criterio.
- En pesos las mejoras son menores: en 2023-2025, 7,1% la LSTM, 5,8% SARIMAX y 3,7% XGBoost, y
  solo la de SARIMAX es significativa. Los tres quedan, en promedio, por debajo del precio real.
- En la semana del 9 al 15 de octubre de 2026, pronosticada antes de que salieran sus precios,
  XGBoost tuvo el menor error (RMSE en logaritmo de 0,201), seguido de SARIMAX (0,218), el
  ingenuo del día (0,234) y la LSTM (0,252).

## Cómo se llegó a una semana

El alcance empezó en 30 días y se redujo a una semana después de ver el test de XGBoost. El criterio
original, fijado antes de abrirlo, pedía bajar el RMSE en log al menos 5% frente al mejor
de dos ingenuos, con Diebold-Mariano p < 0,05. Mejora por bloque de horizontes:

| Bloque | 2023-2025 | 2026, hasta el 6 de octubre |
|---|---|---|
| h = 3 | 17,9%, funciona | 19,5%, funciona |
| h = 3 a 7 | 12,5%, funciona | 11,6%, funciona |
| h = 8 a 14 | 10,7%, funciona | 6,4%, no significativo |
| h = 15 a 30 | 13,1%, funciona | -7,2%, pierde contra el ingenuo |

XGBoost supera al ingenuo con claridad hasta h = 7; más allá, el resultado depende del
periodo. Su ventaja está sobre todo en los errores grandes: en 2023-2025 la mediana del
error fue peor que la del ingenuo en h = 3, 7 y 14.

SARIMAX y la LSTM se diseñaron después, con el alcance de una semana ya fijado.

## Lo que limita el pronóstico

Gran parte del límite está en la información. Dándole a XGBoost la demanda y la hidrología futuras
reales, h = 7 sube de 8,3% a 11,1%; con las ofertas futuras reales, a 39,5%. Esas ofertas se
publican unos 10 días tarde, y pronosticarlas tampoco ayuda. Ver `diagnosticos/RESULTADOS.md`.

Pero parte del límite estaba en cómo se alineaban los datos. Los paneles 2c y 2d paran todo en el
día del último precio, y el precio sale con 2 o 3 días de atraso. El despacho programado de hoy, que
resume las ofertas, sale la víspera, y esos paneles lo usaban con días de atraso que no tiene. En
2020-2022, un modelo de prueba con precio y calendario mejora 9,6% en h = 3; con el despacho de hoy
alineado a su publicación, 27,7%. Ver el panel de la LSTM en `docs/PANEL_HORARIO.md`. La LSTM
usa esa alineación, y es en el nivel del día donde le gana a XGBoost.

## Por dónde empezar

1. `informe/Imforme 1.pdf`: el informe final, con la metodología y los resultados de los tres
   modelos.
2. `resumen_modelos_hallazgos/`: seis notebooks cortos, que corren en menos de un minuto, con los
   datos, cada modelo y la comparación.
3. `resultados/modelo_xgboost/RESULTADOS.md`, `resultados/modelo_sarimax/RESULTADOS.md` y
   `resultados/modelo_lstm_bloques/RESULTADOS.md`: qué salió en cada modelo y cómo leerlo.
4. `4_modelo_xgboost.ipynb`, `5_modelo_sarimax.ipynb`, `6c_lstm_seleccion.ipynb` y
   `6d_lstm_busqueda_y_test.ipynb`: el flujo completo de cada modelo, etapa por etapa.
   `7_resultados.ipynb` presenta XGBoost y SARIMAX con el formato del paper de Salazar-Peña et
   al. (2025), en COP/kWh.
5. `docs/PANEL_HORARIO.md` y `docs/LSTM_DISENO.md`: de dónde sale cada columna, cuándo se conoce,
   cómo se eligió y cómo se diseñó la LSTM.
6. `3_datos_y_caracteristicas.ipynb`: el precio, su transformación y las características.
7. `diagnosticos/RESULTADOS.md`: dónde falla el modelo y qué información le falta.
8. `docs/REFERENCIAS.md`: de qué guía, curso o artículo sale cada parte del código.

## Cómo está organizado

```
1_descargar.py               paso 1: baja los datos de XM, SIMEM, NOAA, ERA5 y la TRM a datos/
1b_ideam.py                  paso 1b: lee los boletines PDF del IDEAM (opcional)
2_construir_panel.py         paso 2: panel diario
2b_panel_horario.py          paso 2b: panel horario (24 filas por día)
2c_caracteristicas_horarias.py  paso 2c: variables base por hora, calendario y objetivos
2d_seleccion_variables.py    paso 2d: elige, por horizonte, las columnas del 2c que van al modelo
2e_panel_lstm.py             paso 2e: panel de la LSTM, con cada dato alineado al día en que se publica
2f_datos_lstm.py             paso 2f: qué datos de ese panel recibe la LSTM
2g_termica_programada.py     paso 2g: parte térmica del despacho de hoy (exploratorio)
2h_panel_lstm_bloques.py     paso 2h: panel de la LSTM nueva, con las variables por bloques
features.py                  características: las del panel diario y el catálogo de rezagos,
                             medias móviles y variabilidad del panel horario
3_datos_y_caracteristicas.ipynb  análisis de la serie, transformación logarítmica y características
4_modelo_xgboost.ipynb       modelo XGBoost a una semana, hora por hora: ajuste, test y semana final
5_modelo_sarimax.ipynb       modelo SARIMAX en R: órdenes, exógenas, test y comparación con XGBoost
6_modelo_lstm.ipynb          primera LSTM, como en Salazar-Peña et al. (2025), sobre el panel del
                             paso 2f (exploratoria; no es la del informe)
6b_modelo_lstm_v2.ipynb      segunda LSTM: codificador y decodificador, MSE, tres años de validación
                             y ensamble de 5 redes (exploratoria, nunca se corrió)
6c_lstm_seleccion.ipynb      LSTM de la tesis, primera parte: selección de bloques de variables,
                             prueba de control y búsqueda corta de control (corrió en Colab)
6d_lstm_busqueda_y_test.ipynb  LSTM de la tesis, segunda parte: búsqueda bayesiana de
                             hiperparámetros, validación, test, semana final y comparación con
                             XGBoost y SARIMAX (corrió en Colab)
6e_pronosticos_para_comparar.py  junta los pronósticos del test de XGBoost y SARIMAX en un solo
                             archivo, para la comparación del 6d
7_resultados.ipynb           XGBoost y SARIMAX con el formato de Salazar-Peña et al. (2025)

paneles/                     lo que producen los pasos 2 a 2h
resultados/modelo_xgboost/   configuración congelada, pronósticos del test, gráficas y RESULTADOS.md
resultados/modelo_sarimax/   lo mismo para SARIMAX
resultados/modelo_lstm_bloques/  lo mismo para la LSTM de la tesis, y la comparación de los tres
                             modelos en las mismas filas
resultados/comparacion/      métricas y gráficas de XGBoost y SARIMAX con el formato del paper
informe/                     informe final (Word y PDF), informe de avance, figuras y, en codigo/,
                             los scripts que escriben y revisan el informe
resumen_modelos_hallazgos/   seis notebooks cortos con los datos, los tres modelos y la comparación
.github/                     consulta horaria temporal a XM para saber a qué hora sale el despacho
                             de mañana (guarda en la rama sondeo-xm)
diagnosticos/                dónde falla el modelo, qué información le falta y si sirve pronosticar ofertas
docs/
  DOCUMENTACION.md           explicación completa del panel diario y sus decisiones
  PANEL_HORARIO.md           los paneles horarios: columnas, cuándo se conoce cada cosa, selección
  LSTM_DISENO.md             plan de la LSTM de la tesis: bloques de variables, selección,
                             arquitectura e hiperparámetros, fijado antes de construirla, y lo
                             que salió en cada etapa
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
python 2e_panel_lstm.py             # paneles/panel_lstm.csv.gz (medio minuto)
python 2f_datos_lstm.py             # paneles/panel_lstm_modelo.csv.gz (unos 12 minutos)
python 2g_termica_programada.py     # le agrega frac_termica_prog a ese panel (unos 3 minutos)
python 2h_panel_lstm_bloques.py     # paneles/panel_lstm_bloques.csv.gz (medio minuto)
python 6e_pronosticos_para_comparar.py  # resultados/comparacion/pronosticos_xgboost_sarimax.csv.gz
```

Con `ATRASO_PRECIO=3` antes de los pasos 2e y 2f se arma la versión con el precio a 3 días
(archivos `_atraso3`).

Después se abren los notebooks. Solo leen `paneles/`, así que los pasos 1 a 2d no hacen
falta para verlos ni para correrlos. Los dos paneles que arma el paso 2b no están en git:
hacen falta solo para repetir los pasos 2c y 2d.

`4_modelo_xgboost.ipynb` reutiliza lo guardado en `resultados/modelo_xgboost/`, así que
correrlo no repite el ajuste ni el test. Las etapas de prueba se activan con una variable
de entorno: `CORRER_TEST=1` (2023-2025), `CORRER_2026=1` (2026 y alcance final) y
`CORRER_FINAL=1` (semana final, del 9 al 15 de octubre de 2026).

`5_modelo_sarimax.ipynb` corre en R, con el kernel de Jupyter para R:

```r
install.packages(c("forecast", "IRkernel", "jsonlite", "R.utils", "data.table", "ggplot2"))
```

También reutiliza lo guardado, y sus etapas de prueba se activan con `CORRER_TEST=1` y
`CORRER_FINAL=1`.

El listado de plantas (`datos/Listado_Recursos_Generacion.xlsx`) se baja a mano de
PARATEC, en la página de XM.

**En Colab** se sube `3_datos_y_caracteristicas.ipynb` y, al correr la primera celda, ella
pide `features.py` y `panel_diario.csv`; para la parte horaria,
`panel_caracteristicas.csv.gz` y `panel_caracteristicas_variables.csv`.

Para la primera LSTM, la exploratoria, se suben `6_modelo_lstm.ipynb` y
`paneles/panel_lstm_modelo.csv.gz`, con GPU.
El test y la semana final solo corren con `CORRER_TEST = True`; la semana final necesita
además `resultados/modelo_xgboost/precio_real_final.csv`.

Para la LSTM de la tesis se suben `6c_lstm_seleccion.ipynb`, `paneles/panel_lstm_bloques.csv.gz` y
`paneles/panel_lstm_bloques_variables.csv`, con GPU. Con `PRUEBA_RAPIDA = True` corre en pocos
minutos con una red mínima, para revisar que no falle nada antes de la corrida larga. Después va
`6d_lstm_busqueda_y_test.ipynb`, con la misma carpeta de salida; su test solo corre con
`CORRER_TEST = True`. Para que al final compare la LSTM con XGBoost y SARIMAX hay que subir también
`resultados/comparacion/pronosticos_xgboost_sarimax.csv.gz`.

## Estado

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
  10 o 20 columnas por horizonte: 57 distintas, de 32 variables, en los nueve horizontes que
  tuvieron selección (h = 1 a 7, 14 y 30), y 37, de 18 variables, en h = 3 a 7.
- **XGBoost:** ajuste y test terminados, con la configuración congelada en
  `resultados/modelo_xgboost/configuracion_final.json`. La semana final, del 9 al 15 de
  octubre de 2026, ya corrió como demostración: RMSE en logaritmo 14,1% menor que el del ingenuo del
  día, en una semana más fácil que lo normal.
- **SARIMAX:** terminado, con test y semana final. Ver `resultados/modelo_sarimax/RESULTADOS.md`.
- **Panel de la LSTM (pasos 2e y 2f):** cada dato entra el día en que se publica. Con 2015-2022
  y el precio a 2 días quedan 5 variables, además del precio y el calendario: el costo marginal
  programado de hoy, frente al último precio y solo, la disponibilidad declarada de hoy, la
  distancia al precio de escasez y la presión hídrica. Con el precio a 3 días quedan las tres del
  despacho de hoy. Están en `paneles/panel_lstm_modelo.csv.gz` y `panel_lstm_modelo_atraso3.csv.gz`.
  Son las variables de la primera LSTM; la de la tesis usa el panel por bloques del paso 2h, con
  136 variables, de las que quedaron los bloques 1 a 4: el precio, el calendario, 4 variables del
  despacho de hoy y 5 del estado hidrológico.
- **LSTM:** terminada, con test y semana final. Ver `resultados/modelo_lstm_bloques/RESULTADOS.md`
  y `docs/LSTM_DISENO.md`.
- **Lo que queda abierto:** los tres modelos no reciben la misma información, porque la LSTM usa
  cada dato desde el día en que se publica y XGBoost y SARIMAX no. Darles la misma regla, probar el
  bloque 7 de la LSTM (los pronósticos de XGBoost y SARIMAX como entrada) y medir el valor del
  pronóstico en una decisión concreta quedan como trabajo futuro (sección 5.2 del informe).

Los modelos diarios anteriores (un día puntual y siete días probabilístico) están en el
commit `a200127` y descritos en `docs/DOCUMENTACION.md`, secciones 6 y 7.
