"""Revisión 25: fusión «Ens-Vb-X o PARAAD» con el presupuesto total de falsas alarmas de 2023 (retador).

    python rev25.py        # calibración en 2023, banco, D1, despliegue, pruebas T1–T3 y predicciones

Registro: docs/registro_previo_rev25_fusion_paraad.md. Sólo combina puntajes ya calculados (revisiones 22, 24 y 23b);
PARAAD en 2023 se recalculó con las mismas funciones (results/linea_base/rev25/paraad_2023.npz).
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
import rev23b as d1  # noqa: E402
import rev24 as r24  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

SAL = r23.cm.RAIZ / 'results/linea_base/rev25'
X = f'Ens-Vb-X{r24.tau_elegido():.4g}'
F = 'Fusion'
NIV = (0.01, 0.001)
B = 2000
DFBAR = ('d100', 'd50', 'd20')
DPPB = ('a10', 'a20', 'a40')


def calibrar():
    cal = np.load(r24.rc.SAL / 'calibracion_2023.npz')
    com = cal['comun']
    x = np.load(r24.SAL / 'calibracion' / 'corrida_a' / 'limpia_2023.npz')[X][com]
    p = np.load(SAL / 'paraad_2023.npz')['PARAAD'][com]
    assert not np.isnan(x).any() and not np.isnan(p).any()
    out = {}
    for obj in NIV:
        mejor = None
        for q in np.linspace(obj / 2, obj, 2001):
            ux, up = ev.umbral_falsas_alarmas(x, q), ev.umbral_falsas_alarmas(p, q)
            fa = float(((x > ux) | (p > up)).mean())
            if fa <= obj:
                mejor = dict(q=float(q), u_X=float(ux), u_PARAAD=float(up), fa_2023=fa,
                             fa_X_2023=float((x > ux).mean()), fa_PARAAD_2023=float((p > up).mean()))
        out[str(obj)] = mejor
    out['estacion_dias'] = int(com.sum())
    return out


def decide(Z, U, nv):
    """Alarmas de X, PARAAD y la fusión; NaN si falta cualquiera de los dos."""
    c = U[str(nv)]
    sx, sp = Z[X] > c['u_X'], Z['PARAAD'] > c['u_PARAAD']
    return {X: Z[X] > r24_umbral(nv), 'PARAAD': Z['PARAAD'] > r23.U_PARAAD[nv], F: sx | sp}


_UX = json.loads((r24.SAL / 'umbrales_2023_X.json').read_text())['umbrales']


def r24_umbral(nv):
    return _UX[str(nv)]


def bloques(dias_a, a, nobj):
    return np.arange(nobj)[None, :] * 31 + ((a - 2024) * 12 + dias_a.month.to_numpy() - 1)[:, None]


def ic(fn, W):
    uno = np.ones((W.shape[0], 1))
    p0 = float(fn(uno)[0])
    lo, hi = np.percentile(fn(W), [2.5, 97.5])
    return dict(valor=p0, ic95_inf=float(lo), ic95_sup=float(hi))


def pesos(nb, semilla):
    return np.random.default_rng(semilla).multinomial(nb, np.full(nb, 1 / nb), size=B).T.astype(float)


def banco(U):
    T, _, _, _ = r24.configurar('banco')
    A = {r24.nombre_tarea(t): dict(np.load(r24.SAL / 'banco' / 'corrida_a' / f'{r24.nombre_tarea(t)}.npz')) for t in T}
    obj = list(r24.rc.objetivos())
    dias, val, blq = {}, {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in ('Ens-Vb-R', X, 'PARAAD')])
        blq[a] = bloques(dias[a], a, len(obj))
    nb = len(obj) * 31
    lab = {(c, e): m23.etiquetas(r24.leer_plan('banco', c, e), dias[r23.anio_de(c)], obj)
           for c in r23.CALS for e in r24.ESC_BANCO}
    filas, C, Co = [], {}, {}
    for e in r24.ESC_BANCO:
        for t in r24.TAM_BANCO:
            for nv in NIV:
                Kd = {d: np.zeros((3, nb)) for d in (X, 'PARAAD', F)}
                Ko = {d: np.zeros((2, nb)) for d in (X, 'PARAAD', F)}
                gr = {d: [0, 0] for d in (X, 'PARAAD', F)}
                for c in r23.CALS:
                    a = r23.anio_de(c)
                    al = decide(A[f'{c}_{e}_{t}'], U, nv)
                    y, papel, grupo = lab[(c, e)]
                    m = val[a]
                    for d, s in al.items():
                        for q, xx in enumerate((s & y & m, s & ~y & m, ~s & y & m)):
                            Kd[d][q] += np.bincount(blq[a][xx], minlength=nb)
                        Ko[d][0] += np.bincount(blq[a][s & m & (papel == 1)], minlength=nb)
                        Ko[d][1] += np.bincount(blq[a][~s & m & (papel == 1)], minlength=nb)
                        for g in np.unique(grupo[y & m]):
                            gr[d][0] += 1
                            gr[d][1] += bool(s[(grupo == g) & y & m].any())
                for d in Kd:
                    C[(d, nv, e, t)], Co[(d, nv, e, t)] = Kd[d], Ko[d]
                    tp, fp, fn = Kd[d].sum(1)
                    P_ = tp / max(tp + fp, 1)
                    R_ = tp / max(tp + fn, 1)
                    filas.append(dict(detector=d, nivel=nv, escenario=e, tamano=t, precision=P_, recall=R_,
                                      F1=2 * P_ * R_ / (P_ + R_) if P_ + R_ else 0.0,
                                      recall_original=Ko[d][0].sum() / max(Ko[d].sum(), 1),
                                      deteccion_ataque=gr[d][1] / max(gr[d][0], 1)))
    fa = []
    for nv in NIV:
        for a in dias:
            pass
        al = {d: 0 for d in (X, 'PARAAD', F)}
        n = 0
        for a in dias:
            dd = decide(A[f'limpia_{a}'], U, nv)
            for d in al:
                al[d] += int(dd[d][val[a]].sum())
            n += int(val[a].sum())
        fa += [dict(detector=d, nivel=nv, fa=al[d] / n, alarmas=al[d], estacion_dias=n) for d in al]
    W = pesos(nb, [42, 25, 1])

    def f1w(d, nv, e, t, w):
        x = C[(d, nv, e, t)] @ w
        P_ = x[0] / np.maximum(x[0] + x[1], 1e-12)
        R_ = x[0] / np.maximum(x[0] + x[2], 1e-12)
        return np.where(P_ + R_ > 0, 2 * P_ * R_ / np.maximum(P_ + R_, 1e-12), 0.0)

    def reco(d, nv, e, t, w):
        x = Co[(d, nv, e, t)] @ w
        return x[0] / np.maximum(x[0] + x[1], 1e-12)

    fb = lambda d, nv, e, tams, w: np.mean([f1w(d, nv, e, t, w) for t in tams], axis=0)  # noqa: E731
    pr = []
    for nv in NIV:
        pap = 'declarada' if nv == 0.01 else 'descriptiva'
        pr.append(dict(prueba='T1', nivel=nv, papel=pap, escenario='E1', tamano='Fbar',
                       **ic(lambda w: fb(F, nv, 'E1', DFBAR, w) - fb(X, nv, 'E1', DFBAR, w), W)))
        pr.append(dict(prueba='T2', nivel=nv, papel=pap, escenario='E2-4', tamano='d50',
                       **ic(lambda w: reco(F, nv, 'E2-4', 'd50', w) - reco(X, nv, 'E2-4', 'd50', w), W)))
        for e in r24.ESC_BANCO:
            for tams, nm in ((DFBAR, 'Fbar'), (DPPB, 'Fbar_ppb')):
                pr.append(dict(prueba=f'd{nm}_F-X', nivel=nv, papel='descriptiva', escenario=e, tamano=nm,
                               **ic(lambda w, e=e, tams=tams: fb(F, nv, e, tams, w) - fb(X, nv, e, tams, w), W)))
            for t in r24.TAM_BANCO:
                pr.append(dict(prueba='dRecall_original_F-X', nivel=nv, papel='descriptiva', escenario=e, tamano=t,
                               **ic(lambda w, e=e, t=t: reco(F, nv, e, t, w) - reco(X, nv, e, t, w), W)))
    return pd.DataFrame(filas), pd.DataFrame(fa), pd.DataFrame(pr)


def d1_fusion(U):
    A = {d1.nombre_tarea(t): dict(np.load(d1.SAL / 'corrida_a' / f'{d1.nombre_tarea(t)}.npz')) for t in d1.tareas()}
    dets6 = ['Ens-Vb-R', 'Ens-V0-R', 'L0unico', 'R3', 'PARAAD', X]
    obj = list(r23.rc.objetivos())
    dias, val, blq = {}, {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in dets6])
        blq[a] = bloques(dias[a], a, len(obj))
    nb = len(obj) * 31
    sem, post = {}, {}
    for c in r23.CALS:
        a = r23.anio_de(c)
        S_in = np.zeros((len(dias[a]), len(obj)), np.int8)
        S_po = np.zeros_like(S_in)
        pos = {d: i for i, d in enumerate(dias[a])}
        for e in d1.leer_plan(c).itertuples():
            j, i0 = obj.index(e.estacion), pos[e.inicio.normalize()]
            for k in range(d1.L):
                S_in[i0 + k, j] = k // 7 + 1
            for k in range(56):
                if i0 + d1.L + k < len(dias[a]):
                    S_po[i0 + d1.L + k, j] = k // 7 + 1
        sem[c], post[c] = S_in, S_po
    filas, Cw = [], {}
    for f in d1.FORMAS:
        for Aa in d1.AMPS:
            for nv in NIV:
                Kw = {d: np.zeros((8, 2, nb)) for d in (X, 'PARAAD', F)}
                Kp = {d: np.zeros((8, 2)) for d in (X, 'PARAAD', F)}
                for c in r23.CALS:
                    a = r23.anio_de(c)
                    al = decide(A[f'{c}_{f}_a{Aa}'], U, nv)
                    m = val[a]
                    for d, s in al.items():
                        for w in range(1, 9):
                            sel = (sem[c] == w) & m
                            Kw[d][w - 1, 0] += np.bincount(blq[a][sel & s], minlength=nb)
                            Kw[d][w - 1, 1] += np.bincount(blq[a][sel & ~s], minlength=nb)
                            selp = (post[c] == w) & m
                            Kp[d][w - 1] += [int((selp & s).sum()), int(selp.sum())]
                for d in Kw:
                    Cw[(f, Aa, d, nv)] = Kw[d]
                    for w in range(8):
                        tp, fn = Kw[d][w, 0].sum(), Kw[d][w, 1].sum()
                        filas.append(dict(forma=f, A=Aa, detector=d, nivel=nv, semana=w + 1, recall=tp / max(tp + fn, 1),
                                          tasa_posterior=Kp[d][w, 0] / max(Kp[d][w, 1], 1)))
    W = pesos(nb, [42, 25, 2])

    def rec(d, nv, sems, w):
        K = Cw[('escalon', 20, d, nv)][[s - 1 for s in sems]].sum(0) @ w
        return K[0] / np.maximum(K[0] + K[1], 1e-12)
    pr = [dict(prueba='T3', nivel=nv, papel='declarada' if nv == 0.01 else 'descriptiva', escenario='D1 escalón 20',
               tamano='sem5-8', **ic(lambda w: rec(F, nv, range(5, 9), w) - rec(X, nv, range(5, 9), w), W)) for nv in NIV]
    return pd.DataFrame(filas), pd.DataFrame(pr)


def despliegue(U):
    import rev22_examen as rx
    T, _, _, _ = r24.configurar('despliegue')
    A = {r24.nombre_tarea(t): dict(np.load(r24.SAL / 'despliegue' / 'corrida_a' / f'{r24.nombre_tarea(t)}.npz')) for t in T}
    pz = np.load(rx.EX / 'paraad_diario.npz')
    dias = pd.DatetimeIndex(A['limpia_2026']['dias'])
    assert pd.DatetimeIndex(pz['dias']).equals(dias)
    A['limpia_2026']['PARAAD'] = pz['limpia']
    for k in range(1, rx.N_CAL + 1):
        for dd in rx.DELTAS:
            A[f'despliegue_{k:02d}_E1_d{dd}']['PARAAD'] = pz[f'c{k:02d}_d{dd}']
    obj = list(r24.rc.objetivos())
    z = A['limpia_2026']
    val = ~np.isnan(z[X]) & ~np.isnan(z['PARAAD'])
    lab = rx.etiquetas(dias, obj)
    mes = dias.month.to_numpy()
    meses = sorted(set(mes))
    nb = len(obj) * len(meses)
    filas, C = [], {}
    for nv in NIV:
        fa = {d: float(s[val].mean()) for d, s in decide(z, U, nv).items()}
        r_ = {d: dict(detector=d, nivel=nv, fa_limpia=fa[d]) for d in fa}
        for dd in rx.DELTAS:
            K = {d: np.zeros((3, len(obj), len(meses))) for d in fa}
            for k in range(1, rx.N_CAL + 1):
                al = decide(A[f'despliegue_{k:02d}_E1_d{dd}'], U, nv)
                y = lab[k]['y']
                for d, s in al.items():
                    for q_, xx in enumerate((s & y & val, s & ~y & val, ~s & y & val)):
                        for i, mo in enumerate(meses):
                            K[d][q_, :, i] += xx[mes == mo].sum(0)
            for d in fa:
                C[(d, nv, dd)] = K[d].reshape(3, -1)
                tp, fp, fn = C[(d, nv, dd)].sum(1)
                P_ = tp / max(tp + fp, 1)
                R_ = tp / max(tp + fn, 1)
                r_[d].update({f'F1_{dd}': 2 * P_ * R_ / (P_ + R_) if P_ + R_ else 0.0, f'recall_{dd}': R_})
        for d in fa:
            r_[d]['Fbar'] = float(np.mean([r_[d][f'F1_{dd}'] for dd in (100, 50, 20)]))
            filas.append(r_[d])
    W = pesos(nb, [42, 25, 3])

    def fb(d, nv, w):
        f = []
        for dd in (100, 50, 20):
            x = C[(d, nv, dd)] @ w
            P_ = x[0] / np.maximum(x[0] + x[1], 1e-12)
            R_ = x[0] / np.maximum(x[0] + x[2], 1e-12)
            f.append(np.where(P_ + R_ > 0, 2 * P_ * R_ / np.maximum(P_ + R_, 1e-12), 0))
        return np.mean(f, axis=0)
    pr = [dict(prueba='dFbar_despliegue_F-X', nivel=nv, papel='descriptiva', escenario='ago-sep 2026', tamano='Fbar',
               **ic(lambda w: fb(F, nv, w) - fb(X, nv, w), W)) for nv in NIV]
    return pd.DataFrame(filas), pd.DataFrame(pr)


def main():
    SAL.mkdir(parents=True, exist_ok=True)
    U = calibrar()
    (SAL / 'umbrales_fusion_2023.json').write_text(json.dumps(U, indent=2) + '\n', encoding='utf8')
    Mb, FAb, PRb = banco(U)
    Md, PRd = d1_fusion(U)
    Mp, PRp = despliegue(U)
    PR = pd.concat([PRb, PRd, PRp], ignore_index=True)
    q = lambda nm: PR[(PR.prueba == nm) & (PR.nivel == 0.01)].iloc[0]  # noqa: E731
    T1, T2, T3 = bool(q('T1').ic95_inf > -0.02), bool(q('T2').ic95_inf > 0), bool(q('T3').ic95_inf > 0)
    if T1 and T2 and T3:
        ver = 'la fusión es mejor en general que Ens-Vb-X'
    elif T2 and T3:
        ver = 'compromiso: Ens-Vb-X es el mejor con un solo nodo; la fusión es un modo de alta cobertura'
    else:
        ver = 'Ens-Vb-X sigue siendo el mejor; la fusión no cubre los huecos'
    ro = lambda d, e, t: float(Mb[(Mb.detector == d) & (Mb.nivel == 0.01) & (Mb.escenario == e) & (Mb.tamano == t)].recall_original.iloc[0])  # noqa: E731
    rs = lambda d, sems: float(Md[(Md.forma == 'escalon') & (Md.A == 20) & (Md.detector == d) & (Md.nivel == 0.01) & Md.semana.isin(list(sems))].recall.mean())  # noqa: E731
    fa = lambda d: float(FAb[(FAb.detector == d) & (FAb.nivel == 0.01)].fa.iloc[0])  # noqa: E731
    t1 = q('T1')
    pred = {
        '1_T1_falla_por_poco(-0.04<dF<-0.01, inf<-0.02)': [[t1.valor, t1.ic95_inf], -0.04 < t1.valor < -0.01 and t1.ic95_inf < -0.02],
        '2_T2_y_recall_E2-4_d50>=0.20': [[ro(X, 'E2-4', 'd50'), ro(F, 'E2-4', 'd50')], T2 and ro(F, 'E2-4', 'd50') >= 0.20],
        '3_T3_y_recall_sem5-8>=0.40': [[rs(X, range(5, 9)), rs(F, range(5, 9))], T3 and rs(F, range(5, 9)) >= 0.40],
        '4_FA_banco_fusion_1.6-2.2%': [[fa(X), fa(F)], 0.016 <= fa(F) <= 0.022],
        '5_despliegue_dFbar<0': [float(q('dFbar_despliegue_F-X').valor), float(q('dFbar_despliegue_F-X').valor) < 0],
        '6_veredicto_compromiso': [ver, ver.startswith('compromiso')],
    }
    pred = {k: dict(valor=v[0], se_cumple=bool(v[1])) for k, v in pred.items()}
    Mb.to_csv(SAL / 'metricas_banco.csv', index=False, lineterminator='\n')
    FAb.to_csv(SAL / 'falsas_alarmas_banco.csv', index=False, lineterminator='\n')
    Md.to_csv(SAL / 'd1_por_semana.csv', index=False, lineterminator='\n')
    Mp.to_csv(SAL / 'despliegue_2026.csv', index=False, lineterminator='\n')
    PR.to_csv(SAL / 'pruebas.csv', index=False, lineterminator='\n')
    (SAL / 'predicciones.json').write_text(json.dumps(pred, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    dec = dict(T1=T1, T2=T2, T3=T3, veredicto=ver, umbrales=U)
    (SAL / 'veredicto.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(dec, ensure_ascii=False, indent=1))
    print(PR[PR.papel == 'declarada'].round(4).to_string(index=False))
    print(json.dumps(pred, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
