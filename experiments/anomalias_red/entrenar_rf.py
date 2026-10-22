"""Random Forest de red del protocolo anomalias_red_v1, un δ a la vez (§8 y §9).

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/entrenar_rf.py --delta 100
    .venv/bin/python experiments/anomalias_red/entrenar_rf.py --delta 100 --calendarios 10
    .venv/bin/python experiments/anomalias_red/entrenar_rf.py --delta 100 --calendarios 20 --entradas relativas

1. Entrena con matriz_entrenamiento_d<δ> (2020–2022) o, con --calendarios 10, con los 10
   calendarios de la revisión 6 juntos (control del LSTM supervisado); con --calendarios 20
   --entradas relativas, el control de la revisión 7. Hiperparámetros por omisión,
   random_state=42. Lo hace dos veces y exige puntajes idénticos.
2. Fija los umbrales de 5 y 1 % de falsas alarmas por hora de red con matriz_limpia_2023.
3. Mide las falsas alarmas en matriz_limpia_2024.
4. Examen con los 10 calendarios del mismo δ: detección por hora, por episodio y por tamaño
   del cambio, cada una junto a su nivel de azar (las alertas de 2024 limpio).

Salidas en results/anomalias_red_v1/rf/d<δ>/ (rf_10cal/ con --calendarios 10 y
rf_<entradas>_<n>cal/ con otras opciones). Si ya existen, se detiene (usar --sustituir).
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
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'


def leer(nombre):
    path = MATRICES / f'matriz_{nombre}.csv.gz'
    return ar.leer_matriz(path), hashlib.sha256(path.read_bytes()).hexdigest()


def entrenar(X, y):
    fijar_semilla(42)
    rf = RandomForestClassifier(random_state=42, n_jobs=-1)    # n_jobs no cambia los árboles
    # Se predice en serie: en paralelo, el orden en que se suman los votos de los árboles cambia
    # el último decimal (1e-16) cuando hay hojas con votos fraccionarios (2026-10-16).
    return rf.fit(X, y).set_params(n_jobs=1)


def puntaje(rf, previa, matriz, tipo, mu, sigma) -> pd.Series:
    """Puntaje de cada hora de `matriz`; `previa` es la historia limpia (para el perfil)."""
    F = ev.entradas_de(tipo, ev.con_historia(previa, matriz), mu, sigma)[len(previa):]
    return pd.Series(rf.predict_proba(F)[:, 1], index=matriz.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--calendarios', type=int, choices=[1, 10, ar.CALENDARIOS_ENTRENAMIENTO], default=1)
    ap.add_argument('--entradas', choices=ev.ENTRADAS, default='crudas')
    ap.add_argument('--sustituir', action='store_true')
    args = ap.parse_args()
    d, tipo = args.delta, args.entradas
    nombre = {(1, 'crudas'): 'rf', (10, 'crudas'): 'rf_10cal'}.get((args.calendarios, tipo),
                                                                   f'rf_{tipo}_{args.calendarios}cal')
    out = SAL / nombre / f'd{d}'
    if (out / 'metricas.csv').exists() and not args.sustituir:
        raise SystemExit(f'{out} ya tiene resultados; usar --sustituir para rehacerlos')
    out.mkdir(parents=True, exist_ok=True)

    # Normalización con 2020–2022 limpio; debe coincidir con la del V4.
    limpia_tr, _ = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)

    # 1. Entrenamiento, dos veces.
    nombres = ([f'entrenamiento_d{d}'] if args.calendarios == 1
               else [f'{c}_d{d}' for c in ar.calendarios_entrenamiento(n=args.calendarios).corrida])
    leidas = [leer(n) for n in nombres]
    X = np.concatenate([ev.entradas_de(tipo, x, mu, sigma) for x, _ in leidas])
    y = np.concatenate([x['anomalia_red'].to_numpy() for x, _ in leidas])
    sha_tr = leidas[0][1] if args.calendarios == 1 else {n: s for n, (_, s) in zip(nombres, leidas)}
    del leidas
    print(f'Entrenando RF δ = {d} %: {len(y)} horas, {y.sum()} con etiqueta 1 ({100 * y.mean():.1f} %)')
    rf = entrenar(X, y)
    cal, sha_cal = leer('limpia_2023')
    s_cal = puntaje(rf, limpia_tr, cal, tipo, mu, sigma)
    rf2 = entrenar(X, y)
    if not np.array_equal(s_cal.to_numpy(), puntaje(rf2, limpia_tr, cal, tipo, mu, sigma).to_numpy()):
        raise RuntimeError('dos entrenamientos con la misma semilla dieron puntajes distintos')
    del rf2
    joblib.dump(rf, out / 'modelo.joblib', compress=3)

    # 2. Umbrales con 2023 limpio.
    umbrales = {f'{round(100 * a)}': ev.umbral_falsas_alarmas(s_cal, a) for a in ev.NIVELES_FA}
    lograda_2023 = {k: 100 * float((s_cal > u).mean()) for k, u in umbrales.items()}

    # 3. Falsas alarmas en 2024 limpio y 4. examen.
    limpia, _ = leer('limpia_2024')
    historia = ev.con_historia(limpia_tr, cal)                  # 2020–2023 limpio
    s_limpia = puntaje(rf, historia, limpia, tipo, mu, sigma)
    puntajes = {'limpia_2023': s_cal, 'limpia_2024': s_limpia}
    metricas, episodios, tamanos = [], [], []
    for _, c in ar.corridas().iloc[1:].iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
        plan = plan[plan.horas_con_dato > 0]                     # episodios evaluables
        x, _ = leer(f'{c["corrida"]}_d{d}')
        s = puntaje(rf, historia, x, tipo, mu, sigma)
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
        protocolo=ar.PROTOCOLO, detector='random_forest', delta_pct=d, origen='recién entrenado',
        calendarios_entrenamiento=args.calendarios, entradas=tipo,
        fecha=datetime.now().isoformat(timespec='seconds'), sklearn=sklearn.__version__,
        hiperparametros={k: v for k, v in rf.get_params().items() if k != 'n_jobs'},
        sha256_matriz_entrenamiento=sha_tr, sha256_matriz_calibracion=sha_cal,
        horas_entrenamiento=int(len(y)), horas_etiqueta_1=int(y.sum()),
        umbrales=umbrales, falsa_alarma_2023_pct=lograda_2023,
        reproducibilidad='dos entrenamientos con puntajes idénticos en 2023'), indent=2, ensure_ascii=False))

    # Resumen agregado (todas las corridas juntas).
    print(f'\nRF δ = {d} % (recién entrenado). Umbrales: {umbrales}')
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
