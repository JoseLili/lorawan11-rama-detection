"""Variante contemporánea (vecinas de la misma hora), línea base lineal y atacante simultáneo.

Protocolo: docs/protocolo_contemporaneo_v1.md (`v4c_multianual_33_p95cal2023_v1`).
Reutiliza la base temporal y la evaluación del V4 multianual sin modificar sus resultados.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect import ataques_multianual as at
from src.detect.red import metricas_binarias

PROTOCOLO = 'v4c_multianual_33_p95cal2023_v1'
ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0, 100000.0]
SEMILLA_SIMULTANEO = 777


# ---------------------------------------------------------------- modelo lineal

class ModeloLineal:
    """Ridge sobre la fila t de la ventana (incluir_t=True). Misma interfaz que Keras para `em.predecir`."""

    def __init__(self, coef, intercepto):
        self.coef = np.asarray(coef, dtype=np.float64)
        self.intercepto = float(intercepto)

    def predict(self, X, batch_size=None, verbose=0):
        return (np.asarray(X)[:, -1, :].astype(np.float64) @ self.coef + self.intercepto)[:, None]


def _ridge(X, y, alpha):
    from sklearn.linear_model import Ridge
    r = Ridge(alpha=alpha).fit(X[:, -1, :].astype(np.float64), y.astype(np.float64))
    return ModeloLineal(r.coef_, r.intercept_)


def _mse(modelo, t):
    return float(np.mean((t['y'] - modelo.predict(t['X']).ravel()) ** 2))


def entrenar_lineal(ctx, objetivo, carpeta, sustituir=False):
    """Selección de α con 2022, reajuste 2020–2022, calibración 2023 y predicción 2024–2026."""
    carpeta = Path(carpeta)
    if (carpeta / 'modelo_lineal.npz').exists() and not sustituir:
        raise FileExistsError(f'{carpeta}/modelo_lineal.npz ya existe; no se sobrescribe sin sustituir=True')
    (carpeta / 'seleccion').mkdir(parents=True, exist_ok=True)
    valores, ini, dfn = ctx['valores'], ctx['inicial'], ctx['definitiva']
    perfil = m.perfil_causal(valores[objetivo])
    kw = dict(incluir_t=True)
    tr1 = em.tensores(ini['entradas'], valores, objetivo, ini['mu'], ini['sigma'], perfil, ('ajuste_inicial',), **kw)
    va1 = em.tensores(ini['entradas'], valores, objetivo, ini['mu'], ini['sigma'], perfil, ('validacion',), **kw)
    filas = []
    for a in ALPHAS:
        mod = _ridge(tr1['X'], tr1['y'], a)
        filas.append(dict(alpha=a, loss=_mse(mod, tr1), val_loss=_mse(mod, va1)))
    hist = pd.DataFrame(filas, index=pd.RangeIndex(1, len(ALPHAS) + 1, name='epoca'))
    alpha = float(hist.loc[hist['val_loss'].idxmin(), 'alpha'])      # primera con el mínimo
    hist.to_csv(carpeta / 'seleccion/historia_seleccion.csv')

    tr2 = em.tensores(dfn['entradas'], valores, objetivo, dfn['mu'], dfn['sigma'], perfil, m.AJUSTE_DEFINITIVO, **kw)
    modelo = _ridge(tr2['X'], tr2['y'], alpha)
    pd.DataFrame({'loss': [_mse(modelo, tr2)]}, index=pd.RangeIndex(1, 2, name='epoca')).to_csv(
        carpeta / 'historia_definitiva.csv')
    vecinas = [c for c in valores.columns if c != objetivo]
    np.savez(carpeta / 'modelo_lineal.npz', coef=modelo.coef, intercepto=modelo.intercepto, alpha=alpha,
             vecinas=np.array(vecinas), mu=dfn['mu'][vecinas].to_numpy(), sigma=dfn['sigma'][vecinas].to_numpy(),
             inactivos=np.array(dfn['inactivos'], dtype=str))

    config = dict(protocolo=PROTOCOLO, tipo='lineal', incluir_t=True, objetivo=objetivo, alpha=alpha,
                  alphas=ALPHAS, epoca_E=None, epocas_seleccion_ejecutadas=len(ALPHAS), max_epocas=None,
                  val_loss_minimo=float(hist['val_loss'].min()), n_ajuste_inicial=len(tr1['y']),
                  n_validacion=len(va1['y']), n_ajuste_definitivo=len(tr2['y']),
                  canales_inactivos=dfn['inactivos'],
                  versiones=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__))
    (carpeta / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n')
    p95 = regenerar(ctx, objetivo, carpeta, umbral_guardado=False)
    config.update(umbral_p95_ppb=p95, n_calibracion=len(pd.read_csv(carpeta / 'calibracion_2023.csv.gz')),
                  sha256=dict(modelo=em._sha(carpeta / 'modelo_lineal.npz')))
    (carpeta / 'configuracion.json').write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n')
    return config


# ---------------------------------------------------------------- carga común

def cargar_modelo(carpeta):
    """(modelo, incluir_t) para V4, lstm_t o lineal_t, según su configuracion.json."""
    carpeta = Path(carpeta)
    cfg = json.loads((carpeta / 'configuracion.json').read_text())
    if cfg.get('tipo') == 'lineal':
        with np.load(carpeta / 'modelo_lineal.npz', allow_pickle=False) as z:
            return ModeloLineal(z['coef'], z['intercepto']), True
    from tensorflow import keras
    return keras.models.load_model(carpeta / 'modelo.keras', compile=False), cfg.get('incluir_t', False)


def regenerar(ctx, objetivo, carpeta, umbral_guardado=True):
    """Calibración y predicciones desde el modelo guardado (sin entrenar). Devuelve el p95.

    Si `umbral_guardado`, exige que el p95 recalculado sea idéntico al guardado.
    """
    carpeta = Path(carpeta)
    modelo, incluir_t = cargar_modelo(carpeta)
    d = ctx['definitiva']
    perfil = m.perfil_causal(ctx['valores'][objetivo])
    t = em.tensores(d['entradas'], ctx['valores'], objetivo, d['mu'], d['sigma'], perfil, ('calibracion',),
                    incluir_t=incluir_t)
    cal = em.predecir(modelo, t)
    p95 = em.umbral_p95(cal)
    if umbral_guardado:
        if p95 != float((carpeta / 'umbral_p95_cal2023.txt').read_text()):
            raise ValueError(f'{objetivo}: p95 recalculado distinto del guardado')
    else:
        (carpeta / 'umbral_p95_cal2023.txt').write_text(f'{p95:.17g}\n')
    cal.to_csv(carpeta / 'calibracion_2023.csv.gz', index=False)
    for anio, etapa in at.ANIOS.items():
        t = em.tensores(d['entradas'], ctx['valores'], objetivo, d['mu'], d['sigma'], perfil, (etapa,),
                        incluir_t=incluir_t)
        if len(t['y']):
            p = em.predecir(modelo, t)
            p.assign(alerta_limpia=np.abs(p['residuo_ppb']) > p95).to_csv(
                carpeta / f'predicciones_{anio}.csv.gz', index=False)
    return p95


def comparar_lineal(a, b) -> pd.DataFrame:
    """Reproducibilidad de lineal_t: coeficientes, α, p95 y predicciones."""
    a, b = Path(a), Path(b)
    with np.load(a / 'modelo_lineal.npz') as za, np.load(b / 'modelo_lineal.npz') as zb:
        filas = [('coeficientes idénticos', np.array_equal(za['coef'], zb['coef']) and za['intercepto'] == zb['intercepto'], ''),
                 ('alpha', float(za['alpha']) == float(zb['alpha']), f"{float(za['alpha'])}")]
    ua, ub = (float((x / 'umbral_p95_cal2023.txt').read_text()) for x in (a, b))
    filas.append(('umbral p95 idéntico', ua == ub, f'{ua!r}'))
    for nombre in ['calibracion_2023.csv.gz'] + [f'predicciones_{x}.csv.gz' for x in at.ANIOS]:
        if (a / nombre).exists():
            filas.append((nombre, pd.read_csv(a / nombre).equals(pd.read_csv(b / nombre)), ''))
    return pd.DataFrame(filas, columns=['comprobacion', 'identico', 'detalle'])


# ---------------------------------------------------------------- evaluación de un mensaje

ARCHIVOS_EVAL = dict(limpias='metricas_limpias.csv', pareadas='metricas_pareadas.csv',
                     pareadas_agr='metricas_pareadas_agregadas.csv', dano='resumen_dano_mensajes.csv',
                     dias='resumen_dano_dias.csv', cobertura='cobertura_prueba.csv')


def evaluar_un_mensaje(ctx, estaciones, salida, clases):
    """Misma evaluación del notebook 13 (§7.1–§8) para cualquier familia de modelos."""
    salida = Path(salida)
    (salida / 'eventos_dano').mkdir(parents=True, exist_ok=True)
    (salida / 'planes_ataque').mkdir(parents=True, exist_ok=True)
    pred = at.cargar_predicciones(estaciones, ctx, regenerar=regenerar)
    limpias, pareadas, dano, dias, cobertura = [], [], [], [], []
    for anio in at.ANIOS:
        base = at.mensajes_prueba(ctx['valores'], pred, anio)
        for est, g in base[base.evaluable].groupby('estacion'):
            r = pd.read_csv(Path(estaciones) / est / f'predicciones_{anio}.csv.gz')
            limpias.append(dict(anio=anio, estacion=est, clasificacion=clases[est], umbral_ppb=g.umbral_ppb.iat[0],
                                **em.metricas_limpias(r, g.umbral_ppb.iat[0])))
        sel = at.plan_pareado(base)
        base.loc[sel, ['timestamp', 'estacion', 'original_ppb', 'evaluable']].to_csv(
            salida / f'planes_ataque/plan_{anio}.csv.gz', index=False)
        pareadas.append(at.evaluar_pareado(base, sel))
        c, ev, agr = at.barrido(base)
        dano.append(c)
        dias.append(at.resumen_dias(base, agr))
        ev.to_parquet(salida / f'eventos_dano/eventos_{anio}.parquet', index=False)
        cobertura.append(dict(anio=anio, lecturas_observadas=len(base), lecturas_evaluables=int(base.evaluable.sum()),
                              estaciones_evaluables=base.loc[base.evaluable, 'estacion'].nunique()))
    R = dict(limpias=pd.DataFrame(limpias), pareadas=pd.concat(pareadas, ignore_index=True),
             dano=pd.concat(dano, ignore_index=True), dias=pd.concat(dias, ignore_index=True),
             cobertura=pd.DataFrame(cobertura))
    R['pareadas_agr'] = at.agregar_pareado(R['pareadas'], clases)
    for k, f in ARCHIVOS_EVAL.items():
        R[k].to_csv(salida / f, index=False)
    return R


# ---------------------------------------------------------------- atacante simultáneo

def plan_horas(valores, anio, semilla=at.SEMILLA, tasa=at.TASA) -> pd.DatetimeIndex:
    """5 % de las horas del año, con un generador propio del atacante simultáneo."""
    idx = valores.loc[str(anio)].index
    rng = np.random.default_rng([semilla, SEMILLA_SIMULTANEO, anio])
    return idx[rng.random(len(idx)) < tasa]


def matriz_atacada(valores, horas, bit) -> pd.DataFrame:
    """Voltea el bit en TODOS los mensajes observados de las horas elegidas (cadena real)."""
    v = valores.copy()
    bloque = v.loc[horas].to_numpy(dtype=float, copy=True)
    obs = ~np.isnan(bloque)
    bloque[obs] = at.voltear(bloque[obs], bit)
    v.loc[horas] = bloque
    return v


def evaluar_simultaneo_bit(ctx, familias: dict, anio, bit, horas, modelos_cache=None):
    """Métricas por familia y estación para un año y un bit.

    `familias`: {nombre: carpeta_estaciones}. Se recalculan perfil, entradas y predicciones
    con la matriz atacada; modelos y umbrales quedan fijos.
    """
    cache = modelos_cache if modelos_cache is not None else {}
    va = matriz_atacada(ctx['valores'], horas, bit)
    d = ctx['definitiva']
    entradas = m.entradas_modelo(va, d['inactivos'])
    etapa = at.ANIOS[anio]
    hset = pd.DatetimeIndex(horas)
    filas = []
    for obj in m.ESTACIONES:
        carpetas = {f: Path(c) / obj for f, c in familias.items() if (Path(c) / obj / 'configuracion.json').exists()}
        if not carpetas:
            continue
        perfil = m.perfil_causal(va[obj])
        for fam, carpeta in carpetas.items():
            if (fam, obj) not in cache:
                cache[(fam, obj)] = (*cargar_modelo(carpeta), float((carpeta / 'umbral_p95_cal2023.txt').read_text()))
            modelo, incluir_t, umbral = cache[(fam, obj)]
            t = em.tensores(entradas, va, obj, d['mu'], d['sigma'], perfil, (etapa,), incluir_t=incluir_t)
            if not len(t['y']):
                continue
            p = em.predecir(modelo, t)
            alerta = np.abs(p['original_ppb'] - p['predicho_ppb']).to_numpy() > umbral
            etiqueta = p['timestamp'].isin(hset).to_numpy()
            fila = dict(familia=fam, anio=anio, bit=bit, delta_ppb=2 ** bit, estacion=obj,
                        mensajes=len(p), atacados=int(etiqueta.sum()))
            fila.update(metricas_binarias(etiqueta, alerta))
            filas.append(fila)
    return pd.DataFrame(filas)


def agregar_simultaneo(por_estacion: pd.DataFrame, clases: pd.Series) -> pd.DataFrame:
    d = por_estacion.assign(grupo=por_estacion.estacion.map(clases))
    filas = []
    for (fam, anio, bit, grupo), g in d.groupby(['familia', 'anio', 'bit', 'grupo']):
        tp, fp, fn, tn = (int(g[c].sum()) for c in ('tp', 'fp', 'fn', 'tn'))
        filas.append(dict(familia=fam, anio=anio, bit=bit, delta_ppb=2 ** bit, grupo=grupo, estaciones=len(g),
                          tp=tp, fp=fp, fn=fn, tn=tn, recall_micro_pct=at._pct(tp, tp + fn),
                          precision_micro_pct=at._pct(tp, tp + fp), f2_micro_pct=at._pct(5 * tp, 5 * tp + 4 * fn + fp),
                          fpr_micro_pct=at._pct(fp, fp + tn), recall_macro_pct=g['recall_pct'].mean()))
    return pd.DataFrame(filas)
