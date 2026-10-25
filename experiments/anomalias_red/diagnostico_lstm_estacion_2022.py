"""Elección con 2022 de la revisión 13: la configuración del LSTM por estación y el LSTM contra la regla R3.

Uso (después de `entrenar_lstm_estacion.py` con δ = 100, 50 y 20 % y las dos referencias):

    .venv/bin/python experiments/anomalias_red/diagnostico_lstm_estacion_2022.py [--lstm DIR] [--salida DIR] [--prueba]

Lee los puntajes por estación-día de 2022 de los modelos de selección (seleccion/dias_2022.csv.gz) y
calcula, con los mismos datos, la regla R3 de la revisión 12 (mediana de 14 días, escala con
2020–2021 limpio, promedio del día y dominancia). Las configuraciones del LSTM son C0 = media sin
dominancia, C1 = media con dominancia, C2 = mediana sin dominancia y C3 = mediana con dominancia, todas
con el promedio del día.

- Umbral para las 31 estaciones con 1 y 5 % de falsas alarmas en las estación-días de 2022 limpio (no
  2021: el LSTM se entrenó con 2021); examen con 2022 de los calendarios 01–10; «sin ataque» con 2022
  limpio. Todo en las estación-días válidas para el LSTM y para R3 a la vez.
- F̄ = F1 con 1 % promediado entre δ = 100, 50 y 20 %.
- Paso 1: queda C0, salvo que otra la supere en 0.02 o más (candidatas); entre las candidatas, la de
  mayor F̄, salvo una candidata con menos cambios a menos de 0.02 de ella.
- Paso 2: la elegida pasa a 2024 sólo si su F̄ supera al de R3 en 0.02 o más.
- Control de máquina: R3 con el esquema de la revisión 12 (umbral de 2021 limpio, sus propias
  estación-días válidas) debe reproducir sus resultados guardados; si no, se anota y se usa la R3 de
  esta sesión.

Salidas en results/anomalias_red_v1/lstm_estacion_2022/ (o --salida). Con --prueba lee los puntajes
de una corrida --prueba (1 calendario) y no imprime métricas.
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
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from entrenar_lstm_estacion import SAL as LSTM, leer_dias  # noqa: E402
from entrenar_lstm_sup import SELECCION, leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/lstm_estacion_2022'
REVISION12 = RAIZ / 'results/anomalias_red_v1/regla_robusta_2022/resultados.csv'
PLANES = RAIZ / 'results/anomalias_red_v1/planes'
CONFIGURACIONES = {'C0': ('media', False), 'C1': ('media', True), 'C2': ('mediana', False), 'C3': ('mediana', True)}
CAMBIOS = {'C0': 0, 'C1': 1, 'C2': 1, 'C3': 2}
AGREGACION = 'promedio_dia'
DECIDEN, MARGEN = (100, 50, 20), 0.02
N_CALENDARIOS = 10


def paso_1(F: dict) -> str:
    candidatas = [c for c in ('C1', 'C2', 'C3') if F[c] >= F['C0'] + MARGEN]
    if not candidatas:
        return 'C0'
    elegida = max(candidatas, key=F.get)
    sencillas = [c for c in candidatas if CAMBIOS[c] < CAMBIOS[elegida] and F[elegida] - F[c] < MARGEN]
    return max(sencillas, key=F.get) if sencillas else elegida


def medir(nombre, d, y, g, s, s0, umbrales, filas, filas_fa):
    for version, puntaje in (('con ataque', s), ('sin ataque', s0)):
        auc = dict(pr_auc=average_precision_score(y, puntaje), roc_auc=roc_auc_score(y, puntaje))
        for nivel in (1, 5):
            u = umbrales[nivel]
            filas.append(dict(delta_pct=d, detector=nombre, nivel_fa_pct=nivel, version=version, umbral=u,
                              **con_umbral(y, puntaje > u), **auc))
    alerta = s > umbrales[1]
    fp_total = int((alerta & ~y).sum())
    for grupo in ed.GRUPOS_FA:
        en = g == grupo
        fp = int((alerta & en).sum())
        filas_fa.append(dict(delta_pct=d, detector=nombre, grupo=grupo, estacion_dias_normales=int(en.sum()),
                             falsas_alarmas=fp, tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                             parte_pct=100 * fp / fp_total if fp_total else np.nan))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lstm', type=Path, default=LSTM)
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    deltas, n_cal = ((100,), 1) if prueba else (DECIDEN, N_CALENDARIOS)
    salida.mkdir(parents=True, exist_ok=True)

    limpia, _ = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia)
    par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, 'mediana')
    vecinas = par.vecinas
    objetivos = alterables_v4()

    def r3(matriz):
        s = ed.juntar_dia(ev.columnas_vecinas(matriz, sigma, par)[objetivos], AGREGACION)
        return ed.dominancia(s, vecinas)

    r3_limpia = r3(limpia)
    r3_2021, r3_2022 = r3_limpia.loc['2021'], r3_limpia.loc['2022']
    dias = r3_2022.index
    calendarios = ar.calendarios_entrenamiento(n=N_CALENDARIOS).corrida.tolist()[:n_cal]
    planes = {c: ar.leer_plan(PLANES / f'plan_{c}.csv') for c in calendarios}
    Y = np.concatenate([ed.etiquetas(planes[c], dias, objetivos).to_numpy().ravel() for c in calendarios])
    G = np.concatenate([ed.grupos_falsa_alarma(planes[c], dias, objetivos, vecinas).to_numpy().ravel()
                        for c in calendarios])

    filas, filas_fa, filas_ap, control, epocas = [], [], [], [], []
    F = {k: [] for k in list(CONFIGURACIONES) + ['R3']}
    for d in deltas:
        lstm = {}
        for ref in ('media', 'mediana'):
            carpeta = args.lstm / ref / f'd{d}'
            leidos = leer_dias(carpeta / 'seleccion/dias_2022.csv.gz')
            sel = json.loads((carpeta / 'configuracion.json').read_text())['seleccion']
            epocas.append(dict(delta_pct=d, referencia=ref, E=sel['E'], epocas_ejecutadas=sel['epocas_ejecutadas'],
                               val_loss_min=sel['val_loss_min']))
            for c, (r, dom) in CONFIGURACIONES.items():
                if r == ref:
                    lstm[c] = {k: ed.dominancia(v[AGREGACION], vecinas) if dom else v[AGREGACION]
                               for k, v in leidos.items()}
        r3_cal = {c: r3(leer(f'{c}_d{d}')[0]).loc['2022'] for c in calendarios}

        # Control de máquina: R3 con el esquema de la revisión 12.
        s = np.concatenate([r3_cal[c].to_numpy().ravel() for c in calendarios])
        ok = ~np.isnan(s)
        for nivel, fa in ((1, 0.01), (5, 0.05)):
            u = ev.umbral_falsas_alarmas(r3_2021.stack().dropna().to_numpy(), fa)
            m = con_umbral(Y[ok], s[ok] > u)
            control.append(dict(delta_pct=d, nivel_fa_pct=nivel, tp=m['tp'], fp=m['fp'], fn=m['fn'], tn=m['tn']))

        # Estación-días válidas para el LSTM y para R3 a la vez.
        validas = r3_2022.notna() & lstm['C0']['limpia_2022'].notna()
        for c in calendarios:
            assert r3_cal[c].notna().equals(r3_2022.notna())
            assert all(lstm[k][c].notna().equals(lstm[k]['limpia_2022'].notna()) for k in lstm)
        comun = np.tile(validas.to_numpy().ravel(), len(calendarios))
        y, g = Y[comun], G[comun]
        detectores = {**{k: (np.concatenate([v[c].to_numpy().ravel() for c in calendarios]), v['limpia_2022'])
                         for k, v in lstm.items()},
                      'R3': (np.concatenate([r3_cal[c].to_numpy().ravel() for c in calendarios]), r3_2022)}
        for nombre, (s, limpio) in detectores.items():
            umbrales = {n: ev.umbral_falsas_alarmas(limpio[validas].stack().dropna().to_numpy(), fa)
                        for n, fa in ((1, 0.01), (5, 0.05))}
            s0 = np.tile(limpio.to_numpy().ravel(), len(calendarios))[comun]
            medir(nombre, d, y, g, s[comun], s0, umbrales, filas, filas_fa)
            F[nombre].append(filas[-4]['f1'])                         # con ataque, 1 %
        for c, (r, dom) in CONFIGURACIONES.items():                   # lo que apaga la dominancia
            if dom:
                base = next(b for b, (rb, db) in CONFIGURACIONES.items() if rb == r and not db)
                sv, sb = detectores[c][0][comun], detectores[base][0][comun]
                filas_ap.append(dict(delta_pct=d, configuracion=c, frente_a=base, atacadas_validas=int(y.sum()),
                                     apagadas=int((y & (sv == 0) & (sb > 0)).sum())))
        print(f'δ = {d} %: listo', flush=True)

    r = pd.DataFrame(filas)
    r.to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    pd.DataFrame(filas_ap).to_csv(salida / 'apagadas.csv', index=False)
    pd.DataFrame(epocas).to_csv(salida / 'epocas.csv', index=False)
    control = pd.DataFrame(control)
    control.to_csv(salida / 'control_r3.csv', index=False)
    reproduce = None
    if not prueba:
        prev = pd.read_csv(REVISION12)
        prev = prev[(prev.variante == 'R3') & (prev.version == 'con ataque') & prev.delta_pct.isin(DECIDEN)]
        prev = prev.set_index(['delta_pct', 'nivel_fa_pct'])[['tp', 'fp', 'fn', 'tn']].sort_index()
        reproduce = bool(control.set_index(['delta_pct', 'nivel_fa_pct']).sort_index().equals(prev))
        print('R3 reproduce la revisión 12 en esta máquina' if reproduce else
              'R3 NO reproduce la revisión 12 en esta máquina: se usa la R3 de esta sesión', flush=True)
    Fb = {k: float(np.mean(v)) for k, v in F.items()}
    elegida = paso_1({k: Fb[k] for k in CONFIGURACIONES})
    ventaja = Fb[elegida] - Fb['R3']
    eleccion = dict(regla_paso_1=f'queda C0 salvo candidatas con F̄ ≥ F̄(C0) + {MARGEN}; la de mayor F̄, salvo una '
                                 f'candidata con menos cambios a menos de {MARGEN}',
                    regla_paso_2=f'pasa a 2024 si F̄(elegida) ≥ F̄(R3) + {MARGEN}',
                    f_barra={k: round(v, 4) for k, v in Fb.items()}, configuracion_elegida=elegida,
                    ventaja_sobre_r3=round(ventaja, 4), pasa_a_2024=bool(ventaja >= MARGEN),
                    r3_reproduce_revision_12=reproduce, deltas_pct=list(deltas), calendarios=calendarios, prueba=prueba)
    (salida / 'eleccion.json').write_text(json.dumps(eleccion, indent=2, ensure_ascii=False))
    if not prueba:
        columnas = ['delta_pct', 'detector', 'nivel_fa_pct', 'version', 'f1', 'precision', 'recall', 'falsas_alarmas',
                    'pr_auc']
        print(r[columnas].round(4).to_string(index=False))
        print(pd.DataFrame(filas_fa).round(2).to_string(index=False))
        print(pd.DataFrame(filas_ap).to_string(index=False))
        print(pd.DataFrame(epocas).to_string(index=False))
        print(json.dumps(eleccion, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
