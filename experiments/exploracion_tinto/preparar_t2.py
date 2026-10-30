"""TINTO T2: precalcula en la lap las 98 columnas de L0, etiquetas y muestras para Colab.

No entrena ni evalúa. Colab solo recibe arreglos numpy; así el script remoto no depende del
entorno de la tesis. Las ventanas se vuelven a armar en Colab con índices y se comprueba aquí que
salen idénticas a las de L0 (`lstm_local.ventanas_locales`) y a la caché de T1.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/anomalias_red'))
T1 = ROOT / 'results/exploracion_tinto_2022'
CACHE_T1 = T1 / 'preparacion_20261029/cache_completa'
VENTANA = 24
N_MUESTRA_RED = 20000


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def gather(F, t, cols=None):
    """(n, 24, c): filas t−23…t de F; misma regla que `lstm_red.ventanas`."""
    W = F[np.asarray(t)[:, None] + np.arange(-VENTANA + 1, 1)[None, :]]
    return W if cols is None else W[:, :, cols]


def main(out, prueba):
    from entrenar_lstm_sup import leer, parametros_vecinas, SELECCION, VALIDACION
    from diagnostico_variantes_2022 import posiciones
    from generar_planes import alterables_v4
    from src.detect import evaluacion_red as ev, estacion_dia as ed, lstm_local as ll, anomalias_red as ar
    out.mkdir(parents=True)
    clean, clean_sha = leer('limpia_2020_2022')
    idx = clean.index
    assert len(idx) == 26304 and idx[0] == pd.Timestamp('2020-01-01') and idx[-1] == pd.Timestamp('2022-12-31 23:00')
    _, sigma = ev.normalizacion(clean)
    par = parametros_vecinas('a14', clean.loc[SELECCION[0]:SELECCION[1]], sigma, 'media')
    targets = list(alterables_v4())
    stations = list(ev.estaciones_de(clean))
    frozen = json.loads((T1 / 'auditoria_l0_20261028/corrida1/vecinas_y_escalas.json').read_text())
    assert targets == frozen['objetivos'] and par.vecinas == frozen['vecinas'] and len(targets) == 31
    local = np.array([ll.indices_locales(stations, par.vecinas, s) for s in targets])
    assert local.shape == (31, 17)
    pos = {'tr': posiciones(idx, *SELECCION), 'va': posiciones(idx, *VALIDACION)}
    days = idx.normalize().unique()
    obs_clean = clean[[f'{s}_mascara' for s in targets]].to_numpy() == 1

    nums_tr = list(range(1, 3 if prueba else 21))
    nums_va = [n for n in nums_tr if n <= 10]
    names = ['limpia_2020_2022'] + [f'entrenamiento_{n:02d}_d50' for n in nums_tr]
    if not prueba:
        names += [f'entrenamiento_{n:02d}_d{d}' for d in (100, 20) for n in range(1, 11)]
    fuentes = {'limpia_2020_2022': clean_sha}
    Fs = {}
    for name in names:
        x = clean if name == 'limpia_2020_2022' else None
        if x is None:
            x, fuentes[name] = leer(name)
            assert x.index.equals(idx)
            # Solo se alteran horas con dato: la disponibilidad es la misma que en la limpia.
            assert np.array_equal(x[[f'{s}_mascara' for s in targets]].to_numpy() == 1, obs_clean), name
        F = np.asarray(ev.entradas_de('vecinas', x, None, sigma, par), dtype=np.float32)
        assert F.shape == (len(idx), 98) and np.isfinite(F).all(), name
        np.save(out / f'F_{name}.npy', F)
        Fs[name] = F
        if name.endswith('_d50'):
            # Solo se entrena con δ = 50 %. La etiqueta por hora depende de δ (una lectura que el
            # redondeo deja igual no queda marcada); la del día sale del plan y no depende de δ.
            cal = name.rsplit('_', 1)[0]
            np.save(out / f'Yhora_{cal}.npy', ed.etiquetas_por_hora(x, targets).to_numpy().astype(np.uint8))
            plan = ar.leer_plan(ROOT / f'results/anomalias_red_v1/planes/plan_{cal}.csv')
            np.save(out / f'Ydia_{cal}.npy', ed.etiquetas(plan, days, targets).to_numpy().astype(np.uint8))
        print(name, flush=True)
    np.save(out / 'obs.npy', obs_clean)

    # Muestra EH de L0: (calendario, objetivo, t), en el mismo orden que `entrenar_lstm_local.ejemplos`.
    for split, nums, uso in [('tr', nums_tr, 'seleccion'), ('va', nums_va, 'validacion')]:
        rows = [(n, j, t) for n in nums for j in range(31) for t in ll.muestra(pos[split], 8, uso, n, j)]
        np.save(out / f'muestra_EH_{split}.npy', np.array(rows, dtype=np.int32))
    eh_tr = np.load(out / 'muestra_EH_tr.npy')
    if not prueba:
        assert len(eh_tr) == 1357800 and len(np.load(out / 'muestra_EH_va.npy')) == 339450
        man = pd.read_csv(CACHE_T1 / 'manifiesto_tr.csv.gz', usecols=['objetivo', 'posicion_matriz'])
        assert np.array_equal(man.posicion_matriz.to_numpy(), eh_tr[:, 2])
        assert np.array_equal(man.objetivo.map(targets.index).to_numpy(), eh_tr[:, 1])
    # Las ventanas armadas con índices son las de L0 y las de la caché de T1.
    Xc = np.load(CACHE_T1 / 'X_tr.npy', mmap_mode='r') if not prueba else None
    for k in [0, 1, 7, 31 * 2190 + 5, len(eh_tr) - 1] if not prueba else [0, 1]:
        n, j, t = eh_tr[k]
        F = Fs[f'entrenamiento_{n:02d}_d50']
        mine = gather(F, [t], local[j])
        np.testing.assert_array_equal(mine, ll.ventanas_locales(F, stations, par.vecinas, targets[j], np.array([t])))
        if Xc is not None:
            np.testing.assert_array_equal(mine.reshape(1, 408), Xc[k:k + 1])

    # Muestra de ventanas de red (98 columnas) de 2020–2021 para ajustar el mapa TINTO 64 × 64.
    rng = np.random.default_rng([42, 29, 20])
    cal = rng.choice(nums_tr, size=N_MUESTRA_RED)
    t = rng.choice(pos['tr'], size=N_MUESTRA_RED)
    Xr = np.stack([gather(Fs[f'entrenamiento_{c:02d}_d50'], [tt])[0] for c, tt in zip(cal, t)])
    np.save(out / 'X_muestra_red.npy', Xr.reshape(N_MUESTRA_RED, -1).astype(np.float32))
    nombres = ([f'rel_{s}' for s in stations] + [f'mascara_{s}' for s in stations] + ['hora_sin', 'hora_cos']
               + [f'a14_{s}' for s in stations])
    assert len(nombres) == 98

    meta = dict(fecha='2026-10-29', prueba=prueba, indice_inicio=str(idx[0]), horas=len(idx),
                dias=[str(d.date()) for d in days], estaciones=stations, objetivos=targets,
                columnas_98=nombres, indices_locales=local.tolist(),
                posiciones={k: [int(v.min()), int(v.max()), len(v)] for k, v in pos.items()},
                calendarios_ajuste=nums_tr, calendarios_validacion=nums_va, matrices=names,
                muestra_red=dict(n=N_MUESTRA_RED, semilla=[42, 29, 20], calendarios=cal.tolist(), t=t.tolist()),
                sha256_matrices=fuentes, codigo=sha(Path(__file__)))
    (out / 'meta.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False) + '\n')
    print('LISTO', out, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--prueba', action='store_true')
    a = ap.parse_args()
    if a.salida.exists():
        ap.error('Usa una carpeta nueva.')
    main(a.salida, a.prueba)
