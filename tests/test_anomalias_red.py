"""Protocolo anomalias_red_v1: plan de inyección, anomalía multiplicativa y etiquetas."""

import numpy as np
import pandas as pd
import pytest

from src.detect import anomalias_red as ar
from src.detect import multianual as m

ALTERABLES = [s for s in m.ESTACIONES if s not in ('HGM', 'XAL')]     # los 31 objetivos del V4


def _valores(inicio='2024-01-01', dias=30, valor=40.0):
    idx = pd.date_range(inicio, periods=24 * dias, freq='h')
    return pd.DataFrame(valor, index=idx, columns=m.ESTACIONES)


def _plan(est='CCA', inicio='2024-01-03', dias=2, signo=1):
    ini = pd.Timestamp(inicio)
    return pd.DataFrame([dict(corrida='t', episodio=1, estacion=est, inicio=ini,
                              fin=ini + pd.Timedelta(days=dias) - pd.Timedelta(hours=1),
                              dias_sorteados=dias, dias=dias, signo=signo, p=0.5)])


# ---------------------------------------------------------------- corridas y plan

def test_corridas_p_base_en_entrenamiento_y_sorteada_en_prueba():
    c = ar.corridas()
    assert len(c) == 11 and c.corrida.is_unique
    assert c.set_index('corrida').at['entrenamiento', 'p'] == ar.P_BASE
    p = c.loc[c.corrida != 'entrenamiento', 'p']
    assert p.between(*ar.P_RANGO).all() and p.nunique() == 10
    pd.testing.assert_frame_equal(c, ar.corridas())


def test_calendarios_de_entrenamiento_no_chocan_con_las_corridas():
    k = ar.calendarios_entrenamiento()
    assert len(k) == ar.CALENDARIOS_ENTRENAMIENTO == 20 and k.numero.tolist() == list(range(1, 21))
    assert k.corrida.tolist()[0] == 'entrenamiento_01' and not set(k.corrida) & set(ar.corridas().corrida)
    assert k.p.between(*ar.P_RANGO).all() and k.p.nunique() == 20
    pd.testing.assert_frame_equal(k.iloc[:10], ar.calendarios_entrenamiento(n=10))   # revisión 6
    assert (k.inicio == '2020-01-01').all() and (k.fin == '2022-12-31').all()
    pd.testing.assert_frame_equal(k, ar.calendarios_entrenamiento())
    original = ar.plan_de(ar.corridas().iloc[0], ALTERABLES)
    primero = ar.plan_de(k.iloc[0], ALTERABLES)
    assert not original[['estacion', 'inicio']].equals(primero[['estacion', 'inicio']])


def test_plan_reproducible_y_distinto_entre_corridas():
    a = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ALTERABLES, 'x', 1)
    b = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ALTERABLES, 'x', 1)
    c = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ALTERABLES, 'x', 2)
    pd.testing.assert_frame_equal(a, b)
    assert not a[['estacion', 'inicio']].equals(c[['estacion', 'inicio']])


def test_plan_de_entrenamiento_cubre_solo_el_ajuste_definitivo():
    tr = ar.plan_de(ar.corridas().iloc[0], ALTERABLES)
    assert (tr['corrida'] == 'entrenamiento').all() and (tr['p'] == ar.P_BASE).all()
    assert tr['inicio'].min() >= pd.Timestamp('2020-01-01')
    assert tr['fin'].max() <= pd.Timestamp('2022-12-31 23:00')


def test_dias_completos_sin_traslape_y_corte_al_final():
    plan = ar.plan_episodios('2024-01-01', '2024-12-31', 0.05, ALTERABLES, 'x', 1)
    ar.validar_plan(plan)
    assert plan['dias'].between(1, 7).all() and plan['dias_sorteados'].between(1, 7).all()
    assert plan['signo'].isin([1, -1]).all() and set(plan['estacion']) <= set(ALTERABLES)
    assert (plan['fin'] <= pd.Timestamp('2024-12-31 23:00')).all()
    cortados = plan[plan.dias < plan.dias_sorteados]
    assert (cortados['fin'] == pd.Timestamp('2024-12-31 23:00')).all()
    assert ((plan['fin'] - plan['inicio']) == pd.to_timedelta(plan['dias'], 'D') - pd.Timedelta(hours=1)).all()


def test_estaciones_independientes_entre_si():
    todas = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ALTERABLES, 'x', 1)
    solo = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ['CCA', 'PED'], 'x', 1)
    cols = ['estacion', 'inicio', 'fin', 'signo']
    esperado = todas[todas.estacion.isin(['CCA', 'PED'])][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(solo[cols], esperado)


def test_rechaza_estaciones_fuera_de_la_matriz():
    with pytest.raises(ValueError):
        ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ['COY'], 'x', 1)


def test_tasa_coincide_con_la_tabla_del_protocolo():
    """§6: con p = 0.15 %, unos 0.56 episodios por estación y año (simulación, sin modelo)."""
    plan = ar.plan_episodios('2030-01-01', '2129-12-31', ar.P_BASE, ALTERABLES, 'sim', 99)
    por_estacion_anio = len(plan) / (len(ALTERABLES) * 100)
    assert 0.50 < por_estacion_anio < 0.62
    assert 3.6 < plan['dias'].mean() < 4.4


def test_guardar_y_leer_plan(tmp_path):
    plan = ar.plan_episodios('2024-01-01', '2024-12-31', 0.01, ALTERABLES, 'prueba_2024_01', 1)
    path = ar.guardar_plan(plan, tmp_path)
    assert path.name == 'plan_prueba_2024_01.csv'
    pd.testing.assert_frame_equal(ar.leer_plan(path), plan, check_dtype=False)


# ---------------------------------------------------------------- anomalía

def test_signo_mas_multiplica_y_signo_menos_divide():
    v = _valores()
    rec, cam = ar.aplicar(v, _plan(signo=1), 1.0)
    t = pd.Timestamp('2024-01-03 12:00')
    assert rec.at[t, 'CCA'] == 80 and cam.at[t, 'CCA']
    rec, _ = ar.aplicar(v, _plan(signo=-1), 1.0)
    assert rec.at[t, 'CCA'] == 20
    rec, _ = ar.aplicar(v, _plan(signo=-1), 0.10)
    assert rec.at[t, 'CCA'] == 36                     # 40 / 1.1 = 36.36


def test_redondeo_a_enteros_con_mitades_hacia_arriba():
    v = _valores(valor=10.0)
    rec, cam = ar.aplicar(v, _plan(), 0.05)           # 10.5 → 11
    t = pd.Timestamp('2024-01-03 05:00')
    assert rec.at[t, 'CCA'] == 11 and cam.at[t, 'CCA']
    v[:] = 9.0
    rec, cam = ar.aplicar(v, _plan(), 0.05)           # 9.45 → 9: no cambia
    assert rec.at[t, 'CCA'] == 9 and not cam.at[t, 'CCA']
    assert np.allclose(rec.to_numpy(), np.round(rec.to_numpy()))


def test_fuera_del_episodio_y_otras_estaciones_no_cambian():
    v = _valores()
    rec, cam = ar.aplicar(v, _plan(), 0.5)
    dentro = (v.index >= '2024-01-03') & (v.index < '2024-01-05')
    assert cam.loc[dentro, 'CCA'].all() and cam['CCA'].sum() == 48
    assert not cam.drop(columns='CCA').any().any()
    pd.testing.assert_frame_equal(rec.loc[~dentro], v.loc[~dentro])


def test_horas_sin_dato_siguen_sin_dato():
    v = _valores()
    t = pd.Timestamp('2024-01-03 10:00')
    v.loc[t, 'CCA'] = np.nan
    rec, cam = ar.aplicar(v, _plan(), 1.0)
    assert np.isnan(rec.at[t, 'CCA']) and not cam.at[t, 'CCA']
    assert cam['CCA'].sum() == 47


def test_cero_sigue_en_cero_y_nunca_negativo():
    v = _valores(valor=0.0)
    for signo in (1, -1):
        rec, cam = ar.aplicar(v, _plan(signo=signo), 1.0)
        assert (rec >= 0).all().all() and not cam.any().any()


def test_mismo_plan_con_todos_los_delta():
    v = _valores(dias=60)
    rng = np.random.default_rng(0)
    v[:] = rng.integers(2, 150, v.shape).astype(float)
    plan = ar.plan_episodios('2024-01-01', '2024-02-29', 0.05, ALTERABLES, 'x', 1)
    dentro = ar.en_episodio(plan, v.index)
    for d in ar.DELTAS:
        _, cam = ar.aplicar(v, plan, d)
        assert not (cam & ~dentro).any().any()        # sólo cambian horas del plan
    _, cam100 = ar.aplicar(v, plan, 1.0)
    assert cam100.eq(dentro).all().all()              # con δ = 100 % cambia toda lectura ≥ 2 ppb


def test_rechaza_plan_con_estacion_ajena():
    with pytest.raises(ValueError):
        ar.aplicar(_valores()[['CCA', 'PED']], _plan(est='MER'), 0.5)


# ---------------------------------------------------------------- etiquetas y resumen

def test_etiqueta_de_red_es_alguna_estacion_cambiada():
    v = _valores()
    plan = pd.concat([_plan('CCA', '2024-01-03', 1), _plan('PED', '2024-01-03', 2)], ignore_index=True)
    plan['episodio'] = [1, 2]
    _, cam = ar.aplicar(v, plan, 0.5)
    y = ar.etiqueta_red(cam)
    assert y.name == 'anomalia_red' and y.sum() == 48
    assert y.loc['2024-01-04'].all() and not y.loc['2024-01-05'].any()


def test_resumen_episodios_evaluable_no_depende_de_delta():
    v = _valores()
    v.loc['2024-01-10':'2024-01-12', 'PED'] = np.nan
    plan = pd.concat([_plan('CCA', '2024-01-03', 2), _plan('PED', '2024-01-10', 3)], ignore_index=True)
    plan['episodio'] = [1, 2]
    r = ar.resumen_episodios(v, plan).set_index('estacion')
    assert r.at['CCA', 'horas_con_dato'] == 48 and r.at['CCA', 'evaluable']
    assert r.at['PED', 'horas_con_dato'] == 0 and not r.at['PED', 'evaluable']
    assert r.at['CCA', 'horas_cambiadas_d5'] == 48 and r.at['PED', 'horas_cambiadas_d100'] == 0


# ---------------------------------------------------------------- matriz de red

def test_matriz_red_ordenada_columnas_y_etiquetas():
    v = _valores(dias=5)
    v.loc['2024-01-02 06:00', 'PED'] = np.nan
    cols = ar.columnas_entrada(['XAL'])
    _, cam = ar.aplicar(v, _plan('CCA', '2024-01-03', 1), 1.0)
    x = ar.matriz_red(v, cols, cam)
    assert len(cols) == 32 and 'XAL' not in cols
    assert x.index.is_monotonic_increasing and len(x) == 5 * 24
    assert list(x.columns[:32]) == [f'{s}_valor' for s in cols]
    assert list(x.columns[32:64]) == [f'{s}_mascara' for s in cols]
    assert list(x.columns[64:]) == ['hora_sin', 'hora_cos', 'anomalia_red', 'estaciones_alteradas']
    assert x.at[pd.Timestamp('2024-01-02 06:00'), 'PED_mascara'] == 0
    assert x['anomalia_red'].sum() == 24 and x.loc['2024-01-03', 'anomalia_red'].all()
    assert (x.loc['2024-01-03', 'estaciones_alteradas'] == 'CCA').all()
    assert (x.loc['2024-01-04', 'estaciones_alteradas'] == '').all()


def test_matriz_red_limpia_sin_etiquetas():
    x = ar.matriz_red(_valores(dias=2), ar.columnas_entrada(['XAL']))
    assert x['anomalia_red'].eq(0).all() and x['estaciones_alteradas'].eq('').all()


def test_matriz_red_rechaza_horas_desordenadas_o_faltantes():
    v = _valores(dias=2)
    with pytest.raises(ValueError):
        ar.matriz_red(v.drop(v.index[5]), ar.columnas_entrada(['XAL']))
    with pytest.raises(ValueError):
        ar.matriz_red(v.iloc[::-1], ar.columnas_entrada(['XAL']))
