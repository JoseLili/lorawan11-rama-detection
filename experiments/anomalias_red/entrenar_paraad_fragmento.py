"""Una repetición independiente; reutiliza el entrenador congelado sin modificarlo."""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import entrenar_paraad as e  # fija CPU/hilos antes de TensorFlow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dropout', type=float, required=True, choices=[.3, .5])
    ap.add_argument('--repeticion', type=int, required=True, choices=[1, 2])
    args = ap.parse_args()
    esperado = json.loads((e.RAIZ / 'esperado.json').read_text())
    actual = dict(python=platform.python_version(), tensorflow=e.tf.__version__,
                  keras=e.tf.keras.__version__, numpy=e.np.__version__, maquina=platform.machine(),
                  cpu=platform.processor())
    for k, v in actual.items():
        if esperado[k] != v:
            raise ValueError(f'entorno diferente: {k}: {v} != {esperado[k]}')
    for archivo, h in esperado['fuentes'].items():
        if e.sha(e.RAIZ / archivo) != h:
            raise ValueError(f'fuente diferente: {archivo}')
    if e.tf.config.get_visible_devices('GPU'):
        raise ValueError('sólo CPU')
    x = e.leer_ajuste(e.RAIZ / 'data/processed/paraad_2020_2022.parquet')
    h = hashlib.sha256(e.pd.util.hash_pandas_object(x, index=True).values.tobytes()).hexdigest()
    if h != esperado['sha256_tabla_2020_2022']:
        raise ValueError('datos diferentes')
    escala = e.p.ajustar_escala(x.loc[:'2021'])
    z, m, _, _ = e.datos(x.loc[:'2021'], escala)
    zv, mv, _, _ = e.datos(x.loc['2022'], escala)
    out = e.RAIZ / 'results/anomalias_red_v1/revision20/seleccion'
    out.mkdir(parents=True, exist_ok=True)
    e.guardar(out / f'entrada_r{args.repeticion}.json', esperado)
    e.repeticion(out / f'dropout{args.dropout}_r{args.repeticion}', args.dropout,
                 z, m, e.EPOCAS, (zv, mv))


if __name__ == '__main__':
    main()
