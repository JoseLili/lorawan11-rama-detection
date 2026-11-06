"""Pruebas de `src.detect.linea_base` con una red sintética de 6 estaciones."""
import numpy as np
import pandas as pd
import pytest

from src.detect import evaluacion_red as ev
from src.detect import linea_base as lb

EST = ['A', 'B', 'C', 'D', 'E', 'F']


@pytest.fixture(scope='module')
def red():
    rng = np.random.default_rng(0)
    idx = pd.date_range('2020-01-01', periods=24 * 90, freq='h')
    ciclo = 30 + 20 * np.sin(2 * np.pi * (idx.hour.to_numpy() - 9) / 24)
    x = pd.DataFrame(index=idx)
    for i, s in enumerate(EST):
        v = ciclo + 3 * i + rng.normal(0, 4, len(idx))
        v[rng.random(len(idx)) < 0.05] = np.nan
        x[f'{s}_valor'] = np.round(v)
        x[f'{s}_mascara'] = (~np.isnan(v)).astype(float)
    x['hora_sin'] = np.sin(2 * np.pi * idx.hour / 24)
    x['hora_cos'] = np.cos(2 * np.pi * idx.hour / 24)
    vecinas = {s: [e for e in EST if e != s][:4] for s in EST}
    _, sigma = ev.normalizacion(x)
    par = ev.ajustar_vecinas('a14', x, sigma, vecinas)
    return x, sigma, par, vecinas


def test_entradas_v0_igual_a_repo(red):
    x, sigma, par, vecinas = red
    vec = lb.indices_vecinas(EST, vecinas)
    F = lb.entradas(x, lb.base_v0(x, EST), EST, sigma[EST].to_numpy(), par.escala[EST].to_numpy(), vec)
    np.testing.assert_array_equal(F, ev.entradas_de('vecinas', x, None, sigma, par))


def test_escala_a14_igual_a_repo(red):
    x, sigma, par, vecinas = red
    vec = lb.indices_vecinas(EST, vecinas)
    esc = lb.escala_a14(x, lb.base_v0(x, EST), EST, sigma[EST].to_numpy(), vec, x.index[-1])
    np.testing.assert_allclose(esc, par.escala[EST].to_numpy(), rtol=1e-12)


@pytest.mark.parametrize('variante', ['Vb', 'Vc'])
def test_bases_causales(red, variante):
    """Cambiar la lectura en t no cambia la base en t ni antes."""
    x, sigma, par, vecinas = red
    vec = lb.indices_vecinas(EST, vecinas)
    t = 24 * 60 + 15

    def base(xx):
        V, b0 = lb.valores(xx, EST), lb.base_v0(xx, EST)
        if variante == 'Vb':
            return lb.base_vb(V, b0, vec, xx.index)
        return lb.base_vc(V, b0, np.full(len(EST), 2.0), xx.index)

    y = x.copy()
    y.iloc[t, y.columns.get_loc('A_valor')] += 100
    np.testing.assert_array_equal(base(x)[:t + 1], base(y)[:t + 1])
    assert not np.array_equal(base(x)[t + 1:], base(y)[t + 1:])
