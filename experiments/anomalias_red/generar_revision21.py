"""Revisión 21: matrices de error fijo en ppb con los calendarios de prueba, por año. No entrena nada.

Uso (desde la raíz del repo):

    .venv/bin/python experiments/anomalias_red/generar_revision21.py --anio 2025

Para cada calendario de prueba del año (`prueba_2024_01…10`, `final_2025_01…10` o `final_2026_01…10`) y cada
a ∈ {5, 10, 20, 40} ppb escribe `matriz_fijo_<corrida>_a<a>` con `anomalias_red.aplicar_fijo` (el mismo plan:
estaciones, días y signos). Cada matriz se aplica dos veces y debe salir igual; fuera de los episodios es
idéntica al año limpio y dentro el cambio es exactamente ±a, salvo el recorte en 0. No se sobrescribe una
matriz distinta. Resumen (con el cambio medio en ppb) en results/anomalias_red_v1/resumen_revision21_<año>.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from generar_matrices import comprobar_alterada, guardar_sin_pisar, periodo  # noqa: E402
from generar_revision19 import PERIODO, calendarios_prueba  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PLANES = SAL / 'planes'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anio', type=int, required=True, choices=sorted(PERIODO))
    anio = ap.parse_args().anio
    ctx = em.contexto(RAIZ)
    valores, inactivos = ctx['valores'], ctx['definitiva']['inactivos']
    if list(inactivos) != ['XAL']:
        raise RuntimeError(f'canales inactivos inesperados: {inactivos}')
    cols = ar.columnas_entrada(inactivos)
    ini, fin = ar.PERIODOS[PERIODO[anio]]
    v = periodo(valores, ini, fin)
    limpia = ar.matriz_red(v, cols)
    filas = []
    for c in calendarios_prueba(anio).itertuples():
        plan = ar.leer_plan(PLANES / f'plan_{c.corrida}.csv')
        dentro = ar.en_episodio(plan, v.index, v.columns)
        negativo = pd.DataFrame(False, index=v.index, columns=v.columns)
        for e in plan.itertuples():
            if e.signo < 0:
                negativo.loc[e.inicio:e.fin, e.estacion] = True
        for a in ar.TAMANOS_FIJOS:
            rec, cam = ar.aplicar_fijo(v, plan, a)
            x = ar.matriz_red(rec, cols, cam)
            rec2, cam2 = ar.aplicar_fijo(v, plan, a)                                # reproducibilidad
            pd.testing.assert_frame_equal(x, ar.matriz_red(rec2, cols, cam2))
            esperado = dentro & v.notna() & ~(negativo & v.eq(0.0))                 # x = 0 con signo − no cambia
            comprobar_alterada(x, limpia, cam, cols, int(esperado[cols].to_numpy().sum()))
            d = (rec - v)[cam]
            ok = (d.abs().eq(a) | (negativo & rec.eq(0.0)))[cam].stack()
            if not ok.all():
                raise RuntimeError(f'{c.corrida} a{a}: un cambio no es ±{a} ni el recorte en 0')
            sha, estado = guardar_sin_pisar(f'fijo_{c.corrida}_a{a}', x)
            filas.append(dict(corrida=c.corrida, a_ppb=a, episodios=len(plan),
                              lecturas_alteradas=int(cam[cols].to_numpy().sum()),
                              cambio_medio_ppb=float(np.nanmean(np.abs(d[cols].to_numpy()))),
                              recortadas_en_cero=int((negativo & cam & rec.eq(0.0))[cols].to_numpy().sum()),
                              sha256_csv=sha, estado=estado))
        print(f'  {c.corrida}: listo', flush=True)
    t = pd.DataFrame(filas)
    t.to_csv(SAL / f'resumen_revision21_{anio}.csv', index=False)
    print(t.groupby('a_ppb')[['lecturas_alteradas', 'cambio_medio_ppb', 'recortadas_en_cero']].mean().round(2).to_string(),
          flush=True)


if __name__ == '__main__':
    main()
