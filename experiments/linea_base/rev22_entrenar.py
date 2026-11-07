"""Un entrenamiento de selección de la revisión 22: base × celda × semilla.

Uso: python rev22_entrenar.py <base> <celda> <semilla> [--hilos 4] [--limite N] [--salida DIR]

- R: sólo 2020–2021. M1: años extra + 2020–2021 mezclados. M2: preentrenar con los años extra
  y afinar con 2020–2021 (Adam 1e-4). EarlyStopping sobre val_loss de 2022, paciencia 3.
- Las ventanas se leen de disco (memmap) en lotes de 64, barajadas por época con la semilla.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('base')
ap.add_argument('celda')
ap.add_argument('semilla', type=int)
ap.add_argument('--hilos', type=int, default=4)
ap.add_argument('--limite', type=int, default=0, help='sólo para la prueba de la tubería')
ap.add_argument('--max-epocas', type=int, default=60)
ap.add_argument('--salida', default='')
A = ap.parse_args()

import tensorflow as tf  # noqa: E402

tf.config.threading.set_intra_op_parallelism_threads(A.hilos)
tf.config.threading.set_inter_op_parallelism_threads(2)

import keras  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev22_comun as rc  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402


class Lotes(keras.utils.PyDataset):
    """Lotes de varias partes en disco; permutación nueva en cada época, con clave [semilla, 22, etapa, época]."""

    def __init__(self, partes, clave, barajar, batch=64, limite=0):
        super().__init__(workers=1, use_multiprocessing=False, max_queue_size=16)
        self.X = [p[0] for p in partes]
        self.y = [p[1] for p in partes]
        self.off = np.cumsum([0] + [len(a) for a in self.y])
        self.n = int(self.off[-1])
        self.clave, self.barajar, self.batch, self.epoca = clave, barajar, batch, 0
        self.sub = np.random.default_rng([*clave, 999]).choice(self.n, limite, replace=False) if limite else None
        self._orden()

    def _orden(self):
        base = self.sub if self.sub is not None else np.arange(self.n)
        self.ix = np.random.default_rng([*self.clave, self.epoca]).permutation(base) if self.barajar else base

    def __len__(self):
        return int(np.ceil(len(self.ix) / self.batch))

    def __getitem__(self, i):
        b = np.sort(self.ix[i * self.batch:(i + 1) * self.batch])
        parte = np.searchsorted(self.off, b, side='right') - 1
        X = np.empty((len(b), 24, 17), np.float32)
        y = np.empty(len(b), np.float32)
        for p in np.unique(parte):
            m = parte == p
            loc = b[m] - self.off[p]
            X[m], y[m] = self.X[p][loc], self.y[p][loc]
        return X, y

    def on_epoch_end(self):
        self.epoca += 1
        self._orden()


def ajustar(modelo, tr, va):
    parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=rc.PACIENCIA, min_delta=0,
                                           restore_best_weights=True)
    h = modelo.fit(tr, validation_data=va, epochs=A.max_epocas, callbacks=[parada], verbose=2)
    hist = pd.DataFrame(h.history)
    hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
    return hist


def main():
    t0 = time.time()
    g = rc.grupos()
    salida = Path(A.salida) if A.salida else rc.MOD
    salida.mkdir(parents=True, exist_ok=True)
    nm = rc.nombre_modelo(A.base, A.celda, A.semilla)
    fondo, rec, val = rc.partes(A.base, g['fondo']), rc.partes(A.base, g['rec']), rc.partes(A.base, g['val'])
    lim_va = A.limite // 4 if A.limite else 0
    va = Lotes(val, [A.semilla, 22, 9], False, batch=2048, limite=lim_va)
    keras.backend.clear_session()
    fijar_semilla(A.semilla)
    modelo = lr.construir_clasificador(n_features=17, unidades=64, salidas=1)
    cfg = dict(revision='22', modelo=nm, base=A.base, celda=A.celda, semilla=A.semilla, hilos=A.hilos,
               paciencia=rc.PACIENCIA, tensorflow=tf.__version__, keras=keras.__version__, limite=A.limite)
    if A.celda in ('R', 'M1'):
        tr = Lotes(fondo + rec if A.celda == 'M1' else rec, [A.semilla, 22, 0], True, limite=A.limite)
        hist = ajustar(modelo, tr, va)
        hist.to_csv(salida / f'historia_{nm}.csv')
        cfg |= dict(ventanas=tr.n, E=int(hist.val_loss.to_numpy().argmin()) + 1, epocas=len(hist),
                    val_loss_min=float(hist.val_loss.min()))
    else:
        tra = Lotes(fondo, [A.semilla, 22, 1], True, limite=A.limite)
        ha = ajustar(modelo, tra, va)
        ha.to_csv(salida / f'historia_{nm}_A.csv')
        modelo.compile(optimizer=keras.optimizers.Adam(learning_rate=rc.LR_AFINAR), loss='binary_crossentropy')
        trb = Lotes(rec, [A.semilla, 22, 2], True, limite=A.limite)
        hb = ajustar(modelo, trb, va)
        hb.to_csv(salida / f'historia_{nm}_B.csv')
        cfg |= dict(ventanas_A=tra.n, ventanas_B=trb.n,
                    E_A=int(ha.val_loss.to_numpy().argmin()) + 1, epocas_A=len(ha),
                    E_B=int(hb.val_loss.to_numpy().argmin()) + 1, epocas_B=len(hb),
                    val_loss_min_A=float(ha.val_loss.min()), val_loss_min=float(hb.val_loss.min()))
    modelo.save(salida / f'{nm}.keras')
    cfg['segundos'] = round(time.time() - t0, 1)
    (salida / f'config_{nm}.json').write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg), flush=True)


if __name__ == '__main__':
    main()
