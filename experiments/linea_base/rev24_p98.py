"""Registro 24-p98: p98 en el banco de la revisión 24, solo E1 (una estación atacada).

    python rev24_p98.py lanzar   [--partes 2 --hilos 2]   # regenera los puntajes de E1 y de los años limpios
    python rev24_p98.py lanzar --corrida b                # segunda corrida, si las huellas no coinciden
    python rev24_p98.py verificar                         # huellas contra rev24/puntajes_sha256.json y a = b
    python rev24_p98.py metricas                          # VP, FP, FN con p99, p99.9 (control) y p98

Usa `rev24.py` sin cambios: solo se filtran las tareas del banco a E1 y a los años limpios. Los puntajes se
escriben donde los dejó la revisión 24 (results/linea_base/rev24/banco/corrida_a, no versionados).
Registro: fila 24-p98 de la sección 15 de docs/protocolo_anomalias_red_v1.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rev23 as r23  # noqa: E402
import rev23_metricas as m23  # noqa: E402
import rev24 as r  # noqa: E402
import rev24_metricas as m24  # noqa: E402

SAL = r.cm.RAIZ / 'results/linea_base/rev24_p98'
NIV = (0.01, 0.001, 0.02)
# Umbrales p98 de 2023 limpio, registrados antes de ver el banco (fila 24-p98 del protocolo)
U_P98 = {'PARAAD': 0.5827050988251964}

_configurar = r.configurar


def configurar_e1(etapa):
    T, grupos, extra, fase = _configurar(etapa)
    if etapa == 'banco':
        T = [t for t in T if t[0] == 'limpia' or t[2] == 'E1']
    return T, grupos, extra, fase


r.configurar = configurar_e1


def huellas(z) -> dict:
    """Variantes de la huella de contenido descrita en rev24/puntajes_sha256.json."""
    ks = sorted(k for k in z.files if k != 'info')
    out = {}
    for nombre, claves in (('todos', ks), ('sin_dias', [k for k in ks if k != 'dias'])):
        h = hashlib.sha256()
        for k in claves:
            h.update(np.ascontiguousarray(z[k]).tobytes())
        out[nombre] = h.hexdigest()
    return out


def verificar():
    reg = json.loads((r.SAL / 'puntajes_sha256.json').read_text())['archivos']
    T, _, _, _ = r.configurar('banco')
    res, variante = {}, None
    for t in T:
        k = f'banco/{r.nombre_tarea(t)}'
        z = np.load(r.SAL / 'banco' / 'corrida_a' / f'{r.nombre_tarea(t)}.npz')
        h = huellas(z)
        ok = [v for v, x in h.items() if x == reg[k]]
        if ok and variante is None:
            variante = ok[0]
        res[k] = bool(ok) and ok[0] == variante
    out = dict(variante=variante, archivos=len(res), coinciden=sum(res.values()),
               distintos=len([k for k, v in res.items() if not v]))
    # si las huellas no coinciden: la corrida b tiene que ser idéntica a la a (registro 24-p98)
    b = r.SAL / 'banco' / 'corrida_b'
    if b.exists():
        dif, faltan = 0.0, 0
        for t in T:
            n = f'{r.nombre_tarea(t)}.npz'
            if not (b / n).exists():
                faltan += 1
                continue
            za, zb = np.load(r.SAL / 'banco' / 'corrida_a' / n), np.load(b / n)
            for k in za.files:
                if k not in ('info', 'dias'):
                    dif = max(dif, float(np.nanmax(np.abs(za[k] - zb[k]))))
                    assert (np.isnan(za[k]) == np.isnan(zb[k])).all(), f'{n} {k}: huecos distintos'
        out['corrida_b'] = dict(diferencia_maxima=dif, faltan=faltan)
    SAL.mkdir(parents=True, exist_ok=True)
    (SAL / 'verificacion.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


def metricas():
    T, _, _, _ = r.configurar('banco')
    A = m24.cargar('banco', 'a', T)
    tau = r.tau_elegido()
    X = m24.etq(tau)
    dets = ['Ens-Vb-R', X, 'PARAAD']          # la misma máscara de validez que la revisión 24
    U = m24.umbrales_banco()
    U[(X, 0.02)] = json.loads((r.SAL / 'umbrales_2023_X.json').read_text())['umbrales']['0.02']
    U[('PARAAD', 0.02)] = U_P98['PARAAD']
    obj = list(r.rc.objetivos())
    dias, val = {}, {}
    for a in (2024, 2025, 2026):
        z = A[f'limpia_{a}']
        dias[a] = pd.DatetimeIndex(z['dias'])
        val[a] = np.logical_and.reduce([~np.isnan(z[d]) for d in dets])
    lab = {c: m23.etiquetas(r.leer_plan('banco', c, 'E1'), dias[r23.anio_de(c)], obj) for c in r23.CALS}
    filas = []
    for t in r.TAM_BANCO:
        for d in (X, 'PARAAD'):
            for nv in NIV:
                u = U[(d, nv)]
                tp = fp = fn = 0
                for c in r23.CALS:
                    a = r23.anio_de(c)
                    s = A[f'{c}_E1_{t}'][d] > u
                    y, _, _ = lab[c]
                    m = val[a]
                    tp += int((s & y & m).sum()); fp += int((s & ~y & m).sum()); fn += int((~s & y & m).sum())
                F, P, R_ = m24.f1(tp, fp, fn)
                filas.append(dict(detector=d, nivel=nv, escenario='E1', tamano=t, umbral=u, tp=tp, fp=fp, fn=fn,
                                  precision=P, recall=R_, F1=F))
    M = pd.DataFrame(filas)
    fa = []
    for d in (X, 'PARAAD'):
        for nv in NIV:
            n_al = sum(int((A[f'limpia_{a}'][d][val[a]] > U[(d, nv)]).sum()) for a in dias)
            n_v = sum(int(val[a].sum()) for a in dias)
            fa.append(dict(detector=d, nivel=nv, umbral=U[(d, nv)], fa=n_al / n_v, alarmas=n_al, estacion_dias=n_v))
    FA = pd.DataFrame(fa)
    # control: p99 y p99.9 deben dar las mismas filas E1 que la revisión 24
    ref = pd.read_csv(r.SAL / 'metricas_banco.csv')
    ref = ref[(ref.escenario == 'E1') & ref.detector.isin([X, 'PARAAD'])].set_index(['detector', 'nivel', 'tamano'])
    q = M[M.nivel != 0.02].set_index(['detector', 'nivel', 'tamano'])
    control = bool((q[['tp', 'fp', 'fn']] == ref.loc[q.index, ['tp', 'fp', 'fn']]).all().all())
    fa_ref = pd.read_csv(r.SAL / 'falsas_alarmas_banco.csv').set_index(['detector', 'nivel'])
    fq = FA[FA.nivel != 0.02].set_index(['detector', 'nivel'])
    control_fa = bool((fq.alarmas == fa_ref.loc[fq.index, 'alarmas']).all())
    SAL.mkdir(parents=True, exist_ok=True)
    M.to_csv(SAL / 'metricas_e1.csv', index=False, lineterminator='\n')
    FA.to_csv(SAL / 'falsas_alarmas.csv', index=False, lineterminator='\n')
    out = dict(control_p99_p999_igual_rev24=control, control_falsas_alarmas_igual_rev24=control_fa,
               umbrales_p98={X: U[(X, 0.02)], 'PARAAD': U[('PARAAD', 0.02)]})
    (SAL / 'control.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print(M[M.nivel == 0.02][['detector', 'tamano', 'tp', 'fp', 'fn', 'precision', 'recall']].round(3).to_string(index=False))
    print(FA.to_string(index=False))


def main():
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument('accion', choices=['puntuar', 'lanzar', 'verificar', 'metricas'])
    ap.add_argument('--etapa', default='banco')
    ap.add_argument('--corrida', default='a')
    ap.add_argument('--parte', type=int, default=0)
    ap.add_argument('--partes', type=int, default=2)
    ap.add_argument('--hilos', type=int, default=2)
    a = ap.parse_args()
    if a.accion == 'puntuar':
        r.etapa_puntuar('banco', a.corrida, a.parte, a.partes, a.hilos)
    elif a.accion == 'lanzar':
        r.etapa_lanzar('banco', a.corrida, a.partes, a.hilos, script='rev24_p98.py')
    elif a.accion == 'verificar':
        verificar()
    else:
        metricas()


if __name__ == '__main__':
    main()
