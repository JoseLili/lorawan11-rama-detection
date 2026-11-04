"""Paso 2 registrado: TINTO real + asignación única; no detector."""
from pathlib import Path
import os,sys,argparse,json,hashlib,math
os.environ.setdefault('MPLCONFIGDIR','/tmp/tinto-mpl-temporal')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
p=argparse.ArgumentParser();p.add_argument('--wheel',type=Path,required=True);p.add_argument('--salida',type=Path,required=True);args=p.parse_args()
# Entorno científico del sistema; sklearn disponible en el entorno del proyecto.
ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'.venv/lib/python3.14/site-packages'))
sys.path.insert(0,str(args.wheel.resolve()))
import numpy as np,pandas as pd,scipy,sklearn
from sklearn.preprocessing import MinMaxScaler
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from threadpoolctl import threadpool_limits
from TINTOlib.tinto import TINTO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=ROOT/'results/exploracion_tinto_2022'; A=B/'auditoria_l0_20261028/corrida1'; E=B/'imagenes_reales_20261029/corrida1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
out=args.salida;out.mkdir(parents=True,exist_ok=False)
X=np.load(A/'X_muestra.npy');meta=pd.read_csv(A/'manifiesto_muestra.csv');dic=pd.read_csv(A/'diccionario_408.csv')
assert X.shape==(19840,24,17)
assert meta.hora_inicio.str[:4].isin(['2020','2021']).all() and meta.hora_final.str[:4].isin(['2020','2021']).all()
roles=[s.split('_',1)[1] for s in dic.nombre[:17]]
clean=np.load(E/'entrada_limpia_24x17.npy');altered=np.load(E/'entrada_alterada_24x17.npy')
sources=[A/'X_muestra.npy',A/'manifiesto_muestra.csv',A/'diccionario_408.csv',E/'entrada_limpia_24x17.npy',E/'entrada_alterada_24x17.npy']
write(out/'configuracion.json',dict(fuentes={str(p.relative_to(ROOT)):sha(p) for p in sources},wheel_sha256=sha(args.wheel),codigo_sha256=sha(Path(__file__)),semilla=42,PCA_filas=20000,MinMax='todas las filas de entrenamiento; clip=False',versiones=dict(numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__),detector=False))
reports=[];panels=[]
with threadpool_limits(limits=1):
 for name,h in [('B12',12),('S1',1)]:
    d=out/name;d.mkdir();n=h*17; raw=X.reshape(-1,n).astype(float)
    columns=[f'pos{k:02d}_{r}' for k in range(h) for r in roles]
    scaler=MinMaxScaler(clip=False).fit(raw);scaled=scaler.transform(raw)
    ids=np.sort(np.random.default_rng(42).choice(len(raw),20000,replace=False));np.save(d/'indices_ajuste_PCA.npy',ids)
    pd.DataFrame({'fila_pool':ids,'fila_ventana_original':ids//(24//h),'paso_en_ventana':ids%(24//h)}).to_csv(d/'procedencia_PCA.csv',index=False)
    pd.DataFrame(dict(feature=columns,minimo=scaler.data_min_,maximo=scaler.data_max_,scale=scaler.scale_,offset=scaler.min_)).to_csv(d/'escalador.csv',index=False)
    train=pd.DataFrame(scaled[ids],columns=columns);train['etiqueta_auxiliar_no_predictora']=0
    model=TINTO(transformer=None,pixels=32,algorithm='PCA',blur=False,zoom=1,format='npy',random_seed=42)
    model.fit(train);xy=model.obtain_coord.copy();np.save(d/'coordenadas_PCA.npy',xy)
    native=model._get_features_mapping();old=native[['row','column']].to_numpy(int)
    centered=xy-xy.mean(axis=0);radius=math.ceil(np.linalg.norm(centered,axis=1).max());assert radius>0
    target=np.abs((centered-[-radius,radius])/(2*radius))*31
    np.testing.assert_array_equal(np.round(target),old)
    grid=np.stack(np.meshgrid(np.arange(32),np.arange(32),indexing='ij'),axis=-1).reshape(-1,2)
    rr,cc=linear_sum_assignment(cdist(target,grid,metric='sqeuclidean'));np.testing.assert_array_equal(rr,np.arange(n));rc=grid[cc]
    assert len(np.unique(rc,axis=0))==n
    pd.DataFrame(dict(feature=columns,row=rc[:,0],column=rc[:,1],row_nativo=old[:,0],column_nativo=old[:,1])).to_csv(d/'mapa_unico_32.csv',index=False)
    def encode(v):
        image=np.zeros((len(v),32,32),np.float32);image[:,rc[:,0],rc[:,1]]=v
        np.testing.assert_array_equal(image[:,rc[:,0],rc[:,1]],v);assert np.isfinite(image).all()
        return image
    outside=0
    for start in range(0,len(raw),512):
        vals=scaled[start:start+512].astype(np.float32);encode(vals);outside+=int(np.count_nonzero((vals<0)|(vals>1)))
    for j in range(n):
        v=scaled[0].astype(np.float32);w=v.copy();w[j]+=np.float32(.125)
        assert np.count_nonzero(encode(w[None])-encode(v[None]))==1
    ex=[]
    for label,values in [('limpia',clean),('alterada',altered)]:
        vals=scaler.transform(values.reshape(-1,n)).astype(np.float32);im=encode(vals)
        np.save(d/f'ejemplo_{label}.npy',im);ex.append(im)
        recovered=im[:,rc[:,0],rc[:,1]]
        np.testing.assert_array_equal(recovered,vals)
    np.save(d/'ejemplo_diferencia.npy',ex[1]-ex[0]);panels.append((name,ex))
    reports.append(dict(variante=name,horas_por_imagen=h,caracteristicas=n,filas_recuperadas=len(raw),valores_recuperados=int(scaled.size),pca_filas=len(ids),pixeles_unicos=n,pixeles_unicos_nativos=len(np.unique(old,axis=0)),cambios_ocultos=0,fuera_rango_ajuste=outside,imagenes_por_dia=24//h,pixeles_cambiados_ejemplo=int(np.count_nonzero(ex[1]-ex[0]))))
write(out/'resultados.json',reports)
fig,axes=plt.subplots(2,3,figsize=(12,8),layout='constrained')
for i in range(2):
 for j,data in enumerate([panels[0][1][0][i],panels[0][1][1][i],panels[0][1][1][i]-panels[0][1][0][i]]):
    bound=max(float(np.abs(panels[0][1][1]-panels[0][1][0]).max()),1e-8)
    kw=dict(cmap='RdBu_r',vmin=-bound,vmax=bound) if j==2 else dict(cmap='viridis',vmin=min(0,float(np.min(panels[0][1]))),vmax=max(1,float(np.max(panels[0][1]))))
    plot=axes[i,j].imshow(data,interpolation='nearest',**kw);axes[i,j].set(title=f'{i*12:02d}:00–{i*12+11:02d}:00 · '+['Limpia','Alterada','Diferencia'][j],xlabel='Columna de píxel',ylabel='Fila de píxel');fig.colorbar(plot,ax=axes[i,j],label='Intensidad escalada' if j<2 else 'Cambio de intensidad')
fig.suptitle('SAC · 2022-01-16 · dos imágenes de 12 h · TINTO-PCA + asignación única')
fig.savefig(out/'bloques_12h.png',dpi=130);plt.close(fig)
print(json.dumps(reports))
