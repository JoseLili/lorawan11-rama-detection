"""Revisión 23: métricas, preguntas Q1–Q4 y predicciones 1–9 (registro y sus precisiones).

    python rev23_metricas.py

Lee results/linea_base/rev23/corrida_a y corrida_b (deben ser idénticas) y escribe en results/linea_base/rev23/:
metricas.csv, resumen.csv, falsas_alarmas_limpias.csv, cambio_real.csv, pruebas.csv, predicciones.json y decision.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rev23 as r  # noqa: E402

NIVELES = (0.01, 0.001)
DFBAR = ('d100', 'd50', 'd20')
DPPB = ('a10', 'a20', 'a40')
B = 2000


def umbrales() -> dict:
    U = r.umbrales_red()
    out = {(d, nv): U[(d, nv)] for d in ('Ens-Vb-R', 'Ens-V0-R', 'L0unico') for nv in NIVELES}
    u3 = r.umbrales_r3()
    for nv in NIVELES:
        out[('PARAAD', nv)] = r.U_PARAAD[nv]
        out[('R3', nv)] = u3[nv]
    return out


def cargar(corrida: str) -> dict:
    out = {}
    for t in r.tareas():
        z = np.load(r.SAL / f'corrida_{corrida}' / f'{r.nombre_tarea(t)}.npz')
        out[r.nombre_tarea(t)] = {k: z[k] for k in z.files}
    return out


def etiquetas(plan: pd.DataFrame, dias: pd.DatetimeIndex, obj: list):
    """y, papel (1 original, 2 añadida) y grupo (episodio original) por estación-día."""
    y = np.zeros((len(dias), len(obj)), bool)
    papel = np.zeros_like(y, dtype=np.int8)
    grupo = np.zeros_like(y, dtype=np.int32)
    pos = {d: i for i, d in enumerate(dias)}
    for e in plan.itertuples():
        j = obj.index(e.estacion)
        for d in pd.date_range(e.inicio.normalize(), e.fin.normalize()):
            i = pos[d]
            y[i, j] = True
            papel[i, j] = 1 if e.papel == 'original' else 2
            grupo[i, j] = int(e.origen)
    return y, papel, grupo


def main():
    A, Bc = cargar('a'), cargar('b')
    dif = 0.0
    for k in A:
        for d in r.DET:
            a, b = A[k][d], Bc[k][d]
            assert (np.isnan(a) == np.isnan(b)).all(), k
            dif = max(dif, float(np.nanmax(np.abs(a - b))) if (~np.isnan(a)).any() else 0.0)
    obj = list(r.rc.objetivos())
    U = umbrales()
    # estación-días evaluables: válidas para los cinco detectores en el año limpio y en la matriz (precisión 7)
    dias, val = {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in r.DET])
    mes = {a: ((a - 2024) * 12 + dias[a].month.to_numpy() - 1) for a in dias}
    nmes = 31
    blq = {a: (np.arange(len(obj))[None, :] * nmes + mes[a][:, None]) for a in dias}   # bloque estación × mes
    nb = len(obj) * nmes
    # falsas alarmas en limpio y decisiones frágiles
    fa, fragiles = [], {}
    for d in r.DET:
        for nv in NIVELES:
            u = U[(d, nv)]
            n_al = sum(int((A[f'limpia_{a}'][d][val[a]] > u).sum()) for a in dias)
            n_v = sum(int(val[a].sum()) for a in dias)
            fa.append(dict(detector=d, nivel=nv, umbral=u, estacion_dias=n_v, alarmas=n_al, fa=n_al / n_v,
                           **{f'fa_{a}': float((A[f'limpia_{a}'][d][val[a]] > u).mean()) for a in dias}))
            fragiles[f'{d}_{nv}'] = int(sum(
                int((np.abs(A[k][d][val[int(k.split('_')[-1]) if k.startswith('limpia') else r.anio_de(k.split('_E')[0])]]
                            - u) < 1e-5).sum()) for k in A))
    FA = pd.DataFrame(fa)
    # conteos por escenario y tamaño (sumados sobre los 30 calendarios), también por bloque y por papel
    filas, C, info = [], {}, []
    lab = {}
    for c in r.CALS:
        a = r.anio_de(c)
        for esc in r.ESCENARIOS:
            lab[(c, esc)] = etiquetas(r.leer_plan(c, esc), dias[a], obj)
    for esc in r.ESCENARIOS:
        for t in r.TAM[esc]:
            for c in r.CALS:
                info.append(dict(escenario=esc, tamano=t, calendario=c,
                                 **json.loads(str(A[f'{c}_{esc}_{t}']['info']))))
            for d in r.DET:
                for nv in NIVELES:
                    u = U[(d, nv)]
                    K = np.zeros((3, nb))
                    rol = np.zeros((2, 2))          # [original, añadida] × [tp, fn]
                    det_ep, n_ep = 0, 0
                    for c in r.CALS:
                        a = r.anio_de(c)
                        s = A[f'{c}_{esc}_{t}'][d] > u
                        y, papel, grupo = lab[(c, esc)]
                        m = val[a] & np.logical_and.reduce([~np.isnan(A[f'{c}_{esc}_{t}'][d2]) for d2 in r.DET])
                        for q, xx in enumerate((s & y & m, s & ~y & m, ~s & y & m)):
                            K[q] += np.bincount(blq[a][xx], minlength=nb)
                        for i, pp in enumerate((1, 2)):
                            rol[i, 0] += (s & m & (papel == pp)).sum()
                            rol[i, 1] += (~s & m & (papel == pp)).sum()
                        for g in np.unique(grupo[y & m]):
                            celdas = (grupo == g) & y & m
                            n_ep += 1
                            det_ep += bool(s[celdas].any())
                    tp, fp, fn = K.sum(1)
                    P = tp / max(tp + fp, 1)
                    R = tp / max(tp + fn, 1)
                    C[(d, nv, esc, t)] = K
                    filas.append(dict(detector=d, nivel=nv, escenario=esc, tamano=t, tp=int(tp), fp=int(fp), fn=int(fn),
                                      precision=P, recall=R, F1=2 * P * R / (P + R) if P + R else 0.0,
                                      recall_original=rol[0, 0] / max(rol[0].sum(), 1),
                                      recall_anadidas=rol[1, 0] / max(rol[1].sum(), 1) if rol[1].sum() else np.nan,
                                      episodios=n_ep, deteccion_ataque=det_ep / max(n_ep, 1)))
    M = pd.DataFrame(filas)
    I = pd.DataFrame(info)
    CR = (I.assign(suma=I.cambio_medio_ppb * I.horas_episodio).groupby(['escenario', 'tamano'])
          .agg(horas=('horas_episodio', 'sum'), suma=('suma', 'sum'), frac_cambiadas=('frac_cambiadas', 'mean'),
               ventanas_Vb=('ventanas_Vb', 'sum'), ventanas_V0=('ventanas_V0', 'sum')).reset_index())
    CR['cambio_medio_ppb'] = CR.suma / CR.horas
    # resumen: F̄ y F̄ppb
    res = []
    for d in r.DET:
        for nv in NIVELES:
            for esc in r.ESCENARIOS:
                g = M[(M.detector == d) & (M.nivel == nv) & (M.escenario == esc)].set_index('tamano')
                res.append(dict(detector=d, nivel=nv, escenario=esc, Fbar=g.loc[list(DFBAR), 'F1'].mean(),
                                Fbar_ppb=g.loc[list(DPPB), 'F1'].mean(),
                                recall_d50=g.loc['d50', 'recall'], recall_a20=g.loc['a20', 'recall']))
    RS = pd.DataFrame(res)
    # bootstrap pareado de bloques estación × mes
    rng = np.random.default_rng([42, 23, 1])
    W = rng.multinomial(nb, np.full(nb, 1 / nb), size=B).T.astype(float)        # (nb, B)
    uno = np.ones((nb, 1))

    def f1(d, nv, esc, t, w):
        x = C[(d, nv, esc, t)] @ w
        P = x[0] / np.maximum(x[0] + x[1], 1e-12)
        R = x[0] / np.maximum(x[0] + x[2], 1e-12)
        return np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0.0)

    def rec(d, nv, esc, t, w):
        x = C[(d, nv, esc, t)] @ w
        return x[0] / np.maximum(x[0] + x[2], 1e-12)

    def fbar(d, nv, esc, tams, w):
        return np.mean([f1(d, nv, esc, t, w) for t in tams], axis=0)

    def ic(fn):
        p0 = float(fn(uno)[0])
        lo, hi = np.percentile(fn(W), [2.5, 97.5])
        return dict(valor=p0, ic95_inf=float(lo), ic95_sup=float(hi))

    pr = []
    for nv in NIVELES:
        papel = 'declarada' if nv == 0.01 else 'descriptiva'
        for esc in r.ESCENARIOS:
            pr.append(dict(prueba='Q1' if esc == 'E2' else 'dFbar_Vb-V0', nivel=nv, escenario=esc,
                           papel=papel if esc == 'E2' else 'descriptiva',
                           **ic(lambda w, esc=esc: fbar('Ens-Vb-R', nv, esc, DFBAR, w) - fbar('Ens-V0-R', nv, esc, DFBAR, w))))
        caida = lambda d, e2, t, w: rec(d, nv, 'E1', t, w) - rec(d, nv, e2, t, w)  # noqa: E731
        pr.append(dict(prueba='Q2', nivel=nv, escenario='E1-E2', papel=papel,
                       **ic(lambda w: caida('Ens-Vb-R', 'E2', 'd50', w) - caida('Ens-V0-R', 'E2', 'd50', w))))
        pr.append(dict(prueba='Q3', nivel=nv, escenario='E1', papel=papel,
                       **ic(lambda w: fbar('Ens-Vb-R', nv, 'E1', DPPB, w) - fbar('R3', nv, 'E1', DPPB, w))))
        pr.append(dict(prueba='Q4', nivel=nv, escenario='E1', papel=papel,
                       **ic(lambda w: fbar('Ens-Vb-R', nv, 'E1', DPPB, w) - fbar('Ens-V0-R', nv, 'E1', DPPB, w))))
        for d in r.DET:
            for e2 in ('E2', 'E3'):
                pr.append(dict(prueba=f'caida_recall_d50_{d}', nivel=nv, escenario=f'E1-{e2}', papel='descriptiva',
                               **ic(lambda w, d=d, e2=e2: caida(d, e2, 'd50', w))))
        for d in ('Ens-V0-R', 'L0unico', 'PARAAD', 'R3'):
            for tams, nm in ((DFBAR, 'Fbar'), (DPPB, 'Fbar_ppb')):
                for esc in r.ESCENARIOS:
                    pr.append(dict(prueba=f'd{nm}_Vb-{d}', nivel=nv, escenario=esc, papel='descriptiva',
                                   **ic(lambda w, d=d, tams=tams, esc=esc: fbar('Ens-Vb-R', nv, esc, tams, w)
                                        - fbar(d, nv, esc, tams, w))))
    PR = pd.DataFrame(pr)
    # predicciones (p99)
    q = lambda nm, esc=None: PR[(PR.prueba == nm) & (PR.nivel == 0.01) & ((PR.escenario == esc) if esc else True)].iloc[0]  # noqa: E731
    Rm = lambda d, esc, t: float(M[(M.detector == d) & (M.nivel == 0.01) & (M.escenario == esc) & (M.tamano == t)].recall.iloc[0])  # noqa: E731
    cv = lambda d, e2, t: Rm(d, 'E1', t) - Rm(d, e2, t)  # noqa: E731
    pred = {
        '1_caida_Vb_d50_E2>=0.10': [cv('Ens-Vb-R', 'E2', 'd50'), cv('Ens-Vb-R', 'E2', 'd50') >= 0.10],
        '2_V0_baja_y_menos_que_Vb': [[cv('Ens-V0-R', 'E2', 'd50'), float(q('Q2').valor)],
                                     cv('Ens-V0-R', 'E2', 'd50') > 0 and float(q('Q2').valor) > 0],
        '3_caidas_E3<E2': [[cv(d, 'E3', 'd50') for d in ('Ens-Vb-R', 'Ens-V0-R')],
                           all(cv(d, 'E3', 'd50') < cv(d, 'E2', 'd50') for d in ('Ens-Vb-R', 'Ens-V0-R'))],
        '4_Q1_IC_incluye_0': [[float(q('Q1').ic95_inf), float(q('Q1').ic95_sup)],
                              bool(q('Q1').ic95_inf <= 0 <= q('Q1').ic95_sup)],
        '5_PARAAD_cambia<0.05': [cv('PARAAD', 'E2', 'd50'), abs(cv('PARAAD', 'E2', 'd50')) < 0.05],
        '6_Q4_IC>0': [[float(q('Q4').ic95_inf), float(q('Q4').ic95_sup)], bool(q('Q4').ic95_inf > 0)],
        '7_Q3_IC_incluye_0': [[float(q('Q3').ic95_inf), float(q('Q3').ic95_sup)],
                              bool(q('Q3').ic95_inf <= 0 <= q('Q3').ic95_sup)],
        '8_recall_a10<0.5_a20>0.8': [[Rm('Ens-Vb-R', 'E1', 'a10'), Rm('Ens-Vb-R', 'E1', 'a20')],
                                     Rm('Ens-Vb-R', 'E1', 'a10') < 0.5 and Rm('Ens-Vb-R', 'E1', 'a20') > 0.8],
        '9_caida_ppb>proporcional': [[float(np.mean([cv('Ens-Vb-R', 'E2', t) for t in DPPB])),
                                      float(np.mean([cv('Ens-Vb-R', 'E2', t) for t in DFBAR]))],
                                     float(np.mean([cv('Ens-Vb-R', 'E2', t) for t in DPPB]))
                                     > float(np.mean([cv('Ens-Vb-R', 'E2', t) for t in DFBAR]))],
    }
    pred = {k: dict(valor=v[0], se_cumple=bool(v[1])) for k, v in pred.items()}
    S = r.SAL
    M.to_csv(S / 'metricas.csv', index=False, lineterminator='\n')
    RS.to_csv(S / 'resumen.csv', index=False, lineterminator='\n')
    FA.to_csv(S / 'falsas_alarmas_limpias.csv', index=False, lineterminator='\n')
    CR.drop(columns='suma').to_csv(S / 'cambio_real.csv', index=False, lineterminator='\n')
    PR.to_csv(S / 'pruebas.csv', index=False, lineterminator='\n')
    (S / 'predicciones.json').write_text(json.dumps(pred, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    nan_distinto = sum(int((np.isnan(A[k][d]) != np.isnan(A[f'limpia_{r.anio_de(k.split("_E")[0])}'][d])).sum())
                       for k in A if not k.startswith('limpia') for d in r.DET)
    dec = dict(corridas_identicas=dif == 0.0, diferencia_max=dif, decisiones_fragiles=fragiles,
               celdas_nan_distinto_del_limpio=nan_distinto,
               estacion_dias_evaluables={a: int(val[a].sum()) for a in val})
    (S / 'decision.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    pd.set_option('display.width', 200)
    print(json.dumps(dec, ensure_ascii=False))
    print(RS[RS.nivel == 0.01].round(3).to_string(index=False))
    print(PR[PR.papel == 'declarada'].round(4).to_string(index=False))
    print(json.dumps(pred, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
