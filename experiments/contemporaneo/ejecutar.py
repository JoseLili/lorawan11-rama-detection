"""Ejecuta el protocolo v4c_multianual_33_p95cal2023_v1 de principio a fin.

Uso (desde la raíz del repo):

    .venv/bin/python experiments/contemporaneo/ejecutar.py            # todo
    .venv/bin/python experiments/contemporaneo/ejecutar.py --solo entrenar
    nohup .venv/bin/python experiments/contemporaneo/ejecutar.py > /dev/null 2>&1 &   # en segundo plano

Etapas: entrenar (lstm_t y lineal_t) → verificar (reproducibilidad CCA) → evaluar (un
mensaje, como el notebook 13) → simultaneo (mismo bit en todas las estaciones, para V4,
lstm_t y lineal_t). Es reanudable: lo que ya está guardado se salta. El progreso queda en
results/contemporaneo_v1/ejecucion.log y bitacora.csv. Nunca modifica el V4 multianual.
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

SAL = RAIZ / 'results/contemporaneo_v1'
V4 = RAIZ / 'results/lstm_v4_multianual_v1/estaciones'
FAMILIAS = {'lstm_t': SAL / 'lstm_t/estaciones', 'lineal_t': SAL / 'lineal_t/estaciones'}
BITACORA = SAL / 'bitacora.csv'


def configurar_log():
    SAL.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter('%(asctime)s  %(message)s', '%Y-%m-%d %H:%M:%S')
    log = logging.getLogger('v4c')
    log.setLevel(logging.INFO)
    for h in (logging.FileHandler(SAL / 'ejecucion.log', encoding='utf-8'), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)
    return log


def clases_elegibles():
    cob = pd.read_csv(RAIZ / 'results/lstm_v4_multianual_v1/cobertura_etapas.csv')
    clases = cob.drop_duplicates('objetivo').set_index('objetivo')['clasificacion']
    return clases, [s for s in m.ESTACIONES if clases[s] != 'fuera']


def entrenar(ctx, log, elegibles, clases):
    for fam, raiz in FAMILIAS.items():
        for i, obj in enumerate(elegibles, 1):
            carpeta = raiz / obj
            if (carpeta / 'configuracion.json').exists():
                log.info(f'[entrenar] {fam} {i:02d}/{len(elegibles)} {obj}: ya existe, se salta')
                continue
            t0 = time.time()
            try:
                if fam == 'lstm_t':
                    cfg = em.entrenar_objetivo(ctx, obj, carpeta, incluir_t=True, protocolo=ct.PROTOCOLO)
                else:
                    cfg = ct.entrenar_lineal(ctx, obj, carpeta)
            except Exception as e:                     # se registra y se sigue
                log.info(f'[entrenar] {fam} {obj}: ERROR {type(e).__name__}: {e}')
                em.registrar(BITACORA, f'entrenar_{fam}', obj, 'error', f'{type(e).__name__}: {e}',
                             segundos=time.time() - t0, origen='ejecutar.py')
                continue
            em.registrar(BITACORA, f'entrenar_{fam}', obj, 'entrenado', f"alpha={cfg.get('alpha')}",
                         flags=dict(clasificacion=clases[obj]), config=cfg, carpeta=carpeta,
                         segundos=time.time() - t0, origen='ejecutar.py')
            log.info(f"[entrenar] {fam} {i:02d}/{len(elegibles)} {obj}: E={cfg.get('epoca_E')} "
                     f"alpha={cfg.get('alpha')} p95={cfg['umbral_p95_ppb']:.2f} ({time.time() - t0:.0f} s)")


def verificar(ctx, log):
    for fam, raiz in FAMILIAS.items():
        original, copia = raiz / 'CCA', SAL / fam / 'verificacion/CCA'
        if not (copia / 'configuracion.json').exists():
            if fam == 'lstm_t':
                em.entrenar_objetivo(ctx, 'CCA', copia, incluir_t=True, protocolo=ct.PROTOCOLO)
            else:
                ct.entrenar_lineal(ctx, 'CCA', copia)
        comp = em.comparar_corridas(original, copia) if fam == 'lstm_t' else ct.comparar_lineal(original, copia)
        ok = bool(comp.identico.all())
        log.info(f'[verificar] {fam} CCA: {"REPRODUCIBLE" if ok else "DIFIERE"}\n{comp.to_string(index=False)}')
        em.registrar(BITACORA, f'verificar_{fam}', 'CCA', 'reproducible' if ok else 'no_reproducible',
                     '; '.join(f'{r.comprobacion}={r.identico}' for r in comp.itertuples()), origen='ejecutar.py')
        if not ok:
            raise SystemExit('Reproducibilidad fallida: no se continúa (CLAUDE.md).')


def evaluar(ctx, log, clases, rehacer=False):
    for fam, raiz in FAMILIAS.items():
        salida = SAL / fam
        if not rehacer and all((salida / f).exists() for f in ct.ARCHIVOS_EVAL.values()):
            log.info(f'[evaluar] {fam}: ya evaluado, se salta')
            continue
        t0 = time.time()
        ct.evaluar_un_mensaje(ctx, raiz, salida, clases)
        em.registrar(BITACORA, f'evaluar_{fam}', 'todos', 'calculado', 'un mensaje: limpio, pareada 5 %, barrido',
                     flags=dict(EVALUAR_PRUEBA=True), segundos=time.time() - t0, origen='ejecutar.py')
        log.info(f'[evaluar] {fam}: listo ({time.time() - t0:.0f} s)')


def simultaneo(ctx, log, clases):
    dsim = SAL / 'simultaneo'
    (dsim / 'parciales').mkdir(parents=True, exist_ok=True)
    familias = {'v4': V4, **FAMILIAS}
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
            r = ct.evaluar_simultaneo_bit(ctx, familias, anio, bit, horas, cache)
            r.to_csv(parcial, index=False)
            log.info(f'[simultaneo] {anio} bit {bit}: {len(horas)} horas atacadas, {len(r)} filas ({time.time() - t0:.0f} s)')
    todo = pd.concat([pd.read_csv(p) for p in sorted((dsim / 'parciales').glob('*.csv'))], ignore_index=True)
    todo.to_csv(dsim / 'metricas_simultaneo.csv', index=False)
    ct.agregar_simultaneo(todo, clases).to_csv(dsim / 'metricas_simultaneo_agregadas.csv', index=False)
    em.registrar(BITACORA, 'evaluar_simultaneo', 'v4 lstm_t lineal_t', 'calculado',
                 f'años {list(at.ANIOS)}; bits 0-7; 5 % de horas; semilla [42, {ct.SEMILLA_SIMULTANEO}, año]',
                 flags=dict(EVALUAR_PRUEBA=True), origen='ejecutar.py')
    log.info('[simultaneo] listo')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', choices=['entrenar', 'verificar', 'evaluar', 'simultaneo'])
    ap.add_argument('--rehacer-evaluacion', action='store_true')
    args = ap.parse_args()
    log = configurar_log()
    t0 = time.time()
    log.info(f'=== {ct.PROTOCOLO}: inicio (etapa: {args.solo or "todas"}) ===')
    (SAL / 'protocolo.json').write_text(json.dumps(dict(
        protocolo=ct.PROTOCOLO, documento='docs/protocolo_contemporaneo_v1.md', referencia=m.PROTOCOLO,
        familias=list(FAMILIAS), alphas=ct.ALPHAS, entrenamiento=em.CONFIG, anios_prueba=list(at.ANIOS),
        bits=at.BITS, tasa=at.TASA, semilla=at.SEMILLA, semilla_simultaneo=ct.SEMILLA_SIMULTANEO),
        indent=2, ensure_ascii=False) + '\n')
    ctx = em.contexto(RAIZ)
    clases, elegibles = clases_elegibles()
    etapas = [args.solo] if args.solo else ['entrenar', 'verificar', 'evaluar', 'simultaneo']
    for e in etapas:
        if e == 'entrenar':
            entrenar(ctx, log, elegibles, clases)
        elif e == 'verificar':
            verificar(ctx, log)
        elif e == 'evaluar':
            evaluar(ctx, log, clases, args.rehacer_evaluacion)
        elif e == 'simultaneo':
            simultaneo(ctx, log, clases)
    log.info(f'=== fin ({(time.time() - t0) / 60:.1f} min) ===')


if __name__ == '__main__':
    main()
