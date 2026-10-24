"""Decisión por estación-día (protocolo anomalias_red_v1, revisión 11).

Cada caso es una estación en un día de reloj (00–23 h): ¿estuvo alterada ese día? El valor por
hora y estación es el que el detector calcula antes de tomar el máximo de la red (la columna de
vecinas de la regla, o el residuo / p95 del V4), con signo. Se junta el día de dos formas:

- `peor_hora` (control): el mayor |valor| entre las horas válidas;
- `promedio_dia` (propuesta): |promedio con signo de las horas válidas|.

Sólo cuentan las estación-días con al menos `MIN_HORAS` horas válidas (valor no NaN). La etiqueta
sale del plan: como los episodios son días completos, cada estación-día queda entera dentro o fuera.
La revisión 12 agrega la dominancia en el vecindario, contra el contagio a las vecinas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_HORAS = 12
AGREGACIONES = ('peor_hora', 'promedio_dia')
DIAS_TRAS = 14
GRUPOS_FA = ('contagio', 'tras_ataque_propio', 'resto')      # en este orden; no se enciman


def _dias_completos(index: pd.DatetimeIndex) -> None:
    if (len(index) == 0 or index[0].hour != 0 or index[-1].hour != 23
            or not index.equals(pd.date_range(index[0], index[-1], freq='h'))):
        raise ValueError('se requieren días completos: rejilla horaria continua de 00 h a 23 h')


def horas_validas(valores: pd.DataFrame) -> pd.DataFrame:
    """Día × estación: cuántas horas del día tienen valor."""
    _dias_completos(valores.index)
    return valores.notna().groupby(valores.index.normalize()).sum()


def juntar_dia(valores: pd.DataFrame, agregacion: str, min_horas: int = MIN_HORAS) -> pd.DataFrame:
    """Puntaje día × estación; NaN en las estación-días con menos de `min_horas` horas válidas."""
    if agregacion not in AGREGACIONES:
        raise ValueError(f'agregación desconocida: {agregacion}')
    validas = horas_validas(valores)
    dia = valores.index.normalize()
    s = valores.abs().groupby(dia).max() if agregacion == 'peor_hora' else valores.groupby(dia).mean().abs()
    return s.where(validas >= min_horas)


def dominancia(puntaje: pd.DataFrame, vecinas: dict) -> pd.DataFrame:
    """Revisión 12: el puntaje de una estación-día pasa a 0 si una vecina evaluada tiene uno mayor ese día.

    Sólo cuentan las vecinas que son columnas de `puntaje` y tienen puntaje (no NaN); con empate se
    quedan las dos. Una estación-día sin puntaje sigue sin puntaje.
    """
    mayor = pd.DataFrame({s: puntaje[[v for v in vecinas[s] if v in puntaje.columns]].max(axis=1)
                          if any(v in puntaje.columns for v in vecinas[s]) else np.nan
                          for s in puntaje.columns}, index=puntaje.index)
    return puntaje.where(~(mayor > puntaje), 0.0)


def etiquetas(plan: pd.DataFrame, dias: pd.DatetimeIndex, estaciones) -> pd.DataFrame:
    """Día × estación: True si el día está dentro de un episodio de esa estación en el plan."""
    ajenas = sorted(set(plan['estacion']) - set(estaciones))
    if ajenas:
        raise ValueError(f'el plan altera estaciones fuera de la evaluación: {ajenas}')
    y = pd.DataFrame(False, index=dias, columns=list(estaciones))
    for e in plan.itertuples():
        y.loc[e.inicio.normalize():e.fin.normalize(), e.estacion] = True
    return y


def grupos_falsa_alarma(plan: pd.DataFrame, dias: pd.DatetimeIndex, estaciones, vecinas: dict,
                        dias_tras: int = DIAS_TRAS) -> pd.DataFrame:
    """Día × estación: a qué grupo pertenece cada estación-día normal ('' si está atacada).

    'contagio' si alguna de sus vecinas está atacada ese día; si no, 'tras_ataque_propio' si cae en
    los `dias_tras` días siguientes al fin de un episodio de la misma estación; si no, 'resto'.
    """
    y = etiquetas(plan, dias, estaciones)
    vistas = sorted(set(estaciones) | {v for s in estaciones for v in vecinas[s]})
    atacada = etiquetas(plan, dias, vistas)
    contagio = pd.DataFrame({s: atacada[vecinas[s]].any(axis=1) for s in estaciones})
    tras = pd.DataFrame(False, index=dias, columns=list(estaciones))
    for e in plan.itertuples():
        f = e.fin.normalize()
        tras.loc[f + pd.Timedelta(days=1):f + pd.Timedelta(days=dias_tras), e.estacion] = True
    g = np.where(y, '', np.where(contagio, GRUPOS_FA[0], np.where(tras, GRUPOS_FA[1], GRUPOS_FA[2])))
    return pd.DataFrame(g, index=dias, columns=list(estaciones))
