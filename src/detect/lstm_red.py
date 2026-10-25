"""LSTM supervisado de red del protocolo `anomalias_red_v1` (revisiones 6 y 7).

Cada ejemplo es la ventana de las horas t−23…t de la matriz de red, con las 66 columnas de
`evaluacion_red.entradas_de` (crudas o relativas al perfil), y su respuesta es la etiqueta de red
de la hora t. A diferencia del V4, la ventana incluye la hora t y a la propia estación alterada.
La etiqueta nunca es entrada. La historia previa se antepone con `evaluacion_red.con_historia`.
No entrena por sí mismo: el entrenamiento está en `experiments/anomalias_red/entrenar_lstm_sup.py`.
"""
from __future__ import annotations

import numpy as np

VENTANA = 24


def ventanas(F: np.ndarray, posiciones: np.ndarray, ventana: int = VENTANA) -> np.ndarray:
    """(n, ventana, columnas): para cada posición t, las filas t − ventana + 1 … t de F."""
    posiciones = np.asarray(posiciones)
    if len(posiciones) and (posiciones.min() < ventana - 1 or posiciones.max() >= len(F)):
        raise ValueError('hay posiciones sin ventana completa')
    return F[posiciones[:, None] + np.arange(-ventana + 1, 1)[None, :]]


def construir_clasificador(ventana: int = VENTANA, n_features: int = 66, unidades: int = 64, salidas: int = 1):
    """La arquitectura del V4 (`lstm.construir_modelo`) con salida de probabilidad.

    `salidas` = 1: la etiqueta de red (revisiones 6–10); 31: una por estación (revisión 13).
    Llamar `fijar_semilla(42)` inmediatamente antes (CLAUDE.md).
    """
    from tensorflow import keras
    from tensorflow.keras import layers
    modelo = keras.Sequential([
        layers.Input(shape=(ventana, n_features)),
        layers.LSTM(unidades),
        layers.Dropout(0.2),
        layers.Dense(32, activation='relu'),
        layers.Dense(salidas, activation='sigmoid'),
    ])
    modelo.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss='binary_crossentropy')
    return modelo
