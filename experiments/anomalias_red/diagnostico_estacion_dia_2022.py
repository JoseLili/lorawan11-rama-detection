"""Fase 1 de la revisión 11: ¿juntar el día con el promedio le gana a la peor hora? (regla de vecinas, 2022).

La regla de vecinas a14 con media (revisión 8), sin entrenamiento, evaluada por estación-día en los
31 objetivos con las dos formas de juntar el día (`src/detect/estacion_dia.py`):
- escala de la columna con 2020–2021 limpio, como en las elecciones de las revisiones 8 y 10;
- un umbral para las 31 estaciones con 1 y 5 % de falsas alarmas en las estación-días de 2021 limpio;
- examen con las estación-días de 2022 de los calendarios 01–10, y «sin ataque» con 2022 limpio
  (mismas estación-días, mismo umbral y mismas etiquetas);
- métricas de la revisión 9, falsas alarmas con 1 % por grupo (contagio, tras ataque propio, resto)
  y estación-días excluidas por tener menos de 12 horas válidas.

Regla, fijada antes de correrla (protocolo, revisión 11): se pasa a la fase 2 si el F1 con 1 % del
promedio del día, promediado entre δ = 100, 50 y 20 %, supera al de la peor hora en 0.02 o más; si
no, la revisión 11 se cierra y no se examina con 2024. δ = 10 y 5 % sólo se reportan. No toca 2023
ni 2024, no entrena ni carga modelos.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_estacion_dia_2022.py [--salida DIR] [--prueba]
     (--prueba: 2 calendarios y δ = 100 y 20 %; sólo comprueba que todo corre)
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
from entrenar_lstm_sup import SELECCION, leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SALIDA = RAIZ / 'results/anomalias_red_v1/estacion_dia_2022'
PLANES = RAIZ / 'results/anomalias_red_v1/planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'
DELTAS, DECIDEN, MARGEN = (100, 50, 20, 10, 5), (100, 50, 20), 0.02
AÑO_UMBRAL, AÑO_EXAMEN = '2021', '2022'
N_CALENDARIOS = 10


def por_dia(columnas: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {a: ed.juntar_dia(columnas, a) for a in ed.AGREGACIONES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    deltas, n_cal = ((100, 20), 2) if prueba else (DELTAS, N_CALENDARIOS)
    salida.mkdir(parents=True, exist_ok=True)

    # Normalización con 2020–2022 limpio (debe coincidir con la del V4) y escala con 2020–2021 limpio.
    limpia, _ = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma)
    objetivos = alterables_v4()

    # Umbrales con 2021 limpio; «sin ataque» con 2022 limpio.
    limpio = por_dia(ev.columnas_vecinas(limpia, sigma, par)[objetivos])
    umbrales, filas_u = {}, []
    for a, s in limpio.items():
        cal = s.loc[AÑO_UMBRAL].stack().dropna().to_numpy()
        for fa in ev.NIVELES_FA:
            u = ev.umbral_falsas_alarmas(cal, fa)
            umbrales[a, round(100 * fa)] = u
            filas_u.append(dict(agregacion=a, nivel_fa_pct=round(100 * fa), umbral=u, estacion_dias_2021=len(cal),
                                falsas_alarmas_2021=float((cal > u).mean())))
    pd.DataFrame(filas_u).to_csv(salida / 'umbrales.csv', index=False)
    sin_ataque = {a: s.loc[AÑO_EXAMEN] for a, s in limpio.items()}
    dias = sin_ataque['peor_hora'].index

    calendarios = ar.calendarios_entrenamiento(n=N_CALENDARIOS).corrida.tolist()[:n_cal]
    filas, filas_fa, filas_ex = [], [], []
    for d in deltas:
        S = {a: [] for a in ed.AGREGACIONES}
        Y, G = [], []
        for c in calendarios:
            x, _ = leer(f'{c}_d{d}')
            plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
            atacado = por_dia(ev.columnas_vecinas(x, sigma, par)[objetivos])
            for a in ed.AGREGACIONES:
                s = atacado[a].loc[AÑO_EXAMEN]
                assert s.index.equals(dias) and s.notna().equals(sin_ataque[a].notna())
                S[a].append(s.to_numpy().ravel())
            Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
            G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, par.vecinas).to_numpy().ravel())
            print(f'δ = {d} %  {c}', flush=True)
        y, g = np.concatenate(Y), np.concatenate(G)
        for a in ed.AGREGACIONES:
            s, s0 = np.concatenate(S[a]), np.tile(sin_ataque[a].to_numpy().ravel(), len(calendarios))
            ok = ~np.isnan(s)
            if a == 'peor_hora':
                filas_ex.append(dict(delta_pct=d, estacion_dias=len(s), validas=int(ok.sum()),
                                     excluidas=int((~ok).sum()), atacadas=int(y.sum()),
                                     atacadas_excluidas=int((y & ~ok).sum())))
            yv, sv, s0v, gv = y[ok], s[ok], s0[ok], g[ok]
            for version, puntaje in (('con ataque', sv), ('sin ataque', s0v)):
                auc = dict(pr_auc=average_precision_score(yv, puntaje), roc_auc=roc_auc_score(yv, puntaje))
                for nivel in (1, 5):
                    u = umbrales[a, nivel]
                    filas.append(dict(delta_pct=d, agregacion=a, nivel_fa_pct=nivel, version=version, umbral=u,
                                      **con_umbral(yv, puntaje > u), **auc))
            alerta = sv > umbrales[a, 1]
            fp_total = int((alerta & ~yv).sum())
            for grupo in ed.GRUPOS_FA:
                en = gv == grupo
                fp = int((alerta & en).sum())
                filas_fa.append(dict(delta_pct=d, agregacion=a, grupo=grupo, estacion_dias_normales=int(en.sum()),
                                     falsas_alarmas=fp, tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                     parte_pct=100 * fp / fp_total if fp_total else np.nan))
        pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)

    r = pd.DataFrame(filas)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    pd.DataFrame(filas_ex).to_csv(salida / 'excluidas.csv', index=False)
    f1 = (r[(r.nivel_fa_pct == 1) & (r.version == 'con ataque')]
          .pivot(index='delta_pct', columns='agregacion', values='f1'))
    decide = f1.loc[[d for d in DECIDEN if d in f1.index]].mean()
    ventaja = float(decide['promedio_dia'] - decide['peor_hora'])
    eleccion = dict(regla=f'se pasa a la fase 2 si el F1 con 1 % del promedio del día, promediado entre δ = '
                          f'{", ".join(map(str, DECIDEN))} %, supera al de la peor hora en {MARGEN} o más',
                    f1_peor_hora=round(float(decide['peor_hora']), 4), f1_promedio_dia=round(float(decide['promedio_dia']), 4),
                    ventaja_promedio_dia=round(ventaja, 4), pasa_a_fase_2=bool(ventaja >= MARGEN),
                    f1_por_delta={int(k): {a: round(float(v), 4) for a, v in fila.items()} for k, fila in f1.iterrows()},
                    calendarios=calendarios, prueba=prueba)
    (salida / 'eleccion.json').write_text(json.dumps(eleccion, indent=2, ensure_ascii=False))
    columnas = ['delta_pct', 'agregacion', 'nivel_fa_pct', 'version', 'f1', 'precision', 'recall', 'falsas_alarmas', 'pr_auc']
    print(r[columnas].round(4).to_string(index=False))
    print(pd.DataFrame(filas_fa).round(2).to_string(index=False))
    print(pd.DataFrame(filas_ex).to_string(index=False))
    print(json.dumps(eleccion, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
