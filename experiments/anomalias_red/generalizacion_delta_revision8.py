"""¿Cómo generalizan los LSTM supervisados a un δ distinto del de su entrenamiento? (exploratorio).

Uso (desde la raíz del repo, con la revisión 8 y la revisión 7 de Colab ya bajadas):

    .venv/bin/python experiments/anomalias_red/generalizacion_delta_revision8.py

Se hizo el 2026-10-23, después de ver los resultados, a pedido del tesista, para comparar en
igualdad con los detectores no supervisados (V4, IsolationForest) y la regla, que tienen un solo
puntaje para todos los δ. No entrena: carga de disco los modelos definitivos (`modelo.keras`) del
LSTM con vecinas (revisión 8) y del LSTM sin vecinas (revisión 7 en Colab) y examina cada uno con los
cinco δ del examen 2024. Los umbrales de 1 y 5 % se recalculan en la lap con 2023 limpio, como en
`entrenar_lstm_sup.py`; la diagonal (δ de entrenamiento = δ del examen) se compara con lo guardado.
Los Random Forest quedan fuera: los de la revisión 8 no se bajaron de Colab.
Salida: results/anomalias_red_v1/analisis_revision8/generalizacion_delta.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES = SAL / 'matrices'
OUT = SAL / 'analisis_revision8'
MODELOS = {'LSTM con vecinas': ('vecinas', 'a14', SAL / 'lstm_sup_vecinas_a14_20cal'),
           'LSTM sin vecinas': ('relativas', None, SAL / 'colab_revision7/lstm_sup_relativas_20cal')}
DELTAS = (100, 50, 20, 10, 5)
NIVELES = (0.01, 0.05)


def leer(nombre: str) -> pd.DataFrame:
    return ar.leer_matriz(MATRICES / f'matriz_{nombre}.csv.gz')


def ventanas(previa, matriz, tipo, mu, sigma, vec) -> np.ndarray:
    x = ev.con_historia(previa, matriz)
    return lr.ventanas(ev.entradas_de(tipo, x, mu, sigma, vec), np.arange(len(previa), len(x)))


def main():
    from tensorflow import keras
    from entrenar_lstm_sup import parametros_vecinas

    pd.set_option('display.width', 220)
    limpia_tr, cal, limpia = leer('limpia_2020_2022'), leer('limpia_2023'), leer('limpia_2024')
    historia = ev.con_historia(limpia_tr, cal)
    mu, sigma = ev.normalizacion(limpia_tr)
    corridas = list(ar.corridas().iloc[1:].corrida)
    filas, control = [], []
    for nombre, (tipo, forma, carpeta) in MODELOS.items():
        vec = parametros_vecinas(forma, limpia_tr, sigma) if forma else None
        modelos = {d: keras.models.load_model(carpeta / f'd{d}/modelo.keras', compile=False) for d in DELTAS}
        pred = lambda d, X: modelos[d].predict(X, batch_size=1024, verbose=0).ravel().astype(np.float64)  # noqa: E731
        X = ventanas(limpia_tr, cal, tipo, mu, sigma, vec)
        s_cal = {d: pred(d, X) for d in DELTAS}
        X = ventanas(historia, limpia, tipo, mu, sigma, vec)
        s_lim = {d: pd.Series(pred(d, X), index=limpia.index) for d in DELTAS}
        umbral = {d: {a: ev.umbral_falsas_alarmas(s_cal[d], a) for a in NIVELES} for d in DELTAS}
        guardado = {d: pd.read_csv(carpeta / f'd{d}/puntajes.csv.gz', index_col='timestamp', parse_dates=True) for d in DELTAS}
        for d in DELTAS:
            m = pd.read_csv(carpeta / f'd{d}/metricas.csv')
            for a in NIVELES:
                u_g = m[m.nivel_fa_pct == round(100 * a)].umbral.iloc[0]
                control.append(dict(modelo=nombre, delta_entrenamiento=d, nivel=a, umbral_lap=umbral[d][a], umbral_guardado=u_g))
        for dt in DELTAS:
            ys, ss = [], {d: [] for d in DELTAS}
            for c in corridas:
                x = leer(f'{c}_d{dt}')
                ys.append(x['anomalia_red'].astype(bool).to_numpy())
                X = ventanas(historia, x, tipo, mu, sigma, vec)
                for d in DELTAS:
                    s = pred(d, X)
                    ss[d].append(s)
                    if d == dt:
                        control.append(dict(modelo=nombre, delta_entrenamiento=d, corrida=c,
                                            dif_max_puntaje=float(np.abs(s - guardado[d][c].loc[x.index].to_numpy()).max())))
            y = np.concatenate(ys)
            for d in DELTAS:
                s = np.concatenate(ss[d])
                sl = np.concatenate([s_lim[d].to_numpy()] * len(corridas))
                for a in NIVELES:
                    for version, sc in (('examen', s), ('sin ataque', sl)):
                        r = con_umbral(y, sc > umbral[d][a])
                        filas.append(dict(modelo=nombre, delta_entrenamiento=d, delta_examen=dt,
                                          nivel_fa_pct=round(100 * a), version=version,
                                          pr_auc=average_precision_score(y, sc), **r))
            print(f'{nombre}: examen δ = {dt} % listo', flush=True)
        del modelos
    f = pd.DataFrame(filas)
    f.to_csv(OUT / 'generalizacion_delta.csv', index=False)
    control = pd.DataFrame(control)
    control.to_csv(OUT / 'generalizacion_delta_control.csv', index=False)
    u = control.dropna(subset=['umbral_lap'])
    print(f'\nControl: puntajes de la diagonal frente a los guardados, diferencia máxima '
          f'{control.dif_max_puntaje.max():.1e}; umbrales, diferencia máxima '
          f'{(u.umbral_lap - u.umbral_guardado).abs().max():.1e}')
    for nombre in MODELOS:
        for k in (1, 5):
            e = f[(f.modelo == nombre) & (f.nivel_fa_pct == k) & (f.version == 'examen')].set_index(['delta_examen', 'delta_entrenamiento'])
            z = f[(f.modelo == nombre) & (f.nivel_fa_pct == k) & (f.version == 'sin ataque')].set_index(['delta_examen', 'delta_entrenamiento'])
            for col in ('f1', 'recall'):
                t = (e[col].round(2).astype(str) + ' (' + z[col].round(2).astype(str) + ')').unstack('delta_entrenamiento')
                print(f'\n{nombre}, nivel {k} %, {col}: filas = δ del examen, columnas = δ del entrenamiento')
                print(t.loc[list(DELTAS), list(DELTAS)].to_string())
        e = f[(f.modelo == nombre) & (f.nivel_fa_pct == 1) & (f.version == 'examen')].pivot(
            index='delta_examen', columns='delta_entrenamiento', values='pr_auc')
        print(f'\n{nombre}, PR-AUC (sin umbral): filas = δ del examen, columnas = δ del entrenamiento')
        print(e.loc[list(DELTAS), list(DELTAS)].round(3).to_string())


if __name__ == '__main__':
    main()
