"""Piezas comunes de la exploración de líneas base (2022) y de la revisión LB1.

Sólo abre 2020–2022: `asegurar_matrices` lee 20RAMA.zip–22RAMA.zip con su SHA-256. Las matrices
se regeneran desde los planes guardados y se comprueban contra `resumen_matrices.csv`
(con fin de línea '\\n', para que el SHA-256 sea igual en Windows y Linux).
"""
from __future__ import annotations

import gzip
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'experiments/anomalias_red'))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402
from src.detect import multianual as mu  # noqa: E402

SAL_RED = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL_RED / 'matrices', SAL_RED / 'planes'
SELECCION = ('2020-01-01', '2021-12-31 23:00')
VALIDACION = ('2022-01-01', '2022-12-31 23:00')
DELTAS_EVAL = (100, 50, 20)
SEMILLA_BOOT = [42, 29, 3]


def _sha_csv(x: pd.DataFrame) -> str:
    return hashlib.sha256(x.to_csv(float_format='%.10g', lineterminator='\n').encode()).hexdigest()


def asegurar_matrices(nombres) -> None:
    """Regenera (si faltan) las matrices pedidas y verifica su SHA-256 contra el repo."""
    from generar_planes import alterables_v4
    resumen = pd.read_csv(SAL_RED / 'resumen_matrices.csv').set_index('archivo')['sha256_csv']
    faltan = [k for k in nombres if not (MATRICES / f'matriz_{k}.csv.gz').exists()]
    if not faltan:
        return
    largo, _ = mu.cargar_o3_zips(RAIZ / 'data/raw', mu.leer_checksums(RAIZ / 'docs/checksums_2020_2026.txt'),
                                 anios=range(2020, 2023))
    valores, _ = mu.matriz_fija(largo)
    cols = ar.columnas_entrada(mu.canales_inactivos(valores, mu.AJUSTE_DEFINITIVO))
    v = valores.loc['2020-01-01':'2022-12-31 23:00']
    cal = ar.calendarios_entrenamiento().set_index('corrida')
    MATRICES.mkdir(parents=True, exist_ok=True)
    for k in faltan:
        if k == 'limpia_2020_2022':
            x = ar.matriz_red(v, cols)
        else:
            corrida, d = k.rsplit('_d', 1)
            plan = ar.leer_plan(PLANES / f'plan_{corrida}.csv')
            fila = cal.loc[corrida].to_dict() | {'corrida': corrida}
            pd.testing.assert_frame_equal(plan, ar.plan_de(fila, alterables_v4()), check_dtype=False)
            rec, cam = ar.aplicar(v, plan, int(d) / 100)
            x = ar.matriz_red(rec, cols, cam)
        if _sha_csv(x) != resumen[f'matriz_{k}.csv.gz']:
            raise RuntimeError(f'{k}: SHA-256 distinto del registrado')
        with gzip.GzipFile(MATRICES / f'matriz_{k}.csv.gz', 'wb', mtime=0) as f:
            f.write(x.to_csv(float_format='%.10g', lineterminator='\n').encode())


def leer(nombre: str) -> pd.DataFrame:
    return ar.leer_matriz(MATRICES / f'matriz_{nombre}.csv.gz')


def nombres_eval() -> list[str]:
    return ['limpia_2020_2022'] + [f'entrenamiento_{i:02d}_d{d}' for d in DELTAS_EVAL for i in range(1, 11)]


def contexto() -> dict:
    """σ, vecinas, escala a14 de V0 (2020–2021), posiciones y objetivos; igual que la revisión 14."""
    from entrenar_lstm_sup import parametros_vecinas
    from generar_planes import alterables_v4
    limpia = leer('limpia_2020_2022')
    _, sigma = ev.normalizacion(limpia)
    par = parametros_vecinas('a14', limpia.loc[SELECCION[0]:SELECCION[1]], sigma, 'media')
    est = ev.estaciones_de(limpia)
    idx = limpia.index

    def pos(a, b):
        p = np.flatnonzero((idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(b)))
        return p[p >= 23]

    return dict(limpia=limpia, estaciones=est, objetivos=alterables_v4(), vecinas=par.vecinas,
                vec=lb.indices_vecinas(est, par.vecinas), sigma=sigma[est].to_numpy(),
                escala_v0=par.escala[est].to_numpy(), index=idx, p_tr=pos(*SELECCION), p_va=pos(*VALIDACION))


def bases(ctx: dict, x: pd.DataFrame, tau: np.ndarray | None = None) -> dict[str, np.ndarray]:
    V = lb.valores(x, ctx['estaciones'])
    b0 = lb.base_v0(x, ctx['estaciones'])
    out = {'V0': b0, 'Vb': lb.base_vb(V, b0, ctx['vec'], x.index)}
    if tau is not None:
        out['Vc'] = lb.base_vc(V, b0, tau, x.index)
    return out


def ventanas(ctx, F, s, pos):
    return ll.ventanas_locales(F, ctx['estaciones'], ctx['vecinas'], s, pos)


def puntuar(ctx, modelo, F, x) -> pd.DataFrame:
    """Probabilidad horaria de 2022 por objetivo → puntaje `promedio_dia` (≥ 12 horas)."""
    pos, obj = ctx['p_va'], ctx['objetivos']
    X = np.concatenate([ventanas(ctx, F, s, pos) for s in obj])
    p = modelo.predict(X, batch_size=8192, verbose=0).astype(np.float64).reshape(len(obj), len(pos)).T
    ix = x.index[pos]
    con = x.loc[ix, [f'{s}_mascara' for s in obj]].to_numpy() == 1
    return ed.juntar_dia(pd.DataFrame(p, index=ix, columns=obj).where(con), 'promedio_dia')


def etiquetas(ctx, dias) -> dict:
    """Por calendario 01–10: atacado (día × objetivo), días desde el fin del episodio propio y día del episodio."""
    obj, out = ctx['objetivos'], {}
    for i in range(1, 11):
        c = f'entrenamiento_{i:02d}'
        plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
        y = pd.DataFrame(False, index=dias, columns=obj)
        tras = pd.DataFrame(np.inf, index=dias, columns=obj)
        dia_ep = pd.DataFrame(0, index=dias, columns=obj)
        for e in plan.itertuples():
            if e.estacion not in obj:
                continue
            for j, d in enumerate(pd.date_range(e.inicio.normalize(), e.fin.normalize())):
                if d in y.index:
                    y.loc[d, e.estacion] = True
                    dia_ep.loc[d, e.estacion] = j + 1
            for k in range(1, 15):
                t = e.fin.normalize() + pd.Timedelta(days=k)
                if t in tras.index:
                    tras.loc[t, e.estacion] = min(tras.loc[t, e.estacion], k)
        out[c] = dict(y=y.to_numpy(), tras=tras.to_numpy(), dia=dia_ep.to_numpy(), plan=plan)
    return out


def _comunes(S, modelos):
    return {k: np.logical_and.reduce([~np.isnan(S[(mn, k)]) for mn in modelos]) for k in nombres_eval()}


def metricas(S: dict, modelos, lab: dict, nivel: float) -> pd.DataFrame:
    """S[(modelo, matriz)] = día × objetivo (2022). Estación-días comunes a todos los modelos."""
    from sklearn.metrics import average_precision_score
    comun = _comunes(S, modelos)
    cl = comun['limpia_2020_2022']
    filas = []
    for mn in modelos:
        u = ev.umbral_falsas_alarmas(S[(mn, 'limpia_2020_2022')][cl], nivel)
        r = dict(modelo=mn, nivel=nivel, umbral=u)
        for d in DELTAS_EVAL:
            tp = fp = fn = 0
            c1, c2, c4, ys, ss = [0, 0], [0, 0], [0, 0], [], []
            for c, L in lab.items():
                k = f'{c}_d{d}'
                s, cm, y = S[(mn, k)], comun[k] & cl, L['y']
                a = s > u
                tp += (a & y & cm).sum(); fp += (a & ~y & cm).sum(); fn += (~a & y & cm).sum()
                post = ~y & cm & (L['tras'] <= 14)
                resto = ~y & cm & ~(L['tras'] <= 14)
                tarde = y & cm & (L['dia'] >= 3)
                c1[0] += (a & post).sum(); c1[1] += post.sum()
                c2[0] += (a & resto).sum(); c2[1] += resto.sum()
                c4[0] += (a & tarde).sum(); c4[1] += tarde.sum()
                ys.append(y[cm]); ss.append(s[cm])
            P = tp / (tp + fp) if tp + fp else 0.0
            R = tp / (tp + fn)
            r.update({f'F1_{d}': 2 * P * R / (P + R) if P + R else 0.0, f'recall_{d}': R, f'precision_{d}': P,
                      f'M1_{d}': c1[0] / c1[1], f'M2_{d}': c2[0] / c2[1], f'M4_{d}': c4[0] / c4[1]})
            if nivel == 0.01:
                r[f'PRAUC_{d}'] = average_precision_score(np.concatenate(ys), np.concatenate(ss))
        r['Fbar'] = float(np.mean([r[f'F1_{d}'] for d in DELTAS_EVAL]))
        filas.append(r)
    return pd.DataFrame(filas)


def bootstrap_dfbar(S, dias, a: str, b: str, modelos, lab, nivel, n: int = 2000):
    """ΔF̄ (a − b): bootstrap pareado de bloques estación-mes, calendarios juntos, umbrales fijos."""
    comun = _comunes(S, modelos)
    cl = comun['limpia_2020_2022']
    mes = pd.DatetimeIndex(dias).month.to_numpy()
    nobj = S[(a, 'limpia_2020_2022')].shape[1]

    def conteos(mn):
        u = ev.umbral_falsas_alarmas(S[(mn, 'limpia_2020_2022')][cl], nivel)
        C = np.zeros((len(DELTAS_EVAL), 3, nobj, 12))
        for di, d in enumerate(DELTAS_EVAL):
            for c, L in lab.items():
                k = f'{c}_d{d}'
                s, cm, y = S[(mn, k)], comun[k] & cl, L['y']
                al = s > u
                for q, msk in enumerate((al & y & cm, al & ~y & cm, ~al & y & cm)):
                    for mo in range(12):
                        C[di, q, :, mo] += msk[mes == mo + 1].sum(0)
        return C.reshape(len(DELTAS_EVAL), 3, -1)

    def fbar(C, w):
        t = C @ w
        P = t[:, 0] / np.maximum(t[:, 0] + t[:, 1], 1e-12)
        R = t[:, 0] / np.maximum(t[:, 0] + t[:, 2], 1e-12)
        return np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0).mean(0)

    Ca, Cb = conteos(a), conteos(b)
    nb = Ca.shape[2]
    rng = np.random.default_rng(SEMILLA_BOOT)
    W = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb) for _ in range(n)], axis=1).astype(float)
    uno = np.ones((nb, 1))
    d = fbar(Ca, W) - fbar(Cb, W)
    return float(fbar(Ca, uno)[0] - fbar(Cb, uno)[0]), float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
