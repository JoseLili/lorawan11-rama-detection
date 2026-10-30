import pandas as pd
from experiments.barcelona.generar_planes_proporcionales import generar, DELTAS


def test_duracion_signo_continuidad_sin_superposiciones():
    p, tasa = generar('2014-01-01', '2014-12-31', ['08015021','08019043'], 0, 1, p=.5)
    assert tasa == .5 and len(p) > 0
    assert p.dias_sorteados.between(1, 7).all()
    assert p.dias.between(1, 7).all() and p.signo.isin([-1,1]).all()
    assert p.inicio.dt.hour.eq(0).all() and p.fin.dt.hour.eq(23).all()
    assert ((p.fin - p.inicio + pd.Timedelta(hours=1)) == pd.to_timedelta(p.dias, unit='D')).all()
    for _, g in p.groupby('estacion'):
        assert (g.inicio.iloc[1:].reset_index(drop=True) > g.fin.iloc[:-1].reset_index(drop=True)).all()
    assert p.fin.max() <= pd.Timestamp('2014-12-31 23:00', tz='UTC')


def test_mismo_plan_cinco_deltas_y_estaciones_independientes():
    p, _ = generar('2018-01-01', '2018-12-31', ['08015021','08019043'], 3, 1, p=.1)
    q, _ = generar('2018-01-01', '2018-12-31', ['08015021'], 3, 1, p=.1)
    pd.testing.assert_frame_equal(p[p.estacion=='08015021'].drop(columns='episodio').reset_index(drop=True),
                                  q.drop(columns='episodio'), check_exact=True)
    z, _ = generar('2018-01-01', '2018-12-31', ['08015021','08019043'], 3, 1, p=.1)
    pd.testing.assert_frame_equal(p, z, check_exact=True)
    assert DELTAS == (1., .5, .2, .1, .05)


def test_usos_separados_y_tasa_original():
    p, tasa = generar('2016-01-01', '2016-12-31', ['08015021'], 1, 1)
    _, otra = generar('2016-01-01', '2016-12-31', ['08015021'], 2, 1)
    assert .001 <= tasa <= .003 and tasa != otra
