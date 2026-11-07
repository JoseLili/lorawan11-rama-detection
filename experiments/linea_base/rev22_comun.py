"""Revisión 22: piezas comunes (años extra, planes de fondo, ventanas en disco, lotes).

Etapas del protocolo: ajuste 2020–2021 + años extra elegibles, elección en 2022, calibración en
2023. Este módulo no abre nada posterior a 2022, salvo los años extra 2012–2019 como fondo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import comun as cm
import numpy as np
import pandas as pd

from src.detect import anomalias_red as ar
from src.detect import estacion_dia as ed
from src.detect import linea_base as lb
from src.detect import lstm_local as ll
from src.detect import multianual as mu

SAL = cm.RAIZ / 'results/linea_base/rev22'
VEN = SAL / 'ventanas'            # memmaps .npy, no se versionan
MOD = SAL / 'modelos_seleccion'
DEF = SAL / 'modelos_definitivos'
PUN = SAL / 'puntajes_2022'
SEMILLAS = (42, 1, 2, 3, 4)
BASES = ('V0', 'Vb')
CELDAS = ('R', 'M1', 'M2')        # R = sólo 2020–2021
N_FONDO, NUM0 = 5, 100            # 5 calendarios por año extra, números 101–105 (sin choques)
COBERTURA_MIN, OBJ_MIN = 0.75, 16
PACIENCIA, LR_AFINAR = 3, 1e-4
CHECKSUMS = ('checksums_2000_2015.txt', 'checksums_2017_2019.txt', 'checksums_2020_2026.txt')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def checksums() -> dict:
    ck = {}
    for f in CHECKSUMS:
        ck |= mu.leer_checksums(cm.RAIZ / 'docs' / f)
    return ck


def valores(desde, hasta) -> pd.DataFrame:
    """O3 horario × 33 estaciones fijas en la rejilla [desde, hasta], con SHA-256 verificado."""
    anios = range(pd.Timestamp(desde).year, pd.Timestamp(hasta).year + 1)
    largo, _ = mu.cargar_o3_zips(cm.RAIZ / 'data/raw', checksums(), anios=anios)
    rej = pd.date_range(desde, hasta, freq='h', name='timestamp')
    largo = largo[largo['station'].isin(mu.ESTACIONES)]
    v = largo.pivot(index='timestamp', columns='station', values='value').reindex(index=rej, columns=mu.ESTACIONES)
    v.columns.name = 'station'
    return v


def columnas():
    return ar.columnas_entrada(['XAL'])


def objetivos():
    from generar_planes import alterables_v4
    return alterables_v4()


def elegibles() -> dict[int, list[str]]:
    """{año: objetivos con cobertura ≥ 0.75} de los años con ≥ 16 objetivos (auditoría registrada)."""
    return {int(k): v for k, v in json.loads((SAL / 'elegibles.json').read_text()).items()}


def plan_fondo(y: int, k: int) -> pd.DataFrame:
    return ar.leer_plan(SAL / f'planes/plan_fondo_{y}_{k:02d}.csv')


def matriz_fondo(y: int, k: int, v: pd.DataFrame | None = None) -> pd.DataFrame:
    """Matriz con δ = 50 % del calendario k del año y, con historia desde el 1 de octubre anterior."""
    if v is None:
        v = valores(f'{y - 1}-10-01', f'{y}-12-31 23:00')
    rec, cam = ar.aplicar(v, plan_fondo(y, k), 0.5)
    return ar.matriz_red(rec, columnas(), cam)


def escalas(ctx, fase: str) -> dict:
    """Escala a14 de cada base: 2020–2021 limpio en la selección, 2020–2022 en la fase definitiva."""
    if fase == 'seleccion':
        import lb1
        return lb1.escalas(ctx)
    z = np.load(cm.RAIZ / 'results/linea_base/examen_final/escalas_definitivas.npz')
    return {v: z[v] for v in BASES}


def ventanas_de(ctx, x, esc, pos, uso, calendario, obj_validos) -> dict:
    """Ventanas (1 de cada 8 horas) y etiquetas de los objetivos válidos, para las dos bases."""
    Y = ed.etiquetas_por_hora(x, ctx['objetivos'])
    b = cm.bases(ctx, x)
    V = lb.valores(x, ctx['estaciones'])
    out = {}
    for v in BASES:
        F = lb.entradas(x, b[v], ctx['estaciones'], ctx['sigma'], esc[v], ctx['vec'], V)
        X, y = [], []
        for j, s in enumerate(ctx['objetivos']):
            if s not in obj_validos:
                continue
            p = ll.muestra(pos, 8, uso, calendario, j)
            X.append(cm.ventanas(ctx, F, s, p))
            y.append(Y[s].to_numpy(np.float32)[p])
        out[v] = (np.concatenate(X), np.concatenate(y))
    return out


def guardar_ventanas(grupo: str, partes: list[dict]) -> dict:
    VEN.mkdir(parents=True, exist_ok=True)
    info = {}
    for v in BASES:
        X = np.concatenate([p[v][0] for p in partes])
        y = np.concatenate([p[v][1] for p in partes])
        np.save(VEN / f'{v}__{grupo}__X.npy', X)
        np.save(VEN / f'{v}__{grupo}__y.npy', y)
        info[v] = dict(ventanas=int(len(y)), positivas_pct=float(100 * y.mean()))
    return info


def grupos() -> dict[str, list[str]]:
    """Grupos de ventanas de la selección: fondo por año, 2020–2021 y validación 2022."""
    fondo = [f'fondo_{y}' for y in elegibles()]
    rec = [f'rec_{a:02d}_{a + 4:02d}' for a in (1, 6, 11, 16)]
    val = ['val_01_05', 'val_06_10']
    return dict(fondo=fondo, rec=rec, val=val)


def partes(v: str, nombres: list[str]):
    return [(np.load(VEN / f'{v}__{g}__X.npy', mmap_mode='r'), np.load(VEN / f'{v}__{g}__y.npy')) for g in nombres]


def nombre_modelo(v, c, s):
    return f'{v}_{c}_s{s}'


def grupos_def() -> dict[str, list[str]]:
    """Grupos de la fase definitiva: fondo por año y 2020–2022 (todas las horas, 1 de cada 8)."""
    return dict(fondo=[f'deffondo_{y}' for y in elegibles()], rec=[f'defrec_{a:02d}_{a + 4:02d}' for a in (1, 6, 11, 16)])
