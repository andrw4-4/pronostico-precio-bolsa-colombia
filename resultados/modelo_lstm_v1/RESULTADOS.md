# Primera LSTM (versión anterior)

Esta carpeta guarda lo que quedó de la primera LSTM de la tesis, la de `6_modelo_lstm.ipynb`. Se
corrió el 2 de noviembre de 2026 en Colab, con GPU L4, y pasó por la prueba de 2023-2025 y de 2026
ese mismo día. La LSTM que reporta la tesis (`6c_lstm_seleccion.ipynb` y
`6d_lstm_busqueda_y_test.ipynb`) se diseñó el 5 y 6 de noviembre, después de conocer estos
resultados.

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `6_modelo_lstm_ejecutado.ipynb` | El notebook tal como quedó en Colab, con sus salidas y la hora de cada celda. Solo se le quitó el nombre de la cuenta de Colab |
| `configuracion.json` | Arquitectura, hiperparámetros y variables |
| `validacion_2022.csv` | El criterio de la tesis en 2022, el año de validación |
| `prueba_criterio.csv` | El criterio de la tesis en 2023-2025 y en 2026 |
| `semana_2026_09_25.png` | El pronóstico del 25 de septiembre de 2026 contra el precio real, la única semana de la prueba que se miró hora por hora |

Los pronósticos fila por fila no se conservaron: quedaron en la máquina de Colab y se perdieron al
cerrar la sesión. Las cifras de abajo salen de las tablas que el notebook dejó impresas.

## Cómo era

- Arquitectura de Salazar-Peña et al. (2025): tres capas LSTM una sobre otra (330, 210 y 150
  unidades), con dropout de 0,2, 0,3 y 0,3, y una capa densa con las 168 salidas de la semana.
  Optimizador Adam con tasa de 0,0037 y pérdida MAE.
- Entrada: los últimos 7 días, hora por hora (168 pasos), con 20 columnas: el logaritmo del
  precio, cinco variables (`cmg_hoy_vs_precio`, `cmg_despacho`, `disp_decl_hoy_rel`,
  `brecha_escasez` y `presion_hidro_horaria`) y 14 columnas de calendario. Las cinco variables las
  eligió el paso 2f con un XGBoost de prueba, y venían del panel con cada dato alineado a su fecha
  de publicación (`panel_lstm_modelo.csv.gz`).
- Hiperparámetros: búsqueda bayesiana de 10 combinaciones, 10 épocas cada una, entrenando hasta
  2021 y midiendo en 2022. La mejor época con parada temprana fue la 6.
- Prueba: reentrenamiento el primer día de cada mes, 6 épocas, una sola semilla. Las filas son las
  mismas de XGBoost y SARIMAX.

## Resultados

Mejora del RMSE en logaritmo frente al ingenuo del día, que fue el mejor ingenuo en todos los
bloques. En todos se cumple el criterio (5% y Diebold-Mariano p < 0,05).

| Periodo | h = 3 a 9 | h = 3 | h = 3 a 7 | h = 8 a 9 |
|---|---|---|---|---|
| Validación, 2022 | 15,0% | 23,1% | 16,5% | 12,5% |
| Prueba, 2023-2025 | 12,0% | 16,0% | 13,2% | 9,8% |
| Prueba, 2026 | 12,9% | 17,7% | 14,4% | 10,4% |

En la semana completa su RMSE fue 0,4418 en 2023-2025 y 0,3791 en 2026. Como referencia, en esas
mismas filas XGBoost tuvo 11,6% y 10,0%, y la LSTM de la tesis, 14,9% y 19,7%.

## Qué se vio y qué motivó la LSTM nueva

Además de las tablas, se miró una semana de la prueba, la del pronóstico del 25 de septiembre de
2026 (`semana_2026_09_25.png`):

- La red repetía casi la misma forma de día en toda la semana y ponía el mismo pico de la tarde el
  sábado y el domingo.
- De noche y en la mañana se quedaba corta.
- No anticipó el salto del 2 de octubre.

Con eso se diseñó la LSTM nueva (`docs/LSTM_DISENO.md`): codificador y decodificador con el
calendario de cada día pronosticado, pérdida MSE, ventana de varias semanas, tres semillas y los
bloques de variables. Otro motivo que da ese documento es que XGBoost subestimó en 670 COP/kWh el
precio de octubre de 2024, un mes de la prueba.

## Qué implica

La LSTM de la tesis pasó una sola vez por la prueba, pero se diseñó después de conocer la prueba
de esta versión y los errores de XGBoost en 2024. Por eso su resultado de 2023-2026 no es una
evaluación independiente del diseño: la elección de la arquitectura ya había usado ese periodo.
La evaluación que ninguna decisión tocó es la de los días posteriores al 6 de octubre de 2026.
