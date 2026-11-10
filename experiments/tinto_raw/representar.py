"""TINTO nativo: O3 estación-día, control completo y rellenos autorizados."""
import os,sys,json,argparse,tempfile,hashlib
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
 df=pd.read_csv(source,index_col=0,parse_dates=True)
 stations=[s for s in ESTACIONES if s not in ['XAL','HGM']]
 X=np.concatenate([df[s].to_numpy().reshape(-1,24) for s in stations])
 dates=np.tile(df.index[::24].to_numpy(),len(stations));names=np.repeat(stations,len(df)//24)
 tr=pd.DatetimeIndex(dates).year<2022
 sac=(names=='SAC')&(pd.DatetimeIndex(dates).year==2022)
 complete=~np.isnan(X).any(axis=1)
 a=np.flatnonzero(sac&complete)[0];b=np.flatnonzero(sac&~complete&~np.isnan(X).all(axis=1))[0]
 cols=[f'h{h:02}' for h in range(24)];results=[]
 config=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),ejemplo_completo=str(dates[a]),ejemplo_faltantes=str(dates[b]),station='SAC',tinto='1.3.1',raw_ppb=True,inputs=cols,seed=42,ajuste='2020–2021',validation='2022',detector='ninguno')
 (out/'configuracion.json').write_text(json.dumps(config,indent=2)+'\n')
 pd.DataFrame({'fecha':dates,'estacion':names,'ajuste':tr,'completo':complete}).to_csv(out/'manifiesto.csv',index=False)
 for name,fill in [('completos',None),('relleno0',0),('relleno99',99)]:
  z=X[tr&complete] if fill is None else np.nan_to_num(X[tr],nan=fill)
  sc=MinMaxScaler(clip=False).fit(z);train=pd.DataFrame(sc.transform(z),columns=cols);train['etiqueta']=0
  pd.DataFrame({'feature':cols,'scale':sc.scale_,'offset':sc.min_}).to_csv(out/f'{name}_escala.csv',index=False)
  base=sc.transform(X[a:a+1])[0];probes=np.tile(base,(25,1));probes[1:]+=np.diag(sc.scale_)
  if fill is not None: probes=np.vstack([probes,sc.transform(np.nan_to_num(X[b:b+1],nan=fill))])
  p=pd.DataFrame(probes,columns=cols);p['etiqueta']=0
  for size in [32,64]:
   model=TINTO(transformer=None,problem='classification',pixels=size,algorithm='PCA',blur=False,zoom=1,format='npy',random_seed=42)
   model.fit(train);mp=model._get_features_mapping();mp.to_csv(out/f'{name}_{size}_mapa.csv',index=False)
   with tempfile.TemporaryDirectory() as td:
    model.transform(p,td);paths=sorted((Path(td)/'00').glob('*.npy'));imgs=[np.load(f) for f in paths]
   assert len(imgs)==len(probes)
   expected=np.zeros((size,size))
   for v,rc in zip(base,mp[['row','column']].to_numpy(int)):expected[tuple(rc)]=v
   np.testing.assert_array_equal(expected,imgs[0])
   hidden=sum(np.array_equal(imgs[0],im) for im in imgs[1:25])
   np.save(out/f'{name}_{size}_completo.npy',imgs[0])
   if fill is not None: np.save(out/f'{name}_{size}_faltantes.npy',imgs[-1])
   results.append(dict(brazo=name,lado=size,filas_ajuste=len(z),columnas=24,pixeles_ocupados=len(mp[['row','column']].drop_duplicates()),cambios_1ppb_ocultos=hidden))
 fig,axs=plt.subplots(2,3,figsize=(11,7),layout='constrained')
 for k,name in enumerate(['completos','relleno0','relleno99']):
  for row,kind in enumerate(['completo','faltantes']):
   path=out/f'{name}_32_{kind}.npy';ax=axs[row,k]
   if not path.exists():ax.text(.5,.5,'Sin imputación:\nno se transforma este día',ha='center',va='center');ax.axis('off');continue
   im=ax.imshow(np.load(path),vmin=0,vmax=1,cmap='viridis',interpolation='nearest');ax.set_title(f'{name} · día {kind}');ax.set_xlabel('Columna de píxel');ax.set_ylabel('Fila de píxel')
 fig.colorbar(im,ax=list(axs.flat),label='Valor MinMax (escala propia de cada brazo)');fig.suptitle('O3 raw · SAC · TINTO-PCA nativo 32×32\nMismas fechas entre brazos; no son ejes estación–hora ni mapas de ataques')
 fig.savefig(out/'comparacion.png',dpi=140);plt.close(fig)
 pd.DataFrame(results).to_csv(out/'resultados.csv',index=False);print(pd.DataFrame(results).to_string(index=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=1):run(a.salida)
