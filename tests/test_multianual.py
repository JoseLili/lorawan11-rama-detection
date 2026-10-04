"""Protocolo temporal común V4 multianual: etapas, causalidad y canal inactivo."""

import numpy as np
import pandas as pd
import pytest

from src.detect import multianual as m


def test_etapas_por_fecha_del_objetivo_sin_solapes_ni_huecos():
    rej = pd.date_range(m.INICIO, m.FIN, freq='h')
    etapa = m.etapa_de(rej)
    assert etapa.notna().all()
    assert etapa[pd.Timestamp('2021-12-31 23:00')] == 'ajuste_inicial'
    assert etapa[pd.Timestamp('2022-01-01 00:00')] == 'validacion'
    assert etapa[pd.Timestamp('2023-12-31 23:00')] == 'calibracion'
    assert etapa[pd.Timestamp('2024-01-01 00:00')] == 'prueba_2024'
    assert etapa[pd.Timestamp('2026-07-31 23:00')] == 'prueba_2026_parcial'
    assert pd.isna(m.etapa_de([pd.Timestamp('2026-08-01')]).iat[0])
    # 2024 bisiesto completo, 2026 hasta julio
    assert (etapa == 'prueba_2024').sum() == 8784
    assert (etapa == 'prueba_2026_parcial').sum() == 5088


def _serie(n_dias=30, inicio='2020-01-01'):
    idx = pd.date_range(inicio, periods=24 * n_dias, freq='h')
    rng = np.random.default_rng(0)
    return pd.Series(rng.uniform(0, 100, len(idx)), index=idx)


def test_perfil_no_usa_el_presente_ni_el_futuro():
    s = _serie()
    t = s.index[24 * 20 + 15]
    base = m.perfil_causal(s).at[t, 'base']
    alterada = s.copy()
    alterada[alterada.index >= t] += 1000
    assert m.perfil_causal(alterada).at[t, 'base'] == pytest.approx(base)
    # 14 días naturales anteriores a la misma hora
    previas = s[(s.index.hour == 15) & (s.index < t)].iloc[-14:]
    assert base == pytest.approx(previas.mean())


def test_perfil_14_dias_naturales_no_14_observaciones():
    s = _serie()
    t = s.index[24 * 20 + 10]
    s[(s.index.hour == 10) & (s.index < t)] = np.nan
    s[s.index == t - pd.Timedelta(days=3)] = 50.0      # única lectura en la ventana
    s[s.index == t - pd.Timedelta(days=15)] = 999.0    # fuera de los 14 días
    p = m.perfil_causal(s)
    assert p.at[t, 'origen_base'] == '14d'
    assert p.at[t, 'base'] == pytest.approx(50.0)


def test_respaldo_en_orden_y_sin_historia():
    s = _serie(n_dias=40)
    t = s.index[24 * 30 + 8]
    hora8 = (s.index.hour == 8) & (s.index < t)
    s[hora8 & (s.index >= t - pd.Timedelta(days=14))] = np.nan
    p = m.perfil_causal(s)
    assert p.at[t, 'origen_base'] == 'historico_hora'
    assert p.at[t, 'base'] == pytest.approx(s[hora8].mean())

    s[hora8] = np.nan
    p = m.perfil_causal(s)
    assert p.at[t, 'origen_base'] == 'historico_global'
    assert p.at[t, 'base'] == pytest.approx(s[s.index < t].mean())

    p0 = m.perfil_causal(_serie())
    assert p0['origen_base'].iat[0] == 'sin_historia' and np.isnan(p0['base'].iat[0])


def test_perfil_exige_rejilla_continua():
    s = _serie().drop(pd.Timestamp('2020-01-05 03:00'))
    with pytest.raises(ValueError):
        m.perfil_causal(s)


def _long_sintetico():
    rej = pd.date_range('2020-01-01', '2023-12-31 23:00', freq='h')
    filas = []
    for s in m.ESTACIONES:
        v = np.full(len(rej), 40.0)
        if s == 'XAL':
            v[rej < pd.Timestamp('2023-01-01')] = np.nan
        filas.append(pd.DataFrame({'timestamp': rej, 'station': s, 'value': v}))
    long = pd.concat(filas, ignore_index=True)
    long['origen'] = np.where(long.value.notna(), 'observado', 'centinela_-99')
    return long


def test_matriz_fija_33_columnas_y_renglon_ausente():
    long = _long_sintetico()
    hueco = pd.Timestamp('2021-03-04 05:00')
    long = long[long.timestamp != hueco]
    valores, origen = m.matriz_fija(long)
    assert list(valores.columns) == m.ESTACIONES
    assert valores.index.equals(pd.date_range(m.INICIO, m.FIN, freq='h'))
    assert valores.loc[hueco].isna().all()
    assert (origen.loc[hueco] == 'renglon_ausente').all()
    assert (origen.loc['2020-06-01', 'XAL'] == 'centinela_-99').all()


def test_canal_inactivo_se_oculta_en_todas_las_etapas():
    valores, _ = m.matriz_fija(_long_sintetico())
    inactivos = m.canales_inactivos(valores)
    assert inactivos == ['XAL']
    mu, sigma = m.normalizacion(valores, m.AJUSTE_DEFINITIVO, inactivos)
    assert (mu['XAL'], sigma['XAL']) == (0.0, 1.0)
    entradas = m.entradas_modelo(valores, inactivos)
    assert entradas['XAL'].isna().all()
    assert valores.loc['2023-06-01', 'XAL'].notna().all()      # sigue para el máximo de red
    perfil = m.perfil_causal(valores['CCA'])
    ej = m.ventana_ejemplo(entradas, 'CCA', '2023-06-01 15:00', mu, sigma, perfil, valores)
    assert ej['X'].shape == (24, 66)
    assert (ej['X']['XAL_mascara'] == 0).all() and (ej['X']['XAL_valor'] == 0).all()
    assert ej['X'].index.max() < ej['t'] and ej['X'].index.min() == ej['t'] - pd.Timedelta(hours=24)
    assert 'CCA_valor' not in ej['X'].columns


def test_clasificacion_por_minimos():
    cob = pd.DataFrame([
        dict(objetivo='A', etapa=e, ejemplos=5000, meses_con_ejemplos=12) for e in m.OBLIGATORIAS
    ] + [
        dict(objetivo='B', etapa='ajuste_inicial', ejemplos=5000, meses_con_ejemplos=24),
        dict(objetivo='B', etapa='validacion', ejemplos=0, meses_con_ejemplos=0),
        dict(objetivo='B', etapa='calibracion', ejemplos=5000, meses_con_ejemplos=12),
        dict(objetivo='C', etapa='ajuste_inicial', ejemplos=5000, meses_con_ejemplos=24),
        dict(objetivo='C', etapa='validacion', ejemplos=5000, meses_con_ejemplos=12),
        dict(objetivo='C', etapa='calibracion', ejemplos=1500, meses_con_ejemplos=3),
    ])
    cob['cumple_minimo'] = (cob.ejemplos >= m.MIN_HORAS) & (cob.meses_con_ejemplos >= m.MIN_MESES)
    c = m.clasificar(cob).set_index('objetivo')['clasificacion']
    assert c.to_dict() == {'A': 'principal', 'B': 'fuera', 'C': 'baja_representatividad'}
