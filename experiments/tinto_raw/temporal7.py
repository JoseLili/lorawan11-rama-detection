"""Predicción registrada en protocolo_temporal7.md."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['TF_ENABLE_ONEDNN_OPTS']='0'
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import sys,json,hashlib,subprocess,argparse
from pathlib import Path
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import roc_auc_score,average_precision_score
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.detect.evaluacion_red import umbral_falsas_alarmas
tf.config.threading.set_intra_op_parallelism_threads(2);tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
    base=ROOT/'results/tinto_autoencoder_20261109'; evaluation=ROOT/'results/tinto_ae_12_escenarios'
    coords_path=ROOT/'results/tinto_raw_20261109/representacion1/completos_32_mapa.csv'
    scale_path=coords_path.with_name('completos_escala.csv')
    for folder in [base,evaluation]:
        for name,digest in json.loads((folder/'checksums.json').read_text()).items():
            assert sha(folder/name)==digest,name
    out.mkdir(parents=True,exist_ok=False)
    sources=[base/'originales.npy',base/'manifiesto.csv',evaluation/'scores.csv',evaluation/'lecturas_y_reconstrucciones.npz',coords_path,scale_path,Path(__file__),Path(__file__).with_name('protocolo_temporal7.md')]
    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    (out/'fuentes.json').write_text(json.dumps(source_hashes,indent=2))
    (out/'entorno.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    m=pd.read_csv(base/'manifiesto.csv',parse_dates=['fecha']); lookup={(r.estacion,r.fecha):i for i,r in m.iterrows()}
    ids=[]; histories=[]
    for i,r in m.iterrows():
        keys=[(r.estacion,r.fecha-pd.Timedelta(days=k)) for k in range(7,0,-1)]
        if all(k in lookup for k in keys):ids.append(i);histories.append([lookup[k] for k in keys])
    ids=np.array(ids); hi=np.array(histories); meta=m.iloc[ids].reset_index(drop=True)
    for j in range(7):
        assert (m.iloc[hi[:,j]].estacion.to_numpy()==meta.estacion.to_numpy()).all()
        assert ((meta.fecha.to_numpy()-m.iloc[hi[:,j]].fecha.to_numpy())==np.timedelta64(7-j,'D')).all()
        meta[f'base_tmenos{7-j}']=hi[:,j]
    meta['base_objetivo']=ids;meta.to_csv(out/'manifiesto.csv',index=False)
    meta.groupby(['particion','estacion']).size().rename('n').to_csv(out/'cobertura.csv')
    images=np.load(base/'originales.npy',mmap_mode='r')
    x=np.stack([images[hi[:,j],:,:,0] for j in range(7)],axis=-1); y=np.array(images[ids])
    c=pd.read_csv(coords_path)[['row','column']].to_numpy(int); positions=c[:,0]*32+c[:,1]
    assert len(set(positions))==24 and np.isfinite(x).all()
    def loss(a,b):return tf.reduce_mean(tf.square(tf.gather(tf.reshape(a,(-1,1024)),positions,axis=1)-tf.gather(tf.reshape(b,(-1,1024)),positions,axis=1)),axis=1)
    def data(a,b,shuffle=False):
        d=tf.data.Dataset.from_tensor_slices((a,b));o=tf.data.Options();o.threading.private_threadpool_size=1
        if shuffle:d=d.shuffle(len(a),seed=42)
        return d.batch(32).with_options(o)
    masks={s:meta.particion.eq(s).to_numpy() for s in ['ajuste','seleccion','evaluacion']}
    assert [int(masks[s].sum()) for s in masks]==[139,38,175]
    weights=[];history=[];predictions=[]
    for run in [1,2]:
        folder=out/f'corrida{run}';folder.mkdir();keras.backend.clear_session();keras.utils.set_random_seed(42);L=keras.layers
        model=keras.Sequential([L.Input((32,32,7)),L.Conv2D(8,3,padding='same',activation='relu'),L.MaxPool2D(),L.Conv2D(16,3,padding='same',activation='relu'),L.MaxPool2D(),L.Flatten(),L.Dense(8),L.Dense(1024,activation='relu'),L.Reshape((8,8,16)),L.UpSampling2D(),L.Conv2D(8,3,padding='same',activation='relu'),L.UpSampling2D(),L.Conv2D(1,3,padding='same')])
        model.compile(optimizer=keras.optimizers.Adam(.001),loss=loss)
        a=masks['ajuste'];v=masks['seleccion'];e=masks['evaluacion']
        h=model.fit(data(x[a],y[a],True),validation_data=data(x[v],y[v]),epochs=30,callbacks=[keras.callbacks.EarlyStopping(monitor='val_loss',patience=5,restore_best_weights=True)],verbose=2)
        pd.DataFrame(h.history).to_csv(folder/'historia.csv',index=False)
        # Load for inference without deserializing the custom training loss.
        model.save(folder/'modelo.keras')
        restored=keras.models.load_model(folder/'modelo.keras',compile=False)
        pred=model(x[e],training=False).numpy();np.testing.assert_array_equal(pred,restored(x[e],training=False).numpy())
        predictions.append(pred);weights.append(model.get_weights());history.append(h.history)
        np.save(folder/'prediccion.npy',pred)
        (folder/'configuracion.json').write_text(json.dumps(dict(parametros=model.count_params(),mejor_epoca=int(np.argmin(h.history['val_loss'])+1),epocas=len(h.history['loss'])),indent=2))
    assert all(np.array_equal(a,b) for a,b in zip(*weights));assert history[0]==history[1];np.testing.assert_array_equal(*predictions)
    old=pd.read_csv(evaluation/'scores.csv',parse_dates=['fecha'])
    index=old.set_index(['estacion','fecha']).index.get_indexer(pd.MultiIndex.from_frame(meta.loc[e,['estacion','fecha']]))
    assert (index>=0).all() and len(set(index))==175
    artifacts=np.load(evaluation/'lecturas_y_reconstrucciones.npz');sc=pd.read_csv(scale_path)
    scenarios=[k[:-4] for k in artifacts.files if k.endswith('_ppb') and '_reconstruccion_' not in k]
    pred=predictions[0][:,c[:,0],c[:,1],0];scores={};allrows=[];thresholds=[];n=len(index)
    physical=(pred-sc.offset.to_numpy())/sc.scale.to_numpy();np.save(out/'prediccion_ppb.npy',physical)
    for name in scenarios:
        vals=artifacts[name+'_ppb'][index];z=(vals*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32')
        scores[name]=tf.reduce_mean(tf.square(z-pred),axis=1).numpy()
    np.testing.assert_array_equal((artifacts['original_ppb'][index]*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32'),y[e][:,c[:,0],c[:,1],0])
    for detector,table in [('temporal7',pd.DataFrame(scores)),('autoencoder',old.iloc[index].reset_index(drop=True))]:
        a=table.original.to_numpy()
        for p,rate in [(95,.05),(98,.02),(99,.01),(99.9,.001)]:
            u=umbral_falsas_alarmas(a,rate);fp=int((a>u).sum())
            thresholds.append(dict(detector=detector,percentil=p,umbral=u,n=n,fa_teoricas=n*rate,fa_observadas=fp,tasa_observada=fp/n))
            for name in scenarios:
                if name=='original':continue
                b=table[name].to_numpy();tp=int((b>u).sum());fn=n-tp;tn=n-fp
                labels=np.r_[np.zeros(n),np.ones(n)];s=np.r_[a,b]
                allrows.append(dict(detector=detector,escenario=name,percentil=p,tp=tp,fp=fp,fn=fn,tn=tn,recall=tp/n,precision=tp/(tp+fp) if tp+fp else 0.,f1=2*tp/(2*tp+fp+fn),auc=roc_auc_score(labels,s),ap=average_precision_score(labels,s)))
        pd.concat([meta.loc[e,['fecha','estacion']].reset_index(drop=True),table[scenarios].reset_index(drop=True)],axis=1).to_csv(out/f'scores_{detector}.csv',index=False)
    result=pd.DataFrame(allrows);result.to_csv(out/'metricas.csv',index=False);th=pd.DataFrame(thresholds);th.to_csv(out/'umbrales.csv',index=False)
    for p in [95,98,99,99.9]:
        subset=result[result.percentil.eq(p)].pivot(index='escenario',columns='detector',values=['recall','precision'])
        subset.to_csv(out/f'comparacion_p{p}.csv')
    checks=dict(pesos_identicos=True,historias_identicas=True,predicciones_identicas=True,modelos_recargados_verificados=True,historial_estrictamente_pasado=True,fuentes_intactas=all(sha(ROOT/k)==v for k,v in source_hashes.items()))
    (out/'verificaciones.json').write_text(json.dumps(checks,indent=2));assert checks['fuentes_intactas']
    lines=['# Predicción temporal de siete días','', 'Diagnóstico exploratorio: 139 ajuste, 38 selección, 175 evaluación. Ninguna secuencia elegible en 2020. Dos corridas idénticas; modelos recargados y verificados. Historia original, ataque solo al objetivo.','', '## Recall (%) en soporte común','', '| Escenario | AE p95 | Temporal p95 | AE p99 | Temporal p99 |','|---|---:|---:|---:|---:|']
    for name in scenarios[1:]:
        vals=[result[(result.escenario==name)&(result.detector==d)&(result.percentil==p)].recall.iloc[0]*100 for p in [95,99] for d in ['autoencoder','temporal7']]
        lines.append('| '+name+' | '+' | '.join(f'{v:.2f}' for v in vals)+' |')
    lines+=['','## Falsas alarmas','', '| Detector | Percentil | N | Teóricas | Observadas |','|---|---:|---:|---:|---:|']
    for row in th.itertuples():lines.append(f'| {row.detector} | {row.percentil} | {n} | {row.fa_teoricas:.3f} | {row.fa_observadas} |')
    lines+=['','## Límites','', 'Calibración y evaluación originales reutilizan2022. p99.9 permite cero alertas en175 casos y se apoya en el máximo; no garantiza cero falsas alarmas futuras. Ventanas solapadas, pocas estaciones, sin intervalos de confianza. Pares artificiales50/50. No prueba independiente ni evidencia causal de temporalidad: cambian objetivo, canales y muestra de entrenamiento. Modelo temporal ve139 bases, autoencoder previo10334. Predicción no usa el objetivo; ataques sostenidos que contaminan historia quedan pendientes. No abrir2023–2026.', '', 'Precisión, recall, F1 y conteos completos en metricas.csv (96 filas). Manifiesto registra índices de los siete antecedentes. Archivos originales preservados.']
    (out/'informe.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'checksums.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='checksums.json'},indent=2))
    print('\n'.join(lines),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--salida',required=True,type=Path);main(p.parse_args().salida)
