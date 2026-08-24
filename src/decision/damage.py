"""Metrica de daño: cambio de decision, no magnitud del desplazamiento."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .nom172 import banda_o3


def daño(x_real, x_recibido):
    """D = 1 si el ataque cambio la banda reportada, 0 si no.

    El daño no es propiedad del bit atacado ni de la magnitud del
    desplazamiento: depende de la distancia del valor original al umbral
    mas cercano. Un flip grande lejos del corte produce daño cero; uno
    minimo junto al corte cambia la decision.

    Devuelve int para entrada escalar, Series para Series, array en el
    resto de casos.
    """
    diff = banda_o3(x_real) != banda_o3(x_recibido)

    if isinstance(diff, pd.Series):
        return diff.astype(int)
    if np.isscalar(x_real) and np.isscalar(x_recibido):
        return int(diff)
    return np.asarray(diff).astype(int)


def severidad(x_real, x_recibido):
    """Numero de bandas que salto la decision. Con signo.

    Positivo: la banda reportada es peor que la real (inflado).
    Negativo: la banda reportada es mejor que la real (ocultamiento).
    """
    return banda_o3(x_recibido) - banda_o3(x_real)


def clasificar(x_real, x_recibido):
    """Categoriza el efecto del ataque.

    'sin_efecto' | 'inflado' | 'ocultamiento'
    """
    s = np.asarray(severidad(x_real, x_recibido))
    return np.select(
        [s > 0, s < 0],
        ["inflado", "ocultamiento"],
        default="sin_efecto",
    )