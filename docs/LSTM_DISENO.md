# Diseño de la LSTM nueva

Plan acordado el 5 y 6 de noviembre de 2026, antes de construirla. Reemplaza el
camino de la v2 (`6b_modelo_lstm_v2.ipynb`), que nunca se corrió. La v1
(`6_modelo_lstm.ipynb`) ya tiene su test y se conserva tal cual.

Este documento dice qué se va a hacer y por qué, para que las decisiones queden
fijadas antes de ver resultados.

Estado al 13 de noviembre de 2026: está el panel por bloques
(`2h_panel_lstm_bloques.py`, que escribe `paneles/panel_lstm_bloques.csv.gz` y
`panel_lstm_bloques_variables.csv`) y el notebook de selección para Colab
(`6c_lstm_seleccion.ipynb`), sin correr. Decisiones de ese día:

- El precio va con 2 días de atraso, como en XGBoost y SARIMAX, para comparar en
  las mismas filas (h = 3 a 9).
- Primero se seleccionan los bloques 1 a 6. El bloque 7 va al final, cuando existan
  los pronósticos de XGBoost y SARIMAX para 2017-2022.
- Las variables de noticias y la salida que detecta crisis de precio quedan para
  después de tener la LSTM base, para medir si aportan algo encima de ella.
- La comprobación de la configuración fija es la búsqueda corta de control (ver
  "Hiperparámetros").

## Por qué una LSTM nueva

- La v1 repite la misma forma de día en toda la semana, pone el mismo pico los
  fines de semana y se queda corta de noche. Le falta saber qué día de la semana
  es cada uno de los 7 que pronostica.
- Sus 5 variables las eligió un XGBoost de prueba que veía cada variable resumida
  en tres números (valor, promedio del día y cambio frente a hace 7 días). Una LSTM
  ve la secuencia completa de varias semanas, así que puede aprovechar variables
  lentas, como la hidrología, que a ese XGBoost no le sirvieron.
- XGBoost se queda corto en las crisis de precio: en octubre de 2024, a h = 6,
  subestimó en 670 COP/kWh el promedio del mes (SARIMAX, 320; el ingenuo del día,
  180). Lo que mantiene el precio alto varias semanas es el estado del agua, y esa
  es la principal apuesta de la LSTM nueva.

## Variables: siete bloques

Cada variable entra como una columna, alineada a su fecha de publicación como en
el panel 2e (`docs/PANEL_HORARIO.md`, sección "Panel para la LSTM"). No se agregan
rezagos ni resúmenes hechos a mano: la red recibe la secuencia de los últimos días
y construye sola esa información. Las variables que ya son acumulados (por ejemplo
`lluvia_sistema_acum90` u `oni`) quedan como están, porque así se mide esa
variable.

Los bloques salen de cómo se forma el precio, no de los datos (decisión del autor).
La evidencia es la del paso 2f, medida con el XGBoost de prueba.

| Bloque | Qué le dice al modelo | Variables | Evidencia del 2f |
|---|---|---|---|
| 1. Precio | Su propia historia | `lp`, 24 horas por día | Entra siempre |
| 2. Calendario de los días pronosticados | Fines de semana y festivos bajan el precio | Día de la semana y festivo de cada uno de los 7 días; hora | Entra siempre |
| 3. Despacho de hoy | Cómo viene el sistema, dos días más fresco que el precio | `cmg_hoy_vs_precio`, `cmg_despacho`, `disp_decl_hoy_rel`, `frac_termica_prog` | El grupo más fuerte: −16,7% en el paso 1 y p < 0,001 en los tres horizontes del paso 3 |
| 4. Estado hidrológico | Si el agua alcanza | `volumen_util_pct`, `aportes_media_hist`, `presion_hidro_horaria`, `brecha_escasez`, `dias_autonomia` | Aportes −11,5% y embalses −7,6% solos; no sumaron encima del despacho |
| 5. Despacho de ayer | Cuánto se corrigió lo programado | `cmg_redespacho`, `error_cmg_despacho`, `redespacho_vs_programa` | −8,1% solo; no sumó encima del despacho de hoy |
| 6. Clima que viene | Si va a llover menos en las próximas semanas | `oni`, `nino34_anom`, `lluvia_anom_acum30`, `pred_deficit` | Débil a una semana: El Niño +0,9%, IDEAM +2,3%, lluvia −3,9% |
| 7. Pronósticos de XGBoost y SARIMAX | Qué dicen los otros dos modelos y cuál viene acertando | Los 168 pronósticos de cada modelo y sus errores recientes ya conocidos | Sin medir; ver la sección del bloque 7 |

No entran como bloque: demanda (la explica el calendario), ofertas y curva de
mérito (se publican con 10 días de atraso), generación y mezcla por planta,
red y contratos, y el resto del grupo sistema (repiten lo del despacho). Se
revisan con la prueba de control.

## Cómo se eligen los bloques

Selección hacia adelante, con la LSTM misma y no con XGBoost.

1. Modelo A: bloques 1 y 2. Es la referencia.
2. Se entrena un modelo nuevo, desde cero, con la referencia más el bloque 3. Si le
   gana a la referencia, pasa a ser la nueva referencia; si no, el bloque sale.
3. Igual con los bloques 4 y 5.
4. El bloque 6 solo se prueba si entró el 4.
5. El bloque 7 va de último (ver abajo).

Regla para que un bloque entre: le gana a la referencia con Diebold-Mariano
p < 0,05 en al menos un horizonte (h = 3, 6 o 9) y no pierde con p < 0,05 en
ninguno. Es la misma regla de SARIMAX y del paso 2f. Se compara contra la
referencia del momento y no siempre contra los bloques 1 y 2, porque los bloques se
repiten entre sí: lo que importa es si agregan algo a lo que ya entró.

### Validación

Walk-forward por años; los días no se mezclan.

| Periodo | Entrena con | Se mide en |
|---|---|---|
| 1 | 2015-2019 | 2020 |
| 2 | 2015-2020 | 2021 |
| 3 | 2015-2021 | 2022 |

Se juntan los errores de los tres años y con eso se hace la prueba. Cada
entrenamiento se repite con 3 semillas y se promedian los pronósticos.

### Prueba de control: todas las variables

Aparte se entrena una versión con todas las variables (las 135 del panel 2e más
`frac_termica_prog`). Con ese modelo ya entrenado, en validación se desordenan los
días de un grupo completo y se mide cuánto empeora el pronóstico (importancia por
permutación). Se hace por grupo y no por variable porque muchas variables dicen lo
mismo: si se desordena una sola de las 21 de lluvia, el modelo usa las otras y
parece que ninguna importa.

- Si los grupos que quedaron fuera casi no importan, la tabla de bloques queda
  confirmada.
- Si alguno importa, se agrega como bloque y se prueba con la misma regla.

"Importa" quiere decir (decisión del autor): un grupo sin ninguna variable en los
bloques sube el RMSE de la semana, al desordenarlo, más que el menos importante de
los bloques que sí entraron. Cada bloque se desordena completo, con todas las
variables de los grupos de donde salió. Los bloques que no entraron no se vuelven
a probar, porque ya pasaron por la selección.

Es el mismo papel que tuvo "las 135" como referencia en el 2f, donde con el
XGBoost de prueba mejoraba en h = 3 (28,5% contra 24,8%) pero empeoraba en h = 6
y h = 9.

## El bloque 7: pronósticos de XGBoost y SARIMAX

Es un apilamiento de pronósticos: la red aprende a cuál modelo creerle según la
situación (por ejemplo, más a SARIMAX en los horizontes largos o cuando el
embalse está bajo).

- Por el decodificador entran los pronósticos de cada hora de la semana, de los dos
  modelos, junto al calendario de cada día.
- Por el codificador entran sus errores recientes, de días cuyo precio ya se conoce
  (respetando el atraso de dos días), para que vea cuál viene acertando.

Condiciones:

1. Los pronósticos tienen que ser como en la vida real: hechos con walk-forward,
   sin ver el futuro. Si se usaran las predicciones que cada modelo hace sobre sus
   propios datos de entrenamiento, la red vería modelos casi perfectos y aprendería
   a creerles todo. Hoy existen los de SARIMAX para 2020-2022 y los de los dos
   modelos para el test 2023-2026. Hay que generar los de 2017-2022 con la
   configuración final de cada uno, sin cambiarla.
2. Como antes de 2017 no hay pronósticos, esa comparación se hace entrenando desde
   2017, tanto la referencia como el modelo con el bloque 7.
3. Además de ganarle a la referencia, tiene que ganarle al promedio simple de
   XGBoost y SARIMAX. En pronósticos es común que el promedio simple le gane a
   combinaciones aprendidas (Smith y Wallis, 2009; Timmermann, 2006).
4. La configuración de XGBoost se eligió mirando 2020-2022, así que sus pronósticos
   de esos años son algo optimistas. Se reporta como limitación.

En la tesis, la LSTM que se compara con XGBoost y SARIMAX es la mejor sin el bloque
7. La versión con el bloque 7 es un modelo combinado y se reporta aparte, como
resultado exploratorio.

## Arquitectura

Codificador-decodificador (Sutskever et al., 2014) con celdas LSTM (Hochreiter y
Schmidhuber, 1997). Durante la selección es la misma en todas las corridas; solo
cambian las variables. Así, si un bloque gana es por sus variables y no por una
red distinta.

```
CODIFICADOR (lo que pasó)                    DECODIFICADOR (la semana que viene)
28 pasos, uno por día (t-27 ... t)           7 pasos, uno por día objetivo

cada paso = las 24 horas de cada             cada paso = calendario de ese día
variable horaria + las diarias               (día de la semana, festivo)
        │                                    [+ bloque 7: 24 pronósticos de
  Dense(64)                                    XGBoost y 24 de SARIMAX]
        │                                            │
  LSTM(128) ──── estado final ─────────────► LSTM(128) arranca con ese estado
                                                     │
                                              Dense(24) por día
                                                     │
                                            7 días × 24 horas = 168 pronósticos
```

- Codificador: cada día entra como un vector con las 24 horas de cada variable
  horaria y una vez cada variable diaria, más el calendario de ese día.
- El calendario, tanto el del codificador como el del decodificador, son 8
  números por día: un indicador por día de la semana y el festivo. Va con
  indicadores y no con seno y coseno porque el efecto del fin de semana no es
  una onda.
- El decodificador no recibe sus propios pronósticos del día anterior, solo el
  calendario, que ya se conoce. Así un error en el primer día no se arrastra al
  resto de la semana.
- La capa Dense(64) de entrada comprime cada día al mismo tamaño, sean 32 números
  (solo precio y calendario), 255 (los seis bloques) o 1.249 (todas las variables). Sin ella, la
  versión con todas tendría una red mucho más grande y la comparación no sería
  justa.
- Decodificador: genera la semana día por día sabiendo qué día es cada uno. Es lo
  que corrige el problema de la v1.
- Salida: para cada hora, `y_h` = lp(t + h, H) − lp(t, H), igual que en XGBoost.
  Se pasa a pesos al final.

Tamaño: 174.168 parámetros con los bloques 1 y 2, 188.440 con los seis bloques y
252.056 con todas las variables; la diferencia está solo en la capa de entrada.
Los ejemplos de entrenamiento son pocos, porque cada ejemplo es un día: unos 1.700
con 2015-2019 y unos 2.400 con 2015-2021. Por eso la red es de una sola capa y
lleva dropout, parada temprana y promedio de semillas.

### Diferencias con Salazar-Peña et al. (2025)

- Ellos apilan tres capas LSTM y pronostican todo con una sola capa de salida.
  Aquí se usa codificador-decodificador porque la semana tiene días distintos
  (laborales, fines de semana, festivos) y porque el bloque 7 entra día por día.
- Ellos usan MAE como pérdida; aquí MSE, porque el criterio de la tesis es el RMSE
  en logaritmo.
- El formato de los resultados sí sigue al paper (`7_resultados.ipynb`).

## Hiperparámetros

Los parámetros son los pesos de la red, que aprende al entrenar. Los
hiperparámetros son las decisiones previas al entrenamiento. Se ajustan en dos
etapas.

| Hiperparámetro | Etapa 1: selección de bloques (fijo) | Etapa 2: búsqueda bayesiana (rango) |
|---|---|---|
| Capas LSTM | 1 en el codificador y 1 en el decodificador | 1 a 3 |
| Neuronas por capa | 128 | 32 a 360 |
| Capa de entrada (Dense) | 64 | 32 a 256 |
| Dropout | 0,2 | 0,2 a 0,5, como el paper |
| Tasa de aprendizaje (Adam) | 0,001 | 1e-5 a 1e-2, escala logarítmica, como el paper |
| Tamaño del lote | 32 | 32 o 64 |
| Ventana de historia | 28 días | 14, 28 o 56 |
| Épocas | Hasta 100, parada temprana con paciencia 10 | Igual |

Comunes a todo: pérdida MSE; parada temprana con el último 10% del periodo de
entrenamiento, en orden de fechas; estandarización solo con datos de
entrenamiento; 3 semillas promediadas.

Por qué fijos en la etapa 1:

1. Para que la comparación sea justa: si cada versión tuviera su propia búsqueda,
   no se sabría si un bloque ganó por sus variables o por sus hiperparámetros.
2. Por tiempo: una búsqueda de 20 pruebas por versión serían más de mil
   entrenamientos; con valores fijos son unos 54.

Los valores fijos son estándar para una red de este tamaño y caen dentro de los
rangos del paper (decisión del autor).

Etapa 2: con los bloques elegidos, búsqueda bayesiana de unas 20 configuraciones
(8 al azar y el resto guiadas por las anteriores), cada una medida en los tres
años de validación. Gana la de menor error promedio, como en el paper, que usa 10.

### Cómo se comprueba que la configuración fija no sesga la selección

Con una búsqueda corta de control (decidido el 13 de noviembre): 10
configuraciones al azar dentro de los rangos de la etapa 2, las mismas en dos
casos, solo los bloques 1 y 2 y todas las variables. Cada una se mide en los tres
años de validación con una semilla. Unas 2 horas más de Colab.

Regla (decisión del autor): la configuración fija queda respaldada en un caso si
ninguna de las 10 le gana con Diebold-Mariano p < 0,05 en el error de toda la
semana.

### Qué salió en la primera corrida y qué se decidió

La corrida completa del 13 de noviembre eligió los bloques 3 (despacho de hoy) y 4
(estado hidrológico), con 16,7% de mejora en la semana en 2020-2022. Los bloques 5 y
6 empeoraron el error, y la red con todas las variables quedó en 9,0%.

La configuración fija no quedó respaldada en ninguno de los dos casos:

- Con solo precio y calendario le ganaron 6 de las 10 configuraciones, pero es en
  buena parte ruido de semilla. La búsqueda usa la semilla 0, y con ella la fija dio
  un RMSE de 0,297; con las semillas 1 y 2 dio 0,277, lo mismo que las
  configuraciones que le ganaron (0,274 a 0,281).
- Con todas las variables sí es real. Las tres semillas de la fija dan 0,272 a
  0,275, y dos configuraciones con 2 capas, dropout de 0,5 y lote de 64 bajan a
  0,256. La fija regulariza poco cuando hay muchas entradas, así que pudo castigar
  a los bloques 5 y 6.

Decisión del autor, tomada ese día después de ver estos resultados de validación y
antes de abrir el test: la selección se repite completa con la configuración de
control que le ganó a la fija con p < 0,05 en los dos casos (la número 2: 2 capas,
192 unidades, densa de 128, dropout de 0,5, tasa de 0,0028, lote de 64 y ventana de
14 días), con la misma regla y las mismas tres semillas. La selección repetida es
la que vale y la primera se reporta al lado. También se repite la comparación
contra todas las variables. Está en la sección 7 de `6c_lstm_seleccion.ipynb`.

### Qué salió en la selección repetida y qué se decidió

La selección repetida con la configuración 2 (14 de noviembre) eligió solo el bloque
3, con 13,0% de mejora en la semana. El bloque 4 mejoró la media pero no pasó la
regla (p = 0,38 en la semana) y el 5 tampoco entró. Con los pronósticos guardados
de las dos corridas (mejora frente al ingenuo del día, 2020-2022, tres semillas):

| Configuración | Bloques 3 | Bloques 3 y 4 |
|---|---|---|
| Fija | 12,6% | 16,7% |
| Configuración 2 | 13,0% | 14,2% |

- El despacho de hoy entra con las dos configuraciones.
- El agua mejora la media con las dos, sobre todo en h = 9 y en 2021-2022, pero solo
  es significativa con la fija.
- La configuración 2 gana con solo precio (6,2% contra 4,2%) y con todas las
  variables (11,6% contra 9,0%), que son los dos casos de la búsqueda de control,
  pero no con los conjuntos informativos: con los bloques 3 y 4 la fija es mejor
  con p = 0,015.

Seguir la regla del 13 de noviembre al pie de la letra dejaba solo el bloque 3, con
un modelo significativamente peor que la primera selección (p = 0,016). Elegir la
primera porque salió mejor habría sido una decisión tomada al ver el resultado.
Decisión del autor, tomada el 14 de noviembre antes de correr la búsqueda bayesiana
y el test: los dos conjuntos (bloques 1 a 3 y bloques 1 a 4) compiten en la búsqueda
bayesiana del 6d como un hiperparámetro más. También compiten, sin reentrenarse,
las cuatro combinaciones de conjunto y configuración que ya entrenó el 6c. Gana la
de menor RMSE de la semana. La búsqueda sube de 20 a 30 pruebas (10 al azar) para
que cada conjunto tenga unas 15. Las dos selecciones y esta tabla se reportan al
lado del resultado.

### Qué salió en la búsqueda bayesiana y qué se decidió

La búsqueda con los dos conjuntos (14 de noviembre) eligió con una semilla la prueba
01: bloques 3 y 4, 1 capa, 192 unidades, densa de 128, dropout de 0,3, lote de 64 y
ventana de 56 días, con RMSE de 0,2439 contra 0,2460 de la configuración fija con
los mismos bloques. Con tres semillas quedó en 12,6% de mejora, contra 16,7% de la
fija (Diebold-Mariano p = 0,011), y casi sin ganarle al ingenuo en 2020 (1,0%).

La causa es el ruido entre corridas. La misma configuración, con la misma semilla,
dio 15,5% en la búsqueda y 11,7% en la validación, porque la GPU no es del todo
determinista y eso cambia la época en que para la parada temprana. Una corrida
varía unos 4 puntos, más que la diferencia entre las mejores configuraciones. La
búsqueda de control tenía el mismo problema.

Decisión del autor, tomada el 14 de noviembre antes de correr esta evaluación y el
test: la búsqueda solo propone candidatas. Se evalúan con tres semillas las cinco
mejores de la búsqueda y compiten también las combinaciones del 6c que ya tienen
tres semillas. Gana la de menor RMSE de la semana con las tres semillas promediadas,
y con ella se repite el ensayo del procedimiento del test, con la misma regla. Las
búsquedas de una semilla se reportan al lado, como exploratorias.

En la tesis va una nota sobre el no determinismo de la GPU: los números del test no
se pueden reproducir exactamente al volver a correrlo, aunque sí las conclusiones.

La otra opción, que se descartó por tiempo, era probar tres tamaños de red en
cada paso de la selección y dejar entrar un bloque solo si ganaba en la mayoría:
unos 160 entrenamientos, 9 a 12 horas de Colab.

### Qué salió en la evaluación con tres semillas

La evaluación del 14 de noviembre (`evaluacion_tres_semillas.csv`) comparó nueve
candidatas, cada una con tres semillas. Ganó la combinación más simple: los bloques 1
a 4 con la configuración fija (1 capa, 128 unidades, densa de 64, dropout de 0,2,
tasa de 0,001, lote de 32 y ventana de 28 días), con 16,7% de mejora en la semana.
Las cinco primeras usan los bloques 1 a 4, y las cuatro últimas, los bloques 1 a 3.

| Candidata | Bloques | Mejora en la semana |
|---|---|---|
| Configuración fija (6c, primera selección) | 1 a 4 | 16,7% |
| Búsqueda, prueba 01 | 1 a 4 | 15,3% |
| Configuración 2 (6c, selección repetida) | 1 a 4 | 14,2% |
| Búsqueda, prueba 25 | 1 a 4 | 13,8% |
| Búsqueda, prueba 00 | 1 a 3 | 13,5% |
| Configuración 2 (6c, selección repetida) | 1 a 3 | 13,0% |
| Búsqueda, prueba 20 | 1 a 3 | 12,6% |
| Configuración fija (6c, primera selección) | 1 a 3 | 12,6% |
| Búsqueda, prueba 23 | 1 a 3 | 12,4% |

La prueba 01 había dado 12,6% con tres semillas en la corrida anterior y aquí dio
15,3%. Es otra muestra del ruido entre corridas: la búsqueda no encontró nada mejor
que la configuración fija.

La ganadora, entrenada otra vez con tres semillas, dio 16,6% (`validacion_criterio.csv`),
casi lo mismo que en la evaluación, así que su cifra no viene de la suerte. La mediana
de su mejor época fue 4, y ese es el número de épocas del test.

Ensayo del procedimiento del test, en 2020-2022:

| Procedimiento | h = 3 a 9 | h = 3 | h = 3 a 7 | h = 8 a 9 |
|---|---|---|---|---|
| Parada temprana | 16,6% | 23,5% | 18,2% | 14,0% |
| Como en el test (4 épocas, con todo) | 14,6% | 23,4% | 16,4% | 11,6% |

El ensayo sale 2 puntos peor, pero sin diferencia significativa: Diebold-Mariano
t = 1,73 y p = 0,083. Según la regla fijada el 13 de noviembre, se usa el
procedimiento del test y el test se abre. Las dos versiones cumplen el criterio en
los cuatro bloques. Se espera que el test quede más cerca de la cifra del ensayo
que de la de la parada temprana.

## Test

El modelo ajustado de la etapa 2 pasa una sola vez por el test: 2023-2025 y 2026
hasta el 6 de octubre, con walk-forward mensual, en las mismas filas que XGBoost y
SARIMAX. Se evalúa con el criterio de la tesis (RMSE en logaritmo al menos 5% menor
que el mejor ingenuo, con Diebold-Mariano p < 0,05) y con las métricas de
`7_resultados.ipynb`.

Cómo se entrena en el test (decisión del autor, tomada el 13 de noviembre de 2026,
antes de correr la selección completa y el test): la parada temprana aparta el
último 10% del entrenamiento, así que el
modelo no aprende de los meses más recientes. En el test, cada modelo mensual se
entrena con todos los días cuyos precios objetivo ya se conocen, sin parada
temprana, durante un número fijo de épocas: la mediana de la mejor época de la
configuración elegida en 2020-2022, con las tres semillas. Antes de abrir el test
se ensaya ese mismo procedimiento en 2020-2022, entrenando una vez por año, y se
reporta junto a la validación con parada temprana. Si el ensayo sale peor que la
parada temprana con Diebold-Mariano p < 0,05 en el error de la semana, el test no
se abre y se revisa el procedimiento; en cualquier otro caso se usa este.

Todo esto está en `6d_lstm_busqueda_y_test.ipynb`. El test y la semana final solo
corren con `CORRER_TEST = True`.

### Qué salió en el test

El test se corrió una sola vez, el 14 de noviembre de 2026, con los bloques 1 a 4,
la configuración fija y 4 épocas. Se reentrenó cada mes, en las mismas filas que
XGBoost y SARIMAX: 183.120 pronósticos en 2023-2025 y 45.864 en 2026.

Mejora del RMSE frente al mejor ingenuo, que en todos los casos es el del día
(`comparacion_criterio.csv`):

| Periodo | Modelo | Semana (h = 3 a 9) | h = 3 | h = 3 a 7 | h = 8 a 9 |
|---|---|---|---|---|---|
| 2023-2025 | LSTM | 14,9% | 24,5% | 17,5% | 10,6% |
| 2023-2025 | XGBoost | 11,6% | 17,9% | 12,5% | 10,1% |
| 2023-2025 | SARIMAX | 6,4% | 7,7% | 6,4% | 6,4% |
| 2026 | LSTM | 19,7% | 27,9% | 21,6% | 16,5% |
| 2026 | XGBoost | 10,0% | 19,5% | 11,6% | 7,2% |
| 2026 | SARIMAX | 5,6% | 6,5% | 5,6% | 5,6% |

Los tres modelos cumplen el criterio en la semana, en los dos periodos. La LSTM
cumple en los cuatro bloques. En 2023-2025 quedó cerca de la cifra del ensayo
(14,6%), como se esperaba.

Diebold-Mariano entre modelos, con el error de toda la semana (`comparacion_pares.csv`):

- En 2023-2025, la LSTM tiene menos error que XGBoost, pero la diferencia no es
  significativa (p = 0,107). Sí le gana a SARIMAX (p = 0,007).
- En 2026, la LSTM le gana a XGBoost (p = 0,033) y a SARIMAX (p = 0,011).
- Por año, la LSTM gana con claridad en 2023 (p = 0,005 contra XGBoost). En 2024
  ningún par se distingue, y en 2025 XGBoost tiene algo menos de error, sin
  diferencia significativa (p = 0,33).

La ventaja de la LSTM está en el nivel del día (`comparacion_nivel_forma.csv`). Su
error de nivel es 0,347 en 2023-2025, contra 0,385 de XGBoost y 0,415 del ingenuo.
En la forma dentro del día, en cambio, XGBoost es mejor (0,221 contra 0,249). En
pesos, la LSTM tiene el menor MAE en los dos periodos (139 contra 149 $/kWh en
2023-2025), y los tres modelos se quedan cortos en promedio (sesgo negativo).

Semana final, del 9 al 15 de octubre de 2026 (`semana_final_resumen.csv`): la LSTM
tuvo un RMSE en logaritmo de 0,252, contra 0,234 del ingenuo del día. Anticipó una
subida que no llegó del 11 al 14 de octubre. Una sola semana no mide el modelo.

## Qué es exploratorio

2020-2022 ya se usó para elegir las variables del 2e/2f, la configuración de
XGBoost y la de SARIMAX. Por eso la selección de bloques de esta LSTM se reporta
como exploratoria. El test de la LSTM nueva sí queda limpio, porque todo se decide
antes de abrirlo.

## Orden de trabajo

1. Armar el panel con los bloques 1 a 6 (`2h_panel_lstm_bloques.py`). Hecho.
2. Armar el notebook de selección para Colab (`6c_lstm_seleccion.ipynb`). Hecho,
   sin correr.
3. Correr en Colab la selección (etapa 1), la prueba de control y la búsqueda
   corta de control.
4. Búsqueda bayesiana (etapa 2) sobre los dos conjuntos, evaluación con tres
   semillas y validación del modelo elegido (`6d_lstm_busqueda_y_test.ipynb`).
   Hecho: ganan los bloques 1 a 4 con la configuración fija y 4 épocas.
5. Test, una vez, y semana final (el mismo notebook, con `CORRER_TEST = True`).
   Hecho el 14 de noviembre de 2026.
   Al final el notebook compara la LSTM con XGBoost y SARIMAX en las mismas filas:
   criterio de la tesis, mejora por horizonte, Diebold-Mariano entre cada par de
   modelos, error en pesos y nivel y forma del día. Los pronósticos de los otros
   dos modelos salen de `6e_pronosticos_para_comparar.py`.
6. Generar los pronósticos walk-forward de XGBoost y SARIMAX para 2017-2022 (en el
   computador local) y probar el bloque 7, que se reporta aparte.

## Tiempo estimado en Colab (GPU L4)

| Parte | Entrenamientos | Horas |
|---|---|---|
| Selección, bloques 1 a 6 | unos 45 | 2,5 a 3,5 |
| Control con todas las variables | 9 | 0,5 |
| Bloque 7 | 18 | 1 |
| Selección repetida con la configuración 2 | unos 45 | 1 a 1,5 |
| Búsqueda bayesiana con los dos conjuntos | 30 configuraciones × 3 años | 4,5 a 6 |
| Evaluación con tres semillas y ensayo | unos 40 a 50 | 1,5 a 2,5 |

## Referencias

- Diebold, F. y Mariano, R. (1995). Comparing predictive accuracy. *Journal of
  Business & Economic Statistics*, 13(3), 253-263.
- Hochreiter, S. y Schmidhuber, J. (1997). Long short-term memory. *Neural
  Computation*, 9(8), 1735-1780.
- Salazar-Peña, N. et al. (2025). Intra-day Solar and Power Forecast for
  Optimization of Intraday Market Participation. Preprint, arXiv:2501.09551v3.
- Smith, J. y Wallis, K. (2009). A simple explanation of the forecast combination
  puzzle. *Oxford Bulletin of Economics and Statistics*, 71(3), 331-355.
- Sutskever, I., Vinyals, O. y Le, Q. (2014). Sequence to sequence learning with
  neural networks. *Advances in Neural Information Processing Systems*, 27.
- Timmermann, A. (2006). Forecast combinations. En G. Elliott, C. Granger y A.
  Timmermann (Eds.), *Handbook of Economic Forecasting*, vol. 1, 135-196.
