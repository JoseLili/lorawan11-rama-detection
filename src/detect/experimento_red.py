"""Orquestación reproducible V4 multiestación; entrenamiento explícito y reanudable."""
from __future__ import annotations

import gc
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.attack.blind import atacar_serie
from src.detect.red import (perfil_v4_sin_test, contexto_diario, efectos_red,
                            metricas_binarias, resumir_dias)
from src.detect.windows import construir_ventanas
from src.ingest.rama import load_wide, to_long


def cargar_matriz(raiz):
    long = to_long(load_wide(Path(raiz) / 'data/raw/2025O3.xls'), 'O3')
    return long.pivot(index='timestamp', columns='station', values='value').sort_index().dropna(axis=1, how='all')


def ejecutar_red(raiz, entrenar_faltantes=False):
    """Entrena sólo estaciones sin checkpoint; jamás sobrescribe referencia CCA.

    Guarda cada estación antes de avanzar. Reanudar con entrenar_faltantes=True
    NO reentrena checkpoints completos. Sin flag sólo se cargan resultados.
    """
    from tensorflow import keras
    import tensorflow as tf
    from src.detect.lstm import construir_modelo, entrenar, fijar_semilla

    raiz = Path(raiz)
    salida = raiz / 'results/multiestacion_v4_p95_2025'
    salida.mkdir(parents=True, exist_ok=True)
    matriz = cargar_matriz(raiz)
    corte = int(len(matriz) * .8)
    train, test = matriz.iloc[:corte], matriz.iloc[corte:]
    config = dict(protocolo='v4_red_p95_respaldo_train_v1', seed=42, bits=list(range(1,8)),
        ventana=24, perfil_dias=14, split=.8, val_frac=.2, epocas=60, batch=64,
        tau_fase1=155, corte=corte, estaciones=matriz.columns.tolist(),
        dataset_sha256=hashlib.sha256((raiz/'data/raw/2025O3.xls').read_bytes()).hexdigest(),
        tensorflow=tf.__version__, keras=keras.__version__, numpy=np.__version__)
    config['codigo_sha256'] = {p: hashlib.sha256((raiz/p).read_bytes()).hexdigest() for p in
        ['src/detect/experimento_red.py','src/detect/red.py','src/detect/windows.py',
         'src/detect/lstm.py','src/attack/blind.py']}
    firma = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    ruta_config = salida/'configuracion.json'
    if ruta_config.exists():
        if json.loads(ruta_config.read_text()) != config:
            raise ValueError('La configuracion/codigo cambio: no mezclar con checkpoints anteriores.')
    else:
        ruta_config.write_text(json.dumps(config, indent=2)+'\n')

    inventario = []
    for estacion in matriz.columns:
        ntr, nte = int(train[estacion].iloc[24:].notna().sum()), int(test[estacion].iloc[24:].notna().sum())
        nfit = int(ntr*.8)
        motivo = ('sin ventanas de entrenamiento' if nfit == 0 or ntr-nfit == 0
                  else 'sin ventanas de prueba' if nte == 0 else '')
        inventario.append(dict(estacion=estacion,n_train=ntr,n_test=nte,
                               evaluable=not motivo,motivo=motivo))
    cobertura = pd.DataFrame(inventario)
    cobertura.to_csv(salida/'cobertura_estaciones.csv', index=False)
    print(cobertura.to_string(index=False), flush=True)
    print(f'Periodo comun: {test.index[24]} a {test.index[-1]}. '
          f'{int(cobertura.evaluable.sum())}/{len(cobertura)} estaciones evaluables.', flush=True)
    faltantes = [r.estacion for r in cobertura.itertuples() if r.evaluable
                 and not (salida/r.estacion/'estado.json').exists()]
    if faltantes and not entrenar_faltantes:
        raise FileNotFoundError(f'Faltan modelos: {faltantes}. Autorizar con ENTRENAR_FALTANTES=True.')

    estados, predicciones, metricas = [], [], []
    for numero, fila in enumerate(cobertura.itertuples(), 1):
        if not fila.evaluable:
            print(f'{numero:02d}/{len(cobertura)} {fila.estacion}: NO EVALUADA ({fila.motivo})', flush=True)
            continue
        estacion = fila.estacion
        directorio = salida/estacion
        checkpoint = directorio/'estado.json'
        if checkpoint.exists():
            estado = json.loads(checkpoint.read_text())
            assert estado['firma'] == firma
            for archivo, valor in estado['sha256'].items():
                assert hashlib.sha256((directorio/archivo).read_bytes()).hexdigest() == valor
            print(f'{numero:02d}/{len(cobertura)} {estacion}: checkpoint verificado, NO reentrena.', flush=True)
        else:
            directorio.mkdir(exist_ok=True)
            inicio = time.monotonic()
            perfil = perfil_v4_sin_test(matriz[estacion], corte)
            Xtr,ytr,ttr,Btr,mu,sg = construir_ventanas(train,estacion,ventana=24,
                perfil=perfil.iloc[:corte],predecir_desviacion=True)
            Xte,yte,tte,Bte,_,_ = construir_ventanas(test,estacion,ventana=24,mu=mu,sigma=sg,
                perfil=perfil.iloc[corte:],predecir_desviacion=True)
            assert np.isfinite(Xtr).all() and np.isfinite(ytr).all()
            assert np.isfinite(Xte).all() and np.isfinite(yte).all()
            keras.backend.clear_session()
            fijar_semilla(42)
            print(f'{numero:02d}/{len(cobertura)} {estacion}: entrenando {len(Xtr)} ventanas, 66 features...', flush=True)
            modelo = construir_modelo(ventana=24,n_features=Xtr.shape[2])
            historia = entrenar(modelo,Xtr,ytr,val_frac=.2,epocas=60,batch=64,verbose=0)
            ptr = Btr+modelo.predict(Xtr,verbose=0).flatten()
            pte = Bte+modelo.predict(Xte,verbose=0).flatten()
            umbral = float(np.percentile(np.abs(Btr+ytr-ptr),95))
            real = test[estacion].reindex(pd.to_datetime(tte)).to_numpy()
            error = np.abs(Bte+yte-pte)
            clean = error > umbral
            rows = []
            for bit in range(1,8):
                atk, etiq = atacar_serie(test[estacion].to_numpy(),bit,tasa=.05,seed=42)
                idx = test.index.get_indexer(pd.to_datetime(tte))
                # Misma aritmetica float32 que las ventanas del protocolo piloto.
                recibido = Bte + (atk[idx]-perfil.iloc[corte:].to_numpy()[idx]).astype(np.float32)
                m = metricas_binarias(etiq[idx],np.abs(recibido-pte)>umbral)
                rows.append(dict(estacion=estacion,bit=bit,umbral_ppb=umbral,
                    n_test=len(idx),n_ataques=int(etiq[idx].sum()),**m))
            pd.DataFrame(rows).to_csv(directorio/'metricas_pareadas.csv',index=False)
            pd.DataFrame(dict(timestamp=tte,estacion=estacion,original_ppb=real,
                predicho_ppb=pte,base_ppb=Bte,perfil_ppb=perfil.iloc[corte:].reindex(pd.to_datetime(tte)).to_numpy(),
                umbral_ppb=umbral,alerta_limpia=clean)).to_csv(directorio/'predicciones.csv',index=False)
            np.savez_compressed(directorio/'preprocesamiento.npz',mu=mu.to_numpy(),sigma=sg.to_numpy(),
                vecinas=mu.index.to_numpy(dtype=str),perfil=perfil.to_numpy(),timestamps=matriz.index.to_numpy())
            pd.DataFrame(historia.history).to_csv(directorio/'entrenamiento.csv',index=False)
            modelo.save(directorio/'modelo.keras')
            (directorio/'umbral_p95.txt').write_text(f'{umbral:.17g}\n')
            estado = dict(estacion=estacion,firma=firma,umbral_ppb=umbral,n_train=len(Xtr),n_test=len(Xte),
                n_features=Xtr.shape[2],epocas=len(historia.history['loss']),
                mae_ppb=float(error.mean()),sesgo_ppb=float((Bte+yte-pte).mean()),
                fp_limpio=int(clean.sum()),fpr_limpio_pct=float(100*clean.mean()),
                segundos=time.monotonic()-inicio)
            estado['sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in directorio.iterdir() if p.is_file() and p.name != 'estado.json'}
            checkpoint.write_text(json.dumps(estado,indent=2)+'\n')
            print(f'{estacion}: p95={umbral:.2f} | MAE={error.mean():.2f} | '
                  f'FP limpio={100*clean.mean():.2f}% | {estado["epocas"]} epocas | '
                  f'{estado["segundos"]:.1f} s. Guardado.', flush=True)
            del modelo,Xtr,Xte,ytr,yte,ptr,pte
            keras.backend.clear_session()
            gc.collect()
        estados.append({k:v for k,v in estado.items() if k not in ['sha256','firma']})
        predicciones.append(pd.read_csv(directorio/'predicciones.csv',parse_dates=['timestamp']))
        metricas.append(pd.read_csv(directorio/'metricas_pareadas.csv'))
        pd.DataFrame(estados).to_csv(salida/'resumen_modelos.csv',index=False)

    predicciones = pd.concat(predicciones,ignore_index=True)
    pd.concat(metricas,ignore_index=True).to_csv(salida/'metricas_pareadas.csv',index=False)
    base = contexto_diario(test.iloc[24:])
    base = base.merge(predicciones.drop(columns='original_ppb'),on=['timestamp','estacion'],how='left',validate='one_to_one')
    base['evaluable'] = base.predicho_ppb.notna()
    base.to_csv(salida/'cobertura_mensajes.csv.gz',index=False)
    eventos, agregables, exhaustivas = [], [], []
    for bit in range(1,8):
        print(f'Contrafactuales aislados: bit {bit}, {len(base)} mensajes observados.',flush=True)
        e = base.copy()
        assert np.allclose(e.original_ppb, np.round(e.original_ppb))
        recibidos,_ = atacar_serie(e.original_ppb.to_numpy(),bit,tasa=1.,seed=42)
        # Cadena CayenneLPP/AES/flip/descifrado real, comprobada contra XOR entero.
        np.testing.assert_array_equal(recibidos,e.original_ppb.to_numpy(dtype=int)^(1<<bit))
        e['bit'],e['recibido_ppb'] = bit,recibidos
        recibido_modelo = e.base_ppb.to_numpy(dtype=np.float32)+(recibidos-e.perfil_ppb.to_numpy()).astype(np.float32)
        e['detectado'] = e.evaluable & (np.abs(recibido_modelo-e.predicho_ppb.to_numpy())>e.umbral_ppb.to_numpy())
        e = pd.concat([e,efectos_red(e,recibidos)],axis=1)
        e['cruce_fase1'] = e.falsa_fase1 | e.anulada_fase1
        eventos.append(e)
        for estacion,g in e[e.evaluable].groupby('estacion'):
            exhaustivas.append(dict(estacion=estacion,bit=bit,n_ataques=len(g),
                detectados=int(g.detectado.sum()),recall_pct=100*g.detectado.mean()))
        for tipo in ['falsa_fase1','anulada_fase1','cruce_fase1','cambio_banda_red']:
            dano = e[tipo]
            agregables.append(pd.DataFrame(dict(fecha=e.fecha,bit=bit,tipo_dano=tipo,
                dano_observado=dano,dano_evaluable=dano&e.evaluable,
                dano_detectado=dano&e.evaluable&e.detectado,
                dano_no_detectado=dano&e.evaluable&~e.detectado,
                dano_sin_evaluacion=dano&~e.evaluable)))
    pd.concat(eventos,ignore_index=True).to_csv(salida/'eventos_aislados.csv.gz',index=False)
    pd.DataFrame(exhaustivas).to_csv(salida/'recall_exhaustivo.csv',index=False)
    resumen,diario = resumir_dias(pd.concat(agregables,ignore_index=True),sorted(base.fecha.unique()))
    resumen.to_csv(salida/'resumen_red_por_bit.csv',index=False)
    diario.to_csv(salida/'dias_por_bit.csv',index=False)
    cobertura_dias = base.groupby('fecha').agg(mensajes_observados=('estacion','size'),
        mensajes_evaluables=('evaluable','sum'),posibles=('mensajes_posibles_dia','first'),
        maximo_ppb=('maximo_original_ppb','first'))
    cobertura_dias['cobertura_modelos_pct'] = 100*cobertura_dias.mensajes_evaluables/cobertura_dias.mensajes_observados
    cobertura_dias.to_csv(salida/'cobertura_dias.csv')
    figuras_red(raiz,resumen)
    print(resumen.to_string(index=False),flush=True)
    return resumen


def figuras_red(raiz,resumen):
    """Curvas empíricas: no multiplicar oportunidad por un recall promedio."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    salida = Path(raiz)/'docs/img/multiestacion_v4_p95_2025'
    salida.mkdir(parents=True,exist_ok=True)
    for tipo in ['cruce_fase1','cambio_banda_red']:
        t = resumen[resumen.tipo_dano==tipo].sort_values('bit')
        for columna,nombre in [('pct_dias_dano_no_detectado','dano_no_detectado'),
                               ('pct_dias_vulnerables_evaluables','oportunidad_real')]:
            fig,ax = plt.subplots(figsize=(11,6.5))
            ax.plot(t.bit,t[columna],'o-',color='crimson',label=(
                '% de días con ≥1 ataque dañino NO detectado' if nombre=='dano_no_detectado'
                else '% de días con ≥1 ataque dañino evaluable'))
            ax.plot(t.bit,t.deteccion_dano_pct,'s--',color='seagreen',
                label='% de ataques dañinos evaluables detectados (p95 por estación)')
            ax.set(ylim=(0,105),xlabel='Bit atacado',ylabel='Porcentaje (%)')
            ax.set_xticks(range(1,8),[f'{b}\n({2**b} ppb)' for b in range(1,8)])
            ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=1))
            caso = 'Cruce del máximo diario observado — umbral 155 ppb' if tipo=='cruce_fase1' else 'Cambio de banda del máximo diario observado'
            ax.set_title(f'{nombre.replace("_"," ").capitalize()} por bit\n{caso}')
            ax.legend(loc='upper left',fontsize=9)
            ax.grid(alpha=.25)
            ax.text(.01,.02,f'{int(t.n_dias.iloc[0])} días de test · un mensaje atacado por escenario\n'
                    'Rojo: días / días del periodo. Verde: ataques dañinos detectados / evaluables.\n'
                    'Sin oportunidades: detección indefinida. Cobertura incompleta: consultar CSV.',
                    transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
            fig.tight_layout()
            fig.savefig(salida/f'{nombre}_{tipo}.png',dpi=180)
            plt.close(fig)
