"""Revisión 19: planes y matrices de los dos escenarios de una sola estación, por año. No entrena nada.

Uso (desde la raíz del repo, con las matrices de prueba de 2024 o del examen final ya generadas):

    .venv/bin/python experiments/anomalias_red/generar_revision19.py --anio 2025

- (B) una a la vez: `plan_unavez_<corrida>.csv`, con `una_a_la_vez` sobre cada calendario de prueba del
  año, y `matriz_unavez_<corrida>_d<δ>`. Control: en las lecturas de los episodios conservados la matriz
  es idéntica a la del calendario original; en el resto, al año limpio.
- (A) un solo nodo: `plan_nodo_<año>_<estación>.csv` (`corridas_nodo`, `plan_nodo`) y
  `matriz_nodo_<año>_<estación>_d<δ>`.

Cada plan se genera dos veces y debe salir igual; cada matriz se aplica dos veces. No se sobrescribe un
plan o una matriz distintos. Resumen en results/anomalias_red_v1/resumen_revision19_<año>.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from generar_matrices import MATRICES, comprobar_alterada, guardar_sin_pisar, periodo  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from generar_planes import guardar_sin_pisar as guardar_plan_sin_pisar  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PLANES = SAL / 'planes'
PERIODO = {2024: 'prueba_2024', 2025: 'final_2025', 2026: 'final_2026'}


def calendarios_prueba(anio: int) -> pd.DataFrame:
    c = ar.corridas().iloc[1:1 + ar.CORRIDAS_PRUEBA] if anio == 2024 else ar.corridas_finales()
    return c[c.corrida.str.startswith(PERIODO[anio])].reset_index(drop=True)


def dias_atacados(plan: pd.DataFrame) -> int:
    return int(sum(e.dias for e in plan.itertuples()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anio', type=int, required=True, choices=sorted(PERIODO))
    anio = ap.parse_args().anio
    ctx = em.contexto(RAIZ)
    valores, inactivos = ctx['valores'], ctx['definitiva']['inactivos']
    if list(inactivos) != ['XAL']:
        raise RuntimeError(f'canales inactivos inesperados: {inactivos}')
    cols = ar.columnas_entrada(inactivos)
    alterables = alterables_v4()
    ini, fin = ar.PERIODOS[PERIODO[anio]]
    v = periodo(valores, ini, fin)
    limpia = ar.matriz_red(v, cols)

    trabajos, filas = [], []                   # (escenario, plan, plan original o None)
    for c in calendarios_prueba(anio).itertuples():
        original = ar.leer_plan(PLANES / f'plan_{c.corrida}.csv')
        q = ar.una_a_la_vez(original).assign(corrida=f'unavez_{c.corrida}')
        pd.testing.assert_frame_equal(q, ar.una_a_la_vez(original).assign(corrida=f'unavez_{c.corrida}'))
        trabajos.append(('B', q, c.corrida))
        filas.append(dict(escenario='B', corrida=q.corrida.iat[0], origen=c.corrida, p=c.p, episodios=len(q),
                          episodios_origen=len(original), dias_atacados=dias_atacados(q),
                          dias_atacados_origen=dias_atacados(original), estado=guardar_plan_sin_pisar(q)))
    for c in ar.corridas_nodo(alterables).itertuples():
        if not c.corrida.startswith(f'nodo_{anio}_'):
            continue
        plan = ar.plan_nodo(c._asdict())
        pd.testing.assert_frame_equal(plan, ar.plan_nodo(c._asdict()))
        trabajos.append(('A', plan, None))
        filas.append(dict(escenario='A', corrida=c.corrida, origen='', p=c.p, episodios=len(plan),
                          episodios_origen=None, dias_atacados=dias_atacados(plan), dias_atacados_origen=None,
                          estado=guardar_plan_sin_pisar(plan) if len(plan) else 'sin episodios'))
    print(f'{anio}: {sum(t[0] == "B" for t in trabajos)} planes B y {sum(t[0] == "A" for t in trabajos)} planes A',
          flush=True)

    for f, (escenario, plan, origen) in zip(filas, trabajos):
        for d in ar.DELTAS:
            k = round(100 * d)
            if not len(plan):                                                    # A: el sorteo no dio episodios
                x, cam = limpia, pd.DataFrame(False, index=v.index, columns=v.columns)
            else:
                rec, cam = ar.aplicar(v, plan, d)
                x = ar.matriz_red(rec, cols, cam)
                rec2, cam2 = ar.aplicar(v, plan, d)                              # reproducibilidad
                pd.testing.assert_frame_equal(x, ar.matriz_red(rec2, cols, cam2))
                esperado = int(ar.resumen_episodios(v, plan, (d,))[f'horas_cambiadas_d{k}'].sum())
                comprobar_alterada(x, limpia, cam, cols, esperado)
            if origen is not None:                                               # B: igual al original en lo conservado
                xo = ar.leer_matriz(MATRICES / f'matriz_{origen}_d{k}.csv.gz')
                dentro = ar.en_episodio(plan, x.index, cols)
                for s in cols:
                    a, b = x[f'{s}_valor'][dentro[s]], xo[f'{s}_valor'][dentro[s]]
                    if not a.equals(b):
                        raise RuntimeError(f'{plan.corrida.iat[0]} d{k} {s}: distinto del calendario original')
            sha, estado = guardar_sin_pisar(f'{plan.corrida.iat[0]}_d{k}' if len(plan) else f'{f["corrida"]}_d{k}', x)
            f[f'sha256_d{k}'] = sha
            f[f'lecturas_alteradas_d{k}'] = int(cam[cols].to_numpy().sum())
        print(f'  {f["corrida"]}: {f["episodios"]} episodios, {f["dias_atacados"]} días atacados', flush=True)
    t = pd.DataFrame(filas)
    t.to_csv(SAL / f'resumen_revision19_{anio}.csv', index=False)
    b = t[t.escenario == 'B']
    print(f'B conserva {100 * b.dias_atacados.sum() / b.dias_atacados_origen.sum():.1f} % de los días atacados; '
          f'A: {t[t.escenario == "A"].episodios.sum()} episodios en 31 nodos', flush=True)


if __name__ == '__main__':
    main()
