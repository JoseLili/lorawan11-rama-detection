"""Funcion de decision segun NOM-172-SEMARNAT-2023.

Implementa el Indice AIRE Y SALUD para O3 (Tabla 6), que clasifica una
concentracion horaria en una de cinco bandas de calidad del aire.

Referencia: DOF 25/01/2024. Copia en docs/normas/.
"""

from __future__ import annotations
from enum import IntEnum

import numpy as np
import pandas as pd


class Banda(IntEnum):
    """Bandas del Indice AIRE Y SALUD, en orden creciente de deterioro."""
    BUENA = 0
    ACEPTABLE = 1
    MALA = 2
    MUY_MALA = 3
    EXTREMADAMENTE_MALA = 4


NOMBRES = {
    Banda.BUENA: "Buena",
    Banda.ACEPTABLE: "Aceptable",
    Banda.MALA: "Mala",
    Banda.MUY_MALA: "Muy Mala",
    Banda.EXTREMADAMENTE_MALA: "Extremadamente Mala",
}

# Tabla 6: intervalos en ppm. Se trabaja en ppb (x1000) porque es la
# unidad en que RAMA reporta, y coincide con la resolucion normativa:
# la Tabla 2 especifica 3 cifras decimales significativas en ppm.
#
#   Buena                <0.058          -> <=58 ppb
#   Aceptable            >0.058 a 0.090  ->  59..90
#   Mala                 >0.090 a 0.135  ->  91..135
#   Muy Mala             >0.135 a 0.175  -> 136..175
#   Extremadamente Mala  >0.175          -> >175
UMBRALES_O3_PPB = (58, 90, 135, 175)


def banda_o3(ppb):
    """f: concentracion horaria de O3 en ppb -> banda (0..4).

    Los limites inferiores de cada intervalo son ABIERTOS en la norma
    ("Aceptable: >0.058 a 0.090"), de modo que 58 ppb es Buena y 59 ppb
    es Aceptable. `side='left'` reproduce esa semantica: devuelve i para
    valores <= umbral[i-1].

    Este detalle es critico: las lecturas que caen exactamente en un
    umbral son las que el adversario explota.

    Acepta escalar, array o Series. Devuelve el mismo tipo.
    """
    escalar = np.isscalar(ppb)
    arr = np.asarray(ppb, dtype=float)

    if np.any(arr[~np.isnan(arr)] < 0):
        raise ValueError("La concentracion de O3 no puede ser negativa")

    b = np.searchsorted(UMBRALES_O3_PPB, arr, side="left")
    b = np.where(np.isnan(arr), -1, b)  # NaN -> -1, banda indefinida

    if escalar:
        return int(b)
    if isinstance(ppb, pd.Series):
        return pd.Series(b, index=ppb.index, dtype=int)
    return b.astype(int)


def nombre_banda(b) -> str:
    """Nombre legible de una banda."""
    return NOMBRES.get(Banda(b), "Indefinida")