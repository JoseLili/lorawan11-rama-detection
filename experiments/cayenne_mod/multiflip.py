"""Experimento 07: máscaras de N flips distintos, enumeración exacta.

Se agrupan efectos por (valor original, valor recibido), conservando las
predicciones, umbrales y contexto diario de cada mensaje al calcularlos.
Esta compresión evita materializar miles de millones de filas equivalentes.
"""
from pathlib import Path
from itertools import combinations
from math import comb
import hashlib
import json
import platform

import numpy as np
import pandas as pd

from experiments.cayenne_mod.selectiva_red import PESOS, codificar, decodificar
from experiments.graficas_revision.generar import verificar_fuentes
from src.detect.red import contexto_diario, efectos_red
from src.ingest.rama import load_wide, to_long

GRUPO_8 = (3, 4, 5, 8, 9, 10, 11)
TIPOS = ("cambio_banda_red", "falsa_fase1", "anulada_fase1")
ESCOPOS = (("grupo_7x8", "B", GRUPO_8),
           ("campo_16", "base", tuple(range(16))),
           ("campo_16", "A", tuple(range(16))),
           ("campo_16", "B", tuple(range(16))))


def construir_efectos(contexto, con_lstm):
    """H[métrica][v,r] = número de mensajes originales v con ese efecto al recibir r."""
    c = contexto.reset_index(drop=True)
    x = c.original_ppb.to_numpy()
    if not np.isfinite(x).all() or (x != np.rint(x)).any() or (x < 0).any() or (x > 255).any():
        raise ValueError("Se requieren originales enteros 0..255, sin recortar")
    x = x.astype(int)
    nombres = list(TIPOS)
    if con_lstm:
        if not c.evaluable.all():
            raise ValueError("Falta detector para alguna lectura")
        nombres += [t+"_no_detectado" for t in TIPOS]
        nombres += ["alertas", "amplitud_supera_p95", "amplitud_supera_p95_sin_alerta"]
    h = {nombre: np.zeros((256,256),dtype=np.int64) for nombre in nombres}
    ejemplos = []
    for recibido in range(256):
        valores = np.full(len(c), recibido, dtype=float)
        efectos = efectos_red(c, valores)
        datos = {t: efectos[t].to_numpy() for t in TIPOS}
        if con_lstm:
            valor_modelo = c.base_ppb.to_numpy(dtype=np.float32) + (valores-c.perfil_ppb.to_numpy()).astype(np.float32)
            residuo = np.abs(valor_modelo-c.predicho_ppb.to_numpy())
            alerta = residuo > c.umbral_ppb.to_numpy()
            grande = np.abs(valores-x) > c.umbral_ppb.to_numpy()
            datos.update({t+"_no_detectado": datos[t] & ~alerta for t in TIPOS})
            datos.update(alertas=alerta, amplitud_supera_p95=grande,
                         amplitud_supera_p95_sin_alerta=grande & ~alerta)
            if len(ejemplos) < 8:
                candidatos = np.flatnonzero(datos["cambio_banda_red_no_detectado"] & (np.abs(valores-x) >= 32))
                if len(candidatos):
                    i = int(candidatos[0])
                    fila = c.iloc[i]
                    ejemplos.append(dict(timestamp=fila.timestamp, estacion=fila.estacion,
                        original=int(x[i]), recibido=recibido, delta=int(recibido-x[i]),
                        predicho=float(fila.predicho_ppb), umbral=float(fila.umbral_ppb),
                        residuo=float(residuo[i]), maximo_original=float(fila.maximo_original_ppb),
                        maximo_atacado=float(efectos.maximo_atacado_ppb.iloc[i])))
        for nombre, mascara in datos.items():
            h[nombre][:,recibido] = np.bincount(x[mascara], minlength=256)
    return h, np.bincount(x,minlength=256), pd.DataFrame(ejemplos)


def mascaras_aceptadas(formato, posiciones, n):
    """Las demás máscaras se rechazan: activan al menos un bit reservado."""
    activas = [b for b in posiciones if b < len(PESOS[formato])]
    return np.array([sum(1<<b for b in grupo) for grupo in combinations(activas,n)],dtype=np.int64)


def tabla_decodificada(formato):
    palabras = np.arange(1<<len(PESOS[formato]),dtype=np.int64)
    return sum(((palabras>>bit)&1)*peso for bit,peso in enumerate(PESOS[formato]))


def enumerar(h, frecuencias, escopos=ESCOPOS):
    """Cada N tiene su denominador C(posiciones,N), no se mezclan presupuestos."""
    n_mensajes = int(frecuencias.sum())
    v = np.flatnonzero(frecuencias)
    f = frecuencias[v]
    resumen, por_mascara, deltas = [], [], []
    con_lstm = "alertas" in h
    for alcance, formato, posiciones in escopos:
        lookup = tabla_decodificada(formato)
        palabras = np.array([int.from_bytes(codificar(int(x),formato)[2:],"big") for x in v])
        for n in range(1,len(posiciones)+1):
            masks = mascaras_aceptadas(formato,posiciones,n)
            total_masks = comb(len(posiciones),n)
            total = n_mensajes * total_masks
            aceptados = n_mensajes * len(masks)
            rechazados = total-aceptados
            row = dict(alcance=alcance,formato=formato,n_flips=n,n_mensajes=n_mensajes,
                       n_mascaras=total_masks,mascaras_aceptadas=len(masks),
                       n_escenarios=total,aceptados=aceptados,rechazos=rechazados,
                       pct_rechazos=100*rechazados/total)
            if len(masks):
                r = lookup[palabras[:,None] ^ masks[None,:]]
                delta = r-v[:,None]
                absdelta = np.abs(delta)
                pesos_mask = np.array([sum(peso for b,peso in enumerate(PESOS[formato]) if (int(m)>>b)&1) for m in masks])
                cancel = ((delta==0)*f[:,None]).sum(axis=0,dtype=np.int64)
                parcial = (((absdelta>0)&(absdelta<pesos_mask[None,:]))*f[:,None]).sum(axis=0,dtype=np.int64)
                sum_abs = (absdelta*f[:,None]).sum(axis=0,dtype=np.int64)
                dm = pd.DataFrame(dict(alcance=alcance,formato=formato,n_flips=n,
                                      mascara=masks, cancelaciones=cancel,compensaciones_parciales=parcial))
                conteos = {nombre: matriz[v[:,None],r].sum(axis=0,dtype=np.int64) for nombre,matriz in h.items()}
                for nombre, cuenta in conteos.items():
                    dm[nombre]=cuenta
                    row[nombre]=int(cuenta.sum())
                row.update(cancelaciones=int(cancel.sum()),compensaciones_parciales=int(parcial.sum()),
                           delta_abs_medio_aceptados=float(sum_abs.sum()/aceptados),delta_abs_max=int(absdelta.max()))
                hist = np.bincount((delta+255).ravel(),weights=np.broadcast_to(f[:,None],delta.shape).ravel(),minlength=511)
                for d in np.flatnonzero(hist):
                    deltas.append(dict(alcance=alcance,formato=formato,n_flips=n,delta_ppb=int(d)-255,
                                       escenarios=int(hist[d]),prob_sobre_todos=float(hist[d]/total)))
                if con_lstm:
                    alertas_cancel = int((h["alertas"][v,v,None]*(delta==0)).sum())
                    row["alertas_sin_cambio_valor"] = alertas_cancel
                    row["recall_sobre_valores_cambiados_pct"] = (100*(row["alertas"]-alertas_cancel)/(aceptados-row["cancelaciones"])
                                                                  if aceptados>row["cancelaciones"] else np.nan)
                    col="cambio_banda_red_no_detectado"
                    j=int(np.argmax(conteos[col]))
                    row["peor_mascara_fija"] = f"0x{int(masks[j]):04X}" if conteos[col][j] else ""
                    row["escapes_peor_mascara_fija"] = int(conteos[col][j])
                por_mascara.append(dm)
            else:
                row.update({nombre:0 for nombre in h})
                row.update(cancelaciones=0,compensaciones_parciales=0,
                           delta_abs_medio_aceptados=np.nan,delta_abs_max=np.nan)
                if con_lstm:
                    row.update(alertas_sin_cambio_valor=0,recall_sobre_valores_cambiados_pct=np.nan,
                               peor_mascara_fija="",escapes_peor_mascara_fija=0)
            row["pct_cancelacion_sobre_todos"] = 100*row["cancelaciones"]/total
            row["pct_cancelacion_aceptados"] = 100*row["cancelaciones"]/aceptados if aceptados else np.nan
            for tipo in TIPOS:
                row[tipo+"_esperados"] = row[tipo]/total_masks
                row[tipo+"_pct_todos"] = 100*row[tipo]/total
                if con_lstm:
                    ne = row[tipo+"_no_detectado"]
                    row[tipo+"_escape_esperado"] = ne/total_masks
                    row[tipo+"_escape_pct_todos"] = 100*ne/total
                    row[tipo+"_escape_pct_aceptados"] = 100*ne/aceptados if aceptados else np.nan
            if con_lstm:
                row["pct_alerta_aceptados"] = 100*row["alertas"]/aceptados if aceptados else np.nan
            resumen.append(row)
    return dict(resumen=pd.DataFrame(resumen),por_mascara=pd.concat(por_mascara,ignore_index=True),
                deltas=pd.DataFrame(deltas))


def validar_mascaras_cifradas():
    """Todas las 65535 máscaras físicas para 3 originales y 3 formatos."""
    from src.encoding.crypto import encrypt,decrypt
    from src.attack.blind import APPSKEY,DEVADDR
    contador=0
    for formato in PESOS:
        lookup=tabla_decodificada(formato)
        for valor in (0,28,60):
            payload=codificar(valor,formato)
            c=encrypt(payload,APPSKEY,DEVADDR,valor+1)
            # Mismo flujo XOR aplicado a un lote de mensajes contrafactuales.
            flujo=np.frombuffer(encrypt(bytes(4),APPSKEY,DEVADDR,valor+1),dtype=np.uint8)
            masks=np.arange(1,65536,dtype=np.uint16)
            atacados=np.tile(np.frombuffer(c,dtype=np.uint8),(len(masks),1))
            atacados[:,2] ^= (masks>>8).astype(np.uint8)
            atacados[:,3] ^= (masks&255).astype(np.uint8)
            desc=atacados ^ flujo
            palabras=(desc[:,2].astype(np.uint16)<<8) | desc[:,3]
            np.testing.assert_array_equal(palabras,int.from_bytes(payload[2:],"big")^masks)
            for mask in (1, (1<<3)|(1<<11), (1<<5)|(1<<9)|(1<<10)|(1<<11),65535):
                mutada=bytes(atacados[mask-1])
                recuperada=decrypt(mutada,APPSKEY,DEVADDR,valor+1)
                assert recuperada==bytes(desc[mask-1])
                resultado=decodificar(recuperada,formato)
                palabra=int(palabras[mask-1])
                assert resultado==(int(lookup[palabra]) if palabra<len(lookup) else None)
            contador+=len(masks)
    return contador


def construir(raiz):
    raiz=Path(raiz)
    carpeta,ctx,fuentes=verificar_fuentes(raiz)
    h,f,ej=construir_efectos(ctx,True)
    assert int(np.trace(h["alertas"])) == int(ctx.alerta_limpia.sum())
    test=enumerar(h,f)
    matriz=(to_long(load_wide(raiz/"data/raw/2025O3.xls"),"O3")
            .pivot(index="timestamp",columns="station",values="value").sort_index().dropna(axis=1,how="all"))
    ctxa=contexto_diario(matriz)
    ha,fa,_=construir_efectos(ctxa,False)
    anual=enumerar(ha,fa)
    # El caso de un flip en las 16 posiciones debe reproducir el experimento 05.
    for prefijo,actual in [("test",test),("anual",anual)]:
        anterior_path=raiz/f"experiments/cayenne_mod/resultados/05/{prefijo}_resumen.csv"
        anterior=pd.read_csv(anterior_path)
        fuentes[str(anterior_path.relative_to(raiz))]=hashlib.sha256(anterior_path.read_bytes()).hexdigest()
        for old in anterior.itertuples():
            new=actual["resumen"].query("alcance == 'campo_16' and n_flips == 1 and formato == @old.formato").iloc[0]
            assert new[old.tipo_dano]==old.daninos
            assert new.rechazos==old.rechazos
            if prefijo=="test":
                assert new[old.tipo_dano+"_no_detectado"]==old.daninos_no_detectados
    # Ejemplos reales: la máscara B se obtiene entre representaciones canónicas.
    if not ej.empty:
        ej["mascara_B"]=[int.from_bytes(codificar(int(v),"B")[2:],"big") ^ int.from_bytes(codificar(int(r),"B")[2:],"big")
                         for v,r in zip(ej.original,ej.recibido)]
        ej["n_flips_B"]=ej.mascara_B.map(lambda m: int(m).bit_count())
        test["ejemplos_grandes_sin_alerta"]=ej
    info=dict(fuentes=fuentes,pesos=PESOS,grupo_8=GRUPO_8,escopos=ESCOPOS,
        dominio=[0,255],test_mensajes=len(ctx),test_dias=ctx.fecha.nunique(),
        test_periodo=[str(ctx.fecha.min().date()),str(ctx.fecha.max().date())],
        test_maximo_ppb=float(ctx.maximo_original_ppb.max()),fpr_limpio_pct=100*float(ctx.alerta_limpia.mean()),
        anual_mensajes=len(ctxa),anual_dias=ctxa.fecha.nunique(),
        anual_dias_excedencia=int(ctxa.groupby("fecha").maximo_original_ppb.first().ge(155).sum()),
        modelo="Predicciones y p95 propios GUARDADOS del notebook 09; sin entrenamiento ni nueva inferencia",
        escenario="N posiciones distintas de un mensaje; otras lecturas/perfiles quedan intactos",
        promedio="Todas las máscaras del presupuesto con peso 1/C(numero_posiciones,N); no muestreo",
        compresion="Efectos por mensaje agrupados por original/recibido; conteos exactos, sin promediar predicciones",
        rechazos="Cualquier posición reservada activada: pérdida de lectura; no se modela decisión tras pérdida",
        casos_sin_dano="Cero ocultamientos en test por máximo <155; no acredita protección",
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__)
    return test,anual,info


def guardar(raiz,test,anual,info):
    raiz=Path(raiz)
    destino=raiz/"experiments/cayenne_mod/resultados/07"
    nombres=[Path(__file__),raiz/"experiments/cayenne_mod/selectiva_red.py",
             raiz/"experiments/graficas_revision/generar.py",raiz/"src/decision/nom172.py",
             raiz/"src/encoding/cayenne.py",raiz/"src/encoding/crypto.py",raiz/"src/ingest/rama.py",
             raiz/"src/detect/red.py"]
    meta=json.loads(json.dumps(dict(info,codigo_sha256={str(p.relative_to(raiz)):hashlib.sha256(p.read_bytes()).hexdigest() for p in nombres})))
    protocolo=destino/"protocolo.json"
    if protocolo.exists() and json.loads(protocolo.read_text())!=meta:
        raise ValueError("Fuentes/protocolo distintos; no sobrescribir esta referencia")
    destino.mkdir(parents=True,exist_ok=True)
    for prefijo,resultados in [("test",test),("anual",anual)]:
        for nombre,df in resultados.items():
            comp=nombre=="por_mascara"
            df.to_csv(destino/f"{prefijo}_{nombre}.csv{'.gz' if comp else ''}",index=False,
                      compression={"method":"gzip","mtime":0} if comp else None)
    protocolo.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
    return destino


def graficar(test, anual, destino):
    import matplotlib.pyplot as plt
    colores = {"base":"#555555", "A":"#C76A18", "B":"#157F86"}
    t = test["resumen"]
    g = t.query("alcance == 'grupo_7x8'")
    fig,axs = plt.subplots(1,3,figsize=(15,4.5),layout="constrained")
    axs[0].plot(g.n_flips,g.pct_cancelacion_aceptados,"o-",color=colores["B"])
    axs[0].set(ylabel="Valor intacto (%)",title="La cancelación depende de N")
    axs[1].plot(g.n_flips,g.cambio_banda_red_esperados,"o-",label="Cambian banda diaria")
    axs[1].plot(g.n_flips,g.cambio_banda_red_escape_esperado,"o-",label="Cambian banda sin alerta")
    axs[1].set(ylabel="Oportunidades esperadas / 35 704",title="Cancelar algunos no elimina el daño")
    axs[1].legend(fontsize=8)
    axs[2].plot(g.n_flips,g.recall_sobre_valores_cambiados_pct,"o-",color="#81449C")
    axs[2].set(ylabel="Lecturas alteradas con alerta (%)",title="El detector ve el resultado neto",ylim=(0,100))
    for ax in axs:
        ax.set(xlabel="N bits distintos de los siete de peso 8",xticks=range(1,8))
        ax.grid(alpha=.2)
    fig.suptitle("B: promedio exacto entre máscaras del mismo tamaño · predicciones guardadas")
    fig.savefig(destino/"grupo_7x8.png",dpi=160)

    fig,axs = plt.subplots(1,3,figsize=(15,4.5),layout="constrained")
    cols = [("cambio_banda_red_escape_pct_todos","Cambiar banda sin alerta (%)","Entre todos los intentos"),
            ("cambio_banda_red_escape_pct_aceptados","Cambiar banda sin alerta (%)","Sólo entre mensajes aceptados"),
            ("pct_rechazos","Mensajes rechazados (%)","Rechazo no equivale a detección LSTM")]
    for ax,(col,ylabel,title) in zip(axs,cols):
        for formato,color in colores.items():
            d = t.query("alcance == 'campo_16' and formato == @formato")
            ax.plot(d.n_flips,d[col],"o-",label=formato,color=color,markersize=3)
        ax.set(xlabel="N bits distintos del campo de 16",ylabel=ylabel,title=title,xticks=(1,2,4,6,8,10,12,14,16))
        ax.grid(alpha=.2)
        ax.legend()
    fig.suptitle("Campo completo: mismos N y posiciones elegibles · faltantes cuando no hay aceptados")
    fig.savefig(destino/"campo_16.png",dpi=160)

    fig,axs = plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    for formato,color in colores.items():
        d = t.query("alcance == 'campo_16' and formato == @formato")
        axs[0].plot(d.n_flips,100*d.escapes_peor_mascara_fija/d.n_mensajes,"o-",color=color,label=formato)
        a = anual["resumen"].query("alcance == 'campo_16' and formato == @formato")
        axs[1].plot(a.n_flips,a.anulada_fase1_esperados,"o-",color=color,label=formato)
    axs[0].set(title="Peor máscara fija observada (retrospectiva)",ylabel="Cambiar banda sin alerta (%)")
    axs[1].set(title="Año completo: ocultar máximo ≥155, sin LSTM",ylabel="Oportunidades esperadas / 218 823")
    for ax in axs:
        ax.set(xlabel="N bits distintos del campo de 16",xticks=(1,2,4,6,8,10,12,14,16))
        ax.grid(alpha=.2)
        ax.legend()
    fig.savefig(destino/"mascara_fija_y_anual.png",dpi=160)
