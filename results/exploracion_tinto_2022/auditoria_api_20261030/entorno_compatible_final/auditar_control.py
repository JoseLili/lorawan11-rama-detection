from pathlib import Path
import sys,json,hashlib,tempfile,zipfile
sys.path.append('/usr/lib/python3/dist-packages') # tqdm puro; no instalar/modificar entorno
wheel=next(Path('/tmp/tinto_auditoria_20261030').glob('*.whl'))
sys.path.insert(0,str(wheel))
import numpy as np,pandas as pd,sklearn
from sklearn.preprocessing import MinMaxScaler
from TINTOlib.tinto import TINTO
out=Path('results/exploracion_tinto_2022/auditoria_api_20261030/entorno_compatible_final')
out.mkdir(exist_ok=False)
rng=np.random.default_rng(42)
X=rng.uniform(0,1,(64,8));X[0]=0;X[1]=1
train=pd.DataFrame(X,columns=[f'F{i}' for i in range(8)]);train['y']=0
native=TINTO(pixels=2,algorithm='PCA',blur=False,format='npy',random_seed=42)
native.fit(train)
external=MinMaxScaler().fit(X)
scaled=pd.DataFrame(external.transform(X),columns=train.columns[:-1]);scaled['y']=0
manual=TINTO(transformer=None,pixels=2,algorithm='PCA',blur=False,format='npy',random_seed=42)
manual.fit(scaled)
pd.testing.assert_frame_equal(native._get_features_mapping(),manual._get_features_mapping())
coords=native._get_features_mapping()[['row','column']].to_numpy(int)
# Etiquetas no determinan PCA: cambiar solo y y volver a ajustar.
labels=train.copy();labels['y']=np.arange(len(labels))%2
control=TINTO(pixels=2,algorithm='PCA',blur=False,format='npy',random_seed=42);control.fit(labels)
np.testing.assert_allclose(native.obtain_coord,control.obtain_coord,rtol=0,atol=1e-12)
pd.testing.assert_frame_equal(native._get_features_mapping(),control._get_features_mapping())
groups={}
for i,rc in enumerate(coords):groups.setdefault(tuple(rc),[]).append(i)
collision=next(ids for ids in groups.values() if len(ids)>1)
base=np.full(8,.25);probe=base.copy();probe[collision[0]]=.75
obs=pd.DataFrame([base,probe,base],columns=train.columns[:-1]);obs['y']=[0,0,1]
folder=str((out/'salida_nativa').resolve());native.transform(obs,folder)
a=np.load(Path(folder)/'00/000000.npy');b=np.load(Path(folder)/'00/000001.npy');c=np.load(Path(folder)/'01/000002.npy')
np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a,c)
expected=np.zeros((2,2))
for val,rc in zip(base,coords):expected[tuple(rc)]=val
np.testing.assert_array_equal(a,expected)
manual.transform(obs,str((out/'salida_escalado_externo').resolve()))
np.testing.assert_array_equal(a,np.load(out/'salida_escalado_externo/00/000000.npy'))
report={'tipo':'Prueba tecnica API con datos inventados 64x8; no entrenamiento ni datos RAMA',
 'TINTOlib':'1.3.1','wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
 'versiones':{'numpy':np.__version__,'pandas':pd.__version__,'scikit-learn':sklearn.__version__},
 'etiqueta_excluida_del_mapa_y_pixeles':True,'MinMax_externo_transformer_None_equivale_interno_en_control':True,
 'ultima_caracteristica_sobrescribe_sin_blur':True,'perturbacion_oculta_comprobada':True,
 'npy_sin_colormap_ni_zoom_numerico':{'forma':list(a.shape),'dtype':str(a.dtype),'valor_base':.25},
 'tolerancia_coordenadas_al_cambiar_etiquetas':1e-12,'diferencia_maxima_coordenadas':float(np.max(np.abs(native.obtain_coord-control.obtain_coord))),'mapa_pixeles_etiquetas_igual_exacto':True,
 'limitacion':'Control sintetico pequeno; no repite PCA completo ni evalua deteccion ni certifica la variante propia'}
(out/'verificacion.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
(out/'auditar_control.py').write_text(Path(__file__).read_text())
print(json.dumps(report,indent=2,ensure_ascii=False))
