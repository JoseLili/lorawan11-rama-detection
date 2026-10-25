"""Genera los planes de inyección del protocolo anomalias_red_v1 (§5–§6). No entrena nada.

Uso (desde la raíz del repo):

    .venv/bin/python experiments/anomalias_red/generar_planes.py

Escribe results/anomalias_red_v1/planes/plan_<corrida>.csv (1 de entrenamiento, 10 de
prueba sobre 2024 y 20 calendarios de entrenamiento sobre 2020–2022: los 10 primeros de la
revisión 6 y los 10 que agrega la revisión 7) y resumen_planes.csv. Cada plan se genera dos veces y debe salir igual.
Si un plan ya existe y es distinto, se detiene en lugar de sobrescribirlo.

Con --ampliados escribe sólo los calendarios entrenamiento_21…60 de la revisión 14 y su resumen en
resumen_planes_revision14.csv; los planes y el resumen de siempre no cambian. Con --final, sólo los
calendarios del examen final (revisión 17), final_2025_01…10 y final_2026_01…10, y resumen_planes_final.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PLANES = SAL / 'planes'
V4 = RAIZ / 'results/lstm_v4_multianual_v1'


def alterables_v4() -> list[str]:
    """Los 31 objetivos del V4, cotejados con los modelos que hay en disco."""
    alt = ar.estaciones_alterables(pd.read_csv(V4 / 'cobertura_etapas.csv'))
    con_modelo = {p.parent.name for p in (V4 / 'estaciones').glob('*/configuracion.json')}
    if len(alt) != 31 or set(alt) != con_modelo:
        raise RuntimeError(f'alterables ({len(alt)}) no coinciden con los modelos V4 en disco')
    return alt


def guardar_sin_pisar(plan: pd.DataFrame) -> str:
    destino = PLANES / f'plan_{plan["corrida"].iat[0]}.csv'
    if destino.exists():
        previo = ar.leer_plan(destino)
        try:
            pd.testing.assert_frame_equal(previo, plan, check_dtype=False)
        except AssertionError:
            raise RuntimeError(f'{destino.name} ya existe y es distinto; no se sobrescribe')
        return 'ya existía, idéntico'
    ar.guardar_plan(plan, PLANES)
    return 'nuevo'


def resumir(valores: pd.DataFrame, plan: pd.DataFrame, corrida: pd.Series) -> dict:
    ini, fin = pd.Timestamp(corrida['inicio']), pd.Timestamp(corrida['fin']) + pd.Timedelta(hours=23)
    v = valores.loc[ini:fin]
    r = ar.resumen_episodios(v, plan)
    ocupadas = ar.en_episodio(plan, v.index).sum(axis=1)
    fila = dict(corrida=corrida['corrida'], inicio=corrida['inicio'], fin=corrida['fin'], p=corrida['p'],
                episodios=len(plan), evaluables=int(r['evaluable'].sum()),
                sin_dato=int((~r['evaluable']).sum()), cortados=int((plan.dias < plan.dias_sorteados).sum()),
                signo_mas=int((plan.signo > 0).sum()), signo_menos=int((plan.signo < 0).sum()),
                dias_media=round(plan['dias'].mean(), 2),
                horas_red=len(v), horas_red_1omas_pct=round(100 * (ocupadas >= 1).mean(), 1),
                horas_red_2omas_pct=round(100 * (ocupadas >= 2).mean(), 1))
    for d in ar.DELTAS:
        _, cambiadas = ar.aplicar(v, plan, d)
        fila[f'etiqueta_red_d{round(100 * d)}_pct'] = round(100 * ar.etiqueta_red(cambiadas).mean(), 1)
    return fila


RESUMEN = {'siempre': 'resumen_planes.csv', 'ampliados': 'resumen_planes_revision14.csv', 'final': 'resumen_planes_final.csv'}


def corridas_de(modo: str = 'siempre') -> pd.DataFrame:
    """Las corridas de siempre; `ampliados`: sólo entrenamiento_21…60 (revisión 14); `final`: las del
    examen final (revisión 17)."""
    if modo == 'ampliados':
        return ar.calendarios_entrenamiento(n=ar.CALENDARIOS_AMPLIADOS).iloc[ar.CALENDARIOS_ENTRENAMIENTO:]
    if modo == 'final':
        return ar.corridas_finales()
    return pd.concat([ar.corridas(), ar.calendarios_entrenamiento()], ignore_index=True)


def modo_de_argumentos() -> str:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--ampliados', action='store_true')
    g.add_argument('--final', action='store_true')
    a = ap.parse_args()
    return 'ampliados' if a.ampliados else 'final' if a.final else 'siempre'


def main():
    modo = modo_de_argumentos()
    ctx = em.contexto(RAIZ)
    valores = ctx['valores']
    alterables = alterables_v4()
    filas = []
    for _, c in corridas_de(modo).iterrows():
        plan = ar.plan_de(c, alterables)
        pd.testing.assert_frame_equal(plan, ar.plan_de(c, alterables))     # reproducibilidad
        estado = guardar_sin_pisar(plan)
        filas.append(resumir(valores, plan, c))
        print(f'{c["corrida"]:>16}  p = {100 * c["p"]:.3f} %  episodios = {len(plan):3d}  ({estado})')
    resumen = pd.DataFrame(filas)
    resumen.to_csv(SAL / RESUMEN[modo], index=False)
    print(resumen.drop(columns=['inicio', 'fin']).to_string(index=False))


if __name__ == '__main__':
    main()
