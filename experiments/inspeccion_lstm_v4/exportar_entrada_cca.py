"""Exporta una entrada real del piloto V4 sin entrenar ni ejecutar el modelo.

Ejecutar desde el repo: .venv/bin/python experiments/inspeccion_lstm_v4/exportar_entrada_cca.py
Se reutiliza el preprocesamiento persistido del notebook 07, no el de la red.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.detect.windows import construir_ventanas
from src.ingest.rama import load_wide, to_long

SALIDA = RAIZ / 'results/muestra_entrada_lstm_v4_cca'
OBJETIVO = pd.Timestamp('2025-10-21 12:00:00')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def construir_exportacion():
    datos = RAIZ / 'data/raw/2025O3.xls'
    preprocesamiento = RAIZ / 'results/preprocesamiento_modelo4_cca.npz'
    metadatos = json.loads((RAIZ / 'results/metadatos_modelo4_cca.json').read_text())
    assert sha256(datos) == metadatos['dataset_sha256']
    assert sha256(RAIZ / 'results/modelo4_lstm.keras') == metadatos['modelo_sha256']
    matriz = (to_long(load_wide(datos), 'O3')
              .pivot(index='timestamp', columns='station', values='value')
              .sort_index().dropna(axis=1, how='all'))
    with np.load(preprocesamiento, allow_pickle=False) as pre:
        np.testing.assert_array_equal(matriz.index.to_numpy(), pre['timestamps'])
        assert matriz.columns.tolist() == pre['estaciones'].tolist()
        corte, ventana = int(pre['corte']), int(pre['ventana'])
        assert ventana == 24 and int(pre['dias_perfil']) == 14
        vecinas = pre['vecinas'].tolist()
        mu = pd.Series(pre['mu'].copy(), index=vecinas)
        sigma = pd.Series(pre['sigma'].copy(), index=vecinas)
        perfil = pd.Series(pre['perfil'].copy(), index=matriz.index)
    assert len(vecinas) == 32 and 'CCA' not in vecinas
    test = matriz.iloc[corte:]
    X, y, tiempos, bases, _, _ = construir_ventanas(
        test, 'CCA', ventana=ventana, mu=mu, sigma=sigma,
        perfil=perfil.iloc[corte:], predecir_desviacion=True)
    coincidencias = np.flatnonzero(tiempos == OBJETIVO.to_datetime64())
    assert len(coincidencias) == 1
    i = int(coincidencias[0])
    bloque = matriz.loc[OBJETIVO-pd.Timedelta(hours=24):OBJETIVO-pd.Timedelta(hours=1)]
    assert bloque.index.equals(pd.date_range(OBJETIVO-pd.Timedelta(hours=24), periods=24, freq='h'))
    assert X[i].shape == (24, 66) and np.isfinite(X[i]).all()
    np.testing.assert_array_equal(X[i, :, 32:64], bloque[vecinas].notna().to_numpy())
    valores = ((bloque[vecinas]-mu)/sigma).fillna(0).to_numpy(dtype=np.float32)
    np.testing.assert_array_equal(X[i, :, :32], valores)

    columnas = ([f'{s}_normalizado' for s in vecinas]
                + [f'{s}_disponible' for s in vecinas] + ['seno_hora', 'coseno_hora'])
    # No índice ni timestamp: estos 66 números son exactamente los canales de X.
    entrada = pd.DataFrame(X[i], columns=columnas)
    historia = matriz.loc[(matriz.index < OBJETIVO) & (matriz.index.hour == OBJETIVO.hour), 'CCA'].tail(14)
    np.testing.assert_allclose(historia.mean(), bases[i], rtol=0, atol=1e-5)
    np.testing.assert_allclose(float(y[i])+float(bases[i]), matriz.loc[OBJETIVO, 'CCA'], atol=1e-5)
    contexto = pd.DataFrame([dict(
        timestamp_objetivo=OBJETIVO, estacion_objetivo='CCA',
        inicio_ventana=bloque.index[0], fin_ventana=bloque.index[-1],
        perfil_adaptativo_ppb=float(bases[i]), lectura_real_cca_ppb=float(matriz.loc[OBJETIVO, 'CCA']),
        desviacion_real_y_ppb=float(y[i]), lecturas_disponibles_perfil=int(historia.count()),
        particion='prueba', indice_muestra_en_Xte=i,
    )])
    diccionario = []
    for j, columna in enumerate(columnas):
        if j < 32:
            estacion, tipo = vecinas[j], 'medicion_normalizada'
            descripcion = '(ppb - media_train) / desviacion_train; faltante se rellena con 0'
        elif j < 64:
            estacion, tipo = vecinas[j-32], 'disponibilidad'
            descripcion = '1: medicion disponible; 0: faltante. Canal informativo, no exclusion automatica.'
        else:
            estacion, tipo = '', 'hora_ciclica'
            descripcion = ('sin' if j == 64 else 'cos') + '(2*pi*hora/24)'
        diccionario.append(dict(indice_canal_desde_0=j, columna=columna, estacion=estacion,
            tipo=tipo, descripcion=descripcion,
            media_train_ppb=float(mu[estacion]) if j < 32 else np.nan,
            desviacion_train_ppb=float(sigma[estacion]) if j < 32 else np.nan))
    tablas = {
        '01_ventana_mediciones_ppb.csv': bloque.reset_index(),
        '02_entrada_exacta_lstm.csv': entrada,
        '03_perfil_cca_14_dias.csv': historia.rename('CCA_ppb').reset_index(),
        '04_objetivo_y_contexto.csv': contexto,
        '05_diccionario_caracteristicas.csv': pd.DataFrame(diccionario),
    }
    fuentes = {
        'data/raw/2025O3.xls': sha256(datos),
        'results/preprocesamiento_modelo4_cca.npz': sha256(preprocesamiento),
        'results/modelo4_lstm.keras': metadatos['modelo_sha256'],
    }
    return tablas, fuentes


def main():
    tablas, fuentes = construir_exportacion()
    repetidas, fuentes_repetidas = construir_exportacion()
    assert fuentes == fuentes_repetidas
    for nombre in tablas:
        pd.testing.assert_frame_equal(tablas[nombre], repetidas[nombre], check_exact=True)
    destinos = [SALIDA / n for n in tablas] + [SALIDA / 'fuentes_sha256.json']
    existentes = [str(p) for p in destinos if p.exists()]
    if existentes:
        raise FileExistsError(f'No se sobrescriben exportaciones existentes: {existentes}')
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas.items():
        # 17 cifras conservan los números float32 y las estadísticas float64.
        tabla.to_csv(SALIDA / nombre, index=False, encoding='utf-8-sig', float_format='%.17g')
        print(f'{nombre}: {tabla.shape[0]} filas x {tabla.shape[1]} columnas')
    (SALIDA / 'fuentes_sha256.json').write_text(json.dumps(fuentes, indent=2)+'\n')
    vuelta = pd.read_csv(SALIDA / '02_entrada_exacta_lstm.csv', float_precision='round_trip')
    np.testing.assert_array_equal(vuelta.to_numpy(dtype=np.float32), tablas['02_entrada_exacta_lstm.csv'].to_numpy())
    assert vuelta.columns.tolist() == tablas['02_entrada_exacta_lstm.csv'].columns.tolist()
    print('Verificado: dos reconstrucciones idénticas y CSV recuperado exactamente como float32.')
    print('No se cargó el modelo en TensorFlow: sólo se verificó su hash. Sin inferencia ni entrenamiento.')


if __name__ == '__main__':
    main()
