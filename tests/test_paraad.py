"""Contratos científicos de PARAAD: ejes, faltantes, atención y universo común."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import numpy as np
import pandas as pd
import pytest

tf = pytest.importorskip('tensorflow')
from src.detect import paraad as p


def muestra():
    idx = pd.date_range('2020-01-01', periods=48, freq='h')
    x = pd.DataFrame(np.arange(48 * 32).reshape(48, 32), index=idx, columns=p.SENSORES, dtype=float)
    escala = pd.DataFrame({'media': np.zeros(32), 'desv': np.ones(32)}, index=p.SENSORES)
    return x, escala


def test_ejes_y_faltantes():
    x, escala = muestra()
    x.iloc[3, 5] = np.nan
    z, m, dias = p.bloques(x, escala)
    assert z.shape == (2, 32, 24)
    assert z[1, 2, 7] == x.iloc[31, 2]
    assert z[0, 5, 3] == 0 and not m[0, 5, 3]
    assert list(dias) == [x.index[0], x.index[24]]
    with pytest.raises(ValueError):
        p.bloques(x.iloc[1:], escala)
    with pytest.raises(ValueError):
        p.bloques(x, escala.iloc[::-1])


def test_perdida_ignora_relleno_y_normaliza_por_bloque():
    z = np.zeros((2, 32, 24), dtype='float32')
    m = np.zeros_like(z, dtype=bool)
    m[0, 0, :2] = True
    m[1, 0, :1] = True
    pred = np.full_like(z, 100)
    pred[0, 0, :2] = [1, 3]
    pred[1, 0, 0] = 2
    np.testing.assert_array_equal(p.mse_observada(p.objetivos_perdida(z, m), pred).numpy(), [5, 4])


def test_mae_no_cancela_signos_y_minimo12():
    z = np.zeros((1, 32, 24), dtype='float32')
    m = np.ones_like(z, dtype=bool)
    pred = np.ones_like(z)
    pred[:, :, :12] = -1
    m[0, 0, 11:] = False
    m[0, 1, 12:] = False
    s = p.puntajes(z, m, pred, pd.DatetimeIndex(['2022-01-01']))
    assert np.isnan(s.iloc[0, 0]) and s.iloc[0, 1] == 1
    assert s.iloc[0, 2] == 1 and 'HGM' not in s.columns
    comunes = s.notna()
    p.exigir_comunes(s, comunes)
    comunes.iloc[0, 0] = True
    with pytest.raises(ValueError):
        p.exigir_comunes(s, comunes)


@pytest.mark.parametrize('ancho', [4, 24])
def test_atencion_contra_formula_numpy(ancho):
    rng = np.random.default_rng(2)
    x = rng.normal(size=(2, 32, 4)).astype('float32')
    capa = p.AtencionSA(ancho)
    capa(x)
    pesos = [rng.normal(scale=.2, size=w.shape).astype('float32') for w in capa.get_weights()]
    capa.set_weights(pesos)
    wt, wx, bh, wa, ba = pesos
    h = np.tanh((x @ wt)[:, :, None, :] + (x @ wx)[:, None, :, :] + bh)
    e = 1 / (1 + np.exp(-(h @ wa + ba)[..., 0]))
    for i in range(32):
        for j in range(32):
            if not i - ancho // 2 <= j < i - ancho // 2 + ancho:
                e[:, i, j] -= 10000
    a = np.exp(e - e.max(axis=-1, keepdims=True))
    a /= a.sum(axis=-1, keepdims=True)
    np.testing.assert_allclose(capa(x).numpy(), a @ x, rtol=2e-5, atol=1e-6)


def test_lector_excluye_calibracion_y_examen(tmp_path):
    from experiments.anomalias_red.entrenar_paraad import leer_ajuste
    x, _ = muestra()
    otro = x.iloc[:1].copy()
    otro.index = pd.DatetimeIndex(['2024-01-01'], name='timestamp')
    otro[:] = 999999
    x.index.name = 'timestamp'
    path = tmp_path / 'datos.parquet'
    pd.concat([x, otro]).to_parquet(path)
    tr = leer_ajuste(path)
    assert tr.index.max() == pd.Timestamp('2022-12-31 23:00')
    assert not (tr.to_numpy() == 999999).any()


def test_calibracion_cli_sintetica(tmp_path):
    import json
    import subprocess
    import sys
    from experiments.anomalias_red.entrenar_paraad import RAIZ, sha
    from src.detect.lstm import fijar_semilla
    tf.keras.backend.clear_session()
    fijar_semilla(42)
    modelo = p.construir_modelo()
    carpeta = tmp_path / 'modelo'
    carpeta.mkdir()
    modelo.save(carpeta / 'modelo_r1.keras')
    x, escala = muestra()
    x.index = pd.date_range('2023-01-01', periods=48, freq='h', name='timestamp')
    escala.to_csv(carpeta / 'escala.csv', index_label='estacion')
    conf = dict(igual=True, sha256_modelo=sha(carpeta / 'modelo_r1.keras'),
                sha256_escala=sha(carpeta / 'escala.csv'), tensorflow=tf.__version__, keras=tf.keras.__version__,
                fuentes={'src/detect/paraad.py': sha(RAIZ / 'src/detect/paraad.py')})
    (carpeta / 'congelado.json').write_text(json.dumps(conf))
    matriz = x.rename(columns={s: f'{s}_valor' for s in p.SENSORES})
    for s in p.SENSORES:
        matriz[f'{s}_mascara'] = 1
    matriz['anomalia_red'] = False
    matriz.to_csv(tmp_path / 'matriz.csv')
    comunes = pd.DataFrame(1, index=x.index[::24], columns=p.OBJETIVOS).rename_axis('dia')
    comunes.to_csv(tmp_path / 'comunes.csv')
    cmd = [sys.executable, str(RAIZ / 'experiments/anomalias_red/puntuar_paraad.py'),
           '--modelo', str(carpeta), '--matriz', str(tmp_path / 'matriz.csv'),
           '--comunes', str(tmp_path / 'comunes.csv'), '--salida', str(tmp_path / 'cal')]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    registro = json.loads((tmp_path / 'cal/registro.json').read_text())
    assert registro['calibracion'] and registro['igual'] and registro['estacion_dias'] == 62
    assert registro['umbrales']['p99.9'] >= registro['umbrales']['p99']
    matriz['anomalia_red'] = True
    matriz.to_csv(tmp_path / 'matriz.csv')
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    assert resultado.returncode != 0 and 'limpia comprobable' in resultado.stderr


def test_recuperacion_completa_y_repeticion_interrumpida(tmp_path):
    from experiments.anomalias_red.entrenar_paraad import repeticion, iguales
    rng = np.random.default_rng(42)
    z = rng.normal(size=(2, 32, 24)).astype('float32')
    m = np.ones_like(z, dtype=bool)
    a, ha, ra = repeticion(tmp_path / 'corrida', .1, z, m, 1)
    b, hb, rb = repeticion(tmp_path / 'corrida', .1, z, m, 1)
    iguales(a, b)
    pd.testing.assert_frame_equal(ha, hb, check_exact=True)
    np.testing.assert_array_equal(ra, rb)
    # Simular escritura interrumpida antes del marcador de finalización.
    (tmp_path / 'corrida/completo.json').unlink()
    c, hc, rc = repeticion(tmp_path / 'corrida', .1, z, m, 1)
    iguales(a, c)
    pd.testing.assert_frame_equal(ha, hc, check_exact=True)
    np.testing.assert_array_equal(ra, rc)
    (tmp_path / 'corrida/historia.csv').write_text('corrupto')
    with pytest.raises(ValueError, match='corrupto'):
        repeticion(tmp_path / 'corrida', .1, z, m, 1)
