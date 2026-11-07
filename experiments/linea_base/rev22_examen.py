"""Revisión 22: examen de despliegue, del 2026-08-01 al 2026-09-30 (uso único).

    python rev22_examen.py planes | puntuar --corrida a|b | metricas

Historia: enero–julio de 2026 del zip validado. Ventana: SINAICA, datos crudos (addendum §8 del registro).
Umbrales: 2023 limpio (`umbrales_2023.csv`, `calibracion_2023.npz`).
"""
from __future__ import annotations

import argparse
import gc
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun as cm  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rev22_comun as rc  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect import linea_base as lb  # noqa: E402
from src.detect import multianual as mu  # noqa: E402

EX = rc.SAL / 'examen_despliegue'
INI, FIN = '2026-08-01', '2026-09-30'
N_CAL, NUM0 = 10, 800
DELTAS = (100, 50, 20, 10, 5)
DFBAR = (100, 50, 20)
DET = ('Ens-V0-R', 'Ens-Vb-R', 'Ens-Vb-M1', 'L0unico')
CANDIDATOS = ('Ens-Vb-R', 'Ens-Vb-M1')
NIVELES = (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)
SINAICA = cm.RAIZ / 'data/raw/sinaica'


def sinaica() -> pd.DataFrame:
    """Agosto–septiembre de SINAICA (SHA-256 verificado), en ppb enteros y con la hora de la RAMA (−1 h)."""
    ck = {l.split()[1]: l.split()[0] for l in (cm.RAIZ / 'docs/checksums_sinaica_2026.txt').read_text().splitlines()
          if l and not l.startswith('#')}
    filas = []
    for nombre, h in ck.items():
        b = (SINAICA / nombre).read_bytes()
        assert rc.sha(b) == h, f'{nombre}: SHA-256 distinto'
        est = nombre.split('_')[0]
        m = re.search(r'var\s+dat\s*=\s*(\[.*?\]);', b.decode('utf8', 'replace'), re.S)
        for x in json.loads(m.group(1)) if m else []:
            filas.append((est, x['fecha'], int(x['hora']), float(x['valor'])))
    L = pd.DataFrame(filas, columns=['station', 'fecha', 'hora', 'valor']).drop_duplicates(['station', 'fecha', 'hora'])
    L['timestamp'] = pd.to_datetime(L.fecha) + pd.to_timedelta(L.hora - 1, 'h')
    W = L.pivot(index='timestamp', columns='station', values='valor').mul(1000).round()
    rej = pd.date_range(INI, f'{FIN} 23:00', freq='h', name='timestamp')
    W = W.reindex(index=rej, columns=mu.ESTACIONES)
    W.columns.name = 'station'
    return W


def valores() -> pd.DataFrame:
    v = pd.concat([rc.valores('2026-01-01', '2026-07-31 23:00'), sinaica()])
    assert v.index.is_unique and (v.index == pd.date_range('2026-01-01', f'{FIN} 23:00', freq='h')).all()
    return v


def etapa_planes():
    d = EX / 'planes'
    d.mkdir(parents=True, exist_ok=True)
    reg = {}
    for k in range(1, N_CAL + 1):
        p = float(np.random.default_rng(ar.clave(ar.SEMILLA, INI, NUM0 + k, ar.USO_TASA)).uniform(*ar.P_RANGO))
        plan = ar.plan_episodios(INI, FIN, p, rc.objetivos(), corrida=f'despliegue_2026_{k:02d}', numero=NUM0 + k)
        ar.validar_plan(plan)
        path = ar.guardar_plan(plan, d)
        reg[path.name] = dict(sha256=rc.sha(path.read_bytes()), p=p, episodios=len(plan))
    (EX / 'planes_sha256.json').write_text(json.dumps(reg, indent=2))
    print(f'{len(reg)} planes; episodios: {[r["episodios"] for r in reg.values()]}', flush=True)


def plan(k):
    return ar.leer_plan(EX / f'planes/plan_despliegue_2026_{k:02d}.csv')


def modelos():
    import keras
    sha = json.loads((rc.SAL / 'modelos_definitivos_sha256.json').read_text())
    out = {}
    for nm, h in sha.items():
        p = rc.DEF / f'{nm}.keras'
        assert rc.sha(p.read_bytes()) == h, f'{nm}: SHA-256 distinto'
        out[nm] = (nm.split('_')[0], keras.models.load_model(p, compile=False))
    out['L0unico'] = ('V0', keras.models.load_model(cm.SAL_RED / 'lstm_local_examen/c20/d50/modelo.keras', compile=False))
    return out


def puntuar(ctx, mods, esc, x, pos):
    """Probabilidad horaria y puntaje diario de los ensambles y de L0 único."""
    b = cm.bases(ctx, x)
    F = {v: lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec']) for v in rc.BASES}
    obj = ctx['objetivos']
    ix = x.index[pos]
    con = x.loc[ix, [f'{s}_mascara' for s in obj]].to_numpy() == 1
    Xw = {v: np.concatenate([cm.ventanas(ctx, F[v], s, pos) for s in obj]) for v in rc.BASES}
    H = {}
    for nm, (v, mdl) in mods.items():
        H[nm] = mdl.predict(Xw[v], batch_size=8192, verbose=0).astype(np.float64).reshape(len(obj), len(pos)).T
    hor = {'L0unico': H['L0unico']}
    for c in ('V0_R', 'Vb_R', 'Vb_M1'):
        hor['Ens-' + c.replace('_', '-')] = np.mean([H[f'{c}_s{s}'] for s in rc.SEMILLAS], axis=0)
    dia = {}
    for nm, h in hor.items():
        dd = ed.juntar_dia(pd.DataFrame(h, index=ix, columns=obj).where(con), 'promedio_dia')
        dia[nm], dias = dd.to_numpy(), dd.index
    hor = {nm: np.where(con, h, np.nan).astype(np.float32) for nm, h in hor.items()}
    return dia, hor, dias


def etapa_puntuar(corrida):
    for k, r in json.loads((EX / 'planes_sha256.json').read_text()).items():
        assert rc.sha((EX / 'planes' / k).read_bytes()) == r['sha256'], f'plan modificado: {k}'
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    mods = modelos()
    v = valores()
    cols = rc.columnas()
    limpia = ar.matriz_red(v, cols)
    pos = np.flatnonzero(limpia.index >= pd.Timestamp(INI))
    vw = v.loc[INI:]
    hist = limpia.loc[:'2026-07-31 23:00']
    D, Hh = {}, {}
    dia, hor, dias = puntuar(ctx, mods, esc, limpia, pos)
    for nm in dia:
        D[f'{nm}__limpia'], Hh[f'{nm}__limpia'] = dia[nm], hor[nm]
    for k in range(1, N_CAL + 1):
        for d in DELTAS:
            rec, cam = ar.aplicar(vw, plan(k), d / 100)
            xa = pd.concat([hist, ar.matriz_red(rec, cols, cam)])
            assert xa.index.equals(limpia.index)
            dia, hor, _ = puntuar(ctx, mods, esc, xa, pos)
            for nm in dia:
                D[f'{nm}__c{k:02d}_d{d}'], Hh[f'{nm}__c{k:02d}_d{d}'] = dia[nm], hor[nm]
        print(f'corrida {corrida}: calendario {k:02d} listo', flush=True)
        gc.collect()
    sal = EX / f'corrida_{corrida}'
    sal.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(sal / 'diario.npz', dias=dias.values.astype('datetime64[ns]'), **D)
    np.savez_compressed(sal / 'horario.npz', horas=limpia.index[pos].values.astype('datetime64[ns]'), **Hh)
    cob = pd.DataFrame({'cobertura': v.loc[INI:, ctx['objetivos']].notna().mean()})
    cob.to_csv(EX / 'cobertura_ventana.csv', lineterminator='\n')
    print(f'corrida {corrida} lista', flush=True)


def etiquetas(dias, obj):
    out = {}
    for k in range(1, N_CAL + 1):
        y = pd.DataFrame(False, index=dias, columns=obj)
        dia_ep = pd.DataFrame(0, index=dias, columns=obj)
        for e in plan(k).itertuples():
            if e.estacion in obj:
                for j, dd in enumerate(pd.date_range(e.inicio.normalize(), e.fin.normalize())):
                    if dd in y.index:
                        y.loc[dd, e.estacion] = True
                        dia_ep.loc[dd, e.estacion] = j + 1
        out[k] = dict(y=y.to_numpy(), dia=dia_ep.to_numpy(), plan=plan(k))
    return out


def etapa_metricas():
    a, b = np.load(EX / 'corrida_a/diario.npz'), np.load(EX / 'corrida_b/diario.npz')
    dif = max(float(np.nanmax(np.abs(a[k] - b[k]))) for k in a.files if k != 'dias')
    Z = {k: a[k] for k in a.files if k != 'dias'}
    dias = pd.DatetimeIndex(a['dias'])
    obj = rc.objetivos()
    cal = np.load(rc.SAL / 'calibracion_2023.npz')
    U = {(dt, nv): float(ev.umbral_falsas_alarmas(cal[dt][cal['comun']], nv)) for dt in DET for nv in NIVELES}
    ref = pd.read_csv(rc.SAL / 'umbrales_2023.csv')
    for r in ref.itertuples():                       # los umbrales registrados se reproducen
        assert abs(U[(r.detector, r.nivel)] - r.umbral) < 1e-12
    lab = etiquetas(dias, obj)
    mats = ['limpia'] + [f'c{k:02d}_d{d}' for k in range(1, N_CAL + 1) for d in DELTAS]
    comun = {m: np.logical_and.reduce([~np.isnan(Z[f'{dt}__{m}']) for dt in DET]) for m in mats}
    cl = comun['limpia']
    mes = dias.month.to_numpy()
    meses = sorted(set(mes))
    filas, bloques = [], {}
    for dt in DET:
        for nv in NIVELES:
            u = U[(dt, nv)]
            al = Z[f'{dt}__limpia'] > u
            r = dict(detector=dt, nivel=nv, umbral=u, fa_limpia=float(al[cl].mean()), dias_limpios=int(cl.sum()),
                     alarmas_limpias=int(al[cl].sum()))
            for d in DELTAS:
                tp = fp = fn = 0
                Cb = np.zeros((3, len(obj), len(meses)))
                for k in range(1, N_CAL + 1):
                    m = f'c{k:02d}_d{d}'
                    s, y, msk = Z[f'{dt}__{m}'] > u, lab[k]['y'], comun[m] & cl
                    tp += (s & y & msk).sum(); fp += (s & ~y & msk).sum(); fn += (~s & y & msk).sum()
                    for q, xx in enumerate((s & y & msk, s & ~y & msk, ~s & y & msk)):
                        for i, mo in enumerate(meses):
                            Cb[q, :, i] += xx[mes == mo].sum(0)
                P = tp / max(tp + fp, 1)
                R = tp / max(tp + fn, 1)
                r.update({f'tp_{d}': int(tp), f'fp_{d}': int(fp), f'fn_{d}': int(fn), f'precision_{d}': P, f'recall_{d}': R,
                          f'F1_{d}': 2 * P * R / (P + R) if P + R else 0.0})
                bloques[(dt, nv, d)] = Cb.reshape(3, -1)
            r['Fbar'] = float(np.mean([r[f'F1_{d}'] for d in DFBAR]))
            filas.append(r)
    T = pd.DataFrame(filas)
    T.to_csv(EX / 'curva_operacion.csv', index=False, lineterminator='\n')
    # prueba registrada: p99, IC 97.5 % (Bonferroni, dos candidatos); p99.9 descriptivo
    rng = np.random.default_rng([42, 22, 1])
    nb = len(obj) * len(meses)
    Wb = np.stack([np.bincount(rng.integers(0, nb, nb), minlength=nb) for _ in range(2000)], axis=1).astype(float)

    def fbar(dt, nv, w):
        f = []
        for d in DFBAR:
            t = bloques[(dt, nv, d)] @ w
            P = t[0] / np.maximum(t[0] + t[1], 1e-12)
            R = t[0] / np.maximum(t[0] + t[2], 1e-12)
            f.append(np.where(P + R > 0, 2 * P * R / np.maximum(P + R, 1e-12), 0))
        return np.mean(f, axis=0)

    uno = np.ones((nb, 1))
    pruebas = []
    for c in CANDIDATOS:
        for nv in (0.01, 0.001):
            d0 = float((fbar(c, nv, uno) - fbar('Ens-V0-R', nv, uno))[0])
            db = fbar(c, nv, Wb) - fbar('Ens-V0-R', nv, Wb)
            lo, hi = np.percentile(db, [1.25, 98.75])
            pruebas.append(dict(candidato=c, nivel=nv, papel='prueba' if nv == 0.01 else 'descriptivo', dFbar=d0,
                                ic975_inf=float(lo), ic975_sup=float(hi),
                                adopta=bool(nv == 0.01 and d0 >= 0.02 and lo > 0)))
    Pr = pd.DataFrame(pruebas)
    Pr.to_csv(EX / 'pruebas.csv', index=False, lineterminator='\n')
    # vista de despliegue: mes a mes y día de la primera alerta (p99)
    vista = []
    for dt in DET:
        u = U[(dt, 0.01)]
        for i, mo in enumerate(meses):
            mm = (mes == mo)[:, None] & cl
            r = dict(detector=dt, mes=int(mo), fa_limpia=float((Z[f'{dt}__limpia'] > u)[mm].mean()))
            for d in (100, 50):
                Cb = bloques[(dt, 0.01, d)].reshape(3, len(obj), len(meses))[:, :, i].sum(1)
                r[f'recall_{d}'] = float(Cb[0] / max(Cb[0] + Cb[2], 1))
            vista.append(r)
    pd.DataFrame(vista).to_csv(EX / 'vista_mensual.csv', index=False, lineterminator='\n')
    prim = []
    for dt in DET:
        u = U[(dt, 0.01)]
        for d in (100, 50, 20):
            for k in range(1, N_CAL + 1):
                m = f'c{k:02d}_d{d}'
                s = Z[f'{dt}__{m}'] > u
                for e in lab[k]['plan'].itertuples():
                    if e.estacion not in obj:
                        continue
                    j = obj.index(e.estacion)
                    rng_d = (dias >= e.inicio.normalize()) & (dias <= e.fin.normalize())
                    ok = rng_d & comun[m][:, j] & cl[:, j]
                    if not ok.any():
                        continue
                    hit = np.flatnonzero(ok & s[:, j])
                    prim.append(dict(detector=dt, delta=d, calendario=k, estacion=e.estacion, dias_evaluables=int(ok.sum()),
                                     detectado=bool(len(hit)),
                                     dia_primera_alerta=int((dias[hit[0]] - e.inicio.normalize()).days + 1) if len(hit) else None))
    pd.DataFrame(prim).to_csv(EX / 'primera_alerta.csv', index=False, lineterminator='\n')
    dec = dict(corridas_identicas=dif == 0.0, diferencia_max=dif, ventana=[INI, FIN],
               adopciones={r.candidato: r.adopta for r in Pr.itertuples() if r.papel == 'prueba'})
    (EX / 'decision.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False))
    show = T[T.nivel.isin([0.01, 0.001])][['detector', 'nivel', 'fa_limpia', 'Fbar', 'F1_100', 'F1_50', 'F1_20', 'F1_10',
                                          'recall_100', 'precision_100', 'recall_50', 'precision_50']]
    print(show.round(3).to_string(index=False))
    print(Pr.round(4).to_string(index=False))
    print(json.dumps(dec, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('etapa')
    ap.add_argument('--corrida', default='a')
    a = ap.parse_args()
    {'planes': etapa_planes, 'metricas': etapa_metricas}.get(a.etapa, lambda: etapa_puntuar(a.corrida))()


if __name__ == '__main__':
    main()
