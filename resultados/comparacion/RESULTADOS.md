# Resultados con el formato del paper

Los genera `7_resultados.ipynb` a partir de los pronósticos del test que ya guardó cada
modelo. No entrena nada ni repite el test. El formato sigue a Salazar-Peña et al. (2025),
*Intra-day Solar and Power Forecast for Optimization of Intraday Market Participation*,
arXiv:2501.09551v3: MAE, RMSE, nRMSE, MBE y MAPE por horizonte con intervalo t al 95%,
skill score contra una referencia, MAPE por hora del día, el mejor modelo por horizonte y
hora, semanas de ejemplo con su correlación y tablas de hiperparámetros.

La LSTM entra sola cuando existan `resultados/modelo_lstm/prueba_2023_2025.csv.gz` y
`prueba_2026.csv.gz`, con `fecha`, `hora`, `h` e `y_hat`, como XGBoost.

## Semana completa (h = 3 a 9)

En COP/kWh, salvo los porcentajes. El skill score es 1 − RMSE / RMSE del ingenuo del día.

| | XGBoost | SARIMAX | Ingenuo del día |
|---|---|---|---|
| MAE, 2023-2025 | 148,6 | 148,8 | 150,1 |
| RMSE, 2023-2025 | 247,5 | 242,1 | 257,1 |
| nRMSE, 2023-2025 | 50,4% | 49,3% | 52,3% |
| MBE, 2023-2025 | −46,4 | −15,3 | 1,3 |
| MAPE, 2023-2025 | 36,2% | 39,0% | 40,1% |
| Skill score, 2023-2025 | 3,7% | 5,8% | |
| RMSE, 2026 | 175,7 | 176,5 | 188,5 |
| MAPE, 2026 | 29,5% | 30,4% | 32,4% |
| Skill score, 2026 | 6,8% | 6,4% | |

Skill score por horizonte, 2023-2025:

| h | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|
| XGBoost | 13,1% | 9,3% | 10,3% | 3,3% | −1,4% | −0,5% | 0,4% |
| SARIMAX | 6,5% | 6,4% | 6,6% | 5,5% | 4,4% | 5,6% | 6,0% |

## Cómo leerlo

- **En COP/kWh la comparación no es la misma que en logaritmo.** Con el criterio de la tesis
  (RMSE del logaritmo), XGBoost mejora 11,6% y SARIMAX 6,4% en 2023-2025. En COP/kWh, 3,7% y
  5,8%: XGBoost gana de h = 3 a 5 y SARIMAX de h = 6 a 9.
- **La razón es la vuelta a COP/kWh.** Los modelos pronostican el logaritmo; exp(ŷ) queda
  cerca de la mediana y no de la media. Con un error en logaritmo de unos 0,44, la media es
  cerca de 10% mayor que la mediana, y XGBoost pronostica en promedio 46 COP/kWh por debajo
  del real (unos 9% del precio medio). En COP/kWh, además, pesan más los meses caros.
- **El MAPE favorece a XGBoost** (164 de 168 celdas), en parte porque castiga más pronosticar
  por encima que por debajo.
- **Los intervalos al 95% se cruzan** en casi todos los horizontes.

Los resultados principales de la tesis siguen siendo los del criterio fijado antes del test,
en logaritmo (`resultados/modelo_xgboost/RESULTADOS.md` y `resultados/modelo_sarimax/RESULTADOS.md`).
Este formato es una segunda lectura, en las unidades del paper.

## Archivos

- `metricas_semana.csv`, `metricas_por_horizonte.csv`, `intervalos_por_horizonte.csv`
- `mape_por_hora_2023_2025.csv`, `semanas_de_ejemplo.csv`
- `error_por_horizonte_2023_2025.png`, `error_por_horizonte_2026.png`: MAE, RMSE y MBE por horizonte
- `nrmse_y_skill_por_horizonte.png`
- `mape_por_hora_2023_2025.png`
- `mejor_modelo_mae_2023_2025.png`, `mejor_modelo_rmse_2023_2025.png`, `mejor_modelo_mape_2023_2025.png`
- `semanas_de_ejemplo.png`, `correlacion_2023_2025.png`
