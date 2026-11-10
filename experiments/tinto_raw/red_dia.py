"""TINTO-PCA nativo red-día O3: mapas nuevos, ataque fijo SAC, sin detector."""
import os,sys,json,hashlib,tempfile,argparse
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-raw-mpl')
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from threadpoolctl import threadpool_limits
from TINTOlib.tinto import TINTO
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.detect.multianual import ESTACIONES

def run(out):
 out.mkdir(parents=True,exist_ok=False)
 source=ROOT/'results/tinto_raw_20261109/auditoria1/o3_raw_ppb.csv'
 df=pd.read_csv(source,index_col=0,parse_dates=True);stations=[s for s in ESTACIONES if s!='XAL']
 raw=df[stations].to_numpy().reshape(-1,24*len(stations));dates=df.index[::24]
 names=[f'{s}_h{h:02}' for h in range(24) for s in stations]
 x=np.nan_to_num(raw,nan=0);trainmask=dates.year<2022
 sc=MinMaxScaler(clip=False).fit(x[trainmask]);train=pd.DataFrame(sc.transform(x[trainmask]),columns=names);train['etiqueta']=0
 pd.DataFrame({'feature':names,'scale':sc.scale_,'offset':sc.min_}).to_csv(out/'escalador.csv',index=False)
 i=int(np.flatnonzero(dates==pd.Timestamp('2022-01-03'))[0]);a=x[i].copy();b=a.copy()
 target=np.array([h*len(stations)+stations.index('SAC') for h in range(24)]);b[target]*=1.5
 probes=pd.DataFrame(sc.transform(np.stack([a,b])),columns=names);probes['etiqueta']=0
 reports=[]
 for size in [32,64]:
  model=TINTO(transformer=None,problem='classification',pixels=size,algorithm='PCA',blur=False,zoom=1,format='npy',random_seed=42)
  model.fit(train);mp=model._get_features_mapping();coords=mp[['row','column']].to_numpy(int)
  owners={tuple(c):j for j,c in enumerate(coords)};mp['sobrescrita']=[owners[tuple(c)]!=j for j,c in enumerate(coords)];mp.to_csv(out/f'mapa_{size}.csv',index=False)
  with tempfile.TemporaryDirectory() as td:
   model.transform(probes,td);imgs=[np.load(p) for p in sorted((Path(td)/'00').glob('*.npy'))]
  assert len(imgs)==2
  for k,v in enumerate([a,b]):
   expected=np.zeros((size,size))
   for val,rc in zip(sc.transform(v[None])[0],coords):expected[tuple(rc)]=val
   np.testing.assert_array_equal(expected,imgs[k])
  diff=imgs[1]-imgs[0];changed=np.flatnonzero(a!=b);visible=sum(owners[tuple(coords[j])]==j for j in changed)
  assert np.count_nonzero(diff)==visible
  for name,img in zip(['original','ataque','diferencia'],[*imgs,diff]):np.save(out/f'{name}_{size}.npy',img)
  reports.append(dict(lado=size,caracteristicas=len(names),pixeles_distintos=len(owners),sobrescritas=int(mp.sobrescrita.sum()),mediciones_modificadas=len(changed),cambios_visibles=int(visible),cambios_ocultos=int(len(changed)-visible)))
  lo=min(0,min(im.min() for im in imgs));hi=max(1,max(im.max() for im in imgs));mx=max(float(abs(diff).max()),1e-12)
  fig,axs=plt.subplots(1,3,figsize=(14,5),layout='constrained')
  for k,(ax,img,title) in enumerate(zip(axs,[*imgs,diff],['Red original · sin inyección','Misma red · SAC +50 %','Diferencia · ataque − original'])):
   im=ax.imshow(img,interpolation='nearest',cmap='magma' if k==2 else 'viridis',vmin=0 if k==2 else lo,vmax=mx if k==2 else hi);ax.set(title=title,xlabel='Columna del píxel',ylabel='Fila del píxel')
   if k in [1,2]:fig.colorbar(im,ax=list(axs[:2]) if k==1 else ax,shrink=.75,label='Cambio MinMax' if k==2 else 'Valor MinMax por característica')
  fig.suptitle(f'Red-día O3 · 3 enero 2022 · TINTO-PCA nativo {size}×{size}\n32 estaciones × 24 horas · faltantes=0 · mapa fijo entre versiones',fontsize=12)
  fig.savefig(out/f'comparacion_{size}.png',dpi=160);plt.close(fig)
 report=dict(fecha='2022-01-03',ajuste_dias=int(trainmask.sum()),ajuste='2020–2021 sin inyección',estaciones=stations,ausencias_ejemplo=int(np.isnan(raw[i]).sum()),fuente_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),codigo_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),resultados=reports,detector='ninguno; mapa TINTO recién ajustado',tinto='1.3.1')
 (out/'informe.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(reports))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=1):run(a.salida)
