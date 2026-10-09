"""
Exploracion del inventario de series descargadas de la API de XM.

Lee todos los parquet de cache_api/, normaliza los dos formatos que entrega la
API (largo: Id/Value/Date  |  ancho horario: Values_Hour01..24) y produce:

  1. inventario_series.csv  - una fila por serie con cobertura y estadisticos
  2. cobertura_series.png   - mapa de disponibilidad por fecha
  3. series_<grupo>.png     - las series graficadas, agrupadas por tema
  4. comparacion_<grupo>.png- las mismas series en z-score para comparar dinamica

Uso:
    python explorar_series.py
"""

from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings('ignore')

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent
DIR_CACHE = RAIZ / 'cache_api'
DIR_OUT = RAIZ / 'salidas' / 'exploracion'
DIR_OUT.mkdir(parents=True, exist_ok=True)

FECHA_INI = '2015-01-01'
FECHA_FIN = '2025-12-31'

# ----------------------------------------------------------------------------
# Registro de series
#   agg        : como colapsar a un valor diario del sistema
#                'sum'  -> energia/cantidad (se suma sobre entidades y horas)
#                'mean' -> precio/porcentaje (se promedia)
#   temporalidad: 'ex_ante'     -> se conoce ANTES del dia D (usable directo)
#                 'estado'      -> se publica con ~1 dia de rezago (usable con lag)
#                 'ex_post'     -> se conoce DESPUES de formado el precio
#                 'estructural' -> cambia lento / catalogo
# ----------------------------------------------------------------------------
REGISTRO = {
    # ---- Oferta y merito (ex-ante, el nucleo predictivo) ----
    'costo_marginal_prog':    ('oferta',     'ex_ante',     'mean', 'COP/kWh'),
    'precio_oferta_desp':     ('oferta',     'ex_ante',     'mean', 'COP/kWh'),
    'max_precio_oferta':      ('oferta',     'ex_ante',     'mean', 'COP/kWh'),
    'gen_programada':         ('oferta',     'ex_ante',     'sum',  'kWh'),
    'disp_declarada':         ('oferta',     'ex_ante',     'sum',  'kWh'),
    'disp_real':              ('oferta',     'ex_ante',     'sum',  'kWh'),
    'disp_comercial':         ('oferta',     'ex_ante',     'sum',  'kWh'),
    'recurso_marginal':       ('oferta',     'ex_ante',     'sum',  'recurso-horas marginales'),

    # ---- Escasez (regulado, publicado con anticipacion) ----
    'precio_escasez':         ('escasez',    'ex_ante',     'mean', 'COP/kWh'),
    'precio_escasez_act':     ('escasez',    'ex_ante',     'mean', 'COP/kWh'),
    'precio_escasez_pon':     ('escasez',    'ex_ante',     'mean', 'COP/kWh'),
    'precio_escasez_inf':     ('escasez',    'ex_ante',     'mean', 'COP/kWh'),
    'precio_marg_escasez':    ('escasez',    'ex_ante',     'mean', 'COP/kWh'),
    'enficc':                 ('escasez',    'ex_ante',     'sum',  'kWh'),
    'precio_cargo_conf':      ('escasez',    'ex_ante',     'mean', 'COP/kWh'),

    # ---- Hidrologia (estado del sistema, usar rezagada) ----
    'volumen_util_pct':       ('hidrologia', 'estado',      'mean', 'fraccion'),
    'aportes_pct_sistema':    ('hidrologia', 'estado',      'mean', 'fraccion'),
    'aportes_media_hist':     ('hidrologia', 'estado',      'sum',  'kWh'),
    'aportes_por_rio':        ('hidrologia', 'estado',      'sum',  'kWh'),
    'aportes_pct_rio':        ('hidrologia', 'estado',      'mean', 'fraccion'),
    'volumen_por_embalse':    ('hidrologia', 'estado',      'sum',  'kWh'),
    'capacidad_por_embalse':  ('hidrologia', 'estado',      'sum',  'kWh'),
    'volumen_util_pct_emb':   ('hidrologia', 'estado',      'mean', 'fraccion'),
    'vertimientos':           ('hidrologia', 'estado',      'sum',  'kWh'),

    # ---- Demanda ----
    'demanda_regulada':       ('demanda',    'estado',      'sum',  'kWh'),
    'demanda_no_regulada':    ('demanda',    'estado',      'sum',  'kWh'),
    'demanda_por_or':         ('demanda',    'estado',      'sum',  'kWh'),
    'demanda_no_atendida':    ('demanda',    'ex_post',     'sum',  'kWh'),
    'dem_no_atendida_noprog': ('demanda',    'ex_post',     'sum',  'kWh'),
    'demanda_upme_alto':      ('demanda',    'ex_ante',     'sum',  'kWh/mes'),
    'demanda_upme_medio':     ('demanda',    'ex_ante',     'sum',  'kWh/mes'),
    'demanda_upme_bajo':      ('demanda',    'ex_ante',     'sum',  'kWh/mes'),

    # ---- Generacion realizada (ex-post) ----
    'gen_por_recurso':        ('generacion', 'ex_post',     'sum',  'kWh'),
    'gen_fuera_merito':       ('generacion', 'ex_post',     'sum',  'kWh'),
    'gen_seguridad':          ('generacion', 'ex_post',     'sum',  'kWh'),
    'consumo_combustible':    ('generacion', 'ex_post',     'sum',  'MBTU'),
    'emisiones_co2_sistema':  ('generacion', 'ex_post',     'sum',  'tCO2'),

    # ---- Economica / contratos ----
    'precio_prom_contrato':   ('economica',  'estado',      'mean', 'COP/kWh'),
    'precio_cont_no_regu':    ('economica',  'estado',      'mean', 'COP/kWh'),
    'compras_contrato':       ('economica',  'estado',      'sum',  'kWh'),
    'cee':                    ('economica',  'ex_ante',     'mean', 'COP/kWh'),
    'cere':                   ('economica',  'ex_ante',     'mean', 'COP/kWh'),
    'mc':                     ('economica',  'ex_ante',     'mean', 'COP/kWh'),

    # ---- Contexto / red ----
    'restricciones':          ('contexto',   'ex_post',     'sum',  'COP'),
    'restricciones_sin_aliv': ('contexto',   'ex_post',     'sum',  'COP'),
    'perdidas_energia':       ('contexto',   'ex_post',     'sum',  'kWh'),
    'importaciones':          ('contexto',   'ex_post',     'sum',  'kWh'),
    'exportaciones':          ('contexto',   'ex_post',     'sum',  'kWh'),

    # ---- Clima (solo desde 2021) ----
    'irradiacion_global':     ('clima',      'estado',      'mean', 'W/m2'),
    'irradiacion_panel':      ('clima',      'estado',      'mean', 'W/m2'),
    'temp_ambiente_solar':    ('clima',      'estado',      'mean', 'C'),
    'temp_panel':             ('clima',      'estado',      'mean', 'C'),

    # ---- Estructural ----
    'capacidad_efectiva':     ('estructura', 'estructural', 'sum',  'kW'),
}

# Catalogos que no son series temporales: se excluyen del analisis
EXCLUIR = {'catalogo_metricas', 'listado_rios', 'listado_embalses'}

COLOR_TEMP = {
    'ex_ante':     '#2a9d8f',   # verde - usable directo
    'estado':      '#e9c46a',   # ambar - usable con rezago
    'ex_post':     '#e76f51',   # rojo  - no usable sin cuidado
    'estructural': '#8d99ae',   # gris  - cambia lento
}

RE_HORA = re.compile(r'values?_hour\d+$', re.I)
COLS_ENTIDAD = ('Values_code', 'Values_Name', 'Name', 'Code')


# ----------------------------------------------------------------------------
# Carga y normalizacion
# ----------------------------------------------------------------------------
def _a_numerico(s):
    """La API entrega los valores como texto; se fuerzan a numerico."""
    return pd.to_numeric(s, errors='coerce')


def cargar_serie_diaria(ruta, agg='sum', batch=150_000):
    """Colapsa cualquiera de los dos formatos de la API a una serie diaria.

    Se lee por lotes para que los archivos grandes (gen_por_recurso, 111 MB;
    disp_comercial, 119 MB) no tengan que caber completos en memoria.

    Devuelve (serie_diaria, n_entidades, formato).
    """
    pf = pq.ParquetFile(ruta)
    cols = list(pf.schema_arrow.names)
    cols_hora = [c for c in cols if RE_HORA.match(c)]
    col_ent = next((c for c in COLS_ENTIDAD if c in cols), None)

    if cols_hora:
        leer = ['Date'] + cols_hora + ([col_ent] if col_ent else [])
    else:
        leer = ['Date', 'Value'] + ([col_ent] if col_ent else [])

    # Acumuladores por fecha: suma y conteo, para poder promediar al final
    suma, cuenta, entidades = {}, {}, set()

    for lote in pf.iter_batches(batch_size=batch, columns=leer):
        df = lote.to_pandas()
        fechas = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()

        if col_ent is not None:
            entidades.update(df[col_ent].dropna().unique().tolist())

        if cols_hora:
            vals = df[cols_hora].apply(_a_numerico)
            # Primero se colapsan las 24 horas de cada fila
            por_fila = vals.sum(axis=1) if agg == 'sum' else vals.mean(axis=1)
            valido = vals.notna().any(axis=1)
        else:
            por_fila = _a_numerico(df['Value'])
            valido = por_fila.notna()

        tmp = pd.DataFrame({'f': fechas.values, 'v': por_fila.values})[valido.values]
        g = tmp.groupby('f')['v'].agg(['sum', 'count'])
        for f, fila in g.iterrows():
            suma[f] = suma.get(f, 0.0) + fila['sum']
            cuenta[f] = cuenta.get(f, 0) + fila['count']

    if not suma:
        return pd.Series(dtype=float), 0, 'vacio'

    s = pd.Series(suma).sort_index()
    if agg == 'mean':
        s = s / pd.Series(cuenta).sort_index()

    formato = 'ancho_horario' if cols_hora else 'largo'
    n_ent = len(entidades) if col_ent else 1
    return s, n_ent, formato


def inferir_frecuencia(idx):
    """Frecuencia dominante a partir del salto tipico entre observaciones."""
    if len(idx) < 3:
        return 'indeterminada'
    d = pd.Series(idx).diff().dt.days.dropna()
    if d.empty:
        return 'indeterminada'
    med = d.median()
    if med <= 1.5:
        return 'diaria'
    if med <= 10:
        return 'semanal'
    if med <= 45:
        return 'mensual'
    return 'irregular'


# ----------------------------------------------------------------------------
# Construccion del inventario
# ----------------------------------------------------------------------------
def construir_inventario():
    calendario = pd.date_range(FECHA_INI, FECHA_FIN, freq='D')
    filas, series = [], {}

    archivos = sorted(DIR_CACHE.glob('*.parquet'))
    print(f'Leyendo {len(archivos)} archivos de {DIR_CACHE}\n')

    for ruta in archivos:
        nombre = ruta.stem
        if nombre in EXCLUIR:
            continue

        grupo, temporalidad, agg, unidad = REGISTRO.get(
            nombre, ('sin_clasificar', 'estructural', 'sum', '?'))

        try:
            s, n_ent, formato = cargar_serie_diaria(ruta, agg=agg)
        except Exception as e:
            print(f'  [ERROR] {nombre:<24} {str(e)[:70]}')
            continue

        if s.empty:
            print(f'  [VACIO] {nombre}')
            continue

        s = s[~s.index.duplicated()]
        series[nombre] = s

        freq = inferir_frecuencia(s.index)
        # La cobertura solo tiene sentido contra el calendario esperado
        if freq == 'diaria':
            esperados = len(calendario)
        elif freq == 'mensual':
            esperados = len(pd.date_range(FECHA_INI, FECHA_FIN, freq='MS'))
        else:
            esperados = len(s)
        cobertura = 100 * len(s) / max(esperados, 1)

        filas.append({
            'serie': nombre,
            'grupo': grupo,
            'temporalidad': temporalidad,
            'unidad': unidad,
            'formato': formato,
            'frecuencia': freq,
            'n_entidades': n_ent,
            'n_obs': len(s),
            'inicio': s.index.min().date(),
            'fin': s.index.max().date(),
            'cobertura_%': round(cobertura, 1),
            'media': s.mean(),
            'std': s.std(),
            'min': s.min(),
            'max': s.max(),
            'ceros_%': round(100 * (s == 0).mean(), 1),
            'agregacion': agg,
            'mb': round(ruta.stat().st_size / 1e6, 1),
        })
        print(f'  [OK] {nombre:<24} {len(s):>6,} obs  {freq:<10} '
              f'{s.index.min().date()} -> {s.index.max().date()}')

    orden_temp = {'ex_ante': 0, 'estado': 1, 'ex_post': 2, 'estructural': 3}
    inv = pd.DataFrame(filas)
    inv['_o'] = inv.temporalidad.map(orden_temp)
    inv = inv.sort_values(['_o', 'grupo', 'serie']).drop(columns='_o')
    return inv, series


# ----------------------------------------------------------------------------
# Graficos
# ----------------------------------------------------------------------------
def grafico_cobertura(inv, series):
    """Mapa de que serie existe en que fecha. Responde 'desde cuando tengo esto'."""
    calendario = pd.date_range(FECHA_INI, FECHA_FIN, freq='D')
    orden = inv.serie.tolist()

    fig, ax = plt.subplots(figsize=(16, 0.32 * len(orden) + 3))
    for i, nombre in enumerate(orden):
        s = series[nombre]
        if inferir_frecuencia(s.index) == 'mensual':
            # Una observacion mensual "cubre" todo su mes
            presente = pd.Series(1.0, index=s.index).reindex(
                calendario, method='ffill', limit=31).fillna(0)
        else:
            presente = pd.Series(1.0, index=s.index).reindex(calendario).fillna(0)
        color = COLOR_TEMP[inv.iloc[i].temporalidad]
        ax.fill_between(calendario, i - 0.4, i + 0.4,
                        where=presente.values > 0, color=color, lw=0)

    ax.set_yticks(range(len(orden)))
    ax.set_yticklabels(orden, fontsize=8)
    ax.set_ylim(-0.6, len(orden) - 0.4)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.grid(axis='x', alpha=.3, ls=':')
    ax.set_title('Cobertura temporal de las series descargadas\n'
                 'verde = ex-ante (usable directo)   ambar = estado (usar rezagada)   '
                 'rojo = ex-post (no usable sin cuidado)   gris = estructural',
                 fontsize=11, loc='left')
    fig.tight_layout()
    fig.savefig(DIR_OUT / 'cobertura_series.png', dpi=130)
    plt.close(fig)
    print('  -> cobertura_series.png')


def graficos_por_grupo(inv, series):
    """Small multiples: cada serie en su escala, agrupadas por tema."""
    for grupo, sub in inv.groupby('grupo'):
        nombres = sub.serie.tolist()
        n = len(nombres)
        ncol = 2
        nfil = int(np.ceil(n / ncol))
        fig, axes = plt.subplots(nfil, ncol, figsize=(15, 2.4 * nfil), squeeze=False)

        for k, nombre in enumerate(nombres):
            ax = axes[k // ncol][k % ncol]
            s = series[nombre]
            meta = sub[sub.serie == nombre].iloc[0]
            ax.plot(s.index, s.values, lw=.6, color=COLOR_TEMP[meta.temporalidad])
            if meta.frecuencia == 'diaria' and len(s) > 60:
                ax.plot(s.index, s.rolling(30).mean(), lw=1.4, color='black', alpha=.7)
            ax.set_title(f'{nombre}  [{meta.temporalidad}]  '
                         f'{meta.unidad} | {meta.n_entidades} ent | '
                         f'cob {meta["cobertura_%"]}%', fontsize=9, loc='left')
            ax.tick_params(labelsize=7)
            ax.grid(alpha=.25, ls=':')
            ax.set_xlim(pd.Timestamp(FECHA_INI), pd.Timestamp(FECHA_FIN))

        for k in range(n, nfil * ncol):
            axes[k // ncol][k % ncol].axis('off')

        fig.suptitle(f'Grupo: {grupo}   (linea negra = media movil 30d)',
                     fontsize=12, y=1.0)
        fig.tight_layout()
        fig.savefig(DIR_OUT / f'series_{grupo}.png', dpi=120)
        plt.close(fig)
        print(f'  -> series_{grupo}.png  ({n} series)')


def grafico_comparacion(inv, series):
    """Series diarias en z-score, para comparar dinamica y no nivel."""
    diarias = inv[inv.frecuencia == 'diaria']
    for grupo, sub in diarias.groupby('grupo'):
        if len(sub) < 2:
            continue
        fig, ax = plt.subplots(figsize=(15, 5))
        for nombre in sub.serie:
            s = series[nombre].resample('W').mean()
            if s.std() == 0 or not np.isfinite(s.std()):
                continue
            z = (s - s.mean()) / s.std()
            ax.plot(z.index, z.values, lw=1.1, alpha=.85, label=nombre)
        ax.axhline(0, color='black', lw=.8)
        ax.set_title(f'{grupo} - series normalizadas (z-score, promedio semanal)',
                     loc='left')
        ax.legend(fontsize=8, ncol=3)
        ax.grid(alpha=.25, ls=':')
        fig.tight_layout()
        fig.savefig(DIR_OUT / f'comparacion_{grupo}.png', dpi=120)
        plt.close(fig)
        print(f'  -> comparacion_{grupo}.png')


# ----------------------------------------------------------------------------
def main():
    inv, series = construir_inventario()

    inv.to_csv(DIR_OUT / 'inventario_series.csv', index=False)
    pd.to_pickle(series, DIR_OUT / 'series_diarias.pkl')

    print(f'\n{len(inv)} series procesadas\n')
    print('=== Resumen por temporalidad ===')
    print(inv.groupby(['temporalidad', 'grupo']).size().to_string())

    print('\n=== Series con cobertura incompleta (<95%) ===')
    flojas = inv[inv['cobertura_%'] < 95][
        ['serie', 'temporalidad', 'inicio', 'fin', 'n_obs', 'cobertura_%']]
    print(flojas.to_string(index=False) if len(flojas) else '  ninguna')

    print('\nGenerando graficos...')
    grafico_cobertura(inv, series)
    graficos_por_grupo(inv, series)
    grafico_comparacion(inv, series)

    print(f'\nTodo en: {DIR_OUT}')


if __name__ == '__main__':
    main()
