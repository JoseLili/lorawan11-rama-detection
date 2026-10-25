"""Protocolo anomalias_red_v1, revisión 6: ventanas del LSTM supervisado de red."""

import numpy as np
import pytest

from src.detect import lstm_red as lr


def test_ventana_termina_en_t_e_incluye_t():
    F = np.arange(100, dtype=float)[:, None] * np.ones((1, 3))
    X = lr.ventanas(F, np.array([23, 50, 99]))
    assert X.shape == (3, 24, 3)
    assert X[0, 0, 0] == 0 and X[0, -1, 0] == 23
    assert X[1, 0, 0] == 27 and X[1, -1, 0] == 50
    assert X[2, -1, 0] == 99


def test_ventana_rechaza_posiciones_sin_historia_completa():
    F = np.zeros((50, 2))
    with pytest.raises(ValueError):
        lr.ventanas(F, np.array([22]))
    with pytest.raises(ValueError):
        lr.ventanas(F, np.array([50]))


def test_clasificador_con_una_salida_igual_al_de_siempre_y_con_31_por_estacion():
    from src.detect.lstm import fijar_semilla
    fijar_semilla(42)
    uno = lr.construir_clasificador(n_features=98)
    fijar_semilla(42)
    varias = lr.construir_clasificador(n_features=98, salidas=31)
    # LSTM 64: 4·64·(98 + 64 + 1); densa 32: 64·32 + 32; salida: 32·k + k
    base = 4 * 64 * (98 + 64 + 1) + 64 * 32 + 32
    assert uno.count_params() == base + 33 and uno.output_shape == (None, 1)
    assert varias.count_params() == base + 32 * 31 + 31 and varias.output_shape == (None, 31)
    fijar_semilla(42)
    local = lr.construir_clasificador(n_features=17)                  # revisión 14
    assert local.count_params() == 4 * 64 * (17 + 64 + 1) + 64 * 32 + 32 + 33
