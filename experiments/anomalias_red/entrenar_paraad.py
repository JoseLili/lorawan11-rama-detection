"""Revisión 20: auditoría por defecto; selección y definitivo explícitos, dos veces.

No lee 2023–2026. Consultar docs/runbook_paraad_revision20.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_DETERMINISTIC_OPS'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np
import pandas as pd
import tensorflow as tf
from src.detect import paraad as p
from src.detect.lstm import fijar_semilla

SAL = RAIZ / 'results/anomalias_red_v1/revision20'
DROPOUTS = (0.1, 0.3, 0.5)
EPOCAS, BATCH = 500, 256


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def guardar(path, datos):
    path = Path(path)
    temporal = path.with_name(path.name + '.tmp')
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporal.replace(path)


def leer_ajuste(path):
    x = pd.read_parquet(path, columns=list(p.SENSORES), filters=[
        ('timestamp', '>=', pd.Timestamp('2020-01-01')),
        ('timestamp', '<', pd.Timestamp('2023-01-01'))])
    if x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise ValueError('índice duplicado o desordenado')
    if len(x) and (x.index.min().year < 2020 or x.index.max().year > 2022):
        raise ValueError('el lector devolvió fechas fuera del ajuste')
    return x.reindex(pd.date_range('2020-01-01', '2022-12-31 23:00', freq='h', name='timestamp'))


def entrenar(modelo, z, m, epocas, validacion=None, progreso=None):
    """Lotes ordenados sin tf.data; MSE por bloque, media global de validación."""
    y = p.objetivos_perdida(z, m)
    historia = []
    for e in range(1, epocas + 1):
        modelo.reset_metrics()
        for i in range(0, len(z), BATCH):
            loss = float(modelo.train_on_batch(z[i:i+BATCH], y[i:i+BATCH]))
        fila = {'epoca': e, 'loss': loss}
        if validacion is not None:
            zv, mv = validacion
            rec = p.reconstruir(modelo, zv)
            errores = ((zv.astype('float64') - rec) ** 2 * mv).sum(axis=(1, 2)) / mv.sum(axis=(1, 2))
            fila['val_loss'] = float(errores.mean())
        if not all(np.isfinite(v) for v in fila.values()):
            raise ValueError('pérdida no finita; no se acepta esta ejecución')
        historia.append(fila)
        if e == 1 or e % 25 == 0 or e == epocas:
            print(fila, flush=True)
            if progreso is not None:
                guardar(progreso, {**fila, 'epocas_objetivo': epocas})
    return pd.DataFrame(historia)


def nuevo(dropout):
    tf.keras.backend.clear_session()
    fijar_semilla(42)
    return p.construir_modelo(dropout)


def datos(x, escala):
    z, m, dias = p.bloques(x, escala)
    ok = m.any(axis=(1, 2))
    if not ok.any():
        raise ValueError('ningún bloque con observaciones')
    return z[ok], m[ok], dias[ok], int((~ok).sum())


def iguales(a, b):
    for x, y in zip(a.get_weights(), b.get_weights(), strict=True):
        np.testing.assert_array_equal(x, y)


def repeticion(carpeta, dropout, z, m, epocas, validacion=None):
    """Recupera unidades completas; una unidad interrumpida se repite desde semilla.

    No reanuda a mitad de época: así no depende de restaurar el RNG de Dropout.
    El manifiesto de fase valida código/entorno/datos antes de llamar aquí.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    listo = carpeta / 'completo.json'
    if listo.exists():
        meta = json.loads(listo.read_text())
        if meta['dropout'] != dropout or meta['epocas'] != epocas:
            raise ValueError('checkpoint de otra configuración')
        for nombre, esperado in meta['archivos'].items():
            if sha(carpeta / nombre) != esperado:
                raise ValueError(f'checkpoint corrupto: {nombre}')
        print(f'Recuperando repetición completa: {carpeta.name}', flush=True)
        modelo = tf.keras.models.load_model(carpeta / 'modelo.keras')
        hist = pd.read_csv(carpeta / 'historia.csv', float_precision='round_trip')
        rec = np.load(carpeta / 'reconstruccion.npy')
        return modelo, hist, rec
    modelo = nuevo(dropout)
    fijar_semilla(42)
    hist = entrenar(modelo, z, m, epocas, validacion, carpeta / 'progreso.json')
    entrada = validacion[0] if validacion is not None else z
    rec = p.reconstruir(modelo, entrada)
    modelo.save(carpeta / 'modelo.keras')
    cargado = tf.keras.models.load_model(carpeta / 'modelo.keras')
    np.testing.assert_array_equal(rec, p.reconstruir(cargado, entrada))
    hist.to_csv(carpeta / 'historia.csv', index=False)
    np.save(carpeta / 'reconstruccion.npy', rec)
    guardar(listo, dict(dropout=dropout, epocas=epocas, archivos={
        nombre: sha(carpeta / nombre) for nombre in ('modelo.keras', 'historia.csv', 'reconstruccion.npy')}))
    return modelo, hist, rec


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fase', choices=['auditar', 'seleccion', 'definitivo', 'smoke', 'benchmark'], default='auditar')
    ap.add_argument('--datos', type=Path, default=RAIZ / 'data/processed/o3_2020_2026_ancho.parquet')
    ap.add_argument('--salida', type=Path, default=SAL)
    ap.add_argument('--reanudar', action='store_true', help='reutilizar sólo repeticiones completas verificadas')
    args = ap.parse_args()
    if tf.config.get_visible_devices('GPU'):
        raise RuntimeError('se requiere CPU')
    out = args.salida / args.fase
    out.mkdir(parents=True, exist_ok=args.reanudar)
    entorno = dict(python=platform.python_version(), tensorflow=tf.__version__, numpy=np.__version__,
                   keras=tf.keras.__version__, maquina=platform.machine(), cpu=platform.processor(),
                   semilla=42, batch=BATCH, sensores=p.SENSORES, origen='recién entrenado',
                   fuentes={str(f.relative_to(RAIZ)): sha(f) for f in
                            (Path(__file__), RAIZ / 'src/detect/paraad.py', RAIZ / 'src/detect/lstm.py')})
    if args.fase == 'smoke':
        rng = np.random.default_rng(42)
        z = rng.normal(size=(4, 32, 24)).astype('float32')
        m = rng.random(z.shape) > 0.15
        z[~m] = 0
        anteriores = None
        for r in (1, 2):
            modelo = nuevo(0.1)
            fijar_semilla(42)
            hist = entrenar(modelo, z, m, 1, (z, m))
            rec = p.reconstruir(modelo, z)
            modelo.save(out / f'modelo_{r}.keras')
            cargado = tf.keras.models.load_model(out / f'modelo_{r}.keras')
            np.testing.assert_array_equal(rec, p.reconstruir(cargado, z))
            if anteriores is not None:
                iguales(anteriores[0], modelo)
                np.testing.assert_array_equal(anteriores[1], rec)
                pd.testing.assert_frame_equal(anteriores[2], hist, check_exact=True)
            anteriores = modelo, rec, hist
        guardar(out / 'verificacion.json', {**entorno, 'igual': True, 'datos': 'sintéticos, 4 días', 'epocas': 1})
        return

    x = leer_ajuste(args.datos)
    entorno['sha256_tabla_2020_2022'] = hashlib.sha256(pd.util.hash_pandas_object(x, index=True).values.tobytes()).hexdigest()
    manifiesto = out / 'entrada.json'
    # JSON normaliza tuplas a listas antes de comparar.
    entrada = json.loads(json.dumps(entorno))
    if manifiesto.exists():
        if json.loads(manifiesto.read_text()) != entrada:
            raise ValueError('cambiaron entorno, código o datos; no se reanuda')
    else:
        if args.reanudar and any(out.iterdir()):
            raise ValueError('carpeta previa sin manifiesto; no se reanuda')
        guardar(manifiesto, entrada)
    n = x.notna().resample('D').sum()
    cobertura = [dict(anio=int(y), dias=len(g), completos=int(g.eq(24).all(axis=1).sum()),
                       minimo23=int(g.ge(23).all(axis=1).sum())) for y, g in n.groupby(n.index.year)]
    guardar(out / 'cobertura.json', cobertura)
    if args.fase == 'auditar':
        escala = p.ajustar_escala(x.loc[:'2021'])
        z, m, dias = p.bloques(x, escala)
        guardar(out / 'auditoria.json', {**entorno, 'origen': 'sin modelo ni entrenamiento',
                                        'forma': list(z.shape), 'bloques_vacios': int((~m.any(axis=(1, 2))).sum())})
        print(cobertura)
        return

    if args.fase == 'benchmark':
        escala = p.ajustar_escala(x.loc[:'2021'])
        z, m, _, _ = datos(x.loc[:'2021'], escala)
        modelo = nuevo(0.1)
        inicio = time.perf_counter()
        fijar_semilla(42)
        entrenar(modelo, z, m, 5)
        segundos = time.perf_counter() - inicio
        guardar(out / 'tiempo.json', {**entorno, 'epocas': 5, 'dias': len(z), 'segundos': segundos,
                                      'nota': 'incluye compilación; sin validación, no estima desempeño'})
        print(f'Benchmark: {segundos:.2f} s para 5 épocas, incluida compilación', flush=True)
        return

    if args.fase == 'seleccion':
        escala = p.ajustar_escala(x.loc[:'2021'])
        z, m, _, vacios_tr = datos(x.loc[:'2021'], escala)
        zv, mv, _, vacios_va = datos(x.loc['2022'], escala)
        escala.to_csv(out / 'escala.csv', index_label='estacion')
        opciones = []
        for d in DROPOUTS:
            anterior = None
            for r in (1, 2):
                modelo, hist, rec = repeticion(out / f'dropout{d}_r{r}', d, z, m, EPOCAS, (zv, mv))
                hist.to_csv(out / f'historia_dropout{d}_r{r}.csv', index=False)
                if anterior is not None:
                    iguales(anterior[0], modelo)
                    np.testing.assert_array_equal(anterior[1], rec)
                    pd.testing.assert_frame_equal(anterior[2], hist, check_exact=True)
                anterior = modelo, rec, hist
            mejor = hist.loc[hist.val_loss.idxmin()]
            opciones.append(dict(dropout=d, epocas=int(mejor.epoca), val_loss=float(mejor.val_loss)))
        elegido = min(opciones, key=lambda c: (c['val_loss'], c['dropout'], c['epocas']))
        guardar(out / 'seleccion.json', {**entorno, 'igual': True, 'elegido': elegido, 'candidatos': opciones,
                                       'vacios_ajuste': vacios_tr, 'vacios_validacion': vacios_va})
        return

    seleccion = args.salida / 'seleccion/seleccion.json'
    conf = json.loads(seleccion.read_text())
    for clave in ('fuentes', 'tensorflow', 'keras', 'numpy', 'sha256_tabla_2020_2022'):
        if conf[clave] != entorno[clave]:
            raise ValueError(f'cambió {clave} desde la selección; no continuar')
    if not conf['igual']:
        raise ValueError('selección no reproducible')
    escala = p.ajustar_escala(x)
    escala.to_csv(out / 'escala.csv', index_label='estacion')
    z, m, dias, vacios = datos(x, escala)
    anterior = None
    for r in (1, 2):
        modelo, hist, rec = repeticion(out / f'repeticion_r{r}', conf['elegido']['dropout'],
                                       z, m, conf['elegido']['epocas'])
        modelo.save(out / f'modelo_r{r}.keras')
        hist.to_csv(out / f'historia_r{r}.csv', index=False)
        cargado = tf.keras.models.load_model(out / f'modelo_r{r}.keras')
        np.testing.assert_array_equal(rec, p.reconstruir(cargado, z))
        s = p.puntajes(z, m, rec, dias)
        if anterior is not None:
            iguales(anterior[0], modelo)
            pd.testing.assert_frame_equal(anterior[1], s, check_exact=True)
            pd.testing.assert_frame_equal(anterior[2], hist, check_exact=True)
        anterior = modelo, s, hist
    guardar(out / 'congelado.json', {**entorno, 'igual': True, 'elegido': conf['elegido'],
                                   'vacios': vacios, 'sha256_seleccion': sha(seleccion),
                                   'sha256_modelo': sha(out / 'modelo_r1.keras'),
                                   'sha256_escala': sha(out / 'escala.csv')})


if __name__ == '__main__':
    main()
