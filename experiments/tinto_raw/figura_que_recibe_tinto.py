"""Figura explicativa: del archivo de la RAMA a la tabla que recibe TINTO y a la imagen 32 × 32.

Usa un día real (ACO, 7 de marzo de 2021, primera fila de la tabla de ajuste) y el mapa y la escala
congelados de la línea de noviembre. No ajusta TINTO ni entrena nada.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'results/tinto_raw_20261109'
OUT = ROOT / 'results/tinto_dataset_para_tintolib_20261124/que_recibe_tinto.png'
EST, DIA = 'ACO', '2021-03-07'
INK, MUTED, ACCENT = '#2b2a27', '#7a786f', '#eb6834'

raw = pd.read_csv(R / 'auditoria1/o3_raw_ppb.csv', index_col=0, parse_dates=True)
dia = raw.loc[DIA]
valores = dia[EST].to_numpy()
assert np.isfinite(valores).all()
mapa = pd.read_csv(R / 'representacion1/completos_32_mapa.csv')
escala = pd.read_csv(R / 'representacion1/completos_escala.csv')
fila_tabla = pd.read_csv(ROOT / 'results/tinto_dataset_para_tintolib_20261124/ajuste_mapa_2020_2021.csv', nrows=1)
assert np.array_equal(fila_tabla.iloc[0, :24].to_numpy(float), valores)   # es la fila 1 que recibió TINTO
esc = valores * escala.scale.to_numpy() + escala.offset.to_numpy()
rc = mapa[['row', 'column']].to_numpy(int)
img = np.zeros((32, 32))
img[rc[:, 0], rc[:, 1]] = esc

fig = plt.figure(figsize=(17, 6.6))
gs = fig.add_gridspec(1, 5, width_ratios=[1.25, 0.75, 1.1, 0.42, 1.1], wspace=0.1)

# 1. Archivo de la RAMA: filas = horas, columnas = estaciones, −99 = sin medición.
ax = fig.add_subplot(gs[0])
ax.axis('off')
cols = ['FECHA', 'HORA', 'ACO', 'AJM', 'AJU', 'ATI', 'BJU', '…']
filas = []
for h in [0, 1, 2, 3, 4, None, 23]:
    if h is None:
        filas.append(['⋮'] * len(cols))
        continue
    r = dia.iloc[h]
    v = ['-99' if np.isnan(r[s]) else f'{r[s]:.0f}' for s in ['ACO', 'AJM', 'AJU', 'ATI', 'BJU']]
    filas.append(['7-mar-21', str(h + 1)] + v + ['…'])
t = ax.table(cellText=filas, colLabels=cols, loc='center', cellLoc='center',
             colWidths=[.19, .11, .11, .11, .11, .11, .11, .08])
t.auto_set_font_size(False)
t.set_fontsize(9.5)
t.scale(1, 1.6)
for (i, j), c in t.get_celld().items():
    c.set_edgecolor('#d6d4cc')
    if j == 2:
        c.set_facecolor('#fde3d6')
    if i == 0:
        c.set_text_props(weight='bold')
ax.set_title('1. Así viene de la RAMA (2021O3.xls)\nuna fila por HORA, una columna por estación (36)',
             fontsize=11, color=INK, loc='left')
ax.text(0, 0.02, '−99 = sin medición. Aquí un día de ACO es una COLUMNA de 24 filas.\nEsta tabla NO se le da a TINTO: primero se reacomoda.',
        transform=ax.transAxes, fontsize=9, color=MUTED)

ax = fig.add_subplot(gs[1])
ax.axis('off')
ax.annotate('', xy=(.42, .5), xytext=(.03, .5), arrowprops=dict(arrowstyle='-|>', lw=2, color=MUTED))
ax.text(.22, .56, 'cada día de\ncada estación\nse vuelve\nUNA fila', ha='center', fontsize=9, color=MUTED)

# 2. La tabla que recibe TINTO: una fila por estación-día, una columna por hora.
ax = fig.add_subplot(gs[2])
ax.axis('off')
tabla = pd.read_csv(ROOT / 'results/tinto_dataset_para_tintolib_20261124/ajuste_mapa_2020_2021.csv')
meta = pd.read_csv(ROOT / 'results/tinto_dataset_para_tintolib_20261124/ajuste_mapa_2020_2021_metadatos.csv')
horas = [0, 1, 2, None, 11, None, 23]
cols2 = ['…' if k is None else f'h{k:02}' for k in horas]
sac = int(meta.index[meta.estacion == 'SAC'][0])
filas2, etiquetas = [], []
for i in [0, 1, 2, None, sac, None, len(tabla) - 1]:
    if i is None:
        filas2.append(['⋮'] * len(cols2))
        etiquetas.append('⋮')
        continue
    filas2.append(['…' if k is None else f'{tabla.iloc[i, k]:.0f}' for k in horas])
    etiquetas.append(f'{meta.estacion[i]} {pd.Timestamp(meta.fecha[i]):%d-%m-%y}')
t = ax.table(cellText=filas2, colLabels=cols2, rowLabels=etiquetas, loc='center', cellLoc='center',
             colWidths=[.1] * len(cols2))
t.auto_set_font_size(False)
t.set_fontsize(9.5)
t.scale(1, 1.6)
for (i, j), c in t.get_celld().items():
    c.set_edgecolor('#d6d4cc')
    if j == -1:                      # estación y fecha: solo para identificar la fila, no entran
        c.set_text_props(color=MUTED, style='italic')
        c.set_edgecolor('none')
    if i == 1 and j >= 0:
        c.set_facecolor('#fde3d6')
    if i == 0:
        c.set_text_props(weight='bold')
ax.set_title('2. Esta es la tabla que recibe TINTO\nuna fila por ESTACIÓN-DÍA, una columna por HORA',
             fontsize=11, color=INK, loc='left')
ax.text(0, 0.02, 'Regla de TINTO en ESTA tabla: cada fila → una imagen;\n'
        'cada columna (h00 … h23) → un píxel fijo. 12 146 filas × 24 columnas.\n'
        'Estación y fecha (en gris) solo identifican la fila: no entran.',
        transform=ax.transAxes, fontsize=9, color=MUTED)

ax = fig.add_subplot(gs[3])
ax.axis('off')
ax.annotate('', xy=(.62, .5), xytext=(.05, .5), arrowprops=dict(arrowstyle='-|>', lw=2, color=MUTED))
ax.text(.33, .56, 'TINTO toma\nla fila\nresaltada', ha='center', fontsize=9, color=MUTED)

# 3. La imagen 32 × 32: cada hora en su píxel fijo; el resto en cero.
ax = fig.add_subplot(gs[4])
cmap = plt.get_cmap('viridis').copy()
cmap.set_bad('#ecebe6')
im = ax.imshow(np.ma.masked_equal(img, 0), cmap=cmap, vmin=0, vmax=1, interpolation='nearest')
ax.plot(rc[:, 1], rc[:, 0], color='#7a786f', lw=.8, ls='--', zorder=1)   # orden de las horas
for k, (r_, c_) in enumerate(rc):
    if k % 3 == 0:
        ax.annotate(f'h{k:02}', (c_, r_), textcoords='offset points', xytext=(7, 0), fontsize=8,
                    color=INK, va='center')
ax.set_xlabel('Columna del píxel')
ax.set_ylabel('Fila del píxel')
fig.colorbar(im, ax=ax, fraction=.046, pad=.03, label='Ozono escalado (0–1, por hora)')
ax.set_title('3. La imagen de la fila resaltada (ACO, 07-03-21)\n24 columnas → 24 píxeles; gris = píxeles vacíos',
             fontsize=11, color=INK, loc='left')
ax.text(0, -0.2, 'La línea punteada une h00→h23: PCA acomodó las horas\nen un anillo que sigue el ciclo del día.',
        transform=ax.transAxes, fontsize=9, color=MUTED, va='top')

fig.savefig(OUT, dpi=150, bbox_inches='tight')
print(OUT)
