"""Examen registrado de PARAAD congelado; no entrena ni selecciona nada."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from entrenar_paraad import RAIZ, SAL, guardar, sha
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import average_precision_score, roc_auc_score
from src.detect import paraad as p, anomalias_red as ar, estacion_dia as ed, evaluacion_red as ev
from metricas_estandar_revision8 import con_umbral

BASE = RAIZ / 'results/anomalias_red_v1'
REGISTRO = RAIZ / 'docs/registro_examen_paraad_revision20.md'
MODELO = SAL / 'colab_20261028/recuperado/definitivo'
CAL = SAL / 'calibracion_2023/registro.json'
DET = ['L0_unico', 'V4S_compartido', 'R3', 'V4']


def medidas(c):
    tp, fp, fn = np.asarray(c).T
    with np.errstate(divide='ignore', invalid='ignore'):
        return dict(f1=np.divide(2*tp, 2*tp+fp+fn, out=np.zeros_like(tp,dtype=float), where=2*tp+fp+fn>0),
                    recall=tp/(tp+fn), precision=np.divide(tp,tp+fp,out=np.zeros_like(tp,dtype=float),where=tp+fp>0))


def conteo_bloques(y, alerta, bloques):
    return np.stack([np.bincount(bloques, weights=w, minlength=int(bloques.max())+1)
                     for w in (y & alerta, ~y & alerta, y & ~alerta)], axis=1)


def intervalo(y, alerta, bloques, semilla, otro=None):
    c = conteo_bloques(y, alerta, bloques)
    nb = len(c)
    W = np.random.default_rng(semilla).multinomial(nb, np.full(nb,1/nb), size=2000)
    boot, est = medidas(W@c), medidas(c.sum(axis=0))
    if otro is not None:
        co = conteo_bloques(y, otro, bloques)
        bo, eo = medidas(W@co), medidas(co.sum(axis=0))
        boot = {k:boot[k]-bo[k] for k in boot}
        est = {k:est[k]-eo[k] for k in est}
    return [dict(metrica=k, estimacion=float(est[k]), ic_bajo=float(np.nanpercentile(boot[k],2.5)),
                 ic_alto=float(np.nanpercentile(boot[k],97.5)),
                 remuestreos_validos=int(np.isfinite(boot[k]).sum())) for k in boot]


def mascara_comun(tabla, nombre, dias):
    soportes = []
    for det in DET:
        t=tabla[(tabla.conjunto==nombre)&(tabla.detector==det)].set_index('dia')
        if t.index.has_duplicates: raise ValueError('puntajes históricos duplicados')
        t=t.reindex(dias).loc[:,list(p.OBJETIVOS)]
        soportes.append(t.notna())
    ok=soportes[0].copy()
    for soporte in soportes[1:]:ok &= soporte
    return ok


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--anio',type=int,choices=[2024,2025,2026],required=True)
    ap.add_argument('--reanudar',action='store_true')
    args=ap.parse_args(); anio=args.anio
    if not REGISTRO.is_file():raise ValueError('falta registro previo')
    conf=json.loads((MODELO/'congelado.json').read_text());cal=json.loads(CAL.read_text())
    assert conf['igual'] and cal['igual'] and cal['calibracion']
    assert sha(MODELO/'modelo_r1.keras')==conf['sha256_modelo']==cal['sha256_modelo']
    assert sha(MODELO/'escala.csv')==conf['sha256_escala']==cal['sha256_escala']
    for f,h in conf['fuentes'].items():assert sha(RAIZ/f)==h
    assert tf.__version__==conf['tensorflow'] and tf.keras.__version__==conf['keras']
    out=SAL/'examen'/str(anio);out.mkdir(parents=True,exist_ok=args.reanudar)
    entrada=dict(anio=anio,sha256_modelo=conf['sha256_modelo'],sha256_escala=conf['sha256_escala'],
                 sha256_calibracion=sha(CAL),sha256_script=sha(__file__),sha256_registro=sha(REGISTRO),
                 tensorflow=tf.__version__,keras=tf.keras.__version__,numpy=np.__version__)
    if (out/'entrada.json').exists():assert json.loads((out/'entrada.json').read_text())==entrada
    else:guardar(out/'entrada.json',entrada)
    modelo=tf.keras.models.load_model(MODELO/'modelo_r1.keras',compile=False)
    escala=pd.read_csv(MODELO/'escala.csv',index_col='estacion',float_precision='round_trip')
    dias=pd.date_range(f'{anio}-01-01', f'{anio}-07-31' if anio==2026 else f'{anio}-12-31',freq='D')
    ref=pd.read_csv(BASE/f'revision18/dias_{anio}.csv.gz',parse_dates=['dia'],float_precision='round_trip')
    ok=mascara_comun(ref,f'limpia_{anio}',dias); valid=ok.to_numpy().ravel()
    ok.astype(int).rename_axis('dia').to_csv(out/'mascara_comun.csv')
    # Contraste con las cuentas históricas de las mismas unidades, antes de métricas.
    cuentas=pd.read_csv(BASE/f'revision19/{anio}/conteos.csv')
    for f in cuentas.itertuples():assert f.atacadas+f.normales==int(valid.sum())*f.calendarios
    def historico(conjunto,det):
        t=ref[(ref.conjunto==conjunto)&(ref.detector==det)].set_index('dia').reindex(dias)
        a=t[list(p.OBJETIVOS)].to_numpy().ravel()[valid]
        assert np.isfinite(a).all();return a
    cache={};evidencia=[]
    def puntuar(nombre):
        if nombre in cache:return cache[nombre]
        matriz=BASE/f'matrices/matriz_{nombre}.csv.gz'
        hp=sha(matriz);dest=out/'puntajes'/f'{nombre}.csv';meta=dest.with_suffix('.json')
        if meta.exists():
            c=json.loads(meta.read_text());assert c['sha256_matriz']==hp and c['sha256_puntajes']==sha(dest)
            assert c['entrada']==entrada
            s=pd.read_csv(dest,index_col='dia',parse_dates=['dia'],float_precision='round_trip')
        else:
            cols=['timestamp']+[f'{s}_{c}' for s in p.SENSORES for c in ['valor','mascara']]
            x=pd.read_csv(matriz,usecols=cols,index_col='timestamp',parse_dates=['timestamp'])
            assert (x.index.year==anio).all()
            v=x[[f'{s}_valor' for s in p.SENSORES]].set_axis(p.SENSORES,axis=1)
            for s0 in p.SENSORES:
                mask=x[f'{s0}_mascara'];assert mask.isin([0,1]).all();v[s0]=v[s0].where(mask==1)
            z,m,fechas=p.bloques(v,escala);np.testing.assert_array_equal(fechas,dias)
            a=p.reconstruir(modelo,z);b=p.reconstruir(modelo,z);np.testing.assert_array_equal(a,b)
            s=p.exigir_comunes(p.puntajes(z,m,a,fechas),ok)
            dest.parent.mkdir(parents=True,exist_ok=True);s.rename_axis('dia').to_csv(dest)
            guardar(meta,dict(sha256_matriz=hp,sha256_puntajes=sha(dest),entrada=entrada,inferencia_duplicada_identica=True))
        p.exigir_comunes(s,ok);cache[nombre]=s.to_numpy().ravel()[valid];evidencia.append(str(meta.relative_to(out)))
        return cache[nombre]
    s0=puntuar(f'limpia_{anio}')
    geo=pd.read_csv(BASE.parent/'inventario_multianual/estaciones_geografia.csv',index_col='station')
    vecinas=ev.vecinas_de(list(p.SENSORES),geo)
    cals=ar.corridas().corrida.tolist()[1:] if anio==2024 else [c for c in ar.corridas_finales().corrida if str(anio) in c]
    nodos=[c for c in ar.corridas_nodo(list(p.OBJETIVOS)).corrida if c.startswith(f'nodo_{anio}_')]
    bloques0=(np.arange(len(p.OBJETIVOS))[None,:]*12+(dias.month.to_numpy()-1)[:,None]).ravel()[valid]
    filas=[];ics=[];pareado=[];comparaciones=[];conteos=[];falsas=[]
    for ie,(esc,nombres) in enumerate([('original',cals),('B',cals),('A',nodos)]):
        for d in [100,50,20,10,5]:
            ys=[];ss=[];bs=[];orig=[];grupos=[];refs={k:[] for k in ['L0_unico','V4']}
            for j,c in enumerate(nombres):
                nombre=f'unavez_{c}' if esc=='B' else c
                planfile=BASE/f'planes/plan_{nombre}.csv'
                if planfile.exists():plan=ar.leer_plan(planfile)
                else:
                    assert esc=='A' and anio==2026 and c.endswith(('_FAR','_VIF'))
                    plan=pd.DataFrame(columns=ar.COLUMNAS_PLAN)
                y=ed.etiquetas(plan,dias,list(p.OBJETIVOS)).to_numpy().ravel()[valid]
                ys.append(y);ss.append(puntuar(f'{nombre}_d{d}'))
                grupos.append(ed.grupos_falsa_alarma(plan,dias,list(p.OBJETIVOS),vecinas).to_numpy().ravel()[valid])
                bs.append(bloques0+(1000*j if esc!='original' else 0))
                if esc=='B':orig.append(puntuar(f'{c}_d{d}'))
                if esc=='original':
                    for k in refs:refs[k].append(historico(f'{c}_d{d}',k))
            y=np.concatenate(ys).astype(bool);s=np.concatenate(ss);clean=np.tile(s0,len(nombres))
            g=np.concatenate(grupos)
            _,bloques=np.unique(np.concatenate(bs),return_inverse=True)
            if esc!='original':
                c=cuentas[(cuentas.escenario==esc)&(cuentas.delta_pct==d)].iloc[0]
                assert int(y.sum())==c.atacadas and int((~y).sum())==c.normales
            conteos.append(dict(anio=anio,escenario=esc,delta_pct=d,atacadas=int(y.sum()),normales=int((~y).sum())))
            referencia=pd.read_csv(BASE/'revision18/resultados.csv') if esc=='original' else pd.read_csv(BASE/f'revision19/{anio}/resultados.csv')
            referencia=referencia[(referencia.anio==anio)&(referencia.delta_pct==d)]
            referencia=referencia[referencia.dias=='comunes'] if esc=='original' else referencia[referencia.escenario==esc]
            for punto,u in cal['umbrales'].items():
                for grupo in ed.GRUPOS_FA:
                    en=g==grupo;fp=int(((s>u)&en).sum())
                    falsas.append(dict(anio=anio,escenario=esc,delta_pct=d,punto=punto,grupo=grupo,
                        estacion_dias_normales=int(en.sum()),falsas_alarmas=fp,
                        tasa_pct=100*fp/int(en.sum()) if en.any() else np.nan))
                for version,score in [('con ataque',s),('sin ataque',clean)]:
                    fila=dict(anio=anio,escenario=esc,delta_pct=d,detector='PARAAD_SA_adaptado',punto=punto,
                              evaluacion=version,umbral=u,**con_umbral(y,score>u),
                              pr_auc=average_precision_score(y,score),roc_auc=roc_auc_score(y,score))
                    filas.append(fila)
                for f in intervalo(y,s>u,bloques,[42,20,anio,ie]):
                    ics.append(dict(anio=anio,escenario=esc,delta_pct=d,punto=punto,comparacion='PARAAD',**f))
                for det in DET:
                    rr=referencia[(referencia.detector==det)&(referencia.punto==punto)&(referencia.evaluacion=='con ataque')].iloc[0]
                    assert rr.tp+rr.fn==int(y.sum()) and rr.fp+rr.tn==int((~y).sum())
                    comparaciones.append(dict(anio=anio,escenario=esc,delta_pct=d,punto=punto,detector=det,
                        **{f'{k}_paraad':filas[-2][k] for k in ['f1','precision','recall']},
                        **{f'{k}_referencia':rr[k] for k in ['f1','precision','recall']}))
                if esc=='original':
                    for det in refs:
                        rr=referencia[(referencia.detector==det)&(referencia.punto==punto)].umbral.iloc[0]
                        for f in intervalo(y,s>u,bloques,[42,20,anio,ie],np.concatenate(refs[det])>rr):
                            ics.append(dict(anio=anio,escenario=esc,delta_pct=d,punto=punto,comparacion=f'PARAAD − {det}',**f))
                if esc=='B':
                    so=np.concatenate(orig);den=y.sum()
                    c=np.stack([np.bincount(bloques,weights=w,minlength=bloques.max()+1) for w in [y&(s>u),y&(so>u),y]],axis=1)
                    nb=len(c);W=np.random.default_rng([42,20,anio,ie]).multinomial(nb,np.full(nb,1/nb),size=2000)
                    cc=W@c
                    with np.errstate(divide='ignore',invalid='ignore'):boot=(cc[:,0]-cc[:,1])/cc[:,2]
                    pareado.append(dict(anio=anio,delta_pct=d,punto=punto,recall_original=float((y&(so>u)).sum()/den),
                        recall_B=float((y&(s>u)).sum()/den),ic_bajo=float(np.nanpercentile(boot,2.5)),ic_alto=float(np.nanpercentile(boot,97.5))))
            # Guardar avance completo por combinación, sin seleccionar ni recalibrar.
            for nombre,datos in [('resultados',filas),('intervalos',ics),('comparaciones',comparaciones),('pareado_recall',pareado),('conteos',conteos),('falsas_alarmas',falsas)]:
                pd.DataFrame(datos).to_csv(out/f'{nombre}.csv',index=False)
            guardar(out/'estado.json',dict(estado='ejecutando',escenario=esc,delta_pct=d,anio=anio))
            print(f'{anio} {esc} d{d}: listo',flush=True)
    guardar(out/'finalizado.json',dict(**entrada,completo=True,inferencia_duplicada_identica=True,
            sha256_resultados=sha(out/'resultados.csv'),matrices_verificadas=len(cache),
            limitacion='IC de diferencias pareadas sólo original; A/B comparadores históricos agregados'))
    guardar(out/'estado.json',dict(estado='completo',anio=anio))


if __name__=='__main__':main()
