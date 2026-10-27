"""V4 supervisado (V4S), protocolo `anomalias_red_v1`, revisión 18.

Las 66 entradas del V4 (las otras 32 estaciones normalizadas, sus máscaras, seno y coseno), con las
filas t−23…t de la variante `incluir_t=True`, más 2 columnas de la estación objetivo: su lectura
contra la base del V4, (lectura − base) / σ, y su máscara (1 si hay lectura y base). El V4 nunca ve
la lectura de su estación; sin esas 2 columnas un clasificador no podría ver el ataque. Un modelo
por estación, como el V4. La etiqueta (¿la lectura de s fue alterada en t?) nunca es entrada.

Revisión 18b, V4S compartido: un solo modelo para las 31 estaciones, como L0. Para que una columna
signifique lo mismo en todas, las otras 32 estaciones (valores y máscaras) van ordenadas por distancia
al objetivo (`orden_por_distancia`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.detect import entrenamiento_multianual as em
from src.detect import multianual as m

N_COLUMNAS = 68
REVISION = 18
CADA = 8                         # 1 de cada 8 horas por calendario y estación, como L0 con 20 calendarios
USOS = {'seleccion': 0, 'validacion': 1, 'definitivo': 2}


def propias(valores: pd.DataFrame, objetivo: str, perfil: pd.DataFrame, sigma) -> np.ndarray:
    """(horas × 2): (lectura − base) / σ del objetivo, con 0 donde falta, y su máscara."""
    rel = (valores[objetivo] - perfil['base']) / sigma[objetivo]
    mascara = rel.notna()
    return np.column_stack([rel.fillna(0.0).to_numpy(np.float32), mascara.to_numpy(np.float32)])


def orden_por_distancia(objetivo: str, dist: pd.DataFrame) -> list[str]:
    """Las otras 32 estaciones de la matriz fija, de la más cercana a la más lejana (empates por clave)."""
    from src.detect.vecinas import vecinas_cercanas
    return vecinas_cercanas(dist, objetivo, len(m.ESTACIONES) - 1)


def tensores(entradas, valores, objetivo, mu, sigma, perfil, etapas, orden=None) -> dict:
    """Ejemplos del objetivo en `etapas`: X (n, 24, 68), las horas `ts` y sus posiciones `pos`.

    Las mismas horas que el V4 (objetivo observado y con base) y sus 66 columnas con filas t−23…t.
    Con `orden` (V4S compartido), los valores y las máscaras de las otras estaciones van en ese orden.
    """
    t = em.tensores(entradas, valores, objetivo, mu, sigma, perfil, etapas, incluir_t=True)
    X = t['X']
    if orden is not None:
        otras = [c for c in entradas.columns if c != objetivo]
        if sorted(orden) != sorted(otras):
            raise ValueError(f'{objetivo}: el orden no tiene exactamente a las otras estaciones')
        i = [otras.index(c) for c in orden]
        n = len(otras)
        X = X[:, :, i + [n + k for k in i] + [2 * n, 2 * n + 1]]
    pos = valores.index.get_indexer(t['ts'])
    P = propias(valores, objetivo, perfil, sigma)
    filas = pos[:, None] + np.arange(-m.VENTANA + 1, 1)[None, :]
    return dict(X=np.concatenate([X, P[filas]], axis=2), ts=t['ts'], pos=pos)


def cuantos(valores, objetivo, perfil, etapas, cada: int = CADA) -> int:
    """Cuántos ejemplos deja `muestra` en `etapas`, sin construir las ventanas."""
    ok = m.ejemplos_validos(valores, objetivo, perfil).to_numpy() & m.mascara_etapas(valores.index, etapas)
    n = int(ok.sum())
    return n if cada == 1 else n // cada


def muestra(n: int, uso: str, calendario: int, estacion: int, cada: int = CADA, semilla: int = 42) -> np.ndarray:
    """1 de cada `cada` de los n ejemplos, sin reemplazo y ordenados; semilla [42, 18, uso, calendario, estación]."""
    if cada == 1:
        return np.arange(n)
    rng = np.random.default_rng([int(semilla), REVISION, USOS[uso], int(calendario), int(estacion)])
    return np.sort(rng.choice(n, size=n // cada, replace=False))


def probabilidades(modelos: dict, valores, inactivos, mu, sigma, etapa, index, ordenes: dict | None = None) -> pd.DataFrame:
    """Hora × estación: la probabilidad del V4S en las horas válidas de `etapa` (NaN en las demás).

    `modelos`: {objetivo: modelo}; en el compartido, el mismo modelo para todos, con `ordenes`.
    """
    entradas = m.entradas_modelo(valores, inactivos)
    cols = {}
    for obj, modelo in modelos.items():
        t = tensores(entradas, valores, obj, mu, sigma, m.perfil_causal(valores[obj]), (etapa,),
                     orden=None if ordenes is None else ordenes[obj])
        p = modelo.predict(t['X'], batch_size=4096, verbose=0).ravel().astype(np.float64) if len(t['ts']) else []
        cols[obj] = pd.Series(p, index=pd.DatetimeIndex(t['ts']), dtype=float)
    return pd.DataFrame(cols).reindex(index)
