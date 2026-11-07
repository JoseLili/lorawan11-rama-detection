"""Revisión 22 (elección en 2022): Vb y más años de fondo (M1, M2). Coordinador por etapas.

    python rev22.py auditoria | planes | ventanas | entrenar | puntuar | seleccion | definitivos | calibracion | todo
    [--paralelo 4] [--hilos 4]

Los entrenamientos y el puntaje corren como procesos separados, hasta `--paralelo` a la vez.
Registro previo: docs/registro_previo_rev22_mas_anios.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import comun as cm
import numpy as np
import pandas as pd
import rev22_comun as rc

from src.detect import anomalias_red as ar
from src.detect import multianual as mu

AQUI = Path(__file__).resolve().parent
NIVELES = (0.01, 0.001)


def lanzar(trabajos: list[tuple[str, list[str]]], paralelo: int) -> list[str]:
    """Corre (nombre, argv) con hasta `paralelo` procesos; log en results/.../logs/<nombre>.log."""
    logs = rc.SAL / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    pend, activos, fallos = list(trabajos), {}, []
    while pend or activos:
        while pend and len(activos) < paralelo:
            nombre, argv = pend.pop(0)
            f = open(logs / f'{nombre}.log', 'w', encoding='utf8')
            activos[nombre] = (subprocess.Popen([sys.executable, *argv], cwd=AQUI, stdout=f, stderr=subprocess.STDOUT,
                                                env=os.environ.copy()), f, time.time())
        time.sleep(5)
        for nombre in list(activos):
            p, f, t = activos[nombre]
            if p.poll() is not None:
                f.close()
                estado = 'ok' if p.returncode == 0 else f'ERROR {p.returncode}'
                if p.returncode:
                    fallos.append(nombre)
                print(f'{time.strftime("%H:%M:%S")} {nombre}: {estado} en {time.time() - t:.0f} s', flush=True)
                del activos[nombre]
    return fallos


def etapa_auditoria():
    obj = rc.objetivos()
    largo, _ = mu.cargar_o3_zips(cm.RAIZ / 'data/raw', rc.checksums(), anios=range(2000, 2020))
    largo = largo[largo.station.isin(mu.ESTACIONES)]
    filas, eleg = [], {}
    for y in range(2000, 2020):
        rej = pd.date_range(f'{y}-01-01', f'{y}-12-31 23:00', freq='h')
        ly = largo[(largo.timestamp >= rej[0]) & (largo.timestamp <= rej[-1])]
        v = ly.pivot(index='timestamp', columns='station', values='value').reindex(index=rej, columns=mu.ESTACIONES)
        cov = v[obj].notna().mean()
        ok = [s for s in obj if cov[s] >= rc.COBERTURA_MIN]
        filas.append(dict(anio=y, horas=len(rej), objetivos_elegibles=len(ok), anio_elegible=len(ok) >= rc.OBJ_MIN,
                          **{s: round(float(c), 3) for s, c in cov.items()}))
        if len(ok) >= rc.OBJ_MIN:
            eleg[y] = ok
    rc.SAL.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(rc.SAL / 'auditoria_cobertura.csv', index=False, lineterminator='\n')
    (rc.SAL / 'elegibles.json').write_text(json.dumps(eleg, indent=1))
    print('años elegibles:', {y: len(o) for y, o in eleg.items()}, flush=True)


def etapa_planes():
    d = rc.SAL / 'planes'
    d.mkdir(parents=True, exist_ok=True)
    reg = {}
    for y in rc.elegibles():
        for k in range(1, rc.N_FONDO + 1):
            plan = ar.plan_episodios(f'{y}-01-01', f'{y}-12-31', ar.P_BASE, rc.objetivos(),
                                     corrida=f'fondo_{y}_{k:02d}', numero=rc.NUM0 + k)
            ar.validar_plan(plan)
            path = ar.guardar_plan(plan, d)
            reg[path.name] = dict(sha256=rc.sha(path.read_bytes()), p=ar.P_BASE, episodios=len(plan))
    (rc.SAL / 'planes_sha256.json').write_text(json.dumps(reg, indent=2))
    print(f'{len(reg)} planes de fondo guardados', flush=True)


def etapa_ventanas(a):
    g = rc.grupos()
    todos = g['fondo'] + g['rec'] + g['val']
    falta = [x for x in todos if not (rc.VEN / f'{x}.json').exists()]
    return lanzar([(f'ventanas_{x}', ['rev22_ventanas.py', x]) for x in falta], a.paralelo)


def etapa_entrenar(a):
    orden = {'M1': 0, 'M2': 1, 'R': 2}            # los más largos primero
    trab = []
    for c in sorted(rc.CELDAS, key=orden.get):
        for s in rc.SEMILLAS:
            for v in rc.BASES:
                nm = rc.nombre_modelo(v, c, s)
                if not (rc.MOD / f'config_{nm}.json').exists():
                    trab.append((f'entrenar_{nm}', ['rev22_entrenar.py', v, c, str(s), '--hilos', str(a.hilos)]))
    return lanzar(trab, a.paralelo)


def etapa_puntuar(a):
    nombres = cm.nombres_eval()
    trab = []
    for v in rc.BASES:
        for i in range(2):
            ks = [k for k in nombres[i::2] if not (rc.PUN / f'{v}__{k}.npz').exists()]
            if ks:
                trab.append((f'puntuar_{v}_{i}', ['rev22_puntuar.py', v, ','.join(ks), '--hilos', str(a.hilos)]))
    return lanzar(trab, a.paralelo)


def cargar_puntajes():
    S, dias = {}, None
    for v in rc.BASES:
        for k in cm.nombres_eval():
            z = np.load(rc.PUN / f'{v}__{k}.npz')
            dias = pd.DatetimeIndex(z['dias'])
            for nm in z.files:
                if nm != 'dias':
                    S[(nm, k)] = z[nm]
    return dias, S


def etapa_seleccion():
    cm.SEMILLA_BOOT = [42, 22, 0]
    ctx = cm.contexto()
    dias, S = cargar_puntajes()
    nombres = cm.nombres_eval()
    celdas = [(v, c) for v in rc.BASES for c in rc.CELDAS]
    for v, c in celdas:
        for k in nombres:
            S[(f'Ens-{v}-{c}', k)] = np.mean([S[(rc.nombre_modelo(v, c, s), k)] for s in rc.SEMILLAS], axis=0)
    lab = cm.etiquetas(ctx, dias)
    indiv = [rc.nombre_modelo(v, c, s) for v, c in celdas for s in rc.SEMILLAS]
    ens = [f'Ens-{v}-{c}' for v, c in celdas]
    todos = indiv + ens
    met = pd.concat([cm.metricas(S, todos, lab, nv) for nv in NIVELES], ignore_index=True)
    met.to_csv(rc.SAL / 'metricas_2022.csv', index=False, lineterminator='\n')
    ref = 'Ens-V0-R'
    filas = []
    for v, c in celdas:
        if (v, c) == ('V0', 'R'):
            continue
        for nv in NIVELES:
            m = met[met.nivel == nv].set_index('modelo')
            d = m.loc[f'Ens-{v}-{c}', 'Fbar'] - m.loc[ref, 'Fbar']
            gana = sum(m.loc[rc.nombre_modelo(v, c, s), 'Fbar'] > m.loc[rc.nombre_modelo('V0', 'R', s), 'Fbar']
                       for s in rc.SEMILLAS)
            r = cm.bootstrap_dfbar(S, dias, f'Ens-{v}-{c}', ref, todos, lab, nv)
            filas.append(dict(celda=f'{v}-{c}', nivel=nv, dFbar=d, semillas_ganadas=int(gana), ic_inf=r[1], ic_sup=r[2],
                              cumple=bool(d >= 0.02 and gana >= 4)))
    P = pd.DataFrame(filas)
    P.to_csv(rc.SAL / 'pruebas_seleccion_2022.csv', index=False, lineterminator='\n')
    avanzan = P.groupby('celda').cumple.any()
    p99 = P[P.nivel == 0.01].set_index('celda').dFbar
    elegidas = sorted([c for c in avanzan.index if avanzan[c]], key=lambda c: -p99[c])[:2]
    # Control: la R de V0 con la tubería nueva frente al Ens-V0r de LB2 (±0.03 de F̄)
    z = np.load(cm.RAIZ / 'results/linea_base/lb2/puntajes_2022.npz')
    for k in nombres:
        S[('Ens-V0r-LB2', k)] = np.mean([z[f'V0r_s{s}__{k}'] for s in rc.SEMILLAS], axis=0)
    ctl = pd.concat([cm.metricas(S, [ref, 'Ens-V0r-LB2'], lab, nv) for nv in NIVELES], ignore_index=True)
    ctl.to_csv(rc.SAL / 'control_lb2.csv', index=False, lineterminator='\n')
    dif = {nv: float(ctl[(ctl.nivel == nv) & (ctl.modelo == ref)].Fbar.iloc[0]
                     - ctl[(ctl.nivel == nv) & (ctl.modelo == 'Ens-V0r-LB2')].Fbar.iloc[0]) for nv in NIVELES}
    dec = dict(elegidas=elegidas, avanzan={c: bool(x) for c, x in avanzan.items()},
               control_lb2_dFbar=dif, control_lb2_ok=all(abs(x) <= 0.03 for x in dif.values()))
    (rc.SAL / 'decision_seleccion.json').write_text(json.dumps(dec, indent=2, ensure_ascii=False))
    print(P.round(4).to_string(index=False))
    print(met[met.modelo.isin(ens)][['modelo', 'nivel', 'Fbar', 'F1_100', 'F1_50', 'F1_20']].round(4).to_string(index=False))
    print(json.dumps(dec, indent=1, ensure_ascii=False), flush=True)


def etapa_definitivos(a):
    """Ventanas de la fase definitiva y modelos definitivos de las casillas elegidas + el comparador V0-R."""
    g = rc.grupos_def()
    falta = [x for x in g['fondo'] + g['rec'] if not (rc.VEN / f'{x}.json').exists()]
    fallos = lanzar([(f'ventanas_{x}', ['rev22_ventanas.py', x]) for x in falta], a.paralelo)
    if fallos:
        return fallos
    dec = json.loads((rc.SAL / 'decision_seleccion.json').read_text())
    celdas = [('V0', 'R')] + [tuple(c.split('-')) for c in dec['elegidas']]
    orden = {'M1': 0, 'M2': 1, 'R': 2}
    trab = [(f'definitivo_{rc.nombre_modelo(v, c, s)}', ['rev22_definitivo.py', v, c, str(s), '--hilos', str(a.hilos)])
            for v, c in sorted(celdas, key=lambda t: orden[t[1]]) for s in rc.SEMILLAS
            if not (rc.DEF / f'{rc.nombre_modelo(v, c, s)}.json').exists()]
    return lanzar(trab, a.paralelo)


def etapa_calibracion():
    """Puntaje de 2023 limpio (historia desde 2020) de los definitivos y de L0 único; umbrales p99 y p99.9."""
    import keras
    from src.detect import estacion_dia as ed
    from src.detect import evaluacion_red as ev
    from src.detect import linea_base as lb
    ctx = cm.contexto()
    esc = rc.escalas(ctx, 'definitivo')
    dec = json.loads((rc.SAL / 'decision_seleccion.json').read_text())
    celdas = [('V0', 'R')] + [tuple(c.split('-')) for c in dec['elegidas']]
    mods = {rc.nombre_modelo(v, c, s): (v, keras.models.load_model(rc.DEF / f'{rc.nombre_modelo(v, c, s)}.keras', compile=False))
            for v, c in celdas for s in rc.SEMILLAS}
    mods['L0unico'] = ('V0', keras.models.load_model(cm.SAL_RED / 'lstm_local_examen/c20/d50/modelo.keras', compile=False))
    x = ar.matriz_red(rc.valores('2020-01-01', '2023-12-31 23:00'), rc.columnas())
    pos = np.flatnonzero(x.index.year == 2023)
    b = cm.bases(ctx, x)
    F = {v: lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec']) for v in rc.BASES}
    obj = ctx['objetivos']
    ix = x.index[pos]
    con = x.loc[ix, [f'{s}_mascara' for s in obj]].to_numpy() == 1
    Xw = {v: np.concatenate([cm.ventanas(ctx, F[v], s, pos) for s in obj]) for v in rc.BASES}
    S = {}
    for nm, (v, mdl) in mods.items():
        p = mdl.predict(Xw[v], batch_size=8192, verbose=0).astype(np.float64).reshape(len(obj), len(pos)).T
        dia = ed.juntar_dia(pd.DataFrame(p, index=ix, columns=obj).where(con), 'promedio_dia')
        S[nm], dias = dia.to_numpy(), dia.index
    for v, c in celdas:
        S[f'Ens-{v}-{c}'] = np.mean([S[rc.nombre_modelo(v, c, s)] for s in rc.SEMILLAS], axis=0)
    det = [f'Ens-{v}-{c}' for v, c in celdas] + ['L0unico']
    comun = np.logical_and.reduce([~np.isnan(S[d]) for d in det])
    filas = [dict(detector=d, nivel=nv, umbral=float(ev.umbral_falsas_alarmas(S[d][comun], nv)),
                  estacion_dias=int(comun.sum())) for d in det for nv in NIVELES]
    np.savez_compressed(rc.SAL / 'calibracion_2023.npz', dias=dias.values.astype('datetime64[ns]'), comun=comun, **S)
    U = pd.DataFrame(filas)
    U.to_csv(rc.SAL / 'umbrales_2023.csv', index=False, lineterminator='\n')
    print(U.to_string(index=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('etapa')
    ap.add_argument('--paralelo', type=int, default=4)
    ap.add_argument('--hilos', type=int, default=4)
    a = ap.parse_args()
    etapas = ['auditoria', 'planes', 'ventanas', 'entrenar', 'puntuar', 'seleccion', 'definitivos'] if a.etapa == 'todo' else [a.etapa]
    for e in etapas:
        print(f'== {e} ({time.strftime("%H:%M:%S")})', flush=True)
        f = {'auditoria': etapa_auditoria, 'planes': etapa_planes, 'seleccion': etapa_seleccion,
             'calibracion': etapa_calibracion}.get(e)
        fallos = f() if f else globals()[f'etapa_{e}'](a)
        if fallos:
            raise SystemExit(f'{e}: fallaron {fallos}')


if __name__ == '__main__':
    main()
