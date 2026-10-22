"""Plan de inyección, anomalía y etiquetas del protocolo `anomalias_red_v1` (§5, §6 y §8).

No entrena ni carga modelos. Todo se deriva de la semilla maestra 42 con claves enteras
estables (sin `hash()`): un generador por (año de inicio del periodo, corrida, uso, índice
de la estación en `multianual.ESTACIONES`).

Flujo:
    1. `corridas`: una de entrenamiento (2020–2022, p base) y 10 de prueba (2024, p sorteada).
    2. `plan_episodios`: episodios de días completos, cada estación independiente.
    3. `aplicar`: el mismo plan con cada δ (diseño pareado), redondeado a ppb enteros.
    4. `etiqueta_red`: 1 si alguna estación tiene una lectura cambiada en esa hora.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.detect import multianual as m

PROTOCOLO = 'anomalias_red_v1'
SEMILLA = 42
DELTAS = (1.00, 0.50, 0.20, 0.10, 0.05)
P_BASE = 0.0015
P_RANGO = (0.0010, 0.0030)
DURACION_DIAS = (1, 7)
CORRIDAS_PRUEBA = 10
CALENDARIOS_ENTRENAMIENTO = 20    # calendarios generados; la revisión 6 usa los 10 primeros, la 7 los 20
PERIODOS = {
    'entrenamiento': ('2020-01-01', '2022-12-31'),    # ajuste definitivo (§4)
    'prueba_2024': ('2024-01-01', '2024-12-31'),
}
USO_TASA, USO_ESTACION = 0, 1
COLUMNAS_PLAN = ['corrida', 'episodio', 'estacion', 'inicio', 'fin', 'dias_sorteados', 'dias', 'signo', 'p']


def clave(semilla, inicio, numero, uso, indice=0) -> list[int]:
    """Clave de `default_rng`, siempre de 5 enteros para que no haya colisiones por longitud."""
    return [int(semilla), pd.Timestamp(inicio).year, int(numero), int(uso), int(indice)]


# ---------------------------------------------------------------- estaciones y corridas

def estaciones_alterables(cobertura: pd.DataFrame) -> list[str]:
    """Los objetivos del V4 (clasificación distinta de `fuera`), en el orden de `ESTACIONES`."""
    clases = cobertura.drop_duplicates('objetivo').set_index('objetivo')['clasificacion']
    return [s for s in m.ESTACIONES if clases.get(s, 'fuera') != 'fuera']


def corridas(semilla=SEMILLA, n_prueba=CORRIDAS_PRUEBA) -> pd.DataFrame:
    """Entrenamiento con p base y `n_prueba` corridas de 2024 con p uniforme en `P_RANGO` (§6)."""
    ini, fin = PERIODOS['entrenamiento']
    filas = [dict(corrida='entrenamiento', inicio=ini, fin=fin, numero=0, p=P_BASE)]
    ini, fin = PERIODOS['prueba_2024']
    for k in range(1, n_prueba + 1):
        rng = np.random.default_rng(clave(semilla, ini, k, USO_TASA))
        filas.append(dict(corrida=f'prueba_2024_{k:02d}', inicio=ini, fin=fin, numero=k,
                          p=float(rng.uniform(*P_RANGO))))
    return pd.DataFrame(filas)


def calendarios_entrenamiento(semilla=SEMILLA, n=CALENDARIOS_ENTRENAMIENTO) -> pd.DataFrame:
    """Calendarios `entrenamiento_01`… sobre 2020–2022 con p uniforme en `P_RANGO` (revisión 6).

    Usan los números 1…n con el año 2020: no chocan con el plan de entrenamiento original
    (número 0) ni con los de prueba (año 2024).
    """
    ini, fin = PERIODOS['entrenamiento']
    filas = []
    for k in range(1, n + 1):
        rng = np.random.default_rng(clave(semilla, ini, k, USO_TASA))
        filas.append(dict(corrida=f'entrenamiento_{k:02d}', inicio=ini, fin=fin, numero=k,
                          p=float(rng.uniform(*P_RANGO))))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- plan

def plan_episodios(inicio, fin, p, alterables, corrida='', numero=0, semilla=SEMILLA) -> pd.DataFrame:
    """Episodios de días completos entre `inicio` y `fin` (fechas, ambos incluidos).

    Cada día sin episodio activo, la estación empieza uno con probabilidad `p`. La duración
    (1–7 días) y el signo (±, 50/50) se sortean al empezar. El episodio va de las 00 h del
    primer día a las 23 h del último y se corta al final del periodo.

    Los sorteos de cada día se hacen por adelantado y no dependen del estado, así que una
    estación no cambia si se quitan otras de `alterables`. No mira los datos: un episodio
    puede caer en horas sin dato (se cuenta en `resumen_episodios`).
    """
    if not 0 < p < 1:
        raise ValueError(f'p fuera de (0, 1): {p}')
    ajenas = sorted(set(alterables) - set(m.ESTACIONES))
    if ajenas:
        raise ValueError(f'estaciones fuera de la matriz: {ajenas}')
    dias = pd.date_range(inicio, fin, freq='D')
    n = len(dias)
    filas = []
    for est in alterables:
        rng = np.random.default_rng(clave(semilla, inicio, numero, USO_ESTACION, m.ESTACIONES.index(est)))
        u = rng.random(n)
        duracion = rng.integers(DURACION_DIAS[0], DURACION_DIAS[1] + 1, n)
        positivo = rng.random(n) < 0.5
        libre = 0
        for j in np.flatnonzero(u < p):
            if j < libre:
                continue
            efectivos = int(min(duracion[j], n - j))
            filas.append(dict(estacion=est, inicio=dias[j],
                              fin=dias[j] + pd.Timedelta(days=efectivos) - pd.Timedelta(hours=1),
                              dias_sorteados=int(duracion[j]), dias=efectivos,
                              signo=1 if positivo[j] else -1))
            libre = j + duracion[j]
    plan = pd.DataFrame(filas, columns=COLUMNAS_PLAN[2:-1])
    plan = plan.sort_values(['inicio', 'estacion'], key=lambda c: c.map(m.ESTACIONES.index)
                            if c.name == 'estacion' else c).reset_index(drop=True)
    plan.insert(0, 'episodio', np.arange(1, len(plan) + 1))
    plan.insert(0, 'corrida', corrida)
    plan['p'] = p
    return plan[COLUMNAS_PLAN]


def plan_de(corrida: pd.Series | dict, alterables, semilla=SEMILLA) -> pd.DataFrame:
    """Plan de una fila de `corridas()`."""
    c = dict(corrida)
    return plan_episodios(c['inicio'], c['fin'], c['p'], alterables, c['corrida'], c['numero'], semilla)


def validar_plan(plan: pd.DataFrame) -> None:
    """Sin traslapes por estación, inicio a las 00 h, fin a las 23 h y signo ±1."""
    if not plan['inicio'].dt.hour.eq(0).all() or not plan['fin'].dt.hour.eq(23).all():
        raise ValueError('los episodios deben ser días completos (00 h a 23 h)')
    if not plan['signo'].isin([1, -1]).all():
        raise ValueError('signo distinto de ±1')
    for est, g in plan.sort_values('inicio').groupby('estacion'):
        if (g['inicio'].iloc[1:].to_numpy() <= g['fin'].iloc[:-1].to_numpy()).any():
            raise ValueError(f'{est}: episodios traslapados')


def guardar_plan(plan: pd.DataFrame, carpeta) -> Path:
    """`plan_<corrida>.csv` (§6). Se guarda el plan, no sólo la semilla."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    path = carpeta / f'plan_{plan["corrida"].iat[0]}.csv'
    plan.to_csv(path, index=False)
    return path


def leer_plan(path) -> pd.DataFrame:
    plan = pd.read_csv(path, parse_dates=['inicio', 'fin'])
    validar_plan(plan)
    return plan


# ---------------------------------------------------------------- anomalía y etiquetas

def en_episodio(plan: pd.DataFrame, index, columnas=m.ESTACIONES) -> pd.DataFrame:
    """Booleano hora × estación: dentro de un episodio del plan (haya o no dato)."""
    dentro = pd.DataFrame(False, index=index, columns=list(columnas))
    for e in plan.itertuples():
        dentro.loc[e.inicio:e.fin, e.estacion] = True
    return dentro


def factores(plan: pd.DataFrame, index, delta: float, columnas=m.ESTACIONES) -> pd.DataFrame:
    """1 fuera de episodio; 1 + δ con signo + y 1/(1 + δ) con signo − (§5)."""
    if delta <= 0:
        raise ValueError(f'δ debe ser positivo: {delta}')
    ajenas = sorted(set(plan['estacion']) - set(columnas))
    if ajenas:
        raise ValueError(f'el plan altera estaciones que no están en la matriz: {ajenas}')
    f = pd.DataFrame(1.0, index=index, columns=list(columnas))
    for e in plan.itertuples():
        f.loc[e.inicio:e.fin, e.estacion] = (1 + delta) if e.signo > 0 else 1 / (1 + delta)
    return f


def aplicar(valores: pd.DataFrame, plan: pd.DataFrame, delta: float):
    """Matriz recibida y lecturas cambiadas con el plan y un δ.

    La RAMA reporta ppb enteros: el valor alterado se redondea al entero más cercano
    (mitades hacia arriba). Sin redondeo, sólo las horas alteradas tendrían decimales y
    un detector supervisado podría aprender esa huella en lugar de la anomalía.
    Las horas sin dato siguen sin dato. `cambiadas` = recibido ≠ original.
    """
    validar_plan(plan)
    f = factores(plan, valores.index, delta, valores.columns)
    alterado = np.floor(valores * f + 0.5)
    recibidos = valores.where(f.eq(1.0), alterado)
    cambiadas = valores.notna() & recibidos.ne(valores)
    return recibidos, cambiadas


def etiqueta_red(cambiadas: pd.DataFrame) -> pd.Series:
    """Etiqueta de red por hora (§8): alguna estación con lectura cambiada. Nunca es entrada."""
    return cambiadas.any(axis=1).rename('anomalia_red')


def columnas_entrada(inactivos) -> list[str]:
    """Estaciones que entran a la matriz de red: las 33 menos los canales inactivos (XAL)."""
    return [s for s in m.ESTACIONES if s not in set(inactivos)]


def matriz_red(valores: pd.DataFrame, columnas, cambiadas: pd.DataFrame | None = None) -> pd.DataFrame:
    """Matriz de red legible: una fila por hora, en orden y sin horas faltantes.

    Columnas, en el orden de entrada del modelo (`caracteristicas` del V4):
    `<est>_valor` en ppb (vacío = sin dato), `<est>_mascara` (1 = hay dato), `hora_sin` y
    `hora_cos`. Al final, fuera de la entrada: `anomalia_red` (0/1) y `estaciones_alteradas`
    (nombres separados por «;»). El modelo ve los valores normalizados con la media y la
    desviación de 2020–2022 y los huecos como 0; eso se hace al entrenar, no aquí.
    """
    columnas = list(columnas)
    v = valores[columnas]
    if not v.index.equals(pd.date_range(v.index[0], v.index[-1], freq='h')):
        raise ValueError('la matriz de red requiere una rejilla horaria continua y ordenada')
    h = v.index.hour.to_numpy()
    out = pd.concat([v.add_suffix('_valor'), v.notna().astype('int8').add_suffix('_mascara'),
                     pd.DataFrame({'hora_sin': np.sin(2 * np.pi * h / 24),
                                   'hora_cos': np.cos(2 * np.pi * h / 24)}, index=v.index)], axis=1)
    cam = (pd.DataFrame(False, index=v.index, columns=columnas) if cambiadas is None
           else cambiadas.reindex(index=v.index, columns=columnas, fill_value=False))
    out['anomalia_red'] = cam.any(axis=1).astype('int8')
    nombres = np.array(columnas)
    out['estaciones_alteradas'] = [';'.join(nombres[fila]) for fila in cam.to_numpy()]
    out.index.name = 'timestamp'
    return out


def leer_matriz(path) -> pd.DataFrame:
    """Lee una matriz guardada con `generar_matrices.py`."""
    x = pd.read_csv(path, index_col='timestamp', parse_dates=['timestamp'], low_memory=False)
    x['estaciones_alteradas'] = x['estaciones_alteradas'].fillna('')
    return x


def resumen_episodios(valores: pd.DataFrame, plan: pd.DataFrame, deltas=DELTAS) -> pd.DataFrame:
    """Plan con horas con dato y horas cambiadas por δ.

    `evaluable` = el episodio tiene al menos una hora con dato. No depende de δ, para que el
    denominador de la detección sea el mismo con todos los δ (diseño pareado).
    """
    out = plan.copy()
    datos = valores.notna()
    out['horas_con_dato'] = [int(datos.loc[e.inicio:e.fin, e.estacion].sum()) for e in plan.itertuples()]
    for d in deltas:
        _, cambiadas = aplicar(valores, plan, d)
        out[f'horas_cambiadas_d{round(100 * d)}'] = [int(cambiadas.loc[e.inicio:e.fin, e.estacion].sum())
                                                     for e in plan.itertuples()]
    out['evaluable'] = out['horas_con_dato'] > 0
    return out
