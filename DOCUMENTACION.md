# Documentación del proyecto

Pronóstico del precio de bolsa de energía en Colombia. Este documento explica de
dónde salen los datos, qué se hace con ellos, por qué se tomó cada decisión y qué
resultados se obtuvieron. Cada técnica se relaciona con la guía de donde viene:
el curso de Feature Engineering de Soledad Galli, el repositorio
Complete-Feature-Selection, el ML Zoomcamp y el curso de Statistical Learning and
Data Analysis (SLDA). Lo que no está en esas guías se cita a su fuente original.

Contenido:

1. De qué se trata
2. Cómo se corre
3. Paso 1: los datos
4. Paso 2: el panel diario
5. Ingeniería de características
6. Los modelos
7. Resultados
8. Lo que no funcionó
9. Limitaciones
10. Diccionario de variables
11. Referencias

---

## 1. De qué se trata

El precio de bolsa es el precio al que se transa la energía en el mercado de corto
plazo colombiano. Lo calcula XM cada hora a partir de las ofertas de las plantas y
de la demanda. Según el propio panel, entre 65% y 86% de la energía de cada año
entre 2015 y 2025 fue hidráulica, así que el precio depende sobre todo de cuánta
agua hay en los embalses y de cuánta va a llegar. Por eso es tan sensible a El Niño.

El proyecto entrega dos modelos:

| | Modelo 1 | Modelo 2 |
|---|---|---|
| Horizonte | 1 día | 7 días |
| Pregunta | ¿cuánto costará mañana? | ¿qué tan probable es que pase de cierto valor? |
| Salida | un número en COP/kWh | mediana, intervalo del 80% y probabilidades |
| Rival | repetir el precio de hoy | la distribución histórica de cambios a 7 días |

La razón de tener dos se explica en la sección 6.

## 2. Cómo se corre

```
pip install pandas numpy scikit-learn xgboost statsmodels scipy matplotlib openpyxl pydataxm
python 1_descargar.py
python 2_construir_panel.py
```

y después se abre `3_modelos.ipynb`.

| Paso | Tiempo |
|---|---|
| `1_descargar.py`, la primera vez | varias horas (más de diez años por planta y por hora) |
| `1_descargar.py`, actualizando | unos 5 minutos |
| `2_construir_panel.py` | unos 20 segundos |
| `3_modelos.ipynb` | unos 5 minutos |

El notebook solo necesita `features.py` y `panel_diario.csv`. En Colab, la primera
celda los baja de GitHub o pide subirlos.

Una nota para Windows: con Smart App Control activado, Windows bloquea `pyarrow`
(la versión 25). El proyecto no lo necesita porque guarda todo en CSV; si aparece el
error `DLL load failed while importing _compute`, basta con desinstalar `pyarrow`.

```
tesis/
├── 1_descargar.py
├── 2_construir_panel.py
├── features.py
├── 3_modelos.ipynb
├── panel_diario.csv
├── datos/            lo que baja el paso 1 (no se sube a git)
│   ├── xm/           una serie por archivo, tal como la entrega la API
│   ├── noaa/
│   ├── lluvia_cuencas.csv
│   ├── trm.csv
│   └── Listado_Recursos_Generacion.xlsx
└── legacy/           versiones anteriores y experimentos
```

---

## 3. Paso 1: los datos (`1_descargar.py`)

### Fuentes

| Fuente | Qué trae | Cómo se baja |
|---|---|---|
| XM (API de SIMEM) | 41 series: precio, hidrología, generación, ofertas, demanda, contratos | librería `pydataxm`, por tramos de 30 días |
| NOAA, Climate Prediction Center | temperatura semanal del Pacífico en las regiones Niño 1+2, 3, 3.4 y 4; ONI y RONI | archivos de texto (`wksst9120.for`, `oni.ascii.txt`, `RONI.ascii.txt`) |
| Open-Meteo, reanálisis ERA5 | lluvia diaria en ocho puntos, uno por cuenca de los embalses grandes | API de archivo histórico, desde 2000 |
| datos.gov.co | TRM | conjunto `32sa-8pi3` |
| XM, PARATEC | listado de plantas con tecnología, combustible y tipo de despacho | a mano |

Las series de XM por grupo:

| Grupo | Series |
|---|---|
| Precio y demanda horaria | precio de bolsa, demanda comercial |
| Hidrología del sistema | aportes (% y media histórica), volumen útil, vertimientos |
| Hidrología por río y embalse | aportes por río, volumen y capacidad por embalse |
| Oferta por planta | generación real, programada, de seguridad y fuera de mérito; disponibilidad declarada, comercial y real; capacidad efectiva; consumo de combustible; precio de oferta |
| Despacho | costo marginal programado |
| Demanda y red | demanda regulada y no regulada, proyecciones UPME, importaciones, exportaciones, pérdidas, restricciones |
| Contratos | compras en contratos, precio de contratos regulados y no regulados |
| Regulación | ENFICC, cargo por confiabilidad, precio de escasez, CEE, CERE, MC |

### Decisiones

- Los códigos de métrica de XM se comprobaron uno por uno: se pidió a la API una
  ventana de días que ya estaba descargada y se verificó que los valores
  coincidieran exactamente. El ONI y la TRM automáticos también se compararon con
  los archivos que antes se bajaban a mano, con diferencia cero.
- Al actualizar, se vuelve a pedir el último mes. XM corrige los datos recientes
  durante varias semanas (liquidaciones provisionales), y sin ese repaso el panel
  se quedaría con versiones viejas.
- El listado de plantas se baja a mano porque el de la API solo trae plantas
  activas. Sin las retiradas desaparecen 34 plantas, entre ellas Jepírachi, que
  fue la única eólica del país hasta 2023.
- Todo se guarda en CSV comprimido, que se puede abrir en cualquier programa y no
  depende de librerías adicionales.

### Lo que ya no se baja

Se probaron y se dejaron por fuera, con el detalle en `legacy/`:

- irradiación y temperatura de paneles solares, emisiones de CO2 y las variantes
  del precio de escasez: empiezan entre 2018 y 2025, y faltan en más del 15% de
  los días;
- demanda no atendida y demanda por operador de red: no se encontró su código en
  la API para descargar 2026;
- el máximo precio de oferta: es parte del despacho y no se usa.

---

## 4. Paso 2: el panel diario (`2_construir_panel.py`)

El resultado es `panel_diario.csv`: una fila por día y una columna por variable.
Este paso no crea rezagos ni nada pensado para el modelo; solo pone todo en la
misma escala de tiempo y calcula las variables derivadas.

### Parte 1. Series de XM a un valor por día

XM entrega cada serie en uno de tres formatos: un valor por día para el sistema,
un valor por día para cada río, embalse o planta, o 24 valores por día para cada
planta. Para llegar a un número diario hay que decidir cómo se juntan las plantas
y cómo se juntan las horas, según lo que mide cada serie:

| Qué mide | Entre plantas | Entre horas | Ejemplos |
|---|---|---|---|
| Energía (un flujo) | suma | suma | generación, demanda, importaciones |
| Capacidad o disponibilidad (un nivel) | suma | promedio | disponibilidad declarada |
| Precio | promedio | promedio | costo marginal, precio de contratos |
| Porcentaje por embalse | promedio ponderado por capacidad | | volumen útil por embalse |

Las series mensuales (CEE, CERE, MC, proyecciones UPME) se repiten todos los días
del mes, porque el valor rige hasta que sale el siguiente.

### Parte 2. Precio, ONI y TRM

- El precio de bolsa del día es el promedio de las 24 horas.
- El ONI de un mes se publica dos meses después (necesita el mes siguiente para
  cerrar el promedio de tres meses), así que se corre dos meses.

### Parte 3. Margen de reserva

Capacidad efectiva del parque dividida por la demanda. La demanda que publica XM
es medida, no pronosticada, así que la del mismo día no se conoce cuando se
pronostica: se usa la del día anterior.

### Parte 4. Mezcla de generación

Cruzando la generación por planta con el listado se calcula cuánto puso cada
tecnología, cada combustible y cuánto pasó por el despacho central, que es donde
se fija el precio. También la concentración del mercado con el índice
Herfindahl-Hirschman (suma de los cuadrados de las participaciones de cada planta).

### Parte 5. Hidrología por río y embalse

El total nacional esconde situaciones distintas. Se agregan la concentración de
los aportes entre ríos, el nivel de cada uno de los cinco embalses más grandes y
la concentración del agua almacenada.

### Parte 6. Perfil del día

El precio diario es un promedio de 24 horas y dos días con el mismo promedio
pueden ser muy distintos. Se agregan el máximo, el mínimo, la dispersión dentro
del día y el factor de carga de la demanda (demanda media sobre demanda pico).

### Parte 7. El Niño semanal

El ONI es un promedio de tres meses publicado con dos meses de rezago: el modelo
veía el Pacífico con cuatro o cinco meses de atraso. NOAA publica la misma medición
cada semana. En febrero de 2026, Niño 1+2 ya estaba en +0,88 °C y el ONI todavía
marcaba La Niña; con la serie semanal la señal llega unos 86 días antes. Se usan
las anomalías de las cuatro regiones, su tendencia a 4 y 12 semanas, la diferencia
entre la costa (Niño 1+2) y el Pacífico central (Niño 3.4), y el RONI. A la serie
semanal se le aplica una semana de rezago de publicación.

### Parte 8. Lluvia sobre las cuencas

El panel ve los aportes (el agua que ya llegó al embalse) pero no la lluvia que
los produce. Se usa ERA5, que es lluvia observada, con cinco días de rezago de
publicación. Como la lluvia la domina la estación del año, lo que se usa es cuánto
se aparta de lo normal para esa fecha, con 2000-2014 como periodo de referencia.

No se usaron pronósticos de lluvia: el archivo de pronósticos tal como se
emitieron solo existe desde 2024, muy poco para entrenar.

### Parte 9. Curva de mérito

El precio de bolsa sale de ordenar las plantas de la más barata a la más cara y
ver dónde se cruza esa curva con la demanda. Cada planta ofrece un solo precio por
día y declara cuánto puede generar, así que la curva se puede reconstruir. Al
cruzarla con la demanda, el precio de la planta marginal reproduce el precio de
bolsa con correlación de 0,96. De la curva se mide su forma: cuánta capacidad
queda por debajo de 100, 200, 300, 500 y 1.000 COP/kWh, qué tan empinada está
cerca de la demanda y cuánto salta el precio a la siguiente planta.

---

## 5. Ingeniería de características (`features.py`)

La regla que manda en todo el archivo: para pronosticar el día $t$ solo se usa
información que ya se conocía antes de ese día.

### 5.1 Datos faltantes

Hay tres tipos y cada uno se trata distinto.

| Tipo | Ejemplo | Tratamiento | Guía |
|---|---|---|---|
| Eventos: el hueco es un cero real | vertimientos, importaciones, generación solar | se llena con 0 | Galli, sección 5, *Arbitrary Value Imputation* |
| La variable no existía todavía | embalse El Quimbo (entró a finales de 2015) | se descarta | |
| Huecos de uno o dos días | festivos, fallas de publicación | último valor conocido | |

En los eventos, el supuesto se comprueba: en once años ninguna de esas series
tiene un cero, lo que indica que XM no publica fila cuando el evento no ocurre.

Las técnicas de imputación del curso de Galli (media, mediana, KNN) están
pensadas para huecos al azar. Aplicarlas a una variable que todavía no existía
sería inventar historia, y además una sola variable que empieza tarde le recorta
el inicio a toda la muestra, porque el modelo necesita todas las columnas el
mismo día. El último valor conocido no está entre las técnicas del curso, que
trata datos sin orden en el tiempo; aquí se usa porque solo mira al pasado.

### 5.2 Variables excluidas

- Despacho (costo marginal programado y precio de oferta promedio): el precio de
  bolsa es el costo marginal del despacho, con correlación de 0,97. Si entraran,
  el modelo copiaría el precio y no aprendería nada del sistema.
- Variables que arrancan después de marzo de 2015.

### 5.3 Transformaciones y variables nuevas

| Qué se hace | Por qué | Guía |
|---|---|---|
| Logaritmo del precio | el precio está muy sesgado a la derecha | Galli, sección 11, *logarithmic transformation* |
| 1 / volumen útil | con embalses bajos el precio sube más que proporcionalmente | Galli, sección 11, *reciprocal transformation* |
| Fracciones y razones (mezcla de generación, margen de reserva) | combinar variables en una medida con sentido físico | Galli, sección 17, *Combine features with functions* |
| Choque: valor de ayer menos su media reciente | lo que mueve el precio es que algo se salga de lo normal | Galli, sección 17, *Comparing features to reference variable* |
| Lunes, sábado, domingo | el precio baja los fines de semana | Galli, sección 15, *date-time features* |
| Rezagos y medias móviles | la información de los días anteriores | |

Para cada variable se crean rezagos de 1, 2, 3, 7, 14 y 30 días, medias móviles
de 7 y 30 días y choques de 7 y 30 días. Las variables ex ante (disponibilidad
declarada, precio de escasez, cargos regulados, margen de reserva) tienen además
el valor del mismo día.

### 5.4 Cómo se evita la fuga de información

| Tipo de variable | Rezago mínimo | Por qué |
|---|---|---|
| Medidas durante el día | 1 día | se conocen al cierre del día |
| Ex ante | 0 días | se publican antes del despacho |
| Curva de mérito | 1 día | la oferta del día $t$ es lo que fija el precio de ese día |
| El Niño semanal | 8 días | una semana de publicación más el rezago mínimo |
| Lluvia ERA5 | 6 días | cinco de publicación más el rezago mínimo |

Toda media móvil se calcula con `shift(1)` antes del `rolling`. Una media que
incluyera el día $t$ usaría el dato que se quiere pronosticar. Es el error que
más fácil pasa desapercibido, porque no rompe nada: solo infla los resultados.

### 5.5 Limpieza de la matriz

Con la ventana de selección (2015-2019):

1. Se quitan las columnas constantes (Complete-Feature-Selection, cuaderno 1).
2. Se quitan las redundantes: si dos columnas correlacionan más de 0,95 se
   conserva la primera (cuaderno 2 del mismo repo, que usa umbrales de 0,7 y 0,9;
   aquí se usa uno más alto para no perder variantes de una misma variable que
   aportan algo distinto).
3. Se quitan las combinaciones lineales exactas. Por construcción
   `x_choque7 = x_lag1 − x_ma7`, y con las tres juntas la regresión no puede
   separar sus efectos. Es el problema de multicolinealidad de las clases 5 a 7
   de SLDA.

De 1.334 características quedan 702.

---

## 6. Los modelos (`3_modelos.ipynb`)

### 6.1 Qué se predice y en qué ventanas

Se predice el cambio del logaritmo del precio, $y = \log P_{t+h} - \log P_t$, y el
precio se reconstruye como $P_t e^{\hat y}$. Con el nivel, un modelo que copia el
precio de ayer ya parece muy bueno; con el cambio, copiar el precio de hoy es el
punto de partida y cualquier mejora es información de verdad.

| Ventana | Fechas | Para qué |
|---|---|---|
| Selección | 2015-2019 | ordenar las variables |
| Validación | 2020-2022 | elegir cuántas variables y calibrar los intervalos |
| Prueba A | 2023-2025 | primera medición |
| Prueba B | 2026 | medición final; esos datos no existían cuando se tomaron las decisiones |

La validación cruzada es temporal: siempre entrena con el pasado y valida con el
futuro, con un hueco de $h$ días porque el objetivo de un día mira $h$ días hacia
adelante. Es la misma idea de la clase 4 de SLDA, pero respetando el orden del
tiempo; la validación cruzada aleatoria entrenaría con 2022 para validar en 2016.

### 6.2 Selección de variables

Se ordenan las 702 variables promediando su puesto en dos rankings calculados
con la ventana de selección:

- Lasso (clases 7 y 8 de SLDA), con las variables estandarizadas antes
  (Galli, sección 18, *Standardisation*). Ve relaciones lineales.
- Ganancia en XGBoost (clase 15 de SLDA; ML Zoomcamp, módulo 6). Ve no
  linealidades e interacciones.

Después se prueba con las 12, 30, 50, 100 y 200 primeras y con todas, y se elige
la mejor en validación. La validación elige 100 variables para el modelo 1 y 30
para el modelo 2. Elegir ese número mirando la prueba sería como probar seis
modelos y reportar el que mejor salió.

### 6.3 Hiperparámetros

Salieron de una búsqueda aleatoria con validación cruzada temporal sobre
2015-2022 (`legacy/experimentos/10_horizontes.py`). Los tres que más pesan son
los que explica el ML Zoomcamp (módulo 6, *XGBoost tuning*): tasa de aprendizaje,
profundidad de los árboles y tamaño mínimo de las hojas.

| | Modelo 1 | Modelo 2 |
|---|---|---|
| árboles | 600 | 400 |
| profundidad | 2 | 2 |
| tasa de aprendizaje | 0,01 | 0,01 |
| tamaño mínimo de hoja | 10 | 10 |
| submuestreo de filas | 0,9 | 0,7 |
| regularización L2 | 10 | 3 |

Son árboles de dos niveles con una tasa de aprendizaje baja: modelos simples y
muy regularizados. La sección 8 muestra por qué tiene sentido.

### 6.4 Modelo 1: un día

XGBoost con pérdida cuadrática sobre las 100 variables elegidas, promediando cinco
modelos con semillas distintas. Se compara con repetir el precio de hoy.

### 6.5 Modelo 2: siete días, probabilístico

Si a este modelo se le pide un solo número, empata con repetir el precio de hoy
(MAPE de 28,7% contra 28,7% en 2026). Pero el modelo sí sabe algo: no hacia dónde
va la mediana, sino cuándo hay más riesgo de que el precio se dispare. Por eso
entrega una distribución.

Se entrena un modelo por cuantil (10, 25, 50, 75 y 90%) con la pérdida pinball,
que es la de la regresión por cuantiles (Koenker y Bassett, 1978): castiga
distinto quedarse corto que pasarse.

Los cuantiles que salen están mal calibrados: el intervalo que dice 80% cubre
alrededor de 70%. Se corrigen con predicción conforme sobre cuantiles (Romano,
Patterson y Candès, 2019). Para cada caso ya resuelto se calcula
$E = \max(q_{10} - y,\; y - q_{90})$, que es positivo cuando el valor real quedó
fuera del intervalo, y el intervalo se ensancha con el percentil 80 de esos
errores. La versión original usa un conjunto fijo para calcularlos; aquí se usa
una ventana móvil de 90 días (elegida en validación), porque 2023-2026 tuvo
movimientos más grandes que 2015-2022 y una corrección fija se habría quedado
corta. Para el día $t$ solo se usan orígenes hasta $t-7$, cuyo resultado ya se
conoce.

### 6.6 Cómo se mide

| Medida | Qué dice |
|---|---|
| MAPE | error porcentual en COP/kWh |
| RMSE del log | error en el cambio, que es lo que el modelo minimiza |
| Dirección | porcentaje de días en que acierta si el precio sube o baja |
| Diebold-Mariano | si la diferencia de error con el rival es real o puede ser ruido |
| Pinball | la forma correcta de puntuar cuantiles |
| Cobertura | si el intervalo del 80% contiene el 80% de los casos |
| Brier | si las probabilidades del tipo "pasa de 500" están bien calibradas |

La prueba de Diebold-Mariano (Diebold y Mariano, 1995) es la que usa la librería
epftoolbox (Lago et al., 2021), la referencia en pronóstico de precios de energía.
Lleva la corrección de Harvey, Leybourne y Newbold (1997) para muestras chicas y
la varianza de Newey-West con $h$ rezagos, porque a siete días dos pronósticos
seguidos comparten seis días de información.

---

## 7. Resultados

Con los datos descargados el 9 de octubre de 2026 (precio hasta el 6 de octubre).

### Modelo 1: un día

| Periodo | Días | MAPE modelo | MAPE ingenuo | Dirección acertada | RMSE frente al ingenuo | p (Diebold-Mariano) |
|---|---|---|---|---|---|---|
| 2023-2025 | 1.096 | 12,00% | 12,86% | 62,0% | −8,4% | < 0,001 |
| 2026 | 278 | 9,06% | 10,01% | 68,3% | −12,5% | 0,0003 |

El modelo le gana a repetir el precio de hoy en los dos periodos, y la diferencia
no es ruido. En 2026, un año de El Niño fuerte que el modelo no había visto, le va
incluso mejor que en 2023-2025.

### Modelo 2: siete días

| | 2023-2025 | 2026 |
|---|---|---|
| Días | 1.096 | 272 |
| Pérdida pinball frente a la climatología | −2,2% | −4,3% |
| Cobertura del intervalo del 80%, sin calibrar | 67,8% | 73,5% |
| Cobertura del intervalo del 80%, calibrado | 80,7% | 82,0% |
| Ancho medio del intervalo | 516 COP/kWh | 450 COP/kWh |
| Brier, probabilidad de pasar de 300, frente a la climatología | −8,3% | −7,9% |
| Brier, pasar de 500 | −8,2% | −2,0% |
| Brier, pasar de 800 | +7,0% | +1,6% |

Le gana a la climatología en los dos periodos y la calibración deja la cobertura
cerca del 80% prometido. Las probabilidades de pasar de 300 y 500 COP/kWh son
mejores que las de la climatología; la de pasar de 800 es un poco peor.

### Pronóstico desde el último dato

Con el precio del 6 de octubre de 2026 (592 COP/kWh), el notebook da:

- para el 7 de octubre, 601 COP/kWh;
- para el 13 de octubre, mediana de 608 COP/kWh, con 80% de probabilidad entre
  398 y 859; probabilidad de pasar de 500 de 74% y de pasar de 800 de 17%.

### Reproducibilidad

Esta versión se comprobó contra la anterior (`legacy/notebooks_unificados/21_modelos_finales.ipynb`):

- el panel es idéntico hasta el 26 de agosto de 2026; después difiere solo en
  días que XM corrigió y que el paso 1 volvió a bajar;
- la matriz de características tiene las mismas 702 columnas, en el mismo orden
  y con los mismos valores;
- con el panel recortado al 26 de septiembre, 2023-2025 da los mismos números
  hasta el último decimal. En 2026 hay diferencias mínimas (MAPE de 9,09% contra
  9,10%) que vienen de las correcciones de XM: incluso el error del modelo ingenuo,
  que solo depende del precio, cambia (10,036% contra 10,035%).

---

## 8. Lo que no funcionó

Antes de llegar a los dos modelos se intentó pronosticar más allá de una semana
de varias formas. Ninguna funcionó; los scripts están en `legacy/experimentos/`.

| Intento | Script | Resultado |
|---|---|---|
| Ampliar el panel de 58 a 104 variables | `00b_ampliar_panel.py` | sin efecto (RMSE 0,1641 frente a 0,1642) |
| Pronóstico puntual a 15, 30, 60 y 90 días | `10_horizontes.py`, `12_test_2026.py` | en 2026, peor que repetir el precio de hoy en todos |
| ¿El modelo solo copia el precio de ayer? | `13_cuanto_es_autocorrelacion.py` | no: sin las variables del sistema queda igual al ingenuo |
| El Niño semanal en vez del ONI | `00f_enso_semanal.py` | la dirección acertada pasó de 34% a 48% a 60 días y de 27% a 38% a 90 días, pero sin ganarle al ingenuo |
| Lluvia sobre las cuencas | `14_h7_con_lluvia.py` | sin efecto |
| Usar pocas variables | `15_h7_menos_es_mas.py` | peor; el mejor número está entre 30 y 100 |
| Historia desde 2000 (unos diez episodios de El Niño o La Niña) | `17_largo_vs_corto.py` | no ayudó; a 30 días empeoró |
| Más capacidad (equivalente a una red neuronal) | `22_capacidad_o_informacion.py` | un modelo que memoriza el entrenamiento quedó 52% peor que el ingenuo |

De ahí salen tres conclusiones:

1. El horizonte útil es corto. A 30 días el modelo se equivocaba 52% contra 41% de
   repetir el precio de hoy.
2. El límite es la información, no el modelo. Ni más variables ni más capacidad
   mejoraron el resultado. Por eso la búsqueda de hiperparámetros eligió árboles
   de dos niveles y por eso no se usaron redes neuronales.
3. Resultados que se veían bien se cayeron al validarlos con cuidado. Los
   horizontes de 60 y 90 días se veían bien en 2023-2025 y fallaron en 2026; un
   p-valor de 0,0496 a siete días dejó de ser significativo al promediar varias
   semillas; y elegir el número de variables mirando la prueba daba una mejora que
   desaparecía al elegirlo en validación.

Esto coincide con la literatura: epftoolbox y los demás trabajos revisados se
concentran en el día siguiente, y el único trabajo encontrado sobre mediano plazo
(Ghelasi y Ziel, 2024, para Alemania) no reporta ganarle a los modelos de referencia.

---

## 9. Limitaciones

- 2026 tiene unos 270 días de prueba. Con esa muestra la prueba de Diebold-Mariano
  tiene poca potencia para diferencias pequeñas.
- La mediana del modelo 2 no le gana a repetir el precio de hoy; su valor está en
  el intervalo y las probabilidades. Para el umbral de 800 COP/kWh su Brier es
  peor que el de la climatología.
- Las tendencias de 12 semanas de El Niño (`nino12_tend12s`, `nino34_tend12s`)
  quedan fuera del modelo por un detalle: se calculan sobre el panel, que empieza
  en enero de 2015, así que sus primeros 84 días quedan vacíos y `features.py` las
  trata como variables que arrancan tarde. La serie semanal existe desde 1981, así
  que se podrían calcular completas. Venía así desde la versión anterior y los
  resultados de este documento son sin ellas; incluirlas requiere volver a evaluar.
- El listado de plantas no reconoce 11 plantas que aparecen en la generación
  (0,26% de la energía). Su generación cuenta en el total pero no en la mezcla.
- XM publica las ofertas con días o semanas de atraso (el 9 de octubre de 2026
  llegaban hasta el 30 de septiembre), así que en los últimos días del panel la
  curva de mérito repite el último valor conocido.
- El pronóstico del notebook usa los modelos entrenados hasta 2025 (los mismos que
  se evaluaron en 2026). En uso real convendría reentrenarlos periódicamente.

---

## 10. Diccionario de variables

El panel tiene 136 columnas. La descripción detallada de las variables de la
mezcla de generación, la hidrología desagregada y el perfil del día está en
`legacy/experimentos/DICCIONARIO_VARIABLES.md`.

| Bloque | Columnas | Fuente |
|---|---|---|
| Objetivo | `precio_bolsa` | XM |
| Hidrología del sistema | `aportes_pct_sistema`, `aportes_media_hist`, `volumen_util_pct`, `vertimientos` | XM |
| Hidrología por río y embalse | `aportes_por_rio`, `aportes_pct_rio`, `volumen_por_embalse`, `capacidad_por_embalse`, `volumen_util_pct_emb` | XM |
| Oferta | `gen_por_recurso`, `gen_programada`, `gen_seguridad`, `gen_fuera_merito`, `disp_declarada`, `disp_comercial`, `disp_real`, `capacidad_efectiva`, `consumo_combustible` | XM |
| Despacho (excluido del modelo) | `costo_marginal_prog`, `precio_oferta_desp` | XM |
| Demanda y red | `demanda_regulada`, `demanda_no_regulada`, `demanda_upme_alto/medio/bajo`, `importaciones`, `exportaciones`, `perdidas_energia`, `restricciones`, `restricciones_sin_aliv` | XM |
| Contratos | `compras_contrato`, `precio_prom_contrato`, `precio_cont_no_regu` | XM |
| Regulación | `enficc`, `precio_cargo_conf`, `precio_escasez`, `cee`, `cere`, `mc` | XM |
| Clima y economía | `oni`, `trm` | NOAA, datos.gov.co |
| Derivada | `margen_reserva` | cálculo propio |
| Mezcla de generación (25) | `gen_hidraulica`, `frac_termica`, `gen_gas`, `frac_despacho_central`, `hhi_generacion`, ... | XM + listado de plantas |
| Disponibilidad por tecnología (3) | `disp_decl_hidraulica`, `disp_decl_termica`, `disp_decl_despacho_central` | XM + listado |
| Hidrología desagregada (9) | `hhi_aportes_rios`, `aportes_top3_pct`, `vol_pct_penol`, `vol_pct_guavio`, ... | XM |
| Perfil del día (8) | `precio_max_dia`, `precio_spread_intradia`, `ratio_pico_valle`, `factor_carga`, ... | XM |
| El Niño semanal (10) | `nino12_anom`, `nino34_anom`, `nino12_tend4s`, `nino_gradiente_costa`, `roni`, ... | NOAA |
| Lluvia (21) | `lluvia_sistema`, `lluvia_anom_acum30`, `lluvia_razon90`, `lluvia_guavio_anom30`, ... | ERA5 |
| Curva de mérito (17) | `cap_bajo_200`, `oferta_marginal`, `oferta_dispersion`, `pendiente_curva`, `escalon_siguiente`, ... | XM |

---

## 11. Referencias

Guías del proyecto

- Galli, S. *Feature Engineering for Machine Learning*. Curso de Train in Data;
  código en github.com/solegalli/feature-engineering-for-machine-learning.
  Secciones usadas: 5 (imputación), 11 (transformación de variables), 15 (fechas),
  17 (creación de variables), 18 (escalamiento).
- Naik, K. *Complete-Feature-Selection*. github.com/krishnaik06/Complete-Feature-Selection.
  Cuadernos 1 (variables constantes) y 2 (correlación).
- DataTalks.Club. *Machine Learning Zoomcamp*, módulo 6 (árboles de decisión y
  XGBoost). github.com/DataTalksClub/machine-learning-zoomcamp.
- Curso Statistical Learning and Data Analysis (SLDA), Universidad de los Andes.
  Clases 4 (error de predicción y validación cruzada), 5 a 7 (selección de
  variables y multicolinealidad), 7 y 8 (Ridge y Lasso), 15 (árboles).

Métodos

- Chen, T. y Guestrin, C. (2016). XGBoost: A scalable tree boosting system.
  *Proceedings of the 22nd ACM SIGKDD Conference*, 785-794.
- Diebold, F. y Mariano, R. (1995). Comparing predictive accuracy. *Journal of
  Business & Economic Statistics*, 13(3), 253-263.
- Harvey, D., Leybourne, S. y Newbold, P. (1997). Testing the equality of
  prediction mean squared errors. *International Journal of Forecasting*, 13(2),
  281-291.
- Newey, W. y West, K. (1987). A simple, positive semi-definite, heteroskedasticity
  and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708.
- Koenker, R. y Bassett, G. (1978). Regression quantiles. *Econometrica*, 46(1),
  33-50.
- Romano, Y., Patterson, E. y Candès, E. (2019). Conformalized quantile
  regression. *Advances in Neural Information Processing Systems*, 32.

Pronóstico de precios de energía

- Lago, J., Marcjasz, G., De Schutter, B. y Weron, R. (2021). Forecasting
  day-ahead electricity prices: A review of state-of-the-art algorithms, best
  practices and an open-access benchmark. *Applied Energy*, 293, 116983.
  Librería: github.com/jeslago/epftoolbox.
- Ghelasi, P. y Ziel, F. (2024). From day-ahead to mid and long-term horizons
  with econometric electricity price forecasting models. arXiv:2406.00326.

Datos

- XM. API de SIMEM, librería `pydataxm`.
- NOAA Climate Prediction Center. Índices Niño semanales, ONI y RONI.
- Hersbach, H. et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the
  Royal Meteorological Society*, 146(730), 1999-2049. Consultado mediante la API
  de Open-Meteo.
- Banco de la República, TRM, publicada en datos.gov.co.
