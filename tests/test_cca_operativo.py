"""Consistencia de la referencia operativa, separada de la calibracion p95."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_metricas_operativas_y_conteos():
    df = pd.read_csv(ROOT / 'results/metricas_operativas_cca_bits_1_7.csv')
    assert df.bit.tolist() == list(range(1, 8))
    assert df.umbral_ppb.eq(22.6).all()
    assert float((ROOT / 'results/umbral_operativo_cca.txt').read_text()) == 22.6
    assert float((ROOT / 'results/umbral_p95_cca.txt').read_text()) == 14.748354911804199
    assert df.tp.tolist() == [3, 3, 8, 14, 61, 78, 78]
    assert df.fp.eq(163).all()
    assert (df.tp + df.fn).eq(78).all()
    assert (df.fp + df.tn).eq(1606).all()
    np.testing.assert_allclose(df.recall_pct, 100 * df.tp / (df.tp + df.fn))
    np.testing.assert_allclose(df.precision_pct, 100 * df.tp / (df.tp + df.fp))
    np.testing.assert_allclose(df.f2_pct, 100 * 5 * df.tp / (5 * df.tp + 4 * df.fn + df.fp))


def test_figuras_comparten_recall_operativo_y_producto():
    metricas = pd.read_csv(ROOT / 'results/metricas_operativas_cca_bits_1_7.csv')
    riesgo = pd.read_csv(ROOT / 'results/riesgo_compuesto_por_bit.csv')
    oportunidad = pd.read_csv(ROOT / 'results/oportunidad_cruda_por_bit.csv')
    for tabla in [riesgo, oportunidad]:
        assert tabla.bit.tolist() == list(range(1, 8))
        assert tabla.umbral_operativo_ppb.eq(22.6).all()
        np.testing.assert_allclose(tabla.recall_pct, metricas.recall_pct)
        np.testing.assert_allclose(tabla.oportunidad_pct, 100 * tabla.dias_oportunidad / tabla.n_dias)
    np.testing.assert_allclose(riesgo.riesgo_compuesto_pct,
                               riesgo.oportunidad_pct * (1 - metricas.recall_fraccion))


def test_celda_figuras_lee_operativo_no_p95():
    nb = json.loads((ROOT / 'notebooks/08_proximidad_umbrales.ipynb').read_text())
    source = ''.join(nb['cells'][-1]['source'])
    assert 'results/umbral_operativo_cca.txt' in source
    assert 'results/metricas_operativas_cca_bits_1_7.csv' in source
    assert 'results/umbral_p95_cca.txt' not in source
    assert 'umbral percentil 95' not in source
