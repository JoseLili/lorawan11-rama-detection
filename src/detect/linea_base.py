"""Líneas base alternativas para L0 (exploración del 2026-11-04 y revisión LB1).

L0 compara cada lectura con su «lo normal», la media de esa hora en los 14 días anteriores
(`multianual.perfil_causal`). Un episodio contamina ese perfil hasta 14 días después. Aquí están
las tres variantes registradas en `docs/registro_previo_linea_base_2022.md`:

- V0: la base actual (`perfil_causal`), igual que `evaluacion_red.relativas`.
- Va: compuerta. Un día con alerta no entra al perfil. Ver `base_compuerta`, que es secuencial.
- Vb: anclada en vecinas = media de los perfiles de 14 días de las 4 vecinas + mediana causal
  de 60 días de (x_s − media de las vecinas) a esa hora. Sin dato, la base V0.
- Vc: dos velocidades = perfil de 14 días, salvo que se aleje más de τ_s de la mediana de
  60 días a esa hora; entonces, la mediana. τ_s = p99 de |P14 − Mediana60| en 2020–2021 limpio.

`entradas` reproduce exactamente las 98 columnas de `evaluacion_red.entradas_de('vecinas', ...)`
para cualquier base (diferencia 0.0 con V0; ver `tests/test_linea_base.py`).
Todo es causal: la base de la hora t sólo usa observaciones estrictamente anteriores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.detect import multianual as m

DIAS_LENTO = 60


def valores(x: pd.DataFrame, estaciones) -> np.ndarray:
    return x[[f'{s}_valor' for s in estaciones]].to_numpy(np.float64)


def indices_vecinas(estaciones, vecinas: dict) -> np.ndarray:
    pos = {s: i for i, s in enumerate(estaciones)}
    return np.array([[pos[v] for v in vecinas[s]] for s in estaciones])


def base_v0(x: pd.DataFrame, estaciones) -> np.ndarray:
    v = x[[f'{s}_valor' for s in estaciones]].set_axis(list(estaciones), axis=1)
    return pd.DataFrame({s: m.perfil_causal(v[s])['base'] for s in estaciones}).to_numpy()


def mediana_hora(a: np.ndarray, index: pd.DatetimeIndex, dias: int = DIAS_LENTO) -> np.ndarray:
    """Mediana causal de los `dias` días anteriores a esa misma hora, por columna."""
    d = pd.DataFrame(a, index=index)
    return d.groupby(index.hour).transform(lambda s: s.shift(1).rolling(dias, min_periods=1).median()).to_numpy()


def base_vb(V: np.ndarray, b0: np.ndarray, vec: np.ndarray, index) -> np.ndarray:
    with np.errstate(all='ignore'):
        perfil_vecinas = np.nanmean(b0[:, vec], axis=2)
        x_vecinas = np.nanmean(V[:, vec], axis=2)
    b = perfil_vecinas + mediana_hora(V - x_vecinas, index)
    return np.where(np.isnan(b), b0, b)


def tau_vc(V_limpia: np.ndarray, b0_limpia: np.ndarray, index, hasta) -> np.ndarray:
    lento = mediana_hora(V_limpia, index)
    sel = index <= pd.Timestamp(hasta)
    return np.nanquantile(np.abs(b0_limpia - lento)[sel], 0.99, axis=0)


def base_vc(V: np.ndarray, b0: np.ndarray, tau: np.ndarray, index) -> np.ndarray:
    lento = mediana_hora(V, index)
    return np.where(~np.isnan(lento) & (np.abs(b0 - lento) > tau), lento, b0)


def entradas(x: pd.DataFrame, base: np.ndarray, estaciones, sigma: np.ndarray, escala: np.ndarray,
             vec: np.ndarray, V: np.ndarray | None = None) -> np.ndarray:
    """Las 98 columnas de L0 con una base cualquiera: relativas, máscaras, seno, coseno y a14."""
    V = valores(x, estaciones) if V is None else V
    d = (V - base) / sigma
    nb = d[:, vec]
    n = np.sum(~np.isnan(nb), axis=2)
    with np.errstate(all='ignore'):
        prom = np.nanmean(nb, axis=2)
    a14 = np.where(~np.isnan(d) & (n >= 2), d - prom, np.nan) / escala
    mascara = x[[f'{s}_mascara' for s in estaciones]].to_numpy(np.float32)
    hora = x[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([np.nan_to_num(d, nan=0.0).astype(np.float32), mascara, hora,
                           np.nan_to_num(a14, nan=0.0).astype(np.float32)], axis=1)


def escala_a14(limpia: pd.DataFrame, base: np.ndarray, estaciones, sigma, vec, hasta) -> np.ndarray:
    """Desviación (ddof=1) de la columna a14 en el periodo limpio hasta `hasta`; 0 o NaN → 1."""
    d = (valores(limpia, estaciones) - base) / sigma
    nb = d[:, vec]
    n = np.sum(~np.isnan(nb), axis=2)
    with np.errstate(all='ignore'):
        prom = np.nanmean(nb, axis=2)
    a = np.where(~np.isnan(d) & (n >= 2), d - prom, np.nan)[limpia.index <= pd.Timestamp(hasta)]
    return pd.DataFrame(a, columns=list(estaciones)).std().replace(0, 1.0).fillna(1.0).to_numpy()
