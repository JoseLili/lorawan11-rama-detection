"""F1 según δ: el LSTM supervisado con vecinas (revisión 8) contra el V4 no supervisado (gráfica de la semana).

Uso (desde la raíz del repo, con la revisión 8 bajada):

    .venv/bin/python experiments/anomalias_red/graficar_f1_delta.py

Métrica principal de la revisión 9: F1 por hora de red con 1 % de falsas alarmas (umbral fijado
con 2023 limpio), en el examen 2024 con los 10 calendarios juntos.
- una línea por detector: su F1 con el ataque;
- zona gris: el mayor de los dos F1 «sin ataque» (mismas horas de 2024 sin alterar, mismo umbral), lo que
  saldría por pura coincidencia.
El rango entre los 10 calendarios se calcula y se imprime, pero no se dibuja (versión simplificada).
El LSTM es el modelo oficial de cada δ (recién entrenado en Colab); el V4, el de la parte 1 cargado de
disco y calculado en la lap. No entrena ni carga modelos: lee puntajes, umbrales y etiquetas.
La ficha está en docs/fichas_graficas.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib  # noqa: E402

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import graficar_curva_delta as gc  # noqa: E402
from metricas_estandar_revision8 import SAL, con_umbral, etiquetas, puntajes  # noqa: E402

FIG = gc.RAIZ / 'docs/img/anomalias_red_v1/f1_por_delta.png'
NIVEL = '1'
# Paleta validada (skill dataviz, fondo blanco): el V4 conserva el naranja de las gráficas anteriores;
# el LSTM con vecinas es un detector nuevo y toma el violeta (el azul era el LSTM sin vecinas).
DETECTORES = [('lstm_sup_vecinas_a14_20cal', 'LSTM con vecinas\n(supervisado)', '#6250d6', 'o'),
              ('v4', 'V4\n(no supervisado)', '#eb6834', 's')]


def f1_por_delta() -> pd.DataFrame:
    filas = []
    for d in gc.DELTAS:
        y_por = None
        for carpeta, nombre, _, _ in DETECTORES:
            c = SAL / carpeta / f'd{d}'
            s = puntajes(c)
            m = pd.read_csv(c / 'metricas.csv')
            col = 'nivel' if 'nivel' in m else 'nivel_fa_pct'
            u = m[m[col].astype(str) == NIVEL].set_index('corrida').umbral
            corridas = sorted(u.index)
            y_por = y_por or etiquetas(d, corridas)
            ex = {r: (s.loc[y_por[r].index, r] > u[r]).to_numpy() for r in corridas}
            li = {r: (s.loc[y_por[r].index, 'limpia_2024'] > u[r]).to_numpy() for r in corridas}
            y = np.concatenate([y_por[r].to_numpy() for r in corridas])
            por_cal = [con_umbral(y_por[r].to_numpy(), ex[r])['f1'] for r in corridas]
            filas.append(dict(carpeta=carpeta, detector=nombre, delta_pct=d,
                              f1=con_umbral(y, np.concatenate([ex[r] for r in corridas]))['f1'],
                              f1_sin_ataque=con_umbral(y, np.concatenate([li[r] for r in corridas]))['f1'],
                              f1_min_calendario=min(por_cal), f1_max_calendario=max(por_cal)))
    return pd.DataFrame(filas)


def graficar(t: pd.DataFrame):
    plt.rcParams.update({'font.size': 11, 'axes.edgecolor': gc.BASE, 'axes.labelcolor': gc.TINTA_2,
                         'xtick.color': gc.TINTA_2, 'ytick.color': gc.TINTA_2, 'text.color': gc.TINTA})
    fig, eje = plt.subplots(figsize=(9, 5.4), facecolor='white')
    x = np.arange(len(gc.DELTAS))
    azar = t.groupby('delta_pct').f1_sin_ataque.max().loc[list(gc.DELTAS)]
    eje.fill_between(x, 0, azar, color=gc.REJILLA, alpha=0.9, lw=0, zorder=1)
    eje.text(3.5, 0.012, 'zona de azar', fontsize=10, color=gc.TINTA_2, ha='center')
    for (carpeta, nombre, color, marca), arriba in zip(DETECTORES, (True, False)):
        s = t[t.carpeta == carpeta].set_index('delta_pct').loc[list(gc.DELTAS)]
        eje.plot(x, s.f1, color=color, lw=2.4, marker=marca, ms=8, mec='white', mew=1, zorder=3)
        for i in (3, 4):                                       # el valor sólo donde hay detección
            eje.annotate(f'{s.f1.iat[i]:.2f}', (x[i], s.f1.iat[i]), xytext=(-10, 9) if arriba else (0, -19),
                         textcoords='offset points', ha='right' if arriba else 'center', fontsize=10, color=gc.TINTA_2)
        eje.annotate(nombre, (x[-1], s.f1.iat[-1]), xytext=(14, 0), textcoords='offset points', va='center',
                     fontsize=11, color=color, fontweight='bold')
    eje.grid(axis='y', color=gc.REJILLA, lw=0.6)
    eje.set_axisbelow(True)
    for lado in ('top', 'right'):
        eje.spines[lado].set_visible(False)
    eje.set_xticks(x, [f'{d} %' for d in gc.DELTAS])
    eje.set_xlim(-0.3, len(gc.DELTAS) - 0.3)
    eje.set_ylim(0, 0.5)
    eje.set_xlabel('Tamaño del ataque (δ)')
    eje.set_ylabel('F1   (0 = no detecta · 1 = perfecto)')
    fig.suptitle('Con ataques grandes, el LSTM con vecinas casi duplica el F1 del V4;\n'
                 'con ataques chicos, ninguno detecta de forma útil', fontsize=13, x=0.08, ha='left', y=0.97,
                 linespacing=1.3)
    fig.text(0.08, 0.86, 'Examen 2024 · 1 % de falsas alarmas · zona gris: lo que saldría por pura coincidencia\n'
             'El LSTM se entrenó con ataques de este tipo; el V4 nunca vio ataques', fontsize=10, color=gc.TINTA_2,
             va='top', linespacing=1.5)
    fig.subplots_adjust(left=0.1, right=0.79, bottom=0.13, top=0.76)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=200, facecolor='white')


def main():
    t = f1_por_delta()
    graficar(t)
    print(f'Escrito {FIG.relative_to(gc.RAIZ)}\n')
    print(t.drop(columns='carpeta').round(3).to_string(index=False))
    e = pd.read_csv(SAL / 'analisis_revision8/metricas_estandar.csv')
    e = e[(e.nivel_fa_pct == int(NIVEL)) & e.detector.isin(['LSTM con vecinas', 'V4'])]
    print('\nControl frente a metricas_estandar.csv (F1 con ataque y sin ataque):')
    print(e.pivot_table(index=['detector', 'delta_pct'], columns='version', values='f1').round(3).to_string())


if __name__ == '__main__':
    main()
