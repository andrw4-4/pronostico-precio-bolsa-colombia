# Modelo SARIMAX

Los genera `5_modelo_sarimax.ipynb`, en R. Pronostica lo mismo que XGBoost: 168 precios, de
h = 3 a h = 9. Son 24 modelos, uno por hora, con la serie diaria de `lp`, ciclo semanal y
`es_festivo` del día objetivo. Todo se eligió con criterios estadísticos y datos hasta 2022.
El test corrió una sola vez, el 1 de noviembre de 2026, sin ajustar nada después.

Tiempos: órdenes 1 min, exógenas 1 min, validación 12 min, test 10 min.

## Qué eligieron las pruebas

**Órdenes (2015-2019).** KPSS y OCSB dieron d = 1 y D = 0 en las 24 horas. Con AICc salieron 12
órdenes distintos; el más frecuente, (1,1,2)(0,0,2) con s = 7, en 5 horas.

**Exógenas (2015-2019).** De 133 variables base, 122 pasaron la limpieza del paso 2d: 8 salieron
por inestables, 2 por seguir al dólar y 1 por casi constante.

| Filtro | Resultado |
|---|---|
| Preblanqueo, rezago 9, con Bonferroni, en al menos 12 horas | Pasa 1 de 122: `holgura_rel`, en justo 12 horas |
| Hacia adelante con AICc | La acepta: de −23.215 a −23.462 |
| Prueba t | La acepta: p < 0,05 en 17 de 24 horas |

**Validación (2020-2022, h = 3 a 9).** Una versión más compleja entraba solo con
Diebold-Mariano p < 0,05 contra la anterior.

| Versión | RMSE log | DM p contra la anterior | Queda |
|---|---|---|---|
| Un solo orden, sin exógenas | 0,2805 | | sí |
| Un orden por hora | 0,2806 | 0,865 | no |
| Con `holgura_rel` | 0,2806 | 0,970 | no |

`holgura_rel` pasó las tres pruebas dentro de la muestra y no mejoró el pronóstico fuera de ella.
El modelo final es (1,1,2)(0,0,2) con s = 7, sin exógenas. El ingenuo del día en esa ventana da
0,2943, así que la mejora fue de 4,7% (p = 0,018), un poco por debajo del 5%.

Ljung-Box a 14 rezagos en 2015-2019: 17 de 24 horas quedan sin autocorrelación al 5%. En las otras
7 el orden común deja algo sin explicar.

## Veredicto del test

Criterio fijado antes de abrir el test: el RMSE en log baja al menos 5% frente al mejor de los dos
ingenuos, con Diebold-Mariano p < 0,05. El mejor ingenuo es el del día en todos los bloques.

| Bloque | 2023-2025 | p | 2026 | p | Funciona |
|---|---|---|---|---|---|
| h = 3 a 9 | 6,4% | < 0,001 | 5,6% | < 0,001 | sí, en los dos |
| h = 3 | 7,7% | < 0,001 | 6,5% | < 0,001 | sí, en los dos |
| h = 3 a 7 | 6,4% | < 0,001 | 5,6% | < 0,001 | sí, en los dos |
| h = 8 a 9 | 6,4% | < 0,001 | 5,6% | 0,001 | sí, en los dos |

## Comparación con XGBoost

En las mismas 228.984 filas, h = 3 a 9, con el mismo objetivo y los mismos ingenuos.

| Medida | SARIMAX 2023-2025 | XGBoost 2023-2025 | Ingenuo 2023-2025 | SARIMAX 2026 | XGBoost 2026 | Ingenuo 2026 |
|---|---|---|---|---|---|---|
| RMSE | 0,470 | 0,443 | 0,502 | 0,411 | 0,392 | 0,435 |
| MAE | 0,327 | 0,318 | 0,333 | 0,301 | 0,289 | 0,311 |
| Mediana del error | 0,221 | 0,225 | 0,203 | 0,215 | 0,212 | 0,215 |
| Error del nivel del día | 0,402 | 0,385 | 0,415 | 0,356 | 0,341 | 0,363 |
| Error de la forma | 0,243 | 0,221 | 0,282 | 0,205 | 0,193 | 0,240 |
| Sesgo | −0,005 | 0,022 | | 0,037 | 0,033 | |

El ingenuo es el del día.

| Periodo | RMSE SARIMAX | RMSE XGBoost | Diebold-Mariano p |
|---|---|---|---|
| 2023-2025 | 0,470 | 0,443 | 0,011 |
| 2026 | 0,411 | 0,392 | 0,062 |
| 2023 | 0,521 | 0,474 | 0,003 |
| 2024 | 0,478 | 0,470 | 0,707 |
| 2025 | 0,401 | 0,379 | 0,070 |

- XGBoost le gana a SARIMAX en RMSE en todos los periodos, pero la diferencia solo es significativa
  en 2023-2025 y en 2023. En 2024 quedan empatados, y ahí SARIMAX tiene mejor MAE (0,323 contra
  0,332).
- En el día típico no hay ventaja real: la mediana de los dos es casi igual y en 2023-2025 los dos
  quedan peor que el ingenuo.
- SARIMAX casi no tiene sesgo por año (de −0,016 a 0,003 en 2023-2025). XGBoost va de −0,060 a 0,063.
- Ninguno anticipa bien el nivel del día. Frente al ingenuo, en 2023-2025 SARIMAX lo mejora 3,1% y
  XGBoost 7,2%; en 2026, 1,9% y 6,1%. En la forma las mejoras son mayores: 13,8% y 21,6% en
  2023-2025. Esto apunta a que el límite está en la información, pero falta la LSTM para decirlo
  con más seguridad, y ninguno de los modelos usa pronósticos de clima o de ofertas.

## Intervalos

El intervalo de 80% queda angosto: cubre 71,1% en 2023-2025 (62,4% en 2023) y 75,4% en 2026. En la
semana final cubrió 94%, pero son solo 168 valores de una semana tranquila. No entra al criterio.

## Semana final: del 9 al 15 de octubre de 2026

Demostración con el corte del 6 de octubre. Usa el precio real que ya había bajado XGBoost.

| Medida | SARIMAX | XGBoost | Ingenuo del día | Ingenuo semanal |
|---|---|---|---|---|
| RMSE log | 0,218 | 0,201 | 0,234 | 0,271 |
| MAE log | 0,176 | 0,159 | 0,195 | 0,203 |
| Mediana del error | 0,160 | 0,133 | 0,171 | 0,159 |
| MAPE | 17,9% | 15,9% | 18,7% | 23,0% |

## Cómo leerlo

- A diferencia de XGBoost, el bloque h = 3 a 9 de SARIMAX sí quedó fijado antes de ver su test. Sus
  números no salen favorecidos por haber elegido el alcance después, aunque ese alcance se decidió
  mirando el test de XGBoost.
- Las decisiones de SARIMAX salieron de reglas fijadas antes y de datos hasta 2022.
- 2023-2026 no está intacto para el proyecto: XGBoost y los experimentos anteriores ya se midieron
  ahí.
- Filtrar las candidatas con el modelo de `lp`, y no con el suyo propio, es una simplificación del
  autor.

## Verificación

- Las funciones en R reproducen el resultado de XGBoost en Python: 11,638% y t = −4,824.
- Mismas 228.984 filas que XGBoost, sin vacíos, con el mismo objetivo y los mismos ingenuos.
- Alterar datos posteriores al origen no cambia el pronóstico, y pedir un dato de 2023 antes del
  test falla.
- Todos los meses convergieron en las 24 horas.
- Al repetir el notebook, las etapas 2 a 5 leen lo guardado y no reentrenan.

## Archivos

- `configuracion_final.json`: la configuración congelada.
- `etapa2_ordenes.csv`, `etapa3_*.csv`, `etapa4_*`: órdenes, exógenas y validación.
- `prueba_2023_2025.csv.gz`, `prueba_2026.csv.gz`: pronósticos del test, con intervalo de 80%.
- `prueba_criterio.csv`, `comparacion_xgboost.csv`: veredicto y comparación.
- `pronostico_final.csv`, `semana_final_resumen.csv`, `semana_final.png`: la semana final.
- `semana_comparacion.png`: los dos modelos contra el real, del 28 de septiembre al 4 de octubre.
