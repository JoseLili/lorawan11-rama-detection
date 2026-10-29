"""Ejercicios con TINTOlib real y datos inventados; no entrena un detector."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from TINTOlib.tinto import TINTO


def imagenes(folder):
    return [np.load(p) for p in sorted(folder.rglob('*.npy'))]


def ejecutar(out):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    cols = [f'F{i+1}' for i in range(8)]
    # Extremos explícitos: MinMaxScaler será identidad en estos ejemplos.
    train = pd.DataFrame(np.vstack([np.zeros(8), np.ones(8), rng.uniform(0, 1, (62, 8))]), columns=cols)
    train['etiqueta'] = 0
    probes = pd.DataFrame([[.25]*8, [.25, .25, .75, .25, .25, .25, .25, .25], [.25]*8], columns=cols)
    probes['etiqueta'] = [0, 0, 1]
    train.to_csv(out/'ajuste_inventado.csv', index=False)
    probes.to_csv(out/'observaciones.csv', index=False)
    arrays = {}
    maps = {}
    for nombre, blur in [('sin_difuminado', False), ('con_difuminado', True)]:
        # Instancias nuevas, incluido el escalador, para cada ajuste independiente.
        model = TINTO(problem='classification', transformer=MinMaxScaler(),
                      algorithm='PCA', pixels=32, blur=blur, distance=1, steps=2,
                      option='maximum', format='npy', random_seed=42)
        model.fit(train)
        model.transform(probes, str(out/nombre))
        mapping = model._get_features_mapping().copy()
        mapping.to_csv(out/f'mapa_{nombre}.csv', index=False)
        arrays[nombre] = imagenes(out/nombre)
        maps[nombre] = mapping
        assert len(arrays[nombre]) == 3
        assert not mapping.duplicated(['row', 'column']).any(), 'Hay colisiones de características'
        assert np.array_equal(arrays[nombre][0], arrays[nombre][2]), 'La etiqueta cambió la imagen'
        # Ajustar con etiquetas distintas tampoco debe cambiar el mapa ni el escalado.
        other = train.copy()
        other['etiqueta'] = rng.integers(0, 2, len(other))
        control = TINTO(problem='classification', transformer=MinMaxScaler(),
                        algorithm='PCA', pixels=32, blur=blur, distance=1, steps=2,
                        option='maximum', format='npy', random_seed=42)
        control.fit(other)
        control.transform(probes, str(out/f'control_etiquetas_{nombre}'))
        for a, b in zip(arrays[nombre], imagenes(out/f'control_etiquetas_{nombre}')):
            assert np.array_equal(a, b)
    a, b, _ = arrays['sin_difuminado']
    changed = np.argwhere(a != b)
    assert changed.shape == (1, 2), changed
    # Confirmar orientación de las coordenadas exportadas contra los píxeles reales.
    row = maps['sin_difuminado'].query("feature == 'F3'").iloc[0]
    assert tuple(changed[0]) == (int(row['row']), int(row['column']))
    assert a[tuple(changed[0])] == .25 and b[tuple(changed[0])] == .75
    assert np.count_nonzero(a) == 8
    assert np.count_nonzero(arrays['con_difuminado'][0] != arrays['con_difuminado'][1]) > 1
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    for i, nombre in enumerate(arrays):
        original, modified, _ = arrays[nombre]
        for j, (img, title) in enumerate([(original, 'Original: todas en 0.25'), (modified, 'Solo F3 cambia a 0.75'), (modified-original, 'Diferencia: modificada − original')]):
            ax = axes[i, j]
            im = ax.imshow(img, origin='upper', cmap='magma', vmin=0, vmax=1, interpolation='nearest')
            ax.set_title(title, fontsize=11)
            ax.set_xlabel('Columna del píxel (0–31)')
            ax.set_ylabel(('Sin difuminado' if i == 0 else 'Con difuminado')+'\nFila del píxel (0–31)')
            if i == 0 and j < 2:
                for m in maps[nombre].itertuples():
                    ax.annotate(m.feature, (m.column, m.row), xytext=(3, 3), textcoords='offset points', color='cyan', fontsize=8)
        fig.colorbar(im, ax=list(axes[i]), label='Valor numérico de la matriz (escala fija 0–1)')
    fig.suptitle('TINTOlib real · 8 características inventadas · PCA · imágenes de 32 × 32', fontsize=14)
    fig.savefig(out/'explicacion.png', dpi=160)
    plt.close(fig)
    checks = {
        'etiqueta_no_altera_imagen': True,
        'etiquetas_de_ajuste_no_alteran_imagen': True,
        'caracteristicas': 8,
        'pixeles_ocupados_sin_difuminado': int(np.count_nonzero(a)),
        'pixeles_modificados_sin_difuminado': len(changed),
        'posicion_F3_fila_columna': changed[0].tolist(),
        'pixeles_modificados_con_difuminado': int(np.count_nonzero(arrays['con_difuminado'][0] != arrays['con_difuminado'][1])),
        'origen': 'Transformación PCA recién ajustada sobre 64 filas inventadas; sin CNN ni detector',
        'versiones': {p: importlib.metadata.version(p) for p in ['TINTOlib','numpy','pandas','scikit-learn','matplotlib']},
        'python': platform.python_version(),
        'huellas_matrices': {k: [hashlib.sha256(a.tobytes()).hexdigest() for a in v] for k, v in arrays.items()},
    }
    (out/'verificaciones.json').write_text(json.dumps(checks, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(checks, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, required=True, help='Carpeta nueva para esta corrida')
    args = parser.parse_args()
    if args.salida.exists():
        parser.error('La carpeta de salida ya existe; elige otra para conservar los resultados.')
    ejecutar(args.salida)
