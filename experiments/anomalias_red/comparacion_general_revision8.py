"""Comparación general de la parte 2: detectores supervisados contra no supervisados (examen 2024).

Uso (desde la raíz del repo, después de `metricas_estandar_revision8.py` y
`generalizacion_delta_revision8.py`):

    .venv/bin/python experiments/anomalias_red/comparacion_general_revision8.py

No calcula nada nuevo: junta las métricas de la revisión 9 (con su valor sin ataque) de
- los supervisados con el modelo de su mismo δ (como en el protocolo) y con un solo modelo para
  todos los δ, el entrenado con δ = 100 % (como los no supervisados, que no saben qué δ viene);
- los no supervisados (V4, IsolationForest) y la regla de vecinas, que no se entrena.
Salida: results/anomalias_red_v1/analisis_revision8/comparacion_general.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
A = RAIZ / 'results/anomalias_red_v1/analisis_revision8'
COLUMNAS = ['f1', 'f2', 'mcc', 'precision', 'recall', 'pr_auc', 'falsas_alarmas']
FAMILIA = {'LSTM con vecinas': 'supervisado', 'LSTM sin vecinas': 'supervisado', 'RF con vecinas': 'supervisado',
           'RF sin vecinas': 'supervisado', 'Regla de vecinas': 'sin entrenamiento', 'V4': 'no supervisado',
           'IsolationForest': 'no supervisado'}


def main():
    e = pd.read_csv(A / 'metricas_estandar.csv')
    e = e[e.version.isin(['examen', 'sin ataque'])].rename(columns={'delta_pct': 'delta_examen'})
    e['modelo'] = e.detector.where(~e.detector.isin(['LSTM con vecinas', 'LSTM sin vecinas', 'RF con vecinas', 'RF sin vecinas']),
                                   e.detector + ' (modelo de su δ)')
    g = pd.read_csv(A / 'generalizacion_delta.csv')
    g = g[g.delta_entrenamiento == 100].assign(modelo=g.modelo + ' (un modelo, δ = 100 %)')
    g['detector'] = g.modelo.str.split(' \\(').str[0]
    t = pd.concat([e[['modelo', 'detector', 'delta_examen', 'nivel_fa_pct', 'version'] + COLUMNAS],
                   g[['modelo', 'detector', 'delta_examen', 'nivel_fa_pct', 'version'] + COLUMNAS]], ignore_index=True)
    t['familia'] = t.detector.map(FAMILIA)
    t.to_csv(A / 'comparacion_general.csv', index=False)

    pd.set_option('display.width', 250)
    orden = ['LSTM con vecinas (modelo de su δ)', 'LSTM con vecinas (un modelo, δ = 100 %)',
             'LSTM sin vecinas (modelo de su δ)', 'LSTM sin vecinas (un modelo, δ = 100 %)',
             'RF con vecinas (modelo de su δ)', 'Regla de vecinas', 'V4', 'IsolationForest']
    for k in (1, 5):
        for col in ('f1', 'f2', 'mcc'):
            x = t[t.nivel_fa_pct == k].pivot_table(index='modelo', columns=['delta_examen', 'version'], values=col)
            x = x.loc[orden, [(d, v) for d in (100, 50, 20, 10, 5) for v in ('examen', 'sin ataque')]]
            print(f'\n{col.upper()} con {k} %: examen | sin ataque')
            print(x.round(2).to_string())
    x = t[t.nivel_fa_pct == 1].pivot_table(index='modelo', columns=['delta_examen', 'version'], values='pr_auc')
    print('\nPR-AUC: examen | sin ataque')
    print(x.loc[orden, [(d, v) for d in (100, 50, 20, 10, 5) for v in ('examen', 'sin ataque')]].round(2).to_string())


if __name__ == '__main__':
    main()
