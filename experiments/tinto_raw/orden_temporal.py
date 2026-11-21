"""Temporalidad diaria y horaria explícita; protocolo_orden_temporal.md."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['TF_ENABLE_ONEDNN_OPTS']='0';os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
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
    base=ROOT/'results/tinto_autoencoder_20261109';ev=ROOT/'results/tinto_ae_12_escenarios';rawroot=ROOT/'results/tinto_raw_20261109'
    for folder in [base,ev]:
        for k,v in json.loads((folder/'checksums.json').read_text()).items():assert sha(folder/k)==v,k
    out.mkdir(parents=True,exist_ok=False)
    files=[base/'originales.npy',base/'manifiesto.csv',ev/'lecturas_y_reconstrucciones.npz',ev/'scores.csv',rawroot/'auditoria1/o3_raw_ppb.csv',rawroot/'representacion1/completos_32_mapa.csv',rawroot/'representacion1/completos_escala.csv',Path(__file__),Path(__file__).with_name('protocolo_orden_temporal.md')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files};(out/'fuentes.json').write_text(json.dumps(hashes,indent=2))
    (out/'entorno.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    m=pd.read_csv(files[1],parse_dates=['fecha']);lookup={(r.estacion,r.fecha):i for i,r in m.iterrows()};audit=[];ids=[];hist=[]
    for days in [1,2,3,7]:
        eligible=[]
        for i,r in m.iterrows():
            keys=[(r.estacion,r.fecha-pd.Timedelta(days=k)) for k in range(days,0,-1)]
            if all(k in lookup for k in keys):
                eligible.append(i)
                if days==2:ids.append(i);hist.append([lookup[k] for k in keys])
        for split,n in m.iloc[eligible].groupby('particion').size().items():audit.append(dict(dias=days,particion=split,n=int(n)))
    pd.DataFrame(audit).to_csv(out/'cobertura_ventanas.csv',index=False)
    ids=np.array(ids);hi=np.array(hist);meta=m.iloc[ids].reset_index(drop=True)
    meta['indice_tmenos2']=hi[:,0];meta['indice_tmenos1']=hi[:,1];meta['indice_objetivo']=ids
    meta.to_csv(out/'manifiesto.csv',index=False);meta.groupby(['particion','estacion']).size().rename('n').to_csv(out/'cobertura_estaciones.csv')
    image=np.load(files[0],mmap_mode='r');mapping=pd.read_csv(files[5]);scale=pd.read_csv(files[6]);c=mapping[['row','column']].to_numpy(int)
    assert mapping.feature.tolist()==[f'h{h:02}' for h in range(24)]
    assert scale.feature.tolist()==mapping.feature.tolist() and len(set(map(tuple,c)))==24
    xd=np.stack([image[hi[:,j]] for j in range(2)],axis=1)
    hourly=xd[:,:,c[:,0],c[:,1],0];xh=hourly.reshape(-1,48,1)
    y=np.array(image[ids][:,c[:,0],c[:,1],0]);df=pd.read_csv(files[4],index_col=0,parse_dates=True)
    # Audit every input hour against the authoritative exported table and timestamps.
    for i,r in meta.iterrows():
        times=pd.date_range(r.fecha-pd.Timedelta(days=2),periods=48,freq='h')
        assert times[23].hour==23 and times[24].hour==0
        assert (times[24]-times[23])==pd.Timedelta(hours=1) and times[-1]<r.fecha
        assert m.iloc[hi[i,0]].estacion==r.estacion==m.iloc[hi[i,1]].estacion
        for j in range(2):assert m.iloc[hi[i,j]].fecha==times[j*24]
        z=(df.loc[times,r.estacion].to_numpy().reshape(2,24)*scale.scale.to_numpy()+scale.offset.to_numpy()).astype('float32')
        np.testing.assert_array_equal(z.reshape(48,1),xh[i])
    example=meta.iloc[0];times=pd.date_range(example.fecha-pd.Timedelta(days=2),periods=48,freq='h')
    pd.DataFrame({'paso':range(48),'timestamp':times,'hora':times.hour,'estacion':example.estacion,'valor_escalado':xh[0,:,0]}).to_csv(out/'ejemplo_secuencia_48h.csv',index=False)
    masks={s:meta.particion.eq(s).to_numpy() for s in ['ajuste','seleccion','evaluacion']};a,v,e=[masks[s] for s in masks]
    assert [a.sum(),v.sum(),e.sum()]==[4625,884,3449]
    def ds(x,t,shuffle=False):
        d=tf.data.Dataset.from_tensor_slices((x,t));opt=tf.data.Options();opt.threading.private_threadpool_size=1
        if shuffle:d=d.shuffle(len(x),seed=42)
        return d.batch(64).with_options(opt)
    def predict(model,x):return np.concatenate([model(x[i:i+64],training=False).numpy() for i in range(0,len(x),64)])
    preds={};order=[];checks={}
    for name,x in [('cnn_gru_diaria',xd),('gru_horaria',xh)]:
        ws=[];hs=[];ps=[]
        for run in [1,2]:
            folder=out/f'{name}_{run}';folder.mkdir();keras.backend.clear_session();keras.utils.set_random_seed(42);L=keras.layers
            if name=='cnn_gru_diaria':
                enc=keras.Sequential([L.Input((32,32,1)),L.Conv2D(8,3,padding='same',activation='relu'),L.MaxPool2D(),L.Conv2D(16,3,padding='same',activation='relu'),L.MaxPool2D(),L.Flatten(),L.Dense(8)])
                model=keras.Sequential([L.Input((2,32,32,1)),L.TimeDistributed(enc),L.GRU(16),L.Dense(24)])
            else:model=keras.Sequential([L.Input((48,1)),L.GRU(16),L.Dense(24)])
            model.compile(optimizer=keras.optimizers.Adam(.001),loss='mse')
            h=model.fit(ds(x[a],y[a],True),validation_data=ds(x[v],y[v]),epochs=30,callbacks=[keras.callbacks.EarlyStopping(patience=5,restore_best_weights=True)],verbose=2)
            pd.DataFrame(h.history).to_csv(folder/'historia.csv',index=False);model.save(folder/'modelo.keras')
            p=predict(model,x[e]);loaded=keras.models.load_model(folder/'modelo.keras',compile=False);np.testing.assert_array_equal(p,predict(loaded,x[e]))
            np.save(folder/'prediccion.npy',p);ws.append(model.get_weights());hs.append(h.history);ps.append(p)
            (folder/'configuracion.json').write_text(json.dumps(dict(parametros=model.count_params(),mejor_epoca=int(np.argmin(h.history['val_loss'])+1),epocas=len(h.history['loss'])),indent=2))
            if run==1:
                variants={'invertir_dias':x[e][:,::-1] if name=='cnn_gru_diaria' else x[e].reshape(-1,2,24,1)[:,::-1].reshape(-1,48,1)}
                if name=='gru_horaria':variants['invertir_48_horas']=x[e][:,::-1]
                for variant,altered in variants.items():
                    q=predict(model,altered);order.append(dict(modelo=name,prueba=variant,mse_original=float(np.mean((p-y[e])**2)),mse_orden_alterado=float(np.mean((q-y[e])**2)),cambio_medio_prediccion=float(np.mean(np.abs(q-p)))))
        assert all(np.array_equal(w,z) for w,z in zip(*ws));assert hs[0]==hs[1];np.testing.assert_array_equal(*ps)
        preds[name]=ps[0];checks[name]=dict(pesos_identicos=True,historias_identicas=True,predicciones_identicas=True,recarga_verificada=True)
    pd.DataFrame(order).to_csv(out/'sensibilidad_orden.csv',index=False)
    old=pd.read_csv(files[3],parse_dates=['fecha']);ix=old.set_index(['estacion','fecha']).index.get_indexer(pd.MultiIndex.from_frame(meta.loc[e,['estacion','fecha']]))
    assert (ix>=0).all() and len(set(ix))==3449
    artifacts=np.load(files[2]);names=[k[:-4] for k in artifacts.files if k.endswith('_ppb') and '_reconstruccion_' not in k]
    tables={'autoencoder':old.iloc[ix].reset_index(drop=True)[names]}
    for name,p in preds.items():
        tables[name]=pd.DataFrame({s:np.mean(((artifacts[s+'_ppb'][ix]*scale.scale.to_numpy()+scale.offset.to_numpy()).astype('float32')-p)**2,axis=1) for s in names})
    rows=[];thresholds=[];n=len(ix)
    for name,t in tables.items():
        pd.concat([meta.loc[e,['fecha','estacion']].reset_index(drop=True),t],axis=1).to_csv(out/f'scores_{name}.csv',index=False)
        clean=t.original.to_numpy()
        for percentile,rate in [(95,.05),(98,.02),(99,.01),(99.9,.001)]:
            u=umbral_falsas_alarmas(clean,rate);fp=int((clean>u).sum());thresholds.append(dict(modelo=name,percentil=percentile,umbral=u,n=n,fa_teoricas=n*rate,fa_observadas=fp,tasa=fp/n))
            for s in names[1:]:
                b=t[s].to_numpy();tp=int((b>u).sum());labels=np.r_[np.zeros(n),np.ones(n)];scores=np.r_[clean,b]
                rows.append(dict(modelo=name,escenario=s,percentil=percentile,tp=tp,fp=fp,fn=n-tp,tn=n-fp,recall=tp/n,precision=tp/(tp+fp) if tp+fp else 0.,f1=2*tp/(tp+fp+n),auc=roc_auc_score(labels,scores),ap=average_precision_score(labels,scores)))
    result=pd.DataFrame(rows);result.to_csv(out/'metricas.csv',index=False);pd.DataFrame(thresholds).to_csv(out/'umbrales.csv',index=False)
    checks['continuidad_48h_todas_secuencias']=True;checks['fuentes_intactas']=all(sha(ROOT/k)==z for k,z in hashes.items());assert checks['fuentes_intactas']
    (out/'verificaciones.json').write_text(json.dumps(checks,indent=2))
    lines=['# Temporalidad explícita: dos días','', '4625 ajuste,884 selección,3449 evaluación. Dos réplicas por arquitectura y recarga verificadas. Cada secuencia tiene48 horas consecutivas, misma estación y cruce23→00 auditados contra la tabla original. No se modifica la convención horaria heredada.','', '## Recall p99 (%)','', '| Escenario | Autoencoder | CNN + GRU diaria | GRU horaria |','|---|---:|---:|---:|']
    for s in names[1:]:
        vals=[result[(result.modelo==model)&(result.escenario==s)&(result.percentil==99)].recall.iloc[0]*100 for model in tables]
        lines.append('| '+s+' | '+' | '.join(f'{z:.2f}' for z in vals)+' |')
    lines+=['','## Falsas alarmas','', 'Por detector, sobre3449 originales: p95 teóricas172.45, p98 68.98, p99 34.49,p99.9 3.449. Conteos observados y umbrales individuales en umbrales.csv. No sumar escenarios ni modelos.','', '## Alcance','', 'Historia original y ataques solo al objetivo: inicio aislado. No evalúa ataques sostenidos. La GRU horaria recibe48 valores en orden; la CNN+GRU resume cada día y tiene dos pasos. La inversión de orden es diagnóstico de sensibilidad y también altera recencia: no demuestra comprensión específica de medianoche. TINTO es reversible en el brazo horario, no se afirma ventaja de imágenes.', 'Calibración y evaluación originales reutilizan2022. Pares50/50, ventanas solapadas. Autoencoder entrenado en otra muestra y tarea; comparar aquí no aísla causalmente temporalidad. Las dos arquitecturas nuevas comparten soporte y tarea, pero distinta capacidad. Sin años2023–2026.']
    (out/'informe.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'checksums.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='checksums.json'},indent=2));print('\n'.join(lines),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--salida',required=True,type=Path);main(p.parse_args().salida)
