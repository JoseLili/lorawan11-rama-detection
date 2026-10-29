"""Experimento 1: rasterización TINTO sin difuminado, con fit solo en ajuste.

Ejecutar con TINTOlib 1.3.1 en entorno separado. No entrena un detector.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tempfile
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from threadpoolctl import threadpool_limits
from TINTOlib.tinto import TINTO

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT/'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1'
SYN = ROOT/'results/exploracion_tinto_2022/ventana_aula_20261028/final1'
SIZES = (32, 64, 128, 256)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guardar_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def datos():
    synth = pd.read_csv(SYN/'ajuste_inventado.csv').drop(columns='etiqueta')
    normal = pd.read_csv(SYN/'tabla_normal.csv', index_col=0).to_numpy().reshape(-1)
    dictionary = pd.read_csv(AUD/'diccionario_408.csv')
    X = np.load(AUD/'X_muestra.npy', allow_pickle=False).reshape(-1, 408)
    meta = pd.read_csv(AUD/'manifiesto_muestra.csv')
    assert X.shape == (19840, 408)
    assert meta.hora_final.str[:4].isin(['2020', '2021']).all()
    base_id = int(meta.index[(meta.etiqueta == 0) & (meta.objetivo_observado == 1)][0])
    return [dict(nombre='sintetica_120', X=synth.to_numpy(dtype=np.float64),
                 columnas=synth.columns.tolist(), base=normal, mascaras=[], base_id='normal inventada'),
            dict(nombre='L0_408', X=X.astype(np.float64), columnas=dictionary.nombre.tolist(),
                 base=X[base_id].astype(np.float64), mascaras=dictionary.index[dictionary.tipo == 'mascara'].tolist(),
                 base_id=base_id)]


def ejecutar(out):
    out.mkdir(parents=True)
    # Registro escrito ANTES de ajustar PCA o medir colisiones.
    config = dict(resoluciones=list(SIZES), algoritmo='PCA', semilla=42, blur=False, zoom=1,
        escalado='MinMax por columna, una vez por tabla de ajuste; clip=False; flotantes float64',
        ajuste_L0='Las 19 840 ventanas auditadas de 2020–2021; NO todo Xtr; sin validación',
        perturbacion='Una columna por vez: +/-0.125 escalado; máscaras binarias se invierten',
        criterio='Menor resolución sin colisiones de columnas no constantes y sin perturbaciones ocultas',
        detector='ninguno; solo transformación recién ajustada',
        sha256_fuentes={str(p.relative_to(ROOT)):sha(p) for p in [AUD/'X_muestra.npy',
            AUD/'manifiesto_muestra.csv', AUD/'diccionario_408.csv', SYN/'ajuste_inventado.csv',
            SYN/'tabla_normal.csv']}, sha256_codigo=sha(__file__),
        versiones={p:importlib.metadata.version(p) for p in ['TINTOlib','numpy','pandas','scikit-learn','matplotlib']})
    guardar_json(out/'configuracion.json', config)
    records, timings = [], []
    plots = {}
    for dataset in datos():
        name, X, columns = dataset['nombre'], dataset['X'], dataset['columnas']
        folder = out/name
        folder.mkdir()
        n = X.shape[1]
        scaler = MinMaxScaler(clip=False).fit(X)
        scaled = scaler.transform(X)
        constant = scaler.data_min_ == scaler.data_max_
        assert not constant.any(), 'Las dos tablas predefinidas deben tener variación en todas sus columnas'
        base = scaler.transform(dataset['base'][None])[0]
        pd.DataFrame(dict(feature=columns, minimo=scaler.data_min_, maximo=scaler.data_max_,
                          scale=scaler.scale_, offset=scaler.min_)).to_csv(folder/'escalador.csv', index=False)
        train = pd.DataFrame(scaled, columns=columns)
        train['etiqueta'] = 0  # Etiqueta ficticia constante; las etiquetas reales nunca entran al fit.
        probes = np.tile(base, (n+1, 1))
        for j in range(n):
            probes[j+1, j] += .125 if base[j] <= .5 else -.125
            if j in dataset['mascaras']:
                probes[j+1, j] = 1-base[j]
        probe_df = pd.DataFrame(probes, columns=columns)
        probe_df['etiqueta'] = 0
        # Ya escaladas externamente: transformer=None evita un segundo escalado.
        continuous = None
        images = []
        for pixels in SIZES:
            model = TINTO(transformer=None, problem='classification', pixels=pixels,
                          algorithm='PCA', blur=False, zoom=1, format='npy', random_seed=42)
            started = time.perf_counter()
            model.fit(train)
            fit_seconds = time.perf_counter()-started
            if continuous is None:
                continuous = model.obtain_coord.copy()
                np.save(folder/'coordenadas_PCA.npy', continuous)
            else:
                np.testing.assert_array_equal(continuous, model.obtain_coord)
            mapping = model._get_features_mapping().copy()
            coords = mapping[['row','column']].to_numpy(dtype=int)
            groups = {}
            for j, rc in enumerate(coords):
                groups.setdefault(tuple(rc), []).append(j)
            owners = {rc:ids[-1] for rc,ids in groups.items()}
            hidden = np.array([owners[tuple(rc)] != j for j,rc in enumerate(coords)])
            mapping['grupo_tamano'] = [len(groups[tuple(rc)]) for rc in coords]
            mapping['sobrescrita'] = hidden
            mapping['ultima_escritora'] = [columns[owners[tuple(rc)]] for rc in coords]
            mapping.to_csv(folder/f'mapa_{pixels}.csv', index=False)
            diffs, matrix_hashes = [], []
            with tempfile.TemporaryDirectory(prefix='tinto-resolucion-') as temp:
                started = time.perf_counter()
                model.transform(probe_df, temp)
                seconds = time.perf_counter()-started
                paths = sorted((Path(temp)/'00').glob('*.npy'))
                assert len(paths) == n+1
                original = np.load(paths[0], allow_pickle=False)
                expected = np.zeros((pixels,pixels))
                for j, rc in enumerate(coords):
                    expected[tuple(rc)] = base[j]
                np.testing.assert_array_equal(original, expected)
                assert original.shape == (pixels,pixels) and original.dtype == np.float64
                np.save(folder/f'imagen_base_{pixels}.npy', original)
                images.append((pixels, original))
                for j, path in enumerate(paths[1:]):
                    img = np.load(path, allow_pickle=False)
                    changed = int(np.count_nonzero(original != img))
                    assert changed == (0 if hidden[j] else 1), (name,pixels,j,changed)
                    if changed:
                        assert img[tuple(coords[j])] == probes[j+1,j]
                    diffs.append(changed)
                    matrix_hashes.append(hashlib.sha256(img.tobytes()).hexdigest())
                npy_bytes = paths[0].stat().st_size
            # Recuperación a escala MinMax: leer cada característica de su píxel.
            # La igualdad anterior verifica la regla de última escritura con TINTO real.
            owner_indices = np.array([owners[tuple(rc)] for rc in coords])
            error = scaled[:, owner_indices]-scaled
            rmse = float(np.sqrt(np.mean(error**2)))
            mae = float(np.mean(np.abs(error)))
            pd.DataFrame(dict(feature=columns, pixeles_modificados=diffs,
                              cambio_oculto=np.array(diffs)==0)).to_csv(folder/f'perturbaciones_{pixels}.csv',index=False)
            guardar_json(folder/f'hashes_perturbaciones_{pixels}.json', matrix_hashes)
            records.append(dict(tabla=name, lado=pixels, caracteristicas=n,
                posiciones_distintas=len(groups), grupos_colision=sum(len(v)>1 for v in groups.values()),
                caracteristicas_en_colision=sum(len(v) for v in groups.values() if len(v)>1),
                caracteristicas_sobrescritas=int(hidden.sum()), cambios_ocultos=int((np.array(diffs)==0).sum()),
                cambios_ocultos_pct=100*float(hidden.mean()), rmse_reconstruccion=rmse, mae_reconstruccion=mae,
                bytes_matriz=original.nbytes, bytes_archivo_npy=npy_bytes,
                cumple_criterio=bool(not hidden.any()),
                sha256_imagen_base=hashlib.sha256(original.tobytes()).hexdigest()))
            timings.append(dict(tabla=name,lado=pixels,segundos_fit=fit_seconds,
                segundos_transformar_y_escribir=seconds,imagenes=n+1,
                milisegundos_por_imagen=1000*seconds/(n+1)))
            print(f'{name} {pixels}×{pixels}: {len(groups)}/{n} posiciones; {hidden.sum()} cambios ocultos',flush=True)
        plots[name] = images
        guardar_json(folder/'detalle_ajuste.json',dict(filas_ajuste=len(X),base_id=dataset['base_id'],
            columnas_constantes=[], base_fuera_0_1=int(((base<0)|(base>1)).sum()),
            rango_ajuste=[float(scaled.min()),float(scaled.max())],mapa_continuo_igual_entre_resoluciones=True))
    result = pd.DataFrame(records)
    result.to_csv(out/'resoluciones.csv',index=False)
    pd.DataFrame(timings).to_csv(out/'tiempos.csv',index=False)
    decisions = {}
    for name in result.tabla.unique():
        candidates = result[(result.tabla==name)&result.cumple_criterio]
        decisions[name] = int(candidates.lado.min()) if len(candidates) else None
    guardar_json(out/'decision.json',dict(resolucion_elegible_por_tabla=decisions,
        criterio=config['criterio'],advertencia='Conservación en esta muestra y mapa; no mide detección ni garantiza conservación en un futuro mapa definitivo.'))
    fig, axes = plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for name, data in result.groupby('tabla',sort=False):
        axes[0].plot(data.lado,data.cambios_ocultos,'o-',label=name)
    axes[0].set(xlabel='Lado de la imagen (píxeles)',ylabel='Características cuyo cambio queda oculto',title='Pérdida por sobrescritura · sin difuminado')
    axes[0].legend()
    axes[0].set_xticks(SIZES)
    axes[1].plot(SIZES,[p*p*8/1024 for p in SIZES],'o-',color='purple')
    axes[1].set(xlabel='Lado de la imagen (píxeles)',ylabel='Memoria por matriz float64 (KiB)',title='Coste numérico por imagen, sin cabecera NPY')
    axes[1].set_xticks(SIZES)
    fig.suptitle('TINTO · mismo escalado y PCA en cada tabla · solo cambia la resolución')
    fig.savefig(out/'resolucion_y_perdida.png',dpi=160)
    plt.close(fig)
    fig, axes=plt.subplots(1,4,figsize=(13,3.7),layout='constrained')
    for ax,(pixels,img) in zip(axes,plots['L0_408']):
        im=ax.imshow(img,vmin=0,vmax=1,cmap='magma',interpolation='nearest')
        row=result[(result.tabla=='L0_408')&(result.lado==pixels)].iloc[0]
        ax.set(title=f'{pixels} × {pixels}\n{int(row.posiciones_distintas)}/408 posiciones',xlabel='Columna del píxel',ylabel='Fila del píxel')
    fig.colorbar(im,ax=list(axes),label='Valor escalado (MinMax)')
    fig.suptitle('Misma ventana L0 en cuatro resoluciones · PCA ajustado en 19 840 ventanas de 2020–2021')
    fig.savefig(out/'imagenes_L0.png',dpi=160)
    plt.close(fig)
    guardar_json(out/'hashes_numericos.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
        if p.is_file() and p.suffix in ['.npy','.csv','.json'] and p.name!='tiempos.csv'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,required=True)
    args=p.parse_args()
    if args.salida.exists():
        p.error('Usa una carpeta nueva para conservar las corridas anteriores.')
    with threadpool_limits(limits=1):
        ejecutar(args.salida)
