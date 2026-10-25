"""Exploración (2026-10-25, a pedido del tesista; no decide nada): precisión y recall de L0 y R3 en
2022 con umbrales más estrictos que el 1 % (5, 1, 0.5, 0.2 y 0.1 % de falsas alarmas en 2022 limpio).

Uso: .venv/bin/python experiments/anomalias_red/exploracion_precision_umbral_2022.py

Lee los puntajes guardados de la selección de L0 (lstm_local/c20) y recalcula R3; no carga modelos.
Usa 2022 y no 2024 para no ajustar nada mirando el examen.
"""
import sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / 'experiments/anomalias_red'))
import numpy as np, pandas as pd
from src.detect import anomalias_red as ar, estacion_dia as ed, evaluacion_red as ev
from entrenar_lstm_estacion import leer_dias
from entrenar_lstm_sup import SELECCION, leer, parametros_vecinas
from generar_planes import alterables_v4
from metricas_estandar_revision8 import con_umbral
limpia, _ = leer('limpia_2020_2022'); _, sigma = ev.normalizacion(limpia)
par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, 'mediana'); vec = par.vecinas
obj = alterables_v4()
r3 = lambda m: ed.dominancia(ed.juntar_dia(ev.columnas_vecinas(m, sigma, par)[obj], 'promedio_dia'), vec)
r3_2022 = r3(limpia).loc['2022']; dias = r3_2022.index
cal = ar.calendarios_entrenamiento(n=10).corrida.tolist()
Y = np.concatenate([ed.etiquetas(ar.leer_plan(RAIZ / f'results/anomalias_red_v1/planes/plan_{c}.csv'), dias, obj).to_numpy().ravel() for c in cal])
filas = []
for d in (100, 50):
    L = leer_dias(RAIZ / f'results/anomalias_red_v1/lstm_local/c20/d{d}/seleccion/dias_2022.csv.gz')
    det = {'L0': {k: v['promedio_dia'] for k, v in L.items()},
           'R3': {**{c: r3(leer(f'{c}_d{d}')[0]).loc['2022'] for c in cal}, 'limpia_2022': r3_2022}}
    validas = r3_2022.notna() & det['L0']['limpia_2022'].notna()
    comun = np.tile(validas.to_numpy().ravel(), len(cal)); y = Y[comun]
    for nombre, v in det.items():
        s = np.concatenate([v[c].to_numpy().ravel() for c in cal])[comun]
        limpio = v['limpia_2022'][validas].stack().dropna().to_numpy()
        for fa in (0.05, 0.01, 0.005, 0.002, 0.001):
            m = con_umbral(y, s > ev.umbral_falsas_alarmas(limpio, fa))
            filas.append(dict(delta=d, detector=nombre, fa_pct=100 * fa, tp=m['tp'], fp=m['fp'], recall=round(m['recall'], 3),
                              precision=round(m['precision'], 3), f1=round(m['f1'], 3)))
print(pd.DataFrame(filas).to_string(index=False))
print('atacadas', int(y.sum()), 'normales', int((~y).sum()))
