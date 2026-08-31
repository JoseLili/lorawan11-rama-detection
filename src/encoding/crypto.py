"""Cifrado del FRMPayload segun LoRaWAN 1.1, seccion 4.3.3.

Bloque Ai (Figura 17 de la especificacion):

    Tamaño:  1     4        1     4         4       1     1
    Ai:     0x01  4x0x00   Dir  DevAddr   FCntUp   0x00   i

Si = aes128_encrypt(K, Ai)  para i = 1..k,  k = ceil(len(pld)/16)
S  = S1 | S2 | ... | Sk
Cifrado: truncar (pld | pad16) xor S a len(pld) octetos.

La clave K es AppSKey para FPort 1..255 (Tabla 3). El Network Server NO
la posee: esa es la base del modelo de adversario entre NS y AS.
"""

from __future__ import annotations
import struct

from Crypto.Cipher import AES

DIR_UPLINK = 0
DIR_DOWNLINK = 1
BLOCK_SIZE = 16


def build_block_a(i: int, devaddr: int, fcnt: int,
                  direction: int = DIR_UPLINK) -> bytes:
    """Construye el bloque Ai de 16 bytes.

    DevAddr y FCnt van LITTLE-ENDIAN: la especificacion (linea 330)
    establece que el orden de octetos al aire para todos los campos
    multi-octeto es little endian.

    El bloque es COMPLETAMENTE DETERMINISTA. Un observador del trafico
    conoce DevAddr y FCnt, por lo que conoce Ai. La seguridad reposa
    exclusivamente en la clave, no en el secreto del contador.
    """
    if not 1 <= i <= 255:
        raise ValueError("i debe estar en [1, 255]")
    if direction not in (DIR_UPLINK, DIR_DOWNLINK):
        raise ValueError("direction debe ser 0 (up) o 1 (down)")

    return (
        b"\x01"                              # 1 byte
        + b"\x00" * 4                        # 4 bytes reservados
        + bytes([direction])                 # 1 byte
        + struct.pack("<I", devaddr)         # 4 bytes little-endian
        + struct.pack("<I", fcnt)            # 4 bytes little-endian
        + b"\x00"                            # 1 byte
        + bytes([i])                         # 1 byte
    )


def keystream(appskey: bytes, devaddr: int, fcnt: int,
              n_blocks: int, direction: int = DIR_UPLINK) -> bytes:
    """Genera S = S1 | ... | Sk."""
    if len(appskey) != 16:
        raise ValueError("AppSKey debe ser de 16 bytes")

    cipher = AES.new(appskey, AES.MODE_ECB)
    return b"".join(
        cipher.encrypt(build_block_a(i, devaddr, fcnt, direction))
        for i in range(1, n_blocks + 1)
    )


def encrypt(pld: bytes, appskey: bytes, devaddr: int, fcnt: int,
            direction: int = DIR_UPLINK) -> bytes:
    """Cifra el FRMPayload. Truncado a len(pld)."""
    k = (len(pld) + BLOCK_SIZE - 1) // BLOCK_SIZE
    s = keystream(appskey, devaddr, fcnt, k, direction)
    return bytes(a ^ b for a, b in zip(pld, s))


# En modo contador, cifrar y descifrar son la misma operacion.
decrypt = encrypt