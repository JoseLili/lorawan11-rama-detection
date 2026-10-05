"""Ataques y daño del protocolo V4 multianual (§7.2, §7.3 y §8).

Sólo CARGA los modelos y umbrales de `results/lstm_v4_multianual_v1/estaciones/`;
nunca entrena ni recalibra. Dos evaluaciones que no se mezclan:

A. Muestra pareada al 5 %: clasificación (TP, FP, FN, TN, recall, precisión, F2, FPR).
B. Barrido exhaustivo: cada lectura observada × cada bit 0–7, como escenario aislado,
   para medir oportunidades de daño local y de la red (155 ppb).

Reutilizar la predicción limpia para un ataque aislado es válido: la estación
objetivo no está entre sus entradas y su perfil sólo usa el pasado (§7.2).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.attack.blind import atacar_serie
from src.decision.nom172 import banda_o3
from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect.red import contexto_diario, efectos_red, metricas_binarias, resumir_dias

BITS = list(range(8))
TAU = 155
SEMILLA = 42
TASA = 0.05
ANIOS = {2024: 'prueba_2024', 2025: 'prueba_2025', 2026: 'prueba_2026_parcial'}
TIPOS_DANO = ['cambio_banda_local', 'cambio_banda_red', 'falsa_fase1', 'anulada_fase1']


# ---------------------------------------------------------------- predicciones

def regenerar_predicciones(ctx, objetivo, carpeta):
    """Recalcula calibración y predicciones desde `modelo.keras` (opción A: no van en git).

    No entrena. Comprueba que el p95 recalculado coincide con el guardado.
    """
    from tensorflow import keras
    carpeta = Path(carpeta)
    modelo = keras.models.load_model(carpeta / 'modelo.keras', compile=False)
    incluir_t = json.loads((carpeta / 'configuracion.json').read_text()).get('incluir_t', False)
    d = ctx['definitiva']
    perfil = m.perfil_causal(ctx['valores'][objetivo])
    umbral = float((carpeta / 'umbral_p95_cal2023.txt').read_text())
    t = em.tensores(d['entradas'], ctx['valores'], objetivo, d['mu'], d['sigma'], perfil, ('calibracion',),
                    incluir_t=incluir_t)
    cal = em.predecir(modelo, t)
    if em.umbral_p95(cal) != umbral:
        raise ValueError(f'{objetivo}: p95 recalculado distinto del guardado; entorno o datos cambiaron')
    cal.to_csv(carpeta / 'calibracion_2023.csv.gz', index=False)
    for anio, etapa in ANIOS.items():
        t = em.tensores(d['entradas'], ctx['valores'], objetivo, d['mu'], d['sigma'], perfil, (etapa,),
                        incluir_t=incluir_t)
        if len(t['y']):
            p = em.predecir(modelo, t)
            p.assign(alerta_limpia=np.abs(p['residuo_ppb']) > umbral).to_csv(
                carpeta / f'predicciones_{anio}.csv.gz', index=False)


def cargar_predicciones(estaciones, ctx=None, regenerar=None) -> pd.DataFrame:
    """Predicciones limpias de prueba de todos los objetivos entrenados, con su umbral.

    Si faltan los CSV (no versionados) y se pasa `ctx`, se regeneran desde el modelo
    con `regenerar(ctx, objetivo, carpeta)` (por defecto, el del LSTM).
    """
    regenerar = regenerar or regenerar_predicciones
    filas = []
    for obj in m.ESTACIONES:
        carpeta = Path(estaciones) / obj
        if not (carpeta / 'configuracion.json').exists():
            continue
        if ctx is not None and not (carpeta / 'calibracion_2023.csv.gz').exists():
            regenerar(ctx, obj, carpeta)
        umbral = float((carpeta / 'umbral_p95_cal2023.txt').read_text())
        for anio in ANIOS:
            f = carpeta / f'predicciones_{anio}.csv.gz'
            if f.exists():
                p = pd.read_csv(f, parse_dates=['timestamp'])
                filas.append(p[['timestamp', 'predicho_ppb']].assign(estacion=obj, umbral_ppb=umbral))
    return pd.concat(filas, ignore_index=True)


def mensajes_prueba(valores: pd.DataFrame, predicciones: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Una fila por lectura OBSERVADA del año en las 33 estaciones, con contexto diario de red.

    `evaluable` = hay modelo y predicción para esa lectura. Las no evaluables se
    conservan: cuentan para el máximo de red y como daño sin evaluación.
    """
    v = valores.loc[str(anio)]
    base = contexto_diario(v)
    base['anio'] = anio
    base = base.merge(predicciones, on=['timestamp', 'estacion'], how='left', validate='one_to_one')
    base['evaluable'] = base['predicho_ppb'].notna()
    base['alerta_limpia'] = base['evaluable'] & (
        np.abs(base['original_ppb'] - base['predicho_ppb']) > base['umbral_ppb'])
    return base


# ---------------------------------------------------------------- ataque

def voltear(originales, bit) -> np.ndarray:
    """Cadena real CayenneLPP → AES-CTR → flip → descifrar → decodificar, cotejada con XOR."""
    o = np.asarray(originales, dtype=float)
    if not np.allclose(o, np.round(o)):
        raise ValueError('las lecturas de O3 deben ser enteras')
    recibidos, _ = atacar_serie(o, bit, tasa=1.0, seed=SEMILLA)
    np.testing.assert_array_equal(recibidos, o.astype(int) ^ (1 << bit))
    return recibidos


def detectado(base, recibidos) -> np.ndarray:
    """Alerta sobre lo recibido con la predicción limpia y el umbral de la estación."""
    return base['evaluable'].to_numpy() & (
        np.abs(np.asarray(recibidos) - base['predicho_ppb'].to_numpy()) > base['umbral_ppb'].to_numpy())


# ---------------------------------------------------------------- A. muestra pareada

def plan_pareado(base: pd.DataFrame, semilla=SEMILLA, tasa=TASA) -> pd.Series:
    """Selección reproducible al 5 % por estación/año, ANTES de filtrar por evaluabilidad.

    Un generador por (semilla, índice de estación, año), con índices estables de
    `multianual.ESTACIONES` (no `hash()`): el mismo plan sirve para los 8 bits.
    """
    sel = pd.Series(False, index=base.index)
    anio = int(base['anio'].iat[0])
    for est, g in base.groupby('estacion', sort=False):
        g = g.sort_values('timestamp')
        rng = np.random.default_rng([semilla, m.ESTACIONES.index(est), anio])
        sel.loc[g.index] = rng.random(len(g)) < tasa
    return sel


def evaluar_pareado(base: pd.DataFrame, seleccion: pd.Series) -> pd.DataFrame:
    """TP/FP/FN/TN por estación y bit, sólo con mensajes evaluables."""
    filas = []
    for bit in BITS:
        recibidos = np.where(seleccion, np.nan, base['original_ppb'])
        idx = seleccion.to_numpy()
        recibidos[idx] = voltear(base.loc[idx, 'original_ppb'], bit)
        alerta = detectado(base, recibidos)
        for est, g in base.assign(_a=alerta, _y=seleccion.to_numpy()).groupby('estacion', sort=False):
            ev = g['evaluable']
            fila = dict(anio=int(base['anio'].iat[0]), estacion=est, bit=bit, delta_ppb=2 ** bit,
                        seleccionados=int(g['_y'].sum()), seleccionados_evaluables=int((g['_y'] & ev).sum()),
                        mensajes_evaluables=int(ev.sum()))
            fila.update(metricas_binarias(g.loc[ev, '_y'], g.loc[ev, '_a']))
            filas.append(fila)
    return pd.DataFrame(filas)


def _pct(n, d):
    return 100 * n / d if d else np.nan


def agregar_pareado(por_estacion: pd.DataFrame, clases: pd.Series) -> pd.DataFrame:
    """Micro (suma de conteos) y macro (promedio simple por estación evaluable), por año, bit y grupo.

    `grupo` = clasificación §3.2 (principal | baja_representatividad); se reportan aparte.
    """
    d = por_estacion[por_estacion.mensajes_evaluables > 0].copy()
    d['grupo'] = d['estacion'].map(clases)
    filas = []
    for (anio, bit, grupo), g in d.groupby(['anio', 'bit', 'grupo']):
        tp, fp, fn, tn = (int(g[c].sum()) for c in ('tp', 'fp', 'fn', 'tn'))
        filas.append(dict(anio=anio, bit=bit, delta_ppb=2 ** bit, grupo=grupo, estaciones=len(g),
                          tp=tp, fp=fp, fn=fn, tn=tn,
                          recall_micro_pct=_pct(tp, tp + fn), precision_micro_pct=_pct(tp, tp + fp),
                          f2_micro_pct=_pct(5 * tp, 5 * tp + 4 * fn + fp), fpr_micro_pct=_pct(fp, fp + tn),
                          recall_macro_pct=g['recall_pct'].mean(), fpr_macro_pct=g['fpr_pct'].mean()))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- B. barrido exhaustivo

def barrido(base: pd.DataFrame):
    """Cada lectura observada × bit, escenario aislado. Devuelve (conteos, eventos_con_daño, agregables)."""
    conteos, eventos, agregables = [], [], []
    anio = int(base['anio'].iat[0])
    for bit in BITS:
        recibidos = voltear(base['original_ppb'], bit)
        e = base[['fecha', 'timestamp', 'estacion', 'original_ppb', 'maximo_original_ppb', 'maximo_otros_ppb',
                  'evaluable', 'predicho_ppb', 'umbral_ppb']].copy()
        e['bit'], e['recibido_ppb'] = bit, recibidos
        e['detectado'] = detectado(base, recibidos)
        e = pd.concat([e, efectos_red(base, recibidos)], axis=1)
        e['subida'] = recibidos > base['original_ppb'].to_numpy()
        for tipo in TIPOS_DANO:
            dano = e[tipo].to_numpy()
            ev, det = e['evaluable'].to_numpy(), e['detectado'].to_numpy()
            conteos.append(dict(anio=anio, bit=bit, delta_ppb=2 ** bit, tipo_dano=tipo, escenarios=len(e),
                                oportunidades=int(dano.sum()), evaluables=int((dano & ev).sum()),
                                detectadas=int((dano & det).sum()), no_detectadas=int((dano & ev & ~det).sum()),
                                sin_evaluacion=int((dano & ~ev).sum())))
            agregables.append(pd.DataFrame(dict(
                fecha=e['fecha'], bit=bit, tipo_dano=tipo, dano_observado=dano, dano_evaluable=dano & ev,
                dano_detectado=dano & det, dano_no_detectado=dano & ev & ~det, dano_sin_evaluacion=dano & ~ev)))
        eventos.append(e[e[TIPOS_DANO].any(axis=1)])
    c = pd.DataFrame(conteos)
    c['deteccion_pct'] = 100 * c.detectadas / c.evaluables.where(c.evaluables > 0)
    return c, pd.concat(eventos, ignore_index=True), pd.concat(agregables, ignore_index=True)


def resumen_dias(base: pd.DataFrame, agregables: pd.DataFrame) -> pd.DataFrame:
    """Días con oportunidad / con daño no detectado (§8). Denominador: días con alguna lectura."""
    fechas = sorted(base['fecha'].unique())
    res, _ = resumir_dias(agregables, fechas)
    res.insert(0, 'anio', int(base['anio'].iat[0]))
    dias_exc = base.groupby('fecha')['maximo_original_ppb'].first().ge(TAU).sum()
    res['dias_con_excedencia_original'] = int(dias_exc)
    return res
