"""Ventana didáctica de 24 h × 5 sensores; no reproduce las 17 entradas de L0."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import FunctionTransformer
from TINTOlib.tinto import TINTO

SENSORES = ['Objetivo', 'Vecina 1', 'Vecina 2', 'Vecina 3', 'Vecina 4']


def ejecutar(out):
    out.mkdir(parents=True)
    rng = np.random.default_rng(42)
    horas = np.arange(24)

    def dia():
        perfil = 30 + rng.uniform(12, 22)*np.sin(2*np.pi*(horas-rng.uniform(7, 9))/24)
        return np.clip(perfil[:, None] + rng.normal(0, 2, (24, 5)) + rng.normal(0, 2, (1, 5)), 1, 65)

    # Ajuste y ejemplos proceden de llamadas distintas. Solo datos inventados.
    ajuste = np.stack([dia() for _ in range(128)])
    normal = dia()
    alterada = normal.copy()
    alterada[:, 0] *= 1.5  # episodio ilustrativo de un día completo, +50 %
    assert np.array_equal(normal[:, 1:], alterada[:, 1:])
    assert np.count_nonzero(normal != alterada) == 24
    cols = [f'h{h:02d}_{s.replace(" ", "_")}' for h in horas for s in SENSORES]
    train = pd.DataFrame(ajuste.reshape(128, -1), columns=cols)
    train['etiqueta'] = 0
    examples = pd.DataFrame(np.stack([normal, alterada]).reshape(2, -1), columns=cols)
    examples['etiqueta'] = [0, 1]
    train.to_csv(out/'ajuste_inventado.csv', index=False)
    examples.to_csv(out/'entrada_tinto.csv', index=False)
    for name, values in [('normal', normal), ('alterada', alterada)]:
        pd.DataFrame(values, columns=SENSORES).rename_axis('hora').to_csv(out/f'tabla_{name}.csv')
    arrays = {}
    checks = {}
    for name, blur in [('sin_difuminado', False), ('con_difuminado', True)]:
        # Escala física fija: 100 ppb -> 1, independiente de las observaciones.
        model = TINTO(transformer=FunctionTransformer(lambda x: x/100),
                      pixels=64, algorithm='PCA', blur=blur, distance=1, steps=2,
                      option='maximum', format='npy', random_seed=42)
        model.fit(train)
        model.transform(examples, str(out/name))
        paths = [out/name/'00'/'000000.npy', out/name/'01'/'000001.npy']
        a, b = [np.load(p) for p in paths]
        arrays[name] = (a, b)
        mapping = model._get_features_mapping()
        mapping.to_csv(out/f'mapa_{name}.csv', index=False)
        assert a.shape == b.shape == (64, 64)
        assert np.isfinite(a).all() and np.isfinite(b).all()
        assert (b >= a - 1e-12).all()
        assert np.any(a != b)
        if name == 'sin_difuminado':
            # La ubicación exportada debe reproducir la asignación incluso si hay colisiones.
            expected = np.zeros((64, 64))
            for m, value in zip(mapping.itertuples(), normal.reshape(-1)/100):
                expected[int(m.row), int(m.column)] = value
            np.testing.assert_array_equal(a, expected)
        checks[name] = {
            'caracteristicas': 120,
            'posiciones_distintas': len(mapping.drop_duplicates(['row', 'column'])),
            'caracteristicas_que_comparten_posicion': int(mapping.duplicated(['row', 'column'], keep=False).sum()),
            'pixeles_modificados': int(np.count_nonzero(a != b)),
            'sha256': [hashlib.sha256(v.tobytes()).hexdigest() for v in (a, b)],
        }
    # Figura temporal: trazas e imágenes matriciales con escalas compartidas.
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout='constrained')
    for i, sensor in enumerate(SENSORES):
        axes[0].plot(horas, normal[:, i], label=sensor, linewidth=1.3)
    axes[0].plot(horas, alterada[:, 0], '--', color='black', linewidth=2, label='Objetivo × 1.5')
    axes[0].set(xlabel='Hora del día', ylabel='Ozono inventado (ppb)', title='Solo alteramos el objetivo')
    axes[0].legend(fontsize=7)
    for ax, data, title in zip(axes[1:], [normal, alterada], ['Ventana normal', 'Objetivo +50 % todo el día']):
        im = ax.imshow(data, aspect='auto', vmin=0, vmax=100, cmap='magma', interpolation='nearest')
        ax.set_xticks(range(5), SENSORES, rotation=30, ha='right')
        ax.set(xlabel='Sensor', ylabel='Hora del día (0–23)', title=title)
    fig.colorbar(im, ax=list(axes[1:]), label='Ozono inventado (ppb), escala fija')
    fig.suptitle('Paso 1 · La misma ventana de 24 horas, antes y después de alterar el objetivo')
    fig.savefig(out/'01_ventana_temporal.png', dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    for i, (name, (a, b)) in enumerate(arrays.items()):
        for j, (data, title) in enumerate([(a, 'Normal'), (b, 'Objetivo +50 %'), (b-a, 'Diferencia: alterada − normal')]):
            im = axes[i, j].imshow(data, vmin=0, vmax=1, cmap='magma', interpolation='nearest')
            axes[i, j].set(title=title, xlabel='Columna del píxel (0–63)', ylabel=('Sin difuminado' if i == 0 else 'Con difuminado')+'\nFila del píxel (0–63)')
        fig.colorbar(im, ax=list(axes[i]), label='Intensidad: ppb / 100')
    fig.suptitle('Paso 2 · TINTOlib real: 120 características → imagen de 64 × 64\nMapa PCA ajustado con 128 días inventados distintos; mismo mapa para ambos casos')
    fig.savefig(out/'02_imagenes_tinto.png', dpi=150)
    plt.close(fig)
    report = {
        'origen': 'PCA recién ajustado con datos inventados; sin detector ni CNN',
        'semilla': 42, 'ajuste_dias': 128, 'horas': 24, 'sensores': 5,
        'alteracion': 'Objetivo multiplicado por 1.5 en las 24 horas',
        'celdas_de_entrada_modificadas': 24, 'vecinas_identicas': True,
        'escala': 'División fija por 100; sin escalado individual por imagen',
        'versiones': {p: importlib.metadata.version(p) for p in ['TINTOlib','numpy','pandas','scikit-learn','matplotlib']},
        'verificaciones': checks,
    }
    (out/'verificaciones.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida', required=True, type=Path)
    args = p.parse_args()
    if args.salida.exists():
        p.error('Usa una carpeta nueva para conservar las corridas anteriores.')
    ejecutar(args.salida)
