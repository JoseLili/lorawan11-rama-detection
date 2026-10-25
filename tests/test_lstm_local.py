"""Protocolo anomalias_red_v1, revisión 14: columnas locales, muestra de ventanas y calendarios nuevos."""

import numpy as np
import pandas as pd
import pytest

from src.detect import anomalias_red as ar
from src.detect import evaluacion_red as ev
from src.detect import lstm_local as ll


def _matriz(estaciones, horas=30):
    idx = pd.date_range('2022-01-01', periods=horas, freq='h')
    rng = np.random.default_rng(0)
    datos = {}
    for s in estaciones:
        datos[f'{s}_valor'] = 30 + 10 * rng.random(horas)
        datos[f'{s}_mascara'] = 1.0
    datos['hora_sin'], datos['hora_cos'] = np.sin(np.arange(horas)), np.cos(np.arange(horas))
    return pd.DataFrame(datos, index=idx)


def test_columnas_locales_salen_de_las_98_en_su_lugar():
    est = ['A', 'B', 'C', 'D', 'E', 'F']
    vecinas = {s: [e for e in est if e != s][:4] for s in est}
    vecinas['C'] = ['F', 'A', 'E', 'B']
    x = _matriz(est)
    par = ev.Vecinas('a14', vecinas, None, pd.Series(1.0, index=est))
    F = ev.entradas_vecinas(x, pd.Series(1.0, index=est), par)
    rel = ev.entradas_relativas(x, pd.Series(1.0, index=est))
    nuevas = ev.columnas_vecinas(x, pd.Series(1.0, index=est), par).fillna(0.0).to_numpy(np.float32)
    idx = ll.indices_locales(est, vecinas, 'C')
    assert len(idx) == ll.N_COLUMNAS
    local = F[:, idx]
    for k, e in enumerate(['C', 'F', 'A', 'E', 'B']):
        i = est.index(e)
        np.testing.assert_array_equal(local[:, 3 * k], rel[:, i])                  # relativa
        np.testing.assert_array_equal(local[:, 3 * k + 1], x[f'{e}_mascara'])      # máscara
        np.testing.assert_array_equal(local[:, 3 * k + 2], nuevas[:, i])           # columna de vecinas
    np.testing.assert_array_equal(local[:, -2:], x[['hora_sin', 'hora_cos']].to_numpy(np.float32))
    X = ll.ventanas_locales(F, est, vecinas, 'C', np.array([23, 29]))
    assert X.shape == (2, 24, ll.N_COLUMNAS) and np.array_equal(X[1, -1], local[29])
    with pytest.raises(ValueError):
        ll.indices_locales(est, {**vecinas, 'C': ['A', 'B']}, 'C')


def test_muestra_reproducible_sin_reemplazo_y_distinta_por_par():
    pos = np.arange(23, 17520)
    a = ll.muestra(pos, 8, 'seleccion', 1, 0)
    assert np.array_equal(a, ll.muestra(pos, 8, 'seleccion', 1, 0))
    assert len(a) == len(pos) // 8 and len(np.unique(a)) == len(a) and np.all(np.diff(a) > 0)
    assert set(a) <= set(pos)
    assert not np.array_equal(a, ll.muestra(pos, 8, 'seleccion', 1, 1))
    assert not np.array_equal(a, ll.muestra(pos, 8, 'validacion', 1, 0))
    assert np.array_equal(ll.muestra(pos, 1, 'seleccion', 1, 0), pos)
    # mismo número de ventanas con 20 calendarios (1 de cada 8) que con 60 (1 de cada 24)
    assert 20 * (len(pos) // ll.CADA[20]) == pytest.approx(60 * (len(pos) // ll.CADA[60]), rel=1e-3)


def test_calendarios_nuevos_no_cambian_los_20_de_siempre():
    veinte = ar.calendarios_entrenamiento()
    sesenta = ar.calendarios_entrenamiento(n=ar.CALENDARIOS_AMPLIADOS)
    assert len(veinte) == 20 and len(sesenta) == 60
    pd.testing.assert_frame_equal(sesenta.iloc[:20], veinte)
    assert sesenta.corrida.iloc[-1] == 'entrenamiento_60'
