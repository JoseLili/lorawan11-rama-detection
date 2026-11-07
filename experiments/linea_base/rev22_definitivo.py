"""Modelo definitivo de la revisión 22: base × celda × semilla, con exactamente su E de la selección.

Uso: python rev22_definitivo.py <base> <celda> <semilla> [--hilos 4]
R: 2020–2022. M1: años extra + 2020–2022 mezclados. M2: años extra (E_A) y luego 2020–2022 (E_B, Adam 1e-4).
Modo `definitivo` de la revisión 14: todas las horas de 2020–2022, 1 de cada 8; escala a14 de 2020–2022.
Los lotes son los de `rev22_entrenar.Lotes` (misma clase, copiada sin cambios), con la clave [semilla, 22, 10 + etapa].
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('base')
ap.add_argument('celda')
ap.add_argument('semilla', type=int)
ap.add_argument('--hilos', type=int, default=4)
A = ap.parse_args()

import tensorflow as tf  # noqa: E402

tf.config.threading.set_intra_op_parallelism_threads(A.hilos)
tf.config.threading.set_inter_op_parallelism_threads(2)

import keras  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev22_comun as rc  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402


class Lotes(keras.utils.PyDataset):
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


def main():
    t0 = time.time()
    nm = rc.nombre_modelo(A.base, A.celda, A.semilla)
    sel = json.loads((rc.MOD / f'config_{nm}.json').read_text())
    g = rc.grupos_def()
    fondo, rec = rc.partes(A.base, g['fondo']), rc.partes(A.base, g['rec'])
    rc.DEF.mkdir(parents=True, exist_ok=True)
    keras.backend.clear_session()
    fijar_semilla(A.semilla)
    modelo = lr.construir_clasificador(n_features=17, unidades=64, salidas=1)
    cfg = dict(revision='22', fase='definitivo', modelo=nm, hilos=A.hilos, tensorflow=tf.__version__,
               keras=keras.__version__)
    if A.celda in ('R', 'M1'):
        tr = Lotes(fondo + rec if A.celda == 'M1' else rec, [A.semilla, 22, 10], True)
        h = modelo.fit(tr, epochs=sel['E'], verbose=2)
        cfg |= dict(ventanas=tr.n, epocas=sel['E'], loss=[float(x) for x in h.history['loss']])
    else:
        tra = Lotes(fondo, [A.semilla, 22, 11], True)
        ha = modelo.fit(tra, epochs=sel['E_A'], verbose=2)
        modelo.compile(optimizer=keras.optimizers.Adam(learning_rate=rc.LR_AFINAR), loss='binary_crossentropy')
        trb = Lotes(rec, [A.semilla, 22, 12], True)
        hb = modelo.fit(trb, epochs=sel['E_B'], verbose=2)
        cfg |= dict(ventanas_A=tra.n, ventanas_B=trb.n, epocas_A=sel['E_A'], epocas_B=sel['E_B'],
                    loss_A=[float(x) for x in ha.history['loss']], loss_B=[float(x) for x in hb.history['loss']])
    path = rc.DEF / f'{nm}.keras'
    modelo.save(path)
    cfg['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    cfg['segundos'] = round(time.time() - t0, 1)
    (rc.DEF / f'{nm}.json').write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg), flush=True)


if __name__ == '__main__':
    main()
