"""Exploración de la revisión 13 con 2022, después de ver su elección (2026-10-24). No decide nada.

Uso: .venv/bin/python experiments/anomalias_red/exploracion_revision13_2022.py

Lee los puntajes por estación-día guardados de los modelos de selección (no carga modelos) y, con
los mismos datos y umbrales que `diagnostico_lstm_estacion_2022.py` (2022 limpio, estación-días
válidas para el LSTM y para R3):

1. la peor hora del LSTM con 1 %, el contraste que el diagnóstico no calculó;
2. las falsas alarmas del grupo «resto» con 1 %, separadas según si ese día hay algún objetivo
   atacado en la red (lo que motivó la revisión 14).
"""
from __future__ import annotations

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
from entrenar_lstm_estacion import SAL as LSTM, leer_dias  # noqa: E402
from entrenar_lstm_sup import SELECCION, leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

PLANES = RAIZ / 'results/anomalias_red_v1/planes'


def main():
    limpia, _ = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia)
    par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, 'mediana')
    objetivos = alterables_v4()

    def r3(matriz):
        return ed.dominancia(ed.juntar_dia(ev.columnas_vecinas(matriz, sigma, par)[objetivos], 'promedio_dia'),
                             par.vecinas)

    r3_2022 = r3(limpia).loc['2022']
    dias = r3_2022.index
    calendarios = ar.calendarios_entrenamiento(n=10).corrida.tolist()
    planes = {c: ar.leer_plan(PLANES / f'plan_{c}.csv') for c in calendarios}
    Y = {c: ed.etiquetas(planes[c], dias, objetivos) for c in calendarios}
    G = {c: ed.grupos_falsa_alarma(planes[c], dias, objetivos, par.vecinas) for c in calendarios}

    peor, resto = [], []
    for d in (100, 50, 20):
        leidos = {ref: leer_dias(LSTM / ref / f'd{d}' / 'seleccion/dias_2022.csv.gz') for ref in ('media', 'mediana')}
        validas = r3_2022.notna() & leidos['media']['limpia_2022']['promedio_dia'].notna()
        comun = np.tile(validas.to_numpy().ravel(), len(calendarios))
        y = np.concatenate([Y[c].to_numpy().ravel() for c in calendarios])[comun]
        for ref, L in leidos.items():
            for agr in ed.AGREGACIONES:
                u = ev.umbral_falsas_alarmas(L['limpia_2022'][agr][validas].stack().dropna().to_numpy(), 0.01)
                s = np.concatenate([L[c][agr].to_numpy().ravel() for c in calendarios])[comun]
                peor.append(dict(delta_pct=d, referencia=ref, agregacion=agr, **con_umbral(y, s > u)))
        if d == 20:
            continue
        detectores = {'C0': ({c: leidos['media'][c]['promedio_dia'] for c in calendarios},
                             leidos['media']['limpia_2022']['promedio_dia']),
                      'R3': ({c: r3(leer(f'{c}_d{d}')[0]).loc['2022'] for c in calendarios}, r3_2022)}
        for nombre, (s, limpio) in detectores.items():
            u = ev.umbral_falsas_alarmas(limpio[validas].stack().dropna().to_numpy(), 0.01)
            cuenta = {False: [0, 0], True: [0, 0]}
            for c in calendarios:
                hay = pd.DataFrame(np.repeat(Y[c].any(axis=1).to_numpy()[:, None], len(objetivos), axis=1),
                                   index=dias, columns=objetivos)
                for con in (False, True):
                    en = (G[c] == 'resto') & (hay == con) & validas
                    cuenta[con][0] += int(((s[c] > u) & en).to_numpy().sum())
                    cuenta[con][1] += int(en.to_numpy().sum())
            for con, (fa, n) in cuenta.items():
                resto.append(dict(delta_pct=d, detector=nombre, dia_con_ataque_en_la_red=con, estacion_dias=n,
                                  falsas_alarmas=fa, tasa_pct=100 * fa / n))

    columnas = ['delta_pct', 'referencia', 'agregacion', 'f1', 'tp', 'fp']
    print(pd.DataFrame(peor)[columnas].round(4).to_string(index=False))
    print(pd.DataFrame(resto).round(2).to_string(index=False))


if __name__ == '__main__':
    main()
