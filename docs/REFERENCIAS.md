# De dónde sale cada parte del código

Cada técnica que no es obvia está aquí con su fuente. Hay tres tipos:

- **Guía:** un cuaderno de los repos guía (en `material_de_apoyo/Repos guia/`)
  o una clase del curso SLDA (en `../SLDA/Codes/_ORGANIZADO/`).
- **Artículo o libro:** cuando la técnica no está en las guías, se cita la
  fuente original.
- **Propia:** decisiones que no salen de una guía. Se dice por qué se tomaron y
  cómo se comprobaron.

En el código, cada una de estas partes tiene un comentario `Fuente:` que remite
a esta tabla.

## Descarga de datos (`1_descargar.py`, `1b_ideam.py`)

| Qué | Dónde | Fuente |
|---|---|---|
| Series de XM | `bajar_xm`, `actualizar_xm` | Librería `pydataxm` de XM (`ReadDB.request_data`). Los códigos de métrica salen de su catálogo, `ReadDB().inventario_metricas` |
| Conjuntos de SIMEM (pronóstico de demanda, costo marginal, holgura, arranques, reserva) | `pedir_simem`, `bajar_simem` | Servicio público de SIMEM (`simem.co/backend-files/api/PublicData`), el mismo que usa por dentro `pydataxm.pydatasimem`. El catálogo es el conjunto `e007fb` |
| Repasar el último mes al actualizar | `REPASO_DIAS` | Propia: XM corrige las liquidaciones provisionales durante varias semanas |
| Leer los boletines del IDEAM | `1b_ideam.py` | Librería `pypdf` (extracción de texto con `visitor_text` para tener la posición de cada palabra en la página) |

## Panel diario (`2_construir_panel.py`)

Las partes 1 a 9 están explicadas una por una en `DOCUMENTACION.md`, sección 4.
Lo que no sale de una guía es la curva de mérito (parte 9): se construye con las
ofertas diarias de cada planta y su disponibilidad, siguiendo la regla de
formación del precio de la CREG (ver la fila de la curva horaria abajo).

## Panel horario (`2b_panel_horario.py`)

| Qué | Dónde | Fuente |
|---|---|---|
| Curva de mérito hora por hora | `curva_horaria` | Regulación: el precio de bolsa de cada hora es el ofertado por la planta marginal no restringida despachada en esa hora (CREG 055 de 1994, art. 14), y cada planta oferta una vez al día con un solo precio para las 24 horas (CREG 025 de 1995, Código de Operación, numeral 3.1). La construcción con los datos es propia: se comprobó que en todo el archivo ninguna planta cambia su precio entre horas, y la oferta marginal calculada tiene correlación de 0,94 con el precio de la misma hora (no 1, porque XM usa su despacho ideal, con inflexibilidades y arranques). La curva toma la oferta de cada hora, por si las ofertas empiezan a variar: la Resolución CREG 101 113 de 2026 cambió la redacción del art. 6 de la CREG 055 a precios "por unidad de energía generada cada hora en el día siguiente" |
| Generación por tecnología | `por_tecnologia` | Propia, con el listado de plantas de PARATEC (XM) |
| Hora de SIMEM frente a la de XM | `leer_simem` | Propia y comprobada: con hora = `FechaHora.hour + 1` coinciden las 240 horas de costo marginal de junio de 2025 |
| Quedarse con la última versión de cada dato (TXR, TX1…TX8, TXF) | `ultima_version` | Convención de liquidación de XM: TXR es la preliminar y TXF la final |
| Proyección de reserva solo con ejecuciones anteriores al día | `bloque_reserva` | Propia, para que no haya fuga: una hora solo toma proyecciones hechas antes de su día |
| Huecos de eventos como cero | `EVENTOS` | Guía: imputación por valor arbitrario, Galli, `Section-05-Missing-Data-Imputation/02-pandas/02-Arbitrary-Value-Imputation.ipynb`. Que el valor sea 0 es propio: XM no publica fila cuando el evento no ocurre |

## Características del panel diario (`features.py`)

| Qué | Dónde | Fuente |
|---|---|---|
| Logaritmo del precio | `construir_features` | Galli, `Section-11-Variable-Transformation/01-numpy-scipy/01-logarithmic-transformation.ipynb` |
| Diferencias y cocientes frente a una referencia (choques `x − media`, `x / demanda`) | `construir_features` | Galli, `Section-17-Feature-creation/01-sklearn/02-Comparing-features-to-reference-variable.ipynb` |
| Calendario (día de la semana, festivos) | `construir_features` | Galli, `Section-15-Date-Time-Features/01-pandas/01-Extracting-date-related-features.ipynb` |
| Eventos con 0, el resto con el último valor | `preparar_panel` | 0: Galli, `Section-05.../02-Arbitrary-Value-Imputation.ipynb`. Último valor: propia, porque solo mira hacia atrás y no mete información del futuro |
| Quitar columnas constantes | `limpiar_matriz` | Naik, `Complete-Feature-Selection/1. Feature Selection- Dropping Constant Features.ipynb` |
| Quitar columnas con correlación > 0,95 | `limpiar_matriz` | Naik, `Complete-Feature-Selection/2-Feature Selection- Correlation.ipynb` |
| Quitar combinaciones lineales exactas (rango de la matriz) | `limpiar_matriz` | Propia. Por construcción `x_choque7 = x_lag1 − x_ma7`, y con las tres juntas una regresión no puede separar sus efectos. Los materiales de SLDA no tratan este punto (la palabra solo aparece en un aviso de sklearn en la clase 12) |
| `shift(1)` antes de cada ventana móvil | `construir_features` | Propia: es la regla que evita la fuga; se comprueba alterando el día t y viendo que ninguna característica de ese día cambie |

## Características del panel horario (`2c_caracteristicas_horarias.py` y el catálogo de `features.py`)

| Qué | Dónde | Fuente |
|---|---|---|
| Logaritmo del precio, de las ofertas y de los precios regulados | `variables_base`, `log_pos` | Galli, `Section-11-Variable-Transformation/01-numpy-scipy/01-logarithmic-transformation.ipynb` |
| Cantidades como fracción de la demanda o la generación de la hora | `variables_base` | Galli, `Section-17-Feature-creation/01-sklearn/02-Comparing-features-to-reference-variable.ipynb` |
| Diarias sobre la media móvil de 7 días de la demanda diaria (`dem7`) | `variables_base`, `media_dias` | La división frente a una referencia: Galli, sección 17 (la misma de arriba). Que la referencia sea la media de 7 días es propio: solo mira hacia atrás y no mete el ruido de domingos y festivos |
| Eventos con 0 | `evento` | Galli, `Section-05-Missing-Data-Imputation/02-pandas/02-Arbitrary-Value-Imputation.ipynb`. Que sea 0: XM no publica fila cuando el evento no ocurre |
| Relleno de huecos sueltos con la misma hora del día anterior (hasta 3 días) | `rellenar` | Propia: solo mira hacia atrás |
| Filtro de calidad: sin variación o con más de 1% de faltantes | `calidad` | Quitar columnas constantes: Naik, `Complete-Feature-Selection/1. Feature Selection- Dropping Constant Features.ipynb`. El umbral de 1% es propio |
| Calendario tal cual y del día objetivo | `calendario` | Galli, `Section-15-Date-Time-Features/01-pandas/01-Extracting-date-related-features.ipynb`. Tomar el día que se pronostica en cada horizonte es propio |
| Calendario cíclico (seno y coseno de la hora, el día de la semana, el día del año y el mes) | `ciclico`, `calendario` | Galli, `Section-15-Date-Time-Features/01-pandas/03-periodic-features.ipynb` y `02-feature-engine/02-periodic-features.ipynb` |
| Variables nuevas: `error_cmg_despacho`, `brecha_escasez`, `presion_hidro_horaria`, `dias_autonomia`, `aportes_caudal_pct` | `variables_base` | Propias, del plan de variables revisado; lo que se ajustó con los datos está en `PANEL_HORARIO.md` |
| Rezagos del precio: las 24 horas del día y los días 1, 2, 3 y 7 | `features._columnas_precio` | Lago et al. (2021), modelo LEAR. Los días 14, 21 y 28 son propios, por la autocorrelación parcial del precio en 2015-2019 |
| Medias móviles de día, semana y mes | `_columnas_precio`, `_columnas_horaria`, `_columnas_diaria` | Corsi (2009), modelo HAR |
| Rampa del día, tendencia (`ma7_menos_ma30`, `delta_7d`), variabilidad y memoria de picos | `_del_dia`, `_misma_hora`, `_ultimas_horas` | Propia, del plan de variables: que el modelo vea la forma del día, si la variable viene subiendo o bajando, qué tan agitada está y si hubo un pico reciente |
| Una ventana se calcula con al menos 75% de sus datos | `MIN_EN_VENTANA` | Propia: así un hueco suelto no borra un mes de medias |
| Todas las columnas en una sola matriz float32, sin `concat` en ciclo | `_a_tabla` | Propia, por memoria: 1.920 columnas caben en 806 MB |
| Prueba de fuga sobre todo el flujo | `comprobar_sin_fuga` | Propia: se alteran los datos crudos posteriores a un día y se corre todo de nuevo; nada anterior puede cambiar, salvo las `_manana` |

## Selección de variables del panel horario (`2d_seleccion_variables.py`)

| Qué | Dónde | Fuente |
|---|---|---|
| Quitar columnas constantes o casi constantes | `limpieza` | Naik, `Complete-Feature-Selection/1. Feature Selection- Dropping Constant Features.ipynb`. El umbral de 99% es propio |
| Quitar columnas inestables (más de 25% de 2018-2019 fuera del rango de 2015-2017) | `limpieza`, `MAX_FUERA_DE_RANGO` | Propia, por el diagnóstico de h = 7: las columnas que más empeoraban en 2020-2022 eran niveles que se corren con el tiempo y quedaban fuera del rango de entrenamiento, donde un árbol no extrapola. La fórmula solo usa 2015-2019, pero la decisión de ponerla y el umbral de 25% se tomaron mirando 2020-2022 |
| Del cargo por confiabilidad y la TRM entran solo las columnas de cambio | `limpieza`, `SOLO_CAMBIO` | El cargo se fija en dólares y se actualiza cada 1 de diciembre con el índice de precios al productor de Estados Unidos: Resolución CREG 071 de 2006, art. 29. Que en pesos se mueva con la TRM se vio en los datos (cambios diarios con correlación de 0,97). La regla es propia y salió de mirar 2020-2022: la caída de h = 14 por `precio_cargo_conf_ma30d` |
| Quitar columnas redundantes (correlación > 0,95) | `limpieza` | Naik, `Complete-Feature-Selection/2-Feature Selection- Correlation.ipynb`. Tres cambios: de cada grupo queda la más correlacionada con el objetivo (decisión del autor); solo se compara con las que ya quedaron; y la correlación es de Spearman, para que no la muevan los picos (propia) |
| Importancia de las columnas con un modelo de árboles | `ordenar` | SLDA, clase 15, `code1_class15.txt` (`importance()` con bagging y random forest). XGBoost: Chen y Guestrin (2016); ML Zoomcamp, `06-trees/07-boosting.md` |
| Configuración fija de XGBoost | `PARAMETROS` | La del medio de la rejilla de `legacy/experimentos_xgboost/4_experimentos_xgboost.ipynb`, que sale de ML Zoomcamp, `06-trees/08-xgb-tuning.md`. No se ajusta: solo sirve para ordenar |
| Valores SHAP | `ordenar` (`pred_contribs=True` de XGBoost) | Lundberg y Lee (2017); para árboles, el algoritmo exacto de Lundberg et al. (2020) |
| Medir la importancia en un año que el modelo no vio | `ordenar`, `CORTES` | Propia: así la importancia es la del uso del modelo con datos nuevos y no la del ajuste |
| Columnas de ruido como umbral | `columnas_de_ruido` | Kursa y Rudnicki (2010), Boruta (columnas sombra). Aquí son 10 y no una por columna, para que alcance el tiempo |
| Cuántas columnas: regla de un error estándar | `cuantas` | SLDA, clases 7 y 8 (`SLDA_class7_book3_penalty.ipynb`, `SLDA_class8_book1_penalty.ipynb`); Hastie, Tibshirani y Friedman (2009), sección 7.10 |
| Error estándar del error medio por día | `media_y_error_estandar` | Newey y West (1987), con h − 1 + 7 rezagos como en el Diebold-Mariano de `4_modelo_xgboost.ipynb` |
| Purga de h+1 días entre entrenamiento y evaluación | `ordenar`, `cuantas` | López de Prado (2018), capítulo 7 |
| Las columnas de la selección no leen la prueba | `matriz` | Propia: la función que arma las matrices se niega a leer filas posteriores a 2022. No vigila la respuesta: los objetivos de los últimos h días de 2022 caen en enero de 2023 |

## Selección lineal anterior (`legacy/seleccion_lineal/2d_seleccion_lineal.py`)

Con ella se obtuvieron los resultados de `legacy/experimentos_xgboost/`.

| Qué | Dónde | Fuente |
|---|---|---|
| Prueba ADF para decidir nivel o desviación | `probar_estacionariedad` | Dickey y Fuller (1979); implementación `statsmodels.tsa.stattools.adfuller` con rezagos por AIC. KPSS (Kwiatkowski et al., 1992) solo se reporta |
| Desviación frente al promedio de 28 días a la misma hora | `transformar` | Galli, `Section-17.../02-Comparing-features-to-reference-variable.ipynb` (diferencia frente a una referencia) |
| Puntajes normales (rango llevado a la normal) | `puntajes_normales` | Beasley, Erickson y Allison (2009) |
| Selección hacia adelante | `adelante` | SLDA, clases 5 a 7, `SLDA_class5_book1_variable_selection.ipynb` (selección forward con `regsubsets`). Aquí el criterio para parar es una prueba t en vez del Cp o el BIC |
| Que una variable sirva si predice más allá del propio precio | `seleccionar`, paso 3 | Granger (1969) |
| Corrección de Bonferroni para parar | `adelante`, `seleccionar` | Dunn (1961) |
| Errores estándar de Driscoll-Kraay | `t_driscoll_kraay`, `wald_driscoll_kraay` | Driscoll y Kraay (1998): se suman las contribuciones de las 24 horas de cada día y a esa serie se le aplica Newey y West (1987) |
| Rezagos de Newey-West, `h − 1 + 7` | `seleccionar` | h − 1 por el traslape de los objetivos; 7 por la regla automática ⌊4(T/100)^{2/9}⌋ de Newey y West (1994) con T ≈ 1.750 días |
| Prueba de Wald conjunta por bloques | `wald_driscoll_kraay` | Prueba de Wald estándar, con la covarianza de Driscoll-Kraay |
| Quitar el efecto del calendario y de lo elegido antes de probar | `quitar` | Teorema de Frisch-Waugh-Lovell: el coeficiente de una variable en la regresión completa es el mismo que se obtiene con los residuos de ella y del objetivo sobre las demás (proyección ortogonal) |
| Atraso de publicación de cada variable | `ATRASO_EXTRA` | Propia y medida: último dato de cada métrica pedido a la API el 10 de octubre de 2026 (`datos/sondeos/publicacion_metricas_horarias.csv`) |
| Prueba de fuga | `comprobar_sin_fuga` | Propia: se alteran los datos posteriores a un día y ninguna característica anterior puede cambiar |

## Experimentos anteriores (`legacy/experimentos_xgboost/4_experimentos_xgboost.ipynb`)

| Qué | Dónde | Fuente |
|---|---|---|
| XGBoost | `ajustar_y_predecir` | Chen y Guestrin (2016); ML Zoomcamp, `06-trees/07-boosting.md` |
| Rejilla de hiperparámetros (`learning_rate`, `max_depth`, `min_child_weight`) | `CONFIGURACIONES` | ML Zoomcamp, `06-trees/08-xgb-tuning.md`: son los tres parámetros que ahí se ajustan |
| Validación cruzada walk-forward | sección 5 | Hyndman y Athanasopoulos (2021), sección 5.10 (validación con origen móvil). La validación cruzada en sí: SLDA, clase 4, `SLDA_class4_book2_CV.ipynb` (allí con KFold; aquí respetando el orden del tiempo) |
| Purga de h+1 días entre entrenamiento y prueba | `ajustar_y_predecir` | López de Prado (2018), capítulo 7 (validación cruzada con purga) |
| Comparar contra el ingenuo con Diebold-Mariano | `diebold_mariano` | Diebold y Mariano (1995), con la varianza de Newey y West (1987) sobre el error promedio de cada día |
| Partición 70/20/10 por días | `partir` | Pedida por el autor; los días van en orden, nunca al azar |

## Modelo XGBoost (`4_modelo_xgboost.ipynb`)

| Qué | Dónde | Fuente |
|---|---|---|
| XGBoost y su búsqueda de hiperparámetros | `ajustar`, `COMBINACIONES` | Chen y Guestrin (2016); ML Zoomcamp, `06-trees/08-xgb-tuning.md` |
| 30 modelos directos, uno por horizonte | `HORIZONTES`, `ancla` | Decisión del autor |
| Walk-forward con reentrenamiento mensual | `walk_forward` | Hyndman y Athanasopoulos (2021), sección 5.10. Reentrenar cada mes es decisión del autor |
| Purga de h+1 días | `para_entrenar` | López de Prado (2018), capítulo 7 |
| Error estándar del error por día | `media_y_error_estandar` | Newey y West (1987) |
| Regla de un error estándar | `elegir` | SLDA, clases 7 y 8; Hastie et al. (2009), sección 7.10 |
| Error relativo al ingenuo | `metricas` | Lago et al. (2021) |
| Comparar contra el ingenuo con Diebold-Mariano | `diebold_mariano` | Diebold y Mariano (1995), con la varianza de Newey y West (1987) |
| Criterio para decir que funciona: por bloque de horizontes, RMSE al menos 5% menor que el mejor ingenuo y Diebold-Mariano con p < 0,05 | `criterio`, `MEJORA_MINIMA`, `BLOQUES` | El umbral de 5% y los bloques son decisión del autor, fijados el 1 de noviembre de 2026, antes de abrir el test. La prueba: Diebold y Mariano (1995) |

## Referencias

Guías del proyecto

- Galli, S. *Feature Engineering for Machine Learning*. github.com/solegalli/feature-engineering-for-machine-learning.
- Naik, K. *Complete-Feature-Selection*. github.com/krishnaik06/Complete-Feature-Selection.
- DataTalks.Club. *Machine Learning Zoomcamp*, módulo 6. github.com/DataTalksClub/machine-learning-zoomcamp.
- Curso Statistical Learning and Data Analysis (SLDA), Universidad de los Andes. Clases 4, 5 a 7, 8 y 15.

Artículos y libros

- Beasley, T. M., Erickson, S. y Allison, D. B. (2009). Rank-based inverse normal transformations are increasingly used, but are they merited? *Behavior Genetics*, 39(5), 580-595.
- Chen, T. y Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD Conference*, 785-794.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*, 7(2), 174-196.
- Dickey, D. y Fuller, W. (1979). Distribution of the estimators for autoregressive time series with a unit root. *Journal of the American Statistical Association*, 74(366), 427-431.
- Diebold, F. y Mariano, R. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics*, 13(3), 253-263.
- Driscoll, J. y Kraay, A. (1998). Consistent covariance matrix estimation with spatially dependent panel data. *Review of Economics and Statistics*, 80(4), 549-560.
- Dunn, O. J. (1961). Multiple comparisons among means. *Journal of the American Statistical Association*, 56(293), 52-64.
- Granger, C. (1969). Investigating causal relations by econometric models and cross-spectral methods. *Econometrica*, 37(3), 424-438.
- Hastie, T., Tibshirani, R. y Friedman, J. (2009). *The Elements of Statistical Learning*, 2.ª ed. Springer.
- Hyndman, R. y Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*, 3.ª ed. OTexts.
- Kursa, M. B. y Rudnicki, W. R. (2010). Feature selection with the Boruta package. *Journal of Statistical Software*, 36(11), 1-13.
- Kwiatkowski, D., Phillips, P., Schmidt, P. y Shin, Y. (1992). Testing the null hypothesis of stationarity against the alternative of a unit root. *Journal of Econometrics*, 54(1-3), 159-178.
- Lago, J., Marcjasz, G., De Schutter, B. y Weron, R. (2021). Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark. *Applied Energy*, 293, 116983.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Lundberg, S. M. y Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30, 4765-4774.
- Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N. y Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence*, 2(1), 56-67.
- Newey, W. y West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708.
- Newey, W. y West, K. (1994). Automatic lag selection in covariance matrix estimation. *Review of Economic Studies*, 61(4), 631-653.

Regulación del mercado (gestor normativo de la CREG, gestornormativo.creg.gov.co)

- Resolución CREG 055 de 1994. Normas de la actividad de generación en el Sistema Interconectado Nacional. Art. 1 (la bolsa de energía transa "hora a hora") y art. 14 ("Precio horario en la bolsa de energía").
- Resolución CREG 025 de 1995, Código de Operación, numeral 3.1 "Información básica - Oferta de precios" (una única oferta de precio para las 24 horas; con oferta integrada para algunas cadenas hidráulicas y ofertas horarias para los enlaces internacionales). El texto con esa frase que se pudo consultar es el del proyecto de Resolución CREG 004 de 2005, que modifica ese numeral; la versión vigente del numeral no se pudo leer en el gestor.
- Resolución CREG 071 de 2006. Metodología del Cargo por Confiabilidad. Art. 29 (el precio de las obligaciones de energía firme va en US$/kWh y se actualiza cada 1 de diciembre con el índice de precios al productor de Estados Unidos de bienes de capital) y art. 82 (valor en US$/MWh en el periodo de transición).
- Resolución CREG 101 113 de 2026, art. 80, que modifica el art. 6 de la CREG 055 de 1994 (Diario Oficial 53.530, 22 de junio de 2026).

Las demás referencias de los modelos diarios (regresión cuantílica,
predicción conforme, Harvey-Leybourne-Newbold) están en `DOCUMENTACION.md`,
sección 11.
