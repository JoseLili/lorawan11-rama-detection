"""Entradas, umbrales y métricas de red del protocolo `anomalias_red_v1` (§8 y §9).

Común a todos los detectores: cada uno produce un puntaje por hora de red y aquí se
convierte en alertas y métricas. No entrena modelos.

Métricas (§9 y revisión 2):
    - por hora: proporción de horas con etiqueta 1 que alertan, con falsas alarmas fijas;
    - por episodio: detectado si hay alguna alerta de red mientras dura, y horas hasta la
      primera alerta, siempre junto a su nivel de azar: las mismas ventanas evaluadas con
      las alertas del año limpio.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.detect import multianual as m

NIVELES_FA = (0.05, 0.01)


# ---------------------------------------------------------------- entradas

def estaciones_de(matriz: pd.DataFrame) -> list[str]:
    return [c[:-len('_valor')] for c in matriz.columns if c.endswith('_valor')]


def normalizacion(limpia: pd.DataFrame):
    """Media y desviación (ddof=1, 0 → 1) por estación con la matriz limpia de 2020–2022, como el V4."""
    v = limpia[[f'{s}_valor' for s in estaciones_de(limpia)]]
    v.columns = estaciones_de(limpia)
    return v.mean(), v.std().replace(0, 1.0)


def entradas(matriz: pd.DataFrame, mu, sigma) -> np.ndarray:
    """Las 66 columnas de la hora t: valores normalizados (hueco → 0), máscaras, seno y coseno."""
    est = estaciones_de(matriz)
    v = matriz[[f'{s}_valor' for s in est]]
    v.columns = est
    norm = ((v - mu[est]) / sigma[est]).fillna(0.0).to_numpy(np.float32)
    mascara = matriz[[f'{s}_mascara' for s in est]].to_numpy(np.float32)
    hora = matriz[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([norm, mascara, hora], axis=1)


REFERENCIAS = ('media', 'mediana')


def perfil_mediana(serie: pd.Series, dias: int = m.PERFIL_DIAS) -> pd.Series:
    """Como `multianual.perfil_causal`, pero con medianas (revisión 10): la mediana de los `dias`
    valores anteriores a esa misma hora; si no hay, la mediana histórica de esa hora y luego la
    global, siempre con observaciones estrictamente anteriores. Sin historia → NaN.
    """
    if not serie.index.equals(pd.date_range(serie.index[0], serie.index[-1], freq='h')):
        raise ValueError('perfil_mediana requiere rejilla horaria continua')
    g = serie.groupby(serie.index.hour)
    base = g.transform(lambda s: s.shift(1).rolling(dias, min_periods=1).median())
    for respaldo in (g.transform(lambda s: s.shift(1).expanding().median()), serie.shift(1).expanding().median()):
        base = base.fillna(respaldo)
    return base


def relativas(matriz: pd.DataFrame, previa: pd.DataFrame | None = None, referencia: str = 'media') -> pd.DataFrame:
    """Valor menos su perfil causal de 14 días a esa hora, por estación y en ppb (la base del V4).

    `previa`, contigua y anterior a `matriz`, da la historia del perfil al inicio de `matriz`.
    Sin dato o sin historia → NaN. `referencia`: 'media' (el perfil del V4, revisiones 7 y 8) o
    'mediana' (revisión 10, que no se mueve tanto cuando parte de los 14 días está alterada).
    """
    if referencia not in REFERENCIAS:
        raise ValueError(f'referencia desconocida: {referencia}')
    est = estaciones_de(matriz)
    v = matriz[[f'{s}_valor' for s in est]].set_axis(est, axis=1)
    serie = v
    if previa is not None:
        p = previa[[f'{s}_valor' for s in est]].set_axis(est, axis=1)
        if p.index[-1] + pd.Timedelta(hours=1) != v.index[0]:
            raise ValueError('la matriz previa no termina una hora antes de la matriz')
        serie = pd.concat([p, v])
    perfil = (lambda x: m.perfil_causal(x)['base']) if referencia == 'media' else perfil_mediana
    base = pd.DataFrame({s: perfil(serie[s]) for s in est}).loc[v.index]
    return v - base


def entradas_relativas(matriz: pd.DataFrame, sigma, previa: pd.DataFrame | None = None,
                       referencia: str = 'media') -> np.ndarray:
    """Como `entradas`, pero con (valor − perfil de 14 días) / σ en lugar del valor normalizado."""
    est = estaciones_de(matriz)
    rel = (relativas(matriz, previa, referencia) / sigma[est]).fillna(0.0).to_numpy(np.float32)
    mascara = matriz[[f'{s}_mascara' for s in est]].to_numpy(np.float32)
    hora = matriz[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([rel, mascara, hora], axis=1)


# ---------------------------------------------------------------- vecinas (revisión 8)

K_VECINAS = 4
SUAVE_PPB = 10.0         # forma (b): evita que el cociente se dispare de noche, con poco ozono
DIAS_REFERENCIA = 14
FORMAS = ('a14', 'afija', 'b14', 'bfija')


@dataclass(frozen=True)
class Vecinas:
    """Parámetros de la columna de vecinas de la revisión 8, ajustados con años limpios.

    `forma`: (a) diferencia de desviaciones o (b) cociente, contra lo típico de los 14 días
    anteriores (`a14`, `b14`) o de un valor fijo por estación y hora del día (`afija`, `bfija`).
    """
    forma: str
    vecinas: dict
    fija: pd.DataFrame | None        # hora del día × estación; sólo en las formas fijas
    escala: pd.Series                # desviación de la columna en los años limpios de ajuste
    referencia: str = 'media'        # perfil de 14 días de la forma a14 y de las relativas (revisión 10)


def vecinas_de(estaciones, geo: pd.DataFrame, k: int = K_VECINAS) -> dict[str, list[str]]:
    """Las k columnas más cercanas de cada columna de la matriz, por distancia haversine.

    Son las del experimento de vecinas cercanas de la parte 1: candidatas sólo entre las columnas
    de la matriz (XAL, inactivo, no está), en orden de distancia y con empates por clave.
    """
    from src.detect.vecinas import distancias, vecinas_cercanas
    fuera = [s for s in m.ESTACIONES if s not in set(estaciones)]
    dist = distancias(geo)
    return {s: vecinas_cercanas(dist, s, k, inactivos=fuera) for s in estaciones}


def _valores(matriz: pd.DataFrame) -> pd.DataFrame:
    est = estaciones_de(matriz)
    return matriz[[f'{s}_valor' for s in est]].set_axis(est, axis=1)


def _promedio_vecinas(x: pd.DataFrame, vecinas: dict):
    """Promedio de las vecinas con dato y cuántas tienen dato, por columna y hora."""
    prom = pd.DataFrame({s: x[vecinas[s]].mean(axis=1) for s in x.columns})
    n = pd.DataFrame({s: x[vecinas[s]].notna().sum(axis=1) for s in x.columns})
    return prom, n


def _cociente(v: pd.DataFrame, vecinas: dict) -> pd.DataFrame:
    """log((x + 10) / (promedio de las vecinas + 10)); NaN sin dato propio o con menos de 2 vecinas."""
    prom, n = _promedio_vecinas(v, vecinas)
    return np.log((v + SUAVE_PPB) / (prom + SUAVE_PPB)).where(v.notna() & (n >= 2))


def _por_hora(fija: pd.DataFrame, index) -> pd.DataFrame:
    return fija.reindex(index.hour).set_axis(index)


def _sin_escala(matriz: pd.DataFrame, sigma, forma: str, vecinas: dict, fija, referencia: str = 'media') -> pd.DataFrame:
    """Comparación de cada estación con sus vecinas, antes de escalar; NaN donde no se calcula."""
    v = _valores(matriz)
    if forma in ('a14', 'afija'):
        base = relativas(matriz, referencia=referencia) if forma == 'a14' else v - _por_hora(fija, v.index)
        d = base / sigma[v.columns]
        prom, n = _promedio_vecinas(d, vecinas)
        return (d - prom).where(d.notna() & (n >= 2))
    q = _cociente(v, vecinas)
    if forma == 'b14':                    # mediana de los 14 días anteriores a esa hora (causal)
        ref = q.groupby(q.index.hour).transform(
            lambda s: s.shift(1).rolling(DIAS_REFERENCIA, min_periods=1).median())
    else:
        ref = _por_hora(fija, q.index)
    return q - ref


def ajustar_vecinas(forma: str, limpia: pd.DataFrame, sigma, vecinas: dict, referencia: str = 'media') -> Vecinas:
    """La referencia fija (si la forma la usa) y la escala, con la matriz limpia de los años de ajuste.

    `referencia` = 'mediana' (revisión 10) sólo está definida para a14, la forma elegida en la revisión 8.
    """
    if forma not in FORMAS:
        raise ValueError(f'forma desconocida: {forma}')
    if referencia not in REFERENCIAS or (referencia != 'media' and forma != 'a14'):
        raise ValueError(f'referencia {referencia} no definida para la forma {forma}')
    v, fija = _valores(limpia), None
    if forma == 'afija':
        fija = v.groupby(v.index.hour).mean()
    elif forma == 'bfija':
        q = _cociente(v, vecinas)
        fija = q.groupby(q.index.hour).median()
    c = _sin_escala(limpia, sigma, forma, vecinas, fija, referencia)
    return Vecinas(forma, vecinas, fija, c.std().replace(0, 1.0).fillna(1.0), referencia)


def columnas_vecinas(matriz: pd.DataFrame, sigma, par: Vecinas) -> pd.DataFrame:
    """La columna nueva de cada estación (revisión 8), ya escalada; NaN donde no se calcula.

    Con la forma de 14 días, `matriz` debe traer la historia que necesita (como `relativas`).
    """
    return _sin_escala(matriz, sigma, par.forma, par.vecinas, par.fija, par.referencia) / par.escala


def entradas_vecinas(matriz: pd.DataFrame, sigma, par: Vecinas) -> np.ndarray:
    """Las 66 columnas de la revisión 7 y, al final, una por estación frente a sus vecinas (98)."""
    nuevas = columnas_vecinas(matriz, sigma, par).fillna(0.0).to_numpy(np.float32)
    return np.concatenate([entradas_relativas(matriz, sigma, referencia=par.referencia), nuevas], axis=1)


ENTRADAS = ('crudas', 'relativas', 'vecinas')


def entradas_de(tipo: str, matriz: pd.DataFrame, mu, sigma, vecinas: Vecinas | None = None) -> np.ndarray:
    """Las columnas de la hora t: `crudas` (§8), `relativas` al perfil de 14 días (revisión 7) o
    `vecinas` (revisión 8: las relativas más una columna por estación frente a sus vecinas).

    Con `relativas` y `vecinas`, `matriz` debe traer la historia que necesita el perfil (las
    matrices anteriores concatenadas); las columnas son puntuales, así que con `crudas` da lo mismo.
    """
    if tipo == 'crudas':
        return entradas(matriz, mu, sigma)
    if tipo == 'relativas':
        return entradas_relativas(matriz, sigma)
    if tipo == 'vecinas':
        if vecinas is None:
            raise ValueError('las entradas de vecinas necesitan sus parámetros (ajustar_vecinas)')
        return entradas_vecinas(matriz, sigma, vecinas)
    raise ValueError(f'entradas desconocidas: {tipo}')


def con_historia(previa: pd.DataFrame, matriz: pd.DataFrame) -> pd.DataFrame:
    """`previa` y `matriz` concatenadas; `previa` debe terminar una hora antes de `matriz`."""
    if previa.index[-1] + pd.Timedelta(hours=1) != matriz.index[0]:
        raise ValueError('la historia no termina una hora antes de la matriz')
    return pd.concat([previa[matriz.columns], matriz])


# ---------------------------------------------------------------- umbral

def umbral_falsas_alarmas(puntaje_limpio, objetivo: float) -> float:
    """El umbral más bajo u tal que la proporción de horas limpias con puntaje > u no pasa de `objetivo`.

    Con puntajes con empates (p. ej., probabilidades de un Random Forest) la tasa lograda
    puede quedar por debajo del objetivo; se reporta la lograda.
    """
    p = np.sort(np.asarray(puntaje_limpio, dtype=float))
    n = len(p)
    for u in np.unique(p):
        if (n - np.searchsorted(p, u, side='right')) / n <= objetivo:
            return float(u)
    return float(p[-1])


# ---------------------------------------------------------------- métricas

def por_hora(alerta: pd.Series, etiqueta: pd.Series) -> dict:
    a, y = alerta.to_numpy(bool), etiqueta.to_numpy(bool)
    return dict(horas_anomalas=int(y.sum()), horas_normales=int((~y).sum()),
                deteccion_hora_pct=100 * a[y].mean() if y.any() else np.nan,
                falsa_alarma_hora_pct=100 * a[~y].mean() if (~y).any() else np.nan)


def por_episodio(plan: pd.DataFrame, alerta: pd.Series) -> pd.DataFrame:
    """Para cada episodio: si hubo alguna alerta de red mientras duró y las horas hasta la primera.

    `horas_hasta_alerta` = 0 si la alerta llega en la primera hora del episodio; NaN si no hubo.
    """
    tiempos = alerta.index[alerta.to_numpy(bool)]
    det, horas = [], []
    for e in plan.itertuples():
        dentro = tiempos[(tiempos >= e.inicio) & (tiempos <= e.fin)]
        det.append(len(dentro) > 0)
        horas.append((dentro[0] - e.inicio) / pd.Timedelta(hours=1) if len(dentro) else np.nan)
    return plan.assign(detectado=det, horas_hasta_alerta=horas)


TRAMOS_PPB = (1, 16, 32, 64)


def cambio_maximo(alterada: pd.DataFrame, limpia: pd.DataFrame) -> pd.Series:
    """Mayor |recibido − original| en ppb entre estaciones en cada hora; 0 si nada cambió."""
    cols = [f'{s}_valor' for s in estaciones_de(limpia)]
    d = np.abs(alterada[cols].to_numpy(float) - limpia[cols].to_numpy(float))
    return pd.Series(np.nan_to_num(d, nan=0.0).max(axis=1), index=limpia.index)


def por_tamano(alerta: pd.Series, cambio: pd.Series, alerta_limpia: pd.Series | None = None,
               tramos=TRAMOS_PPB) -> pd.DataFrame:
    """Horas que alertan según el mayor cambio de la hora (revisiones 3 y 4).

    Tramos cerrados por la izquierda: sin cambio (< 1 ppb), [1, 16), [16, 32), [32, 64), ≥ 64.
    Con `alerta_limpia` (las alertas del año limpio) agrega `alertan_azar`: cuántas de esas
    mismas horas alertan sin la alteración. Lo que aporta la alteración es la diferencia.
    """
    bordes = [0, *tramos, np.inf]
    nombres = ['sin cambio'] + [f'{a}-{b}' for a, b in zip(tramos, tramos[1:])] + [f'>={tramos[-1]}']
    tramo = pd.cut(cambio.to_numpy(), bordes, right=False, labels=nombres)
    contar = lambda a: pd.Series(a.to_numpy(bool)).groupby(tramo, observed=False)  # noqa: E731
    g = contar(alerta)
    t = pd.DataFrame(dict(tramo_ppb=nombres, horas=g.size().to_numpy(), alertan=g.sum().to_numpy().astype(int)))
    if alerta_limpia is not None:
        t['alertan_azar'] = contar(alerta_limpia).sum().to_numpy().astype(int)
    return t


def horas_con_dato(plan: pd.DataFrame, limpia: pd.DataFrame) -> list[int]:
    """Horas con dato de la estación durante cada episodio, con las máscaras de la matriz limpia."""
    return [int(limpia.loc[e.inicio:e.fin, f'{e.estacion}_mascara'].sum()) for e in plan.itertuples()]
