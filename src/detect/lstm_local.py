"""LSTM local compartido por estación (protocolo `anomalias_red_v1`, revisión 14).

Un solo modelo mira, para cada objetivo s, la ventana t−23…t con 17 columnas sacadas de las 98 de
`evaluacion_red.entradas_vecinas`: las 3 de s (relativa, máscara y columna de vecinas a14), las
mismas 3 de cada una de sus 4 vecinas en orden de distancia, y el seno y el coseno de la hora. Se
aplica igual a las 31 estaciones, sin identificador de estación. La etiqueta (¿la lectura de s fue
alterada en t?) nunca es entrada.
"""
from __future__ import annotations

import numpy as np

from src.detect import evaluacion_red as ev
from src.detect import lstm_red as lr

N_COLUMNAS = 17
CADA = {20: 8, 60: 24}          # calendarios → 1 de cada k horas: el mismo número de ventanas por época
CADA_VALIDACION = 8
USOS = {'seleccion': 0, 'validacion': 1, 'definitivo': 2}


def indices_locales(estaciones, vecinas: dict, s: str) -> list[int]:
    """Las 17 columnas de s dentro de las 98: [rel, máscara, vecinas] de s y de sus 4 vecinas, seno, coseno.

    Las 98 son las relativas (n), las máscaras (n), el seno y el coseno, y las columnas de vecinas
    (n), con n estaciones en el orden de `estaciones`.
    """
    est = list(estaciones)
    n = len(est)
    if len(vecinas[s]) != ev.K_VECINAS:
        raise ValueError(f'{s} no tiene {ev.K_VECINAS} vecinas')
    idx = []
    for e in [s] + list(vecinas[s]):
        i = est.index(e)
        idx += [i, n + i, 2 * n + 2 + i]
    return idx + [2 * n, 2 * n + 1]


def muestra(posiciones: np.ndarray, cada: int, uso: str, calendario: int, estacion: int,
            semilla: int = 42) -> np.ndarray:
    """1 de cada `cada` posiciones, sin reemplazo y ordenadas; la semilla sale de 42, el uso y el par."""
    posiciones = np.asarray(posiciones)
    if cada == 1:
        return posiciones
    rng = np.random.default_rng([int(semilla), 14, USOS[uso], int(calendario), int(estacion)])
    return np.sort(rng.choice(posiciones, size=len(posiciones) // cada, replace=False))


def ventanas_locales(F: np.ndarray, estaciones, vecinas: dict, s: str, posiciones: np.ndarray) -> np.ndarray:
    """(n, 24, 17): las ventanas de s en `posiciones`, con F de 98 columnas."""
    return lr.ventanas(F[:, indices_locales(estaciones, vecinas, s)], posiciones)
