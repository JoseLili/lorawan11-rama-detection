import numpy as np
import pandas as pd
import pytest

from experiments.barcelona.preparar_tiempo import preparar


def datos(fecha):
    return pd.DataFrame(dict(codi_eoi=['A'] * 24, fecha=pd.to_datetime([fecha] * 24),
                             hora_fuente=range(1, 25), o3=np.arange(24, dtype=float)))


@pytest.mark.parametrize('fecha,inicio,fin,horas', [
    ('2018-03-25', '2018-03-24', '2018-03-27', 23),
    ('2018-10-28', '2018-10-27', '2018-10-30', 25)])
def test_transicion_no_inventa_lecturas_y_mantiene_horas_fisicas(fecha, inicio, fin, horas):
    r, e = preparar(datos(fecha), ['A'], inicio, fin)
    assert len(e) == 24
    assert r.excluida_cambio_reloj.sum() == horas
    assert not r.observado.any()
    assert r.timestamp_utc.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    assert not r.timestamp_utc.duplicated().any()


@pytest.mark.parametrize('fecha,desfase', [('2018-01-10', 1), ('2018-07-10', 2)])
def test_inicio_fin_y_hora_local_independiente_de_utc(fecha, desfase):
    r, e = preparar(datos(fecha), ['A'], fecha, str((pd.Timestamp(fecha) + pd.Timedelta(days=1)).date()))
    assert e.empty and r.observado.sum() == 24
    assert r.iloc[0].timestamp_utc == pd.Timestamp(fecha, tz='UTC') - pd.Timedelta(hours=desfase)
    assert r.iloc[-1].hora_local == 23 and r.iloc[-1].hora_fuente == 24
    assert r.iloc[6].hora_sin == pytest.approx(1.)
    assert r.o3.tolist() == list(range(24))


def test_duplicados_no_se_promedian():
    d = datos('2018-01-10')
    with pytest.raises(ValueError, match='duplicadas'):
        preparar(pd.concat([d, d.iloc[:1]]), ['A'])


def test_respaldo_puede_releerse_sin_perder_claves(tmp_path):
    r, e = preparar(datos('2018-03-25'), ['A'])
    for nombre, frame in [('rejilla', r), ('excluidas', e)]:
        p = tmp_path / (nombre + '.parquet')
        frame.to_parquet(p, index=False)
        pd.testing.assert_frame_equal(pd.read_parquet(p), frame, check_exact=True)
