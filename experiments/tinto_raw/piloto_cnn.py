"""Piloto acotado CNN estación-día raw. Sin selección ni examen."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['TF_ENABLE_ONEDNN_OPTS']='0'
os.environ['TF_NUM_INTRAOP_THREADS']='2';os.environ['TF_NUM_INTEROP_THREADS']='1';os.environ['TF_CPP_MIN_LOG_LEVEL']='3'
import sys,time,json,argparse,hashlib,resource
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.detect.multianual import ESTACIONES
from sklearn.metrics import f1_score,precision_score,recall_score,accuracy_score,roc_auc_score,average_precision_score

def main(out):
 out.mkdir(parents=True,exist_ok=False);t=time.perf_counter()
 r=ROOT/'results/tinto_raw_20261109';source=r/'auditoria1/o3_raw_ppb.csv';mp=r/'representacion1/completos_32_mapa.csv';sp=r/'representacion1/completos_escala.csv'
 df=pd.read_csv(source,index_col=0,parse_dates=True);stations=[s for s in ESTACIONES if s not in ['XAL','HGM']]
 raw=np.concatenate([df[s].to_numpy().reshape(-1,24) for s in stations]);dates=np.tile(df.index[::24].to_numpy(),len(stations));names=np.repeat(stations,len(df)//24);complete=np.isfinite(raw).all(axis=1)
 m=pd.read_csv(mp);sc=pd.read_csv(sp);coords=m[['row','column']].to_numpy(int);assert len(set(map(tuple,coords)))==24
 (out/'configuracion.json').write_text(json.dumps(dict(epocas=5,semilla=42,batch=64,umbral=.5,delta=.5,fuentes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,mp,sp,Path(__file__)]}),indent=2)+'\n')
 arrays={}
 for split,n,tag in [('ajuste',1024,1),('validacion',256,2)]:
  rng=np.random.default_rng([42,1109,tag]);year=pd.DatetimeIndex(dates).year;eligible=np.flatnonzero(complete&((year<2022) if tag==1 else (year==2022)))
  ids=np.sort(rng.choice(eligible,n,replace=False));sign=rng.choice([-1,1],n);a=raw[ids];b=np.where(sign[:,None]>0,a*1.5,a/1.5);assert np.all(np.any(a!=b,axis=1))
  val=np.concatenate([a,b]);y=np.repeat([0.,1.],n).astype(np.float32)
  z=(val*sc.scale.to_numpy()+sc.offset.to_numpy()).astype(np.float32);im=np.zeros((2*n,32,32,1),np.float32);im[:,coords[:,0],coords[:,1],0]=z;np.testing.assert_array_equal(im[:,coords[:,0],coords[:,1],0],z)
  manifest=pd.DataFrame({'base_id':np.tile(ids,2),'fecha':np.tile(dates[ids],2),'estacion':np.tile(names[ids],2),'etiqueta':y.astype(int),'signo':np.concatenate([np.zeros(n,int),sign])});manifest.to_csv(out/f'{split}_manifiesto.csv',index=False)
  np.save(out/f'{split}_y.npy',y);arrays[split]=(im,y)
 prep=time.perf_counter()-t
 import tensorflow as tf
 from tensorflow import keras
 from src.detect.lstm import fijar_semilla
 def ds(x,y,shuffle):
  options=tf.data.Options();options.threading.private_threadpool_size=1;options.threading.max_intra_op_parallelism=1;options.experimental_deterministic=True
  d=tf.data.Dataset.from_tensor_slices((x,y))
  if shuffle:d=d.shuffle(len(y),seed=42,reshuffle_each_iteration=True)
  return d.batch(64).with_options(options)
 train=ds(*arrays['ajuste'],True);valid=ds(*arrays['validacion'],False)
 keras.backend.clear_session();fijar_semilla(42)
 L=keras.layers
 model=keras.Sequential([L.Input((32,32,1)),L.Conv2D(8,3,padding='same',activation='relu'),L.MaxPool2D(2),L.Conv2D(16,3,padding='same',activation='relu'),L.MaxPool2D(2),L.Flatten(),L.Dense(32,activation='relu'),L.Dropout(.2),L.Dense(1,activation='sigmoid')])
 model.compile(optimizer=keras.optimizers.Adam(.001),loss='binary_crossentropy')
 w0=[w.copy() for w in model.get_weights()]
 t=time.perf_counter();fijar_semilla(42)
 hist=model.fit(train,validation_data=valid,epochs=5,verbose=2)
 elapsed=time.perf_counter()-t;pd.DataFrame(hist.history).to_csv(out/'historia.csv',index=False)
 model.save(out/'modelo_final.keras');np.savez(out/'pesos.npz',*model.get_weights())
 t=time.perf_counter();p=np.concatenate([model(x,training=False).numpy().reshape(-1) for x,_ in valid]);inference=time.perf_counter()-t
 y=arrays['validacion'][1];pred=p>.5;np.save(out/'probabilidades.npy',p)
 metrics=dict(f1=float(f1_score(y,pred,zero_division=0)),precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred)),exactitud=float(accuracy_score(y,pred)),roc_auc=float(roc_auc_score(y,p)),average_precision=float(average_precision_score(y,p)),positivos_predichos=int(pred.sum()),f1_siempre_positivo=float(f1_score(y,np.ones(len(y)))),ap_prior=.5,roc_auc_constante=.5)
 report=dict(modelo='CNN recién entrenada; checkpoint final época5',parametros=model.count_params(),ajuste_imagenes=2048,validacion_imagenes=512,memoria_tensores_MiB=sum(x.nbytes for x,y in arrays.values())/2**20,preparacion_segundos=prep,entrenamiento_segundos=elapsed,inferencia_512_segundos=inference,rss_max_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,pesos_cambiaron=any(not np.array_equal(a,b) for a,b in zip(w0,model.get_weights())),tensorflow=tf.__version__,keras=keras.__version__,metricas=metrics)
 (out/'resultado.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);main(p.parse_args().salida)
