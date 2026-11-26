# Experimento de decisión

Reglas escritas el 26 de noviembre de 2026, antes de calcular ningún resultado de este experimento.
Responden al objetivo 3 de la tesis: comparar los modelos por el valor que tienen para tomar una
decisión, y no solo por su error.

## Qué se sabía al escribir estas reglas

- Los pronósticos de SARIMAX, XGBoost y la LSTM en 2023-2025 y 2026 ya existían y sus errores ya
  se habían visto. El experimento no reentrena nada: usa esos pronósticos tal como quedaron
  guardados.
- El 19 de noviembre de 2026 se calculó otro ejercicio de decisión, distinto de este: elegir el día
  más barato de la semana y comprar un bloque plano de un comercializador. Ese ejercicio se retiró
  del informe y no se usa aquí. Sus resultados sí se conocían al escribir estas reglas.
- Las dos decisiones, las referencias y la medida de abajo las propuso la asesora en sus
  comentarios del 26 de noviembre de 2026. No se eligieron mirando resultados.

Por eso este experimento no es una prueba limpia: es un cálculo con reglas fijadas de antemano
sobre pronósticos ya conocidos.

## Datos

- Las mismas filas de la prueba: orígenes t de 2023-2025 y de 2026 hasta el 6 de octubre.
- Solo entran los orígenes con la semana completa, es decir, con los siete días t + 3 a t + 9
  dentro del periodo (1.087 orígenes en 2023-2025 y 270 en 2026).
- El pronóstico en pesos es P(t, H) por la exponencial del cambio pronosticado, sin corrección de
  sesgo. El costo siempre se mide con el precio real, en COP/kWh.

## Decisión 1: elegir días

Un consumidor debe ubicar dos días de consumo plano dentro de la semana pronosticada (t + 3 a
t + 9). Elige los dos días con el menor precio medio pronosticado. Su costo es el precio medio
real de las 48 horas de esos dos días.

## Decisión 2: elegir horas

En cada uno de los siete días pronosticados, el consumidor elige las cuatro horas más baratas
según el pronóstico. Su costo es el precio real medio de esas cuatro horas. El costo de un origen
es el promedio de sus siete días.

## Empates

Si dos días o dos horas tienen el mismo precio pronosticado, se elige el que va primero en el
tiempo.

## Referencias

| Referencia | Elegir días | Elegir horas |
|---|---|---|
| Al azar | costo esperado: el precio medio real de la semana | costo esperado: el precio medio real del día |
| Ingenuo semanal | sí | sí |
| Ingenuo del día | no: pronostica el mismo nivel para los siete días | sí |
| Información perfecta | los dos días realmente más baratos | las cuatro horas realmente más baratas |

## Medida

La fracción del ahorro posible que captura cada pronóstico:

    captura = (C_azar - C_modelo) / (C_azar - C_perfecto)

C es el costo promedio sobre los orígenes del periodo. La captura se calcula con esos promedios
(suma de ahorros sobre suma de ahorros posibles), no promediando la razón de cada origen. Vale 1
con información perfecta y 0 si el pronóstico no sirve más que elegir al azar; puede ser negativa.

Se reporta por periodo (2023-2025 y 2026) y por año del origen.

## Prueba estadística

Prueba pareada sobre las diferencias de costo por origen, con error estándar de Newey-West con 15
rezagos (los mismos de la semana completa, porque las semanas de orígenes seguidos se traslapan) y
la corrección de Harvey, Leybourne y Newbold (1997). Se prueba:

1. Cada pronóstico contra la elección al azar.
2. Cada par de modelos entre sí.

## Modelos

Los tres de la tesis (SARIMAX, XGBoost y LSTM) y los dos ingenuos. También se calculan, marcados
como agregados después de abrir la prueba, los modelos de la revisión: LEAR, el XGBoost con la
información alineada y las combinaciones.

## Qué se concluye

- Si la LSTM captura más que XGBoost al elegir días y XGBoost más que la LSTM al elegir horas,
  con diferencias significativas, la recomendación del capítulo V (LSTM para elegir días y XGBoost
  para elegir horas) queda respaldada.
- Si no, la recomendación se corrige o se retira.

El código está en `9e_decision.py` y los resultados quedan en `resultados/revision/`.
