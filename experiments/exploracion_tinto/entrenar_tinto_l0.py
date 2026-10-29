"""Preparar y entrenar una CNN TINTO-PCA con asignación única, solo selección.

Subcomandos separados: preparar y entrenar. No calibra ni abre años de examen.
"""
import os
os.environ.setdefault('CUDA_VISIBLE_DEVICES','-1')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS','0')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','3')
import argparse
import gzip
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'experiments/anomalias_red'))
HERE=Path(__file__).resolve().parent
CFG=HERE/'configuracion_entrenamiento_v1.json'


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def write(p,obj):
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def load_config():
    c=json.loads(CFG.read_text())
    assert c['delta_pct']==50 and c['columnas']==408 and c['lado']==32
    return c


def preparar(out,prueba):
    from entrenar_lstm_local import ejemplos
    from entrenar_lstm_sup import leer, parametros_vecinas, SELECCION, VALIDACION
    from diagnostico_variantes_2022 import posiciones
    from generar_planes import alterables_v4
    from src.detect import evaluacion_red as ev, estacion_dia as ed, lstm_local as ll
    out.mkdir(parents=True)
    c=load_config()
    clean,clean_sha=leer('limpia_2020_2022')
    assert clean.index.min().year==2020 and clean.index.max().year==2022
    _,sigma=ev.normalizacion(clean)
    targets=alterables_v4()
    stations=ev.estaciones_de(clean)
    par=parametros_vecinas('a14',clean.loc[SELECCION[0]:SELECCION[1]],sigma,'media')
    positions={'tr':posiciones(clean.index,*SELECCION),'va':posiciones(clean.index,*VALIDACION)}
    calendars=list(range(1,3 if prueba else 21))
    counts={'tr':len(calendars)*31*(min(8,len(positions['tr'])//8) if prueba else len(positions['tr'])//8),
            'va':(1 if prueba else 10)*31*(min(8,len(positions['va'])//8) if prueba else len(positions['va'])//8)}
    if not prueba:
        assert counts=={'tr':1357800,'va':339450}
    write(out/'configuracion_preparacion.json',dict(configuracion=c,prueba=prueba,conteos=counts,
        sha256_config=sha(CFG),sha256_codigo=sha(Path(__file__)),sha256_limpia=clean_sha,
        representacion_congelada={k:sha(ROOT/c[k]) for k in ['mapa','escalador']},
        nota='Caché X crudo L0 float32 por bloques; imágenes solo al formar lotes. Preparación no entrena.'))
    arrays={split:(np.lib.format.open_memmap(out/f'X_{split}.npy',mode='w+',dtype=np.float32,shape=(n,408)),
                   np.lib.format.open_memmap(out/f'y_{split}.npy',mode='w+',dtype=np.float32,shape=(n,))) for split,n in counts.items()}
    offsets={s:0 for s in counts}; positives={s:0 for s in counts}
    hx={s:hashlib.sha256() for s in counts};hy={s:hashlib.sha256() for s in counts}
    streams={};raws=[];zips=[]
    for split in counts:
        f=open(out/f'manifiesto_{split}.csv.gz','wb');raws.append(f)
        z=gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='');zips.append(z)
        streams[split]=io.TextIOWrapper(z,encoding='utf-8',newline='')
    sources={}
    try:
        for number in calendars:
            calendar=f'entrenamiento_{number:02d}'
            x,sources[calendar]=leer(f'{calendar}_d50')
            assert x.index.equals(clean.index)
            F=ev.entradas_de('vecinas',x,None,sigma,par)
            Y=ed.etiquetas_por_hora(x,targets)
            for split in ['tr','va']:
                if split=='va' and number>(1 if prueba else 10):
                    continue
                usage='seleccion' if split=='tr' else 'validacion'
                p=positions[split]
                # La ruta original L0 permite verificar igual conjunto y orden.
                Xref,yref=ejemplos(F,Y,p,8,usage,number,stations,par.vecinas,targets)
                keep=[];rows=[];start=0
                for j,target in enumerate(targets):
                    selected=ll.muestra(p,8,usage,number,j)
                    take=np.linspace(0,len(selected)-1,min(8,len(selected)),dtype=int) if prueba else np.arange(len(selected))
                    t=selected[take]
                    np.testing.assert_array_equal(Xref[start+take],ll.ventanas_locales(F,stations,par.vecinas,target,t))
                    keep.extend((start+take).tolist())
                    rows.append(pd.DataFrame({'calendario':calendar,'objetivo':target,'hora_final':x.index[t],
                        'posicion_matriz':t,'etiqueta':Y[target].to_numpy()[t].astype(int)}))
                    start+=len(selected)
                a=np.ascontiguousarray(Xref[keep].reshape(-1,408));b=np.ascontiguousarray(yref[keep])
                assert np.isfinite(a).all() and np.isin(b,[0,1]).all()
                lo=offsets[split];hi=lo+len(b)
                arrays[split][0][lo:hi]=a;arrays[split][1][lo:hi]=b
                hx[split].update(a.tobytes());hy[split].update(b.tobytes())
                pd.concat(rows,ignore_index=True).to_csv(streams[split],index=False,header=(lo==0))
                positives[split]+=int(b.sum());offsets[split]=hi
                del Xref,yref,a,b
            print(f'{calendar}: {offsets}',flush=True)
    finally:
        for f in streams.values(): f.close()
        for f in raws: f.close()
    assert offsets==counts
    for a,b in arrays.values(): a.flush();b.flush()
    if not prueba:
        audit=json.loads((ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1/verificaciones.json').read_text())
        assert hx['tr'].hexdigest()==audit['sha256_X_entrenamiento_en_orden']
        assert hy['tr'].hexdigest()==audit['sha256_y_entrenamiento_en_orden']
    ready=dict(prueba=prueba,conteos=counts,positivas=positives,sha256_fuentes=sources,
        sha256_config=sha(CFG),sha256_X={s:h.hexdigest() for s,h in hx.items()},sha256_y={s:h.hexdigest() for s,h in hy.items()},
        sha256_cache={p.name:sha(p) for p in sorted(out.glob('*.npy'))})
    write(out/'LISTO.json',ready)
    print(json.dumps(ready,indent=2))


def entrenar(cache,out):
    import tensorflow as tf
    from tensorflow import keras
    from src.detect.lstm import fijar_semilla
    c=load_config()
    ready=json.loads((cache/'LISTO.json').read_text())
    assert ready['sha256_config']==sha(CFG),'La configuración cambió desde preparar la caché'
    for name,h in ready['sha256_cache'].items():
        assert sha(cache/name)==h, f'Caché alterada: {name}'
    prep=json.loads((cache/'configuracion_preparacion.json').read_text())
    for key,h in prep['representacion_congelada'].items():
        assert sha(ROOT/c[key])==h,'Mapa o escalador alterado'
    mapping=pd.read_csv(ROOT/c['mapa']);scaler=pd.read_csv(ROOT/c['escalador'])
    assert mapping.feature.tolist()==scaler.feature.tolist() and len(mapping)==408
    rc=mapping[['row','column']].to_numpy(dtype=int)
    assert len(np.unique(rc,axis=0))==408 and rc.min()>=0 and rc.max()<32
    arrays={s:(np.load(cache/f'X_{s}.npy',mmap_mode='r'),np.load(cache/f'y_{s}.npy',mmap_mode='r')) for s in ['tr','va']}
    def encode(raw):
        scaled=(raw.astype(np.float64)*scaler.scale.to_numpy()+scaler.offset.to_numpy()).astype(np.float32)
        images=np.zeros((len(raw),32,32,1),dtype=np.float32)
        images[:,rc[:,0],rc[:,1],0]=scaled
        np.testing.assert_array_equal(images[:,rc[:,0],rc[:,1],0],scaled)
        assert np.isfinite(images).all()
        return images
    epochs=2 if ready['prueba'] else c['max_epocas']
    out.mkdir(parents=True)
    write(out/'configuracion_previa.json',dict(configuracion=c,prueba=ready['prueba'],epocas_maximas=epochs,
        sha256_cache_listo=sha(cache/'LISTO.json'),sha256_codigo=sha(Path(__file__)),
        runtime_CPU={k:os.environ.get(k) for k in ['TF_ENABLE_ONEDNN_OPTS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS','CUDA_VISIBLE_DEVICES']},
        versiones={p:importlib.metadata.version(p) for p in ['tensorflow','keras-nightly','numpy','pandas']}))
    class Batches(keras.utils.PyDataset):
        def __init__(self,split):
            super().__init__(workers=1,use_multiprocessing=False,max_queue_size=1)
            self.x,self.y=arrays[split];self.split=split;self.epoch=0;self.order=np.arange(len(self.y))
            self.shuffle()
        def shuffle(self):
            if self.split=='tr':
                self.order=np.random.default_rng([42,29,2,self.epoch]).permutation(len(self.y))
        def __len__(self):return (len(self.y)+c['batch']-1)//c['batch']
        def __getitem__(self,i):
            ids=self.order[i*c['batch']:(i+1)*c['batch']]
            return encode(self.x[ids]),np.asarray(self.y[ids])
        def on_epoch_end(self):self.epoch+=1;self.shuffle()
    train,valid=Batches('tr'),Batches('va')
    def dataset(batches,training):
        def gen():
            for i in range(len(batches)): yield batches[i]
            if training: batches.on_epoch_end()
        opt=tf.data.Options();opt.threading.private_threadpool_size=1;opt.threading.max_intra_op_parallelism=1
        opt.experimental_deterministic=True
        return tf.data.Dataset.from_generator(gen,output_signature=(tf.TensorSpec((None,32,32,1),tf.float32),tf.TensorSpec((None,),tf.float32))).with_options(opt).repeat().prefetch(1)
    # Ejemplo de conversión y etiqueta para revisión, separado del manifiesto.
    probe=encode(arrays['tr'][0][:64]);np.save(out/'imagenes_control.npy',probe)
    np.save(out/'etiquetas_control.npy',np.asarray(arrays['tr'][1][:64]))
    keras.backend.clear_session();fijar_semilla(42)
    model=keras.Sequential([keras.layers.Input((32,32,1)),keras.layers.Conv2D(8,3,padding='same',activation='relu'),
        keras.layers.MaxPool2D(2),keras.layers.Conv2D(16,3,padding='same',activation='relu'),keras.layers.MaxPool2D(2),
        keras.layers.Flatten(),keras.layers.Dense(32,activation='relu'),keras.layers.Dropout(.2),keras.layers.Dense(1,activation='sigmoid')])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=.001),loss='binary_crossentropy')
    assert model.count_params()==34081
    stop=keras.callbacks.EarlyStopping(monitor='val_loss',patience=8,min_delta=0,restore_best_weights=True)
    class ContarLotes(keras.callbacks.Callback):
        def on_train_begin(self,logs=None): self.start=time.perf_counter();self.epoch=0
        def progress(self,fase,lote,total):
            write(out/'progreso.json',dict(fase=fase,epoca=self.epoch+1,lote=lote,lotes_total=total,
                segundos=time.perf_counter()-self.start))
        def on_epoch_begin(self,epoch,logs=None):
            self.n=0;self.epoch=epoch;self.progress('entrenamiento',0,len(train))
        def on_train_batch_end(self,batch,logs=None):
            self.n+=1
            if self.n%512==0 or self.n==len(train):self.progress('entrenamiento',self.n,len(train))
        def on_test_batch_end(self,batch,logs=None):
            if (batch+1)%512==0 or batch+1==len(valid):self.progress('validacion',batch+1,len(valid))
        def on_epoch_end(self,epoch,logs=None):
            assert self.n==len(train), 'Faltaron lotes en una época'
            self.progress('epoca_completa',self.n,len(train))
    checkpoint=keras.callbacks.ModelCheckpoint(out/'mejor_hasta_ahora.keras',monitor='val_loss',save_best_only=True)
    logger=keras.callbacks.CSVLogger(out/'historia_en_curso.csv')
    fijar_semilla(42)
    history=model.fit(dataset(train,True),validation_data=dataset(valid,False),epochs=epochs,
        steps_per_epoch=len(train),validation_steps=len(valid),callbacks=[stop,ContarLotes(),checkpoint,logger],verbose=2)
    hist=pd.DataFrame(history.history);hist.index=pd.RangeIndex(1,len(hist)+1,name='epoca')
    hist.to_csv(out/'historia.csv');model.save(out/'modelo_seleccion.keras')
    before=model(probe,training=False).numpy()
    loaded=keras.models.load_model(out/'modelo_seleccion.keras',compile=False)
    np.testing.assert_array_equal(before,loaded(probe,training=False).numpy())
    np.save(out/'probabilidades_control.npy',before)
    write(out/'resultado.json',dict(prueba=ready['prueba'],origen='CNN recién entrenada; recarga verificada',
        E=int(hist.val_loss.to_numpy().argmin())+1,epocas=len(hist),parametros=model.count_params(),
        pesos_sha256=hashlib.sha256(b''.join(a.tobytes() for a in model.get_weights())).hexdigest(),
        recarga_identica=True,alcance='Solo selección; sin p99/p99.9, sin F1 ni examen. --prueba no es un resultado científico.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='accion',required=True)
    a=sub.add_parser('preparar');a.add_argument('--salida',type=Path,required=True);a.add_argument('--prueba',action='store_true')
    a=sub.add_parser('entrenar');a.add_argument('--cache',type=Path,required=True);a.add_argument('--salida',type=Path,required=True)
    args=p.parse_args()
    if args.salida.exists():p.error('Usa una carpeta nueva; no se sobrescriben resultados.')
    if args.accion=='preparar':preparar(args.salida,args.prueba)
    else:entrenar(args.cache,args.salida)
