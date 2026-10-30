"""Protocolo anomalias_red_v1, revisión 19: una estación a la vez (B) y un solo nodo comprometido (A)."""

import numpy as np
import pandas as pd

from src.detect import anomalias_red as ar
from src.detect import multianual as m


def _plan(filas):
    p = pd.DataFrame(filas, columns=['estacion', 'inicio', 'dias', 'signo'])
    p['inicio'] = pd.to_datetime(p['inicio'])
    p['fin'] = p['inicio'] + pd.to_timedelta(p['dias'], unit='D') - pd.Timedelta(hours=1)
    p = p.assign(corrida='x', episodio=np.arange(1, len(p) + 1), dias_sorteados=p['dias'], p=0.002)
    return p[ar.COLUMNAS_PLAN]


def test_una_a_la_vez_conserva_en_orden_de_inicio_y_sin_dias_compartidos():
    plan = _plan([('PED', '2025-03-12', 4, 1), ('CAM', '2025-03-12', 2, -1),     # mismo día: CAM va antes en la matriz
                  ('TLA', '2025-03-14', 1, 1),                                    # comparte el 14 con PED
                  ('MER', '2025-03-16', 3, -1),                                   # PED termina el 15: libre
                  ('GAM', '2025-03-18', 2, 1)])                                   # comparte el 18 con MER
    primero = min(['PED', 'CAM'], key=m.ESTACIONES.index)
    q = ar.una_a_la_vez(plan)
    assert q['estacion'].tolist()[0] == primero
    assert ar.una_a_la_vez(plan).equals(q)                                        # sin azar
    dias = [d for e in q.itertuples() for d in pd.date_range(e.inicio.normalize(), e.fin.normalize())]
    assert len(dias) == len(set(dias))                                            # nunca dos a la vez
    assert set(q['episodio']) <= set(plan['episodio'])                            # mismos episodios, sin cambios
    pd.testing.assert_frame_equal(q.set_index('episodio'), plan.set_index('episodio').loc[q['episodio']])
    assert 'MER' in q['estacion'].tolist() and 'GAM' not in q['estacion'].tolist()


def test_calendarios_de_un_nodo_solo_alteran_su_estacion_y_no_chocan():
    alt = ['PED', 'TLA', 'MER']
    c = ar.corridas_nodo(alt)
    assert len(c) == 9 and c.equals(ar.corridas_nodo(alt))
    assert c.corrida.iloc[0] == 'nodo_2024_PED' and c.corrida.iloc[-1] == 'nodo_2026_MER'
    assert ((c.p >= ar.P_RANGO_NODO[0]) & (c.p <= ar.P_RANGO_NODO[1])).all()
    assert c.numero.min() > ar.CORRIDAS_PRUEBA and c.numero.max() <= ar.NUMERO_NODO + 31
    pruebas = pd.concat([ar.corridas(), ar.corridas_finales()]).p.to_numpy()
    assert not np.isin(c.p.to_numpy(), pruebas).any()
    for fila in c.itertuples():
        plan = ar.plan_nodo(fila._asdict())
        assert set(plan['estacion']) <= {fila.estacion} and (plan['corrida'] == fila.corrida).all()
        ar.validar_plan(plan)
    plan = ar.plan_nodo(c.iloc[0])
    assert 2 <= len(plan) <= 12                                                    # unos 4 a 7 por año


def test_error_fijo_suma_o_resta_a_ppb_sin_bajar_de_cero():
    """Revisión 21."""
    import pytest
    idx = pd.date_range('2024-01-01', periods=72, freq='h')
    v = pd.DataFrame({'PED': 3.0, 'TLA': 50.0, 'MER': 40.0}, index=idx)
    v.iloc[5, 0] = np.nan
    plan = _plan([('PED', '2024-01-01', 1, -1), ('TLA', '2024-01-02', 1, 1)])
    rec, cam = ar.aplicar_fijo(v, plan, 10)
    assert (rec['PED'].iloc[:24].dropna() == 0.0).all() and np.isnan(rec['PED'].iloc[5])   # recorte en 0
    assert (rec['TLA'].iloc[24:48] == 60.0).all() and (rec['TLA'].iloc[:24] == 50.0).all()
    assert rec['MER'].equals(v['MER']) and not cam['MER'].any()
    assert cam['PED'].sum() == 23 and cam['TLA'].sum() == 24
    with pytest.raises(ValueError):
        ar.aplicar_fijo(v, plan, 15)
