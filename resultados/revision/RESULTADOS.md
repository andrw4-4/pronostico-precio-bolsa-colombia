# Resultados de la revisión del 26 de noviembre de 2026

Responde a los comentarios de la asesora al Informe 1. Nada de lo que la tesis había fijado se
cambió: los modelos nuevos se corrieron aparte y sus cifras de 2023-2026 son de modelos agregados
después de abrir la prueba. El estado anterior quedó con la etiqueta de git `informe-1`.

Todas las mejoras son del RMSE en logaritmo de la semana completa (h = 3 a 9) frente al mejor
ingenuo. Los valores p de Diebold-Mariano llevan la corrección de Harvey et al. (1997).

## 1. Modelo e información (`dos_por_dos.csv`, `todos_criterio.csv`)

| Modelo | Información | 2020-2022 | 2023-2025 | 2026 |
|---|---|---|---|---|
| SARIMAX | precio y calendario | 4,7% | 6,4% | 5,6% |
| LEAR | cortada en t | 9,0% | 9,9% | 14,0% |
| XGBoost | cortada en t | 11,6% | 11,6% | 10,0% |
| LSTM, bloques 1 y 2 | cortada en t | 5,7% | 6,1% | 8,8% |
| LEAR | alineada a su publicación | 19,7% | 21,3% | 24,8% |
| XGBoost | alineada a su publicación | 18,7% | 18,5% | 22,4% |
| LSTM (la de la tesis) | alineada a su publicación | 17,1% | 14,9% | 19,7% |
| Promedio de los tres de la tesis | | | 15,6% | 17,3% |
| Nivel de la LSTM y forma de XGBoost | | | 18,0% | 22,9% |

- Con la misma información, la LSTM no le gana a XGBoost ni a LEAR. Con la información alineada,
  XGBoost tiene menos error que la LSTM en los tres periodos (p = 0,32, 0,04 y 0,26).
- Con la información cortada en t, XGBoost le gana a la LSTM en 2020-2022 y 2023-2025 (p = 0,001).
- Pasar de la información cortada en t a la alineada mejora los dos modelos, siempre con p < 0,01.
- La ventaja de la LSTM de la tesis frente al XGBoost de la tesis venía de la información.

## 2. Primera LSTM (`../modelo_lstm_v1/`)

Pasó por la prueba el 2 de noviembre de 2026: 12,0% en 2023-2025 y 12,9% en 2026. La LSTM de la
tesis se diseñó después. La repetición del 26 de noviembre (`9j_lstm_v1_repeticion.py`), con el
mismo código, panel, configuración y semilla, dio 11,6% y 14,7% y cumple el criterio en los cuatro
bloques, también con la corrección de Harvey et al. (1997); sus pronósticos están en la carpeta y
su fila, en `tabla15_ampliada.csv`.

## 3. Periodo limpio (`../periodo_limpio/criterio.csv`)

Orígenes del 7 de octubre al 20 de noviembre de 2026 (45; 39 con la semana completa), con el
precio publicado hasta el 23 de noviembre. El mejor ingenuo es el semanal (RMSE 0,400).

| Modelo | Mejora | p |
|---|---|---|
| XGBoost alineado | 18,6% | 0,09 |
| Promedio de los tres | 16,2% | 0,22 |
| Nivel LSTM y forma XGBoost | 13,4% | 0,48 |
| XGBoost | 11,7% | 0,16 |
| LEAR | 11,7% | 0,31 |
| LEAR alineado | 11,2% | 0,09 |
| SARIMAX con día de la semana | 10,9% | 0,20 |
| LSTM, bloques 1 y 2 | 9,5% | 0,19 |
| SARIMAX | 9,3% | 0,26 |
| LSTM | 8,3% | 0,63 |

Todos reducen el error y ninguno de forma significativa: con 45 orígenes la prueba tiene poca
potencia. Solo 9 orígenes tienen su semana después del 14 de noviembre, la fecha de la última
decisión; no alcanzan para una prueba.

## 4. Atraso del precio (`atraso3.csv`)

- Tres consultas a la API dieron 3, 2 y 3 días (9 y 10 de octubre y 26 de noviembre de 2026).
- Con tres días de atraso la semana pronosticable es h = 4 a 10. Los tres modelos siguen cumpliendo
  el criterio: SARIMAX 6,5% y 5,8%, XGBoost 11,2% y 8,7%, LSTM 18,8% y 23,3%.
- XM corrigió todos los precios de los 31 días anteriores al 6 de octubre entre la descarga del 9
  de octubre y la del 26 de noviembre (`../../periodo_limpio/comprobacion_paneles.csv`): en
  promedio pocos pesos, pero en algunas horas varios cientos. El precio que se conoce al pronosticar
  es una versión provisional.

## 5. SARIMAX con día de la semana (`../modelo_sarimax_dia_semana/`)

Gana en validación con la regla de la tabla 5 (RMSE 0,2805 a 0,2776, p < 0,001). Las horas sin
autocorrelación a 21 rezagos pasan de 6 a 17 de 24.

## 6. Otros análisis

- `criterio_hln.csv`: la corrección cambia un solo veredicto (XGBoost, 2026, h = 8 a 9: p de 0,047
  a 0,056).
- `mediana_error.csv`: en 2023-2025 la mediana del error absoluto de SARIMAX y XGBoost es peor que
  la del ingenuo del día; la de la LSTM es igual.
- `episodios.csv`: en El Niño (septiembre de 2023 a abril de 2024) la LSTM mejora 18,6%; en el
  déficit de aportes de agosto a noviembre de 2024, con el ONI neutro, ningún modelo se distingue
  del ingenuo (LSTM 1,6%, XGBoost 4,0%, SARIMAX 8,2%).
- `regimenes.csv`: con aportes bajos, SARIMAX 4,1%, XGBoost 6,8% y LSTM 11,7%.
- `diseno_30_dias.csv`: los cuatro bloques del diseño original de XGBoost; en 2026 no cumplen
  h = 8 a 14 (6,4%, p = 0,11) ni h = 15 a 30 (−7,2%).
- `origenes.csv`: una sola regla para los orígenes de cada periodo.
- Las cifras de SARIMAX de la tabla 15 no son un error de copia: 6,41, 6,40 y 6,42.

## 7. Experimento de decisión (`decision.csv`, reglas en `docs/EXPERIMENTO_DECISION.md`)

Fracción del ahorro posible que captura cada pronóstico:

| Pronóstico | Días, 2023-2025 | Días, 2026 | Horas, 2023-2025 | Horas, 2026 |
|---|---|---|---|---|
| Ingenuo semanal | 0,20 | 0,24 | 0,81 | 0,83 |
| Ingenuo del día | | | 0,76 | 0,76 |
| SARIMAX | 0,32 | 0,35 | 0,77 | 0,82 |
| XGBoost | 0,32 | 0,32 | 0,83 | 0,78 |
| LSTM | 0,35 | 0,55 | 0,78 | 0,76 |
| LEAR | 0,41 | 0,57 | 0,89 | 0,77 |

- Elegir días: la LSTM le gana a XGBoost solo en 2026 (p < 0,001); en 2023-2025 no se distinguen
  (p = 0,51).
- Elegir horas: XGBoost le gana a la LSTM en 2023-2025 (p < 0,001) y no en 2026. El ingenuo
  semanal captura tanto como los modelos, y en 2026 más que XGBoost y la LSTM (p < 0,01).
- La recomendación de usar la LSTM para elegir días y XGBoost para elegir horas queda respaldada
  solo en parte.
