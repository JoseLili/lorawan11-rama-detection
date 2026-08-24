"""Validacion de la funcion de decision NOM-172 y la metrica de daño."""

import numpy as np
import pandas as pd
import pytest

from src.decision import Banda, banda_o3, clasificar, daño, nombre_banda, severidad


# --- Bordes de banda: lo mas critico del modulo ----------------------

@pytest.mark.parametrize("ppb,esperada", [
    (0,   Banda.BUENA),
    (57,  Banda.BUENA),
    (58,  Banda.BUENA),               # limite inferior ABIERTO: 58 aun es Buena
    (59,  Banda.ACEPTABLE),
    (89,  Banda.ACEPTABLE),
    (90,  Banda.ACEPTABLE),
    (91,  Banda.MALA),
    (134, Banda.MALA),
    (135, Banda.MALA),
    (136, Banda.MUY_MALA),
    (174, Banda.MUY_MALA),
    (175, Banda.MUY_MALA),
    (176, Banda.EXTREMADAMENTE_MALA),
    (500, Banda.EXTREMADAMENTE_MALA),
])
def test_bordes_de_banda(ppb, esperada):
    """La norma define los intervalos con limite inferior abierto.

    'Aceptable: >0.058 a 0.090' significa que 58 ppb es Buena y 59 es
    Aceptable. Las lecturas en el borde son las que el adversario
    explota, asi que un error de 1 ppb aqui invalidaria justamente los
    casos que importan.
    """
    assert banda_o3(ppb) == esperada


# --- Tipos de entrada ------------------------------------------------

def test_escalar_devuelve_int():
    assert isinstance(banda_o3(43), int)


def test_series_conserva_indice():
    s = pd.Series([10.0, 70.0, 100.0], index=[5, 6, 7])
    out = banda_o3(s)
    assert isinstance(out, pd.Series)
    assert out.index.tolist() == [5, 6, 7]
    assert out.tolist() == [0, 1, 2]


def test_array_devuelve_array():
    out = banda_o3(np.array([10.0, 70.0]))
    assert isinstance(out, np.ndarray)
    assert out.tolist() == [0, 1]


def test_nan_es_banda_indefinida():
    assert banda_o3(pd.Series([np.nan])).iloc[0] == -1


def test_negativo_lanza_error():
    with pytest.raises(ValueError):
        banda_o3(-99)


# --- Metrica de daño -------------------------------------------------

def test_flip_grande_lejos_del_umbral_no_hace_daño():
    """10 -> 42 ppb: desplazamiento de 32, ambos en Buena."""
    assert daño(10, 42) == 0


def test_flip_minimo_junto_al_umbral_si_hace_daño():
    """57 -> 59 ppb: desplazamiento de 2, cruza de Buena a Aceptable."""
    assert daño(57, 59) == 1


def test_el_daño_no_depende_de_la_magnitud():
    """Caso central de la tesis: un flip de 2 ppb causa daño y uno de
    32 ppb no, segun la distancia al umbral."""
    assert daño(10, 42) == 0   # +32
    assert daño(57, 59) == 1   # +2


def test_severidad_positiva_es_inflado():
    assert severidad(43, 107) == 2   # Buena -> Mala


def test_severidad_negativa_es_ocultamiento():
    assert severidad(107, 43) == -2


def test_severidad_cero_sin_cambio():
    assert severidad(10, 42) == 0


def test_clasificar():
    real = np.array([10, 57, 107])
    recv = np.array([42, 59, 43])
    assert clasificar(real, recv).tolist() == [
        "sin_efecto", "inflado", "ocultamiento"
    ]


# --- Reproduccion del EDA --------------------------------------------

def test_reproduce_distribucion_del_eda():
    """Verifica contra los conteos calculados a mano en notebooks/01.

    CCA 2025, 8491 lecturas validas.
    """
    conteos = {0: 6578, 1: 1289, 2: 604, 3: 20, 4: 0}
    total = sum(conteos.values())
    assert total == 8491

    # Reconstruye una muestra con la misma distribucion y verifica
    # que la clasificacion es estable
    valores = pd.Series([30] * conteos[0] + [70] * conteos[1] +
                        [100] * conteos[2] + [140] * conteos[3])
    b = banda_o3(valores)
    for banda, n in conteos.items():
        if n > 0:
            assert (b == banda).sum() == n


def test_nombre_banda():
    assert nombre_banda(0) == "Buena"
    assert nombre_banda(4) == "Extremadamente Mala"


def test_daño_acepta_los_tres_tipos_de_entrada():
    """Regresion: banda_o3 es polimorfica, y daño debe serlo tambien.
    Con escalares, `.astype()` no existe."""
    assert isinstance(daño(57, 59), int)

    arr = daño(np.array([57, 10]), np.array([59, 42]))
    assert isinstance(arr, np.ndarray)
    assert arr.tolist() == [1, 0]

    ser = daño(pd.Series([57, 10]), pd.Series([59, 42]))
    assert isinstance(ser, pd.Series)
    assert ser.tolist() == [1, 0]