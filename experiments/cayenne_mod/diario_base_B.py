"""10: decisiones diarias CCA, alertas y pérdidas; referencia 08 sin reentrenar."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from experiments.cayenne_mod.comparacion_base_B import construir as comparar
from experiments.cayenne_mod.campana_cca import cargar_cca
from src.decision.nom172 import banda_o3

TIPOS=('banda','falsa_excedencia','ocultamiento')


def maximo(x):
    ok=np.isfinite(x)
    return float(np.max(x[ok])) if ok.any() else np.nan


def dano(original,recibido,tipo):
    if not np.isfinite(recibido):
        return False
    if tipo=='banda': return banda_o3(original)!=banda_o3(recibido)
    if tipo=='falsa_excedencia': return original<155<=recibido
    if tipo=='ocultamiento': return recibido<155<=original
    raise ValueError(tipo)


def medir_dia(g):
    x=g.original_ppb.to_numpy(dtype=float)
    r=g.recibido_ppb.to_numpy(dtype=float)
    alerta=g.alerta.fillna(False).to_numpy(dtype=bool)
    atacado=g.atacado.to_numpy(dtype=bool)
    ok=np.isfinite(r)
    cambiado=atacado & ok & (r!=x)
    detectado=cambiado & alerta
    # Reconstrucciones con originales conocidos por el simulador. No políticas.
    valores=np.where(ok,r,x)                 # reponer sólo rechazados
    perdidas=np.where(ok,x,np.nan)           # corregir todo valor alterado
    corregidos=np.where(detectado,x,r)       # corregir sólo alterados con alerta
    silenciosos=np.where(cambiado & ~alerta,r,x)  # sólo alterados sin alerta
    mx,mr,mv,mp,mc,ms=map(maximo,(x,r,valores,perdidas,corregidos,silenciosos))
    row=dict(maximo_original=mx,maximo_recibido=mr,maximo_solo_valores=mv,maximo_solo_perdidas=mp,
        maximo_restaurando_detectados=mc,maximo_solo_silenciosos=ms,
        observados=len(g),recibidos=int(ok.sum()),rechazos=int((atacado & ~ok).sum()),
        ataques=int(atacado.sum()),dia_sin_datos=not ok.any(),
        alertas_totales=int((ok & alerta).sum()),alertas_alterados=int(detectado.sum()),
        alertas_limpios=int((~atacado & alerta).sum()),
        alertas_cancelados=int((atacado & ok & (r==x) & alerta).sum()),
        banda_original=banda_o3(mx),banda_recibida=banda_o3(mr))
    for t in TIPOS:
        h,v,p=dano(mx,mr,t),dano(mx,mv,t),dano(mx,mp,t)
        row[t]=h
        row[t+'_solo_valores']=v
        row[t+'_solo_perdidas']=p
        row[t+'_sin_alerta_alguna']=h and row['alertas_totales']==0
        row[t+'_sin_alerta_en_alterados']=h and row['alertas_alterados']==0
        row[t+'_persiste_restaurando_detectados']=h and dano(mx,mc,t)
        row[t+'_persiste_solo_silenciosos']=h and dano(mx,ms,t)
        row[t+'_fuente']=('sin_dano' if not h else
            'valores_y_perdidas_por_separado' if v and p else
            'solo_valores_suficientes' if v else
            'solo_perdidas_suficientes' if p else 'interaccion')
    return row


def construir(raiz):
    raiz=Path(raiz)
    comp,info=comparar(raiz)
    c,_=cargar_cca(raiz)
    pares=comp['parejas']
    filas=[]
    for semilla,p in pares.groupby('semilla',sort=True):
        for formato in ('base','B'):
            d=c.copy()
            d['recibido_ppb']=d.original_ppb
            d['alerta']=d.alerta_limpia.astype('boolean')
            d['atacado']=False
            idx=p.id_mensaje.to_numpy(dtype=int)
            d.loc[idx,'recibido_ppb']=p[f'recibido_ppb_{formato}'].to_numpy()
            d.loc[idx,'alerta']=p[f'alerta_{formato}'].array
            d.loc[idx,'atacado']=True
            for fecha,g in d.groupby('fecha',sort=True):
                filas.append(dict(semilla=int(semilla),formato=formato,fecha=fecha,**medir_dia(g)))
    diario=pd.DataFrame(filas)
    prev_path=raiz/'experiments/cayenne_mod/resultados/08/diario.csv.gz'
    prev=pd.read_csv(prev_path,parse_dates=['fecha']).query("formato in ['base','B']")
    keys=['semilla','formato','fecha']
    actual=diario.set_index(keys).sort_index()
    previo=prev.set_index(keys).sort_index()
    assert actual.index.equals(previo.index)
    for nuevo,viejo in [('maximo_original','maximo_original'),('maximo_recibido','maximo_recibido'),
                        ('banda','cambio_banda_disponibles'),('falsa_excedencia','falsa_excedencia'),
                        ('ocultamiento','ocultamiento'),('dia_sin_datos','dia_sin_datos'),
                        ('alertas_totales','alertas_totales'),('alertas_alterados','alertas_en_valores_alterados')]:
        np.testing.assert_array_equal(actual[nuevo],previo[viejo])
    info['fuentes'][str(prev_path.relative_to(raiz))]=hashlib.sha256(prev_path.read_bytes()).hexdigest()
    eventos=[col for col in diario if diario[col].dtype==bool]
    sem=diario.groupby(['semilla','formato'])[eventos].sum().reset_index()
    resumen=[]
    for f,g in diario.groupby('formato',sort=False):
        for t in TIPOS:
            s=sem.query('formato==@f')[t]
            row=dict(formato=f,tipo=t,dias_campana=len(g),dias_unicos=g.fecha.nunique(),
                dias_danados=int(g[t].sum()),media_por_campana=s.mean(),p05=s.quantile(.05),p95=s.quantile(.95),
                dias_sin_datos=int(g.dia_sin_datos.sum()))
            for suf in ('solo_valores','solo_perdidas','sin_alerta_alguna','sin_alerta_en_alterados',
                        'persiste_restaurando_detectados','persiste_solo_silenciosos'):
                row[suf]=int(g[t+'_'+suf].sum())
            resumen.append(row)
    fuentes=[]
    for f,g in diario.groupby('formato',sort=False):
        for t in TIPOS:
            for nombre,n in g.loc[g[t],t+'_fuente'].value_counts().items():
                fuentes.append(dict(formato=f,tipo=t,fuente=nombre,dias_campana=int(n)))
    ejemplos=[]
    grupos=[('banda_sin_alerta_en_alterados','Daño sin alerta en valores alterados'),
            ('banda_persiste_restaurando_detectados','Daño persiste al restaurar detectados'),
            ('banda_persiste_solo_silenciosos','Daño persiste sólo con alteraciones silenciosas'),
            ('falsa_excedencia_sin_alerta_en_alterados','Falsa excedencia sin alerta en alterados')]
    for col,nombre in grupos:
        for f in ('base','B'):
            ex=diario.loc[diario[col] & diario.formato.eq(f)].head(1).copy()
            ex['ejemplo']=nombre
            ejemplos.append(ex)
    info.update(pregunta='Daño diario y señales LSTM en las mismas campañas CCA Base/B',
        principal='Daño en máximo diario disponible, todos los intentos 0..15; pérdidas y alertas se informan por separado',
        unidad='Un día de una campaña; 72 fechas repetidas en 100 campañas, no 7200 días independientes',
        alertas='Cualquier alerta del día se separa de alertas en valores realmente alterados',
        diagnostico='Restauraciones con originales del simulador; no eliminación de alertas ni corrección operativa',
        no_datos='Día sin ningún dato: decisión indefinida, contado aparte, nunca día seguro',
        contingencia='Cruce del umbral experimental 155 ppb en máximo observado CCA; no declaración oficial',
        ocultamiento_evaluable=bool((c.original_ppb>=155).any()))
    return dict(diario=diario,por_semilla=sem,resumen=pd.DataFrame(resumen),
                fuentes_dano=pd.DataFrame(fuentes),ejemplos=pd.concat(ejemplos,ignore_index=True)),info


def guardar(raiz,r,info):
    raiz=Path(raiz)
    destino=raiz/'experiments/cayenne_mod/resultados/10'
    archivos=[Path(__file__),raiz/'experiments/cayenne_mod/comparacion_base_B.py',
        raiz/'experiments/cayenne_mod/campana_cca.py',raiz/'src/decision/nom172.py']
    meta=dict(info,codigo_sha256={str(p.relative_to(raiz)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos})
    path=destino/'protocolo.json'
    if path.exists() and json.loads(path.read_text())!=meta:
        raise ValueError('Protocolo diferente; no sobrescribir')
    destino.mkdir(parents=True,exist_ok=True)
    for n,df in r.items():
        comp=n=='diario'
        df.to_csv(destino/f"{n}.csv{'.gz' if comp else ''}",index=False,compression={'method':'gzip','mtime':0} if comp else None)
    path.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    return destino


def graficar(r,destino):
    import matplotlib.pyplot as plt
    s=r['resumen'].query("tipo == 'banda'").set_index('formato')
    cols=['dias_danados','sin_alerta_alguna','sin_alerta_en_alterados',
          'persiste_restaurando_detectados','persiste_solo_silenciosos']
    labels=['Banda distinta','Sin ninguna\nalerta del día','Sin alerta en\nvalores alterados',
            'Persiste al restaurar\nalterados detectados*','Persiste sólo con\nalteraciones sin alerta*']
    fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
    x=np.arange(len(cols))
    for offset,f,color in [(-.18,'base','#666666'),(.18,'B','#157F86')]:
        bars=ax.bar(x+offset,s.loc[f,cols].to_numpy(dtype=float),width=.36,label=f+' + LSTM',color=color)
        ax.bar_label(bars,padding=3)
    ax.set(xticks=x,xticklabels=labels,ylabel='Días-campaña, acumulados en 100 sorteos',
           title='CCA: daño diario y relación con alertas · Predicciones guardadas')
    ax.legend()
    ax.grid(axis='y',alpha=.2)
    ax.set_axisbelow(True)
    fig.supxlabel('*Reconstrucciones diagnósticas con originales conocidos; no políticas del receptor. Categorías no sumables.',fontsize=9)
    fig.savefig(destino/'dano_y_alertas.png',dpi=160)
