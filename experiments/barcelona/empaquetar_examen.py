"""Empaqueta examen autorizado sin modificar arrays: base + parches exactos."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def indices_iguales(a,b):
    """Compara instantes UTC, tolerando sólo representación us/ns, no desfases."""
    if a.tz is None or b.tz is None:return False
    return a.tz_convert('UTC').as_unit('ns').equals(b.tz_convert('UTC').as_unit('ns'))


def firma(a):
    a=np.ascontiguousarray(a)
    return dict(shape=list(a.shape),dtype=str(a.dtype),sha256=hashlib.sha256(a.tobytes()).hexdigest())


def parche(a,b):
    a,b=np.ascontiguousarray(a),np.ascontiguousarray(b)
    assert a.shape==b.shape and a.dtype==b.dtype
    tipo=np.dtype('u'+str(a.dtype.itemsize))
    pos=np.flatnonzero(a.view(tipo).ravel()!=b.view(tipo).ravel()).astype('int32')
    val=a.ravel()[pos].copy()
    c=b.copy();c.ravel()[pos]=val
    assert firma(c)==firma(a)
    return pos,val


def main():
    base=ROOT/'results/barcelona_paraad';out=base/'examen_colab_2018_2019'
    stage=out/'paquete';ent=stage/'entrada';ent.mkdir(parents=True,exist_ok=False)
    w=base/'ventanas_v1';a=base/'ataques_proporcionales_v1';cal=base/'calibracion_2017_colab'
    assert json.loads((cal/'verificacion_final.json').read_text())['igual']
    globalv=pd.read_parquet(w/'valores.parquet')
    globalb=pd.read_parquet(w/'perfiles_causales.parquet')
    clock=pd.read_parquet(w/'reloj.parquet');dias=pd.read_parquet(w/'estacion_dias.parquet')
    ml=pd.read_parquet(w/'horas_validas_l0.parquet');mv=pd.read_parquet(w/'horas_validas_v4.parquet')
    z=np.load(w/'z_definitivo.npy',mmap_mode='r');F=np.load(w/'l0_features_definitivo.npy',mmap_mode='r')
    info={};bases={}
    for ano in [2017,2018,2019]:
        start=pd.Timestamp(f'{ano}-01-01',tz='UTC');end=pd.Timestamp(f'{ano+1}-01-01',tz='UTC')
        p0=max(0,int(globalv.index.searchsorted(start))-24);p1=int(globalv.index.searchsorted(end))
        sl=slice(p0,p1);idx=globalv.index[sl]
        arrays=dict(v=globalv.iloc[sl].to_numpy('float64'),b=globalb.iloc[sl].to_numpy('float64'),
                    z=np.asarray(z[sl]),F=np.asarray(F[sl]),
                    valid_l0=ml.iloc[sl].to_numpy(bool),valid_v4=mv.iloc[sl].to_numpy(bool),
                    hora=clock[['hora_sin','hora_cos']].iloc[sl].to_numpy('float32'))
        arrays={n:np.ascontiguousarray(x) for n,x in arrays.items()}
        np.savez_compressed(ent/f'base_{ano}.npz',**arrays)
        pd.DataFrame(index=idx).to_parquet(ent/f'indice_{ano}.parquet')
        sd=dias[dias.dia_utc.dt.year==ano].copy();sd['inicio_pos']-=p0;sd['fin_pos']-=p0
        sd.to_parquet(ent/f'dias_{ano}.parquet',index=False)
        info[str(ano)]=dict(offset=p0,arrays={n:firma(x) for n,x in arrays.items()},casos=int(sd.comun.sum()))
        bases[ano]=(arrays,idx,sd)
    unidades=[]
    for carpeta in sorted(a.glob('*201[89]_[0-9][0-9]')):
        ano=2018 if carpeta.name.startswith('prueba') else 2019
        ref,idx,sd=bases[ano]
        for delta in [100,50,20,10,5]:
            p=carpeta/f'd{delta}'
            original=json.loads((p/'completo.json').read_text())
            for n,h in original['sha256_salidas'].items():assert sha(p/n)==h
            v=pd.read_parquet(p/'valores_alterados.parquet');assert v.index.equals(idx)
            arrays=dict(v=v.to_numpy('float64'),b=pd.read_parquet(p/'perfiles_causales.parquet').to_numpy('float64'),
                        z=np.load(p/'z.npy'),F=np.load(p/'l0_features.npy'))
            patch={};firmas={}
            for n,x in arrays.items():
                patch[n+'_i'],patch[n+'_x']=parche(x,ref[n]);firmas[n]=firma(x)
            nombre=f'{carpeta.name}_d{delta}'
            np.savez_compressed(ent/f'{nombre}.npz',**patch)
            labels=pd.read_parquet(p/'estacion_dias.parquet')
            label=labels.pivot(index='dia_utc',columns='estacion',values='etiqueta').reindex(columns=globalv.columns).to_numpy(bool)
            labels2=sd.pivot(index='dia_utc',columns='estacion',values='comun').reindex(columns=globalv.columns)
            assert int(labels2.to_numpy().sum())==info[str(ano)]['casos']
            np.save(ent/f'{nombre}_y.npy',label,allow_pickle=False)
            unidades.append(dict(nombre=nombre,ano=ano,plan=carpeta.name,delta=delta,arrays=firmas))
    assert len(unidades)==100
    (ent/'unidades.json').write_text(json.dumps(unidades,indent=2)+'\n')
    (ent/'bases.json').write_text(json.dumps(info,indent=2)+'\n')
    (ent/'codigos.json').write_text(json.dumps(list(globalv.columns))+'\n')
    shutil.copyfile(w/'vecinas.json',ent/'vecinas.json')
    modeldir=ent/'modelos';modeldir.mkdir()
    train=base/'colab_20261029'
    tabla=pd.read_csv(train/'seleccion_modelos_verificada.csv',dtype={'estacion':str})
    for row in tabla.itertuples():
        r=train/row.detector/'recuperado/salidas'/row.detector
        r=(r/row.estacion if row.detector=='v4' else r)/'definitivo/r1/modelo.keras'
        assert sha(r)==row.sha256_modelo
        shutil.copyfile(r,modeldir/(f'v4_{row.estacion}.keras' if row.detector=='v4' else f'{row.detector}.keras'))
    c=cal/'recuperado/salidas/calibracion'
    for n in ['congelado.json','p95_v4.csv']+['puntajes_'+d+'.csv' for d in ['l0','v4','paraad']]:
        shutil.copyfile(c/n,ent/('calibracion_'+n))
    for p in (cal/'paquete').rglob('*.py'):
        rel=p.relative_to(cal/'paquete');dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/rel if (ROOT/rel).exists() else p,dst)
    for n in ['empaquetar_examen.py','evaluar_examen_colab.py']:
        shutil.copyfile(ROOT/'experiments/barcelona'/n,stage/'experiments/barcelona'/n)
    shutil.copyfile(cal/'paquete/requirements.txt',stage/'requirements.txt')
    shutil.copyfile(ROOT/'docs/registro_examen_barcelona_2018_2019.md',ent/'registro_previo.md')
    meta=dict(alcance='Examen autorizado2018–2019 y control limpio2017, sin entrenamiento',
               archivos={str(p.relative_to(stage)):sha(p) for p in sorted(stage.rglob('*')) if p.is_file()})
    (ent/'registro_paquete.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    paquete=out/'examen_barcelona.tar.gz'
    with tarfile.open(paquete,'w:gz') as tar:
        for p in sorted(stage.rglob('*')):
            if p.is_file():tar.add(p,arcname=str(p.relative_to(stage)),recursive=False)
    partes=[]
    with paquete.open('rb') as f:
        i=0
        while b:=f.read(8*1024*1024):
            n=f'examen_parte_{i:03}.bin';(out/n).write_bytes(b)
            partes.append(dict(nombre=n,sha256=hashlib.sha256(b).hexdigest()));i+=1
    (out/'transferencia.json').write_text(json.dumps(dict(bytes=paquete.stat().st_size,sha256=sha(paquete),partes=partes,matrices=102),indent=2)+'\n')
    print((out/'transferencia.json').read_text())


if __name__=='__main__':main()
