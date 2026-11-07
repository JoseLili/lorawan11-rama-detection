"""Puntaje diario de 2022 (promedio_dia, ≥ 12 h) de los 15 modelos de una base, en unas matrices.

Uso: python rev22_puntuar.py <base> <matriz1,matriz2,...> [--hilos 4] [--modelos DIR] [--salida DIR]
Igual que `comun.puntuar`, pero construye las ventanas una vez por matriz para todos los modelos.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('base')
ap.add_argument('matrices')
ap.add_argument('--hilos', type=int, default=4)
ap.add_argument('--modelos', default='')
ap.add_argument('--salida', default='')
A = ap.parse_args()

import tensorflow as tf  # noqa: E402

tf.config.threading.set_intra_op_parallelism_threads(A.hilos)
tf.config.threading.set_inter_op_parallelism_threads(2)

import keras  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun as cm  # noqa: E402
import rev22_comun as rc  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402


def puntuar_varios(ctx, modelos: dict, F, x) -> dict:
    pos, obj = ctx['p_va'], ctx['objetivos']
    X = np.concatenate([cm.ventanas(ctx, F, s, pos) for s in obj])
    ix = x.index[pos]
    con = x.loc[ix, [f'{s}_mascara' for s in obj]].to_numpy() == 1
    out, dias = {}, None
    for nm, mdl in modelos.items():
        p = mdl.predict(X, batch_size=8192, verbose=0).astype(np.float64).reshape(len(obj), len(pos)).T
        dia = ed.juntar_dia(pd.DataFrame(p, index=ix, columns=obj).where(con), 'promedio_dia')
        out[nm], dias = dia.to_numpy(), dia.index
    return out, dias


def main():
    t0 = time.time()
    dmod = Path(A.modelos) if A.modelos else rc.MOD
    dsal = Path(A.salida) if A.salida else rc.PUN
    dsal.mkdir(parents=True, exist_ok=True)
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'seleccion')
    mods = {p.stem: keras.models.load_model(p, compile=False) for p in sorted(dmod.glob(f'{A.base}_*.keras'))}
    for k in A.matrices.split(','):
        x = cm.leer(k)
        b = cm.bases(ctx, x)[A.base]
        F = lb.entradas(x, b, ctx['estaciones'], ctx['sigma'], esc[A.base], ctx['vec'])
        S, dias = puntuar_varios(ctx, mods, F, x)
        np.savez_compressed(dsal / f'{A.base}__{k}.npz', dias=dias.values.astype('datetime64[ns]'), **S)
        print(f'{A.base} {k}: {len(mods)} modelos, {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main()
