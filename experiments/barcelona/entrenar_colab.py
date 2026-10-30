"""Entrenamiento CPU Barcelona 2014–2016, selección y definitivo duplicados.

No incluye calibración ni prueba. Datos preparados por empaquetar_colab.py.
"""
import os
for k, v in {'CUDA_VISIBLE_DEVICES':'-1', 'TF_DETERMINISTIC_OPS':'1',
             'TF_ENABLE_ONEDNN_OPTS':'0', 'TF_NUM_INTRAOP_THREADS':'1',
             'TF_NUM_INTEROP_THREADS':'1', 'OMP_NUM_THREADS':'1'}.items():
    os.environ[k] = v
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

from src.detect.lstm import fijar_semilla, construir_modelo
from src.detect.lstm_red import construir_clasificador
from src.detect.lstm_local import muestra
from experiments.barcelona.preparar_ventanas import ventana_l0, ventana_v4, bloque_paraad

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'salidas'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def guardar(p, datos):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(p)


def limpio(fase):
    d = ROOT / 'entrada'
    return (pd.read_parquet(d / 'valores.parquet'), pd.read_parquet(d / 'perfiles.parquet'),
            pd.read_parquet(d / 'reloj.parquet'), np.load(d / f'z_{fase}.npy'),
            json.loads((d / 'vecinas.json').read_text()))


def l0_datos(uso):
    d = ROOT / 'entrada'
    codigos = json.loads((d / 'codigos.json').read_text())
    vec = json.loads((d / 'vecinas.json').read_text())
    valida = pd.read_parquet(d / 'horas_l0.parquet')
    X, Y = [], []
    carpetas = sorted((d / 'ataques').glob(uso + '_[0-9][0-9]'))
    esperado = 10 if uso == 'validacion' else 20
    assert len(carpetas) == esperado
    for c in carpetas:
        num = int(c.name[-2:])
        v = pd.read_parquet(c / 'valores_alterados.parquet')
        y = pd.read_parquet(c / 'etiquetas_hora.parquet')
        F = np.load(c / 'l0_features.npy', mmap_mode='r')
        anos = v.index.year
        etapa = (anos == 2016) if uso == 'validacion' else (
            (anos >= 2014) & (anos <= (2015 if uso == 'ajuste_inicial' else 2016)))
        mask = valida.reindex(v.index)
        for j, s in enumerate(codigos):
            pos = np.flatnonzero(mask[s].to_numpy() & etapa)
            nombre = {'ajuste_inicial':'seleccion', 'validacion':'validacion', 'ajuste_definitivo':'definitivo'}[uso]
            pos = muestra(pos, 8, nombre, num, j)
            X.append(ventana_l0(F, codigos, vec, s, pos))
            Y.append(y[s].to_numpy(np.float32)[pos])
    return np.concatenate(X), np.concatenate(Y)


def v4_datos(s, fase, anos):
    v, base, reloj, z, _ = limpio(fase)
    ok = pd.read_parquet(ROOT / 'entrada/horas_v4.parquet')[s].to_numpy()
    pos = np.flatnonzero(ok & np.isin(v.index.year, anos))
    X = ventana_v4(z, v.notna().to_numpy(np.float32),
                   reloj[['hora_sin','hora_cos']].to_numpy(np.float32), list(v).index(s), pos)
    y = (v[s] - base[s]).to_numpy(np.float32)[pos]
    return X, y


def paraad_datos(fase, anos):
    v, _, _, z, _ = limpio(fase)
    dias = pd.read_parquet(ROOT / 'entrada/estacion_dias.parquet')
    filas = dias[dias.bloque_seguro & dias.dia_utc.dt.year.isin(anos)]
    pos = filas.inicio_pos.drop_duplicates().to_numpy()
    X, mask = bloque_paraad(z, v.notna().to_numpy(np.float32), pos)
    ok = mask.any(axis=(1, 2))
    return X[ok], mask[ok]


def nuevo(detector, dropout):
    tf.keras.backend.clear_session()
    fijar_semilla(42)
    if detector == 'paraad':
        from src.detect.paraad import construir_modelo as cp
        return cp(dropout=dropout, sensores=13)
    if detector == 'l0':
        return construir_clasificador(n_features=17)
    return construir_modelo(24, 26)


class Progreso(tf.keras.callbacks.Callback):
    def __init__(self, ruta):
        super().__init__(); self.ruta = ruta
    def on_epoch_end(self, epoch, logs=None):
        datos = {'epoca':epoch+1, **{k:float(v) for k,v in (logs or {}).items()}}
        guardar(self.ruta, datos)
        print(datos, flush=True)


def repeticion(carpeta, detector, dropout, tr, va, epocas, seleccion):
    from src.detect import paraad as p
    carpeta.mkdir(parents=True, exist_ok=True)
    if (carpeta / 'completo.json').exists():
        meta = json.loads((carpeta / 'completo.json').read_text())
        for n,h in meta['sha256'].items(): assert sha(carpeta/n) == h
        return
    modelo = nuevo(detector, dropout)
    fijar_semilla(42)
    if detector == 'paraad':
        X, mask = tr; y = p.objetivos_perdida(X, mask)
        hist = []
        for e in range(1, epocas+1):
            modelo.reset_metrics()
            for i in range(0, len(X), 256):
                loss = float(modelo.train_on_batch(X[i:i+256], y[i:i+256]))
            fila = dict(epoca=e, loss=loss)
            if seleccion:
                xv,mv = va
                pred = p.reconstruir(modelo, xv)
                fila['val_loss'] = float((((xv.astype('float64')-pred)**2*mv).sum(axis=(1,2)) / mv.sum(axis=(1,2))).mean())
            hist.append(fila)
            guardar(carpeta/'progreso.json', fila)
            if e==1 or e%25==0: print(carpeta.name, fila, flush=True)
        historia = pd.DataFrame(hist)
        entrada = va[0] if seleccion else tr[0]
    else:
        callbacks = [Progreso(carpeta/'progreso.json')]
        if seleccion:
            callbacks.append(tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=8,
                                                               min_delta=0, restore_best_weights=True))
        h = modelo.fit(tr[0], tr[1], validation_data=va if seleccion else None,
                       epochs=epocas, batch_size=64, shuffle=True, callbacks=callbacks, verbose=0)
        historia = pd.DataFrame(h.history)
        historia.insert(0, 'epoca', np.arange(1,len(historia)+1))
        entrada = va[0] if seleccion else tr[0]
    if not np.isfinite(historia.to_numpy()).all(): raise ValueError('Pérdida no finita')
    modelo.save(carpeta/'modelo.keras')
    # Predicción de control fija; además se comparan TODOS los pesos/optimizer.
    entrada = entrada[:256]
    pred = modelo(entrada, training=False).numpy()
    cargado = tf.keras.models.load_model(carpeta/'modelo.keras')
    np.testing.assert_array_equal(pred, cargado(entrada, training=False).numpy())
    np.save(carpeta/'prediccion_control.npy', pred, allow_pickle=False)
    historia.to_csv(carpeta/'historia.csv', index=False, float_format='%.17g')
    pesos = {f'p{i}':x for i,x in enumerate(modelo.get_weights())}
    pesos.update({f'o{i}':x.numpy() for i,x in enumerate(modelo.optimizer.variables)})
    np.savez(carpeta/'pesos_control.npz', **pesos)
    guardar(carpeta/'completo.json', dict(sha256={n:sha(carpeta/n) for n in
            ['modelo.keras','historia.csv','prediccion_control.npy','pesos_control.npz']}))


def par(out, detector, dropout, tr, va, epocas, seleccion):
    for r in (1,2): repeticion(out/f'r{r}', detector, dropout, tr, va, epocas, seleccion)
    pd.testing.assert_frame_equal(pd.read_csv(out/'r1/historia.csv', float_precision='round_trip'),
                                  pd.read_csv(out/'r2/historia.csv', float_precision='round_trip'), check_exact=True)
    np.testing.assert_array_equal(np.load(out/'r1/prediccion_control.npy'), np.load(out/'r2/prediccion_control.npy'))
    a,b=np.load(out/'r1/pesos_control.npz'),np.load(out/'r2/pesos_control.npz')
    assert a.files==b.files
    for n in a.files: np.testing.assert_array_equal(a[n],b[n])
    guardar(out/'verificado.json',dict(igual=True, historias=True, pesos=True, optimizador=True,
                                      prediccion_control=True, origen='dos modelos recién entrenados'))
    h=pd.read_csv(out/'r1/historia.csv', float_precision='round_trip')
    return dict(epocas=int(h.loc[h.val_loss.idxmin(),'epoca']), val_loss=float(h.val_loss.min())) if seleccion else None


def ejecutar(detector, smoke=False):
    if tf.config.get_visible_devices('GPU'): raise RuntimeError('Sólo CPU')
    paquete=json.loads((ROOT/'entrada/registro_paquete.json').read_text())
    for nombre,h in paquete['archivos'].items(): assert sha(ROOT/nombre)==h, nombre
    out=OUT/detector
    firma=dict(sha256_entrada=sha(ROOT/'entrada/registro_paquete.json'),
               sha256_script=sha(Path(__file__)), tensorflow=tf.__version__, keras=tf.keras.__version__,
               numpy=np.__version__, python=platform.python_version(), cpu=platform.machine(), semilla=42,
               threads=1, smoke=smoke, origen='modelos nuevos Barcelona')
    if (out/'entrada.json').exists(): assert json.loads((out/'entrada.json').read_text())==firma
    else: guardar(out/'entrada.json', firma)
    if detector=='paraad':
        tr=paraad_datos('seleccion',[2014,2015]); va=paraad_datos('seleccion',[2016])
        candidatos=[]
        for d in ([.1] if smoke else [.1,.3,.5]):
            c=par(out/f'seleccion/dropout{d}',detector,d,tr,va,1 if smoke else 500,True)
            candidatos.append(dict(dropout=d,**c))
        elegido=min(candidatos,key=lambda c:(c['val_loss'],c['dropout'],c['epocas']))
        guardar(out/'seleccion.json',dict(candidatos=candidatos,elegido=elegido))
        tr=paraad_datos('definitivo',[2014,2015,2016])
        par(out/'definitivo',detector,elegido['dropout'],tr,None,elegido['epocas'],False)
    elif detector=='v4':
        codigos=json.loads((ROOT/'entrada/codigos.json').read_text())
        for s in codigos[:1] if smoke else codigos:
            tr=v4_datos(s,'seleccion',[2014,2015]); va=v4_datos(s,'seleccion',[2016])
            if smoke: tr=tuple(x[:8] for x in tr); va=tuple(x[:8] for x in va)
            c=par(out/s/'seleccion',detector,.2,tr,va,1 if smoke else 60,True)
            guardar(out/s/'seleccion.json',c)
            del tr,va
            tr=v4_datos(s,'definitivo',[2014,2015,2016])
            if smoke: tr=tuple(x[:8] for x in tr)
            par(out/s/'definitivo',detector,.2,tr,None,c['epocas'],False)
    else:
        tr=l0_datos('ajuste_inicial'); va=l0_datos('validacion')
        if smoke: tr=tuple(x[:8] for x in tr); va=tuple(x[:8] for x in va)
        guardar(out/'conteos.json',dict(ajuste=len(tr[1]),validacion=len(va[1]),
                                       positivos_ajuste=int(tr[1].sum()),positivos_validacion=int(va[1].sum())))
        c=par(out/'seleccion',detector,.2,tr,va,1 if smoke else 60,True)
        guardar(out/'seleccion.json',c)
        del tr,va
        tr=l0_datos('ajuste_definitivo')
        if smoke: tr=tuple(x[:8] for x in tr)
        par(out/'definitivo',detector,.2,tr,None,c['epocas'],False)
    guardar(out/'congelado.json',dict(detector=detector,igual=True,smoke=smoke,entrada=firma,
                                     verificados={str(p.relative_to(out)):sha(p) for p in out.rglob('verificado.json')}))


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--detector',choices=['l0','v4','paraad'],required=True)
    ap.add_argument('--smoke',action='store_true'); args=ap.parse_args()
    if args.smoke: OUT=ROOT/'smoke_salidas'
    try: ejecutar(args.detector,args.smoke)
    except Exception as e:
        guardar(OUT/args.detector/'error.json',dict(tipo=type(e).__name__,error=str(e)))
        raise
