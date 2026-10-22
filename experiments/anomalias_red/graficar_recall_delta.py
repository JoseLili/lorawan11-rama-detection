"""Recall por hora según δ, con el azar a la vista: la gráfica de la curva por δ rehecha para explicarse sola.

Uso (desde la raíz del repo, con los detectores corridos en los cinco δ):

    .venv/bin/python experiments/anomalias_red/graficar_recall_delta.py

Sustituye, para presentar, a deteccion_por_delta.png (que se conserva). Muestra sólo el LSTM
supervisado (revisión 7) y el V4, al nivel de 5 % de falsas alarmas por hora de red:
- línea sólida: recall por hora = % de horas alteradas del examen 2024 que dan alerta;
- línea punteada: % de esas mismas horas que dan alerta sin alterar (2024 limpio, mismo umbral);
- barras: rango del recall entre los 10 calendarios del examen.
La ficha está en docs/fichas_graficas.md. No entrena ni carga modelos: lee los CSV de resultados y,
para el eje, las matrices del examen. Imprime la tabla de la ficha con los cuatro detectores.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graficar_curva_delta as gc  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

FIG = gc.RAIZ / 'docs/img/anomalias_red_v1/recall_por_delta.png'
EN_GRAFICA = ['lstm_sup_relativas_20cal', 'v4']


def recall_por_corrida() -> pd.DataFrame:
    """Recall y azar por hora, agregados y por calendario, para los cuatro detectores y los dos niveles."""
    filas = []
    for carpeta, nombre, _, _ in gc.DETECTORES:
        for d in gc.DELTAS:
            t = pd.read_csv(gc.SAL / carpeta / f'd{d}/por_tamano.csv')
            for k in gc.NIVELES:
                tk = gc.del_nivel(t, k)
                g = tk[tk.tramo_ppb != 'sin cambio'].groupby('corrida')[['horas', 'alertan', 'alertan_azar']].sum()
                rc = 100 * g.alertan / g.horas
                filas.append(dict(carpeta=carpeta, detector=nombre, delta_pct=d, nivel_fa_pct=int(k),
                                  recall_pct=100 * g.alertan.sum() / g.horas.sum(),
                                  azar_pct=100 * g.alertan_azar.sum() / g.horas.sum(),
                                  recall_min_corrida=rc.min(), recall_max_corrida=rc.max()))
    return pd.DataFrame(filas)


def graficar(tabla: pd.DataFrame, medianas: dict[int, float]):
    plt.rcParams.update({'font.size': 10, 'axes.edgecolor': gc.BASE, 'axes.labelcolor': gc.TINTA_2,
                         'xtick.color': gc.TINTA_2, 'ytick.color': gc.TINTA_2, 'text.color': gc.TINTA})
    fig, eje = plt.subplots(figsize=(9, 5.8), facecolor='white')
    x = np.arange(len(gc.DELTAS))
    estilo = {c: (n, col, m) for c, n, col, m in gc.DETECTORES}
    for carpeta, dx in zip(EN_GRAFICA, (-0.07, 0.07)):
        nombre, color, marca = estilo[carpeta]
        s = tabla[(tabla.carpeta == carpeta) & (tabla.nivel_fa_pct == 5)].set_index('delta_pct').loc[list(gc.DELTAS)]
        eje.vlines(x + dx, s.recall_min_corrida, s.recall_max_corrida, color=color, lw=1.3, alpha=0.4, zorder=1)
        eje.plot(x + dx, s.recall_pct, color=color, lw=2, marker=marca, ms=7, mec='white', mew=1, zorder=3,
                 label=f'{nombre}: horas alteradas que alertan')
        eje.plot(x + dx, s.azar_pct, color=color, lw=1.6, ls=(0, (4, 3)), zorder=2,
                 label=f'{nombre}: las mismas horas sin alterar (azar)')
    # Cómo se lee el hueco, con el LSTM supervisado en δ = 100 %.
    s = tabla[(tabla.carpeta == EN_GRAFICA[0]) & (tabla.nivel_fa_pct == 5) & (tabla.delta_pct == 100)].iloc[0]
    xb = x[-1] + 0.24
    eje.annotate('', xy=(xb, s.recall_pct), xytext=(xb, s.azar_pct),
                 arrowprops=dict(arrowstyle='<->', color=gc.TINTA_2, lw=1, shrinkA=0, shrinkB=0))
    eje.text(xb + 0.07, (s.recall_pct + s.azar_pct) / 2,
             f'{s.recall_pct:.1f} % − {s.azar_pct:.1f} %\n= {s.recall_pct - s.azar_pct:.0f} puntos\nque aporta\nla alteración',
             va='center', fontsize=9, color=gc.TINTA_2)
    eje.text(1.0, 19, 'Con δ de 20 % o menos, cada línea sólida queda encima\nde su punteada: el detector alerta '
             'lo mismo que sin alterar', ha='center', va='center', fontsize=9, color=gc.TINTA_2)
    eje.grid(axis='y', color=gc.REJILLA, lw=0.6)
    eje.set_axisbelow(True)
    for lado in ('top', 'right'):
        eje.spines[lado].set_visible(False)
    eje.set_xticks(x, [f'{d} %\n{medianas[d]:.0f} ppb' for d in gc.DELTAS])
    eje.set_xlim(-0.4, len(gc.DELTAS) + 0.35)
    eje.set_ylim(0, None)
    eje.set_xlabel('δ: cuánto se multiplica (o divide) la lectura · debajo, el cambio típico en ppb')
    eje.set_ylabel('Recall por hora (%)')
    eje.legend(loc='upper left', frameon=False, fontsize=9)
    fig.suptitle('¿Cuántas horas alteradas detecta cada detector?', fontsize=13, x=0.08, ha='left', y=0.975)
    fig.text(0.08, 0.915, 'Recall por hora con 5 % de falsas alarmas por hora de red · examen 2024 · '
             'barras: rango entre los 10 calendarios\nV4 cargado de disco; LSTM supervisado (revisión 7) '
             'recién entrenado', fontsize=9, color=gc.TINTA_2, va='top', linespacing=1.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=200, facecolor='white')


def main():
    tabla = recall_por_corrida()
    graficar(tabla, gc.mediana_cambio())
    print(f'Escrito {FIG.relative_to(gc.RAIZ)}\n')
    for k in (5, 1):
        print(f'Nivel {k} %: recall / azar (%)')
        t = tabla[tabla.nivel_fa_pct == k]
        print(t.assign(v=t.recall_pct.map('{:.1f}'.format) + ' / ' + t.azar_pct.map('{:.1f}'.format))
              .pivot(index='detector', columns='delta_pct', values='v').to_string(), '\n')
    s = tabla[(tabla.nivel_fa_pct == 5) & tabla.carpeta.isin(EN_GRAFICA)]
    print('Rango entre calendarios (5 %):\n', s[['detector', 'delta_pct', 'recall_min_corrida',
                                                 'recall_max_corrida']].round(1).to_string(index=False))


if __name__ == '__main__':
    main()
