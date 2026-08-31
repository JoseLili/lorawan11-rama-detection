"""Validacion de la codificacion CayenneLPP y el cifrado LoRaWAN 1.1.

Este es el modulo mas critico del proyecto: produce el ground truth de
toda la tesis. Un error de endianness, escala o signo invalidaria todos
los resultados posteriores sin producir ningun fallo visible.
"""

import os
import struct

import pytest

from src.encoding.cayenne import decode_o3, encode_o3, flip_bit
from src.encoding.crypto import (
    DIR_DOWNLINK, DIR_UPLINK, build_block_a, decrypt, encrypt, keystream,
)

KEY = bytes(range(16))          # clave fija: los tests deben ser deterministas
DEVADDR = 0x26011BDA
FCNT = 42


# --- Codificacion CayenneLPP ------------------------------------------

def test_trama_conocida():
    """43 ppb -> canal 1, tipo 0x02, valor 0x002B big-endian."""
    assert encode_o3(43) == bytes([0x01, 0x02, 0x00, 0x2B])


def test_es_big_endian():
    """300 = 0x012C. El byte alto va PRIMERO.

    Si estuviera invertido, el valor seria 0x2C01 = 11265.
    """
    assert encode_o3(300)[2:] == bytes([0x01, 0x2C])


def test_ida_y_vuelta():
    for ppb in (0, 1, 43, 58, 90, 135, 168, 175):
        assert decode_o3(encode_o3(ppb)) == ppb


def test_canal_configurable():
    assert encode_o3(43, channel=7)[0] == 7


def test_rechaza_fuera_de_rango():
    with pytest.raises(ValueError):
        encode_o3(40000)


def test_rechaza_tipo_incorrecto():
    with pytest.raises(ValueError):
        decode_o3(bytes([0x01, 0x67, 0x00, 0x2B]))   # 0x67 = temperatura


def test_rechaza_longitud_incorrecta():
    with pytest.raises(ValueError):
        decode_o3(bytes([0x01, 0x02, 0x00]))


# --- flip_bit: valor posicional ---------------------------------------

@pytest.mark.parametrize("k,delta", [
    (0, 1), (1, 2), (2, 4), (3, 8),
    (4, 16), (5, 32), (6, 64), (7, 128),
    (8, 256), (12, 4096),
])
def test_bit_k_vale_dos_a_la_k(k, delta):
    """Sobre valor 0, todos los bits estan apagados: el flip suma."""
    atacada = flip_bit(encode_o3(0), k)
    assert decode_o3(atacada) == delta


def test_endianness_del_flip():
    """El bit 0 esta en el ULTIMO byte, no en el primero.

    Regresion: omitir la inversion big-endian aplicaria el bit 5 donde
    debia ir el bit 13.
    """
    trama = encode_o3(0)
    assert flip_bit(trama, 0)[3] == 0x01     # LSB, byte 3
    assert flip_bit(trama, 8)[2] == 0x01     # MSB, byte 2


def test_bit_15_es_el_de_signo():
    """Analog Input tiene signo. El bit 15 produce un valor negativo.

    No es un fallo: un valor negativo tras el ataque es una lectura
    fisicamente imposible, y por tanto un ataque autodelatado.
    """
    assert decode_o3(flip_bit(encode_o3(0), 15)) == -32768


def test_bit_fuera_de_rango():
    with pytest.raises(ValueError):
        flip_bit(encode_o3(43), 16)


# --- La conmutacion: D2 como asercion ejecutable ----------------------

def test_flip_suma_si_el_bit_estaba_apagado():
    """10 = 0b0000_1010. Bit 5 apagado -> el flip SUMA 32."""
    assert (10 >> 5) & 1 == 0
    assert decode_o3(flip_bit(encode_o3(10), 5)) == 42

