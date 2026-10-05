"""Ejecuta el protocolo v4k_multianual_33_p95cal2023_v1 (vecinas cercanas) de principio a fin.

Uso (desde la raíz del repo):

    .venv/bin/python experiments/vecinas/ejecutar.py                 # todo
    .venv/bin/python experiments/vecinas/ejecutar.py --solo entrenar
    nohup .venv/bin/python experiments/vecinas/ejecutar.py > /dev/null 2>&1 &

Etapas: entrenar (elige k ∈ {4, 8, 16, 32} con 2022 por estación) → verificar
(reproducibilidad de un objetivo con k < 32) → evaluar (un mensaje) → simultaneo (mismo
plan que la variante contemporánea). Reanudable. Progreso en
results/vecinas_cercanas_v1/ejecucion.log y bitacora.csv. No modifica el V4.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from src.detect import multianual as m  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import ataques_multianual as at  # noqa: E402
from src.detect import contemporaneo as ct  # noqa: E402
from src.detect import vecinas as vc  # noqa: E402

SAL = RAIZ / 'results/vecinas_cercanas_v1'
EST = SAL / 'estaciones'
V4 = RAIZ / 'results/lstm_v4_multianual_v1/estaciones'
BITACORA = SAL / 'bitacora.csv'


def configurar_log():
    SAL.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter('%(asctime)s  %(message)s', '%Y-%m-%d %H:%M:%S')
    log = logging.getLogger('v4k')
    log.setLevel(logging.INFO)
    for h in (logging.FileHandler(SAL / 'ejecucion.log', encoding='utf-8'), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    return log


def clases_elegibles():
    cob = pd.read_csv(RAIZ / 'results/lstm_v4_multianual_v1/cobertura_etapas.csv')
    clases = cob.drop_duplicates('objetivo').set_index('objetivo')['clasificacion']
    return clases, [s for s in m.ESTACIONES if clases[s] != 'fuera']


def entrenar(ctx, log, dist, elegibles, clases):
    for i, obj in enumerate(elegibles, 1):
        if (EST / obj / 'configuracion.json').exists():
            log.info(f'[entrenar] {i:02d}/{len(elegibles)} {obj}: ya existe, se salta')
            continue
        t0 = time.time()
        try:
            cfg = vc.entrenar_knn(ctx, obj, EST / obj, dist, V4)
        except Exception as e:
            log.info(f'[entrenar] {obj}: ERROR {type(e).__name__}: {e}')
            em.registrar(BITACORA, 'entrenar_knn', obj, 'error', f'{type(e).__name__}: {e}',
                         segundos=time.time() - t0, origen='experiments/vecinas/ejecutar.py')
            continue
        sel = pd.read_csv(EST / obj / 'seleccion_k.csv')
        detalle = f"k*={cfg['k']}; " + '; '.join(f'k={r.k}: val={r.val_loss_min:.1f}' for r in sel.itertuples())
        em.registrar(BITACORA, 'entrenar_knn', obj, 'entrenado', detalle, flags=dict(clasificacion=clases[obj]),
                     config=cfg, carpeta=EST / obj, segundos=time.time() - t0,
                     origen='experiments/vecinas/ejecutar.py')
        log.info(f"[entrenar] {i:02d}/{len(elegibles)} {obj}: k*={cfg['k']} E={cfg.get('epoca_E')} "
                 f"p95={cfg['umbral_p95_ppb']:.2f} ({time.time() - t0:.0f} s) | {detalle}")


def verificar(ctx, log, elegibles):
    con_k = [o for o in elegibles if json.loads((EST / o / 'configuracion.json').read_text())['k'] < vc.K_V4]
    if not con_k:
        log.info('[verificar] todos eligieron k = 32 (V4): no hay modelo nuevo que verificar')
        return
    obj = 'CCA' if 'CCA' in con_k else con_k[0]
    cfg = json.loads((EST / obj / 'configuracion.json').read_text())
    copia = SAL / 'verificacion' / obj
    if not (copia / 'configuracion.json').exists():
        em.entrenar_objetivo(ctx, obj, copia, vecinas=cfg['vecinas'], protocolo=vc.PROTOCOLO)
    comp = em.comparar_corridas(EST / obj, copia)
    ok = bool(comp.identico.all())
    log.info(f'[verificar] {obj} (k={cfg["k"]}): {"REPRODUCIBLE" if ok else "DIFIERE"}\n{comp.to_string(index=False)}')
    em.registrar(BITACORA, 'verificar_knn', obj, 'reproducible' if ok else 'no_reproducible',
                 '; '.join(f'{r.comprobacion}={r.identico}' for r in comp.itertuples()),
                 origen='experiments/vecinas/ejecutar.py')
    if not ok:
        raise SystemExit('Reproducibilidad fallida: no se continúa (CLAUDE.md).')


def evaluar(ctx, log, clases, rehacer=False):
    if not rehacer and all((SAL / f).exists() for f in ct.ARCHIVOS_EVAL.values()):
        log.info('[evaluar] ya evaluado, se salta')
        return
    t0 = time.time()
    ct.evaluar_un_mensaje(ctx, EST, SAL, clases)
    em.registrar(BITACORA, 'evaluar_knn', 'todos', 'calculado', 'un mensaje: limpio, pareada 5 %, barrido',
                 flags=dict(EVALUAR_PRUEBA=True), segundos=time.time() - t0, origen='experiments/vecinas/ejecutar.py')
    log.info(f'[evaluar] listo ({time.time() - t0:.0f} s)')


def simultaneo(ctx, log, clases):
    dsim = SAL / 'simultaneo'
    (dsim / 'parciales').mkdir(parents=True, exist_ok=True)
    cache = {}
    for anio in at.ANIOS:
        horas = ct.plan_horas(ctx['valores'], anio)
        pd.Series(horas, name='timestamp').to_csv(dsim / f'plan_{anio}.csv', index=False)
        for bit in at.BITS:
            parcial = dsim / f'parciales/{anio}_bit{bit}.csv'
            if parcial.exists():
                log.info(f'[simultaneo] {anio} bit {bit}: ya existe, se salta')
                continue
            t0 = time.time()
            ct.evaluar_simultaneo_bit(ctx, {'knn': EST}, anio, bit, horas, cache).to_csv(parcial, index=False)
            log.info(f'[simultaneo] {anio} bit {bit}: {len(horas)} horas ({time.time() - t0:.0f} s)')
    todo = pd.concat([pd.read_csv(p) for p in sorted((dsim / 'parciales').glob('*.csv'))], ignore_index=True)
    todo.to_csv(dsim / 'metricas_simultaneo.csv', index=False)
    ct.agregar_simultaneo(todo, clases).to_csv(dsim / 'metricas_simultaneo_agregadas.csv', index=False)
    em.registrar(BITACORA, 'evaluar_simultaneo_knn', 'knn', 'calculado',
                 f'mismo plan que contemporaneo_v1: semilla [42, {ct.SEMILLA_SIMULTANEO}, año]',
                 flags=dict(EVALUAR_PRUEBA=True), origen='experiments/vecinas/ejecutar.py')
    log.info('[simultaneo] listo')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', choices=['entrenar', 'verificar', 'evaluar', 'simultaneo'])
    ap.add_argument('--rehacer-evaluacion', action='store_true')
    args = ap.parse_args()
    log = configurar_log()
    t0 = time.time()
    log.info(f'=== {vc.PROTOCOLO}: inicio (etapa: {args.solo or "todas"}) ===')
    (SAL / 'protocolo.json').write_text(json.dumps(dict(
        protocolo=vc.PROTOCOLO, documento='docs/protocolo_vecinas_cercanas_v1.md', referencia=m.PROTOCOLO,
        ks=[*vc.KS, vc.K_V4], entrenamiento=em.CONFIG, anios_prueba=list(at.ANIOS), bits=at.BITS,
        tasa=at.TASA, semilla=at.SEMILLA, semilla_simultaneo=ct.SEMILLA_SIMULTANEO), indent=2, ensure_ascii=False) + '\n')
    ctx = em.contexto(RAIZ)
    dist = vc.distancias(pd.read_csv(RAIZ / 'results/inventario_multianual/estaciones_geografia.csv', index_col=0))
    clases, elegibles = clases_elegibles()
    for e in ([args.solo] if args.solo else ['entrenar', 'verificar', 'evaluar', 'simultaneo']):
        if e == 'entrenar':
            entrenar(ctx, log, dist, elegibles, clases)
        elif e == 'verificar':
            verificar(ctx, log, elegibles)
        elif e == 'evaluar':
            evaluar(ctx, log, clases, args.rehacer_evaluacion)
        elif e == 'simultaneo':
            simultaneo(ctx, log, clases)
    log.info(f'=== fin ({(time.time() - t0) / 60:.1f} min) ===')


if __name__ == '__main__':
    main()
