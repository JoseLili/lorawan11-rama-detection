"""Entradas restringidas a las k vecinas geográficamente más cercanas.

Protocolo: docs/protocolo_vecinas_cercanas_v1.md (`v4k_multianual_33_p95cal2023_v1`).
Mismo V4 multianual (contexto pasado), sólo cambia qué estaciones entran al modelo.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from src.detect import multianual as m
from src.detect import entrenamiento_multianual as em
from src.detect import contemporaneo as ct

PROTOCOLO = 'v4k_multianual_33_p95cal2023_v1'
KS = (4, 8, 16)
K_V4 = 32
RADIO_KM = 6371.0
ARCHIVOS_V4 = ['modelo.keras', 'preprocesamiento.npz', 'umbral_p95_cal2023.txt', 'historia_definitiva.csv']


def distancias(geo: pd.DataFrame) -> pd.DataFrame:
    """Matriz haversine (km) entre las estaciones de la matriz fija."""
    g = geo.loc[m.ESTACIONES]
    la, lo = np.radians(g['latitud'].to_numpy()), np.radians(g['longitud'].to_numpy())
    dla, dlo = la[:, None] - la[None, :], lo[:, None] - lo[None, :]
    a = np.sin(dla / 2) ** 2 + np.cos(la)[:, None] * np.cos(la)[None, :] * np.sin(dlo / 2) ** 2
    return pd.DataFrame(2 * RADIO_KM * np.arcsin(np.sqrt(a)), index=m.ESTACIONES, columns=m.ESTACIONES)


def vecinas_cercanas(dist: pd.DataFrame, objetivo: str, k: int, inactivos=()) -> list[str]:
    """Las k estaciones activas más cercanas (empates por clave), sin el objetivo."""
    cand = [s for s in m.ESTACIONES if s != objetivo and s not in set(inactivos)]
    return sorted(cand, key=lambda s: (dist.at[objetivo, s], s))[:k]


def fase1(ctx, objetivo, vecinas, max_epocas=em.CONFIG['max_epocas'], unidades=em.CONFIG['unidades']):
    """Fase 1 del V4 (ajuste 2020–21, validación 2022) con sólo `vecinas`. Devuelve (historia, E)."""
    valores, ini = ctx['valores'], ctx['inicial']
    entradas = ini['entradas'][[objetivo] + list(vecinas)]
    perfil = m.perfil_causal(valores[objetivo])
    tr = em.tensores(entradas, valores, objetivo, ini['mu'], ini['sigma'], perfil, ('ajuste_inicial',))
    va = em.tensores(entradas, valores, objetivo, ini['mu'], ini['sigma'], perfil, ('validacion',))
    modelo = em.nuevo_modelo(2 * len(vecinas) + 2, unidades=unidades)
    hist = em.entrenar_seleccion(modelo, tr, va, max_epocas=max_epocas)
    return hist, em.seleccionar_epoca(hist)


def entrenar_knn(ctx, objetivo, carpeta, dist, v4_estaciones, ks=KS,
                 max_epocas=em.CONFIG['max_epocas'], unidades=em.CONFIG['unidades']):
    """Elige k con 2022 y deja en `carpeta` el modelo definitivo (o la copia del V4 si k* = 32)."""
    carpeta = Path(carpeta)
    if (carpeta / 'configuracion.json').exists():
        raise FileExistsError(f'{carpeta} ya tiene modelo; no se sobrescribe')
    carpeta.mkdir(parents=True, exist_ok=True)
    inactivos = ctx['definitiva']['inactivos']
    filas = []
    for k in ks:
        vec = vecinas_cercanas(dist, objetivo, k, inactivos)
        hist, E = fase1(ctx, objetivo, vec, max_epocas=max_epocas, unidades=unidades)
        (carpeta / f'seleccion_k/{k}').mkdir(parents=True, exist_ok=True)
        hist.to_csv(carpeta / f'seleccion_k/{k}/historia_seleccion.csv')
        filas.append(dict(k=k, val_loss_min=float(hist['val_loss'].min()), E=E, vecinas=' '.join(vec),
                          dist_max_km=round(float(dist.loc[objetivo, vec].max()), 2)))
    v4 = Path(v4_estaciones) / objetivo
    cfg_v4 = json.loads((v4 / 'configuracion.json').read_text())
    filas.append(dict(k=K_V4, val_loss_min=float(cfg_v4['val_loss_minimo']), E=cfg_v4['epoca_E'],
                      vecinas='todas (V4)', dist_max_km=round(float(dist.loc[objetivo].drop(objetivo).max()), 2)))
    sel = pd.DataFrame(filas)
    sel.to_csv(carpeta / 'seleccion_k.csv', index=False)
    mejor = sel.sort_values(['val_loss_min', 'k']).iloc[0]
    k_est = int(mejor.k)

    if k_est == K_V4:                                # el V4 ya es el mejor: se copia, no se reentrena
        for f in ARCHIVOS_V4:
            shutil.copy2(v4 / f, carpeta / f)
        shutil.copytree(v4 / 'seleccion', carpeta / 'seleccion', dirs_exist_ok=True)
        cfg = dict(cfg_v4, protocolo=PROTOCOLO, origen='copia del V4 multianual (k* = 32)')
        (carpeta / 'configuracion.json').write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n')
        ct.regenerar(ctx, objetivo, carpeta)          # exige el mismo p95 que el V4
    else:
        vec = mejor.vecinas.split()
        cfg = em.entrenar_objetivo(ctx, objetivo, carpeta, vecinas=vec, protocolo=PROTOCOLO,
                                   max_epocas=max_epocas, unidades=unidades)
        cfg['origen'] = 'entrenado con las k vecinas más cercanas'
    cfg.update(k=k_est, ks_probados=[*ks, K_V4])
    (carpeta / 'configuracion.json').write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n')
    return cfg
