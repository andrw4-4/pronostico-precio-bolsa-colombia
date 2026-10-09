# Pronóstico del precio de bolsa de energía en Colombia

Tesis de pregrado, Universidad de los Andes. Pronóstico del precio de bolsa diario
del mercado eléctrico colombiano con datos públicos de XM, NOAA y ERA5.

Hay dos modelos:

- Modelo 1, a un día: un número, el precio de mañana en COP/kWh.
- Modelo 2, a siete días: una distribución (mediana, intervalo del 80% y
  probabilidad de pasar de 300, 500 u 800 COP/kWh).

## Cómo se corre

```bash
pip install pandas numpy scikit-learn xgboost statsmodels scipy matplotlib openpyxl pydataxm
python 1_descargar.py        # baja los datos a datos/
python 2_construir_panel.py  # arma panel_diario.csv
```

Después se abre `3_modelos.ipynb`. El notebook solo necesita `features.py` y
`panel_diario.csv`, así que también corre en Colab sin los pasos 1 y 2.

La primera descarga tarda varias horas; después solo pide los días nuevos.
El listado de plantas (`datos/Listado_Recursos_Generacion.xlsx`) se baja a mano de
PARATEC, en la página de XM.

## Archivos

| Archivo | Qué hace |
|---|---|
| `1_descargar.py` | baja las series de XM, El Niño de NOAA, la lluvia de ERA5 y la TRM |
| `2_construir_panel.py` | lleva todo a un valor por día y calcula las variables derivadas |
| `features.py` | ingeniería de características: rezagos, medias, choques y limpieza |
| `3_modelos.ipynb` | los dos modelos, su evaluación y el pronóstico del día |
| `panel_diario.csv` | el panel que produce el paso 2 |
| `DOCUMENTACION.md` | explicación completa: fuentes, decisiones, resultados y referencias |
| `legacy/` | versiones anteriores y experimentos que no funcionaron |
