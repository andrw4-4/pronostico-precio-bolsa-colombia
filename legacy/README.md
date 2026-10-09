# legacy

Aquí está todo lo que se hizo antes de llegar a la versión actual (los cuatro
archivos de la raíz). No hace falta para correr los modelos, pero respalda la
sección "Lo que no funcionó" de `DOCUMENTACION.md` y deja la historia del proyecto.

Los scripts usan las rutas que tenían cuando se escribieron, así que para volver
a correr alguno hay que ajustarlas a las carpetas de aquí.

## pipeline_v1/

La primera versión, por scripts encadenados. Usaba tres ventanas (selección,
validación, prueba), pruebas de Granger e información mutua para elegir variables,
evaluación por bloques temáticos con Diebold-Mariano y una auditoría de fuga.

| Archivo | Qué hacía |
|---|---|
| `00_consolidar_panel.py` | armaba el panel diario desde la caché de la API. Su lógica pasó casi intacta a `2_construir_panel.py` |
| `01_seleccion_variables.py` a `03_bloques_candidatos.py` | selección de variables y de bloques |
| `04_xgboost.ipynb`, `05_xgboost_diferencia.ipynb` | primeros XGBoost, en nivel y en diferencias |
| `06_auditoria.py` | chequeos automáticos de fuga de información |
| `01_analisis_exhaustivo_precio_bolsa.ipynb` | análisis exploratorio inicial |

## notebooks_unificados/

Las versiones intermedias del notebook único: `08_flujo_completo`, `09_tesis_completo`
(con todos los métodos del curso SLDA) y `21_modelos_finales`, que es el antecesor
directo de `3_modelos.ipynb` y da los mismos resultados.

## experimentos/

Cada prueba que se hizo para mejorar el pronóstico, en el orden en que se hizo.

| Archivo | Pregunta | Respuesta |
|---|---|---|
| `00b_ampliar_panel.py` | ¿sirven 46 variables nuevas (mezcla de generación, concentración, perfil del día)? | entran al modelo pero no bajan el error |
| `00c` a `00e` | descarga y armado de 2026 | se usó como prueba final |
| `10_horizontes.py` | ¿hasta qué horizonte se puede pronosticar? | hasta una semana; aquí salieron los hiperparámetros |
| `11_trayectoria.py` | un solo modelo para todos los horizontes | peor a corto plazo |
| `12_test_2026.py` | prueba sobre 2026 | a 30-90 días el modelo falla |
| `13_cuanto_es_autocorrelacion.py` | ¿el modelo solo copia el precio de ayer? | no: la señal viene del sistema |
| `00f_enso_semanal.py` | ¿El Niño semanal en vez del ONI? | 86 días de anticipación; corrige el peor fallo |
| `00h_lluvia_cuencas.py`, `14_h7_con_lluvia.py` | ¿la lluvia sobre las cuencas ayuda? | no |
| `15_h7_menos_es_mas.py`, `16_modelo_final_h7.py` | ¿menos variables? | no; y elegir k mirando la prueba engaña |
| `00g`, `00i`, `00j`, `17_largo_vs_corto.py` | ¿historia desde 2000? | no ayuda |
| `18_curva_merito.py` | curva de mérito desde las ofertas | se reproduce el precio con correlación 0,96 |
| `19_cuantilica.py`, `20_calibrar_h7.py` | pronóstico probabilístico y calibración | es el modelo 2 |
| `22_capacidad_o_informacion.py` | ¿una red neuronal ayudaría? | no: más capacidad empeora |
| `DICCIONARIO_VARIABLES.md` | descripción detallada de las 46 variables nuevas | |

## salidas/

Resultados guardados por los scripts anteriores (tablas, gráficos, hiperparámetros).

## datos_viejos/ y paneles/

La caché original de la API en parquet (`cache_api`, `cache_2026`, `cache_historico`),
los CSV de `data/` y los paneles anteriores. `panel_diario_58_variables.csv` es el
panel con el que empezó el proyecto. Estas carpetas no se suben a git.
