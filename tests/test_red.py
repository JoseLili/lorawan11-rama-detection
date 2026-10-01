import numpy as np
import pandas as pd

from src.detect.red import contexto_diario, efectos_red, perfil_v4_sin_test, resumir_dias, metricas_binarias


def test_no_maxima_puede_provocar_cruce():
    m = pd.DataFrame({'A':[150.], 'B':[149.]},index=pd.date_range('2025-01-01',periods=1,freq='h'))
    c = contexto_diario(m)
    recibido = c.original_ppb.to_numpy().copy()
    recibido[1] = 157  # 149 XOR bit3 = 157; original no era el máximo.
    r = efectos_red(c,recibido)
    assert r.falsa_fase1.tolist() == [False,True]
    assert r.maximo_atacado_ppb.tolist() == [150,157]


def test_anular_requiere_ningun_otro_mensaje_sobre_umbral():
    m = pd.DataFrame({'A':[160.,156.], 'B':[120.,100.]},index=pd.date_range('2025-01-01',periods=2,freq='h'))
    c = contexto_diario(m)
    recibido = c.original_ppb.to_numpy().copy()
    recibido[0] = 128
    assert not efectos_red(c,recibido).anulada_fase1.any()
    m.iloc[1,0] = 150
    c = contexto_diario(m)
    assert efectos_red(c,recibido).anulada_fase1.iloc[0]


def test_empates_y_faltantes_no_se_borran():
    m = pd.DataFrame({'A':[160.], 'B':[160.], 'C':[np.nan]},index=pd.date_range('2025-01-01',periods=1,freq='h'))
    c = contexto_diario(m)
    assert len(c)==2
    assert c.maximo_otros_ppb.eq(160).all()
    assert not efectos_red(c,[128,128]).anulada_fase1.any() # son dos escenarios distintos


def test_perfil_no_usa_test_en_respaldo_y_solo_pasado_en_test():
    s = pd.Series(np.arange(96,dtype=float),index=pd.date_range('2025-01-01',periods=96,freq='h'))
    mod = s.copy()
    mod.iloc[72:] = 99999
    a,b = perfil_v4_sin_test(s,48),perfil_v4_sin_test(mod,48)
    np.testing.assert_array_equal(a.iloc[:73],b.iloc[:73])


def test_dias_no_se_suman_por_estacion_ni_desconocidos_como_negativos():
    fecha = pd.Timestamp('2025-01-01')
    e = pd.DataFrame(dict(fecha=[fecha]*3,bit=[3]*3,tipo_dano=['cruce_fase1']*3,
        dano_observado=[True]*3,dano_evaluable=[True,True,False],
        dano_detectado=[True,False,False],dano_no_detectado=[False,True,False],
        dano_sin_evaluacion=[False,False,True]))
    r,d = resumir_dias(e,pd.date_range(fecha,periods=2))
    assert r.dias_vulnerables_evaluables.iloc[0]==1
    assert r.pct_dias_dano_no_detectado.iloc[0]==50
    assert r.deteccion_dano_pct.iloc[0]==50
    assert r.dias_con_dano_sin_evaluacion.iloc[0]==1
    assert len(d)==2


def test_sin_dano_no_es_deteccion_cero():
    e = pd.DataFrame(dict(fecha=[pd.Timestamp('2025-01-01')],bit=[1],tipo_dano=['cruce_fase1'],
        dano_observado=[False],dano_evaluable=[False],dano_detectado=[False],
        dano_no_detectado=[False],dano_sin_evaluacion=[False]))
    r,_ = resumir_dias(e,e.fecha)
    assert np.isnan(r.deteccion_dano_pct.iloc[0])
    assert np.isnan(metricas_binarias([False],[False])['recall_pct'])


def test_reemplazo_individual_coincide_con_recalculo_completo():
    rng = np.random.default_rng(42)
    values = rng.integers(0,200,size=(48,4)).astype(float)
    values[0,0] = np.nan
    m = pd.DataFrame(values,index=pd.date_range('2025-01-01',periods=48,freq='h'),columns=list('ABCD'))
    c = contexto_diario(m)
    for bit in range(1,8):
        recibido = c.original_ppb.to_numpy(dtype=int) ^ (1<<bit)
        efecto = efectos_red(c,recibido)
        for i in [0, 12, 94, 120, 180]:
            fila = c.iloc[i]
            dia = m.loc[m.index.normalize()==fila.fecha].copy()
            dia.loc[fila.timestamp,fila.estacion] = recibido[i]
            assert efecto.maximo_atacado_ppb.iloc[i] == np.nanmax(dia.to_numpy())
