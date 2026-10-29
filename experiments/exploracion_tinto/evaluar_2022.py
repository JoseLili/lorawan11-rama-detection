"""Inferencia TINTO época 5 vs L0 selección; nunca entrena ni abre otros años."""
import os
os.environ.setdefault('CUDA_VISIBLE_DEVICES','-1')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS','1')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','3')
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'experiments/anomalias_red'))
BASE=ROOT/'results/anomalias_red_v1'
MODEL=ROOT/'results/exploracion_tinto_2022/seleccion_tinto_v1/cierre_manual/corrida1/modelo_mejor_observado.keras'
MAP=ROOT/'results/exploracion_tinto_2022/prototipos_20261028/corrida1/L0_408/mapa_unico_32.csv'
SCALE=ROOT/'results/exploracion_tinto_2022/hora_compacta_20261028/corrida1/L0_408/escalador.csv'
L0=BASE/'lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras'
NAMES=['TINTO_epoca5','L0_d50']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out,prueba,batch,bootstrap):
    import tensorflow as tf
    from tensorflow import keras
    from src.detect.lstm import fijar_semilla
    from src.detect import evaluacion_red as ev, estacion_dia as ed, lstm_local as ll, anomalias_red as ar
    from entrenar_lstm_sup import leer, parametros_vecinas, SELECCION
    from entrenar_lstm_estacion import leer_dias
    from metricas_estandar_revision8 import con_umbral
    from sklearn.metrics import average_precision_score, roc_auc_score
    out.mkdir(parents=True)
    clean,clean_sha=leer('limpia_2020_2022')
    assert clean.index.min().year==2020 and clean.index.max().year==2022
    _,sigma=ev.normalizacion(clean)
    par=parametros_vecinas('a14',clean.loc[SELECCION[0]:SELECCION[1]],sigma,'media')
    frozen=json.loads((ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1/vecinas_y_escalas.json').read_text())
    targets=frozen['objetivos'];stations=ev.estaciones_de(clean)
    assert len(targets)==31 and par.vecinas==frozen['vecinas']
    pos=np.flatnonzero(clean.index.year==2022)
    if prueba:pos=pos[:48]
    ts=clean.index[pos]
    assert len(ts)%24==0 and ts[0].hour==0 and ts[-1].hour==23
    mapping=pd.read_csv(MAP);scaler=pd.read_csv(SCALE)
    assert mapping.feature.tolist()==scaler.feature.tolist()
    rc=mapping[['row','column']].to_numpy(dtype=int)
    assert len(np.unique(rc,axis=0))==408
    fijar_semilla(42)
    models={NAMES[0]:keras.models.load_model(MODEL,compile=False),NAMES[1]:keras.models.load_model(L0,compile=False)}
    cnn=tf.function(lambda x:models[NAMES[0]](x,training=False),input_signature=[tf.TensorSpec([None,32,32,1],tf.float32)])
    lstm=tf.function(lambda x:models[NAMES[1]](x,training=False),input_signature=[tf.TensorSpec([None,24,17],tf.float32)])
    saved=leer_dias(BASE/'lstm_local_examen/c20/d50/seleccion/dias_2022.csv.gz')
    sources={'matriz_limpia_2020_2022':clean_sha}
    record={'fecha':'2026-10-29','alcance':'Exploración 2022, sin reentrenar, no examen independiente',
        'prueba':prueba,'batch':batch,'bootstrap':bootstrap,'origen_modelos':'Ambos cargados de disco; TINTO de cierre manual época 5',
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [MODEL,L0,MAP,SCALE,Path(__file__)]},
        'python':platform.python_version(),'tensorflow':tf.__version__,'keras':keras.__version__,
        'CPU':platform.processor(),'gpu_visible':len(tf.config.get_visible_devices('GPU'))}
    assert record['gpu_visible']==0
    (out/'configuracion_previa.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n')
    days={};controls=[]
    def score(key,matrix):
        F=ev.entradas_de('vecinas',matrix,None,sigma,par)
        scores={name:pd.DataFrame(index=ts,columns=targets,dtype=float) for name in NAMES}
        for target in targets:
            for start in range(0,len(pos),batch):
                ix=pos[start:start+batch]
                X=ll.ventanas_locales(F,stations,par.vecinas,target,ix)
                flat=X.reshape(-1,408).astype(np.float64)*scaler.scale.to_numpy()+scaler.offset.to_numpy()
                images=np.zeros((len(X),32,32,1),dtype=np.float32)
                images[:,rc[:,0],rc[:,1],0]=flat.astype(np.float32)
                assert np.isfinite(images).all()
                pred=[cnn(tf.convert_to_tensor(images)).numpy().ravel(),lstm(tf.convert_to_tensor(X)).numpy().ravel()]
                for name,p in zip(NAMES,pred):
                    assert np.isfinite(p).all()
                    scores[name].loc[matrix.index[ix],target]=p.astype(np.float64)
        obs=matrix.loc[ts,[f'{s}_mascara' for s in targets]].set_axis(targets,axis=1).eq(1)
        daily={name:ed.juntar_dia(p.where(obs),'promedio_dia',min_horas=12) for name,p in scores.items()}
        days[key]=daily
        for name,data in daily.items():
            data.to_csv(out/f'{key}_{name}_dias.csv.gz',index_label='dia')
        stored_key='limpia_2022' if key=='limpia_2022' else key.removesuffix('_d50') if key.endswith('_d50') else None
        if stored_key in saved:
            reference=saved[stored_key]['promedio_dia'].reindex(index=daily[NAMES[1]].index,columns=targets)
            a=daily[NAMES[1]].to_numpy();b=reference.to_numpy()
            assert np.array_equal(np.isnan(a),np.isnan(b))
            maximum=float(np.nanmax(np.abs(a-b)))
            controls.append({'matriz':key,'diferencia_maxima_L0_guardado':maximum,'tolerancia':1e-6,'cumple':maximum<=1e-6})
            assert maximum<=1e-6,'L0 difiere del guardado: revisar máquina/entorno antes de interpretar métricas'
        print(key+': puntajes diarios guardados',flush=True)
    score('limpia_2022',clean)
    deltas=[50] if prueba else [100,50,20]
    calendars=[f'entrenamiento_{i:02d}' for i in range(1,2 if prueba else 11)]
    for delta in deltas:
        for calendar in calendars:
            matrix,h=leer(f'{calendar}_d{delta}');sources[f'{calendar}_d{delta}']=h
            assert matrix.index.equals(clean.index)
            score(f'{calendar}_d{delta}',matrix)
    (out/'control_L0.json').write_text(json.dumps(controls,indent=2)+'\n')
    (out/'fuentes_matrices.json').write_text(json.dumps(sources,indent=2)+'\n')
    if prueba:
        (out/'PRUEBA_OK.json').write_text(json.dumps({'solo_flujo':True,'modelos_cargados':True,'sin_metricas':True,'horas':len(ts)},indent=2)+'\n')
        return
    # Días comunes GLOBALMENTE: ambos detectores, todos los calendarios y deltas.
    mask=days['limpia_2022'][NAMES[0]].notna()
    for daily in days.values():
        for p in daily.values():mask &= p.notna()
    assert mask.to_numpy().any()
    mask.to_csv(out/'dias_comunes.csv',index_label='dia')
    thresholds={name:{point:ev.umbral_falsas_alarmas(days['limpia_2022'][name].to_numpy()[mask],fa)
        for point,fa in [('p99',.01),('p999',.001)]} for name in NAMES}
    (out/'umbrales.json').write_text(json.dumps(thresholds,indent=2)+'\n')
    rows=[];counts={};common=mask.to_numpy();dates=mask.index
    block=(np.repeat(dates.month.to_numpy()-1,len(targets))*len(targets)+np.tile(np.arange(len(targets)),len(dates))).reshape(common.shape)
    for delta in deltas:
        for name in NAMES:
            for point in ['p99','p999']:
                counts[delta,name,point]=np.zeros((12*len(targets),3))
        for calendar in calendars:
            plan=ar.leer_plan(BASE/f'planes/plan_{calendar}.csv')
            y=ed.etiquetas(plan,dates,targets).to_numpy()[common]
            assert y.any() and (~y).any()
            for name in NAMES:
                for version,key in [('con_ataque',f'{calendar}_d{delta}'),('sin_ataque','limpia_2022')]:
                    s=days[key][name].to_numpy()[common]
                    auc=dict(AP=float(average_precision_score(y,s)),ROC_AUC=float(roc_auc_score(y,s)))
                    for point,u in thresholds[name].items():
                        alert=s>u
                        rows.append(dict(delta_pct=delta,calendario=calendar,detector=name,version=version,punto=point,
                            umbral=u,estacion_dias=len(y),**con_umbral(y,alert),**auc))
                        if version=='con_ataque':
                            counts[delta,name,point]+=np.stack([np.bincount(block[common],weights=w,minlength=12*len(targets)) for w in [alert&y,alert&~y,~alert&y]],axis=1)
    pd.DataFrame(rows).to_csv(out/'metricas_por_calendario.csv',index=False)
    # Agrupar puntajes/etiquetas: métricas globales, no promediar F1 de calendarios.
    pooled=[]
    for delta in deltas:
        y=np.concatenate([ed.etiquetas(ar.leer_plan(BASE/f'planes/plan_{c}.csv'),dates,targets).to_numpy()[common] for c in calendars])
        for name in NAMES:
            for version in ['con_ataque','sin_ataque']:
                s=np.concatenate([days[f'{c}_d{delta}' if version=='con_ataque' else 'limpia_2022'][name].to_numpy()[common] for c in calendars])
                for point,u in thresholds[name].items():
                    pooled.append(dict(delta_pct=delta,detector=name,version=version,punto=point,
                        umbral=u,estacion_dias=len(y),**con_umbral(y,s>u),AP=float(average_precision_score(y,s)),ROC_AUC=float(roc_auc_score(y,s))))
    pd.DataFrame(pooled).to_csv(out/'resultados.csv',index=False)
    # Bootstrap pareado por estación-mes, calendarios juntos; no incertidumbre de umbral/semilla.
    def metrics(a):
        tp,fp,fn=a[...,0],a[...,1],a[...,2]
        div=lambda x,y:np.divide(x,y,out=np.zeros_like(x,dtype=float),where=y!=0)
        return {'f1':div(2*tp,2*tp+fp+fn),'recall':div(tp,tp+fn),'precision':div(tp,tp+fp)}
    active=np.bincount(block[common],minlength=12*len(targets))>0
    nb=int(active.sum())
    W=np.random.default_rng([42,29,3]).multinomial(nb,np.full(nb,1/nb),size=bootstrap)
    intervals=[]
    for delta in deltas:
        for point in ['p99','p999']:
            a=metrics(W@counts[delta,NAMES[0],point][active]);b=metrics(W@counts[delta,NAMES[1],point][active])
            for metric in a:
                lo,hi=np.percentile(a[metric]-b[metric],[2.5,97.5])
                intervals.append(dict(delta_pct=delta,punto=point,metrica=metric,comparacion='TINTO_epoca5 - L0_d50',IC95_bajo=lo,IC95_alto=hi))
    pd.DataFrame(intervals).to_csv(out/'intervalos_exploratorios.csv',index=False)
    (out/'LISTO.json').write_text(json.dumps({'evaluacion_2022':True,'modelos_entrenados':False,'dias_comunes':int(common.sum()),'bootstrap':bootstrap,'limite':'Validación reutilizada y parada manual; no examen independiente ni prueba confirmatoria.'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--prueba',action='store_true');p.add_argument('--batch',type=int,default=512);p.add_argument('--bootstrap',type=int,default=2000)
    a=p.parse_args()
    if a.salida.exists():p.error('Usa una carpeta nueva.')
    if a.batch<1 or a.bootstrap<1:p.error('batch y bootstrap deben ser positivos')
    run(a.salida,a.prueba,a.batch,a.bootstrap)
