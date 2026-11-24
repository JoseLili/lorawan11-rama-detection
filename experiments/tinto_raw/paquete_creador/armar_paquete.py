"""Arma la carpeta del paquete para el creador de TINTO (sin README ni ZIP; esos van después).

- 1_originales_rama: 2020O3.xls, 2021O3.xls y 2022O3.xls extraídos byte a byte de los YYRAMA.zip,
  con SHA-256 comprobado contra docs/checksums_2020_2026.txt.
- 2 y 3: copias de las tablas ya exportadas y verificadas por exportar_dataset_tinto.py.
- 4: mapa, escala, figura y armar_tabla.py.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.detect.multianual import leer_checksums  # noqa: E402

EXP = ROOT / 'results/tinto_dataset_para_tintolib_20261124'
AQUI = Path(__file__).resolve().parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(out):
    out.mkdir(parents=True)
    checks = leer_checksums(ROOT / 'docs/checksums_2020_2026.txt')
    d = out / '1_originales_rama'
    d.mkdir()
    for anio in (2020, 2021, 2022):
        z, interno = f'{str(anio)[2:]}RAMA.zip', f'{anio}O3.xls'
        with zipfile.ZipFile(ROOT / 'data/raw' / z) as zf:
            b = zf.read(interno)
        assert sha(b) == checks[f'{z}:{interno}'], interno
        (d / interno).write_bytes(b)
    copias = {
        '2_tabla_que_recibio_tinto': ['ajuste_mapa_2020_2021.csv', 'ajuste_mapa_2020_2021_metadatos.csv'],
        '3_piloto_clasificacion': ['piloto_ajuste.csv', 'piloto_ajuste_metadatos.csv',
                                   'piloto_validacion.csv', 'piloto_validacion_metadatos.csv'],
        '4_nuestro_mapa_y_figura': ['completos_32_mapa.csv', 'completos_escala.csv', 'que_recibe_tinto.png'],
    }
    for carpeta, archivos in copias.items():
        (out / carpeta).mkdir()
        for f in archivos:
            shutil.copy2(EXP / f, out / carpeta / f)
    shutil.copy2(AQUI / 'armar_tabla.py', out / '4_nuestro_mapa_y_figura/armar_tabla.py')
    print(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida', type=Path, required=True)
    a = ap.parse_args()
    if a.salida.exists():
        ap.error('Usa una carpeta nueva.')
    main(a.salida)
