"""Revisión 24: Ens-Vb-X, Ens-Vb-R congelado con exclusión de vecinas sospechosas (idea del tesista).

    python rev24.py planes
    python rev24.py validar
    python rev24.py puntuar --etapa diseno|calibracion|banco|despliegue --corrida a [--parte i --partes n --hilos h]
    python rev24.py lanzar  --etapa ... --corrida a [--partes 4 --hilos 4]
    python rev24_metricas.py diseno|banco|despliegue

Registro: docs/registro_previo_rev24_exclusion_vecinas.md (precisiones al final). También es el motor de la
revisión 23b (rev23b.py): `Periodo` puntúa cualquier combinación de grupos (Vb, Vx con τ, V0) y PARAAD/R3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent / 'anomalias_red'))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import comun as cm  # noqa: E402
import rev22_comun as rc  # noqa: E402
import rev23 as r23  # noqa: E402
from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/rev24'
TAUS = tuple(json.loads((cm.RAIZ / 'results/linea_base/rev24/grilla_tau.json').read_text())['tau'])  # enmienda 1
CALS22 = [f'entrenamiento_{i:02d}' for i in range(1, 11)]
TAM_BANCO = ('d100', 'd50', 'd20', 'a10', 'a20', 'a40')
ESC_BANCO = ('E1', 'E2-1', 'E2-2', 'E2-4')
DISENO = {'E1': ('d100', 'd50', 'd20'), 'E2-1': ('d50', 'a20'), 'E2-2': ('d50', 'a20')}
LOTE = r23.LOTE


# ---------------------------------------------------------------- la regla
def senal_z(V: np.ndarray, b0: np.ndarray, sigma: np.ndarray, index) -> np.ndarray:
    """z_i(t): media de las últimas 24 h (≥ 12 con dato) de la desviación V0 / σ."""
    d0 = (V - b0) / sigma
    return pd.DataFrame(d0, index=index).rolling(24, min_periods=12).mean().to_numpy()


def exclusion(z: np.ndarray, vec: np.ndarray, tau: float) -> np.ndarray:
    """(horas, estaciones, 4): la vecina j de s es sospechosa (precisión 3 y regla del registro)."""
    Z = z[:, vec]
    H, S, K = Z.shape
    E = np.zeros((H, S, K), bool)
    if not np.isfinite(tau):
        return E
    with np.errstate(all='ignore'):
        for j in range(K):
            otras = np.delete(Z, j, axis=2)
            m = np.nanmedian(otras, axis=2)
            m[(~np.isnan(otras)).sum(axis=2) < 2] = np.nan
            dn, ds = Z[:, :, j] - m, z - m
            E[:, :, j] = (np.abs(dn) > tau) & (np.abs(ds) > tau) & (np.sign(dn) == np.sign(ds))
    E[E.sum(axis=2) > 2] = False
    return E


def base_vb_x(V, b0, vec, index, E):
    with np.errstate(all='ignore'):
        perfil = np.nanmean(np.where(E, np.nan, b0[:, vec]), axis=2)
        xv = np.nanmean(np.where(E, np.nan, V[:, vec]), axis=2)
    b = perfil + lb.mediana_hora(V - xv, index)
    return np.where(np.isnan(b), b0, b)


def entradas_x(x, base, estaciones, sigma, escala, vec, E, V):
    """Como `lb.entradas`, pero sin las vecinas excluidas en el promedio de a14."""
    d = (V - base) / sigma
    nb = np.where(E, np.nan, d[:, vec])
    n = np.sum(~np.isnan(nb), axis=2)
    with np.errstate(all='ignore'):
        prom = np.nanmean(nb, axis=2)
    a14 = np.where(~np.isnan(d) & (n >= 2), d - prom, np.nan) / escala
    mascara = x[[f'{s}_mascara' for s in estaciones]].to_numpy(np.float32)
    hora = x[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    return np.concatenate([np.nan_to_num(d, nan=0.0).astype(np.float32), mascara, hora,
                           np.nan_to_num(a14, nan=0.0).astype(np.float32)], axis=1)


# ---------------------------------------------------------------- modelos de selección (diseño en 2022)
class Seleccion:
    """Los 5 modelos de selección Vb-R de la revisión 22, con la misma inferencia bit a bit que `r23.Detectores`."""

    def __init__(self):
        import keras
        import tensorflow as tf
        self.tf, self.modo = tf, 'tf'
        reg = json.loads((SAL / 'modelos_seleccion_sha256.json').read_text())
        self.nombres = {'Vb': [rc.nombre_modelo('Vb', 'R', s) for s in rc.SEMILLAS]}
        ms = []
        for nm in self.nombres['Vb']:
            p = rc.MOD / f'{nm}.keras'
            assert r23.sha(p) == reg[nm], f'{nm}: SHA-256 distinto'
            ms.append(keras.models.load_model(p, compile=False))
        self.f = {'Vb': [tf.function(lambda a, m=m: m(a, training=False)) for m in ms]}

    predecir = r23.Detectores.predecir


# ---------------------------------------------------------------- motor
class Periodo:
    """Historia + periodo evaluado; puntaje limpio en caché y matrices alteradas incrementales.

    grupos: 'Vb', 'V0' (con L0 único) y ('Vx', τ). extra: subconjunto de {'PARAAD', 'R3'}."""

    def __init__(self, v: pd.DataFrame, ini, ctx, esc, det, grupos, extra=(), h3=None, incremental=True):
        self.ctx, self.esc, self.det, self.incremental = ctx, esc, det, incremental
        self.grupos, self.extra, self.h3 = list(grupos), tuple(extra), h3
        self.cols = rc.columnas()
        self.obj = list(ctx['objetivos'])
        self.est = list(ctx['estaciones'])
        ini = pd.Timestamp(ini)
        self.vy = v.loc[ini:]
        self.xh = ar.matriz_red(v.loc[:ini - pd.Timedelta(hours=1)], self.cols)
        x = ar.matriz_red(v, self.cols)
        self.n = len(x)
        self.pos = np.flatnonzero(x.index >= ini)
        self.ix = x.index[self.pos]
        self.con = x.iloc[self.pos][[f'{s}_mascara' for s in self.obj]].to_numpy() == 1
        self.loc_idx = {s: ll.indices_locales(self.est, ctx['vecinas'], s) for s in self.obj}
        self.i_est = {s: self.est.index(s) for s in self.obj}
        self.F0, self.E0 = self.entradas(x)
        self.P0 = {g: self.horarios(g, self.F0[g], self.E0.get(g), None) for g in self.claves()}
        self.limpio = self.diarios(ar.matriz_red(self.vy, self.cols), self.P0)

    def claves(self):
        return [g if isinstance(g, str) else f'Vx{g[1]:.4g}' for g in self.grupos]

    @staticmethod
    def modelos_de(clave):
        return 'Vb' if clave.startswith('Vx') else clave

    def entradas(self, x: pd.DataFrame):
        V = lb.valores(x, self.est)
        b0 = lb.base_v0(x, self.est)
        vec, sig = self.ctx['vec'], self.ctx['sigma']
        F, E, z = {}, {}, None
        for g in self.grupos:
            if g == 'Vb':
                F['Vb'] = lb.entradas(x, lb.base_vb(V, b0, vec, x.index), self.est, sig, self.esc['Vb'], vec, V)
            elif g == 'V0':
                F['V0'] = lb.entradas(x, b0, self.est, sig, self.esc['V0'], vec, V)
            else:
                tau, k = g[1], f'Vx{g[1]:.4g}'
                if z is None:
                    z = senal_z(V, b0, sig, x.index)
                E[k] = exclusion(z, vec, tau)
                F[k] = entradas_x(x, base_vb_x(V, b0, vec, x.index, E[k]), self.est, sig, self.esc['Vb'], vec, E[k], V)
        return F, E

    def cambio(self, g, F, E, s):
        a0 = self.pos[0] - 23
        il = self.loc_idx[s]
        dif = (F[a0:, il] != self.F0[g][a0:, il]).any(axis=1)
        if E is not None:
            i = self.i_est[s]
            dif |= (E[a0:, i] != self.E0[g][a0:, i]).any(axis=1)
        c = np.concatenate([[0], np.cumsum(dif)])
        q = self.pos - a0
        return (c[q + 1] - c[q - 23]) > 0

    def ventanas(self, F, E, s, p):
        X = ll.ventanas_locales(F, self.est, self.ctx['vecinas'], s, p)
        if E is not None:
            Ew = E[p[:, None] + np.arange(-23, 1)[None, :], self.i_est[s], :]       # (n, 24, 4)
            for j in range(4):
                X[:, :, 3 * (j + 1):3 * (j + 1) + 3][Ew[:, :, j]] = 0.0
        return X

    def horarios(self, g, F, E, previo):
        mg = self.modelos_de(g)
        S, H, M = len(self.obj), len(self.pos), len(self.det.nombres[mg])
        P = np.full((S, H, M), np.nan, np.float32) if previo is None else previo[0].copy()
        Xs, sel_ = [], []
        for j, s in enumerate(self.obj):
            sel = self.con[:, j].copy()
            if previo is not None and self.incremental:
                sel &= self.cambio(g, F, E, s)
            if sel.any():
                Xs.append(self.ventanas(F, E, s, self.pos[sel]))
                sel_.append((j, np.flatnonzero(sel)))
        n = 0
        if Xs:
            Y = self.det.predecir(mg, np.concatenate(Xs))
            for j, h in sel_:
                P[j, h] = Y[n:n + len(h)]
                n += len(h)
        return P, n

    def diarios(self, xm, P):
        out, por = {}, {}
        for g in self.claves():
            mg = self.modelos_de(g)
            for m, nm in enumerate(self.det.nombres[mg]):
                h = P[g][0][:, :, m].astype(np.float64).T
                dd = ed.juntar_dia(pd.DataFrame(h, index=self.ix, columns=self.obj).where(self.con), 'promedio_dia')
                por[(g, nm)] = dd.to_numpy()
                self.dias = dd.index
            if g == 'Vb':
                out['Ens-Vb-R'] = np.mean([por[(g, n)] for n in self.det.nombres['Vb']], axis=0)
            elif g == 'V0':
                out['Ens-V0-R'] = np.mean([por[(g, n)] for n in self.det.nombres['V0'][:5]], axis=0)
                out['L0unico'] = por[(g, 'L0unico')]
            else:
                out[f'Ens-Vb-X{g[2:]}'] = np.mean([por[(g, n)] for n in self.det.nombres['Vb']], axis=0)
        if 'PARAAD' in self.extra:
            out['PARAAD'] = self.det.paraad(xm).reindex(self.dias)[self.obj].to_numpy()
        if 'R3' in self.extra:
            out['R3'] = self.det.r3(self.h3, xm, self.obj).reindex(self.dias)[self.obj].to_numpy()
        return out

    def alterada(self, rec: pd.DataFrame, cam: pd.DataFrame, plan: pd.DataFrame):
        xm = ar.matriz_red(rec, self.cols, cam)
        x = pd.concat([self.xh, xm])
        assert len(x) == self.n
        F, E = self.entradas(x)
        P = {g: self.horarios(g, F[g], E.get(g), self.P0[g]) for g in self.claves()}
        S = self.diarios(xm, P)
        ep = pd.DataFrame(False, index=self.vy.index, columns=self.vy.columns)
        for e in plan.itertuples():
            ep.loc[e.inicio:e.fin, e.estacion] = True
        ok = ep.to_numpy() & self.vy.notna().to_numpy()
        dif = np.abs(rec.to_numpy() - self.vy.to_numpy())[ok]
        info = dict(horas_episodio=int(ok.sum()), cambio_medio_ppb=float(dif.mean()) if len(dif) else np.nan,
                    ventanas={g: P[g][1] for g in self.claves()},
                    exclusiones={g: int(E[g].sum()) for g in E})
        return S, info


def alterar(vy, plan, tam):
    if tam[0] == 'd':
        return ar.aplicar(vy, plan, int(tam[1:]) / 100)
    return ar.aplicar_fijo(vy, plan, int(tam[1:]))


# ---------------------------------------------------------------- planes
def derivar_k(plan: pd.DataFrame, kv: int, kcal: int, vecinas: dict, alterables: list) -> pd.DataFrame:
    """E2-k: s y k vecinas alterables, barajadas con [42, 24, k_cal, episodio] y anidadas (precisión 1)."""
    base = plan.copy()
    base['papel'] = 'original'
    base['origen'] = base['episodio']
    ocupado: dict[str, set] = {}
    for r in plan.itertuples():
        ocupado.setdefault(r.estacion, set()).update(pd.date_range(r.inicio.normalize(), r.fin.normalize()))
    nuevas = []
    for r in plan.sort_values('episodio').itertuples():
        vs = [t for t in vecinas[r.estacion] if t in alterables]
        orden = [vs[i] for i in np.random.default_rng([42, 24, kcal, int(r.episodio)]).permutation(len(vs))]
        dias = pd.date_range(r.inicio.normalize(), r.fin.normalize())
        j = 0
        for t in orden[:kv]:
            libres = [d for d in dias if d not in ocupado.setdefault(t, set())]
            ocupado[t].update(libres)
            for tr in r23.tramos(libres):
                j += 1
                nuevas.append(dict(corrida=r.corrida, episodio=1000 * int(r.episodio) + j, estacion=t, inicio=tr[0],
                                   fin=tr[-1] + pd.Timedelta(hours=23), dias_sorteados=int(r.dias_sorteados),
                                   dias=len(tr), signo=int(r.signo), p=float(r.p), papel='añadida',
                                   origen=int(r.episodio)))
    out = pd.concat([base, pd.DataFrame(nuevas)], ignore_index=True) if nuevas else base
    ar.validar_plan(out)
    return out


def ruta_plan(etapa, c, esc):
    return SAL / 'planes' / etapa / f'plan_{c}_{esc}.csv'


def leer_plan(etapa, c, esc):
    if etapa == 'banco' and esc in ('E1', 'E2-4'):
        return r23.leer_plan(c, 'E1' if esc == 'E1' else 'E2')
    p = pd.read_csv(ruta_plan(etapa, c, esc), parse_dates=['inicio', 'fin'])
    ar.validar_plan(p)
    return p


def etapa_planes():
    (SAL / 'planes').mkdir(parents=True, exist_ok=False)
    vecinas = json.loads((rc.SAL / 'vecinas_vb.json').read_text())
    alterables = list(rc.objetivos())
    reg = {}
    # modelos de selección: SHA-256 antes de usarlos
    sel = {nm: r23.sha(rc.MOD / f'{nm}.keras') for nm in [rc.nombre_modelo('Vb', 'R', s) for s in rc.SEMILLAS]}
    (SAL / 'modelos_seleccion_sha256.json').write_text(json.dumps(sel, indent=2) + '\n', encoding='utf8')
    for etapa, cals in (('diseno', CALS22), ('banco', r23.CALS)):
        (SAL / 'planes' / etapa).mkdir()
        for k, c in enumerate(cals, start=1):
            orig = r23.PLANES0 / f'plan_{c}.csv'
            plan = ar.leer_plan(orig)
            if etapa == 'diseno':
                plan = plan[plan.inicio >= '2022-01-01'].reset_index(drop=True)
            reg[f'original/{orig.name}'] = r23.sha_texto(orig)
            escs = {'E1': 0, 'E2-1': 1, 'E2-2': 2} if etapa == 'diseno' else {'E2-1': 1, 'E2-2': 2}
            for esc, kv in escs.items():
                p = derivar_k(plan, kv, k, vecinas, alterables)
                p.to_csv(ruta_plan(etapa, c, esc), index=False, lineterminator='\n', date_format='%Y-%m-%d %H:%M:%S')
                assert len(leer_plan(etapa, c, esc)) == len(p)
                reg[f'{etapa}/{ruta_plan(etapa, c, esc).name}'] = r23.sha_texto(ruta_plan(etapa, c, esc))
    (SAL / 'planes_sha256.json').write_text(json.dumps(reg, indent=2) + '\n', encoding='utf8')
    print(f'{len(reg)} planes registrados', flush=True)


def verificar_planes():
    for nombre, h in json.loads((SAL / 'planes_sha256.json').read_text()).items():
        d, f = nombre.split('/')
        p = r23.PLANES0 / f if d == 'original' else SAL / 'planes' / d / f
        assert r23.sha_texto(p) == h, f'plan modificado: {nombre}'
    r23.verificar_planes()


# ---------------------------------------------------------------- etapas de puntuación
def tau_elegido() -> float:
    return float(json.loads((SAL / 'decision_tau.json').read_text())['tau'])


def configurar(etapa):
    """(años o periodos, tareas, grupos, extra, fase de modelos) de cada etapa."""
    if etapa == 'diseno':
        tareas = [('limpia', 2022, None, None)] + [(c, 2022, e, t) for c in CALS22 for e, ts in DISENO.items()
                                                    for t in ts]
        return tareas, ['Vb'] + [('Vx', t) for t in TAUS], (), 'seleccion'
    if etapa == 'calibracion':
        return [('limpia', 2023, None, None)], ['Vb', ('Vx', tau_elegido())], (), 'definitivo'
    if etapa == 'banco':
        tareas = [('limpia', a, None, None) for a in (2024, 2025, 2026)]
        tareas += [(c, r23.anio_de(c), e, t) for c in r23.CALS for e in ESC_BANCO for t in TAM_BANCO]
        return sorted(tareas, key=lambda r: (r[1], r[0] != 'limpia', r[0], r[2] or '', r[3] or '')), \
            ['Vb', ('Vx', tau_elegido())], ('PARAAD',), 'definitivo'
    if etapa == 'despliegue':
        import rev22_examen as rx
        tareas = [('limpia', 2026, None, None)] + [(f'despliegue_{k:02d}', 2026, 'E1', f'd{d}')
                                                    for k in range(1, rx.N_CAL + 1) for d in rx.DELTAS]
        return tareas, ['Vb', ('Vx', tau_elegido())], (), 'definitivo'
    raise ValueError(etapa)


def nombre_tarea(t):
    return f'limpia_{t[1]}' if t[0] == 'limpia' else f'{t[0]}_{t[2]}_{t[3]}'


def periodo_de(etapa, anio, ctx, esc, det, grupos, extra):
    if etapa == 'despliegue':
        import rev22_examen as rx
        return Periodo(rx.valores(), rx.INI, ctx, esc, det, grupos, extra)
    fin = {2022: '2022-12-31 23:00', **r23.FIN}[anio]
    return Periodo(rc.valores('2020-01-01', fin), f'{anio}-01-01', ctx, esc, det, grupos, extra)


def plan_de(etapa, t):
    if etapa == 'despliegue':
        import rev22_examen as rx
        p = rx.plan(int(t[0].split('_')[1])).copy()
        p['papel'], p['origen'] = 'original', p['episodio']
        return p
    return leer_plan(etapa, t[0], t[2])


def etapa_puntuar(etapa, corrida, parte, partes, hilos):
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(hilos)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    verificar_planes()
    T, grupos, extra, fase = configurar(etapa)
    mias = [T[i] for i in range(len(T)) if i * partes // len(T) == parte]
    sal = SAL / etapa / f'corrida_{corrida}'
    sal.mkdir(parents=True, exist_ok=True)
    det = Seleccion() if fase == 'seleccion' else r23.Detectores()
    ctx = cm.contexto()
    esc = rc.escalas(ctx, fase)
    actual, anio_actual, t0 = None, None, time.time()
    for n, t in enumerate(mias, start=1):
        p = sal / f'{nombre_tarea(t)}.npz'
        if p.exists():
            continue
        if actual is None or anio_actual != t[1]:
            actual = None
            actual = periodo_de(etapa, t[1], ctx, esc, det, grupos, extra)
            anio_actual = t[1]
        if t[0] == 'limpia':
            S, info = actual.limpio, {}
        else:
            plan = plan_de(etapa, t)
            rec, cam = alterar(actual.vy, plan, t[3])
            S, info = actual.alterada(rec, cam, plan)
        r23.guardar(p, dias=actual.dias.values.astype('datetime64[ns]'), **S, info=np.array(json.dumps(info)))
        print(f'{time.strftime("%H:%M:%S")} {etapa} parte {parte}: {n}/{len(mias)} {nombre_tarea(t)} '
              f'({(time.time() - t0) / n:.1f} s/tarea)', flush=True)
    print(f'{etapa} parte {parte} lista en {time.time() - t0:.0f} s', flush=True)


def etapa_lanzar(etapa, corrida, partes, hilos, script='rev24.py'):
    logs = SAL / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS=str(hilos), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', TF_CPP_MIN_LOG_LEVEL='2')
    ps = []
    for i in range(partes):
        f = open(logs / f'{etapa}_{corrida}_parte{i}.log', 'w', encoding='utf8')
        ps.append((subprocess.Popen([sys.executable, str(AQUI / script), 'puntuar', '--etapa', etapa, '--corrida',
                                     corrida, '--parte', str(i), '--partes', str(partes), '--hilos', str(hilos)],
                                    cwd=AQUI, stdout=f, stderr=subprocess.STDOUT, env=env), f))
    t0 = time.time()
    for p, f in ps:
        p.wait()
        f.close()
    cod = [p.returncode for p, _ in ps]
    print(f'{etapa} {corrida}: códigos {cod} en {time.time() - t0:.0f} s', flush=True)
    if any(cod):
        raise SystemExit(1)


# ---------------------------------------------------------------- validación
def etapa_validar(hilos):
    """τ = ∞ reproduce Ens-Vb-R bit a bit, y el puntaje incremental de Vx coincide con el completo."""
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(hilos)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    verificar_planes()
    det = r23.Detectores()
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    v = rc.valores('2020-01-01', r23.FIN[2025])
    out = {}
    P = Periodo(v, '2025-01-01', ctx, esc, det, ['Vb', ('Vx', float('inf')), ('Vx', TAUS[0])])
    out['limpio_tau_inf_igual_Vb'] = float(np.nanmax(np.abs(P.limpio['Ens-Vb-Xinf'] - P.limpio['Ens-Vb-R'])))
    a23 = np.load(r23.SAL / 'corrida_a' / 'limpia_2025.npz')
    out['limpio_Vb_igual_rev23'] = float(np.nanmax(np.abs(P.limpio['Ens-Vb-R'] - a23['Ens-Vb-R'])))
    for c, e, t in (('final_2025_01', 'E2-1', 'd50'), ('final_2025_04', 'E2-4', 'a20')):
        plan = leer_plan('banco', c, e)
        rec, cam = alterar(P.vy, plan, t)
        S1, i1 = P.alterada(rec, cam, plan)
        P.incremental = False
        S2, i2 = P.alterada(rec, cam, plan)
        P.incremental = True
        r = dict(dif_incremental={k: float(np.nanmax(np.abs(S1[k] - S2[k]))) for k in S1},
                 tau_inf_igual_Vb=float(np.nanmax(np.abs(S1['Ens-Vb-Xinf'] - S1['Ens-Vb-R']))),
                 ventanas=[i1['ventanas'], i2['ventanas']], exclusiones=i1['exclusiones'])
        if e == 'E2-4':
            z = np.load(r23.SAL / 'corrida_a' / f'{c}_E2_{t}.npz')
            r['Vb_igual_rev23'] = float(np.nanmax(np.abs(S1['Ens-Vb-R'] - z['Ens-Vb-R'])))
        out[f'{c}_{e}_{t}'] = r
    out['exclusiones_limpio_2025'] = {k: int(E.sum()) for k, E in P.E0.items()}
    out['cumple'] = bool(out['limpio_tau_inf_igual_Vb'] == 0 and out['limpio_Vb_igual_rev23'] == 0 and all(
        max(r['dif_incremental'].values()) == 0 and r['tau_inf_igual_Vb'] == 0 and r.get('Vb_igual_rev23', 0) == 0
        for k, r in out.items() if isinstance(r, dict) and 'dif_incremental' in r))
    (SAL / 'validacion.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(out, indent=1, ensure_ascii=False), flush=True)


def main():
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument('accion', choices=['planes', 'validar', 'puntuar', 'lanzar'])
    ap.add_argument('--etapa', default='diseno')
    ap.add_argument('--corrida', default='a')
    ap.add_argument('--parte', type=int, default=0)
    ap.add_argument('--partes', type=int, default=4)
    ap.add_argument('--hilos', type=int, default=4)
    a = ap.parse_args()
    if a.accion == 'planes':
        etapa_planes()
    elif a.accion == 'validar':
        etapa_validar(a.hilos)
    elif a.accion == 'puntuar':
        etapa_puntuar(a.etapa, a.corrida, a.parte, a.partes, a.hilos)
    else:
        etapa_lanzar(a.etapa, a.corrida, a.partes, a.hilos)


if __name__ == '__main__':
    main()
