"""Revisión 16 (3): la prueba con hora de inicio al azar de la revisión 6, en 2024, con p99 y p99.9 (en la lap).

Uso (después de modelo_unico_delta.py): .venv/bin/python experiments/anomalias_red/hora_azar_2024.py [--salida DIR]

Los mismos 10 calendarios de 2024, con cada episodio recorrido una hora h (una por calendario y
estación, `anomalias_red.recorrer_plan`); las matrices se guardan como
matrices/matriz_hora_azar_2024_<k>_d<δ>.csv.gz y los planes en <salida>/planes/. Una estación-día
está atacada si 12 horas o más caen en un episodio, es normal si ninguna, y se excluye en medio
(`estacion_dia.etiquetas_recorridas`).

Detectores, sin reentrenar y con los umbrales de siempre (2023 limpio, p99 y p99.9): L0 con el modelo
definitivo de cada δ, el modelo único elegido en modelo_unico_delta.py, R3 y el V4 (cargado de disco,
inferencia repetida). L0 y R3 en las estación-días válidas para los dos; el V4 en las suyas. Se
compara con el examen con inicio a medianoche (revisiones 14, 15 y 16-2).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from entrenar_lstm_local import REFERENCIA, por_dia  # noqa: E402
from entrenar_lstm_sup import leer, parametros_vecinas  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla, valores_v4  # noqa: E402
from generar_matrices import guardar_sin_pisar, periodo  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402
from modelo_unico_delta import SALIDA as UNICO, cargar  # noqa: E402
from puntos_operacion_2024 import LSTM, PUNTOS  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'comprobaciones_2024/hora_azar'
PLANES = SAL / 'planes'
AGREGACION = 'promedio_dia'
DELTAS = [round(100 * d) for d in ar.DELTAS]


def generar(corridas, salida):
    """Planes recorridos y matrices; devuelve las etiquetas día × estación de cada calendario."""
    ctx = em.contexto(RAIZ)
    cols = ar.columnas_entrada(ctx['definitiva']['inactivos'])
    ini, fin = ar.PERIODOS['prueba_2024']
    v = periodo(ctx['valores'], ini, fin)
    objetivos = alterables_v4()
    (salida / 'planes').mkdir(parents=True, exist_ok=True)
    etiquetas, filas = {}, []
    for k, c in enumerate(corridas, 1):
        plan = ar.leer_plan(PLANES / f'plan_{c}.csv')
        r = ar.recorrer_plan(plan, k, ini, fin)
        pd.testing.assert_frame_equal(r, ar.recorrer_plan(plan, k, ini, fin))            # reproducibilidad
        r.to_csv(salida / 'planes' / f'plan_hora_azar_2024_{k:02d}.csv', index=False)
        etiquetas[k] = ed.etiquetas_recorridas(r, v.index, objetivos)
        for d in ar.DELTAS:
            rec, cam = ar.aplicar_horas(v, r, d)
            x = ar.matriz_red(rec, cols, cam)
            nombre = f'hora_azar_2024_{k:02d}_d{round(100 * d)}'
            sha, estado = guardar_sin_pisar(nombre, x)
            filas.append(dict(matriz=nombre, sha256_csv=sha, estado=estado, lecturas_alteradas=int(cam.to_numpy().sum())))
    pd.DataFrame(filas).to_csv(salida / 'matrices.csv', index=False)
    print(f'{len(filas)} matrices listas', flush=True)
    return etiquetas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--tolerancia-v4', type=float, default=None,
                    help='ppb; control del V4 contra sus predicciones guardadas en otra máquina (por omisión 1e-9)')
    args = ap.parse_args()
    salida = args.salida
    if args.tolerancia_v4 is not None:                 # otra CPU: la inferencia float32 difiere ~1e-5 ppb
        import evaluar_estacion_dia
        evaluar_estacion_dia.TOLERANCIA_PPB = args.tolerancia_v4
    salida.mkdir(parents=True, exist_ok=True)
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA].tolist()
    unico = json.loads((UNICO / 'eleccion.json').read_text())['eleccion_2022']['modelo_unico']
    etiquetas = generar(corridas, salida)
    nombres = {d: [f'hora_azar_2024_{k:02d}_d{d}' for k in range(1, len(corridas) + 1)] for d in DELTAS}
    examen = [n for d in DELTAS for n in nombres[d]]

    limpia_tr, _, sigma, vec = normalizacion_y_vecinas('mediana')
    r3 = {n: ed.dominancia(ed.juntar_dia(v[objetivos], AGREGACION), vec.vecinas)
          for n, v, _ in valores_regla(examen, limpia_tr, sigma, vec)}
    print('R3 lista', flush=True)
    v4 = {n: ed.juntar_dia(v[objetivos], AGREGACION) for n, v, _ in valores_v4(examen)}
    print('V4 listo', flush=True)

    par = parametros_vecinas('a14', limpia_tr, sigma, REFERENCIA)
    estaciones = ev.estaciones_de(limpia_tr)
    modelos = {m: cargar(LSTM / f'd{m}' / 'modelo.keras') for m in DELTAS}
    cal, _ = leer('limpia_2023')
    historia = ev.con_historia(limpia_tr, cal)

    def puntuar(previa, matriz, ms):
        x = ev.con_historia(previa, matriz)
        F = ev.entradas_de('vecinas', x, None, sigma, par)
        return {m: por_dia(modelos[m], F, x, np.arange(len(previa), len(x)), estaciones, par.vecinas,
                           objetivos)[AGREGACION] for m in ms}

    l23 = puntuar(limpia_tr, cal, DELTAS)
    l24 = puntuar(historia, leer('limpia_2024')[0], DELTAS)
    dias = r3['limpia_2024'].index
    Y = np.concatenate([etiquetas[k].to_numpy().ravel() for k in range(1, len(corridas) + 1)])     # 1, 0 o NaN
    filas, conteos = [], []
    for d in DELTAS:
        p = {n: puntuar(historia, leer(n)[0], sorted({d, unico})) for n in nombres[d]}
        dets = {'L0': ({'limpia_2023': l23[d], 'limpia_2024': l24[d]}, [p[n][d] for n in nombres[d]]),
                f'L0_unico_d{unico}': ({'limpia_2023': l23[unico], 'limpia_2024': l24[unico]},
                                       [p[n][unico] for n in nombres[d]]),
                'R3': ({'limpia_2023': r3['limpia_2023'], 'limpia_2024': r3['limpia_2024']}, [r3[n] for n in nombres[d]]),
                'V4': ({'limpia_2023': v4['limpia_2023'], 'limpia_2024': v4['limpia_2024']}, [v4[n] for n in nombres[d]])}
        v23 = r3['limpia_2023'].notna() & l23[d].notna()
        v24 = r3['limpia_2024'].notna() & l24[d].notna()
        for nombre, (limpio, cals) in dets.items():
            assert all(s.index.equals(dias) for s in cals)
            if nombre == 'V4':
                a23, a24 = limpio['limpia_2023'].notna(), limpio['limpia_2024'].notna()
            else:
                a23, a24 = v23, v24
            ok = np.tile(a24.to_numpy().ravel(), len(corridas)) & ~np.isnan(Y)
            y = Y[ok] == 1.0
            s = np.concatenate([x.to_numpy().ravel() for x in cals])[ok]
            s0 = np.tile(limpio['limpia_2024'].to_numpy().ravel(), len(corridas))[ok]
            excl = np.tile(a24.to_numpy().ravel(), len(corridas)) & np.isnan(Y)
            conteos.append(dict(delta_pct=d, detector=nombre, atacadas=int(y.sum()), normales=int((~y).sum()),
                                excluidas_parciales=int(excl.sum())))
            cal23 = limpio['limpia_2023'][a23].stack().dropna().to_numpy()
            for punto, fa in PUNTOS.items():
                u = ev.umbral_falsas_alarmas(cal23, fa)
                for version, puntaje in (('con ataque', s), ('sin ataque', s0)):
                    filas.append(dict(delta_pct=d, detector=nombre, punto=punto, version=version, umbral=u,
                                      **con_umbral(y, puntaje > u)))
        print(f'δ = {d} %: listo', flush=True)

    r = pd.DataFrame(filas)
    r.to_csv(salida / 'resultados.csv', index=False)
    pd.DataFrame(conteos).to_csv(salida / 'conteos.csv', index=False)

    # Comparación con el examen con inicio a medianoche (F1, con ataque).
    po = pd.read_csv(SAL / 'puntos_operacion_2024/puntos_operacion.csv')
    po = po[po.version == 'con ataque'][['delta_pct', 'detector', 'punto', 'f1']]
    mu = pd.read_csv(UNICO / 'examen_2024.csv')
    mu = mu[mu.modelo == f'L0_d{unico}'].rename(columns={'delta_examen': 'delta_pct'})
    mu = mu.assign(detector=f'L0_unico_d{unico}')[['delta_pct', 'detector', 'punto', 'f1']]
    medianoche = pd.concat([po, mu]).rename(columns={'f1': 'f1_medianoche'})
    azar = r[r.version == 'con ataque'][['delta_pct', 'detector', 'punto', 'f1']].rename(columns={'f1': 'f1_hora_azar'})
    comp = azar.merge(medianoche, on=['delta_pct', 'detector', 'punto'], how='left')
    comp['cambio'] = comp.f1_hora_azar - comp.f1_medianoche
    comp.to_csv(salida / 'comparacion_medianoche.csv', index=False)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=16, comprobacion='hora de inicio al azar', modelo_unico=unico,
        etiqueta=f'atacada con {ed.MIN_HORAS} horas o más en un episodio; normal con ninguna; en medio se excluye',
        origen=dict(L0='modelos definitivos cargados de disco (Colab, rev14); inferencia en la lap',
                    V4='cargado de disco, inferencia repetida', R3='sin entrenamiento'),
        puntos=PUNTOS, tolerancia_control_v4_ppb=args.tolerancia_v4 or 1e-9), indent=2, ensure_ascii=False))
    print(comp.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
