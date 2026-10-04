import numpy as np
import pandas as pd
from experiments.cayenne_mod.campanas_estaciones import diario_vector,semilla_estacion
from experiments.cayenne_mod.campana_cca import sortear_plan
from experiments.cayenne_mod.diario_base_B import medir_dia


def test_sorteos_independientes_por_estacion_y_CCA_preservada():
    pd.testing.assert_frame_equal(sortear_plan(1684,semilla_estacion(42,'CCA')),sortear_plan(1684,42))
    a=sortear_plan(1684,semilla_estacion(42,'AJM'))
    pd.testing.assert_frame_equal(a,sortear_plan(1684,semilla_estacion(42,'AJM')))
    assert not a.equals(sortear_plan(1684,semilla_estacion(42,'CCA')))
    assert not a.equals(sortear_plan(1684,semilla_estacion(42,'MER')))


def test_diario_vector_equivale_al_analisis_detallado():
    casos=[([60,59,20],[28,27,20],[True,False,False]),
           ([60,59,20],[np.nan,27,20],[None,False,False]),
           ([100,50],[np.nan,np.nan],[None,None]),
           ([154,10],[155,10],[False,True]),
           ([155,10],[154,10],[False,False]),
           ([60,20],[28,30],[False,True])]
    for x,r,al in casos:
        x=np.array(x,dtype=float);r=np.array(r,dtype=float)
        d=pd.DataFrame(dict(fecha=pd.Timestamp('2025-01-01'),original_ppb=x,recibido_ppb=r,
            atacado=True,aceptado=np.isfinite(r),alterados=np.isfinite(r)&(r!=x),
            alerta=pd.array(al,dtype='boolean')))
        lento=medir_dia(d);rapido=diario_vector(d).iloc[0]
        assert rapido.sin_datos==lento['dia_sin_datos']
        np.testing.assert_equal(rapido.recibido,lento['maximo_recibido'])
        for t in ('banda','falsa_excedencia','ocultamiento'):
            assert rapido[t]==lento[t]
            assert rapido[t+'_sin_alerta_alterados']==lento[t+'_sin_alerta_en_alterados']
            assert rapido[t+'_persiste_silenciosos']==lento[t+'_persiste_solo_silenciosos']
