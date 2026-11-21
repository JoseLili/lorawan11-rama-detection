"""Evaluación congelada; ver protocolo_evaluacion_12.md."""
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
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT))
from src.detect.evaluacion_red import umbral_falsas_alarmas
tf.config.threading.set_intra_op_parallelism_threads(2)
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
    base=ROOT/'results/tinto_autoencoder_20261109'; rawroot=ROOT/'results/tinto_raw_20261109'
    for name,digest in json.loads((base/'fuentes.json').read_text()).items():
        assert sha(ROOT/name)==digest, name
    prior_hashes={k.replace('\\','/'):v for k,v in json.loads((base/'checksums.json').read_text()).items()}
    for name in ['corrida1/modelo.keras','corrida2/modelo.keras','originales.npy','manifiesto.csv']:
        assert sha(base/name)==prior_hashes[name]
    out.mkdir(parents=True,exist_ok=False)
    paths=[base/'corrida1/modelo.keras',base/'corrida2/modelo.keras',base/'manifiesto.csv',rawroot/'auditoria1/o3_raw_ppb.csv',rawroot/'representacion1/completos_32_mapa.csv',rawroot/'representacion1/completos_escala.csv',Path(__file__),Path(__file__).with_name('protocolo_evaluacion_12.md'),ROOT/'src/detect/evaluacion_red.py']
    (out/'fuentes.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in paths},indent=2))
    (out/'entorno.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    allmeta=pd.read_csv(base/'manifiesto.csv'); sel=allmeta.particion.eq('evaluacion')
    meta=allmeta.loc[sel,['fecha','estacion']].reset_index(drop=True)
    assert len(meta)==7154 and not meta.duplicated().any() and meta.fecha.str.startswith('2022').all()
    df=pd.read_csv(paths[3],index_col=0,parse_dates=True)
    values=np.stack([df.loc[pd.date_range(row.fecha,periods=24,freq='h'),row.estacion].to_numpy(float) for row in meta.itertuples()])
    assert np.isfinite(values).all()
    coords=pd.read_csv(paths[4])[['row','column']].to_numpy(int); sc=pd.read_csv(paths[5])
    assert len(set(map(tuple,coords)))==24
    def images(v):
        z=(v*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32')
        x=np.zeros((len(v),32,32,1),dtype='float32'); x[:,coords[:,0],coords[:,1],0]=z
        assert np.isfinite(x).all()
        np.testing.assert_array_equal(x[:,coords[:,0],coords[:,1],0],z)
        return x,z
    np.testing.assert_array_equal(images(values)[0],np.load(base/'originales.npy',mmap_mode='r')[sel])
    models=[keras.models.load_model(base/f'corrida{i}/modelo.keras',compile=False) for i in [1,2]]
    assert all(np.array_equal(a,b) for a,b in zip(models[0].get_weights(),models[1].get_weights()))
    scenarios=[('original',1.,0.)]+[(f'd{int(d*100)}_{sign}',1+d if sign=='aumento' else 1/(1+d),0.) for d in [1.,.5,.2,.05] for sign in ['aumento','reduccion']]+[(f'ppb_{b}',1.,float(b)) for b in [5,10,20,40]]
    (out/'configuracion.json').write_text(json.dumps(dict(escenarios=scenarios,percentiles=[95,98,99,99.9],principal=99,batch=128,score='MSE 24 pixeles',reentrenamiento=False),indent=2))
    meta.to_csv(out/'manifiesto.csv',index=False)
    scores={}; hours=[]; artifacts={}; checks={}
    for name,factor,offset in scenarios:
        v=values*factor+offset; x,z=images(v)
        recon=[]; repeat=[]
        for start in range(0,len(x),128):
            batch=x[start:start+128]
            recon.append(models[0](batch,training=False).numpy()[:,coords[:,0],coords[:,1],0])
            repeat.append(models[1](batch,training=False).numpy()[:,coords[:,0],coords[:,1],0])
        pred=np.concatenate(recon); np.testing.assert_array_equal(pred,np.concatenate(repeat))
        errors=(z-pred)**2
        # Same TF reduction as the original experiment, preserving near-threshold decisions.
        score=tf.reduce_mean(tf.square(tf.constant(z)-tf.constant(pred)),axis=1).numpy()
        assert np.isfinite(score).all(); scores[name]=score
        physical=(pred-sc.offset.to_numpy())/sc.scale.to_numpy()
        artifacts[name+'_ppb']=v; artifacts[name+'_reconstruccion_ppb']=physical
        checks[name]=dict(replicas_identicas=True,mediciones_cambiadas=int(np.count_nonzero(v!=values)),dias_sin_cambio=int(np.sum(np.all(v==values,axis=1))))
        for station in ['TODAS']+sorted(meta.estacion.unique().tolist()):
            ix=np.ones(len(v),bool) if station=='TODAS' else meta.estacion.eq(station).to_numpy()
            for h in range(24):
                hours.append(dict(escenario=name,estacion=station,hora=h,n=int(ix.sum()),mse_escalado=float(errors[ix,h].mean()),mae_ppb=float(np.abs(v[ix,h]-physical[ix,h]).mean()),sesgo_reconstruccion_ppb=float((physical[ix,h]-v[ix,h]).mean())))
        print(name,'evaluado y verificado',flush=True)
    old=pd.read_csv(base/'corrida1/scores.csv')
    np.testing.assert_allclose(scores['original'],old.original,rtol=1e-6,atol=1e-9)
    for name,factor,offset in scenarios:
        key=f'factor_{factor:.6f}'
        if name!='original' and offset==0 and key in old:
            np.testing.assert_allclose(scores[name],old[key],rtol=1e-6,atol=1e-9)
    thresholds={p:umbral_falsas_alarmas(scores['original'],rate) for p,rate in [(95,.05),(98,.02),(99,.01),(99.9,.001)]}
    rows=[]; stations=[]; paired=[]
    def metrics(a,b,u):
        tp=int((b>u).sum()); fp=int((a>u).sum()); fn=len(b)-tp; tn=len(a)-fp
        labels=np.r_[np.zeros(len(a)),np.ones(len(b))]; s=np.r_[a,b]
        return dict(n_original=len(a),n_ataque=len(b),tp=tp,fp=fp,fn=fn,tn=tn,recall=tp/len(b),falsa_alarma=fp/len(a),precision=tp/(tp+fp) if tp+fp else 0.,f1=2*tp/(2*tp+fp+fn),roc_auc=roc_auc_score(labels,s),ap=average_precision_score(labels,s))
    for name,_,_ in scenarios[1:]:
        a=scores['original']; b=scores[name]
        paired.append(dict(escenario=name,fraccion_error_menor=float(np.mean(b<a)),media_original=float(a.mean()),media_alterada=float(b.mean()),mediana_cambio=float(np.median(b-a))))
        for p,u in thresholds.items():
            rows.append(dict(escenario=name,percentil=p,umbral=u,**metrics(a,b,u)))
            for station in sorted(meta.estacion.unique()):
                ix=meta.estacion.eq(station).to_numpy()
                stations.append(dict(escenario=name,percentil=p,estacion=station,umbral=u,**metrics(a[ix],b[ix],u)))
    result=pd.DataFrame(rows)
    assert len(result)==48
    for name in result.escenario.unique():
        assert np.all(np.diff(result[result.escenario.eq(name)].recall)<=0)
    prev=pd.read_csv(base/'metricas.csv')
    for name,factor,offset in scenarios[1:]:
        if offset==0 and factor!=1.05 and factor!=1/1.05:
            for p,rate in [(99,.01),(99.9,.001)]:
                prior=prev[(prev.corrida==1)&np.isclose(prev.factor,factor)&np.isclose(prev.tasa_objetivo,rate)].iloc[0]
                now=result[(result.escenario==name)&(result.percentil==p)].iloc[0]
                for metric in ['recall','precision','f1','falsa_alarma']:
                    assert np.isclose(prior[metric],now[metric],rtol=1e-10,atol=1e-12)
    result.to_csv(out/'metricas.csv',index=False)
    pd.DataFrame(stations).to_csv(out/'metricas_estacion.csv',index=False)
    pd.DataFrame(hours).to_csv(out/'diagnostico_hora_estacion.csv',index=False)
    pd.DataFrame(paired).to_csv(out/'comparacion_pareada.csv',index=False)
    pd.concat([meta,pd.DataFrame(scores)],axis=1).to_csv(out/'scores.csv',index=False)
    np.savez_compressed(out/'lecturas_y_reconstrucciones.npz',**artifacts)
    th=pd.DataFrame([dict(percentil=p,umbral=u,alertas_originales=int((scores['original']>u).sum()),tasa=float(np.mean(scores['original']>u))) for p,u in thresholds.items()]); th.to_csv(out/'umbrales.csv',index=False)
    (out/'verificaciones.json').write_text(json.dumps(dict(escenarios=checks,originales_y_metricas_previas_coinciden=True,fuentes_intactas=all(sha(p)==json.loads((out/'fuentes.json').read_text())[str(p.relative_to(ROOT))] for p in paths)),indent=2))
    lines=['# Autoencoder congelado: 12 escenarios','', '7154 originales estación-día de 2022; sin reentrenamiento. Dos modelos con pesos idénticos producen reconstrucciones idénticas en los 13 conjuntos (original y 12 alteraciones).','', '## Recall (%)','', '| Escenario | p95 | p98 | p99 | p99.9 |','|---|---:|---:|---:|---:|']
    for name,_,_ in scenarios[1:]:
        rr=result[result.escenario.eq(name)]
        lines.append('| '+name+' | '+' | '.join(f'{v*100:.3f}' for v in rr.recall)+' |')
    lines+=['','## Calibración','']
    for row in th.itertuples(): lines.append(f'- p{row.percentil}: umbral {row.umbral:.9g}; {row.alertas_originales}/7154 alertas ({row.tasa*100:.4f}%).')
    lines+=['','## Límites e interpretación','', 'Los umbrales son globales, calibrados en los mismos originales 2022; falsas alarmas descriptivas, no estimación independiente. Pares 50/50 por escenario: precisión y F1 no son valores operativos. Original no significa ausencia garantizada de anomalías reales.', 'Delta de reducción usa división entre 1+delta, no resta del porcentaje. Todas las alteraciones abarcan el día completo. No hay calendarios L0 ni años 2023–2026.', 'La comparación pareada cuantifica si la alteración reduce el error. El diagnóstico por hora/estación conserva errores escalados, MAE en ppb y sesgo de reconstrucción. No se cambió score, modelo ni umbrales para mejorar los resultados. Estos datos no demuestran que la falta de contexto sea la causa.', '', '## Archivos', '', '- metricas.csv: 48 combinaciones; metricas_estacion.csv: desglose con umbrales globales.', '- scores.csv y comparacion_pareada.csv: puntuaciones y cambios por escenario.', '- diagnostico_hora_estacion.csv: errores por hora y estación, incluyendo agregado TODAS.', '- lecturas_y_reconstrucciones.npz: originales, alterados y reconstrucciones en ppb; orden de manifiesto.csv.', '- fuentes.json, verificaciones.json, entorno.txt y checksums.json: trazabilidad y verificación.', '', 'Reproducción: python experiments/tinto_raw/evaluar_12.py --salida results/NUEVA_CARPETA. Rechaza sobrescribir resultados.']
    (out/'informe.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'checksums.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='checksums.json'},indent=2))
    print(result.to_string(index=False),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--salida',type=Path,required=True); main(p.parse_args().salida)
