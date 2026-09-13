# Pronóstico del precio de bolsa de energía en Colombia

Pipeline de datos y modelos para pronosticar el precio de bolsa horario/diario
del mercado eléctrico colombiano (XM/SIMEM), con XGBoost como modelo principal
y una auditoría automática de fuga de información.

## Estructura del pipeline

Los scripts se corren en orden; cada uno depende de las salidas del anterior.

| Paso | Script | Qué hace |
|---|---|---|
| 00 | `00_consolidar_panel.py` | Consolida las series de `cache_api/` (no incluido en este repo) en un panel diario |
| 01 | `01_seleccion_variables.py` | Selecciona variables con datos hasta 2019 (ADF, Granger, información mutua, Lasso, permutación) |
| 02 | `02_evaluacion_bloques.py` | Evalúa bloques temáticos con walk-forward y Diebold-Mariano sobre 2020-2022 |
| 03 | `03_bloques_candidatos.py` | Combina bloques, corrige por multiplicidad (FDR) y fija el modelo final |
| 06 | `06_auditoria.py` | Verifica mecánicamente que no haya fuga temporal ni inconsistencias entre etapas |
| 04 | `04_xgboost.ipynb` | XGBoost sobre el precio en nivel, prueba 2023-2025 |
| 05 | `05_xgboost_diferencia.ipynb` | XGBoost sobre la diferencia del log-precio, misma prueba |

`correr_pipeline.py` ejecuta todo en este orden con un solo comando:

```bash
python correr_pipeline.py
```

## Períodos (sin traslape)

- **Selección de variables:** 2015-01-01 a 2019-12-31
- **Validación (elección de bloques):** 2020-01-01 a 2022-12-31
- **Prueba (métricas finales):** 2023-01-01 a 2025-12-31

## Datos

Este repositorio **no incluye los datos crudos** (`cache_api/`, `data/`,
`Datos que usaré/`), por tamaño y porque provienen de fuentes externas:

- Series de XM vía [SIMEM](https://www.simem.co/) / `pydataxm`
- Índice ONI de El Niño: [NOAA CPC](https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php)
- TRM: [Banco de la República](https://www.banrep.gov.co/)

Para reproducir el panel, descarga esas series con la estructura de columnas
que espera `00_consolidar_panel.py` (ver los comentarios del script) y colócalas
en `cache_api/` y `data/`.

## Auditoría de fuga

`06_auditoria.py` corre chequeos mecánicos agrupados en temporalidad, split,
construcción de features, coherencia entre etapas y calidad de datos. Un
veredicto sin FAIL no prueba que el modelo sea bueno, solo que el proceso de
selección y evaluación es válido.
