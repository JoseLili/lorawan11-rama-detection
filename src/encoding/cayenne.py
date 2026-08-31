"""Codificacion CayenneLPP.

Formato: [canal][tipo][datos...], datos en BIG-ENDIAN.
Referencia: myDevicesIoT/CayenneLPP.

Nota: CayenneLPP es big-endian, mientras que los campos multi-octeto de
LoRaWAN van little-endian al aire. Son convenciones opuestas dentro del
mismo sistema.
"""

from __future__ import annotations
import struct

LPP_ANALOG_INPUT = 0x02
ANALOG_INPUT_SIZE = 2      # 2 bytes, con signo, big-endian
DATA_OFFSET = 2            # canal(1) + tipo(1)

# D7: se reinterpreta la escala a 1 ppb/LSB. La especificacion define
# 0.01/LSB. Ver docs/02_codificacion.md.
PPB_PER_LSB = 1


def encode_o3(ppb: int, channel: int = 1) -> bytes:
    """Codifica una concentracion de O3 en ppb como trama CayenneLPP.

        43 ppb -> 01 02 00 2B
    """
    if not 0 <= channel <= 255:
        raise ValueError("canal fuera de rango")
    raw = int(round(ppb / PPB_PER_LSB))
    if not -32768 <= raw <= 32767:
        raise ValueError(f"{ppb} ppb excede el rango de Analog Input")
    return struct.pack(">BBh", channel, LPP_ANALOG_INPUT, raw)


def decode_o3(frame: bytes) -> int:
    """Decodifica una trama CayenneLPP a ppb.

    Devuelve el valor tal cual, incluso si es negativo: un valor negativo
    tras un ataque es informacion (lectura fisicamente imposible), no un
    error a ocultar.
    """
    if len(frame) != DATA_OFFSET + ANALOG_INPUT_SIZE:
        raise ValueError(f"longitud inesperada: {len(frame)}")
    _, tipo, raw = struct.unpack(">BBh", frame)
    if tipo != LPP_ANALOG_INPUT:
        raise ValueError(f"tipo inesperado: 0x{tipo:02X}")
    return raw * PPB_PER_LSB


def flip_bit(data: bytes, k: int, offset: int = DATA_OFFSET) -> bytes:
    """Voltea el bit k del VALOR contenido en `data`.

    k se numera sobre el valor de 16 bits: el bit k vale 2^k ppb.
    Como CayenneLPP es big-endian, el bit 0 esta en el ULTIMO byte del
    campo de datos, no en el primero.

        byte_idx = offset + (ANALOG_INPUT_SIZE - 1 - k // 8)

    Omitir esa inversion aplicaria el bit 5 donde debia ir el bit 13.
    Es el error clasico en este punto.
    """
    if not 0 <= k < ANALOG_INPUT_SIZE * 8:
        raise ValueError(f"bit {k} fuera de rango [0, 15]")

    byte_idx = offset + (ANALOG_INPUT_SIZE - 1 - k // 8)
    bit_pos = k % 8

    out = bytearray(data)
    out[byte_idx] ^= (1 << bit_pos)
    return bytes(out)