"""Inferencia duplicada del PARAAD congelado; calibración sólo en 2023 limpio.

Requiere máscara común exportada por los comparadores (CSV dia × 31 objetivos,
0/1). No deduce esa máscara a partir de PARAAD ni modifica modelos existentes.
El examen exige --examen-registrado y umbrales previamente congelados.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Importar primero establece CPU y determinismo antes de cargar TensorFlow.
from entrenar_paraad import RAIZ, SAL, guardar, sha
import numpy as np
import pandas as pd
import tensorflow as tf
from src.detect import paraad as p
from src.detect.evaluacion_red import umbral_falsas_alarmas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--modelo', type=Path, default=SAL / 'definitivo')
    ap.add_argument('--matriz', type=Path, required=True)
    ap.add_argument('--comunes', type=Path, required=True)
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--umbrales', type=Path)
    ap.add_argument('--examen-registrado', action='store_true')
    args = ap.parse_args()
    c = json.loads((args.modelo / 'congelado.json').read_text())
    if not c['igual'] or sha(args.modelo / 'modelo_r1.keras') != c['sha256_modelo']:
        raise ValueError('modelo no coincide con el congelado reproducible')
    if sha(args.modelo / 'escala.csv') != c['sha256_escala']:
        raise ValueError('escala distinta de la congelada')
    if c['fuentes']['src/detect/paraad.py'] != sha(RAIZ / 'src/detect/paraad.py'):
        raise ValueError('implementación distinta de la entrenada')
    if c['tensorflow'] != tf.__version__ or c['keras'] != tf.keras.__version__:
        raise ValueError('entorno distinto; verificar reproducibilidad antes de continuar')
    # Leer primero sólo fechas para no inspeccionar valores de un examen no habilitado.
    idx = pd.DatetimeIndex(pd.read_csv(args.matriz, usecols=['timestamp'], parse_dates=['timestamp']).timestamp)
    cal = bool(len(idx) and (idx.year == 2023).all())
    if not cal and not (args.examen_registrado and args.umbrales and len(idx)
                        and idx.year.min() >= 2024 and idx.year.max() <= 2026):
        raise ValueError('sólo 2023 limpio; el examen requiere registro y umbrales congelados')
    if cal and args.umbrales:
        raise ValueError('la calibración crea umbrales; no recibe umbrales de examen')
    matriz = pd.read_csv(args.matriz, index_col='timestamp', parse_dates=['timestamp'])
    if cal:
        if 'anomalia_red' not in matriz or matriz.anomalia_red.fillna(1).astype(bool).any():
            raise ValueError('calibración requiere matriz 2023 limpia comprobable')
    x = matriz[[f'{s}_valor' for s in p.SENSORES]].set_axis(p.SENSORES, axis=1)
    for s in p.SENSORES:
        mascara = matriz[f'{s}_mascara']
        if not mascara.isin([0, 1]).all():
            raise ValueError('máscara horaria no binaria')
        x[s] = x[s].where(mascara == 1)
    comunes = pd.read_csv(args.comunes, index_col='dia', parse_dates=['dia'])
    if not comunes.isin([0, 1]).all().all():
        raise ValueError('máscara común debe contener sólo 0/1')
    comunes = comunes.astype(bool)
    escala = pd.read_csv(args.modelo / 'escala.csv', index_col='estacion', float_precision='round_trip')
    z, m, dias = p.bloques(x, escala)
    anteriores = None
    for _ in range(2):
        tf.keras.backend.clear_session()
        modelo = tf.keras.models.load_model(args.modelo / 'modelo_r1.keras', compile=False)
        s = p.exigir_comunes(p.puntajes(z, m, p.reconstruir(modelo, z), dias), comunes)
        if anteriores is not None:
            pd.testing.assert_frame_equal(anteriores, s, check_exact=True)
        anteriores = s
    if not comunes.to_numpy().any():
        raise ValueError('universo común vacío')
    base = dict(origen='modelo cargado de disco; no entrenado', igual=True,
                sha256_modelo=c['sha256_modelo'], sha256_escala=c['sha256_escala'],
                sha256_matriz=sha(args.matriz), sha256_comunes=sha(args.comunes),
                estacion_dias=int(comunes.to_numpy().sum()), calibracion=cal)
    if cal:
        v = s.to_numpy()[comunes.to_numpy()]
        u = {nombre: umbral_falsas_alarmas(v, fa) for nombre, fa in [('p99', .01), ('p99.9', .001)]}
    else:
        previo = json.loads(args.umbrales.read_text())
        if not previo['calibracion'] or previo['sha256_modelo'] != c['sha256_modelo'] or previo['sha256_escala'] != c['sha256_escala']:
            raise ValueError('umbrales no corresponden a este modelo y escala')
        u = previo['umbrales']
        base['sha256_calibracion'] = sha(args.umbrales)
    args.salida.mkdir(parents=True, exist_ok=False)
    s.rename_axis('dia').to_csv(args.salida / 'puntajes.csv')
    for nombre, umbral in u.items():
        (s > umbral).astype(float).where(comunes).rename_axis('dia').to_csv(args.salida / f'alertas_{nombre}.csv')
    guardar(args.salida / 'registro.json', {**base, 'umbrales': u})


if __name__ == '__main__':
    main()
