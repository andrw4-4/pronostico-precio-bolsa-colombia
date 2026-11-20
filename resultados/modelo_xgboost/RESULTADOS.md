# Modelo XGBoost

Los genera `4_modelo_xgboost.ipynb`. El modelo pronostica una semana, hora por hora: 168
precios, de h = 3 a h = 9, con 7 modelos directos y las columnas de la selección
congelada. El test corrió una sola vez, el 1 de noviembre de 2026, con la configuración
de `configuracion_final.json`. No se repite ni se ajusta nada a partir de estos números.

El alcance empezó en 30 días. Este documento conserva esos resultados, porque son la
evidencia de hasta dónde sirve el modelo.

Tiempos: búsqueda 77 min, walk-forward mensual 24 min, variantes 14 min, test 20 min.

## Alcance final: una semana

Se decidió después de ver el test, porque en 2026 el modelo solo funcionó hasta h = 7
(ver "Test en 2026"). Los modelos son los mismos: no se reentrenó ni se ajustó nada. Son
los días h = 3 a 9 porque, por el atraso de dos días del precio, esos son los primeros
siete que de verdad se pueden pronosticar.

| Periodo | RMSE log | Mejor ingenuo (del día) | Mejora | DM t | DM p |
|---|---|---|---|---|---|
| 2023-2025 | 0,443 | 0,502 | 11,6% | -4,82 | < 0,001 |
| 2026, hasta el 6 de octubre | 0,392 | 0,435 | 10,0% | -3,29 | 0,001 |
| 2023 | 0,474 | 0,544 | 12,9% | -3,32 | 0,001 |
| 2024 | 0,470 | 0,508 | 7,6% | -1,65 | 0,100 |
| 2025 | 0,379 | 0,447 | 15,3% | -4,75 | < 0,001 |

- Este bloque no hacía parte del criterio fijado antes del test: sus números salen algo
  favorecidos y no reemplazan el veredicto de abajo.
- h = 8 y h = 9 usan la configuración de h = 7 y no tuvieron validación propia.
- Ninguno de los 7 modelos usa `cmg_redespacho`, así que el dato de 24.595 de abril de
  2026 no los afecta.

## Semana final: del 9 al 15 de octubre de 2026

Un solo pronóstico, con datos hasta el 6 de octubre, guardado antes de bajar el precio
real. Es una demostración: una semana no mide el modelo y no permite Diebold-Mariano.

| Medida | Modelo | Ingenuo del día | Ingenuo semanal |
|---|---|---|---|
| RMSE log | 0,201 | 0,234 | 0,271 |
| MAE log | 0,159 | 0,195 | 0,203 |
| Mediana del error | 0,133 | 0,171 | 0,159 |
| MAPE | 15,9% | 18,7% | 23,0% |

- Mejora el RMSE 14,1% frente al ingenuo del día y 25,6% frente al semanal.
- Fue el mejor de los tres en 5 de 7 días. Perdió el viernes 9 contra el semanal y el
  miércoles 14 contra el del día.
- Subestimó los picos del viernes y el sábado (934 contra 1.317 y 895 contra 1.263) y
  sobrestimó los del martes y el miércoles (1.009 contra 690 y 1.116 contra 766). El del
  jueves le salió casi exacto (1.116 contra 1.093).
- Fue una semana más fácil que lo normal: el 79% de los cortes de 2026 tuvo más error. El
  RMSE de esta semana es 0,201, y la mediana de esos cortes es 0,321.

## Criterio

Fijado antes de abrir el test. El umbral de 5% y los bloques son decisión del autor.
Un modelo funciona en un bloque si su RMSE en log baja al menos 5% frente al mejor de
los dos ingenuos y Diebold-Mariano contra ese ingenuo da p < 0,05. h = 1 y h = 2 no
cuentan, porque el primer pronóstico real es h = 3.

## Veredicto, 2023-2025

| Bloque | RMSE log | Mejor ingenuo | Mejora | DM t | DM p | Funciona |
|---|---|---|---|---|---|---|
| h = 3 | 0,338 | 0,412 (del día) | 17,9% | -8,65 | < 0,001 | sí |
| h = 3 a 7 | 0,413 | 0,472 (del día) | 12,5% | -6,24 | < 0,001 | sí |
| h = 8 a 14 | 0,546 | 0,612 (del día) | 10,7% | -2,68 | 0,007 | sí |
| h = 15 a 30 | 0,615 | 0,708 (del día) | 13,1% | -2,41 | 0,016 | sí |

El criterio se mide por bloque. Por horizonte, h = 14 (p = 0,057) y h = 27 (p = 0,056)
no llegan a 0,05.

## Por horizonte

Mejora del RMSE frente al mejor de los dos ingenuos.

| h | RMSE test | Ingenuo test | Test | Validación 2020-2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| 1 | 0,216 | 0,305 | 29,3% | 29,9% | 29,8% | 29,9% | 28,2% |
| 2 | 0,284 | 0,367 | 22,4% | 24,0% | 19,1% | 21,5% | 26,3% |
| 3 | 0,338 | 0,411 | 17,9% | 18,4% | 14,4% | 16,8% | 22,5% |
| 4 | 0,377 | 0,447 | 15,7% | 16,9% | 14,1% | 13,4% | 20,1% |
| 5 | 0,406 | 0,479 | 15,1% | 13,4% | 15,2% | 13,3% | 16,7% |
| 6 | 0,452 | 0,499 | 9,3% | 8,9% | 10,0% | 7,3% | 10,8% |
| 7 | 0,475 | 0,517 | 8,0% | 8,3% | 11,7% | 1,8% | 10,6% |
| 14 | 0,578 | 0,639 | 9,7% | 10,8% | 12,6% | 3,0% | 14,9% |
| 30 | 0,637 | 0,733 | 13,1% | 16,1% | 15,5% | 4,6% | 24,4% |

La mejora relativa casi no cae frente a validación. El error absoluto sí sube, también
el del ingenuo, porque 2023-2025 es más volátil: en h = 7 el ingenuo pasa de 0,303 a
0,517. Le gana al mejor ingenuo en los 30 horizontes y en los tres años; el caso más
ajustado es h = 7 en 2024.

## Lo que el criterio no muestra

El criterio usa RMSE, que pesa los errores grandes. Con otras medidas la ventaja se
reduce, sobre todo entre h = 7 y h = 14.

| Bloque | Mejora del MAE, ingenuo del día |
|---|---|
| h = 3 | 13,2% |
| h = 3 a 7 | 6,4% |
| h = 8 a 14 | 2,4% |
| h = 15 a 30 | 10,4% |

| h | MAPE modelo | MAPE ingenuo del día | Mediana del error, modelo | Mediana del error, ingenuo |
|---|---|---|---|---|
| 3 | 25,3% | 29,7% | 0,142 | 0,137 |
| 7 | 40,1% | 42,3% | 0,277 | 0,217 |
| 14 | 47,6% | 58,3% | 0,344 | 0,308 |
| 30 | 51,1% | 75,0% | 0,361 | 0,446 |

- En MAE, h = 7 queda 1,9% peor que el ingenuo y h = 8 queda igual (0,1% peor).
- En la mediana del error absoluto en log, el ingenuo gana en h = 3, 7 y 14. Ahí la
  ventaja del modelo está en los errores grandes, no en el día típico.
- El sesgo cambia de signo entre años. Positivo significa que el precio real quedó por
  encima del pronóstico.

| h | 2023 | 2024 | 2025 |
|---|---|---|---|
| 3 | 0,032 | 0,005 | -0,026 |
| 7 | 0,083 | 0,100 | -0,062 |
| 14 | 0,163 | 0,170 | -0,084 |
| 30 | 0,095 | 0,283 | -0,192 |

## Test en 2026

Etapa 6b, del 1 de enero al 6 de octubre de 2026, con la misma configuración y el mismo
criterio. Se pidió después de ver el test de 2023-2025 y no cambia nada de lo anterior.
Son de 249 a 278 días por horizonte, así que Diebold-Mariano tiene menos potencia. Hay
dos planes: mensual, con el diseño del test, y fijo, entrenado una sola vez con 2015-2025.

| Bloque | Mejor ingenuo | Mejora mensual | Mejora fijo | DM p mensual | DM p fijo | Funciona |
|---|---|---|---|---|---|---|
| h = 3 | del día | 19,5% | 19,2% | < 0,001 | < 0,001 | sí |
| h = 3 a 7 | del día | 11,6% | 11,4% | < 0,001 | < 0,001 | sí |
| h = 8 a 14 | del día | 6,4% | 6,8% | 0,096 | 0,053 | no |
| h = 15 a 30 | semanal | -7,2% | -7,5% | 0,361 | 0,332 | no |

- Pasa hasta h = 7. En h = 8 a 14 la mejora supera el 5%, pero Diebold-Mariano no llega a
  0,05 y no se distingue de la suerte.
- En h = 15 a 30 pierde contra el ingenuo semanal, en cada horizonte del bloque (de -0,3%
  a -14,6% en el plan mensual). La diferencia tampoco es significativa.
- Reentrenar cada mes no cambió el resultado frente al modelo fijo.
- En h = 30 los peores orígenes fueron enero (0,995 contra 0,585 del ingenuo del día),
  marzo (0,732 contra 0,498) y septiembre (0,603 contra 0,394). De mayo a julio ganó.
- 2026 es el año de mayor variabilidad del panel (desviación del log del precio 0,767) y
  la mediana del precio pasó de 164 en 2025 a 385. Puede explicar la caída, pero no se
  midió.

Plan mensual, frente al ingenuo del día:

| Bloque | Mejora del MAE | Mediana del error, modelo | Mediana del error, ingenuo |
|---|---|---|---|
| h = 3 | 17,2% | 0,127 | 0,143 |
| h = 3 a 7 | 9,3% | 0,188 | 0,197 |
| h = 8 a 14 | 2,7% | 0,307 | 0,295 |
| h = 15 a 30 | -14,8% | 0,469 | 0,351 |

Corrió sin errores en 6 minutos, sin vacíos y con objetivos hasta el 6 de octubre. El
modelo no se ajusta con este resultado: si algo cambiara por él, 2026 dejaría de servir
como test.

## Cómo leerlo

- El test no está intacto del todo: los experimentos de `legacy/experimentos_xgboost/` ya evaluaron
  en 2023-2026 con la selección lineal. Nada de eso se usó para decidir aquí.
- Los errores de validación son optimistas: esa ventana se usó para la selección y para
  el ajuste.
- Los 21 horizontes fuera de las anclas no tuvieron validación; su primera medida es este
  test.
- SARIMAX y la LSTM deben congelarse sin usar estos números para decidir.

## Verificación

- Corrió sin errores en los 30 horizontes, de 1.066 a 1.095 días cada uno, sin vacíos
  y sin objetivos posteriores al 31 de diciembre de 2025.
- Recalculado aparte: el objetivo de h = 3, 7, 12 y 30 coincide con el panel, y el RMSE
  del ingenuo de esos horizontes da lo mismo a mano.
- La mejora de los cuatro bloques da idéntica. El t de Diebold-Mariano difiere en la
  tercera cifra decimal por la forma de promediar las autocovarianzas.
- En la semana final, el pronóstico se guardó antes de bajar el precio real: 168 valores
  sin vacíos contra 168 precios reales, los 7 días completos.

## Archivos

- `configuracion_final.json`: la configuración congelada.
- `etapa2_h*.csv`, `etapa3_h*.csv.gz`, `etapa4_*.csv`: búsqueda, walk-forward y variantes.
- `alcance_semana.csv`: la tabla del alcance final.
- `pronostico_final.csv`, `pronostico_final_creado.txt`, `precio_real_final.csv`,
  `semana_final_resumen.csv`, `semana_final.png`: la semana final.
- `prueba_h*.csv.gz`: pronósticos del test por horizonte.
- `prueba_criterio.csv`, `prueba_resumen.csv`, `prueba_por_año.csv`: veredicto y tablas.
- `prueba2026_mensual.csv.gz`, `prueba2026_fijo.csv.gz`, `prueba2026_criterio.csv`,
  `prueba2026_resumen.csv`: pronósticos y tablas del test en 2026.
- `mejora_por_horizonte.png`: mejora del RMSE por horizonte.
- `semana_real_vs_pronostico.png`: última semana completa del panel, del 28 de septiembre
  al 4 de octubre de 2026, hora por hora, con el pronóstico del 25 de septiembre. No es
  una semana típica: el 71% de los cortes de 2026 tiene más error.
