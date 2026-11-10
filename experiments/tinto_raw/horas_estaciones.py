"""Comparación anotada: estaciones prefijadas SAC, CCA y PED; mismo día/mapa."""
from pathlib import Path
import os,json
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-raw-mpl')
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];r=ROOT/'results/tinto_raw_20261109'
out=r/'horas_estaciones';out.mkdir(exist_ok=True)
df=pd.read_csv(r/'auditoria1/o3_raw_ppb.csv',index_col=0,parse_dates=True)
m=pd.read_csv(r/'representacion1/completos_32_mapa.csv');e=pd.read_csv(r/'representacion1/completos_escala.csv')
coords=m[['row','column']].to_numpy(int);assert len(set(map(tuple,coords)))==24
scale=e.scale.to_numpy();offset=e.offset.to_numpy();entries=[]
for station in ['SAC','CCA','PED']:
 raw=df.loc['2022-01-03',station].to_numpy();assert len(raw)==24
 observed=np.isfinite(raw);a=np.nan_to_num(raw,nan=0);b=a*1.5
 ims=[]
 for v in [a,b]:
  im=np.zeros((32,32));im[coords[:,0],coords[:,1]]=v*scale+offset;ims.append(im)
 entries.append((station,raw,observed,ims))
lo=min(0,min(float(im.min()) for _,_,_,ims in entries for im in ims));hi=max(1,max(float(im.max()) for _,_,_,ims in entries for im in ims))
for station,raw,observed,ims in entries:
 fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
 for ax,im,title in zip(axes,ims,['Original sin inyección','Ataque simulado +50 %']):
  image=ax.imshow(im,cmap='viridis',vmin=lo,vmax=hi,interpolation='nearest')
  for h,(row,col) in enumerate(coords):
   label=f'{h:02}' if observed[h] else f'{h:02}*'
   if h in [0,1,2,8]:
    positions={2:(8.5,7),1:(16,7),8:(8.5,10),0:(16,10)}
    ax.annotate(label,(col,row),xytext=positions[h],ha='center',va='center',fontsize=7,color='white',arrowprops=dict(arrowstyle='-',color='white',lw=.6))
   else: ax.text(col,row,label,ha='center',va='center',fontsize=6.5,color='white',fontweight='bold')
  ax.set(title=title,xlabel='Columna del píxel',ylabel='Fila del píxel');ax.set_xticks([0,8,16,24,31]);ax.set_yticks([0,8,16,24,31])
 fig.colorbar(image,ax=list(axes),shrink=.8,label='Valor MinMax por hora · escala compartida')
 fig.suptitle(f'{station} · 3 enero 2022 · cada número identifica la hora 00–23\n* Dato faltante rellenado con 0 · mismo mapa para todas las estaciones',fontsize=12)
 fig.savefig(out/f'{station}_horas.png',dpi=200);plt.close(fig)
 pd.DataFrame({'hora':np.arange(24),'HORA_archivo':np.arange(1,25),'fila_pixel':coords[:,0],'columna_pixel':coords[:,1],'ppb_original':raw,'ppb_ataque':raw*1.5,'observado':observed}).to_csv(out/f'{station}_detalle.csv',index=False)
 print(station,'observadas',observed.sum(),'faltantes',np.flatnonzero(~observed).tolist())
(out/'README.md').write_text('''# Horas anotadas por estación

SAC, CCA y PED prefijadas antes de visualizar; 2022-01-03 en las tres. Mapa y escala compartidos del control completo 2020–2021; ningún ajuste nuevo. El ataque de CCA/PED es una simulación pareada local +50% de sus propias observaciones, no una nueva ejecución del plan de ataques de red. Sin entrenamiento ni scores. Cada estación se representa por separado.

Las etiquetas 00–23 usan la convención heredada HORA RAMA menos 1; el CSV conserva también HORA original 1–24. Asterisco: ausencia rellenada con0. El color sigue siendo MinMax por columna horaria, no ppb absolutos. Las anotaciones son ayudas de lectura superpuestas al gráfico, no entradas del modelo. Los patrones geométricos coinciden por construcción porque el mapa es común; comparar intensidades, no interpretar coincidencia geométrica como descubrimiento independiente. La proximidad de horas en PCA no garantiza orden cronológico.
''')
