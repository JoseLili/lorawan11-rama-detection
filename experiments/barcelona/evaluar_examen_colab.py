"""Examen congelado CPU; produce puntajes duplicados, no selecciona modelos."""
import os
for k,v in {'CUDA_VISIBLE_DEVICES':'-1','TF_ENABLE_ONEDNN_OPTS':'0','TF_DETERMINISTIC_OPS':'1',
            'TF_NUM_INTRAOP_THREADS':'1','TF_NUM_INTEROP_THREADS':'1','OMP_NUM_THREADS':'1'}.items():os.environ[k]=v
import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import tensorflow as tf

from experiments.barcelona.calibrar_2017_colab import cargar,predecir
from experiments.barcelona.empaquetar_examen import firma,indices_iguales
from experiments.barcelona.preparar_ventanas import ventana_l0,ventana_v4,bloque_paraad

ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def guardar(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(p)


def leer_base(d,ano,codes):
    arrays={n:x for n,x in np.load(d/f'base_{ano}.npz').items()}
    meta=json.loads((d/'bases.json').read_text())[str(ano)]
    for n,x in arrays.items():assert firma(x)==meta['arrays'][n]
    idx=pd.read_parquet(d/f'indice_{ano}.parquet').index
    sd=pd.read_parquet(d/f'dias_{ano}.parquet')
    comun=sd.pivot(index='dia_utc',columns='estacion',values='comun').reindex(columns=codes)
    assert int(comun.to_numpy().sum())==meta['casos']
    return arrays,idx,sd,comun


def reconstruir(d,u,base):
    patch=np.load(d/(u['nombre']+'.npz'))
    arrays=dict(base)
    for n,meta in u['arrays'].items():
        x=base[n].copy();x.ravel()[patch[n+'_i']]=patch[n+'_x']
        assert firma(x)==meta,(u['nombre'],n)
        arrays[n]=x
    assert np.array_equal(np.isnan(arrays['v']),np.isnan(base['v']))
    return arrays


def inferir(detector,modelos,a,idx,sd,comun,codes,vec,p95):
    ano=int(comun.index[0].year);cal=idx.year==ano
    if detector=='l0':
        h=pd.DataFrame(np.nan,index=idx[cal],columns=codes)
        for j,s in enumerate(codes):
            pos=np.flatnonzero(a['valid_l0'][:,j] & cal)
            X=ventana_l0(a['F'],codes,vec,s,pos)
            val=predecir(modelos['l0'],X).ravel().astype('float64');assert np.isfinite(val).all()
            h.loc[idx[pos],s]=val
        score=h.groupby(h.index.normalize()).mean().where(h.notna().groupby(h.index.normalize()).sum()>=12)
    elif detector=='v4':
        h=pd.DataFrame(np.nan,index=idx[cal],columns=codes)
        for j,s in enumerate(codes):
            pos=np.flatnonzero(a['valid_v4'][:,j] & cal)
            X=ventana_v4(a['z'],np.isfinite(a['v']).astype('float32'),a['hora'],j,pos)
            cor=predecir(modelos[s],X).ravel().astype('float64')
            val=a['v'][pos,j]-a['b'][pos,j]-cor;assert np.isfinite(val).all()
            h.loc[idx[pos],s]=val
        score=(h.groupby(h.index.normalize()).mean().abs()/p95).where(h.notna().groupby(h.index.normalize()).sum()>=12)
    else:
        pos=sd[sd.bloque_seguro].inicio_pos.drop_duplicates().to_numpy()
        X,m=bloque_paraad(a['z'],np.isfinite(a['v']).astype('float32'),pos)
        rec=predecir(modelos['paraad'],X)
        n=m.sum(axis=2);err=(np.abs(X.astype('float64')-rec)*m).sum(axis=2)
        val=np.divide(err,n,out=np.full(err.shape,np.nan),where=n>=12)
        score=pd.DataFrame(val,index=idx[pos].normalize(),columns=codes)
    score=score.reindex(index=comun.index,columns=codes).where(comun)
    assert np.isfinite(score.to_numpy()[comun.to_numpy()]).all()
    return score


def unidad(out,nombre,detector,modelos,a,idx,sd,comun,codes,vec,p95,meta=None):
    carpeta=out/nombre;listo=carpeta/'completo.json'
    if listo.exists():
        r=json.loads(listo.read_text())
        for n,h in r['sha256'].items():assert sha(carpeta/n)==h
        return np.load(carpeta/'puntajes.npy')
    previo=None
    for r in (1,2):
        guardar(out/'progreso.json',dict(unidad=nombre,repeticion=r,detector=detector))
        s=inferir(detector,modelos,a,idx,sd,comun,codes,vec,p95)
        if previo is not None:pd.testing.assert_frame_equal(previo,s,check_exact=True)
        previo=s
    carpeta.mkdir(exist_ok=True);np.save(carpeta/'puntajes.npy',s.to_numpy(),allow_pickle=False)
    guardar(carpeta/'datos.json',dict(nombre=nombre,detector=detector,ano=int(comun.index[0].year),
                                     casos=int(comun.to_numpy().sum()),igual=True,unidad=meta))
    guardar(listo,dict(sha256={n:sha(carpeta/n) for n in ['puntajes.npy','datos.json']}))
    print('COMPLETO',detector,nombre,flush=True)
    return s.to_numpy()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--detector',choices=['l0','v4','paraad'],required=True);args=ap.parse_args()
    d=ROOT/'entrada';out=ROOT/'salidas'/args.detector
    assert not tf.config.get_visible_devices('GPU')
    assert tf.__version__=='2.21.0' and tf.keras.__version__=='3.13.2'
    paquete=json.loads((d/'registro_paquete.json').read_text())
    for n,h in paquete['archivos'].items():assert sha(ROOT/n)==h,n
    calib=json.loads((d/'calibracion_congelado.json').read_text())
    for n,h in calib['modelos'].items():assert sha(d/'modelos'/n)==h
    assert sha(d/'calibracion_p95_v4.csv')==calib['sha256_p95_v4']
    codes=json.loads((d/'codigos.json').read_text());vec=json.loads((d/'vecinas.json').read_text())
    p95=pd.read_csv(d/'calibracion_p95_v4.csv',dtype={'estacion':str},float_precision='round_trip').set_index('estacion').iloc[:,0]
    firma_entrada=dict(sha256_paquete=sha(d/'registro_paquete.json'),sha256_script=sha(Path(__file__)),
                       sha256_calibracion=sha(d/'calibracion_congelado.json'),tensorflow=tf.__version__,keras=tf.keras.__version__,
                       numpy=np.__version__,python=platform.python_version(),detector=args.detector,
                       origen='Modelos congelados cargados; sin entrenamiento')
    if (out/'entrada.json').exists():assert json.loads((out/'entrada.json').read_text())==firma_entrada
    else:guardar(out/'entrada.json',firma_entrada)
    modelos={s:cargar(d/f'modelos/v4_{s}.keras') for s in codes} if args.detector=='v4' else {
        args.detector:cargar(d/f'modelos/{args.detector}.keras')}
    arrays,idx,sd,comun=leer_base(d,2017,codes)
    s=unidad(out,'control_2017',args.detector,modelos,arrays,idx,sd,comun,codes,vec,p95)
    ref=pd.read_csv(d/f'calibracion_puntajes_{args.detector}.csv',index_col='dia_utc',parse_dates=['dia_utc'],float_precision='round_trip')
    assert indices_iguales(ref.index,comun.index) and ref.columns.equals(comun.columns)
    m=comun.to_numpy();np.testing.assert_allclose(s[m],ref.to_numpy()[m],rtol=1e-6,atol=1e-6)
    cambios={p:int(((s[m]>u)!=(ref.to_numpy()[m]>u)).sum()) for p,u in calib['umbrales'][args.detector].items()}
    guardar(out/'control_calibracion.json',dict(tolerancia_rtol=1e-6,tolerancia_atol=1e-6,
            maxima_diferencia=float(np.abs(s[m]-ref.to_numpy()[m]).max()),cambios_alertas=cambios,
            nota='No se ajustan los umbrales por diferencias entre VMs'))
    unidades=json.loads((d/'unidades.json').read_text())
    for ano in [2018,2019]:
        base,idx,sd,comun=leer_base(d,ano,codes)
        unidad(out,f'limpio_{ano}',args.detector,modelos,base,idx,sd,comun,codes,vec,p95)
        for u in [x for x in unidades if x['ano']==ano]:
            a=reconstruir(d,u,base)
            unidad(out,u['nombre'],args.detector,modelos,a,idx,sd,comun,codes,vec,p95,meta=u)
    listos=sorted(out.glob('*/completo.json'));assert len(listos)==103
    guardar(out/'congelado.json',dict(igual=True,unidades_examen=102,control2017=True,entrada=firma_entrada,
                 sha256_unidades={str(p.relative_to(out)):sha(p) for p in listos}))


if __name__=='__main__':main()
