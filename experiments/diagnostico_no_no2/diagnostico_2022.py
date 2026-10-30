"""Diagnóstico exploratorio: ¿el NO y el NO2 de la propia estación explican el error del V4?

Idea del 2026-10-15, fuera de todo protocolo: sólo sirve para decidir si vale la pena
dedicarle tiempo a un modelo con más variables. No es un detector ni un resultado de la
tesis.

Qué hace, por cada uno de los 31 objetivos del V4:
    1. Carga el modelo de SELECCIÓN del V4 (seleccion/modelo_seleccion.keras), entrenado
       sólo con 2020–2021. No entrena ni modifica nada del V4.
    2. Predice la validación 2022 con las mismas entradas de su fase 1 y comprueba que el
       MAE reproduce el val_mae guardado en historia_seleccion.csv.
    3. Ajusta dos modelos auxiliares (HistGradientBoosting) que intentan predecir el
       residuo, con validación cruzada dejando fuera un mes de 2022 a la vez:
         A: sólo la hora del día (sin, cos)  -> lo que el V4 ya veía;
         B: la hora + NO y NO2 de la propia estación a la misma hora.
       La diferencia entre A y B es lo que aportan el NO y el NO2.
No usa 2023 (calibración) ni 2024–2026.

Criterio fijado ANTES de correrlo (mediana de los 28 principales, reducción del p95 de
|residuo| de B frente a A): >= 10 % vale la pena explorarlo; 3–10 % marginal; < 3 % no.

Uso (desde la raíz del repo):

    .venv/bin/python experiments/diagnostico_no_no2/diagnostico_2022.py [--salida DIR]

Escribe en results/diagnostico_no_no2_2022/ (o DIR): por_estacion.csv, residuos_2022.csv.gz
y resumen.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import multianual as m  # noqa: E402
from src.ingest.rama import load_wide, to_long  # noqa: E402

V4 = RAIZ / 'results/lstm_v4_multianual_v1'
SAL = RAIZ / 'results/diagnostico_no_no2_2022'
TARDE = range(12, 18)          # 12–17 h, donde se concentra la anomalía proporcional
CRITERIO = dict(vale_la_pena=10.0, marginal=3.0)


def cargar_2022(contaminante: str) -> pd.DataFrame:
    """Formato ancho (timestamp × estación) de 2022, verificando el SHA-256 del .xls."""
    checksums = m.leer_checksums(RAIZ / 'docs/checksums_2020_2026.txt')
    interno = f'2022{contaminante}.xls'
    with zipfile.ZipFile(RAIZ / 'data/raw/22RAMA.zip') as zf:
        b = zf.read(interno)
    if m.sha256(b) != checksums.get(f'22RAMA.zip:{interno}'):
        raise ValueError(f'{interno} no coincide con docs/checksums_2020_2026.txt')
    largo = to_long(load_wide(BytesIO(b)), contaminante)
    return largo.pivot(index='timestamp', columns='station', values='value')


def residuos_seleccion(ctx, objetivo: str) -> pd.DataFrame:
    """Residuo del modelo de selección en 2022, con las entradas de su fase 1."""
    from tensorflow import keras
    carpeta = V4 / 'estaciones' / objetivo
    ini = ctx['inicial']
    perfil = m.perfil_causal(ctx['valores'][objetivo])
    t = em.tensores(ini['entradas'], ctx['valores'], objetivo, ini['mu'], ini['sigma'], perfil,
                    ('validacion',))
    modelo = keras.models.load_model(carpeta / 'seleccion/modelo_seleccion.keras', compile=False)
    pred = em.predecir(modelo, t)

    cfg = json.loads((carpeta / 'configuracion.json').read_text())
    hist = pd.read_csv(carpeta / 'seleccion/historia_seleccion.csv', index_col=0)
    esperado = float(hist.loc[cfg['epoca_E'], 'val_mae'])
    obtenido = float(pred['residuo_ppb'].abs().mean())
    if abs(obtenido - esperado) > 1e-3:
        raise RuntimeError(f'{objetivo}: MAE 2022 {obtenido:.5f} no reproduce val_mae {esperado:.5f}')
    return pred[['timestamp', 'residuo_ppb']].assign(objetivo=objetivo, val_mae_guardado=esperado)


def fuera_de_mes(X: np.ndarray, y: np.ndarray, mes: np.ndarray) -> np.ndarray:
    """Predicción de cada mes con un modelo ajustado en los otros 11 (sin ver ese mes)."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from src.detect.lstm import fijar_semilla
    out = np.full(len(y), np.nan)
    for k in np.unique(mes):
        prueba = mes == k
        # Una columna sin al menos dos valores distintos en el ajuste no aporta (p. ej. NO2
        # ausente todo el año) y HistGradientBoosting falla con ella: se omite en ese pliegue.
        cols = [j for j in range(X.shape[1])
                if np.unique(X[~prueba, j][~np.isnan(X[~prueba, j])]).size >= 2]
        fijar_semilla(42)
        aux = HistGradientBoostingRegressor(random_state=42, early_stopping=False)
        aux.fit(X[~prueba][:, cols], y[~prueba])
        out[prueba] = aux.predict(X[prueba][:, cols])
    return out


def p95(x) -> float:
    return float(np.percentile(np.abs(x), 95, method='linear'))


def metricas(objetivo: str, d: pd.DataFrame) -> dict:
    r, ra, rb = d['residuo_ppb'], d['residuo_ppb'] - d['aux_A'], d['residuo_ppb'] - d['aux_B']
    tarde = d['timestamp'].dt.hour.isin(TARDE)
    con = d['no2'].notna() | d['no'].notna()
    fila = dict(objetivo=objetivo, n=len(d), cobertura_no=d['no'].notna().mean(),
                cobertura_no2=d['no2'].notna().mean(),
                mae_v4=r.abs().mean(), mae_A=ra.abs().mean(), mae_B=rb.abs().mean(),
                p95_v4=p95(r), p95_A=p95(ra), p95_B=p95(rb),
                mae_tarde_A=ra[tarde].abs().mean(), mae_tarde_B=rb[tarde].abs().mean(),
                p95_con_dato_A=p95(ra[con]) if con.any() else np.nan,
                p95_con_dato_B=p95(rb[con]) if con.any() else np.nan)
    for q in ('mae', 'p95', 'mae_tarde'):
        fila[f'reduccion_{q}_pct'] = 100 * (1 - fila[f'{q}_B'] / fila[f'{q}_A'])
    fila['reduccion_p95_con_dato_pct'] = 100 * (1 - fila['p95_con_dato_B'] / fila['p95_con_dato_A'])
    return fila


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SAL)
    salida = ap.parse_args().salida
    salida.mkdir(parents=True, exist_ok=True)

    clases = pd.read_csv(V4 / 'estado_objetivos.csv').set_index('objetivo')['clasificacion']
    objetivos = sorted(p.parent.name for p in (V4 / 'estaciones').glob('*/configuracion.json'))
    if len(objetivos) != 31:
        raise RuntimeError(f'se esperaban 31 objetivos con modelo V4, hay {len(objetivos)}')

    ctx = em.contexto(RAIZ)
    no, no2 = cargar_2022('NO'), cargar_2022('NO2')

    filas, todos = [], []
    for obj in objetivos:
        d = residuos_seleccion(ctx, obj)
        d['no'] = no[obj].reindex(d['timestamp']).to_numpy() if obj in no else np.nan
        d['no2'] = no2[obj].reindex(d['timestamp']).to_numpy() if obj in no2 else np.nan
        h = d['timestamp'].dt.hour.to_numpy()
        hora = np.column_stack([np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)])
        y, mes = d['residuo_ppb'].to_numpy(), d['timestamp'].dt.month.to_numpy()
        d['aux_A'] = fuera_de_mes(hora, y, mes)
        d['aux_B'] = fuera_de_mes(np.column_stack([hora, d[['no', 'no2']].to_numpy()]), y, mes)
        fila = metricas(obj, d)
        fila['clasificacion'] = clases[obj]
        filas.append(fila)
        todos.append(d)
        print(f"{obj}: MAE {fila['mae_v4']:.2f} | p95 A {fila['p95_A']:.2f} -> B {fila['p95_B']:.2f} "
              f"({fila['reduccion_p95_pct']:+.1f} %) | NO2 {fila['cobertura_no2']:.0%}", flush=True)

    tabla = pd.DataFrame(filas)
    tabla.round(4).to_csv(salida / 'por_estacion.csv', index=False)
    pd.concat(todos).round(4).to_csv(salida / 'residuos_2022.csv.gz', index=False)

    principal = tabla[tabla['clasificacion'] == 'principal']
    med = float(principal['reduccion_p95_pct'].median())
    veredicto = ('vale la pena explorarlo' if med >= CRITERIO['vale_la_pena'] else
                 'marginal' if med >= CRITERIO['marginal'] else 'no vale la pena')
    resumen = dict(
        fecha='2026-10-15', tipo='diagnóstico exploratorio, fuera de protocolo',
        origen_modelos='V4 cargado de disco: seleccion/modelo_seleccion.keras (ajuste 2020–2021)',
        modelos_auxiliares='HistGradientBoostingRegressor recién ajustado, random_state=42, '
                           'validación dejando fuera un mes de 2022',
        n_principales=len(principal), criterio_pct=CRITERIO,
        mediana_principales=dict(
            reduccion_p95_pct=med,
            reduccion_mae_pct=float(principal['reduccion_mae_pct'].median()),
            reduccion_mae_tarde_pct=float(principal['reduccion_mae_tarde_pct'].median()),
            reduccion_p95_con_dato_pct=float(principal['reduccion_p95_con_dato_pct'].median()),
            p95_v4=float(principal['p95_v4'].median()), p95_A=float(principal['p95_A'].median()),
            p95_B=float(principal['p95_B'].median())),
        veredicto=veredicto,
    )
    (salida / 'resumen.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
