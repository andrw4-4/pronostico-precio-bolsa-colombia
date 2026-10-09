# Diccionario de variables — panel ampliado

Generado por `00b_ampliar_panel.py`. Panel resultante: **4018 días × 104 variables** (58 del panel original + 46 nuevas), del 2015-01-01 al 2025-12-31.

Archivo de datos: `panel_diario_ampliado.csv`

## Cómo leer este documento

Cada variable nueva lleva: qué significa, **de dónde salió** (fuente primaria y archivo concreto), cómo se calculó, y una advertencia cuando hay algo que puede llevar a un error de interpretación o a fuga de información.

**Ninguna variable de este panel está rezagada.** Tal como están, la mayoría son información que se conoce al cierre del día y usarlas sin rezago sería fuga. El rezago lo aplica el notebook, no este archivo.

---

## Fuentes primarias

| Fuente | Qué aporta | Acceso |
|---|---|---|
| **XM API (`servapibi.xm.com.co`)** | generación, disponibilidad, aportes, volúmenes, precios, demanda | `pydataxm`, cacheado en `cache_api/` |
| **Listado de Recursos de Generación (XM)** | planta → tecnología, combustible, tipo de despacho, clasificación, departamento | `data/Listado_Recursos_Generacion.xlsx` |
| **Ministerio de Minas / datos abiertos** | precios de GNCV | `data/Consulta_Precios_Promedio_de_Gas_Natural_*.csv` |
| **NOAA CPC** | índice ONI de El Niño | `data/oni_noaa.csv` (ya en el panel base) |
| **Banco de la República** | TRM | `data/Tasa de cambio del peso colombiano.csv` (ya en el panel base) |

---

## Mezcla de generacion

### `gen_hidraulica`

**Energia generada por las plantas de tipo HIDRAULICA.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), cruzada con el Listado de Recursos de Generacion de XM.
- **Cálculo:** Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `gen_termica`

**Energia generada por las plantas de tipo TERMICA.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), cruzada con el Listado de Recursos de Generacion de XM.
- **Cálculo:** Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `gen_solar`

**Energia generada por las plantas de tipo SOLAR.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), cruzada con el Listado de Recursos de Generacion de XM.
- **Cálculo:** Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.
- **Cobertura:** 76.1% de los días (2017-08-19 a 2025-12-31)

### `gen_eolica`

**Energia generada por las plantas de tipo EOLICA.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), cruzada con el Listado de Recursos de Generacion de XM.
- **Cálculo:** Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.
- **Cobertura:** 89.2% de los días (2015-01-01 a 2025-12-31)

### `gen_cogenerador`

**Energia generada por las plantas de tipo COGENERADOR.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica Gene por Recurso (cache_api/gen_por_recurso.parquet), cruzada con el Listado de Recursos de Generacion de XM.
- **Cálculo:** Suma de las 24 horas de cada planta del tipo, sumada sobre plantas.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `frac_hidraulica`

**Participacion de hidraulica en la generacion total del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada de gen_* y gen_total_sistema.
- **Cálculo:** gen_hidraulica / gen_total_sistema.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es la variable interesante para el precio: lo que importa no es cuanto genera la hidraulica sino que tanto del sistema depende de ella.

### `frac_termica`

**Participacion de termica en la generacion total del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada de gen_* y gen_total_sistema.
- **Cálculo:** gen_termica / gen_total_sistema.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es la variable interesante para el precio: lo que importa no es cuanto genera la hidraulica sino que tanto del sistema depende de ella.

### `frac_solar`

**Participacion de solar en la generacion total del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada de gen_* y gen_total_sistema.
- **Cálculo:** gen_solar / gen_total_sistema.
- **Cobertura:** 76.1% de los días (2017-08-19 a 2025-12-31)

> **Advertencia.** Es la variable interesante para el precio: lo que importa no es cuanto genera la hidraulica sino que tanto del sistema depende de ella.

### `frac_eolica`

**Participacion de eolica en la generacion total del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada de gen_* y gen_total_sistema.
- **Cálculo:** gen_eolica / gen_total_sistema.
- **Cobertura:** 89.2% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es la variable interesante para el precio: lo que importa no es cuanto genera la hidraulica sino que tanto del sistema depende de ella.

### `gen_fncer`

**Generacion de fuentes no convencionales de energia renovable (solar + eolica).**

- **Unidad:** GWh/dia
- **Fuente:** Derivada de gen_solar + gen_eolica.
- **Cálculo:** Suma de solar y eolica.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `frac_fncer`

**Penetracion de renovables no convencionales en la generacion del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada.
- **Cálculo:** gen_fncer / gen_total_sistema.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Practicamente cero antes de 2021: la capacidad solar del pais era marginal.

---

## Generacion por combustible

### `gen_gas`

**Energia generada quemando gas (GAS, MEZCLA GAS - CARBÓN, MEZCLA GAS-FUEL OIL (ACPM O COMBUSTOLEO)).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Combustible por Defecto' del Listado de Recursos.
- **Cálculo:** Suma diaria de las plantas cuyo combustible por defecto esta en la lista.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es el combustible POR DEFECTO declarado, no el realmente quemado ese dia: una planta dual puede estar operando con el otro combustible.

### `gen_carbon`

**Energia generada quemando carbon (CARBON).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Combustible por Defecto' del Listado de Recursos.
- **Cálculo:** Suma diaria de las plantas cuyo combustible por defecto esta en la lista.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es el combustible POR DEFECTO declarado, no el realmente quemado ese dia: una planta dual puede estar operando con el otro combustible.

### `gen_liquidos`

**Energia generada quemando liquidos (ACPM, COMBUSTOLEO, CRUDO, DIESEL MAR).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Combustible por Defecto' del Listado de Recursos.
- **Cálculo:** Suma diaria de las plantas cuyo combustible por defecto esta en la lista.
- **Cobertura:** 83.2% de los días (2015-01-05 a 2025-12-31)

> **Advertencia.** Es el combustible POR DEFECTO declarado, no el realmente quemado ese dia: una planta dual puede estar operando con el otro combustible.

### `gen_biomasa`

**Energia generada quemando biomasa (BAGAZO, BIOMASA, BIOGAS).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Combustible por Defecto' del Listado de Recursos.
- **Cálculo:** Suma diaria de las plantas cuyo combustible por defecto esta en la lista.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es el combustible POR DEFECTO declarado, no el realmente quemado ese dia: una planta dual puede estar operando con el otro combustible.

### `frac_gas_en_termica`

**Que parte del parque termico en operacion esta quemando gas frente a carbon o liquidos.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada.
- **Cálculo:** gen_gas / gen_termica.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Proxy del costo marginal termico: los liquidos son mucho mas caros que el gas, asi que si esta fraccion cae, el termico marginal se encarecio.

---

## Estructura del despacho

### `gen_despacho_central`

**Energia generada por plantas con tipo de despacho DC (centralizado, participan en el orden de merito).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Tipo Despacho' del Listado de Recursos.
- **Cálculo:** Suma diaria por tipo de despacho.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `gen_no_despachado`

**Energia generada por plantas con tipo de despacho ND (no despachadas centralmente).**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Tipo Despacho' del Listado de Recursos.
- **Cálculo:** Suma diaria por tipo de despacho.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `frac_despacho_central`

**Parte del sistema que se forma en el mercado centralizado.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada.
- **Cálculo:** gen_despacho_central / gen_total_sistema.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Solo las plantas DC ofertan precio, asi que esta fraccion mide que tanto del sistema pasa por el mecanismo que fija el precio de bolsa.

---

## Hidrologia estructural

### `gen_filo_agua`

**Generacion de plantas hidraulicas a filo de agua, que no tienen embalse y deben turbinar el caudal que llega o perderlo.**

- **Unidad:** GWh/dia
- **Fuente:** XM API Gene por Recurso + columna 'Clasificacion' del Listado de Recursos.
- **Cálculo:** Suma diaria de las plantas clasificadas FILO DE AGUA o FILO AGUA ESPECIAL.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `frac_filo_en_hidro`

**Parte de la generacion hidraulica que no es almacenable.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada.
- **Cálculo:** gen_filo_agua / gen_hidraulica.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Distincion economica real: el agua embalsada tiene valor de opcion (se puede guardar para cuando el precio suba); la de filo de agua no.

---

## Concentracion de mercado

### `hhi_generacion`

**Indice Herfindahl-Hirschman de la generacion diaria por planta. Mide que tan concentrada esta la generacion del dia.**

- **Unidad:** indice 0-10.000
- **Fuente:** Derivada de XM API Gene por Recurso.
- **Cálculo:** Suma de los cuadrados de las participaciones de cada planta, x10.000.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Por encima de 2.500 se considera un mercado concentrado. Dias de alta concentracion implican mas poder de mercado y, en teoria, precios mas altos.

### `gen_top5_pct`

**Participacion de las cinco plantas mas grandes del dia en la generacion total.**

- **Unidad:** fraccion (0-1)
- **Fuente:** Derivada de XM API Gene por Recurso.
- **Cálculo:** Suma de las 5 participaciones mas altas de cada dia.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `n_plantas_activas`

**Numero de plantas que generaron algo ese dia.**

- **Unidad:** conteo
- **Fuente:** Derivada de XM API Gene por Recurso.
- **Cálculo:** Conteo de codigos de planta con generacion diaria mayor que cero.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Crece mucho a lo largo del periodo por la entrada de solares pequenias, asi que tiene tendencia: usar en diferencias o como choque.

---

## Disponibilidad por tecnologia

### `disp_decl_hidraulica`

**Disponibilidad declarada por las plantas HIDRAULICA.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica DispoDeclarada por Recurso (cache_api/disp_declarada.parquet) + Listado de Recursos.
- **Cálculo:** Suma de las 24 horas declaradas por cada planta del tipo.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es ex ante: se declara antes del despacho, asi que puede entrar con rezago 0 sin fuga.

### `disp_decl_termica`

**Disponibilidad declarada por las plantas TERMICA.**

- **Unidad:** GWh/dia
- **Fuente:** XM API, metrica DispoDeclarada por Recurso (cache_api/disp_declarada.parquet) + Listado de Recursos.
- **Cálculo:** Suma de las 24 horas declaradas por cada planta del tipo.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Es ex ante: se declara antes del despacho, asi que puede entrar con rezago 0 sin fuga.

### `disp_decl_despacho_central`

**Disponibilidad declarada por las plantas de despacho centralizado, que son las que realmente compiten por fijar el precio.**

- **Unidad:** GWh/dia
- **Fuente:** XM API DispoDeclarada por Recurso + Tipo Despacho del Listado.
- **Cálculo:** Suma diaria de las plantas DC.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

---

## Hidrologia desagregada

### `hhi_aportes_rios`

**Concentracion de los aportes hidricos entre los 47 rios del sistema.**

- **Unidad:** indice 0-10.000
- **Fuente:** XM API, metrica AporEner por Rio (cache_api/aportes_por_rio.parquet).
- **Cálculo:** Herfindahl sobre la participacion de cada rio en el aporte total del dia.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Un valor alto significa que el sistema depende de pocas cuencas ese dia, que es una fragilidad que el agregado del sistema no muestra.

### `aportes_top3_pct`

**Parte del aporte hidrico total que viene de las tres cuencas mas caudalosas del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API AporEner por Rio.
- **Cálculo:** Suma de las 3 participaciones mas altas.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `n_rios_aportando`

**Numero de rios con aporte positivo reportado ese dia.**

- **Unidad:** conteo
- **Fuente:** XM API AporEner por Rio.
- **Cálculo:** Conteo de rios con Value > 0.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

### `vol_pct_penol`

**Nivel del embalse PENOL como fraccion de su capacidad util.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner por Embalse (cache_api/volumen_por_embalse.parquet y capacidad_por_embalse.parquet).
- **Cálculo:** volumen_util(PENOL) / capacidad_util(PENOL).
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Este embalse esta entre los cinco de mayor capacidad del pais. El agregado nacional esconde que un embalse grande y regulador puede estar critico mientras el promedio se ve normal. Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM reporta volumen por encima de la capacidad util declarada cuando el embalse esta rebosando. No se recorta a 1 a proposito, porque ese exceso es informacion real (embalse lleno, vertimiento probable).

### `vol_pct_agregado_bogota`

**Nivel del embalse AGREGADO BOGOTA como fraccion de su capacidad util.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner por Embalse (cache_api/volumen_por_embalse.parquet y capacidad_por_embalse.parquet).
- **Cálculo:** volumen_util(AGREGADO BOGOTA) / capacidad_util(AGREGADO BOGOTA).
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Este embalse esta entre los cinco de mayor capacidad del pais. El agregado nacional esconde que un embalse grande y regulador puede estar critico mientras el promedio se ve normal. Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM reporta volumen por encima de la capacidad util declarada cuando el embalse esta rebosando. No se recorta a 1 a proposito, porque ese exceso es informacion real (embalse lleno, vertimiento probable).

### `vol_pct_guavio`

**Nivel del embalse GUAVIO como fraccion de su capacidad util.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner por Embalse (cache_api/volumen_por_embalse.parquet y capacidad_por_embalse.parquet).
- **Cálculo:** volumen_util(GUAVIO) / capacidad_util(GUAVIO).
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Este embalse esta entre los cinco de mayor capacidad del pais. El agregado nacional esconde que un embalse grande y regulador puede estar critico mientras el promedio se ve normal. Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM reporta volumen por encima de la capacidad util declarada cuando el embalse esta rebosando. No se recorta a 1 a proposito, porque ese exceso es informacion real (embalse lleno, vertimiento probable).

### `vol_pct_esmeralda`

**Nivel del embalse ESMERALDA como fraccion de su capacidad util.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner por Embalse (cache_api/volumen_por_embalse.parquet y capacidad_por_embalse.parquet).
- **Cálculo:** volumen_util(ESMERALDA) / capacidad_util(ESMERALDA).
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Este embalse esta entre los cinco de mayor capacidad del pais. El agregado nacional esconde que un embalse grande y regulador puede estar critico mientras el promedio se ve normal. Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM reporta volumen por encima de la capacidad util declarada cuando el embalse esta rebosando. No se recorta a 1 a proposito, porque ese exceso es informacion real (embalse lleno, vertimiento probable).

### `vol_pct_el_quimbo`

**Nivel del embalse EL QUIMBO como fraccion de su capacidad util.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API, metricas VoluUtilDiarEner por Embalse y CapaUtilDiarEner por Embalse (cache_api/volumen_por_embalse.parquet y capacidad_por_embalse.parquet).
- **Cálculo:** volumen_util(EL QUIMBO) / capacidad_util(EL QUIMBO).
- **Cobertura:** 92.4% de los días (2015-11-01 a 2025-12-31)

> **Advertencia.** Este embalse esta entre los cinco de mayor capacidad del pais. El agregado nacional esconde que un embalse grande y regulador puede estar critico mientras el promedio se ve normal. Algunos dias el cociente pasa ligeramente de 1 (hasta 1,04): XM reporta volumen por encima de la capacidad util declarada cuando el embalse esta rebosando. No se recorta a 1 a proposito, porque ese exceso es informacion real (embalse lleno, vertimiento probable).

### `hhi_volumen_embalses`

**Concentracion del agua almacenada entre los 24 embalses del sistema.**

- **Unidad:** indice 0-10.000
- **Fuente:** XM API VoluUtilDiarEner por Embalse.
- **Cálculo:** Herfindahl sobre la participacion de cada embalse en el volumen total.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

---

## Perfil intradiario del precio

### `precio_max_dia`

**Precio de bolsa mas alto del dia entre las 24 horas.**

- **Unidad:** COP/kWh
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** Maximo de las 24 columnas horarias.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

### `precio_min_dia`

**Precio de bolsa mas bajo del dia.**

- **Unidad:** COP/kWh
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** Minimo de las 24 columnas horarias.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

### `precio_spread_intradia`

**Diferencia entre la hora mas cara y la mas barata del dia.**

- **Unidad:** COP/kWh
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** precio_max_dia - precio_min_dia.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

### `precio_cv_intradia`

**Coeficiente de variacion del precio dentro del dia.**

- **Unidad:** razon
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** desviacion estandar horaria / media horaria.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

### `hora_precio_max`

**Hora del dia (1 a 24) en que el precio alcanzo su maximo.**

- **Unidad:** COP/kWh
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** Indice de la columna horaria con el valor mas alto.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

### `ratio_pico_valle`

**Cuantas veces mas caro fue el pico frente al valle. Vale exactamente 1 en los dias en que el precio fue plano las 24 horas, que son dias en que una sola planta quedo marginal todo el dia o en que el precio toco el techo de escasez (paso 15 veces entre 2015 y 2025, tres de ellas en 2024 con el precio pegado en ~2.460 COP/kWh).**

- **Unidad:** razon
- **Fuente:** XM API, metrica PrecBolsNaci por Sistema, version horaria (data/PrecBolsNaci_Sistema.csv).
- **Cálculo:** precio_max_dia / precio_min_dia.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** CUIDADO: se calcula a partir del precio del mismo dia, asi que es informacion ex post. Solo puede usarse con rezago de al menos 1 dia. El pipeline la rezagara como cualquier otra variable medida durante el dia.

---

## Perfil intradiario de la demanda

### `demanda_pico`

**Demanda comercial de la hora de mayor consumo del dia.**

- **Unidad:** GWh en la hora pico
- **Fuente:** XM API, metrica DemaCome por Sistema, version horaria (data/DemaCome_Sistema.csv).
- **Cálculo:** Maximo de las 24 horas, pasado a GWh.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** El precio se forma en el margen: lo que estresa el sistema es la hora pico, no el promedio del dia.

### `factor_carga`

**Que tan plana es la curva de demanda del dia.**

- **Unidad:** fraccion (0-1)
- **Fuente:** XM API DemaCome por Sistema horaria.
- **Cálculo:** demanda media / demanda pico.
- **Cobertura:** 100.0% de los días (2015-01-01 a 2025-12-31)

> **Advertencia.** Un factor de carga bajo significa un pico pronunciado, que exige encender plantas caras solo unas horas.

---

## Costo de combustible

### `precio_gncv`

**Precio promedio publicado del gas natural comprimido vehicular, mediana nacional entre estaciones de servicio.**

- **Unidad:** COP/m3
- **Fuente:** Ministerio de Minas y Energia / datos abiertos, consulta de precios promedio de GNCV (data/Consulta_Precios_Promedio_de_Gas_Natural_Comprimido_Vehicular_(AUTOMATIZADO)_20260912.csv).
- **Cálculo:** Mediana de PRECIO_PROMEDIO_PUBLICADO por fecha, sobre todas las estaciones del pais. Se usa mediana y no media porque hay estaciones con precios atipicos.
- **Cobertura:** 1.2% de los días (2022-01-01 a 2025-12-01)

> **Advertencia.** LIMITACION IMPORTANTE: solo hay 57 fechas entre 2022 y 2026 (es una serie mensual, no diaria) y empieza en 2022, asi que queda vacia en la ventana de seleccion. Ademas es gas VEHICULAR, no el gas industrial que compran las termicas: sirve como proxy de la tendencia del costo del gas, no como su precio real. Tratarla con desconfianza.

---

## Variables de XM que NO se descargaron

El catálogo de la API (`cache_api/catalogo_metricas.parquet`, 193 métricas, 98 a nivel de Sistema) tiene más series que podrían agregarse. Las que parecen más prometedoras para el pronóstico del precio:

| MetricId | Qué es | Por qué podría servir |
|---|---|---|
| `DemaMaxPot` | Demanda máxima de potencia (kW) | el pico de potencia es lo que agota la capacidad disponible |
| `VolTurbMasa` | Volumen turbinado (m³) | uso real del agua, no solo el nivel almacenado |
| `CompNetArranPara` | Compras netas de arranque y parada (COP) | costo de encender térmicas, señal de rigidez del parque |
| `DeltaNal` / `DeltaInt` | Delta de incremento nacional / internacional | componentes del precio, se conocen por regulación |
| `RentasCongestRestr` | Rentas de congestión (COP) | congestión de la red, que separa precios regionales |
| `CompBolsNaciEner` / `VentBolsNaciEner` | energía comprada y vendida en bolsa (kWh) | volumen transado, mide liquidez del mercado spot |
| `PrecEscaSup` | Precio de escasez superior | falta esta variante; el panel ya tiene inferior, activación, ponderado y marginal |
| `RemuRealIndiv` | Remuneración real individual diaria (COP) | ingreso por cargo por confiabilidad |
| `SnTIEMerito` / `SnTIEFueraMerito` | saldo neto de transacciones internacionales | intercambio con Ecuador |
| `GeneIdea` | Generación ideal (sin restricciones de red) | la brecha contra la generación real mide cuánto cuesta la red |

Para bajarlas hay que extender `00_consolidar_panel.py` con el `MetricId` y la entidad correspondientes. El costo es una llamada más a la API por métrica.

### Fuentes externas que valdría explorar

- **Precio del gas natural industrial** (no el vehicular): es el costo marginal real de las térmicas a gas. Lo publica la Bolsa Mercantil de Colombia y en los informes de la CREG; no está en la API de XM.
- **Henry Hub** (referencia internacional de gas): el panel base tiene un prefijo `henry_hub` previsto en la configuración pero la serie no está descargada. Fuente: EIA de Estados Unidos.
- **Caudales del IDEAM**: aportes medidos en estación, con más resolución espacial que los agregados de XM por río.
- **Índices ENSO alternativos** (SOI, Niño 3.4, MEI): el panel usa solo ONI. Fuente: NOAA CPC.
