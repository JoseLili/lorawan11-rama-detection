"""Preparacion de tensores para modelos secuenciales multiestacion.

Convierte la matriz horas x estaciones en ventanas deslizantes con
mascara de validez, para predecir el valor de una estacion objetivo a
partir de sus vecinas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def perfil_horario(serie: pd.Series) -> pd.Series:
    """Media historica por hora del dia.

    Debe calcularse SOLO sobre el conjunto de entrenamiento y
    reutilizarse en el de prueba: calcularlo sobre todo el periodo seria
    fuga de informacion.
    """
    return serie.groupby(serie.index.hour).mean()


def construir_ventanas(
    matriz: pd.DataFrame,
    objetivo: str,
    ventana: int = 24,
    mu: pd.Series | None = None,
    sigma: pd.Series | None = None,
    con_hora: bool = True,
    perfil: pd.Series | None = None,
    predecir_desviacion: bool = False,
):
    """Construye X (ventanas + mascara + hora) e y (objetivo).

    `matriz`: filas = timestamps horarios, columnas = estaciones.

    `objetivo`: estacion a predecir. Se EXCLUYE de las entradas para
        evitar que el modelo copie el valor y para que un ataque
        sostenido no contamine la ventana.

    `mu`, `sigma`: normalizacion. Deben calcularse sobre el conjunto de
        entrenamiento y reutilizarse en el de prueba.

    `con_hora`: añade dos columnas por paso temporal con la hora del dia
        codificada como seno y coseno. El O3 es fotoquimico y su
        comportamiento depende de la hora solar. La codificacion circular
        evita que las 23:00 y las 00:00 queden en extremos opuestos.

    `predecir_desviacion`: si True, `y` contiene la desviacion respecto
        al perfil horario en lugar del valor absoluto. El modelo deja de
        tener que aprender la amplitud del ciclo diurno, que es
        calculable exactamente. El valor absoluto se recupera sumando el
        perfil: x_hat = base + y_hat.

    `perfil`: media por hora del conjunto de entrenamiento. Obligatorio
        si predecir_desviacion.

    Devuelve (X, y, ts, base, mu, sigma) donde:
        X     (n, ventana, 2*n_vecinas [+2])  valores + mascara [+ hora]
        y     (n,)                            valor o desviacion
        ts    (n,)                            timestamp de la prediccion
        base  (n,)                            perfil horario, o ceros
    """
    vecinas = [c for c in matriz.columns if c != objetivo]
    v = matriz[vecinas]

    if mu is None or sigma is None:
        mu = v.mean()
        sigma = v.std().replace(0, 1.0)   # evita division por cero

    mascara = v.notna().astype(np.float32).values
    valores = ((v - mu) / sigma).fillna(0.0).astype(np.float32).values

    if con_hora:
        h = matriz.index.hour.values
        hora = np.column_stack([
            np.sin(2 * np.pi * h / 24),
            np.cos(2 * np.pi * h / 24),
        ]).astype(np.float32)
    else:
        hora = None

    obj = matriz[objetivo].values
    horas_obj = matriz.index.hour.values
    ts = matriz.index.values

    if predecir_desviacion:
        if perfil is None:
            raise ValueError("predecir_desviacion requiere `perfil`")
        if isinstance(perfil, pd.Series) and len(perfil) == len(matriz):
            base = perfil.values                    # adaptativo, por timestamp
        else:
            base = perfil.reindex(horas_obj).values  # fijo, por hora
    else:
        base = np.zeros(len(matriz))

    X, y, T, B = [], [], [], []
    for t in range(ventana, len(matriz)):
        if np.isnan(obj[t]):
            continue                       # sin verdad de campo
        partes = [valores[t - ventana:t], mascara[t - ventana:t]]
        if con_hora:
            partes.append(hora[t - ventana:t])
        X.append(np.concatenate(partes, axis=1))
        y.append(obj[t] - base[t])
        T.append(ts[t])
        B.append(base[t])

    return (np.asarray(X, dtype=np.float32),
            np.asarray(y, dtype=np.float32),
            np.asarray(T),
            np.asarray(B, dtype=np.float32),
            mu, sigma)

def perfil_adaptativo(serie: pd.Series, dias: int = 14) -> pd.Series:
    """Media movil por hora del dia sobre los ultimos N dias.

    A diferencia de `perfil_horario`, sigue el regimen vigente. Se
    calcula de forma causal: para cada instante t usa solo observaciones
    anteriores, de modo que no introduce informacion del futuro.

    Los NaN de arranque (primeras observaciones de cada franja horaria)
    se rellenan con el perfil global de la serie.
    """
    df = pd.DataFrame({'v': serie.values, 'h': serie.index.hour},
                      index=serie.index)

    adaptativo = (df.groupby('h')['v']
                    .transform(lambda s: s.shift(1)
                                          .rolling(dias, min_periods=1)
                                          .mean()))

    # Respaldo: perfil global por hora, para el arranque
    global_ = serie.groupby(serie.index.hour).mean()
    respaldo = pd.Series(global_.reindex(df['h']).values, index=serie.index)

    return adaptativo.fillna(respaldo)