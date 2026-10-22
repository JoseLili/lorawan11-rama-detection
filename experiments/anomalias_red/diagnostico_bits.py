"""Diagnóstico (P4 del protocolo): bit flipping dentro del montaje de red.

Mismos calendarios, mismo Random Forest de red, mismas falsas alarmas fijas; sólo cambia la
alteración: en las horas con dato de cada episodio, valor XOR 2^bit (como en la parte 1), en
lugar de x(1 ± δ). Sirve para separar el efecto del tamaño de la alteración del efecto del
montaje. No es un detector del protocolo y no guarda modelos.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_bits.py --bits 5 6 7
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
warnings.filterwarnings('ignore')

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
M, PLANES = SAL / 'matrices', SAL / 'planes'


def voltear(limpia: pd.DataFrame, plan: pd.DataFrame, bit: int) -> pd.DataFrame:
    """Matriz con XOR 2^bit en las horas con dato de cada episodio y su etiqueta de red."""
    x = limpia.copy()
    cambiadas = pd.DataFrame(False, index=x.index, columns=ev.estaciones_de(x))
    for e in plan.itertuples():
        col = f'{e.estacion}_valor'
        v = x.loc[e.inicio:e.fin, col]
        v = v[v.notna()]
        x.loc[v.index, col] = (v.astype(int) ^ (1 << bit)).astype(float)
        cambiadas.loc[v.index, e.estacion] = True
    x['anomalia_red'] = cambiadas.any(axis=1).astype('int8')
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bits', type=int, nargs='+', default=[5, 6, 7])
    bits = ap.parse_args().bits
    lee = lambda n: ar.leer_matriz(M / f'matriz_{n}.csv.gz')  # noqa: E731
    limpia_tr, cal, limpia = lee('limpia_2020_2022'), lee('limpia_2023'), lee('limpia_2024')
    mu, sigma = ev.normalizacion(limpia_tr)
    plan_tr = ar.leer_plan(PLANES / 'plan_entrenamiento.csv')
    planes = {c: ar.leer_plan(PLANES / f'plan_{c}.csv') for c in ar.corridas().corrida.iloc[1:]}
    filas = []
    for bit in bits:
        tr = voltear(limpia_tr, plan_tr, bit)
        fijar_semilla(42)
        rf = RandomForestClassifier(random_state=42, n_jobs=-1).fit(ev.entradas(tr, mu, sigma), tr['anomalia_red'])
        p = lambda m: pd.Series(rf.predict_proba(ev.entradas(m, mu, sigma))[:, 1], index=m.index)  # noqa: E731
        s_cal, s_limpia = p(cal), p(limpia)
        for a in ev.NIVELES_FA:
            u = ev.umbral_falsas_alarmas(s_cal, a)
            horas, eps = [], []
            for c, plan in planes.items():
                plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
                plan = plan[plan.horas_con_dato > 0]
                x = voltear(limpia, plan, bit)
                alerta = p(x) > u
                horas.append(ev.por_hora(alerta, x['anomalia_red']))
                e = ev.por_episodio(plan, alerta)
                eps.append(e.assign(azar=ev.por_episodio(plan, s_limpia > u)['detectado'].to_numpy()))
            h, e = pd.DataFrame(horas), pd.concat(eps)
            det_h = (h.deteccion_hora_pct * h.horas_anomalas).sum() / h.horas_anomalas.sum()
            filas.append(dict(bit=bit, delta_ppb=1 << bit, nivel_fa_pct=round(100 * a),
                              falsa_alarma_2024_limpio_pct=round(100 * (s_limpia > u).mean(), 2),
                              deteccion_hora_pct=round(det_h, 1),
                              deteccion_episodio_pct=round(100 * e.detectado.mean(), 1),
                              azar_pct=round(100 * e.azar.mean(), 1)))
            print(filas[-1])
    pd.DataFrame(filas).to_csv(SAL / 'diagnostico_bits_rf_red.csv', index=False)


if __name__ == '__main__':
    main()
