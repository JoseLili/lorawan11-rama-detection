"""Curva de aprendizaje con la validación 2022: ¿más años de entrenamiento ayudarían? (progreso.md, 2026-10-22).

El LSTM supervisado de la revisión 7 (entradas relativas, misma arquitectura y lotes), entrenado 10
épocas fijas con cuatro conjuntos y validado siempre con las horas de 2022 de los calendarios 01–10:

    1. sólo 2020, calendarios 01–20;     2. sólo 2021, calendarios 01–20;
    3. 2020–2021, calendarios 01–20 (la revisión 7);
    4. sólo 2021, calendarios 01–40 (tantos ejemplos como la 3, pero de un solo año).

Criterio: detección de las horas con etiqueta 1 con un umbral que deja 5 % de falsas alarmas en las
horas con etiqueta 0 de la validación, con δ = 100 % y δ = 20 %. Los calendarios 21–40 se generan en
memoria con las reglas de los guardados (se comprueba con el 01). No toca 2023 ni 2024 y no guarda
modelos.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_curva_aprendizaje_2022.py [--salida DIR]
     [--delta 100] [--solo 3]   (sólo esa severidad y esa configuración: la prueba de equivalencia
                                 de otra máquina repite la 3 con δ = 100 % y la compara época por época)
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
from sklearn.metrics import roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from diagnostico_variantes_2022 import deteccion, posiciones  # noqa: E402
from entrenar_lstm_sup import CONFIG, VALIDACION, leer, nuevo_modelo  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/curva_aprendizaje_2022'
EPOCAS, DELTAS = 10, (100, 20)
AÑOS = {'2020': ('2020-01-01', '2020-12-31 23:00'), '2021': ('2021-01-01', '2021-12-31 23:00'),
        '2020-2021': ('2020-01-01', '2021-12-31 23:00')}
CONFIGURACIONES = [(1, '2020', 20), (2, '2021', 20), (3, '2020-2021', 20), (4, '2021', 40)]


def matrices_40(d):
    """Las 20 matrices guardadas de entrenamiento con δ = d % y los calendarios 21–40 generados en memoria."""
    guardadas = [leer(f'{c}_d{d}')[0] for c in ar.calendarios_entrenamiento(n=20).corrida]
    ctx = em.contexto(RAIZ)
    cols = ar.columnas_entrada(ctx['definitiva']['inactivos'])
    v = ctx['valores'].loc['2020-01-01':'2022-12-31 23:00']
    alterables = alterables_v4()

    def generar(c):
        rec, cam = ar.aplicar(v, ar.plan_de(c, alterables), d / 100)
        return ar.matriz_red(rec, cols, cam)
    todas = ar.calendarios_entrenamiento(n=40)
    pd.testing.assert_frame_equal(generar(todas.iloc[0]), guardadas[0], check_freq=False, check_dtype=False)
    return guardadas + [generar(c) for _, c in todas.iloc[20:].iterrows()]


def por_epoca():
    from tensorflow import keras

    class PorEpoca(keras.callbacks.Callback):
        """Detección, AUC y pérdida en la validación 2022 al final de cada época (un solo fit)."""
        def __init__(self, Xva, yva, filas, base):
            super().__init__()
            self.Xva, self.yva, self.filas, self.base = Xva, yva, filas, base

        def on_epoch_end(self, ep, logs=None):
            s = self.model.predict(self.Xva, batch_size=4096, verbose=0).ravel()
            self.filas.append(dict(self.base, epoca=ep + 1, deteccion_2022_fa5_pct=deteccion(self.yva, s),
                                   auc_2022=roc_auc_score(self.yva, s), val_loss=logs['val_loss']))
            print(self.filas[-1], flush=True)
    return PorEpoca


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--delta', type=int, choices=DELTAS, nargs='+', default=list(DELTAS))
    ap.add_argument('--solo', type=int, choices=[c[0] for c in CONFIGURACIONES], nargs='+')
    args = ap.parse_args()
    salida, deltas = args.salida, args.delta
    configuraciones = [c for c in CONFIGURACIONES if args.solo is None or c[0] in args.solo]
    salida.mkdir(parents=True, exist_ok=True)
    PorEpoca = por_epoca()
    limpia_tr, _ = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia_tr)
    filas = []
    for d in deltas:
        mats = matrices_40(d)
        idx = mats[0].index
        assert all(x.index.equals(idx) for x in mats)
        F = [ev.entradas_relativas(x, sigma) for x in mats]
        Y = [x['anomalia_red'].to_numpy(np.float32) for x in mats]
        p_va = posiciones(idx, *VALIDACION)
        Xva = np.concatenate([lr.ventanas(F[k], p_va) for k in range(10)])
        yva = np.concatenate([Y[k][p_va] for k in range(10)])
        for num, años, n in configuraciones:
            p_tr = posiciones(idx, *AÑOS[años])
            Xtr = np.concatenate([lr.ventanas(F[k], p_tr) for k in range(n)])
            ytr = np.concatenate([Y[k][p_tr] for k in range(n)])
            base = dict(delta_pct=d, configuracion=num, años=años, calendarios=n, ventanas=len(ytr),
                        etiqueta_1_pct=round(100 * float(ytr.mean()), 2))
            print(base, flush=True)
            modelo = nuevo_modelo()
            modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=EPOCAS, batch_size=CONFIG['batch'],
                       shuffle=CONFIG['shuffle'], verbose=0, callbacks=[PorEpoca(Xva, yva, filas, base)])
            del modelo, Xtr, ytr
            pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)
        del mats, F, Y, Xva, yva
    r = pd.DataFrame(filas)
    claves = ['delta_pct', 'configuracion', 'años', 'calendarios', 'ventanas']
    g = r.groupby(claves, sort=False)
    resumen = g.apply(lambda x: pd.Series(dict(
        mejor_epoca=int(x.loc[x.deteccion_2022_fa5_pct.idxmax(), 'epoca']),
        deteccion_mejor_pct=x.deteccion_2022_fa5_pct.max(), deteccion_promedio_10_pct=x.deteccion_2022_fa5_pct.mean(),
        epoca_val_loss_min=int(x.loc[x.val_loss.idxmin(), 'epoca']), val_loss_min=x.val_loss.min())),
        include_groups=False).reset_index()
    resumen.to_csv(salida / 'resumen.csv', index=False)
    print(resumen.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
