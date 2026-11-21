"""Piloto preregistrado; conserva checkpoints y permite continuar sin reentrenar."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['TF_ENABLE_ONEDNN_OPTS']='0';os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import sys,json,hashlib,time,argparse,subprocess,warnings,gc
from pathlib import Path
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import roc_auc_score,average_precision_score
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'experiments/linea_base'));sys.path.insert(0,str(ROOT/'experiments/anomalias_red'))
import comun as cm
import rev22_comun as rc
import rev23 as r23
import rev24 as r24
from src.detect import multianual as mu,anomalias_red as ar,evaluacion_red as ev,estacion_dia as ed
tf.config.threading.set_intra_op_parallelism_threads(2);tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism();warnings.filterwarnings('ignore',category=RuntimeWarning)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Detector:
    def __init__(self):
        self.tf=tf;self.modo='tf';self.nombres={'Vb':[f'Vb_R_s{s}' for s in [42,1,2,3,4]]};self.f={'Vb':[]}
        reg=json.loads((rc.SAL/'modelos_definitivos_sha256.json').read_text())
        for name in self.nombres['Vb']:
            p=rc.DEF/f'{name}.keras';assert sha(p)==reg[name];m=keras.models.load_model(p,compile=False)
            self.f['Vb'].append(tf.function(lambda x,m=m:m(x,training=False)))
    predecir=r23.Detectores.predecir
def main(raw,out):
    frozen=ROOT/'results/tinto_congelado_20261111'
    for k,v in json.loads((frozen/'checksums.json').read_text()).items():assert sha(frozen/k)==v
    out.mkdir(parents=True,exist_ok=True)
    config=dict(raw=str(raw.resolve()),calibracion=2023,evaluacion=2025,calendario='final_2025_01',protocolo_sha=sha(Path(__file__).with_name('protocolo_pareado_final.md')),codigo_sha=sha(Path(__file__)),tinto_sha=sha(frozen/'modelo.keras'))
    if (out/'configuracion.json').exists():assert json.loads((out/'configuracion.json').read_text())==config
    else:(out/'configuracion.json').write_text(json.dumps(config,indent=2))
    (out/'entorno.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    ck=mu.leer_checksums(ROOT/'docs/checksums_2020_2026.txt');long,sources=mu.cargar_o3_zips(raw,ck,anios=range(2020,2026))
    (out/'fuentes_raw.json').write_text(json.dumps(sources,indent=2));print('ZIP verificados y leidos',flush=True)
    values=long.pivot(index='timestamp',columns='station',values='value').reindex(index=pd.date_range('2020-01-01','2025-12-31 23:00',freq='h',name='timestamp'),columns=mu.ESTACIONES)
    del long;gc.collect()
    clean=ar.matriz_red(values.loc[:'2022-12-31 23:00'],rc.columnas())
    registered=pd.read_csv(cm.SAL_RED/'resumen_matrices.csv').set_index('archivo').sha256_csv['matriz_limpia_2020_2022.csv.gz']
    assert cm._sha_csv(clean)==registered
    cm.MATRICES.mkdir(exist_ok=True,parents=True);cache=cm.MATRICES/'matriz_limpia_2020_2022.csv.gz'
    if not cache.exists():clean.to_csv(cache,float_format='%.10g',lineterminator='\n',compression='gzip')
    assert cm._sha_csv(cm.leer('limpia_2020_2022'))==registered
    del clean;gc.collect();ctx=cm.contexto();esc=rc.escalas(ctx,'definitivo');tau=json.loads((r24.SAL/'decision_tau.json').read_text())['tau']
    det=Detector();tmodel=keras.models.load_model(frozen/'modelo.keras',compile=False)
    mapping=pd.read_csv(frozen/'mapa.csv');sc=pd.read_csv(frozen/'escala.csv');coords=mapping[['row','column']].to_numpy(int)
    obj=ctx['objetivos'];all_days=pd.date_range('2020-01-01','2025-12-31',freq='D')
    tensor=values[obj].to_numpy().reshape(-1,24,len(obj)).transpose(0,2,1)
    complete=np.isfinite(tensor).all(axis=2);eligible=complete.copy();eligible[:2]=False;eligible[2:]&=complete[1:-1]&complete[:-2]
    plan=ar.leer_plan(ROOT/'results/anomalias_red_v1/planes/plan_final_2025_01.csv');plan.to_csv(out/'plan_base.csv',index=False)
    label=pd.DataFrame(False,index=all_days,columns=obj);post=label.copy();diasep=pd.DataFrame(0,index=all_days,columns=obj)
    for r in plan.itertuples():
        begin=pd.Timestamp(r.inicio).normalize();end=pd.Timestamp(r.fin).normalize();label.loc[begin:end,r.estacion]=True
        diasep.loc[begin:end,r.estacion]=np.arange(1,(end-begin).days+2)
        post.loc[end+pd.Timedelta(days=1):end+pd.Timedelta(days=14),r.estacion]=True
    post&=~label
    costs=[];coverage=[];supports={};clean_scores={};period2025=None;thresholds={}
    def tscore(v,year):
        a=v[obj].to_numpy().reshape(-1,24,len(obj)).transpose(0,2,1)
        # same global dates through evaluation year, positions only in requested year
        rows,cols=np.where(eligible[:len(a)]&(all_days[:len(a)].year==year)[:,None]);scores=np.full((sum(all_days.year==year),len(obj)),np.nan)
        days=all_days[rows];yearstart=np.flatnonzero(all_days.year==year)[0]
        for start in range(0,len(rows),64):
            rr=rows[start:start+64];cc=cols[start:start+64]
            rawx=np.stack([a[rr-2,cc],a[rr-1,cc]],axis=1)
            z=(rawx*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32')
            x=np.zeros((len(rr),2,32,32,1),np.float32);x[:,:,coords[:,0],coords[:,1],0]=z
            p=tmodel(x,training=False).numpy();target=(a[rr,cc]*sc.scale.to_numpy()+sc.offset.to_numpy()).astype('float32')
            scores[rr-yearstart,cc]=np.mean((target-p)**2,axis=1)
        return scores
    for year in [2023,2025]:
        v=values.loc[:f'{year}-12-31 23:00'];checkpoint=out/f'original_{year}.npz';t0=time.perf_counter()
        # Engine caches original features/probabilities for sustained-attack incremental inference.
        period=r24.Periodo(v,f'{year}-01-01',ctx,esc,det,[('Vx',tau)])
        xs=next(iter(period.limpio.values()));sec_x=time.perf_counter()-t0;t0=time.perf_counter();ts=tscore(v,year);sec_t=time.perf_counter()-t0
        assert xs.shape==ts.shape
        common=np.isfinite(xs)&np.isfinite(ts);supports[year]=common;clean_scores[year]={'Ens-Vb-X':xs,'TINTO':ts}
        np.savez_compressed(checkpoint,**clean_scores[year],comun=common,dias=period.dias.to_numpy(),estaciones=np.array(obj))
        dd,ss=np.where(common);pd.DataFrame({'fecha':period.dias[dd],'estacion':np.array(obj)[ss]}).to_csv(out/f'soporte_{year}.csv',index=False)
        coverage.extend([dict(anio=year,modelo=name,elegibles=int(np.isfinite(score).sum()),comunes=int(common.sum())) for name,score in clean_scores[year].items()])
        costs.extend([dict(etapa=f'original_{year}',modelo='Ens-Vb-X',segundos=sec_x),dict(etapa=f'original_{year}',modelo='TINTO',segundos=sec_t)])
        if year==2023:
            stored=json.loads((r24.SAL/'umbrales_2023_X.json').read_text());(out/'umbrales_historicos_referencia.json').write_text(json.dumps(stored,indent=2))
            # Regression on full native calibration support, before common-support recalibration.
            full={str(rate):ev.umbral_falsas_alarmas(xs[np.isfinite(xs)],rate) for rate in [.01,.001]}
            assert int(np.isfinite(xs).sum())==stored['estacion_dias']
            assert all(abs(u-stored['umbrales'][rate])<=1e-5 for rate,u in full.items()), full
            (out/'regresion_calibracion.json').write_text(json.dumps(dict(umbrales_obtenidos=full,referencia=stored,n=int(np.isfinite(xs).sum())),indent=2))
            for name,score in clean_scores[year].items():
                thresholds[name]={p:ev.umbral_falsas_alarmas(score[common],rate) for p,rate in [(95,.05),(98,.02),(99,.01),(99.9,.001)]}
            (out/'umbrales_comunes.json').write_text(json.dumps(thresholds,indent=2))
            del period;gc.collect()
        else:period2025=period
        print('Original',year,'comunes',common.sum(),'segundos',sec_x,sec_t,flush=True)
    pd.DataFrame(coverage).to_csv(out/'cobertura.csv',index=False)
    scenarios=[(f'd{int(d*100)}_{sign}',1+d if sign=='aumento' else 1/(1+d),0.) for d in [1.,.5,.2,.05] for sign in ['aumento','reduccion']]+[(f'ppb_{b}',1.,float(b)) for b in [5,10,20,40]]
    dates=period2025.dias;mask=supports[2025];lab=label.loc[dates,obj].to_numpy();after=post.loc[dates,obj].to_numpy();daynum=diasep.loc[dates,obj].to_numpy();rows=[];alerts=[];byday=[]
    def metrics(name,s,score):
        y=lab[mask];scores=score[mask];assert np.isfinite(scores).all()
        for p,u in thresholds[name].items():
            pred=scores>u;tp=int((pred&y).sum());fp=int((pred&~y).sum());fn=int((~pred&y).sum());tn=int((~pred&~y).sum())
            rows.append(dict(modelo=name,escenario=s,percentil=p,tp=tp,fp=fp,fn=fn,tn=tn,recall=tp/(tp+fn) if tp+fn else 0.,precision=tp/(tp+fp) if tp+fp else 0.,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,auc=roc_auc_score(y,scores) if y.any() and (~y).any() else None,ap=average_precision_score(y,scores) if y.any() else None,fp_post14=int(((score>u)&after&mask).sum()),n_post14=int((after&mask).sum()),fa_teoricas=(fp+tn)*(1-p/100)))
            for day in range(1,8):
                select=(daynum==day)&mask;byday.append(dict(modelo=name,escenario=s,percentil=p,dia_episodio=day,n=int(select.sum()),detectados=int(((score>u)&select).sum())))
    for name,score in clean_scores[2025].items():
        for p,u in thresholds[name].items():
            cal=clean_scores[2023][name][supports[2023]];obs=score[mask];alerts.append(dict(modelo=name,percentil=p,umbral=u,n_cal=len(cal),fa_cal_teoricas=len(cal)*(1-p/100),fa_cal=int((cal>u).sum()),n_eval=len(obs),fa_eval_teoricas=len(obs)*(1-p/100),fa_eval=int((obs>u).sum()),tasa_eval=float(np.mean(obs>u))))
    pd.DataFrame(alerts).to_csv(out/'falsas_alarmas_originales.csv',index=False)
    for name,factor,offset in scenarios:
        checkpoint=out/f'{name}.npz'
        if checkpoint.exists():z=np.load(checkpoint);scores={k:z[k] for k in ['Ens-Vb-X','TINTO']}
        else:
            rec=period2025.vy.copy();cam=pd.DataFrame(False,index=rec.index,columns=rec.columns)
            for r in plan.itertuples():
                old=rec.loc[r.inicio:r.fin,r.estacion];new=old*factor+offset;rec.loc[r.inicio:r.fin,r.estacion]=new;cam.loc[r.inicio:r.fin,r.estacion]=old.notna()&(old!=new)
            t0=time.perf_counter();S,info=period2025.alterada(rec,cam,plan);sec_x=time.perf_counter()-t0
            t0=time.perf_counter();altered=pd.concat([values.loc[:'2024-12-31 23:00'],rec]);ts=tscore(altered,2025);sec_t=time.perf_counter()-t0
            scores={'Ens-Vb-X':next(iter(S.values())),'TINTO':ts};np.savez_compressed(checkpoint,**scores,info=np.array(json.dumps(info)))
            costs.extend([dict(etapa=name,modelo='Ens-Vb-X',segundos=sec_x),dict(etapa=name,modelo='TINTO',segundos=sec_t)])
        for detector,score in scores.items():metrics(detector,name,score)
        pd.DataFrame(rows).to_csv(out/'metricas.csv',index=False);pd.DataFrame(costs).to_csv(out/'costos.csv',index=False);pd.DataFrame(byday).to_csv(out/'recall_por_dia_episodio.csv',index=False)
        print(name,'completado',flush=True)
    for k,v in json.loads((frozen/'checksums.json').read_text()).items():assert sha(frozen/k)==v
    (out/'verificaciones.json').write_text(json.dumps(dict(modelo_tinto_intacto=True,modelos_ens_vb_x_hashes_verificados=True,fuentes_raw_verificadas=True,matriz_historica_exacta=True,comparaciones=len(rows),positivos_comunes=int((lab&mask).sum()),negativos_comunes=int((~lab&mask).sum())),indent=2))
    (out/'checksums.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='checksums.json'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--salida',type=Path,required=True);args=p.parse_args();main(args.raw,args.salida)
