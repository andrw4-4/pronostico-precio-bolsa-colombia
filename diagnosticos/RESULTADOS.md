# Diagnósticos

Tres análisis sobre por qué el pronóstico se queda donde se queda. No son modelos para usar:
explican el límite. Se corren desde la raíz del repo, solo imprimen y no cambian nada.

```bash
python diagnosticos/diagnostico_errores.py
python diagnosticos/oraculo.py
python diagnosticos/pronosticar_ofertas.py
```

## 1. Dónde falla XGBoost (`diagnostico_errores.py`)

Sobre los pronósticos guardados, h = 3 a 9, de 2023 a 2026. Usa datos de test, así que es
exploratorio: sirve para entender, no para ajustar el modelo.

| Qué se midió | Resultado |
|---|---|
| Nivel del día contra forma | 75% del error cuadrático es nivel y 25% forma |
| Mejora frente al ingenuo del día | 7% en el nivel y 21,5% en la forma |
| Movimientos grandes (más de 0,7 en log) | 14% de las filas y 57% del error |
| Caídas fuertes | Real −1,08 en promedio, pronóstico −0,20 |
| Subidas fuertes | Real +1,03 en promedio, pronóstico +0,32 |
| Hora del pico | Exacta 41% de los días, con ±1 hora 70% |
| Pico real más de 1,5 veces el pronosticado | 20% de los días |
| Horas con el mismo precio de la hora anterior | 55% |
| Madrugada, horas 1 a 6 | 32% del error en log |
| Horas 18 a 21 | 15% del error en log, con sesgo de +0,08 |

No resultaron ser problema: un día base raro, que el modelo corrige; el día de la semana; y la
escala de los pronósticos, con pendiente de 0,91. Frente a un ingenuo más exigente, la media de 7
días, el modelo sigue ganando (0,434 contra 0,500).

## 2. Oráculo (`oraculo.py`)

Le da a XGBoost valores futuros reales del día objetivo, que nadie tendría al pronosticar. Mide qué
información falta. En 2020-2022, con la configuración congelada. Mejora del RMSE frente al ingenuo
del día:

| Lo que recibe el modelo | h = 3 | h = 7 |
|---|---|---|
| Lo que tiene hoy | 18,4% | 8,3% |
| + demanda futura | 19,5% | 8,5% |
| + hidrología futura | 19,0% | 11,1% |
| + demanda e hidrología | 20,2% | 11,1% |
| + ofertas futuras | 35,8% | 39,5% |
| + todo | 35,0% | 40,3% |

El error del nivel del día en h = 7 baja de 0,250 a 0,241 con demanda e hidrología, y a 0,145 con
las ofertas. La información que falta es cómo ofertarán los generadores. Saber las ofertas es casi
saber el precio, así que 39,5% es un techo teórico, no una meta.

## 3. Pronosticar las ofertas (`pronosticar_ofertas.py`)

Las ofertas se publican unos 10 días tarde, así que hay que anticiparlas entre 11 y 15 días para
estos horizontes. En 2020-2022, siempre con pronósticos fuera de muestra y purga por el atraso.

| Variable | Correlación h = 3 | Mejora contra el último dato | Correlación h = 7 | Mejora contra el último dato |
|---|---|---|---|---|
| `oferta_marginal` | 0,92 | 43,7% | 0,84 | 23,6% |
| `margen_ofertado` | 0,91 | 51,3% | 0,90 | 41,2% |
| `holgura_rel` | 0,91 | 46,2% | 0,90 | 29,1% |
| `cap_bajo_200_rel` | 0,91 | 39,9% | 0,82 | 20,2% |
| `cap_bajo_500_rel` | 0,84 | 35,0% | 0,77 | 20,5% |
| `oferta_dispersion` | 0,38 | 11,3% | 0,34 | 18,9% |

Se pueden pronosticar, pero casi no ayudan al precio. Mejora del RMSE frente al ingenuo del día:

| Modelo, entrenado desde 2018 | h = 3 | h = 7 |
|---|---|---|
| Actual | 17,6% | 6,6% |
| + ofertas pronosticadas | 18,4% | 6,7% |
| + ofertas reales | 34,9% | 36,3% |

Lo pronosticable de las ofertas sale de los mismos datos que el modelo ya tiene, sobre todo del
precio reciente, que llega 8 días antes. Lo que mueve el precio es la sorpresa en cómo oferta cada
generador.

## Conclusión

Con datos públicos, el precio se puede pronosticar a una semana con una mejora de 10 a 12% sobre el
ingenuo. Más clima o demanda casi no ayuda, incluso con datos perfectos, y pronosticar las ofertas
tampoco. La ganancia grande exige conocer ofertas que aún no existen o no se han publicado.

**Límites.** Son 2 horizontes, con 11 variables de oráculo y 6 de ofertas, y parámetros congelados.
No descarta lo que podría lograr un modelo de la curva completa por planta, ni mide lo que un
agente con información privada podría hacer.
