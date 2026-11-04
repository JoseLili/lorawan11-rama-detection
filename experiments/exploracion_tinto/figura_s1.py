"""Ejemplo fijo SAC2022-01-16; representación, no predicciones."""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-s1-mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parents[2]/'results/exploracion_tinto_2022/s1_20261031'
x=np.load(B/'preparacion1/ejemplo_limpia.npy');y=np.load(B/'preparacion1/ejemplo_alterada.npy')
lo=min(0,float(x.min()),float(y.min()));hi=max(1,float(x.max()),float(y.max()))
for name,data in [('limpia',x),('alterada',y)]:
 fig,axs=plt.subplots(4,6,figsize=(13,9),layout='constrained')
 for h,ax in enumerate(axs.flat):
  im=ax.imshow(data[h,:,:,0],cmap='viridis',vmin=lo,vmax=hi,interpolation='nearest');ax.set_title(f'{h:02d}:00');ax.set_xticks([0,31]);ax.set_yticks([0,31])
 fig.colorbar(im,ax=list(axs.flat),shrink=.65,label='Intensidad MinMax (adimensional)')
 fig.suptitle(f'S1 · SAC · 2022-01-16 · {name}\n24 imágenes de 17 características · ejes: columna/fila del píxel; no geografía')
 fig.savefig(B/f'24_horas_{name}.png',dpi=130);plt.close(fig)
