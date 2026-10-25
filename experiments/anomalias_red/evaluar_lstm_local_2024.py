"""Examen 2024 de la revisión 14: el LSTM local (L0) contra la regla R3, por estación-día.

Uso (después de `entrenar_lstm_local.py --calendarios 20 --definitivo` con los cinco δ):

    .venv/bin/python experiments/anomalias_red/evaluar_lstm_local_2024.py [--lstm DIR] [--salida DIR] [--prueba]

Lee los puntajes por estación-día del modelo definitivo (dias_examen.csv.gz: 2023 limpio, 2024
limpio y los 10 calendarios de 2024) y recalcula R3 como la fase 2 de la revisión 12 (mediana de 14
días, referencia y escala con 2020–2022 limpio, promedio del día y dominancia). No elige nada.

- Umbral de cada detector para las 31 estaciones con 1 y 5 % de falsas alarmas en las estación-días
  de 2023 limpio; examen con los 10 calendarios de 2024 juntos; «sin ataque» con 2024 limpio.
- Comparación que se reporta: L0 contra R3 en las estación-días válidas para los dos.
- Contraste: la peor hora de L0; L0 y R3 en sus propias estación-días válidas; el V4 por estación-día
  de la fase 2 de la revisión 11 (guardado); el «resto» de las falsas alarmas separado en días con y
  sin ataque en la red.
- Control de máquina: R3 en sus propias estación-días válidas debe reproducir la revisión 12.

Salidas en results/anomalias_red_v1/lstm_local_2024/ (o --salida). Con --prueba (1 calendario,
δ = 100 %) sólo comprueba que corre: no imprime métricas.
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
from diagnostico_lstm_local_2022 import medir  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
LSTM = SAL / 'lstm_local_examen'
SALIDA = SAL / 'lstm_local_2024'
PLANES = SAL / 'planes'
REVISION12 = SAL / 'estacion_dia/regla_mediana_dominancia/resultados.csv'
V4 = SAL / 'estacion_dia/v4/resultados.csv'
AGREGACION = 'promedio_dia'
CALENDARIOS = 20                                  # L0, elegida con 2022


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lstm', type=Path, default=LSTM)
    ap.add_argument('--calendarios', type=int, default=CALENDARIOS)
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    deltas, n_cal = ((100,), 1) if prueba else ([round(100 * d) for d in ar.DELTAS], ar.CORRIDAS_PRUEBA)
    salida.mkdir(parents=True, exist_ok=True)

    limpia_tr, sha_tr, sigma, vec = normalizacion_y_vecinas('mediana')
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + n_cal].tolist()
    examen = [f'{c}_d{d}' for d in deltas for c in corridas]
    r3 = {}
    for nombre, valores, _ in valores_regla(examen, limpia_tr, sigma, vec):
        r3[nombre] = ed.dominancia(ed.juntar_dia(valores[objetivos], AGREGACION), vec.vecinas)
    print('R3 recalculada', flush=True)

    dias = r3['limpia_2024'].index
    planes = {c: ar.leer_plan(PLANES / f'plan_{c}.csv') for c in corridas}
    etiquetas = {c: ed.etiquetas(planes[c], dias, objetivos) for c in corridas}
    Y = np.concatenate([etiquetas[c].to_numpy().ravel() for c in corridas])
    G = np.concatenate([ed.grupos_falsa_alarma(planes[c], dias, objetivos, vec.vecinas).to_numpy().ravel()
                        for c in corridas])
    H = np.concatenate([np.repeat(etiquetas[c].any(axis=1).to_numpy()[:, None], len(objetivos), axis=1).ravel()
                        for c in corridas])                         # ese día hay algún objetivo atacado

    def umbrales_de(limpio_2023, validas_2023):
        cal = limpio_2023[validas_2023].stack().dropna().to_numpy()
        return {round(100 * fa): ev.umbral_falsas_alarmas(cal, fa) for fa in ev.NIVELES_FA}

    filas, filas_fa, control, propias = [], [], [], []
    for d in deltas:
        L = leer_dias(args.lstm / f'c{args.calendarios}' / f'd{d}' / 'dias_examen.csv.gz')
        lstm = {'L0': {k: v[AGREGACION] for k, v in L.items()}, 'L0_peor_hora': {k: v['peor_hora'] for k, v in L.items()}}
        r3d = {k: r3[k if k.startswith('limpia') else f'{k}_d{d}'] for k in ['limpia_2023', 'limpia_2024'] + corridas}
        for c in corridas:
            assert r3d[c].notna().equals(r3d['limpia_2024'].notna())
            assert all(v[c].index.equals(dias) and v[c].notna().equals(v['limpia_2024'].notna())
                       for v in lstm.values())

        # Control de máquina y contraste: cada detector en sus propias estación-días válidas.
        for nombre, v in (('R3', r3d), ('L0', lstm['L0'])):
            u = umbrales_de(v['limpia_2023'], v['limpia_2023'].notna())
            s = np.concatenate([v[c].to_numpy().ravel() for c in corridas])
            ok = ~np.isnan(s)
            for nivel in (1, 5):
                m = con_umbral(Y[ok], s[ok] > u[nivel])
                fila = dict(delta_pct=d, detector=nombre, nivel_fa_pct=nivel, umbral=u[nivel], **m)
                propias.append(fila)
                if nombre == 'R3':
                    control.append({k: fila[k] for k in ('delta_pct', 'nivel_fa_pct', 'tp', 'fp', 'fn', 'tn')})

        # Comparación: estación-días válidas para L0 y para R3 a la vez.
        validas_23 = r3d['limpia_2023'].notna() & lstm['L0']['limpia_2023'].notna()
        validas_24 = r3d['limpia_2024'].notna() & lstm['L0']['limpia_2024'].notna()
        comun = np.tile(validas_24.to_numpy().ravel(), len(corridas))
        y, g, h = Y[comun], G[comun], H[comun]
        for nombre, v in {**lstm, 'R3': r3d}.items():
            s = np.concatenate([v[c].to_numpy().ravel() for c in corridas])[comun]
            s0 = np.tile(v['limpia_2024'].to_numpy().ravel(), len(corridas))[comun]
            medir(nombre, d, y, g, h, s, s0, umbrales_de(v['limpia_2023'], validas_23), filas, filas_fa)
        print(f'δ = {d} %: listo', flush=True)

    r = pd.DataFrame(filas)
    r.to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    propias = pd.DataFrame(propias)
    control = pd.DataFrame(control)
    reproduce = None
    if not prueba:
        prev = pd.read_csv(REVISION12)
        prev = prev[(prev.agregacion == AGREGACION) & (prev.version == 'con ataque')]
        prev = prev.set_index(['delta_pct', 'nivel_fa_pct'])[['tp', 'fp', 'fn', 'tn']].sort_index()
        reproduce = bool(control.set_index(['delta_pct', 'nivel_fa_pct']).sort_index().equals(prev))
        print('R3 reproduce la revisión 12 en esta máquina' if reproduce else
              'R3 NO reproduce la revisión 12 en esta máquina: se usa la R3 de esta sesión', flush=True)
        v4 = pd.read_csv(V4)
        v4 = v4[(v4.agregacion == AGREGACION) & (v4.version == 'con ataque')].assign(detector='V4 (revisión 11)')
        propias = pd.concat([propias, v4[propias.columns.intersection(v4.columns)]], ignore_index=True)
    propias.to_csv(salida / 'propias_validas.csv', index=False)

    f1 = r[(r.version == 'con ataque') & (r.nivel_fa_pct == 1)].set_index(['delta_pct', 'detector'])['f1']
    resumen = dict(protocolo=ar.PROTOCOLO, revision=14, examen=2024, origen_l0='modelo definitivo recién entrenado',
                   f1_1pct={str(d): {k: round(float(f1[d, k]), 4) for k in ('L0', 'R3')} for d in deltas},
                   diferencia_l0_menos_r3={str(d): round(float(f1[d, 'L0'] - f1[d, 'R3']), 4) for d in deltas},
                   r3_reproduce_revision_12=reproduce, calendarios=corridas, deltas_pct=list(deltas),
                   sha256_matriz_ajuste=sha_tr, prueba=prueba)
    (salida / 'resumen.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    if not prueba:
        columnas = ['delta_pct', 'detector', 'nivel_fa_pct', 'version', 'f1', 'f2', 'precision', 'recall',
                    'falsas_alarmas', 'pr_auc']
        print(r[columnas].round(4).to_string(index=False))
        print(pd.DataFrame(filas_fa).round(2).to_string(index=False))
        print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
