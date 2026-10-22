"""Elección del segundo diseño supervisado con la validación 2022, δ = 100 % (progreso.md, 2026-10-16).

Ocho configuraciones: modelo (LSTM supervisado o Random Forest) × entradas (crudas o relativas
al perfil de 14 días) × calendarios de entrenamiento (10 o 20). Se entrena con las horas de
2020–2021 y se valida con las de 2022 de los calendarios 01–10, la misma validación para todas.
Criterio principal: detección de las horas con etiqueta 1 con un umbral que deja 5 % de falsas
alarmas en las horas con etiqueta 0 de esa validación. No toca 2023 ni 2024 y no guarda modelos.

Los calendarios 11–20 se generan en memoria con las reglas de los guardados (se comprueba que el
01 regenerado en memoria es igual a su matriz guardada).

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_variantes_2022.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402
from entrenar_lstm_sup import SELECCION, VALIDACION, leer, nuevo_modelo  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/variantes_2022'
D, EPOCAS, FA = 1.0, 10, 0.05


def matrices_20():
    """Las 10 matrices guardadas (δ = 100 %) y los calendarios 11–20 generados en memoria."""
    guardadas = [leer(f'{c}_d100')[0] for c in ar.calendarios_entrenamiento(n=10).corrida]
    ctx = em.contexto(RAIZ)
    cols = ar.columnas_entrada(ctx['definitiva']['inactivos'])
    v = ctx['valores'].loc['2020-01-01':'2022-12-31 23:00']
    alterables = alterables_v4()

    def generar(c):
        rec, cam = ar.aplicar(v, ar.plan_de(c, alterables), D)
        return ar.matriz_red(rec, cols, cam)
    todas = ar.calendarios_entrenamiento(n=20)
    pd.testing.assert_frame_equal(generar(todas.iloc[0]), guardadas[0], check_freq=False, check_dtype=False)
    return guardadas + [generar(c) for _, c in todas.iloc[10:].iterrows()]


def posiciones(index, desde, hasta):
    pos = np.flatnonzero((index >= pd.Timestamp(desde)) & (index <= pd.Timestamp(hasta)))
    return pos[pos >= lr.VENTANA - 1]


def deteccion(y, s, fa=FA):
    u = np.quantile(s[y == 0], 1 - fa)
    return 100 * float((s[y == 1] > u).mean())


def por_epoca():
    from tensorflow import keras

    class PorEpoca(keras.callbacks.Callback):
        """Detección y AUC en la validación 2022 al final de cada época (un solo fit, como el protocolo)."""
        def __init__(self, Xva, yva, filas, entradas, n):
            super().__init__()
            self.Xva, self.yva, self.filas, self.entradas, self.n = Xva, yva, filas, entradas, n

        def on_epoch_end(self, ep, logs=None):
            s = self.model.predict(self.Xva, batch_size=4096, verbose=0).ravel()
            self.filas.append(dict(modelo='lstm_supervisado', entradas=self.entradas, calendarios=self.n,
                                   epoca=ep + 1, deteccion_2022_fa5_pct=deteccion(self.yva, s),
                                   auc_2022=roc_auc_score(self.yva, s), val_loss=logs['val_loss']))
            print(self.filas[-1], flush=True)
    return PorEpoca


def main():
    PorEpoca = por_epoca()
    SALIDA.mkdir(parents=True, exist_ok=True)
    limpia_tr, _ = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    mats = matrices_20()
    idx = mats[0].index
    p_tr, p_va = posiciones(idx, *SELECCION), posiciones(idx, *VALIDACION)
    F = {'crudas': [ev.entradas(x, mu, sigma) for x in mats],
         'relativas': [ev.entradas_relativas(x, sigma) for x in mats]}
    Y = [x['anomalia_red'].to_numpy(np.float32) for x in mats]
    yva = np.concatenate([Y[k][p_va] for k in range(10)])
    filas = []
    for entradas in ('crudas', 'relativas'):
        for n in (10, 20):
            ytr = np.concatenate([Y[k][p_tr] for k in range(n)])
            # Random Forest: las 66 columnas de la hora t.
            Xtr = np.concatenate([F[entradas][k][p_tr] for k in range(n)])
            Xva = np.concatenate([F[entradas][k][p_va] for k in range(10)])
            fijar_semilla(42)
            rf = RandomForestClassifier(random_state=42, n_jobs=-1).fit(Xtr, ytr)
            s = rf.predict_proba(Xva)[:, 1]
            filas.append(dict(modelo='random_forest', entradas=entradas, calendarios=n, epoca=np.nan,
                              deteccion_2022_fa5_pct=deteccion(yva, s), auc_2022=roc_auc_score(yva, s)))
            print(filas[-1], flush=True)
            del rf, Xtr, Xva
            # LSTM supervisado: ventanas t−23…t, 10 épocas fijas.
            Xtr = np.concatenate([lr.ventanas(F[entradas][k], p_tr) for k in range(n)])
            Xva = np.concatenate([lr.ventanas(F[entradas][k], p_va) for k in range(10)])
            modelo = nuevo_modelo()
            modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=EPOCAS, batch_size=64, shuffle=True,
                       verbose=0, callbacks=[PorEpoca(Xva, yva, filas, entradas, n)])
            del modelo, Xtr, Xva
            pd.DataFrame(filas).to_csv(SALIDA / 'resultados.csv', index=False)
    r = pd.DataFrame(filas)
    mejor = (r.sort_values('deteccion_2022_fa5_pct', ascending=False)
              .groupby(['modelo', 'entradas', 'calendarios'], sort=False).head(1)
              .sort_values(['modelo', 'entradas', 'calendarios']))
    mejor.to_csv(SALIDA / 'mejor_por_configuracion.csv', index=False)
    print(mejor.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
