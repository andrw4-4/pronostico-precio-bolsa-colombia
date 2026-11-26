# Resumen de los modelos y hallazgos

Esta carpeta reúne en seis notebooks cómo se limpiaron y organizaron los datos, qué análisis se les
hizo, cómo se implementó cada modelo, sus resultados en el test y lo que se encontró. Se pueden leer
en este orden:

1. [0_datos_limpieza_y_estructura.ipynb](0_datos_limpieza_y_estructura.ipynb): fuentes, cobertura de
   cada serie, tratamiento de los faltantes, panel diario, panel de una fila por día y hora, variables
   base y derivadas, selección de variables y panel de la LSTM.
2. [0b_datos_analisis.ipynb](0b_datos_analisis.ipynb): el precio entre 2015 y 2026, por qué se usa su
   logaritmo, sus ciclos, pruebas de estacionariedad, el tamaño del cambio a una semana, la relación
   con el agua y El Niño, el precio de escasez, el despacho programado y qué grupos de variables
   traen información.
3. [1_sarimax.ipynb](1_sarimax.ipynb): SARIMAX en R, un modelo por hora del día.
4. [2_xgboost.ipynb](2_xgboost.ipynb): XGBoost, un modelo por horizonte.
5. [3_lstm.ipynb](3_lstm.ipynb): LSTM con codificador y decodificador, una sola red para toda la semana.
6. [4_comparacion.ipynb](4_comparacion.ipynb): los tres modelos en las mismas filas.

Ningún notebook vuelve a descargar datos ni a correr el test: leen los paneles y los pronósticos
guardados que están en `datos/`. La descarga y la construcción de los paneles están en los scripts
`1_descargar.py` a `2h_panel_lstm_bloques.py` y en `3_datos_y_caracteristicas.ipynb`, y el flujo
completo de cada modelo, en `4_modelo_xgboost.ipynb`, `5_modelo_sarimax.ipynb`,
`6c_lstm_seleccion.ipynb` y `6d_lstm_busqueda_y_test.ipynb`, todos en la raíz del repositorio.

## Cómo correrlos

La carpeta `datos/` trae copias sin cambios de los archivos del repositorio que usan los notebooks
(unos 60 MB):

- `datos/paneles/`: el panel diario, el panel horario con el precio y el calendario, el panel por
  bloques de la LSTM y las tablas que describen sus variables, la selección de XGBoost y la prueba de
  grupos de la LSTM.
- `datos/sondeos/`: la revisión de cobertura de cada serie descargada y el atraso con el que se
  publica cada una.
- `datos/resultados/`: lo que guardó cada modelo, es decir, las decisiones de cada etapa, los
  pronósticos del test y el pronóstico de la semana del 9 al 15 de octubre de 2026 con su precio real.

Los datos crudos de XM y de las demás fuentes no están aquí; los dos primeros notebooks trabajan con
los paneles ya construidos.

Los notebooks se abren desde esta carpeta, en Jupyter o en VS Code, y cada uno corre en menos de un
minuto.

`1_sarimax.ipynb` usa el kernel de R. Los paquetes se instalan desde R con:

```r
install.packages(c("forecast", "data.table", "ggplot2", "jsonlite", "IRkernel"))
IRkernel::installspec()
```

Los otros cinco usan Python 3:

```bash
pip install jupyter pandas numpy scipy statsmodels matplotlib xgboost keras torch
```

`2_xgboost.ipynb` entrena un modelo de ejemplo con datos hasta 2022. `3_lstm.ipynb` usa Keras con
PyTorch por debajo (el notebook lo fija con `KERAS_BACKEND`) solo para armar la red y mostrar su
arquitectura; no entrena nada.

Versiones con las que se corrieron: R 4.6.1 (forecast 9.0.2, data.table 1.18.6.1, ggplot2 4.0.3) y
Python 3.13 (pandas 2.3.3, numpy 2.5.1, scipy 1.16.3, statsmodels 0.14.6, matplotlib 3.11.1, xgboost
3.4.1, keras 3.15.1 y torch 2.13.0).

## Diseño común

- Con el último precio conocido, el del día t, se pronostica la semana siguiente: los horizontes h = 3
  a 9, con sus 24 horas (168 precios). El precio se publica con dos días de atraso y por eso la semana
  empieza en h = 3.
- Los tres modelos pronostican el cambio en logaritmo frente al último precio conocido a la misma hora.
- Validación en 2020-2022. Test en 2023-2025 y en 2026 hasta el 6 de octubre, corrido una sola vez y
  reentrenando el primer día de cada mes.
- Un modelo funciona si su RMSE en logaritmo es al menos 5% menor que el del mejor ingenuo y la prueba
  de Diebold-Mariano contra ese ingenuo da p < 0,05.

## Criterio de la tesis en la semana completa

Mejora del RMSE en logaritmo frente al ingenuo del día, que repite el último precio conocido:

| Modelo | 2023-2025 | 2026 |
|---|---|---|
| SARIMAX | 6,4% | 5,6% |
| XGBoost | 11,6% | 10,0% |
| LSTM | 14,9% | 19,7% |

Los tres cumplen el criterio en los dos periodos.

## Resultados con el formato de Salazar-Peña et al. (2025)

Los notebooks también presentan los resultados como en Salazar-Peña et al. (2025): MAE, RMSE, nRMSE,
MBE y MAPE por horizonte con intervalo de 95%, el skill score frente al ingenuo del día, el MAPE por
hora del día, el mejor pronóstico en cada horizonte y hora, y semanas de ejemplo con la correlación de
Pearson entre el pronóstico y el precio real. Las métricas se calculan en COP/kWh, con el error igual
al pronóstico menos el precio real, y el skill score es la mejora del RMSE en pesos. En la semana
completa:

| Periodo | Modelo | MAE | RMSE | nRMSE (%) | MBE | MAPE (%) | Skill score (%) |
|---|---|---|---|---|---|---|---|
| 2023-2025 | SARIMAX | 148,8 | 242,1 | 49,3 | -15,3 | 39,0 | 5,8 |
| | XGBoost | 148,6 | 247,5 | 50,4 | -46,4 | 36,2 | 3,7 |
| | LSTM | 138,9 | 238,9 | 48,6 | -33,1 | 34,1 | 7,1 |
| | Ingenuo del día | 150,1 | 257,1 | 52,3 | 1,3 | 40,1 | |
| 2026 | SARIMAX | 122,9 | 176,5 | 36,2 | -29,2 | 30,4 | 6,4 |
| | XGBoost | 122,5 | 175,7 | 36,0 | -38,0 | 29,5 | 6,8 |
| | LSTM | 114,5 | 172,0 | 35,2 | -30,6 | 25,6 | 8,8 |
| | Ingenuo del día | 127,1 | 188,5 | 38,6 | -8,3 | 32,4 | |

MAE, RMSE y MBE en COP/kWh.

## Hallazgos principales

1. La LSTM tiene la mayor mejora, pero frente a XGBoost la diferencia solo es significativa en 2026
   (p = 0,033); en 2023-2025 no lo es (p = 0,107). La LSTM le gana a SARIMAX en los dos periodos, y
   XGBoost solo en 2023-2025.
2. Lo que más aporta a la LSTM es el despacho programado del día del pronóstico, que se publica antes
   que el precio. Con él la red mejora el nivel del día, que era lo que XGBoost y SARIMAX no lograban.
3. XGBoost sigue siendo el mejor en la forma del día y en el pico de la noche. Su ventaja viene de los
   días con cambios grandes: en la mediana del error, el ingenuo del día le gana.
4. SARIMAX aprovecha sobre todo el ciclo semanal del precio. Ninguna variable exógena mejoró su
   pronóstico, y sus intervalos de 80% cubren el precio real solo entre 71% y 75% de las veces.
5. Los resultados cambian entre años. En 2024 XGBoost y la LSTM no se distinguen del ingenuo y SARIMAX
   sí; en 2023 SARIMAX no llega al 5%.
6. A más de una semana XGBoost deja de funcionar en 2026. Por eso el alcance de la tesis es una semana.
7. En pesos el orden se mantiene en el MAE y el MAPE, pero las ventajas en el RMSE son menores que en
   logaritmo (skill score entre 3,7% y 8,8%). Los tres modelos se quedan cortos en promedio por la
   vuelta de logaritmos a pesos (Duan, 1983). Corregir ese sesgo con el estimador de Duan se probó
   después y no bajó el RMSE en pesos (sección 4.1 del informe).
8. La ventaja de la LSTM y XGBoost está en los primeros días de la semana (skill score de 20% y 13% en
   h = 3 en 2023-2025). SARIMAX casi no baja el MAE del ingenuo, pero sí los errores grandes, y desde
   h = 7 es el de menor RMSE en pesos.

## Referencias

- Duan, N. (1983). Smearing estimate: a nonparametric retransformation method. *Journal of the
  American Statistical Association*, 78(383), 605-610.
- Salazar-Peña, N., Palma-Vergara, A., Montes-Vera, M., Vargas-Torres, M. A., Hernández Vanegas, R.,
  Amador, M., Rojas, B., Salinas, A., Velasco, A., Tabares, A. y González-Mancera, A. (2025).
  Intra-day solar and power forecast for optimization of intraday market participation. *arXiv*,
  2501.09551v3.
