# Resultados de la LSTM de la tesis

Los guardan `6c_lstm_seleccion.ipynb` (selección de bloques y pruebas de control) y
`6d_lstm_busqueda_y_test.ipynb` (búsqueda, evaluación con tres semillas, test, semana final y
comparación con XGBoost y SARIMAX), los dos corridos en Colab con GPU. El diseño, fijado antes de
construirla, y lo que salió en cada etapa están en `docs/LSTM_DISENO.md`, y la explicación completa,
en las secciones 3.6 y 4.1 del informe.

## Modelo final

Una red codificador-decodificador para las 24 horas y los 7 días (h = 3 a 9), con los bloques 1 a 4:
el precio, el calendario, 4 variables del despacho programado de hoy y 5 del estado hidrológico,
cada una desde el día en que se publica. Una capa LSTM de 128 unidades en el codificador y otra en
el decodificador, capa de entrada de 64, dropout de 0,2, tasa de aprendizaje de 0,001, lotes de 32
y ventana de 28 días. En el test se entrena 4 épocas, sin parada temprana, con tres semillas cuyos
pronósticos se promedian, y se reentrena el primer día de cada mes (`configuracion_final.json`).

## Validación, 2020-2022

Mejora del RMSE en logaritmo frente al ingenuo del día (`validacion_criterio.csv`):

| Procedimiento | h = 3 a 9 | h = 3 | h = 3 a 7 | h = 8 a 9 |
|---|---|---|---|---|
| Parada temprana | 16,6% | 23,5% | 18,2% | 14,0% |
| Como en el test: 4 épocas, con todos los datos | 14,6% | 23,4% | 16,4% | 11,6% |

Aquí cada año se evalúa solo con los orígenes cuya semana pronosticada termina dentro de ese año,
así que el ingenuo del día tiene un RMSE de 0,2888, y no el 0,2943 de la validación de SARIMAX.

## Test

Se corrió una sola vez, el 14 de noviembre de 2026, en las mismas filas que XGBoost y SARIMAX:
183.120 pronósticos en 2023-2025 y 45.864 en 2026. RMSE en logaritmo y mejora frente al ingenuo
del día, que fue el mejor de los dos ingenuos en todos los casos (`comparacion_criterio.csv`):

| Periodo | Modelo | RMSE | Semana (h = 3 a 9) | h = 3 | h = 3 a 7 | h = 8 a 9 |
|---|---|---|---|---|---|---|
| 2023-2025 | LSTM | 0,427 | 14,9% | 24,5% | 17,5% | 10,6% |
| 2023-2025 | XGBoost | 0,443 | 11,6% | 17,9% | 12,5% | 10,1% |
| 2023-2025 | SARIMAX | 0,470 | 6,4% | 7,7% | 6,4% | 6,4% |
| 2026 | LSTM | 0,350 | 19,7% | 27,9% | 21,6% | 16,5% |
| 2026 | XGBoost | 0,392 | 10,0% | 19,5% | 11,6% | 7,2% |
| 2026 | SARIMAX | 0,411 | 5,6% | 6,5% | 5,6% | 5,6% |

Los tres modelos cumplen el criterio en todos los bloques, con Diebold-Mariano p < 0,05.

## Cómo leerlo

- Entre modelos (`comparacion_pares.csv`): la LSTM tiene menos error que SARIMAX en los dos periodos
  (p = 0,007 y 0,011). Frente a XGBoost la diferencia no es significativa en 2023-2025 (p = 0,107)
  y sí en 2026 (p = 0,033). Por años, los pares solo se distinguen en 2023; en 2025 XGBoost tuvo
  algo menos de error que la LSTM, sin diferencia significativa.
- La ventaja de la LSTM está en el nivel del día (`comparacion_nivel_forma.csv`): en 2023-2025 su
  error de nivel es 0,347, contra 0,385 de XGBoost, 0,402 de SARIMAX y 0,415 del ingenuo. En la
  forma de las horas, XGBoost es mejor (0,221 contra 0,249). El nivel es 66% del error cuadrático
  de la LSTM.
- En pesos (`comparacion_pesos.csv`): en 2023-2025 el RMSE baja 7,1% frente al ingenuo del día,
  sin diferencia significativa (p = 0,297), y el pronóstico queda en promedio 33 COP/kWh por debajo
  del precio real. En 2026 baja 8,8% (p = 0,042).
- Semana final, del 9 al 15 de octubre de 2026 (`semana_final_resumen.csv`): RMSE en logaritmo de
  0,252, contra 0,234 del ingenuo del día. Anticipó una subida que no llegó. Una sola semana no mide
  el modelo.

## Archivos

- `seleccion.csv`, `seleccion.json`: selección hacia adelante de los bloques con la configuración
  fija (tabla 10 del informe).
- `control_todas.csv`, `importancia_grupos.csv`: la red con todas las variables y la importancia
  por permutación de cada grupo (figura 16).
- `busqueda_control.csv`, `seleccion_repetida.csv`, `control_todas_repetida.csv`: la búsqueda corta
  de control y la selección repetida con la configuración 2.
- `busqueda.csv`: las 30 configuraciones de la búsqueda bayesiana, con una semilla.
- `evaluacion_tres_semillas.csv`: las nueve candidatas con tres semillas (tabla 12).
- `validacion_criterio.csv`, `configuracion_final.json`: el modelo elegido y su validación (tabla 13).
- `configuracion_final_busqueda1.json`, `validacion_criterio_busqueda1.csv`: la primera corrida, que
  tomaba la mejor de la búsqueda con una semilla. La reemplazó la evaluación con tres semillas.
- `prueba_2023_2025.csv.gz`, `prueba_2026.csv.gz`, `prueba_criterio.csv`: pronósticos del test y
  criterio.
- `comparacion_criterio.csv`, `comparacion_pares.csv`, `comparacion_nivel_forma.csv`,
  `comparacion_pesos.csv`, `comparacion_por_horizonte.png`: los tres modelos en las mismas filas.
- `pronostico_final.csv`, `semana_final_resumen.csv`: la semana del 9 al 15 de octubre de 2026.
