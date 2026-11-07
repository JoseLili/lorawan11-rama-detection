"""Revisión 23: ataque coordinado (E1, E2, E3) y error fijo en ppb contra los detectores congelados.

    python rev23.py planes
    python rev23.py validar                       # criterio de la optimización a (2023) y exactitud de la c
    python rev23.py puntuar --corrida a --parte 0 --partes 4 [--hilos 4]
    python rev23.py lanzar --corrida a [--partes 4 --hilos 4]
    python rev23_metricas.py                      # después de las corridas a y b

Registro: docs/registro_previo_rev23_ataque_coordinado.md (precisiones y optimización al final).
No entrena ni elige ningún modelo. Salidas en results/linea_base/rev23/.
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
from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import lstm_local as ll  # noqa: E402

SAL = cm.RAIZ / 'results/linea_base/rev23'
PLANES0 = cm.RAIZ / 'results/anomalias_red_v1/planes'
PARAAD_DIR = cm.RAIZ / 'results/anomalias_red_v1/revision20/colab_20261028/recuperado/definitivo'
FIN = {2023: '2023-12-31 23:00', 2024: '2024-12-31 23:00', 2025: '2025-12-31 23:00', 2026: '2026-07-31 23:00'}  # 2023: sólo validar
PERIODO = {2024: 'prueba_2024', 2025: 'final_2025', 2026: 'final_2026'}
CALS = [f'{PERIODO[a]}_{i:02d}' for a in (2024, 2025, 2026) for i in range(1, 11)]   # k = 1…30
ESCENARIOS = ('E1', 'E2', 'E3')
TAM = {'E1': ('d100', 'd50', 'd20', 'a5', 'a10', 'a20', 'a40'),
       'E2': ('d100', 'd50', 'd20', 'a10', 'a20', 'a40'),
       'E3': ('d100', 'd50', 'd20', 'a10', 'a20', 'a40')}
DET = ('Ens-Vb-R', 'Ens-V0-R', 'L0unico', 'PARAAD', 'R3')
U_PARAAD = {0.01: 0.6405011077101032, 0.001: 0.8366300233950218}
LOTE = 8192
# Alarmas de R3 en el año limpio (revisión 18, «propias», sin ataque, entre 10 calendarios) con p99 y p99.9,
# y sus estación-días válidas: R3 tiene que reproducirlas para entrar «sin cambios».
R3_CONTROL = {2024: (119, 3, 8977), 2025: (82, 8, 8633), 2026: (57, 2, 4858)}


def anio_de(c: str) -> int:
    return int(c.split('_')[1])


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_texto(p: Path) -> str:
    """SHA-256 de un archivo de texto con finales de línea LF (como en git), igual en Windows y en Linux."""
    return hashlib.sha256(Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def umbrales_r3() -> dict:
    r = pd.read_csv(cm.RAIZ / 'results/anomalias_red_v1/revision18/resultados.csv')
    r = r[(r.dias == 'comunes') & (r.evaluacion == 'con ataque') & (r.detector == 'R3')].groupby('punto').umbral.first()
    return {0.01: float(r['p99']), 0.001: float(r['p99.9'])}


def umbrales_red() -> dict:
    """Umbrales registrados de la revisión 22 (2023 limpio) de Ens-Vb-R, Ens-V0-R y L0 único."""
    U = pd.read_csv(rc.SAL / 'umbrales_2023.csv')
    return {(r.detector, r.nivel): float(r.umbral) for r in U.itertuples()}


# ---------------------------------------------------------------- planes
def tramos(dias: list) -> list[list]:
    out = []
    for d in dias:
        if out and d - out[-1][-1] == pd.Timedelta(days=1):
            out[-1].append(d)
        else:
            out.append([d])
    return out


def derivar(plan: pd.DataFrame, esc: str, k: int, vecinas: dict, alterables: list) -> pd.DataFrame:
    """E1 tal cual; E2 con las vecinas de Vb alterables; E3 con el mismo número al azar (precisiones 4–6)."""
    base = plan.copy()
    base['papel'] = 'original'
    base['origen'] = base['episodio']
    if esc == 'E1':
        return base
    ocupado: dict[str, set] = {}
    for r in plan.itertuples():
        ocupado.setdefault(r.estacion, set()).update(pd.date_range(r.inicio.normalize(), r.fin.normalize()))
    nuevas = []
    for r in plan.sort_values('episodio').itertuples():
        vs = [t for t in vecinas[r.estacion] if t in alterables]
        if esc == 'E2':
            grupo = vs
        else:
            cand = sorted(set(alterables) - {r.estacion} - set(vecinas[r.estacion]))
            rng = np.random.default_rng([42, 23, k, int(r.episodio)])
            grupo = [str(t) for t in rng.choice(cand, size=len(vs), replace=False)]
        dias = pd.date_range(r.inicio.normalize(), r.fin.normalize())
        j = 0
        for t in grupo:
            libres = [d for d in dias if d not in ocupado.setdefault(t, set())]
            ocupado[t].update(libres)
            for tr in tramos(libres):
                j += 1
                nuevas.append(dict(corrida=r.corrida, episodio=1000 * int(r.episodio) + j, estacion=t, inicio=tr[0],
                                   fin=tr[-1] + pd.Timedelta(hours=23), dias_sorteados=int(r.dias_sorteados),
                                   dias=len(tr), signo=int(r.signo), p=float(r.p), papel='añadida',
                                   origen=int(r.episodio)))
    out = pd.concat([base, pd.DataFrame(nuevas)], ignore_index=True) if nuevas else base
    ar.validar_plan(out)
    return out


def ruta_plan(c: str, esc: str) -> Path:
    return SAL / 'planes' / f'plan_{c}_{esc}.csv'


def leer_plan(c: str, esc: str) -> pd.DataFrame:
    p = pd.read_csv(ruta_plan(c, esc), parse_dates=['inicio', 'fin'])
    ar.validar_plan(p)
    return p


def etapa_planes():
    d = SAL / 'planes'
    d.mkdir(parents=True, exist_ok=False)          # los planes se generan una sola vez
    vecinas = json.loads((rc.SAL / 'vecinas_vb.json').read_text())
    alterables = list(rc.objetivos())
    reg = {}
    for k, c in enumerate(CALS, start=1):
        orig = PLANES0 / f'plan_{c}.csv'
        plan = ar.leer_plan(orig)
        assert set(plan.estacion) <= set(alterables), c
        reg[orig.name] = dict(sha256=sha_texto(orig), episodios=len(plan), papel='original del banco')
        for esc in ESCENARIOS:
            p = derivar(plan, esc, k, vecinas, alterables)
            p.to_csv(ruta_plan(c, esc), index=False, lineterminator='\n', date_format='%Y-%m-%d %H:%M:%S')
            q = leer_plan(c, esc)
            assert len(q) == len(p)
            reg[ruta_plan(c, esc).name] = dict(sha256=sha_texto(ruta_plan(c, esc)), filas=len(p), k=k,
                                               anadidas=int((p.papel == 'añadida').sum()),
                                               estacion_dias=int(p.dias.sum()))
    (SAL / 'planes_sha256.json').write_text(json.dumps(reg, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    T = pd.DataFrame([dict(plan=k, **v) for k, v in reg.items() if 'k' in v])
    T['esc'] = T.plan.str.extract(r'_(E\d)\.csv')[0]
    print(T.groupby('esc')[['filas', 'anadidas', 'estacion_dias']].sum().to_string(), flush=True)


def verificar_planes():
    reg = json.loads((SAL / 'planes_sha256.json').read_text(encoding='utf8'))
    for nombre, r in reg.items():
        p = (PLANES0 if r.get('papel') == 'original del banco' else SAL / 'planes') / nombre
        assert sha_texto(p) == r['sha256'], f'plan modificado: {nombre}'


# ---------------------------------------------------------------- detectores
class Detectores:
    """Los 11 modelos neuronales fusionados por base (XLA), PARAAD y R3, con sus integridades verificadas."""

    def __init__(self, modo: str = 'tf'):
        """modo 'tf': tf.function por modelo con lotes fijos de 8 192 (idéntico bit a bit a `predict`);
        'xla': fusionados con XLA (no cumplió el criterio a, se conserva sólo para documentarlo); 'predict'."""
        import keras
        import tensorflow as tf
        self.tf = tf
        sha_def = json.loads((rc.SAL / 'modelos_definitivos_sha256.json').read_text())
        cargar = lambda p: keras.models.load_model(p, compile=False)  # noqa: E731
        mods = {}
        for v in ('Vb', 'V0'):
            for s in rc.SEMILLAS:
                nm = rc.nombre_modelo(v, 'R', s)
                p = rc.DEF / f'{nm}.keras'
                assert sha(p) == sha_def[nm], f'{nm}: SHA-256 distinto'
                mods[nm] = cargar(p)
        mods['L0unico'] = cargar(cm.SAL_RED / 'lstm_local_examen/c20/d50/modelo.keras')
        self.nombres = {'Vb': [rc.nombre_modelo('Vb', 'R', s) for s in rc.SEMILLAS],
                        'V0': [rc.nombre_modelo('V0', 'R', s) for s in rc.SEMILLAS] + ['L0unico']}
        self.modo = modo
        self.f = {}
        for g, nms in self.nombres.items():
            ms = [mods[n] for n in nms]
            if modo == 'xla':
                self.f[g] = tf.function(lambda a, ms=ms: tf.concat([m(a, training=False) for m in ms], axis=1),
                                        jit_compile=True)
            elif modo == 'tf':
                self.f[g] = [tf.function(lambda a, m=m: m(a, training=False)) for m in ms]
            else:
                self.f[g] = ms
        # PARAAD-SA congelado (revisión 20)
        from src.detect import paraad as pa
        self.pa = pa
        c = json.loads((PARAAD_DIR / 'congelado.json').read_text())
        lf = lambda p: hashlib.sha256(Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()  # noqa: E731
        assert sha(PARAAD_DIR / 'modelo_r1.keras') == c['sha256_modelo']
        assert lf(PARAAD_DIR / 'escala.csv') == c['sha256_escala']
        assert lf(cm.RAIZ / 'src/detect/paraad.py') == c['fuentes']['src/detect/paraad.py']
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.escala_pa = pd.read_csv(PARAAD_DIR / 'escala.csv', index_col='estacion', float_precision='round_trip')
        self.m_pa = cargar(PARAAD_DIR / 'modelo_r1.keras')
        # R3 (revisión 12, fase 2), como en evaluar_revision21.py
        import evaluar_estacion_dia as ee
        self.limpia_tr, _, self.sigma3, self.vec3 = ee.normalizacion_y_vecinas('mediana')

    def predecir(self, g: str, X: np.ndarray) -> np.ndarray:
        """(n, modelos) en float32, en lotes fijos de 8 192 (el último se rellena con ceros)."""
        n = len(X)
        out = np.empty((n, len(self.nombres[g])), np.float32)
        if self.modo == 'predict':
            for j, m in enumerate(self.f[g]):
                out[:, j] = m.predict(X, batch_size=LOTE, verbose=0)[:, 0]
            return out
        for i in range(0, n, LOTE):
            b = X[i:i + LOTE]
            k = len(b)
            if k < LOTE:
                b = np.concatenate([b, np.zeros((LOTE - k,) + b.shape[1:], b.dtype)])
            b = self.tf.constant(b)
            if self.modo == 'xla':
                out[i:i + k] = self.f[g](b).numpy()[:k]
            else:
                for j, f in enumerate(self.f[g]):
                    out[i:i + k, j] = f(b).numpy()[:k, 0]
        return out

    def paraad(self, xm: pd.DataFrame) -> pd.DataFrame:
        pa = self.pa
        x = xm[[f'{s}_valor' for s in pa.SENSORES]].set_axis(pa.SENSORES, axis=1)
        for s in pa.SENSORES:
            x[s] = x[s].where(xm[f'{s}_mascara'] == 1)
        z, m, dias = pa.bloques(x, self.escala_pa)
        return pa.puntajes(z, m, pa.reconstruir(self.m_pa, z), dias)

    def r3(self, historia: pd.DataFrame, xm: pd.DataFrame, obj) -> pd.DataFrame:
        x = ev.con_historia(historia, xm)
        col = ev.columnas_vecinas(x, self.sigma3, self.vec3).iloc[len(historia):]
        return ed.dominancia(ed.juntar_dia(col[list(obj)], 'promedio_dia'), self.vec3.vecinas)


class Anio:
    """Un año del banco con historia desde 2020 (precisión 1) y su puntaje limpio en caché."""

    def __init__(self, anio: int, ctx: dict, esc: dict, det: Detectores, incremental: bool = True):
        self.anio, self.ctx, self.esc, self.det, self.incremental = anio, ctx, esc, det, incremental
        self.cols = rc.columnas()
        self.obj = list(ctx['objetivos'])
        ini = pd.Timestamp(f'{anio}-01-01')
        v = rc.valores('2020-01-01', FIN[anio])
        self.vy = v.loc[ini:]
        self.xh = ar.matriz_red(v.loc[:ini - pd.Timedelta(hours=1)], self.cols)
        x = ar.matriz_red(v, self.cols)
        self.n = len(x)
        self.pos = np.flatnonzero(x.index >= ini)
        self.ix = x.index[self.pos]
        self.con = x.iloc[self.pos][[f'{s}_mascara' for s in self.obj]].to_numpy() == 1
        self.loc_idx = {s: ll.indices_locales(ctx['estaciones'], ctx['vecinas'], s) for s in self.obj}
        self.F0 = self.entradas(x)
        self.P0 = {g: self.horarios(g, self.F0[g], None) for g in ('Vb', 'V0')}
        h3 = det.limpia_tr
        for a in range(2023, anio):
            h3 = ev.con_historia(h3, ar.matriz_red(v.loc[f'{a}-01-01':f'{a}-12-31 23:00'], self.cols))
        self.h3 = h3
        self.limpio = self.diarios(self.F0, ar.matriz_red(self.vy, self.cols), self.P0)
        al = [int((self.limpio['R3'] > u).sum()) for u in umbrales_r3().values()]
        if anio in R3_CONTROL:
            assert (al[0], al[1], int((~np.isnan(self.limpio['R3'])).sum())) == R3_CONTROL[anio], \
                f'R3 no reproduce la revisión 18 en {anio}: {al}'

    def entradas(self, x: pd.DataFrame) -> dict:
        b = cm.bases(self.ctx, x)
        return {g: lb.entradas(x, b[g], self.ctx['estaciones'], self.ctx['sigma'], self.esc[g], self.ctx['vec'])
                for g in ('Vb', 'V0')}

    def cambio(self, g: str, F: np.ndarray, s: str) -> np.ndarray:
        """Posiciones del año cuya ventana (filas t − 23 … t de las 17 columnas de s) cambia respecto al limpio."""
        a0 = self.pos[0] - 23
        il = self.loc_idx[s]
        dif = (F[a0:, il] != self.F0[g][a0:, il]).any(axis=1)
        c = np.concatenate([[0], np.cumsum(dif)])
        q = self.pos - a0
        return (c[q + 1] - c[q - 23]) > 0

    def horarios(self, g: str, F: np.ndarray, previo) -> tuple[np.ndarray, int]:
        """(estaciones, horas, modelos) con NaN donde no hay dato; incremental si hay `previo` (limpio)."""
        S, H, M = len(self.obj), len(self.pos), len(self.det.nombres[g])
        P = np.full((S, H, M), np.nan, np.float32) if previo is None else previo[0].copy()
        Xs, sel_ = [], []
        for j, s in enumerate(self.obj):
            sel = self.con[:, j].copy()
            if previo is not None and self.incremental:
                sel &= self.cambio(g, F, s)
            if sel.any():
                Xs.append(ll.ventanas_locales(F, self.ctx['estaciones'], self.ctx['vecinas'], s, self.pos[sel]))
                sel_.append((j, np.flatnonzero(sel)))
        n = 0
        if Xs:
            Y = self.det.predecir(g, np.concatenate(Xs))
            for j, h in sel_:
                P[j, h] = Y[n:n + len(h)]
                n += len(h)
        return P, n

    def diarios(self, F: dict, xm: pd.DataFrame, P: dict) -> dict:
        out = {}
        con = self.con
        # como en la calibración de 2023 (rev22.etapa_calibracion): puntaje diario por modelo y luego el promedio
        por_modelo = {}
        for g in ('Vb', 'V0'):
            for m, nm in enumerate(self.det.nombres[g]):
                h = P[g][0][:, :, m].astype(np.float64).T
                dd = ed.juntar_dia(pd.DataFrame(h, index=self.ix, columns=self.obj).where(con), 'promedio_dia')
                por_modelo[nm] = dd.to_numpy()
                self.dias = dd.index
        out['Ens-Vb-R'] = np.mean([por_modelo[n] for n in self.det.nombres['Vb']], axis=0)
        out['Ens-V0-R'] = np.mean([por_modelo[n] for n in self.det.nombres['V0'][:5]], axis=0)
        out['L0unico'] = por_modelo['L0unico']
        pa = self.det.paraad(xm)
        out['PARAAD'] = pa.reindex(self.dias)[self.obj].to_numpy()
        out['R3'] = self.det.r3(self.h3, xm, self.obj).reindex(self.dias)[self.obj].to_numpy()
        return out

    def alterada(self, plan: pd.DataFrame, tam: str) -> tuple[dict, dict]:
        if tam[0] == 'd':
            rec, cam = ar.aplicar(self.vy, plan, int(tam[1:]) / 100)
        else:
            rec, cam = ar.aplicar_fijo(self.vy, plan, int(tam[1:]))
        xm = ar.matriz_red(rec, self.cols, cam)
        x = pd.concat([self.xh, xm])
        assert len(x) == self.n
        F = self.entradas(x)
        P = {g: self.horarios(g, F[g], self.P0[g]) for g in ('Vb', 'V0')}
        S = self.diarios(F, xm, P)
        # cambio real: horas de episodio con dato
        ep = pd.DataFrame(False, index=self.vy.index, columns=self.vy.columns)
        for e in plan.itertuples():
            ep.loc[e.inicio:e.fin, e.estacion] = True
        ok = ep.to_numpy() & self.vy.notna().to_numpy()
        dif = np.abs(rec.to_numpy() - self.vy.to_numpy())[ok]
        info = dict(horas_episodio=int(ok.sum()), cambio_medio_ppb=float(dif.mean()) if len(dif) else np.nan,
                    frac_cambiadas=float((dif > 0).mean()) if len(dif) else np.nan,
                    ventanas_Vb=P['Vb'][1], ventanas_V0=P['V0'][1])
        return S, info


# ---------------------------------------------------------------- tareas
def tareas() -> list[tuple]:
    out = [('limpia', a, None, None) for a in (2024, 2025, 2026)]
    for c in CALS:
        for esc in ESCENARIOS:
            for t in TAM[esc]:
                out.append((c, anio_de(c), esc, t))
    return sorted(out, key=lambda r: (r[1], r[0] != 'limpia', r[0], r[2] or '', r[3] or ''))


def nombre_tarea(t) -> str:
    return f'limpia_{t[1]}' if t[0] == 'limpia' else f'{t[0]}_{t[2]}_{t[3]}'


def guardar(path: Path, **arr):
    tmp = path.with_suffix('.tmp.npz')
    np.savez_compressed(tmp, **arr)
    os.replace(tmp, path)


def etapa_puntuar(corrida: str, parte: int, partes: int, hilos: int):
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(hilos)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    verificar_planes()
    sal = SAL / f'corrida_{corrida}'
    sal.mkdir(parents=True, exist_ok=True)
    T = tareas()
    mias = [T[i] for i in range(len(T)) if i * partes // len(T) == parte]
    det = Detectores()
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    actual, t0 = None, time.time()
    for n, t in enumerate(mias, start=1):
        p = sal / f'{nombre_tarea(t)}.npz'
        if p.exists():
            continue
        if actual is None or actual.anio != t[1]:
            actual = None
            actual = Anio(t[1], ctx, esc, det)
        if t[0] == 'limpia':
            S, info = actual.limpio, {}
        else:
            S, info = actual.alterada(leer_plan(t[0], t[2]), t[3])
        guardar(p, dias=actual.dias.values.astype('datetime64[ns]'), **{k: S[k] for k in DET},
                info=np.array(json.dumps(info)))
        print(f'{time.strftime("%H:%M:%S")} parte {parte}: {n}/{len(mias)} {nombre_tarea(t)} '
              f'({(time.time() - t0) / n:.1f} s/tarea) {info}', flush=True)
    print(f'parte {parte} lista en {time.time() - t0:.0f} s', flush=True)


def etapa_lanzar(corrida: str, partes: int, hilos: int):
    logs = SAL / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS=str(hilos), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', TF_CPP_MIN_LOG_LEVEL='2')
    ps = []
    for i in range(partes):
        f = open(logs / f'corrida_{corrida}_parte{i}.log', 'w', encoding='utf8')
        ps.append((subprocess.Popen([sys.executable, str(AQUI / 'rev23.py'), 'puntuar', '--corrida', corrida,
                                     '--parte', str(i), '--partes', str(partes), '--hilos', str(hilos)],
                                    cwd=AQUI, stdout=f, stderr=subprocess.STDOUT, env=env), f))
    t0 = time.time()
    for p, f in ps:
        p.wait()
        f.close()
    cod = [p.returncode for p, _ in ps]
    print(f'corrida {corrida}: códigos {cod} en {time.time() - t0:.0f} s', flush=True)
    if any(cod):
        raise SystemExit(1)


def etapa_validar(hilos: int):
    """Optimización a: 2023 frente a la revisión 22 (y R3/PARAAD frente a la revisión 20). Optimización c: exactitud."""
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(hilos)
    tf.config.threading.set_inter_op_parallelism_threads(2)
    verificar_planes()
    det = Detectores()
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    t0 = time.time()
    A = Anio(2023, ctx, esc, det)
    cal = np.load(rc.SAL / 'calibracion_2023.npz')
    assert pd.DatetimeIndex(cal['dias']).equals(A.dias)
    U = umbrales_red()
    out = dict(segundos_2023=round(time.time() - t0, 1))
    ok = True
    for d in ('Ens-Vb-R', 'Ens-V0-R', 'L0unico'):
        a, b, com = A.limpio[d], cal[d], cal['comun']
        mismo_nan = bool((np.isnan(a) == np.isnan(b)).all())
        dmax = float(np.nanmax(np.abs(a - b)))
        alarmas = {str(nv): [int((b[com] > U[(d, nv)]).sum()), int((a[com] > U[(d, nv)]).sum()),
                             bool(((a[com] > U[(d, nv)]) == (b[com] > U[(d, nv)])).all())] for nv in (0.01, 0.001)}
        cumple = mismo_nan and dmax == 0.0 and all(v[2] for v in alarmas.values())
        ok &= cumple
        out[d] = dict(mismo_nan=mismo_nan, dif_max=dmax, alarmas_registro_aqui_identicas=alarmas, cumple=cumple)
    r3 = pd.read_csv(cm.RAIZ / 'results/anomalias_red_v1/revision20/comunes_2023/puntajes_R3.csv',
                     parse_dates=['dia']).set_index('dia').reindex(A.dias)[A.obj].to_numpy()
    out['R3_dif_max_rev20'] = float(np.nanmax(np.abs(A.limpio['R3'] - r3)))
    pp = pd.read_csv(cm.RAIZ / 'results/anomalias_red_v1/revision20/calibracion_2023/puntajes.csv',
                     parse_dates=['dia']).set_index('dia').reindex(A.dias)[A.obj].to_numpy()
    out['PARAAD_dif_max_rev20'] = float(np.nanmax(np.abs(A.limpio['PARAAD'] - pp)))
    out['criterio_a_cumple'] = bool(ok)
    # optimización c: incremental contra completo, en dos matrices
    exact = []
    for c, e, t in (('final_2025_01', 'E2', 'd50'), ('final_2025_04', 'E1', 'a20')):
        B = Anio(2025, ctx, esc, det)
        S1, i1 = B.alterada(leer_plan(c, e), t)
        B.incremental = False
        S2, i2 = B.alterada(leer_plan(c, e), t)
        dif = {d: float(np.nanmax(np.abs(S1[d] - S2[d]))) for d in DET}
        exact.append(dict(matriz=f'{c}_{e}_{t}', dif=dif, ventanas_incremental=[i1['ventanas_Vb'], i1['ventanas_V0']],
                          ventanas_completo=[i2['ventanas_Vb'], i2['ventanas_V0']],
                          mismo_nan=all(bool((np.isnan(S1[d]) == np.isnan(S2[d])).all()) for d in DET)))
    out['criterio_c'] = exact
    out['criterio_c_cumple'] = all(max(x['dif'].values()) == 0.0 and x['mismo_nan'] for x in exact)
    out['modo'] = det.modo
    (SAL / 'validacion_optimizacion.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(out, indent=1, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('etapa', choices=['planes', 'validar', 'puntuar', 'lanzar'])
    ap.add_argument('--corrida', default='a')
    ap.add_argument('--parte', type=int, default=0)
    ap.add_argument('--partes', type=int, default=4)
    ap.add_argument('--hilos', type=int, default=4)
    a = ap.parse_args()
    if a.etapa == 'planes':
        etapa_planes()
    elif a.etapa == 'validar':
        etapa_validar(a.hilos)
    elif a.etapa == 'puntuar':
        etapa_puntuar(a.corrida, a.parte, a.partes, a.hilos)
    else:
        etapa_lanzar(a.corrida, a.partes, a.hilos)


if __name__ == '__main__':
    main()
