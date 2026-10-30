import numpy as np
import pandas as pd

from experiments.barcelona.aplicar_ataques_proporcionales import aplicar, caracteristicas
from experiments.barcelona.preparar_ventanas import perfil_local


def ejemplo():
    idx = pd.date_range('2018-01-01', periods=96, freq='h', tz='UTC')
    v = pd.DataFrame(60., index=idx, columns=list('ABCDE'))
    plan = pd.DataFrame([dict(estacion='A', inicio=idx[24], fin=idx[47], signo=1),
                         dict(estacion='B', inicio=idx[24], fin=idx[47], signo=-1)])
    return v, plan


def test_inyeccion_real_signos_faltantes_y_no_cambia_fuera():
    v, p = ejemplo(); v.iloc[25, 0] = np.nan
    a, y, prog = aplicar(v, p, .5)
    assert a.iloc[24, 0] == 90 and a.iloc[24, 1] == 40
    assert np.isnan(a.iloc[25, 0]) and not y.iloc[25, 0] and prog.iloc[25, 0]
    assert a.notna().equals(v.notna())
    pd.testing.assert_frame_equal(a.iloc[:24], v.iloc[:24], check_exact=True)
    pd.testing.assert_frame_equal(a.iloc[48:], v.iloc[48:], check_exact=True)


def test_redondeo_y_etiqueta_cambio_real():
    v, p = ejemplo(); v['A'] = 0; v['B'] = 1
    a, y, prog = aplicar(v, p, .05)
    assert prog.iloc[24, 0] and not y.iloc[24, 0]
    assert not y.any().any()
    assert a.equals(v)


def test_contexto_se_contamina_causalmente_sin_reajustar_escalas():
    v, p = ejemplo()
    a, _, _ = aplicar(v, p, .5)
    reloj = pd.DataFrame(dict(hora_sin=np.zeros(len(v)), hora_cos=np.ones(len(v))), index=v.index)
    esc = pd.DataFrame(dict(media=[60.]*5, desv=[10.]*5, escala_a14=[1.]*5), index=v.columns)
    vec = {s: [t for t in v if t != s] for s in v}
    b, z, F = caracteristicas(a, esc, reloj, vec)
    original = perfil_local(v)
    pd.testing.assert_frame_equal(b.iloc[:25], original.iloc[:25], check_exact=True)
    assert b.iloc[48, 0] > original.iloc[48, 0]  # Después del episodio persiste en el perfil.
    assert z[24, 0] == 3 and esc.loc['A', 'desv'] == 10
    assert F.shape == (96, 17)  # Matriz global: 3*n+2 con cinco estaciones.
