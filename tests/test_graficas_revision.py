import numpy as np
import pandas as pd
import pytest

from experiments.graficas_revision.generar import resumir
from src.attack.blind import atacar_serie
from src.detect.red import contexto_diario, efectos_red


def eventos():
    return pd.DataFrame(dict(
        fecha=pd.to_datetime(['2025-10-21', '2025-10-21', '2025-10-22', '2025-10-22']),
        bit=[4]*4, evaluable=[True]*4, detectado=[True, False, False, False],
        falsa_fase1=[True, False, False, False], anulada_fase1=[False]*4))


def test_producto_no_es_dano_observado():
    r = resumir(eventos()).set_index('tipo_dano').loc['falsa_fase1']
    assert r.dias_vulnerables_pct == 50
    assert r.no_deteccion_pct == 75
    assert r.riesgo_compuesto_indicador_pct == 37.5
    assert r.dias_dano_no_detectado_pct == 0
    assert r.no_deteccion_condicionada_dano_pct == 0


def test_sin_dano_no_inventa_recall_condicionado():
    r = resumir(eventos()).set_index('tipo_dano').loc['anulada_fase1']
    assert r.dias_vulnerables == 0 and r.riesgo_compuesto_indicador_pct == 0
    assert np.isnan(r.no_deteccion_condicionada_dano_pct)
    assert r.no_deteccion_pct == 75  # Hay ataques aunque no provoquen este daño.


def test_dia_con_varios_ataques_se_cuenta_una_vez():
    e = eventos()
    e.loc[1, 'falsa_fase1'] = True
    r = resumir(e).set_index('tipo_dano').loc['falsa_fase1']
    assert r.dias_vulnerables == 1 and r.ataques_daninos == 2
    assert r.dias_dano_no_detectado == 1


def test_sin_modelo_no_se_supone_detectado():
    e = eventos()
    e.loc[0, 'evaluable'] = False
    with pytest.raises(AssertionError, match='sin modelo'):
        resumir(e)


@pytest.mark.parametrize('bit', range(8))
def test_bits_inferiores_no_se_renumeran(bit):
    x = np.arange(256, dtype=float)
    real, labels = atacar_serie(x, bit, tasa=1, seed=42)
    np.testing.assert_array_equal(real, x.astype(int) ^ (1 << bit))
    assert labels.all()


def test_ocultar_un_maximo_no_oculta_otro():
    m = pd.DataFrame({'CCA': [160., 100.], 'AJM': [159., 90.]},
                     index=pd.date_range('2025-01-01', periods=2, freq='h'))
    contexto = contexto_diario(m)
    alteradas = contexto.original_ppb.to_numpy().copy()
    alteradas[0] = 128
    efecto = efectos_red(contexto, alteradas)
    assert efecto.maximo_atacado_ppb.iloc[0] == 159
    assert not efecto.anulada_fase1.iloc[0]


def test_bit0_puede_cruzar_umbral_desde_154():
    m = pd.DataFrame({'CCA': [154.]}, index=pd.to_datetime(['2025-01-01']))
    contexto = contexto_diario(m)
    alterada, _ = atacar_serie(contexto.original_ppb.to_numpy(), 0, tasa=1)
    assert efectos_red(contexto, alterada).falsa_fase1.iloc[0]
