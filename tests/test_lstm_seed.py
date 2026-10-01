"""La semilla fija generadores e inicializacion del modelo."""

import random

import numpy as np
import pytest

tf = pytest.importorskip('tensorflow')
from src.detect.lstm import construir_modelo, fijar_semilla


def test_reinicia_los_tres_generadores():
    fijar_semilla(42)
    a = (random.random(), np.random.random(4), tf.random.uniform((4,)).numpy())
    fijar_semilla(42)
    b = (random.random(), np.random.random(4), tf.random.uniform((4,)).numpy())
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


def test_inicializacion_keras_repetible():
    tf.keras.backend.clear_session()
    fijar_semilla(42)
    pesos_a = construir_modelo(2, 3, unidades=4).get_weights()
    tf.keras.backend.clear_session()
    fijar_semilla(42)
    pesos_b = construir_modelo(2, 3, unidades=4).get_weights()
    for x, y in zip(pesos_a, pesos_b):
        np.testing.assert_array_equal(x, y)
