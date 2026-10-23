"""Protocolo anomalias_red_v1: entradas, umbral por falsas alarmas y métricas de red."""

import numpy as np
import pandas as pd
import pytest

from src.detect import anomalias_red as ar
from src.detect import evaluacion_red as ev
from src.detect import multianual as m


def _matriz(dias=3, valor=40.0):
    idx = pd.date_range('2024-01-01', periods=24 * dias, freq='h')
    v = pd.DataFrame(valor, index=idx, columns=m.ESTACIONES)
    return ar.matriz_red(v, ar.columnas_entrada(['XAL']))


def test_entradas_66_columnas_normalizadas_y_huecos_en_cero():
    x = _matriz()
    x.iloc[0, x.columns.get_loc('CCA_valor')] = np.nan
    x.iloc[0, x.columns.get_loc('CCA_mascara')] = 0
    mu = pd.Series(30.0, index=ev.estaciones_de(x))
    sigma = pd.Series(5.0, index=ev.estaciones_de(x))
    X = ev.entradas(x, mu, sigma)
    i = ev.estaciones_de(x).index('CCA')
    assert X.shape == (72, 66) and X.dtype == np.float32
    assert X[1, i] == 2.0 and X[0, i] == 0.0 and X[0, 32 + i] == 0.0 and X[1, 32 + i] == 1.0
    np.testing.assert_allclose(X[:, 64], x['hora_sin'].to_numpy(), rtol=1e-6)


def test_normalizacion_ddof1_y_desviacion_cero_a_uno():
    x = _matriz()
    mu, sigma = ev.normalizacion(x)
    assert (mu == 40.0).all() and (sigma == 1.0).all()


def test_umbral_respeta_el_objetivo_con_empates():
    s = np.r_[np.zeros(90), np.full(5, 0.3), np.full(5, 0.8)]
    assert ev.umbral_falsas_alarmas(s, 0.05) == 0.3       # > 0.3 deja 5 %
    assert ev.umbral_falsas_alarmas(s, 0.10) == 0.0       # > 0 deja 10 %
    assert ev.umbral_falsas_alarmas(s, 0.01) == 0.8       # nada pasa de 0.8
    rng = np.random.default_rng(0)
    c = rng.random(10000)
    u = ev.umbral_falsas_alarmas(c, 0.05)
    assert 0.049 <= (c > u).mean() <= 0.05


def test_por_episodio_primera_alerta_y_sin_alerta():
    idx = pd.date_range('2024-01-01', periods=24 * 10, freq='h')
    alerta = pd.Series(False, index=idx)
    alerta[pd.Timestamp('2024-01-03 05:00')] = True
    alerta[pd.Timestamp('2024-01-03 09:00')] = True
    plan = pd.DataFrame(dict(estacion=['CCA', 'PED'], signo=[1, -1],
                             inicio=pd.to_datetime(['2024-01-03', '2024-01-06']),
                             fin=pd.to_datetime(['2024-01-04 23:00', '2024-01-06 23:00'])))
    e = ev.por_episodio(plan, alerta)
    assert e.detectado.tolist() == [True, False]
    assert e.horas_hasta_alerta.iat[0] == 5 and np.isnan(e.horas_hasta_alerta.iat[1])


def test_por_hora():
    y = pd.Series([1, 1, 0, 0, 0, 0])
    a = pd.Series([True, False, True, False, False, False])
    r = ev.por_hora(a, y)
    assert r['deteccion_hora_pct'] == 50 and r['falsa_alarma_hora_pct'] == 25


def test_horas_con_dato():
    x = _matriz(dias=5)
    x.loc['2024-01-02', 'CCA_mascara'] = 0
    plan = pd.DataFrame(dict(estacion=['CCA', 'CCA'], inicio=pd.to_datetime(['2024-01-02', '2024-01-03']),
                             fin=pd.to_datetime(['2024-01-02 23:00', '2024-01-04 23:00'])))
    assert ev.horas_con_dato(plan, x) == [0, 48]


def test_cambio_maximo_y_por_tamano():
    limpia = _matriz(dias=1, valor=40.0)
    limpia.iloc[0, limpia.columns.get_loc('PED_valor')] = np.nan
    x = limpia.copy()
    x.iloc[1, x.columns.get_loc('CCA_valor')] = 80.0       # +40
    x.iloc[1, x.columns.get_loc('PED_valor')] = 30.0       # −10: el mayor de la hora es 40
    x.iloc[2, x.columns.get_loc('PED_valor')] = 104.0      # +64
    x.iloc[3, x.columns.get_loc('PED_valor')] = 39.0       # −1
    c = ev.cambio_maximo(x, limpia)
    assert c.iloc[:5].tolist() == [0, 40, 64, 1, 0]
    alerta = pd.Series(False, index=x.index)
    alerta.iloc[[1, 5]] = True
    t = ev.por_tamano(alerta, c)
    assert t.tramo_ppb.tolist() == ['sin cambio', '1-16', '16-32', '32-64', '>=64']
    assert t.horas.tolist() == [21, 1, 0, 1, 1] and t.alertan.tolist() == [1, 0, 0, 1, 0]
    assert 'alertan_azar' not in t
    limpia_alerta = pd.Series(False, index=x.index)
    limpia_alerta.iloc[[2, 5, 6]] = True
    t = ev.por_tamano(alerta, c, limpia_alerta)
    assert t.alertan.tolist() == [1, 0, 0, 1, 0] and t.alertan_azar.tolist() == [2, 0, 0, 0, 1]


def test_relativas_restan_el_perfil_causal_de_14_dias():
    x = _matriz(dias=20, valor=40.0)
    t = pd.Timestamp('2024-01-18 15:00')
    x.loc[t, 'CCA_valor'] = 80.0                       # el doble a las 15 h del día 18
    r = ev.relativas(x)
    assert r.loc[t, 'CCA'] == 40.0                     # perfil de los 14 días previos = 40
    assert r.loc[t + pd.Timedelta(days=1), 'CCA'] == pytest.approx(40 - (13 * 40 + 80) / 14)
    assert r.loc['2024-01-05':, 'PED'].abs().max() == 0
    sigma = pd.Series(10.0, index=ev.estaciones_de(x))
    X = ev.entradas_relativas(x, sigma)
    i = ev.estaciones_de(x).index('CCA')
    assert X.shape == (480, 66) and X[x.index.get_loc(t), i] == 4.0 and X[0, 32 + i] == 1.0


def test_relativas_con_historia_previa_contigua():
    x = _matriz(dias=30, valor=40.0)
    previa, actual = x.iloc[:24 * 20], x.iloc[24 * 20:]
    pd.testing.assert_frame_equal(ev.relativas(actual, previa), ev.relativas(x).iloc[24 * 20:])
    with pytest.raises(ValueError):
        ev.relativas(actual, previa.iloc[:-1])


def test_con_historia_y_entradas_de():
    x = _matriz(dias=30, valor=40.0)
    previa, actual = x.iloc[:24 * 20], x.iloc[24 * 20:]
    h = ev.con_historia(previa, actual)
    pd.testing.assert_frame_equal(h, x, check_freq=False)
    with pytest.raises(ValueError):
        ev.con_historia(previa.iloc[:-1], actual)
    mu = pd.Series(30.0, index=ev.estaciones_de(x))
    sigma = pd.Series(5.0, index=ev.estaciones_de(x))
    np.testing.assert_array_equal(ev.entradas_de('crudas', x, mu, sigma), ev.entradas(x, mu, sigma))
    np.testing.assert_array_equal(ev.entradas_de('relativas', x, mu, sigma), ev.entradas_relativas(x, sigma))
    with pytest.raises(ValueError):
        ev.entradas_de('otra', x, mu, sigma)


# ---------------------------------------------------------------- vecinas (revisión 8)

GEO = pd.read_csv('results/inventario_multianual/estaciones_geografia.csv', index_col='station')


def _vecinas(x):
    return ev.vecinas_de(ev.estaciones_de(x), GEO)


def test_vecinas_de_son_las_4_mas_cercanas_entre_las_columnas():
    x = _matriz()
    vec = _vecinas(x)
    est = ev.estaciones_de(x)
    assert set(vec) == set(est) and 'XAL' not in est
    assert vec['CCA'] == ['PED', 'BJU', 'AJM', 'UAX']           # el mismo orden de la parte 1
    for s, vs in vec.items():
        assert len(vs) == 4 and s not in vs and set(vs) <= set(est)


@pytest.mark.parametrize('forma', ev.FORMAS)
def test_columna_de_vecinas_vale_cero_si_todas_marcan_igual_y_ve_a_la_alterada(forma):
    x = _matriz(dias=20, valor=40.0)
    est = ev.estaciones_de(x)
    sigma = pd.Series(1.0, index=est)
    par = ev.ajustar_vecinas(forma, x, sigma, _vecinas(x))
    t = pd.Timestamp('2024-01-18 15:00')
    assert ev.columnas_vecinas(x, sigma, par).loc[t].abs().max() == pytest.approx(0.0, abs=1e-12)
    y = x.copy()
    y.loc[t, 'CCA_valor'] = 80.0                               # sólo CCA se aleja de sus vecinas
    c = ev.columnas_vecinas(y, sigma, par)
    assert c.loc[t, 'CCA'] > 0
    assert all(c.loc[t, s] < 0 for s in par.vecinas['CCA'] if 'CCA' in par.vecinas[s])
    lejanas = [s for s in est if s != 'CCA' and 'CCA' not in par.vecinas[s]]
    assert c.loc[t, lejanas].abs().max() == pytest.approx(0.0, abs=1e-12)
    assert c.loc[:t - pd.Timedelta(hours=1)].abs().max().max() == pytest.approx(0.0, abs=1e-12)  # causal


def test_diferencia_de_desviaciones_cancela_un_cambio_comun_a_todas():
    x = _matriz(dias=20, valor=40.0)
    sigma = pd.Series(1.0, index=ev.estaciones_de(x))
    par = ev.ajustar_vecinas('a14', x, sigma, _vecinas(x))
    t = pd.Timestamp('2024-01-18 15:00')
    y = x.copy()
    y.loc[t, [c for c in y.columns if c.endswith('_valor')]] += 25.0     # un día de mucho sol para todas
    assert ev.columnas_vecinas(y, sigma, par).loc[t].abs().max() == pytest.approx(0.0, abs=1e-12)


def test_cociente_ve_un_error_de_ganancia_como_un_desplazamiento_de_log():
    x = _matriz(dias=20, valor=60.0)
    sigma = pd.Series(1.0, index=ev.estaciones_de(x))
    sin_escala = ev.Vecinas('bfija', _vecinas(x), None, pd.Series(1.0, index=ev.estaciones_de(x)))
    par = ev.ajustar_vecinas('bfija', x, sigma, sin_escala.vecinas)
    par = ev.Vecinas(par.forma, par.vecinas, par.fija, sin_escala.escala)
    t = pd.Timestamp('2024-01-18 15:00')
    y = x.copy()
    y.loc[t, 'CCA_valor'] = 66.0                               # +10 %
    assert ev.columnas_vecinas(y, sigma, par).loc[t, 'CCA'] == pytest.approx(np.log(76 / 70))


def test_columna_de_vecinas_sin_dato_o_con_menos_de_2_vecinas_es_nan_y_entra_como_cero():
    x = _matriz(dias=20, valor=40.0)
    est = ev.estaciones_de(x)
    sigma = pd.Series(1.0, index=est)
    vec = _vecinas(x)
    par = ev.ajustar_vecinas('b14', x, sigma, vec)
    t = pd.Timestamp('2024-01-18 15:00')
    y = x.copy()
    y.loc[t, 'CCA_valor'] = np.nan                             # sin dato propio
    y.loc[t, [f'{s}_valor' for s in vec['PED'][:3]]] = np.nan  # PED se queda con 1 vecina con dato
    c = ev.columnas_vecinas(y, sigma, par)
    assert np.isnan(c.loc[t, 'CCA']) and np.isnan(c.loc[t, 'PED'])
    X = ev.entradas_de('vecinas', y, None, sigma, par)
    assert X.shape == (len(y), 98)
    np.testing.assert_array_equal(X[:, :66], ev.entradas_relativas(y, sigma))
    assert X[y.index.get_loc(t), 66 + est.index('CCA')] == 0.0


def test_ajustar_vecinas_referencia_fija_y_escala():
    x = _matriz(dias=20, valor=40.0)
    x[[c for c in x.columns if c.endswith('_valor')]] += np.arange(len(x))[:, None] % 7   # algo de variación
    sigma = pd.Series(1.0, index=ev.estaciones_de(x))
    vec = _vecinas(x)
    for forma in ev.FORMAS:
        par = ev.ajustar_vecinas(forma, x, sigma, vec)
        assert (par.escala > 0).all()
        assert (par.fija is None) == forma.endswith('14')
        if par.fija is not None:
            assert par.fija.shape == (24, 32)
    with pytest.raises(ValueError):
        ev.ajustar_vecinas('c14', x, sigma, vec)
    with pytest.raises(ValueError):
        ev.entradas_de('vecinas', x, None, sigma)
