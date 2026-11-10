"""Episodio predeterminado O3; rasterización con mapa nativo congelado auditado."""
import os,argparse,json,hashlib
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-raw-mpl')
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]

def run(out):
 out.mkdir(parents=True,exist_ok=False)
 r=ROOT/'results/tinto_raw_20261109';src=r/'auditoria1/o3_raw_ppb.csv';mp=r/'representacion1/completos_32_mapa.csv';ep=r/'representacion1/completos_escala.csv'
 x=pd.read_csv(src,index_col=0,parse_dates=True)['SAC'].loc['2022'];daily=x.to_numpy().reshape(-1,24);ok=np.isfinite(daily).all(axis=1)
 start=0;raw=daily[:7].copy();observed=np.isfinite(raw);a=np.nan_to_num(raw,nan=0);b=a.copy();b[2:5]*=1.5
 dates=x.index[::24][start:start+7];m=pd.read_csv(mp);e=pd.read_csv(ep);assert m.feature.tolist()==e.feature.tolist();coords=m[['row','column']].to_numpy(int);assert len(set(map(tuple,coords)))==24
 scale=e.scale.to_numpy();offset=e.offset.to_numpy()
 def encode(v):
  z=v*scale+offset;im=np.zeros((7,32,32));im[:,coords[:,0],coords[:,1]]=z;return im
 ia,ib=encode(a),encode(b);diff=ib-ia
 rec=(ib[:,coords[:,0],coords[:,1]]-offset)/scale
 err=float(np.max(abs(rec-b)));assert err<1e-10
 changed=(a!=b).sum(axis=1);pix=(ia!=ib).sum(axis=(1,2));np.testing.assert_array_equal(changed,pix);assert np.array_equal(ia[[0,1,5,6]],ib[[0,1,5,6]])
 for name,v in [('original_ppb',a),('alterada_ppb',b),('original_imagen',ia),('alterada_imagen',ib),('diferencia',diff)]:np.save(out/f'{name}.npy',v)
 pd.DataFrame({'fecha':dates,'ataque':[False,False,True,True,True,False,False],'mediciones_modificadas':changed,'pixeles_modificados':pix,'faltantes_rellenados':(~observed).sum(axis=1)}).to_csv(out/'dias.csv',index=False)
 pd.DataFrame({'timestamp':x.index[start*24:(start+7)*24],'original_ppb':raw.ravel(),'alterada_ppb':np.where(observed,b,np.nan).ravel()}).to_csv(out/'curva_ppb.csv',index=False)
 report=dict(estacion='SAC',inicio=str(dates[0]),fin=str(dates[-1]),ataque_inicio=str(dates[2]),ataque_fin=str(dates[4]+pd.Timedelta(hours=23)),factor=1.5,faltantes_rellenados=int((~observed).sum()),cambios_ppb=int(changed.sum()),cambios_tensor=int(pix.sum()),error_maximo_reconstruccion_ppb=err,valores_fuera_0_1_original=int(((ia<0)|(ia>1)).sum()),valores_fuera_0_1_alterada=int(((ib<0)|(ib>1)).sum()),fuentes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src,mp,ep,Path(__file__)]},detector='ninguno; mapa TINTO nativo cargado de disco, no reajustado')
 (out/'informe.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 lo=min(0,ia.min(),ib.min());hi=max(1,ia.max(),ib.max());dmax=max(float(diff.max()),1e-10)
 fig,axs=plt.subplots(3,7,figsize=(16,7),layout='constrained')
 for row,data in enumerate([ia,ib,diff]):
  for day in range(7):
   ax=axs[row,day];im=ax.imshow(data[day],interpolation='nearest',cmap='magma' if row==2 else 'viridis',vmin=0 if row==2 else lo,vmax=dmax if row==2 else hi)
   ax.set_xticks([]);ax.set_yticks([])
   if row==0:ax.set_title(dates[day].strftime('%d %b')+ ('\nAtaque +50%' if 2<=day<=4 else '\nControl'),fontsize=10)
   if day==0:ax.set_ylabel(['Original','Alterada','Diferencia'][row],fontsize=11)
  if row in [1,2]:fig.colorbar(im,ax=list(axs[:2].flat) if row==1 else list(axs[2]),shrink=.7,label='Valor MinMax' if row==1 else 'Cambio MinMax')
 fig.suptitle('SAC · siete días · una imagen TINTO por día\n24 horas en posiciones fijas; faltantes = 0 en ambas imágenes; no son ejes temporales')
 fig.savefig(out/'secuencia.png',dpi=140);plt.close(fig)
 fig,(ax,legend)=plt.subplots(1,2,figsize=(13,4.5),gridspec_kw={'width_ratios':[2,1]},layout='constrained')
 times=x.index[start*24:(start+7)*24];ax.plot(times,raw.ravel(),label='Original sin inyección',lw=1.5);ax.plot(times,np.where(observed,b,np.nan).ravel(),label='Con episodio +50%',lw=1.3,ls='--');ax.axvspan(dates[2],dates[5],alpha=.12,color='red',label='Episodio de tres días');ax.set(xlabel='Fecha y hora (convención heredada RAMA)',ylabel='Ozono (ppb)',title='Cambio físico aplicado a las mediciones');ax.legend(fontsize=8);ax.tick_params(axis='x',rotation=25)
 legend.set(xlim=(-1,32),ylim=(32,-1),xlabel='Columna del píxel',ylabel='Fila del píxel',title='Hora → posición fija en TINTO')
 for h,(row,col) in enumerate(coords):legend.scatter(col,row,s=90,c='lightblue',marker='s');legend.text(col,row,f'{h:02}',ha='center',va='center',fontsize=6)
 fig.savefig(out/'curva_y_mapa.png',dpi=170);plt.close(fig)
 print(json.dumps({k:v for k,v in report.items() if k!='fuentes'},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);run(p.parse_args().salida)
