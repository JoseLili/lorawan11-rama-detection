"""Ataques V4 multianual: cadena real, plan pareado y daño de red."""

import numpy as np
import pandas as pd
import pytest

from src.detect import ataques_multianual as at
from src.detect import multianual as m


def _valores(dias=3):
    idx = pd.date_range('2024-05-01', periods=24 * dias, freq='h')
    v = pd.DataFrame(np.nan, index=idx, columns=m.ESTACIONES)
    v['CCA'] = 40.0
    v['PED'] = 30.0
    return v


def _preds(v, est=('CCA',), umbral=20.0):
    return pd.concat([pd.DataFrame({'timestamp': v.index, 'predicho_ppb': v[e].to_numpy(),
                                    'estacion': e, 'umbral_ppb': umbral}) for e in est], ignore_index=True)


def test_voltear_usa_cadena_real_y_coincide_con_xor():
    o = np.array([0, 1, 87, 155, 167, 187], dtype=float)
    for bit in at.BITS:
        np.testing.assert_array_equal(at.voltear(o, bit), o.astype(int) ^ (1 << bit))


def test_mensajes_conserva_no_evaluables():
    v = _valores()
    b = at.mensajes_prueba(v, _preds(v), 2024)
    assert len(b) == 2 * 72
    assert b.loc[b.estacion == 'CCA', 'evaluable'].all() and not b.loc[b.estacion == 'PED', 'evaluable'].any()


def test_plan_pareado_reproducible_e_independiente_de_evaluabilidad():
    v = _valores(dias=60)
    b1 = at.mensajes_prueba(v, _preds(v), 2024)
    b2 = at.mensajes_prueba(v, _preds(v, est=('CCA', 'PED')), 2024)
    s1, s2 = at.plan_pareado(b1), at.plan_pareado(b2)
    assert s1.equals(s2) and s1.equals(at.plan_pareado(b1))
    assert 0.02 < s1.mean() < 0.09


def test_pareado_detecta_bit_grande_y_no_bit_pequeno():
    v = _valores(dias=60)
    b = at.mensajes_prueba(v, _preds(v), 2024)
    r = at.evaluar_pareado(b, at.plan_pareado(b))
    cca = r[r.estacion == 'CCA'].set_index('bit')
    assert cca.at[7, 'recall_pct'] == 100 and cca.at[0, 'recall_pct'] == 0
    assert (cca.fp == 0).all()                      # predicción perfecta: sin falsas alarmas
    ped = r[r.estacion == 'PED']
    assert (ped.mensajes_evaluables == 0).all() and ped.recall_pct.isna().all()


def test_ocultamiento_requiere_bajar_el_maximo_de_toda_la_red():
    v = _valores(dias=1)
    t = v.index[15]
    v.loc[t, 'CCA'] = 167.0     # 167 ^ 32 = 135
    v.loc[t, 'PED'] = 166.0     # sigue >= 155: no hay ocultamiento
    b = at.mensajes_prueba(v, _preds(v, umbral=1000.0), 2024)
    c, ev, _ = at.barrido(b)
    fila = ev[(ev.bit == 5) & (ev.timestamp == t) & (ev.estacion == 'CCA')].iloc[0]
    assert fila.recibido_ppb == 135 and not fila.anulada_fase1 and fila.cambio_banda_local
    v.loc[t, 'PED'] = 150.0
    b = at.mensajes_prueba(v, _preds(v, umbral=1000.0), 2024)
    c, ev, _ = at.barrido(b)
    fila = ev[(ev.bit == 5) & (ev.timestamp == t) & (ev.estacion == 'CCA')].iloc[0]
    assert fila.anulada_fase1 and not fila.detectado
    fila5 = c[(c.bit == 5) & (c.tipo_dano == 'anulada_fase1')].iloc[0]
    assert fila5.oportunidades == 1 and fila5.no_detectadas == 1
