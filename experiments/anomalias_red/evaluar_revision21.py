"""Revisión 21: evaluación del error fijo en ppb, un año a la vez. No entrena ni elige nada.

Uso (después de generar_revision21.py --anio AÑO, con los puntajes de la revisión 18 de ese año):

    .venv/bin/python experiments/anomalias_red/evaluar_revision21.py --anio 2025 [--salida DIR]
    .venv/bin/python experiments/anomalias_red/evaluar_revision21.py --anio 2024 --prueba --salida DIR --tolerancia 1e-6

Detectores congelados, como en la revisión 19: el L0 único, el V4S compartido (revisión 18b), R3 y el V4, con los
umbrales p99 y p99.9 «comunes» de 2023 limpio (los de la revisión 18) y la historia limpia anterior al año. PARAAD se
califica aparte, en su entorno (`puntuar_paraad.py`), y se une con `resumir_revision21.py`.

- Métricas completas por a ∈ {5, 10, 20, 40} ppb, con su valor sin ataque, y falsas alarmas por grupo.
- L0 único − V4S compartido (F1, recall y precisión), bootstrap de bloques estación × mes, 2 000 remuestreos,
  semilla [42, 21, año].
- Contra el proporcional: el recall de cada detector en las mismas estación-días atacadas, con los puntajes del
  calendario original de la revisión 18 para cada δ.
- Guarda los puntajes por estación-día (`dias_<año>.csv.gz`) para unirlos con los de PARAAD.

Controles, como en la revisión 19: los umbrales son los comunes de la revisión 18 y los puntajes del año limpio son
idénticos a los guardados. Con --prueba: 2024, 1 calendario y a = 20; sólo comprueba que corre.
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
SALIDA = SAL / 'revision21'
REVISION18 = SAL / 'revision18'
DETECTORES = ('L0_unico', 'V4S_compartido', 'R3', 'V4')
PAR = ('L0_unico', 'V4S_compartido')
REVISION = 21


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
    tamanos = [20] if prueba else list(ar.TAMANOS_FIJOS)
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

    # 2023 limpio: umbrales comunes; control contra la revisión 18.
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
    corridas = calendarios_prueba(anio).corrida.tolist()[:1 if prueba else None]

    guardar = [S0[k].assign(conjunto=cfg['limpia'], detector=k) for k in DETECTORES]
    filas, filas_fa, filas_ic, filas_prop, conteos = [], [], [], [], []
    for a in tamanos:
        Y, G, S, mes = [], [], {k: [] for k in DETECTORES}, []
        for k, c in enumerate(corridas):
            plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
            x, _ = leer(f'fijo_{c}_a{a}')
            s = puntajes(historia, x, cfg['etapa'])
            Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
            G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vec.vecinas).to_numpy().ravel())
            for det in DETECTORES:
                S[det].append(s[det].to_numpy().ravel())
            guardar += [s[det].assign(conjunto=f'fijo_{c}_a{a}', detector=det) for det in DETECTORES]
            mes.append(mes1 + 1000 * k)
        ok = np.tile(val, len(corridas))
        y, g = np.concatenate(Y)[ok] == 1.0, np.concatenate(G)[ok]
        _, mes_b = np.unique(np.concatenate(mes)[ok], return_inverse=True)
        nb = mes_b.max() + 1
        W = np.random.default_rng([42, REVISION, anio]).multinomial(nb, np.full(nb, 1 / nb), size=B)
        conteos.append(dict(anio=anio, a_ppb=a, calendarios=len(corridas), atacadas=int(y.sum()), normales=int((~y).sum())))
        alertas = {}
        for det in DETECTORES:
            sc = np.concatenate(S[det])[ok]
            s0 = np.tile(S0[det].to_numpy().ravel(), len(corridas))[ok]
            auc = {'con ataque': dict(pr_auc=average_precision_score(y, sc), roc_auc=roc_auc_score(y, sc)),
                   'sin ataque': dict(pr_auc=average_precision_score(y, s0), roc_auc=roc_auc_score(y, s0))}
            for p in PUNTOS:
                u = U[det][p]
                for v_, puntaje in (('con ataque', sc), ('sin ataque', s0)):
                    filas.append(dict(anio=anio, a_ppb=a, detector=det, punto=p, evaluacion=v_, umbral=u,
                                      **con_umbral(y, puntaje > u), **auc[v_]))
                al = sc > u
                alertas[(det, p)] = al
                fp_total = int((al & ~y).sum())
                for grupo in ed.GRUPOS_FA:
                    en = g == grupo
                    fp = int((al & en).sum())
                    filas_fa.append(dict(anio=anio, a_ppb=a, detector=det, punto=p, grupo=grupo,
                                         estacion_dias_normales=int(en.sum()), falsas_alarmas=fp,
                                         tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                         parte_pct=100 * fp / fp_total if fp_total else np.nan))
                # Contra el proporcional: el recall de los mismos episodios con cada δ (revisión 18).
                if a == tamanos[0]:
                    for d in DELTAS:
                        so = np.concatenate([de_18(f'{c}_d{d}', det).to_numpy().ravel() for c in corridas])[ok]
                        filas_prop.append(dict(anio=anio, detector=det, punto=p, forma='proporcional', tamano=f'δ = {d} %',
                                               estacion_dias=int(y.sum()), recall=float((so[y] > u).mean())))
                filas_prop.append(dict(anio=anio, detector=det, punto=p, forma='fijo', tamano=f'{a} ppb',
                                       estacion_dias=int(y.sum()), recall=float(al[y].mean())))
        for p in PUNTOS:
            cuenta = {k: np.stack([np.bincount(mes_b, weights=w, minlength=nb) for w in
                                   (alertas[(k, p)] & y, alertas[(k, p)] & ~y, ~alertas[(k, p)] & y)], axis=1)
                      for k in PAR}
            est = {k: metricas(c_.sum(axis=0)) for k, c_ in cuenta.items()}
            boot = {k: metricas(W @ c_) for k, c_ in cuenta.items()}
            for m in ('f1', 'recall', 'precision'):
                lo, hi = np.percentile(boot[PAR[0]][m] - boot[PAR[1]][m], [2.5, 97.5])
                filas_ic.append(dict(anio=anio, a_ppb=a, punto=p, comparacion=f'{PAR[0]} − {PAR[1]}', metrica=m,
                                     detector_1=float(est[PAR[0]][m]), detector_2=float(est[PAR[1]][m]),
                                     diferencia=float(est[PAR[0]][m] - est[PAR[1]][m]), ic_bajo=float(lo),
                                     ic_alto=float(hi), excluye_cero=bool(lo > 0 or hi < 0)))
        print(f'{anio}, a = {a} ppb: listo', flush=True)

    for nombre, t in (('resultados', filas), ('falsas_alarmas', filas_fa), ('intervalos', filas_ic),
                      ('contra_proporcional', filas_prop), ('conteos', conteos)):
        pd.DataFrame(t).to_csv(salida / f'{nombre}.csv', index=False)
    pd.concat(guardar).rename_axis('dia').reset_index()[['conjunto', 'detector', 'dia'] + objetivos].to_csv(
        salida / f'dias_{anio}.csv.gz', index=False)
    pd.DataFrame(validas(S0).astype(int)).rename_axis('dia').to_csv(salida / 'mascara_comun.csv')
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=REVISION, anio=anio, prueba=prueba, puntos=PUNTOS, tamanos_ppb=tamanos,
        detectores=list(DETECTORES), principal=list(PAR),
        origen=dict(L0_unico='modelo definitivo de δ = 50 % de la revisión 14, cargado de disco',
                    V4S_compartido='modelo definitivo de la revisión 18b, cargado de disco', V4='cargado de disco',
                    R3='sin entrenamiento'),
        sha256_l0_unico=sha(ruta_l0), sha256_v4s_compartido=sha_v4sc, remuestreos=B, sha256_matriz_ajuste=sha_tr,
        control_umbrales_revision18=dif_u, control_limpio_revision18=dif_s0, tolerancia=args.tolerancia),
        indent=2, ensure_ascii=False))
    if not prueba:
        r = pd.DataFrame(filas)
        print(r[r.evaluacion == 'con ataque'].pivot_table(index=['a_ppb', 'detector'], columns='punto',
                                                          values='f1').round(3).to_string())


if __name__ == '__main__':
    main()
