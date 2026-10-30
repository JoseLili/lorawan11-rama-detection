"""PARAAD-SA adaptado a faltantes RAMA (revisión 20).

Arquitectura contrastada con XhensildaAllka/PARAAD@6dbb5a9. Atención aditiva
equivalente a la configuración de SeqSelfAttention (CyberZHG, commit f3bf21d),
implementada con operaciones TensorFlow actuales; no requiere esa dependencia.
Ejes siempre (día, sensor, hora). No carga datos, modelos ni años implícitamente.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras

from src.detect.multianual import ESTACIONES

SENSORES = tuple(s for s in ESTACIONES if s != 'XAL')
OBJETIVOS = tuple(s for s in SENSORES if s != 'HGM')


def ajustar_escala(x: pd.DataFrame) -> pd.DataFrame:
    """El llamador proporciona exclusivamente el periodo de ajuste permitido."""
    x = x.loc[:, list(SENSORES)]
    mu, sigma = x.mean(), x.std(ddof=1).replace(0, 1)
    if not np.isfinite(mu).all() or not np.isfinite(sigma).all():
        raise ValueError('sensor sin suficientes observaciones en el ajuste')
    return pd.DataFrame({'media': mu, 'desv': sigma})


def bloques(x: pd.DataFrame, escala: pd.DataFrame):
    """Devuelve valores neutrales, máscara aparte y fechas; nunca interpola."""
    if (x.empty or x.index.has_duplicates or x.index[0].hour != 0
            or x.index[-1].hour != 23 or len(x) % 24
            or not x.index.equals(pd.date_range(x.index[0], x.index[-1], freq='h'))):
        raise ValueError('se requiere rejilla horaria continua de días completos')
    if tuple(escala.index) != SENSORES:
        raise ValueError('orden de escala distinto del orden fijo de sensores')
    if not np.isfinite(escala.to_numpy()).all() or (escala.desv <= 0).any():
        raise ValueError('escala no finita o desviación no positiva')
    a = x.loc[:, list(SENSORES)].to_numpy(dtype=np.float64)
    if np.isinf(a).any():
        raise ValueError('hay infinitos en los datos')
    m = np.isfinite(a)
    z = np.where(m, (a - escala.media.to_numpy()) / escala.desv.to_numpy(), 0)
    z = z.reshape(-1, 24, len(SENSORES)).transpose(0, 2, 1).astype('float32')
    m = m.reshape(-1, 24, len(SENSORES)).transpose(0, 2, 1)
    return z, m, x.index[::24]


def objetivos_perdida(z, mascara):
    return np.concatenate([z, mascara.astype('float32')], axis=-1)


@keras.utils.register_keras_serializable(package='rama_paraad')
def mse_observada(y_true, y_pred):
    """Una MSE por bloque, normalizada sólo por sus celdas observadas."""
    z, m = y_true[..., :24], y_true[..., 24:]
    return tf.math.divide_no_nan(tf.reduce_sum(tf.square(z - y_pred) * m, axis=(1, 2)),
                                 tf.reduce_sum(m, axis=(1, 2)))


@keras.utils.register_keras_serializable(package='rama_paraad')
class AtencionSA(keras.layers.Layer):
    """Sigmoid de emisiones aditivas seguido de softmax local, como SA público."""
    def __init__(self, ancho, unidades=32, **kwargs):
        super().__init__(**kwargs)
        self.ancho, self.unidades = int(ancho), int(unidades)

    def build(self, shape):
        def peso(nombre, dims, init):
            return self.add_weight(name=nombre, shape=dims, initializer=init)
        self.wt = peso('wt', (shape[-1], self.unidades), 'glorot_normal')
        self.wx = peso('wx', (shape[-1], self.unidades), 'glorot_normal')
        self.bh = peso('bh', (self.unidades,), 'zeros')
        self.wa = peso('wa', (self.unidades, 1), 'glorot_normal')
        self.ba = peso('ba', (1,), 'zeros')
        super().build(shape)

    def call(self, x):
        q, k = tf.matmul(x, self.wt), tf.matmul(x, self.wx)
        h = tf.tanh(q[:, :, None, :] + k[:, None, :, :] + self.bh)
        e = tf.sigmoid(tf.squeeze(tf.matmul(h, self.wa) + self.ba, axis=-1))
        i = tf.range(tf.shape(x)[1])
        inferior = i[:, None] - self.ancho // 2
        dentro = (i[None, :] >= inferior) & (i[None, :] < inferior + self.ancho)
        e = e - tf.cast(~dentro, e.dtype) * 10000
        return tf.matmul(tf.nn.softmax(e, axis=-1), x)

    def get_config(self):
        return {**super().get_config(), 'ancho': self.ancho, 'unidades': self.unidades}


def construir_modelo(dropout=0.1, sensores=32):
    """Llamar fijar_semilla(42) inmediatamente antes de esta función."""
    x = keras.Input((sensores, 24), name='dia_sensor_hora')
    y = keras.layers.Dropout(dropout, seed=42)(x)
    y = AtencionSA(24)(y)
    y = keras.layers.Bidirectional(keras.layers.LSTM(7, activation='linear', return_sequences=True))(y)
    y = keras.layers.Bidirectional(keras.layers.LSTM(2, activation='relu'))(y)
    y = keras.layers.RepeatVector(sensores)(y)
    y = AtencionSA(4)(y)
    y = keras.layers.Bidirectional(keras.layers.LSTM(7, activation='linear', return_sequences=True))(y)
    y = keras.layers.TimeDistributed(keras.layers.Dense(24))(y)
    modelo = keras.Model(x, y, name='paraad_sa_rama')
    modelo.compile(optimizer=keras.optimizers.Adam(0.01, clipnorm=1), loss=mse_observada)
    return modelo


def reconstruir(modelo, z, batch=256):
    p = np.concatenate([modelo(z[i:i+batch], training=False).numpy()
                        for i in range(0, len(z), batch)])
    if not np.isfinite(p).all():
        raise ValueError('reconstrucción no finita')
    return p


def puntajes(z, m, reconstruccion, dias, min_horas=12):
    if z.shape != m.shape or z.shape != reconstruccion.shape:
        raise ValueError('formas incompatibles')
    n = m.sum(axis=-1)
    error = np.where(m, np.abs(z.astype('float64') - reconstruccion), 0).sum(axis=-1)
    s = np.divide(error, n, out=np.full(n.shape, np.nan), where=n >= min_horas)
    return pd.DataFrame(s, index=dias, columns=SENSORES).loc[:, list(OBJETIVOS)]


def exigir_comunes(puntaje, comunes):
    """Falla si cambia el universo; nunca elimina filas silenciosamente."""
    if not puntaje.index.equals(comunes.index) or not puntaje.columns.equals(comunes.columns):
        raise ValueError('índices de estación-día distintos')
    if comunes.isna().any().any() or not all(t == bool for t in comunes.dtypes):
        raise ValueError('máscara común debe ser booleana sin faltantes')
    if not np.isfinite(puntaje.to_numpy()[comunes.to_numpy()]).all():
        raise ValueError('PARAAD no cubre todas las estación-días comunes')
    return puntaje.where(comunes)
