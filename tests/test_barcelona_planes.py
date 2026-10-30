import numpy as np
import pandas as pd

from experiments.barcelona.generar_planes import generar, half_up


def base():
    codes = [f'{i:08}' for i in range(13)]
    dias = pd.date_range('2018-01-01', periods=20, tz='UTC')
    d = pd.DataFrame([dict(estacion=s, dia_utc=t, comun=not (s == codes[0] and t.day > 10))
                      for s in codes for t in dias])
    e = pd.DataFrame({'desv': np.arange(1, 14, dtype=float)}, index=codes)
    return codes, d, e


def test_plan_pareado_soporte_y_magnitud():
    codes, d, e = base()
    p, m = generar(d, e, codes, 3, True)
    assert len(m) == 125 and half_up(.3 * 13) == 4
    assert (p.groupby('plan').estacion.nunique() == 4).all()
    for (_, s), g in p.groupby(['plan', 'estacion']):
        assert len(g) == half_up(.3 * d[(d.estacion == s) & d.comun].shape[0])
    assert set(zip(p.estacion, p.dia_utc)) <= set(zip(d[d.comun].estacion, d[d.comun].dia_utc))
    np.testing.assert_allclose(p.desplazamiento_ug_m3, p.beta * p.sigma_ajuste)
    assert p.beta.between(.4, 4).all()
    # Un factor de magnitud fija beta por caso, aunque cambien sensores/días.
    assert p.groupby(['factor_ruido', 'estacion', 'dia_utc']).beta.nunique().eq(1).all()
    p2, m2 = generar(d, e, codes, 3, True)
    pd.testing.assert_frame_equal(p, p2, check_exact=True)
    pd.testing.assert_frame_equal(m, m2, check_exact=True)


def test_usos_independientes_y_numero_calendarios():
    codes, d, e = base()
    p, m = generar(d, e, codes, 0, False)
    q, n = generar(d, e, codes, 1, False)
    assert len(m) == 20 and len(n) == 10
    assert not p.iloc[:20].beta.equals(q.iloc[:20].beta)
