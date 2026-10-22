"""IsolationForest de red del protocolo anomalias_red_v1, un δ a la vez (§8, §9 y revisión 3).

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/entrenar_if.py --delta 100

1. Entrena con matriz_limpia_2020_2022: no ve anomalías, así que es el mismo modelo para todos
   los δ. Hiperparámetros por omisión, random_state=42. Lo hace dos veces y exige puntajes
   idénticos; si ya hay un modelo guardado, exige además que dé los mismos puntajes.
2. Puntaje = −score_samples (mayor, más anómalo). Umbrales de 5 y 1 % de falsas alarmas por
   hora de red con matriz_limpia_2023.
3. Mide las falsas alarmas en matriz_limpia_2024.
4. Examen con los 10 calendarios del δ: detección por hora, por episodio (con su nivel de azar)
   y por tamaño del cambio.

El modelo va en results/anomalias_red_v1/if/modelo.joblib y las salidas del δ en
results/anomalias_red_v1/if/d<δ>/. Si ya existen, se detiene (usar --sustituir).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from sklearn.ensemble import IsolationForest  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES, CARPETA = SAL / 'matrices', SAL / 'planes', SAL / 'if'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'


def leer(nombre):
    path = MATRICES / f'matriz_{nombre}.csv.gz'
    return ar.leer_matriz(path), hashlib.sha256(path.read_bytes()).hexdigest()


def entrenar(X):
    fijar_semilla(42)
    return IsolationForest(random_state=42, n_jobs=-1).fit(X)   # n_jobs no cambia el resultado


def puntaje(modelo, matriz, mu, sigma) -> pd.Series:
    return pd.Series(-modelo.score_samples(ev.entradas(matriz, mu, sigma)), index=matriz.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--sustituir', action='store_true')
    args = ap.parse_args()
    d = args.delta
    out = CARPETA / f'd{d}'
    if (out / 'metricas.csv').exists() and not args.sustituir:
        raise SystemExit(f'{out} ya tiene resultados; usar --sustituir para rehacerlos')
    out.mkdir(parents=True, exist_ok=True)

    # Normalización con 2020–2022 limpio; debe coincidir con la del V4.
    limpia_tr, sha_tr = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)

    # 1. Entrenamiento con 2020–2022 limpio, dos veces, y contra el modelo guardado.
    X = ev.entradas(limpia_tr, mu, sigma)
    print(f'Entrenando IsolationForest: {len(X)} horas limpias de 2020–2022')
    modelo = entrenar(X)
    cal, sha_cal = leer('limpia_2023')
    s_cal = puntaje(modelo, cal, mu, sigma)
    if not np.array_equal(s_cal.to_numpy(), puntaje(entrenar(X), cal, mu, sigma).to_numpy()):
        raise RuntimeError('dos entrenamientos con la misma semilla dieron puntajes distintos')
    guardado = CARPETA / 'modelo.joblib'
    if guardado.exists():
        if not np.array_equal(s_cal.to_numpy(), puntaje(joblib.load(guardado), cal, mu, sigma).to_numpy()):
            raise RuntimeError(f'{guardado} da puntajes distintos a los de este entrenamiento')
    else:
        joblib.dump(modelo, guardado, compress=3)

    # 2. Umbrales con 2023 limpio.
    umbrales = {f'{round(100 * a)}': ev.umbral_falsas_alarmas(s_cal, a) for a in ev.NIVELES_FA}
    lograda_2023 = {k: 100 * float((s_cal > u).mean()) for k, u in umbrales.items()}

    # 3. Falsas alarmas en 2024 limpio y 4. examen.
    limpia, _ = leer('limpia_2024')
    s_limpia = puntaje(modelo, limpia, mu, sigma)
    puntajes = {'limpia_2023': s_cal, 'limpia_2024': s_limpia}
    metricas, episodios, tamanos = [], [], []
    for _, c in ar.corridas().iloc[1:].iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
        plan = plan[plan.horas_con_dato > 0]                     # episodios evaluables
        x, _ = leer(f'{c["corrida"]}_d{d}')
        s = puntaje(modelo, x, mu, sigma)
        puntajes[c['corrida']] = s
        cambio = ev.cambio_maximo(x, limpia)
        for k, u in umbrales.items():
            alerta, alerta_limpia = s > u, s_limpia > u
            e = ev.por_episodio(plan, alerta)
            azar = ev.por_episodio(plan, alerta_limpia)
            e = e.assign(nivel_fa_pct=int(k), detectado_azar=azar['detectado'].to_numpy(),
                         horas_hasta_alerta_azar=azar['horas_hasta_alerta'].to_numpy())
            episodios.append(e)
            tamanos.append(ev.por_tamano(alerta, cambio, alerta_limpia).assign(
                corrida=c['corrida'], nivel_fa_pct=int(k)))
            fila = dict(delta_pct=d, corrida=c['corrida'], p=c['p'], nivel_fa_pct=int(k), umbral=u,
                        falsa_alarma_2023_pct=lograda_2023[k],
                        falsa_alarma_2024_limpio_pct=100 * float(alerta_limpia.mean()),
                        episodios=len(e), detectados=int(e.detectado.sum()),
                        deteccion_episodio_pct=100 * e.detectado.mean(),
                        deteccion_azar_pct=100 * e.detectado_azar.mean(),
                        mediana_horas_hasta_alerta=e.horas_hasta_alerta.median(),
                        mediana_horas_azar=e.horas_hasta_alerta_azar.median())
            fila.update(ev.por_hora(alerta, x['anomalia_red']))
            metricas.append(fila)
    metricas, episodios = pd.DataFrame(metricas), pd.concat(episodios, ignore_index=True)
    tamanos = pd.concat(tamanos, ignore_index=True)
    metricas.to_csv(out / 'metricas.csv', index=False)
    episodios.to_csv(out / 'episodios.csv', index=False)
    tamanos.to_csv(out / 'por_tamano.csv', index=False)
    pd.DataFrame(puntajes).rename_axis('timestamp').to_csv(out / 'puntajes.csv.gz', float_format='%.6g')
    (out / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, detector='isolation_forest', delta_pct=d, origen='recién entrenado',
        fecha=datetime.now().isoformat(timespec='seconds'), sklearn=sklearn.__version__,
        hiperparametros={k: v for k, v in modelo.get_params().items() if k != 'n_jobs'},
        puntaje='-score_samples', sha256_matriz_entrenamiento=sha_tr, sha256_matriz_calibracion=sha_cal,
        horas_entrenamiento=int(len(X)), umbrales=umbrales, falsa_alarma_2023_pct=lograda_2023,
        reproducibilidad='dos entrenamientos con puntajes idénticos en 2023, iguales a los del modelo guardado'),
        indent=2, ensure_ascii=False))

    # Resumen agregado (todas las corridas juntas).
    print(f'\nIsolationForest δ = {d} % (recién entrenado). Umbrales: {umbrales}')
    for k in umbrales:
        e = episodios[episodios.nivel_fa_pct == int(k)]
        m_ = metricas[metricas.nivel_fa_pct == int(k)]
        h_anom = m_.horas_anomalas.sum()
        det_h = (m_.deteccion_hora_pct * m_.horas_anomalas).sum() / h_anom
        print(f'  Nivel {k} %: falsas alarmas 2023 {lograda_2023[k]:.2f} %, 2024 limpio '
              f'{m_.falsa_alarma_2024_limpio_pct.iat[0]:.2f} %')
        print(f'    Por hora: detecta {det_h:.1f} % de {h_anom} horas anómalas')
        print(f'    Por episodio: {e.detectado.sum()}/{len(e)} = {100 * e.detectado.mean():.1f} % '
              f'(azar {100 * e.detectado_azar.mean():.1f} %); entre corridas '
              f'{m_.deteccion_episodio_pct.min():.0f}–{m_.deteccion_episodio_pct.max():.0f} %')
        print(f'    Mediana de horas hasta la alerta: {e.horas_hasta_alerta.median():.0f} '
              f'(azar {e.horas_hasta_alerta_azar.median():.0f})')
        for signo, g in e.groupby('signo'):
            print(f'    Signo {"+" if signo > 0 else "−"}: {100 * g.detectado.mean():.1f} % '
                  f'(azar {100 * g.detectado_azar.mean():.1f} %)')
        t = tamanos[tamanos.nivel_fa_pct == int(k)].groupby('tramo_ppb', sort=False)[
            ['horas', 'alertan', 'alertan_azar']].sum()
        print('    Por tamaño del cambio (las mismas horas sin alterar): ' + '; '.join(
            f'{n} ppb {100 * r.alertan / r.horas:.1f} % ({100 * r.alertan_azar / r.horas:.1f} %)'
            for n, r in t.iterrows()))


if __name__ == '__main__':
    main()
