import numpy as np
from experiments.barcelona.resumir_examen import conteos,medidas,grupos_conteos


def test_confusion_y_f1_agregados_no_promedio_de_f1():
    y=np.array([[1,1,0],[0,1,0]],bool);p=np.array([[1,0,1],[0,1,0]],bool)
    c=conteos(y,p);np.testing.assert_array_equal(c,[2,1,1,2])
    assert medidas(c)['f1']==2/3
    g=grupos_conteos(y,p,np.array([0,1,0]),2)
    np.testing.assert_array_equal(g.sum(axis=0),c)
    # Un bloque conserva ambas realizaciones; duplicarlo duplica sus conteos.
    np.testing.assert_array_equal(np.array([[2,0]])@g,2*g[[0]])


def test_denominadores_cero_siguen_regla_registrada():
    m=medidas([0,0,0,100])
    assert all(float(x)==0 for x in m.values())
