"""Piloto técnico de TINTO-PCA con asignación única; no evaluación de tesis."""
import os
os.environ.setdefault('CUDA_VISIBLE_DEVICES','-1')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS','0')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','3')
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
AUD=ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1'
MAP=ROOT/'results/exploracion_tinto_2022/prototipos_20261028/corrida1/L0_408/mapa_unico_32.csv'
SCALE=ROOT/'results/exploracion_tinto_2022/hora_compacta_20261028/corrida1/L0_408/escalador.csv'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,obj):
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def ejecutar(out):
    out.mkdir(parents=True)
    config=dict(alcance='Prueba técnica sin validación ni métricas de detección; no modelo definitivo',
        representacion='408 entradas; mapa PCA de TINTO cargado, asignación única propia 32×32; sin difuminado',
        origen_mapa='Ajustado previamente con 19 840 ventanas 2020–2021; no se considera holdout al subconjunto piloto',
        arquitectura=['Input(32,32,1)','Conv2D(8,3,same,relu)','MaxPool2D(2)',
            'Conv2D(16,3,same,relu)','MaxPool2D(2)','Flatten','Dense(32,relu)','Dropout(0.2)','Dense(1,sigmoid)'],
        entrenamiento=dict(semilla=42,epocas=60,batch=64,optimizer='Adam',learning_rate=.001,
            loss='binary_crossentropy',pesos_clase=False,shuffle=True),
        etapas=['64 ejemplos inventados con señal artificial conocida',
            '64 ventanas reales de 2020: 32 positivas y 32 negativas, prueba de memorización'],
        criterio_sintetica='Pérdida final < 0.1 y exactitud de entrenamiento >= 0.95; prueba de funcionamiento, no generalización',
        criterio_real='Pérdidas finitas, pesos cambian y pérdida de entrenamiento final < inicial; no umbrales ni prueba independiente',
        seleccion='Muestreo sin reemplazo con [42,29,0], solo 2020; balance exclusivo del diagnóstico, no del entrenamiento principal',
        sin_ajustes_posteriores='No aumentar épocas ni cambiar arquitectura para hacer pasar el piloto; informar cualquier fallo',
        fuentes={str(p.relative_to(ROOT)):sha(p) for p in [MAP,SCALE,AUD/'X_muestra.npy',AUD/'manifiesto_muestra.csv']},
        codigo=sha(Path(__file__)),versiones={p:importlib.metadata.version(p) for p in ['numpy','pandas','tensorflow','keras-nightly']})
    write(out/'configuracion_previa.json',config)
    mapping=pd.read_csv(MAP)
    scaler=pd.read_csv(SCALE)
    assert mapping.feature.tolist()==scaler.feature.tolist()
    coords=mapping[['row','column']].to_numpy(dtype=int)
    assert len(np.unique(coords,axis=0))==408

    def encode(values):
        values=np.asarray(values,dtype=np.float32)
        images=np.zeros((len(values),32,32,1),dtype=np.float32)
        images[:,coords[:,0],coords[:,1],0]=values
        np.testing.assert_array_equal(images[:,coords[:,0],coords[:,1],0],values)
        return images

    X=np.load(AUD/'X_muestra.npy',allow_pickle=False).reshape(-1,408)
    meta=pd.read_csv(AUD/'manifiesto_muestra.csv')
    rng=np.random.default_rng([42,29,0])
    selected=np.concatenate([rng.choice(meta.index[(meta.hora_final.str[:4]=='2020')&(meta.etiqueta==label)],32,replace=False) for label in [0,1]])
    rng.shuffle(selected)
    manifest=meta.iloc[selected].copy()
    manifest['fila_piloto']=np.arange(64)
    manifest.to_csv(out/'manifiesto_piloto.csv',index=False)
    values=X[selected].astype(np.float64)*scaler.scale.to_numpy()+scaler.offset.to_numpy()
    real=encode(values)
    yreal=manifest.etiqueta.to_numpy(dtype=np.float32)
    assert manifest.hora_final.str[:4].eq('2020').all() and yreal.sum()==32
    # La señal artificial no pretende ser una anomalía RAMA físicamente coherente.
    synrng=np.random.default_rng([42,29,1])
    ysyn=np.tile([0.,1.],32).astype(np.float32)
    synthetic=synrng.uniform(.4,.6,(64,408)).astype(np.float32)
    signal=mapping.feature.str.endswith('_obj_rel').to_numpy()
    assert signal.sum()==24
    synthetic[:,signal]=(.1+.8*ysyn)[:,None]
    invented=encode(synthetic)
    np.save(out/'imagenes_reales_piloto.npy',real)
    np.save(out/'etiquetas_reales_piloto.npy',yreal)
    import tensorflow as tf
    from tensorflow import keras
    from src.detect.lstm import fijar_semilla

    def build():
        layers=keras.layers
        model=keras.Sequential([layers.Input((32,32,1)),layers.Conv2D(8,3,padding='same',activation='relu'),
            layers.MaxPool2D(2),layers.Conv2D(16,3,padding='same',activation='relu'),layers.MaxPool2D(2),
            layers.Flatten(),layers.Dense(32,activation='relu'),layers.Dropout(.2),layers.Dense(1,activation='sigmoid')])
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=.001),loss='binary_crossentropy')
        return model

    stages={}
    times=[]
    for name,images,labels in [('sintetica',invented,ysyn),('real_memorizacion',real,yreal)]:
        folder=out/name
        folder.mkdir()
        options=tf.data.Options()
        options.threading.private_threadpool_size=1
        options.threading.max_intra_op_parallelism=1
        options.experimental_deterministic=True
        data=tf.data.Dataset.from_tensor_slices((images,labels)).shuffle(64,seed=42,reshuffle_each_iteration=True).batch(64).with_options(options)
        keras.backend.clear_session()
        fijar_semilla(42)
        model=build()
        initial_weights=hashlib.sha256(b''.join(v.tobytes() for v in model.get_weights())).hexdigest()
        initial=float(model.evaluate(data,verbose=0))
        epoch_times=[]
        class Timing(keras.callbacks.Callback):
            def on_epoch_begin(self,epoch,logs=None):
                self.start=time.perf_counter()
            def on_epoch_end(self,epoch,logs=None):
                epoch_times.append(time.perf_counter()-self.start)
        fijar_semilla(42)
        started=time.perf_counter()
        history=model.fit(data,epochs=60,verbose=0,callbacks=[Timing()])
        elapsed=time.perf_counter()-started
        final=float(model.evaluate(data,verbose=0))
        probabilities=model(images,training=False).numpy().ravel()
        weights=hashlib.sha256(b''.join(v.tobytes() for v in model.get_weights())).hexdigest()
        accuracy=float(np.mean((probabilities>.5)==labels))
        finite=bool(np.isfinite(history.history['loss']).all() and np.isfinite(probabilities).all())
        passed=finite and weights!=initial_weights and final<initial
        if name=='sintetica':
            passed=passed and final<.1 and accuracy>=.95
        stages[name]=dict(origen='CNN recién entrenada para diagnóstico, no cargada',ejemplos=len(labels),positivas=int(labels.sum()),
            parametros=model.count_params(),perdida_inicial=initial,perdida_final=final,
            exactitud_sobre_los_mismos_ejemplos=accuracy,pesos_cambiaron=weights!=initial_weights,
            valores_finitos=finite,cumple_criterio=bool(passed),sha256_pesos=weights)
        pd.DataFrame(history.history).rename_axis('epoca_desde_cero').to_csv(folder/'historia.csv')
        np.save(folder/'probabilidades_entrenamiento.npy',probabilities)
        model.save(folder/'modelo_piloto.keras')
        median=float(np.median(epoch_times[5:]))
        times.append(dict(etapa=name,segundos_fit=elapsed,mediana_epoca_caliente=median,
            segundos_por_epoca_completa_extrapolados=median*math.ceil(1357800/64)))
        print(name,stages[name],flush=True)
    write(out/'resultados.json',dict(etapas=stages,todos_pasan=all(s['cumple_criterio'] for s in stages.values()),
        advertencia='Exactitud y pérdida calculadas en entrenamiento; no estiman precisión, recall ni rendimiento en datos nuevos.',
        memoria=dict(bytes_imagen_float32=32*32*4,bytes_tensor_completo_1357800=1357800*32*32*4)))
    pd.DataFrame(times).to_csv(out/'tiempos.csv',index=False)
    write(out/'hashes_numericos.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
        if p.is_file() and p.suffix in ['.json','.csv','.npy'] and p.name!='tiempos.csv'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',required=True,type=Path)
    args=parser.parse_args()
    if args.salida.exists():
        parser.error('Usa una carpeta nueva.')
    ejecutar(args.salida)
