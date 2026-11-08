"""Revisión 24: métricas y decisiones registradas.

    python rev24_metricas.py diseno        # elige τ en 2022 (criterio del registro) -> decision_tau.json
    python rev24_metricas.py calibracion   # umbrales p99 y p99.9 de Ens-Vb-X en 2023 limpio
    python rev24_metricas.py banco         # T1, T2, descriptivos y predicciones -> decision_adopcion.json
    python rev24_metricas.py despliegue    # comprobación descriptiva ago–sep 2026
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rev23 as r23  # noqa: E402
import rev23_metricas as m23  # noqa: E402
import rev24 as r  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

B = 2000
NIV = (0.01, 0.001)
DFBAR = ('d100', 'd50', 'd20')
DPPB = ('a10', 'a20', 'a40')


def etq(tau):
    return f'Ens-Vb-X{tau:.4g}'


def cargar(etapa, corrida, tareas):
    out = {}
    for t in tareas:
        z = np.load(r.SAL / etapa / f'corrida_{corrida}' / f'{r.nombre_tarea(t)}.npz')
        out[r.nombre_tarea(t)] = {k: z[k] for k in z.files}
    return out


def f1(tp, fp, fn):
    P = tp / max(tp + fp, 1)
    R_ = tp / max(tp + fn, 1)
    return 2 * P * R_ / (P + R_) if P + R_ else 0.0, P, R_


def diseno():
    T, _, _, _ = r.configurar('diseno')
    A = cargar('diseno', 'a', T)
    dets = ['Ens-Vb-R'] + [etq(t) for t in r.TAUS]
    z = A['limpia_2022']
    dias = pd.DatetimeIndex(z['dias'])
    val = np.logical_and.reduce([~np.isnan(z[d]) for d in dets])
    U = {d: float(ev.umbral_falsas_alarmas(z[d][val], 0.01)) for d in dets}
    obj = list(r.rc.objetivos())
    filas = []
    for d in dets:
        res = dict(detector=d, umbral_p99_2022=U[d], fa_limpia=float((z[d][val] > U[d]).mean()))
        for esc, tams in r.DISENO.items():
            for t in tams:
                tp = fp = fn = tpo = fno = 0
                for c in r.CALS22:
                    y, papel, _ = m23.etiquetas(r.leer_plan('diseno', c, esc), dias, obj)
                    s = A[f'{c}_{esc}_{t}'][d] > U[d]
                    m = val & np.logical_and.reduce([~np.isnan(A[f'{c}_{esc}_{t}'][k]) for k in dets])
                    tp += (s & y & m).sum(); fp += (s & ~y & m).sum(); fn += (~s & y & m).sum()
                    tpo += (s & m & (papel == 1)).sum(); fno += (~s & m & (papel == 1)).sum()
                F, P, Rr = f1(tp, fp, fn)
                res[f'F1_{esc}_{t}'] = F
                res[f'recall_original_{esc}_{t}'] = tpo / max(tpo + fno, 1)
        res['Fbar_E1'] = float(np.mean([res[f'F1_E1_{t}'] for t in DFBAR]))
        res['recall_medio_s'] = float(np.mean([res[f'recall_original_{e}_{t}'] for e in ('E2-1', 'E2-2')
                                               for t in ('d50', 'a20')]))
        filas.append(res)
    D = pd.DataFrame(filas)
    base = D[D.detector == 'Ens-Vb-R'].iloc[0]
    cand = []
    for tau in r.TAUS:
        q = D[D.detector == etq(tau)].iloc[0]
        cand.append(dict(tau=tau, cumple_E1=bool(q.Fbar_E1 >= base.Fbar_E1 - 0.01), recall_medio_s=float(q.recall_medio_s),
                         Fbar_E1=float(q.Fbar_E1)))
    ok = [c for c in cand if c['cumple_E1']]
    if ok:
        mejor = max(c['recall_medio_s'] for c in ok)
        elegido = max(c['tau'] for c in ok if c['recall_medio_s'] >= mejor - 1e-12)
    else:
        elegido = None
    dec = dict(tau=elegido, candidatos=cand, referencia=dict(Fbar_E1=float(base.Fbar_E1),
                                                             recall_medio_s=float(base.recall_medio_s)),
               avanza=elegido is not None)
    D.to_csv(r.SAL / 'diseno_2022.csv', index=False, lineterminator='\n')
    (r.SAL / 'decision_tau.json').write_text(json.dumps(dec, indent=2) + '\n', encoding='utf8')
    print(D[['detector', 'Fbar_E1', 'recall_medio_s', 'fa_limpia']].round(4).to_string(index=False))
    print(json.dumps(dec, indent=1))


def calibracion():
    z = np.load(r.SAL / 'calibracion' / 'corrida_a' / 'limpia_2023.npz')
    cal = np.load(r.rc.SAL / 'calibracion_2023.npz')
    com = cal['comun']
    tau = r.tau_elegido()
    dif_vb = float(np.nanmax(np.abs(z['Ens-Vb-R'] - cal['Ens-Vb-R'])))
    x = z[etq(tau)]
    assert (~np.isnan(x[com])).all()
    U = {str(nv): float(ev.umbral_falsas_alarmas(x[com], nv)) for nv in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)}
    out = dict(tau=tau, detector=etq(tau), estacion_dias=int(com.sum()), umbrales=U,
               Ens_Vb_R_igual_calibracion_rev22=dif_vb)
    (r.SAL / 'umbrales_2023_X.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf8')
    print(json.dumps(out, indent=1))


def umbrales_banco():
    tau = r.tau_elegido()
    Ur = r23.umbrales_red()
    Ux = json.loads((r.SAL / 'umbrales_2023_X.json').read_text())['umbrales']
    U = {}
    for nv in NIV:
        U[('Ens-Vb-R', nv)] = Ur[('Ens-Vb-R', nv)]
        U[(etq(tau), nv)] = Ux[str(nv)]
        U[('PARAAD', nv)] = r23.U_PARAAD[nv]
    return U


def banco():
    T, _, _, _ = r.configurar('banco')
    A, Bc = cargar('banco', 'a', T), cargar('banco', 'b', T)
    tau = r.tau_elegido()
    X = etq(tau)
    dets = ['Ens-Vb-R', X, 'PARAAD']
    dif = max(float(np.nanmax(np.abs(A[k][d] - Bc[k][d]))) for k in A for d in dets)
    # reproducibilidad frente a la revisión 23 (E1 y E2-4 = E2)
    rep = 0.0
    for k in A:
        if k.startswith('limpia') or not (('_E1_' in k) or ('_E2-4_' in k)):
            continue
        z = np.load(r23.SAL / 'corrida_a' / f"{k.replace('_E2-4_', '_E2_')}.npz")
        for d in ('Ens-Vb-R', 'PARAAD'):
            rep = max(rep, float(np.nanmax(np.abs(A[k][d] - z[d]))))
    obj = list(r.rc.objetivos())
    U = umbrales_banco()
    dias, val = {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in dets])
    nmes = 31
    blq = {a: (np.arange(len(obj))[None, :] * nmes + ((a - 2024) * 12 + dias[a].month.to_numpy() - 1)[:, None])
           for a in dias}
    nb = len(obj) * nmes
    lab = {(c, e): m23.etiquetas(r.leer_plan('banco', c, e), dias[r23.anio_de(c)], obj)
           for c in r23.CALS for e in r.ESC_BANCO}
    filas, C, Co = [], {}, {}
    for e in r.ESC_BANCO:
        for t in r.TAM_BANCO:
            for d in dets:
                for nv in NIV:
                    u = U[(d, nv)]
                    K = np.zeros((3, nb))
                    Ko = np.zeros((2, nb))     # estación original: tp, fn
                    tpa = fna = 0
                    det_ep = n_ep = 0
                    for c in r23.CALS:
                        a = r23.anio_de(c)
                        s = A[f'{c}_{e}_{t}'][d] > u
                        y, papel, grupo = lab[(c, e)]
                        m = val[a]
                        for q, xx in enumerate((s & y & m, s & ~y & m, ~s & y & m)):
                            K[q] += np.bincount(blq[a][xx], minlength=nb)
                        Ko[0] += np.bincount(blq[a][s & m & (papel == 1)], minlength=nb)
                        Ko[1] += np.bincount(blq[a][~s & m & (papel == 1)], minlength=nb)
                        tpa += (s & m & (papel == 2)).sum(); fna += (~s & m & (papel == 2)).sum()
                        for g in np.unique(grupo[y & m]):
                            cel = (grupo == g) & y & m
                            n_ep += 1
                            det_ep += bool(s[cel].any())
                    C[(d, nv, e, t)], Co[(d, nv, e, t)] = K, Ko
                    F, P, Rr = f1(*K.sum(1))
                    filas.append(dict(detector=d, nivel=nv, escenario=e, tamano=t, tp=int(K[0].sum()), fp=int(K[1].sum()),
                                      fn=int(K[2].sum()), precision=P, recall=Rr, F1=F,
                                      recall_original=Ko[0].sum() / max(Ko.sum(), 1),
                                      recall_anadidas=tpa / max(tpa + fna, 1) if tpa + fna else np.nan,
                                      deteccion_ataque=det_ep / max(n_ep, 1), episodios=n_ep))
    M = pd.DataFrame(filas)
    fa = []
    for d in dets:
        for nv in NIV:
            n_al = sum(int((A[f'limpia_{a}'][d][val[a]] > U[(d, nv)]).sum()) for a in dias)
            n_v = sum(int(val[a].sum()) for a in dias)
            fa.append(dict(detector=d, nivel=nv, umbral=U[(d, nv)], fa=n_al / n_v, alarmas=n_al, estacion_dias=n_v))
    FA = pd.DataFrame(fa)
    rng = np.random.default_rng([42, 24, 1])
    W = rng.multinomial(nb, np.full(nb, 1 / nb), size=B).T.astype(float)
    uno = np.ones((nb, 1))

    def f1w(d, nv, e, t, w):
        x = C[(d, nv, e, t)] @ w
        P = x[0] / np.maximum(x[0] + x[1], 1e-12)
        R_ = x[0] / np.maximum(x[0] + x[2], 1e-12)
        return np.where(P + R_ > 0, 2 * P * R_ / np.maximum(P + R_, 1e-12), 0.0)

    def reco(d, nv, e, t, w):
        x = Co[(d, nv, e, t)] @ w
        return x[0] / np.maximum(x[0] + x[1], 1e-12)

    def fbar(d, nv, e, tams, w):
        return np.mean([f1w(d, nv, e, t, w) for t in tams], axis=0)

    def ic(fn):
        p0 = float(fn(uno)[0])
        lo, hi = np.percentile(fn(W), [2.5, 97.5])
        return dict(valor=p0, ic95_inf=float(lo), ic95_sup=float(hi))

    pr = []
    for nv in NIV:
        pap = 'declarada' if nv == 0.01 else 'descriptiva'
        pr.append(dict(prueba='T1', nivel=nv, escenario='E1', tamano='Fbar', papel=pap,
                       **ic(lambda w: fbar(X, nv, 'E1', DFBAR, w) - fbar('Ens-Vb-R', nv, 'E1', DFBAR, w))))
        pr.append(dict(prueba='T2', nivel=nv, escenario='E2-1', tamano='d50', papel=pap,
                       **ic(lambda w: reco(X, nv, 'E2-1', 'd50', w) - reco('Ens-Vb-R', nv, 'E2-1', 'd50', w))))
        for e in r.ESC_BANCO:
            for t in r.TAM_BANCO:
                pr.append(dict(prueba='dRecall_original_X-R', nivel=nv, escenario=e, tamano=t, papel='descriptiva',
                               **ic(lambda w, e=e, t=t: reco(X, nv, e, t, w) - reco('Ens-Vb-R', nv, e, t, w))))
            for tams, nm in ((DFBAR, 'Fbar'), (DPPB, 'Fbar_ppb')):
                pr.append(dict(prueba=f'd{nm}_X-R', nivel=nv, escenario=e, tamano=nm, papel='descriptiva',
                               **ic(lambda w, e=e, tams=tams: fbar(X, nv, e, tams, w) - fbar('Ens-Vb-R', nv, e, tams, w))))
    PR = pd.DataFrame(pr)
    q = lambda nm, nv=0.01: PR[(PR.prueba == nm) & (PR.nivel == nv)].iloc[0]  # noqa: E731
    Ro = lambda d, e, t: float(M[(M.detector == d) & (M.nivel == 0.01) & (M.escenario == e) & (M.tamano == t)].recall_original.iloc[0])  # noqa: E731
    t1, t2 = q('T1'), q('T2')
    T1 = bool(t1.ic95_inf > -0.02)
    T2 = bool(t2.ic95_inf > 0)
    prec = lambda d, t: float(M[(M.detector == d) & (M.nivel == 0.01) & (M.escenario == 'E1') & (M.tamano == t)].precision.iloc[0])  # noqa: E731
    dprec = float(np.mean([prec(X, t) - prec('Ens-Vb-R', t) for t in DFBAR]))
    pred = {
        '1_T1_pasa': [[t1.ic95_inf, t1.ic95_sup], T1],
        '2_T2_pasa_y_recall_E2-1_d50>=0.65': [[Ro('Ens-Vb-R', 'E2-1', 'd50'), Ro(X, 'E2-1', 'd50')],
                                              T2 and Ro(X, 'E2-1', 'd50') >= 0.65],
        '3_recall_E2-2_d50>=0.45': [[Ro('Ens-Vb-R', 'E2-2', 'd50'), Ro(X, 'E2-2', 'd50')], Ro(X, 'E2-2', 'd50') >= 0.45],
        '4_E2-4_sin_cambio(<0.03)': [[Ro('Ens-Vb-R', 'E2-4', 'd50'), Ro(X, 'E2-4', 'd50')],
                                     abs(Ro(X, 'E2-4', 'd50') - Ro('Ens-Vb-R', 'E2-4', 'd50')) < 0.03],
        '5_precision_E1_baja<=0.02': [dprec, -0.02 <= dprec <= 0],
        '6_ppb_ganancia_parecida(±0.10)': [[Ro(X, 'E2-1', 'a20') - Ro('Ens-Vb-R', 'E2-1', 'a20'),
                                            Ro(X, 'E2-1', 'd50') - Ro('Ens-Vb-R', 'E2-1', 'd50')],
                                           abs((Ro(X, 'E2-1', 'a20') - Ro('Ens-Vb-R', 'E2-1', 'a20'))
                                               - (Ro(X, 'E2-1', 'd50') - Ro('Ens-Vb-R', 'E2-1', 'd50'))) <= 0.10],
    }
    pred = {k: dict(valor=v[0], se_cumple=bool(v[1])) for k, v in pred.items()}
    adop = 'sustituye a Ens-Vb-R' if (T1 and T2) else ('variante descriptiva' if T1 else 'no se adopta')
    S = r.SAL
    M.to_csv(S / 'metricas_banco.csv', index=False, lineterminator='\n')
    FA.to_csv(S / 'falsas_alarmas_banco.csv', index=False, lineterminator='\n')
    PR.to_csv(S / 'pruebas_banco.csv', index=False, lineterminator='\n')
    (S / 'predicciones.json').write_text(json.dumps(pred, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    dec = dict(tau=tau, detector=X, T1=T1, T2=T2, adopcion=adop, corridas_identicas=dif == 0.0, diferencia_max=dif,
               Vb_y_PARAAD_igual_rev23=rep, estacion_dias_evaluables={a: int(val[a].sum()) for a in val})
    (S / 'decision_adopcion.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(dec, ensure_ascii=False))
    print(PR[PR.papel == 'declarada'].round(4).to_string(index=False))
    print(json.dumps(pred, indent=1, ensure_ascii=False))


def despliegue():
    import rev22_examen as rx
    T, _, _, _ = r.configurar('despliegue')
    A = cargar('despliegue', 'a', T)
    tau = r.tau_elegido()
    X = etq(tau)
    dets = ['Ens-Vb-R', X]
    U = umbrales_banco()
    ex = np.load(rx.EX / 'corrida_a' / 'diario.npz')
    dif_ex = max(float(np.nanmax(np.abs(A[f'despliegue_{k:02d}_E1_d{d}']['Ens-Vb-R'] - ex[f'Ens-Vb-R__c{k:02d}_d{d}'])))
                 for k in range(1, rx.N_CAL + 1) for d in rx.DELTAS)
    obj = list(r.rc.objetivos())
    z = A['limpia_2026']
    dias = pd.DatetimeIndex(z['dias'])
    val = np.logical_and.reduce([~np.isnan(z[d]) for d in dets])
    lab = rx.etiquetas(dias, obj)
    mes = dias.month.to_numpy()
    meses = sorted(set(mes))
    nb = len(obj) * len(meses)
    filas, C = [], {}
    for d in dets:
        for nv in NIV:
            u = U[(d, nv)]
            r_ = dict(detector=d, nivel=nv, fa_limpia=float((z[d][val] > u).mean()))
            for dd in rx.DELTAS:
                K = np.zeros((3, len(obj), len(meses)))
                for k in range(1, rx.N_CAL + 1):
                    s = A[f'despliegue_{k:02d}_E1_d{dd}'][d] > u
                    y = lab[k]['y']
                    for q_, xx in enumerate((s & y & val, s & ~y & val, ~s & y & val)):
                        for i, mo in enumerate(meses):
                            K[q_, :, i] += xx[mes == mo].sum(0)
                C[(d, nv, dd)] = K.reshape(3, -1)
                F, P, Rr = f1(*K.reshape(3, -1).sum(1))
                r_.update({f'F1_{dd}': F, f'recall_{dd}': Rr, f'precision_{dd}': P})
            r_['Fbar'] = float(np.mean([r_[f'F1_{dd}'] for dd in (100, 50, 20)]))
            filas.append(r_)
    D = pd.DataFrame(filas)
    rng = np.random.default_rng([42, 24, 2])
    W = rng.multinomial(nb, np.full(nb, 1 / nb), size=B).T.astype(float)

    def fb(d, nv, w):
        f = []
        for dd in (100, 50, 20):
            x = C[(d, nv, dd)] @ w
            P = x[0] / np.maximum(x[0] + x[1], 1e-12)
            R_ = x[0] / np.maximum(x[0] + x[2], 1e-12)
            f.append(np.where(P + R_ > 0, 2 * P * R_ / np.maximum(P + R_, 1e-12), 0))
        return np.mean(f, axis=0)
    ics = []
    for nv in NIV:
        d0 = float((fb(X, nv, np.ones((nb, 1))) - fb('Ens-Vb-R', nv, np.ones((nb, 1))))[0])
        lo, hi = np.percentile(fb(X, nv, W) - fb('Ens-Vb-R', nv, W), [2.5, 97.5])
        ics.append(dict(nivel=nv, dFbar_X_R=d0, ic95_inf=float(lo), ic95_sup=float(hi)))
    D.to_csv(r.SAL / 'despliegue_2026.csv', index=False, lineterminator='\n')
    out = dict(intervalos=ics, Ens_Vb_R_igual_examen_rev22=dif_ex, estacion_dias_limpias=int(val.sum()))
    (r.SAL / 'despliegue_2026.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf8')
    print(D[['detector', 'nivel', 'fa_limpia', 'Fbar', 'F1_100', 'F1_50', 'F1_20']].round(3).to_string(index=False))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'diseno': diseno, 'calibracion': calibracion, 'banco': banco, 'despliegue': despliegue}[sys.argv[1]]()
