"""Variante contemporánea: ventana con la hora t, lineal reproducible y atacante simultáneo."""

import numpy as np
import pandas as pd
import pytest

from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect import ataques_multianual as at
from src.detect import contemporaneo as ct


@pytest.fixture(scope='module')
def ctx():
    rej = pd.date_range(m.INICIO, m.FIN, freq='h')
    rng = np.random.default_rng(3)
    comun = 40 + 30 * np.sin(2 * np.pi * (rej.hour - 9) / 24) + rng.normal(0, 8, len(rej))
    v = pd.DataFrame({s: np.round(np.clip(comun + rng.normal(0, 3, len(rej)), 0, 180)) for s in m.ESTACIONES},
                     index=rej)
    v[rng.random(v.shape) < 0.1] = np.nan
    v.loc[:'2022-12-31 23:00', 'XAL'] = np.nan
    ina_i = m.canales_inactivos(v, ('ajuste_inicial',))
    ina_d = m.canales_inactivos(v, m.AJUSTE_DEFINITIVO)
    mu_i, sg_i = m.normalizacion(v, ('ajuste_inicial',), ina_i)
    mu_d, sg_d = m.normalizacion(v, m.AJUSTE_DEFINITIVO, ina_d)
    return dict(valores=v,
                inicial=dict(inactivos=ina_i, mu=mu_i, sigma=sg_i, entradas=m.entradas_modelo(v, ina_i)),
                definitiva=dict(inactivos=ina_d, mu=mu_d, sigma=sg_d, entradas=m.entradas_modelo(v, ina_d)))


def test_ventana_con_hora_t_termina_en_t_y_excluye_objetivo(ctx):
    v, d = ctx['valores'], ctx['definitiva']
    perfil = m.perfil_causal(v['CCA'])
    t4 = em.tensores(d['entradas'], v, 'CCA', d['mu'], d['sigma'], perfil, ('calibracion',))
    tc = em.tensores(d['entradas'], v, 'CCA', d['mu'], d['sigma'], perfil, ('calibracion',), incluir_t=True)
    assert tc['X'].shape[1:] == (24, 66) and t4['ts'].equals(tc['ts'])
    F = em.caracteristicas(d['entradas'], 'CCA', d['mu'], d['sigma'])
    i = v.index.get_loc(tc['ts'][100])
    np.testing.assert_array_equal(tc['X'][100, -1], F[i])          # última fila = hora t
    np.testing.assert_array_equal(t4['X'][100, -1], F[i - 1])      # V4: hora t−1
    np.testing.assert_array_equal(tc['X'][100, :-1], t4['X'][100, 1:])


def test_lineal_reproducible_y_cargable(ctx, tmp_path):
    cfg = ct.entrenar_lineal(ctx, 'CCA', tmp_path / 'a/CCA')
    assert cfg['tipo'] == 'lineal' and cfg['alpha'] in ct.ALPHAS and cfg['incluir_t']
    ct.entrenar_lineal(ctx, 'CCA', tmp_path / 'b/CCA')
    assert ct.comparar_lineal(tmp_path / 'a/CCA', tmp_path / 'b/CCA').identico.all()
    with pytest.raises(FileExistsError):
        ct.entrenar_lineal(ctx, 'CCA', tmp_path / 'a/CCA')
    modelo, incluir_t = ct.cargar_modelo(tmp_path / 'a/CCA')
    assert incluir_t and isinstance(modelo, ct.ModeloLineal)
    pred = at.cargar_predicciones(tmp_path / 'a', ctx, regenerar=ct.regenerar)
    assert set(pred.timestamp.dt.year) == {2024, 2025, 2026} and (pred.estacion == 'CCA').all()
    # el modelo con información de la misma hora predice mejor que el perfil solo
    cal = pd.read_csv(tmp_path / 'a/CCA/calibracion_2023.csv.gz')
    assert cal.residuo_ppb.abs().mean() < (cal.original_ppb - cal.base_ppb).abs().mean()


def test_matriz_atacada_voltea_todas_las_estaciones_solo_en_horas_elegidas(ctx):
    v = ctx['valores']
    horas = ct.plan_horas(v, 2024)
    assert 0.03 < len(horas) / len(v.loc['2024']) < 0.07
    va = ct.matriz_atacada(v, horas, 5)
    a, b = v.loc[horas].to_numpy(), va.loc[horas].to_numpy()
    obs = ~np.isnan(a)
    np.testing.assert_array_equal(b[obs], a[obs].astype(int) ^ 32)
    otras = v.index.difference(horas)
    assert va.loc[otras].equals(v.loc[otras])


def test_simultaneo_etiqueta_mensajes_de_horas_atacadas(ctx, tmp_path):
    ct.entrenar_lineal(ctx, 'CCA', tmp_path / 'lin/CCA')
    horas = ct.plan_horas(ctx['valores'], 2026)
    r = ct.evaluar_simultaneo_bit(ctx, {'lineal_t': tmp_path / 'lin'}, 2026, 7, horas)
    assert list(r.estacion) == ['CCA']
    fila = r.iloc[0]
    observadas = ctx['valores'].loc[horas, 'CCA'].notna().sum()
    assert fila.atacados == observadas and fila.tp + fila.fn == observadas
    agr = ct.agregar_simultaneo(r, pd.Series({'CCA': 'principal'}))
    assert agr.iloc[0].tp == fila.tp


def test_lstm_t_guarda_incluir_t(ctx, tmp_path):
    pytest.importorskip('tensorflow')
    cfg = em.entrenar_objetivo(ctx, 'CCA', tmp_path / 'CCA', max_epocas=2, unidades=4,
                               incluir_t=True, protocolo=ct.PROTOCOLO)
    assert cfg['incluir_t'] and cfg['protocolo'] == ct.PROTOCOLO
    assert ct.cargar_modelo(tmp_path / 'CCA')[1] is True
    assert ct.regenerar(ctx, 'CCA', tmp_path / 'CCA') == cfg['umbral_p95_ppb']
