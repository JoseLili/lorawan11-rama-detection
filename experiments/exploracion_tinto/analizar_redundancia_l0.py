"""Diagnóstico descriptivo de redundancia L0, sin quitar entradas ni entrenar."""
import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1'
GEO = ROOT/'results/inventario_multianual/estaciones_geografia.csv'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ejecutar(out):
    out.mkdir(parents=True)
    sources=[AUD/'X_muestra.npy', AUD/'manifiesto_muestra.csv', AUD/'vecinas_y_escalas.json', GEO]
    config={'alcance':'19 840 ventanas 2020–2021; descripción y reconstrucción, no selección de detector',
        'entradas_modificadas':False,'modelos_entrenados':False,'tolerancia_hora_abs':1e-7,
        'tolerancia_a14':{'atol':1e-5,'rtol':1e-5},
        'sha256_fuentes':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'sha256_codigo':sha(Path(__file__)),
        'versiones':{p:importlib.metadata.version(p) for p in ['numpy','pandas']}}
    (out/'configuracion.json').write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n')
    X=np.load(AUD/'X_muestra.npy',allow_pickle=False).astype(np.float64)
    meta=pd.read_csv(AUD/'manifiesto_muestra.csv')
    par=json.loads((AUD/'vecinas_y_escalas.json').read_text())
    assert X.shape==(19840,24,17)
    assert meta.hora_final.str[:4].isin(['2020','2021']).all()
    # Rotar seno/coseno de la hora final para recuperar cada hora de la ventana.
    phase=2*np.pi*np.arange(-23,1)/24
    sin_t,cos_t=X[:,-1,15],X[:,-1,16]
    recovered_sin=sin_t[:,None]*np.cos(phase)+cos_t[:,None]*np.sin(phase)
    recovered_cos=cos_t[:,None]*np.cos(phase)-sin_t[:,None]*np.sin(phase)
    sin_error=np.abs(recovered_sin-X[:,:,15])
    cos_error=np.abs(recovered_cos-X[:,:,16])
    assert sin_error.max()<1e-7 and cos_error.max()<1e-7
    rank_singular=np.linalg.svd(X[:,:,15:17].reshape(len(X),48),compute_uv=False)
    rows=[]
    for lag in range(23,-1,-1):
        for j,err in [('hora_sin',sin_error[:,23-lag]),('hora_cos',cos_error[:,23-lag])]:
            rows.append({'nombre':f'lag{lag:02d}_{j}','max_error_reconstruccion':err.max()})
    pd.DataFrame(rows).to_csv(out/'reconstruccion_hora.csv',index=False)
    # La comparación a14 del objetivo usa justamente sus cuatro vecinas visibles.
    rel=X[:,:,0:15:3]
    mask=X[:,:,1:15:3]
    assert np.isin(mask,[0,1]).all()
    count=mask[:,:,1:].sum(axis=2)
    neigh_sum=(rel[:,:,1:]*mask[:,:,1:]).sum(axis=2)
    avg=np.divide(neigh_sum,count,out=np.zeros_like(count),where=count>0)
    scale=np.array([par['escala_a14_2020_2021'][s] for s in meta.objetivo])
    predicted=np.where((mask[:,:,0]==1)&(count>=2),(rel[:,:,0]-avg)/scale[:,None],0)
    actual=X[:,:,2]
    error=predicted-actual
    match=np.isclose(predicted,actual,atol=1e-5,rtol=1e-5)
    detail=[]
    for target in par['objetivos']:
        use=(meta.objetivo==target).to_numpy()
        detail.append({'objetivo':target,'celdas':int(use.sum()*24),'coincidencias':int(match[use].sum()),
            'max_error_abs':float(np.abs(error[use]).max()),'rmse':float(np.sqrt(np.mean(error[use]**2)))})
    pd.DataFrame(detail).to_csv(out/'reconstruccion_a14_objetivo.csv',index=False)
    bad=np.argwhere(~match)
    badrows=[]
    for i,h in bad:
        badrows.append({'fila_muestra':int(i),'indice_hora':int(h),'calendario':meta.calendario.iloc[i],
            'objetivo':meta.objetivo.iloc[i],'hora_final':meta.hora_final.iloc[i],
            'a14_guardada':float(actual[i,h]),'a14_reconstruida':float(predicted[i,h]),
            'error_abs':float(abs(error[i,h]))})
    pd.DataFrame(badrows,columns=['fila_muestra','indice_hora','calendario','objetivo','hora_final',
         'a14_guardada','a14_reconstruida','error_abs']).to_csv(out/'discrepancias_a14.csv',index=False)
    # Auditar excepciones contra la disponibilidad del perfil ANTES de imputar.
    sys.path.insert(0, str(ROOT))
    from src.detect import evaluacion_red as ev, anomalias_red as ar
    exceptions=[]
    bad_df=pd.DataFrame(badrows)
    if len(bad_df):
        for calendar, group in bad_df.groupby('calendario',sort=True):
            path=ROOT/f'results/anomalias_red_v1/matrices/matriz_{calendar}_d50.csv.gz'
            config['sha256_fuentes'][str(path.relative_to(ROOT))]=sha(path)
            matrix=ar.leer_matriz(path)
            assert matrix.index.min().year==2020 and matrix.index.max().year==2022
            raw=ev.relativas(matrix,referencia='media')/pd.Series(par['sigma_2020_2022'])
            for row in group.itertuples():
                t=pd.Timestamp(row.hora_final)+pd.Timedelta(hours=int(row.indice_hora)-23)
                target=row.objetivo
                neighbors=par['vecinas'][target]
                own=raw.loc[t,target]
                nr=raw.loc[t,neighbors]
                correct=(own-nr.mean())/par['escala_a14_2020_2021'][target] if pd.notna(own) and nr.notna().sum()>=2 else 0.0
                assert np.isclose(correct,row.a14_guardada,atol=1e-5,rtol=1e-5)
                missing_profile=[station for station in [target]+neighbors
                    if matrix.loc[t,f'{station}_mascara']==1 and pd.isna(raw.loc[t,station])]
                assert missing_profile, 'La discrepancia no se explica por perfil indisponible'
                exceptions.append({'fila_muestra':row.fila_muestra,'indice_hora':row.indice_hora,
                    'calendario':calendar,'objetivo':target,'hora_real':str(t),
                    'lectura_sin_perfil':';'.join(missing_profile),
                    'a14_recalculada_con_disponibilidad_perfil':float(correct),
                    'a14_guardada':row.a14_guardada})
    pd.DataFrame(exceptions).to_csv(out/'causa_discrepancias_a14.csv',index=False)
    (out/'configuracion.json').write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n')
    # Las comparaciones de las vecinas pueden necesitar estaciones fuera del bloque local.
    footprints=[]
    for target in par['objetivos']:
        local=[target]+par['vecinas'][target]
        for role,station in enumerate(local):
            external=[s for s in par['vecinas'][station] if s not in local]
            footprints.append({'objetivo':target,'rol':'obj' if role==0 else f'v{role}',
                'estacion':station,'vecinas_de_esa_estacion':';'.join(par['vecinas'][station]),
                'contexto_externo':';'.join(external),'n_externas':len(external)})
    footprints=pd.DataFrame(footprints)
    footprints.to_csv(out/'dependencias_vecindarios.csv',index=False)
    # Ambigüedad del cero: misma relativa cero con máscara tanto cero como uno.
    masks=[]
    for j,role in enumerate(['obj','v1','v2','v3','v4']):
        r,m=rel[:,:,j],mask[:,:,j]
        masks.append({'rol':role,'celdas':r.size,'sin_lectura':int((m==0).sum()),
            'relativa_cero_sin_lectura':int(((r==0)&(m==0)).sum()),
            'relativa_cero_con_lectura':int(((r==0)&(m==1)).sum())})
    pd.DataFrame(masks).to_csv(out/'ambiguedad_cero_y_mascaras.csv',index=False)
    # Coordenadas solo del catálogo congelado, sin usar cobertura de otros años.
    geo=pd.read_csv(GEO,usecols=['station','latitud','longitud']).set_index('station')
    selected=geo.loc[par['estaciones']]
    assert selected.notna().all().all()
    georows=[]
    for target in par['objetivos']:
        local=[target]+par['vecinas'][target]
        g=geo.loc[local]
        georows.append({'objetivo':target,'estaciones_locales':';'.join(local),
            'ubicaciones_distintas':len(g.drop_duplicates()),
            'entradas_por_ubicacion_en_ventana':24*3})
    pd.DataFrame(georows).to_csv(out/'geografia_por_objetivo.csv',index=False)
    # Correlaciones descriptivas: no justifican por sí solas retirar columnas.
    flat=X.reshape(-1,17)
    names=[f'{role}_{kind}' for role in ['obj','v1','v2','v3','v4'] for kind in ['rel','mascara','a14']]+['hora_sin','hora_cos']
    pd.DataFrame(np.corrcoef(flat,rowvar=False),index=names,columns=names).to_csv(out/'correlaciones_17_descriptivas.csv')
    report={'ventanas':len(X),'celdas_estacion_hora_por_rol':len(X)*24,
        'hora':{'columnas_actuales':48,'columnas_suficientes_propuestas':2,
            'max_error_seno':float(sin_error.max()),'max_error_coseno':float(cos_error.max()),
            'singulares_hora':rank_singular.tolist(),
            'interpretacion':'Reconstruible a precisión float32 desde la hora final y desfases; no demuestra que eliminar toda hora sea inocuo.'},
        'a14_objetivo':{'coincidencias':int(match.sum()),'celdas':match.size,'discrepancias':len(bad),
            'max_error_abs':float(np.abs(error).max()),'rmse':float(np.sqrt(np.mean(error**2))),
            'discrepancias_explicadas_por_perfil_indisponible':len(exceptions),
            'depende_de':'Relativas y máscaras de las cinco estaciones visibles más escala del objetivo; disponibilidad de perfil puede requerir información adicional.',
            'es_R3':False},
        'a14_vecinas':{'roles_evaluados':int((footprints.rol!='obj').sum()),
            'roles_con_contexto_externo':int(((footprints.rol!='obj')&(footprints.n_externas>0)).sum()),
            'interpretacion':'Una comparación de vecina con contexto externo no es algebraicamente reconstruible solo con estas cinco estaciones.'},
        'mascaras':masks,
        'geografia':{'estaciones_con_coordenadas':len(selected),'ubicaciones_distintas':len(selected.drop_duplicates()),
            'objetivos_con_cinco_ubicaciones_distintas':int(sum(r['ubicaciones_distintas']==5 for r in georows)),
            'advertencia':'Una ubicación por estación no separa las 72 entradas hora/tipo de esa estación. Hace falta otra dimensión o canal; no se ha cambiado la representación.'}}
    (out/'resultados.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    files=[p for p in sorted(out.iterdir()) if p.is_file()]
    (out/'hashes.json').write_text(json.dumps({p.name:sha(p) for p in files},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='mascaras'},indent=2,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,required=True)
    args=p.parse_args()
    if args.salida.exists():
        p.error('Usa una carpeta nueva para preservar resultados.')
    ejecutar(args.salida)
