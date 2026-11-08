"""Revisión 23b (D1): sesgo sostenido y deriva lenta, con el motor de la revisión 24.

    python rev23b.py planes
    python rev23b.py validar                      # escalón == ar.aplicar_fijo (sin puntajes)
    python rev23b.py puntuar --corrida a --parte i --partes n [--hilos h]
    python rev23b.py lanzar --corrida a [--partes 4 --hilos 4]
    python rev23b_metricas.py

Registro: docs/registro_previo_rev23b_ataque_lento.md (enmienda y precisiones al final).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent / 'anomalias_red'))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import comun as cm  # noqa: E402
import rev22_comun as rc  # noqa: E402
import rev23 as r23  # noqa: E402
import rev24 as r24  # noqa: E402
from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/rev23b'
L, SEP = 56, 60
FORMAS = ('escalon', 'rampa28', 'deriva56')
AMPS = (20, 40)
FIN_DIA = {2024: pd.Timestamp('2024-12-31'), 2025: pd.Timestamp('2025-12-31'), 2026: pd.Timestamp('2026-07-31')}


def vecindario(vecinas: dict, s: str) -> set:
    return set(vecinas.get(s, [])) | {t for t in vecinas if s in vecinas[t]}


def largos(plan: pd.DataFrame, anio: int, vecinas: dict) -> pd.DataFrame:
    """Episodios de 56 días aislados (misma estación y vecinas de Vb a > 60 días), en orden de inicio."""
    kept, filas = [], []
    for e in plan.sort_values('inicio').itertuples():
        i0 = e.inicio.normalize()
        f0 = i0 + pd.Timedelta(days=L - 1)
        if f0 > FIN_DIA[anio]:
            continue
        ok = all(not (s2 == e.estacion or s2 in vecindario(vecinas, e.estacion))
                 or i0 > g0 + pd.Timedelta(days=SEP) or f0 < j0 - pd.Timedelta(days=SEP) for s2, j0, g0 in kept)
        if ok:
            kept.append((e.estacion, i0, f0))
            filas.append(dict(corrida=e.corrida, episodio=int(e.episodio), estacion=e.estacion, inicio=i0,
                              fin=f0 + pd.Timedelta(hours=23), dias_sorteados=int(e.dias_sorteados), dias=L,
                              signo=int(e.signo), p=float(e.p), papel='original', origen=int(e.episodio)))
    out = pd.DataFrame(filas)
    ar.validar_plan(out)
    return out


def ruta_plan(c):
    return SAL / 'planes' / f'plan_{c}_largo.csv'


def leer_plan(c):
    p = pd.read_csv(ruta_plan(c), parse_dates=['inicio', 'fin'])
    ar.validar_plan(p)
    return p


def etapa_planes():
    (SAL / 'planes').mkdir(parents=True, exist_ok=False)
    vecinas = json.loads((rc.SAL / 'vecinas_vb.json').read_text())
    reg, n = {}, {}
    for c in r23.CALS:
        a = r23.anio_de(c)
        p = largos(ar.leer_plan(r23.PLANES0 / f'plan_{c}.csv'), a, vecinas)
        p.to_csv(ruta_plan(c), index=False, lineterminator='\n', date_format='%Y-%m-%d %H:%M:%S')
        assert len(leer_plan(c)) == len(p)
        reg[ruta_plan(c).name] = dict(sha256=r23.sha_texto(ruta_plan(c)), episodios=len(p))
        n[a] = n.get(a, 0) + len(p)
    (SAL / 'planes_sha256.json').write_text(json.dumps(reg, indent=2) + '\n', encoding='utf8')
    print('episodios por año:', n, 'total', sum(n.values()), flush=True)


def verificar_planes():
    for nombre, r in json.loads((SAL / 'planes_sha256.json').read_text()).items():
        assert r23.sha_texto(SAL / 'planes' / nombre) == r['sha256'], f'plan modificado: {nombre}'
    r23.verificar_planes()


def aplicar_forma(valores: pd.DataFrame, plan: pd.DataFrame, A: int, forma: str):
    """x + o(t) con signo +, max(x − o(t), 0) con signo −; redondeo y faltantes como `ar.aplicar_fijo`."""
    ar.validar_plan(plan)
    o = pd.DataFrame(0.0, index=valores.index, columns=valores.columns)
    for e in plan.itertuples():
        ix = valores.loc[e.inicio:e.fin].index
        h = ((ix - e.inicio) / pd.Timedelta(hours=1)).to_numpy(float)
        f = {'escalon': np.ones_like(h), 'rampa28': np.minimum(1.0, h / (28 * 24)), 'deriva56': h / (56 * 24)}[forma]
        o.loc[ix, e.estacion] = float(e.signo) * A * f
    alterado = np.floor(np.maximum(valores + o, 0.0) + 0.5)
    recibidos = valores.where(o.eq(0.0), alterado)
    cambiadas = valores.notna() & recibidos.ne(valores)
    return recibidos, cambiadas


def cambio_por_semana(vy, rec, plan):
    tot = np.zeros(8)
    n = np.zeros(8)
    for e in plan.itertuples():
        bloque = slice(e.inicio, e.fin)
        x0 = vy.loc[bloque, e.estacion]
        d = (rec.loc[bloque, e.estacion] - x0).abs()
        w = ((x0.index - e.inicio).days // 7).to_numpy()
        ok = x0.notna().to_numpy()
        np.add.at(tot, w[ok], d.to_numpy()[ok])
        np.add.at(n, w[ok], 1)
    return (tot / np.maximum(n, 1)).tolist()


def etapa_validar():
    verificar_planes()
    v = {a: rc.valores(f'{a}-01-01', r23.FIN[a]) for a in (2024, 2025, 2026)}
    malos = 0
    for c in r23.CALS:
        p = leer_plan(c)
        for A in AMPS:
            r1, c1 = aplicar_forma(v[r23.anio_de(c)], p, A, 'escalon')
            r2, c2 = ar.aplicar_fijo(v[r23.anio_de(c)], p, A)
            malos += int(not (r1.equals(r2) and c1.equals(c2)))
    out = dict(escalon_igual_aplicar_fijo=malos == 0, planes_distintos=malos)
    (SAL / 'validacion.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf8')
    print(out, flush=True)


def tareas():
    out = [('limpia', a, None, None) for a in (2024, 2025, 2026)]
    out += [(c, r23.anio_de(c), f, A) for c in r23.CALS for f in FORMAS for A in AMPS]
    return sorted(out, key=lambda r: (r[1], r[0] != 'limpia', r[0], r[2] or '', r[3] or 0))


def nombre_tarea(t):
    return f'limpia_{t[1]}' if t[0] == 'limpia' else f'{t[0]}_{t[2]}_a{t[3]}'


def grupos():
    g = ['Vb', 'V0']
    dt = r24.SAL / 'decision_tau.json'
    if dt.exists() and json.loads(dt.read_text())['avanza']:
        g.append(('Vx', r24.tau_elegido()))
    return g


def etapa_puntuar(corrida, parte, partes, hilos):
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(hilos)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    verificar_planes()
    T = tareas()
    mias = [T[i] for i in range(len(T)) if i * partes // len(T) == parte]
    sal = SAL / f'corrida_{corrida}'
    sal.mkdir(parents=True, exist_ok=True)
    det = r23.Detectores()
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    G = grupos()
    actual, anio_actual, t0 = None, None, time.time()
    for n, t in enumerate(mias, start=1):
        p = sal / f'{nombre_tarea(t)}.npz'
        if p.exists():
            continue
        if actual is None or anio_actual != t[1]:
            actual = None
            a = t[1]
            v = rc.valores('2020-01-01', r23.FIN[a])
            h3 = det.limpia_tr
            for y in range(2023, a):
                h3 = ev.con_historia(h3, ar.matriz_red(v.loc[f'{y}-01-01':f'{y}-12-31 23:00'], rc.columnas()))
            actual = r24.Periodo(v, f'{a}-01-01', ctx, esc, det, G, ('PARAAD', 'R3'), h3=h3)
            al = [int((actual.limpio['R3'] > u).sum()) for u in r23.umbrales_r3().values()]
            assert (al[0], al[1], int((~np.isnan(actual.limpio['R3'])).sum())) == r23.R3_CONTROL[a]
            anio_actual = a
        if t[0] == 'limpia':
            S, info = actual.limpio, {}
        else:
            plan = leer_plan(t[0])
            rec, cam = aplicar_forma(actual.vy, plan, t[3], t[2])
            S, info = actual.alterada(rec, cam, plan)
            info['cambio_por_semana'] = cambio_por_semana(actual.vy, rec, plan)
        r23.guardar(p, dias=actual.dias.values.astype('datetime64[ns]'), **S, info=np.array(json.dumps(info)))
        print(f'{time.strftime("%H:%M:%S")} parte {parte}: {n}/{len(mias)} {nombre_tarea(t)} '
              f'({(time.time() - t0) / n:.1f} s/tarea)', flush=True)
    print(f'parte {parte} lista en {time.time() - t0:.0f} s', flush=True)


def etapa_lanzar(corrida, partes, hilos):
    logs = SAL / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS=str(hilos), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', TF_CPP_MIN_LOG_LEVEL='2')
    ps = []
    for i in range(partes):
        f = open(logs / f'corrida_{corrida}_parte{i}.log', 'w', encoding='utf8')
        ps.append((subprocess.Popen([sys.executable, str(AQUI / 'rev23b.py'), 'puntuar', '--corrida', corrida,
                                     '--parte', str(i), '--partes', str(partes), '--hilos', str(hilos)],
                                    cwd=AQUI, stdout=f, stderr=subprocess.STDOUT, env=env), f))
    t0 = time.time()
    for p, f in ps:
        p.wait()
        f.close()
    cod = [p.returncode for p, _ in ps]
    print(f'corrida {corrida}: códigos {cod} en {time.time() - t0:.0f} s', flush=True)
    if any(cod):
        raise SystemExit(1)


def main():
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument('accion', choices=['planes', 'validar', 'puntuar', 'lanzar'])
    ap.add_argument('--corrida', default='a')
    ap.add_argument('--parte', type=int, default=0)
    ap.add_argument('--partes', type=int, default=4)
    ap.add_argument('--hilos', type=int, default=4)
    a = ap.parse_args()
    if a.accion == 'planes':
        etapa_planes()
    elif a.accion == 'validar':
        etapa_validar()
    elif a.accion == 'puntuar':
        etapa_puntuar(a.corrida, a.parte, a.partes, a.hilos)
    else:
        etapa_lanzar(a.corrida, a.partes, a.hilos)


if __name__ == '__main__':
    main()
