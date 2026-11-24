"""De los archivos originales de la RAMA a la tabla que recibió TINTO.

Uso (desde la carpeta raíz del paquete):
    python 4_nuestro_mapa_y_figura/armar_tabla.py

Necesita pandas, numpy y xlrd (para leer .xls). Pasos:
1. Lee 2020O3.xls y 2021O3.xls tal como los publica la RAMA: una fila por hora (FECHA, HORA 1..24),
   una columna por estación, −99 = sin medición.
2. Convierte −99 en vacío (NaN). HORA 1 se toma como 00:00 y HORA 24 como 23:00 del mismo día.
3. Voltea la tabla: cada día de cada estación pasa a ser UNA fila con 24 columnas h00..h23.
4. Se queda con los días completos (24 horas con dato) de 31 estaciones.
5. Compara el resultado con 2_tabla_que_recibio_tinto/ajuste_mapa_2020_2021.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
# 31 estaciones usadas, en este orden (las de la RAMA menos HGM, XAL, COY, SJA y SFE).
ESTACIONES = ['ACO', 'AJM', 'AJU', 'ATI', 'BJU', 'CAM', 'CCA', 'CHO', 'CUA', 'CUT', 'FAC', 'FAR', 'GAM',
              'INN', 'IZT', 'LLA', 'LPR', 'MER', 'MGH', 'MON', 'MPA', 'NEZ', 'PED', 'SAC', 'SAG', 'TAH',
              'TLA', 'TLI', 'UAX', 'UIZ', 'VIF']
HORAS = [f'h{h:02}' for h in range(24)]


def leer_rama(anio):
    """Pasos 1 y 2: tabla horaria con un índice de fecha-hora y −99 como NaN."""
    x = pd.read_excel(RAIZ / f'1_originales_rama/{anio}O3.xls', header=0)
    x.index = pd.to_datetime(x['FECHA']) + pd.to_timedelta(x['HORA'] - 1, unit='h')
    return x.drop(columns=['FECHA', 'HORA']).replace(-99, np.nan)


def main():
    horaria = pd.concat([leer_rama(a) for a in (2020, 2021)])
    # Rejilla horaria completa: si faltara un renglón en el archivo, queda como hora sin dato.
    horaria = horaria.reindex(pd.date_range('2020-01-01', '2021-12-31 23:00', freq='h'))
    # Paso 3: la columna de cada estación se corta en días de 24 horas (una fila por día).
    filas = []
    for s in ESTACIONES:
        dias = horaria[s].to_numpy().reshape(-1, 24)
        filas.append(pd.DataFrame(dias, columns=HORAS).assign(estacion=s, fecha=horaria.index[::24].date))
    tabla = pd.concat(filas, ignore_index=True)
    # Paso 4: solo días completos.
    tabla = tabla[tabla[HORAS].notna().all(axis=1)].reset_index(drop=True)
    print(f'{len(tabla)} filas (estación-día completas de 2020–2021) × {len(HORAS)} columnas')

    # Paso 5: comparar con la tabla entregada (valores y orden de las filas).
    ref = pd.read_csv(RAIZ / '2_tabla_que_recibio_tinto/ajuste_mapa_2020_2021.csv')
    meta = pd.read_csv(RAIZ / '2_tabla_que_recibio_tinto/ajuste_mapa_2020_2021_metadatos.csv')
    iguales = (np.array_equal(tabla[HORAS].to_numpy(float), ref[HORAS].to_numpy(float))
               and tabla.estacion.tolist() == meta.estacion.tolist()
               and [str(f) for f in tabla.fecha] == meta.fecha.tolist())
    print('¿Idéntica a la tabla que recibió TINTO?', 'sí' if iguales else 'NO')


if __name__ == '__main__':
    main()
