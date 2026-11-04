"""Comprueba etiquetas, tiempos y mapas S1 antes de entrenar."""
from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.detect import anomalias_red as ar,estacion_dia as ed
from s1_colab import ejemplos
B=ROOT/'results/exploracion_tinto_2022';P=B/'t2_granularidad/paquete'
def run(out):
 out.mkdir(parents=True,exist_ok=False);meta=json.loads((P/'meta.json').read_text());days=pd.to_datetime(meta['dias']);obs=np.load(P/'obs.npy');stats={}
 for n in range(1,21):
  name=f'entrenamiento_{n:02d}';plan=ar.leer_plan(ROOT/f'results/anomalias_red_v1/planes/plan_{name}.csv');y=ed.etiquetas(plan,days,meta['objetivos']).to_numpy().astype(np.uint8)
  np.testing.assert_array_equal(y,np.load(P/f'Ydia_{name}.npy'))
 for split,nums in [('tr',list(range(1,21))),('va',list(range(1,11)))]:
  idx,y=ejemplos('S1',P,meta,nums,split,False);np.save(out/f'indices_{split}.npy',idx);np.save(out/f'etiquetas_{split}.npy',y)
  assert (idx[:,1]%24==23).all();assert ((idx[:,1]<731*24) if split=='tr' else (idx[:,1]>=731*24)).all()
  assert (obs.reshape(-1,24,31).sum(axis=1)[idx[:,1]//24,idx[:,2]]>=12).all()
  stats[split]={'ejemplos':len(y),'positivos':int(y.sum())}
 common=pd.read_csv(B/'preparacion_colab_20261029/resultados_descargados/corrida1/dias_comunes.csv',index_col=0);assert common.columns.tolist()==meta['objetivos'];assert common.to_numpy().sum()==9661
 assert np.all((obs[731*24:].reshape(-1,24,31).sum(axis=1)>=12)|~common.to_numpy(bool))
 mp=B/'mapas_temporales_20261030/corrida1/S1';m=pd.read_csv(mp/'mapa_unico_32.csv');s=pd.read_csv(mp/'escalador.csv');local=np.array(meta['indices_locales']);j=meta['objetivos'].index('SAC');day=731+15
 for label,key in [('limpia','limpia_2020_2022'),('alterada','entrenamiento_01_d50')]:
  F=np.load(P/f'F_{key}.npy');raw=F[day*24:day*24+24][:,local[j]]
  np.testing.assert_array_equal(raw,np.load(B/f'imagenes_reales_20261029/corrida1/entrada_{label}_24x17.npy'))
  v=(raw.reshape(24,17).astype(float)*s.scale.to_numpy()+s.offset.to_numpy()).astype(np.float32);im=np.zeros((24,32,32,1),np.float32);im[:,m.row,m.column,0]=v
  np.testing.assert_array_equal(im[:,m.row,m.column,0],v);np.save(out/f'ejemplo_{label}.npy',im)
 stats['soporte_comun']=9661;stats['modelo_entrenado']=False
 (out/'auditoria.json').write_text(json.dumps(stats,indent=2)+'\n');print(stats)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--salida',type=Path,required=True);run(a.parse_args().salida)
