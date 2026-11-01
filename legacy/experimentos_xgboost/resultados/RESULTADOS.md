# Experimentos con XGBoost

Archivado. El modelo actual está en `4_modelo_xgboost.ipynb`, en la raíz del repo.

Los genera el notebook `4_experimentos_xgboost.ipynb` (unos 35 minutos en 20
núcleos) con `panel_horario_modelo.csv.gz` y las características que eligió, para cada
horizonte, la selección lineal anterior (Granger y Wald con Driscoll-Kraay). Esos
archivos están en `legacy/seleccion_lineal/`; el paso 2d actual elige de otra forma.

## Diseño

- **Ventanas de datos:** los últimos 3 años, los últimos 5 y toda la historia.
  Todas terminan el 6 de octubre de 2026.
- **Partición por días, en orden:** 70% entrenamiento, 20% validación, 10%
  prueba. Cada ventana tiene su propio corte.

| Ventana | Entrenamiento | Validación | Prueba | Días de prueba |
|---|---|---|---|---|
| 3 años | 2023-10-07 a 2025-11-11 | 2025-11-12 a 2026-06-18 | 2026-06-19 a 2026-10-06 | 109 |
| 5 años | 2021-10-07 a 2025-04-06 | 2025-04-07 a 2026-04-06 | 2026-04-07 a 2026-10-06 | 182 |
| Toda | 2015-03-01 a 2023-04-14 | 2023-04-15 a 2025-08-09 | 2025-08-10 a 2026-10-06 | 422 |

- **Walk-forward.**
  - La validación se divide en 4 pliegues seguidos. En cada uno se entrena con
    todo lo anterior y se pronostica el pliegue.
  - Con el error de los cuatro se elige una de 6 configuraciones de
    hiperparámetros.
  - La prueba se hace igual en 2 pliegues, reentrenando con todo lo anterior y
    con la configuración ya elegida.
  - Entre el entrenamiento y cada pliegue se purgan h+1 días, para que ningún
    objetivo del entrenamiento caiga dentro del pliegue.
- **Horizontes:** 1 a 7 días, 14 y 30. Cada fila (día t, hora H) pronostica la
  hora H del día t+h, así que se pronostican las 24 horas de cada día.
- **Comparación:** el ingenuo repite el precio de esa hora del día t. La prueba
  de Diebold-Mariano usa el error cuadrático promedio de cada día.

## Resultados en la prueba

La primera cifra es la mejora del RMSE frente al ingenuo (en el log del precio;
positivo = mejor que el ingenuo). La segunda es el MAPE horario del modelo
frente al del ingenuo. "Sí" quiere decir que Diebold-Mariano es significativo
al 5%.

| h | 3 años | 5 años | Toda la historia |
|---|---|---|---|
| 1 | +16,4% · 12,5 vs 12,1 · sí | +22,8% · 14,1 vs 15,8 · sí | +23,1% · 15,7 vs 17,6 · sí |
| 2 | +14,2% · 16,0 vs 15,4 | +23,7% · 18,3 vs 21,4 · sí | +21,6% · 21,5 vs 24,1 · sí |
| 3 | +8,0% · 19,2 vs 18,1 | +23,3% · 21,2 vs 25,0 · sí | +17,6% · 26,1 vs 28,5 · sí |
| 4 | +3,4% · 21,3 vs 20,0 | +16,4% · 24,5 vs 28,3 · sí | +10,0% · 29,8 vs 32,3 · sí |
| 5 | +0,7% · 23,1 vs 21,4 | +9,5% · 27,8 vs 30,1 | +13,3% · 31,4 vs 35,0 · sí |
| 6 | −0,6% · 23,8 vs 21,9 | +12,2% · 28,1 vs 30,3 | +8,9% · 34,9 vs 36,2 · sí |
| 7 | −4,4% · 24,6 vs 22,4 | +5,8% · 29,1 vs 31,0 | +3,5% · 37,5 vs 37,4 |
| 14 | +1,1% · 31,0 vs 28,9 | +13,3% · 33,1 vs 39,2 · sí | +2,3% · 49,8 vs 47,1 |
| 30 | −18,1% · 54,3 vs 38,8 · sí (peor) | −4,9% · 49,1 vs 45,6 | −12,4% · 67,7 vs 54,7 |

En pesos, con toda la historia y h = 1, el RMSE horario es de 98 COP/kWh frente
a 120 del ingenuo. Para el promedio diario es de 46 frente a 60.

## Lo que se ve

1. **Con 3 años no alcanza.** La mejora es menor en todos los horizontes y el
   MAPE queda peor que el del ingenuo incluso en h = 1. Con 5 años o con toda
   la historia, XGBoost le gana al ingenuo de forma significativa hasta h = 4
   (5 años) y h = 6 (toda la historia).
2. **El horizonte útil es de una a dos semanas.** En h = 7 la mejora ya no es
   significativa. En h = 14 solo lo es con 5 años. En h = 30 el modelo es peor
   que el ingenuo en las tres ventanas.
3. **Con h = 3, el pronóstico realista de mañana** (por el atraso de
   publicación del precio), la mejora es de 17% a 23% con 5 años o más.
4. **Sesgo en horizontes largos.** De h = 4 a h = 7, con 3 y 5 años, el modelo
   pronostica en promedio bajadas de 3% a 10%, mientras que en la prueba
   (2026) el precio subió en promedio. Lo que aprendió de la reversión a la
   media no se cumplió en ese periodo. En h = 30 con 3 años pronostica +16% en
   promedio y el precio bajó 6%.
5. **Por hora,** el error más grande está en el pico de la noche (horas 19 a
   21), igual que en el ingenuo. En h = 1 la mejora está sobre todo en las
   horas del día (8 a 20); en la madrugada el modelo y el ingenuo quedan
   parecidos.
6. **Qué usa el modelo** (ganancia, toda la historia):
   - h = 1: la forma del día, el día de la semana pronosticado, la última hora
     del día t y el costo marginal programado de mañana.
   - h = 3: el festivo y el día de la semana pronosticados.
   - h = 7 y 14: el nivel del precio, el rezago de 7 días, los aportes y el mes.

## Cuidados al leerlo

- **Las tres pruebas son periodos distintos** (cada ventana con su propio
  corte), así que los errores absolutos no se comparan entre ventanas. Lo que
  sí se compara es la mejora frente al ingenuo dentro de cada prueba.
- **La prueba de 3 años tiene 109 días.** Diebold-Mariano con tan pocos días,
  y con horizontes de 14 o 30 que se traslapan, tiene poca potencia.
- **Las características se eligieron con 2015-2019.** Es antes de todas las
  pruebas, así que no hay fuga. Para las ventanas de 3 y 5 años, la selección
  usó datos más viejos que la ventana.
- **La rejilla de hiperparámetros es pequeña** (6 configuraciones). Las que más
  se eligieron son la de árboles poco profundos (profundidad 3) y la de
  profundidad 8 con hojas de al menos 50 horas.

## Archivos

| Archivo | Qué tiene |
|---|---|
| `resumen.csv` | una fila por ventana y horizonte: configuración elegida, métricas del modelo y del ingenuo, Diebold-Mariano |
| `validacion.csv` | el error de cada configuración en cada pliegue de validación |
| `predicciones.csv.gz` | cada pronóstico de la prueba, hora por hora: fecha, hora, día objetivo, precio real y pronosticado |
| `error_por_hora.csv` | RMSE por hora del día, modelo e ingenuo |
| `importancias.csv` | ganancia de cada característica en el último modelo de cada prueba |
| `mejora_por_horizonte.png`, `error_por_hora.png`, `ejemplo_hora_a_hora.png` | las gráficas |
