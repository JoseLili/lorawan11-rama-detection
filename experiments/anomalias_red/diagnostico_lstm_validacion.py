"""Diagnóstico de la selección de épocas del LSTM supervisado, δ = 100 % (revisión 6).

Sólo usa 2020–2022: no toca 2023 ni 2024. No es un detector del protocolo ni guarda modelos.
Uso: .venv/bin/python experiments/anomalias_red/diagnostico_lstm_validacion.py <salida.csv>
"""
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'experiments/anomalias_red')
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from tensorflow import keras
import entrenar_lstm_sup as e
from src.detect import anomalias_red as ar, evaluacion_red as ev
lt, _ = e.leer('limpia_2020_2022'); mu, sg = ev.normalizacion(lt)
mats = [e.leer(f'{c}_d100')[0] for c in ar.calendarios_entrenamiento(n=10).corrida]
Xtr, ytr = e.juntar(mats, mu, sg, *e.SELECCION); Xva, yva = e.juntar(mats, mu, sg, *e.VALIDACION)
p0 = ytr.mean(); bce0 = -np.mean(yva * np.log(p0) + (1 - yva) * np.log(1 - p0))
print(f'pérdida de validación de un modelo constante (p = {p0:.3f}): {bce0:.4f}')
def tpr_a_fpr(y, s, a=0.05):
    u = np.quantile(s[y == 0], 1 - a); return 100 * (s[y == 1] > u).mean()
filas = []
class Diag(keras.callbacks.Callback):
    def on_epoch_end(self, ep, logs=None):
        s_tr = self.model.predict(Xtr[::5], batch_size=4096, verbose=0).ravel()
        s = self.model.predict(Xva, batch_size=4096, verbose=0).ravel()
        filas.append(dict(epoca=ep + 1, loss=logs['loss'], val_loss=logs['val_loss'],
                          auc_entrenamiento=roc_auc_score(ytr[::5], s_tr), auc_2022=roc_auc_score(yva, s),
                          deteccion_2022_fa5_pct=tpr_a_fpr(yva, s), media_puntaje_normales_2022=s[yva == 0].mean()))
        print({k: round(v, 3) for k, v in filas[-1].items()}, flush=True)
m = e.nuevo_modelo()
m.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=10, batch_size=64, shuffle=True, callbacks=[Diag()], verbose=0)
pd.DataFrame(filas).to_csv(sys.argv[1], index=False)
