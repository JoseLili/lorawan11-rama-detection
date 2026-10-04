import numpy as np
import pandas as pd
from experiments.cayenne_mod.diario_base_B import medir_dia


def medir(x,r,at,al):
    return medir_dia(pd.DataFrame(dict(original_ppb=x,recibido_ppb=r,atacado=at,alerta=pd.array(al,dtype='boolean'))))


def test_alarma_limpia_no_equivale_a_alerta_del_ataque():
    d=medir([60,10],[28,10],[True,False],[False,True])
    assert d['banda'] and not d['banda_sin_alerta_alguna']
    assert d['banda_sin_alerta_en_alterados']
    assert d['banda_persiste_solo_silenciosos']


def test_detectar_otra_alteracion_no_elimina_dano():
    d=medir([60,20],[28,30],[True,True],[False,True])
    assert d['banda'] and not d['banda_sin_alerta_en_alterados']
    assert d['banda_persiste_restaurando_detectados']
    assert d['banda_persiste_solo_silenciosos']


def test_ataques_juntos_y_restauracion_del_detectado():
    d=medir([60,59,20],[28,27,20],[True,True,False],[True,False,False])
    assert d['maximo_recibido']==28 and d['banda']
    assert d['maximo_restaurando_detectados']==60
    assert not d['banda_persiste_restaurando_detectados']
    assert not d['banda_persiste_solo_silenciosos']


def test_perdida_no_se_acredita_como_lectura_integra_o_deteccion():
    d=medir([100,50],[np.nan,50],[True,False],[None,False])
    assert d['banda_fuente']=='solo_perdidas_suficientes'
    assert d['banda_sin_alerta_en_alterados']
    assert d['banda_persiste_restaurando_detectados']
    assert not d['banda_persiste_solo_silenciosos']
    nada=medir([100,50],[np.nan,np.nan],[True,True],[None,None])
    assert nada['dia_sin_datos'] and np.isnan(nada['maximo_recibido'])
    assert not nada['banda'] and not nada['ocultamiento']


def test_interaccion_perdidas_y_valores_no_se_suma_como_dos_danos():
    d=medir([60,59,20],[np.nan,27,20],[True,True,False],[None,False,False])
    assert d['banda_fuente']=='interaccion'
    assert not d['banda_solo_valores'] and not d['banda_solo_perdidas']
    assert d['banda_persiste_restaurando_detectados']
    assert not d['banda_persiste_solo_silenciosos']


def test_umbral155_y_ausencia_de_dano():
    d=medir([154,10],[155,10],[True,False],[False,False])
    assert d['falsa_excedencia'] and not d['ocultamiento']
    d=medir([155,10],[154,10],[True,False],[False,False])
    assert d['ocultamiento'] and not d['falsa_excedencia']
    d=medir([60,10],[60,10],[False,False],[True,False])
    assert not d['banda'] and d['alertas_limpios']==1
