"""08: campañas pareadas aleatorias sobre CCA, con predicciones 09 fijas.

Tres sorteos independientes: selección Bernoulli, N uniforme, posiciones sin
reemplazo. Sólo el payload de valor se modifica; no simula la trama completa.
"""
from pathlib import Path
from math import comb
import hashlib
import json
import platform

import numpy as np
import pandas as pd

from experiments.cayenne_mod.selectiva_red import FORMATOS, PESOS, codificar, decodificar
from experiments.graficas_revision.generar import verificar_fuentes
from src.attack.blind import APPSKEY, DEVADDR
from src.encoding.crypto import encrypt, decrypt
from src.encoding.cayenne import flip_bit
from src.decision.nom172 import banda_o3
from src.ingest.rama import load_wide, to_long

SEMILLAS = tuple(range(42,142))
TASA = .05
CONTEOS = ('ataques','rechazos','aceptados_atacados','cancelaciones','alterados',
           'detectados_alterados','alertas_cancelados','banda_local_cambiada',
           'banda_local_sin_alerta','falsa_excedencia','falsa_excedencia_sin_alerta',
           'ocultamiento','ocultamiento_sin_alerta')


def cargar_cca(raiz):
    raiz=Path(raiz)
    carpeta,base,fuentes=verificar_fuentes(raiz)
    c=base.query("estacion == 'CCA'").copy()
    c['timestamp']=pd.to_datetime(c.timestamp)
    # Sólo columnas del detector: jamás reutilizar máximos de toda la red.
    c=c[['timestamp','estacion','original_ppb','base_ppb','perfil_ppb',
         'predicho_ppb','umbral_ppb','alerta_limpia']].sort_values('timestamp').reset_index(drop=True)
    raw=to_long(load_wide(raiz/'data/raw/2025O3.xls'),'O3').query("station == 'CCA'")
    raw=raw[raw.timestamp.between(c.timestamp.min(),c.timestamp.max())]
    obs=raw.dropna(subset=['value']).sort_values('timestamp')
    np.testing.assert_array_equal(obs.timestamp.to_numpy(),c.timestamp.to_numpy())
    np.testing.assert_array_equal(obs.value.to_numpy(),c.original_ppb.to_numpy())
    assert not c.timestamp.duplicated().any()
    assert c.original_ppb.between(0,255).all()
    np.testing.assert_array_equal(c.original_ppb,np.rint(c.original_ppb))
    c['fecha']=c.timestamp.dt.normalize()
    c['id_mensaje']=np.arange(len(c))
    c['fcnt']=np.arange(1,len(c)+1)
    # Cálculo limpio conservando exactamente la aritmética float32 del 09.
    pred_val=c.base_ppb.to_numpy(dtype=np.float32)+(c.original_ppb-c.perfil_ppb).to_numpy(dtype=np.float32)
    np.testing.assert_array_equal(np.abs(pred_val-c.predicho_ppb.to_numpy())>c.umbral_ppb.to_numpy(),c.alerta_limpia)
    for nombre in ['CCA/predicciones.csv','CCA/modelo.keras','CCA/umbral_p95.txt']:
        p=carpeta/nombre
        fuentes[str(p.relative_to(raiz))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return c,dict(fuentes=fuentes,horas_periodo=len(raw),faltantes_raw=int(raw.value.isna().sum()),
        n_mensajes=len(c),n_dias=c.fecha.nunique(),inicio=str(c.timestamp.min()),fin=str(c.timestamp.max()),
        umbral_ppb=float(c.umbral_ppb.iloc[0]),maximo_limpio_ppb=float(c.original_ppb.max()),
        alertas_limpias=int(c.alerta_limpia.sum()),fpr_limpio_pct=100*float(c.alerta_limpia.mean()))


def sortear_plan(n_mensajes,semilla,tasa=TASA):
    if n_mensajes<0 or not 0<=tasa<=1:
        raise ValueError('Número de mensajes y tasa inválidos')
    hijos=np.random.SeedSequence(semilla).spawn(3)
    rsel,rn,rpos=[np.random.default_rng(h) for h in hijos]
    elegido=rsel.random(n_mensajes)<tasa
    # N se sortea para todos los índices, independiente de la selección.
    presupuestos=rn.integers(1,17,size=n_mensajes)
    n=np.where(elegido,presupuestos,0)
    masks=np.zeros(n_mensajes,dtype=np.int64)
    for i in np.flatnonzero(elegido):
        bits=rpos.choice(16,size=int(n[i]),replace=False)
        masks[i]=sum(1<<int(b) for b in bits)
    return pd.DataFrame({'id_mensaje':np.arange(n_mensajes),'atacado':elegido,
                         'n_flips':n,'mascara':masks})


def evaluar(c,plan,formato,semilla):
    """Pasa cada mensaje atacado por cifrado/flip/descifrado y decodificación."""
    np.testing.assert_array_equal(c.id_mensaje,plan.id_mensaje)
    d=c.copy()
    for col in ('atacado','n_flips','mascara'):
        d[col]=plan[col].to_numpy()
    d['semilla'],d['formato']=semilla,formato
    x=c.original_ppb.to_numpy()
    recibidos=x.astype(float).copy()
    for i in np.flatnonzero(plan.atacado):
        p=codificar(int(x[i]),formato)
        cifrada=encrypt(p,APPSKEY,DEVADDR,int(c.fcnt.iloc[i]))
        mask=int(plan.mascara.iloc[i])
        for b in range(16):
            if (mask>>b)&1:
                cifrada=flip_bit(cifrada,b)
        recuperada=decrypt(cifrada,APPSKEY,DEVADDR,int(c.fcnt.iloc[i]))
        assert recuperada==p[:2]+(int.from_bytes(p[2:],'big')^mask).to_bytes(2,'big')
        r=decodificar(recuperada,formato)
        recibidos[i]=np.nan if r is None else r
    aceptado=np.isfinite(recibidos)
    atacado=d.atacado.to_numpy()
    delta=recibidos-x
    valor_modelo=c.base_ppb.to_numpy(dtype=np.float32)+(recibidos-c.perfil_ppb.to_numpy()).astype(np.float32)
    residuo=np.abs(valor_modelo-c.predicho_ppb.to_numpy())
    alerta=aceptado & (residuo>c.umbral_ppb.to_numpy())
    alterado=atacado & aceptado & (delta!=0)
    dano=alterado & (banda_o3(x)!=banda_o3(recibidos))
    falsa=alterado & (x<155) & (recibidos>=155)
    oculta=alterado & (x>=155) & (recibidos<155)
    d['recibido_ppb'],d['delta_ppb'],d['residuo_ppb']=recibidos,delta,residuo
    d['aceptado']=aceptado
    d['alerta']=pd.array(np.where(aceptado,alerta,None),dtype='boolean')
    for nombre,valor in dict(ataques=atacado,rechazos=atacado & ~aceptado,
            aceptados_atacados=atacado & aceptado,cancelaciones=atacado & aceptado & (delta==0),
            alterados=alterado,detectados_alterados=alterado & alerta,
            alertas_cancelados=atacado & aceptado & (delta==0) & alerta,
            banda_local_cambiada=dano,banda_local_sin_alerta=dano & ~alerta,
            falsa_excedencia=falsa,falsa_excedencia_sin_alerta=falsa & ~alerta,
            ocultamiento=oculta,ocultamiento_sin_alerta=oculta & ~alerta).items():
        d[nombre]=valor
    d['limpios']=~atacado
    d['falsas_alarmas_limpios']=~atacado & alerta
    return d


def diario(d):
    """Máximo observado de CCA con todos los ataques del día presentes.

    Principal: máximo de recibidos disponibles, rechazados como NaN. Las dos
    referencias adicionales separan alteración de valor y pérdida de datos;
    usan originales del simulador y NO son imputaciones disponibles al AS.
    """
    filas=[]
    for fecha,g in d.groupby('fecha',sort=True):
        x=g.original_ppb.to_numpy()
        r=g.recibido_ppb.to_numpy()
        ok=np.isfinite(r)
        original=float(x.max())
        recibido=float(np.max(r[ok])) if ok.any() else np.nan
        solo_valores=float(np.where(ok,r,x).max())
        solo_perdidas=float(x[ok].max()) if ok.any() else np.nan
        indefinido=not ok.any()
        fila=dict(semilla=int(g.semilla.iloc[0]),formato=g.formato.iloc[0],fecha=fecha,
            observados=len(g),ataques=int(g.atacado.sum()),rechazos=int(g.rechazos.sum()),
            aceptados=int(ok.sum()),maximo_original=original,maximo_recibido=recibido,
            maximo_solo_valores=solo_valores,maximo_solo_perdidas=solo_perdidas,
            banda_original=banda_o3(original),banda_recibida=banda_o3(recibido),
            dia_sin_datos=indefinido,dia_con_perdida=bool(g.rechazos.any()),
            cambio_banda_disponibles=not indefinido and banda_o3(original)!=banda_o3(recibido),
            cambio_banda_solo_valores=banda_o3(original)!=banda_o3(solo_valores),
            cambio_banda_solo_perdidas=not indefinido and banda_o3(original)!=banda_o3(solo_perdidas),
            falsa_excedencia=not indefinido and original<155<=recibido,
            ocultamiento=not indefinido and recibido<155<=original,
            alertas_totales=int(g.alerta.sum()),
            alertas_en_valores_alterados=int(g.detectados_alterados.sum()),
            lecturas_banda_sin_alerta=int(g.banda_local_sin_alerta.sum()))
        filas.append(fila)
    return pd.DataFrame(filas)


def resumen_mensajes(d):
    r={nombre:int(d[nombre].sum()) for nombre in CONTEOS}
    r.update(semilla=int(d.semilla.iloc[0]),formato=d.formato.iloc[0],mensajes=len(d),
             limpios=int(d.limpios.sum()),falsas_alarmas_limpios=int(d.falsas_alarmas_limpios.sum()))
    def pct(n,den):
        return 100*n/den if den else np.nan
    r.update(tasa_real_ataque_pct=pct(r['ataques'],r['mensajes']),
             rechazo_ataques_pct=pct(r['rechazos'],r['ataques']),
             recall_alterados_pct=pct(r['detectados_alterados'],r['alterados']),
             banda_sin_alerta_por_ataque_pct=pct(r['banda_local_sin_alerta'],r['ataques']),
             banda_sin_alerta_por_aceptado_pct=pct(r['banda_local_sin_alerta'],r['aceptados_atacados']),
             fpr_limpios_pct=pct(r['falsas_alarmas_limpios'],r['limpios']))
    return r


def construir(raiz,semillas=SEMILLAS,tasa=TASA):
    c,info=cargar_cca(raiz)
    semillas=tuple(semillas)
    if not semillas or len(set(semillas))!=len(semillas):
        raise ValueError('Se requieren semillas distintas')
    res,ataques,dias,por_n,planes=[],[],[],[],[]
    ejemplo=None
    for semilla in semillas:
        plan=sortear_plan(len(c),semilla,tasa)
        p=plan.loc[plan.atacado].copy()
        p['semilla']=semilla
        p['timestamp']=c.loc[p.index,'timestamp']
        p['bits']=p.mascara.map(lambda m: ','.join(str(b) for b in range(16) if (int(m)>>b)&1))
        planes.append(p)
        for formato in FORMATOS:
            d=evaluar(c,plan,formato,semilla)
            at=d.loc[d.atacado].copy()
            ataques.append(at)
            dia=diario(d)
            dias.append(dia)
            r=resumen_mensajes(d)
            for col in ['cambio_banda_disponibles','cambio_banda_solo_valores','cambio_banda_solo_perdidas',
                        'dia_con_perdida','dia_sin_datos','falsa_excedencia','ocultamiento']:
                r['dias_'+col]=int(dia[col].sum())
            res.append(r)
            for n in range(1,17):
                gn=at.loc[at.n_flips==n]
                fila=dict(semilla=semilla,formato=formato,n_flips=n)
                fila.update({nombre:int(gn[nombre].sum()) for nombre in CONTEOS})
                por_n.append(fila)
            if semilla==semillas[0]:
                ejemplo=pd.concat([ejemplo,d],ignore_index=True) if ejemplo is not None else d.copy()
    resumen=pd.DataFrame(res)
    detalle_dias=pd.concat(dias,ignore_index=True)
    resultados=dict(contexto_limpio=c,plan_ataques=pd.concat(planes,ignore_index=True),
        ataques=pd.concat(ataques,ignore_index=True),serie_ejemplo=ejemplo,
        diario=detalle_dias,resumen_por_semilla=resumen,por_n=pd.DataFrame(por_n))
    metricas=[col for col in resumen if col not in ('semilla','formato')]
    estadisticas=[]
    for formato,g in resumen.groupby('formato',sort=False):
        for metrica in metricas:
            s=g[metrica].dropna()
            estadisticas.append(dict(formato=formato,metrica=metrica,media=s.mean(),
                mediana=s.median(),p05=s.quantile(.05),p95=s.quantile(.95),
                minimo=s.min(),maximo=s.max(),n_semillas_definidas=len(s)))
    resultados['estadisticas']=pd.DataFrame(estadisticas)
    pareados=[]
    rb=resumen.query("formato == 'base'").set_index('semilla')
    for formato in ('A','B'):
        alt=resumen.query('formato == @formato').set_index('semilla')
        for metrica in ('banda_local_sin_alerta','rechazos','dias_cambio_banda_disponibles','dias_cambio_banda_solo_valores'):
            dif=alt[metrica]-rb[metrica]
            pareados.append(dict(formato=formato,metrica=metrica,diferencia_media_vs_base=dif.mean(),
                                 p05=dif.quantile(.05),p95=dif.quantile(.95),
                                 semillas_menor=int((dif<0).sum()),semillas_igual=int((dif==0).sum()),
                                 semillas_mayor=int((dif>0).sum())))
    resultados['pareados']=pd.DataFrame(pareados)
    # Conteos agregados por N: mismas oportunidades en los tres formatos.
    pn=resultados['por_n'].groupby(['formato','n_flips'],sort=False)[list(CONTEOS)].sum().reset_index()
    for nombre,num,den in [('rechazo_pct','rechazos','ataques'),
                           ('recall_alterados_pct','detectados_alterados','alterados'),
                           ('banda_sin_alerta_por_ataque_pct','banda_local_sin_alerta','ataques')]:
        pn[nombre]=100*pn[num]/pn[den].replace(0,np.nan)
    pn['rechazo_teorico_pct']=[100*(1-comb(len(PESOS[f]),int(n))/comb(16,int(n))) for f,n in zip(pn.formato,pn.n_flips)]
    resultados['resumen_por_n']=pn
    info.update(semillas=list(semillas),semilla_ejemplo=semillas[0],tasa=tasa,
        seleccion='Bernoulli independiente por lectura válida; no exige exactamente 5%',
        n_flips='Uniforme discreta 1..16, condicionada a que haya ataque',
        posiciones='Subconjunto uniforme sin reemplazo del campo de 16 bits del valor',
        pareado='Mismos mensajes, N y máscaras físicas para Base/A/B',pesos=PESOS,
        modelo='Predicciones y p95 GUARDADOS de CCA del notebook 09; sin entrenamiento ni nueva inferencia',
        detector='Modelo 09 previamente entrenado con variables de red; sólo se evalúa CCA y se congelan entradas/predicciones',
        diario='Máximo observado de CCA, ataques simultáneos en la serie. No es máximo de red ni decisión oficial',
        rechazos='NaN: lectura perdida, sin alerta LSTM evaluable. No imputar cero ni quitar lecturas por alertas',
        referencias_diarias='Solo valores restaura originales de rechazados; solo pérdidas conserva originales aceptados. Contrafactuales del simulador, no política operativa',
        deteccion='Por lectura. Los días con banda distinta no se etiquetan automáticamente como escapes del detector',
        limite='Sin propagación a ventanas/perfiles futuros; mismo periodo reutilizado, sin validación externa',
        intervalo='p05-p95 describe variación entre campañas; no es intervalo de confianza poblacional',
        transformaciones_cifradas=int(resultados['ataques'].shape[0]),
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__)
    return resultados,info


def guardar(raiz,resultados,info):
    raiz=Path(raiz)
    destino=raiz/'experiments/cayenne_mod/resultados/08'
    archivos=[Path(__file__),raiz/'experiments/cayenne_mod/selectiva_red.py',
        raiz/'experiments/graficas_revision/generar.py',raiz/'src/encoding/cayenne.py',
        raiz/'src/encoding/crypto.py',raiz/'src/decision/nom172.py',raiz/'src/ingest/rama.py']
    meta=json.loads(json.dumps(dict(info,codigo_sha256={str(p.relative_to(raiz)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos})))
    protocolo=destino/'protocolo.json'
    if protocolo.exists() and json.loads(protocolo.read_text())!=meta:
        raise ValueError('Referencia 08 con otro protocolo; no sobrescribir')
    destino.mkdir(parents=True,exist_ok=True)
    grandes={'ataques','serie_ejemplo','diario'}
    for nombre,df in resultados.items():
        comp=nombre in grandes
        df.to_csv(destino/f"{nombre}.csv{'.gz' if comp else ''}",
                  index=False,compression={'method':'gzip','mtime':0} if comp else None)
    protocolo.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
    return destino


def graficar(r,info,destino):
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter
    colores={'base':'#555555','A':'#C76A18','B':'#157F86'}
    s=r['resumen_por_semilla']
    fig,axs=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    for ax,col,titulo in zip(axs,['rechazos','banda_local_sin_alerta','dias_cambio_banda_disponibles'],
                            ['Lecturas rechazadas','Lecturas que cambian banda sin alerta','Días con banda distinta (CCA)']):
        for j,f in enumerate(FORMATOS):
            v=s.loc[s.formato==f,col].to_numpy()
            # Desplazamiento determinista de los puntos para ver las 100 campañas.
            ax.scatter(j+.14*np.sin(np.arange(len(v))*2.4),v,s=12,alpha=.35,color=colores[f])
            ax.scatter(j,v.mean(),marker='_',s=500,color='black',zorder=4)
        ax.set(xticks=range(3),xticklabels=FORMATOS,ylabel='Cantidad por campaña',title=titulo)
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('100 campañas pareadas · 5 % por lectura · N uniforme entre 1 y 16\nCada punto es una semilla; raya negra = promedio. Predicciones CCA guardadas.')
    fig.savefig(destino/'campanas.png',dpi=160)

    fig,axs=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    pn=r['resumen_por_n']
    for f,color in colores.items():
        g=pn.loc[pn.formato==f]
        for ax,col in zip(axs,['rechazo_pct','banda_sin_alerta_por_ataque_pct','recall_alterados_pct']):
            ax.plot(g.n_flips,g[col],'o-',color=color,label=f,markersize=4)
    for ax,title,ylabel in zip(axs,['Rechazo','Cambio de banda local sin alerta','Detección de valores alterados'],
        ['% de ataques','% de ataques','% de valores realmente alterados']):
        ax.set(xlabel='N = bits distintos invertidos en un mensaje',ylabel=ylabel,title=title,xticks=(1,2,4,6,8,10,12,14,16))
        ax.legend()
        ax.grid(alpha=.2)
    fig.suptitle('CCA · Campañas agregadas por N · Huecos = denominador cero, no detección perfecta')
    fig.savefig(destino/'por_n.png',dpi=160)

    d=r['serie_ejemplo']
    inicio=d.timestamp.min()
    fin=inicio+pd.Timedelta(days=14)
    fig,axs=plt.subplots(3,1,figsize=(14,8),sharex=True,layout='constrained')
    for ax,f in zip(axs,FORMATOS):
        g=d.loc[(d.formato==f)&(d.timestamp<fin)]
        ax.plot(g.timestamp,g.original_ppb,color='#AAAAAA',lw=1,label='Original')
        ax.plot(g.timestamp,g.recibido_ppb,color=colores[f],lw=.8,label='Recibido')
        acept=g.loc[g.atacado & g.aceptado]
        rech=g.loc[g.rechazos]
        det=g.loc[g.detectados_alterados]
        ax.scatter(acept.timestamp,acept.recibido_ppb,s=45,facecolors='none',edgecolors='#D78B00',label='Ataque aceptado',zorder=4)
        ax.scatter(rech.timestamp,rech.original_ppb,marker='x',color='#81449C',label='Rechazo (original perdido)',zorder=5)
        ax.scatter(det.timestamp,det.recibido_ppb,s=12,color='red',label='Alteración con alerta',zorder=6)
        ax.set(ylabel=f'{f} · ppb')
        ax.grid(alpha=.15)
    axs[0].legend(ncol=5,fontsize=8,loc='upper left')
    axs[-1].xaxis.set_major_formatter(DateFormatter('%d/%m'))
    fig.suptitle(f"Ejemplo fijado antes de mirar resultados: semilla {info['semilla_ejemplo']}, primeros 14 días\nLas cruces muestran datos perdidos; no son valores recibidos ni alertas LSTM.")
    fig.savefig(destino/'serie_semilla42.png',dpi=160)
