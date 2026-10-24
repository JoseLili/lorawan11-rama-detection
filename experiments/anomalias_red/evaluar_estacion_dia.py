"""Fase 2 de la revisión 11: examen 2024 por estación-día, con la regla de vecinas o el V4 (en la lap).

Uso (desde la raíz del repo, con la fase 1 ya corrida):

    .venv/bin/python experiments/anomalias_red/evaluar_estacion_dia.py --detector regla
    .venv/bin/python experiments/anomalias_red/evaluar_estacion_dia.py --detector v4

Valor por hora y estación, con signo (`src/detect/estacion_dia.py` junta el día de las dos formas):
- regla: la columna de vecinas a14 con media, con referencia y escala de 2020–2022 limpio y la
  historia limpia anterior como contexto (como `evaluar_regla_vecinas.py`). Sin entrenamiento;
- v4: el residuo de la estación entre su p95 de 2023, con el V4 cargado de disco y la inferencia
  repetida sobre cada matriz alterada (como `evaluar_v4.py`). 2023 usa los residuos guardados.

Umbral para las 31 estaciones con 1 y 5 % de falsas alarmas en las estación-días de 2023 limpio;
examen con los 10 calendarios de 2024 juntos; «sin ataque» con 2024 limpio. Decide el promedio del
día (elegido en la fase 1); la peor hora se reporta. Métricas de la revisión 9, falsas alarmas con
1 % por grupo y estación-días excluidas.

Controles: el puntaje de red que sale de estos valores debe reproducir el guardado por
`evaluar_regla_vecinas.py` o `evaluar_v4.py` (6 cifras); el V4 además reproduce sus predicciones de
2024 limpio y repite el primer calendario con valores idénticos.

Revisión 12, sólo con la regla: `--referencia mediana` (perfil de 14 días con la mediana) y
`--dominancia` (`estacion_dia.dominancia`, contra el contagio). Con los valores por defecto da la
revisión 11. Con la mediana no hay puntaje de red guardado contra el cual controlar; con la
dominancia se reportan además las estación-días atacadas que apaga.

Salidas en results/anomalias_red_v1/estacion_dia/<detector>/ (regla_mediana, regla_dominancia o
regla_mediana_dominancia en la revisión 12; o --salida). Con --prueba (1 calendario, δ = 100 %)
sólo comprueba que corre: no imprime métricas.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
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
from entrenar_lstm_sup import leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral, puntajes  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PLANES = SAL / 'planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'
GUARDADOS = {'regla': SAL / 'regla_vecinas_a14', 'v4': SAL / 'v4'}
DECIDE = 'promedio_dia'                           # elegida en la fase 1
TOLERANCIA_RED = 1e-5                             # los puntajes de red se guardaron con 6 cifras
TOLERANCIA_PPB = 1e-9


def normalizacion_y_vecinas(referencia='media'):
    limpia_tr, sha = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    return limpia_tr, sha, sigma, parametros_vecinas('a14', limpia_tr, sigma, referencia)


def valores_regla(examen, limpia_tr, sigma, vec):
    """(nombre, valores hora × estación, puntaje de red) de 2023 limpio, 2024 limpio y el examen."""
    def columnas(previa, matriz):
        return ev.columnas_vecinas(ev.con_historia(previa, matriz), sigma, vec).iloc[len(previa):]

    cal, _ = leer('limpia_2023')
    historia = ev.con_historia(limpia_tr, cal)
    for nombre, previa in [('limpia_2023', limpia_tr), ('limpia_2024', historia)] + [(c, historia) for c in examen]:
        col = columnas(previa, leer(nombre)[0])
        yield nombre, col, col.abs().fillna(0.0).max(axis=1)


def valores_v4(examen):
    """Como `valores_regla`, con el residuo / p95 del V4 (cargado de disco, sin reentrenar)."""
    from evaluar_v4 import V4, cargar_v4, con_examen, puntaje_red, residuos
    from src.detect import entrenamiento_multianual as em
    ctx = em.contexto(RAIZ)
    valores, dfn = ctx['valores'], ctx['definitiva']
    if list(dfn['inactivos']) != ['XAL']:
        raise RuntimeError(f'canales inactivos inesperados: {dfn["inactivos"]}')
    modelos, p95 = cargar_v4()
    cal = ar.leer_matriz(SAL / 'matrices/matriz_limpia_2023.csv.gz')
    limpia = ar.leer_matriz(SAL / 'matrices/matriz_limpia_2024.csv.gz')
    res = pd.DataFrame({obj: pd.read_csv(V4 / obj / 'calibracion_2023.csv.gz', parse_dates=['timestamp'],
                                         index_col='timestamp')['residuo_ppb'] for obj in modelos}).reindex(cal.index)
    yield 'limpia_2023', res / p95[res.columns], puntaje_red(res, p95)['puntaje']
    res = residuos(modelos, valores, dfn, limpia.index)
    dif = 0.0
    for obj in modelos:                                # 2024 limpio reproduce las predicciones guardadas
        r, g = res[obj].dropna(), V4 / obj / 'predicciones_2024.csv.gz'
        if g.exists():
            g = pd.read_csv(g, parse_dates=['timestamp'], index_col='timestamp')['residuo_ppb']
            if not r.index.equals(g.index):
                raise RuntimeError(f'{obj}: horas con predicción distintas a las guardadas')
            dif = max(dif, float(np.abs(r.to_numpy() - g.to_numpy()).max()))
        elif len(r):
            raise RuntimeError(f'{obj}: hay predicciones en 2024 y no estaban guardadas')
    if dif > TOLERANCIA_PPB:
        raise RuntimeError(f'el 2024 limpio no reproduce las predicciones guardadas (máx. {dif} ppb)')
    print(f'V4 cargado de disco ({len(modelos)} estaciones); 2024 limpio reproduce sus predicciones '
          f'(diferencia máxima {dif:.1e} ppb)', flush=True)
    yield 'limpia_2024', res / p95[res.columns], puntaje_red(res, p95)['puntaje']
    for i, c in enumerate(examen):
        x = ar.leer_matriz(SAL / f'matrices/matriz_{c}.csv.gz')
        res = residuos(modelos, con_examen(valores, x), dfn, limpia.index)
        if i == 0:                                     # reproducibilidad: el primer calendario otra vez
            if not res.equals(residuos(modelos, con_examen(valores, x), dfn, limpia.index)):
                raise RuntimeError(f'dos inferencias de {c} dieron residuos distintos')
        yield c, res / p95[res.columns], puntaje_red(res, p95)['puntaje']


def control_red(detector, nombre, red):
    """El puntaje de red debe reproducir el guardado por el script original del detector."""
    if nombre.startswith('limpia'):
        carpeta, columna = GUARDADOS[detector] / 'd100', nombre
    else:
        corrida, d = nombre.rsplit('_d', 1)
        carpeta, columna = GUARDADOS[detector] / f'd{d}', corrida
    g = puntajes(carpeta)[columna].reindex(red.index)
    np.testing.assert_allclose(red.to_numpy(), g.to_numpy(), rtol=TOLERANCIA_RED, atol=1e-9,
                               err_msg=f'{detector} {nombre}: el puntaje de red no reproduce el guardado')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detector', choices=tuple(GUARDADOS), required=True)
    ap.add_argument('--salida', type=Path)
    ap.add_argument('--prueba', action='store_true')
    ap.add_argument('--referencia', choices=ev.REFERENCIAS, default='media', help='revisión 12, sólo con la regla')
    ap.add_argument('--dominancia', action='store_true', help='revisión 12, sólo con la regla')
    args = ap.parse_args()
    detector, prueba, referencia, dom = args.detector, args.prueba, args.referencia, args.dominancia
    if detector != 'regla' and (referencia != 'media' or dom):
        raise SystemExit('--referencia y --dominancia sólo se definen para la regla')
    nombre_salida = detector if referencia == 'media' and not dom else (
        f"regla{'_mediana' if referencia == 'mediana' else ''}{'_dominancia' if dom else ''}")
    salida = args.salida or SAL / 'estacion_dia' / nombre_salida
    deltas, n_cal = ((100,), 1) if prueba else ([round(100 * d) for d in ar.DELTAS], ar.CORRIDAS_PRUEBA)
    salida.mkdir(parents=True, exist_ok=True)

    limpia_tr, sha_tr, sigma, vec = normalizacion_y_vecinas(referencia)
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + n_cal].tolist()
    examen = [f'{c}_d{d}' for d in deltas for c in corridas]
    fuente = valores_regla(examen, limpia_tr, sigma, vec) if detector == 'regla' else valores_v4(examen)
    dia, sin_dominancia = {}, {}
    for nombre, valores, red in fuente:
        if referencia == 'media':
            control_red(detector, nombre, red)
        dia[nombre] = {a: ed.juntar_dia(valores[objetivos], a) for a in ed.AGREGACIONES}
        if dom:
            sin_dominancia[nombre] = dia[nombre]
            dia[nombre] = {a: ed.dominancia(s, vec.vecinas) for a, s in dia[nombre].items()}
        print(f'  {nombre}: listo', flush=True)

    umbrales, filas_u = {}, []
    for a in ed.AGREGACIONES:
        cal = dia['limpia_2023'][a].stack().dropna().to_numpy()
        for fa in ev.NIVELES_FA:
            u = ev.umbral_falsas_alarmas(cal, fa)
            umbrales[a, round(100 * fa)] = u
            filas_u.append(dict(agregacion=a, nivel_fa_pct=round(100 * fa), umbral=u, estacion_dias_2023=len(cal),
                                falsas_alarmas_2023=float((cal > u).mean())))
    pd.DataFrame(filas_u).to_csv(salida / 'umbrales.csv', index=False)

    dias = dia['limpia_2024']['peor_hora'].index
    filas, filas_fa, filas_ex, filas_ap = [], [], [], []
    for d in deltas:
        Y, G = [], []
        for c in corridas:
            plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
            Y.append(ed.etiquetas(plan, dias, objetivos).to_numpy().ravel())
            G.append(ed.grupos_falsa_alarma(plan, dias, objetivos, vec.vecinas).to_numpy().ravel())
        y, g = np.concatenate(Y), np.concatenate(G)
        for a in ed.AGREGACIONES:
            limpio = dia['limpia_2024'][a]
            for c in corridas:
                s = dia[f'{c}_d{d}'][a]
                assert s.index.equals(dias) and s.notna().equals(limpio.notna())
            s = np.concatenate([dia[f'{c}_d{d}'][a].to_numpy().ravel() for c in corridas])
            s0 = np.tile(limpio.to_numpy().ravel(), len(corridas))
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
                    filas.append(dict(detector=detector, delta_pct=d, agregacion=a, decide=a == DECIDE,
                                      nivel_fa_pct=nivel, version=version, umbral=u,
                                      **con_umbral(yv, puntaje > u), **auc))
            if dom:                                    # lo que apaga la dominancia en los días atacados
                sb = np.concatenate([sin_dominancia[f'{c}_d{d}'][a].to_numpy().ravel() for c in corridas])[ok]
                apagada = yv & (sv == 0) & (sb > 0)
                filas_ap.append(dict(detector=nombre_salida, delta_pct=d, agregacion=a, atacadas_validas=int(yv.sum()),
                                     apagadas=int(apagada.sum())))
            alerta = sv > umbrales[a, 1]
            fp_total = int((alerta & ~yv).sum())
            for grupo in ed.GRUPOS_FA:
                en = gv == grupo
                fp = int((alerta & en).sum())
                filas_fa.append(dict(detector=detector, delta_pct=d, agregacion=a, grupo=grupo,
                                     estacion_dias_normales=int(en.sum()), falsas_alarmas=fp,
                                     tasa_pct=100 * fp / en.sum() if en.any() else np.nan,
                                     parte_pct=100 * fp / fp_total if fp_total else np.nan))

    r = pd.DataFrame(filas)
    r.to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(filas_fa).to_csv(salida / 'falsas_alarmas.csv', index=False)
    pd.DataFrame(filas_ex).to_csv(salida / 'excluidas.csv', index=False)
    if dom:
        pd.DataFrame(filas_ap).to_csv(salida / 'apagadas.csv', index=False)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=11 if nombre_salida == detector else 12, fase=2, detector=detector,
        referencia_14_dias=referencia, dominancia=dom, decide=DECIDE,
        origen=('sin entrenamiento (referencia y escala con 2020–2022 limpio)' if detector == 'regla'
                else 'V4 cargado de disco, inferencia repetida en la lap'),
        valor_por_hora=('columna de vecinas a14 con media' if detector == 'regla'
                        else 'residuo / p95 de 2023, con signo'),
        fecha=datetime.now().isoformat(timespec='seconds'), calendarios=corridas, deltas_pct=list(deltas),
        min_horas=ed.MIN_HORAS, umbrales={f'{a}_{n}': u for (a, n), u in umbrales.items()},
        sha256_matriz_ajuste=sha_tr,
        controles=(('puntaje de red igual al guardado por el script original (rtol 1e-5)' if referencia == 'media'
                    else 'sin puntaje de red guardado con la mediana: no hay control contra el original')
                   + ('' if detector == 'regla' else '; 2024 limpio reproduce predicciones_2024 (1e-9 ppb); '
                      'primer calendario repetido con residuos idénticos')),
        prueba=prueba), indent=2, ensure_ascii=False))
    if not prueba:
        columnas = ['delta_pct', 'agregacion', 'nivel_fa_pct', 'version', 'f1', 'f2', 'precision', 'recall',
                    'falsas_alarmas', 'mcc', 'pr_auc']
        print(r[columnas].round(4).to_string(index=False))
        print(pd.DataFrame(filas_fa).round(2).to_string(index=False))
        print(pd.DataFrame(filas_ex).to_string(index=False))


if __name__ == '__main__':
    main()
