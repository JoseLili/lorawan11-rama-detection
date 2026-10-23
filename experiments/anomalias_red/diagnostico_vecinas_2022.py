"""Elección de la forma de la columna de vecinas con la validación 2022 (protocolo, revisión 8).

El LSTM supervisado de la revisión 7 (arquitectura, lotes, barajado, fijar_semilla(42)) entrenado
10 épocas fijas con las horas de 2020–2021 de los 20 calendarios, y validado con las de 2022 de los
calendarios 01–10, con cinco entradas: las relativas de la revisión 7 (referencia, 66 columnas) y
las cuatro formas de la columna de vecinas (a14, afija, b14, bfija; 98 columnas). La referencia
fija y la escala de la columna se ajustan con 2020–2021 limpio. Severidades: δ = 20 % (decide) y
δ = 100 % (sólo se reporta).

Criterio: detección de las horas con etiqueta 1 con un umbral que deja 5 % de falsas alarmas en las
de etiqueta 0 de la validación, en la mejor de las 10 épocas. Gana la forma con mayor detección con
δ = 20 %; si su ventaja sobre a14 es menor que 2 puntos, se queda a14. Como contraste se reportan
la precisión, el F1 y el AUC con el mismo umbral. No toca 2023 ni 2024 y no guarda modelos.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_vecinas_2022.py [--salida DIR] [--prueba]
     (--prueba: 2 calendarios, 1 época y 1 de cada 50 ventanas; sólo comprueba que todo corre)
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
from sklearn.metrics import roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from diagnostico_variantes_2022 import posiciones  # noqa: E402
from entrenar_lstm_sup import CONFIG, SELECCION, VALIDACION, leer, nuevo_modelo, parametros_vecinas  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/vecinas_2022'
EPOCAS, DELTAS, FA, MARGEN = 10, (20, 100), 0.05, 2.0
VARIANTES = ('relativas',) + ev.FORMAS            # la primera es la revisión 7, sin vecinas


def medidas(y, s, fa=FA) -> dict:
    """Detección, precisión y F1 con el umbral que deja `fa` de falsas alarmas en las etiquetas 0."""
    u = np.quantile(s[y == 0], 1 - fa)
    tp, fp = int((s[y == 1] > u).sum()), int((s[y == 0] > u).sum())
    rec = tp / int((y == 1).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    return dict(deteccion_2022_fa5_pct=100 * rec, precision_pct=100 * prec,
                f1=2 * prec * rec / (prec + rec) if prec + rec else 0.0, auc_2022=float(roc_auc_score(y, s)))


def por_epoca():
    from tensorflow import keras

    class PorEpoca(keras.callbacks.Callback):
        def __init__(self, Xva, yva, filas, base):
            super().__init__()
            self.Xva, self.yva, self.filas, self.base = Xva, yva, filas, base

        def on_epoch_end(self, ep, logs=None):
            s = self.model.predict(self.Xva, batch_size=4096, verbose=0).ravel()
            self.filas.append(dict(self.base, epoca=ep + 1, **medidas(self.yva, s), val_loss=logs['val_loss']))
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.filas[-1].items()}, flush=True)
    return PorEpoca


def elegir(resumen: pd.DataFrame) -> dict:
    """La regla de la revisión 8, con la detección de la mejor época y δ = 20 %."""
    r = resumen[(resumen.delta_pct == 20) & (resumen.variante.isin(ev.FORMAS))].set_index('variante')
    mejor = r.deteccion_mejor_pct.idxmax()
    ventaja = float(r.at[mejor, 'deteccion_mejor_pct'] - r.at['a14', 'deteccion_mejor_pct'])
    elegida = mejor if mejor == 'a14' or ventaja >= MARGEN else 'a14'
    ref = resumen[(resumen.delta_pct == 20) & (resumen.variante == 'relativas')].deteccion_mejor_pct.iat[0]
    return dict(regla=f'gana la forma con mayor detección (δ = 20 %, mejor de {EPOCAS} épocas); si su ventaja '
                      f'sobre a14 es menor que {MARGEN} puntos, se queda a14',
                mayor=mejor, ventaja_sobre_a14=round(ventaja, 3), forma_elegida=elegida,
                deteccion_elegida_pct=round(float(r.at[elegida, 'deteccion_mejor_pct']), 3),
                deteccion_revision7_pct=round(float(ref), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    epocas, n_tr, n_va, paso = (1, 2, 1, 50) if prueba else (EPOCAS, 20, 10, 1)
    salida.mkdir(parents=True, exist_ok=True)
    PorEpoca = por_epoca()
    limpia_tr, _ = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia_tr)
    limpia_ajuste = limpia_tr.loc[SELECCION[0]:SELECCION[1]]          # 2020–2021 limpio
    params = {f: parametros_vecinas(f, limpia_ajuste, sigma) for f in ev.FORMAS}
    filas = []
    for d in DELTAS:
        mats = [leer(f'{c}_d{d}')[0] for c in ar.calendarios_entrenamiento(n=n_tr).corrida]
        idx = mats[0].index
        assert all(x.index.equals(idx) for x in mats)
        p_tr, p_va = posiciones(idx, *SELECCION)[::paso], posiciones(idx, *VALIDACION)[::paso]
        Y = [x['anomalia_red'].to_numpy(np.float32) for x in mats]
        ytr = np.concatenate([Y[k][p_tr] for k in range(n_tr)])
        yva = np.concatenate([Y[k][p_va] for k in range(n_va)])
        for variante in VARIANTES:
            tipo, vec = ('relativas', None) if variante == 'relativas' else ('vecinas', params[variante])
            F = [ev.entradas_de(tipo, x, None, sigma, vec) for x in mats]
            Xtr = np.concatenate([lr.ventanas(F[k], p_tr) for k in range(n_tr)])
            Xva = np.concatenate([lr.ventanas(F[k], p_va) for k in range(n_va)])
            del F
            base = dict(delta_pct=d, variante=variante, columnas=int(Xtr.shape[2]), ventanas=len(ytr))
            print(base, flush=True)
            modelo = nuevo_modelo(Xtr.shape[2])
            modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=epocas, batch_size=CONFIG['batch'],
                       shuffle=CONFIG['shuffle'], verbose=0, callbacks=[PorEpoca(Xva, yva, filas, base)])
            del modelo, Xtr, Xva
            pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)
        del mats, Y
    r = pd.DataFrame(filas)

    def resumir(x):
        b = x.loc[x.deteccion_2022_fa5_pct.idxmax()]
        return pd.Series(dict(mejor_epoca=int(b.epoca), deteccion_mejor_pct=b.deteccion_2022_fa5_pct,
                              deteccion_promedio_pct=x.deteccion_2022_fa5_pct.mean(), precision_pct=b.precision_pct,
                              f1=b.f1, auc_2022=b.auc_2022, epoca_val_loss_min=int(x.loc[x.val_loss.idxmin(), 'epoca']),
                              val_loss_min=x.val_loss.min()))
    resumen = (r.groupby(['delta_pct', 'variante', 'columnas', 'ventanas'], sort=False)
               .apply(resumir, include_groups=False).reset_index())
    resumen.to_csv(salida / 'resumen.csv', index=False)
    eleccion = elegir(resumen)
    eleccion.update(prueba=prueba, vecinas=params['a14'].vecinas)
    (salida / 'eleccion.json').write_text(json.dumps(eleccion, indent=2, ensure_ascii=False))
    print(resumen.round(3).to_string(index=False))
    print(json.dumps({k: v for k, v in eleccion.items() if k != 'vecinas'}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
