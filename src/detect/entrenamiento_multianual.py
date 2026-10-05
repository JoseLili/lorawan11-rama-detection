"""Entrenamiento, calibración y evaluación limpia del protocolo V4 multianual.

Implementa el §5–§7.1 de docs/protocolo_lstm_v4_multianual.md sobre la base
temporal de `src.detect.multianual`. No modifica `src.detect.lstm.entrenar`
ni ningún artefacto de 2025.

Flujo por objetivo:
    1. Selección: entrenar con 2020–2021, validar en 2022, elegir E.
    2. Definitivo: modelo nuevo, 2020–2022, exactamente E épocas.
    3. Calibración: p95 de |original − predicho| en 2023.
    4. Predicción limpia en 2024, 2025 y 2026 (sin reentrenar ni recalibrar).
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from src.detect import multianual as m

CONFIG = dict(
    semilla=42, unidades=64, batch=64, max_epocas=60, paciencia=8,
    shuffle=True, percentil=95,
)
ANIOS_PRUEBA = {'prueba_2024': 2024, 'prueba_2025': 2025, 'prueba_2026_parcial': 2026}


# ---------------------------------------------------------------- tensores

def caracteristicas(entradas: pd.DataFrame, objetivo: str, mu, sigma) -> np.ndarray:
    """Matriz (horas × 66): 32 valores normalizados, 32 máscaras, sin, cos.

    Mismo orden y operaciones que `construir_ventanas` del V4 de 2025.
    """
    vecinas = [c for c in entradas.columns if c != objetivo]
    v = entradas[vecinas]
    mascara = v.notna().astype(np.float32).to_numpy()
    valores = ((v - mu[vecinas]) / sigma[vecinas]).fillna(0.0).astype(np.float32).to_numpy()
    h = entradas.index.hour.to_numpy()
    hora = np.column_stack([np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)]).astype(np.float32)
    return np.concatenate([valores, mascara, hora], axis=1)


def tensores(entradas, valores, objetivo, mu, sigma, perfil, etapas, ventana=m.VENTANA, incluir_t=False):
    """Ejemplos cuyo OBJETIVO cae en `etapas`.

    Devuelve dict con X (n, 24, 66), y = original − base, base, original, ts.
    El contexto puede venir de la etapa anterior (pasado disponible).

    `incluir_t=False` (V4): filas t−24 … t−1 de las vecinas.
    `incluir_t=True` (variante contemporánea): filas t−23 … t; la última fila trae a las
    vecinas a la MISMA hora del objetivo. El objetivo nunca está entre las entradas.
    """
    ok = m.ejemplos_validos(valores, objetivo, perfil, ventana).to_numpy()
    idx = np.flatnonzero(ok & m.mascara_etapas(valores.index, etapas))
    F = caracteristicas(entradas, objetivo, mu, sigma)
    X = F[idx[:, None] + (np.arange(-ventana, 0) + int(incluir_t))[None, :]]
    original = valores[objetivo].to_numpy()[idx]
    base = perfil['base'].to_numpy()[idx]
    return dict(X=X, y=(original - base).astype(np.float32), base=base,
                original=original, ts=valores.index[idx],
                origen_base=perfil['origen_base'].to_numpy()[idx])


# ---------------------------------------------------------------- entrenamiento

def _keras():
    import tensorflow as tf
    from tensorflow import keras
    return tf, keras


def nuevo_modelo(n_features=66, unidades=CONFIG['unidades'], semilla=CONFIG['semilla']):
    """Limpia la sesión, fija la semilla y construye el modelo (CLAUDE.md)."""
    _, keras = _keras()
    from src.detect.lstm import construir_modelo, fijar_semilla
    keras.backend.clear_session()
    fijar_semilla(semilla)
    return construir_modelo(m.VENTANA, n_features, unidades=unidades)


def entrenar_seleccion(modelo, tr, val, max_epocas=CONFIG['max_epocas'],
                       paciencia=CONFIG['paciencia'], batch=CONFIG['batch'], verbose=0):
    """Fase 1: validación EXTERNA (2022) y EarlyStopping. Devuelve historia como DataFrame."""
    _, keras = _keras()
    parada = keras.callbacks.EarlyStopping(monitor='val_loss', patience=paciencia,
                                           min_delta=0, restore_best_weights=True)
    h = modelo.fit(tr['X'], tr['y'], validation_data=(val['X'], val['y']),
                   epochs=max_epocas, batch_size=batch, shuffle=CONFIG['shuffle'],
                   callbacks=[parada], verbose=verbose)
    hist = pd.DataFrame(h.history)
    hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
    return hist


def seleccionar_epoca(historia: pd.DataFrame) -> int:
    """E = primera época (desde 1) con el menor val_loss."""
    return int(historia['val_loss'].to_numpy().argmin()) + 1


def entrenar_definitivo(modelo, tr, epocas, batch=CONFIG['batch'], verbose=0):
    """Fase 2: exactamente `epocas`, sin validación ni EarlyStopping."""
    h = modelo.fit(tr['X'], tr['y'], epochs=epocas, batch_size=batch,
                   shuffle=CONFIG['shuffle'], verbose=verbose)
    hist = pd.DataFrame(h.history)
    hist.index = pd.RangeIndex(1, len(hist) + 1, name='epoca')
    return hist


def predecir(modelo, t) -> pd.DataFrame:
    """Predicción absoluta = base + corrección. Residuo = original − predicho."""
    corr = modelo.predict(t['X'], batch_size=1024, verbose=0).ravel().astype(np.float64)
    pred = t['base'] + corr
    return pd.DataFrame({'timestamp': t['ts'], 'original_ppb': t['original'],
                         'base_ppb': t['base'], 'origen_base': t['origen_base'],
                         'correccion_ppb': corr, 'predicho_ppb': pred,
                         'residuo_ppb': t['original'] - pred})


def umbral_p95(calibracion: pd.DataFrame) -> float:
    return float(np.percentile(np.abs(calibracion['residuo_ppb'].to_numpy()),
                               CONFIG['percentil'], method='linear'))


# ---------------------------------------------------------------- orquestación

def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contexto(raiz):
    """Matriz fija, canales inactivos y normalizaciones de ambas fases."""
    raiz = Path(raiz)
    long, fuentes = m.cargar_o3_zips(raiz / 'data/raw', m.leer_checksums(raiz / 'docs/checksums_2020_2026.txt'))
    valores, origen = m.matriz_fija(long)
    ina_i = m.canales_inactivos(valores, ('ajuste_inicial',))
    ina_d = m.canales_inactivos(valores, m.AJUSTE_DEFINITIVO)
    mu_i, sg_i = m.normalizacion(valores, ('ajuste_inicial',), ina_i)
    mu_d, sg_d = m.normalizacion(valores, m.AJUSTE_DEFINITIVO, ina_d)
    return dict(valores=valores, origen=origen, fuentes=fuentes,
                inicial=dict(inactivos=ina_i, mu=mu_i, sigma=sg_i,
                             entradas=m.entradas_modelo(valores, ina_i)),
                definitiva=dict(inactivos=ina_d, mu=mu_d, sigma=sg_d,
                                entradas=m.entradas_modelo(valores, ina_d)))


def entrenar_objetivo(ctx, objetivo, carpeta, sustituir=False, max_epocas=CONFIG['max_epocas'],
                      unidades=CONFIG['unidades'], verbose=0, incluir_t=False, protocolo=m.PROTOCOLO):
    """Fases 1–4 para un objetivo; guarda todo en `carpeta`. Devuelve resumen."""
    import tensorflow as tf
    from tensorflow import keras

    carpeta = Path(carpeta)
    if (carpeta / 'modelo.keras').exists() and not sustituir:
        raise FileExistsError(f'{carpeta}/modelo.keras ya existe; no se sobrescribe sin sustituir=True')
    (carpeta / 'seleccion').mkdir(parents=True, exist_ok=True)

    valores = ctx['valores']
    perfil = m.perfil_causal(valores[objetivo])
    ini, dfn = ctx['inicial'], ctx['definitiva']

    # Fase 1 — selección de épocas
    tr1 = tensores(ini['entradas'], valores, objetivo, ini['mu'], ini['sigma'], perfil, ('ajuste_inicial',),
                   incluir_t=incluir_t)
    va1 = tensores(ini['entradas'], valores, objetivo, ini['mu'], ini['sigma'], perfil, ('validacion',),
                   incluir_t=incluir_t)
    modelo1 = nuevo_modelo(unidades=unidades)
    hist1 = entrenar_seleccion(modelo1, tr1, va1, max_epocas=max_epocas, verbose=verbose)
    E = seleccionar_epoca(hist1)
    hist1.to_csv(carpeta / 'seleccion/historia_seleccion.csv')
    modelo1.save(carpeta / 'seleccion/modelo_seleccion.keras')

    # Fase 2 — ajuste definitivo desde cero
    tr2 = tensores(dfn['entradas'], valores, objetivo, dfn['mu'], dfn['sigma'], perfil, m.AJUSTE_DEFINITIVO,
                   incluir_t=incluir_t)
    modelo2 = nuevo_modelo(unidades=unidades)
    hist2 = entrenar_definitivo(modelo2, tr2, E, verbose=verbose)
    hist2.to_csv(carpeta / 'historia_definitiva.csv')
    modelo2.save(carpeta / 'modelo.keras')
    vecinas = [c for c in valores.columns if c != objetivo]
    np.savez_compressed(carpeta / 'preprocesamiento.npz',
                        vecinas=np.array(vecinas), mu=dfn['mu'][vecinas].to_numpy(),
                        sigma=dfn['sigma'][vecinas].to_numpy(),
                        inactivos=np.array(dfn['inactivos'], dtype=str))

    # Fases 3–4 — se recarga el modelo guardado: calibrar y predecir NO entrenan
    cargado = keras.models.load_model(carpeta / 'modelo.keras', compile=False)
    resultados = {}
    for etapa in ('calibracion', *ANIOS_PRUEBA):
        t = tensores(dfn['entradas'], valores, objetivo, dfn['mu'], dfn['sigma'], perfil, (etapa,),
                     incluir_t=incluir_t)
        resultados[etapa] = predecir(cargado, t) if len(t['y']) else None
    cal = resultados['calibracion']
    p95 = umbral_p95(cal) if cal is not None and len(cal) else float('nan')
    (carpeta / 'umbral_p95_cal2023.txt').write_text(f'{p95:.17g}\n')
    if cal is not None:
        cal.to_csv(carpeta / 'calibracion_2023.csv.gz', index=False)
    for etapa, anio in ANIOS_PRUEBA.items():
        r = resultados[etapa]
        if r is not None:
            r = r.assign(alerta_limpia=np.abs(r['residuo_ppb']) > p95)
            r.to_csv(carpeta / f'predicciones_{anio}.csv.gz', index=False)

    config = dict(
        protocolo=protocolo, tipo='lstm', incluir_t=incluir_t, objetivo=objetivo, **CONFIG,
        unidades_usadas=unidades,
        max_epocas_usadas=max_epocas, epoca_E=E, epocas_seleccion_ejecutadas=len(hist1),
        val_loss_minimo=float(hist1['val_loss'].min()),
        n_ajuste_inicial=len(tr1['y']), n_validacion=len(va1['y']), n_ajuste_definitivo=len(tr2['y']),
        n_calibracion=0 if cal is None else len(cal), umbral_p95_ppb=p95,
        canales_inactivos=dfn['inactivos'],
        versiones=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                       tensorflow=tf.__version__, keras=keras.__version__),
        sha256=dict(modelo=_sha(carpeta / 'modelo.keras'),
                    preprocesamiento=_sha(carpeta / 'preprocesamiento.npz')),
    )
    (carpeta / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n')
    return config


# ---------------------------------------------------------------- lectura y métricas

def cargar_objetivo(carpeta):
    """Lee lo guardado de un objetivo sin entrenar nada."""
    carpeta = Path(carpeta)
    if not (carpeta / 'configuracion.json').exists():
        return None
    out = dict(config=json.loads((carpeta / 'configuracion.json').read_text()),
               seleccion=pd.read_csv(carpeta / 'seleccion/historia_seleccion.csv', index_col=0),
               definitiva=pd.read_csv(carpeta / 'historia_definitiva.csv', index_col=0),
               umbral=float((carpeta / 'umbral_p95_cal2023.txt').read_text()))
    cal = carpeta / 'calibracion_2023.csv.gz'
    out['calibracion'] = pd.read_csv(cal, parse_dates=['timestamp']) if cal.exists() else None
    out['prueba'] = {a: pd.read_csv(carpeta / f'predicciones_{a}.csv.gz', parse_dates=['timestamp'])
                     for a in ANIOS_PRUEBA.values() if (carpeta / f'predicciones_{a}.csv.gz').exists()}
    return out


def metricas_limpias(pred: pd.DataFrame, umbral: float) -> dict:
    """§7.1: n, MAE, sesgo, sigma (ddof=0), falsas alarmas, y lo mismo con sólo el perfil."""
    r = pred['residuo_ppb'].to_numpy()
    rp = (pred['original_ppb'] - pred['base_ppb']).to_numpy()
    fa = int((np.abs(r) > umbral).sum())
    return dict(n=len(r), mae=float(np.abs(r).mean()), sesgo=float(r.mean()), sigma=float(r.std(ddof=0)),
                falsas_alarmas=fa, fpr=fa / len(r) if len(r) else float('nan'),
                mae_solo_perfil=float(np.abs(rp).mean()), sesgo_solo_perfil=float(rp.mean()))


def comparar_corridas(a, b) -> pd.DataFrame:
    """Reproducibilidad (§5): compara E, pesos, umbral y predicciones de dos carpetas."""
    from tensorflow import keras
    a, b = Path(a), Path(b)
    ca, cb = (json.loads((x / 'configuracion.json').read_text()) for x in (a, b))
    wa = keras.models.load_model(a / 'modelo.keras', compile=False).get_weights()
    wb = keras.models.load_model(b / 'modelo.keras', compile=False).get_weights()
    filas = [('epoca_E', ca['epoca_E'] == cb['epoca_E'], f"{ca['epoca_E']} vs {cb['epoca_E']}"),
             ('pesos idénticos', all(np.array_equal(x, y) for x, y in zip(wa, wb)), f'{len(wa)} arrays'),
             ('umbral p95 idéntico', ca['umbral_p95_ppb'] == cb['umbral_p95_ppb'],
              f"{ca['umbral_p95_ppb']!r} vs {cb['umbral_p95_ppb']!r}")]
    for nombre in ['calibracion_2023.csv.gz'] + [f'predicciones_{x}.csv.gz' for x in ANIOS_PRUEBA.values()]:
        if (a / nombre).exists() and (b / nombre).exists():
            pa, pb = pd.read_csv(a / nombre), pd.read_csv(b / nombre)
            filas.append((nombre, pa.equals(pb), f'{len(pa)} filas'))
    return pd.DataFrame(filas, columns=['comprobacion', 'identico', 'detalle'])


# ---------------------------------------------------------------- registro de progreso

COLUMNAS_BITACORA = [
    'fecha_hora', 'accion', 'objetivo', 'resultado', 'detalle', 'carpeta',
    'ENTRENAR', 'SUSTITUIR', 'VERIFICAR_REPRODUCIBILIDAD', 'EVALUAR_PRUEBA', 'OBJETIVOS',
    'clasificacion', 'epoca_E', 'epocas_seleccion_ejecutadas', 'val_loss_minimo',
    'n_ajuste_inicial', 'n_validacion', 'n_ajuste_definitivo', 'n_calibracion',
    'umbral_p95_ppb', 'segundos', 'semilla', 'unidades', 'batch', 'max_epocas', 'paciencia',
    'shuffle', 'canales_inactivos', 'tensorflow', 'keras', 'sha256_modelo', 'origen_registro',
]


def registrar(bitacora, accion, objetivo='', resultado='', detalle='', flags=None, config=None,
              carpeta='', segundos=None, fecha_hora=None, origen='notebook 12'):
    """Agrega una fila a la bitácora CSV (nunca la reescribe).

    `accion`: entrenar | verificar | evaluar_prueba | ...
    `resultado`: entrenado | saltado_ya_existe | fuera_del_protocolo | error |
                 reproducible | no_reproducible | mostrada ...
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    flags = flags or {}
    config = config or {}
    fila = dict.fromkeys(COLUMNAS_BITACORA, '')
    fila.update(
        fecha_hora=fecha_hora or datetime.now(ZoneInfo('America/Mexico_City')).isoformat(timespec='seconds'),
        accion=accion, objetivo=objetivo, resultado=resultado, detalle=detalle, carpeta=str(carpeta),
        origen_registro=origen,
        segundos='' if segundos is None else round(float(segundos), 1),
        **{k: (' '.join(v) if isinstance(v, (list, tuple)) else v) for k, v in flags.items()
           if k in COLUMNAS_BITACORA})
    for k in ('epoca_E', 'epocas_seleccion_ejecutadas', 'val_loss_minimo', 'n_ajuste_inicial',
              'n_validacion', 'n_ajuste_definitivo', 'n_calibracion', 'umbral_p95_ppb',
              'semilla', 'unidades', 'batch', 'max_epocas', 'paciencia', 'shuffle'):
        if k in config:
            fila[k] = config[k]
    if 'canales_inactivos' in config:
        fila['canales_inactivos'] = ' '.join(config['canales_inactivos'])
    if 'versiones' in config:
        fila['tensorflow'] = config['versiones'].get('tensorflow', '')
        fila['keras'] = config['versiones'].get('keras', '')
    if 'sha256' in config:
        fila['sha256_modelo'] = config['sha256'].get('modelo', '')
    bitacora = Path(bitacora)
    nueva = not bitacora.exists()
    pd.DataFrame([fila], columns=COLUMNAS_BITACORA).to_csv(bitacora, mode='a', header=nueva, index=False)
    return fila


def leer_bitacora(bitacora) -> pd.DataFrame:
    bitacora = Path(bitacora)
    if not bitacora.exists():
        return pd.DataFrame(columns=COLUMNAS_BITACORA)
    return pd.read_csv(bitacora, dtype=str, keep_default_na=False)


def estado_objetivos(estaciones, verificacion, clases: pd.DataFrame) -> pd.DataFrame:
    """Una fila por cada uno de los 33 objetivos con lo que hay en disco hoy."""
    filas = []
    for obj in m.ESTACIONES:
        fila = dict(objetivo=obj, clasificacion=clases.at[obj, 'clasificacion'],
                    motivo=clases.at[obj, 'motivo'] or '', entrenado=False, verificado='no')
        r = cargar_objetivo(Path(estaciones) / obj)
        if r is not None:
            c = r['config']
            fila.update(entrenado=True, epoca_E=c['epoca_E'],
                        epocas_fase1=c['epocas_seleccion_ejecutadas'],
                        E_en_maximo=c['epoca_E'] == c['max_epocas'],
                        val_loss_min=round(c['val_loss_minimo'], 2),
                        loss_final_fase2=round(float(r['definitiva']['loss'].iloc[-1]), 2),
                        n_ajuste_def=c['n_ajuste_definitivo'], n_calibracion=c['n_calibracion'],
                        umbral_p95=round(r['umbral'], 3),
                        anios_prueba=' '.join(str(a) for a in sorted(r['prueba'])))
            if r['calibracion'] is not None and len(r['calibracion']):
                met = metricas_limpias(r['calibracion'], r['umbral'])
                fila.update(mae_cal=round(met['mae'], 2), sesgo_cal=round(met['sesgo'], 2),
                            sigma_cal=round(met['sigma'], 2), mae_perfil_cal=round(met['mae_solo_perfil'], 2),
                            mejora_vs_perfil_pct=round(100 * (1 - met['mae'] / met['mae_solo_perfil']), 1))
            if (Path(verificacion) / obj / 'modelo.keras').exists():
                fila['verificado'] = 'sí' if comparar_corridas(Path(estaciones) / obj,
                                                               Path(verificacion) / obj)['identico'].all() else 'DIFIERE'
        filas.append(fila)
    return pd.DataFrame(filas)
