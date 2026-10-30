"""No confundir ausencias con cobertura ni horas locales con UTC."""
import pandas as pd
from experiments.barcelona.auditar_horas_etapas import elegibilidad_ajuste,resumen_cambio_horario


def test_estacion_sin_ajuste_no_se_vuelve_elegible_por_tener_test():
    d=pd.DataFrame(dict(codi_eoi=['A','A','B'],fecha=pd.to_datetime(['2014-01-01','2014-02-01','2018-01-01']),hora_fuente=[1,1,1],o3=[1.,2.,3.]))
    c=pd.DataFrame(dict(codigo=['A','A','B','B'],nombre=['a','a','b','b'],anio=[2014,2015,2014,2015],horas_presentes=[3000,3000,0,0],horas_posibles=[8760]*4))
    s=elegibilidad_ajuste(d,c)
    assert s.loc[('B','b'),'meses_ajuste']==0
    assert not s.loc[('B','b'),'elegible_provisional_2000h_6meses']
    # Horas suficientes pero pocos meses tampoco alcanzan el criterio.
    assert not s.loc[('A','a'),'elegible_provisional_2000h_6meses']


def test_cambio_estacional_conserva_hora_fuente_y_distingue_faltante():
    d=pd.DataFrame(dict(codi_eoi=['A']*3,fecha=pd.to_datetime(['2018-03-25']*3),hora_fuente=[1,2,3],o3=[10.,float('nan'),20.]))
    r=resumen_cambio_horario(d)
    s=r[r.fecha=='2018-03-25'].set_index('hora_fuente')
    assert s.loc[2,'estaciones_con_fila']==1 and s.loc[2,'con_valor']==0
    assert s.loc[3,'con_valor']==1
    assert not any('utc' in k.lower() for k in r.columns)
