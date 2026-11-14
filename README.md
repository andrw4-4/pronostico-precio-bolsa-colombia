# Pronóstico del precio de bolsa de energía en Colombia

Tesis de pregrado, Universidad de los Andes. Pronostica el precio de bolsa del mercado
eléctrico colombiano para la próxima semana, hora por hora, con datos públicos de XM
(API y SIMEM), NOAA, ERA5, el IDEAM y la TRM.

Hay dos modelos terminados, XGBoost y SARIMAX. Falta una LSTM, con el mismo diseño; su
panel ya está armado (pasos 2e y 2f).

## El modelo en breve

- Se pronostican 168 precios: las 24 horas de los próximos 7 días. El precio sale con dos
  días de atraso, así que esos días son h = 3 a h = 9 desde el último precio conocido.
- Son 7 modelos directos, uno por día. Cada uno predice `log P(t+h, H) − log P(t, H)`,
  con las 24 horas juntas y `hora` como columna.
- Las columnas salen de la selección congelada del paso 2d.
- Los hiperparámetros se ajustan con walk-forward en 2020-2022. El test se hace en
  2023-2025 y en 2026, reentrenando cada mes.

En esa semana le gana al mejor ingenuo en los dos periodos: 11,6% en 2023-2025 y 10,0% en
2026, con Diebold-Mariano p ≤ 0,001.

El alcance empezó en 30 días y se redujo a una semana después de ver el test. El criterio
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

## Comparación con SARIMAX

SARIMAX son 24 modelos, uno por hora, con la serie diaria y ciclo semanal. Se eligió solo con
criterios estadísticos y datos hasta 2022: quedó un orden, (1,1,2)(0,0,2) con s = 7, sin
exógenas. En h = 3 a 9, en las mismas filas que XGBoost:

| | 2023-2025 | 2026 |
|---|---|---|
| Ingenuo del día, RMSE | 0,502 | 0,435 |
| SARIMAX, RMSE y mejora | 0,470 (6,4%) | 0,411 (5,6%) |
| XGBoost, RMSE y mejora | 0,443 (11,6%) | 0,392 (10,0%) |
| XGBoost contra SARIMAX, Diebold-Mariano p | 0,011 | 0,062 |

Los dos cumplen el criterio. XGBoost es mejor, aunque la diferencia solo es significativa en
2023-2025. Ninguno anticipa bien el nivel del día, y en el día típico quedan casi iguales.

Gran parte del límite está en la información. Dándole a XGBoost la demanda y la hidrología futuras
reales, h = 7 sube de 8,3% a 11,1%; con las ofertas futuras reales, a 39,5%. Esas ofertas se
publican unos 10 días tarde, y pronosticarlas tampoco ayuda. Ver `diagnosticos/RESULTADOS.md`.

Pero parte del límite estaba en cómo se alineaban los datos. Los paneles 2c y 2d paran todo en el
día del último precio, y el precio sale con 2 o 3 días de atraso. El despacho programado de hoy, que
resume las ofertas, sale la víspera, y esos paneles lo usaban con días de atraso que no tiene. En
2020-2022, un modelo de prueba con precio y calendario mejora 9,6% en h = 3; con el despacho de hoy
alineado a su publicación, 27,7%. Ver el panel de la LSTM en `docs/PANEL_HORARIO.md`.

## Por dónde empezar

1. `resultados/modelo_xgboost/RESULTADOS.md` y `resultados/modelo_sarimax/RESULTADOS.md`: qué
   salió y cómo leerlo.
2. `4_modelo_xgboost.ipynb` y `5_modelo_sarimax.ipynb`: todo el flujo, etapa por etapa, ya
   ejecutado. `7_resultados.ipynb` presenta los resultados de todos con el formato del paper
   de Salazar-Peña et al. (2025), en COP/kWh.
3. `docs/PANEL_HORARIO.md`: de dónde sale cada columna, cuándo se conoce y cómo se eligió.
4. `3_datos_y_caracteristicas.ipynb`: el precio, su transformación y las características.
5. `diagnosticos/RESULTADOS.md`: dónde falla el modelo y qué información le falta.
6. `docs/REFERENCIAS.md`: de qué guía, curso o artículo sale cada parte del código.

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
6_modelo_lstm.ipynb          LSTM como en Salazar-Peña et al. (2025), sobre el panel del paso 2f
6b_modelo_lstm_v2.ipynb      segunda LSTM: codificador y decodificador, MSE, tres años de validación
                             y ensamble de 5 redes (exploratoria: se diseñó después de ver la primera)
6c_lstm_seleccion.ipynb      LSTM nueva, primera parte: selección de bloques de variables, prueba
                             de control y búsqueda corta de control (para Colab, sin correr)
6d_lstm_busqueda_y_test.ipynb  LSTM nueva, segunda parte: búsqueda bayesiana de hiperparámetros,
                             validación, test, semana final y comparación con XGBoost y SARIMAX
                             (para Colab, sin correr)
6e_pronosticos_para_comparar.py  junta los pronósticos del test de XGBoost y SARIMAX en un solo
                             archivo, para la comparación del 6d
7_resultados.ipynb           resultados de todos los modelos con el formato de Salazar-Peña et al. (2025)

paneles/                     lo que producen los pasos 2 a 2f
resultados/modelo_xgboost/   configuración congelada, pronósticos del test, gráficas y RESULTADOS.md
resultados/modelo_sarimax/   lo mismo para SARIMAX
resultados/comparacion/      métricas y gráficas con el formato del paper, y RESULTADOS.md
diagnosticos/                dónde falla el modelo, qué información le falta y si sirve pronosticar ofertas
docs/
  DOCUMENTACION.md           explicación completa del panel diario y sus decisiones
  PANEL_HORARIO.md           los paneles horarios: columnas, cuándo se conoce cada cosa, selección
  LSTM_DISENO.md             plan de la LSTM nueva: bloques de variables, selección, arquitectura
                             e hiperparámetros, fijado antes de construirla
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

Para la LSTM se suben `6_modelo_lstm.ipynb` y `paneles/panel_lstm_modelo.csv.gz`, con GPU.
El test y la semana final solo corren con `CORRER_TEST = True`; la semana final necesita
además `resultados/modelo_xgboost/precio_real_final.csv`.

Para la LSTM nueva se suben `6c_lstm_seleccion.ipynb`, `paneles/panel_lstm_bloques.csv.gz` y
`paneles/panel_lstm_bloques_variables.csv`, con GPU. Con `PRUEBA_RAPIDA = True` corre en pocos
minutos con una red mínima, para revisar que no falle nada antes de la corrida larga. Después va
`6d_lstm_busqueda_y_test.ipynb`, con la misma carpeta de salida; su test solo corre con
`CORRER_TEST = True`. Para que al final compare la LSTM con XGBoost y SARIMAX hay que subir también
`resultados/comparacion/pronosticos_xgboost_sarimax.csv.gz`.

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
  `resultados/modelo_xgboost/configuracion_final.json`. La semana final, del 9 al 15 de
  octubre de 2026, ya corrió como demostración: RMSE 14,1% menor que el ingenuo del día y
  MAPE de 15,9%, en una semana más fácil que lo normal.
- **SARIMAX:** terminado, con test y semana final. Ver `resultados/modelo_sarimax/RESULTADOS.md`.
- **Panel de la LSTM (pasos 2e y 2f):** cada dato entra el día en que se publica. Con 2015-2022
  y el precio a 2 días quedan 5 variables, además del precio y el calendario: el costo marginal
  programado de hoy, frente al último precio y solo, la disponibilidad declarada de hoy, la
  distancia al precio de escasez y la presión hídrica. Con el precio a 3 días quedan las tres del
  despacho de hoy. Están en `paneles/panel_lstm_modelo.csv.gz` y `panel_lstm_modelo_atraso3.csv.gz`.
- **Lo que sigue:** la LSTM, a una semana, con las mismas filas, ingenuos y criterio. Con este
  panel ya no usa la misma información que XGBoost y SARIMAX; para comparar en igualdad, esos dos
  tendrían que usar la misma regla.

Los modelos diarios anteriores (un día puntual y siete días probabilístico) están en el
commit `a200127` y descritos en `docs/DOCUMENTACION.md`, secciones 6 y 7.
