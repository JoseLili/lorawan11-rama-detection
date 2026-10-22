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
