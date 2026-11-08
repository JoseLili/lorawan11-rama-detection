"""Revisión 23b (D1): recall por semana, rebote, Q1–Q4 y predicciones 1–7.

    python rev23b_metricas.py

Lee results/linea_base/rev23b/corrida_a y corrida_b (deben ser idénticas) y escribe en results/linea_base/rev23b/:
por_semana.csv, rebote.csv, episodios.csv, resumen.csv, pruebas.csv, predicciones.json y decision.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rev23 as r23  # noqa: E402
import rev23b as d1  # noqa: E402
import rev24 as r24  # noqa: E402

B = 2000
NIV = (0.01, 0.001)


def detectores():
    dets = ['Ens-Vb-R', 'Ens-V0-R', 'L0unico', 'R3', 'PARAAD']
    U = {}
    Ur = r23.umbrales_red()
    u3 = r23.umbrales_r3()
    for nv in NIV:
        for d in ('Ens-Vb-R', 'Ens-V0-R', 'L0unico'):
            U[(d, nv)] = Ur[(d, nv)]
        U[('R3', nv)] = u3[nv]
        U[('PARAAD', nv)] = r23.U_PARAAD[nv]
    X = None
    if any(isinstance(g, tuple) for g in d1.grupos()):
        X = f'Ens-Vb-X{r24.tau_elegido():.4g}'
        Ux = json.loads((r24.SAL / 'umbrales_2023_X.json').read_text())['umbrales']
        dets.append(X)
        for nv in NIV:
            U[(X, nv)] = Ux[str(nv)]
    return dets, U, X


def cargar(corrida):
    out = {}
    for t in d1.tareas():
        z = np.load(d1.SAL / f'corrida_{corrida}' / f'{d1.nombre_tarea(t)}.npz')
        out[d1.nombre_tarea(t)] = {k: z[k] for k in z.files}
    return out


def main():
    dets, U, X = detectores()
    A, Bc = cargar('a'), cargar('b')
    dif = max(float(np.nanmax(np.abs(A[k][d] - Bc[k][d]))) for k in A for d in dets)
    obj = list(r23.rc.objetivos())
    dias, val = {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in dets])
    nmes = 31
    blq = {a: (np.arange(len(obj))[None, :] * nmes + ((a - 2024) * 12 + dias[a].month.to_numpy() - 1)[:, None])
           for a in dias}
    nb = len(obj) * nmes
    # semana dentro del episodio (1–8) y semana posterior al fin (1–8), por estación-día y calendario
    sem, post, epi = {}, {}, {}
    for c in r23.CALS:
        a = r23.anio_de(c)
        S_in = np.zeros((len(dias[a]), len(obj)), np.int8)
        S_po = np.zeros_like(S_in)
        E_id = np.full(S_in.shape, -1, np.int32)
        pos = {d: i for i, d in enumerate(dias[a])}
        for e in d1.leer_plan(c).itertuples():
            j = obj.index(e.estacion)
            i0 = pos[e.inicio.normalize()]
            for k in range(d1.L):
                S_in[i0 + k, j] = k // 7 + 1
                E_id[i0 + k, j] = int(e.episodio)
            for k in range(56):
                i = i0 + d1.L + k
                if i < len(dias[a]):
                    S_po[i, j] = k // 7 + 1
        sem[c], post[c], epi[c] = S_in, S_po, E_id
    # clean rates per block (once per year) for each detector/level
    Kc = {}
    for d in dets:
        for nv in NIV:
            K = np.zeros((2, nb))
            for a in dias:
                s = A[f'limpia_{a}'][d] > U[(d, nv)]
                K[0] += np.bincount(blq[a][s & val[a]], minlength=nb)
                K[1] += np.bincount(blq[a][val[a]], minlength=nb)
            Kc[(d, nv)] = K
    filas_s, filas_r, filas_e, res = [], [], [], []
    Cw, Cp = {}, {}
    for f in d1.FORMAS:
        for Aa in d1.AMPS:
            for d in dets:
                for nv in NIV:
                    u = U[(d, nv)]
                    Kw = np.zeros((8, 2, nb))      # semana × [tp, fn]
                    Kp = np.zeros((8, 2, nb))      # semana posterior × [alarmas, n]
                    fp = 0
                    n_ep = det_ep = 0
                    prim = []
                    for c in r23.CALS:
                        a = r23.anio_de(c)
                        s = A[f'{c}_{f}_a{Aa}'][d] > u
                        m = val[a]
                        y = sem[c] > 0
                        for w in range(1, 9):
                            sel = (sem[c] == w) & m
                            Kw[w - 1, 0] += np.bincount(blq[a][sel & s], minlength=nb)
                            Kw[w - 1, 1] += np.bincount(blq[a][sel & ~s], minlength=nb)
                            selp = (post[c] == w) & m
                            Kp[w - 1, 0] += np.bincount(blq[a][selp & s], minlength=nb)
                            Kp[w - 1, 1] += np.bincount(blq[a][selp], minlength=nb)
                        fp += int((s & ~y & m).sum())
                        for g in np.unique(epi[c][y & m]):
                            cel = (epi[c] == g) & m
                            n_ep += 1
                            hit = np.flatnonzero(s[cel])
                            if len(hit):
                                det_ep += 1
                                ii = np.flatnonzero(cel.ravel())
                                prim.append(int(sem[c].ravel()[ii[hit[0]]]))
                    Cw[(f, Aa, d, nv)], Cp[(f, Aa, d, nv)] = Kw, Kp
                    tp, fn = Kw[:, 0].sum(), Kw[:, 1].sum()
                    P = tp / max(tp + fp, 1)
                    Rr = tp / max(tp + fn, 1)
                    fa_l = Kc[(d, nv)][0].sum() / Kc[(d, nv)][1].sum()
                    res.append(dict(forma=f, A=Aa, detector=d, nivel=nv, recall=Rr, precision=P,
                                    F1=2 * P * Rr / (P + Rr) if P + Rr else 0.0, episodios=n_ep,
                                    deteccion_episodio=det_ep / max(n_ep, 1),
                                    semana_mediana_primera_alarma=float(np.median(prim)) if prim else np.nan))
                    dur = 0
                    for w in range(8):
                        tp_w, fn_w = Kw[w, 0].sum(), Kw[w, 1].sum()
                        al_w, n_w = Kp[w, 0].sum(), Kp[w, 1].sum()
                        filas_s.append(dict(forma=f, A=Aa, detector=d, nivel=nv, semana=w + 1,
                                            recall=tp_w / max(tp_w + fn_w, 1), positivos=int(tp_w + fn_w)))
                        tasa = al_w / max(n_w, 1)
                        filas_r.append(dict(forma=f, A=Aa, detector=d, nivel=nv, semana_posterior=w + 1, tasa=tasa,
                                            fa_limpia=fa_l, razon=tasa / fa_l if fa_l else np.nan, dias=int(n_w)))
                    for w in range(8):
                        t_ = Kp[w, 0].sum() / max(Kp[w, 1].sum(), 1)
                        if t_ >= 2 * fa_l:
                            dur += 1
                        else:
                            break
                    res[-1]['duracion_rebote_semanas'] = dur
    S = pd.DataFrame(filas_s)
    Rb = pd.DataFrame(filas_r)
    RS = pd.DataFrame(res)
    CR = []
    for c in r23.CALS:
        for f in d1.FORMAS:
            for Aa in d1.AMPS:
                CR.append(dict(forma=f, A=Aa, calendario=c, **{f'sem{w + 1}': v for w, v in enumerate(
                    json.loads(str(A[f'{c}_{f}_a{Aa}']['info']))['cambio_por_semana'])}))
    CR = pd.DataFrame(CR).groupby(['forma', 'A']).mean(numeric_only=True).reset_index()
    rng = np.random.default_rng([42, 23, 2])
    W = rng.multinomial(nb, np.full(nb, 1 / nb), size=B).T.astype(float)
    uno = np.ones((nb, 1))

    def rec(f, Aa, d, nv, semanas, w):
        K = Cw[(f, Aa, d, nv)][[s - 1 for s in semanas]].sum(0) @ w
        return K[0] / np.maximum(K[0] + K[1], 1e-12)

    def rebote(f, Aa, d, nv, semanas, w):
        K = Cp[(f, Aa, d, nv)][[s - 1 for s in semanas]].sum(0) @ w
        Kl = Kc[(d, nv)] @ w
        return K[0] / np.maximum(K[1], 1e-12) - Kl[0] / np.maximum(Kl[1], 1e-12)

    def ic(fn):
        p0 = float(fn(uno)[0])
        lo, hi = np.percentile(fn(W), [2.5, 97.5])
        return dict(valor=p0, ic95_inf=float(lo), ic95_sup=float(hi))

    pr = []
    for nv in NIV:
        pap = 'declarada' if nv == 0.01 else 'descriptiva'
        pr.append(dict(prueba='Q1', nivel=nv, papel=pap, **ic(lambda w: rec('escalon', 20, 'PARAAD', nv, range(5, 9), w)
                                                                 - rec('escalon', 20, 'Ens-Vb-R', nv, range(5, 9), w))))
        pr.append(dict(prueba='Q2', nivel=nv, papel=pap, **ic(lambda w: rec('rampa28', 20, 'Ens-Vb-R', nv, range(1, 5), w)
                                                                 - rec('rampa28', 20, 'Ens-V0-R', nv, range(1, 5), w))))
        pr.append(dict(prueba='Q3', nivel=nv, papel=pap, **ic(lambda w: rebote('escalon', 20, 'Ens-Vb-R', nv, range(1, 5), w))))
        pr.append(dict(prueba='Q4', nivel=nv, papel=pap, **ic(lambda w: rec('deriva56', 40, 'Ens-Vb-R', nv, range(1, 9), w)
                                                                 - rec('deriva56', 40, 'PARAAD', nv, range(1, 9), w))))
        for d in dets:
            if d == 'Ens-Vb-R':
                continue
            for f in d1.FORMAS:
                for Aa in d1.AMPS:
                    for nm, sems in (('sem1-4', range(1, 5)), ('sem5-8', range(5, 9))):
                        pr.append(dict(prueba=f'dRecall_{nm}_{d}-Vb', nivel=nv, papel='descriptiva', forma=f, A=Aa,
                                       **ic(lambda w, d=d, f=f, Aa=Aa, sems=sems: rec(f, Aa, d, nv, sems, w)
                                            - rec(f, Aa, 'Ens-Vb-R', nv, sems, w))))
    PR = pd.DataFrame(pr)
    q = lambda nm: PR[(PR.prueba == nm) & (PR.nivel == 0.01)].iloc[0]  # noqa: E731
    rs = lambda f, Aa, d, s_: float(S[(S.forma == f) & (S.A == Aa) & (S.detector == d) & (S.nivel == 0.01)
                                      & S.semana.isin(list(s_))].pipe(lambda g: (g.recall * g.positivos).sum() / g.positivos.sum()))  # noqa: E731
    dur = lambda d: int(RS[(RS.forma == 'escalon') & (RS.A == 20) & (RS.detector == d) & (RS.nivel == 0.01)].duracion_rebote_semanas.iloc[0])  # noqa: E731
    razon14 = float(Rb[(Rb.forma == 'escalon') & (Rb.A == 20) & (Rb.detector == 'Ens-Vb-R') & (Rb.nivel == 0.01)
                       & Rb.semana_posterior.isin([1, 2, 3, 4])].pipe(lambda g: (g.tasa * g.dias).sum() / g.dias.sum() / g.fa_limpia.iloc[0]))
    rec_all = lambda f, Aa, d: float(RS[(RS.forma == f) & (RS.A == Aa) & (RS.detector == d) & (RS.nivel == 0.01)].recall.iloc[0])  # noqa: E731
    pred = {
        '1_Vb_escalon20_sem1>=0.7_sem5-8<=0.3': [[rs('escalon', 20, 'Ens-Vb-R', [1]), rs('escalon', 20, 'Ens-Vb-R', range(5, 9))],
                                                rs('escalon', 20, 'Ens-Vb-R', [1]) >= 0.7 and rs('escalon', 20, 'Ens-Vb-R', range(5, 9)) <= 0.3],
        '2_V0_L0_R3_sem3<=0.3': [[rs('escalon', 20, d, [3]) for d in ('Ens-V0-R', 'L0unico', 'R3')],
                                 all(rs('escalon', 20, d, [3]) <= 0.3 for d in ('Ens-V0-R', 'L0unico', 'R3'))],
        '3_PARAAD_plano_y_Q1>0': [[rs('escalon', 20, 'PARAAD', [1]), rs('escalon', 20, 'PARAAD', range(5, 9)),
                                   float(q('Q1').ic95_inf)],
                                  abs(rs('escalon', 20, 'PARAAD', range(5, 9)) - rs('escalon', 20, 'PARAAD', [1])) < 0.10
                                  and q('Q1').ic95_inf > 0],
        '4_Q2>0': [[float(q('Q2').valor), float(q('Q2').ic95_inf)], bool(q('Q2').ic95_inf > 0)],
        '5_rebote_Vb': [[float(q('Q3').ic95_inf), razon14, dur('Ens-Vb-R'), dur('Ens-V0-R')],
                        bool(q('Q3').ic95_inf > 0) and razon14 >= 3 and dur('Ens-V0-R') < dur('Ens-Vb-R')],
        '6_deriva': [[rec_all('deriva56', 20, 'Ens-Vb-R'), float(q('Q4').valor), float(q('Q4').ic95_sup)],
                     rec_all('deriva56', 20, 'Ens-Vb-R') < 0.3 and q('Q4').ic95_sup < 0],
    }
    if X:
        dmax = max(abs(rs('escalon', 20, X, [w]) - rs('escalon', 20, 'Ens-Vb-R', [w])) for w in range(1, 9))
        pred['7_X_igual_Vb(<0.03)'] = [dmax, dmax < 0.03]
    pred = {k: dict(valor=v[0], se_cumple=bool(v[1])) for k, v in pred.items()}
    out = d1.SAL
    S.to_csv(out / 'por_semana.csv', index=False, lineterminator='\n')
    Rb.to_csv(out / 'rebote.csv', index=False, lineterminator='\n')
    RS.to_csv(out / 'resumen.csv', index=False, lineterminator='\n')
    CR.to_csv(out / 'cambio_por_semana.csv', index=False, lineterminator='\n')
    PR.to_csv(out / 'pruebas.csv', index=False, lineterminator='\n')
    (out / 'predicciones.json').write_text(json.dumps(pred, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    dec = dict(corridas_identicas=dif == 0.0, diferencia_max=dif, detectores=dets,
               estacion_dias_evaluables={a: int(val[a].sum()) for a in val})
    (out / 'decision.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(dec, ensure_ascii=False))
    print(PR[PR.papel == 'declarada'].round(4).to_string(index=False))
    print(json.dumps(pred, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
