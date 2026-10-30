"""TINTO T2: mapa TINTO-PCA 64 × 64 para las 2 352 entradas de red (24 h × 98 columnas).

Mismo procedimiento que T1 (`experimento_hora_compacta.py` + `prototipos_sin_colisiones.py`):
MinMax sin recorte, TINTOlib 1.3.1 PCA sin difuminado y asignación única de mínimo costo.
Se ajusta solo con la muestra de 20 000 ventanas de 2020–2021 de `preparar_t2.py`.
Correr en un entorno aparte con TINTOlib (requirements-aula.txt); no entrena nada.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from sklearn.preprocessing import MinMaxScaler
from TINTOlib.tinto import TINTO

LADO = 64


def main(paquete):
    meta = json.loads((paquete / 'meta.json').read_text())
    X = np.load(paquete / 'X_muestra_red.npy').astype(np.float64)
    names = [f'{c}_d{k}' for k in range(-23, 1) for c in meta['columnas_98']]  # orden hora → columna
    assert X.shape == (20000, 24 * 98) == (20000, len(names))
    scaler = MinMaxScaler(clip=False).fit(X)
    constant = scaler.data_min_ == scaler.data_max_
    escala = pd.DataFrame(dict(feature=names, minimo=scaler.data_min_, maximo=scaler.data_max_,
                               scale=scaler.scale_, offset=scaler.min_))
    escala.to_csv(paquete / 'escalador_red.csv', index=False)
    train = pd.DataFrame(scaler.transform(X), columns=names)
    train['etiqueta'] = 0  # etiqueta ficticia: las reales nunca entran al ajuste del mapa
    model = TINTO(transformer=None, problem='classification', pixels=LADO, algorithm='PCA', blur=False,
                  zoom=1, format='npy', random_seed=42)
    model.fit(train)
    xy = model.obtain_coord.copy()
    np.save(paquete / 'coordenadas_PCA_red.npy', xy)
    original = model._get_features_mapping()[['row', 'column']].to_numpy(dtype=int)
    centered = xy - xy.mean(axis=0)
    radius = math.ceil(np.sqrt((centered ** 2).sum(axis=1)).max())
    target = np.abs((centered - np.array([-radius, radius])) / (2 * radius)) * (LADO - 1)
    np.testing.assert_array_equal(np.round(target), original)  # misma convención que TINTO 1.3.1
    grid = np.stack(np.meshgrid(np.arange(LADO), np.arange(LADO), indexing='ij'), axis=-1).reshape(-1, 2)
    rows, cols = linear_sum_assignment(cdist(target, grid, metric='sqeuclidean'))
    np.testing.assert_array_equal(rows, np.arange(len(names)))
    coords = grid[cols]
    assert len(np.unique(coords, axis=0)) == len(names)
    pd.DataFrame(dict(feature=names, row=coords[:, 0], column=coords[:, 1], row_TINTO=original[:, 0],
                      column_TINTO=original[:, 1])).to_csv(paquete / 'mapa_unico_red_64.csv', index=False)
    colisiones = len(names) - len(np.unique(original, axis=0))
    info = dict(lado=LADO, entradas=len(names), columnas_constantes_en_muestra=int(constant.sum()),
                posiciones_TINTO_original_con_choque=int(colisiones),
                desplazamiento_medio_pixeles=float(np.linalg.norm(coords - original, axis=1).mean()),
                sha256_muestra=hashlib.sha256((paquete / 'X_muestra_red.npy').read_bytes()).hexdigest())
    (paquete / 'mapa_red.json').write_text(json.dumps(info, indent=1) + '\n')
    print(info)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--paquete', type=Path, required=True)
    main(ap.parse_args().paquete)
