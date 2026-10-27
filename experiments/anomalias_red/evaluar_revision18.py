"""Revisión 18: comparación justa con el V4, en 2024 y una sola vez en 2025–2026.

Uso (después de entrenar_v4_supervisado.py, y con las matrices de 2024 y del examen final):

    .venv/bin/python experiments/anomalias_red/evaluar_revision18.py [--salida DIR] [--tolerancia-v4 PPB]
    .venv/bin/python experiments/anomalias_red/evaluar_revision18.py --prueba --salida DIR --v4s DIR

Detectores congelados, sin entrenar: el L0 único (el `modelo.keras` de δ = 50 % de lstm_local_examen/c20,
revisión 16), los dos V4 supervisados con δ = 50 % (el compartido de la revisión 18b y el de un modelo por
estación de la revisión 18), R3 (fase 2 de la revisión 12) y el V4 (cargado de disco, inferencia
repetida). Los cinco se juntan por día con el promedio del día.

- (a) **Mismas estación-días:** los cinco se califican en las estación-días válidas para los cinco, con
  umbrales p99 y p99.9 de 2023 limpio en esas mismas estación-días.
- (b) **Peras con peras:** intervalos del 95 % de L0 único − V4S compartido (principal, fijado en la
  revisión 18b) y de L0 único − V4S por estación (contraste), en F1, recall y precisión, por bootstrap
  de bloques estación × mes, 2 000 remuestreos, semilla [42, 18, año] (0 con 2025 y 2026 juntos).
- (c) La curva de recall, precisión y F1 según el umbral (10 a 0.05 % de falsas alarmas) para la gráfica.
- **Control:** el L0 único, R3 y el V4 en sus propias estación-días y con sus umbrales deben reproducir
  la revisión 17 (TP, FP, FN y TN idénticos en 2025 y 2026).

No elige nada. Contexto: la historia limpia anterior a cada año. Con --prueba corre 2024 con 1 calendario
y δ = 100 % para probar el código sin tocar 2025–2026, y no imprime métricas.
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
from src.detect import v4_supervisado as vs  # noqa: E402
import evaluar_estacion_dia as ee  # noqa: E402
from entrenar_lstm_local import REFERENCIA, por_dia  # noqa: E402
from entrenar_lstm_sup import leer, parametros_vecinas  # noqa: E402
from evaluar_v4 import V4, cargar_v4, con_examen, residuos  # noqa: E402
from examen_final import ANIOS as ANIOS_17  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from intervalos_2024 import metricas  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402
from puntos_operacion_2024 import CURVA, LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'revision18'
V4S = SAL / 'v4_supervisado/d50'
V4SC = SAL / 'v4_supervisado_compartido/d50'
PLANES = SAL / 'planes'
CONGELADOS = SAL / 'examen_final_modelos_congelados.json'
EXAMEN_17 = SAL / 'examen_final/resultados.csv'
AGREGACION = 'promedio_dia'
DELTAS = [round(100 * d) for d in ar.DELTAS]
UNICO = 50
B = 2000
DETECTORES = ('L0_unico', 'V4S_compartido', 'V4S_estacion', 'R3', 'V4')
PARES = (('L0_unico', 'V4S_compartido'),         # principal «peras con peras» (revisión 18b)
         ('L0_unico', 'V4S_estacion'))           # contraste
EN_PARES = sorted({d for par in PARES for d in par})
ANIOS = {2024: dict(periodo='prueba_2024', etapa='prueba_2024', limpia='limpia_2024', previas=['limpia_2023']),
         **ANIOS_17}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corridas_de(anio, prueba):
    if anio == 2024:
        c = ar.corridas().iloc[1:1 + ar.CORRIDAS_PRUEBA].reset_index(drop=True)
        return c.iloc[:1] if prueba else c
    c = ar.corridas_finales()
    return c[c.corrida.str.startswith(f'final_{anio}')].reset_index(drop=True)


def validas_todos(puntajes: dict) -> pd.DataFrame:
    """Día × estación: True donde los cuatro detectores tienen puntaje."""
    ok = puntajes[DETECTORES[0]].notna()
    for k in DETECTORES[1:]:
        ok &= puntajes[k].notna()
    return ok


def cargar_v4s(carpeta: Path, objetivos, prueba):
    """{objetivo: modelo} del V4S, verificando su configuración y el SHA-256 de cada modelo."""
    from tensorflow import keras
    modelos, shas = {}, {}
    for s in objetivos:
        c = carpeta / s
        if not (c / 'modelo.keras').exists():
            if prueba:
                continue
            raise RuntimeError(f'{s}: falta el modelo del V4S')
        conf = json.loads((c / 'configuracion.json').read_text())
        if conf['revision'] != vs.REVISION or conf['delta_pct'] != UNICO or 'definitivo' not in conf:
            raise RuntimeError(f'{s}: no es el V4S definitivo de la revisión 18')
        if conf['prueba'] != prueba:
            raise RuntimeError(f'{s}: el modelo es de prueba={conf["prueba"]} y la evaluación de prueba={prueba}')
        shas[s] = sha(c / 'modelo.keras')
        if shas[s] != conf['sha256']['modelo']:
            raise RuntimeError(f'{s}: modelo.keras no coincide con su SHA-256 guardado')
        modelos[s] = keras.models.load_model(c / 'modelo.keras', compile=False)
    return modelos, shas


def cargar_v4s_compartido(carpeta: Path, objetivos, prueba):
    """El V4S compartido (revisión 18b), verificando su configuración, su SHA-256 y el orden de entradas."""
    from tensorflow import keras
    from src.detect.vecinas import distancias
    from entrenar_lstm_sup import GEOGRAFIA
    conf = json.loads((carpeta / 'configuracion.json').read_text())
    if conf['revision'] != '18b' or conf['delta_pct'] != UNICO or 'definitivo' not in conf or conf['prueba'] != prueba:
        raise RuntimeError('no es el V4S compartido definitivo de la revisión 18b (o no coincide --prueba)')
    if sha(carpeta / 'modelo.keras') != conf['sha256']['modelo']:
        raise RuntimeError('el modelo del V4S compartido no coincide con su SHA-256 guardado')
    dist = distancias(pd.read_csv(GEOGRAFIA, index_col='station'))
    ordenes = {s: vs.orden_por_distancia(s, dist) for s in objetivos}
    if ordenes != conf['ordenes']:
        raise RuntimeError('el orden por distancia no es el del entrenamiento')
    return keras.models.load_model(carpeta / 'modelo.keras', compile=False), ordenes, conf['sha256']['modelo']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--v4s', type=Path, default=V4S)
    ap.add_argument('--v4s-compartido', type=Path, default=V4SC)
    ap.add_argument('--tolerancia-v4', type=float, default=None)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    salida, prueba = args.salida, args.prueba
    salida.mkdir(parents=True, exist_ok=True)
    anios = {2024: ANIOS[2024]} if prueba else ANIOS
    deltas = [100] if prueba else DELTAS
    if args.tolerancia_v4 is not None:
        ee.TOLERANCIA_PPB = args.tolerancia_v4
    objetivos = alterables_v4()

    # Detectores congelados.
    from tensorflow import keras
    ruta_l0 = LSTM / f'd{UNICO}' / 'modelo.keras'
    if sha(ruta_l0) != json.loads(CONGELADOS.read_text())['L0'][f'L0_d{UNICO}']:
        raise RuntimeError('el L0 único no es el registrado antes del examen final')
    l0m = keras.models.load_model(ruta_l0, compile=False)
    modelos_v4, p95 = cargar_v4()
    modelos_v4s, sha_v4s = cargar_v4s(args.v4s, objetivos, prueba)   # con --prueba, sólo algunas estaciones
    modelo_c, ordenes, sha_v4sc = cargar_v4s_compartido(args.v4s_compartido, objetivos, prueba)
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
        prob = vs.probabilidades(modelos_v4s, v, dfn['inactivos'], dfn['mu'], dfn['sigma'], etapa, matriz.index)
        prob_c = vs.probabilidades({s: modelo_c for s in objetivos}, v, dfn['inactivos'], dfn['mu'], dfn['sigma'],
                                   etapa, matriz.index, ordenes=ordenes)
        return {'L0_unico': l0, 'V4S_compartido': ed.juntar_dia(prob_c[objetivos], AGREGACION),
                'V4S_estacion': ed.juntar_dia(prob.reindex(columns=objetivos), AGREGACION), 'R3': r3, 'V4': v4}

    def umbrales(limpio, validas):
        c = limpio[validas].stack().dropna().to_numpy()
        return {p: ev.umbral_falsas_alarmas(c, fa) for p, fa in PUNTOS.items()}

    # 2023 limpio: los umbrales. El V4 usa sus residuos de calibración guardados, como en la revisión 17.
    cal, _ = leer('limpia_2023')
    r23 = pd.DataFrame({o: pd.read_csv(V4 / o / 'calibracion_2023.csv.gz', parse_dates=['timestamp'],
                                       index_col='timestamp')['residuo_ppb'] for o in modelos_v4}).reindex(cal.index)
    u23 = puntajes(limpia_tr, cal, 'calibracion', v4_guardado=r23)
    comun23 = validas_todos(u23)
    propias23 = {'L0_unico': u23['R3'].notna() & u23['L0_unico'].notna(), 'R3': u23['R3'].notna() & u23['L0_unico'].notna(),
                 'V4': u23['V4'].notna(), 'V4S_compartido': u23['V4S_compartido'].notna(),
                 'V4S_estacion': u23['V4S_estacion'].notna()}
    U = {(k, 'comunes'): umbrales(u23[k], comun23) for k in DETECTORES}
    U.update({(k, 'propias'): umbrales(u23[k], propias23[k]) for k in DETECTORES})
    print('umbrales:', {f'{k}/{v}': {p: round(x, 4) for p, x in u.items()} for (k, v), u in U.items()}, flush=True)

    filas, filas_fa, filas_ic, conteos, curva, dias_guardados = [], [], [], [], [], {}
    acumulado = {}
    for anio, cfg in anios.items():
        corridas = corridas_de(anio, prueba)
        limpia_y, _ = leer(cfg['limpia'])
        historia = limpia_tr
        for n in cfg['previas']:
            historia = ev.con_historia(historia, leer(n)[0])
        dias = limpia_y.index.normalize().unique()
        S0 = puntajes(historia, limpia_y, cfg['etapa'])
        guardar = [S0[k].assign(conjunto=cfg['limpia'], detector=k) for k in DETECTORES]
        validas = {'comunes': {k: validas_todos(S0) for k in DETECTORES},
                   'propias': {'L0_unico': S0['R3'].notna() & S0['L0_unico'].notna(),
                               'R3': S0['R3'].notna() & S0['L0_unico'].notna(),
                               'V4': S0['V4'].notna(), 'V4S_compartido': S0['V4S_compartido'].notna(),
                               'V4S_estacion': S0['V4S_estacion'].notna()}}
        mes = np.tile((np.arange(len(objetivos))[None, :] * 12 + (dias.month.to_numpy() - 1)[:, None]).ravel(),
                      len(corridas))
        for d in deltas:
            S, Y, G = {}, [], []
            for c in corridas.itertuples():
                plan = ar.leer_plan(PLANES / f'plan_{c.corrida}.csv')
                x, _ = leer(f'{c.corrida}_d{d}')
                Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel().astype(float))
                G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vec.vecinas).to_numpy().ravel())
                S[c.corrida] = puntajes(historia, x, cfg['etapa'])
                guardar += [S[c.corrida][k].assign(conjunto=f'{c.corrida}_d{d}', detector=k) for k in DETECTORES]
            Y, G = np.concatenate(Y), np.concatenate(G)
            for version, val in validas.items():
                for det in DETECTORES:
                    ok = np.tile(val[det].to_numpy().ravel(), len(corridas)) & ~np.isnan(Y)
                    y = Y[ok] == 1.0
                    s = np.concatenate([S[c][det].to_numpy().ravel() for c in S])[ok]
                    s0 = np.tile(S0[det].to_numpy().ravel(), len(corridas))[ok]
                    conteos.append(dict(anio=anio, dias=version, delta_pct=d, detector=det, atacadas=int(y.sum()),
                                        normales=int((~y).sum())))
                    auc = {'con ataque': dict(pr_auc=average_precision_score(y, s), roc_auc=roc_auc_score(y, s)),
                           'sin ataque': dict(pr_auc=average_precision_score(y, s0), roc_auc=roc_auc_score(y, s0))}
                    for p in PUNTOS:
                        u = U[(det, version)][p]
                        for v, puntaje in (('con ataque', s), ('sin ataque', s0)):
                            filas.append(dict(anio=anio, dias=version, delta_pct=d, detector=det, punto=p,
                                              evaluacion=v, umbral=u, **con_umbral(y, puntaje > u), **auc[v]))
                    if version != 'comunes':
                        continue
                    c23 = u23[det][comun23].stack().dropna().to_numpy()
                    for fa in CURVA:
                        m = con_umbral(y, s > ev.umbral_falsas_alarmas(c23, fa))
                        curva.append(dict(anio=anio, delta_pct=d, detector=det, fa_objetivo_pct=100 * fa,
                                          recall=m['recall'], precision=m['precision'], f1=m['f1'],
                                          fa_examen_pct=100 * m['falsas_alarmas'], tp=m['tp'], fp=m['fp']))
                    for p in PUNTOS:
                        alerta = s > U[(det, version)][p]
                        if det in EN_PARES:
                            acumulado.setdefault((d, p, det), []).append((anio, y, alerta, mes[ok]))
                        g = G[ok]
                        fp_total = int((alerta & ~y).sum())
                        for grupo in ed.GRUPOS_FA:
                            en = g == grupo
                            fp = int((alerta & en).sum())
                            filas_fa.append(dict(anio=anio, delta_pct=d, detector=det, punto=p, grupo=grupo,
                                                 estacion_dias_normales=int(en.sum()), falsas_alarmas=fp,
                                                 tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                                 parte_pct=100 * fp / fp_total if fp_total else np.nan))
            print(f'{anio}, δ = {d} %: listo', flush=True)
        dias_guardados[anio] = pd.concat(guardar).rename_axis('dia').reset_index()

    # (b) Intervalos del 95 % de L0 único − V4S (compartido y por estación), por año y con 2025 y 2026 juntos.
    claves = sorted({(d, p) for d, p, _ in acumulado})
    for (d, p), (uno, otro) in [(k, par) for k in claves for par in PARES]:
        partes = acumulado[(d, p, uno)]
        grupos = [(str(a), [i for i, x in enumerate(partes) if x[0] == a]) for a in anios]
        if {2025, 2026} <= set(anios):
            grupos.append(('2025-2026', [i for i, x in enumerate(partes) if x[0] in (2025, 2026)]))
        for etiqueta, sel in grupos:
            conteo = {}
            for nombre in (uno, otro):
                lista = acumulado[(d, p, nombre)]
                y = np.concatenate([lista[i][1] for i in sel])
                a = np.concatenate([lista[i][2] for i in sel])
                b = np.concatenate([lista[i][3] + 1000 * k for k, i in enumerate(sel)])   # bloques por año
                _, b = np.unique(b, return_inverse=True)
                conteo[nombre] = np.stack([np.bincount(b, weights=w, minlength=b.max() + 1)
                                           for w in (a & y, a & ~y, ~a & y)], axis=1)
            nb = conteo[uno].shape[0]
            semilla = [42, vs.REVISION, int(etiqueta) if etiqueta.isdigit() else 0]
            W = np.random.default_rng(semilla).multinomial(nb, np.full(nb, 1 / nb), size=B)
            est = {k: metricas(c.sum(axis=0)) for k, c in conteo.items()}
            boot = {k: metricas(W @ c) for k, c in conteo.items()}
            for m in ('f1', 'recall', 'precision'):
                lo, hi = np.percentile(boot[uno][m] - boot[otro][m], [2.5, 97.5])
                filas_ic.append(dict(anio=etiqueta, delta_pct=d, punto=p, comparacion=f'{uno} − {otro}',
                                     principal=(uno, otro) == PARES[0], metrica=m, detector_1=float(est[uno][m]),
                                     detector_2=float(est[otro][m]), diferencia=float(est[uno][m] - est[otro][m]),
                                     ic_bajo=float(lo), ic_alto=float(hi), excluye_cero=bool(lo > 0 or hi < 0)))

    r = pd.DataFrame(filas)
    r.to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    pd.DataFrame(filas_ic).to_csv(salida / 'intervalos.csv', index=False)
    pd.DataFrame(conteos).to_csv(salida / 'conteos.csv', index=False)
    pd.DataFrame(curva).to_csv(salida / 'curva.csv', index=False)
    for anio, t in dias_guardados.items():
        t[['conjunto', 'detector', 'dia'] + objetivos].to_csv(salida / f'dias_{anio}.csv.gz', index=False)

    # Control: en sus propias estación-días, el L0 único, R3 y el V4 reproducen la revisión 17.
    control = []
    if not prueba:
        e17 = pd.read_csv(EXAMEN_17)
        e17 = e17[(e17.version == 'medianoche')].set_index(['anio', 'delta_pct', 'detector', 'punto', 'evaluacion'])
        for f in r[(r.dias == 'propias') & r.detector.isin(['L0_unico', 'R3', 'V4']) & r.anio.isin([2025, 2026])].itertuples():
            ref = e17.loc[(f.anio, f.delta_pct, f.detector, f.punto, f.evaluacion)]
            control.append(dict(anio=f.anio, delta_pct=f.delta_pct, detector=f.detector, punto=f.punto,
                                evaluacion=f.evaluacion, igual=bool(all(getattr(f, k) == ref[k] for k in ('tp', 'fp', 'fn', 'tn')))))
        pd.DataFrame(control).to_csv(salida / 'control_revision17.csv', index=False)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision='18 y 18b', anios=list(anios), prueba=prueba, puntos=PUNTOS,
        detectores=list(DETECTORES), principal=list(PARES[0]), contraste=list(PARES[1]),
        origen=dict(L0_unico='modelo definitivo de δ = 50 % de la revisión 14, cargado de disco',
                    V4S_compartido='modelo definitivo de la revisión 18b, cargado de disco',
                    V4S_estacion='modelos definitivos de la revisión 18, cargados de disco', V4='cargado de disco',
                    R3='sin entrenamiento'),
        sha256_l0_unico=sha(ruta_l0), sha256_v4s_compartido=sha_v4sc, sha256_v4s_estacion=sha_v4s, remuestreos=B,
        sha256_matriz_ajuste=sha_tr,
        control_revision17_igual=bool(all(c['igual'] for c in control)) if control else None,
        tolerancia_control_v4_ppb=args.tolerancia_v4 or ee.TOLERANCIA_PPB), indent=2, ensure_ascii=False))
    if control and not all(c['igual'] for c in control):
        raise RuntimeError('en sus propias estación-días, algún detector no reproduce la revisión 17')
    if not prueba:
        print(r[(r.dias == 'comunes') & (r.evaluacion == 'con ataque')].pivot_table(
            index=['anio', 'delta_pct', 'detector'], columns='punto', values='f1').round(3).to_string())


if __name__ == '__main__':
    main()
