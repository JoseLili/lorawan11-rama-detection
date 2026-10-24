"""Análisis de los resultados de la revisión 8 en el examen 2024 (exploratorio, después de verlos).

Uso (desde la raíz del repo, con la revisión 8 y la revisión 7 de Colab ya bajadas):

    .venv/bin/python experiments/anomalias_red/analisis_revision8.py

No entrena ni carga modelos y no cambia la revisión 8: lee los puntajes, umbrales, planes y matrices
guardados. Compara tres detectores (LSTM con vecinas a14, LSTM sin vecinas de la revisión 7 en Colab
y la regla de vecinas) con δ = 100, 50 y 20 %, al nivel de 5 % de falsas alarmas:
1. recall por tamaño del cambio en ppb, contra las mismas horas sin alterar;
2. señal por hora dentro de cada episodio, según signo, duración, estación y distancia a sus vecinas;
3. falsas alarmas en las horas normales del examen según el tiempo desde el último episodio, contra
   esas mismas horas en 2024 limpio (¿el exceso de falsas alarmas viene de después de los episodios?).
Salidas en results/anomalias_red_v1/analisis_revision8/.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
OUT = SAL / 'analisis_revision8'
GEOGRAFIA = RAIZ / 'results/inventario_multianual/estaciones_geografia.csv'
DETECTORES = {'LSTM con vecinas': SAL / 'lstm_sup_vecinas_a14_20cal',
              'LSTM sin vecinas': SAL / 'colab_revision7/lstm_sup_relativas_20cal',
              'Regla de vecinas': SAL / 'regla_vecinas_a14'}
DELTAS = (100, 50, 20)
NIVEL = 5
DURACION = {1: '1–2 días', 2: '1–2 días', 3: '3–4 días', 4: '3–4 días', 5: '5–7 días', 6: '5–7 días', 7: '5–7 días'}
TRAS_EPISODIO_H = (0, 24, 72, 168, 336)                      # 0–1 d, 1–3 d, 3–7 d, 7–14 d, ≥ 14 d


def leer(nombre: str) -> pd.DataFrame:
    return pd.read_csv(MATRICES / f'matriz_{nombre}.csv.gz', index_col='timestamp', parse_dates=True,
                       low_memory=False)


def senal(g: pd.DataFrame) -> pd.Series:
    """Recall, azar pareado y señal (puntos) de un grupo de horas."""
    h = g.horas.sum()
    if h == 0:
        return pd.Series(dict(horas=0, recall_pct=np.nan, azar_pct=np.nan, senal=np.nan))
    return pd.Series(dict(horas=h, recall_pct=100 * g.alertan.sum() / h, azar_pct=100 * g.alertan_azar.sum() / h,
                          senal=100 * (g.alertan.sum() - g.alertan_azar.sum()) / h))


def por_tamano() -> pd.DataFrame:
    filas = []
    for n, c in DETECTORES.items():
        for d in DELTAS:
            t = pd.read_csv(c / f'd{d}/por_tamano.csv')
            t = t[(t.nivel_fa_pct == NIVEL) & (t.tramo_ppb != 'sin cambio')]
            for tramo, g in t.groupby('tramo_ppb', sort=False):
                filas.append(dict(detector=n, delta_pct=d, tramo_ppb=tramo, **senal(g)))
    return pd.DataFrame(filas)


def distancia_vecinas(estaciones) -> pd.Series:
    """Distancia media (km) de cada estación a sus 4 vecinas de la revisión 8."""
    from src.detect.vecinas import distancias
    geo = pd.read_csv(GEOGRAFIA, index_col='station')
    dist = distancias(geo)
    vec = ev.vecinas_de(estaciones, geo)
    return pd.Series({s: float(np.mean([dist.at[s, v] for v in vs])) for s, vs in vec.items()})


def horas_y_alertas(limpia: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Por detector, δ y calendario: horas de cada episodio y falsas alarmas tras los episodios."""
    episodios, normales, control = [], [], []
    for n, c in DETECTORES.items():
        for d in DELTAS:
            s = pd.read_csv(c / f'd{d}/puntajes.csv.gz', index_col='timestamp', parse_dates=True)
            m = pd.read_csv(c / f'd{d}/metricas.csv')
            m = m[m.nivel_fa_pct == NIVEL].set_index('corrida')
            for corrida, fila in m.iterrows():
                u = fila.umbral
                alerta, alerta_limpia = s[corrida] > u, s['limpia_2024'] > u
                x = leer(f'{corrida}_d{d}')
                y = x['anomalia_red'].astype(bool)
                control.append(dict(detector=n, delta_pct=d, corrida=corrida,
                                    recall_guardado=fila.deteccion_hora_pct,
                                    recall_recalculado=100 * alerta.loc[y.index][y].mean()))
                plan = ar.leer_plan(PLANES / f'plan_{corrida}.csv')
                for e in plan.itertuples():
                    con_dato = limpia.loc[e.inicio:e.fin, f'{e.estacion}_mascara'].astype(bool)
                    horas = con_dato.index[con_dato.to_numpy()]
                    if len(horas) == 0:
                        continue
                    episodios.append(dict(detector=n, delta_pct=d, corrida=corrida, estacion=e.estacion,
                                          dias=e.dias, signo=e.signo, horas=len(horas),
                                          alertan=int(alerta.loc[horas].sum()),
                                          alertan_azar=int(alerta_limpia.loc[horas].sum())))
                # Horas normales del examen según las horas desde el fin del último episodio.
                fines = np.sort(plan.fin.to_numpy(dtype='datetime64[ns]'))
                idx = y.index[~y.to_numpy()].to_numpy(dtype='datetime64[ns]')
                k = np.searchsorted(fines, idx, side='right') - 1
                tras = np.where(k >= 0, (idx - fines[np.clip(k, 0, None)]) / np.timedelta64(1, 'h'), np.inf)
                bordes = [*TRAS_EPISODIO_H, np.inf]
                nombres = ['0–1 d', '1–3 d', '3–7 d', '7–14 d', '≥ 14 d o ninguno']
                tramo = pd.cut(tras, bordes, right=False, labels=nombres)
                a, al = alerta.loc[idx].to_numpy(), alerta_limpia.loc[idx].to_numpy()
                g = pd.DataFrame(dict(tramo=tramo, alertan=a, alertan_azar=al)).groupby('tramo', observed=False)
                normales.append(pd.DataFrame(dict(detector=n, delta_pct=d, corrida=corrida, tras_episodio=nombres,
                                                  horas=g.size().to_numpy(), alertan=g.alertan.sum().to_numpy(),
                                                  alertan_azar=g.alertan_azar.sum().to_numpy())))
    return pd.DataFrame(episodios), pd.concat(normales, ignore_index=True), pd.DataFrame(control)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option('display.width', 200)
    limpia = leer('limpia_2024')
    tam = por_tamano()
    epi, normales, control = horas_y_alertas(limpia)
    dif = (control.recall_guardado - control.recall_recalculado).abs().max()
    print(f'Control: recall por hora recalculado desde los puntajes guardados; diferencia máxima {dif:.3f} puntos')

    print('\n1. Recall por tamaño del cambio (nivel 5 %): recall (azar) señal')
    tam['texto'] = tam.apply(lambda r: f'{r.recall_pct:.1f} ({r.azar_pct:.1f}) {r.senal:+.1f}', axis=1)
    print(tam.pivot_table(index=['delta_pct', 'tramo_ppb'], columns='detector', values='texto', aggfunc='first',
                          sort=False).to_string())

    dist = distancia_vecinas(ev.estaciones_de(limpia))
    epi['duracion'] = epi.dias.map(DURACION)
    epi['signo_txt'] = epi.signo.map({1: 'x·(1+δ)', -1: 'x/(1+δ)'})
    epi['dist_km'] = epi.estacion.map(dist)
    terciles = pd.qcut(dist, 3, labels=['cercanas', 'medias', 'lejanas'])
    epi['vecinas'] = epi.estacion.map(terciles)
    print('\n2. Señal por hora dentro de los episodios (nivel 5 %, puntos)')
    resumenes = {}
    for col in ['signo_txt', 'duracion', 'vecinas']:
        r = epi.groupby(['delta_pct', col, 'detector'], observed=True).apply(senal, include_groups=False).reset_index()
        resumenes[col] = r
        print(f'\n   según {col}:')
        print(r.pivot_table(index=['delta_pct', col], columns='detector', values='senal', observed=True)
              .round(1).to_string())
    rango = {t: f'{dist[terciles == t].min():.1f}–{dist[terciles == t].max():.1f} km' for t in terciles.cat.categories}
    print('   distancia media a las 4 vecinas por grupo:', rango)

    est = epi.groupby(['delta_pct', 'estacion', 'detector']).apply(senal, include_groups=False).reset_index()
    est['dist_km'] = est.estacion.map(dist)
    print('\n   correlación de Spearman entre la distancia a las vecinas y la ganancia por estación')
    for d in DELTAS:
        p = est[est.delta_pct == d].pivot(index='estacion', columns='detector', values='senal')
        gan = p['LSTM con vecinas'] - p['LSTM sin vecinas']
        print(f'   δ = {d} %: {gan.corr(dist.loc[gan.index], method="spearman"):+.2f} '
              f'(n = {len(gan)} estaciones; ganancia mediana {gan.median():+.1f} puntos; '
              f'{int((gan > 0).sum())} de {len(gan)} estaciones ganan)')

    print('\n3. Falsas alarmas en las horas normales del examen según el tiempo desde el último episodio')
    fa = normales.groupby(['detector', 'delta_pct', 'tras_episodio'], sort=False).apply(senal, include_groups=False)
    fa = fa.rename(columns=dict(recall_pct='fa_examen_pct', azar_pct='fa_2024_limpio_pct', senal='exceso')).reset_index()
    print(fa.pivot_table(index=['delta_pct', 'tras_episodio'], columns='detector',
                         values=['fa_examen_pct', 'fa_2024_limpio_pct'], sort=False).round(1).to_string())

    tam.drop(columns='texto').to_csv(OUT / 'por_tamano.csv', index=False)
    epi.to_csv(OUT / 'horas_por_episodio.csv', index=False)
    est.to_csv(OUT / 'por_estacion.csv', index=False)
    fa.to_csv(OUT / 'falsas_alarmas_tras_episodio.csv', index=False)
    control.to_csv(OUT / 'control_recalculo.csv', index=False)
    for col, r in resumenes.items():
        r.to_csv(OUT / f'senal_por_{col.removesuffix("_txt")}.csv', index=False)


if __name__ == '__main__':
    main()
