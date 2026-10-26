"""Comparación descriptiva con la parte 1 (2026-10-25, a pedido del tesista): recall con la misma tasa
nominal de falsas alarmas (5 %, el p95 de 2023), ordenado por el tamaño del cambio en ppb.

Uso: .venv/bin/python experiments/anomalias_red/comparacion_parte1_2024.py [--anio 2024|2025|2026]

Con 2024 la parte 2 sale de la revisión 15; con 2025 o 2026, del examen final (revisión 17).

- Parte 1: el V4 por lectura contra bit flipping (bit k = ±2^k ppb), grupo principal, de
  results/lstm_v4_multianual_v1/metricas_pareadas_agregadas.csv.
- Parte 2: L0, R3 y el V4 por estación-día contra episodios de δ, de
  results/anomalias_red_v1/puntos_operacion_2024/curva.csv (revisión 15). El tamaño de cada δ es el
  |cambio| medio por lectura alterada, medido en las matrices de 2024 contra 2024 limpio.

No es una comparación controlada: cambian la unidad (lectura contra estación-día), la duración (un
mensaje contra días completos), la forma (±2^k fijo contra proporcional) y la información (la
estación contra la estación y sus vecinas). No carga modelos ni entrena.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PARTE1 = RAIZ / 'results/lstm_v4_multianual_v1/metricas_pareadas_agregadas.csv'
CURVA = {2024: SAL / 'puntos_operacion_2024/curva.csv', 2025: SAL / 'examen_final/curva.csv',
         2026: SAL / 'examen_final/curva.csv'}


def cambio_medio(d: int, objetivos, anio: int) -> float:
    limpia = ar.leer_matriz(SAL / f'matrices/matriz_limpia_{anio}.csv.gz')[[f'{s}_valor' for s in objetivos]].to_numpy()
    cambios = []
    corridas = (ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA] if anio == 2024 else
                [c for c in ar.corridas_finales().corrida if c.startswith(f'final_{anio}')])
    for c in corridas:
        plan = ar.leer_plan(SAL / f'planes/plan_{c}.csv')
        x = ar.leer_matriz(SAL / f'matrices/matriz_{c}_d{d}.csv.gz')
        dentro = ar.en_episodio(plan, x.index, objetivos).to_numpy() & ~np.isnan(limpia)
        cambios.append(np.abs(x[[f'{s}_valor' for s in objetivos]].to_numpy() - limpia)[dentro])
    return float(np.concatenate(cambios).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anio', type=int, default=2024, choices=sorted(CURVA))
    anio = ap.parse_args().anio
    objetivos = alterables_v4()
    p1 = pd.read_csv(PARTE1)
    p1 = p1[(p1.anio == anio) & (p1.grupo == 'principal')]
    filas = [dict(parte=1, alteracion=f'bit {int(r.bit)}', cambio_ppb=float(r.delta_ppb), detector='V4 por lectura',
                  recall_pct=r.recall_micro_pct, falsas_alarmas_pct=r.fpr_micro_pct) for r in p1.itertuples()]
    cv = pd.read_csv(CURVA[anio])
    cv = cv[(cv.fa_objetivo_pct.round(6) == 5.0) & ((cv.anio == anio) if 'anio' in cv else True)]
    for d in sorted(cv.delta_pct.unique(), reverse=True):
        ppb = cambio_medio(int(d), objetivos, anio)
        for r in cv[cv.delta_pct == d].itertuples():
            filas.append(dict(parte=2, alteracion=f'δ = {d} %', cambio_ppb=ppb, detector=f'{r.detector} por estación-día',
                              recall_pct=100 * r.recall, falsas_alarmas_pct=r.fa_examen_pct))
    t = pd.DataFrame(filas)
    t['recall_sobre_azar_pts'] = t.recall_pct - t.falsas_alarmas_pct
    t = t.sort_values(['cambio_ppb', 'parte', 'detector']).reset_index(drop=True)
    t.to_csv(SAL / f'comparacion_parte1_{anio}.csv', index=False)
    print(t.round(1).to_string(index=False))


if __name__ == '__main__':
    main()
