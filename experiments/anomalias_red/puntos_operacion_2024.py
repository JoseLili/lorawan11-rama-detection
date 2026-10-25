"""Revisión 15: dos puntos de operación por estación-día (p99 y p99.9) y la curva, en 2024 (en la lap).

Uso (desde la raíz del repo, con el examen de la revisión 14 ya descargado):

    .venv/bin/python experiments/anomalias_red/puntos_operacion_2024.py [--salida DIR] [--sin-v4]

Detectores, sin entrenar nada:
- L0: los puntajes del modelo definitivo de la revisión 14 (lstm_local_examen/c20, dias_examen.csv.gz);
- R3: recalculada como la fase 2 de la revisión 12 (mediana de 14 días, promedio del día, dominancia);
- V4: residuo / p95 juntado con el promedio del día, cargado de disco con la inferencia repetida, como
  la fase 2 de la revisión 11 (unos 10 min).

Umbrales con las estación-días de 2023 limpio: p99 (1 % de falsas alarmas) y p99.9 (0.1 %), y para
la curva 10, 5, 2, 1, 0.5, 0.2, 0.1 y 0.05 %. L0 y R3 se miden en las estación-días válidas para los
dos (como el examen de la revisión 14); el V4 en las suyas (como la revisión 11). No elige nada.

Controles: con 1 y 5 %, L0 y R3 reproducen lstm_local_2024/resultados.csv y el V4
estacion_dia/v4/resultados.csv (TP, FP, FN y TN). Salidas en results/anomalias_red_v1/puntos_operacion_2024/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla, valores_v4  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from metricas_estandar_revision8 import con_umbral  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
SALIDA = SAL / 'puntos_operacion_2024'
LSTM = SAL / 'lstm_local_examen/c20'
EXAMEN_14 = SAL / 'lstm_local_2024/resultados.csv'
V4_11 = SAL / 'estacion_dia/v4/resultados.csv'
PLANES = SAL / 'planes'
AGREGACION = 'promedio_dia'
PUNTOS = {'p99': 0.01, 'p99.9': 0.001}
CURVA = (0.10, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=SALIDA)
    ap.add_argument('--sin-v4', action='store_true')
    args = ap.parse_args()
    salida = args.salida
    salida.mkdir(parents=True, exist_ok=True)
    deltas = [round(100 * d) for d in ar.DELTAS]
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA].tolist()
    examen = [f'{c}_d{d}' for d in deltas for c in corridas]

    limpia_tr, sha_tr, sigma, vec = normalizacion_y_vecinas('mediana')
    r3 = {n: ed.dominancia(ed.juntar_dia(v[objetivos], AGREGACION), vec.vecinas)
          for n, v, _ in valores_regla(examen, limpia_tr, sigma, vec)}
    print('R3 recalculada', flush=True)
    v4 = {} if args.sin_v4 else {n: ed.juntar_dia(v[objetivos], AGREGACION) for n, v, _ in valores_v4(examen)}
    print('V4 listo' if v4 else 'sin V4', flush=True)

    dias = r3['limpia_2024'].index
    Y = np.concatenate([ed.etiquetas(ar.leer_plan(PLANES / f'plan_{c}.csv'), dias, objetivos).to_numpy().ravel()
                        for c in corridas])

    filas, curva = [], []
    for d in deltas:
        L = leer_dias(LSTM / f'd{d}' / 'dias_examen.csv.gz')
        por = {'L0': {k: v[AGREGACION] for k, v in L.items()},
               'R3': {k: r3[k if k.startswith('limpia') else f'{k}_d{d}'] for k in ['limpia_2023', 'limpia_2024'] + corridas}}
        if v4:
            por['V4'] = {k: v4[k if k.startswith('limpia') else f'{k}_d{d}'] for k in ['limpia_2023', 'limpia_2024'] + corridas}
        comunes = {a: por['R3'][a].notna() & por['L0'][a].notna() for a in ('limpia_2023', 'limpia_2024')}
        for nombre, v in por.items():
            if nombre == 'V4':
                validas = {a: v[a].notna() for a in ('limpia_2023', 'limpia_2024')}
            else:
                validas = comunes
            for c in corridas:
                assert v[c].index.equals(dias) and v[c].notna().equals(v['limpia_2024'].notna())
            comun = np.tile(validas['limpia_2024'].to_numpy().ravel(), len(corridas))
            y = Y[comun]
            s = np.concatenate([v[c].to_numpy().ravel() for c in corridas])[comun]
            s0 = np.tile(v['limpia_2024'].to_numpy().ravel(), len(corridas))[comun]
            cal = v['limpia_2023'][validas['limpia_2023']].stack().dropna().to_numpy()
            lim24 = v['limpia_2024'][validas['limpia_2024']].stack().dropna().to_numpy()
            auc = {'con ataque': dict(pr_auc=average_precision_score(y, s), roc_auc=roc_auc_score(y, s)),
                   'sin ataque': dict(pr_auc=average_precision_score(y, s0), roc_auc=roc_auc_score(y, s0))}
            for fa in CURVA:
                u = ev.umbral_falsas_alarmas(cal, fa)
                base = dict(delta_pct=d, detector=nombre, fa_objetivo_pct=100 * fa, umbral=u,
                            estacion_dias_2023=len(cal), por_encima_2023=int((cal > u).sum()),
                            fa_2024_limpio_pct=100 * float((lim24 > u).mean()))
                m = con_umbral(y, s > u)
                curva.append(dict(**base, tp=m['tp'], fp=m['fp'], fn=m['fn'], tn=m['tn'], recall=m['recall'],
                                  precision=m['precision'], f1=m['f1'], fa_examen_pct=100 * m['falsas_alarmas']))
                for punto, fa_p in PUNTOS.items():
                    if fa == fa_p:
                        for version, puntaje in (('con ataque', s), ('sin ataque', s0)):
                            filas.append(dict(punto=punto, version=version, **base, **con_umbral(y, puntaje > u),
                                              **auc[version]))
        print(f'δ = {d} %: listo', flush=True)

    r, cv = pd.DataFrame(filas), pd.DataFrame(curva)
    r.to_csv(salida / 'puntos_operacion.csv', index=False)
    cv.to_csv(salida / 'curva.csv', index=False)

    # Controles: con 1 y 5 %, lo mismo que el examen de la revisión 14 y la fase 2 de la revisión 11.
    claves = ['delta_pct', 'nivel_fa_pct']
    mio = cv[cv.fa_objetivo_pct.round(6).isin([1.0, 5.0])].assign(nivel_fa_pct=lambda x: x.fa_objetivo_pct.round().astype(int))
    control = {}
    e14 = pd.read_csv(EXAMEN_14)
    e14 = e14[e14.version == 'con ataque']
    for nombre in ('L0', 'R3'):
        a = mio[mio.detector == nombre].set_index(claves)[['tp', 'fp', 'fn', 'tn']].sort_index()
        b = e14[e14.detector == nombre].set_index(claves)[['tp', 'fp', 'fn', 'tn']].sort_index()
        control[nombre] = bool(a.equals(b))
    if v4:
        e11 = pd.read_csv(V4_11)
        e11 = e11[(e11.version == 'con ataque') & (e11.agregacion == AGREGACION)]
        a = mio[mio.detector == 'V4'].set_index(claves)[['tp', 'fp', 'fn', 'tn']].sort_index()
        b = e11.set_index(claves)[['tp', 'fp', 'fn', 'tn']].sort_index()
        control['V4'] = bool(a.equals(b))
    print('controles (reproducen 1 y 5 %):', control, flush=True)
    (salida / 'configuracion.json').write_text(json.dumps(dict(
        protocolo=ar.PROTOCOLO, revision=15, puntos=PUNTOS, curva_fa=list(CURVA), agregacion=AGREGACION,
        origen=dict(L0='modelo definitivo de la revisión 14, puntajes guardados (recién entrenado en Colab, rev14)',
                    R3='sin entrenamiento', V4='cargado de disco, inferencia repetida en la lap'),
        controles_reproducen=control, calendarios=corridas, deltas_pct=deltas, sha256_matriz_ajuste=sha_tr,
        fecha=datetime.now().isoformat(timespec='seconds')), indent=2, ensure_ascii=False))
    columnas = ['delta_pct', 'detector', 'punto', 'version', 'umbral', 'por_encima_2023', 'fa_2024_limpio_pct', 'tp',
                'fp', 'fn', 'recall', 'precision', 'f1', 'f2', 'falsas_alarmas']
    print(r[columnas].round(4).to_string(index=False))


if __name__ == '__main__':
    main()
