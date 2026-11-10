"""Primer día del episodio ya registrado: comparación pareada, sin nuevo ajuste."""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-raw-mpl')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[2]
r=root/'results/tinto_raw_20261109/episodio_primera_semana1'
days=pd.read_csv(r/'dias.csv');i=int(np.flatnonzero(days.ataque.to_numpy())[0])
a=np.load(r/'original_imagen.npy')[i];b=np.load(r/'alterada_imagen.npy')[i]
fig,axes=plt.subplots(1,2,figsize=(10,5.5),layout='constrained')
for ax,data,title in zip(axes,[a,b],['Original · sin ataque inyectado','Mismo día · ataque +50 %']):
 im=ax.imshow(data,cmap='viridis',vmin=min(0,a.min(),b.min()),vmax=max(1,a.max(),b.max()),interpolation='nearest')
 ax.set(title=title,xlabel='Columna del píxel',ylabel='Fila del píxel');ax.set_xticks([0,8,16,24,31]);ax.set_yticks([0,8,16,24,31])
fig.colorbar(im,ax=list(axes),shrink=.8,label='Valor escalado por hora (MinMax)')
fig.suptitle('TINTO-PCA · SAC · 3 de enero de 2022 · 32×32\nMismo mapa y escala · 21 mediciones observadas y 3 faltantes rellenados con 0',fontsize=12)
fig.savefig(r/'comparacion_original_ataque.png',dpi=170)
print(r/'comparacion_original_ataque.png')
