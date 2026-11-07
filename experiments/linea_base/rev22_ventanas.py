"""Construye un grupo de ventanas de la revisión 22 (selección) y lo guarda en disco.

Uso: python rev22_ventanas.py <grupo>, con grupo = fondo_<año> | rec_<a>_<b> | val_<a>_<b>.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun as cm  # noqa: E402
import numpy as np
import pandas as pd
import rev22_comun as rc


def main(grupo: str):
    t0 = time.time()
    ctx = cm.contexto()
    definitivo = grupo.startswith('def')
    esc = rc.escalas(ctx, 'definitivo' if definitivo else 'seleccion')
    uso = 'definitivo' if definitivo else 'seleccion'
    obj = ctx['objetivos']
    out = []
    if grupo.startswith('defrec_'):
        _, a, b = grupo.split('_')
        cm.asegurar_matrices([f'entrenamiento_{i:02d}_d50' for i in range(int(a), int(b) + 1)])
        todas = np.arange(23, len(ctx['limpia']))
        for i in range(int(a), int(b) + 1):
            x = cm.leer(f'entrenamiento_{i:02d}_d50')
            out.append(rc.ventanas_de(ctx, x, esc, todas, 'definitivo', i, obj))
    elif grupo.startswith(('fondo_', 'deffondo_')):
        y = int(grupo.split('_')[1])
        validos = rc.elegibles()[y]
        v = rc.valores(f'{y - 1}-10-01', f'{y}-12-31 23:00')
        for k in range(1, rc.N_FONDO + 1):
            x = rc.matriz_fondo(y, k, v)
            idx = x.index
            pos = np.flatnonzero(idx >= pd.Timestamp(f'{y}-01-01'))
            pos = pos[pos >= 23]
            out.append(rc.ventanas_de(ctx, x, esc, pos, uso, y * 1000 + rc.NUM0 + k, validos))
    else:
        tipo, a, b = grupo.split('_')
        nombres = [f'entrenamiento_{i:02d}_d50' for i in range(int(a), int(b) + 1)]
        cm.asegurar_matrices(nombres)
        for i in range(int(a), int(b) + 1):
            x = cm.leer(f'entrenamiento_{i:02d}_d50')
            if tipo == 'rec':
                out.append(rc.ventanas_de(ctx, x, esc, ctx['p_tr'], 'seleccion', i, obj))
            else:
                out.append(rc.ventanas_de(ctx, x, esc, ctx['p_va'], 'validacion', i, obj))
    info = rc.guardar_ventanas(grupo, out)
    info['segundos'] = round(time.time() - t0, 1)
    (rc.VEN / f'{grupo}.json').write_text(json.dumps(info, indent=2))
    print(grupo, json.dumps(info), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
