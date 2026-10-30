import numpy as np
import pytest
from experiments.barcelona.empaquetar_examen import firma,parche
from experiments.barcelona.empaquetar_examen import indices_iguales
import pandas as pd


@pytest.mark.parametrize('tipo',['float32','float64'])
def test_parche_preserva_bits_nan_y_cero_con_signo(tipo,tmp_path):
    b=np.array([[np.nan,0.,1.],[3.,4.,5.]],dtype=tipo)
    a=b.copy();a[0,1]=-0.;a[1,0]=99.
    i,x=parche(a,b)
    np.savez_compressed(tmp_path/'p.npz',i=i,x=x)
    p=np.load(tmp_path/'p.npz');r=b.copy();r.ravel()[p['i']]=p['x']
    assert firma(r)==firma(a)
    assert len(i)==2 and np.signbit(r[0,1])


def test_no_se_acepta_otro_tipo_o_forma():
    with pytest.raises(AssertionError):parche(np.ones(3,'float32'),np.ones(3,'float64'))


def test_indices_aceptan_resolucion_pero_no_cambio_de_horas():
    a=pd.date_range('2017-01-01',periods=3,freq='D',tz='UTC')
    assert indices_iguales(a.as_unit('us'),a.as_unit('ns'))
    assert not indices_iguales(a,a+pd.Timedelta(hours=1))
    assert not indices_iguales(a,a.tz_localize(None))
