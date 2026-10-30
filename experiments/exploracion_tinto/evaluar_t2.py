"""TINTO T2: métricas 2022 por estación-día de EH, ED, RH y RD contra L0 y T1 época 5.

Corre en la lap con los puntajes descargados de Colab. Mismo esquema que `evaluar_2022.py`:
las 9 661 estación-días comunes de T1, umbral propio con 2022 limpio (p99 y p99.9), métricas
agrupando los 10 calendarios y bootstrap pareado por bloques estación-mes contra L0.
L0 y T1 no se recalculan: se leen sus puntajes diarios guardados (modelos cargados de disco).
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/anomalias_red'))
T1 = ROOT / 'results/exploracion_tinto_2022/preparacion_colab_20261029/resultados_descargados/corrida1'
BASE = ROOT / 'results/anomalias_red_v1'
DELTAS = (100, 50, 20)
CALS = [f'entrenamiento_{n:02d}' for n in range(1, 11)]
VARIANTES = ['EH', 'ED', 'RH', 'RD']
REGLA = 0.02


def main(salidas, out):
    from src.detect import evaluacion_red as ev, estacion_dia as ed, anomalias_red as ar
    from metricas_estandar_revision8 import con_umbral
    from sklearn.metrics import average_precision_score
    out.mkdir(parents=True)
    comunes = pd.read_csv(T1 / 'dias_comunes.csv', index_col=0, parse_dates=True)
    targets, dates = list(comunes.columns), comunes.index
    common = comunes.to_numpy()
    assert common.sum() == 9661 and len(dates) == 365
    claves = ['limpia_2022'] + [f'{c}_d{d}' for d in DELTAS for c in CALS]

    scores, entrenamiento = {}, []
    for nombre, archivo in [('L0', 'L0_d50'), ('T1_epoca5', 'TINTO_epoca5')]:
        scores[nombre] = {k: pd.read_csv(T1 / f'{k}_{archivo}_dias.csv.gz', index_col=0)[targets].to_numpy()
                          for k in claves}
    for v in VARIANTES:
        for c in (1, 2):
            carpeta = salidas / f'{v}_c{c}'
            if not (carpeta / 'LISTO').exists():
                print('falta', carpeta.name)
                continue
            z = np.load(carpeta / 'puntajes_dia_2022.npz')
            scores[f'{v}_c{c}'] = {k: z[k] for k in claves}
            r = json.loads((carpeta / 'resultado.json').read_text())
            entrenamiento.append({k: r.get(k) for k in ['variante', 'corrida', 'parametros', 'ejemplos_ajuste',
                'positivas_ajuste', 'epocas', 'epoca_mejor', 'val_loss_mejor', 'paro_por_paciencia',
                'minutos_entrenamiento', 'gpu_nombre', 'tensorflow']})
    pd.DataFrame(entrenamiento).to_csv(out / 'entrenamiento.csv', index=False)
    for nombre, s in scores.items():
        for k, a in s.items():
            assert a.shape == common.shape and not np.isnan(a[common]).any(), (nombre, k)

    umbrales = {n: {p: ev.umbral_falsas_alarmas(s['limpia_2022'][common], fa) for p, fa in [('p99', .01), ('p999', .001)]}
                for n, s in scores.items()}
    (out / 'umbrales.json').write_text(json.dumps(umbrales, indent=1) + '\n')
    Y = {c: ed.etiquetas(ar.leer_plan(BASE / f'planes/plan_{c}.csv'), dates, targets).to_numpy()[common] for c in CALS}
    block = (np.repeat(dates.month.to_numpy() - 1, len(targets)) * len(targets)
             + np.tile(np.arange(len(targets)), len(dates))).reshape(common.shape)[common]
    filas, cuentas = [], {}
    for d in DELTAS:
        y = np.concatenate([Y[c] for c in CALS])
        bl = np.concatenate([block for _ in CALS])
        for n, s in scores.items():
            for version in ['con_ataque', 'sin_ataque']:
                x = np.concatenate([s[f'{c}_d{d}' if version == 'con_ataque' else 'limpia_2022'][common] for c in CALS])
                for p, u in umbrales[n].items():
                    a = x > u
                    filas.append(dict(delta_pct=d, detector=n, version=version, punto=p, umbral=u,
                                      estacion_dias=len(y), **con_umbral(y, a), AP=float(average_precision_score(y, x))))
                    if version == 'con_ataque':
                        cuentas[d, n, p] = np.stack([np.bincount(bl, weights=w, minlength=12 * 31)
                                                     for w in [a & y, a & ~y, ~a & y]], axis=1)
    res = pd.DataFrame(filas)
    res.to_csv(out / 'resultados.csv', index=False)

    # Bootstrap pareado contra L0 (bloques estación-mes, calendarios juntos), como T1.
    activos = np.bincount(block, minlength=12 * 31) > 0
    nb = int(activos.sum())
    W = np.random.default_rng([42, 29, 3]).multinomial(nb, np.full(nb, 1 / nb), size=2000)
    f1 = lambda a: np.divide(2 * a[..., 0], 2 * a[..., 0] + a[..., 1] + a[..., 2],
                             out=np.zeros(a.shape[:-1]), where=(2 * a[..., 0] + a[..., 1] + a[..., 2]) > 0)
    ic = []
    for d in DELTAS:
        for p in ['p99', 'p999']:
            ref = f1(W @ cuentas[d, 'L0', p][activos])
            for n in scores:
                if n == 'L0':
                    continue
                lo, hi = np.percentile(f1(W @ cuentas[d, n, p][activos]) - ref, [2.5, 97.5])
                ic.append(dict(delta_pct=d, punto=p, detector=n, IC95_bajo=lo, IC95_alto=hi))
    pd.DataFrame(ic).to_csv(out / 'intervalos_F1_contra_L0.csv', index=False)

    con = res[(res.version == 'con_ataque')]
    tabla = con.pivot_table(index='detector', columns=['punto', 'delta_pct'], values='f1')
    fbar = con[con.punto == 'p99'].groupby('detector').f1.mean()
    l0 = float(fbar['L0'])
    decision = {}
    for v in VARIANTES:
        corr = [fbar.get(f'{v}_c{c}') for c in (1, 2)]
        if None in corr:
            decision[v] = dict(Fbar=corr, pasa=None, nota='faltan corridas')
            continue
        decision[v] = dict(Fbar=[float(x) for x in corr], pasa=bool(min(corr) >= l0 + REGLA),
                           diferencia_entre_corridas=float(abs(corr[0] - corr[1])))
    resumen = dict(Fbar_L0=l0, umbral_regla=l0 + REGLA, Fbar=fbar.round(4).to_dict(), decision=decision,
                   origen='L0 y T1 cargados de disco (puntajes guardados); EH/ED/RH/RD recién entrenados en Colab GPU',
                   limite='2022 se usó para EarlyStopping y evaluación; comparación exploratoria, no examen')
    (out / 'resumen.json').write_text(json.dumps(resumen, indent=1, ensure_ascii=False) + '\n')
    pd.set_option('display.width', 200)
    print(tabla.round(4))
    print(json.dumps(resumen, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salidas', type=Path, required=True)
    ap.add_argument('--resultado', type=Path, required=True)
    a = ap.parse_args()
    if a.resultado.exists():
        ap.error('Usa una carpeta nueva.')
    main(a.salidas, a.resultado)
