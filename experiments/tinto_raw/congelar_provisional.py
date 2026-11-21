"""Crea paquete inmutable por hashes; no entrena ni modifica modelos fuente."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import json,hashlib,shutil
from pathlib import Path
from tensorflow import keras
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'results/tinto_orden_temporal_20261111';out=ROOT/'results/tinto_congelado_20261111'
for k,v in json.loads((base/'checksums.json').read_text()).items():assert sha(base/k)==v,k
out.mkdir(exist_ok=False)
sources={'modelo.keras':base/'cnn_gru_diaria_1/modelo.keras','configuracion_entrenamiento.json':base/'cnn_gru_diaria_1/configuracion.json','historia.csv':base/'cnn_gru_diaria_1/historia.csv','entorno.txt':base/'entorno.txt','manifiesto_entrenamiento.csv':base/'manifiesto.csv','mapa.csv':ROOT/'results/tinto_raw_20261109/representacion1/completos_32_mapa.csv','escala.csv':ROOT/'results/tinto_raw_20261109/representacion1/completos_escala.csv','protocolo.md':ROOT/'experiments/tinto_raw/protocolo_orden_temporal.md','implementacion.py':ROOT/'experiments/tinto_raw/orden_temporal.py'}
for name,p in sources.items():shutil.copyfile(p,out/name);assert sha(p)==sha(out/name)
model=keras.models.load_model(out/'modelo.keras',compile=False)
config=dict(nombre='TINTO-CNN-GRU-D2 provisional',fecha='2026-11-11',parametros=model.count_params(),entrada=[2,32,32,1],salida=24,semilla=42,replica=1,mejor_epoca=16,ajuste='objetivos hasta 2021-09-30',seleccion='2021-10-01 a 2021-12-31',datos_ajuste=4625,datos_seleccion=884,umbral='NO congelado global: calibrar por protocolo, sin actualizar pesos/mapa/escala',estado='congelado provisional; no detector final adoptado',fuentes={name:str(p.relative_to(ROOT)) for name,p in sources.items()})
(out/'congelado.json').write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf-8')
ref=ROOT/'results/linea_base/rev22';expected=json.loads((ref/'modelos_definitivos_sha256.json').read_text());rows=[]
for seed in [42,1,2,3,4]:
    name=f'Vb_R_s{seed}';p=ref/f'modelos_definitivos/{name}.keras';assert sha(p)==expected[name]
    m=keras.models.load_model(p,compile=False);rows.append(dict(modelo=name,parametros=m.count_params(),bytes_keras=p.stat().st_size,sha256=sha(p)))
comparison=dict(tinto=dict(parametros=model.count_params(),bytes_keras=(out/'modelo.keras').stat().st_size),ens_vb_x=dict(parametros=sum(r['parametros'] for r in rows),bytes_keras=sum(r['bytes_keras'] for r in rows),modelos=rows,tau=json.loads((ROOT/'results/linea_base/rev24/decision_tau.json').read_text())['tau']),nota='Bytes .keras incluyen metadatos/optimizador; no equivalen a RAM ni latencia. Ens-Vb-X además usa preprocesamiento y exclusión.')
(out/'complejidad_estatica.json').write_text(json.dumps(comparison,indent=2))
(out/'checksums.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file()},indent=2));print(json.dumps(comparison),flush=True)
