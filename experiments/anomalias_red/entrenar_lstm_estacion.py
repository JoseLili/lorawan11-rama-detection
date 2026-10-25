"""LSTM supervisado por estación (protocolo, revisión 13): una salida por objetivo, un modelo por δ.

Uso (desde la raíz del repo, después de generar_matrices.py):

    .venv/bin/python experiments/anomalias_red/entrenar_lstm_estacion.py --delta 100 --referencia media
    .venv/bin/python experiments/anomalias_red/entrenar_lstm_estacion.py --delta 100 --referencia media --definitivo

El LSTM de la revisión 8 (ventana t−23…t con las 98 columnas de `evaluacion_red.entradas_de('vecinas')`,
forma a14, con la media o la mediana de 14 días) con 31 salidas sigmoides y la etiqueta por
estación-hora (`estacion_dia.etiquetas_por_hora`), que nunca es entrada. `fijar_semilla(42)`
inmediatamente antes de construir cada modelo.

1. Selección (siempre): entrena con 2020–2021 de los 20 calendarios, con EarlyStopping sobre la
   pérdida de validación en 2022 de los calendarios 01–10 (paciencia 8, máximo 60 épocas, pesos de
   la mejor época). La escala de la columna de vecinas se ajusta con 2020–2021 limpio, como en las
   elecciones de las revisiones 8, 10 y 12. Guarda en seleccion/ el modelo, su historia, E y los
   puntajes por estación-día de 2022 (calendarios 01–10 y 2022 limpio) con las dos formas de juntar
   el día; la dominancia se aplica después.
2. Con --definitivo, como la revisión 8: el modelo con 2020–2022 y exactamente E épocas (escala con
   2020–2022 limpio), y los puntajes por estación-día de 2023 limpio, 2024 limpio y los 10
   calendarios de 2024. Las probabilidades por hora no se guardan: se regeneran con modelo.keras.

Las horas válidas son las que tienen dato de la estación. Salidas en
results/anomalias_red_v1/lstm_estacion/<referencia>/d<δ>/ (o --salida). Con --prueba: 2 calendarios,
1 de cada 50 ventanas de entrenamiento y 1 época; sólo comprueba que corre.
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
from src.detect import lstm_red as lr  # noqa: E402
from src.detect.lstm import fijar_semilla  # noqa: E402
from diagnostico_variantes_2022 import posiciones  # noqa: E402
from entrenar_lstm_sup import CONFIG, SELECCION, VALIDACION, leer, parametros_vecinas  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1/lstm_estacion'
V4_NORM = RAIZ / 'results/lstm_v4_multianual_v1/normalizacion.csv'
N_VALIDACION = 10


def nuevo_modelo(n_features: int, salidas: int):
    from tensorflow import keras
    keras.backend.clear_session()
    fijar_semilla(CONFIG['semilla'])
    return lr.construir_clasificador(n_features=n_features, unidades=CONFIG['unidades'], salidas=salidas)


def por_dia(modelo, F: np.ndarray, x: pd.DataFrame, pos: np.ndarray, objetivos) -> dict[str, pd.DataFrame]:
    """Probabilidad por estación en las horas `pos` de `x` (NaN sin dato) y el día juntado de las dos formas."""
    p = modelo.predict(lr.ventanas(F, pos), batch_size=4096, verbose=0).astype(np.float64)
    idx = x.index[pos]
    con_dato = x.loc[idx, [f'{s}_mascara' for s in objetivos]].to_numpy() == 1
    prob = pd.DataFrame(p, index=idx, columns=objetivos).where(con_dato)
    return {a: ed.juntar_dia(prob, a) for a in ed.AGREGACIONES}


def guardar_dias(path: Path, dias: dict[str, dict[str, pd.DataFrame]]) -> None:
    filas = [s.rename_axis('dia').reset_index().assign(conjunto=c, agregacion=a)
             for c, por in dias.items() for a, s in por.items()]
    t = pd.concat(filas, ignore_index=True)
    t[['conjunto', 'agregacion', 'dia'] + [c for c in t.columns if c not in ('conjunto', 'agregacion', 'dia')]].to_csv(
        path, index=False)


def leer_dias(path: Path) -> dict[str, dict[str, pd.DataFrame]]:
    """Inverso de `guardar_dias`: {conjunto: {agregación: día × estación}}."""
    t = pd.read_csv(path, parse_dates=['dia'])
    return {c: {a: s.drop(columns=['conjunto', 'agregacion']).set_index('dia').rename_axis(None)
                for a, s in g.groupby('agregacion', sort=False)} for c, g in t.groupby('conjunto', sort=False)}


def juntar(F, Y, pos, k):
    return np.concatenate([lr.ventanas(F[i], pos) for i in range(k)]), np.concatenate([Y[i][pos] for i in range(k)])


def main():
    from tensorflow import keras

    ap = argparse.ArgumentParser()
    ap.add_argument('--delta', type=int, required=True, choices=[round(100 * d) for d in ar.DELTAS])
    ap.add_argument('--referencia', choices=ev.REFERENCIAS, required=True)
    ap.add_argument('--definitivo', action='store_true')
    ap.add_argument('--salida', type=Path, default=SAL)
    ap.add_argument('--prueba', action='store_true')
    args = ap.parse_args()
    d, ref, prueba = args.delta, args.referencia, args.prueba
    n_tr, n_va, paso, max_epocas = (2, 1, 50, 1) if prueba else (ar.CALENDARIOS_ENTRENAMIENTO, N_VALIDACION, 1,
                                                                  CONFIG['max_epocas'])
    out = args.salida / ref / f'd{d}'
    (out / 'seleccion').mkdir(parents=True, exist_ok=True)

    limpia_tr, sha_tr = leer('limpia_2020_2022')
    mu, sigma = ev.normalizacion(limpia_tr)
    v4 = pd.read_csv(V4_NORM, index_col='estacion')
    np.testing.assert_allclose(mu, v4.loc[mu.index, 'media_definitiva'], rtol=1e-9)
    np.testing.assert_allclose(sigma, v4.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    objetivos = alterables_v4()
    calendarios = ar.calendarios_entrenamiento(n=n_tr).corrida.tolist()
    mats = [leer(f'{c}_d{d}')[0] for c in calendarios]
    idx = mats[0].index
    assert all(x.index.equals(idx) for x in mats) and limpia_tr.index.equals(idx)
    Y = [ed.etiquetas_por_hora(x, objetivos).to_numpy(np.float32) for x in mats]

    # 1. Selección: escala con 2020–2021 limpio; EarlyStopping con 2022.
    par = parametros_vecinas('a14', limpia_tr.loc[SELECCION[0]:SELECCION[1]], sigma, ref)
    F = [ev.entradas_de('vecinas', x, None, sigma, par) for x in mats]
    p_tr, p_va = posiciones(idx, *SELECCION), posiciones(idx, *VALIDACION)
    Xtr, ytr = juntar(F, Y, p_tr[::paso], n_tr)
    Xva, yva = juntar(F, Y, p_va[::paso], n_va)
    print(f'δ = {d} %, {ref}: {len(ytr)} ventanas de 2020–2021 ({100 * ytr.mean():.2f} % de estación-horas con '
          f'etiqueta 1) y {len(yva)} de 2022; {Xtr.shape[2]} columnas, {len(objetivos)} salidas', flush=True)
    modelo = nuevo_modelo(Xtr.shape[2], len(objetivos))
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

    dias = {calendarios[k]: por_dia(modelo, F[k], mats[k], p_va, objetivos) for k in range(n_va)}
    dias['limpia_2022'] = por_dia(modelo, ev.entradas_de('vecinas', limpia_tr, None, sigma, par), limpia_tr, p_va,
                                  objetivos)
    guardar_dias(out / 'seleccion/dias_2022.csv.gz', dias)
    config = dict(protocolo=ar.PROTOCOLO, revision=13, detector='lstm_estacion', delta_pct=d, referencia_14_dias=ref,
                  origen='recién entrenado', entradas='vecinas a14 (98 columnas)', salidas=objetivos,
                  arquitectura=dict(unidades=CONFIG['unidades'], dropout=0.2, densa=32, salidas=len(objetivos)),
                  entrenamiento={k: CONFIG[k] for k in ('semilla', 'batch', 'max_epocas', 'paciencia', 'shuffle')},
                  calendarios=calendarios, seleccion=dict(E=E, epocas_ejecutadas=len(hist),
                                                          val_loss_min=float(hist.val_loss.min()), **n_sel),
                  sha256_matriz_limpia=sha_tr, fecha=datetime.now().isoformat(timespec='seconds'),
                  maquina=platform.processor() or platform.machine(), prueba=prueba)
    (out / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False))
    del modelo
    if not args.definitivo:
        return

    # 2. Definitivo: escala con 2020–2022 limpio, 2020–2022 de los 20 calendarios, exactamente E épocas.
    par = parametros_vecinas('a14', limpia_tr, sigma, ref)
    F = [ev.entradas_de('vecinas', x, None, sigma, par) for x in mats]
    X, y = juntar(F, Y, np.arange(lr.VENTANA - 1, len(idx))[::paso], n_tr)
    del F, mats
    modelo = nuevo_modelo(X.shape[2], len(objetivos))
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
                       objetivos)

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
