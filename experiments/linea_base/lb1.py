"""Revisión LB1: L0 reentrenado con la línea base Vb (anclada en vecinas) frente a V0 reentrenado.

Registro previo: docs/registro_previo_LB1_reentrenamiento_Vb.md (aprobado el 2026-11-04).
Sólo 2020–2022. Igual que la fase de selección de la revisión 14 (`entrenar_lstm_local.py`):
20 calendarios δ = 50 %, 1 de cada 8 horas de 2020–2021, validación con 1 de cada 8 horas de 2022
de los calendarios 01–10, EarlyStopping (paciencia 8, máximo 60), `fijar_semilla(42)` antes de
construir. La escala a14 se ajusta con 2020–2021 limpio con la base de cada modelo.

Uso (desde la raíz del repo, con data/raw/20RAMA.zip–22RAMA.zip):

    python experiments/linea_base/lb1.py --entrenar     # entrena V0r y Vbr (~30 min en CPU)
    python experiments/linea_base/lb1.py                # evalúa los modelos guardados

Salidas en results/linea_base/lb1/: modelo_<m>.keras, historia_<m>.csv, config_<m>.json,
metricas.csv (p99 y p99.9; V0r, Vbr y el L0 guardado) y bootstrap.csv (ΔF̄ Vbr − V0r).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comun as cm  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/lb1'
L0_GUARDADO = cm.SAL_RED / 'lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras'
MODELOS = {'V0r': 'V0', 'Vbr': 'Vb'}


def ejemplos(ctx, F, Y, pos, cada, uso, numero):
    X, y = [], []
    for j, s in enumerate(ctx['objetivos']):
        p = ll.muestra(pos, cada, uso, numero, j)
        X.append(cm.ventanas(ctx, F, s, p))
        y.append(Y[s].to_numpy(np.float32)[p])
    return np.concatenate(X), np.concatenate(y)


def escalas(ctx):
    b = cm.bases(ctx, ctx['limpia'])
    return {v: lb.escala_a14(ctx['limpia'], b[v], ctx['estaciones'], ctx['sigma'], ctx['vec'], cm.SELECCION[1])
            for v in ('V0', 'Vb')}


def entrenar(ctx):
    import keras
    import tensorflow as tf
    from entrenar_lstm_estacion import nuevo_modelo
    from entrenar_lstm_sup import CONFIG
    esc = escalas(ctx)
    assert np.abs(esc['V0'] - ctx['escala_v0']).max() == 0, 'la escala a14 de V0 no reproduce la del repo'
    nombres = [f'entrenamiento_{i:02d}_d50' for i in range(1, 21)]
    cm.asegurar_matrices(nombres)
    xs = {k: cm.leer(k) for k in nombres}
    bs = {k: cm.bases(ctx, x) for k, x in xs.items()}
    for mn, v in MODELOS.items():
        tr, va = [], []
        for i, k in enumerate(nombres, start=1):
            x = xs[k]
            Y = ed.etiquetas_por_hora(x, ctx['objetivos'])
            F = lb.entradas(x, bs[k][v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'])
            tr.append(ejemplos(ctx, F, Y, ctx['p_tr'], 8, 'seleccion', i))
            if i <= 10:
                va.append(ejemplos(ctx, F, Y, ctx['p_va'], 8, 'validacion', i))
        Xtr, ytr = np.concatenate([a for a, _ in tr]), np.concatenate([b for _, b in tr])
        Xva, yva = np.concatenate([a for a, _ in va]), np.concatenate([b for _, b in va])
        del tr, va
        print(f'{mn}: {len(ytr)} ventanas, {len(yva)} de validación, {100 * ytr.mean():.3f} % positivas', flush=True)
        modelo = nuevo_modelo(17, 1)
        parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                               restore_best_weights=True)
        h = modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=CONFIG['max_epocas'], batch_size=CONFIG['batch'],
                       shuffle=CONFIG['shuffle'], callbacks=[parada], verbose=2)
        hist = pd.DataFrame(h.history)
        hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
        SAL.mkdir(parents=True, exist_ok=True)
        hist.to_csv(SAL / f'historia_{mn}.csv')
        modelo.save(SAL / f'modelo_{mn}.keras')
        E = int(hist['val_loss'].to_numpy().argmin()) + 1
        (SAL / f'config_{mn}.json').write_text(json.dumps(dict(
            revision='LB1', modelo=mn, base=v, E=E, epocas=len(hist), val_loss_min=float(hist.val_loss.min()),
            ventanas=len(ytr), positivas_pct=float(100 * ytr.mean()), tensorflow=tf.__version__,
            keras=keras.__version__, origen='recién entrenado'), indent=2, ensure_ascii=False))
        print(f'{mn}: E = {E} de {len(hist)}', flush=True)
        del Xtr, ytr, Xva, yva, modelo


def evaluar(ctx):
    import keras
    esc = escalas(ctx)
    nombres = cm.nombres_eval()
    cm.asegurar_matrices(nombres)
    mods = {mn: keras.models.load_model(SAL / f'modelo_{mn}.keras', compile=False) for mn in MODELOS}
    mods['L0guardado'] = keras.models.load_model(L0_GUARDADO, compile=False)
    S, dias = {}, None
    cache = SAL / 'puntajes_2022.npz'
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        dias = pd.DatetimeIndex(z['dias'])
        S = {(mn, k): z[f'{mn}__{k}'] for mn in list(MODELOS) + ['L0guardado'] for k in nombres}
        print('puntajes leídos de', cache.name, flush=True)
    for k in ([] if cache.exists() else nombres):
        x = cm.leer(k)
        b = cm.bases(ctx, x)
        V = lb.valores(x, ctx['estaciones'])
        F = {v: lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'], V) for v in ('V0', 'Vb')}
        for mn, mdl in mods.items():
            dia = cm.puntuar(ctx, mdl, F[MODELOS.get(mn, 'V0')], x)
            S[(mn, k)] = dia.to_numpy()
            dias = dia.index
        print(f'  {k}: listo', flush=True)
    if not cache.exists():
        np.savez_compressed(cache, dias=dias.values.astype('datetime64[ns]'),
                            **{f'{mn}__{k}': v for (mn, k), v in S.items()})
        print('puntajes guardados en', cache.name, flush=True)
    print('etiquetas...', flush=True)
    lab = cm.etiquetas(ctx, dias)
    print('métricas...', flush=True)
    modelos = ['V0r', 'Vbr', 'L0guardado']
    met = pd.concat([cm.metricas(S, modelos, lab, nv) for nv in (0.01, 0.001)], ignore_index=True)
    met.to_csv(SAL / 'metricas.csv', index=False)
    print('bootstrap...', flush=True)
    boot = pd.DataFrame([dict(zip(('dFbar', 'ic_inf', 'ic_sup'),
                                  cm.bootstrap_dfbar(S, dias, 'Vbr', 'V0r', modelos, lab, nv)), nivel=nv)
                         for nv in (0.01, 0.001)])
    boot.to_csv(SAL / 'bootstrap.csv', index=False)
    print(met[['modelo', 'nivel', 'umbral', 'Fbar', 'F1_100', 'F1_50', 'F1_20', 'M1_50']].round(4).to_string(index=False))
    print(boot.round(4).to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--entrenar', action='store_true')
    args = ap.parse_args()
    ctx = cm.contexto()
    if args.entrenar:
        entrenar(ctx)
    evaluar(ctx)


if __name__ == '__main__':
    main()
