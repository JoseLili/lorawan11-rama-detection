"""Exploración registrada del 2026-11-04 con L0 congelado: P1 (líneas base), P4 (umbral por estación), P5 (CUSUM).

Registro previo: docs/registro_previo_linea_base_2022.md. Sólo 2022, sin entrenar. El modelo es el
L0 de selección δ = 50 % (revisión 14) cargado de disco, con la escala a14 de V0 para todas las bases.

Uso (desde la raíz del repo):

    python experiments/linea_base/explorar_2022.py

Salidas en results/linea_base/exploracion_2022/: p1_metricas.csv, p4_p5.csv y control_v0.json
(diferencia máxima contra `dias_2022.csv.gz` guardado).
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
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/exploracion_2022'
U_COMPUERTA, TOPE, INICIO_COMPUERTA = 0.0578, 10, '2021-12-01'
N_AJUSTE = 200


def compuerta(ctx, modelo, xs: dict, b0s: dict):
    """Va, día por día y de forma causal, para todas las matrices a la vez. Devuelve bases y diagnóstico."""
    est, obj = ctx['estaciones'], ctx['objetivos']
    n, idx = len(est), ctx['index']
    loc = {s: ll.indices_locales(est, ctx['vecinas'], s) for s in obj}
    oi = [est.index(s) for s in obj]
    d0, nd = int((pd.Timestamp(INICIO_COMPUERTA) - idx[0]).days), len(idx) // 24
    K = list(xs)
    V = {k: lb.valores(xs[k], est) for k in K}
    Vd = {k: V[k].reshape(nd, 24, n) for k in K}
    msk = {k: xs[k][[f'{s}_mascara' for s in obj]].to_numpy() == 1 for k in K}
    B = {k: b0s[k].copy() for k in K}
    acep = {k: np.ones((nd, n), bool) for k in K}
    racha = {k: np.zeros(n, int) for k in K}
    topes = {k: 0 for k in K}
    for D in range(d0, nd):
        for k in K:
            for j in range(n):
                ds = np.flatnonzero(acep[k][:D, j])[-14:]
                with np.errstate(all='ignore'):
                    b = np.nanmean(Vd[k][ds, :, j], axis=0)
                B[k][D * 24:(D + 1) * 24, j] = np.where(np.isnan(b), b0s[k][D * 24:(D + 1) * 24, j], b)
        X = []
        for k in K:
            r0 = (D - 1) * 24
            F = lb.entradas(xs[k].iloc[r0:r0 + 48], B[k][r0:r0 + 48], est, ctx['sigma'], ctx['escala_v0'],
                            ctx['vec'], V[k][r0:r0 + 48])
            W = np.stack([F[i + 1:i + 25] for i in range(24)])
            X.append(np.concatenate([W[:, :, loc[s]] for s in obj]))
        p = modelo.predict(np.concatenate(X), batch_size=8192, verbose=0).astype(np.float64).reshape(len(K), len(obj), 24)
        for a, k in enumerate(K):
            mk = msk[k][D * 24:(D + 1) * 24].T
            nv = mk.sum(1)
            sc = np.where(nv >= 12, np.where(mk, p[a], 0).sum(1) / np.maximum(nv, 1), np.nan)
            for q, j in enumerate(oi):
                alerta = sc[q] > U_COMPUERTA
                if alerta and racha[k][j] < TOPE:
                    acep[k][D, j] = False
                    racha[k][j] += 1
                else:
                    topes[k] += int(alerta)
                    racha[k][j] = 0
    diag = dict(topes_total=int(sum(topes.values())), topes_limpia=topes['limpia_2020_2022'],
                excluidos_limpia=int((~acep['limpia_2020_2022'][d0:]).sum()))
    return B, diag


def umbral(a):
    return ev.umbral_falsas_alarmas(a[~np.isnan(a)], 0.01)


def p4_p5(S0, lab, dias, comun):
    """P4 y P5 sobre los puntajes V0, con ajuste en meses impares y medición en pares (y al revés)."""
    mes = pd.DatetimeIndex(dias).month.to_numpy()
    folds = [(mes % 2 == 1, mes % 2 == 0), (mes % 2 == 0, mes % 2 == 1)]
    CL, cl = S0['limpia_2020_2022'], comun['limpia_2020_2022']
    nobj = CL.shape[1]

    def umbrales(fit, modo):
        uc = umbral(np.where(cl & fit[:, None], CL, np.nan).ravel())
        if modo == 'comun':
            return np.full(nobj, uc)
        out = []
        for j in range(nobj):
            a = CL[fit & cl[:, j], j]
            w = len(a) / (len(a) + N_AJUSTE)
            out.append(w * umbral(a) + (1 - w) * uc)
        return np.array(out)

    def cusum(S, k):
        Y, s, out = np.log(S), np.zeros(S.shape[1]), np.full(S.shape, np.nan)
        for t in range(len(Y)):
            ok = ~np.isnan(Y[t])
            s[ok] = np.maximum(0, s[ok] + Y[t][ok] - k)
            out[t] = np.where(ok, s, np.nan)
        return out

    def alertas(nombre, modo):
        A = np.zeros_like(S0[nombre], bool)
        for fit, med in folds:
            if modo == 'cusum':
                k = np.nanquantile(np.log(np.where(cl & fit[:, None], CL, np.nan)), 0.90)
                h = umbral(np.where(cl & fit[:, None], cusum(CL, k), np.nan).ravel())
                A[med] = (cusum(S0[nombre], k) > h)[med]
            else:
                A[med] = S0[nombre][med] > umbrales(fit, modo)[None, :]
        return A

    filas = []
    for modo in ('comun', 'estacion', 'cusum'):
        Al = alertas('limpia_2020_2022', modo)
        fa = np.array([Al[cl[:, j], j].mean() for j in range(nobj)])
        r = dict(modo=modo, sd_FA=fa.std(), n_0=int((fa == 0).sum()), n_gt2=int((fa > 0.02).sum()), FA_limpia=Al[cl].mean())
        for d in cm.DELTAS_EVAL:
            tp = fp = fn = 0
            for c, L in lab.items():
                k = f'{c}_d{d}'
                A, msk, y = alertas(k, modo), comun[k] & cl, L['y']
                tp += (A & y & msk).sum(); fp += (A & ~y & msk).sum(); fn += (~A & y & msk).sum()
            P, R = tp / (tp + fp), tp / (tp + fn)
            r[f'F1_{d}'] = 2 * P * R / (P + R) if P + R else 0.0
        r['Fbar'] = float(np.mean([r[f'F1_{d}'] for d in cm.DELTAS_EVAL]))
        filas.append(r)
    return pd.DataFrame(filas)


def main():
    import keras
    from entrenar_lstm_estacion import leer_dias
    ctx = cm.contexto()
    nombres = cm.nombres_eval()
    cm.asegurar_matrices(nombres)
    modelo = keras.models.load_model(cm.SAL_RED / 'lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras',
                                     compile=False)
    est = ctx['estaciones']
    V0l = lb.valores(ctx['limpia'], est)
    tau = lb.tau_vc(V0l, lb.base_v0(ctx['limpia'], est), ctx['index'], cm.SELECCION[1])
    xs = {k: cm.leer(k) for k in nombres}
    bs = {k: cm.bases(ctx, x, tau) for k, x in xs.items()}
    Ba, diag = compuerta(ctx, modelo, xs, {k: b['V0'] for k, b in bs.items()})
    S, dias = {}, None
    for k, x in xs.items():
        for v in ('V0', 'Vb', 'Vc', 'Va'):
            base = Ba[k] if v == 'Va' else bs[k][v]
            dia = cm.puntuar(ctx, modelo, lb.entradas(x, base, est, ctx['sigma'], ctx['escala_v0'], ctx['vec']), x)
            S[(v, k)], dias = dia.to_numpy(), dia.index
    guardado = leer_dias(cm.SAL_RED / 'lstm_local_examen/c20/d50/seleccion/dias_2022.csv.gz')
    ref = {'limpia_2020_2022': 'limpia_2022'} | {f'entrenamiento_{i:02d}_d50': f'entrenamiento_{i:02d}' for i in range(1, 11)}
    dif = max(float(np.nanmax(np.abs(S[('V0', k)] - guardado[r]['promedio_dia'][ctx['objetivos']].to_numpy())))
              for k, r in ref.items())
    SAL.mkdir(parents=True, exist_ok=True)
    (SAL / 'control_v0.json').write_text(json.dumps(dict(diferencia_maxima_v0=dif, **diag), indent=2))
    lab = cm.etiquetas(ctx, dias)
    variantes = ['V0', 'Va', 'Vb', 'Vc']
    cm.metricas(S, variantes, lab, 0.01).to_csv(SAL / 'p1_metricas.csv', index=False)
    comun = {k: np.logical_and.reduce([~np.isnan(S[(v, k)]) for v in variantes]) for k in nombres}
    p4_p5({k: S[('V0', k)] for k in nombres}, lab, dias, comun).to_csv(SAL / 'p4_p5.csv', index=False)
    print(json.dumps(dict(diferencia_maxima_v0=dif, **diag)))
    print(pd.read_csv(SAL / 'p1_metricas.csv')[['modelo', 'umbral', 'Fbar', 'M1_50', 'M2_50', 'PRAUC_50']].round(4).to_string(index=False))
    print(pd.read_csv(SAL / 'p4_p5.csv').round(4).to_string(index=False))


if __name__ == '__main__':
    main()
