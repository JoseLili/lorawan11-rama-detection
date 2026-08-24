"""Ingesta de archivos RAMA/SIMAT.

Formato de origen: .xls (BIFF legacy, requiere xlrd), formato ancho.
    FECHA | HORA | ACO | AJM | ... | XAL
HORA es entero 1..24; -99 indica dato faltante.
"""

from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd

MISSING = -99
NON_STATION_COLS = ("FECHA", "HORA")

# Criterio de tratamiento de faltantes (ver notebooks/01, celda 6).
# Derivado de CCA/2025: 65 bloques de 2-5 h, 5 bloques de 10-17 h,
# ninguno entre 5 y 10 h. El vacio da el corte sin arbitrariedad.
# Ajustar si se cambia de estacion o periodo.
MAX_GAP_INTERP = 5


def load_wide(path: str | Path) -> pd.DataFrame:
    """Lee un .xls de RAMA con -99 convertido a NaN."""
    df = pd.read_excel(path, header=0)
    stations = [c for c in df.columns if c not in NON_STATION_COLS]
    df[stations] = df[stations].replace(MISSING, np.nan)
    return df


def to_long(df: pd.DataFrame, pollutant: str) -> pd.DataFrame:
    """Formato ancho a largo con timestamp horario.

    HORA=1 se interpreta como 00:00 y HORA=24 como 23:00 del mismo dia.

    ADVERTENCIA: esta interpretacion es un supuesto sin verificar contra
    la especificacion de SIMAT. Si esta invertida, todas las series
    quedan desfasadas una hora. Ver docs/00_fuentes_datos.md.
    """
    stations = [c for c in df.columns if c not in NON_STATION_COLS]

    long = df.melt(
        id_vars=list(NON_STATION_COLS),
        value_vars=stations,
        var_name="station",
        value_name="value",
    )
    long["timestamp"] = pd.to_datetime(long["FECHA"]) + pd.to_timedelta(
        long["HORA"] - 1, unit="h"
    )
    long["pollutant"] = pollutant

    return (
        long[["timestamp", "station", "pollutant", "value"]]
        .sort_values(["station", "timestamp"])
        .reset_index(drop=True)
    )


def gap_lengths(series: pd.Series) -> pd.Series:
    """Longitud de cada bloque contiguo de faltantes."""
    missing = series.isna().astype(int)
    blocks = (missing != missing.shift()).cumsum()
    lengths = missing.groupby(blocks).sum()
    return lengths[lengths > 0]


def _segment_one(g: pd.DataFrame, max_gap: int) -> pd.DataFrame:
    """Asigna segment_id a una estacion. Corta en huecos > max_gap."""
    missing = g["value"].isna()
    blocks = (missing != missing.shift()).cumsum()
    block_len = missing.groupby(blocks).transform("sum")

    # Un hueco largo abre un segmento nuevo
    is_break = missing & (block_len > max_gap)
    g = g.copy()
    g["segment_id"] = (is_break & ~is_break.shift(fill_value=False)).cumsum()
    return g[~is_break]  # las filas del hueco largo se descartan


def segment(long: pd.DataFrame, max_gap: int = MAX_GAP_INTERP) -> pd.DataFrame:
    """Parte cada serie en tramos continuos.

    Los huecos de mas de max_gap horas se consideran interrupciones de
    operacion: sus filas se descartan y la serie se corta. Los tramos
    resultantes son independientes; ninguna operacion temporal posterior
    (diferencias, ventanas deslizantes) debe cruzar sus fronteras.

    Los segment_id son unicos a nivel global, no por estacion.
    """
    out = []
    offset = 0
    for _, g in long.groupby("station", sort=False):
        s = _segment_one(g, max_gap)
        if len(s) == 0:
            continue
        s["segment_id"] = s["segment_id"] + offset
        offset = int(s["segment_id"].max()) + 1
        out.append(s)

    if not out:
        return long.iloc[0:0].assign(segment_id=pd.Series(dtype=int))

    return pd.concat(out, ignore_index=True)


def interpolate(long: pd.DataFrame) -> pd.DataFrame:
    """Interpola linealmente los huecos restantes dentro de cada segmento.

    Añade la columna booleana `interpolated`, que marca los valores
    inventados. Es necesaria porque un valor interpolado produce una
    diferencia |x[t] - x[t-1]| artificialmente suave, y la Capa 2 se
    calibra precisamente sobre esa metrica.

    Interpolacion lineal: los huecos cortos se concentran de madrugada
    (celda 6), donde el ozono es bajo y estable. Un metodo que respete
    la forma del ciclo diurno no aportaria precision en esa franja.
    """
    long = long.copy()
    long["interpolated"] = long["value"].isna()
    long["value"] = (
        long.groupby(["station", "segment_id"])["value"]
        .transform(lambda s: s.interpolate(method="linear", limit_direction="both"))
    )
    return long


def chronological_split(
    long: pd.DataFrame, train_frac: float = 0.8
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corte cronologico global sobre el eje temporal.

    El corte se calcula sobre el rango de timestamps, no sobre el numero
    de filas, para que todas las estaciones compartan la misma frontera.

    DEBE aplicarse antes de interpolar: un valor interpolado cerca del
    corte podria calcularse con vecinos del conjunto de prueba.
    """
    if not 0.0 < train_frac < 1.0:
        raise ValueError("train_frac debe estar en (0, 1)")

    t_min, t_max = long["timestamp"].min(), long["timestamp"].max()
    cutoff = t_min + (t_max - t_min) * train_frac

    return (
        long[long["timestamp"] <= cutoff].copy(),
        long[long["timestamp"] > cutoff].copy(),
    )