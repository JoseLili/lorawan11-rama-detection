"""Prueba y dos corridas B12; sin reintentos. Empaqueta incluso ante error."""
from pathlib import Path
import subprocess,sys,os,json,time,tarfile,hashlib
R=Path('/content/b12');S=R/'salidas'
def state(**k):
 p=S/'ESTADO.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(k,indent=2)+'\n');q.replace(p)
def job(name,prueba=False):
 state(fase=name)
 with (S/(name+'.log')).open('w') as log:
  cmd=[sys.executable,'-u',str(R/'b12_colab.py'),'--paquete',str(R/'paquete'),'--variante','B12','--salida',str(S/name),'--corrida','2' if name.endswith('2') else '1']+(['--prueba'] if prueba else [])
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,TF_CPP_MIN_LOG_LEVEL='2',TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='1'))
  try: code=p.wait(timeout=6*3600)
  except subprocess.TimeoutExpired:
   p.terminate();p.wait(timeout=30);raise RuntimeError('Presupuesto excedido; corrida incompleta')
  assert code==0 and (S/name/'LISTO').exists(),f'Falló {name}, código {code}'
def main():
 S.mkdir(exist_ok=False)
 try:
  # Cotejo del codificador ejecutado por TF contra NumPy de precisión registrada.
  import tensorflow as tf,numpy as np,pandas as pd,keras
  import b12_colab as b
  assert tf.config.list_physical_devices('GPU'),'No GPU; no iniciar entrenamiento'
  for g in tf.config.list_physical_devices('GPU'):tf.config.experimental.set_memory_growth(g,True)
  paq=R/'paquete';meta=json.loads((paq/'meta.json').read_text());local=np.array(meta['indices_locales'],np.int32)
  lado,src,scale,offset=b.mapa(paq,False);encode=b.hacer_imagenes(False,lado,src,scale,offset,local)
  F=np.load(paq/'F_limpia_2020_2022.npy');t=np.array([731*24+11,731*24+23],np.int32);j=np.array([0,0],np.int32)
  actual=encode(tf.constant(F[None]),tf.constant([0,0]),tf.constant(t),tf.constant(j)).numpy()
  raw=F[t[:,None]+np.arange(-11,1)][...,local[0]].reshape(2,204)
  vals=(raw.astype(float)*scale+offset).astype(np.float32);m=pd.read_csv(paq/'mapa_B12.csv');expect=np.zeros((2,32,32,1),np.float32);expect[:,m.row,m.column,0]=vals
  np.testing.assert_array_equal(actual,expect)
  (S/'control_codificador.json').write_text(json.dumps(dict(exacto=True,tensorflow=tf.__version__,keras=keras.__version__,gpu=[tf.config.experimental.get_device_details(g).get('device_name') for g in tf.config.list_physical_devices('GPU')]),indent=2))
  job('prueba1',True);job('prueba2',True)
  for f in ['historia.csv','puntajes_dia_2022.npz']:
   if f.endswith('.npz'):
    a=np.load(S/'prueba1'/f);c=np.load(S/'prueba2'/f)
    for key in a.files:np.testing.assert_array_equal(a[key],c[key])
   else: assert (S/'prueba1'/f).read_bytes()==(S/'prueba2'/f).read_bytes()
  job('B12_c1');job('B12_c2')
  assert (S/'B12_c1/historia.csv').read_bytes()==(S/'B12_c2/historia.csv').read_bytes()
  a=np.load(S/'B12_c1/puntajes_dia_2022.npz');c=np.load(S/'B12_c2/puntajes_dia_2022.npz')
  for key in a.files:np.testing.assert_array_equal(a[key],c[key])
  models=[keras.models.load_model(S/n/'modelo_mejor.keras',compile=False) for n in ['B12_c1','B12_c2']]
  for w,v in zip(models[0].get_weights(),models[1].get_weights()):np.testing.assert_array_equal(w,v)
  state(fase='completado',reproducibilidad=True)
 except BaseException as e:state(fase='error',error=repr(e))
 finally:
  dst=R/'resultados.tar.gz'
  with tarfile.open(dst,'w:gz') as tar:tar.add(S,arcname='salidas')
  (R/'DESCARGA.json').write_text(json.dumps(dict(ruta=str(dst),bytes=dst.stat().st_size,sha256=hashlib.sha256(dst.read_bytes()).hexdigest()),indent=2))
if __name__=='__main__':main()
