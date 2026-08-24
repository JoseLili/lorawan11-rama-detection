"""Validacion del modulo de ingesta RAMA."""

import numpy as np
import pandas as pd
import pytest

from src.ingest.rama import (
    chronological_split, gap_lengths, interpolate, segment, to_long,
)


def _wide(valores_aaa, valores_bbb=None):
    """Construye un DataFrame ancho sintetico a partir de listas horarias."""
    n = len(valores_aaa)
    if valores_bbb is None:
        valores_bbb = [10.0] * n
    rows = []
    for i in range(n):
        rows.append({
            "FECHA": pd.Timestamp("2025-01-01") + pd.Timedelta(days=i // 24),
            "HORA": (i % 24) + 1,
            "AAA": valores_aaa[i],
            "BBB": valores_bbb[i],
        })
    return pd.DataFrame(rows)


# --- to_long ---------------------------------------------------------

def test_hora_1_es_medianoche():
    long = to_long(_wide([1.0] * 24), "O3")
    assert long["timestamp"].min() == pd.Timestamp("2025-01-01 00:00")


def test_hora_24_son_las_23():
    long = to_long(_wide([1.0] * 24), "O3")
    assert long["timestamp"].max() == pd.Timestamp("2025-01-01 23:00")


def test_no_hay_timestamps_duplicados():
    long = to_long(_wide([1.0] * 48), "O3")
    assert not long.duplicated(subset=["station", "timestamp"]).any()


# --- gap_lengths -----------------------------------------------------

def test_gap_lengths_detecta_bloques():
    s = pd.Series([1, np.nan, np.nan, 4, np.nan, 6, 7])
    assert sorted(gap_lengths(s).tolist()) == [1, 2]


def test_gap_lengths_sin_faltantes():
    assert len(gap_lengths(pd.Series([1.0, 2.0, 3.0]))) == 0


# --- segment ---------------------------------------------------------

def test_hueco_corto_no_corta():
    v = [1.0] * 10 + [np.nan] * 3 + [1.0] * 10
    seg = segment(to_long(_wide(v), "O3"), max_gap=5)
    aaa = seg[seg.station == "AAA"]
    assert aaa["segment_id"].nunique() == 1
    assert len(aaa) == 23  # nada se descarta


def test_hueco_largo_corta_y_descarta():
    v = [1.0] * 10 + [np.nan] * 8 + [1.0] * 10
    seg = segment(to_long(_wide(v), "O3"), max_gap=5)
    aaa = seg[seg.station == "AAA"]
    assert aaa["segment_id"].nunique() == 2
    assert len(aaa) == 20  # las 8 filas del hueco se van


def test_segment_ids_unicos_entre_estaciones():
    """Regresion: los ids no deben reiniciarse por estacion."""
    v = [1.0] * 10 + [np.nan] * 8 + [1.0] * 10
    seg = segment(to_long(_wide(v, v), "O3"), max_gap=5)
    ids_aaa = set(seg[seg.station == "AAA"]["segment_id"])
    ids_bbb = set(seg[seg.station == "BBB"]["segment_id"])
    assert ids_aaa.isdisjoint(ids_bbb)


def test_segment_conserva_columna_station():
    """Regresion: groupby.apply en pandas 3 excluia la columna de grupo."""
    seg = segment(to_long(_wide([1.0] * 24), "O3"))
    assert "station" in seg.columns


# --- interpolate -----------------------------------------------------

def test_interpolacion_es_lineal():
    v = [10.0, np.nan, np.nan, 40.0]
    out = interpolate(segment(to_long(_wide(v), "O3")))
    aaa = out[out.station == "AAA"].sort_values("timestamp")
    assert aaa["value"].tolist() == pytest.approx([10.0, 20.0, 30.0, 40.0])


def test_bandera_marca_solo_los_inventados():
    v = [10.0, np.nan, 30.0]
    out = interpolate(segment(to_long(_wide(v), "O3")))
    aaa = out[out.station == "AAA"].sort_values("timestamp")
    assert aaa["interpolated"].tolist() == [False, True, False]


def test_no_interpola_a_traves_de_segmentos():
    """Un valor no debe calcularse usando vecinos de otro tramo."""
    v = [10.0] * 5 + [np.nan] * 8 + [100.0] * 5
    out = interpolate(segment(to_long(_wide(v), "O3"), max_gap=5))
    aaa = out[out.station == "AAA"]
    assert set(aaa["value"].unique()) == {10.0, 100.0}


# --- chronological_split ---------------------------------------------

def test_split_es_cronologico():
    long = to_long(_wide([1.0] * 48), "O3")
    train, test = chronological_split(long, 0.8)
    assert train["timestamp"].max() < test["timestamp"].min()


def test_split_no_pierde_filas():
    long = to_long(_wide([1.0] * 48), "O3")
    train, test = chronological_split(long, 0.8)
    assert len(train) + len(test) == len(long)


def test_split_misma_frontera_para_todas_las_estaciones():
    long = to_long(_wide([1.0] * 48), "O3")
    train, _ = chronological_split(long, 0.8)
    assert train.groupby("station")["timestamp"].max().nunique() == 1


def test_train_frac_invalido():
    long = to_long(_wide([1.0] * 24), "O3")
    with pytest.raises(ValueError):
        chronological_split(long, 1.5)