"""Entradas, umbrales y métricas de red del protocolo `anomalias_red_v1` (§8 y §9).

Común a todos los detectores: cada uno produce un puntaje por hora de red y aquí se
convierte en alertas y métricas. No entrena modelos.

Métricas (§9 y revisión 2):
    - por hora: proporción de horas con etiqueta 1 que alertan, con falsas alarmas fijas;
    - por episodio: detectado si hay alguna alerta de red mientras dura, y horas hasta la
      primera alerta, siempre junto a su nivel de azar: las mismas ventanas evaluadas con
      las alertas del año limpio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.detect import multianual as m

NIVELES_FA = (0.05, 0.01)


# ---------------------------------------------------------------- entradas

def estaciones_de(matriz: pd.DataFrame) -> list[str]:
    return [c[:-len('_valor')] for c in matriz.columns if c.endswith('_valor')]


def normalizacion(limpia: pd.DataFrame):
    """Media y desviación (ddof=1, 0 → 1) por estación con la matriz limpia de 2020–2022, como el V4."""
    v = limpia[[f'{s}_valor' for s in estaciones_de(limpia)]]
    v.columns = estaciones_de(limpia)
    return v.mean(), v.std().replace(0, 1.0)


def entradas(matriz: pd.DataFrame, mu, sigma) -> np.ndarray:
    """Las 66 columnas de la hora t: valores normalizados (hueco → 0), máscaras, seno y coseno."""
    est = estaciones_de(matriz)
    v = matriz[[f'{s}_valor' for s in est]]
    v.columns = est
    norm = ((v - mu[est]) / sigma[est]).fillna(0.0).to_numpy(np.float32)
    mascara = matriz[[f'{s}_mascara' for s in est]].to_numpy(np.float32)
    hora = matriz[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([norm, mascara, hora], axis=1)


def relativas(matriz: pd.DataFrame, previa: pd.DataFrame | None = None) -> pd.DataFrame:
    """Valor menos su perfil causal de 14 días a esa hora, por estación y en ppb (la base del V4).

    `previa`, contigua y anterior a `matriz`, da la historia del perfil al inicio de `matriz`.
    Sin dato o sin historia → NaN.
    """
    est = estaciones_de(matriz)
    v = matriz[[f'{s}_valor' for s in est]].set_axis(est, axis=1)
    serie = v
    if previa is not None:
        p = previa[[f'{s}_valor' for s in est]].set_axis(est, axis=1)
        if p.index[-1] + pd.Timedelta(hours=1) != v.index[0]:
            raise ValueError('la matriz previa no termina una hora antes de la matriz')
        serie = pd.concat([p, v])
    base = pd.DataFrame({s: m.perfil_causal(serie[s])['base'] for s in est}).loc[v.index]
    return v - base


def entradas_relativas(matriz: pd.DataFrame, sigma, previa: pd.DataFrame | None = None) -> np.ndarray:
    """Como `entradas`, pero con (valor − perfil de 14 días) / σ en lugar del valor normalizado."""
    est = estaciones_de(matriz)
    rel = (relativas(matriz, previa) / sigma[est]).fillna(0.0).to_numpy(np.float32)
    mascara = matriz[[f'{s}_mascara' for s in est]].to_numpy(np.float32)
    hora = matriz[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([rel, mascara, hora], axis=1)


ENTRADAS = ('crudas', 'relativas')


def entradas_de(tipo: str, matriz: pd.DataFrame, mu, sigma) -> np.ndarray:
    """Las 66 columnas de la hora t: `crudas` (§8) o `relativas` al perfil de 14 días (revisión 7).

    Con `relativas`, `matriz` debe traer la historia que necesita el perfil (las matrices
    anteriores concatenadas); las columnas son puntuales, así que con `crudas` da lo mismo.
    """
    if tipo == 'crudas':
        return entradas(matriz, mu, sigma)
    if tipo == 'relativas':
        return entradas_relativas(matriz, sigma)
    raise ValueError(f'entradas desconocidas: {tipo}')


def con_historia(previa: pd.DataFrame, matriz: pd.DataFrame) -> pd.DataFrame:
    """`previa` y `matriz` concatenadas; `previa` debe terminar una hora antes de `matriz`."""
    if previa.index[-1] + pd.Timedelta(hours=1) != matriz.index[0]:
        raise ValueError('la historia no termina una hora antes de la matriz')
    return pd.concat([previa[matriz.columns], matriz])


# ---------------------------------------------------------------- umbral

def umbral_falsas_alarmas(puntaje_limpio, objetivo: float) -> float:
    """El umbral más bajo u tal que la proporción de horas limpias con puntaje > u no pasa de `objetivo`.

    Con puntajes con empates (p. ej., probabilidades de un Random Forest) la tasa lograda
    puede quedar por debajo del objetivo; se reporta la lograda.
    """
    p = np.sort(np.asarray(puntaje_limpio, dtype=float))
    n = len(p)
    for u in np.unique(p):
        if (n - np.searchsorted(p, u, side='right')) / n <= objetivo:
            return float(u)
    return float(p[-1])


# ---------------------------------------------------------------- métricas

def por_hora(alerta: pd.Series, etiqueta: pd.Series) -> dict:
    a, y = alerta.to_numpy(bool), etiqueta.to_numpy(bool)
    return dict(horas_anomalas=int(y.sum()), horas_normales=int((~y).sum()),
                deteccion_hora_pct=100 * a[y].mean() if y.any() else np.nan,
                falsa_alarma_hora_pct=100 * a[~y].mean() if (~y).any() else np.nan)


def por_episodio(plan: pd.DataFrame, alerta: pd.Series) -> pd.DataFrame:
    """Para cada episodio: si hubo alguna alerta de red mientras duró y las horas hasta la primera.

    `horas_hasta_alerta` = 0 si la alerta llega en la primera hora del episodio; NaN si no hubo.
    """
    tiempos = alerta.index[alerta.to_numpy(bool)]
    det, horas = [], []
    for e in plan.itertuples():
        dentro = tiempos[(tiempos >= e.inicio) & (tiempos <= e.fin)]
        det.append(len(dentro) > 0)
        horas.append((dentro[0] - e.inicio) / pd.Timedelta(hours=1) if len(dentro) else np.nan)
    return plan.assign(detectado=det, horas_hasta_alerta=horas)


TRAMOS_PPB = (1, 16, 32, 64)


def cambio_maximo(alterada: pd.DataFrame, limpia: pd.DataFrame) -> pd.Series:
    """Mayor |recibido − original| en ppb entre estaciones en cada hora; 0 si nada cambió."""
    cols = [f'{s}_valor' for s in estaciones_de(limpia)]
    d = np.abs(alterada[cols].to_numpy(float) - limpia[cols].to_numpy(float))
    return pd.Series(np.nan_to_num(d, nan=0.0).max(axis=1), index=limpia.index)


def por_tamano(alerta: pd.Series, cambio: pd.Series, alerta_limpia: pd.Series | None = None,
               tramos=TRAMOS_PPB) -> pd.DataFrame:
    """Horas que alertan según el mayor cambio de la hora (revisiones 3 y 4).

    Tramos cerrados por la izquierda: sin cambio (< 1 ppb), [1, 16), [16, 32), [32, 64), ≥ 64.
    Con `alerta_limpia` (las alertas del año limpio) agrega `alertan_azar`: cuántas de esas
    mismas horas alertan sin la alteración. Lo que aporta la alteración es la diferencia.
    """
    bordes = [0, *tramos, np.inf]
    nombres = ['sin cambio'] + [f'{a}-{b}' for a, b in zip(tramos, tramos[1:])] + [f'>={tramos[-1]}']
    tramo = pd.cut(cambio.to_numpy(), bordes, right=False, labels=nombres)
    contar = lambda a: pd.Series(a.to_numpy(bool)).groupby(tramo, observed=False)  # noqa: E731
    g = contar(alerta)
    t = pd.DataFrame(dict(tramo_ppb=nombres, horas=g.size().to_numpy(), alertan=g.sum().to_numpy().astype(int)))
    if alerta_limpia is not None:
        t['alertan_azar'] = contar(alerta_limpia).sum().to_numpy().astype(int)
    return t


def horas_con_dato(plan: pd.DataFrame, limpia: pd.DataFrame) -> list[int]:
    """Horas con dato de la estación durante cada episodio, con las máscaras de la matriz limpia."""
    return [int(limpia.loc[e.inicio:e.fin, f'{e.estacion}_mascara'].sum()) for e in plan.itertuples()]
