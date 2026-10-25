"""Revisión 17: examen final de la estación-día con 2025 y 2026 (enero a julio). Una sola vez.

Uso (después de generar_planes.py --final y generar_matrices.py --final):

    .venv/bin/python experiments/anomalias_red/examen_final.py --solo-generar        # matrices de hora al azar
    .venv/bin/python experiments/anomalias_red/examen_final.py [--salida DIR] [--tolerancia-v4 PPB]
    .venv/bin/python experiments/anomalias_red/examen_final.py --prueba --salida DIR  # 2024, 1 calendario

Detectores congelados, sin entrenar: L0 por δ (los modelo.keras de lstm_local_examen/c20), el L0 único
(el de δ = 50 %, elegido con 2022 en la revisión 16), R3 (fase 2 de la revisión 12) y el V4 (cargado de
disco, inferencia repetida). Umbrales p99 y p99.9 de 2023 limpio, los mismos del examen 2024 (se
comprueba). Contexto: la historia limpia anterior a cada año. Por año: los 10 calendarios con sus
cinco δ, su versión con hora al azar (`recorrer_plan`, etiqueta de `etiquetas_recorridas`) y el año
limpio como «sin ataque». Intervalos del 95 % de L0 − R3 y L0 único − R3 por bootstrap de bloques
estación × mes. No elige nada. Con --prueba corre lo mismo con 2024 (1 calendario, δ = 100 %) para
probar el código sin tocar 2025–2026, y no imprime métricas.
"""
from __future__ import annotations

import argparse
import hashlib
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
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
import evaluar_estacion_dia as ee  # noqa: E402
from entrenar_lstm_local import REFERENCIA, por_dia  # noqa: E402
from entrenar_lstm_sup import leer, parametros_vecinas  # noqa: E402
from evaluar_v4 import V4, cargar_v4, con_examen, residuos  # noqa: E402
from generar_matrices import guardar_sin_pisar, periodo  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from intervalos_2024 import metricas  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402
from puntos_operacion_2024 import CURVA, LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'examen_final'
PLANES = SAL / 'planes'
CONGELADOS = SAL / 'examen_final_modelos_congelados.json'
EXAMEN_14 = SAL / 'lstm_local_2024/resultados.csv'
PUNTOS_15 = SAL / 'puntos_operacion_2024/puntos_operacion.csv'
AGREGACION = 'promedio_dia'
DELTAS = [round(100 * d) for d in ar.DELTAS]
UNICO = 50                                       # revisión 16 (2a)
B = 2000
ANIOS = {2025: dict(periodo='final_2025', etapa='prueba_2025', limpia='limpia_2025',
                    previas=['limpia_2023', 'limpia_2024']),
         2026: dict(periodo='final_2026', etapa='prueba_2026_parcial', limpia='limpia_2026',
                    previas=['limpia_2023', 'limpia_2024', 'limpia_2025'])}
PRUEBA = {2024: dict(periodo='prueba_2024', etapa='prueba_2024', limpia='limpia_2024', previas=['limpia_2023'])}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corridas_de(anio, cfg, prueba):
    if prueba:
        return ar.corridas()[ar.corridas().corrida == 'prueba_2024_01'].reset_index(drop=True)
    c = ar.corridas_finales()
    return c[c.corrida.str.startswith(cfg['periodo'])].reset_index(drop=True)


def generar_hora_azar(anios, deltas, prueba, salida):
    """Planes recorridos y sus matrices `hora_azar_<corrida>_d<δ>` (la segunda vez sólo comprueba)."""
    ctx = em.contexto(RAIZ)
    cols = ar.columnas_entrada(ctx['definitiva']['inactivos'])
    (salida / 'planes').mkdir(parents=True, exist_ok=True)
    filas = []
    for anio, cfg in anios.items():
        ini, fin = ar.PERIODOS[cfg['periodo']]
        v = periodo(ctx['valores'], ini, fin)
        for c in corridas_de(anio, cfg, prueba).itertuples():
            r = ar.recorrer_plan(ar.leer_plan(PLANES / f'plan_{c.corrida}.csv'), c.numero, ini, fin)
            r.to_csv(salida / 'planes' / f'plan_hora_azar_{c.corrida}.csv', index=False)
            for d in deltas:
                rec, cam = ar.aplicar_horas(v, r, d / 100)
                sha_csv, estado = guardar_sin_pisar(f'hora_azar_{c.corrida}_d{d}', ar.matriz_red(rec, cols, cam))
                filas.append(dict(matriz=f'hora_azar_{c.corrida}_d{d}', sha256_csv=sha_csv, estado=estado))
    pd.DataFrame(filas).to_csv(salida / 'matrices_hora_azar.csv', index=False)
    print(f'{len(filas)} matrices de hora al azar', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--tolerancia-v4', type=float, default=None)
    ap.add_argument('--solo-generar', action='store_true')
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    salida.mkdir(parents=True, exist_ok=True)
    anios = PRUEBA if prueba else ANIOS
    deltas = [100] if prueba else DELTAS
    if args.solo_generar:
        generar_hora_azar(anios, deltas, prueba, salida)
        return
    if args.tolerancia_v4 is not None:
        ee.TOLERANCIA_PPB = args.tolerancia_v4
    objetivos = alterables_v4()

    # Detectores congelados: los SHA-256 registrados antes de correr.
    rutas = {f'L0_d{m}': LSTM / f'd{m}' / 'modelo.keras' for m in DELTAS}
    congelados = json.loads(CONGELADOS.read_text())
    sha_ok = {k: sha(p) == congelados['L0'][k] for k, p in rutas.items()}
    if not all(sha_ok.values()):
        raise RuntimeError(f'modelos L0 distintos de los registrados: {sha_ok}')
    from tensorflow import keras
    modelos = {m: keras.models.load_model(rutas[f'L0_d{m}'], compile=False) for m in DELTAS}
    modelos_v4, p95 = cargar_v4()                     # verifica el SHA-256 de cada modelo del V4
    ctx = em.contexto(RAIZ)
    valores, dfn = ctx['valores'], ctx['definitiva']

    limpia_tr, sha_tr, sigma, vec = ee.normalizacion_y_vecinas('mediana')
    par = parametros_vecinas('a14', limpia_tr, sigma, REFERENCIA)
    estaciones = ev.estaciones_de(limpia_tr)

    def l0(previa, matriz, ms):
        x = ev.con_historia(previa, matriz)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        return {m: por_dia(modelos[m], F, x, np.arange(len(previa), len(x)), estaciones, par.vecinas,
                           objetivos)[AGREGACION] for m in ms}

    def r3(previa, matriz):
        col = ev.columnas_vecinas(ev.con_historia(previa, matriz), sigma, vec).iloc[len(previa):]
        return ed.dominancia(ed.juntar_dia(col[objetivos], AGREGACION), vec.vecinas)

    def v4(matriz, etapa):
        res = residuos(modelos_v4, con_examen(valores, matriz), dfn, matriz.index, etapa)
        return ed.juntar_dia((res / p95[res.columns])[objetivos], AGREGACION)

    # 2023 limpio: los umbrales.
    cal, _ = leer('limpia_2023')
    u23 = {'L0': l0(limpia_tr, cal, DELTAS), 'R3': r3(limpia_tr, cal)}
    r23 = pd.DataFrame({o: pd.read_csv(V4 / o / 'calibracion_2023.csv.gz', parse_dates=['timestamp'],
                                       index_col='timestamp')['residuo_ppb'] for o in modelos_v4}).reindex(cal.index)
    u23['V4'] = ed.juntar_dia((r23 / p95[r23.columns])[objetivos], AGREGACION)
    v23 = u23['R3'].notna() & u23['L0'][DELTAS[0]].notna()

    def umbrales(limpio, validas):
        c = limpio[validas].stack().dropna().to_numpy()
        return {p: ev.umbral_falsas_alarmas(c, fa) for p, fa in PUNTOS.items()}

    U = {('R3', d): umbrales(u23['R3'], v23) for d in deltas}
    U.update({('L0', d): umbrales(u23['L0'][d], v23) for d in deltas})
    U.update({('L0_unico', d): umbrales(u23['L0'][UNICO], v23) for d in deltas})
    U.update({('V4', d): umbrales(u23['V4'], u23['V4'].notna()) for d in deltas})

    # Control: los umbrales son los del examen 2024 (revisiones 14 y 15).
    e14 = pd.read_csv(EXAMEN_14)
    e14 = e14[(e14.version == 'con ataque') & (e14.nivel_fa_pct == 1)].set_index(['detector', 'delta_pct'])['umbral']
    p15 = pd.read_csv(PUNTOS_15)
    p15 = p15[(p15.version == 'con ataque')].set_index(['detector', 'delta_pct', 'punto'])['umbral']
    dif_u = 0.0
    for (det, d), u in U.items():
        ref = {'p99': (e14.get((det, d)) if det in ('L0', 'R3') else p15.get((det, d, 'p99'))),
               'p99.9': p15.get((det, d, 'p99.9'))}
        if det == 'L0_unico':
            ref = {'p99': e14.get(('L0', UNICO)), 'p99.9': p15.get(('L0', UNICO, 'p99.9'))}
        for p in PUNTOS:
            if ref[p] is not None:
                dif_u = max(dif_u, abs(u[p] - ref[p]) / max(abs(ref[p]), 1e-12))
    print(f'umbrales frente al examen 2024: diferencia relativa máxima {dif_u:.1e}', flush=True)

    filas, filas_fa, filas_ic, filas_az, conteos, controles_v4, curva = [], [], [], [], [], {}, []
    acumulado = {}                                         # para los dos años juntos
    for anio, cfg in anios.items():
        corridas = corridas_de(anio, cfg, prueba)
        limpia_y, _ = leer(cfg['limpia'])
        historia = limpia_tr
        for n in cfg['previas']:
            historia = ev.con_historia(historia, leer(n)[0])
        dias = limpia_y.index.normalize().unique()
        # El año limpio: «sin ataque» y control del V4 contra sus predicciones guardadas.
        S = {'limpio': {'L0': l0(historia, limpia_y, DELTAS), 'R3': r3(historia, limpia_y),
                        'V4': v4(limpia_y, cfg['etapa'])}}
        res = residuos(modelos_v4, valores, dfn, limpia_y.index, cfg['etapa'])
        dif = 0.0
        for o in modelos_v4:
            g = V4 / o / f'predicciones_{anio}.csv.gz'
            r = res[o].dropna()
            if g.exists():
                g = pd.read_csv(g, parse_dates=['timestamp'], index_col='timestamp')['residuo_ppb']
                if not r.index.equals(g.index):
                    raise RuntimeError(f'{o}: horas con predicción distintas a las guardadas en {anio}')
                dif = max(dif, float(np.abs(r.to_numpy() - g.to_numpy()).max()) if len(r) else 0.0)
            elif len(r):
                raise RuntimeError(f'{o}: hay predicciones en {anio} y no estaban guardadas')
        tol = args.tolerancia_v4 if args.tolerancia_v4 is not None else ee.TOLERANCIA_PPB
        if dif > tol:
            raise RuntimeError(f'el V4 en {anio} limpio no reproduce sus predicciones (máx. {dif} ppb)')
        controles_v4[anio] = dif
        valido = S['limpio']['R3'].notna() & S['limpio']['L0'][DELTAS[0]].notna()
        valido_v4 = S['limpio']['V4'].notna()
        mes = np.tile((np.arange(len(objetivos))[None, :] * 12 + (dias.month.to_numpy() - 1)[:, None]).ravel(), len(corridas))
        for d in deltas:
            for version in ('medianoche', 'hora al azar'):
                cal_d, Y, G = {}, [], []
                for c in corridas.itertuples():
                    plan = ar.leer_plan(PLANES / f'plan_{c.corrida}.csv')
                    if version == 'medianoche':
                        x, _ = leer(f'{c.corrida}_d{d}')
                        Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel().astype(float))
                        G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vec.vecinas).to_numpy().ravel())
                    else:
                        x, _ = leer(f'hora_azar_{c.corrida}_d{d}')
                        r = pd.read_csv(salida / 'planes' / f'plan_hora_azar_{c.corrida}.csv',
                                        parse_dates=['inicio', 'fin'])
                        Y.append(ed.etiquetas_recorridas(r, limpia_y.index, objetivos).to_numpy().ravel())
                    s = l0(historia, x, sorted({d, UNICO}))
                    cal_d[c.corrida] = {'L0': s[d], 'L0_unico': s[UNICO], 'R3': r3(historia, x), 'V4': v4(x, cfg['etapa'])}
                Y = np.concatenate(Y)
                for det in ('L0', 'L0_unico', 'R3', 'V4'):
                    limpio = S['limpio']['L0'][UNICO if det == 'L0_unico' else d] if det.startswith('L0') else S['limpio'][det]
                    ok = np.tile((valido_v4 if det == 'V4' else valido).to_numpy().ravel(), len(corridas)) & ~np.isnan(Y)
                    y = Y[ok] == 1.0
                    s = np.concatenate([cal_d[c][det].to_numpy().ravel() for c in cal_d])[ok]
                    s0 = np.tile(limpio.to_numpy().ravel(), len(corridas))[ok]
                    conteos.append(dict(anio=anio, version=version, delta_pct=d, detector=det, atacadas=int(y.sum()),
                                        normales=int((~y).sum()), excluidas=int((np.isnan(Y) & np.tile(
                                            (valido_v4 if det == 'V4' else valido).to_numpy().ravel(), len(corridas))).sum())))
                    auc = {'con ataque': dict(pr_auc=average_precision_score(y, s), roc_auc=roc_auc_score(y, s)),
                           'sin ataque': dict(pr_auc=average_precision_score(y, s0), roc_auc=roc_auc_score(y, s0))}
                    if version == 'medianoche':                 # la curva: umbrales de 10 a 0.05 % (G2)
                        c23 = (u23['L0'][UNICO if det == 'L0_unico' else d] if det.startswith('L0') else u23[det])
                        c23 = c23[u23['V4'].notna() if det == 'V4' else v23].stack().dropna().to_numpy()
                        for fa in CURVA:
                            m = con_umbral(y, s > ev.umbral_falsas_alarmas(c23, fa))
                            curva.append(dict(anio=anio, delta_pct=d, detector=det, fa_objetivo_pct=100 * fa,
                                              recall=m['recall'], precision=m['precision'], f1=m['f1'],
                                              fa_examen_pct=100 * m['falsas_alarmas'], tp=m['tp'], fp=m['fp']))
                    for p in PUNTOS:
                        u = U[(det, d)][p]
                        for v, puntaje in (('con ataque', s), ('sin ataque', s0)):
                            fila = dict(anio=anio, version=version, delta_pct=d, detector=det, punto=p, evaluacion=v,
                                        umbral=u, **con_umbral(y, puntaje > u), **auc[v])
                            (filas if version == 'medianoche' else filas_az).append(fila)
                        if version == 'medianoche' and det != 'V4':
                            alerta = s > u
                            acumulado.setdefault((d, p, det), []).append((anio, y, alerta, mes[ok]))
                            g = np.concatenate(G)[ok]
                            fp_total = int((alerta & ~y).sum())
                            for grupo in ed.GRUPOS_FA:
                                en = g == grupo
                                fp = int((alerta & en).sum())
                                filas_fa.append(dict(anio=anio, delta_pct=d, detector=det, punto=p, grupo=grupo,
                                                     estacion_dias_normales=int(en.sum()), falsas_alarmas=fp,
                                                     tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                                     parte_pct=100 * fp / fp_total if fp_total else np.nan))
                print(f'{anio}, δ = {d} %, {version}: listo', flush=True)

    # Intervalos del 95 %: L0 − R3 y L0 único − R3, por año y con los dos años juntos.
    for (d, p, det), partes in acumulado.items():
        if det == 'R3':
            continue
        for etiqueta, sel in [(str(a), [i for i, x in enumerate(partes) if x[0] == a]) for a in anios] + \
                             ([('juntos', list(range(len(partes))))] if len(anios) > 1 else []):
            conteo = {}
            for nombre, lista in ((det, partes), ('R3', acumulado[(d, p, 'R3')])):
                y = np.concatenate([lista[i][1] for i in sel])
                a = np.concatenate([lista[i][2] for i in sel])
                b = np.concatenate([lista[i][3] + 1000 * k for k, i in enumerate(sel)])   # bloques por año
                _, b = np.unique(b, return_inverse=True)
                conteo[nombre] = np.stack([np.bincount(b, weights=w, minlength=b.max() + 1)
                                           for w in (a & y, a & ~y, ~a & y)], axis=1)
            nb = conteo['R3'].shape[0]
            semilla = [42, 17, int(etiqueta) if etiqueta != 'juntos' else 0]
            W = np.random.default_rng(semilla).multinomial(nb, np.full(nb, 1 / nb), size=B)
            est = {k: metricas(c.sum(axis=0)) for k, c in conteo.items()}
            boot = {k: metricas(W @ c) for k, c in conteo.items()}
            for m in ('f1', 'recall', 'precision'):
                lo, hi = np.percentile(boot[det][m] - boot['R3'][m], [2.5, 97.5])
                filas_ic.append(dict(anio=etiqueta, delta_pct=d, punto=p, comparacion=f'{det} − R3', metrica=m,
                                     detector=float(est[det][m]), R3=float(est['R3'][m]),
                                     diferencia=float(est[det][m] - est['R3'][m]), ic_bajo=float(lo), ic_alto=float(hi),
                                     excluye_cero=bool(lo > 0 or hi < 0)))

    pd.DataFrame(filas).to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(filas_az).to_csv(salida / 'hora_azar.csv', index=False)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    pd.DataFrame(filas_ic).to_csv(salida / 'intervalos.csv', index=False)
    pd.DataFrame(conteos).to_csv(salida / 'conteos.csv', index=False)
    pd.DataFrame(curva).to_csv(salida / 'curva.csv', index=False)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=17, anios=list(anios), prueba=prueba, puntos=PUNTOS, modelo_unico=f'L0_d{UNICO}',
        origen=dict(L0='modelos definitivos de la revisión 14 cargados de disco', V4='cargado de disco',
                    R3='sin entrenamiento'),
        sha256_modelos_l0={k: sha(p) for k, p in rutas.items()}, sha256_coinciden=sha_ok,
        umbrales_diferencia_relativa_max_frente_a_2024=dif_u, v4_diferencia_max_ppb_frente_a_guardadas=controles_v4,
        tolerancia_control_v4_ppb=args.tolerancia_v4 or ee.TOLERANCIA_PPB, remuestreos=B,
        sha256_matriz_ajuste=sha_tr), indent=2, ensure_ascii=False))
    if not prueba:
        r = pd.DataFrame(filas)
        print(r[(r.evaluacion == 'con ataque')].pivot_table(index=['anio', 'delta_pct', 'detector'], columns='punto',
                                                             values='f1').round(3).to_string())


if __name__ == '__main__':
    main()
