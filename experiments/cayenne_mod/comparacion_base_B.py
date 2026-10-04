"""Comparación pareada de Base+LSTM y B+LSTM a partir de campañas verificadas.

No entrena, no genera ataques nuevos y no cambia umbrales. El análisis de
aceptación común es diagnóstico; no reemplaza el resultado de todos los ataques.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from experiments.cayenne_mod.campana_cca import cargar_cca
from src.decision.nom172 import banda_o3

METRICAS=('ataques','rechazos','aceptados_atacados','cancelaciones','alterados',
          'detectados_alterados','banda_local_cambiada','banda_local_sin_alerta',
          'falsa_excedencia','falsa_excedencia_sin_alerta','ocultamiento_sin_alerta')
CLAVES=['semilla','id_mensaje']


def emparejar(ataques):
    base=ataques.query("formato == 'base'").set_index(CLAVES).sort_index()
    b=ataques.query("formato == 'B'").set_index(CLAVES).sort_index()
    if base.index.has_duplicates or b.index.has_duplicates or not base.index.equals(b.index):
        raise ValueError('Los formatos deben compartir exactamente los mismos intentos')
    comunes=['timestamp','original_ppb','n_flips','mascara','predicho_ppb','umbral_ppb']
    pd.testing.assert_frame_equal(base[comunes],b[comunes],check_exact=True)
    p=base[comunes].copy()
    for nombre,d in [('base',base),('B',b)]:
        for col in METRICAS+('aceptado','recibido_ppb','delta_ppb','residuo_ppb','alerta'):
            p[f'{col}_{nombre}']=d[col]
    p['grupo']=np.select([p.aceptado_base & p.aceptado_B,
                          ~p.aceptado_base & p.aceptado_B,
                          p.aceptado_base & ~p.aceptado_B],
                         ['ambos_aceptan','solo_B_acepta','solo_base_acepta'],default='ambos_rechazan')
    return p.reset_index()


def analizar(ataques):
    p=emparejar(ataques)
    filas,transiciones=[],[]
    selecciones=[('todos',np.ones(len(p),dtype=bool))]
    selecciones += [(g,p.grupo.eq(g)) for g in ('ambos_aceptan','solo_B_acepta','solo_base_acepta','ambos_rechazan')]
    for grupo,mask in selecciones:
        g=p.loc[mask]
        for formato in ('base','B'):
            row=dict(grupo=grupo,formato=formato,intentos=len(g))
            row.update({col:int(g[f'{col}_{formato}'].sum()) for col in METRICAS})
            def pct(num,den): return 100*num/den if den else np.nan
            row['riesgo_por_intento_pct']=pct(row['banda_local_sin_alerta'],len(g))
            row['riesgo_por_aceptado_pct']=pct(row['banda_local_sin_alerta'],row['aceptados_atacados'])
            row['recall_alterados_pct']=pct(row['detectados_alterados'],row['alterados'])
            row['delta_abs_medio_aceptados']=g[f'delta_ppb_{formato}'].abs().mean()
            filas.append(row)
        e0=g.banda_local_sin_alerta_base
        e1=g.banda_local_sin_alerta_B
        transiciones.append(dict(grupo=grupo,intentos=len(g),
            escape_en_ambos=int((e0 & e1).sum()),solo_base_escapa=int((e0 & ~e1).sum()),
            solo_B_escapa=int((~e0 & e1).sum()),sin_escape_en_ambos=int((~e0 & ~e1).sum())))
    resumen=pd.DataFrame(filas)
    # Una fila por semilla, comparada dentro del mismo sorteo.
    campos=[f'{m}_{f}' for f in ('base','B') for m in METRICAS]
    sem=p.groupby('semilla')[campos].sum().reset_index()
    sem['diferencia_escapes_B_menos_base']=sem.banda_local_sin_alerta_B-sem.banda_local_sin_alerta_base
    pn=p.groupby('n_flips')[campos].sum().reset_index()
    # Explica los cambios de resultado sobre posiciones que ambos aceptan.
    g=p.loc[p.grupo.eq('ambos_aceptan')].copy()
    mejor=g.banda_local_sin_alerta_base & ~g.banda_local_sin_alerta_B
    explicacion=pd.DataFrame([
        dict(resultado='Base escapaba; B ya no cambia banda local',casos=int((mejor & ~g.banda_local_cambiada_B).sum())),
        dict(resultado='Base escapaba; B cambia banda pero alerta',casos=int((mejor & g.banda_local_cambiada_B & g.alerta_B.fillna(False)).sum())),
        dict(resultado='B crea un escape que Base no tenía',casos=int((~g.banda_local_sin_alerta_base & g.banda_local_sin_alerta_B).sum())),
        dict(resultado='El cambio de banda escapa en ambos',casos=int((g.banda_local_sin_alerta_base & g.banda_local_sin_alerta_B).sum())),
    ])
    ejemplos=[]
    categorias=[('Base escapaba; B ya no cambia banda',p.grupo.eq('ambos_aceptan') & p.banda_local_sin_alerta_base & ~p.banda_local_cambiada_B),
        ('Base escapaba; B cambia banda pero alerta',p.grupo.eq('ambos_aceptan') & p.banda_local_sin_alerta_base & p.banda_local_cambiada_B & p.alerta_B.fillna(False)),
        ('B crea un escape; ambos aceptan',p.grupo.eq('ambos_aceptan') & ~p.banda_local_sin_alerta_base & p.banda_local_sin_alerta_B),
        ('B acepta y hay escape; Base rechaza',p.grupo.eq('solo_B_acepta') & p.banda_local_sin_alerta_B),
        ('El cambio de banda escapa en ambos',p.banda_local_sin_alerta_base & p.banda_local_sin_alerta_B)]
    for etiqueta,mask in categorias:
        ex=p.loc[mask].head(1).copy()
        ex['ejemplo']=etiqueta
        ejemplos.append(ex)
    return dict(resumen=resumen,transiciones=pd.DataFrame(transiciones),por_semilla=sem,
        por_n=pn,explicacion_comun=explicacion,ejemplos=pd.concat(ejemplos,ignore_index=True),parejas=p)


def construir(raiz):
    raiz=Path(raiz)
    carpeta=raiz/'experiments/cayenne_mod/resultados/08'
    info08=json.loads((carpeta/'protocolo.json').read_text())
    for nombre,h in info08['codigo_sha256'].items():
        assert hashlib.sha256((raiz/nombre).read_bytes()).hexdigest()==h,nombre
    c,fuentes=cargar_cca(raiz)
    a=pd.read_csv(carpeta/'ataques.csv.gz',dtype={'alerta':'boolean'},parse_dates=['timestamp','fecha'])
    a=a.loc[a.formato.isin(['base','B'])].copy()
    # Recalcular alertas y banda: no confiar sólo en etiquetas persistidas.
    esperado=c.set_index('id_mensaje').loc[a.id_mensaje]
    for col in ['original_ppb','predicho_ppb','umbral_ppb']:
        np.testing.assert_array_equal(a[col],esperado[col])
    recibido=a.recibido_ppb.to_numpy()
    aceptado=np.isfinite(recibido)
    modelo=a.base_ppb.to_numpy(dtype=np.float32)+(recibido-a.perfil_ppb.to_numpy()).astype(np.float32)
    alerta=np.abs(modelo-a.predicho_ppb.to_numpy())>a.umbral_ppb.to_numpy()
    np.testing.assert_array_equal(a.loc[aceptado,'alerta'].to_numpy(dtype=bool),alerta[aceptado])
    assert a.loc[~aceptado,'alerta'].isna().all()
    banda=aceptado & (banda_o3(a.original_ppb)!=banda_o3(recibido))
    np.testing.assert_array_equal(banda,a.banda_local_cambiada)
    np.testing.assert_array_equal(banda & ~alerta,a.banda_local_sin_alerta)
    r=analizar(a)
    anterior=pd.read_csv(carpeta/'resumen_por_semilla.csv').query("formato in ['base','B']")
    for f in ('base','B'):
        g=anterior.query('formato==@f').sort_values('semilla')
        for col in METRICAS:
            np.testing.assert_array_equal(r['por_semilla'][f'{col}_{f}'],g[col])
    r['costos_por_semilla']=anterior[['semilla','formato','mensajes','limpios','falsas_alarmas_limpios',
        'fpr_limpios_pct','rechazos','dias_cambio_banda_disponibles','dias_cambio_banda_solo_perdidas']].copy()
    info=dict(estacion='CCA',fuentes=fuentes['fuentes'],n_mensajes=fuentes['n_mensajes'],
        n_dias=fuentes['n_dias'],umbral_ppb=fuentes['umbral_ppb'],fpr_limpio_pct=fuentes['fpr_limpio_pct'],
        n_campanas=len(info08['semillas']),semillas=info08['semillas'],tasa=info08['tasa'],
        modelo=info08['modelo'],maximo_limpio_ppb=fuentes['maximo_limpio_ppb'],
        pregunta='¿B reduce cambios de banda por lectura que escapan al mismo LSTM?',
        principal='Todos los intentos pareados; rechazo es pérdida, nunca escape cero interpretado como lectura íntegra',
        diagnostico='Aceptación común se define por máscaras y formato, no por éxito del ataque; no sustituye resultado global',
        independencia='Campañas repetidas sobre el mismo periodo: describen variación del sorteo, no validación externa',
        control='Base binaria con dominio 0..255 y bits 8..15 reservados; B usa bits 0..11',
        alcance='Predicciones fijas, efectos inmediatos; alertas sin retirada automática de lecturas')
    for nombre in ['protocolo.json','ataques.csv.gz','resumen_por_semilla.csv']:
        p=carpeta/nombre
        info['fuentes'][str(p.relative_to(raiz))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return r,info


def guardar(raiz,r,info):
    raiz=Path(raiz)
    destino=raiz/'experiments/cayenne_mod/resultados/09'
    archivos=[Path(__file__),raiz/'experiments/cayenne_mod/campana_cca.py',raiz/'src/decision/nom172.py']
    meta=dict(info,codigo_sha256={str(p.relative_to(raiz)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos})
    protocolo=destino/'protocolo.json'
    if protocolo.exists() and json.loads(protocolo.read_text())!=meta:
        raise ValueError('Protocolo distinto; no sobrescribir resultados 09')
    destino.mkdir(parents=True,exist_ok=True)
    for nombre,df in r.items():
        comp=nombre=='parejas'
        df.to_csv(destino/f"{nombre}.csv{'.gz' if comp else ''}",index=False,
            compression={'method':'gzip','mtime':0} if comp else None)
    protocolo.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    return destino


def graficar(r,info,destino):
    import matplotlib.pyplot as plt
    datos=r['resumen'].set_index(['grupo','formato'])
    fig,axs=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    paneles=[('todos','banda_local_sin_alerta','Todos los intentos: 8 377','Lecturas que cambian banda sin alerta'),
             ('ambos_aceptan','banda_local_sin_alerta','Subgrupo: los mismos 420 aceptados','Lecturas que cambian banda sin alerta'),
             ('todos','rechazos','Costo: lecturas perdidas por rechazo','Mensajes rechazados')]
    for ax,(grupo,col,titulo,ylabel) in zip(axs,paneles):
        valores=[int(datos.loc[(grupo,f),col]) for f in ('base','B')]
        bars=ax.bar(['Base + LSTM','B + LSTM'],valores,color=['#666666','#157F86'],width=.55)
        ax.bar_label(bars,padding=4)
        ax.set(title=titulo,ylabel=ylabel,ylim=(0,max(valores)*1.2))
        ax.grid(axis='y',alpha=.15)
        ax.set_axisbelow(True)
    fig.suptitle('CCA · Conteos acumulados en las mismas 100 campañas del experimento 08\nEl subgrupo explica un mecanismo; no sustituye el resultado de todos los intentos.')
    fig.savefig(destino/'comparacion_base_B.png',dpi=160)
