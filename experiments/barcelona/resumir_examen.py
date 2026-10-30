"""Verifica inferencia congelada y resume métricas pareadas, sin ajustar nada."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score,roc_auc_score

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/barcelona_paraad/examen_colab_2018_2019'
DETECTORES=['l0','v4','paraad']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def medidas(c):
    c=np.asarray(c,dtype='float64');tp,fp,fn,tn=np.moveaxis(c,-1,0)
    def dividir(n,d):return np.divide(n,d,out=np.zeros_like(np.asarray(n,dtype=float)),where=d!=0)
    return dict(precision=dividir(tp,tp+fp),recall=dividir(tp,tp+fn),
                f1=dividir(2*tp,2*tp+fp+fn),f2=dividir(5*tp,5*tp+4*fn+fp))


def conteos(y,p):
    y,p=np.asarray(y,bool),np.asarray(p,bool)
    return np.array([(y&p).sum(),(~y&p).sum(),(y&~p).sum(),(~y&~p).sum()],dtype='int64')


def grupos_conteos(y,p,grupo,n):
    partes=[(y&p).sum(axis=0),(~y&p).sum(axis=0),(y&~p).sum(axis=0),(~y&~p).sum(axis=0)]
    return np.column_stack([np.bincount(grupo,weights=x,minlength=n) for x in partes])


def verificar():
    ent=BASE/'paquete/entrada';reg=json.loads((ent/'registro_paquete.json').read_text())
    for n,h in reg['archivos'].items():assert sha(BASE/'paquete'/n)==h,n
    congelados={}
    for d in DETECTORES:
        r=BASE/d;estado=json.loads((r/'estado_supervisor.json').read_text())
        assert estado['estado']['estado']=='completo' and estado['sesion_liberada'],d
        assert sha(r/'snapshot_ultimo.tar.gz')==estado['sha256_snapshot']
        root=r/'recuperado/salidas'/d;c=json.loads((root/'congelado.json').read_text())
        assert c['igual'] and c['unidades_examen']==102 and len(c['sha256_unidades'])==103
        assert c['entrada']['sha256_paquete']==sha(ent/'registro_paquete.json')
        assert c['entrada']['sha256_script']==sha(BASE/'paquete/experiments/barcelona/evaluar_examen_colab.py')
        assert c['entrada']['sha256_calibracion']==sha(ent/'calibracion_congelado.json')
        for n,h in c['sha256_unidades'].items():
            completo=root/n;assert sha(completo)==h
            for name,h2 in json.loads(completo.read_text())['sha256'].items():assert sha(completo.parent/name)==h2
            assert json.loads((completo.parent/'datos.json').read_text())['igual']
        congelados[d]=sha(root/'congelado.json')
    return congelados


def leer_score(detector,nombre,mask):
    p=BASE/detector/'recuperado/salidas'/detector/nombre/'puntajes.npy'
    s=np.load(p,allow_pickle=False)
    assert s.shape==mask.shape and np.array_equal(np.isfinite(s),mask)
    return s[mask]


def calcular():
    ent=BASE/'paquete/entrada';codes=json.loads((ent/'codigos.json').read_text())
    unidades=json.loads((ent/'unidades.json').read_text());cal=json.loads((ent/'calibracion_congelado.json').read_text())
    agregadas=[];individuales=[];intervalos=[];diferencias=[];tasas=[]
    for ano in [2018,2019]:
        sd=pd.read_parquet(ent/f'dias_{ano}.parquet')
        comun=sd.pivot(index='dia_utc',columns='estacion',values='comun').reindex(columns=codes)
        mask=comun.to_numpy();N=int(mask.sum());assert N=={2018:4549,2019:4567}[ano]
        g=((comun.index.month.to_numpy()-1)[:,None]*len(codes)+np.arange(len(codes))[None,:])[mask]
        _,grupo=np.unique(g,return_inverse=True);G=int(grupo.max()+1)
        pesos=np.random.default_rng([42,238,ano]).multinomial(G,np.full(G,1/G),size=2000)
        limpios={d:leer_score(d,f'limpio_{ano}',mask) for d in DETECTORES}
        for d in DETECTORES:
            for punto,u in cal['umbrales'][d].items():
                alertas=int((limpios[d]>u).sum())
                tasas.append(dict(ano=ano,detector=d,punto=punto,casos=N,alertas=alertas,tasa=alertas/N))
        for delta in [100,50,20,10,5]:
            us=sorted([u for u in unidades if u['ano']==ano and u['delta']==delta],key=lambda u:u['plan'])
            assert len(us)==10
            Y=np.stack([np.load(ent/(u['nombre']+'_y.npy'))[mask] for u in us])
            botas={}
            for d in DETECTORES:
                atacado=np.stack([leer_score(d,u['nombre'],mask) for u in us])
                for estado,S in [('con_ataque',atacado),('sin_ataque',np.broadcast_to(limpios[d],Y.shape))]:
                    yy,ss=Y.ravel(),S.ravel()
                    areas=dict(pr_auc_ap=float(average_precision_score(yy,ss)),roc_auc=float(roc_auc_score(yy,ss))) if np.unique(yy).size==2 else dict(pr_auc_ap=np.nan,roc_auc=np.nan)
                    for punto,u in cal['umbrales'][d].items():
                        pred=S>u;c=conteos(Y,pred);m=medidas(c)
                        clave=dict(ano=ano,delta=delta,detector=d,estado=estado,punto=punto)
                        agregadas.append(dict(**clave,**dict(zip(['tp','fp','fn','tn'],map(int,c))),
                                              **{k:float(v) for k,v in m.items()},**areas,
                                              prevalencia=float(Y.mean()),casos_ambientales=N,exposiciones=int(Y.size),calendarios=10))
                        for j,unidad in enumerate(us):
                            cc=conteos(Y[j],pred[j]);mm=medidas(cc)
                            area_j=dict(pr_auc_ap=float(average_precision_score(Y[j],S[j])),roc_auc=float(roc_auc_score(Y[j],S[j]))) if np.unique(Y[j]).size==2 else dict(pr_auc_ap=np.nan,roc_auc=np.nan)
                            individuales.append(dict(**clave,plan=unidad['plan'],**dict(zip(['tp','fp','fn','tn'],map(int,cc))),
                                                      **{k:float(v) for k,v in mm.items()},**area_j))
                        counts=grupos_conteos(Y,pred,grupo,G)
                        assert np.array_equal(counts.sum(axis=0),c)
                        boot=medidas(pesos@counts)
                        botas[d,estado,punto]=boot['f1']
                        for met in ['f1','precision','recall']:
                            lo,hi=np.quantile(boot[met],[.025,.975],method='linear')
                            intervalos.append(dict(**clave,metrica=met,valor=float(m[met]),inferior=float(lo),superior=float(hi),bloques=G,remuestreos=2000))
            for punto in ['p99','p99.9']:
                for estado in ['con_ataque','sin_ataque']:
                    for a,b in [('l0','v4'),('l0','paraad'),('v4','paraad')]:
                        diff=botas[a,estado,punto]-botas[b,estado,punto]
                        aa=next(x for x in agregadas if all(x[k]==v for k,v in dict(ano=ano,delta=delta,detector=a,estado=estado,punto=punto).items()))
                        bb=next(x for x in agregadas if all(x[k]==v for k,v in dict(ano=ano,delta=delta,detector=b,estado=estado,punto=punto).items()))
                        lo,hi=np.quantile(diff,[.025,.975],method='linear')
                        diferencias.append(dict(ano=ano,delta=delta,punto=punto,estado=estado,comparacion=f'{a}-{b}',
                                                diferencia=aa['f1']-bb['f1'],inferior=float(lo),superior=float(hi),bloques=G,remuestreos=2000))
    return dict(metricas=pd.DataFrame(agregadas),por_calendario=pd.DataFrame(individuales),
                intervalos=pd.DataFrame(intervalos),diferencias_pareadas=pd.DataFrame(diferencias),tasa_limpia=pd.DataFrame(tasas))


def figura(tablas,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colores={'l0':'#2b6cb0','v4':'#d69e2e','paraad':'#2f855a'}
    nombres={'l0':'L0 (supervisado)','v4':'V4','paraad':'PARAAD'}
    fig,axs=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
    levels=[5,10,20,50,100];x=np.arange(5);ancho=.24
    for ax,ano in zip(axs,[2018,2019]):
        for j,d in enumerate(DETECTORES):
            t=tablas['intervalos'];t=t[(t.ano==ano)&(t.detector==d)&(t.estado=='con_ataque')&(t.punto=='p99')&(t.metrica=='f1')].set_index('delta').loc[levels]
            val=t.valor.to_numpy();lo=t.inferior.to_numpy();hi=t.superior.to_numpy()
            ax.bar(x+(j-1)*ancho,val,ancho,color=colores[d],label=nombres[d])
            ax.errorbar(x+(j-1)*ancho,(lo+hi)/2,yerr=(hi-lo)/2,fmt='none',ecolor='black',capsize=2)
            c=tablas['metricas'];c=c[(c.ano==ano)&(c.detector==d)&(c.estado=='sin_ataque')&(c.punto=='p99')]
            assert c.f1.nunique()==1
            ax.axhline(c.f1.iloc[0],color=colores[d],linestyle='--',linewidth=1,alpha=.7)
        ax.set_title(f'{ano} · '+('prueba principal' if ano==2018 else 'complementaria'))
        ax.set_xticks(x,levels);ax.set_xlabel('Intensidad δ (%)');ax.set_ylim(0,1);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axs[0].set_ylabel('F1 por estación-día · umbral p99')
    h,l=axs[0].get_legend_handles_labels();h.append(Line2D([0],[0],color='gray',linestyle='--'));l.append('Sin inyección (color del detector)')
    fig.legend(h,l,loc='upper center',ncol=4,frameon=False);fig.tight_layout(rect=(0,0,1,.91))
    fig.savefig(out/'f1_barcelona_p99.png',dpi=180,metadata={'Software':'Barcelona frozen evaluation'});plt.close(fig)
    (out/'ficha_figura.md').write_text('''# Ficha: F1 Barcelona p99

Eje X: cinco intensidades porcentuales discretas, no intervalos equidistantes
de concentración. Eje Y: F1 por estación-día, 0–1, umbral p99 de2017 limpio.
Barras: confusiones sumadas de diez calendarios pareados por año y δ.
Líneas discontinuas: F1 del dato limpio usando las mismas etiquetas programadas;
no son la tasa limpia de falsas alarmas. Colores identifican el detector.
Error: IC95% de2,000 bootstrap estación×mes, manteniendo juntas las diez
realizaciones. Para diferencias entre métodos ver diferencias_pareadas.csv.
2018 es prueba principal;2019 complementaria. Sus prevalencias pueden diferir.
Modelos cargados de disco: L0 d50 supervisado, V4 y PARAAD sin etiquetas de
ataque en ajuste. Las barras no aíslan el efecto de arquitectura/supervisión.
Datos:13 estaciones propias AMB, misma fuente pública, no ocho exactas del artículo.
No se entrenó, seleccionó o calibró con estos años.
''')


def main():
    congelados=verificar();tablas=calcular();control=calcular()
    for n,t in tablas.items():pd.testing.assert_frame_equal(t,control[n],check_exact=True)
    out=BASE/'resumen';out.mkdir(exist_ok=False)
    for n,t in tablas.items():t.to_csv(out/(n+'.csv'),index=False,float_format='%.17g')
    principal=tablas['metricas'];principal=principal[(principal.estado=='con_ataque')&(principal.punto=='p99')]
    principal.pivot(index=['ano','delta'],columns='detector',values='f1').to_csv(out/'tabla_f1_p99.csv',float_format='%.17g')
    figura(tablas,out)
    control2017={d:json.loads((BASE/d/'recuperado/salidas'/d/'control_calibracion.json').read_text()) for d in DETECTORES}
    registro=dict(igual=True,origen='Modelos cargados de disco; sin reentrenamiento/recalibración',
                    pares_inferencia_examen=306,pares_control_2017=3,matrices_examen=102,controles2017=control2017,
                    sha256_congelados=congelados,sha256_script=sha(Path(__file__)),
                    bootstrap=dict(remuestreos=2000,semilla='[42,238,año]',bloque='estación×mes; diez calendarios juntos'),
                    sha256_salidas={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                    versiones=dict(numpy=np.__version__,pandas=pd.__version__))
    (out/'verificacion_final.json').write_text(json.dumps(registro,ensure_ascii=False,indent=2)+'\n')
    print(principal.pivot(index=['ano','delta'],columns='detector',values='f1').to_string())
    print(tablas['tasa_limpia'].to_string(index=False))


if __name__=='__main__':main()
