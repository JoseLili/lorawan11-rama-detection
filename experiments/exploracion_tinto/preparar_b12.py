"""Verifica etiquetas/soporte B12; sella paquete, sin entrenamiento."""
from pathlib import Path
import sys,json,hashlib,shutil,argparse,tarfile
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
from src.detect import anomalias_red as ar, estacion_dia as ed
from b12_colab import ejemplos
B=ROOT/'results/exploracion_tinto_2022';SRC=B/'t2_granularidad/paquete';MAP=B/'mapas_temporales_20261030/corrida1/B12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(out):
 out.mkdir(parents=True,exist_ok=False);paq=out/'paquete';paq.mkdir()
 meta=json.loads((SRC/'meta.json').read_text());targets=meta['objetivos'];obs=np.load(SRC/'obs.npy');assert obs.shape==(26304,31)
 records=[]
 for n in range(1,21):
    name=f'entrenamiento_{n:02d}';path=ROOT/f'results/anomalias_red_v1/matrices/matriz_{name}_d50.csv.gz'
    assert sha(path)==meta['sha256_matrices'][name+'_d50']
    x=ar.leer_matriz(path);y=ed.etiquetas_por_hora(x,targets).to_numpy().astype(np.uint8)
    np.testing.assert_array_equal(y,np.load(SRC/f'Yhora_{name}.npy'))
    np.testing.assert_array_equal(obs,x[[s+'_mascara' for s in targets]].to_numpy()==1)
    assert not (y.astype(bool)&~obs).any()
    Yd=np.load(SRC/f'Ydia_{name}.npy');any_day=y.reshape(-1,24,31).any(axis=1)
    records.append(dict(calendario=name,etiquetas_hora_verificadas=y.size,discrepancias_episodio_vs_lectura=int(np.count_nonzero(Yd!=any_day))))
 for path in SRC.glob('*.npy'):
    if path.name.startswith(('F_','Yhora_')) or path.name=='obs.npy':shutil.copy2(path,paq/path.name)
 shutil.copy2(SRC/'meta.json',paq/'meta.json');shutil.copy2(MAP/'mapa_unico_32.csv',paq/'mapa_B12.csv');shutil.copy2(MAP/'escalador.csv',paq/'escalador_B12.csv')
 counts=obs.reshape(-1,2,12,31).sum(axis=2);summaries={}
 for split,nums in [('tr',list(range(1,21))),('va',list(range(1,11)))]:
    idx,y=ejemplos('B12',paq,meta,nums,split,False);np.save(out/f'indices_{split}.npy',idx);np.save(out/f'etiquetas_{split}.npy',y)
    assert np.all(idx[:,1]%24==np.where(idx[:,1]%24==11,11,23))
    assert np.all(counts[idx[:,1]//24,idx[:,1]%24//12,idx[:,2]]>0)
    assert np.all((idx[:,1]<731*24) if split=='tr' else (idx[:,1]>=731*24))
    summaries[split]=dict(ejemplos=len(y),positivos=int(y.sum()),negativos=int((y==0).sum()))
 common_path=B/'preparacion_colab_20261029/resultados_descargados/corrida1/dias_comunes.csv'
 common=pd.read_csv(common_path,index_col=0,parse_dates=True);assert common.columns.tolist()==targets and common.to_numpy().sum()==9661
 assert ((counts[731:].sum(axis=1)>=12)|~common.to_numpy(bool)).all()
 shutil.copy2(common_path,out/'dias_comunes.csv')
 report=dict(etiquetas=records,muestras=summaries,soporte_comun=9661,modelo_entrenado=False)
 (out/'auditoria.json').write_text(json.dumps(report,indent=2)+'\n')
 (paq/'SHA256.json').write_text(json.dumps({p.name:sha(p) for p in sorted(paq.iterdir())},indent=2)+'\n')
 print(json.dumps(summaries))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);main(p.parse_args().salida)
