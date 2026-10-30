"""Revisión 21: une PARAAD (calificado aparte con `puntuar_paraad.py`) con los demás detectores. No usa TensorFlow.

Uso (después de evaluar_revision21.py y de calificar PARAAD en las matrices de error fijo del año):

    .venv/bin/python experiments/anomalias_red/resumir_revision21.py --anio 2025

Lee los puntajes por estación-día de `revision21/<año>/dias_<año>.csv.gz` (L0 único, V4S compartido, R3, V4) y los de
PARAAD en `revision21/paraad/<año>/fijo_<corrida>_a<a>/puntajes.csv`. Su año limpio y el escenario proporcional salen
de la revisión 20 (`revision20/examen/<año>/puntajes/`). Umbrales de PARAAD: los congelados de la revisión 20.

- Métricas de PARAAD por a, con su valor sin ataque, en las mismas estación-días (la máscara común de la revisión 21,
  que debe ser la de la revisión 20).
- PARAAD − V4 (F1, recall y precisión), bootstrap de bloques estación × mes, semilla [42, 21, año], como L0 − V4S.
- PARAAD contra el proporcional: su recall en las mismas estación-días atacadas con cada δ.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from evaluar_revision18 import ANIOS, B, DELTAS, PLANES  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from generar_revision19 import calendarios_prueba  # noqa: E402
from intervalos_2024 import metricas  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
R21, R20 = SAL / 'revision21', SAL / 'revision20'
CAL_PARAAD = R20 / 'calibracion_2023/registro.json'
REVISION = 21


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anio', type=int, required=True, choices=sorted(ANIOS))
    anio = ap.parse_args().anio
    cfg, objetivos = ANIOS[anio], alterables_v4()
    base = R21 / str(anio)
    U = json.loads(CAL_PARAAD.read_text())['umbrales']
    mascara = pd.read_csv(base / 'mascara_comun.csv', index_col='dia', parse_dates=['dia'])[objetivos].astype(bool)
    m20 = pd.read_csv(R20 / f'examen/{anio}/mascara_comun.csv', index_col='dia', parse_dates=['dia'])[objetivos].astype(bool)
    if not mascara.equals(m20):
        raise RuntimeError('la máscara común de la revisión 21 no es la de la revisión 20')
    dias = mascara.index
    val = mascara.to_numpy().ravel()
    d21 = pd.read_csv(base / f'dias_{anio}.csv.gz', parse_dates=['dia'])

    def v4(conjunto):
        return d21[(d21.conjunto == conjunto) & (d21.detector == 'V4')].set_index('dia').reindex(dias)[objetivos]

    def paraad(ruta):
        return pd.read_csv(ruta, index_col='dia', parse_dates=['dia']).reindex(dias)[objetivos]

    s0 = paraad(R20 / f'examen/{anio}/puntajes/{cfg["limpia"]}.csv')
    v0 = v4(cfg['limpia'])
    corridas = calendarios_prueba(anio).corrida.tolist()
    mes1 = (np.arange(len(objetivos))[None, :] * 12 + (dias.month.to_numpy() - 1)[:, None]).ravel()
    filas, filas_ic, filas_prop = [], [], []
    for a in ar.TAMANOS_FIJOS:
        Y, Sp, Sv, mes = [], [], [], []
        for k, c in enumerate(corridas):
            plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
            Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
            Sp.append(paraad(R21 / f'paraad/{anio}/fijo_{c}_a{a}/puntajes.csv').to_numpy().ravel())
            Sv.append(v4(f'fijo_{c}_a{a}').to_numpy().ravel())
            mes.append(mes1 + 1000 * k)
        ok = np.tile(val, len(corridas))
        y = np.concatenate(Y)[ok] == 1.0
        sp, sv = np.concatenate(Sp)[ok], np.concatenate(Sv)[ok]
        if np.isnan(sp).any():
            raise RuntimeError('PARAAD sin puntaje en una estación-día común')
        sp0 = np.tile(s0.to_numpy().ravel(), len(corridas))[ok]
        _, mes_b = np.unique(np.concatenate(mes)[ok], return_inverse=True)
        nb = mes_b.max() + 1
        W = np.random.default_rng([42, REVISION, anio]).multinomial(nb, np.full(nb, 1 / nb), size=B)
        auc = {'con ataque': dict(pr_auc=average_precision_score(y, sp), roc_auc=roc_auc_score(y, sp)),
               'sin ataque': dict(pr_auc=average_precision_score(y, sp0), roc_auc=roc_auc_score(y, sp0))}
        r21 = pd.read_csv(base / 'resultados.csv')
        for p, u in U.items():
            for v_, puntaje in (('con ataque', sp), ('sin ataque', sp0)):
                filas.append(dict(anio=anio, a_ppb=a, detector='PARAAD', punto=p, evaluacion=v_, umbral=u,
                                  **con_umbral(y, puntaje > u), **auc[v_]))
            uv = r21[(r21.detector == 'V4') & (r21.punto == p)].umbral.iat[0]
            alertas = {'PARAAD': sp > u, 'V4': sv > uv}
            cuenta = {k: np.stack([np.bincount(mes_b, weights=w, minlength=nb) for w in
                                   (al & y, al & ~y, ~al & y)], axis=1) for k, al in alertas.items()}
            est = {k: metricas(c_.sum(axis=0)) for k, c_ in cuenta.items()}
            boot = {k: metricas(W @ c_) for k, c_ in cuenta.items()}
            for m in ('f1', 'recall', 'precision'):
                lo, hi = np.percentile(boot['PARAAD'][m] - boot['V4'][m], [2.5, 97.5])
                filas_ic.append(dict(anio=anio, a_ppb=a, punto=p, comparacion='PARAAD − V4', metrica=m,
                                     detector_1=float(est['PARAAD'][m]), detector_2=float(est['V4'][m]),
                                     diferencia=float(est['PARAAD'][m] - est['V4'][m]), ic_bajo=float(lo),
                                     ic_alto=float(hi), excluye_cero=bool(lo > 0 or hi < 0)))
            if a == ar.TAMANOS_FIJOS[0]:
                for d in DELTAS:
                    so = np.concatenate([paraad(R20 / f'examen/{anio}/puntajes/{c}_d{d}.csv').to_numpy().ravel()
                                         for c in corridas])[ok]
                    filas_prop.append(dict(anio=anio, detector='PARAAD', punto=p, forma='proporcional',
                                           tamano=f'δ = {d} %', estacion_dias=int(y.sum()), recall=float((so[y] > u).mean())))
            filas_prop.append(dict(anio=anio, detector='PARAAD', punto=p, forma='fijo', tamano=f'{a} ppb',
                                   estacion_dias=int(y.sum()), recall=float((sp[y] > u).mean())))
        print(f'{anio}, a = {a} ppb: PARAAD listo', flush=True)
    pd.DataFrame(filas).to_csv(base / 'resultados_paraad.csv', index=False)
    pd.DataFrame(filas_ic).to_csv(base / 'intervalos_paraad.csv', index=False)
    pd.DataFrame(filas_prop).to_csv(base / 'contra_proporcional_paraad.csv', index=False)


if __name__ == '__main__':
    main()
