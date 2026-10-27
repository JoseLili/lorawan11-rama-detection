"""V4 supervisado (V4S), protocolo `anomalias_red_v1`, revisión 18: un modelo por estación, sólo δ = 50 %.

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/entrenar_v4_supervisado.py [--estaciones PED,TLA] [--solo-seleccion]
                                                                         [--salida DIR] [--prueba]

Cada ejemplo es una estación s y una hora t con dato y base: las 66 entradas del V4 con filas t−23…t
y las 2 columnas de s (`v4_supervisado.tensores`), y la etiqueta de s en t
(`estacion_dia.etiquetas_por_hora`), que nunca es entrada. Arquitectura del V4 con salida sigmoide
(`lstm_red.construir_clasificador`); `fijar_semilla(42)` inmediatamente antes de construir cada modelo.
Por estación, en el orden de `alterables_v4`:

1. Selección: normalización y canales inactivos del ajuste inicial del V4 (2020–2021). Entrena con
   2020–2021 de los 20 calendarios de L0, 1 de cada 8 horas por calendario y estación
   (`v4_supervisado.muestra`), con EarlyStopping sobre la pérdida en 1 de cada 8 horas de 2022 de los
   calendarios 01–10 (paciencia 8, máximo 60 épocas, pesos de la mejor). E = primera época con el
   menor val_loss.
2. Definitivo (salvo --solo-seleccion): normalización definitiva del V4 (2020–2022), 2020–2022 de los
   20 calendarios con la misma fracción de horas y exactamente E épocas.

Salidas en results/anomalias_red_v1/v4_supervisado/d50/<estación>/ (o --salida). Una estación ya
terminada se conserva y se salta (el entrenamiento es determinista). Con --prueba: 2 calendarios
(01 y 20), 50 veces menos ventanas, 1 época y 2 estaciones; sólo comprueba que corre.

Con --compartido (revisión 18b): un solo modelo para las 31 estaciones, con las otras 32 estaciones
ordenadas por distancia al objetivo (`v4_supervisado.orden_por_distancia`) y exactamente las mismas
ventanas que el V4S por estación (la misma muestra y la misma semilla), juntadas. Mismos pasos 1 y 2.
Salidas en results/anomalias_red_v1/v4_supervisado_compartido/d50/ (o --salida).
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import multianual as m  # noqa: E402
from src.detect import v4_supervisado as vs  # noqa: E402
from src.detect.vecinas import distancias  # noqa: E402
from entrenar_lstm_estacion import nuevo_modelo  # noqa: E402
from entrenar_lstm_sup import CONFIG, GEOGRAFIA, leer  # noqa: E402
from evaluar_v4 import con_examen  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1/v4_supervisado'
SAL_COMPARTIDO = RAIZ / 'results/anomalias_red_v1/v4_supervisado_compartido'
DELTA = 50
CALENDARIOS = 20
N_VALIDACION = 10
FIN_AJUSTE = '2022-12-31 23:00'
PRUEBA = 50                      # con --prueba, 50 veces menos ventanas


def ejemplos(entradas, V, perfiles, Y, s, j, mu, sigma, etapas, uso, numeros, cada):
    """Ventanas y etiquetas de s en `etapas`: 1 de cada `cada` por calendario."""
    X, y = [], []
    for k, numero in enumerate(numeros):
        t = vs.tensores(entradas[k], V[k], s, mu, sigma, perfiles[k], etapas)
        sel = vs.muestra(len(t['ts']), uso, numero, j, cada)
        X.append(t['X'][sel])
        y.append(Y[k][s].to_numpy(np.float32)[t['pos'][sel]])
    return np.concatenate(X), np.concatenate(y)


def compartido(keras, objetivos, V, Y, entradas, fases, numeros, calendarios, cada, n_va, max_epocas, out, prueba):
    """Revisión 18b: un solo V4S para las 31 estaciones, con las ventanas del V4S por estación juntadas."""
    if (out / 'modelo.keras').exists():
        print('V4S compartido: ya existía, se conserva', flush=True)
        return
    (out / 'seleccion').mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    dist = distancias(pd.read_csv(GEOGRAFIA, index_col='station'))
    ordenes = {s: vs.orden_por_distancia(s, dist) for s in objetivos}
    conjuntos = {'entrenamiento': (('ajuste_inicial',), 'seleccion', len(V)),
                 'validacion': (('validacion',), 'validacion', n_va),
                 'definitivo': (m.AJUSTE_DEFINITIVO, 'definitivo', len(V))}
    n = dict.fromkeys(conjuntos, 0)                   # pasada 1: cuántas ventanas, sin construirlas
    for s in objetivos:
        for k, v in enumerate(V):
            perfil = m.perfil_causal(v[s])
            for nombre, (etapas, _, n_cal) in conjuntos.items():
                if k < n_cal:
                    n[nombre] += vs.cuantos(v, s, perfil, etapas, cada)
    print(f'V4S compartido: ventanas {n}, {(time.time() - t0) / 60:.1f} min', flush=True)

    def llenar(fase, nombres):
        """Pasada 2: las ventanas de `nombres`, en arreglos del tamaño exacto."""
        f = fases[fase]
        arr = {c: (np.empty((n[c], m.VENTANA, vs.N_COLUMNAS), np.float32), np.empty(n[c], np.float32)) for c in nombres}
        i = dict.fromkeys(nombres, 0)
        for j, s in enumerate(objetivos):
            for k, (v, numero) in enumerate(zip(V, numeros)):
                perfil = m.perfil_causal(v[s])
                for c in nombres:
                    etapas, uso, n_cal = conjuntos[c]
                    if k >= n_cal:
                        continue
                    t = vs.tensores(entradas[fase][k], v, s, f['mu'], f['sigma'], perfil, etapas, orden=ordenes[s])
                    sel = vs.muestra(len(t['ts']), uso, numero, j, cada)
                    X, y = arr[c]
                    X[i[c]:i[c] + len(sel)] = t['X'][sel]
                    y[i[c]:i[c] + len(sel)] = Y[k][s].to_numpy(np.float32)[t['pos'][sel]]
                    i[c] += len(sel)
        if i != {c: n[c] for c in nombres}:
            raise RuntimeError(f'ventanas llenadas {i} distintas de las contadas')
        return arr

    # 1. Selección: normalización del ajuste inicial; EarlyStopping con 2022.
    arr = llenar('seleccion', ['entrenamiento', 'validacion'])
    (Xtr, ytr), (Xva, yva) = arr['entrenamiento'], arr['validacion']
    del arr
    print(f'V4S compartido: {len(ytr)} ventanas de 2020–2021 ({100 * ytr.mean():.2f} % atacadas) y {len(yva)} de '
          f'2022, {(time.time() - t0) / 60:.1f} min', flush=True)
    modelo = nuevo_modelo(Xtr.shape[2], 1)
    parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                           restore_best_weights=True)
    hist = historia(modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=max_epocas, batch_size=CONFIG['batch'],
                               shuffle=CONFIG['shuffle'], callbacks=[parada], verbose=2))
    E = int(hist['val_loss'].to_numpy().argmin()) + 1
    hist.to_csv(out / 'seleccion/historia_seleccion.csv')
    modelo.save(out / 'seleccion/modelo_seleccion.keras')
    config = dict(protocolo=ar.PROTOCOLO, revision='18b', detector='v4_supervisado_compartido', delta_pct=DELTA,
                  calendarios=calendarios, origen='recién entrenado', estaciones=objetivos,
                  entradas=f'las 66 del V4 con filas t−23…t, las otras estaciones ordenadas por distancia, y 2 de la '
                           f'propia estación ({vs.N_COLUMNAS} columnas)', ordenes=ordenes,
                  arquitectura=dict(unidades=CONFIG['unidades'], dropout=0.2, densa=32, salidas=1),
                  entrenamiento={k: CONFIG[k] for k in ('semilla', 'batch', 'max_epocas', 'paciencia', 'shuffle')},
                  una_de_cada=cada,
                  seleccion=dict(E=E, epocas_ejecutadas=len(hist), val_loss_min=float(hist.val_loss.min()),
                                 ventanas_entrenamiento=len(ytr), ventanas_validacion=len(yva),
                                 positivas_pct=100 * float(ytr.mean())),
                  fecha=datetime.now().isoformat(timespec='seconds'),
                  maquina=platform.processor() or platform.machine(), prueba=prueba)
    (out / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f'V4S compartido: selección E = {E} de {len(hist)} épocas, {(time.time() - t0) / 60:.1f} min', flush=True)
    del Xtr, ytr, Xva, yva, modelo

    # 2. Definitivo: normalización definitiva; 2020–2022 de los 20 calendarios; exactamente E épocas.
    X, y = llenar('definitivo', ['definitivo'])['definitivo']
    modelo = nuevo_modelo(X.shape[2], 1)
    hist2 = historia(modelo.fit(X, y, epochs=E, batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], verbose=2))
    hist2.to_csv(out / 'historia_definitiva.csv')
    modelo.save(out / 'modelo.keras')
    config['definitivo'] = dict(ventanas=len(y), positivas_pct=100 * float(y.mean()), epocas=E)
    config['sha256'] = dict(modelo=em._sha(out / 'modelo.keras'))
    (out / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f'V4S compartido: definitivo listo, {(time.time() - t0) / 60:.1f} min en total', flush=True)


def historia(h) -> pd.DataFrame:
    hist = pd.DataFrame(h.history)
    hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
    return hist


def main():
    from tensorflow import keras

    ap = argparse.ArgumentParser()
    ap.add_argument('--estaciones', default=None, help='lista separada por comas; por omisión, las 31')
    ap.add_argument('--solo-seleccion', action='store_true')
    ap.add_argument('--compartido', action='store_true', help='revisión 18b: un solo modelo para las 31')
    ap.add_argument('--salida', type=Path, default=None)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    prueba = args.prueba
    objetivos = alterables_v4()
    estaciones = args.estaciones.split(',') if args.estaciones else (objetivos[:2] if prueba else objetivos)
    if args.compartido and (args.estaciones or args.solo_seleccion):
        raise SystemExit('--compartido entrena las 31 estaciones juntas, con selección y definitivo')
    if not set(estaciones) <= set(objetivos):
        raise SystemExit(f'estaciones fuera de los 31 objetivos: {sorted(set(estaciones) - set(objetivos))}')
    todos = ar.calendarios_entrenamiento(n=CALENDARIOS)
    if prueba:
        todos = todos.iloc[[0, -1]]
    cada = vs.CADA * (PRUEBA if prueba else 1)
    n_va, max_epocas = (1, 1) if prueba else (N_VALIDACION, CONFIG['max_epocas'])
    out = (args.salida or (SAL_COMPARTIDO if args.compartido else SAL)) / f'd{DELTA}'
    out.mkdir(parents=True, exist_ok=True)

    ctx = em.contexto(RAIZ)
    valores = ctx['valores'].loc[:FIN_AJUSTE]
    fases = {'seleccion': ctx['inicial'], 'definitivo': ctx['definitiva']}
    calendarios, numeros = todos.corrida.tolist(), todos.numero.tolist()
    V, Y = [], []
    for c in calendarios:
        x, _ = leer(f'{c}_d{DELTA}')
        if not x.index.equals(valores.index):
            raise RuntimeError(f'{c}: la matriz no cubre exactamente 2020–2022')
        V.append(con_examen(valores, x))
        Y.append(ed.etiquetas_por_hora(x, objetivos))
    entradas = {f: [m.entradas_modelo(v, fases[f]['inactivos']) for v in V] for f in fases}
    print(f'V4S, δ = {DELTA} %: {len(calendarios)} calendarios, {len(estaciones)} estaciones, 1 de cada {cada} horas',
          flush=True)
    if args.compartido:
        compartido(keras, objetivos, V, Y, entradas, fases, numeros, calendarios, cada, n_va, max_epocas, out, prueba)
        return

    for s in estaciones:
        j = objetivos.index(s)
        dest = out / s
        listo = dest / ('seleccion/historia_seleccion.csv' if args.solo_seleccion else 'modelo.keras')
        if listo.exists():
            print(f'{s}: ya existía, se conserva', flush=True)
            continue
        (dest / 'seleccion').mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        perfiles = [m.perfil_causal(v[s]) for v in V]

        # 1. Selección: normalización del ajuste inicial; EarlyStopping con 2022.
        f = fases['seleccion']
        Xtr, ytr = ejemplos(entradas['seleccion'], V, perfiles, Y, s, j, f['mu'], f['sigma'], ('ajuste_inicial',),
                            'seleccion', numeros, cada)
        Xva, yva = ejemplos(entradas['seleccion'][:n_va], V[:n_va], perfiles[:n_va], Y[:n_va], s, j, f['mu'],
                            f['sigma'], ('validacion',), 'validacion', numeros[:n_va], cada)
        modelo = nuevo_modelo(Xtr.shape[2], 1)
        parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=CONFIG['paciencia'], min_delta=0,
                                               restore_best_weights=True)
        hist = historia(modelo.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=max_epocas,
                                   batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], callbacks=[parada],
                                   verbose=0))
        E = int(hist['val_loss'].to_numpy().argmin()) + 1
        hist.to_csv(dest / 'seleccion/historia_seleccion.csv')
        modelo.save(dest / 'seleccion/modelo_seleccion.keras')
        config = dict(protocolo=ar.PROTOCOLO, revision=vs.REVISION, detector='v4_supervisado', estacion=s,
                      delta_pct=DELTA, calendarios=calendarios, origen='recién entrenado',
                      entradas=f'las 66 del V4 con filas t−23…t y 2 de la propia estación ({vs.N_COLUMNAS} columnas)',
                      arquitectura=dict(unidades=CONFIG['unidades'], dropout=0.2, densa=32, salidas=1),
                      entrenamiento={k: CONFIG[k] for k in ('semilla', 'batch', 'max_epocas', 'paciencia', 'shuffle')},
                      una_de_cada=cada,
                      seleccion=dict(E=E, epocas_ejecutadas=len(hist), val_loss_min=float(hist.val_loss.min()),
                                     ventanas_entrenamiento=len(ytr), ventanas_validacion=len(yva),
                                     positivas_pct=100 * float(ytr.mean())),
                      fecha=datetime.now().isoformat(timespec='seconds'),
                      maquina=platform.processor() or platform.machine(), prueba=prueba)
        (dest / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
        print(f'{s}: selección E = {E} de {len(hist)} épocas, {len(ytr)} ventanas '
              f'({100 * ytr.mean():.2f} % atacadas), {(time.time() - t0) / 60:.1f} min', flush=True)
        del Xtr, ytr, Xva, yva, modelo
        if args.solo_seleccion:
            continue

        # 2. Definitivo: normalización definitiva; 2020–2022 de los 20 calendarios; exactamente E épocas.
        f = fases['definitivo']
        X, y = ejemplos(entradas['definitivo'], V, perfiles, Y, s, j, f['mu'], f['sigma'], m.AJUSTE_DEFINITIVO,
                        'definitivo', numeros, cada)
        modelo = nuevo_modelo(X.shape[2], 1)
        hist2 = historia(modelo.fit(X, y, epochs=E, batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], verbose=0))
        hist2.to_csv(dest / 'historia_definitiva.csv')
        modelo.save(dest / 'modelo.keras')
        config['definitivo'] = dict(ventanas=len(y), positivas_pct=100 * float(y.mean()), epocas=E)
        config['sha256'] = dict(modelo=em._sha(dest / 'modelo.keras'))
        (dest / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
        print(f'{s}: definitivo listo, {(time.time() - t0) / 60:.1f} min en total', flush=True)
        del X, y, modelo

    filas = []
    for s in objetivos:
        p = out / s / 'configuracion.json'
        if p.exists():
            c = json.loads(p.read_text())
            filas.append(dict(estacion=s, E=c['seleccion']['E'], epocas_ejecutadas=c['seleccion']['epocas_ejecutadas'],
                              val_loss_min=c['seleccion']['val_loss_min'], definitivo='definitivo' in c))
    pd.DataFrame(filas).to_csv(out / 'epocas.csv', index=False)


if __name__ == '__main__':
    main()
