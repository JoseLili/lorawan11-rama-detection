"""Exploración (2026-10-25, a pedido del tesista; no decide nada): ¿dónde detecta L0 y dónde no?

Uso: .venv/bin/python experiments/anomalias_red/exploracion_sesgos_2024.py

Examen 2024 de la revisión 14, p99 (umbrales de 2023 limpio, estación-días comunes con R3): recall de
L0 y R3 por signo del episodio, por su duración y por estación, y su relación con la distancia a las
4 vecinas. Usa los puntajes guardados de L0 y recalcula R3; no carga modelos.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402
from src.detect.vecinas import distancias  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from entrenar_lstm_sup import GEOGRAFIA  # noqa: E402
from evaluar_estacion_dia import normalizacion_y_vecinas, valores_regla  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402
from puntos_operacion_2024 import LSTM  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'


def main():
    objetivos = alterables_v4()
    corridas = ar.corridas().corrida.iloc[1:1 + ar.CORRIDAS_PRUEBA].tolist()
    deltas = (100, 50, 20)
    limpia_tr, _, sigma, vec = normalizacion_y_vecinas('mediana')
    examen = [f'{c}_d{d}' for d in deltas for c in corridas]
    r3 = {n: ed.dominancia(ed.juntar_dia(v[objetivos], 'promedio_dia'), vec.vecinas)
          for n, v, _ in valores_regla(examen, limpia_tr, sigma, vec)}
    dias = r3['limpia_2024'].index
    # atributos de cada estación-día atacada: signo y duración del episodio
    signo, dur = [], []
    for c in corridas:
        s = pd.DataFrame(0, index=dias, columns=objetivos)
        u = pd.DataFrame(0, index=dias, columns=objetivos)
        for e in ar.leer_plan(SAL / f'planes/plan_{c}.csv').itertuples():
            s.loc[e.inicio.normalize():e.fin.normalize(), e.estacion] = e.signo
            u.loc[e.inicio.normalize():e.fin.normalize(), e.estacion] = e.dias
        signo.append(s.to_numpy().ravel()); dur.append(u.to_numpy().ravel())
    signo, dur = np.concatenate(signo), np.concatenate(dur)
    estacion = np.tile(np.tile(np.array(objetivos), len(dias)), len(corridas))
    geo = pd.read_csv(GEOGRAFIA, index_col='station')
    dist = distancias(geo)
    d_vec = pd.Series({s: float(np.mean([dist.loc[s, v] for v in vec.vecinas[s]])) for s in objetivos})
    filas, por_est = [], []
    for d in deltas:
        L = leer_dias(LSTM / f'd{d}' / 'dias_examen.csv.gz')
        por = {'L0': {k: v['promedio_dia'] for k, v in L.items()},
               'R3': {k: r3[k if k.startswith('limpia') else f'{k}_d{d}'] for k in ['limpia_2023', 'limpia_2024'] + corridas}}
        v23 = por['R3']['limpia_2023'].notna() & por['L0']['limpia_2023'].notna()
        v24 = np.tile((por['R3']['limpia_2024'].notna() & por['L0']['limpia_2024'].notna()).to_numpy().ravel(), len(corridas))
        for nombre, v in por.items():
            u = ev.umbral_falsas_alarmas(v['limpia_2023'][v23].stack().dropna().to_numpy(), 0.01)
            alerta = np.concatenate([v[c].to_numpy().ravel() for c in corridas]) > u
            at = (signo != 0) & v24
            for etiqueta, m in [('signo +', signo > 0), ('signo −', signo < 0), ('1 día', dur == 1),
                                ('2–3 días', (dur >= 2) & (dur <= 3)), ('4–7 días', dur >= 4)]:
                sel = at & m
                filas.append(dict(delta_pct=d, detector=nombre, grupo=etiqueta, estacion_dias=int(sel.sum()),
                                  recall_pct=100 * float(alerta[sel].mean())))
            for s in objetivos:
                sel = at & (estacion == s)
                por_est.append(dict(delta_pct=d, detector=nombre, estacion=s, atacadas=int(sel.sum()),
                                    recall_pct=100 * float(alerta[sel].mean()) if sel.any() else np.nan,
                                    distancia_media_vecinas_km=d_vec[s]))
    t = pd.DataFrame(filas)
    print(t.pivot_table(index=['delta_pct', 'grupo'], columns='detector', values='recall_pct').round(1))
    e = pd.DataFrame(por_est)
    for (d, n), g in e.groupby(['delta_pct', 'detector']):
        g = g.dropna()
        print(f'δ = {d} %, {n}: recall por estación de {g.recall_pct.min():.0f} a {g.recall_pct.max():.0f} % '
              f'(mediana {g.recall_pct.median():.0f}); correlación con la distancia a las vecinas '
              f'{g[["recall_pct", "distancia_media_vecinas_km"]].corr(method="spearman").iat[0, 1]:+.2f}')
    print(e[(e.delta_pct == 50) & (e.detector == 'L0')].sort_values('recall_pct').head(5).round(1).to_string(index=False))
    print(e[(e.delta_pct == 50) & (e.detector == 'L0')].sort_values('recall_pct').tail(3).round(1).to_string(index=False))


if __name__ == '__main__':
    main()
