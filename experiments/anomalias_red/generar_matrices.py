"""Genera las matrices de red del protocolo anomalias_red_v1 para revisarlas. No entrena nada.

Uso (desde la raíz del repo, después de generar_planes.py):

    .venv/bin/python experiments/anomalias_red/generar_matrices.py

Escribe results/anomalias_red_v1/matrices/matriz_<nombre>.csv.gz (158 matrices) y
resumen_matrices.csv:

    limpia_2020_2022                 entrenamiento del IsolationForest
    entrenamiento_d<δ>      × 5      entrenamiento del Random Forest (un modelo por δ)
    entrenamiento_<k>_d<δ>  × 100    LSTM supervisado y su Random Forest de control:
                                     20 calendarios × 5 δ (la revisión 6 usa los 10 primeros)
    limpia_2023                      calibración del umbral
    limpia_2024                      falsas alarmas
    prueba_2024_<k>_d<δ>    × 50     examen: 10 calendarios × 5 δ

Comprobaciones: rejilla horaria continua y ordenada, límites del periodo, máscaras iguales a las
de la matriz limpia, valores distintos sólo donde el plan altera, conteos iguales a los del
resumen de episodios y la misma matriz al generarla dos veces. Si un archivo ya existe y es
distinto, se detiene en lugar de sobrescribirlo.
"""
from __future__ import annotations

import gzip
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
PLANES = SAL / 'planes'
MATRICES = SAL / 'matrices'
sys.path.insert(0, str(Path(__file__).parent))
from generar_planes import alterables_v4  # noqa: E402

LIMPIAS = {
    'limpia_2020_2022': (('2020-01-01', '2022-12-31'), 'entrenamiento IsolationForest'),
    'limpia_2023': (('2023-01-01', '2023-12-31'), 'calibración del umbral'),
    'limpia_2024': (('2024-01-01', '2024-12-31'), 'falsas alarmas'),
}


def periodo(valores, ini, fin):
    ini, fin = pd.Timestamp(ini), pd.Timestamp(fin) + pd.Timedelta(hours=23)
    v = valores.loc[ini:fin]
    if v.index[0] != ini or v.index[-1] != fin or len(v) != int((fin - ini) / pd.Timedelta(hours=1)) + 1:
        raise RuntimeError(f'periodo incompleto {ini} – {fin}')
    return v


def texto(x: pd.DataFrame) -> str:
    return x.to_csv(float_format='%.10g')


def guardar_sin_pisar(nombre: str, x: pd.DataFrame) -> tuple[str, str]:
    """CSV comprimido sin fecha en la cabecera, para que el mismo contenido dé el mismo archivo."""
    s = texto(x).encode()
    sha = hashlib.sha256(s).hexdigest()
    destino = MATRICES / f'matriz_{nombre}.csv.gz'
    if destino.exists():
        previo = hashlib.sha256(gzip.decompress(destino.read_bytes())).hexdigest()
        if previo != sha:
            raise RuntimeError(f'{destino.name} ya existe y es distinto; no se sobrescribe')
        return sha, 'ya existía, idéntico'
    with gzip.GzipFile(destino, 'wb', mtime=0) as f:
        f.write(s)
    return sha, 'nuevo'


def comprobar_alterada(x: pd.DataFrame, limpia: pd.DataFrame, cam: pd.DataFrame, cols, esperado: int):
    vc, mc = [f'{s}_valor' for s in cols], [f'{s}_mascara' for s in cols]
    pd.testing.assert_frame_equal(x[mc], limpia[mc])
    pd.testing.assert_frame_equal(x[['hora_sin', 'hora_cos']], limpia[['hora_sin', 'hora_cos']])
    distinto = x[vc].ne(limpia[vc]) & limpia[vc].notna()
    distinto.columns = cols
    if not distinto.equals(cam[cols]):
        raise RuntimeError('los valores cambian fuera de las lecturas marcadas como alteradas')
    if int(cam.to_numpy().sum()) != esperado:
        raise RuntimeError('lecturas alteradas distintas del resumen de episodios')


def main():
    ctx = em.contexto(RAIZ)
    valores = ctx['valores']
    inactivos = ctx['definitiva']['inactivos']
    if list(inactivos) != ['XAL']:
        raise RuntimeError(f'canales inactivos inesperados: {inactivos}')
    cols = ar.columnas_entrada(inactivos)
    alterables = alterables_v4()
    MATRICES.mkdir(parents=True, exist_ok=True)

    trabajos = []    # (nombre, uso, corrida, δ, inicio, fin, plan)
    for nombre, ((ini, fin), uso) in LIMPIAS.items():
        trabajos.append((nombre, uso, '', np.nan, ini, fin, None))
    for _, c in pd.concat([ar.corridas(), ar.calendarios_entrenamiento()], ignore_index=True).iterrows():
        plan = ar.leer_plan(PLANES / f'plan_{c["corrida"]}.csv')
        pd.testing.assert_frame_equal(plan, ar.plan_de(c, alterables), check_dtype=False)
        uso = ('entrenamiento Random Forest' if c['corrida'] == 'entrenamiento'
               else 'entrenamiento supervisado (revisión 6)' if c['corrida'].startswith('entrenamiento_')
               else 'examen')
        for d in ar.DELTAS:
            nombre = f'{c["corrida"]}_d{round(100 * d)}'
            trabajos.append((nombre, uso, c['corrida'], d, c['inicio'], c['fin'], plan))

    filas, limpias = [], {}
    for nombre, uso, corrida, d, ini, fin, plan in trabajos:
        v = periodo(valores, ini, fin)
        clave_limpia = (str(ini), str(fin))
        if clave_limpia not in limpias:
            limpias[clave_limpia] = ar.matriz_red(v, cols)
        if plan is None:
            x, cam = limpias[clave_limpia], None
        else:
            rec, cam = ar.aplicar(v, plan, d)
            x = ar.matriz_red(rec, cols, cam)
            rec2, cam2 = ar.aplicar(v, plan, d)                                  # reproducibilidad
            pd.testing.assert_frame_equal(x, ar.matriz_red(rec2, cols, cam2))
            esperado = int(ar.resumen_episodios(v, plan, (d,))[f'horas_cambiadas_d{round(100 * d)}'].sum())
            comprobar_alterada(x, limpias[clave_limpia], cam, cols, esperado)
        sha, estado = guardar_sin_pisar(nombre, x)
        mascaras = x[[f'{s}_mascara' for s in cols]].to_numpy()
        filas.append(dict(
            archivo=f'matriz_{nombre}.csv.gz', uso=uso, corrida=corrida,
            delta_pct=round(100 * d) if plan is not None else np.nan,
            inicio=x.index[0], fin=x.index[-1], filas=len(x), estaciones=len(cols),
            lecturas_con_dato=int(mascaras.sum()),
            lecturas_alteradas=0 if cam is None else int(cam[cols].to_numpy().sum()),
            horas_anomalia_red=int(x['anomalia_red'].sum()),
            horas_anomalia_red_pct=round(100 * x['anomalia_red'].mean(), 1),
            sha256_csv=sha))
        print(f'{nombre:>26}  {len(x):6d} horas  anomalía de red {filas[-1]["horas_anomalia_red_pct"]:5.1f} %  ({estado})')
    pd.DataFrame(filas).to_csv(SAL / 'resumen_matrices.csv', index=False)


if __name__ == '__main__':
    main()
