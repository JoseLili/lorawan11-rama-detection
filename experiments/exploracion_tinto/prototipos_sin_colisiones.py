"""Prototipos de codificación: asignación única y canales; no detectores."""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[2]
AUD=ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1'
PREV=ROOT/'results/exploracion_tinto_2022/hora_compacta_20261028/corrida1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')


def ejecutar(out):
    out.mkdir(parents=True)
    inputs=[AUD/'X_muestra.npy',AUD/'diccionario_408.csv',AUD/'manifiesto_muestra.csv']
    for name in ['L0_408','L0_362']:
        inputs += [PREV/name/'coordenadas_PCA.npy',PREV/name/'escalador.csv']
        inputs += [PREV/name/f'mapa_{s}.csv' for s in [32,64]]
    write(out/'configuracion.json',dict(alcance='Prototipos numéricos; no CNN ni evaluación de anomalías',
        lados=[32,64],variantes=['L0_408','L0_362'],
        asignacion='Mínima suma de distancias euclidianas cuadradas del PCA continuo a píxeles únicos; sin difuminado',
        orden='Columnas originales; píxeles por fila y luego columna; solver SciPy fijado por versión',
        criterio='Todas las entradas numéricas se recuperan exactamente desde la imagen y mapa',
        canales='24 horas × 5 roles × 3 tipos; hora en bloque aparte, sin retirar máscaras ni comparaciones',
        origen='PCA y escaladores cargados del ajuste previo 2020–2021; asignación única calculada ahora',
        fuentes={str(p.relative_to(ROOT)):sha(p) for p in inputs},codigo=sha(Path(__file__)),
        versiones={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','matplotlib']}))
    X=np.load(AUD/'X_muestra.npy',allow_pickle=False)
    dictionary=pd.read_csv(AUD/'diccionario_408.csv')
    meta=pd.read_csv(AUD/'manifiesto_muestra.csv')
    assert X.shape==(19840,24,17) and meta.hora_final.str[:4].isin(['2020','2021']).all()
    base_id=int(meta.index[(meta.etiqueta==0)&(meta.objetivo_observado==1)][0])
    masks=dictionary.tipo.isin(['hora_sin','hora_cos'])
    keep=~masks | (dictionary.desfase_horas==0)
    results=[]
    figures={}
    for name,raw in [('L0_408',X.reshape(-1,408)),('L0_362',X.reshape(-1,408)[:,keep.to_numpy()])]:
        folder=out/name
        folder.mkdir()
        scaler=pd.read_csv(PREV/name/'escalador.csv')
        scaled=raw.astype(np.float64)*scaler.scale.to_numpy()+scaler.offset.to_numpy()
        n=raw.shape[1]
        xy=np.load(PREV/name/'coordenadas_PCA.npy')
        centered=xy-xy.mean(axis=0)
        radius=math.ceil(np.sqrt((centered**2).sum(axis=1)).max())
        # Misma convención fila/columna efectiva de TINTO 1.3.1.
        continuous=np.abs((centered-np.array([-radius,radius]))/(2*radius))
        source_dist=cdist(xy,xy)
        np.fill_diagonal(source_dist,np.inf)
        nn=np.argsort(source_dist,axis=1,kind='stable')[:,:4]
        for size in [32,64]:
            target=continuous*(size-1)
            old=pd.read_csv(PREV/name/f'mapa_{size}.csv')
            np.testing.assert_array_equal(np.round(target),old[['row','column']].to_numpy())
            grid=np.stack(np.meshgrid(np.arange(size),np.arange(size),indexing='ij'),axis=-1).reshape(-1,2)
            cost=cdist(target,grid,metric='sqeuclidean')
            rows,cols=linear_sum_assignment(cost)
            np.testing.assert_array_equal(rows,np.arange(n))
            coords=grid[cols]
            assert len(np.unique(coords,axis=0))==n
            error=0.0
            # Verificar TODAS las ventanas, no solo la observación mostrada.
            for batch in np.array_split(scaled,80):
                encoded=np.zeros((len(batch),size,size),dtype=np.float64)
                encoded[:,coords[:,0],coords[:,1]]=batch
                recovered=encoded[:,coords[:,0],coords[:,1]]
                np.testing.assert_array_equal(recovered,batch)
                error=max(error,float(np.max(np.abs(recovered-batch))))
            baseline=np.zeros((size,size),dtype=np.float64)
            baseline[coords[:,0],coords[:,1]]=scaled[base_id]
            original=np.load(PREV/name/f'imagen_base_{size}.npy')
            # Comprobar una perturbación real del nuevo codificador por cada columna.
            for j in range(n):
                value=scaled[base_id].copy()
                value[j]+=.125 if value[j]<=.5 else -.125
                changed=np.zeros_like(baseline)
                changed[coords[:,0],coords[:,1]]=value
                assert np.count_nonzero(changed!=baseline)==1
            moved=np.linalg.norm(coords-old[['row','column']].to_numpy(),axis=1)
            assigned_dist=cdist(coords,coords)
            np.fill_diagonal(assigned_dist,np.inf)
            new_nn=np.argsort(assigned_dist,axis=1,kind='stable')[:,:4]
            overlap=float(np.mean([len(set(a)&set(b))/4 for a,b in zip(nn,new_nn)]))
            result=dict(variante=name,lado=size,entradas=n,posiciones_unicas=n,cambios_ocultos=0,
                ventanas_recuperadas=len(scaled),error_maximo_escala_minmax=error,
                desplazamiento_medio_pixeles=float(moved.mean()),desplazamiento_maximo_pixeles=float(moved.max()),
                posiciones_cambiadas=int((moved>0).sum()),vecinos_PCA_conservados_fraccion=overlap,
                suma_distancias_cuadradas=float(cost[rows,cols].sum()),bytes_matriz=baseline.nbytes)
            results.append(result)
            mapping=pd.DataFrame(dict(feature=scaler.feature,row=coords[:,0],column=coords[:,1],
                row_TINTO=old.row,column_TINTO=old.column,desplazamiento_pixeles=moved))
            mapping.to_csv(folder/f'mapa_unico_{size}.csv',index=False)
            np.save(folder/f'imagen_unica_{size}.npy',baseline)
            figures[name,size]=(original,baseline)
            print(result,flush=True)
    # Canales conservan las 360 entradas de sensores; hora sigue siendo explícita.
    channels=X[:,:,:15].reshape(len(X),24,5,3)
    clock=X[:,:,15:17]
    recovered=np.concatenate([channels.reshape(len(X),24,15),clock],axis=2)
    np.testing.assert_array_equal(recovered,X)
    np.save(out/'canales_sensor_ejemplo.npy',channels[base_id])
    np.save(out/'hora_ejemplo.npy',clock[base_id])
    write(out/'canales.json',dict(forma_sensores_por_ventana=[24,5,3],tipos=['relativa','mascara','comparacion_a14'],
        roles=['objetivo','vecina1','vecina2','vecina3','vecina4'],
        forma_hora_original=[24,2],forma_hora_compacta=[2],
        ventanas_reconstruidas_original=len(X),error_maximo_original=0.0,
        mapa='Roles locales, no coordenadas geográficas; posición temporal explícita',
        advertencia='Los canales de sensores no forman una entrada completa sin el bloque horario; aún no hay arquitectura CNN definida.'))
    pd.DataFrame(results).to_csv(out/'resultados.csv',index=False)
    fig,axes=plt.subplots(2,2,figsize=(8,8),layout='constrained')
    for i,size in enumerate([32,64]):
        for j,data in enumerate(figures['L0_362',size]):
            im=axes[i,j].imshow(data,vmin=0,vmax=1,cmap='magma',interpolation='nearest')
            axes[i,j].set(title=f'{size} × {size}: '+('TINTO original' if j==0 else 'Asignación única'),
                xlabel='Columna del píxel',ylabel='Fila del píxel')
    fig.colorbar(im,ax=list(axes.flat),label='Intensidad MinMax')
    fig.suptitle('Misma ventana de 362 entradas · reubicación explícita, sin difuminado')
    fig.savefig(out/'comparacion_asignacion.png',dpi=150)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(11,5),layout='constrained')
    # Escalas distintas por tipo: no comparar brillo entre paneles.
    for j,title in enumerate(['Relativa','Máscara','Comparación a14']):
        data=channels[base_id,:,:,j]
        lo,hi=(0,1) if j==1 else (-max(1,float(np.abs(data).max())),max(1,float(np.abs(data).max())))
        im=axes[j].imshow(data,aspect='auto',vmin=lo,vmax=hi,cmap='viridis' if j==1 else 'coolwarm',interpolation='nearest')
        axes[j].set(title=title,xlabel='Rol de estación',ylabel='Desfase horario')
        axes[j].set_xticks(range(5),['Obj','V1','V2','V3','V4'])
        axes[j].set_yticks([0,6,12,18,23],[-23,-17,-11,-5,0])
        fig.colorbar(im,ax=axes[j],label='0/1' if j==1 else 'Escala histórica L0')
    fig.suptitle('Tres canales de sensores · misma ventana · hora conservada aparte')
    fig.savefig(out/'canales_sensor.png',dpi=150)
    plt.close(fig)
    write(out/'hashes_numericos.json',{p.name if p.parent==out else str(p.relative_to(out)):sha(p)
        for p in sorted(out.rglob('*')) if p.is_file() and p.suffix in ['.json','.csv','.npy']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',required=True,type=Path)
    args=p.parse_args()
    if args.salida.exists():
        p.error('Usa una carpeta nueva.')
    ejecutar(args.salida)
