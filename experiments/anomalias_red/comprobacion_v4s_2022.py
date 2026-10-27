"""Revisión 18: comprobación de funcionamiento del V4S con 2022, antes de la evaluación. No elige nada.

Uso: .venv/bin/python experiments/anomalias_red/comprobacion_v4s_2022.py [--compartido]

Muchas estaciones eligieron E = 1. Esto comprueba, sin mirar 2023–2026, que el V4S sí distingue horas
atacadas: con los modelos de **selección** (entrenados con 2020–2021, cargados de disco) sobre todas las
horas de 2022 de los calendarios 01–10 con δ = 50 %, el ROC-AUC y el PR-AUC por hora, por estación y
juntas. Contraste por estación-día (promedio del día): el V4S contra el modelo de selección de L0 con
δ = 50 % (sus puntajes guardados en lstm_local/c20/d50/seleccion/dias_2022.csv.gz), en las
estación-días válidas para los dos. Es optimista para los dos, porque 2022 se usó para el
EarlyStopping. Salida en results/anomalias_red_v1/v4_supervisado/comprobacion_2022.csv. Con --compartido,
lo mismo con el modelo de selección del V4S compartido (revisión 18b), en
results/anomalias_red_v1/v4_supervisado_compartido/comprobacion_2022.csv.
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
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import entrenamiento_multianual as em  # noqa: E402
from src.detect import estacion_dia as ed  # noqa: E402
from src.detect import multianual as m  # noqa: E402
from src.detect import v4_supervisado as vs  # noqa: E402
from entrenar_lstm_estacion import leer_dias  # noqa: E402
from entrenar_lstm_sup import leer  # noqa: E402
from entrenar_v4_supervisado import FIN_AJUSTE, N_VALIDACION  # noqa: E402
from evaluar_v4 import con_examen  # noqa: E402
from generar_planes import alterables_v4  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
V4S = SAL / 'v4_supervisado/d50'
V4SC = SAL / 'v4_supervisado_compartido/d50'
L0_2022 = SAL / 'lstm_local/c20/d50/seleccion/dias_2022.csv.gz'


def main():
    from tensorflow import keras
    ap = argparse.ArgumentParser()
    ap.add_argument('--compartido', action='store_true')
    compartido = ap.parse_args().compartido
    objetivos = alterables_v4()
    ctx = em.contexto(RAIZ)
    valores, f = ctx['valores'].loc[:FIN_AJUSTE], ctx['inicial']
    cal = ar.calendarios_entrenamiento(n=20).iloc[:N_VALIDACION]
    if compartido:
        uno = keras.models.load_model(V4SC / 'seleccion/modelo_seleccion.keras', compile=False)
        modelos, ordenes = {s: uno for s in objetivos}, json.loads((V4SC / 'configuracion.json').read_text())['ordenes']
    else:
        modelos = {s: keras.models.load_model(V4S / s / 'seleccion/modelo_seleccion.keras', compile=False)
                   for s in objetivos}
        ordenes = None
    horas = valores.loc['2022-01-01':].index
    dias = horas.normalize().unique()
    filas, prob, Yd = [], {}, []
    Yh = {s: [] for s in objetivos}
    Sg = {s: [] for s in objetivos}                 # signo del episodio en cada hora (0 si no hay)
    Ph = {s: [] for s in objetivos}
    for c in cal.corrida:
        x, _ = leer(f'{c}_d50')
        V = con_examen(valores, x)
        p = vs.probabilidades(modelos, V, f['inactivos'], f['mu'], f['sigma'], 'validacion', horas, ordenes=ordenes)
        y = ed.etiquetas_por_hora(x, objetivos).loc[horas]
        plan = ar.leer_plan(SAL / 'planes' / f'plan_{c}.csv')
        signo = pd.DataFrame(0, index=horas, columns=objetivos)
        for e in plan.itertuples():
            signo.loc[max(e.inicio, horas[0]):e.fin, e.estacion] = e.signo
        for s in objetivos:
            ok = p[s].notna().to_numpy()
            Yh[s].append(y[s].to_numpy()[ok])
            Ph[s].append(p[s].to_numpy()[ok])
            Sg[s].append(signo[s].to_numpy()[ok])
        prob[c] = ed.juntar_dia(p[objetivos], 'promedio_dia')
        Yd.append(ed.etiquetas(ar.leer_plan(SAL / 'planes' / f'plan_{c}.csv'), dias, objetivos))
        print(f'{c}: listo', flush=True)
    for s in objetivos:
        y, p = np.concatenate(Yh[s]), np.concatenate(Ph[s])
        filas.append(dict(nivel='hora', estacion=s, horas=len(y), atacadas=int(y.sum()),
                          roc_auc=roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan,
                          pr_auc=average_precision_score(y, p) if y.any() else np.nan, azar_pr=float(y.mean())))
    y, p = np.concatenate([np.concatenate(Yh[s]) for s in objetivos]), np.concatenate([np.concatenate(Ph[s]) for s in objetivos])
    filas.append(dict(nivel='hora', estacion='todas', horas=len(y), atacadas=int(y.sum()), roc_auc=roc_auc_score(y, p),
                      pr_auc=average_precision_score(y, p), azar_pr=float(y.mean())))
    # Por signo: horas atacadas con signo + (o −) contra las normales.
    for s in objetivos + ['todas']:
        est = objetivos if s == 'todas' else [s]
        y = np.concatenate([np.concatenate(Yh[e]) for e in est]).astype(bool)
        p = np.concatenate([np.concatenate(Ph[e]) for e in est])
        g = np.concatenate([np.concatenate(Sg[e]) for e in est])
        for signo, nombre in ((1, 'hora, signo +'), (-1, 'hora, signo −')):
            sel = ~y | (y & (g == signo))
            ys = y[sel]
            if 0 < ys.sum() < len(ys):
                filas.append(dict(nivel=nombre, estacion=s, horas=int(sel.sum()), atacadas=int(ys.sum()),
                                  roc_auc=roc_auc_score(ys, p[sel]), pr_auc=average_precision_score(ys, p[sel]),
                                  azar_pr=float(ys.mean())))
    L = leer_dias(L0_2022)
    for det, S in (('V4S', prob), ('L0', {c: L[c]['promedio_dia'][objetivos] for c in cal.corrida})):
        sv = np.concatenate([S[c].reindex(dias).to_numpy().ravel() for c in cal.corrida])
        otro = prob if det == 'L0' else {c: L[c]['promedio_dia'][objetivos] for c in cal.corrida}
        so = np.concatenate([otro[c].reindex(dias).to_numpy().ravel() for c in cal.corrida])
        yd = np.concatenate([t.to_numpy().ravel() for t in Yd]).astype(bool)
        ok = ~np.isnan(sv) & ~np.isnan(so)
        filas.append(dict(nivel='estacion-dia (comunes)', estacion=det, horas=int(ok.sum()), atacadas=int(yd[ok].sum()),
                          roc_auc=roc_auc_score(yd[ok], sv[ok]), pr_auc=average_precision_score(yd[ok], sv[ok]),
                          azar_pr=float(yd[ok].mean())))
    t = pd.DataFrame(filas)
    t.to_csv((V4SC if compartido else V4S).parent / 'comprobacion_2022.csv', index=False)
    print(t.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
