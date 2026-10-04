import numpy as np
import pandas as pd
import pytest

from experiments.cayenne_mod.campana_cca import sortear_plan,evaluar,diario,resumen_mensajes


def contexto(valores,predicciones=None,umbral=15.):
    t=pd.date_range('2025-01-01',periods=len(valores),freq='h')
    c=pd.DataFrame(dict(timestamp=t,estacion='CCA',original_ppb=np.array(valores,dtype=float),
        base_ppb=0.,perfil_ppb=0.,predicho_ppb=valores if predicciones is None else predicciones,
        umbral_ppb=umbral,id_mensaje=np.arange(len(valores)),fcnt=np.arange(1,len(valores)+1)))
    c['fecha']=c.timestamp.dt.normalize()
    c['alerta_limpia']=(c.original_ppb-c.predicho_ppb).abs()>umbral
    return c


def plan(mascaras):
    return pd.DataFrame(dict(id_mensaje=np.arange(len(mascaras)),atacado=np.array(mascaras)!=0,
                             n_flips=[int(m).bit_count() for m in mascaras],mascara=mascaras))


def test_sorteo_reproducible_y_posiciones_distintas():
    p=sortear_plan(2000,42)
    pd.testing.assert_frame_equal(p,sortear_plan(2000,42),check_exact=True)
    assert not p.equals(sortear_plan(2000,43))
    assert p.n_flips.between(0,16).all()
    np.testing.assert_array_equal(p.mascara.map(lambda m:int(m).bit_count()),p.n_flips)
    np.testing.assert_array_equal(p.atacado,p.n_flips>0)
    assert sortear_plan(100,42,0).mascara.eq(0).all()
    assert sortear_plan(100,42,1).atacado.all()
    with pytest.raises(ValueError):
        sortear_plan(10,42,1.1)


def test_misma_mascara_y_valor_original_tres_formatos():
    c=contexto([60,28])
    p=plan([1<<5,1<<5])
    for f,esperados in [('base',[28,60]),('A',[44,44]),('B',[52,36])]:
        d=evaluar(c,p,f,42)
        np.testing.assert_array_equal(d.recibido_ppb,esperados)
        np.testing.assert_array_equal(d.mascara,p.mascara)
        np.testing.assert_array_equal(d.original_ppb,c.original_ppb)


def test_cancelacion_no_se_cuenta_como_deteccion_de_valor_alterado():
    c=contexto([28],[0],10.)
    d=evaluar(c,plan([(1<<3)|(1<<11)]),'B',42)
    assert d.recibido_ppb.iloc[0]==28
    assert d.cancelaciones.iloc[0]
    assert d.alerta.iloc[0]
    s=resumen_mensajes(d)
    assert s['alertas_cancelados']==1
    assert s['alterados']==s['detectados_alterados']==0
    assert np.isnan(s['recall_alterados_pct'])


def test_ataques_del_mismo_dia_se_combinan():
    c=contexto([60,59,20])
    juntas=diario(evaluar(c,plan([32,32,0]),'base',42)).iloc[0]
    assert juntas.maximo_recibido==28
    assert juntas.cambio_banda_disponibles
    for masks in ([32,0,0],[0,32,0]):
        aislada=diario(evaluar(c,plan(masks),'base',42)).iloc[0]
        assert not aislada.cambio_banda_disponibles


def test_rechazo_es_perdida_con_alerta_indefinida_y_sin_cero_imputado():
    c=contexto([100,50])
    d=evaluar(c,plan([1<<15,0]),'B',42)
    assert pd.isna(d.recibido_ppb.iloc[0]) and pd.isna(d.alerta.iloc[0])
    s=resumen_mensajes(d)
    assert s['rechazos']==1 and s['banda_local_sin_alerta']==0
    dia=diario(d).iloc[0]
    assert dia.maximo_recibido==50
    assert dia.cambio_banda_disponibles and dia.cambio_banda_solo_perdidas
    assert not dia.cambio_banda_solo_valores
    todo=diario(evaluar(c,plan([1<<15,1<<15]),'B',42)).iloc[0]
    assert todo.dia_sin_datos and pd.isna(todo.maximo_recibido)
    assert not todo.cambio_banda_disponibles


def test_limpios_y_falsas_alarmas_se_conservan_sin_ataques():
    c=contexto([60,28,90],[40,28,90])
    p=sortear_plan(len(c),42,0)
    for f in ('base','A','B'):
        d=evaluar(c,p,f,42)
        np.testing.assert_array_equal(d.recibido_ppb,c.original_ppb)
        np.testing.assert_array_equal(d.alerta,c.alerta_limpia)
        s=resumen_mensajes(d)
        assert s['ataques']==s['rechazos']==s['banda_local_sin_alerta']==0
        assert s['falsas_alarmas_limpios']==1
        assert not diario(d).cambio_banda_disponibles.any()


def test_descomposicion_de_ataques_y_excedencia155():
    c=contexto([27,28,60,155,160],[27,28,60,155,160],500.)
    p=plan([128,(1<<3)|(1<<11),65535,128,128])
    for f in ('base','A','B'):
        d=evaluar(c,p,f,42)
        s=resumen_mensajes(d)
        assert s['ataques']==s['rechazos']+s['aceptados_atacados']
        assert s['aceptados_atacados']==s['cancelaciones']+s['alterados']
        assert s['banda_local_sin_alerta']<=s['banda_local_cambiada']<=s['alterados']
        assert s['falsa_excedencia']==s['falsa_excedencia_sin_alerta']==1
        assert s['ocultamiento']==s['ocultamiento_sin_alerta']==2
