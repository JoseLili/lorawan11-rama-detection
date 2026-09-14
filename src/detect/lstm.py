"""Modelo LSTM para prediccion de una estacion a partir de sus vecinas.

La deteccion se basa en el residuo: si el valor observado se aparta
sustancialmente del predicho, la lectura es candidata a manipulacion.

El modelo se entrena UNICAMENTE con trafico legitimo. No ve ataques
durante el entrenamiento.
"""

from __future__ import annotations

import numpy as np
from tensorflow import keras
from tensorflow.keras import layers


def construir_modelo(ventana: int, n_features: int, unidades: int = 64):
    """LSTM de una capa para regresion."""
    modelo = keras.Sequential([
        layers.Input(shape=(ventana, n_features)),
        layers.LSTM(unidades),
        layers.Dropout(0.2),
        layers.Dense(32, activation='relu'),
        layers.Dense(1),
    ])
    modelo.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss='mse',            # error cuadratico medio
        metrics=['mae'],       # error absoluto medio, en ppb
    )
    return modelo


def entrenar(modelo, X, y, val_frac=0.2, epocas=50, batch=64, verbose=1):
    """Entrena con corte de validacion CRONOLOGICO.

    Keras por defecto toma el ultimo `val_frac` sin barajar cuando se usa
    validation_split, lo cual es correcto para series temporales. Se hace
    explicito para que la decision quede documentada.
    """
    n = int(len(X) * (1 - val_frac))
    parada = keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=8, restore_best_weights=True
    )
    return modelo.fit(
        X[:n], y[:n],
        validation_data=(X[n:], y[n:]),
        epochs=epocas, batch_size=batch,
        callbacks=[parada], verbose=verbose,
    )