import numpy as np
import pandas as pd
import pytest

from experiments.cayenne_mod.campana_cca import evaluar
from experiments.cayenne_mod.comparacion_base_B import analizar,emparejar


def ataques():
    vals=[80.,60.,28.,60.,60.]
    t=pd.date_range('2025-01-01',periods=5,freq='h')
    c=pd.DataFrame(dict(timestamp=t,estacion='CCA',original_ppb=vals,base_ppb=0.,perfil_ppb=0.,
        predicho_ppb=vals,umbral_ppb=[40.,20.,20.,40.,40.],id_mensaje=range(5),fcnt=range(1,6),alerta_limpia=False))
    c['fecha']=c.timestamp.dt.normalize()
    masks=[32,32,(1<<3)|(1<<11),256,1<<15]
    p=pd.DataFrame(dict(id_mensaje=range(5),atacado=True,n_flips=[int(m).bit_count() for m in masks],mascara=masks))
    return pd.concat([evaluar(c,p,f,42) for f in ('base','B')],ignore_index=True)


def test_aceptacion_comun_no_oculta_ataques_extra():
    r=analizar(ataques())
    resumen=r['resumen'].set_index(['grupo','formato'])
    assert resumen.loc[('todos','base'),'banda_local_sin_alerta']==1
    assert resumen.loc[('todos','B'),'banda_local_sin_alerta']==2
    assert resumen.loc[('ambos_aceptan','base'),'intentos']==2
    assert resumen.loc[('ambos_aceptan','B'),'banda_local_sin_alerta']==1
    assert resumen.loc[('solo_B_acepta','B'),'banda_local_sin_alerta']==1
    assert resumen.loc[('solo_B_acepta','B'),'cancelaciones']==1
    assert resumen.loc[('ambos_rechazan','base'),'intentos']==1
    for f in ('base','B'):
        grupos=resumen.xs(f,level='formato').drop(index='todos')
        assert grupos.banda_local_sin_alerta.sum()==resumen.loc[('todos',f),'banda_local_sin_alerta']


def test_transiciones_y_lectura_rechazada_no_se_confunden_con_deteccion():
    r=analizar(ataques())
    trans=r['transiciones'].set_index('grupo')
    assert trans.loc['ambos_aceptan','solo_base_escapa']==1
    assert trans.loc['ambos_aceptan','solo_B_escapa']==1
    assert trans.loc['todos','solo_B_escapa']==2
    assert trans.loc['todos','sin_escape_en_ambos']==2
    for row in trans.itertuples():
        assert row.intentos==row.escape_en_ambos+row.solo_base_escapa+row.solo_B_escapa+row.sin_escape_en_ambos
    resumen=r['resumen'].set_index(['grupo','formato'])
    assert np.isnan(resumen.loc[('ambos_rechazan','base'),'recall_alterados_pct'])
    assert np.isnan(resumen.loc[('ambos_rechazan','B'),'riesgo_por_aceptado_pct'])


def test_pareado_rechaza_mensajes_o_mascaras_distintos():
    a=ataques()
    p=emparejar(a.sample(frac=1,random_state=7))
    assert len(p)==5
    with pytest.raises(ValueError):
        emparejar(a.iloc[:-1])
    a.loc[a.formato.eq('B') & a.id_mensaje.eq(0),'mascara']=64
    with pytest.raises(AssertionError):
        emparejar(a)
