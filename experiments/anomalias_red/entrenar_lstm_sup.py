"""LSTM supervisado de red del protocolo anomalias_red_v1, un δ a la vez (revisiones 6, 7 y 8).

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/entrenar_lstm_sup.py --delta 100              # revisión 6
    .venv/bin/python experiments/anomalias_red/entrenar_lstm_sup.py --delta 100 \
        --entradas relativas --calendarios 20 --en-vivo                                      # revisión 7
    .venv/bin/python experiments/anomalias_red/entrenar_lstm_sup.py --delta 100 \
        --entradas vecinas --forma a14 --calendarios 20                                      # revisión 8

1. Ventanas t−23…t de los calendarios de entrenamiento del δ (2020–2022), con la etiqueta de
   red de la hora t. Entradas crudas (revisión 6), relativas al perfil de 14 días (revisión 7) o
   relativas más una columna por estación frente a sus 4 vecinas (revisión 8, con la forma elegida
   con 2022; su referencia fija y su escala se ajustan con 2020–2022 limpio, como la normalización).
2. Selección: entrena con las horas de 2020–2021 y valida con las de 2022 (EarlyStopping,
   paciencia 8, máximo 60 épocas). E = primera época con la menor pérdida de validación.
3. Definitivo: un modelo nuevo con 2020–2022 y exactamente E épocas. Se guarda y se recarga.
4. Umbrales de 5 y 1 % de falsas alarmas por hora de red con 2023 limpio, falsas alarmas en
   2024 limpio y examen con los 10 calendarios de 2024: las mismas métricas que los otros
   detectores.

fijar_semilla(42) inmediatamente antes de construir cada modelo. Salidas en
results/anomalias_red_v1/lstm_sup/d<δ>/ (revisión 6), lstm_sup_<entradas>_<n>cal/d<δ>/ (revisión 7) o
lstm_sup_vecinas_<forma>_<n>cal/d<δ>/ (revisión 8). Si ya
existen, se detiene (usar --sustituir). Con --en-vivo, las curvas se ven en el navegador (ver
en_vivo.py); el monitor no cambia el entrenamiento.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'
GEOGRAFIA = RAIZ / 'results/inventario_multianual/estaciones_geografia.csv'
CONFIG = dict(semilla=42, unidades=64, batch=64, max_epocas=60, paciencia=8, shuffle=True)
SELECCION = ('2020-01-01', '2021-12-31 23:00')
VALIDACION = ('2022-01-01', '2022-12-31 23:00')


def leer(nombre):
    path = MATRICES / f'matriz_{nombre}.csv.gz'
    return ar.leer_matriz(path), hashlib.sha256(path.read_bytes()).hexdigest()


def ejemplos(matriz, tipo, mu, sigma, desde=None, hasta=None, vec=None):
    """Ventanas y etiquetas de las horas t entre `desde` y `hasta` con historia completa en la matriz."""
    t = matriz.index
    dentro = np.ones(len(t), bool)
    if desde is not None:
        dentro &= (t >= pd.Timestamp(desde)) & (t <= pd.Timestamp(hasta))
    pos = np.flatnonzero(dentro)
    pos = pos[pos >= lr.VENTANA - 1]
    X = lr.ventanas(ev.entradas_de(tipo, matriz, mu, sigma, vec), pos)
    return X, matriz['anomalia_red'].to_numpy(np.float32)[pos]


def juntar(matrices, tipo, mu, sigma, desde=None, hasta=None, vec=None):
    partes = [ejemplos(x, tipo, mu, sigma, desde, hasta, vec) for x in matrices]
    return np.concatenate([p[0] for p in partes]), np.concatenate([p[1] for p in partes])


def nuevo_modelo(n_features=66):
    from tensorflow import keras
    keras.backend.clear_session()
    fijar_semilla(CONFIG['semilla'])
    return lr.construir_clasificador(n_features=n_features, unidades=CONFIG['unidades'])


def parametros_vecinas(forma, limpia, sigma, referencia='media'):
    """La columna de vecinas de la revisión 8 (con 'mediana', la de la revisión 10), ajustada con `limpia`."""
    vec = ev.vecinas_de(ev.estaciones_de(limpia), pd.read_csv(GEOGRAFIA, index_col='station'))
    return ev.ajustar_vecinas(forma, limpia, sigma, vec, referencia)


def puntaje(modelo, previa, matriz, tipo, mu, sigma, vec=None) -> pd.Series:
    """Puntaje de cada hora de `matriz`; `previa` es la historia limpia (contexto y perfil)."""
    x = ev.con_historia(previa, matriz)
    X = lr.ventanas(ev.entradas_de(tipo, x, mu, sigma, vec), np.arange(len(previa), len(x)))
    return pd.Series(modelo.predict(X, batch_size=1024, verbose=0).ravel().astype(np.float64), index=matriz.index)


def main():
    import tensorflow as tf
    from tensorflow import keras

    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--entradas', choices=ev.ENTRADAS, default='crudas')
    ap.add_argument('--forma', choices=ev.FORMAS, help='columna de vecinas (revisión 8), con --entradas vecinas')
    ap.add_argument('--referencia', choices=ev.REFERENCIAS, default='media',
                    help='perfil de 14 días: media (revisiones 7 y 8) o mediana (revisión 10, con --entradas vecinas --forma a14)')
    ap.add_argument('--calendarios', type=int, choices=[10, ar.CALENDARIOS_ENTRENAMIENTO], default=10)
    ap.add_argument('--en-vivo', action='store_true', help='curvas en el navegador (en_vivo.py)')
    ap.add_argument('--sustituir', action='store_true')
    args = ap.parse_args()
    d, tipo, n_cal, forma = args.delta, args.entradas, args.calendarios, args.forma
    if (tipo == 'vecinas') != (forma is not None):
        raise SystemExit('--forma va con --entradas vecinas, y sólo con ellas')
    referencia = args.referencia
    if referencia == 'mediana' and (tipo, forma) != ('vecinas', 'a14'):
        raise SystemExit('--referencia mediana sólo está definida con --entradas vecinas --forma a14 (revisión 10)')
    sufijo = '_mediana' if referencia == 'mediana' else ''
    nombre = ('lstm_sup' if (tipo, n_cal) == ('crudas', 10) else f'lstm_sup_vecinas_{forma}{sufijo}_{n_cal}cal'
              if tipo == 'vecinas' else f'lstm_sup_{tipo}_{n_cal}cal')
    revision = 10 if referencia == 'mediana' else {'crudas': 6, 'relativas': 7, 'vecinas': 8}[tipo] if nombre != 'lstm_sup' else 6
    out = SAL / nombre / f'd{d}'
    if (out / 'metricas.csv').exists() and not args.sustituir:
        raise SystemExit(f'{out} ya tiene resultados; usar --sustituir para rehacerlos')
    (out / 'seleccion').mkdir(parents=True, exist_ok=True)

    # Normalización con 2020–2022 limpio; debe coincidir con la del V4.
    limpia_tr, _ = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    vec = parametros_vecinas(forma, limpia_tr, sigma, referencia) if tipo == 'vecinas' else None

    # 1. Los calendarios de entrenamiento del δ.
    calendarios = ar.calendarios_entrenamiento(n=n_cal)
    leidas = [leer(f'{c}_d{d}') for c in calendarios.corrida]
    matrices, sha_tr = [x for x, _ in leidas], {c: s for c, (_, s) in zip(calendarios.corrida, leidas)}

    # 2. Selección de épocas.
    Xtr, ytr = juntar(matrices, tipo, mu, sigma, *SELECCION, vec=vec)
    Xva, yva = juntar(matrices, tipo, mu, sigma, *VALIDACION, vec=vec)
    n_features = Xtr.shape[2]
    print(f'Selección: {len(ytr)} ventanas de 2020–2021 ({100 * ytr.mean():.1f} % con etiqueta 1), '
          f'{len(yva)} de 2022 ({100 * yva.mean():.1f} %)', flush=True)
    vivo = []
    if args.en_vivo:
        from en_vivo import EnVivo
        corrida = f'{nombre} · δ = {d} % · {datetime.now():%Y-%m-%d %H:%M}'
        vivo = [EnVivo(corrida, 'seleccion', val=(Xva, yva))]
    modelo1 = nuevo_modelo(n_features)
    parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                           restore_best_weights=True)
    h = modelo1.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=CONFIG['max_epocas'],
                    batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], callbacks=[parada] + vivo, verbose=2)
    hist1 = pd.DataFrame(h.history)
    hist1.index = pd.RangeIndex(1, len(hist1) + 1, name='epoca')
    E = int(hist1['val_loss'].to_numpy().argmin()) + 1
    hist1.to_csv(out / 'seleccion/historia_seleccion.csv')
    modelo1.save(out / 'seleccion/modelo_seleccion.keras')
    print(f'E = {E} (de {len(hist1)} épocas ejecutadas; val_loss mínimo {hist1.val_loss.min():.5f})', flush=True)
    if vivo:
        vivo[0].nota(f'Época elegida E = {E}, de {len(hist1)} ejecutadas (EarlyStopping sobre la pérdida de '
                     f'validación, paciencia {CONFIG["paciencia"]}).')
    del Xtr, ytr, Xva, yva, modelo1

    # 3. Modelo definitivo con 2020–2022 y exactamente E épocas.
    X, y = juntar(matrices, tipo, mu, sigma, vec=vec)
    print(f'Definitivo: {len(y)} ventanas de 2020–2022 ({100 * y.mean():.1f} % con etiqueta 1), {E} épocas',
          flush=True)
    modelo2 = nuevo_modelo(n_features)
    if vivo:
        vivo = [EnVivo(corrida, 'definitivo')]
    h = modelo2.fit(X, y, epochs=E, batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], callbacks=vivo,
                    verbose=2)
    hist2 = pd.DataFrame(h.history)
    hist2.index = pd.RangeIndex(1, len(hist2) + 1, name='epoca')
    hist2.to_csv(out / 'historia_definitiva.csv')
    modelo2.save(out / 'modelo.keras')
    n_definitivo, positivos = len(y), float(y.mean())
    del X, y, modelo2, matrices
    modelo = keras.models.load_model(out / 'modelo.keras', compile=False)   # puntuar no entrena

    # 4. Umbrales con 2023 limpio (contexto: final de 2022 limpio).
    cal, sha_cal = leer('limpia_2023')
    s_cal = puntaje(modelo, limpia_tr, cal, tipo, mu, sigma, vec)
    umbrales = {f'{round(100 * a)}': ev.umbral_falsas_alarmas(s_cal, a) for a in ev.NIVELES_FA}
    lograda_2023 = {k: 100 * float((s_cal > u).mean()) for k, u in umbrales.items()}

    # Falsas alarmas en 2024 limpio y examen (contexto: final de 2023 limpio).
    limpia, _ = leer('limpia_2024')
    historia = ev.con_historia(limpia_tr, cal)                  # 2020–2023 limpio
    s_limpia = puntaje(modelo, historia, limpia, tipo, mu, sigma, vec)
    puntajes = {'limpia_2023': s_cal, 'limpia_2024': s_limpia}
    metricas, episodios, tamanos = [], [], []
    for _, c in ar.corridas().iloc[1:].iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        plan = plan.assign(horas_con_dato=ev.horas_con_dato(plan, limpia))
        plan = plan[plan.horas_con_dato > 0]                     # episodios evaluables
        x, _ = leer(f'{c["corrida"]}_d{d}')
        s = puntaje(modelo, historia, x, tipo, mu, sigma, vec)
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
        protocolo=ar.PROTOCOLO, revision=revision, detector='lstm_supervisado',
        entradas=tipo, forma_vecinas=forma, referencia_14_dias=referencia, vecinas=vec.vecinas if vec else None, columnas=n_features,
        delta_pct=d, origen='recién entrenado',
        fecha=datetime.now().isoformat(timespec='seconds'), **CONFIG, ventana=lr.VENTANA,
        epoca_E=E, epocas_seleccion_ejecutadas=len(hist1), val_loss_minimo=float(hist1['val_loss'].min()),
        ventanas_definitivo=n_definitivo, etiqueta_1_definitivo_pct=100 * positivos,
        calendarios=calendarios.corrida.tolist(), sha256_matrices_entrenamiento=sha_tr,
        sha256_matriz_calibracion=sha_cal, umbrales=umbrales, falsa_alarma_2023_pct=lograda_2023,
        sha256_modelo=hashlib.sha256((out / 'modelo.keras').read_bytes()).hexdigest(),
        versiones=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                       tensorflow=tf.__version__, keras=keras.__version__)),
        indent=2, ensure_ascii=False))

    # Resumen agregado (todas las corridas juntas).
    print(f'\nLSTM supervisado δ = {d} % (recién entrenado). Umbrales: {umbrales}')
    for k in umbrales:
        e = episodios[episodios.nivel_fa_pct == int(k)]
        m_ = metricas[metricas.nivel_fa_pct == int(k)]
        h_anom = m_.horas_anomalas.sum()
        det_h = (m_.deteccion_hora_pct * m_.horas_anomalas).sum() / h_anom
        print(f'  Nivel {k} %: falsas alarmas 2023 {lograda_2023[k]:.2f} %, 2024 limpio '
              f'{m_.falsa_alarma_2024_limpio_pct.iat[0]:.2f} %, fuera de episodio en el examen '
              f'{(m_.falsa_alarma_hora_pct * m_.horas_normales).sum() / m_.horas_normales.sum():.2f} %')
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
        if vivo:
            vivo[0].nota(f'Examen 2024, nivel {k} %: detecta {det_h:.1f} % de las horas anómalas; falsas alarmas '
                         f'en 2024 limpio {m_.falsa_alarma_2024_limpio_pct.iat[0]:.2f} %.')


if __name__ == '__main__':
    main()
