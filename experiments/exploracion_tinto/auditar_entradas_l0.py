"""Audita X de selección L0 sin entrenar ni leer datos fuera de 2020–2022.

Guarda muestra de 32 ventanas por estación/calendario, manifiesto COMPLETO de
las ventanas L0 de ajuste y estadísticas de todas sus entradas (por bloques).
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'experiments/anomalias_red'))
import numpy as np
import pandas as pd
from src.detect import evaluacion_red as ev, lstm_local as ll, estacion_dia as ed
from entrenar_lstm_local import ejemplos
from entrenar_lstm_sup import leer, parametros_vecinas, SELECCION
from diagnostico_variantes_2022 import posiciones
from generar_planes import alterables_v4


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ejecutar(out):
    out.mkdir(parents=True)
    clean, clean_sha = leer('limpia_2020_2022')
    assert clean.index.min().year == 2020 and clean.index.max().year == 2022
    _, sigma = ev.normalizacion(clean)  # Particularidad histórica de L0.
    saved = pd.read_csv(ROOT/'results/lstm_v4_multianual_v1/normalizacion.csv', index_col='estacion')
    np.testing.assert_allclose(sigma, saved.loc[sigma.index, 'desv_definitiva'], rtol=1e-9)
    par = parametros_vecinas('a14', clean.loc[SELECCION[0]:SELECCION[1]], sigma, 'media')
    stations = ev.estaciones_de(clean)
    targets = alterables_v4()
    pos = posiciones(clean.index, *SELECCION)
    dictionary = []
    roles = ['obj', 'v1', 'v2', 'v3', 'v4']
    for lag in range(23, -1, -1):
        for role in roles:
            for kind in ['rel', 'mascara', 'vecinas']:
                dictionary.append(dict(columna=len(dictionary), nombre=f'lag{lag:02d}_{role}_{kind}',
                    desfase_horas=-lag, rol=role, tipo=kind,
                    escala='binaria 0/1' if kind == 'mascara' else 'adimensional; escala histórica L0'))
        for kind in ['hora_sin', 'hora_cos']:
            dictionary.append(dict(columna=len(dictionary), nombre=f'lag{lag:02d}_{kind}',
                desfase_horas=-lag, rol='tiempo', tipo=kind, escala='adimensional [-1,1]'))
    d = pd.DataFrame(dictionary)
    assert len(d) == 408 and d.nombre.is_unique
    d.to_csv(out/'diccionario_408.csv', index=False)
    cols = d.nombre.tolist()
    minima, maxima = np.full(408, np.inf), np.full(408, -np.inf)
    sums, squares = np.zeros(408), np.zeros(408)
    h_full, h_y = hashlib.sha256(), hashlib.sha256()
    samples, ys, sample_meta, counts = [], [], [], []
    total = positives = missing_target = 0
    sources = {'limpia_2020_2022': clean_sha, 'geografia': sha(ROOT/'results/inventario_multianual/estaciones_geografia.csv'),
               'normalizacion_v4':sha(ROOT/'results/lstm_v4_multianual_v1/normalizacion.csv')}
    mask_indices = d.index[d.tipo == 'mascara'].to_numpy()
    manifest_path = out/'manifiesto_entrenamiento.csv.gz'
    # mtime fijo permite comparar archivos comprimidos byte a byte.
    with open(manifest_path, 'wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed:
            import io
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as stream:
                header = True
                for number in range(1, 21):
                    calendar = f'entrenamiento_{number:02d}'
                    x, sources[calendar] = leer(f'{calendar}_d50')
                    assert x.index.equals(clean.index)
                    Y = ed.etiquetas_por_hora(x, targets)
                    F = ev.entradas_de('vecinas', x, None, sigma, par)
                    # Ruta original de entrenamiento, por calendario completo.
                    Xref, yref = ejemplos(F, Y, pos, 8, 'seleccion', number, stations, par.vecinas, targets)
                    flat = Xref.reshape(-1, 408)
                    assert Xref.shape[1:] == (24, 17) and np.isfinite(flat).all()
                    assert np.isin(flat[:, mask_indices], [0, 1]).all()
                    np.testing.assert_allclose(Xref[:, :, 15]**2 + Xref[:, :, 16]**2, 1, atol=2e-7)
                    minima = np.minimum(minima, flat.min(axis=0))
                    maxima = np.maximum(maxima, flat.max(axis=0))
                    # Reducción float64 por columnas sin guardar el dataset completo.
                    for chunk in np.array_split(flat, 16):
                        z = chunk.astype(np.float64)
                        sums += z.sum(axis=0)
                        squares += np.square(z).sum(axis=0)
                    h_full.update(np.ascontiguousarray(Xref).tobytes())
                    h_y.update(np.ascontiguousarray(yref).tobytes())
                    offset = 0
                    for j, target in enumerate(targets):
                        p = ll.muestra(pos, 8, 'seleccion', number, j)
                        n = len(p)
                        # 32 índices de la muestra L0 ya seleccionada, sin nuevo sorteo.
                        take = np.linspace(0, n-1, min(32, n), dtype=int)
                        ps = p[take]
                        local = [target] + par.vecinas[target]
                        nst = len(stations)
                        # Reconstrucción explícita independiente del helper de ventanas.
                        ix = []
                        for station in local:
                            k = stations.index(station)
                            ix.extend([k, nst+k, 2*nst+2+k])
                        ix += [2*nst, 2*nst+1]
                        assert ix == ll.indices_locales(stations, par.vecinas, target)
                        direct = np.stack([F[t-23:t+1, ix] for t in ps])
                        np.testing.assert_array_equal(direct, Xref[offset+take])
                        np.testing.assert_array_equal(yref[offset:offset+n], Y[target].to_numpy(np.float32)[p])
                        times = x.index[p]
                        assert ((times >= pd.Timestamp(SELECCION[0])) & (times <= pd.Timestamp(SELECCION[1]))).all()
                        observed = x[f'{target}_mascara'].to_numpy()[p].astype(bool)
                        meta = pd.DataFrame({'indice_entrenamiento':total+offset+np.arange(n),
                            'calendario':calendar,'objetivo':target,'hora_final':times,
                            'hora_inicio': x.index[p-23], 'posicion_matriz':p,
                            'etiqueta':yref[offset:offset+n].astype(int), 'objetivo_observado':observed.astype(int)})
                        meta.to_csv(stream, index=False, header=header)
                        header = False
                        sm = meta.iloc[take].copy()
                        sm['fila_muestra'] = np.arange(len(sample_meta)*32, len(sample_meta)*32+len(take))
                        samples.append(direct)
                        ys.append(yref[offset+take])
                        sample_meta.append(sm)
                        missing_target += int((~observed).sum())
                        offset += n
                    assert offset == len(Xref)
                    counts.append(dict(calendario=calendar, ventanas=len(Xref), positivas=int(yref.sum())))
                    total += len(Xref)
                    positives += int(yref.sum())
                    print(f'{calendar}: {len(Xref)} ventanas cotejadas; acumulado {total}', flush=True)
                    del Xref, yref, flat, F, x
    X = np.concatenate(samples)
    y = np.concatenate(ys)
    meta = pd.concat(sample_meta, ignore_index=True)
    assert np.array_equal(meta.fila_muestra.to_numpy(), np.arange(len(X)))
    np.save(out/'X_muestra.npy', X)
    np.save(out/'y_muestra.npy', y)
    meta.to_csv(out/'manifiesto_muestra.csv', index=False)
    pd.DataFrame(X.reshape(-1,408), columns=cols).to_csv(out/'tabla_408_muestra.csv', index=False)
    stats = d.copy()
    stats['minimo'] = minima
    stats['maximo'] = maxima
    stats['media'] = sums/total
    stats['desviacion'] = np.sqrt(np.maximum(squares/total-(sums/total)**2, 0))
    stats['constante'] = minima == maxima
    stats.to_csv(out/'auditoria_columnas.csv', index=False)
    # Duplicados evaluados solo en la muestra: no inferir igualdad universal.
    groups = {}
    for i, name in enumerate(cols):
        key = hashlib.sha256(np.ascontiguousarray(X.reshape(-1,408)[:,i]).tobytes()).hexdigest()
        groups.setdefault(key, []).append(name)
    duplicates = [v for v in groups.values() if len(v)>1]
    (out/'duplicados_solo_muestra.json').write_text(json.dumps(duplicates, indent=2)+'\n')
    (out/'vecinas_y_escalas.json').write_text(json.dumps({'objetivos':targets, 'estaciones':stations,
        'vecinas':par.vecinas, 'sigma_2020_2022':sigma.to_dict(), 'escala_a14_2020_2021':par.escala.to_dict()},indent=2)+'\n')
    config = json.loads((ROOT/'results/anomalias_red_v1/lstm_local_examen/c20/d50/configuracion.json').read_text())
    assert total == config['seleccion']['ventanas_entrenamiento']
    report = {'alcance':'X de selección L0 completo; solo 2020–2022; sin entrenamiento ni inferencia',
        'ventanas_auditadas':total, 'positivas':positives, 'positivas_pct':100*positives/total,
        'muestra_guardada':list(X.shape), 'columnas_aplanadas':408,
        'constantes_en_entrenamiento_completo':stats.loc[stats.constante,'nombre'].tolist(),
        'grupos_duplicados_solo_muestra':len(duplicates), 'objetivo_faltante_en_t':missing_target,
        'nota_faltantes':'Se conserva muestreo original de entrenamiento L0; en evaluación se enmascaran horas sin dato propio.',
        'sha256_X_entrenamiento_en_orden':h_full.hexdigest(), 'sha256_y_entrenamiento_en_orden':h_y.hexdigest(),
        'calendarios':counts, 'sha256_fuentes':sources,
        'sha256_codigo':{p:sha(ROOT/p) for p in ['experiments/exploracion_tinto/auditar_entradas_l0.py',
            'experiments/anomalias_red/entrenar_lstm_local.py','src/detect/lstm_local.py','src/detect/evaluacion_red.py']},
        'versiones':{p:importlib.metadata.version(p) for p in ['numpy','pandas','tensorflow','scikit-learn']}}
    (out/'verificaciones.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    paths=[p for p in sorted(out.iterdir()) if p.is_file()]
    (out/'hashes.json').write_text(json.dumps({p.name:sha(p) for p in paths},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['calendarios','sha256_fuentes','sha256_codigo']},indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',required=True,type=Path)
    a=p.parse_args()
    if a.salida.exists():
        p.error('Usa una carpeta nueva para preservar las corridas anteriores.')
    ejecutar(a.salida)
