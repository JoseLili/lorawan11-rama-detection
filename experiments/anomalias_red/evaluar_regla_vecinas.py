"""Regla de vecinas de la revisión 8: el control sin entrenamiento del LSTM supervisado con vecinas.

Uso (desde la raíz del repo, después de generar_matrices.py y de elegir la forma con 2022):

    .venv/bin/python experiments/anomalias_red/evaluar_regla_vecinas.py --delta 100 --forma a14

1. La columna de vecinas de cada estación (`evaluacion_red.columnas_vecinas`), con la forma dada.
   Su referencia fija y su escala se ajustan con 2020–2022 limpio, como en el LSTM. No aprende de
   las anomalías, así que es el mismo puntaje para todos los δ; sólo cambia el examen.
2. Puntaje de red de cada hora = el mayor |columna| entre las estaciones (sin dato → 0). La historia
   limpia anterior da el contexto de 14 días. Lo calcula dos veces y exige puntajes idénticos.
3. Umbrales de 5 y 1 % de falsas alarmas por hora de red con 2023 limpio, falsas alarmas en 2024
   limpio y examen con los 10 calendarios del δ: las mismas métricas que los otros detectores.

Salidas en results/anomalias_red_v1/regla_vecinas_<forma>/d<δ>/ (con --referencia mediana, de la
revisión 10: regla_vecinas_<forma>_mediana/). Si ya existen, se detiene (usar --sustituir).
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
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from entrenar_lstm_sup import parametros_vecinas  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'


def leer(nombre):
    path = MATRICES / f'matriz_{nombre}.csv.gz'
    return ar.leer_matriz(path), hashlib.sha256(path.read_bytes()).hexdigest()


def puntaje(previa, matriz, sigma, vec) -> pd.Series:
    """El mayor |columna de vecinas| de cada hora de `matriz`; `previa` es la historia limpia."""
    x = ev.con_historia(previa, matriz)
    c = ev.columnas_vecinas(x, sigma, vec).iloc[len(previa):]
    return c.abs().fillna(0.0).max(axis=1).astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--forma', choices=ev.FORMAS, required=True)
    ap.add_argument('--referencia', choices=ev.REFERENCIAS, default='media',
                    help='perfil de 14 días: media (revisión 8) o mediana (revisión 10, sólo con a14)')
    ap.add_argument('--sustituir', action='store_true')
    args = ap.parse_args()
    d, forma, referencia = args.delta, args.forma, args.referencia
    out = SAL / f"regla_vecinas_{forma}{'_mediana' if referencia == 'mediana' else ''}" / f'd{d}'
    if (out / 'metricas.csv').exists() and not args.sustituir:
        raise SystemExit(f'{out} ya tiene resultados; usar --sustituir para rehacerlos')
    out.mkdir(parents=True, exist_ok=True)

    # Normalización con 2020–2022 limpio; debe coincidir con la del V4.
    limpia_tr, sha_tr = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    vec = parametros_vecinas(forma, limpia_tr, sigma, referencia)

    # 1–2. Puntajes de 2023 limpio, dos veces, y umbrales.
    cal, sha_cal = leer('limpia_2023')
    s_cal = puntaje(limpia_tr, cal, sigma, vec)
    otra_vez = puntaje(limpia_tr, cal, sigma, parametros_vecinas(forma, limpia_tr, sigma, referencia))
    if not np.array_equal(s_cal.to_numpy(), otra_vez.to_numpy()):
        raise RuntimeError('dos cálculos de la regla dieron puntajes distintos')
    umbrales = {f'{round(100 * a)}': ev.umbral_falsas_alarmas(s_cal, a) for a in ev.NIVELES_FA}
    lograda_2023 = {k: 100 * float((s_cal > u).mean()) for k, u in umbrales.items()}

    # 3. Falsas alarmas en 2024 limpio y examen (contexto: 2020–2023 limpio).
    limpia, _ = leer('limpia_2024')
    historia = ev.con_historia(limpia_tr, cal)
    s_limpia = puntaje(historia, limpia, sigma, vec)
    puntajes = {'limpia_2023': s_cal, 'limpia_2024': s_limpia}
    metricas, episodios, tamanos = [], [], []
    for _, c in ar.corridas().iloc[1:].iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
        plan = plan[plan.horas_con_dato > 0]                     # episodios evaluables
        x, _ = leer(f'{c["corrida"]}_d{d}')
        s = puntaje(historia, x, sigma, vec)
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
        protocolo=ar.PROTOCOLO, revision=10 if referencia == 'mediana' else 8, detector='regla_vecinas',
        forma_vecinas=forma, referencia_14_dias=referencia, delta_pct=d,
        origen='sin entrenamiento (referencia y escala con 2020–2022 limpio)',
        fecha=datetime.now().isoformat(timespec='seconds'), vecinas=vec.vecinas,
        escala=vec.escala.round(6).to_dict(), puntaje='máximo |columna de vecinas| entre estaciones',
        sha256_matriz_ajuste=sha_tr, sha256_matriz_calibracion=sha_cal, umbrales=umbrales,
        falsa_alarma_2023_pct=lograda_2023,
        reproducibilidad='dos cálculos con puntajes idénticos en 2023'), indent=2, ensure_ascii=False))

    # Resumen agregado (todas las corridas juntas).
    print(f'\nRegla de vecinas ({forma}, {referencia}) δ = {d} % (sin entrenamiento). Umbrales: {umbrales}')
    for k in umbrales:
        e = episodios[episodios.nivel_fa_pct == int(k)]
        m_ = metricas[metricas.nivel_fa_pct == int(k)]
        h_anom = m_.horas_anomalas.sum()
        det_h = (m_.deteccion_hora_pct * m_.horas_anomalas).sum() / h_anom
        print(f'  Nivel {k} %: falsas alarmas 2023 {lograda_2023[k]:.2f} %, 2024 limpio '
              f'{m_.falsa_alarma_2024_limpio_pct.iat[0]:.2f} %')
        print(f'    Por hora: detecta {det_h:.1f} % de {h_anom} horas anómalas')
        print(f'    Por episodio: {e.detectado.sum()}/{len(e)} = {100 * e.detectado.mean():.1f} % '
              f'(azar {100 * e.detectado_azar.mean():.1f} %)')
        t = tamanos[tamanos.nivel_fa_pct == int(k)].groupby('tramo_ppb', sort=False)[
            ['horas', 'alertan', 'alertan_azar']].sum()
        print('    Por tamaño del cambio (las mismas horas sin alterar): ' + '; '.join(
            f'{n} ppb {100 * r.alertan / r.horas:.1f} % ({100 * r.alertan_azar / r.horas:.1f} %)'
            for n, r in t.iterrows() if r.horas))


if __name__ == '__main__':
    main()
