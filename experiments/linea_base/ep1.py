"""Revisión EP1: decisión por episodio con puntajes estandarizados por estación (solo 2022, sin entrenar).

Registro previo: docs/registro_previo_EP1_decision_episodio_Vb.md (aprobado el 2026-11-04).
Usa los puntajes guardados de LB1 (results/linea_base/lb1/puntajes_2022.npz).

Estandarización: p(s, d) = (1 + #{días limpios de calibración de s con puntaje ≥ x}) / (n_s + 1), e = −ln p.
Calibración cruzada: los meses pares usan los días limpios de los meses impares de 2022, y al revés.
Reglas: D (diario, e), C (CUSUM con k = 2, sin reinicio, S se conserva en días sin puntaje) y
R (2 de 3: segundo mayor e entre los últimos 3 días con puntaje). Cada regla alerta si su estadístico
supera un umbral elegido para que el 1 % o el 0.1 % de las estación-días limpias de calibración alerten.

Uso:  python experiments/linea_base/ep1.py   → results/linea_base/ep1/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comun as cm  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import evaluacion_red as ev  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/ep1'
PUNTAJES = cm.RAIZ / 'results/linea_base/lb1/puntajes_2022.npz'
MODELOS = ['V0r', 'Vbr', 'L0guardado']
REGLAS = ['D', 'C', 'R']
NIVELES = (0.01, 0.001)
K_CUSUM = 2.0
LIMPIA = 'limpia_2020_2022'


def cargar():
    z = np.load(PUNTAJES, allow_pickle=False)
    dias = pd.DatetimeIndex(z['dias'])
    S = {(mn, k): z[f'{mn}__{k}'] for mn in MODELOS for k in cm.nombres_eval()}
    return dias, S


def sorpresa(x: np.ndarray, cal: list[np.ndarray]) -> np.ndarray:
    """e = −ln p por estación, con la referencia `cal[j]` (ordenada) de cada estación j."""
    e = np.full(x.shape, np.nan)
    for j, c in enumerate(cal):
        ok = ~np.isnan(x[:, j])
        mayores = len(c) - np.searchsorted(c, x[ok, j], side='left')
        e[ok, j] = -np.log((1 + mayores) / (len(c) + 1))
    return e


def estadistico(e: np.ndarray, regla: str) -> np.ndarray:
    if regla == 'D':
        return e
    T = np.full(e.shape, np.nan)
    for j in range(e.shape[1]):
        s, ult = 0.0, []
        for d in range(e.shape[0]):
            v = e[d, j]
            if np.isnan(v):
                continue
            if regla == 'C':
                s = max(0.0, s + v - K_CUSUM)
                T[d, j] = s
            else:
                ult = (ult + [v])[-3:]
                T[d, j] = sorted(ult)[-2] if len(ult) >= 2 else -np.inf
    return T


def alertas(S, dias, comun, mn, regla, nivel):
    """Alertas día × estación de cada matriz con calibración cruzada por meses; también el umbral por pliegue."""
    mes = dias.month.to_numpy()
    pliegues = [(mes % 2 == 1, mes % 2 == 0), (mes % 2 == 0, mes % 2 == 1)]
    L, cl = S[(mn, LIMPIA)], comun[LIMPIA]
    A, umbrales = {k: np.zeros(L.shape, bool) for k in cm.nombres_eval()}, []
    for ajuste, medida in pliegues:
        cal = [np.sort(L[ajuste & cl[:, j], j]) for j in range(L.shape[1])]
        T_l = estadistico(sorpresa(L, cal), regla)
        t = ev.umbral_falsas_alarmas(T_l[ajuste[:, None] & cl], nivel)
        umbrales.append(t)
        for k in cm.nombres_eval():
            T = T_l if k == LIMPIA else estadistico(sorpresa(S[(mn, k)], cal), regla)
            A[k][medida] = (T > t)[medida]
    return A, umbrales


def resumen(A, comun, lab, dias):
    cl = comun[LIMPIA]
    r = dict(fa_limpia=float(A[LIMPIA][cl].mean()))
    for d in cm.DELTAS_EVAL:
        tp = fp = fn = 0
        m1 = [0, 0]; detect, retardo = [], []
        for c, L in lab.items():
            k = f'{c}_d{d}'
            a, y, msk = A[k], L['y'], comun[k] & cl
            tp += (a & y & msk).sum(); fp += (a & ~y & msk).sum(); fn += (~a & y & msk).sum()
            post = ~y & msk & (L['tras'] <= 14)
            m1[0] += (a & post).sum(); m1[1] += post.sum()
            for e in L['plan'].itertuples():
                if e.inicio < pd.Timestamp('2022-01-01') or e.estacion not in L['objetivos']:
                    continue
                j = L['objetivos'].index(e.estacion)
                dentro = (dias >= e.inicio.normalize()) & (dias <= e.fin.normalize())
                hit = np.flatnonzero(a[dentro, j])
                detect.append(len(hit) > 0)
                if len(hit):
                    retardo.append(hit[0] + 1)
        P = tp / (tp + fp) if tp + fp else 0.0
        R = tp / (tp + fn)
        r.update({f'F1_{d}': 2 * P * R / (P + R) if P + R else 0.0, f'recall_{d}': R, f'precision_{d}': P,
                  f'M1_{d}': m1[0] / m1[1], f'episodios_detectados_{d}': float(np.mean(detect)),
                  f'retardo_mediano_{d}': float(np.median(retardo)) if retardo else np.nan, f'n_episodios_{d}': len(detect)})
    r['Fbar'] = float(np.mean([r[f'F1_{d}'] for d in cm.DELTAS_EVAL]))
    return r


def bootstrap(Aa, Ab, comun, lab, dias, n=2000):
    cl = comun[LIMPIA]
    mes = dias.month.to_numpy()
    nobj = Aa[LIMPIA].shape[1]

    def conteos(A):
        C = np.zeros((len(cm.DELTAS_EVAL), 3, nobj, 12))
        for di, d in enumerate(cm.DELTAS_EVAL):
            for c, L in lab.items():
                k = f'{c}_d{d}'
                a, y, msk = A[k], L['y'], comun[k] & cl
                for q, x in enumerate((a & y & msk, a & ~y & msk, ~a & y & msk)):
                    for mo in range(12):
                        C[di, q, :, mo] += x[mes == mo + 1].sum(0)
        return C.reshape(len(cm.DELTAS_EVAL), 3, -1)

    def fbar(C, w):
        t = np.einsum('dqb,bn->dqn', C, w)
        P = t[:, 0] / np.maximum(t[:, 0] + t[:, 1], 1e-12)
        R = t[:, 0] / np.maximum(t[:, 0] + t[:, 2], 1e-12)
        return np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0).mean(0)

    Ca, Cb = conteos(Aa), conteos(Ab)
    nb = Ca.shape[2]
    rng = np.random.default_rng(cm.SEMILLA_BOOT)
    W = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb) for _ in range(n)], axis=1).astype(float)
    uno = np.ones((nb, 1))
    dif = fbar(Ca, W) - fbar(Cb, W)
    return float(fbar(Ca, uno)[0] - fbar(Cb, uno)[0]), float(np.quantile(dif, 0.025)), float(np.quantile(dif, 0.975))


def main():
    from generar_planes import alterables_v4
    dias, S = cargar()
    objetivos = alterables_v4()
    comun = {k: np.logical_and.reduce([~np.isnan(S[(mn, k)]) for mn in MODELOS]) for k in cm.nombres_eval()}
    lab = cm.etiquetas(dict(objetivos=objetivos), dias)
    for L in lab.values():
        L['objetivos'] = objetivos
    filas, AL, umb = [], {}, {}
    for nivel in NIVELES:
        for mn in MODELOS:
            for regla in REGLAS:
                A, u = alertas(S, dias, comun, mn, regla, nivel)
                AL[(nivel, mn, regla)] = A
                umb[f'{mn}_{regla}_{nivel}'] = u
                filas.append(dict(nivel=nivel, modelo=mn, regla=regla, **resumen(A, comun, lab, dias)))
    SAL.mkdir(parents=True, exist_ok=True)
    met = pd.DataFrame(filas)
    met.to_csv(SAL / 'metricas.csv', index=False)
    boot = []
    for nivel in NIVELES:
        for (a, b) in ((('Vbr', 'C'), ('Vbr', 'D')), (('Vbr', 'R'), ('Vbr', 'D')), (('V0r', 'C'), ('V0r', 'D')),
                       (('Vbr', 'C'), ('V0r', 'C'))):
            dF, lo, hi = bootstrap(AL[(nivel, *a)], AL[(nivel, *b)], comun, lab, dias)
            boot.append(dict(nivel=nivel, a='-'.join(a), b='-'.join(b), dFbar=dF, ic_inf=lo, ic_sup=hi))
    pd.DataFrame(boot).to_csv(SAL / 'bootstrap.csv', index=False)
    (SAL / 'umbrales.json').write_text(json.dumps(umb, indent=2))
    cols = ['nivel', 'modelo', 'regla', 'fa_limpia', 'Fbar', 'F1_100', 'F1_50', 'F1_20', 'recall_50', 'precision_50', 'M1_50',
            'episodios_detectados_50', 'retardo_mediano_50']
    print(met[cols].round(4).to_string(index=False))
    print(pd.DataFrame(boot).round(4).to_string(index=False))


if __name__ == '__main__':
    main()
