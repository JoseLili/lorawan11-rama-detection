"""Entrenamiento V4 multianual: mismas ventanas que V4, épocas y no sobrescritura."""

import numpy as np
import pandas as pd
import pytest

from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect.windows import construir_ventanas


def _valores():
    rej = pd.date_range(m.INICIO, m.FIN, freq='h')
    rng = np.random.default_rng(1)
    v = pd.DataFrame(rng.uniform(0, 120, (len(rej), len(m.ESTACIONES))), index=rej, columns=m.ESTACIONES)
    v[rng.random(v.shape) < 0.2] = np.nan
    v.loc[:'2022-12-31 23:00', 'XAL'] = np.nan
    return v


@pytest.fixture(scope='module')
def valores():
    return _valores()


def test_tensores_identicos_a_construir_ventanas_v4(valores):
    obj = 'CCA'
    perfil = m.perfil_causal(valores[obj])
    mu, sigma = m.normalizacion(valores, m.AJUSTE_DEFINITIVO)
    trozo = valores.loc['2022-12-20':'2023-01-10']
    t = em.tensores(valores, valores, obj, mu, sigma, perfil, ('calibracion',))
    X4, y4, ts4, B4, _, _ = construir_ventanas(
        trozo, obj, ventana=24, mu=mu.drop(obj), sigma=sigma.drop(obj),
        perfil=perfil['base'].loc[trozo.index], predecir_desviacion=True)
    comunes = pd.DatetimeIndex(ts4).intersection(t['ts'])
    assert len(comunes) > 100
    i_nuevo = t['ts'].get_indexer(comunes)
    i_v4 = pd.DatetimeIndex(ts4).get_indexer(comunes)
    np.testing.assert_array_equal(t['X'][i_nuevo], X4[i_v4])
    np.testing.assert_allclose(t['y'][i_nuevo], y4[i_v4], rtol=1e-6)
    assert t['X'].shape[1:] == (24, 66)


def test_tensores_solo_objetivos_de_la_etapa(valores):
    perfil = m.perfil_causal(valores['PED'])
    mu, sigma = m.normalizacion(valores, ('ajuste_inicial',))
    t = em.tensores(valores, valores, 'PED', mu, sigma, perfil, ('validacion',))
    assert t['ts'].min() >= pd.Timestamp('2022-01-01') and t['ts'].max() <= pd.Timestamp('2022-12-31 23:00')
    assert np.isfinite(t['y']).all() and np.isfinite(t['base']).all()


def test_seleccionar_epoca_primera_con_minimo():
    h = pd.DataFrame({'val_loss': [5.0, 3.0, 2.0, 2.0, 4.0]}, index=pd.RangeIndex(1, 6))
    assert em.seleccionar_epoca(h) == 3


def test_entrenamiento_completo_y_no_sobrescribe(valores, tmp_path):
    pytest.importorskip('tensorflow')
    ina_i = m.canales_inactivos(valores, ('ajuste_inicial',))
    ina_d = m.canales_inactivos(valores, m.AJUSTE_DEFINITIVO)
    mu_i, sg_i = m.normalizacion(valores, ('ajuste_inicial',), ina_i)
    mu_d, sg_d = m.normalizacion(valores, m.AJUSTE_DEFINITIVO, ina_d)
    ctx = dict(valores=valores,
               inicial=dict(inactivos=ina_i, mu=mu_i, sigma=sg_i, entradas=m.entradas_modelo(valores, ina_i)),
               definitiva=dict(inactivos=ina_d, mu=mu_d, sigma=sg_d, entradas=m.entradas_modelo(valores, ina_d)))
    cfg = em.entrenar_objetivo(ctx, 'CCA', tmp_path / 'CCA', max_epocas=2, unidades=4)
    assert 1 <= cfg['epoca_E'] <= 2
    assert cfg['canales_inactivos'] == ['XAL']
    r = em.cargar_objetivo(tmp_path / 'CCA')
    assert len(r['definitiva']) == cfg['epoca_E']
    assert set(r['prueba']) == {2024, 2025, 2026}
    assert r['umbral'] == pytest.approx(em.umbral_p95(r['calibracion']))
    with pytest.raises(FileExistsError):
        em.entrenar_objetivo(ctx, 'CCA', tmp_path / 'CCA', max_epocas=2, unidades=4)
    # Segunda corrida independiente: idéntica
    em.entrenar_objetivo(ctx, 'CCA', tmp_path / 'CCA_b', max_epocas=2, unidades=4)
    assert em.comparar_corridas(tmp_path / 'CCA', tmp_path / 'CCA_b')['identico'].all()


def test_bitacora_solo_agrega(tmp_path):
    b = tmp_path / 'bitacora.csv'
    em.registrar(b, 'entrenar', 'CCA', 'entrenado', flags=dict(ENTRENAR=True, OBJETIVOS=['CCA']),
                 config=dict(epoca_E=2, umbral_p95_ppb=24.1, canales_inactivos=['XAL']))
    em.registrar(b, 'entrenar', 'PED', 'saltado_ya_existe', flags=dict(ENTRENAR=True, OBJETIVOS=['PED', 'TLI']))
    bit = em.leer_bitacora(b)
    assert list(bit.columns) == em.COLUMNAS_BITACORA
    assert bit.objetivo.tolist() == ['CCA', 'PED']
    assert bit.OBJETIVOS.tolist() == ['CCA', 'PED TLI']
    assert bit.at[0, 'epoca_E'] == '2' and bit.at[0, 'canales_inactivos'] == 'XAL'
