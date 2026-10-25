"""Protocolo anomalias_red_v1, revisión 16: episodios recorridos a una hora al azar."""

import numpy as np
import pandas as pd
import pytest

from src.detect import anomalias_red as ar
from src.detect import estacion_dia as ed


def _plan():
    return pd.DataFrame(dict(corrida='prueba_2024_01', episodio=[1, 2, 3], estacion=['PED', 'PED', 'TLA'],
                             inicio=pd.to_datetime(['2024-01-02', '2024-01-05', '2024-12-30']),
                             fin=pd.to_datetime(['2024-01-04 23:00', '2024-01-05 23:00', '2024-12-31 23:00']),
                             dias_sorteados=[3, 1, 4], dias=[3, 1, 2], signo=[1, -1, 1], p=0.002))


def test_recorre_igual_a_todos_los_episodios_de_una_estacion_y_corta_al_final():
    plan = _plan()
    r = ar.recorrer_plan(plan, 1, '2024-01-01', '2024-12-31')
    assert r.equals(ar.recorrer_plan(plan, 1, '2024-01-01', '2024-12-31'))           # reproducible
    h = {e: int(np.random.default_rng([42, 2024, 1, ar.USO_HORA, ar.m.ESTACIONES.index(e)]).integers(0, 24))
         for e in ('PED', 'TLA')}
    assert r.hora.tolist() == [h['PED'], h['PED'], h['TLA']]
    assert (r.inicio - plan.inicio).tolist() == [pd.Timedelta(hours=x) for x in r.hora]
    dur = (r.fin - r.inicio + pd.Timedelta(hours=1)).iloc[:2]
    assert dur.tolist() == [pd.Timedelta(hours=72), pd.Timedelta(hours=24)]             # misma duración
    assert r.fin.iloc[2] <= pd.Timestamp('2024-12-31 23:00')
    assert r.inicio.iloc[1] > r.fin.iloc[0]                                             # sin traslape


def test_aplicar_horas_cambia_solo_las_horas_recorridas():
    idx = pd.date_range('2024-01-01', '2024-01-08 23:00', freq='h')
    v = pd.DataFrame({'PED': 40.0, 'TLA': 30.0, 'MER': 20.0}, index=idx)
    plan = _plan().iloc[:2]
    r = ar.recorrer_plan(plan, 1, '2024-01-01', '2024-12-31')
    rec, cam = ar.aplicar_horas(v, r, 1.0)
    dentro = ar.en_episodio(r, idx, v.columns)
    assert cam.equals(dentro) and (rec['PED'][dentro['PED']].isin([80.0, 20.0])).all()
    recorrido = plan.assign(inicio=plan.inicio + pd.Timedelta(hours=5), fin=plan.fin + pd.Timedelta(hours=5))
    with pytest.raises(ValueError):                                     # `aplicar` sigue exigiendo días completos
        ar.aplicar(v, recorrido, 1.0)
    ar.aplicar_horas(v, recorrido, 1.0)


def test_etiqueta_por_dia_con_12_horas_o_mas_y_excluye_los_dias_parciales():
    idx = pd.date_range('2024-01-01', periods=72, freq='h')
    plan = pd.DataFrame(dict(estacion=['PED'], inicio=[pd.Timestamp('2024-01-01 13:00')],
                             fin=[pd.Timestamp('2024-01-02 12:00')]))           # 11 h el día 1, 13 h el día 2
    y = ed.etiquetas_recorridas(plan, idx, ['PED', 'TLA'])
    assert np.isnan(y.iat[0, 0]) and y.iat[1, 0] == 1.0 and y.iat[2, 0] == 0.0
    assert y['TLA'].eq(0.0).all()


def test_corridas_finales_son_nuevas_y_no_chocan_con_2024():
    f = ar.corridas_finales()
    assert len(f) == 20 and f.corrida.iloc[0] == 'final_2025_01' and f.corrida.iloc[-1] == 'final_2026_10'
    assert f.fin.iloc[-1] == '2026-07-31'
    p24 = ar.corridas().p.iloc[1:].to_numpy()
    assert not np.isin(f.p.to_numpy(), p24).any() and f.equals(ar.corridas_finales())
    assert ((f.p >= ar.P_RANGO[0]) & (f.p <= ar.P_RANGO[1])).all()
