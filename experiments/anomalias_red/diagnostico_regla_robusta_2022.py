"""Elección de la regla de vecinas robusta con 2022 (protocolo, revisión 12).

La regla de vecinas a14 por estación-día con el promedio del día (revisión 11), en cuatro
variantes: R0 = la de la revisión 11 (media de 14 días, sin dominancia), R1 = mediana de 14 días,
R2 = dominancia en el vecindario (`estacion_dia.dominancia`) y R3 = las dos. Mismos datos que la
fase 1 de la revisión 11: escala con 2020–2021 limpio (con la referencia de cada variante), umbral
para las 31 estaciones con 1 y 5 % de falsas alarmas en las estación-días de 2021 limpio, examen con
2022 de los calendarios 01–10 y «sin ataque» con 2022 limpio.

Regla, fijada antes de correrla: F̄ = F1 con 1 % promediado entre δ = 100, 50 y 20 %. Son candidatas
las variantes con F̄ ≥ F̄(R0) + 0.02; si no hay, la revisión 12 se cierra sin 2024. Se elige la
candidata de mayor F̄, salvo que una candidata con menos cambios (R1 o R2 frente a R3) quede a menos
de 0.02: entonces esa (si son las dos, la de mayor F̄).

Control: R0 reproduce exactamente el promedio del día de la fase 1 de la revisión 11. No toca 2023
ni 2024, no entrena ni carga modelos.

Uso: .venv/bin/python experiments/anomalias_red/diagnostico_regla_robusta_2022.py [--salida DIR] [--prueba]
     (--prueba: 2 calendarios y δ = 100 y 20 %; sólo comprueba que corre: no imprime métricas)
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

SALIDA = RAIZ / 'results/anomalias_red_v1/regla_robusta_2022'
REVISION11 = RAIZ / 'results/anomalias_red_v1/estacion_dia_2022'
PLANES = RAIZ / 'results/anomalias_red_v1/planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'
VARIANTES = {'R0': ('media', False), 'R1': ('mediana', False), 'R2': ('media', True), 'R3': ('mediana', True)}
CAMBIOS = {'R0': 0, 'R1': 1, 'R2': 1, 'R3': 2}
AGREGACION = 'promedio_dia'                       # elegida en la revisión 11
DELTAS, DECIDEN, MARGEN = (100, 50, 20, 10, 5), (100, 50, 20), 0.02
AÑO_UMBRAL, AÑO_EXAMEN = '2021', '2022'
N_CALENDARIOS = 10


def elegir(F: dict) -> dict:
    """La regla de la revisión 12 con F̄ por variante."""
    candidatas = [v for v in ('R1', 'R2', 'R3') if F[v] >= F['R0'] + MARGEN]
    elegida = max(candidatas, key=F.get) if candidatas else None
    if elegida:
        sencillas = [v for v in candidatas if CAMBIOS[v] < CAMBIOS[elegida] and F[elegida] - F[v] < MARGEN]
        elegida = max(sencillas, key=F.get) if sencillas else elegida
    return dict(regla=f'candidatas: F̄ ≥ F̄(R0) + {MARGEN}; la de mayor F̄, salvo una candidata con menos cambios '
                      f'a menos de {MARGEN}', f_barra={v: round(f, 4) for v, f in F.items()}, candidatas=candidatas,
                variante_elegida=elegida, examinar_2024=elegida is not None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    deltas, n_cal = ((100, 20), 2) if prueba else (DELTAS, N_CALENDARIOS)
    salida.mkdir(parents=True, exist_ok=True)

    limpia, _ = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    ajuste = limpia.loc[SELECCION[0]:SELECCION[1]]                    # 2020–2021 limpio
    par = {r: parametros_vecinas('a14', ajuste, sigma, r) for r in ('media', 'mediana')}
    vecinas = par['media'].vecinas
    objetivos = alterables_v4()

    def por_variante(matriz) -> dict[str, pd.DataFrame]:
        dia = {r: ed.juntar_dia(ev.columnas_vecinas(matriz, sigma, p)[objetivos], AGREGACION) for r, p in par.items()}
        return {v: ed.dominancia(dia[r], vecinas) if dom else dia[r] for v, (r, dom) in VARIANTES.items()}

    limpio = por_variante(limpia)
    umbrales, filas_u = {}, []
    for v, s in limpio.items():
        cal = s.loc[AÑO_UMBRAL].stack().dropna().to_numpy()
        for fa in ev.NIVELES_FA:
            u = ev.umbral_falsas_alarmas(cal, fa)
            umbrales[v, round(100 * fa)] = u
            filas_u.append(dict(variante=v, nivel_fa_pct=round(100 * fa), umbral=u, estacion_dias_2021=len(cal),
                                falsas_alarmas_2021=float((cal > u).mean())))
    pd.DataFrame(filas_u).to_csv(salida / 'umbrales.csv', index=False)
    sin_ataque = {v: s.loc[AÑO_EXAMEN] for v, s in limpio.items()}
    dias = sin_ataque['R0'].index

    calendarios = ar.calendarios_entrenamiento(n=N_CALENDARIOS).corrida.tolist()[:n_cal]
    filas, filas_fa, filas_ap, filas_ex = [], [], [], []
    for d in deltas:
        S = {v: [] for v in VARIANTES}
        Y, G = [], []
        for c in calendarios:
            x, _ = leer(f'{c}_d{d}')
            plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
            for v, s in por_variante(x).items():
                s = s.loc[AÑO_EXAMEN]
                assert s.index.equals(dias) and s.notna().equals(sin_ataque[v].notna())
                S[v].append(s.to_numpy().ravel())
            Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
            G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vecinas).to_numpy().ravel())
            print(f'δ = {d} %  {c}', flush=True)
        y, g = np.concatenate(Y), np.concatenate(G)
        S = {v: np.concatenate(S[v]) for v in VARIANTES}
        ok = ~np.isnan(S['R0'])
        assert all(np.array_equal(~np.isnan(S[v]), ok) for v in VARIANTES)
        filas_ex.append(dict(delta_pct=d, estacion_dias=len(y), validas=int(ok.sum()), excluidas=int((~ok).sum()),
                             atacadas=int(y.sum()), atacadas_excluidas=int((y & ~ok).sum())))
        yv, gv = y[ok], g[ok]
        for v in VARIANTES:
            sv = S[v][ok]
            s0v = np.tile(sin_ataque[v].to_numpy().ravel(), len(calendarios))[ok]
            for version, puntaje in (('con ataque', sv), ('sin ataque', s0v)):
                auc = dict(pr_auc=average_precision_score(yv, puntaje), roc_auc=roc_auc_score(yv, puntaje))
                for nivel in (1, 5):
                    u = umbrales[v, nivel]
                    filas.append(dict(delta_pct=d, variante=v, referencia=VARIANTES[v][0], dominancia=VARIANTES[v][1],
                                      nivel_fa_pct=nivel, version=version, umbral=u,
                                      **con_umbral(yv, puntaje > u), **auc))
            alerta = sv > umbrales[v, 1]
            fp_total = int((alerta & ~yv).sum())
            for grupo in ed.GRUPOS_FA:
                en = gv == grupo
                fp = int((alerta & en).sum())
                filas_fa.append(dict(delta_pct=d, variante=v, grupo=grupo, estacion_dias_normales=int(en.sum()),
                                     falsas_alarmas=fp, tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                     parte_pct=100 * fp / fp_total if fp_total else np.nan))
            if VARIANTES[v][1]:                       # lo que apaga la dominancia en los días atacados
                base = next(b for b, (r, dom) in VARIANTES.items() if r == VARIANTES[v][0] and not dom)
                sb = S[base][ok]
                apagada = yv & (sv == 0) & (sb > 0)
                filas_ap.append(dict(delta_pct=d, variante=v, frente_a=base, atacadas_validas=int(yv.sum()),
                                     apagadas=int(apagada.sum()),
                                     alertas_verdaderas_perdidas=int((apagada & (sb > umbrales[base, 1])).sum())))
        pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)

    r = pd.DataFrame(filas)
    for nombre, filas_x in (('falsas_alarmas', filas_fa), ('apagadas', filas_ap), ('excluidas', filas_ex)):
        pd.DataFrame(filas_x).to_csv(salida / f'{nombre}.csv', index=False)
    if not prueba:                                    # control: R0 es la fase 1 de la revisión 11
        prev = pd.read_csv(REVISION11 / 'resultados.csv')
        prev = prev[prev.agregacion == AGREGACION].reset_index(drop=True)
        r0 = pd.read_csv(salida / 'resultados.csv')                  # mismo paso por CSV que la revisión 11
        r0 = r0[r0.variante == 'R0'].reset_index(drop=True)
        for col in ('delta_pct', 'nivel_fa_pct', 'version', 'umbral', 'tp', 'fp', 'fn', 'tn', 'f1', 'pr_auc'):
            if not r0[col].equals(prev[col]):
                raise RuntimeError(f'R0 no reproduce la fase 1 de la revisión 11 ({col})')
        print('R0 reproduce exactamente la fase 1 de la revisión 11')
    f1 = r[(r.nivel_fa_pct == 1) & (r.version == 'con ataque')].pivot(index='delta_pct', columns='variante', values='f1')
    F = f1.loc[[d for d in DECIDEN if d in f1.index]].mean().to_dict()
    eleccion = elegir(F)
    eleccion.update(f1_por_delta={int(k): {v: round(float(x), 4) for v, x in fila.items()} for k, fila in f1.iterrows()},
                    calendarios=calendarios, prueba=prueba)
    (salida / 'eleccion.json').write_text(json.dumps(eleccion, indent=2, ensure_ascii=False))
    if not prueba:
        columnas = ['delta_pct', 'variante', 'nivel_fa_pct', 'version', 'f1', 'precision', 'recall', 'falsas_alarmas', 'pr_auc']
        print(r[columnas].round(4).to_string(index=False))
        for t in (filas_fa, filas_ap, filas_ex):
            print(pd.DataFrame(t).round(2).to_string(index=False))
        print(json.dumps(eleccion, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
