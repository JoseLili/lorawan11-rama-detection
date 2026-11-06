"""Revisión LB2: semillas 1–4 de V0r y Vbr (más la 42 de LB1) y el ensamble de las 5, evaluados en 2022.

Registro previo: docs/registro_previo_LB2_semillas_ensamble.md (aprobado el 2026-11-04).
Igual que lb1.py; sólo cambia `fijar_semilla(s)` antes de construir cada modelo. Las ventanas de
entrenamiento son las mismas para todas las semillas (lstm_local.muestra con semilla 42).

Uso:  python experiments/linea_base/lb2.py            → entrena lo que falte y evalúa
Salidas en results/linea_base/lb2/: modelo_<m>_s<s>.keras, historia_*, config_*, puntajes_2022.npz,
metricas.csv, bootstrap.csv y por_semilla.csv.
"""
from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comun as cm  # noqa: E402
import lb1  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/lb2'
SEMILLAS_NUEVAS = (1, 2, 3, 4)
SEMILLAS = (42,) + SEMILLAS_NUEVAS
BASES = {'V0r': 'V0', 'Vbr': 'Vb'}


def ruta_modelo(mn, s):
    return lb1.SAL / f'modelo_{mn}.keras' if s == 42 else SAL / f'modelo_{mn}_s{s}.keras'


def entrenar(ctx):
    import keras
    import tensorflow as tf
    from entrenar_lstm_sup import CONFIG
    from src.detect import lstm_red as lr
    from src.detect.lstm import fijar_semilla
    esc = lb1.escalas(ctx)
    nombres = [f'entrenamiento_{i:02d}_d50' for i in range(1, 21)]
    cm.asegurar_matrices(nombres)
    SAL.mkdir(parents=True, exist_ok=True)
    for mn, v in BASES.items():
        faltan = [s for s in SEMILLAS_NUEVAS if not ruta_modelo(mn, s).exists()]
        if not faltan:
            continue
        tr, va = [], []
        for i, k in enumerate(nombres, start=1):
            x = cm.leer(k)
            Y = ed.etiquetas_por_hora(x, ctx['objetivos'])
            F = lb.entradas(x, cm.bases(ctx, x)[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'])
            tr.append(lb1.ejemplos(ctx, F, Y, ctx['p_tr'], 8, 'seleccion', i))
            if i <= 10:
                va.append(lb1.ejemplos(ctx, F, Y, ctx['p_va'], 8, 'validacion', i))
        Xtr, ytr = np.concatenate([a for a, _ in tr]), np.concatenate([b for _, b in tr])
        Xva, yva = np.concatenate([a for a, _ in va]), np.concatenate([b for _, b in va])
        del tr, va
        gc.collect()
        print(f'{mn}: {len(ytr)} ventanas, {len(yva)} de validación', flush=True)
        for s in faltan:
            keras.backend.clear_session()
            fijar_semilla(s)
            modelo = lr.construir_clasificador(n_features=17, unidades=CONFIG['unidades'], salidas=1)
            parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                                   restore_best_weights=True)
            h = modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=CONFIG['max_epocas'],
                           batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], callbacks=[parada], verbose=2)
            hist = pd.DataFrame(h.history)
            hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
            hist.to_csv(SAL / f'historia_{mn}_s{s}.csv')
            modelo.save(ruta_modelo(mn, s))
            E = int(hist['val_loss'].to_numpy().argmin()) + 1
            (SAL / f'config_{mn}_s{s}.json').write_text(json.dumps(dict(
                revision='LB2', modelo=mn, base=v, semilla=s, E=E, epocas=len(hist),
                val_loss_min=float(hist.val_loss.min()), tensorflow=tf.__version__, keras=keras.__version__,
                origen='recién entrenado'), indent=2))
            print(f'{mn} semilla {s}: E = {E} de {len(hist)}, val_loss {hist.val_loss.min():.5f}', flush=True)
            del modelo
        del Xtr, ytr, Xva, yva
        gc.collect()


def puntuar_todo(ctx):
    import keras
    cache = SAL / 'puntajes_2022.npz'
    nombres = cm.nombres_eval()
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        return pd.DatetimeIndex(z['dias']), {tuple(k.split('__')): z[k] for k in z.files if k != 'dias'}
    esc = lb1.escalas(ctx)
    mods = {(f'{mn}_s{s}'): keras.models.load_model(ruta_modelo(mn, s), compile=False) for mn in BASES for s in SEMILLAS}
    S, dias = {}, None
    for k in nombres:
        x = cm.leer(k)
        b = cm.bases(ctx, x)
        V = lb.valores(x, ctx['estaciones'])
        F = {v: lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'], V) for v in ('V0', 'Vb')}
        for nombre, mdl in mods.items():
            dia = cm.puntuar(ctx, mdl, F[BASES[nombre.split('_s')[0]]], x)
            S[(nombre, k)], dias = dia.to_numpy(), dia.index
        print(f'  {k}: listo', flush=True)
    np.savez_compressed(cache, dias=dias.values.astype('datetime64[ns]'), **{f'{a}__{b}': v for (a, b), v in S.items()})
    return dias, S


def main():
    ctx = cm.contexto()
    entrenar(ctx)
    dias, S = puntuar_todo(ctx)
    nombres = cm.nombres_eval()
    for mn in BASES:
        for k in nombres:
            S[(f'Ens-{mn}', k)] = np.mean([S[(f'{mn}_s{s}', k)] for s in SEMILLAS], axis=0)
    lab = cm.etiquetas(ctx, dias)
    todos = [f'{mn}_s{s}' for mn in BASES for s in SEMILLAS] + [f'Ens-{mn}' for mn in BASES]
    met = pd.concat([cm.metricas(S, todos, lab, nv) for nv in (0.01, 0.001)], ignore_index=True)
    met.to_csv(SAL / 'metricas.csv', index=False)
    filas = []
    for nv in (0.01, 0.001):
        m = met[met.nivel == nv].set_index('modelo')
        for s in SEMILLAS:
            filas.append(dict(nivel=nv, semilla=s, Fbar_V0r=m.loc[f'V0r_s{s}', 'Fbar'], Fbar_Vbr=m.loc[f'Vbr_s{s}', 'Fbar'],
                              dFbar=m.loc[f'Vbr_s{s}', 'Fbar'] - m.loc[f'V0r_s{s}', 'Fbar']))
    pd.DataFrame(filas).to_csv(SAL / 'por_semilla.csv', index=False)
    boot = []
    for nv in (0.01, 0.001):
        for a, b in (('Ens-Vbr', 'Ens-V0r'), ('Ens-Vbr', 'Vbr_s42'), ('Ens-V0r', 'V0r_s42')):
            r = cm.bootstrap_dfbar(S, dias, a, b, todos, lab, nv)
            boot.append(dict(nivel=nv, a=a, b=b, dFbar=r[0], ic_inf=r[1], ic_sup=r[2]))
    pd.DataFrame(boot).to_csv(SAL / 'bootstrap.csv', index=False)
    print(pd.DataFrame(filas).round(4).to_string(index=False))
    print(met[met.modelo.str.startswith('Ens')][['modelo', 'nivel', 'umbral', 'Fbar', 'F1_100', 'F1_50', 'F1_20',
                                                  'recall_50', 'precision_50', 'M1_50']].round(4).to_string(index=False))
    print(pd.DataFrame(boot).round(4).to_string(index=False))


if __name__ == '__main__':
    main()
