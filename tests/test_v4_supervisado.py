"""Protocolo anomalias_red_v1, revisión 18: entradas del V4 supervisado (V4S) y su muestra."""

import numpy as np
import pandas as pd
import pytest

from src.detect import entrenamiento_multianual as em
from src.detect import multianual as m
from src.detect import v4_supervisado as vs


@pytest.fixture(scope='module')
def valores():
    rej = pd.date_range('2021-11-01', '2022-02-28 23:00', freq='h')
    rng = np.random.default_rng(3)
    v = pd.DataFrame(rng.uniform(0, 120, (len(rej), len(m.ESTACIONES))), index=rej, columns=m.ESTACIONES)
    v[rng.random(v.shape) < 0.2] = np.nan
    v['XAL'] = np.nan
    return v


def _tensores(v, obj='PED'):
    perfil = m.perfil_causal(v[obj])
    mu, sigma = m.normalizacion(v, ('validacion',), ['XAL'])
    entradas = m.entradas_modelo(v, ['XAL'])
    return vs.tensores(entradas, v, obj, mu, sigma, perfil, ('validacion',)), perfil, mu, sigma, entradas


def test_las_66_del_v4_con_t_y_las_2_de_la_propia_estacion(valores):
    t, perfil, mu, sigma, entradas = _tensores(valores)
    v4 = em.tensores(entradas, valores, 'PED', mu, sigma, perfil, ('validacion',), incluir_t=True)
    assert t['X'].shape == (len(v4['ts']), 24, vs.N_COLUMNAS) and t['ts'].equals(v4['ts'])
    np.testing.assert_array_equal(t['X'][:, :, :66], v4['X'])
    rel = ((valores['PED'] - perfil['base']) / sigma['PED']).loc[t['ts']].to_numpy(np.float32)
    np.testing.assert_allclose(t['X'][:, -1, 66], rel, rtol=1e-6)            # la hora t: su lectura contra la base
    assert (t['X'][:, -1, 67] == 1).all()                                      # siempre con dato en t
    falta = t['X'][:, :, 67] == 0
    assert falta.any() and (t['X'][:, :, 66][falta] == 0).all()                # sin dato: 0 con máscara 0
    assert t['ts'].min() >= pd.Timestamp('2022-01-01')


def test_la_lectura_del_objetivo_solo_entra_por_sus_2_columnas(valores):
    t, *_ = _tensores(valores)
    otra = valores.copy()
    h = t['ts'][100]
    otra.loc[h, 'PED'] += 50.0
    t2, *_ = _tensores(otra)
    i = t['ts'].get_loc(h)
    np.testing.assert_array_equal(t2['X'][:, :, :66], t['X'][:, :, :66])     # las 66 del V4 no ven al objetivo
    assert t2['X'][i, -1, 66] > t['X'][i, -1, 66]


def test_muestra_reproducible_sin_reemplazo_y_distinta_por_uso_y_estacion():
    a = vs.muestra(17000, 'seleccion', 1, 0)
    assert np.array_equal(a, vs.muestra(17000, 'seleccion', 1, 0))
    assert len(a) == 17000 // vs.CADA and len(np.unique(a)) == len(a) and np.all(np.diff(a) > 0)
    assert not np.array_equal(a, vs.muestra(17000, 'seleccion', 1, 1))
    assert not np.array_equal(a, vs.muestra(17000, 'validacion', 1, 0))
    assert not np.array_equal(a, vs.muestra(17000, 'seleccion', 2, 0))
    rng = np.random.default_rng([42, 18, 0, 1, 0])
    assert np.array_equal(a, np.sort(rng.choice(17000, size=17000 // 8, replace=False)))


def test_compartido_ordena_las_otras_estaciones_por_distancia(valores):
    t, perfil, mu, sigma, entradas = _tensores(valores)
    otras = [c for c in entradas.columns if c != 'PED']
    orden = otras[::-1]
    t2 = vs.tensores(entradas, valores, 'PED', mu, sigma, perfil, ('validacion',), orden=orden)
    n = len(otras)
    for k, c in enumerate(orden):
        i = otras.index(c)
        np.testing.assert_array_equal(t2['X'][:, :, k], t['X'][:, :, i])              # valor
        np.testing.assert_array_equal(t2['X'][:, :, n + k], t['X'][:, :, n + i])      # máscara
    np.testing.assert_array_equal(t2['X'][:, :, 2 * n:], t['X'][:, :, 2 * n:])        # hora y propias
    with pytest.raises(ValueError):
        vs.tensores(entradas, valores, 'PED', mu, sigma, perfil, ('validacion',), orden=orden[:-1])
    dist = pd.DataFrame(np.abs(np.subtract.outer(np.arange(len(m.ESTACIONES)), np.arange(len(m.ESTACIONES)))),
                        index=m.ESTACIONES, columns=m.ESTACIONES, dtype=float)
    o = vs.orden_por_distancia('PED', dist)
    assert len(o) == len(m.ESTACIONES) - 1 and 'PED' not in o and 'XAL' in o and sorted(o) == sorted(otras)
    assert all(dist.at['PED', a] <= dist.at['PED', b] for a, b in zip(o, o[1:]))
    assert vs.cuantos(valores, 'PED', perfil, ('validacion',)) == len(t['ts']) // vs.CADA


class _Eco:
    """Modelo de prueba: devuelve la columna propia de la última fila."""

    def predict(self, X, batch_size=None, verbose=0):
        return X[:, -1, 66:67]


def test_probabilidades_en_las_horas_validas_y_nan_en_las_demas(valores):
    mu, sigma = m.normalizacion(valores, ('validacion',), ['XAL'])
    idx = valores.loc['2022-01-01':].index
    p = vs.probabilidades({'PED': _Eco(), 'TLA': _Eco()}, valores, ['XAL'], mu, sigma, 'validacion', idx)
    t, *_ = _tensores(valores)
    assert list(p.columns) == ['PED', 'TLA'] and p.index.equals(idx)
    np.testing.assert_allclose(p['PED'].loc[t['ts']].to_numpy(), t['X'][:, -1, 66], rtol=1e-6)
    assert p['PED'].drop(t['ts']).isna().all()
