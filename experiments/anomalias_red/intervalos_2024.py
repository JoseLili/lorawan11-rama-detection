"""Revisión 16 (1): intervalos de confianza de L0 − R3 en el examen 2024, con p99 y p99.9 (en la lap).

Uso: .venv/bin/python experiments/anomalias_red/intervalos_2024.py [--salida DIR]

Mismos datos y umbrales que el examen de la revisión 14 y la revisión 15: L0 son los puntajes
guardados de sus modelos definitivos; R3 se recalcula; estación-días válidas para los dos; umbrales
de 2023 limpio. Bootstrap por bloques: un bloque es una estación en un mes con sus 10 calendarios
juntos (372 bloques); 2 000 remuestreos con `default_rng([42, 16, 1])`, los mismos para todos los δ
y puntos, y para los dos detectores. Se reporta el intervalo del 2.5 al 97.5 % del F1, el recall y
la precisión de cada uno y de su diferencia. No carga modelos ni entrena.
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

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from puntos_operacion_2024 import EXAMEN_14, LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'comprobaciones_2024/intervalos'
PLANES = SAL / 'planes'
AGREGACION = 'promedio_dia'
B = 2000


def metricas(c):
    """c: (..., 3) con TP, FP, FN → F1, recall y precisión."""
    tp, fp, fn = c[..., 0], c[..., 1], c[..., 2]
    with np.errstate(invalid='ignore', divide='ignore'):
        return dict(f1=np.where(tp > 0, 2 * tp / (2 * tp + fp + fn), 0.0), recall=tp / (tp + fn),
                    precision=np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1), 0.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    deltas = [round(100 * d) for d in ar.DELTAS]
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA].tolist()
    examen = [f'{c}_d{d}' for d in deltas for c in corridas]
    limpia_tr, _, sigma, vec = normalizacion_y_vecinas('mediana')
    r3 = {n: ed.dominancia(ed.juntar_dia(v[objetivos], AGREGACION), vec.vecinas)
          for n, v, _ in valores_regla(examen, limpia_tr, sigma, vec)}
    dias = r3['limpia_2024'].index
    Y = np.concatenate([ed.etiquetas(ar.leer_plan(PLANES / f'plan_{c}.csv'), dias, objetivos).to_numpy().ravel()
                        for c in corridas])
    bloque_1 = (np.arange(len(objetivos))[None, :] * 12 + (dias.month.to_numpy() - 1)[:, None]).ravel()
    bloques = np.tile(bloque_1, len(corridas))
    n_bloques = len(objetivos) * 12
    rng = np.random.default_rng([42, 16, 1])
    W = rng.multinomial(n_bloques, np.full(n_bloques, 1 / n_bloques), size=B)        # B × bloques

    filas, puntuales = [], []
    for d in deltas:
        L = leer_dias(LSTM / f'd{d}' / 'dias_examen.csv.gz')
        por = {'L0': {k: v[AGREGACION] for k, v in L.items()},
               'R3': {k: r3[k if k.startswith('limpia') else f'{k}_d{d}'] for k in ['limpia_2023', 'limpia_2024'] + corridas}}
        v23 = por['R3']['limpia_2023'].notna() & por['L0']['limpia_2023'].notna()
        v24 = por['R3']['limpia_2024'].notna() & por['L0']['limpia_2024'].notna()
        comun = np.tile(v24.to_numpy().ravel(), len(corridas))
        y, b = Y[comun], bloques[comun]
        for punto, fa in PUNTOS.items():
            conteo = {}
            for nombre, v in por.items():
                u = ev.umbral_falsas_alarmas(v['limpia_2023'][v23].stack().dropna().to_numpy(), fa)
                alerta = np.concatenate([v[c].to_numpy().ravel() for c in corridas])[comun] > u
                c = np.stack([np.bincount(b, weights=w, minlength=n_bloques)
                              for w in (alerta & y, alerta & ~y, ~alerta & y)], axis=1)   # bloques × 3
                conteo[nombre] = c
                puntuales.append(dict(delta_pct=d, punto=punto, detector=nombre, tp=int(c[:, 0].sum()),
                                      fp=int(c[:, 1].sum()), fn=int(c[:, 2].sum())))
            est = {k: metricas(c.sum(axis=0)) for k, c in conteo.items()}
            boot = {k: metricas(W @ c) for k, c in conteo.items()}
            for m in ('f1', 'recall', 'precision'):
                dif = boot['L0'][m] - boot['R3'][m]
                lo, hi = np.percentile(dif, [2.5, 97.5])
                fila = dict(delta_pct=d, punto=punto, metrica=m)
                for k in ('L0', 'R3'):
                    a, z = np.percentile(boot[k][m], [2.5, 97.5])
                    fila.update({k: float(est[k][m]), f'{k}_ic_bajo': float(a), f'{k}_ic_alto': float(z)})
                fila.update(diferencia=float(est['L0'][m] - est['R3'][m]), dif_ic_bajo=float(lo), dif_ic_alto=float(hi),
                            excluye_cero=bool(lo > 0 or hi < 0))
                filas.append(fila)
        print(f'δ = {d} %: listo', flush=True)

    r = pd.DataFrame(filas)
    r.to_csv(args.salida / 'intervalos.csv', index=False)
    puntuales = pd.DataFrame(puntuales)
    e14 = pd.read_csv(EXAMEN_14)
    e14 = e14[(e14.version == 'con ataque') & (e14.nivel_fa_pct == 1) & e14.detector.isin(['L0', 'R3'])]
    mio = puntuales[puntuales.punto == 'p99'].set_index(['delta_pct', 'detector'])[['tp', 'fp', 'fn']].sort_index()
    control = bool(mio.equals(e14.set_index(['delta_pct', 'detector'])[['tp', 'fp', 'fn']].sort_index()))
    (args.salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=16, comprobacion='intervalos', remuestreos=B, bloques=n_bloques,
        bloque='estación × mes, con los 10 calendarios juntos', semilla=[42, 16, 1], puntos=PUNTOS,
        control_p99_igual_al_examen=control, origen_l0='puntajes guardados del modelo definitivo (revisión 14)'),
        indent=2, ensure_ascii=False))
    print('control p99 igual al examen de la revisión 14:', control)
    print(r[r.metrica == 'f1'].round(3).to_string(index=False))


if __name__ == '__main__':
    main()
