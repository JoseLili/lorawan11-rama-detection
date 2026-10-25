"""Protocolo anomalias_red_v1, revisión 11: etiquetas, horas válidas y formas de juntar el día."""

import numpy as np
import pandas as pd
import pytest

from src.detect import estacion_dia as ed


def _horas(dias=2, inicio='2022-01-01'):
    return pd.date_range(inicio, periods=24 * dias, freq='h')


def _plan(filas):
    return pd.DataFrame([dict(estacion=s, inicio=pd.Timestamp(i), fin=pd.Timestamp(f) + pd.Timedelta(hours=23))
                         for s, i, f in filas])


def test_promedio_con_signo_contra_peor_hora():
    idx = _horas(1)
    ruido = np.where(np.arange(24) % 2 == 0, 1.0, -1.0)
    ruido[5] = 3.0                                          # una hora rara (antes -1), sin corrimiento
    v = pd.DataFrame({'A': ruido, 'B': np.full(24, -0.5)}, index=idx)   # B: corrido todo el día
    peor, prom = ed.juntar_dia(v, 'peor_hora'), ed.juntar_dia(v, 'promedio_dia')
    assert peor.at[idx[0], 'A'] == 3.0 and peor.at[idx[0], 'B'] == 0.5
    assert prom.at[idx[0], 'A'] == pytest.approx(4 / 24) and prom.at[idx[0], 'B'] == 0.5


def test_excluye_estacion_dias_con_menos_de_12_horas():
    idx = _horas(2)
    v = pd.DataFrame({'A': 1.0, 'B': 1.0}, index=idx)
    v.iloc[:13, 0] = np.nan                                 # A, día 1: 11 horas válidas
    v.iloc[:12, 1] = np.nan                                 # B, día 1: 12 horas válidas
    for agregacion in ed.AGREGACIONES:
        s = ed.juntar_dia(v, agregacion)
        assert np.isnan(s.iat[0, 0]) and s.iat[0, 1] == 1.0 and s.iloc[1].eq(1.0).all()
    assert ed.horas_validas(v).iloc[0].tolist() == [11, 12]


def test_exige_dias_completos_y_agregacion_conocida():
    v = pd.DataFrame({'A': 1.0}, index=_horas(1))
    with pytest.raises(ValueError):
        ed.juntar_dia(v.iloc[1:], 'peor_hora')              # empieza a la 01 h
    with pytest.raises(ValueError):
        ed.juntar_dia(v.drop(v.index[5]), 'peor_hora')      # falta una hora
    with pytest.raises(ValueError):
        ed.juntar_dia(v, 'mediana')


def test_etiquetas_de_un_episodio_que_cruza_el_año():
    dias = pd.date_range('2022-01-01', periods=5, freq='D')
    y = ed.etiquetas(_plan([('A', '2021-12-30', '2022-01-02')]), dias, ['A', 'B'])
    assert y['A'].tolist() == [True, True, False, False, False] and not y['B'].any()
    with pytest.raises(ValueError):
        ed.etiquetas(_plan([('C', '2022-01-01', '2022-01-01')]), dias, ['A', 'B'])


def test_grupos_de_falsa_alarma_en_orden():
    dias = pd.date_range('2022-01-01', periods=40, freq='D')
    plan = _plan([('A', '2022-01-01', '2022-01-02'),       # A atacada los días 1 y 2
                  ('B', '2022-01-05', '2022-01-05')])       # B, vecina de A, atacada el día 5
    vecinas = {'A': ['B', 'HGM'], 'B': ['A', 'HGM']}
    g = ed.grupos_falsa_alarma(plan, dias, ['A', 'B'], vecinas)
    a = g['A']
    assert a.iat[0] == '' and a.iat[1] == ''                # atacada: no es normal
    assert a.iat[2] == 'tras_ataque_propio'                 # día siguiente al fin propio
    assert a.iat[4] == 'contagio'                           # también tras ataque propio: gana contagio
    assert a.iat[15] == 'tras_ataque_propio' and a.iat[16] == 'resto'   # 14 días después del fin
    assert g['B'].iat[0] == 'contagio' and g['B'].iat[4] == ''
    assert set(g.to_numpy().ravel()) <= {'', *ed.GRUPOS_FA}


def test_dominancia_apaga_a_la_vecina_menor():
    dias = pd.date_range('2022-01-01', periods=3, freq='D')
    s = pd.DataFrame({'A': [3.0, 1.0, np.nan], 'B': [1.0, 1.0, 2.0], 'C': [5.0, 0.5, 1.0]}, index=dias)
    vecinas = {'A': ['B', 'HGM'], 'B': ['A'], 'C': ['B']}   # asimétricas; HGM no se evalúa
    d = ed.dominancia(s, vecinas)
    assert d['A'].tolist()[:2] == [3.0, 1.0] and np.isnan(d.at[dias[2], 'A'])   # sin puntaje sigue NaN
    assert d['B'].tolist() == [0.0, 1.0, 2.0]               # día 1: A es mayor; día 2: empate; día 3: A sin dato
    assert d['C'].tolist() == [5.0, 0.0, 0.0]               # C sólo se compara con B
    assert ed.dominancia(s, {'A': ['HGM'], 'B': ['A'], 'C': ['B']})['A'].iloc[:2].tolist() == [3.0, 1.0]


def test_etiquetas_por_hora_desde_estaciones_alteradas():
    idx = _horas(1)
    m = pd.DataFrame({'estaciones_alteradas': [''] * 22 + ['A', 'A;CC']}, index=idx)
    y = ed.etiquetas_por_hora(m, ['A', 'C', 'CC'])
    assert y['A'].sum() == 2 and not y['C'].any() and y['CC'].tolist()[-1] and y['CC'].sum() == 1
