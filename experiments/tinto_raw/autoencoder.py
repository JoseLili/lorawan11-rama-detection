"""Experimento registrado en protocolo_autoencoder.md; ejecutar desde raíz."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import sys, json, hashlib, subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.detect.multianual import ESTACIONES
from src.detect.evaluacion_red import umbral_falsas_alarmas
tf.config.threading.set_intra_op_parallelism_threads(2)
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()
OUT = ROOT / 'results/tinto_autoencoder_20261109'
OUT.mkdir(exist_ok=False)
R = ROOT / 'results/tinto_raw_20261109'
source = R/'auditoria1/o3_raw_ppb.csv'
mp = R/'representacion1/completos_32_mapa.csv'
sp = R/'representacion1/completos_escala.csv'
files = [source, mp, sp, Path(__file__), Path(__file__).with_name('protocolo_autoencoder.md')]
(OUT/'fuentes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2))
(OUT/'entorno.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'], text=True))
df = pd.read_csv(source, index_col=0, parse_dates=True)
assert len(df) == 1096*24 and df.index.is_unique
assert (df.index == pd.date_range('2020-01-01', periods=len(df), freq='h')).all()
stations = [s for s in ESTACIONES if s not in ['HGM','XAL']]
raw = np.concatenate([df[s].to_numpy().reshape(-1,24) for s in stations])
meta = pd.DataFrame({'fecha':np.tile(df.index[::24],len(stations)), 'estacion':np.repeat(stations,len(df)//24)})
ok = np.isfinite(raw).all(axis=1)
raw, meta = raw[ok], meta.loc[ok].reset_index(drop=True)
assert len(raw) == 19300
m, sc = pd.read_csv(mp), pd.read_csv(sp)
coords = m[['row','column']].to_numpy(int)
assert len(set(map(tuple, coords))) == 24
def images(values):
    z = (values*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32')
    x = np.zeros((len(z),32,32,1), dtype='float32')
    x[:,coords[:,0],coords[:,1],0] = z
    np.testing.assert_array_equal(x[:,coords[:,0],coords[:,1],0],z)
    return x
x = images(raw)
meta['particion'] = np.where(meta.fecha < '2021-10-01','ajuste',np.where(meta.fecha < '2022-01-01','seleccion','evaluacion'))
meta.to_csv(OUT/'manifiesto.csv', index=False)
np.save(OUT/'originales.npy',x)
indices = coords[:,0]*32+coords[:,1]
@keras.utils.register_keras_serializable(package='TINTO')
def occupied_mse(y, pred):
    a = tf.gather(tf.reshape(y,(-1,1024)),indices,axis=1)
    b = tf.gather(tf.reshape(pred,(-1,1024)),indices,axis=1)
    return tf.reduce_mean(tf.square(a-b),axis=1)
def dataset(a, shuffle=False):
    d = tf.data.Dataset.from_tensor_slices((a,a))
    if shuffle: d = d.shuffle(len(a),seed=42)
    opt = tf.data.Options(); opt.threading.private_threadpool_size=1
    return d.batch(128).with_options(opt)
def scores(model,a):
    return np.concatenate([occupied_mse(b,model(b,training=False)).numpy() for b,_ in dataset(a)])
train = x[meta.particion.eq('ajuste')]; val = x[meta.particion.eq('seleccion')]
ev = meta.particion.eq('evaluacion').to_numpy(); clean = x[ev]
results=[]; weights=[]; histories=[]; predictions=[]
for run in [1,2]:
    folder=OUT/f'corrida{run}'; folder.mkdir()
    keras.backend.clear_session(); keras.utils.set_random_seed(42)
    L=keras.layers
    model=keras.Sequential([L.Input((32,32,1)),L.Conv2D(8,3,padding='same',activation='relu'),L.MaxPool2D(),L.Conv2D(16,3,padding='same',activation='relu'),L.MaxPool2D(),L.Flatten(),L.Dense(8),L.Dense(1024,activation='relu'),L.Reshape((8,8,16)),L.UpSampling2D(),L.Conv2D(8,3,padding='same',activation='relu'),L.UpSampling2D(),L.Conv2D(1,3,padding='same')])
    model.compile(optimizer=keras.optimizers.Adam(.001),loss=occupied_mse)
    hist=model.fit(dataset(train,True),validation_data=dataset(val),epochs=30,callbacks=[keras.callbacks.EarlyStopping(monitor='val_loss',patience=5,restore_best_weights=True)],verbose=2)
    pd.DataFrame(hist.history).to_csv(folder/'historia.csv',index=False)
    model.save(folder/'modelo.keras'); weights.append(model.get_weights()); histories.append(hist.history)
    base=scores(model,clean); predictions.append(base)
    table=meta.loc[ev,['fecha','estacion']].reset_index(drop=True); table['original']=base
    for factor in [1.2,1/1.2,1.5,1/1.5,2.,.5]:
        attacked=scores(model,images(raw[ev]*factor)); table[f'factor_{factor:.6f}']=attacked
        y=np.r_[np.zeros(len(base)),np.ones(len(base))]; score=np.r_[base,attacked]
        for rate in [.01,.001]:
            threshold=umbral_falsas_alarmas(base,rate); pred=score>threshold
            results.append(dict(corrida=run,factor=factor,tasa_objetivo=rate,umbral=threshold,falsa_alarma=float(np.mean(base>threshold)),recall=recall_score(y,pred),precision=precision_score(y,pred,zero_division=0),f1=f1_score(y,pred),roc_auc=roc_auc_score(y,score),ap=average_precision_score(y,score),mejor_epoca=int(np.argmin(hist.history['val_loss'])+1),epocas=len(hist.history['loss']),parametros=model.count_params()))
    table.to_csv(folder/'scores.csv',index=False)
pd.DataFrame(results).to_csv(OUT/'metricas.csv',index=False)
repro=dict(pesos_identicos=all(np.array_equal(a,b) for a,b in zip(*weights)),historias_identicas=histories[0]==histories[1],scores_identicos=np.array_equal(*predictions))
(OUT/'reproducibilidad.json').write_text(json.dumps(repro,indent=2))
print(meta.groupby('particion').size().to_string()); print(pd.DataFrame(results).to_string(index=False)); print(repro)
