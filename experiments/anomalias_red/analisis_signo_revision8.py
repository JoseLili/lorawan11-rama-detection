"""¿Subir la lectura se detecta mejor que bajarla, aun con el mismo cambio en ppb? (revisión 8, exploratorio).

Uso (desde la raíz del repo, con la revisión 8 y la revisión 7 de Colab ya bajadas):

    .venv/bin/python experiments/anomalias_red/analisis_signo_revision8.py

No entrena ni carga modelos. Con los puntajes y umbrales guardados (nivel 5 %), para cada hora
alterada del examen 2024 toma el cambio de su estación en ppb, |alterado − original|, y separa las
horas que subieron (x·(1+δ)) de las que bajaron (x/(1+δ)). Si a igual cambio en ppb bajar sigue
detectándose peor, la dirección importa por sí misma y no sólo el tamaño.

Además mide, en 2023 y 2024 limpios, qué tan seguido una estación queda naturalmente por encima o
por debajo de sus 4 vecinas (estación menos la mediana de sus vecinas, sin su diferencia habitual).
Salidas en results/anomalias_red_v1/analisis_revision8/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import analisis_revision8 as an  # noqa: E402

TRAMOS = [1, 8, 16, 32, np.inf]
NOMBRES = ['1–8 ppb', '8–16 ppb', '16–32 ppb', '≥ 32 ppb']
UMBRALES_PPB = (10, 20, 30)
NIVELES_VECINAS = [0, 20, 40, 60, 80, 100, np.inf]


def horas_alteradas(limpia: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for n, c in an.DETECTORES.items():
        for d in an.DELTAS:
            s = pd.read_csv(c / f'd{d}/puntajes.csv.gz', index_col='timestamp', parse_dates=True)
            m = pd.read_csv(c / f'd{d}/metricas.csv')
            m = m[m.nivel_fa_pct == an.NIVEL].set_index('corrida')
            for corrida, fila in m.iterrows():
                alerta, alerta_limpia = s[corrida] > fila.umbral, s['limpia_2024'] > fila.umbral
                x = an.leer(f'{corrida}_d{d}')
                for e in an.ar.leer_plan(an.PLANES / f'plan_{corrida}.csv').itertuples():
                    orig = limpia.loc[e.inicio:e.fin, f'{e.estacion}_valor']
                    orig = orig[limpia.loc[e.inicio:e.fin, f'{e.estacion}_mascara'].astype(bool)]
                    if orig.empty:
                        continue
                    filas.append(pd.DataFrame(dict(
                        detector=n, delta_pct=d, signo=e.signo, original_ppb=orig.to_numpy(),
                        cambio_ppb=(x.loc[orig.index, f'{e.estacion}_valor'] - orig).abs().to_numpy(),
                        alertan=alerta.loc[orig.index].to_numpy(), alertan_azar=alerta_limpia.loc[orig.index].to_numpy())))
    h = pd.concat(filas, ignore_index=True)
    h['tramo'] = pd.cut(h.cambio_ppb, TRAMOS, right=False, labels=NOMBRES)
    h['direccion'] = h.signo.map({1: 'sube', -1: 'baja'})
    h['horas'] = 1
    return h


def frente_a_vecinas() -> pd.DataFrame:
    """% de horas en que la estación queda > X ppb arriba o abajo de la mediana de sus vecinas."""
    filas, dispersion = [], []
    for anio in (2023, 2024):
        lim = an.leer(f'limpia_{anio}')
        ests = an.ev.estaciones_de(lim)
        vec = an.ev.vecinas_de(ests, pd.read_csv(an.GEOGRAFIA, index_col='station'))
        for s in ests:
            v = lim[[f'{x}_valor' for x in vec[s]]].where(lim[[f'{x}_mascara' for x in vec[s]]].astype(bool).to_numpy())
            dif = lim[f'{s}_valor'].where(lim[f'{s}_mascara'].astype(bool)) - v.median(axis=1)
            dif = (dif - dif.median()).dropna()                       # sin la diferencia habitual
            nivel = pd.cut(v.median(axis=1).loc[dif.index], NIVELES_VECINAS, right=False)
            dispersion.append(pd.DataFrame(dict(nivel=nivel, dif=dif.to_numpy())))
            filas.append(dict(anio=anio, estacion=s, horas=len(dif),
                              **{f'abajo_{u}': int((dif < -u).sum()) for u in UMBRALES_PPB},
                              **{f'arriba_{u}': int((dif > u).sum()) for u in UMBRALES_PPB}))
    return pd.DataFrame(filas), pd.concat(dispersion, ignore_index=True)


def main():
    pd.set_option('display.width', 200)
    limpia = an.leer('limpia_2024')
    h = horas_alteradas(limpia)
    t = (h.groupby(['detector', 'delta_pct', 'tramo', 'direccion'], observed=True)[['horas', 'alertan', 'alertan_azar']]
         .sum().reset_index())
    t['recall_pct'] = 100 * t.alertan / t.horas
    t['azar_pct'] = 100 * t.alertan_azar / t.horas
    t['senal'] = t.recall_pct - t.azar_pct
    t.to_csv(an.OUT / 'senal_por_direccion_y_tramo.csv', index=False)
    print('Horas alteradas que alertan, por dirección y cambio en ppb (nivel 5 %): detecta % (por casualidad %) [horas]')
    t['texto'] = t.apply(lambda r: f'{r.recall_pct:.1f} ({r.azar_pct:.1f}) [{r.horas}]', axis=1)
    print(t.pivot_table(index=['delta_pct', 'tramo'], columns=['detector', 'direccion'], values='texto',
                        aggfunc='first', observed=True).to_string())
    o = h[h.detector == 'LSTM con vecinas'].groupby(['delta_pct', 'tramo', 'direccion'], observed=True).original_ppb.median()
    print('\nOzono original mediano (ppb) de esas horas:')
    print(o.unstack().round(0).to_string())

    v, disp = frente_a_vecinas()
    v.to_csv(an.OUT / 'frente_a_vecinas_limpio.csv', index=False)
    tot = v.sum(numeric_only=True)
    print('\nEn 2023 y 2024 limpios (todas las estaciones), % de horas en que la estación queda, frente a la mediana')
    print('de sus 4 vecinas y sin su diferencia habitual:')
    for u in UMBRALES_PPB:
        print(f'   más de {u} ppb abajo: {100 * tot[f"abajo_{u}"] / tot.horas:.2f} %   '
              f'más de {u} ppb arriba: {100 * tot[f"arriba_{u}"] / tot.horas:.2f} %')
    g = disp.groupby('nivel', observed=True).dif
    r = pd.DataFrame(dict(horas=g.size(), desviacion_ppb=g.std(), p10=g.quantile(0.1), p90=g.quantile(0.9)))
    r.to_csv(an.OUT / 'dispersion_frente_a_vecinas.csv')
    print('\nCuánto se separa normalmente una estación de sus vecinas, según el ozono de las vecinas (ppb):')
    print(r.round(1).to_string())


if __name__ == '__main__':
    main()
