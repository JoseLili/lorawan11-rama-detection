"""Estudio de las falsas alarmas de la parte 2 en el examen 2024 (revisión 8, exploratorio).

Uso (desde la raíz del repo, con la revisión 8 y la revisión 7 de Colab ya bajadas):

    .venv/bin/python experiments/anomalias_red/falsas_alarmas_revision8.py

Se hizo después de ver los resultados y no cambia ningún modelo ni umbral. No entrena ni carga
modelos: usa los puntajes y umbrales guardados; sólo recalcula, sin aprender nada, las columnas de
vecinas y las entradas relativas para ver qué estación dispara la regla y qué ve el LSTM.
Una «falsa alarma» es una alarma en una hora con etiqueta de red 0. Se compara siempre con esas
mismas horas en 2024 limpio, con el mismo umbral. Responde cinco preguntas:
A. ¿cuántos días después de un ataque duran las falsas alarmas de más?
B. ¿dependen del ataque anterior (dirección y duración)?
C. ¿la estación que dispara la alarma es la que fue atacada? (regla de vecinas y V4)
   y ¿qué le pasa a la estación atacada después del ataque? (entradas del LSTM, δ = 100 %)
D. ¿por qué 2024 limpio da más falsas alarmas que 2023? (por mes, por hora, ozono y cobertura)
E. ¿cómo cambian las métricas sin las horas de los 14 días posteriores a cada ataque? (contraste)
Salidas en results/anomalias_red_v1/analisis_revision8/falsas_alarmas_*.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import matthews_corrcoef  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
MATRICES, PLANES = SAL / 'matrices', SAL / 'planes'
OUT = SAL / 'analisis_revision8'
DETECTORES = {'LSTM con vecinas': 'lstm_sup_vecinas_a14_20cal', 'LSTM sin vecinas': 'colab_revision7/lstm_sup_relativas_20cal',
              'RF con vecinas': 'rf_vecinas_a14_20cal', 'Regla de vecinas': 'regla_vecinas_a14', 'V4': 'v4',
              'IsolationForest': 'if'}
DELTAS = (100, 50, 20)
NIVELES = ('1', '5')
DIAS_MAX = 20
VENTANA_TRAS = 14                    # días tras el fin de un ataque que se excluyen en E


def leer(nombre: str) -> pd.DataFrame:
    return ar.leer_matriz(MATRICES / f'matriz_{nombre}.csv.gz')


def puntajes(carpeta: Path) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Puntajes por corrida y, en el V4, la estación con el mayor residuo."""
    if carpeta.parent.name == 'v4':
        s = pd.read_csv(carpeta / 'puntajes.csv.gz', header=[0, 1], index_col=0)
        s.index = pd.to_datetime(s.index)
        return s.xs('puntaje', axis=1, level=1).astype(float), s.xs('estacion_max', axis=1, level=1)
    s = pd.read_csv(carpeta / 'puntajes.csv.gz', index_col='timestamp', parse_dates=True)
    return s.astype(float), None


def umbrales(carpeta: Path) -> dict[str, pd.Series]:
    m = pd.read_csv(carpeta / 'metricas.csv')
    col = 'nivel' if 'nivel' in m else 'nivel_fa_pct'
    return {k: m[m[col].astype(str) == k].set_index('corrida').umbral for k in NIVELES}


def dias_tras_ataque(index: pd.DatetimeIndex, plan: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Días completos desde el fin del último ataque terminado (0 = primeras 24 h) y su posición en el plan."""
    orden = plan.sort_values('fin').reset_index(drop=True)
    fines = orden.fin.to_numpy(dtype='datetime64[ns]')
    t = index.to_numpy(dtype='datetime64[ns]')
    k = np.searchsorted(fines, t, side='left') - 1          # fin estrictamente anterior
    h = np.where(k >= 0, (t - fines[np.clip(k, 0, None)]) / np.timedelta64(1, 'h'), np.inf)
    return np.floor((h - 1) / 24), k, orden


def tabla_metricas(y, a) -> dict:
    tp, fp = int((a & y).sum()), int((a & ~y).sum())
    fn, tn = int((~a & y).sum()), int((~a & ~y).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = lambda b: (1 + b * b) * p * r / (b * b * p + r) if p + r else 0.0  # noqa: E731
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=p, recall=r, falsas_alarmas=fp / (fp + tn),
                f1=f(1), f2=f(2), mcc=matthews_corrcoef(y, a))


def por_cobertura() -> pd.DataFrame:
    """D (complemento): % de horas limpias con alarma según cuántas estaciones tienen dato (umbral de δ = 100 %)."""
    filas = []
    for anio in (2023, 2024):
        m = leer(f'limpia_{anio}')
        n = m[[f'{s}_mascara' for s in ev.estaciones_de(m)]].sum(axis=1)
        tramo = pd.cut(n, [0, 16, 20, 24, 28, 33], right=False, labels=['<16', '16–19', '20–23', '24–27', '≥28'])
        for det in ('LSTM con vecinas', 'LSTM sin vecinas', 'Regla de vecinas', 'V4', 'IsolationForest'):
            (s, _), u = puntajes(SAL / DETECTORES[det] / 'd100'), umbrales(SAL / DETECTORES[det] / 'd100')
            for k in NIVELES:
                a = s.loc[m.index, f'limpia_{anio}'] > u[k].iloc[0]
                for t, v in a.groupby(tramo, observed=False):
                    filas.append(dict(anio=anio, detector=det, nivel=k, estaciones_con_dato=t, horas=len(v),
                                      alertan_pct=100 * v.mean()))
    f = pd.DataFrame(filas)
    f.to_csv(OUT / 'falsas_alarmas_por_cobertura.csv', index=False)
    return f


def main():
    pd.set_option('display.width', 220)
    OUT.mkdir(parents=True, exist_ok=True)
    limpia_tr = leer('limpia_2020_2022')
    cal = leer('limpia_2023')
    limpia = leer('limpia_2024')
    historia = ev.con_historia(limpia_tr, cal)
    _, sigma = ev.normalizacion(limpia_tr)
    from entrenar_lstm_sup import parametros_vecinas
    vec = parametros_vecinas('a14', limpia_tr, sigma)
    col_limpia = ev.columnas_vecinas(ev.con_historia(historia, limpia), sigma, vec).iloc[len(historia):]
    rel_limpia = ev.relativas(ev.con_historia(historia, limpia)).iloc[len(historia):] / sigma

    datos = {n: (puntajes(SAL / c / 'd100'), umbrales(SAL / c / 'd100')) for n, c in DETECTORES.items()}
    decaimiento, previo, estacion, mecanismo, sin_ventana, control = [], [], [], [], [], []
    for d in DELTAS:
        por_det = {n: (puntajes(SAL / c / f'd{d}'), umbrales(SAL / c / f'd{d}')) for n, c in DETECTORES.items()}
        for corrida in ar.corridas().iloc[1:].corrida:
            x = leer(f'{corrida}_d{d}')
            y = x['anomalia_red'].astype(bool).to_numpy()
            plan = ar.leer_plan(PLANES / f'plan_{corrida}.csv')
            dias, k, orden = dias_tras_ataque(x.index, plan)
            normal = ~y
            previo_signo = np.where(k >= 0, orden.signo.to_numpy()[np.clip(k, 0, None)], 0)
            previo_dias = np.where(k >= 0, orden.dias.to_numpy()[np.clip(k, 0, None)], 0)
            previo_est = np.where(k >= 0, orden.estacion.to_numpy()[np.clip(k, 0, None)], '')
            tramo = np.where(dias <= DIAS_MAX, dias, DIAS_MAX + 1)
            # Columnas de vecinas del examen (regla) y entradas relativas (LSTM), recalculadas sin aprender.
            col_x = ev.columnas_vecinas(ev.con_historia(historia, x), sigma, vec).iloc[len(historia):]
            rec = col_x.abs().fillna(0.0).max(axis=1)
            control.append(dict(delta_pct=d, corrida=corrida, dif_max_regla=float(
                (rec - por_det['Regla de vecinas'][0][0][corrida]).abs().max())))
            est_regla, est_regla_limpia = col_x.abs().fillna(0.0).idxmax(axis=1), col_limpia.abs().fillna(0.0).idxmax(axis=1)
            if d == 100:
                rel_x = ev.relativas(ev.con_historia(historia, x)).iloc[len(historia):] / sigma
                for j, e in orden.iterrows():
                    for dia in range(DIAS_MAX + 1):
                        t0 = e.fin + pd.Timedelta(hours=1 + 24 * dia)
                        h = pd.date_range(t0, periods=24, freq='h').intersection(x.index)
                        if len(h) == 0:
                            continue
                        mecanismo.append(dict(corrida=corrida, estacion=e.estacion, signo=e.signo, dia=dia,
                                              relativa_examen=rel_x.loc[h, e.estacion].mean(),
                                              relativa_limpia=rel_limpia.loc[h, e.estacion].mean(),
                                              vecinas_examen=col_x.loc[h, e.estacion].mean(),
                                              vecinas_limpia=col_limpia.loc[h, e.estacion].mean()))
            for n, ((s, est_v4), u) in por_det.items():
                for nivel in NIVELES:
                    a = (s.loc[x.index, corrida] > u[nivel][corrida]).to_numpy()
                    al = (s.loc[x.index, 'limpia_2024'] > u[nivel][corrida]).to_numpy()
                    base = dict(detector=n, delta_pct=d, nivel_fa_pct=int(nivel), corrida=corrida)
                    g = pd.DataFrame(dict(dia=tramo[normal], examen=a[normal], limpio=al[normal])).groupby('dia')
                    decaimiento.append(pd.DataFrame(dict(**base, dia=g.size().index, horas=g.size().to_numpy(),
                                                         alertan=g.examen.sum().to_numpy(), alertan_limpio=g.limpio.sum().to_numpy())))
                    dentro = normal & (dias < VENTANA_TRAS)
                    for signo in (1, -1):
                        for dur in ((1, 2), (3, 4), (5, 7)):
                            msk = dentro & (previo_signo == signo) & (previo_dias >= dur[0]) & (previo_dias <= dur[1])
                            previo.append(dict(**base, signo=signo, duracion=f'{dur[0]}–{dur[1]} días', horas=int(msk.sum()),
                                               alertan=int(a[msk].sum()), alertan_limpio=int(al[msk].sum())))
                    if n in ('Regla de vecinas', 'V4'):
                        if n == 'V4':
                            ex, li = est_v4.loc[x.index, corrida].to_numpy(), est_v4.loc[x.index, 'limpia_2024'].to_numpy()
                        else:
                            ex, li = est_regla.to_numpy(), est_regla_limpia.to_numpy()
                        fa_ex, fa_li = dentro & a, dentro & al
                        estacion.append(dict(**base, falsas_alarmas=int(fa_ex.sum()),
                                             de_la_atacada=int((ex[fa_ex] == previo_est[fa_ex]).sum()),
                                             falsas_alarmas_limpio=int(fa_li.sum()),
                                             de_la_atacada_limpio=int((li[fa_li] == previo_est[fa_li]).sum())))
                    for version, alerta in (('examen', a), ('sin ataque', al)):
                        fuera = normal & (dias < VENTANA_TRAS)
                        sin_ventana.append(dict(**base, version=version, horas_excluidas=int(fuera.sum()),
                                                **tabla_metricas(y[~fuera], alerta[~fuera])))
            print(f'δ = {d} %, {corrida} listo', flush=True)

    control = pd.DataFrame(control)
    print(f'\nControl: la regla recalculada coincide con su puntaje guardado (diferencia máxima '
          f'{control.dif_max_regla.max():.1e}; los puntajes se guardan con 6 cifras)')
    dec = pd.concat(decaimiento, ignore_index=True).groupby(['detector', 'delta_pct', 'nivel_fa_pct', 'dia'])[
        ['horas', 'alertan', 'alertan_limpio']].sum().reset_index()
    dec['fa_examen_pct'], dec['fa_limpio_pct'] = 100 * dec.alertan / dec.horas, 100 * dec.alertan_limpio / dec.horas
    dec['exceso'] = dec.fa_examen_pct - dec.fa_limpio_pct
    dec.to_csv(OUT / 'falsas_alarmas_por_dia.csv', index=False)
    print('\nA. Falsas alarmas de más (examen − limpio, puntos) según los días desde el fin del último ataque; '
          f'{DIAS_MAX + 1} = más de {DIAS_MAX} días o ninguno')
    for k in (1, 5):
        t = dec[dec.nivel_fa_pct == k].pivot_table(index='dia', columns=['delta_pct', 'detector'], values='exceso')
        print(f'\nnivel {k} %'); print(t[[(dd, n) for dd in DELTAS for n in DETECTORES]].round(1).to_string())

    pre = pd.DataFrame(previo).groupby(['detector', 'delta_pct', 'nivel_fa_pct', 'signo', 'duracion'])[
        ['horas', 'alertan', 'alertan_limpio']].sum().reset_index()
    pre['exceso'] = 100 * (pre.alertan - pre.alertan_limpio) / pre.horas
    pre.to_csv(OUT / 'falsas_alarmas_por_ataque_previo.csv', index=False)
    print(f'\nB. Exceso de falsas alarmas en los {VENTANA_TRAS} días tras un ataque, según el ataque anterior (puntos)')
    for k in (1, 5):
        t = pre[pre.nivel_fa_pct == k].pivot_table(index=['delta_pct', 'signo', 'duracion'], columns='detector', values='exceso')
        print(f'\nnivel {k} %'); print(t[list(DETECTORES)].round(1).to_string())

    est = pd.DataFrame(estacion).groupby(['detector', 'delta_pct', 'nivel_fa_pct'])[
        ['falsas_alarmas', 'de_la_atacada', 'falsas_alarmas_limpio', 'de_la_atacada_limpio']].sum().reset_index()
    est['de_la_atacada_pct'] = 100 * est.de_la_atacada / est.falsas_alarmas
    est['de_la_atacada_limpio_pct'] = 100 * est.de_la_atacada_limpio / est.falsas_alarmas_limpio
    est.to_csv(OUT / 'falsas_alarmas_estacion.csv', index=False)
    print(f'\nC. De las falsas alarmas en los {VENTANA_TRAS} días tras un ataque, % disparadas por la estación atacada')
    print(est.round(1).to_string(index=False))

    mec = pd.DataFrame(mecanismo).groupby(['signo', 'dia'])[['relativa_examen', 'relativa_limpia', 'vecinas_examen', 'vecinas_limpia']].mean()
    mec['relativa_cambio'] = mec.relativa_examen - mec.relativa_limpia
    mec['vecinas_cambio'] = mec.vecinas_examen - mec.vecinas_limpia
    mec.reset_index().to_csv(OUT / 'falsas_alarmas_mecanismo_d100.csv', index=False)
    print('\n   Estación atacada tras el ataque (δ = 100 %): cambio medio de su entrada relativa (desviaciones típicas)'
          ' y de su columna de vecinas, examen − limpio')
    print(mec[['relativa_cambio', 'vecinas_cambio']].unstack('signo').round(2).to_string())

    sv = pd.DataFrame(sin_ventana).groupby(['detector', 'delta_pct', 'nivel_fa_pct', 'version'])[
        ['tp', 'fp', 'fn', 'tn', 'horas_excluidas']].sum().reset_index()
    for c, v in [('precision', lambda r: r.tp / (r.tp + r.fp)), ('recall', lambda r: r.tp / (r.tp + r.fn)),
                 ('falsas_alarmas', lambda r: r.fp / (r.fp + r.tn))]:
        sv[c] = sv.apply(v, axis=1)
    sv['f1'] = 2 * sv.precision * sv.recall / (sv.precision + sv.recall)
    sv['f2'] = 5 * sv.precision * sv.recall / (4 * sv.precision + sv.recall)
    sv.to_csv(OUT / 'falsas_alarmas_sin_ventana.csv', index=False)
    print(f'\nE. Sin las horas normales de los {VENTANA_TRAS} días tras cada ataque (contraste): F1 examen (sin ataque)')
    for k in (1, 5):
        e = sv[(sv.nivel_fa_pct == k) & (sv.version == 'examen')].pivot(index='delta_pct', columns='detector', values='f1')
        z = sv[(sv.nivel_fa_pct == k) & (sv.version == 'sin ataque')].pivot(index='delta_pct', columns='detector', values='f1')
        fa = sv[(sv.nivel_fa_pct == k) & (sv.version == 'examen')].pivot(index='delta_pct', columns='detector', values='falsas_alarmas')
        print(f'\nnivel {k} %: F1')
        print((e.round(2).astype(str) + ' (' + z.round(2).astype(str) + ')')[list(DETECTORES)].sort_index(ascending=False).to_string())
        print(f'nivel {k} %: falsas alarmas en las horas normales que quedan (%)')
        print((100 * fa)[list(DETECTORES)].round(1).sort_index(ascending=False).to_string())

    # D. 2023 contra 2024 limpios.
    filas = []
    for n, ((s, _), u) in datos.items():
        for nivel in NIVELES:
            uu = u[nivel].iloc[0]
            for anio, colname in ((2023, 'limpia_2023'), (2024, 'limpia_2024')):
                a = s[colname].dropna() > uu
                for mes, v in a.groupby(a.index.month):
                    filas.append(dict(detector=n, nivel_fa_pct=int(nivel), anio=anio, mes=mes, alertan_pct=100 * v.mean()))
    mes = pd.DataFrame(filas)
    mes.to_csv(OUT / 'falsas_alarmas_por_mes.csv', index=False)
    print('\nD. Falsas alarmas por mes en 2023 y 2024 limpios (nivel 5 %; umbral de δ = 100 % en los supervisados)')
    t = mes[mes.nivel_fa_pct == 5].pivot_table(index='mes', columns=['detector', 'anio'], values='alertan_pct')
    print(t.round(1).to_string())
    ctx = []
    for anio, m_ in ((2023, cal), (2024, limpia)):
        est_ = ev.estaciones_de(m_)
        v = m_[[f'{s_}_valor' for s_ in est_]]
        msk = m_[[f'{s_}_mascara' for s_ in est_]].to_numpy(bool)
        for mm in range(1, 13):
            sel = m_.index.month == mm
            ctx.append(dict(anio=anio, mes=mm, ozono_medio_ppb=float(np.nanmean(v.to_numpy(float)[sel])),
                            ozono_max_diario_medio_ppb=float(v[sel].max(axis=1).resample('D').max().mean()),
                            cobertura_pct=100 * float(msk[sel].mean())))
    ctx = pd.DataFrame(ctx)
    ctx.to_csv(OUT / 'contexto_2023_2024.csv', index=False)
    print('\n   Contexto: ozono medio, máximo diario medio de la red y cobertura de datos')
    print(ctx.pivot(index='mes', columns='anio').round(1).to_string())
    cob = por_cobertura()
    print('\n   Horas limpias con alarma según cuántas estaciones tienen dato (nivel 5 %, umbral de δ = 100 %)')
    print(cob[cob.nivel == '5'].pivot_table(index=['anio', 'estaciones_con_dato'], columns='detector',
                                            values='alertan_pct', observed=False).round(1).to_string())


if __name__ == '__main__':
    main()
