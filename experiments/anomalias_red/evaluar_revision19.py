"""Revisión 19: evaluación de los escenarios de una sola estación, un año a la vez. No entrena ni elige nada.

Uso (después de generar_revision19.py --anio AÑO, con los puntajes de la revisión 18 de ese año):

    .venv/bin/python experiments/anomalias_red/evaluar_revision19.py --anio 2025 [--salida DIR]
    .venv/bin/python experiments/anomalias_red/evaluar_revision19.py --anio 2024 --prueba --salida DIR

Detectores congelados, como en la revisión 18: el L0 único, el V4S compartido (revisión 18b), R3 y el V4. Los
umbrales p99 y p99.9 de 2023 limpio en las estación-días válidas para los cuatro (son los «comunes» de la
revisión 18) y la historia limpia anterior al año.

- (B) una a la vez (`unavez_<corrida>`):
  - **pareado (principal):** el recall en las estación-días de los episodios conservados, con los
    puntajes del calendario original (dias_<año>.csv.gz de la revisión 18) contra los de B, con
    intervalo del 95 % de la diferencia;
  - las falsas alarmas en las estación-días normales en los dos escenarios, por grupo (del plan original);
  - las métricas completas de B y el intervalo de L0 único − V4S compartido.
- (A) un solo nodo (`nodo_<año>_<estación>`, 31 calendarios): las métricas completas, las falsas alarmas
  por grupo y el intervalo de L0 único − V4S compartido.

Bootstrap de bloques estación × mes, 2 000 remuestreos, semilla [42, 19, año]. Controles: los umbrales son los
«comunes» de la revisión 18, y los puntajes del año limpio son idénticos a los guardados en la revisión 18.
Con --prueba: 2024, 1 calendario B, 2 nodos y δ = 100 %; sólo comprueba que corre.
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
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import v4_supervisado as vs  # noqa: E402
import evaluar_estacion_dia as ee  # noqa: E402
from entrenar_lstm_local import REFERENCIA, por_dia  # noqa: E402
from entrenar_lstm_sup import leer, parametros_vecinas  # noqa: E402
from evaluar_revision18 import (AGREGACION, ANIOS, B, CONGELADOS, DELTAS, PLANES, UNICO, V4SC,  # noqa: E402
                                cargar_v4s_compartido, sha)
from evaluar_v4 import V4, cargar_v4, con_examen, residuos  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from generar_revision19 import calendarios_prueba  # noqa: E402
from intervalos_2024 import metricas  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402
from puntos_operacion_2024 import LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'revision19'
REVISION18 = SAL / 'revision18'
DETECTORES = ('L0_unico', 'V4S_compartido', 'R3', 'V4')
PAR = ('L0_unico', 'V4S_compartido')
REVISION = 19


def leer_plan_o_vacio(nombre: str) -> pd.DataFrame:
    p = PLANES / f'plan_{nombre}.csv'
    return ar.leer_plan(p) if p.exists() else pd.DataFrame(columns=ar.COLUMNAS_PLAN).astype(
        {'inicio': 'datetime64[ns]', 'fin': 'datetime64[ns]'})


def remuestreo(nb, anio):
    return np.random.default_rng([42, REVISION, anio]).multinomial(nb, np.full(nb, 1 / nb), size=B)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anio', type=int, required=True, choices=sorted(ANIOS))
    ap.add_argument('--salida', type=Path, default=None)
    ap.add_argument('--prueba', action='store_true')
    ap.add_argument('--tolerancia', type=float, default=1e-12,
                    help='relativa en umbrales y absoluta en puntajes; mayor sólo en otra máquina que la de la revisión 18')
    args = ap.parse_args()
    anio, prueba = args.anio, args.prueba
    if prueba and anio != 2024:
        raise SystemExit('--prueba sólo con 2024')
    salida = args.salida or SALIDA / str(anio)
    salida.mkdir(parents=True, exist_ok=True)
    deltas = [100] if prueba else DELTAS
    cfg = ANIOS[anio]
    objetivos = alterables_v4()

    from tensorflow import keras
    ruta_l0 = LSTM / f'd{UNICO}' / 'modelo.keras'
    if sha(ruta_l0) != json.loads(CONGELADOS.read_text())['L0'][f'L0_d{UNICO}']:
        raise RuntimeError('el L0 único no es el registrado antes del examen final')
    l0m = keras.models.load_model(ruta_l0, compile=False)
    modelos_v4, p95 = cargar_v4()
    modelo_c, ordenes, sha_v4sc = cargar_v4s_compartido(V4SC, objetivos, False)
    ctx = em.contexto(RAIZ)
    valores, dfn = ctx['valores'], ctx['definitiva']
    limpia_tr, sha_tr, sigma, vec = ee.normalizacion_y_vecinas('mediana')
    par = parametros_vecinas('a14', limpia_tr, sigma, REFERENCIA)
    estaciones = ev.estaciones_de(limpia_tr)

    def puntajes(previa, matriz, etapa, v4_guardado=None):
        x = ev.con_historia(previa, matriz)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        l0 = por_dia(l0m, F, x, np.arange(len(previa), len(x)), estaciones, par.vecinas, objetivos)[AGREGACION]
        col = ev.columnas_vecinas(x, sigma, vec).iloc[len(previa):]
        r3 = ed.dominancia(ed.juntar_dia(col[objetivos], AGREGACION), vec.vecinas)
        res = v4_guardado if v4_guardado is not None else residuos(modelos_v4, con_examen(valores, matriz), dfn,
                                                                   matriz.index, etapa)
        v4 = ed.juntar_dia((res / p95[res.columns])[objetivos], AGREGACION)
        v = con_examen(valores.loc[:matriz.index[-1]], matriz)
        prob = vs.probabilidades({s: modelo_c for s in objetivos}, v, dfn['inactivos'], dfn['mu'], dfn['sigma'],
                                 etapa, matriz.index, ordenes=ordenes)
        return {'L0_unico': l0, 'V4S_compartido': ed.juntar_dia(prob[objetivos], AGREGACION), 'R3': r3, 'V4': v4}

    def validas(S):
        ok = S[DETECTORES[0]].notna()
        for k in DETECTORES[1:]:
            ok &= S[k].notna()
        return ok

    # 2023 limpio: umbrales en las estación-días válidas para los cuatro.
    cal, _ = leer('limpia_2023')
    r23 = pd.DataFrame({o: pd.read_csv(V4 / o / 'calibracion_2023.csv.gz', parse_dates=['timestamp'],
                                       index_col='timestamp')['residuo_ppb'] for o in modelos_v4}).reindex(cal.index)
    u23 = puntajes(limpia_tr, cal, 'calibracion', v4_guardado=r23)
    c23 = validas(u23)
    U = {k: {p: ev.umbral_falsas_alarmas(u23[k][c23].stack().dropna().to_numpy(), fa) for p, fa in PUNTOS.items()}
         for k in DETECTORES}
    r18 = pd.read_csv(REVISION18 / 'resultados.csv')
    r18 = r18[(r18.dias == 'comunes') & (r18.evaluacion == 'con ataque')].groupby(['detector', 'punto']).umbral.first()
    dif_u = max(abs(U[k][p] - r18[(k, p)]) / abs(r18[(k, p)]) for k in DETECTORES for p in PUNTOS)
    if dif_u > args.tolerancia:
        raise RuntimeError(f'los umbrales no son los comunes de la revisión 18 (diferencia relativa {dif_u})')

    # El año limpio, «sin ataque», y control contra los puntajes guardados de la revisión 18.
    limpia_y, _ = leer(cfg['limpia'])
    historia = limpia_tr
    for n in cfg['previas']:
        historia = ev.con_historia(historia, leer(n)[0])
    dias = limpia_y.index.normalize().unique()
    S0 = puntajes(historia, limpia_y, cfg['etapa'])
    val = validas(S0).to_numpy().ravel()
    d18 = pd.read_csv(REVISION18 / f'dias_{anio}.csv.gz', parse_dates=['dia'])

    def de_18(conjunto, det):
        t = d18[(d18.conjunto == conjunto) & (d18.detector == det)].set_index('dia')
        return t.reindex(dias)[objetivos]

    dif_s0 = max(float(np.nanmax(np.abs(S0[k].to_numpy() - de_18(cfg['limpia'], k).to_numpy()))) for k in DETECTORES)
    if dif_s0 > args.tolerancia:
        raise RuntimeError(f'los puntajes del año limpio no son los de la revisión 18 (máx. {dif_s0})')
    print(f'{anio}: umbrales y año limpio idénticos a la revisión 18', flush=True)
    mes1 = (np.arange(len(objetivos))[None, :] * 12 + (dias.month.to_numpy() - 1)[:, None]).ravel()

    corridas_b = calendarios_prueba(anio).corrida.tolist()
    nodos = [c for c in ar.corridas_nodo(objetivos).corrida if c.startswith(f'nodo_{anio}_')]
    if prueba:
        corridas_b, nodos = corridas_b[:1], nodos[:2]

    filas, filas_fa, filas_ic, filas_par, filas_fp, conteos = [], [], [], [], [], []
    for escenario, nombres in (('B', corridas_b), ('A', nodos)):
        for d in deltas:
            Y, Yo, G, Go, S, So, mes = [], [], [], [], {k: [] for k in DETECTORES}, {k: [] for k in DETECTORES}, []
            for k, c in enumerate(nombres):
                nombre = f'unavez_{c}' if escenario == 'B' else c
                plan = leer_plan_o_vacio(nombre)
                x, _ = leer(f'{nombre}_d{d}')
                s = puntajes(historia, x, cfg['etapa'])
                Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
                original = ar.leer_plan(PLANES / f'plan_{c}.csv') if escenario == 'B' else plan
                Yo.append(ed.etiquetas(original, dias, objetivos).to_numpy().ravel())
                G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vec.vecinas).to_numpy().ravel())
                Go.append(ed.grupos_falsa_alarma(original, dias, objetivos, vec.vecinas).to_numpy().ravel())
                for det in DETECTORES:
                    S[det].append(s[det].to_numpy().ravel())
                    if escenario == 'B':
                        So[det].append(de_18(f'{c}_d{d}', det).to_numpy().ravel())
                mes.append(mes1 + 1000 * k)
            ok = np.tile(val, len(nombres))
            y, yo = np.concatenate(Y)[ok] == 1.0, np.concatenate(Yo)[ok] == 1.0
            g, go = np.concatenate(G)[ok], np.concatenate(Go)[ok]
            _, mes_b = np.unique(np.concatenate(mes)[ok], return_inverse=True)
            nb = mes_b.max() + 1
            W = remuestreo(nb, anio)
            conteos.append(dict(anio=anio, escenario=escenario, delta_pct=d, calendarios=len(nombres),
                                atacadas=int(y.sum()), normales=int((~y).sum()),
                                atacadas_origen=int(yo.sum()) if escenario == 'B' else None))
            alertas = {}
            for det in DETECTORES:
                sc = np.concatenate(S[det])[ok]
                s0 = np.tile(S0[det].to_numpy().ravel(), len(nombres))[ok]
                auc = {'con ataque': dict(pr_auc=average_precision_score(y, sc), roc_auc=roc_auc_score(y, sc)),
                       'sin ataque': dict(pr_auc=average_precision_score(y, s0), roc_auc=roc_auc_score(y, s0))}
                for p in PUNTOS:
                    u = U[det][p]
                    for v, puntaje in (('con ataque', sc), ('sin ataque', s0)):
                        filas.append(dict(anio=anio, escenario=escenario, delta_pct=d, detector=det, punto=p,
                                          evaluacion=v, umbral=u, **con_umbral(y, puntaje > u), **auc[v]))
                    a = sc > u
                    alertas[(det, p)] = a
                    fp_total = int((a & ~y).sum())
                    for grupo in ed.GRUPOS_FA:
                        en = g == grupo
                        fp = int((a & en).sum())
                        filas_fa.append(dict(anio=anio, escenario=escenario, delta_pct=d, detector=det, punto=p,
                                             grupo=grupo, estacion_dias_normales=int(en.sum()), falsas_alarmas=fp,
                                             tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                             parte_pct=100 * fp / fp_total if fp_total else np.nan))
                    if escenario != 'B':
                        continue
                    # Pareado: los episodios conservados, con los puntajes del calendario original y los de B.
                    ao = np.concatenate(So[det])[ok] > u
                    cuenta = np.stack([np.bincount(mes_b, weights=w, minlength=nb)
                                       for w in (y & ao, y & a, y)], axis=1)
                    est, bo = cuenta.sum(axis=0), W @ cuenta
                    r_o, r_b = est[0] / est[2], est[1] / est[2]
                    lo, hi = np.percentile(bo[:, 1] / bo[:, 2] - bo[:, 0] / bo[:, 2], [2.5, 97.5])
                    filas_par.append(dict(anio=anio, delta_pct=d, detector=det, punto=p, estacion_dias=int(est[2]),
                                          recall_original=float(r_o), recall_una_a_la_vez=float(r_b),
                                          diferencia=float(r_b - r_o), ic_bajo=float(lo), ic_alto=float(hi),
                                          excluye_cero=bool(lo > 0 or hi < 0)))
                    normal = ~yo                                               # normales en los dos escenarios
                    for grupo in ('todas',) + tuple(ed.GRUPOS_FA):
                        en = normal & ((go == grupo) if grupo != 'todas' else True)
                        filas_fp.append(dict(anio=anio, delta_pct=d, detector=det, punto=p, grupo=grupo,
                                             estacion_dias=int(en.sum()),
                                             falsas_alarmas_original_pct=100 * float((ao & en).sum()) / max(en.sum(), 1),
                                             falsas_alarmas_una_a_la_vez_pct=100 * float((a & en).sum()) / max(en.sum(), 1)))
            for p in PUNTOS:                                                   # L0 único − V4S compartido
                cuenta = {k: np.stack([np.bincount(mes_b, weights=w, minlength=nb) for w in
                                       (alertas[(k, p)] & y, alertas[(k, p)] & ~y, ~alertas[(k, p)] & y)], axis=1)
                          for k in PAR}
                est = {k: metricas(c.sum(axis=0)) for k, c in cuenta.items()}
                boot = {k: metricas(W @ c) for k, c in cuenta.items()}
                for m in ('f1', 'recall', 'precision'):
                    lo, hi = np.percentile(boot[PAR[0]][m] - boot[PAR[1]][m], [2.5, 97.5])
                    filas_ic.append(dict(anio=anio, escenario=escenario, delta_pct=d, punto=p,
                                         comparacion=f'{PAR[0]} − {PAR[1]}', metrica=m,
                                         detector_1=float(est[PAR[0]][m]), detector_2=float(est[PAR[1]][m]),
                                         diferencia=float(est[PAR[0]][m] - est[PAR[1]][m]), ic_bajo=float(lo),
                                         ic_alto=float(hi), excluye_cero=bool(lo > 0 or hi < 0)))
            print(f'{anio}, escenario {escenario}, δ = {d} %: listo', flush=True)

    for nombre, t in (('resultados', filas), ('falsas_alarmas', filas_fa), ('intervalos', filas_ic),
                      ('pareado_recall', filas_par), ('pareado_falsas_alarmas', filas_fp), ('conteos', conteos)):
        pd.DataFrame(t).to_csv(salida / f'{nombre}.csv', index=False)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=REVISION, anio=anio, prueba=prueba, puntos=PUNTOS, detectores=list(DETECTORES),
        principal=list(PAR), escenarios=dict(B='una estación a la vez (pareado)', A='un solo nodo comprometido'),
        origen=dict(L0_unico='modelo definitivo de δ = 50 % de la revisión 14, cargado de disco',
                    V4S_compartido='modelo definitivo de la revisión 18b, cargado de disco', V4='cargado de disco',
                    R3='sin entrenamiento'),
        sha256_l0_unico=sha(ruta_l0), sha256_v4s_compartido=sha_v4sc, remuestreos=B, sha256_matriz_ajuste=sha_tr,
        control_umbrales_revision18=dif_u, control_limpio_revision18=dif_s0, tolerancia=args.tolerancia), indent=2, ensure_ascii=False))
    if not prueba:
        r = pd.DataFrame(filas)
        print(r[r.evaluacion == 'con ataque'].pivot_table(index=['escenario', 'delta_pct', 'detector'], columns='punto',
                                                          values='f1').round(3).to_string())


if __name__ == '__main__':
    main()
