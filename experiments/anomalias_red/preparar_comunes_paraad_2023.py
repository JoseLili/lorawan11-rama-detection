"""Exporta la máscara común de revisiones 18/19, sin cargar datos de examen.

V4 y ambos V4S tienen exactamente el mismo criterio de hora válida, definido
por multianual.ejemplos_validos y entrenamiento_multianual.tensores. Se coteja
su soporte con los residuos V4 guardados. L0 y R3 se puntúan sobre 2023 limpio.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'

import hashlib
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
from tensorflow import keras
from src.detect import multianual as m, estacion_dia as ed, evaluacion_red as ev, lstm_local as ll
from entrenar_lstm_sup import leer, parametros_vecinas
from generar_planes import alterables_v4
from puntos_operacion_2024 import LSTM, PUNTOS

SAL = RAIZ / 'results/anomalias_red_v1'
OUT = SAL / 'revision20/comunes_2023'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    tr, ht = leer('limpia_2020_2022')
    cal, hc = leer('limpia_2023')
    assert tr.index.min().year == 2020 and tr.index.max().year == 2022
    assert (cal.index.year == 2023).all() and not cal.anomalia_red.astype(bool).any()
    objetivos = alterables_v4()
    mu, sigma = ev.normalizacion(tr)
    par = parametros_vecinas('a14', tr, sigma, 'media')
    vec = parametros_vecinas('a14', tr, sigma, 'mediana')
    x = ev.con_historia(tr, cal)
    F = ev.entradas_de('vecinas', x, None, sigma, par)
    estaciones = ev.estaciones_de(tr)
    ruta = LSTM / 'd50/modelo.keras'
    congelados = json.loads((SAL/'examen_final_modelos_congelados.json').read_text())
    assert sha(ruta) == congelados['L0']['L0_d50']
    modelo = keras.models.load_model(ruta, compile=False)
    pos = np.arange(len(tr), len(x))
    cols = {}
    for s in objetivos:
        X = ll.ventanas_locales(F, estaciones, par.vecinas, s, pos)
        prob = np.concatenate([modelo(X[i:i+512], training=False).numpy().ravel()
                               for i in range(0, len(X), 512)]).astype('float64')
        assert np.isfinite(prob).all()
        cols[s] = pd.Series(prob, index=cal.index).where(cal[f'{s}_mascara'] == 1)
    l0 = ed.juntar_dia(pd.DataFrame(cols), 'promedio_dia')
    col = ev.columnas_vecinas(x, sigma, vec).iloc[len(tr):]
    r3 = ed.dominancia(ed.juntar_dia(col[objetivos], 'promedio_dia'), vec.vecinas)
    valores = x[[f'{s}_valor' for s in estaciones]].set_axis(estaciones, axis=1).reindex(columns=m.ESTACIONES)
    res, p95, fuentes = {}, {}, {}
    for s in objetivos:
        carpeta = RAIZ / 'results/lstm_v4_multianual_v1/estaciones' / s
        path = carpeta / 'calibracion_2023.csv.gz'
        serie = pd.read_csv(path, parse_dates=['timestamp'], index_col='timestamp')['residuo_ppb'].reindex(cal.index)
        esperado = m.ejemplos_validos(valores, s, m.perfil_causal(valores[s])).loc[cal.index]
        np.testing.assert_array_equal(serie.notna(), esperado)
        res[s] = serie
        p95[s] = float((carpeta/'umbral_p95_cal2023.txt').read_text())
        fuentes[s] = sha(path)
    v4 = ed.juntar_dia(pd.DataFrame(res) / pd.Series(p95), 'promedio_dia')
    # El soporte de V4S (por estación y compartido) usa el mismo ejemplos_validos;
    # la normalización y el orden de vecinos no añaden exclusiones de horas.
    comunes = l0.notna() & r3.notna() & v4.notna()
    assert list(comunes.columns) == objetivos
    # Validación del universo contra los umbrales históricos: sólo lee metadatos
    # de calibración de la tabla, nunca puntajes/etiquetas de los años de examen.
    referencia = pd.read_csv(SAL/'revision18/resultados.csv', usecols=['dias','detector','punto','umbral'])
    referencia = referencia[referencia.dias=='comunes'].groupby(['detector','punto']).umbral.first()
    controles = []
    for nombre, tabla in [('L0_unico', l0), ('R3',r3), ('V4',v4)]:
        tabla.rename_axis('dia').to_csv(OUT/f'puntajes_{nombre}.csv')
        vals = tabla.to_numpy()[comunes.to_numpy()]
        for punto, fa in PUNTOS.items():
            u = ev.umbral_falsas_alarmas(vals, fa)
            previo = float(referencia[nombre,punto])
            np.testing.assert_allclose(u, previo, rtol=1e-6, atol=1e-9)
            controles.append(dict(detector=nombre,punto=punto,umbral=u,umbral_historico=previo))
    comunes.astype(int).rename_axis('dia').to_csv(OUT/'mascara.csv')
    pd.DataFrame(controles).to_csv(OUT/'control_umbrales.csv', index=False)
    pd.DataFrame({'comunes':comunes.sum(),'validas_L0':l0.notna().sum(),
                  'validas_R3':r3.notna().sum(),'validas_V4_y_V4S':v4.notna().sum()}).to_csv(OUT/'cobertura.csv',index_label='estacion')
    (OUT/'registro.json').write_text(json.dumps(dict(
        origen='comparadores congelados; sin entrenar', estacion_dias=int(comunes.to_numpy().sum()),
        sha256_mascara=sha(OUT/'mascara.csv'),sha256_l0=sha(ruta),
        sha256_matriz_ajuste=ht,sha256_matriz_calibracion=hc,sha256_residuos_v4=fuentes,
        criterio_v4s='mismo soporte horario de V4 por ejemplos_validos; cotejado con residuos guardados',
        control_umbrales='L0, R3 y V4 coinciden con calibración común revisión18',
        sha256_script=sha(__file__)),indent=2)+'\n')
    print('Estación-días comunes:',int(comunes.to_numpy().sum()),flush=True)


if __name__ == '__main__':
    main()
