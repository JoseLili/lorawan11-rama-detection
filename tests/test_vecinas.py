"""Vecinas cercanas: orden por distancia, selección de k y copia del V4 cuando k* = 32."""

import json

import numpy as np
import pandas as pd
import pytest

from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect import contemporaneo as ct
from src.detect import vecinas as vc

GEO = pd.read_csv('results/inventario_multianual/estaciones_geografia.csv', index_col=0)


def test_vecinas_ordenadas_por_distancia_sin_objetivo_ni_inactivas():
    d = vc.distancias(GEO)
    assert d.at['CCA', 'PED'] == pytest.approx(2.9, abs=0.1)        # catálogo: 2.9 km
    np.testing.assert_allclose(d.to_numpy(), d.to_numpy().T)
    v = vc.vecinas_cercanas(d, 'CCA', 8, inactivos=['XAL'])
    assert v[0] == 'PED' and 'CCA' not in v and len(v) == 8
    assert list(d.loc['CCA', v]) == sorted(d.loc['CCA', v])
    assert 'XAL' not in vc.vecinas_cercanas(d, 'LPR', 31, inactivos=['XAL'])


@pytest.fixture(scope='module')
def ctx():
    rej = pd.date_range(m.INICIO, m.FIN, freq='h')
    rng = np.random.default_rng(5)
    comun = 40 + 30 * np.sin(2 * np.pi * (rej.hour - 9) / 24) + rng.normal(0, 8, len(rej))
    v = pd.DataFrame({s: np.round(np.clip(comun + rng.normal(0, 3, len(rej)), 0, 180)) for s in m.ESTACIONES},
                     index=rej)
    v.loc[:'2022-12-31 23:00', 'XAL'] = np.nan
    ina_i = m.canales_inactivos(v, ('ajuste_inicial',)); ina_d = m.canales_inactivos(v, m.AJUSTE_DEFINITIVO)
    mu_i, sg_i = m.normalizacion(v, ('ajuste_inicial',), ina_i); mu_d, sg_d = m.normalizacion(v, m.AJUSTE_DEFINITIVO, ina_d)
    return dict(valores=v, inicial=dict(inactivos=ina_i, mu=mu_i, sigma=sg_i, entradas=m.entradas_modelo(v, ina_i)),
                definitiva=dict(inactivos=ina_d, mu=mu_d, sigma=sg_d, entradas=m.entradas_modelo(v, ina_d)))


@pytest.mark.parametrize('val_v4, k_esperado', [(1e9, 4), (1e-9, 32)])
def test_entrenar_knn_entrena_o_copia_v4(ctx, tmp_path, val_v4, k_esperado):
    pytest.importorskip('tensorflow')
    v4 = tmp_path / 'v4'
    em.entrenar_objetivo(ctx, 'CCA', v4 / 'CCA', max_epocas=2, unidades=4)
    cfg_v4 = json.loads((v4 / 'CCA/configuracion.json').read_text())
    cfg_v4['val_loss_minimo'] = val_v4                             # fuerza qué k gana
    (v4 / 'CCA/configuracion.json').write_text(json.dumps(cfg_v4))
    d = vc.distancias(GEO)
    cfg = vc.entrenar_knn(ctx, 'CCA', tmp_path / 'knn/CCA', d, v4, ks=(4,), max_epocas=2, unidades=4)
    assert cfg['k'] == k_esperado
    sel = pd.read_csv(tmp_path / 'knn/CCA/seleccion_k.csv')
    assert list(sel.k) == [4, 32]
    if k_esperado == 4:
        assert cfg['n_features'] == 10 and len(cfg['vecinas']) == 4
        assert ct.regenerar(ctx, 'CCA', tmp_path / 'knn/CCA') == cfg['umbral_p95_ppb']
    else:
        assert (tmp_path / 'knn/CCA/modelo.keras').read_bytes() == (v4 / 'CCA/modelo.keras').read_bytes()
        assert (tmp_path / 'knn/CCA/predicciones_2024.csv.gz').exists()
    with pytest.raises(FileExistsError):
        vc.entrenar_knn(ctx, 'CCA', tmp_path / 'knn/CCA', d, v4, ks=(4,), max_epocas=2, unidades=4)
