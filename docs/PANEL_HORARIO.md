# Panel horario

Todos los paneles están en la carpeta `paneles/`. La fuente de cada parte del
código está en `REFERENCIAS.md`.

`panel_horario.csv.gz` lo arma `2b_panel_horario.py` con los archivos de
`datos/xm` y `datos/simem`. Tiene una fila por día y hora: 4.300 días × 24
horas = 103.200 filas, del 1 de enero de 2015 al 9 de octubre de 2026. El precio
horario llega hasta el 6 de octubre y no tiene huecos (103.128 horas).

La hora sigue la convención de XM: la hora 1 va de 0:00 a 1:00 y la 24 de 23:00
a 24:00. `fecha_hora` es el inicio de esa hora.

## Dos versiones

| Archivo | Columnas | Tamaño | Qué tiene |
|---|---|---|---|
| `panel_horario.csv.gz` | 66 | 18,7 MB | solo lo que cambia dentro del día |
| `panel_horario_completo.csv.gz` | 178 | 21,9 MB | lo anterior más 112 variables que solo existen por día, repetidas en las 24 horas de su día |

Las dos tienen las mismas 103.200 filas.

La completa no copia del panel diario nada que se pueda calcular con las
columnas horarias, para no tener la misma información dos veces (la lista está
en `NO_COPIAR`, en el paso 2b):

- la misma variable sumada o promediada en el día: el precio promedio, las
  demandas, las disponibilidades, la generación por tecnología, el CO2, los
  contratos, las pérdidas, las restricciones y los intercambios;
- la curva de mérito del día, que aquí está hora por hora;
- lo que sale de combinar columnas horarias: el perfil del día (máximo, mínimo,
  rango y variación del precio, hora del pico, pico/valle, demanda pico, factor
  de carga) y la participación solar y eólica;
- el despacho y los saldos con Ecuador, que tampoco están en el horario.

Lo que sí trae son las 112 que no se pueden armar con lo horario: hidrología
(aportes por río, embalses uno por uno, descargas, turbinado, vertimientos),
lluvia, El Niño, predicción y alertas del IDEAM, cargos regulados y precio de
escasez, energía en firme, capacidad efectiva, margen de reserva, generación
por combustible y por tipo de despacho, concentración del mercado y la forma de
la curva de ofertas del día (percentiles, capacidad barata, pendiente). Todas
van en las unidades del panel diario (kWh y COP).

## Cuándo se conoce cada cosa

Es lo que más importa al modelar por hora. Si el pronóstico de las 24 horas de
mañana se hace hoy, solo se puede usar lo que ya se sabía hoy.

| Cuándo se conoce | Columnas | Cómo entra |
|---|---|---|
| Antes del día (calendario) | `dia_semana`, `es_festivo`, `hora` | del mismo día que se pronostica |
| Antes del despacho | `disp_declarada`, `disp_decl_hidraulica`, `disp_decl_termica` | sin rezago |
| Resultado del despacho del día anterior (**suposición**, ver abajo) | `pron_demanda_cnd`, `cmg_despacho` | sin rezago |
| Después de que pasa la hora | todo lo demás | rezagado |
| Es el objetivo | `precio_bolsa` | solo rezagado como característica |

**La suposición.** SIMEM publica el pronóstico de demanda y el costo marginal
del despacho con una fecha de carga posterior al día, no con la hora a la que
el CND los produjo. El costo marginal de hoy estaba disponible hoy en la API de
XM (se comprobó), lo que es coherente con que sea el resultado del despacho del
día anterior, pero no se verificó a qué hora. Si no se quiere asumir, se quitan
de `EX_ANTE_HORARIAS` en `features.py` y entran rezagados 24 horas.

**El precio llega con dos días de atraso.** En la API de XM el último precio
publicado de hoy (10 de octubre) era el del 8. Las características de este
proyecto suponen que el precio de ayer ya se conoce; con la API, el rezago real
es de 72 horas para pronosticar mañana. Los resultados con rezago de 24 horas
son optimistas por ese día. Lo mismo vale para la demanda y la generación
real (2 días); los contratos y las pérdidas llegan con 5 y el precio de oferta
con 10.

## Columnas

Unidades: energías y capacidades en MWh (en una hora, MW y MWh son el mismo
número); precios en COP/kWh; CO2 en toneladas; las restricciones, en millones de
pesos (son lo que cuestan, no energía).

### Demanda, disponibilidad y generación

| Columna | Qué es | Desde |
|---|---|---|
| `precio_bolsa` | precio de bolsa nacional de esa hora | 2015 |
| `demanda_comercial`, `demanda_regulada`, `demanda_no_regulada` | demanda comercial del sistema y por mercado | 2015 |
| `demanda_real`, `demanda_real_reg`, `demanda_real_no_reg` | demanda real (medida) | 2015 |
| `disp_declarada`, `disp_comercial`, `disp_real` | disponibilidad de las plantas | 2015 |
| `disp_decl_hidraulica`, `disp_decl_termica` | disponibilidad declarada por tecnología | 2015 |
| `gen_total` | generación de todas las plantas | 2015 |
| `gen_hidraulica`, `gen_termica`, `gen_solar`, `gen_eolica`, `gen_cogenerador` | generación por tecnología, con el listado de PARATEC | 2015 |
| `frac_hidraulica`, `frac_termica`, `frac_fncer` | participación de cada tecnología (fncer = solar + eólica) | 2015 |
| `gen_programada`, `gen_prog_redespacho` | generación programada en el despacho y en el redespacho | 2015 |
| `gen_seguridad`, `gen_fuera_merito` | generación por seguridad y fuera de mérito | 2015 |
| `consumo_combustible` | combustible consumido por las térmicas (MBTU) | 2015 |
| `restricciones`, `restricciones_sin_aliv` | costo de las restricciones de la red, en millones de pesos | 2015 |
| `perdidas_energia` | pérdidas de energía; en 270 horas sale negativa, por ajustes de liquidación de XM | 2015 |
| `importaciones`, `exportaciones`, `compras_tie` | intercambios internacionales; 0 si no hubo. No se guarda `ventas_tie`: es igual a `compras_tie` en todas las horas | 2015 |
| `compras_contrato`, `precio_prom_contrato`, `precio_cont_no_regu` | contratos | 2015 |
| `margen_declarado` | disponibilidad declarada / demanda comercial | 2015 |

### Curva de mérito por hora

| Columna | Qué es | Desde |
|---|---|---|
| `oferta_cap_total`, `cap_bajo_200`, `cap_bajo_500` | capacidad ofertada, y la que ofrece a menos de 200 y 500 COP/kWh | 2015 |
| `oferta_marginal` | precio de la planta que queda al margen frente a la demanda de la hora | 2015 |
| `escalon_siguiente`, `holgura_mw`, `margen_ofertado` | salto a la siguiente planta, capacidad menos demanda y cociente | 2015 |

Cada planta oferta una vez al día, con un solo precio para las 24 horas (CREG
025 de 1995, numeral 3.1; se comprobó en todo el archivo), y declara su
disponibilidad hora por hora. El precio de bolsa es horario (CREG 055 de 1994,
art. 14) porque en cada hora queda al margen una planta distinta. La curva usa
la oferta de cada hora, por si las ofertas empiezan a variar por hora.
`oferta_marginal` tiene correlación de 0,94 con el precio de la misma hora, así
que solo puede entrar rezagada. XM publica las ofertas con unos 10 días de
atraso.

### Agregadas en esta versión

| Columna | Qué es | Fuente | Desde | Hasta | Atraso |
|---|---|---|---|---|---|
| `gen_ideal_total`, `gen_ideal_hidraulica`, `gen_ideal_termica` | generación del despacho ideal, sin restricciones de la red | XM | 2015 | 8 oct. 2026 | 2 días |
| `gen_restricciones` | generación real menos ideal; casi siempre ≤ 0 | derivada | 2015 | 6 oct. | 4 días |
| `co2_gas`, `co2_carbon`, `co2_liquidos`, `co2_total` | toneladas de CO2 por combustible (gas incluye gas importado; líquidos: ACPM, combustóleo, queroseno, crudo y GLP) | XM | 2015 | 8 oct. | 2 días |
| `marg_hidraulica`, `marg_termica` | 1 si la planta marginal de esa hora es hidráulica o térmica | XM | 2015 | 30 sep. | 10 días |
| `marg_gas`, `marg_carbon`, `marg_liquidos` | combustible de la planta marginal térmica | XM | 2015 | 30 sep. | 10 días |
| `pron_demanda_cnd` | pronóstico de demanda del CND, suma de los mercados de comercialización | SIMEM | 2015 | 30 sep. | 10 días |
| `error_pron_demanda` | demanda comercial menos el pronóstico | derivada | 2015 | 30 sep. | 10 días |
| `cmg_despacho` | costo marginal del despacho económico (programado) | SIMEM | 2015 | 9 oct. | 1 día |
| `cmg_redespacho` | costo marginal del redespacho | SIMEM | 2015 | 9 oct. | 1 día |
| `ajuste_cmg` | redespacho menos despacho | derivada | 2015 | 9 oct. | 1 día |

## Lo que hay que saber de las nuevas

- **El costo marginal programado no es el precio.** La correlación horaria en
  logaritmos es 0,95, pero el precio es en promedio 9% mayor y el error sube
  con los años: RMSE del log de 0,15 en 2015 y 0,53 en 2024. El 2 de
  septiembre de 2026, a la hora 9, el programado fue 200 y el precio 919.
  Sirve como característica, no como pronóstico.
- **Lo que se baja pero no entra al panel, por ahora.** La holgura horaria de 18
  plantas, los arranques y las paradas empiezan en 2021, y la reserva solo
  cubre de septiembre de 2024 a septiembre de 2025 (`reserva_caliente_*`) y de
  octubre de 2025 en adelante (`reserva_*`), en dos versiones que no se pueden
  comparar. Un modelo que arranca en 2015 no las puede usar. Los datos siguen en
  `datos/simem` y el código que las arma sigue en el paso 2b; para volver a
  incluirlas se vacía la lista `NO_SE_USAN_POR_AHORA`.
- **Recurso marginal.** XM marca una sola planta como marginal en cada hora (en
  los 11 años no hay una hora sin ella ni con dos). La térmica es la marginal
  en 1% a 8% de las horas según el año; el resto es hidráulica.
- **El número de mercados de comercialización crece de 37 en 2015 a 45 en
  2026,** y el pronóstico suma todos los que haya cada día. Frente a la demanda
  real queda en 0,96 a 0,99, con error medio de 4,4%.
- **La hora de SIMEM empieza una hora antes que la de XM** (`FechaHora` 04:00 es
  la hora 5). Está corregido en el script; se comprobó con 240 horas de costo
  marginal, que coinciden al 100%.
- **Pronóstico de demanda duplicado (corregido).** En 70 días de 2019, 2020 y
  2024, SIMEM trae además de los mercados de comercialización un "mercado"
  `MC-SIN`, que es el total nacional (vale lo mismo que la suma de los demás).
  Al sumarlo, el pronóstico salía al doble en 1.680 horas. Ahora se deja fuera.
- **Días con la demanda publicada a medias.** El 5 y el 6 de octubre de 2026
  XM publicó la demanda incompleta (22% de lo normal, con la generación normal).
  Un día cuya demanda comercial es menos de la mitad de la mediana de los 28
  días anteriores queda con la demanda vacía, y con ella lo que se calcula a
  partir de la demanda. La regla está en `dias_demanda_incompleta()` del paso 2
  y ningún otro día desde 2015 la cumple, ni siquiera en la cuarentena de 2020.
- **Solar de noche.** Desde 2025 aparecen valores pequeños de generación solar en
  horas sin sol (máximo de 5 MWh frente a unos 3.000 al mediodía),
  probablemente baterías.

## Comprobaciones

- El promedio de las 24 horas reproduce el precio diario (diferencia máxima de
  0,004 COP/kWh, por redondeo).
- Las sumas horarias de demanda, generación programada y restricciones
  reproducen exactamente los totales diarios.
- La generación ideal es igual a la real en la mediana (cociente 1,000).
- Cada hora tiene exactamente una planta marginal, y gas + carbón + líquidos
  suman el CO2 total.
- Al alterar todos los datos de un día y reconstruir las características, ese
  día solo cambian las columnas ex ante que tienen datos en esa fecha.

## Lo que hay que saber al modelar

- **La muestra no es 24 veces más grande en información.** Las 24 horas de un
  día comparten el estado del sistema. Hay que partir por fechas, nunca por
  filas, y una prueba como Diebold-Mariano debería hacerse sobre el error
  promedio de cada día.
- **Festivos de 2026.** El conteo va hasta el 9 de octubre; faltan los de
  octubre a diciembre.

---

# Panel de características: `panel_caracteristicas.csv.gz`

Lo arma `2c_caracteristicas_horarias.py` a partir del panel completo. Guarda
las variables base (una columna por variable, ya transformada y sin rezagos),
el calendario y los objetivos. Las columnas derivadas (rezagos, medias móviles,
tendencia y variabilidad) no se guardan: las arma `features.py` en memoria.

Este paso no mira el objetivo ni hace pruebas estadísticas. Cada variable se
transforma con una regla fija según lo que mide, y lo único que deja variables
por fuera es el filtro de calidad. La elección queda para el paso 2d.

| | |
|---|---|
| Filas | 103.200 (todo el panel horario, 24 horas por día) |
| Columnas | 194: 61 fijas (con `fecha` y `hora`) y 133 variables base |
| Tamaño | 20 MB |
| Diccionario | `panel_caracteristicas_variables.csv`: una fila por variable, con grupo, tipo (precio, horaria o diaria), de qué columnas sale, regla, faltantes, si se conoce de antemano, atraso extra, cuántas columnas derivadas tiene y si entra |

La regla de información es la del panel para modelar (más abajo): la fila (día
t, hora H) se para al cierre del día t y el objetivo es
`y_h = log P(t+h, H) − log P(t, H)`. El atraso de publicación (`ATRASO_EXTRA`)
y el relleno de huecos sueltos (hasta 3 días, con la misma hora del día
anterior) son los mismos.

## Variables base: 134

**Precio.** `lp` = log(precio).

**Horarias (44).** Las 41 del paso 2d, con la misma definición: cantidades
sobre la demanda o la generación de esa hora, precios y ofertas en logaritmo.
Más tres nuevas:

| Variable | Regla | Qué mide |
|---|---|---|
| `error_cmg_despacho` | lp − log(costo marginal programado) | cuánto se equivocó el despacho programado frente al precio que salió |
| `brecha_escasez` | lp − log(precio de escasez) | distancia al techo regulatorio; es positiva en 12% de las horas (sobre todo 2015-2016, 2020 y 2023-2026) |
| `presion_hidro_horaria` | demanda de la hora / (aportes del día / 24) | cuánta demanda hay por cada MWh de agua que entra |

**Diarias (89).** Repetidas en las 24 horas de su día. Las cantidades del
sistema se pasan a GWh y se dividen por la media móvil de 7 días de la demanda
diaria (`dem7`), que solo mira hacia atrás y no mete el ruido de domingos y
festivos. Los eventos (vertimientos, demanda no atendida y generación por
combustible) valen 0 en un día con datos y sin fila.

| Grupo | Cuántas | Variables y regla |
|---|---|---|
| Aportes | 7 | porcentaje del sistema y de los ríos; caudal sobre su media histórica (nueva); media histórica de XM en GWh; concentración entre ríos, participación de los 3 mayores, número de ríos |
| Embalses | 10 | volumen útil del sistema (2 versiones) y de Peñol, Bogotá, Guavio y Esmeralda; concentración; `dias_autonomia` = volumen útil / `dem7` (nueva, mediana 56 días); capacidad útil / `dem7`; vertimientos / `dem7` |
| Lluvia | 21 | tal cual: acumulados, anomalías, razones, por cuenca, contraste norte-sur |
| El Niño | 11 | tal cual: las 4 regiones, tendencias de 4 y 12 semanas, contraste costa-centro, ONI, RONI |
| IDEAM | 7 | tal cual: predicción de lluvia en 4 regiones, déficit, probabilidad máxima, fase de El Niño |
| Mezcla por planta | 13 | gas, carbón, líquidos, biomasa, no despachada y filo de agua como fracción de la generación del día; fracción de gas en la térmica, del despacho central y del filo de agua en la hidráulica; concentración, participación de las 5 mayores, número de plantas; disponibilidad del despacho central / `dem7` |
| Curva de ofertas del día | 10 | percentiles 25, 50 y 75, mínimo y máximo (en log); dispersión; pendiente; capacidad a menos de 100, 300 y 1.000 $/kWh / `dem7` |
| Sistema y regulación | 10 | capacidad efectiva, ENFICC y obligaciones de energía en firme / `dem7`; margen de reserva; cargo por confiabilidad, precio de escasez y TRM en log; demanda máxima de potencia sobre la demanda media por hora; demanda no atendida (2) / `dem7` |

**Fuera por el filtro de calidad** (más de 1% de faltantes desde marzo de
2015): el volumen de El Quimbo (5,8%) y la predicción de lluvia del Pacífico
(3,2%).

**Fuera por diseño:** las 5 alertas del IDEAM (tienen ceros falsos en
2019-2021), las 4 variantes del precio de escasez, CEE, CERE y MC, las 3
proyecciones de la UPME, las 9 que empiezan tarde (ya salen en el paso 2b), y las que se usan solo
normalizadas (volumen y capacidad en kWh, aportes por río en kWh). Tampoco
descargas, turbinado ni vertido por embalse: van en volumen de agua y los
reportan entre 1 y 23 embalses según el día, así que la suma no es comparable
en el tiempo.

## Qué se tomó del plan de variables y qué se ajustó

El diseño sigue el plan de variables revisado (documento personal "Plan
variables"), ajustado a lo que permiten los datos:

| Propuesta del plan | Resultado | Decisión |
|---|---|---|
| `error_cmg_despacho` | se puede | entra |
| `brecha_escasez` con el precio de escasez de activación | esa versión tiene un hueco de 14 meses en 2025-2026 | entra, con `precio_escasez` (0,07% de faltantes) |
| `presion_hidro_horaria` | se puede | entra |
| `estrechez_horaria` = demanda / disponibilidad | es exactamente 1 / `margen_declarado` | no entra |
| `spread_termico_hidro` (diaria) | correlación de 0,993 con la fracción térmica del día | no entra |
| `dias_autonomia` | se puede | entra, en lugar del volumen en kWh |
| aportes sobre su media móvil de 365 días | los datos empiezan en enero de 2015: se perdería todo 2015. XM ya publica la media histórica, y energía / media histórica = `aportes_pct_sistema` | se usa la media histórica de XM: el caudal sobre su media es nueva; la energía ya estaba |
| descargas, turbinado y vertido por embalse sobre la demanda | van en volumen de agua y cambia el número de embalses que reportan | no entran; queda el vertimiento del sistema en energía |
| índice SOI | no está en los datos | no entra |
| ADF y KPSS para decidir la transformación | — | no se usan: regla fija por tipo de variable, y la tendencia la dan `ma7_menos_ma30` y `delta_7d` |

## Columnas fijas: 61

| Bloque | Columnas | Cuántas |
|---|---|---|
| Identificación | `fecha`, `hora`, `bloque`, `precio`, `lp` | 5 |
| Calendario del día t | `dia_semana`, `mes`, `es_festivo` | 3 |
| Calendario cíclico del día t | seno y coseno de la hora (ciclo de 24), del día de la semana (7), del día del año (365,25) y del mes (12) | 8 |
| Calendario del día objetivo, para cada horizonte | `dia_semana_h{h}`, `es_festivo_h{h}` y el seno y coseno del día de la semana | 36 |
| Objetivos | `y_h1` … `y_h7`, `y_h14`, `y_h30` | 9 |

**Por qué seno y coseno.** Con el número tal cual, la hora 24 y la hora 1
quedan lejos aunque son vecinas; lo mismo domingo y lunes, o diciembre y enero.
Con el par seno-coseno quedan en un círculo, y la distancia entre la hora 24 y
la 1 es la misma que entre la 1 y la 2. Hace falta el par: con solo el seno,
dos horas distintas tienen el mismo valor. A un árbol casi no le cambia nada,
porque puede cortar el número tal cual, pero ayuda a los modelos lineales, a
SARIMAX y a las redes. Se dejan las dos versiones. Fuente: Galli, sección 15.

## Columnas derivadas: el catálogo de `features.py`

`fe.armar_todas(base, info)` arma todas; `fe.armar(base, info, nombres)` solo
las pedidas. Todo usa horas que ya pasaron al cierre del día t, salvo las
`_manana`.

| Familia | Precio (`dlp_`, `lp_`) | Cada horaria | Cada diaria |
|---|---|---|---|
| Rezagos en horas | 1 a 23, como lp − lp de hace k horas | 0 a 3 | — |
| Misma hora, días antes | 1, 2, 3, 7, 14, 21, 28 | 1, 2, 3, 7, 14 | días 0, 1, 2, 7 |
| Resumen del día t | hora 24, promedio, rampa (máximo − mínimo) | igual | — |
| Media móvil a la misma hora | 7 y 30 días | igual | 7 y 30 días |
| Media móvil de todas las horas | 168 y 720 horas | igual | — |
| Tendencia | — | `ma7_menos_ma30` a la misma hora | `delta_7d` (día t − día t−7) y `ma7_menos_ma30` |
| Variabilidad a la misma hora | desviación de 7 y 30 días, sobre el cambio diario | desviación de 7 y 30 días | igual |
| Variabilidad de todas las horas | desviación de 24 y 168 horas | igual | — |
| Memoria de picos | `dlp_max_24h` (máximo de las últimas 24 horas − lp) y `dlp_max_7d` (máximo a esa hora en 7 días − lp) | — | — |
| De mañana | — | `_manana`: solo costo marginal programado, pronóstico de demanda, disponibilidad sobre demanda pronosticada y fracción térmica de la disponibilidad | — |
| Columnas por variable | 43 | 21 (22 las de mañana) | 10 |

Una ventana se calcula si tiene al menos 75% de sus datos, para que un hueco
suelto no borre un mes de medias.

Fuentes: los rezagos del precio salen del modelo LEAR (Lago et al., 2021), con
14, 21 y 28 días por el ciclo semanal; las medias de día, semana y mes, del
modelo HAR (Corsi, 2009). La rampa, la tendencia y la memoria de picos son
decisión propia.

**Tamaño.** 101.712 filas (desde marzo de 2015, horas con precio) × 1.920
columnas: 59 fijas y 1.861 derivadas (43 del precio, 928 de las horarias y 890
de las diarias), más `fecha` y `hora` en el índice. Son 806 MB en float32 y se
arman en unos 2 segundos. Ninguna columna derivada tiene más de 1% de
faltantes.

## Comprobaciones del panel de características

- **Sin fuga, sobre todo el flujo.** Se alteran los datos crudos posteriores al
  15 de junio de 2021 y se corre de nuevo todo: relleno, atraso, variables base
  con sus normalizaciones móviles y el catálogo completo. En los días ≤ D solo
  cambian las 4 columnas `_manana`, y solo el día D. La prueba corre cada vez
  que se arma el panel.
- Las 41 horarias que vienen del paso 2d dan lo mismo que allá (salvo el
  redondeo a 6 cifras del archivo).
- Seno² + coseno² = 1 en todas las cíclicas; el día de la semana objetivo a 7
  días es el mismo de la fila.
- Rangos con sentido: `dias_autonomia` entre 21 y 76 días; las fracciones de la
  generación entre 0 y 1 y suman menos de 1; `contrato_frac` pasa de 1 porque
  los generadores también compran en contratos.
- Casos a mano en `armar_todas()`: `demanda_l1d` es la demanda de 24 filas
  antes, `dlp_l1h` es lp menos el de la hora anterior, la media de 7 días a la
  misma hora y la desviación de 24 horas coinciden con pandas, `dlp_max_24h` y
  `dlp_max_7d` nunca son negativas, y `armar()` da lo mismo que `armar_todas()`.

---

# Panel para modelar: `panel_horario_modelo.csv.gz`

Lo arma `2d_seleccion_variables.py`. De las 1.861 columnas derivadas del panel
de características (paso 2c) elige, para cada horizonte, las que van al modelo.
`lp` y el calendario entran siempre.

**La selección está congelada desde el 1 de noviembre de 2026.** Varias de sus
reglas se decidieron mirando 2020-2022 (ver "Qué decisiones miraron la
validación"), así que no se les cambia nada más.

| | |
|---|---|
| Filas | 101.712 (1 de marzo de 2015 a 6 de octubre de 2026, 24 horas por día) |
| Columnas | 118: `fecha`, `hora`, `bloque`, `precio`, `lp`, 47 de calendario (11 del día t y 4 del día objetivo por horizonte), 9 objetivos y 57 columnas elegidas en algún horizonte |
| Columnas por horizonte | h1: 20, h2: 10, h3: 10, h4: 20, h5: 10, h6: 10, h7: 20, h14: 10, h30: 10 (más `lp` y 16 de calendario) |
| Tamaño | 12,5 MB |

Tres archivos acompañan la tabla:

- `panel_horario_modelo_columnas.csv`: cada columna, con su variable y, por
  horizonte, su correlación de Spearman con el objetivo, qué le pasó en la
  limpieza, su importancia, su orden, si entra (`entra_h`) y si está en la
  lista corta (`corta_h`).
- `panel_horario_modelo_validacion.csv`: el error en 2020-2022 con las primeras
  k columnas del orden, para cada horizonte.
- `panel_horario_modelo_variables.csv`: la importancia sumada por variable, en
  porcentaje del total, y cuántas de sus columnas entran en cada horizonte.

La primera versión de este paso elegía con pruebas lineales (ADF, Granger y
Wald con errores de Driscoll-Kraay). Está en `legacy/seleccion_lineal/` con sus
salidas, que son las que usaron los experimentos de `legacy/experimentos_xgboost/`.

## La regla de información

Cada fila es (día t, hora H) y se para al cierre del día t: se conocen las 24
horas del día t y todo lo anterior. El objetivo es

    y_h = log P(t+h, H) − log P(t, H),     h = 1 … 7, 14 y 30      (columnas y_h1 … y_h30)

y el ingenuo (y = 0) es "a esa hora, igual que hoy". Como la base del objetivo
es el precio del día t, el día t entra completo; por eso valen los rezagos de
horas. Esto corrige un desajuste del panel diario y de la primera versión de
las características horarias, donde el objetivo era el cambio frente al día t
pero las características llegaban solo hasta t−1.

Lo único que mira más allá del día t son las columnas `*_manana` (costo marginal
del despacho programado y disponibilidad declarada sobre demanda pronosticada,
del día t+1). Que se publiquen antes del cierre del día t es una suposición:
el despacho del día siguiente se publica la víspera, pero no se verificó la
hora exacta.

**Atraso de publicación.** El precio sale con 2 días de atraso: con datos hasta
t, el pronóstico real de mañana es h = 3. Las variables que se publican más
tarde que el precio entran con el atraso adicional: la curva de mérito y el
recurso marginal con 8 días más, los contratos, las pérdidas y las
restricciones con 3.

## Cómo se eligieron

Para cada horizonte, en tres etapas. Entre entrenamiento y evaluación se dejan
h+1 días.

1. **Limpieza, con 2015-2019.**
   - Salen 10 columnas casi constantes (un mismo valor en 99% de las horas o
     más).
   - Salen 106 inestables: más de 25% de sus valores de 2018-2019 quedan fuera
     del rango de 2015-2017 (percentiles 1 a 99). Son niveles que se corren con
     el tiempo, como los precios de contratos en pesos, el número de plantas,
     la participación solar o los promedios de la demanda. Un árbol no
     extrapola: todo lo que pasa del máximo que vio cae en la misma hoja.
   - Salen 12 columnas de nivel del cargo por confiabilidad y la TRM. El cargo
     se fija en dólares (CREG 071 de 2006, art. 29) y en pesos se mueve con la
     TRM, así que su nivel sigue al dólar y no al mercado de energía. De esas
     dos variables quedan solo `delta_7d`, `ma7_menos_ma30` y la variabilidad.
   - De cada grupo de columnas con correlación de Spearman mayor a 0,95 queda
     la más correlacionada con el objetivo del horizonte. Para eso se recorren
     de mayor a menor correlación con el objetivo, y una se queda solo si no
     pasa de 0,95 con ninguna de las que ya quedaron. Quedan unas 1.290 por
     horizonte.
2. **Orden, con 2015-2019.** Se entrena XGBoost con 2015-2017 y se mide en 2018,
   y con 2015-2018 y se mide en 2019. Al modelo se le agregan 10 columnas de
   ruido: copias de columnas al azar con los días barajados. La importancia de
   cada columna es el promedio de su |SHAP| en el año que el modelo no vio.
   Sigue la que le gana al mejor ruido en los dos años, y se ordenan por el
   promedio.
3. **Cuántas, con 2020-2022.** Con las primeras k del orden (10, 20, 40, 80, 160
   y todas las que pasaron) se entrena con 2015-2019 y se mide en 2020-2022. El
   error es el promedio por día del error cuadrático en log, con error estándar
   de Newey-West (h − 1 + 7 rezagos). Entra el k más chico cuyo error no pasa
   el del mejor más un error estándar.

La lista corta son las primeras 20, o las k elegidas si son menos, para
SARIMAX o una LSTM.

XGBoost va con una configuración fija (profundidad 5, tasa 0,05, 600 árboles),
la del medio de la rejilla de los experimentos anteriores. Aquí solo ordena columnas; los
modelos de pronóstico van aparte.

## Qué quedó

| h | Tras la limpieza | Le ganan al ruido | Entran | RMSE log en 2020-2022 (modelo / ingenuo) | Mejora |
|---|---|---|---|---|---|
| 1 | 1.291 | 40 | 20 | 0,133 / 0,175 | 24,2% |
| 2 | 1.291 | 13 | 10 | 0,166 / 0,212 | 21,7% |
| 3 | 1.289 | 15 | 10 | 0,206 / 0,240 | 14,2% |
| 4 | 1.290 | 43 | 20 | 0,233 / 0,263 | 11,4% |
| 5 | 1.291 | 89 | 10 | 0,259 / 0,278 | 6,8% |
| 6 | 1.290 | 99 | 10 | 0,282 / 0,292 | 3,3% |
| 7 | 1.289 | 117 | 20 | 0,308 / 0,302 | −1,9% |
| 14 | 1.288 | 77 | 10 | 0,382 / 0,386 | 0,9% |
| 30 | 1.290 | 105 | 10 | 0,458 / 0,500 | 8,2% |

Estas mejoras son optimistas: la validación se usó para decidir (ver abajo).

En total entran 57 columnas de 32 variables: 14 del precio, 23 de variables
horarias y 20 de diarias.

- **El precio** encabeza casi todos los horizontes. `dlp_ma7d_mh` y
  `dlp_ma30d_mh` entran en los nueve: cuánto se aparta el precio de hoy de sus
  medias a esa hora. Es la reversión a la media.
- **A un día manda lo que ya se decidió para mañana:** el costo marginal
  programado (`cmg_despacho_manana`, la primera de h = 1), el pronóstico de
  demanda y la disponibilidad sobre la demanda pronosticada. El grupo del costo
  marginal pesa 17% en h = 1 y 4% o menos desde h = 2.
- **Con el horizonte, el peso pasa a la hidrología y el clima.** De h = 1 a
  h = 30, la lluvia pasa de 4% a 12% y los embalses de 2% a 12%. El Niño pasa de
  1% a 6% en h = 14. En h = 30 entran la concentración de la generación, el
  caudal sobre su media, el volumen de los embalses de Bogotá, el ONI y la
  lluvia de 90 días.
- **Variables nuevas del plan que entraron:** `brecha_escasez` (h = 1, 7 y 14; es
  la primera de h = 14), `error_cmg_despacho` (h = 1 y 2), `presion_hidro_horaria`
  (h = 3, 4 y 5), la capacidad útil de los embalses (h = 4) y el caudal sobre su
  media (h = 4 y 30). `dias_autonomia` no entró.
- **Solo con `lp` y el calendario** (k = 0) el modelo pierde contra el ingenuo
  en ocho de los nueve horizontes.
- **h = 7 pierde contra el ingenuo y h = 14 casi empata.** En h = 7 ningún k le
  gana. El diagnóstico mostró que la pérdida se concentra en 2021: el precio
  estuvo bajo todo el año (mediana de 108 COP/kWh) y el modelo pronosticó
  subidas que no llegaron.

## Qué decisiones miraron la validación

- **Por diseño:** cuántas columnas entran (etapa 3).
- **El filtro de estabilidad:** la fórmula solo usa 2015-2019, pero se agregó y
  se eligió el umbral de 25% después de ver qué columnas fallaban en 2020-2022
  en h = 7.
- **La regla del dólar:** salió de ver que h = 14 caía a −6,6% por
  `precio_cargo_conf_ma30d`.

Por eso los errores de 2020-2022 no estiman lo que pasará con datos nuevos. El
modelo no entrenó con esos años, pero las reglas sí se ajustaron a ellos.

**La prueba (2023-2026).** Las columnas del paso 2d no la leen: `matriz()` falla si
se le piden filas posteriores a 2022, y el diagnóstico de h = 7 tampoco usó esas
filas. La respuesta sí alcanza a cruzar: en la etapa 3, los objetivos de los últimos
h días de 2022 caen en enero de 2023 (0,6% de las filas de validación en h = 7,
2,7% en h = 30). Se detectó después de congelar y quedó así; el modelo del notebook
5 sí lo impide. El filtro de calidad del paso 2c cuenta faltantes hasta 2026, pero
contando solo 2015-2019 salen las mismas dos variables. Esos años, además, ya se
vieron:
los experimentos de `legacy/experimentos_xgboost/` validaron y probaron ahí con la selección lineal, y se
leyeron sus resultados. Se usa una sola vez, con el modelo final.

## Comprobaciones

- **Filtro y regla por separado.** Mejora en 2020-2022 en cada corrida:

  | h | Sin filtro | Con filtro | Con filtro y regla del dólar (final) |
  |---|---|---|---|
  | 1 | 25,7% | 24,3% | 24,2% |
  | 2 | 20,8% | 21,7% | 21,7% |
  | 3 | 10,9% | 14,5% | 14,2% |
  | 4 | 7,0% | 12,4% | 11,4% |
  | 5 | 7,3% | 8,9% | 6,8% |
  | 6 | 2,5% | 5,4% | 3,3% |
  | 7 | −1,1% | 0,3% | −1,9% |
  | 14 | 5,4% | −6,6% | 0,9% |
  | 30 | 8,5% | 11,2% | 8,2% |

- **Ruido entre corridas.** De la segunda a la tercera corrida solo cambió la
  regla del dólar, que saca una columna elegida, y casi todas las listas quedaron
  iguales: 9 de 10 o 19 de 20. Aun así la mejora se movió hasta 2 puntos (h = 5
  y h = 7), en parte porque al cambiar las candidatas cambian las columnas de
  ruido. En h = 6 entran 10 en vez de 20. Diferencias de 2 puntos entre estas
  corridas no son evidencia de nada.
- **Límites.** SHAP en el año no visto mide cuánto usa el modelo una columna, no
  si baja el error. Con solo 10 columnas de ruido el umbral es más bajo que en
  Boruta, que usa una sombra por columna. La etapa 3 mira un solo periodo y una
  sola semilla, y la curva del error contra k es irregular.

## Al modelar

- `columnas(h)` en la sección 4c del notebook 3 da las columnas del horizonte
  h, con `lp` y el calendario, de la más a la menos importante.
  `columnas(h, corta=True)` da la lista corta.
- Se parte por la columna `bloque`, nunca por filas, y entre entrenamiento y
  prueba se dejan h+1 días.
- Las 24 filas de un día comparten el estado del sistema: para Diebold-Mariano
  conviene promediar el error de cada día antes de la prueba.
- En h = 7 y h = 14 hay que comparar siempre contra el ingenuo: en la validación
  no le ganaron de forma clara.
