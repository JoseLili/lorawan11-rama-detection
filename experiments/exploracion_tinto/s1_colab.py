"""S1: CNN compartida + LSTM de dos bloques; protocolo temporal §14. Derivado de t2_colab.py, sin modificar T2."""
import argparse
import json
import os
from pathlib import Path
import platform
import random
import time

import numpy as np
import pandas as pd

V = 1                      # horas por ventana
MIN_HORAS = 12              # estacion_dia.MIN_HORAS
DIA0_2022 = 731             # 2020 y 2020-2021 suman 731 días
CONFIG = dict(batch=64, max_epocas=60, paciencia=8, lr=1e-3, semilla=42)


def fijar_semilla(seed=42):
    """Copia de src/detect/lstm.py: llamar antes de construir y antes de entrenar."""
    import tensorflow as tf
    import keras
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()


def leer(p):
    return np.load(p, allow_pickle=False)


def mapa(paquete, red):
    m = pd.read_csv(paquete / 'mapa_S1.csv')
    e = pd.read_csv(paquete / 'escalador_S1.csv')
    assert m.feature.tolist() == e.feature.tolist()
    lado = 64 if red else 32
    n = len(m)
    assert n == 17
    src = np.full(lado * lado, n, dtype=np.int32)          # n = píxel vacío (cero)
    src[m.row.to_numpy() * lado + m.column.to_numpy()] = np.arange(n)
    assert (src < n).sum() == n
    return lado, src, e.scale.to_numpy(np.float64), e.offset.to_numpy(np.float64)


def hacer_imagenes_bloque(red, lado, src, scale, offset, local):
    """Función (F, c, t, j) → imágenes; F es (calendarios, horas, 98) y t la hora final de la ventana."""
    import tensorflow as tf
    tf_local, tf_src = tf.constant(local), tf.constant(src)
    tf_scale, tf_offset = tf.constant(scale), tf.constant(offset)
    lags = tf.range(-V + 1, 1, dtype=tf.int32)

    def imagenes(F, c, t, j):
        """Ventanas (B, 24, 98) → columnas de la variante → escala MinMax → imagen (B, lado, lado, 1)."""
        rows = t[:, None] + lags[None, :]
        W = tf.gather_nd(F, tf.stack([tf.broadcast_to(c[:, None], tf.shape(rows)), rows], -1))
        if not red:
            W = tf.gather(W, tf.gather(tf_local, j), axis=2, batch_dims=1)
        x = tf.cast(tf.cast(tf.reshape(W, [tf.shape(W)[0], -1]), tf.float64) * tf_scale + tf_offset, tf.float32)
        x = tf.concat([x, tf.zeros_like(x[:, :1])], 1)
        return tf.reshape(tf.gather(x, tf_src, axis=1), [-1, lado, lado, 1])
    return imagenes


def hacer_imagenes(red, lado, src, scale, offset, local):
    import tensorflow as tf
    block=hacer_imagenes_bloque(red,lado,src,scale,offset,local)
    def sequence(F,c,t,j):
        times=tf.reshape(t[:,None]+tf.range(-23,1,dtype=tf.int32)[None,:],[-1])
        images=block(F,tf.repeat(c,24),times,tf.repeat(j,24))
        return tf.reshape(images,[-1,24,lado,lado,1])
    return sequence


def validos_dia(obs):
    """(días, 31): la estación tiene al menos 12 horas con dato ese día."""
    return obs.reshape(-1, 24, obs.shape[1]).sum(axis=1) >= MIN_HORAS


def ejemplos(var, paq, meta, nums, split, prueba):
    """Índices (calendario, t, objetivo) y etiquetas; t es la hora final de la ventana."""
    obs=leer(paq/'obs.npy');valid=validos_dia(obs)
    days=np.arange(0 if split=='tr' else 731,731 if split=='tr' else 1096)
    rows=[];ys=[]
    for k,n in enumerate(nums):
        Y=leer(paq/f'Ydia_entrenamiento_{n:02d}.npy')
        dd,jj=np.nonzero(valid[days]);d=days[dd]
        rows.append(np.stack([np.full(len(d),k),d*24+23,jj],axis=1))
        ys.append(Y[d,jj].astype(np.float32))
    idx,y=np.concatenate(rows).astype(np.int32),np.concatenate(ys)
    if prueba:
        ids=np.sort(np.random.default_rng([42,30,3]).choice(len(y),min(3000,len(y)),replace=False));idx,y=idx[ids],y[ids]
    return idx,y


def construir(lado, salidas):
    import keras
    from keras import layers
    encoder = keras.Sequential([layers.Input((lado,lado,1)),layers.Conv2D(8,3,padding='same',activation='relu'),
        layers.MaxPool2D(2),layers.Conv2D(16,3,padding='same',activation='relu'),layers.MaxPool2D(2),
        layers.Flatten(),layers.Dense(32,activation='relu'),layers.Dropout(.2)],name='cnn_compartida')
    model = keras.Sequential([layers.Input((24,lado,lado,1)),layers.TimeDistributed(encoder),
        layers.LSTM(32,activation='tanh',recurrent_activation='sigmoid',dropout=0.,recurrent_dropout=0.,use_cudnn=False),
        layers.Dense(1,activation='sigmoid')])
    return model


def bce_enmascarada(y, p):
    """Entropía cruzada por salida; las etiquetas −1 (estación-día sin 12 horas) no cuentan."""
    import tensorflow as tf
    m = tf.cast(y >= 0, p.dtype)
    yy = tf.maximum(y, 0.)
    pc = tf.clip_by_value(p, 1e-7, 1 - 1e-7)
    b = -(yy * tf.math.log(pc) + (1 - yy) * tf.math.log(1 - pc))
    return tf.reduce_sum(m * b, axis=-1) / tf.maximum(tf.reduce_sum(m, axis=-1), 1.)


def main(a):
    import tensorflow as tf
    import keras
    for g in tf.config.list_physical_devices('GPU'):
        tf.config.experimental.set_memory_growth(g, True)
    paq, var, out = a.paquete, a.variante, a.salida
    out.mkdir(parents=True)
    meta = json.loads((paq / 'meta.json').read_text())
    red = var in ('RH', 'RD')
    lado, src, scale, offset = mapa(paq, red)
    local = np.array(meta['indices_locales'], dtype=np.int32)
    nums_tr, nums_va = meta['calendarios_ajuste'], meta['calendarios_validacion']
    started = time.time()
    info = dict(variante=var, corrida=a.corrida, prueba=a.prueba, config=CONFIG, lado=lado,
                python=platform.python_version(), tensorflow=tf.__version__, keras=keras.__version__,
                gpu=[d.name for d in tf.config.list_physical_devices('GPU')],
                origen='CNN–LSTM recién entrenada en Colab; GPU autorizada; determinismo habilitado y verificación requerida')
    try:
        info['gpu_nombre'] = tf.config.experimental.get_device_details(tf.config.list_physical_devices('GPU')[0]).get('device_name')
    except Exception:
        pass
    (out / 'configuracion.json').write_text(json.dumps(info, indent=1) + '\n')

    # Las 98 columnas de los calendarios d50 (ajuste y validación), en memoria de la CPU.
    Ftr = tf.constant(np.stack([leer(paq / f'F_entrenamiento_{n:02d}_d50.npy') for n in nums_tr]))
    imagenes = hacer_imagenes(red, lado, src, scale, offset, local)

    def dataset(idx, y, train):
        ds = tf.data.Dataset.from_tensor_slices((idx, y))
        if train:
            ds = ds.shuffle(len(y), seed=CONFIG['semilla'], reshuffle_each_iteration=True)
        ds = ds.batch(CONFIG['batch'] if train else 128)
        ds = ds.map(lambda i, yy: (imagenes(Ftr, i[:, 0], i[:, 1], i[:, 2]), yy), num_parallel_calls=tf.data.AUTOTUNE)
        return ds.prefetch(tf.data.AUTOTUNE)

    itr, ytr = ejemplos(var, paq, meta, nums_tr, 'tr', a.prueba)
    iva, yva = ejemplos(var, paq, meta, nums_va, 'va', a.prueba)
    # El índice de calendario es la posición en la lista; la validación usa los primeros de Ftr.
    assert nums_va == nums_tr[:len(nums_va)]
    pos = lambda y: float(np.mean(y[y >= 0])) if y.ndim == 1 else float(y[y >= 0].mean())
    info.update(ejemplos_ajuste=len(ytr), ejemplos_validacion=len(yva), positivas_ajuste=pos(ytr),
                positivas_validacion=pos(yva))
    print(json.dumps({k: info[k] for k in ['variante', 'ejemplos_ajuste', 'ejemplos_validacion',
                                            'positivas_ajuste', 'gpu']}), flush=True)

    keras.backend.clear_session()
    fijar_semilla(CONFIG['semilla'])
    salidas = 31 if red else 1
    model = construir(lado, salidas)
    model.compile(optimizer=keras.optimizers.Adam(CONFIG['lr']),
                  loss=bce_enmascarada if red else 'binary_crossentropy',
                  steps_per_execution=32)   # varios lotes por llamada: mismos pasos, menos espera
    info['parametros'] = model.count_params()
    best = out / 'modelo_mejor.keras'
    callbacks = [keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0),
                 keras.callbacks.ModelCheckpoint(best, monitor='val_loss', save_best_only=True),
                 keras.callbacks.CSVLogger(out / 'historia.csv')]
    fijar_semilla(CONFIG['semilla'])
    h = model.fit(dataset(itr, ytr, True), validation_data=dataset(iva, yva, False),
                  epochs=2 if a.prueba else CONFIG['max_epocas'], callbacks=callbacks, verbose=2)
    hist = pd.DataFrame(h.history)
    E = int(hist.val_loss.to_numpy().argmin()) + 1
    info.update(epocas=len(hist), epoca_mejor=E, val_loss_mejor=float(hist.val_loss.min()),
                paro_por_paciencia=len(hist) < (2 if a.prueba else CONFIG['max_epocas']),
                minutos_entrenamiento=(time.time() - started) / 60)
    del Ftr
    model = keras.models.load_model(best, custom_objects={'bce_enmascarada': bce_enmascarada}, compile=False)
    predict = tf.function(lambda x: model(x, training=False))

    # Puntajes 2022 por estación-día en las 31 matrices de evaluación.
    obs = leer(paq / 'obs.npy')
    horas = np.arange(24 * DIA0_2022, obs.shape[0])
    if a.prueba:
        horas = horas[:48]
    dias = horas[23::24]
    ok = validos_dia(obs[horas])
    claves = ['limpia_2022'] + [f'entrenamiento_{n:02d}_d{d}' for d in (100, 50, 20) for n in range(1, 11)]
    if a.prueba:
        claves = claves[:2]
    puntajes = {}
    for clave in claves:
        F = tf.constant(leer(paq / ('F_limpia_2020_2022.npy' if clave == 'limpia_2022' else f'F_{clave}.npy'))[None])
        t_fin = dias
        P = np.zeros((len(t_fin), 31), dtype=np.float64)
        for j in (range(31) if not red else [0]):
            for s in range(0, len(t_fin), 128):
                t = tf.constant(t_fin[s:s + 128], tf.int32)
                z = tf.zeros_like(t)
                p = predict(imagenes(F, z, t, z + j)).numpy()
                if red:
                    P[s:s + len(t)] = p
                else:
                    P[s:s + len(t), j] = p[:, 0]
        assert np.isfinite(P).all()
        D = P
        puntajes[clave] = np.where(ok, D, np.nan)
        print(clave, 'puntuada', flush=True)
    np.savez_compressed(out / 'puntajes_dia_2022.npz', **puntajes)
    info.update(minutos_total=(time.time() - started) / 60, matrices_puntuadas=len(puntajes))
    (out / 'resultado.json').write_text(json.dumps(info, indent=1) + '\n')
    (out / 'LISTO').write_text('ok\n')
    print('LISTO', json.dumps({k: info[k] for k in ['variante', 'corrida', 'epocas', 'epoca_mejor',
                                                     'val_loss_mejor', 'minutos_total']}), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--paquete', type=Path, required=True)
    ap.add_argument('--variante', choices=['S1'], required=True)
    ap.add_argument('--corrida', type=int, default=1)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--prueba', action='store_true')
    a = ap.parse_args()
    if a.salida.exists():
        ap.error('Usa una carpeta nueva.')
    main(a)
