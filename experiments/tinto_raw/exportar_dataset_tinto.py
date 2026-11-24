"""Exporta, en formato tabular para TINTOlib, los datos exactos que usó la línea TINTO de noviembre.

1. La tabla con la que se ajustó el mapa TINTO (`representar.py`, brazo «completos»): días completos
   estación-día de 2020–2021, 24 columnas h00..h23 en ppb crudos.
2. Los conjuntos del piloto CNN (`piloto_cnn.py`): originales y alterados ×1.5 o /1.5, clase 0/1.
3. La tabla estación-día completa 2020–2022 con faltantes (NaN), para pruebas propias.

Comprueba que todo coincide con lo guardado (escala, manifiestos y etiquetas del piloto). No entrena.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.detect.multianual import ESTACIONES  # noqa: E402

R = ROOT / 'results/tinto_raw_20261109'
COLS = [f'h{h:02}' for h in range(24)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(out):
    out.mkdir(parents=True)
    source = R / 'auditoria1/o3_raw_ppb.csv'
    df = pd.read_csv(source, index_col=0, parse_dates=True)
    stations = [s for s in ESTACIONES if s not in ['XAL', 'HGM']]          # igual que representar.py
    X = np.concatenate([df[s].to_numpy().reshape(-1, 24) for s in stations])
    dates = pd.DatetimeIndex(np.tile(df.index[::24].to_numpy(), len(stations)))
    names = np.repeat(stations, len(df) // 24)
    complete = np.isfinite(X).all(axis=1)
    meta = pd.DataFrame({'estacion': names, 'fecha': dates.strftime('%Y-%m-%d'), 'anio': dates.year,
                         'horas_con_dato': np.isfinite(X).sum(axis=1)})

    # 1. Tabla de ajuste del mapa: días completos 2020–2021.
    fit = (dates.year < 2022) & complete
    tabla = pd.DataFrame(X[fit], columns=COLS)
    sc = MinMaxScaler(clip=False).fit(tabla.to_numpy())
    escala = pd.read_csv(R / 'representacion1/completos_escala.csv', float_precision='round_trip')
    np.testing.assert_array_equal(sc.scale_, escala.scale.to_numpy())
    np.testing.assert_array_equal(sc.min_, escala.offset.to_numpy())
    tabla.assign(clase=0).to_csv(out / 'ajuste_mapa_2020_2021.csv', index=False)
    meta[fit].to_csv(out / 'ajuste_mapa_2020_2021_metadatos.csv', index=False)

    # 2. Piloto CNN: mismas bases, signos y etiquetas que piloto_cnn.py.
    piloto = {}
    for split, n, tag in [('ajuste', 1024, 1), ('validacion', 256, 2)]:
        rng = np.random.default_rng([42, 1109, tag])
        eligible = np.flatnonzero(complete & ((dates.year < 2022) if tag == 1 else (dates.year == 2022)))
        ids = np.sort(rng.choice(eligible, n, replace=False))
        sign = rng.choice([-1, 1], n)
        a = X[ids]
        b = np.where(sign[:, None] > 0, a * 1.5, a / 1.5)
        man = pd.read_csv(R / f'piloto_cnn1/{split}_manifiesto.csv')
        np.testing.assert_array_equal(man.base_id.to_numpy(), np.tile(ids, 2))
        np.testing.assert_array_equal(man.signo.to_numpy(), np.concatenate([np.zeros(n, int), sign]))
        y = np.repeat([0, 1], n)
        np.testing.assert_array_equal(np.load(R / f'piloto_cnn1/{split}_y.npy'), y)
        datos = pd.DataFrame(np.concatenate([a, b]), columns=COLS).assign(clase=y)
        datos.to_csv(out / f'piloto_{split}.csv', index=False)
        pd.DataFrame({'base_id': np.tile(ids, 2), 'estacion': np.tile(names[ids], 2),
                      'fecha': np.tile(dates[ids].strftime('%Y-%m-%d'), 2), 'clase': y,
                      'alteracion': np.concatenate([np.full(n, 'original'),
                                                    np.where(sign > 0, 'x1.5', '/1.5')])}
                     ).to_csv(out / f'piloto_{split}_metadatos.csv', index=False)
        piloto[split] = dict(filas=2 * n, bases=n, positivas=n)

    # 3. Todas las estación-días 2020–2022, con NaN donde no hubo medición.
    pd.concat([meta, pd.DataFrame(X, columns=COLS)], axis=1).to_csv(out / 'o3_estacion_dia_2020_2022.csv', index=False)

    for f in ['completos_32_mapa.csv', 'completos_escala.csv']:
        (out / f).write_bytes((R / 'representacion1' / f).read_bytes())
    info = dict(fuente=str(source.relative_to(ROOT)), sha256_fuente=sha(source), estaciones=stations,
                ajuste_mapa=dict(filas=int(fit.sum())), piloto=piloto, todas=dict(filas=len(X), completas=int(complete.sum())),
                comprobado='escala MinMax y manifiestos/etiquetas del piloto idénticos a los guardados',
                sha256={p.name: sha(p) for p in sorted(out.glob('*.csv'))})
    (out / 'verificacion.json').write_text(json.dumps(info, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: info[k] for k in ['ajuste_mapa', 'piloto', 'todas']}, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida', type=Path, required=True)
    a = ap.parse_args()
    if a.salida.exists():
        ap.error('Usa una carpeta nueva.')
    main(a.salida)
