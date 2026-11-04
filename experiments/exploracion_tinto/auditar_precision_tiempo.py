"""Auditoría sin entrenamiento: escalado congelado T1 y particiones temporales."""
from pathlib import Path
import sys, json, hashlib, argparse
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.detect import evaluacion_red as ev, anomalias_red as ar, lstm_local as ll
B=ROOT/'results/exploracion_tinto_2022'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out):
    out.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/'results/anomalias_red_v1/matrices/matriz_limpia_2020_2022.csv.gz',B/'prototipos_20261028/corrida1/L0_408/mapa_unico_32.csv',B/'hora_compacta_20261028/corrida1/L0_408/escalador.csv',B/'auditoria_l0_20261028/corrida1/vecinas_y_escalas.json',ROOT/'results/inventario_multianual/estaciones_geografia.csv']
    x=ar.leer_matriz(sources[0]); mp=pd.read_csv(sources[1]); sc=pd.read_csv(sources[2]); frozen=json.loads(sources[3].read_text())
    assert mp.feature.tolist()==sc.feature.tolist()
    rc=mp[['row','column']].to_numpy(int); assert len(np.unique(rc,axis=0))==408
    assert x.index.equals(pd.date_range(x.index[0],x.index[-1],freq='h'))
    hours=x.index.hour.to_numpy(); clock=x[['hora_sin','hora_cos']].to_numpy()
    np.testing.assert_allclose(clock,np.column_stack([np.sin(2*np.pi*hours/24),np.cos(2*np.pi*hours/24)]),atol=1e-14)
    midnight=np.flatnonzero(hours[1:]==0)+1
    assert np.all(hours[midnight-1]==23)
    _,sigma=ev.normalizacion(x); relative=ev.relativas(x)
    stations=ev.estaciones_de(x); neighbors=ev.vecinas_de(stations,pd.read_csv(sources[4],index_col='station'))
    par=ev.ajustar_vecinas('a14',x.loc['2020':'2021'],sigma,neighbors,'media')
    assert par.vecinas==frozen['vecinas']
    F=ev.entradas_de('vecinas',x,None,sigma,par)
    rows=[]; totals={'ventanas_diarias':0,'valores_recuperados':0,'fuera_0_1':0}; maxerr=0.
    ends=np.flatnonzero((x.index.year==2022)&(hours==23))
    for s in frozen['objetivos']:
        raw=x[f'{s}_valor']; base=raw-relative[s]
        valid=(x.index.year==2022)&x[f'{s}_mascara'].eq(1)&base.notna()
        b=base[valid].to_numpy(); r=raw[valid].to_numpy(); assert len(b)>0
        for j, feature in enumerate(sc.feature):
            if not feature.endswith('_obj_rel'): continue
            a,o=float(sc.scale.iloc[j]),float(sc.offset.iloc[j])
            for label,left,right in [('50_51',np.full(len(b),50.),np.full(len(b),51.)),('real_mas_1',r,r+1),('real_menos_1',r,r-1)]:
                # Misma conversión float32 que entradas_relativas, perfil causal fijo.
                p=(((left-b)/sigma[s]).astype(np.float32).astype(np.float64)*a+o).astype(np.float32)
                q=(((right-b)/sigma[s]).astype(np.float32).astype(np.float64)*a+o).astype(np.float32)
                ideal=(right-b)/sigma[s]*a+o
                assert np.isfinite(p).all() and np.isfinite(q).all()
                collapsed=int(np.count_nonzero(p==q)); assert collapsed==0
                rows.append(dict(estacion=s,feature=feature,prueba=label,n=len(b),iguales=collapsed,delta_min=float(np.abs(q-p).min()),delta_max=float(np.abs(q-p).max()),error_max_float64=float(np.abs(q.astype(float)-ideal).max())))
        windows=ll.ventanas_locales(F,stations,par.vecinas,s,ends)
        assert windows.shape==(len(ends),24,17)
        halves=windows.reshape(len(ends),2,12,17)
        np.testing.assert_array_equal(halves.reshape(-1,24,17),windows)
        np.testing.assert_array_equal(np.stack([windows[:,h,:] for h in range(24)],axis=1),windows)
        rawflat=windows.reshape(-1,408)
        ideal=rawflat.astype(float)*sc.scale.to_numpy()+sc.offset.to_numpy(); scaled=ideal.astype(np.float32)
        im=np.zeros((len(ends),32,32),np.float32); im[:,rc[:,0],rc[:,1]]=scaled
        np.testing.assert_array_equal(im[:,rc[:,0],rc[:,1]],scaled)
        assert np.isfinite(im).all()
        maxerr=max(maxerr,float(np.abs(ideal-scaled).max()))
        totals['ventanas_diarias']+=len(ends); totals['valores_recuperados']+=scaled.size
        totals['fuera_0_1']+=int(np.count_nonzero((scaled<0)|(scaled>1)))
        if s==frozen['objetivos'][0]:
            np.save(out/'ejemplo_24x17.npy',windows[0]); np.save(out/'ejemplo_2x12x17.npy',halves[0]); np.save(out/'ejemplo_imagen_D24.npy',im[0])
    table=pd.DataFrame(rows); table.to_csv(out/'precision_por_estacion_y_desfase.csv',index=False)
    times=x.index[x.index.year==2022]
    timeline=pd.DataFrame({'timestamp':times,'dia':times.normalize(),'hora':times.hour,'bloque_12h':times.hour//12,'posicion_bloque':times.hour%12})
    assert timeline.groupby('dia').size().eq(24).all()
    assert timeline.groupby(['dia','bloque_12h']).size().eq(12).all()
    timeline.to_csv(out/'trazabilidad_temporal_2022.csv',index=False)
    report=dict(estado='SUPERADA_EN_ALCANCE_AUDITADO',**totals,pares_precision=int(table.n.sum()),colapsos=int(table.iguales.sum()),delta_min_50_51=float(table[table.prueba=='50_51'].delta_min.min()),error_max_imagen_float32=maxerr,transiciones_medianoche=len(midnight),horas_2022=len(timeline),modelos_cargados=False,entrenamiento=False,alcance='Escalador y mapa D24 congelados T1; todas las estaciones objetivo y días 2022; bloques y secuencia comprobados como tensores, mapas B12/S1 pendientes de etapa 2.',limites=['Perfil causal fijo: se audita característica relativa objetivo, no se simulan cambios completos de a14 ni ataques nuevos.','Normalización heredada de L0; no se ajusta un escalador nuevo.','Precisión numérica no demuestra detectabilidad ni percepción visual.','Secuencias diarias no cruzan medianoche.'],fuentes_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},codigo_sha256=sha(Path(__file__)),versiones={'numpy':np.__version__,'pandas':pd.__version__})
    (out/'informe.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);run(p.parse_args().salida)
