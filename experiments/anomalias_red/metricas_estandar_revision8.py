"""Métricas de presentación de la parte 2 en el examen 2024 (protocolo, revisión 9).

Uso (desde la raíz del repo, con la revisión 8 y la revisión 7 de Colab ya bajadas):

    .venv/bin/python experiments/anomalias_red/metricas_estandar_revision8.py

Se fijaron el 2026-10-23, después de ver los resultados, a pedido del tesista: no cambian ninguna
elección, umbral ni modelo. No entrena ni carga modelos: usa los puntajes y umbrales guardados y la
etiqueta de red de cada hora (`anomalia_red`), juntando los 10 calendarios.

- La unidad es la hora de red. Clase positiva = hora atacada.
- Con los umbrales del protocolo (5 % y 1 % de falsas alarmas en 2023 limpio): TP, FP, FN, TN,
  exactitud, precisión, recall, especificidad, tasa de falsas alarmas, F1, F2 y MCC.
- Sin umbral: ROC-AUC y PR-AUC (precisión promedio).
- Cada métrica se calcula también «sin ataque»: con los puntajes de 2024 limpio en las mismas horas
  y con las mismas etiquetas. Es su azar pareado, lo que saldría aunque el detector no viera el ataque.
- Dos referencias sin detector: «alertar siempre» y «nunca alertar».
Salida: results/anomalias_red_v1/analisis_revision8/metricas_estandar.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
OUT = SAL / 'analisis_revision8'
DETECTORES = {'LSTM con vecinas': 'lstm_sup_vecinas_a14_20cal', 'LSTM sin vecinas': 'colab_revision7/lstm_sup_relativas_20cal',
              'Regla de vecinas': 'regla_vecinas_a14', 'RF con vecinas': 'rf_vecinas_a14_20cal',
              'RF sin vecinas': 'colab_revision7/rf_relativas_20cal', 'V4': 'v4', 'IsolationForest': 'if'}
DELTAS = (100, 50, 20, 10, 5)
NIVELES = ('1', '5')


def puntajes(carpeta: Path) -> pd.DataFrame:
    if carpeta.parent.name == 'v4':                       # el V4 guarda (corrida, puntaje/estación)
        s = pd.read_csv(carpeta / 'puntajes.csv.gz', header=[0, 1], index_col=0).xs('puntaje', axis=1, level=1)
    else:
        s = pd.read_csv(carpeta / 'puntajes.csv.gz', index_col='timestamp')
    s.index = pd.to_datetime(s.index)
    return s.astype(float)


def etiquetas(d: int, corridas) -> dict[str, pd.Series]:
    return {c: pd.read_csv(SAL / f'matrices/matriz_{c}_d{d}.csv.gz', index_col='timestamp', parse_dates=True,
                           usecols=['timestamp', 'anomalia_red'])['anomalia_red'].astype(bool) for c in corridas}


def fbeta(p: float, r: float, beta: float) -> float:
    return (1 + beta ** 2) * p * r / (beta ** 2 * p + r) if p + r > 0 else 0.0


def con_umbral(y: np.ndarray, a: np.ndarray) -> dict:
    tp, fp = int((a & y).sum()), int((a & ~y).sum())
    fn, tn = int((~a & y).sum()), int((~a & ~y).sum())
    p = tp / (tp + fp) if tp + fp else np.nan
    r = tp / (tp + fn)
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, exactitud=(tp + tn) / len(y), precision=p, recall=r,
                especificidad=tn / (tn + fp), falsas_alarmas=fp / (fp + tn),
                f1=fbeta(0 if np.isnan(p) else p, r, 1), f2=fbeta(0 if np.isnan(p) else p, r, 2),
                mcc=matthews_corrcoef(y, a), alertan=a.mean())


def main():
    filas = []
    for d in DELTAS:
        y_por = None
        for n, c in DETECTORES.items():
            carpeta = SAL / c / f'd{d}'
            s = puntajes(carpeta)
            m = pd.read_csv(carpeta / 'metricas.csv')
            col = 'nivel' if 'nivel' in m else 'nivel_fa_pct'
            corridas = sorted(m.corrida.unique())
            if y_por is None:
                y_por = etiquetas(d, corridas)
                y = np.concatenate([y_por[k].to_numpy() for k in corridas])
                for ref, a in (('Alertar siempre', np.ones_like(y)), ('Nunca alertar', np.zeros_like(y))):
                    for k in NIVELES:
                        filas.append(dict(detector=ref, delta_pct=d, version='referencia', nivel_fa_pct=int(k),
                                          horas=len(y), atacadas=y.mean(), roc_auc=0.5, pr_auc=y.mean(), **con_umbral(y, a)))
            for version, fuente in (('examen', None), ('sin ataque', 'limpia_2024')):
                col_s = (lambda k: k) if fuente is None else (lambda k: fuente)
                p = np.concatenate([s.loc[y_por[k].index, col_s(k)].to_numpy() for k in corridas])
                sin_umbral = dict(roc_auc=roc_auc_score(y, p), pr_auc=average_precision_score(y, p))
                for k in NIVELES:
                    u = m[m[col].astype(str) == k].set_index('corrida').umbral
                    a = np.concatenate([(s.loc[y_por[r].index, col_s(r)] > u[r]).to_numpy() for r in corridas])
                    filas.append(dict(detector=n, delta_pct=d, version=version, nivel_fa_pct=int(k), horas=len(y),
                                      atacadas=y.mean(), **sin_umbral, **con_umbral(y, a)))
    f = pd.DataFrame(filas)
    OUT.mkdir(parents=True, exist_ok=True)
    f.to_csv(OUT / 'metricas_estandar.csv', index=False)

    pd.set_option('display.width', 250)
    principales = ['LSTM con vecinas', 'LSTM sin vecinas', 'Regla de vecinas', 'V4']
    for k in (1, 5):
        g = f[(f.nivel_fa_pct == k) & f.detector.isin(principales + ['Alertar siempre', 'Nunca alertar'])]
        print(f'\n== Nivel {k} %: examen (sin ataque)')
        for d in DELTAS:
            print(f'\nδ = {d} %  (horas atacadas {100 * g[g.delta_pct == d].atacadas.iloc[0]:.1f} %)')
            for n in principales + ['Alertar siempre', 'Nunca alertar']:
                e = g[(g.delta_pct == d) & (g.detector == n) & (g.version != 'sin ataque')].iloc[0]
                z = g[(g.delta_pct == d) & (g.detector == n) & (g.version == 'sin ataque')]
                z = z.iloc[0] if len(z) else None
                v = lambda c, fm='{:.2f}': fm.format(e[c]) + (f' ({fm.format(z[c])})' if z is not None else '')  # noqa: E731
                print(f'  {n:17s} TP {e.tp:5d} FP {e.fp:5d} FN {e.fn:5d} TN {e.tn:5d} | exact {v("exactitud")} '
                      f'prec {v("precision")} rec {v("recall")} F1 {v("f1")} F2 {v("f2")} MCC {v("mcc")} '
                      f'| ROC {v("roc_auc")} PR {v("pr_auc")}')


if __name__ == '__main__':
    main()
