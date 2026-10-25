"""LSTM V4 de la parte 1 sobre las matrices de red alteradas, un δ a la vez (§8, §9 y revisión 5).

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/evaluar_v4.py --delta 100

No entrena ni recalibra: carga de disco los 31 modelos del V4 y sus p95 de 2023.
1. Reconstruye la serie del V4 desde los zip y exige que la matriz limpia de 2024 sea igual.
2. Puntaje de red = máximo de |residuo| / p95 entre estaciones. Umbrales de 5 y 1 % de falsas
   alarmas por hora de red con los residuos de 2023 guardados; además, el nivel original del
   V4 (puntaje > 1: alguna estación pasa su p95).
3. 2024 limpio por la misma vía: debe reproducir las predicciones guardadas.
4. Examen con los 10 calendarios del δ: se sustituyen las horas de 2024 por las de la matriz
   alterada y se repite la inferencia de las 31 estaciones. Mismas métricas que el Random
   Forest y el IsolationForest, más la estación que da el máximo.
5. Repite el primer calendario y exige el mismo puntaje.

Salidas en results/anomalias_red_v1/v4/d<δ>/. Si ya existen, se detiene (usar --sustituir).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import multianual as m  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
V4 = RAIZ / 'results/lstm_v4_multianual_v1/estaciones'
ETAPA = 'prueba_2024'
TOLERANCIA_PPB = 1e-9    # sólo el paso por texto de los CSV guardados


def cargar_v4():
    """{objetivo: modelo} y p95 por estación, verificando el SHA-256 de cada modelo."""
    from tensorflow import keras
    modelos, p95 = {}, {}
    for obj in m.ESTACIONES:
        c = V4 / obj
        if not (c / 'configuracion.json').exists():
            continue
        conf = json.loads((c / 'configuracion.json').read_text())
        if conf.get('incluir_t', False) or conf.get('vecinas') is not None:
            raise RuntimeError(f'{obj}: no es el V4 (incluir_t o vecinas)')
        if em._sha(c / 'modelo.keras') != conf['sha256']['modelo']:
            raise RuntimeError(f'{obj}: modelo.keras no coincide con su SHA-256 guardado')
        modelos[obj] = keras.models.load_model(c / 'modelo.keras', compile=False)
        p95[obj] = float((c / 'umbral_p95_cal2023.txt').read_text())
    return modelos, pd.Series(p95)


def residuos(modelos, valores, definitiva, index, etapa=ETAPA) -> pd.DataFrame:
    """Residuo (recibido − predicho) de cada estación en la etapa (2024; el examen final usa 2025 y
    2026); NaN donde no hay predicción."""
    entradas = m.entradas_modelo(valores, definitiva['inactivos'])
    cols = {}
    for obj, modelo in modelos.items():
        perfil = m.perfil_causal(valores[obj])
        t = em.tensores(entradas, valores, obj, definitiva['mu'], definitiva['sigma'], perfil, (etapa,))
        if not len(t['y']):                      # sin datos en 2024 (ACO): nunca alerta
            cols[obj] = pd.Series(dtype=float)
            continue
        p = em.predecir(modelo, t)
        cols[obj] = pd.Series(p['residuo_ppb'].to_numpy(), index=pd.DatetimeIndex(p['timestamp']))
    return pd.DataFrame(cols).reindex(index)


def puntaje_red(res: pd.DataFrame, p95: pd.Series) -> pd.DataFrame:
    """Máximo de |residuo| / p95 entre estaciones con predicción y la estación que lo da."""
    z = res.abs() / p95[res.columns]
    vacia = z.isna().all(axis=1)
    return pd.DataFrame({'puntaje': z.max(axis=1).where(~vacia, 0.0),
                         'estacion_max': z.fillna(-1.0).idxmax(axis=1).where(~vacia, '')})


def con_examen(valores: pd.DataFrame, matriz: pd.DataFrame) -> pd.DataFrame:
    """Serie del V4 con las horas de la matriz sustituidas (mismos huecos)."""
    est = ev.estaciones_de(matriz)
    bloque = matriz[[f'{s}_valor' for s in est]].set_axis(est, axis=1)
    if not valores.loc[matriz.index, est].notna().equals(bloque.notna()):
        raise RuntimeError('la matriz cambia los huecos de la serie del V4')
    out = valores.copy()
    out.loc[matriz.index, est] = bloque
    return out


def ubicada(alerta: pd.Series, sc: pd.DataFrame, x: pd.DataFrame) -> float:
    """% de horas anómalas con alerta en que la estación del máximo es una de las alteradas."""
    a = alerta.to_numpy(bool) & x['anomalia_red'].to_numpy(bool)
    if not a.any():
        return np.nan
    alteradas = x['estaciones_alteradas'].to_numpy()[a]
    return 100 * np.mean([e in str(s).split(';') for e, s in zip(sc['estacion_max'].to_numpy()[a], alteradas)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--sustituir', action='store_true')
    args = ap.parse_args()
    d = args.delta
    out = SAL / 'v4' / f'd{d}'
    if (out / 'metricas.csv').exists() and not args.sustituir:
        raise SystemExit(f'{out} ya tiene resultados; usar --sustituir para rehacerlos')
    out.mkdir(parents=True, exist_ok=True)

    # 1. Serie del V4 y matriz limpia de 2024.
    ctx = em.contexto(RAIZ)
    valores, dfn = ctx['valores'], ctx['definitiva']
    if list(dfn['inactivos']) != ['XAL']:
        raise RuntimeError(f'canales inactivos inesperados: {dfn["inactivos"]}')
    limpia = ar.leer_matriz(MATRICES / 'matriz_limpia_2024.csv.gz')
    est = ev.estaciones_de(limpia)
    pd.testing.assert_frame_equal(valores.loc[limpia.index, est],
                                  limpia[[f'{s}_valor' for s in est]].set_axis(est, axis=1),
                                  check_names=False, check_freq=False)
    modelos, p95 = cargar_v4()
    print(f'V4 cargado de disco: {len(modelos)} estaciones, sin reentrenar ni recalibrar')

    # 2. Puntaje de red de 2023 limpio con los residuos guardados, y umbrales.
    cal = ar.leer_matriz(MATRICES / 'matriz_limpia_2023.csv.gz')
    res_cal = pd.DataFrame({
        obj: pd.read_csv(V4 / obj / 'calibracion_2023.csv.gz', parse_dates=['timestamp'],
                         index_col='timestamp')['residuo_ppb'] for obj in modelos}).reindex(cal.index)
    sc_cal = puntaje_red(res_cal, p95)
    umbrales = {f'{round(100 * a)}': ev.umbral_falsas_alarmas(sc_cal['puntaje'], a) for a in ev.NIVELES_FA}
    umbrales['p95'] = 1.0
    lograda_2023 = {k: 100 * float((sc_cal['puntaje'] > u).mean()) for k, u in umbrales.items()}

    # 3. 2024 limpio por la misma vía: debe reproducir las predicciones guardadas.
    res_limpia = residuos(modelos, valores, dfn, limpia.index)
    dif_max = 0.0
    for obj in modelos:
        r = res_limpia[obj].dropna()
        guardadas = V4 / obj / 'predicciones_2024.csv.gz'
        if not guardadas.exists():
            if len(r):
                raise RuntimeError(f'{obj}: hay predicciones en 2024 y no estaban guardadas')
            continue
        g = pd.read_csv(guardadas, parse_dates=['timestamp'], index_col='timestamp')
        if not r.index.equals(g.index):
            raise RuntimeError(f'{obj}: horas con predicción distintas a las guardadas')
        dif_max = max(dif_max, float(np.abs(r.to_numpy() - g['residuo_ppb'].to_numpy()).max()))
    if dif_max > TOLERANCIA_PPB:
        raise RuntimeError(f'el 2024 limpio no reproduce las predicciones guardadas (máx. {dif_max} ppb)')
    print(f'2024 limpio reproduce las predicciones guardadas (diferencia máxima {dif_max:.1e} ppb)')
    sc_limpia = puntaje_red(res_limpia, p95)

    # 4. Examen.
    puntajes = {'limpia_2023': sc_cal, 'limpia_2024': sc_limpia}
    metricas, episodios, tamanos = [], [], []
    for _, c in ar.corridas().iloc[1:].iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
        plan = plan[plan.horas_con_dato > 0]                     # episodios evaluables
        x = ar.leer_matriz(MATRICES / f'matriz_{c["corrida"]}_d{d}.csv.gz')
        sc = puntaje_red(residuos(modelos, con_examen(valores, x), dfn, limpia.index), p95)
        puntajes[c['corrida']] = sc
        print(f'  {c["corrida"]}: inferencia repetida')
        cambio = ev.cambio_maximo(x, limpia)
        for k, u in umbrales.items():
            alerta, alerta_limpia = sc['puntaje'] > u, sc_limpia['puntaje'] > u
            e = ev.por_episodio(plan, alerta)
            azar = ev.por_episodio(plan, alerta_limpia)
            e = e.assign(nivel=k, detectado_azar=azar['detectado'].to_numpy(),
                         horas_hasta_alerta_azar=azar['horas_hasta_alerta'].to_numpy())
            episodios.append(e)
            tamanos.append(ev.por_tamano(alerta, cambio, alerta_limpia).assign(corrida=c['corrida'], nivel=k))
            fila = dict(delta_pct=d, corrida=c['corrida'], p=c['p'], nivel=k, umbral=u,
                        falsa_alarma_2023_pct=lograda_2023[k],
                        falsa_alarma_2024_limpio_pct=100 * float(alerta_limpia.mean()),
                        episodios=len(e), detectados=int(e.detectado.sum()),
                        deteccion_episodio_pct=100 * e.detectado.mean(),
                        deteccion_azar_pct=100 * e.detectado_azar.mean(),
                        mediana_horas_hasta_alerta=e.horas_hasta_alerta.median(),
                        mediana_horas_azar=e.horas_hasta_alerta_azar.median(),
                        ubicada_pct=ubicada(alerta, sc, x))
            fila.update(ev.por_hora(alerta, x['anomalia_red']))
            metricas.append(fila)

    # 5. Reproducibilidad: el primer calendario otra vez.
    c0 = ar.corridas().corrida.iloc[1]
    x0 = ar.leer_matriz(MATRICES / f'matriz_{c0}_d{d}.csv.gz')
    otra = puntaje_red(residuos(modelos, con_examen(valores, x0), dfn, limpia.index), p95)
    if not otra.equals(puntajes[c0]):
        raise RuntimeError('dos inferencias del mismo calendario dieron puntajes distintos')

    metricas, episodios = pd.DataFrame(metricas), pd.concat(episodios, ignore_index=True)
    tamanos = pd.concat(tamanos, ignore_index=True)
    metricas.to_csv(out / 'metricas.csv', index=False)
    episodios.to_csv(out / 'episodios.csv', index=False)
    tamanos.to_csv(out / 'por_tamano.csv', index=False)
    pd.concat({k: v for k, v in puntajes.items()}, axis=1).rename_axis('timestamp').to_csv(
        out / 'puntajes.csv.gz', float_format='%.6g')
    (out / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, detector='lstm_v4', delta_pct=d, origen='cargado de disco',
        modelos=str(V4.relative_to(RAIZ)), estaciones=list(modelos),
        fecha=datetime.now().isoformat(timespec='seconds'), etapa=ETAPA,
        puntaje='max |residuo| / p95 por estación; 0 sin predicción', umbrales=umbrales,
        falsa_alarma_2023_pct=lograda_2023,
        control_2024_limpio=f'reproduce predicciones_2024.csv.gz (diferencia máxima {dif_max:.1e} ppb)',
        reproducibilidad=f'dos inferencias de {c0} con puntajes idénticos'), indent=2, ensure_ascii=False))

    # Resumen agregado (todas las corridas juntas).
    print(f'\nV4 δ = {d} % (cargado de disco). Umbrales: {umbrales}')
    for k in umbrales:
        e = episodios[episodios.nivel == k]
        m_ = metricas[metricas.nivel == k]
        h_anom = m_.horas_anomalas.sum()
        det_h = (m_.deteccion_hora_pct * m_.horas_anomalas).sum() / h_anom
        print(f'  Nivel {k}: falsas alarmas 2023 {lograda_2023[k]:.2f} %, 2024 limpio '
              f'{m_.falsa_alarma_2024_limpio_pct.iat[0]:.2f} %, fuera de episodio en el examen '
              f'{(m_.falsa_alarma_hora_pct * m_.horas_normales).sum() / m_.horas_normales.sum():.2f} %')
        print(f'    Por hora: detecta {det_h:.1f} % de {h_anom} horas anómalas; la estación del máximo '
              f'es una alterada en el {np.nansum(m_.ubicada_pct * m_.horas_anomalas * m_.deteccion_hora_pct) / np.nansum(m_.horas_anomalas * m_.deteccion_hora_pct):.1f} % de las detectadas')
        print(f'    Por episodio: {e.detectado.sum()}/{len(e)} = {100 * e.detectado.mean():.1f} % '
              f'(azar {100 * e.detectado_azar.mean():.1f} %); entre corridas '
              f'{m_.deteccion_episodio_pct.min():.0f}–{m_.deteccion_episodio_pct.max():.0f} %')
        print(f'    Mediana de horas hasta la alerta: {e.horas_hasta_alerta.median():.0f} '
              f'(azar {e.horas_hasta_alerta_azar.median():.0f})')
        for signo, g in e.groupby('signo'):
            print(f'    Signo {"+" if signo > 0 else "−"}: {100 * g.detectado.mean():.1f} % '
                  f'(azar {100 * g.detectado_azar.mean():.1f} %)')
        t = tamanos[tamanos.nivel == k].groupby('tramo_ppb', sort=False)[['horas', 'alertan', 'alertan_azar']].sum()
        print('    Por tamaño del cambio (las mismas horas sin alterar): ' + '; '.join(
            f'{n} ppb {100 * r.alertan / r.horas:.1f} % ({100 * r.alertan_azar / r.horas:.1f} %)'
            for n, r in t.iterrows()))


if __name__ == '__main__':
    main()
