"""Elección de la referencia de 14 días con la validación 2022 (protocolo, revisión 10).

Compara, con los mismos datos y la misma semilla, el LSTM supervisado con vecinas de la revisión 8
(forma a14, perfil de 14 días con la **media**) y el de la revisión 10 (el mismo, con la **mediana**
de 14 días en las entradas relativas y en la columna de vecinas). Entrena 10 épocas fijas con las
horas de 2020–2021 de los 20 calendarios y valida con las de 2022 de los calendarios 01–10, como la
elección de la revisión 8. La escala de la columna se ajusta con 2020–2021 limpio. δ = 100 y 50 %
deciden; δ = 20 % sólo se reporta. No toca 2023 ni 2024 y no guarda modelos.

Medidas por época, con umbrales que dejan 1 y 5 % de falsas alarmas en las horas con etiqueta 0 de
la validación: F1, recall y precisión; PR-AUC; pérdida de validación; y, con 1 %, las falsas
alarmas en las horas normales de los 14 días posteriores a un ataque y en las demás (lo que la
mediana busca bajar).

Regla, fijada antes de correrla (protocolo, revisión 10): para cada variante y δ se toma la época
de menor pérdida de validación (la que elegiría el EarlyStopping del modelo definitivo). Si el F1
con 1 % de la mediana, promediado entre δ = 100 y 50 %, supera al de la media en 0.02 o más, se
adopta la mediana; si no, se queda la media y la revisión 10 no se examina con 2024.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_referencia_2022.py [--salida DIR] [--prueba]
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
from sklearn.metrics import average_precision_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from diagnostico_variantes_2022 import posiciones  # noqa: E402
from entrenar_lstm_sup import CONFIG, SELECCION, VALIDACION, leer, nuevo_modelo, parametros_vecinas  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/referencia_2022'
PLANES = RAIZ / 'results/anomalias_red_v1/planes'
EPOCAS, DELTAS, DECIDEN, MARGEN = 10, (100, 50, 20), (100, 50), 0.02
VARIANTES = ('media', 'mediana')            # la primera es la revisión 8
DIAS_TRAS = 14


def tras_ataque(index: pd.DatetimeIndex, plan: pd.DataFrame) -> np.ndarray:
    """True en las horas de los `DIAS_TRAS` días siguientes al fin de un ataque terminado."""
    fines = np.sort(plan.fin.to_numpy(dtype='datetime64[ns]'))
    t = index.to_numpy(dtype='datetime64[ns]')
    k = np.searchsorted(fines, t, side='left') - 1
    h = np.where(k >= 0, (t - fines[np.clip(k, 0, None)]) / np.timedelta64(1, 'h'), np.inf)
    return (h >= 1) & (h <= 24 * DIAS_TRAS)


def medidas(y, s, tras) -> dict:
    out = dict(pr_auc=float(average_precision_score(y, s)))
    for fa in (0.01, 0.05):
        k = round(100 * fa)
        u = np.quantile(s[y == 0], 1 - fa)
        a = s > u
        tp, fp = int((a & (y == 1)).sum()), int((a & (y == 0)).sum())
        rec = tp / int((y == 1).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        out.update({f'f1_{k}': 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
                    f'recall_{k}': rec, f'precision_{k}': prec})
        if k == 1:
            normal = y == 0
            out.update(fa_tras_ataque_1=float(a[normal & tras].mean()), fa_resto_1=float(a[normal & ~tras].mean()))
    return out


def por_epoca():
    from tensorflow import keras

    class PorEpoca(keras.callbacks.Callback):
        def __init__(self, Xva, yva, tras, filas, base):
            super().__init__()
            self.Xva, self.yva, self.tras, self.filas, self.base = Xva, yva, tras, filas, base

        def on_epoch_end(self, ep, logs=None):
            s = self.model.predict(self.Xva, batch_size=4096, verbose=0).ravel()
            self.filas.append(dict(self.base, epoca=ep + 1, **medidas(self.yva, s, self.tras), val_loss=logs['val_loss']))
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.filas[-1].items()}, flush=True)
    return PorEpoca


def elegir(resumen: pd.DataFrame) -> dict:
    """La regla de la revisión 10, con la época de menor pérdida de validación."""
    r = resumen[resumen.delta_pct.isin(DECIDEN)].groupby('variante').f1_1_epoca_E.mean()
    ventaja = float(r['mediana'] - r['media'])
    return dict(regla=f'se adopta la mediana si su F1 con 1 % (época de menor pérdida), promediado entre δ = '
                      f'{" y ".join(map(str, DECIDEN))} %, supera al de la media en {MARGEN} o más',
                f1_media=round(float(r['media']), 4), f1_mediana=round(float(r['mediana']), 4),
                ventaja_mediana=round(ventaja, 4), referencia_elegida='mediana' if ventaja >= MARGEN else 'media')


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
    params = {r: parametros_vecinas('a14', limpia_ajuste, sigma, r) for r in VARIANTES}
    calendarios = ar.calendarios_entrenamiento(n=n_tr).corrida.tolist()
    filas = []
    for d in DELTAS:
        mats = [leer(f'{c}_d{d}')[0] for c in calendarios]
        idx = mats[0].index
        assert all(x.index.equals(idx) for x in mats)
        p_tr, p_va = posiciones(idx, *SELECCION)[::paso], posiciones(idx, *VALIDACION)[::paso]
        Y = [x['anomalia_red'].to_numpy(np.float32) for x in mats]
        ytr = np.concatenate([Y[k][p_tr] for k in range(n_tr)])
        yva = np.concatenate([Y[k][p_va] for k in range(n_va)])
        tras = np.concatenate([tras_ataque(idx, ar.leer_plan(PLANES / f'plan_{calendarios[k]}.csv'))[p_va]
                               for k in range(n_va)])
        for variante in VARIANTES:
            F = [ev.entradas_de('vecinas', x, None, sigma, params[variante]) for x in mats]
            Xtr = np.concatenate([lr.ventanas(F[k], p_tr) for k in range(n_tr)])
            Xva = np.concatenate([lr.ventanas(F[k], p_va) for k in range(n_va)])
            del F
            base = dict(delta_pct=d, variante=variante, columnas=int(Xtr.shape[2]), ventanas=len(ytr))
            print(base, flush=True)
            modelo = nuevo_modelo(Xtr.shape[2])
            modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=epocas, batch_size=CONFIG['batch'],
                       shuffle=CONFIG['shuffle'], verbose=0, callbacks=[PorEpoca(Xva, yva, tras, filas, base)])
            del modelo, Xtr, Xva
            pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)
        del mats, Y
    r = pd.DataFrame(filas)

    def resumir(x):
        e = x.loc[x.val_loss.idxmin()]
        return pd.Series(dict(epoca_E=int(e.epoca), f1_1_epoca_E=e.f1_1, f1_5_epoca_E=e.f1_5,
                              recall_1_epoca_E=e.recall_1, precision_1_epoca_E=e.precision_1, pr_auc_epoca_E=e.pr_auc,
                              fa_tras_ataque_1_epoca_E=e.fa_tras_ataque_1, fa_resto_1_epoca_E=e.fa_resto_1,
                              f1_1_mejor=x.f1_1.max(), f1_1_promedio=x.f1_1.mean(), val_loss_min=x.val_loss.min()))
    resumen = (r.groupby(['delta_pct', 'variante', 'columnas', 'ventanas'], sort=False)
               .apply(resumir, include_groups=False).reset_index())
    resumen.to_csv(salida / 'resumen.csv', index=False)
    eleccion = elegir(resumen)
    eleccion.update(prueba=prueba)
    (salida / 'eleccion.json').write_text(json.dumps(eleccion, indent=2, ensure_ascii=False))
    print(resumen.round(4).to_string(index=False))
    print(json.dumps(eleccion, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
