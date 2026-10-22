"""Detección por hora según δ, la gráfica análoga a la detección por bit de la parte 1 (§11).

Uso (desde la raíz del repo, con los cuatro detectores corridos en los cinco δ):

    .venv/bin/python experiments/anomalias_red/graficar_curva_delta.py

La señal es el % de horas alteradas que alertan menos el % de esas mismas horas que alertan sin
alterar (2024 limpio, mismo detector y umbral): el azar por tramo de la revisión 4 sumado sobre
todas las horas alteradas (nota del 2026-10-18 en progreso.md). Las barras son el rango entre
las 10 corridas del examen. No entrena ni carga modelos: lee los CSV de resultados y, para el
eje, las matrices del examen.

Salidas: docs/img/anomalias_red_v1/deteccion_por_delta.png y results/anomalias_red_v1/
curva_delta.csv (la misma información en tabla, con la detección por episodio).
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.detect import anomalias_red as ar  # noqa: E402
from src.detect import evaluacion_red as ev  # noqa: E402

SAL = RAIZ / 'results/anomalias_red_v1'
FIG = RAIZ / 'docs/img/anomalias_red_v1/deteccion_por_delta.png'
DELTAS = (5, 10, 20, 50, 100)
NIVELES = ('5', '1')
# Paleta categórica validada (skill dataviz, todos los pares, fondo blanco); el IsolationForest,
# que queda en el azar, va en gris.
DETECTORES = [
    ('lstm_sup_relativas_20cal', 'LSTM supervisado', '#2a78d6', 'o'),
    ('v4', 'V4 (no supervisado)', '#eb6834', 's'),
    ('rf_relativas_20cal', 'Random Forest', '#1baf7a', '^'),
    ('if', 'IsolationForest', '#898781', 'D'),
]
TINTA, TINTA_2, TENUE, REJILLA, BASE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'


def del_nivel(df: pd.DataFrame, nivel: str) -> pd.DataFrame:
    columna = 'nivel' if 'nivel' in df else 'nivel_fa_pct'         # el V4 tiene también 'p95'
    return df[df[columna].astype(str) == nivel]


def curva() -> pd.DataFrame:
    filas = []
    for carpeta, nombre, _, _ in DETECTORES:
        for d in DELTAS:
            t = pd.read_csv(SAL / carpeta / f'd{d}/por_tamano.csv')
            e = pd.read_csv(SAL / carpeta / f'd{d}/episodios.csv')
            for k in NIVELES:
                tk = del_nivel(t, k)
                tk = tk[tk.tramo_ppb != 'sin cambio']               # = las horas con etiqueta 1
                g = tk.groupby('corrida')[['horas', 'alertan', 'alertan_azar']].sum()
                senal = 100 * (g.alertan - g.alertan_azar) / g.horas
                ek = del_nivel(e, k)
                filas.append(dict(
                    detector=nombre, carpeta=carpeta, delta_pct=d, nivel_fa_pct=int(k),
                    horas_alteradas=int(g.horas.sum()),
                    deteccion_hora_pct=100 * g.alertan.sum() / g.horas.sum(),
                    azar_hora_pct=100 * g.alertan_azar.sum() / g.horas.sum(),
                    senal_hora_pts=100 * (g.alertan.sum() - g.alertan_azar.sum()) / g.horas.sum(),
                    senal_hora_min_corrida=senal.min(), senal_hora_max_corrida=senal.max(),
                    episodios=len(ek), deteccion_episodio_pct=100 * ek.detectado.mean(),
                    azar_episodio_pct=100 * ek.detectado_azar.mean()))
    return pd.DataFrame(filas)


def mediana_cambio() -> dict[int, float]:
    """Mediana del mayor cambio de la hora (ppb) en las horas alteradas del examen, por δ."""
    limpia = ar.leer_matriz(SAL / 'matrices/matriz_limpia_2024.csv.gz')
    out = {}
    for d in DELTAS:
        cambios = []
        for c in ar.corridas().iloc[1:].corrida:
            x = ar.leer_matriz(SAL / f'matrices/matriz_{c}_d{d}.csv.gz')
            cambios.append(ev.cambio_maximo(x, limpia)[x['anomalia_red'] == 1])
        out[d] = float(pd.concat(cambios).median())
    return out


def etiquetas_sin_choque(ys: list[float], separacion: float) -> list[float]:
    """Sube las etiquetas que quedarían encimadas, conservando su orden vertical."""
    orden = np.argsort(ys)
    pos = np.array(ys, dtype=float)
    for a, b in zip(orden, orden[1:]):
        pos[b] = max(pos[b], pos[a] + separacion)
    return list(pos)


def graficar(tabla: pd.DataFrame, medianas: dict[int, float]):
    plt.rcParams.update({'font.size': 10, 'axes.edgecolor': BASE, 'axes.labelcolor': TINTA_2,
                         'xtick.color': TINTA_2, 'ytick.color': TINTA_2, 'text.color': TINTA})
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.9), sharey=True, facecolor='white')
    x = np.arange(len(DELTAS))
    desplazar = np.linspace(-0.12, 0.12, len(DETECTORES))
    for eje, k in zip(ejes, NIVELES):
        finales = []
        for (carpeta, nombre, color, marca), dx in zip(DETECTORES, desplazar):
            s = tabla[(tabla.carpeta == carpeta) & (tabla.nivel_fa_pct == int(k))].set_index('delta_pct')
            s = s.loc[list(DELTAS)]
            eje.vlines(x + dx, s.senal_hora_min_corrida, s.senal_hora_max_corrida, color=color,
                       lw=1.4, alpha=0.45, zorder=2)
            eje.plot(x + dx, s.senal_hora_pts, color=color, lw=1.8, marker=marca, ms=6.5,
                     mec='white', mew=1, label=nombre, zorder=3)
            finales.append((s.senal_hora_pts.iat[-1], nombre, color))
        for y, (_, nombre, color) in zip(etiquetas_sin_choque([f[0] for f in finales], 2.2), finales):
            eje.plot([x[-1] + 0.3, x[-1] + 0.4], [y, y], color=color, lw=2, solid_capstyle='round')
            eje.annotate(nombre, (x[-1] + 0.47, y), va='center', fontsize=9, color=TINTA_2)
        eje.axhline(0, color=BASE, lw=1, zorder=1)
        eje.text(-0.66, -0.35, 'azar', fontsize=8.5, color=TENUE, va='top')
        eje.grid(axis='y', color=REJILLA, lw=0.6)
        eje.set_axisbelow(True)
        for lado in ('top', 'right'):
            eje.spines[lado].set_visible(False)
        eje.set_xticks(x, [f'{d} %\n{medianas[d]:.0f} ppb' for d in DELTAS])
        eje.set_xlim(-0.7, len(DELTAS) + 1.0)
        eje.set_xlabel('δ / mediana del cambio en las horas alteradas')
        eje.set_title(f'Nivel de {k} % de falsas alarmas por hora de red', fontsize=11, color=TINTA)
    ejes[0].set_ylabel('Señal (puntos)')
    ejes[0].set_ylim(-2, None)
    ejes[0].legend(loc='upper left', frameon=False, fontsize=9)
    fig.suptitle('Detección por hora según δ, examen 2024', fontsize=13, x=0.055, ha='left', y=0.975)
    fig.text(0.055, 0.905, 'Señal = % de horas alteradas que alertan menos % de esas mismas horas que '
             'alertan sin alterar (0 = azar).\nBarras: rango entre las 10 corridas del examen. V4 '
             'cargado de disco; LSTM supervisado, Random Forest e IsolationForest recién entrenados.',
             fontsize=9, color=TINTA_2, va='top', linespacing=1.5)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=200, facecolor='white')


def main():
    tabla = curva()
    medianas = mediana_cambio()
    tabla['mediana_cambio_ppb'] = tabla.delta_pct.map(medianas)
    tabla.to_csv(SAL / 'curva_delta.csv', index=False, float_format='%.4g')
    graficar(tabla, medianas)
    print(f'Escrito {FIG.relative_to(RAIZ)} y {(SAL / "curva_delta.csv").relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
