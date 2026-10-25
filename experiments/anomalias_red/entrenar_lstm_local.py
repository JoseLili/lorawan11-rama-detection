"""LSTM local compartido por estación (protocolo, revisión 14): un modelo por δ para las 31 estaciones.

Uso (desde la raíz del repo, después de generar_matrices.py y generar_matrices.py --ampliados):

    .venv/bin/python experiments/anomalias_red/entrenar_lstm_local.py --delta 100 --calendarios 20
    .venv/bin/python experiments/anomalias_red/entrenar_lstm_local.py --delta 100 --calendarios 20 --definitivo

Cada ejemplo es una estación s y una hora t: la ventana t−23…t con las 17 columnas de
`lstm_local.indices_locales` (s y sus 4 vecinas, sacadas de las 98 de la revisión 8 con la forma a14
y la media de 14 días) y la etiqueta de s en t (`estacion_dia.etiquetas_por_hora`), que nunca es
entrada. El mismo modelo (LSTM de 64, una salida) se aplica a las 31 estaciones.
`fijar_semilla(42)` inmediatamente antes de construir cada modelo.

1. Selección (siempre): entrena con 2020–2021 de los 20 o 60 calendarios, 1 de cada 8 o 24 horas
   por calendario y estación (`lstm_local.muestra`), con EarlyStopping sobre la pérdida de
   validación en 1 de cada 8 horas de 2022 de los calendarios 01–10 (paciencia 8, máximo 60 épocas,
   pesos de la mejor época). La escala de la columna de vecinas se ajusta con 2020–2021 limpio.
   Guarda en seleccion/ el modelo, su historia, E y los puntajes por estación-día de 2022 (todas
   las horas de los calendarios 01–10 y de 2022 limpio) con las dos formas de juntar el día.
2. Con --definitivo: el modelo con 2020–2022 (la misma fracción de horas) y exactamente E épocas
   (escala con 2020–2022 limpio), y los puntajes por estación-día de 2023 limpio, 2024 limpio y los
   10 calendarios de 2024.

Salidas en results/anomalias_red_v1/lstm_local/c<calendarios>/d<δ>/ (o --salida). Con --prueba: 2
calendarios (con 60, el 01 y el 60), 50 veces menos ventanas y 1 época; sólo comprueba que corre.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402
from src.detect import lstm_red as lr  # noqa: E402
from diagnostico_variantes_2022 import posiciones  # noqa: E402
from entrenar_lstm_estacion import V4_NORM, guardar_dias, nuevo_modelo  # noqa: E402
from entrenar_lstm_sup import CONFIG, SELECCION, VALIDACION, leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1/lstm_local'
REFERENCIA = 'media'
N_VALIDACION = 10
PRUEBA = 50                      # con --prueba, 50 veces menos ventanas


def por_dia(modelo, F, x, pos, estaciones, vecinas, objetivos) -> dict[str, pd.DataFrame]:
    """Probabilidad por estación en las horas `pos` de `x` (NaN sin dato) y el día juntado de las dos formas."""
    X = np.concatenate([ll.ventanas_locales(F, estaciones, vecinas, s, pos) for s in objetivos])
    p = modelo.predict(X, batch_size=4096, verbose=0).astype(np.float64).reshape(len(objetivos), len(pos)).T
    idx = x.index[pos]
    con_dato = x.loc[idx, [f'{s}_mascara' for s in objetivos]].to_numpy() == 1
    prob = pd.DataFrame(p, index=idx, columns=objetivos).where(con_dato)
    return {a: ed.juntar_dia(prob, a) for a in ed.AGREGACIONES}


def ejemplos(F, Y, pos, cada, uso, numero, estaciones, vecinas, objetivos):
    """Ventanas y etiquetas de un calendario: 1 de cada `cada` horas de `pos` por estación."""
    X, y = [], []
    for j, s in enumerate(objetivos):
        p = ll.muestra(pos, cada, uso, numero, j)
        X.append(ll.ventanas_locales(F, estaciones, vecinas, s, p))
        y.append(Y[s].to_numpy(np.float32)[p])
    return np.concatenate(X), np.concatenate(y)


def main():
    from tensorflow import keras

    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--calendarios', type=int, required=True, choices=sorted(ll.CADA))
    ap.add_argument('--definitivo', action='store_true')
    ap.add_argument('--salida', type=Path, default=SAL)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    d, n_cal, prueba = args.delta, args.calendarios, args.prueba
    todos = ar.calendarios_entrenamiento(n=n_cal)
    if prueba:
        todos = todos.iloc[[0, -1]]
    cada, cada_va = ll.CADA[n_cal], ll.CADA_VALIDACION
    if prueba:
        cada, cada_va = cada * PRUEBA, cada_va * PRUEBA
    n_va, max_epocas = (1, 1) if prueba else (N_VALIDACION, CONFIG['max_epocas'])
    out = args.salida / f'c{n_cal}' / f'd{d}'
    (out / 'seleccion').mkdir(parents=True, exist_ok=True)

    limpia_tr, sha_tr = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    objetivos = alterables_v4()
    estaciones = ev.estaciones_de(limpia_tr)
    calendarios, numeros = todos.corrida.tolist(), todos.numero.tolist()
    idx = limpia_tr.index

    def calendario(c):
        x = leer(f'{c}_d{d}')[0]
        assert x.index.equals(idx)
        return x, ed.etiquetas_por_hora(x, objetivos)

    # 1. Selección: escala con 2020–2021 limpio; EarlyStopping con 2022.
    par = parametros_vecinas('a14', limpia_tr.loc[SELECCION[0]:SELECCION[1]], sigma, REFERENCIA)
    vecinas = par.vecinas
    p_tr, p_va = posiciones(idx, *SELECCION), posiciones(idx, *VALIDACION)
    tr, va, puntuar = [], [], {}
    for k, (c, numero) in enumerate(zip(calendarios, numeros)):
        x, Y = calendario(c)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        tr.append(ejemplos(F, Y, p_tr, cada, 'seleccion', numero, estaciones, vecinas, objetivos))
        if k < n_va:
            va.append(ejemplos(F, Y, p_va, cada_va, 'validacion', numero, estaciones, vecinas, objetivos))
            puntuar[c] = (F, x)
    Xtr, ytr = np.concatenate([a for a, _ in tr]), np.concatenate([b for _, b in tr])
    Xva, yva = np.concatenate([a for a, _ in va]), np.concatenate([b for _, b in va])
    del tr, va
    print(f'δ = {d} %, {n_cal} calendarios: {len(ytr)} ventanas de 2020–2021 (1 de cada {cada} horas; '
          f'{100 * ytr.mean():.2f} % con etiqueta 1) y {len(yva)} de 2022; {Xtr.shape[2]} columnas', flush=True)
    modelo = nuevo_modelo(Xtr.shape[2], 1)
    parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                           restore_best_weights=True)
    h = modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=max_epocas, batch_size=CONFIG['batch'],
                   shuffle=CONFIG['shuffle'], callbacks=[parada], verbose=2)
    hist = pd.DataFrame(h.history)
    hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
    E = int(hist['val_loss'].to_numpy().argmin()) + 1
    hist.to_csv(out / 'seleccion/historia_seleccion.csv')
    modelo.save(out / 'seleccion/modelo_seleccion.keras')
    print(f'E = {E} (de {len(hist)} épocas; val_loss mínimo {hist.val_loss.min():.6f})', flush=True)
    n_sel = dict(ventanas_entrenamiento=len(ytr), ventanas_validacion=len(yva), positivas_pct=100 * float(ytr.mean()))
    del Xtr, ytr, Xva, yva

    dias = {c: por_dia(modelo, F, x, p_va, estaciones, vecinas, objetivos) for c, (F, x) in puntuar.items()}
    dias['limpia_2022'] = por_dia(modelo, ev.entradas_de('vecinas', limpia_tr, None, sigma, par), limpia_tr, p_va,
                                  estaciones, vecinas, objetivos)
    guardar_dias(out / 'seleccion/dias_2022.csv.gz', dias)
    del puntuar
    config = dict(protocolo=ar.PROTOCOLO, revision=14, detector='lstm_local', delta_pct=d, calendarios_n=n_cal,
                  referencia_14_dias=REFERENCIA, origen='recién entrenado',
                  entradas=f'locales ({ll.N_COLUMNAS} columnas: la estación y sus 4 vecinas)', objetivos=objetivos,
                  arquitectura=dict(unidades=CONFIG['unidades'], dropout=0.2, densa=32, salidas=1),
                  entrenamiento={k: CONFIG[k] for k in ('semilla', 'batch', 'max_epocas', 'paciencia', 'shuffle')},
                  una_de_cada=dict(entrenamiento=cada, validacion=cada_va), calendarios=calendarios,
                  seleccion=dict(E=E, epocas_ejecutadas=len(hist), val_loss_min=float(hist.val_loss.min()), **n_sel),
                  sha256_matriz_limpia=sha_tr, fecha=datetime.now().isoformat(timespec='seconds'),
                  maquina=platform.processor() or platform.machine(), prueba=prueba)
    (out / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    del modelo
    if not args.definitivo:
        return

    # 2. Definitivo: escala con 2020–2022 limpio, 2020–2022 de los calendarios, exactamente E épocas.
    par = parametros_vecinas('a14', limpia_tr, sigma, REFERENCIA)
    todas = np.arange(lr.VENTANA - 1, len(idx))
    partes = []
    for c, numero in zip(calendarios, numeros):
        x, Y = calendario(c)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        partes.append(ejemplos(F, Y, todas, cada, 'definitivo', numero, estaciones, vecinas, objetivos))
    X, y = np.concatenate([a for a, _ in partes]), np.concatenate([b for _, b in partes])
    del partes
    modelo = nuevo_modelo(X.shape[2], 1)
    h = modelo.fit(X, y, epochs=E, batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], verbose=2)
    hist2 = pd.DataFrame(h.history)
    hist2.index = pd.RangeIndex(1, len(hist2) + 1, name='epoca')
    hist2.to_csv(out / 'historia_definitiva.csv')
    modelo.save(out / 'modelo.keras')
    config['definitivo'] = dict(ventanas=len(y), positivas_pct=100 * float(y.mean()), epocas=E)
    del X, y, modelo
    modelo = keras.models.load_model(out / 'modelo.keras', compile=False)   # puntuar no entrena

    def con_historia(previa, matriz):
        x = ev.con_historia(previa, matriz)
        return por_dia(modelo, ev.entradas_de('vecinas', x, None, sigma, par), x, np.arange(len(previa), len(x)),
                       estaciones, vecinas, objetivos)

    cal, _ = leer('limpia_2023')
    historia = ev.con_historia(limpia_tr, cal)                   # 2020–2023 limpio
    dias = {'limpia_2023': con_historia(limpia_tr, cal), 'limpia_2024': con_historia(historia, leer('limpia_2024')[0])}
    for c in ar.corridas().corrida.iloc[1:1 + (1 if prueba else ar.CORRIDAS_PRUEBA)]:
        dias[c] = con_historia(historia, leer(f'{c}_d{d}')[0])
        print(f'  {c}: listo', flush=True)
    guardar_dias(out / 'dias_examen.csv.gz', dias)
    (out / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
