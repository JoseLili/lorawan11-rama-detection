"""Revisión 16 (2): un solo modelo L0 para todos los δ, elegido con 2022 y examinado en 2024 (en la lap).

Uso: .venv/bin/python experiments/anomalias_red/modelo_unico_delta.py [--salida DIR]

(2a) Elección con 2022: cada modelo de selección (lstm_local_examen/c20/d<m>/seleccion/
modelo_seleccion.keras, entrenado con 2020–2021) puntúa 2022 de los calendarios 01–10 con δ = 100,
50 y 20 % y 2022 limpio; umbral de 2022 limpio en las estación-días comunes con R3 (como
diagnostico_lstm_local_2022.py). El modelo único es el de mayor F1 con 1 % promediado entre esos tres
δ; con un empate a menos de 0.005 gana el de mayor δ.

(2b) Examen 2024: cada modelo definitivo (modelo.keras) puntúa 2023 limpio, 2024 limpio y los 10
calendarios de los cinco δ (5 × 5), con su umbral de 2023 limpio en las estación-días comunes con R3,
con p99 y p99.9.

Los modelos se cargan de disco y sólo infieren en la lap. Controles: la diagonal reproduce los
puntajes guardados de Colab (diferencia máxima) y los conteos de la elección de la revisión 14 y de su
examen 2024. Salidas en results/anomalias_red_v1/comprobaciones_2024/modelo_unico/.
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

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from diagnostico_variantes_2022 import posiciones  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from entrenar_lstm_local import REFERENCIA, por_dia  # noqa: E402
from entrenar_lstm_sup import SELECCION, VALIDACION, leer, parametros_vecinas  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402
from puntos_operacion_2024 import LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'comprobaciones_2024/modelo_unico'
PLANES = SAL / 'planes'
ELECCION_14 = SAL / 'lstm_local_2022/resultados.csv'
EXAMEN_14 = SAL / 'lstm_local_2024/resultados.csv'
AGREGACION = 'promedio_dia'
DECIDEN, EMPATE = (100, 50, 20), 0.005
DELTAS = [round(100 * d) for d in ar.DELTAS]


def cargar(path):
    from tensorflow import keras
    return keras.models.load_model(path, compile=False)


def medir(y, s, limpio, validas_cal, comun, fa):
    u = ev.umbral_falsas_alarmas(limpio[validas_cal].stack().dropna().to_numpy(), fa)
    return con_umbral(y, s[comun] > u)


def eleccion_2022(objetivos, estaciones, salida):
    limpia, _ = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia)
    par_r3 = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, 'mediana')
    par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, REFERENCIA)

    def r3(m):
        return ed.dominancia(ed.juntar_dia(ev.columnas_vecinas(m, sigma, par_r3)[objetivos], AGREGACION), par_r3.vecinas)

    r3_2022 = r3(limpia).loc['2022']
    dias = r3_2022.index
    calendarios = ar.calendarios_entrenamiento(n=10).corrida.tolist()
    Y = np.concatenate([ed.etiquetas(ar.leer_plan(PLANES / f'plan_{c}.csv'), dias, objetivos).to_numpy().ravel()
                        for c in calendarios])
    pos = posiciones(limpia.index, *VALIDACION)
    modelos = {m: cargar(LSTM / f'd{m}' / 'seleccion/modelo_seleccion.keras') for m in DELTAS}
    entradas = {'limpia_2022': (ev.entradas_de('vecinas', limpia, None, sigma, par), limpia)}
    puntajes = {m: {'limpia_2022': por_dia(modelos[m], *entradas['limpia_2022'], pos, estaciones, par.vecinas,
                                           objetivos)[AGREGACION]} for m in DELTAS}
    filas, dif = [], 0.0
    for e in DECIDEN:
        r3e = {}
        for c in calendarios:
            x = leer(f'{c}_d{e}')[0]
            F = ev.entradas_de('vecinas', x, None, sigma, par)
            for m in DELTAS:
                puntajes[m][c] = por_dia(modelos[m], F, x, pos, estaciones, par.vecinas, objetivos)[AGREGACION]
            r3e[c] = r3(x).loc['2022']
        for m in (e,):                                               # control: la diagonal
            g = leer_dias(LSTM / f'd{m}' / 'seleccion/dias_2022.csv.gz')
            for k in ['limpia_2022'] + calendarios:
                dif = max(dif, float(np.nanmax(np.abs(puntajes[m][k].to_numpy() - g[k][AGREGACION].to_numpy()))))
        validas = r3_2022.notna() & puntajes[DELTAS[0]]['limpia_2022'].notna()
        comun = np.tile(validas.to_numpy().ravel(), len(calendarios))
        y = Y[comun]
        for nombre, v in [(f'L0_d{m}', puntajes[m]) for m in DELTAS] + [('R3', {**r3e, 'limpia_2022': r3_2022})]:
            s = np.concatenate([v[c].to_numpy().ravel() for c in calendarios])
            for punto, fa in PUNTOS.items():
                filas.append(dict(delta_examen=e, modelo=nombre, punto=punto,
                                  **medir(y, s, v['limpia_2022'], validas, comun, fa)))
        print(f'2022, δ = {e} %: listo', flush=True)
    r = pd.DataFrame(filas)
    r.to_csv(salida / 'eleccion_2022.csv', index=False)
    f1 = r[(r.punto == 'p99') & r.modelo.str.startswith('L0')].groupby('modelo')['f1'].mean()
    f1 = {int(k[4:]): float(v) for k, v in f1.items()}
    mejor = max(f1.values())
    unico = max(m for m, v in f1.items() if mejor - v < EMPATE)
    # control: la diagonal reproduce los conteos de la elección de la revisión 14 (L0, p99)
    e14 = pd.read_csv(ELECCION_14)
    e14 = e14[(e14.detector == 'L0') & (e14.version == 'con ataque') & (e14.nivel_fa_pct == 1)].set_index('delta_pct')
    diag = r[(r.punto == 'p99') & (r.modelo == r.delta_examen.map(lambda e: f'L0_d{e}'))].set_index('delta_examen')
    control = bool((diag[['tp', 'fp', 'fn', 'tn']] == e14.loc[diag.index, ['tp', 'fp', 'fn', 'tn']]).all().all())
    return dict(f1_medio_2022=f1, modelo_unico=unico, regla=f'mayor F1 con 1 % promediado en δ = {DECIDEN}; '
                f'empate a menos de {EMPATE}: el de mayor δ', control_diagonal_conteos=control,
                diferencia_maxima_puntajes_diagonal=dif)


def examen_2024(objetivos, estaciones, salida):
    limpia_tr, _, sigma, vec = normalizacion_y_vecinas('mediana')
    par = parametros_vecinas('a14', limpia_tr, sigma, REFERENCIA)
    corridas = ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA].tolist()
    examen = [f'{c}_d{d}' for d in DELTAS for c in corridas]
    r3 = {n: ed.dominancia(ed.juntar_dia(v[objetivos], AGREGACION), vec.vecinas)
          for n, v, _ in valores_regla(examen, limpia_tr, sigma, vec)}
    dias = r3['limpia_2024'].index
    modelos = {m: cargar(LSTM / f'd{m}' / 'modelo.keras') for m in DELTAS}
    cal, _ = leer('limpia_2023')
    historia = ev.con_historia(limpia_tr, cal)

    def puntuar(previa, matriz):
        x = ev.con_historia(previa, matriz)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        return {m: por_dia(modelos[m], F, x, np.arange(len(previa), len(x)), estaciones, par.vecinas,
                           objetivos)[AGREGACION] for m in DELTAS}

    p = {'limpia_2023': puntuar(limpia_tr, cal), 'limpia_2024': puntuar(historia, leer('limpia_2024')[0])}
    filas, dif = [], 0.0
    for e in DELTAS:
        for c in corridas:
            p[f'{c}_d{e}'] = puntuar(historia, leer(f'{c}_d{e}')[0])
        g = leer_dias(LSTM / f'd{e}' / 'dias_examen.csv.gz')                       # control: la diagonal
        for k in ['limpia_2023', 'limpia_2024'] + corridas:
            mio = p[k if k.startswith('limpia') else f'{k}_d{e}'][e]
            dif = max(dif, float(np.nanmax(np.abs(mio.to_numpy() - g[k][AGREGACION].to_numpy()))))
        Y = np.concatenate([ed.etiquetas(ar.leer_plan(PLANES / f'plan_{c}.csv'), dias, objetivos).to_numpy().ravel()
                            for c in corridas])
        v23 = r3['limpia_2023'].notna() & p['limpia_2023'][DELTAS[0]].notna()
        v24 = r3['limpia_2024'].notna() & p['limpia_2024'][DELTAS[0]].notna()
        comun = np.tile(v24.to_numpy().ravel(), len(corridas))
        y = Y[comun]
        dets = [(f'L0_d{m}', {k: p[k][m] for k in ('limpia_2023',)}, np.concatenate(
                    [p[f'{c}_d{e}'][m].to_numpy().ravel() for c in corridas])) for m in DELTAS]
        dets.append(('R3', {'limpia_2023': r3['limpia_2023']},
                     np.concatenate([r3[f'{c}_d{e}'].to_numpy().ravel() for c in corridas])))
        for nombre, limpio, s in dets:
            for punto, fa in PUNTOS.items():
                filas.append(dict(delta_examen=e, modelo=nombre, punto=punto,
                                  **medir(y, s, limpio['limpia_2023'], v23, comun, fa)))
        print(f'2024, δ = {e} %: listo', flush=True)
    r = pd.DataFrame(filas)
    r.to_csv(salida / 'examen_2024.csv', index=False)
    e14 = pd.read_csv(EXAMEN_14)
    e14 = e14[(e14.detector == 'L0') & (e14.version == 'con ataque')].set_index(['delta_pct', 'nivel_fa_pct'])
    diag = r[r.modelo == r.delta_examen.map(lambda e: f'L0_d{e}')].copy()
    diag = diag[diag.punto == 'p99'].assign(nivel_fa_pct=1).set_index(['delta_examen', 'nivel_fa_pct'])
    control = bool((diag[['tp', 'fp', 'fn', 'tn']].to_numpy() == e14.loc[diag.index, ['tp', 'fp', 'fn', 'tn']].to_numpy()).all())
    return dict(control_diagonal_conteos=control, diferencia_maxima_puntajes_diagonal=dif)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    objetivos = alterables_v4()
    estaciones = ev.estaciones_de(leer('limpia_2023')[0])
    a = eleccion_2022(objetivos, estaciones, args.salida)
    print(json.dumps(a, indent=2, ensure_ascii=False), flush=True)
    b = examen_2024(objetivos, estaciones, args.salida)
    (args.salida / 'eleccion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=16, comprobacion='modelo único', eleccion_2022=a, examen_2024=b,
        origen='modelos cargados de disco (entrenados en Colab, rev14); inferencia en la lap'),
        indent=2, ensure_ascii=False))
    print(json.dumps(b, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
