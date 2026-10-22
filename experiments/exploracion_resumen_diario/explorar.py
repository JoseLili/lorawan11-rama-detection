"""Exploración fuera de protocolo (2026-10-19): ¿resumir el día en 1, 2 o 4 números baja el ruido?

Surge de la junta del 2026-10-19 (sintetizar las 24 horas en promedios). Sólo usa 2020–2022, los años
de entrenamiento; no toca 2023–2026. No entrena ni carga modelos. Uso, desde la raíz del repo:

    .venv/bin/python experiments/exploracion_resumen_diario/explorar.py

Para cada estación objetivo y cada día:
- resumen = promedio de las horas de un bloque (exige 75 % de horas con dato);
- referencia «propia»: log(resumen) menos la mediana de log(resumen) de los 14 días previos;
- referencia «vecinas»: log(resumen / promedio de los resúmenes de sus 4 vecinas más cercanas, con al
  menos 2 con dato), menos la mediana de esa razón en los 14 días previos.
Se altera la estación como en el protocolo (x·(1+δ) o x/(1+δ), redondeado a ppb enteros), con la base
y las vecinas limpias. Se divide entre el σ robusto de cada estación y se alerta si |u| pasa el umbral
que deja la fracción fa de días limpios con alerta (dos colas; con varios bloques, el mayor |u|).

Es una cota optimista: el detector sabe qué estación mirar, las vecinas están limpias y el umbral se fija
con los mismos años. fa = 5 %/31 por estación y día equivale a 5 % por día de red si las 31 estaciones
fueran independientes.

Salidas en results/exploracion_resumen_diario_2020_2022/: resumenes.csv y varios_dias.csv.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import multianual as m  # noqa: E402
from src.detect import vecinas as v  # noqa: E402

SAL = RAIZ / 'results/exploracion_resumen_diario_2020_2022'
BLOQUES = {'dia': list(range(24)), 'dia_06_17': list(range(6, 18)), 'noche': list(range(0, 6)) + list(range(18, 24)),
           'c00_05': list(range(0, 6)), 'c06_11': list(range(6, 12)), 'c12_17': list(range(12, 18)),
           'c18_23': list(range(18, 24)), 'hora_15': [15]}
REGLAS = {'1 número: día completo': ['dia'], '2 números: día y noche': ['dia_06_17', 'noche'],
          '4 números: cuartos de 6 h': ['c00_05', 'c06_11', 'c12_17', 'c18_23'],
          '1 número: sólo la tarde 12–17 h': ['c12_17'], 'Una sola hora (15 h)': ['hora_15']}
DELTAS, NIVELES, K_VECINAS = (0.05, 0.10, 0.20), (0.05, 0.05 / 31), 4


def resumen(A, horas):
    """Promedio del bloque por día (A: día × hora); NaN si faltan más del 25 % de las horas."""
    b = A[:, horas]
    ok = np.isfinite(b).sum(1) >= 0.75 * len(horas)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        return np.where(ok, np.nanmean(b, 1), np.nan)


def base_movil(serie, dias_previos=14, minimo=7):
    """Mediana de los `dias_previos` días anteriores (sin el día), si hay al menos `minimo`."""
    return pd.Series(serie).shift(1).rolling(dias_previos, min_periods=minimo).median().to_numpy()


def lg(x):
    return np.log(np.maximum(x, 0.5))


def alterar(A, delta, signo):
    return np.floor(A * ((1 + delta) if signo > 0 else 1 / (1 + delta)) + 0.5)


def promedio_vecinas(X, col, vecinas, horas):
    Sv = np.column_stack([resumen(X[:, :, col[n]], horas) for n in vecinas])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        return np.where(np.isfinite(Sv).sum(1) >= 2, np.nanmean(Sv, 1), np.nan)


def detecciones(u_limpio, u_alterado, fila):
    for fa in NIVELES:
        q = np.quantile(u_limpio, 1 - fa)
        f = dict(fila, fa_estacion_dia_pct=round(100 * fa, 3), umbral_sigmas=round(float(q), 2))
        for d in DELTAS:
            f[f'deteccion_d{round(100 * d)}_pct'] = round(100 * np.mean(
                [np.mean(np.concatenate(u_alterado[(d, sg)]) > q) for sg in (1, -1)]), 1)
        yield f


def main():
    w = pd.read_parquet(RAIZ / 'data/processed/o3_2020_2026_ancho.parquet')
    w = w.loc['2020-01-01':'2022-12-31 23:00', m.ESTACIONES]
    dias = w.index.normalize().unique()
    assert len(w) == 24 * len(dias)
    X = w.to_numpy(float).reshape(len(dias), 24, len(m.ESTACIONES))        # día × hora × estación
    col = {s: i for i, s in enumerate(m.ESTACIONES)}
    geo = pd.read_csv(RAIZ / 'results/inventario_multianual/estaciones_geografia.csv', index_col='station')
    D = v.distancias(geo)
    objetivos = [s for s in m.ESTACIONES if s not in ('HGM', 'XAL')]
    vecinas = {s: v.vecinas_cercanas(D, s, K_VECINAS, inactivos=['XAL']) for s in objetivos}
    claves = [(d, sg) for d in DELTAS for sg in (1, -1)]

    # 1. Un día alterado, distintas formas de resumirlo.
    filas = []
    for ref in ('propia', 'vecinas'):
        for regla, bloques in REGLAS.items():
            ul, ua, sigmas = [], {k: [] for k in claves}, []
            for s in objetivos:
                A = X[:, :, col[s]]
                zs, za = [], {k: [] for k in claves}
                for b in bloques:
                    h = BLOQUES[b]
                    lv = lg(promedio_vecinas(X, col, vecinas[s], h)) if ref == 'vecinas' else 0
                    r = lg(resumen(A, h)) - lv
                    base = base_movil(r)
                    z = r - base
                    sig = 1.4826 * np.nanmedian(np.abs(z - np.nanmedian(z)))
                    sigmas.append(sig)
                    zs.append(z / sig)
                    for d, sg in claves:
                        za[(d, sg)].append((lg(resumen(alterar(A, d, sg), h)) - lv - base) / sig)
                Z = np.abs(np.column_stack(zs))
                ok = np.isfinite(Z).all(1)
                ul.append(Z.max(1)[ok])
                for k in claves:
                    ua[k].append(np.abs(np.column_stack(za[k])).max(1)[ok])
            fila = dict(referencia=ref, resumen=regla, dias_estacion=int(sum(map(len, ul))),
                        ruido_pct=round(100 * float(np.median(sigmas)), 1))
            filas.extend(detecciones(np.concatenate(ul), ua, fila))
    resumenes = pd.DataFrame(filas)

    # 2. La tarde frente a las vecinas, acumulando L días alterados seguidos.
    h, filas = BLOQUES['c12_17'], []
    for L in (1, 3, 7):
        prom = lambda x: pd.Series(x).rolling(L, min_periods=L).mean().shift(-(L - 1)).to_numpy()  # noqa: E731
        ul, ua = [], {k: [] for k in claves}
        for s in objetivos:
            A = X[:, :, col[s]]
            lv = lg(promedio_vecinas(X, col, vecinas[s], h))
            r = lg(resumen(A, h)) - lv
            base = base_movil(r)                       # 14 días antes del primer día de la ventana
            z = prom(r) - base
            sig = 1.4826 * np.nanmedian(np.abs(z - np.nanmedian(z)))
            ok = np.isfinite(z)
            ul.append(np.abs(z[ok] / sig))
            for d, sg in claves:
                ua[(d, sg)].append(np.abs((prom(lg(resumen(alterar(A, d, sg), h)) - lv) - base)[ok] / sig))
        filas.extend(detecciones(np.concatenate(ul), ua, dict(dias_acumulados=L, ventanas=int(sum(map(len, ul))))))
    varios = pd.DataFrame(filas)

    SAL.mkdir(parents=True, exist_ok=True)
    resumenes.to_csv(SAL / 'resumenes.csv', index=False)
    varios.to_csv(SAL / 'varios_dias.csv', index=False)
    pd.set_option('display.width', 220)
    print(resumenes.to_string(index=False), '\n')
    print(varios.to_string(index=False))


if __name__ == '__main__':
    main()
