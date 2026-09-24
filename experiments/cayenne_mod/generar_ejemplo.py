"""Genera dos payloads didácticos con el codificador actual de la tesis."""

from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.encoding.cayenne import decode_o3, encode_o3, flip_bit


def main():
    original = encode_o3(160)
    modificado = flip_bit(original, 5)

    # Referencias independientes: comprueban bytes, posición y decodificación.
    assert original == bytes.fromhex('01 02 00 a0')
    assert modificado == bytes.fromhex('01 02 00 80')
    assert decode_o3(original) == 160
    assert decode_o3(modificado) == 128
    assert sum((a ^ b).bit_count() for a, b in zip(original, modificado)) == 1
    assert flip_bit(modificado, 5) == original

    carpeta = Path(__file__).resolve().parent / 'samples'
    muestras = {
        carpeta / 'o3_160ppb.bin': original,
        carpeta / 'o3_160ppb_flip_bit5.bin': modificado,
    }
    # Si editaste una muestra, conservarla para que puedas investigar el cambio.
    for ruta, contenido in muestras.items():
        if ruta.exists() and ruta.read_bytes() != contenido:
            raise FileExistsError(f'Muestra modificada; no se sobrescribe: {ruta}')
    carpeta.mkdir(parents=True, exist_ok=True)
    for ruta, contenido in muestras.items():
        if not ruta.exists():
            with ruta.open('xb') as archivo:
                archivo.write(contenido)
        print(f'{ruta.name}: {contenido.hex(" ")} -> {decode_o3(contenido)} ppb')

    print('Valor original: 00000000 10100000 (160)')
    print('Mascara bit 5:  00000000 00100000 (32)')
    print('Valor con XOR: 00000000 10000000 (128)')
    print('Comprobado: un solo bit cambia y un segundo flip restaura el original.')


if __name__ == '__main__':
    main()
