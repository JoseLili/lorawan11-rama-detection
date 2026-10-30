"""Paquete permitido: código y Barcelona UTC hasta 2016, sin examen/calibración."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'results/barcelona_paraad/colab_20261029'
    stage=out/'paquete'; stage.mkdir(parents=True,exist_ok=False)
    ent=stage/'entrada'; ent.mkdir()
    w=ROOT/'results/barcelona_paraad/ventanas_v1'
    ataques=ROOT/'results/barcelona_paraad/ataques_proporcionales_v1'
    for base in [w,ataques]:
        reg=json.loads((base/'registro.json').read_text())
        if base==w:
            for n,h in reg['sha256_salidas'].items(): assert sha(base/n)==h
        else:
            for n,h in reg['sha256_completos'].items(): assert sha(base/n)==h
    audit=json.loads((ataques/'verificacion_final.json').read_text())
    assert audit['unidades_verificadas']==150
    assert audit['sha256_registro']==sha(ataques/'registro.json')
    for nombre,salida in [('valores.parquet','valores.parquet'),('perfiles_causales.parquet','perfiles.parquet'),
                           ('reloj.parquet','reloj.parquet'),('horas_validas_l0.parquet','horas_l0.parquet'),
                           ('horas_validas_v4.parquet','horas_v4.parquet')]:
        d=pd.read_parquet(w/nombre); d=d[d.index.year<=2016]
        assert d.index.max().year==2016
        d.to_parquet(ent/salida)
        n=len(d)
    for fase in ['seleccion','definitivo']:
        np.save(ent/f'z_{fase}.npy',np.load(w/f'z_{fase}.npy',mmap_mode='r')[:n],allow_pickle=False)
        shutil.copyfile(w/f'escalas_{fase}.csv',ent/f'escalas_{fase}.csv')
    sd=pd.read_parquet(w/'estacion_dias.parquet')
    sd[sd.dia_utc.dt.year.between(2014,2016)].to_parquet(ent/'estacion_dias.parquet',index=False)
    shutil.copyfile(w/'vecinas.json',ent/'vecinas.json')
    codes=json.loads((w/'registro.json').read_text())['orden_estaciones']
    (ent/'codigos.json').write_text(json.dumps(codes)+'\n')
    for pref,num in [('ajuste_inicial',20),('validacion',10),('ajuste_definitivo',20)]:
        for i in range(1,num+1):
            nombre=f'{pref}_{i:02}'
            src=ataques/nombre/'d50'; dst=ent/'ataques'/nombre; dst.mkdir(parents=True)
            meta=json.loads((src/'completo.json').read_text())
            for archivo in ['valores_alterados.parquet','etiquetas_hora.parquet','l0_features.npy']:
                assert sha(src/archivo)==meta['sha256_salidas'][archivo]
                shutil.copyfile(src/archivo,dst/archivo)
            v=pd.read_parquet(dst/'valores_alterados.parquet')
            assert v.index.max().year<=2016
    fuentes=['src/__init__.py','src/detect/__init__.py','src/ingest/__init__.py','src/ingest/rama.py']+[f'src/detect/{s}.py' for s in
               ['lstm','lstm_red','lstm_local','evaluacion_red','multianual','paraad']]
    fuentes+=['experiments/barcelona/preparar_ventanas.py','experiments/barcelona/entrenar_colab.py']
    for nombre in fuentes:
        p=stage/nombre;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/nombre,p)
    for nombre in ['experiments/__init__.py','experiments/barcelona/__init__.py']:
        p=stage/nombre;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
    paquetes='tensorflow==2.21.0\nkeras==3.13.2\nnumpy==2.1.3\npandas==2.2.3\npyarrow==23.0.1\n'
    (stage/'requirements.txt').write_text(paquetes)
    manifiesto=dict(alcance='Barcelona UTC hasta 2016; sin calibración 2017 ni prueba 2018–2019; sin credenciales/PDF',
                    columnas=13, calendarios_d50=50, semilla=42,
                    politica='Sólo CPU, un hilo, selección y definitivo dos veces; no elegir con examen',
                    archivos={str(p.relative_to(stage)):sha(p) for p in sorted(stage.rglob('*')) if p.is_file()})
    (ent/'registro_paquete.json').write_text(json.dumps(manifiesto,ensure_ascii=False,indent=2)+'\n')
    paquete=out/'barcelona_entrenamiento.tar.gz'
    with tarfile.open(paquete,'w:gz') as tar:
        for p in sorted(stage.rglob('*')):
            if p.is_file():tar.add(p,arcname=str(p.relative_to(stage)),recursive=False)
    (out/'transferencia.json').write_text(json.dumps(dict(nombre=paquete.name,bytes=paquete.stat().st_size,
            sha256=sha(paquete),archivos=len(manifiesto['archivos']),alcance=manifiesto['alcance']),ensure_ascii=False,indent=2)+'\n')
    print((out/'transferencia.json').read_text())


if __name__=='__main__': main()
