"""Inferencia duplicada de modelos congelados; sólo calibración limpia 2017."""
import os
for k,v in {'CUDA_VISIBLE_DEVICES':'-1','TF_ENABLE_ONEDNN_OPTS':'0','TF_DETERMINISTIC_OPS':'1',
            'TF_NUM_INTRAOP_THREADS':'1','TF_NUM_INTEROP_THREADS':'1','OMP_NUM_THREADS':'1'}.items():os.environ[k]=v
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

from src.detect import paraad as p
from src.detect.lstm import fijar_semilla
from src.detect.evaluacion_red import umbral_falsas_alarmas
from experiments.barcelona.preparar_ventanas import ventana_l0,ventana_v4,bloque_paraad

ROOT=Path(__file__).resolve().parents[2]


def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()


def cargar(path):
    tf.keras.backend.clear_session();fijar_semilla(42)
    return tf.keras.models.load_model(path,compile=False)


def predecir(modelo,X):
    return np.concatenate([modelo(X[i:i+256],training=False).numpy() for i in range(0,len(X),256)])


def inferir(d):
    v=pd.read_parquet(d/'valores.parquet');base=pd.read_parquet(d/'perfiles.parquet')
    reloj=pd.read_parquet(d/'reloj.parquet');z=np.load(d/'z.npy');F=np.load(d/'l0_features.npy',mmap_mode='r')
    l0mask=pd.read_parquet(d/'horas_l0.parquet');v4mask=pd.read_parquet(d/'horas_v4.parquet')
    sd=pd.read_parquet(d/'estacion_dias.parquet')
    assert v.index.max().year==2017 and set(sd.dia_utc.dt.year)=={2017}
    comun=sd.pivot(index='dia_utc',columns='estacion',values='comun').reindex(columns=v.columns)
    assert comun.to_numpy().sum()==4536
    vec=json.loads((d/'vecinas.json').read_text())
    cal=v.index.year==2017;idx=v.index[cal];diarios={};horarios={}
    ml0=cargar(d/'modelos/l0.keras');prob=pd.DataFrame(np.nan,index=idx,columns=v.columns)
    for s in v:
        pos=np.flatnonzero(l0mask[s].to_numpy() & cal)
        X=ventana_l0(F,list(v),vec,s,pos)
        val=predecir(ml0,X).ravel().astype('float64');assert np.isfinite(val).all()
        prob.loc[v.index[pos],s]=val
    horarios['l0']=prob
    diarios['l0']=prob.groupby(prob.index.normalize()).mean().where(prob.notna().groupby(prob.index.normalize()).sum()>=12)
    res=pd.DataFrame(np.nan,index=idx,columns=v.columns)
    hora=reloj[['hora_sin','hora_cos']].to_numpy(np.float32);mask=v.notna().to_numpy(np.float32)
    for j,s in enumerate(v):
        pos=np.flatnonzero(v4mask[s].to_numpy() & cal)
        modelo=cargar(d/f'modelos/v4_{s}.keras')
        X=ventana_v4(z,mask,hora,j,pos)
        cor=predecir(modelo,X).ravel().astype('float64')
        val=v[s].to_numpy()[pos]-base[s].to_numpy()[pos]-cor
        assert np.isfinite(val).all();res.loc[v.index[pos],s]=val
    horarios['v4_residuo']=res
    p95=res.abs().quantile(.95,interpolation='linear')
    assert np.isfinite(p95).all() and (p95>0).all()
    diarios['v4']=(res.groupby(res.index.normalize()).mean().abs()/p95).where(res.notna().groupby(res.index.normalize()).sum()>=12)
    # Bloques completos seguros; se conservan NaN fuera de soporte común.
    pos=sd[sd.bloque_seguro].inicio_pos.drop_duplicates().to_numpy()
    X,m=bloque_paraad(z,mask,pos)
    rec=predecir(cargar(d/'modelos/paraad.keras'),X)
    n=m.sum(axis=2);err=(np.abs(X.astype('float64')-rec)*m).sum(axis=2)
    score=np.divide(err,n,out=np.full(err.shape,np.nan),where=n>=12)
    diarios['paraad']=pd.DataFrame(score,index=v.index[pos].normalize(),columns=v.columns)
    for nombre,s in diarios.items():
        s=s.reindex(index=comun.index,columns=comun.columns)
        assert np.isfinite(s.to_numpy()[comun.to_numpy()]).all()
        diarios[nombre]=s.where(comun)
    return diarios,horarios,p95,comun


def main():
    assert not tf.config.get_visible_devices('GPU')
    d=ROOT/'entrada';out=ROOT/'salidas/calibracion';out.mkdir(parents=True,exist_ok=False)
    meta=json.loads((d/'registro_paquete.json').read_text())
    for n,h in meta['archivos'].items():assert sha(ROOT/n)==h,n
    assert tf.__version__=='2.21.0' and tf.keras.__version__=='3.13.2'
    a,ha,p95,comun=inferir(d);b,hb,p952,comun2=inferir(d)
    for n in a:pd.testing.assert_frame_equal(a[n],b[n],check_exact=True)
    for n in ha:pd.testing.assert_frame_equal(ha[n],hb[n],check_exact=True)
    pd.testing.assert_series_equal(p95,p952,check_exact=True)
    pd.testing.assert_frame_equal(comun,comun2,check_exact=True)
    filas=[];umbrales={}
    for n,s in a.items():
        s.to_csv(out/f'puntajes_{n}.csv',float_format='%.17g',index_label='dia_utc')
        vals=s.to_numpy()[comun.to_numpy()];umbrales[n]={}
        for punto,fa in [('p99',.01),('p99.9',.001)]:
            u=umbral_falsas_alarmas(vals,fa);assert u==umbral_falsas_alarmas(b[n].to_numpy()[comun.to_numpy()],fa)
            alertas=int((vals>u).sum());umbrales[n][punto]=u
            filas.append(dict(detector=n,punto=punto,umbral=u,casos=len(vals),alertas=alertas,tasa=alertas/len(vals)))
    for n,s in ha.items():s.to_parquet(out/f'horas_{n}.parquet')
    p95.rename('p95_abs_residuo_ug_m3').to_csv(out/'p95_v4.csv',index_label='estacion',float_format='%.17g')
    comun.to_csv(out/'mascara_comun.csv',index_label='dia_utc')
    pd.DataFrame(filas).to_csv(out/'resumen.csv',index=False,float_format='%.17g')
    registro=dict(igual=True,calibracion=True,anio=2017,casos=4536,umbrales=umbrales,
                   origen='Modelos cargados de disco; sin reentrenamiento',tensorflow=tf.__version__,keras=tf.keras.__version__,
                   numpy=np.__version__,sha256_paquete=sha(d/'registro_paquete.json'),
                   modelos={f.name:sha(f) for f in (d/'modelos').glob('*.keras')},sha256_p95_v4=sha(out/'p95_v4.csv'))
    (out/'congelado.json').write_text(json.dumps(registro,ensure_ascii=False,indent=2)+'\n')
    archivos={f.name:sha(f) for f in out.iterdir() if f.is_file()}
    (out/'completo.json').write_text(json.dumps(dict(sha256=archivos),indent=2)+'\n')
    print(pd.DataFrame(filas).to_string(index=False),flush=True)


if __name__=='__main__':main()
