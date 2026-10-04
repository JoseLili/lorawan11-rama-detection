"""11: Base/B con detectores guardados, 27 estaciones y campañas pareadas."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from experiments.graficas_revision.generar import verificar_fuentes
from experiments.cayenne_mod.campana_cca import sortear_plan,evaluar,resumen_mensajes,SEMILLAS,CONTEOS
from src.ingest.rama import load_wide,to_long
from src.decision.nom172 import banda_o3


def diario_vector(d):
    ok=d.aceptado.to_numpy()
    x=d.original_ppb.to_numpy()
    r=d.recibido_ppb.to_numpy()
    al=d.alerta.fillna(False).to_numpy(dtype=bool)
    alter=d.alterados.to_numpy()
    z=pd.DataFrame(dict(fecha=d.fecha,original=x,recibido=r,
        valores=np.where(ok,r,x),perdidas=np.where(ok,x,np.nan),
        corregidos=np.where(alter & al,x,r),silenciosos=np.where(alter & ~al,r,x),
        alerta=ok & al,alerta_alterado=alter & al,rechazos=~ok))
    g=z.groupby('fecha').agg(original=('original','max'),recibido=('recibido','max'),
        valores=('valores','max'),perdidas=('perdidas','max'),corregidos=('corregidos','max'),
        silenciosos=('silenciosos','max'),alertas=('alerta','sum'),alertas_alterados=('alerta_alterado','sum'),
        rechazos=('rechazos','sum'),observados=('original','size'),aceptados=('recibido','count')).reset_index()
    valido=g.recibido.notna()
    g['sin_datos']=~valido
    for t in ('banda','falsa_excedencia','ocultamiento'):
        def dano(v):
            if t=='banda': return v.notna() & (banda_o3(v)!=banda_o3(g.original))
            if t=='falsa_excedencia': return (g.original<155)&(v>=155)
            return (g.original>=155)&(v<155)
        g[t]=dano(g.recibido)
        g[t+'_sin_alerta_alterados']=g[t] & g.alertas_alterados.eq(0)
        g[t+'_persiste_silenciosos']=g[t] & dano(g.silenciosos)
        g[t+'_solo_valores']=dano(g.valores)
        g[t+'_solo_perdidas']=dano(g.perdidas)
    return g


def semilla_estacion(seed,estacion):
    # CCA conserva el sorteo histórico; otras estaciones usan flujos separados.
    return seed if estacion=='CCA' else [seed,int.from_bytes(estacion.encode('ascii'),'little')]


def construir(raiz,semillas=SEMILLAS,avisar=print):
    raiz=Path(raiz)
    carpeta,base,fuentes=verificar_fuentes(raiz)
    base.timestamp=pd.to_datetime(base.timestamp)
    raw=to_long(load_wide(raiz/'data/raw/2025O3.xls'),'O3')
    raw=raw[raw.timestamp.between(base.timestamp.min(),base.timestamp.max())]
    cobertura=pd.read_csv(carpeta/'cobertura_estaciones.csv')
    fuentes[str((carpeta/'cobertura_estaciones.csv').relative_to(raiz))]=hashlib.sha256((carpeta/'cobertura_estaciones.csv').read_bytes()).hexdigest()
    res,ats,dias,planes,limpios=[],[],[],[],[]
    for estacion,grupo in base.groupby('estacion',sort=True):
        c=grupo[['timestamp','fecha','estacion','original_ppb','base_ppb','perfil_ppb',
                 'predicho_ppb','umbral_ppb','alerta_limpia']].sort_values('timestamp').reset_index(drop=True)
        obs=raw.query('station==@estacion').dropna(subset=['value']).sort_values('timestamp')
        np.testing.assert_array_equal(c.timestamp,obs.timestamp)
        np.testing.assert_array_equal(c.original_ppb,obs.value)
        assert c.original_ppb.between(0,255).all()
        np.testing.assert_array_equal(c.original_ppb,np.rint(c.original_ppb))
        c['id_mensaje']=np.arange(len(c));c['fcnt']=np.arange(1,len(c)+1)
        limpios.append(dict(estacion=estacion,mensajes=len(c),dias_observados=c.fecha.nunique(),
            umbral_ppb=float(c.umbral_ppb.iloc[0]),maximo_limpio=float(c.original_ppb.max()),
            falsas_alarmas=int(c.alerta_limpia.sum()),fpr_limpio_pct=100*c.alerta_limpia.mean()))
        for seed in semillas:
            plan=sortear_plan(len(c),semilla_estacion(seed,estacion))
            p=plan.loc[plan.atacado].copy();p['semilla']=seed;p['estacion']=estacion
            p['timestamp']=c.loc[p.index,'timestamp'];planes.append(p)
            for f in ('base','B'):
                d=evaluar(c,plan,f,seed)
                at=d.loc[d.atacado].copy();ats.append(at)
                dia=diario_vector(d);dia['estacion']=estacion;dia['semilla']=seed;dia['formato']=f;dias.append(dia)
                fila=resumen_mensajes(d);fila['estacion']=estacion
                for col in dia.select_dtypes(include='bool'):
                    fila['dias_'+col]=int(dia[col].sum())
                res.append(fila)
        avisar(f'{estacion}: {len(c)} lecturas; {len(semillas)} campañas Base/B completadas',flush=True)
    rs=pd.DataFrame(res);at=pd.concat(ats,ignore_index=True)
    diario=pd.concat(dias,ignore_index=True)
    # Regresión: CCA conserva exactamente conteos históricos (sin nuevos sorteos).
    antpath=raiz/'experiments/cayenne_mod/resultados/08/resumen_por_semilla.csv'
    anterior=pd.read_csv(antpath).query("formato in ['base','B'] and semilla in @semillas").set_index(['semilla','formato']).sort_index()
    actual=rs.query("estacion=='CCA'").set_index(['semilla','formato']).sort_index()
    for col in CONTEOS+('falsas_alarmas_limpios',):
        np.testing.assert_array_equal(actual[col],anterior[col])
    np.testing.assert_array_equal(actual.dias_banda,anterior.dias_cambio_banda_disponibles)
    fuentes[str(antpath.relative_to(raiz))]=hashlib.sha256(antpath.read_bytes()).hexdigest()
    # Tablas de estación: conteos acumulados y tasas con denominador explícito.
    met=list(CONTEOS)+['mensajes','limpios','falsas_alarmas_limpios']+[c for c in rs if c.startswith('dias_')]
    total=rs.groupby(['estacion','formato'])[met].sum().reset_index()
    for nombre,num,den in [('escape_por_intento_pct','banda_local_sin_alerta','ataques'),
                          ('escape_por_aceptado_pct','banda_local_sin_alerta','aceptados_atacados'),
                          ('rechazo_pct','rechazos','ataques'),('fpr_limpios_pct','falsas_alarmas_limpios','limpios')]:
        total[nombre]=100*total[num]/total[den].replace(0,np.nan)
    pareados=[]
    for est,g in rs.groupby('estacion'):
        a=g.query("formato=='base'").set_index('semilla');b=g.query("formato=='B'").set_index('semilla')
        dif=b.banda_local_sin_alerta-a.banda_local_sin_alerta
        ta=total.query("estacion==@est and formato=='base'").iloc[0]
        tb=total.query("estacion==@est and formato=='B'").iloc[0]
        pareados.append(dict(estacion=est,intentos=int(ta.ataques),escapes_base=int(ta.banda_local_sin_alerta),
            escapes_B=int(tb.banda_local_sin_alerta),diferencia=int(dif.sum()),
            tasa_base=ta.escape_por_intento_pct,tasa_B=tb.escape_por_intento_pct,
            diferencia_pp=tb.escape_por_intento_pct-ta.escape_por_intento_pct,
            semillas_menos=int((dif<0).sum()),semillas_igual=int((dif==0).sum()),semillas_mas=int((dif>0).sum())))
    pn=at.groupby(['estacion','formato','n_flips'])[list(CONTEOS)].sum().reset_index()
    micro=total.groupby('formato')[met].sum().reset_index()
    micro['escape_por_intento_pct']=100*micro.banda_local_sin_alerta/micro.ataques
    micro['rechazo_pct']=100*micro.rechazos/micro.ataques
    macro=total.groupby('formato')[['escape_por_intento_pct','rechazo_pct','fpr_limpios_pct']].mean().reset_index()
    info=dict(fuentes=fuentes,semillas=list(semillas),n_estaciones=len(limpios),n_mensajes=len(base),
        inicio=str(base.timestamp.min()),fin=str(base.timestamp.max()),tasa=.05,n_flips='Uniforme 1..16',
        posiciones='0..15, mismas posiciones para Base/B; cabeceras no atacadas',
        azar='CCA conserva semillas 42..141; demás: SeedSequence([semilla,código ASCII entero estación])',
        modelo='Predicciones y p95 GUARDADOS por estación del notebook 09; sin entrenamiento ni nueva inferencia',
        propagacion='Entradas y predicciones congeladas; no se simula contaminación futura',
        diario='Máximo de cada estación, todos los ataques de su día juntos. No es máximo global de red',
        agregado='Micro suma eventos y oportunidades; macro promedia tasas de estaciones por igual. Ninguno es una contingencia de red',
        dominio='0..255; Base reserva 8..15, B reserva 12..15; rechazo implica lectura perdida',
        restauraciones='Persiste_silenciosos: originales restaurados salvo alteraciones aceptadas sin alerta; diagnóstico, no defensa operativa',
        ocultamiento_evaluable=bool((base.original_ppb>=155).any()),maximo_limpio=float(base.original_ppb.max()),
        alcance='Un periodo de 2025 repetido con otros sorteos; no valida otros años ni ataques dirigidos',
        criterio='Primario: cambio de banda por lectura sin alerta entre todos los intentos; reportar costos y cada estación. No seleccionar estaciones ganadoras',
        comprobacion_CCA='Reproduce exactamente los conteos del 08',ataques_cifrados_evaluados=len(at))
    return dict(por_estacion=total,pareados=pd.DataFrame(pareados),micro=micro,macro=macro,
        por_semilla=rs,por_n=pn,limpios=pd.DataFrame(limpios),cobertura=cobertura,
        plan=pd.concat(planes,ignore_index=True),ataques=at,diario=diario),info


def guardar(raiz,r,info):
    raiz=Path(raiz);dest=raiz/'experiments/cayenne_mod/resultados/11'
    files=[Path(__file__),raiz/'experiments/cayenne_mod/campana_cca.py',raiz/'experiments/cayenne_mod/selectiva_red.py',raiz/'src/decision/nom172.py']
    meta=dict(info,codigo_sha256={str(p.relative_to(raiz)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    path=dest/'protocolo.json'
    if path.exists() and json.loads(path.read_text())!=meta: raise ValueError('No sobrescribir protocolo distinto')
    dest.mkdir(parents=True,exist_ok=True)
    for name,df in r.items():
        comp=name in ('plan','ataques','diario')
        df.to_csv(dest/f"{name}.csv{'.gz' if comp else ''}",index=False,compression={'method':'gzip','mtime':0} if comp else None)
    path.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    return dest


def graficar(r,dest):
    import matplotlib.pyplot as plt
    p=r['pareados'].sort_values('diferencia_pp')
    fig,ax=plt.subplots(figsize=(10,8),layout='constrained')
    ax.barh(p.estacion,p.diferencia_pp,color=np.where(p.diferencia_pp<0,'#157F86','#C76A18'))
    ax.axvline(0,color='black',lw=1)
    ax.set(xlabel='Tasa B − tasa Base (puntos porcentuales por intento)',ylabel='Estación',
        title='Cambio de banda por lectura sin alerta · mismas 100 campañas por estación\nNegativo favorece B; positivo favorece Base. Predicciones guardadas.')
    ax.grid(axis='x',alpha=.2)
    fig.savefig(dest/'comparacion_estaciones.png',dpi=160)


def cargar(raiz):
    """Lectura rápida del informe ejecutado; verifica fuentes, código y tablas."""
    raiz=Path(raiz);dest=raiz/'experiments/cayenne_mod/resultados/11'
    meta=json.loads((dest/'protocolo.json').read_text())
    verificar_fuentes(raiz)
    for name,h in dict(meta['fuentes'],**meta['codigo_sha256']).items():
        assert hashlib.sha256((raiz/name).read_bytes()).hexdigest()==h,name
    firmas=json.loads((dest/'archivos.json').read_text())
    r={}
    for name,h in firmas.items():
        p=dest/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
        clave=name.split('.csv')[0]
        if clave not in ('plan','ataques','diario'):
            r[clave]=pd.read_csv(p)
    return r,meta,dest


def firmar_tablas(destino):
    destino=Path(destino)
    firmas={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destino.glob('*.csv*'))}
    (destino/'archivos.json').write_text(json.dumps(firmas,indent=2)+'\n')
