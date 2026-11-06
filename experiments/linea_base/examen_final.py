"""Examen final de uso único: Ens-Vbr contra Ens-V0r (y el L0 definitivo de la rev. 14) sobre RAMA 2017–2019.

Registro previo: docs/registro_previo_examen_final_2017_2019.md (aprobado el 2026-11-04).

Etapas (cada una guarda su salida en results/linea_base/examen_final/ y no se repite si ya existe):
  planes      30 calendarios (2017–2019 × 10), guardados con SHA-256 ANTES de construir datos del holdout
  modelos     10 definitivos (V0/Vb × semillas 42, 1–4) con 2020–2022, exactamente su E
  calibracion puntajes diarios de 2023 limpio (historia 2020–2022) y umbrales por nivel de falsas alarmas
  holdout     puntajes de 2017–2019 limpio y de los 90 calendarios×δ (historia limpia desde 2016); corrida a o b
  metricas    curva de operación, dos pruebas declaradas (p99 y p99.9, IC 97.5 %) y comparación de corridas

Uso:  python experiments/linea_base/examen_final.py --etapa {planes,modelos,calibracion,holdout,metricas} [--corrida a|b]
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comun as cm  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402
from src.detect import multianual as mu  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/examen_final'
ANIOS = (2017, 2018, 2019)
N_CAL = 10
DELTAS = (100, 50, 20)
SEMILLAS = (42, 1, 2, 3, 4)
E = {'V0r': {42: 1, 1: 1, 2: 1, 3: 1, 4: 1}, 'Vbr': {42: 1, 1: 1, 2: 2, 3: 2, 4: 1}}
BASES = {'V0r': 'V0', 'Vbr': 'Vb'}
L0_REV14 = cm.SAL_RED / 'lstm_local_examen/c20/d50/modelo.keras'
NIVELES = (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)
DECLARADOS = (0.01, 0.001)
DETECTORES = ('Ens-Vbr', 'Ens-V0r', 'L0rev14')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ datos
def valores(desde, hasta) -> pd.DataFrame:
    """O3 horario × 33 estaciones fijas, verificado por SHA-256, en la rejilla [desde, hasta]."""
    ck = mu.leer_checksums(cm.RAIZ / 'docs/checksums_2020_2026.txt')
    ck |= mu.leer_checksums(cm.RAIZ / 'docs/checksums_2017_2019.txt')
    anios = range(pd.Timestamp(desde).year, pd.Timestamp(hasta).year + 1)
    largo, _ = mu.cargar_o3_zips(cm.RAIZ / 'data/raw', ck, anios=anios)
    rej = pd.date_range(desde, hasta, freq='h', name='timestamp')
    largo = largo[largo['station'].isin(mu.ESTACIONES)]
    v = largo.pivot(index='timestamp', columns='station', values='value').reindex(index=rej, columns=mu.ESTACIONES)
    v.columns.name = 'station'
    return v


def columnas():
    return ar.columnas_entrada(['XAL'])


def alterables():
    from generar_planes import alterables_v4
    return alterables_v4()


# ------------------------------------------------------------------ etapa 1: planes
def etapa_planes():
    d = SAL / 'planes'
    d.mkdir(parents=True, exist_ok=True)
    reg = {}
    for y in ANIOS:
        ini, fin = f'{y}-01-01', f'{y}-12-31'
        for k in range(1, N_CAL + 1):
            rng = np.random.default_rng(ar.clave(ar.SEMILLA, ini, k, ar.USO_TASA))
            p = float(rng.uniform(*ar.P_RANGO))
            plan = ar.plan_episodios(ini, fin, p, alterables(), corrida=f'final_{y}_{k:02d}', numero=k)
            ar.validar_plan(plan)
            path = ar.guardar_plan(plan, d)
            reg[path.name] = dict(sha256=sha(path.read_bytes()), p=p, episodios=len(plan))
    (SAL / 'planes_sha256.json').write_text(json.dumps(reg, indent=2))
    print(f'{len(reg)} planes guardados', flush=True)


def plan(y, k):
    return ar.leer_plan(SAL / f'planes/plan_final_{y}_{k:02d}.csv')


# ------------------------------------------------------------------ etapa 2: modelos definitivos
def etapa_modelos(ctx):
    import keras
    import tensorflow as tf
    from entrenar_lstm_sup import CONFIG
    from src.detect import lstm_red as lr
    from src.detect.lstm import fijar_semilla
    d = SAL / 'modelos'
    d.mkdir(parents=True, exist_ok=True)
    nombres = [f'entrenamiento_{i:02d}_d50' for i in range(1, 21)]
    cm.asegurar_matrices(nombres)
    limpia = ctx['limpia']
    b_l = cm.bases(ctx, limpia)
    esc = {v: lb.escala_a14(limpia, b_l[v], ctx['estaciones'], ctx['sigma'], ctx['vec'], '2022-12-31 23:00') for v in ('V0', 'Vb')}
    np.savez(SAL / 'escalas_definitivas.npz', **esc)
    todas = np.arange(lr.VENTANA - 1, len(limpia))
    for mn, v in BASES.items():
        faltan = [s for s in SEMILLAS if not (d / f'{mn}_s{s}.keras').exists()]
        if not faltan:
            continue
        X, y = [], []
        for i, k in enumerate(nombres, start=1):
            x = cm.leer(k)
            Y = ed.etiquetas_por_hora(x, ctx['objetivos'])
            F = lb.entradas(x, cm.bases(ctx, x)[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'])
            for j, s in enumerate(ctx['objetivos']):
                p = ll.muestra(todas, 8, 'definitivo', i, j)
                X.append(cm.ventanas(ctx, F, s, p))
                y.append(Y[s].to_numpy(np.float32)[p])
        X, y = np.concatenate(X), np.concatenate(y)
        print(f'{mn}: {len(y)} ventanas de 2020–2022, {100 * y.mean():.3f} % positivas', flush=True)
        for s in faltan:
            keras.backend.clear_session()
            fijar_semilla(s)
            mdl = lr.construir_clasificador(n_features=17, unidades=CONFIG['unidades'], salidas=1)
            h = mdl.fit(X, y, epochs=E[mn][s], batch_size=CONFIG['batch'], shuffle=CONFIG['shuffle'], verbose=2)
            mdl.save(d / f'{mn}_s{s}.keras')
            (d / f'{mn}_s{s}.json').write_text(json.dumps(dict(modelo=mn, semilla=s, epocas=E[mn][s],
                                                               loss=[float(a) for a in h.history['loss']], ventanas=len(y),
                                                               tensorflow=tf.__version__, keras=keras.__version__), indent=2))
            print(f'{mn} semilla {s}: {E[mn][s]} época(s), loss final {h.history["loss"][-1]:.5f}', flush=True)
            del mdl
        del X, y
        gc.collect()


# ------------------------------------------------------------------ puntuación
def cargar_modelos():
    import keras
    m = {f'{mn}_s{s}': keras.models.load_model(SAL / f'modelos/{mn}_s{s}.keras', compile=False) for mn in BASES for s in SEMILLAS}
    m['L0rev14'] = keras.models.load_model(L0_REV14, compile=False)
    return m


def puntuar_matriz(ctx, mods, esc, x, pos):
    """Puntaje diario (promedio_dia, ≥ 12 h) de cada modelo en las horas `pos` de `x` (que trae su historia)."""
    b = cm.bases(ctx, x)
    V = lb.valores(x, ctx['estaciones'])
    F = {v: lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'], V) for v in ('V0', 'Vb')}
    obj = ctx['objetivos']
    ix = x.index[pos]
    con = x.loc[ix, [f'{s}_mascara' for s in obj]].to_numpy() == 1
    out = {}
    for nombre, mdl in mods.items():
        base = 'V0' if nombre == 'L0rev14' else BASES[nombre.split('_s')[0]]
        Xw = np.concatenate([cm.ventanas(ctx, F[base], s, pos) for s in obj])
        p = mdl.predict(Xw, batch_size=8192, verbose=0).astype(np.float64).reshape(len(obj), len(pos)).T
        out[nombre] = ed.juntar_dia(pd.DataFrame(p, index=ix, columns=obj).where(con), 'promedio_dia')
    return out


def guardar_npz(path, puntajes: dict):
    dias = next(iter(next(iter(puntajes.values())).values())).index
    np.savez_compressed(path, dias=dias.values.astype('datetime64[ns]'),
                        **{f'{k}__{n}': df.to_numpy() for k, d in puntajes.items() for n, df in d.items()})


def etapa_calibracion(ctx):
    mods, esc = cargar_modelos(), dict(np.load(SAL / 'escalas_definitivas.npz'))
    v = valores('2020-01-01', '2023-12-31 23:00')
    x = ar.matriz_red(v, columnas())
    pos = np.flatnonzero(x.index.year == 2023)
    guardar_npz(SAL / 'calibracion_2023.npz', {'limpia_2023': puntuar_matriz(ctx, mods, esc, x, pos)})
    print('calibración 2023 lista', flush=True)


def etapa_holdout(ctx, corrida):
    mods, esc = cargar_modelos(), dict(np.load(SAL / 'escalas_definitivas.npz'))
    for f in (SAL / 'planes_sha256.json',):
        reg = json.loads(f.read_text())
        for nombre, r in reg.items():
            assert sha((SAL / 'planes' / nombre).read_bytes()) == r['sha256'], f'plan modificado: {nombre}'
    v = valores('2016-01-01', '2019-12-31 23:00')
    cols = columnas()
    limpia = ar.matriz_red(v, cols)
    salida = SAL / f'holdout_{corrida}'
    salida.mkdir(parents=True, exist_ok=True)
    orden = list(ANIOS) if corrida == 'a' else list(reversed(ANIOS))
    for y in orden:
        hasta = pd.Timestamp(f'{y}-12-31 23:00')
        idx = limpia.index[limpia.index <= hasta]
        pos = np.flatnonzero(idx.year == y)
        arch = salida / f'{y}.npz'
        if arch.exists():
            continue
        P = {f'limpia_{y}': puntuar_matriz(ctx, mods, esc, limpia.loc[:hasta], pos)}
        vy = v.loc[f'{y}-01-01':hasta]
        for k in range(1, N_CAL + 1):
            pl = plan(y, k)
            for d in DELTAS:
                rec, cam = ar.aplicar(vy, pl, d / 100)
                xa = pd.concat([limpia.loc[:f'{y - 1}-12-31 23:00'], ar.matriz_red(rec, cols, cam)])
                assert xa.index.equals(idx)
                P[f'final_{y}_{k:02d}_d{d}'] = puntuar_matriz(ctx, mods, esc, xa, pos)
            print(f'  corrida {corrida}: {y} calendario {k:02d} listo', flush=True)
        guardar_npz(arch, P)
        del P
        gc.collect()
    print(f'holdout corrida {corrida} lista', flush=True)


# ------------------------------------------------------------------ métricas
def leer_npz(path):
    z = np.load(path, allow_pickle=False)
    dias = pd.DatetimeIndex(z['dias'])
    S = {}
    for k in z.files:
        if k == 'dias':
            continue
        mat, nombre = k.split('__')
        S[(nombre, mat)] = z[k]
    for mn in BASES:
        for mat in {m for _, m in S}:
            S[(f'Ens-{mn}', mat)] = np.mean([S[(f'{mn}_s{s}', mat)] for s in SEMILLAS], axis=0)
    return dias, S


def etiquetas_anio(y, dias, objetivos):
    out = {}
    for k in range(1, N_CAL + 1):
        pl = plan(y, k)
        yy = pd.DataFrame(False, index=dias, columns=objetivos)
        tras = pd.DataFrame(np.inf, index=dias, columns=objetivos)
        for e in pl.itertuples():
            if e.estacion not in objetivos:
                continue
            yy.loc[e.inicio.normalize():e.fin.normalize(), e.estacion] = True
            for t in range(1, 15):
                dd = e.fin.normalize() + pd.Timedelta(days=t)
                if dd in tras.index:
                    tras.loc[dd, e.estacion] = min(tras.loc[dd, e.estacion], t)
        out[k] = dict(y=yy.to_numpy(), tras=tras.to_numpy())
    return out


def etapa_metricas(ctx):
    from sklearn.metrics import average_precision_score
    obj = ctx['objetivos']
    _, C = leer_npz(SAL / 'calibracion_2023.npz')
    cal_comun = np.logical_and.reduce([~np.isnan(C[(dt, 'limpia_2023')]) for dt in DETECTORES])
    umbral = {(dt, nv): ev.umbral_falsas_alarmas(C[(dt, 'limpia_2023')][cal_comun], nv) for dt in DETECTORES for nv in NIVELES}
    # comparación de corridas
    dif = 0.0
    for y in ANIOS:
        _, A = leer_npz(SAL / f'holdout_a/{y}.npz')
        _, B = leer_npz(SAL / f'holdout_b/{y}.npz')
        dif = max(dif, max(float(np.nanmax(np.abs(A[k] - B[k]))) for k in A))
    # unidades y conteos por año
    filas, bloques = [], {}
    for y in ANIOS:
        dias, S = leer_npz(SAL / f'holdout_a/{y}.npz')
        lab = etiquetas_anio(y, dias, obj)
        mats = [f'limpia_{y}'] + [f'final_{y}_{k:02d}_d{d}' for k in range(1, N_CAL + 1) for d in DELTAS]
        comun = {m: np.logical_and.reduce([~np.isnan(S[(dt, m)]) for dt in DETECTORES]) for m in mats}
        cl = comun[f'limpia_{y}']
        mes = dias.month.to_numpy()
        for dt in DETECTORES:
            for nv in NIVELES:
                u = umbral[(dt, nv)]
                al = S[(dt, f'limpia_{y}')] > u
                r = dict(anio=y, detector=dt, nivel=nv, umbral=u, fa_limpia=float(al[cl].mean()), dias_limpios=int(cl.sum()),
                         alarmas_limpias=int(al[cl].sum()))
                for d in DELTAS:
                    tp = fp = fn = 0
                    m1 = [0, 0]
                    Cb = np.zeros((3, len(obj), 12))
                    for k in range(1, N_CAL + 1):
                        m = f'final_{y}_{k:02d}_d{d}'
                        a, yy, msk = S[(dt, m)] > u, lab[k]['y'], comun[m] & cl
                        tp += (a & yy & msk).sum(); fp += (a & ~yy & msk).sum(); fn += (~a & yy & msk).sum()
                        post = ~yy & msk & (lab[k]['tras'] <= 14)
                        m1[0] += (a & post).sum(); m1[1] += post.sum()
                        for q, xx in enumerate((a & yy & msk, a & ~yy & msk, ~a & yy & msk)):
                            for mo in range(12):
                                Cb[q, :, mo] += xx[mes == mo + 1].sum(0)
                    r.update({f'tp_{d}': int(tp), f'fp_{d}': int(fp), f'fn_{d}': int(fn), f'M1_{d}': m1[0] / max(m1[1], 1)})
                    bloques[(dt, nv, y, d)] = Cb
                if nv == DECLARADOS[0]:
                    for d in DELTAS:
                        ys = np.concatenate([lab[k]['y'][comun[f'final_{y}_{k:02d}_d{d}'] & cl] for k in range(1, N_CAL + 1)])
                        ss = np.concatenate([S[(dt, f'final_{y}_{k:02d}_d{d}')][comun[f'final_{y}_{k:02d}_d{d}'] & cl]
                                             for k in range(1, N_CAL + 1)])
                        r[f'PRAUC_{d}'] = float(average_precision_score(ys, ss))
                filas.append(r)
    t = pd.DataFrame(filas)
    # agregado 2017–2019
    agg = t.drop(columns=[c for c in t.columns if c.startswith('PRAUC')]).groupby(['detector', 'nivel']).sum(numeric_only=True).reset_index()
    for df in (t, agg):
        for d in DELTAS:
            P = df[f'tp_{d}'] / (df[f'tp_{d}'] + df[f'fp_{d}']).clip(lower=1)
            R = df[f'tp_{d}'] / (df[f'tp_{d}'] + df[f'fn_{d}'])
            df[f'precision_{d}'], df[f'recall_{d}'] = P, R
            df[f'F1_{d}'] = np.where(P + R > 0, 2 * P * R / (P + R).where(P + R > 0, 1), 0)
        df['Fbar'] = df[[f'F1_{d}' for d in DELTAS]].mean(axis=1)
    agg['fa_limpia'] = agg['alarmas_limpias'] / agg['dias_limpios']
    agg['alarmas_por_estacion_anio'] = agg['fa_limpia'] * 365
    t.to_csv(SAL / 'metricas_por_anio.csv', index=False)
    agg.drop(columns=['anio', 'umbral'], errors='ignore').to_csv(SAL / 'curva_operacion_2017_2019.csv', index=False)
    # dos pruebas declaradas: bootstrap pareado de bloques estación × año-mes, IC 97.5 %
    rng = np.random.default_rng(cm.SEMILLA_BOOT)
    nb = len(obj) * 12 * len(ANIOS)
    W = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb) for _ in range(2000)], axis=1).astype(float)
    uno = np.ones((nb, 1))

    def fbar(dt, nv, w):
        f = []
        for d in DELTAS:
            Cb = np.concatenate([bloques[(dt, nv, y, d)].reshape(3, -1) for y in ANIOS], axis=1)
            tt = np.einsum('qb,bn->qn', Cb, w)
            P = tt[0] / np.maximum(tt[0] + tt[1], 1e-12)
            R = tt[0] / np.maximum(tt[0] + tt[2], 1e-12)
            f.append(np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0))
        return np.mean(f, axis=0)

    pruebas = []
    for nv in DECLARADOS:
        for a, b in (('Ens-Vbr', 'Ens-V0r'), ('Ens-Vbr', 'L0rev14')):
            dd = fbar(a, nv, W) - fbar(b, nv, W)
            pruebas.append(dict(nivel=nv, a=a, b=b, dFbar=float((fbar(a, nv, uno) - fbar(b, nv, uno))[0]),
                                ic975_inf=float(np.quantile(dd, 0.0125)), ic975_sup=float(np.quantile(dd, 0.9875)),
                                declarada=(b == 'Ens-V0r')))
    pr = pd.DataFrame(pruebas)
    pr.to_csv(SAL / 'pruebas_declaradas.csv', index=False)
    decl = pr[pr.declarada]
    adopta = bool(((decl.dFbar >= 0.02) & (decl.ic975_inf > 0)).any())
    res = dict(diferencia_maxima_corridas=dif, adopcion_ens_vbr=adopta,
               umbrales_2023={f'{dt}_{nv}': umbral[(dt, nv)] for dt in DETECTORES for nv in NIVELES})
    (SAL / 'decision.json').write_text(json.dumps(res, indent=2))
    cols = ['detector', 'nivel', 'fa_limpia', 'alarmas_por_estacion_anio', 'Fbar'] + [f'{m}_{d}' for d in DELTAS for m in ('F1', 'recall', 'precision')]
    print(agg[agg.nivel.isin(DECLARADOS)][cols].round(4).to_string(index=False))
    print(pr.round(4).to_string(index=False))
    print(json.dumps(dict(diferencia_maxima_corridas=dif, adopcion_ens_vbr=adopta)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--etapa', required=True, choices=['planes', 'modelos', 'calibracion', 'holdout', 'metricas'])
    ap.add_argument('--corrida', default='a', choices=['a', 'b'])
    a = ap.parse_args()
    if a.etapa == 'planes':
        etapa_planes()
        return
    ctx = cm.contexto()
    {'modelos': etapa_modelos, 'calibracion': etapa_calibracion, 'metricas': etapa_metricas}.get(
        a.etapa, lambda c: etapa_holdout(c, a.corrida))(ctx)


if __name__ == '__main__':
    main()
