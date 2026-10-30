"""TINTO T2: una gráfica, F1 con 1 % de falsas alarmas por δ, L0 contra las cuatro imágenes."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / 'results/exploracion_tinto_2022/t2_granularidad/evaluacion'
DET = [('L0', 'L0 (LSTM, referencia)', '#55534e'),
       ('EH_c1', 'TINTO estación-hora (T1 reentrenado)', '#2a78d6'),
       ('ED_c1', 'TINTO estación-día', '#eb6834'),
       ('RH_c1', 'TINTO red-hora', '#1baf7a'),
       ('RD_c1', 'TINTO red-día', '#eda100')]
DELTAS = [100, 50, 20]

r = pd.read_csv(EV / 'resultados.csv')
r = r[(r.version == 'con_ataque') & (r.punto == 'p99')].set_index(['detector', 'delta_pct'])
sin = pd.read_csv(EV / 'resultados.csv')
sin = sin[(sin.version == 'sin_ataque') & (sin.punto == 'p99')].groupby('detector').f1.max()

fig, ax = plt.subplots(figsize=(9, 5), layout='constrained')
w, gap = 0.16, 0.012
x = np.arange(len(DELTAS))
for k, (d, nombre, color) in enumerate(DET):
    v = [r.loc[(d, delta), 'f1'] for delta in DELTAS]
    bars = ax.bar(x + (k - 2) * w, v, w - gap, color=color, label=nombre, zorder=2)
    if d in ('L0', 'ED_c1'):   # solo la referencia y la mejor variante llevan número
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.008, f'{val:.2f}', ha='center', va='bottom',
                    fontsize=8, color='#2b2a27')
ax.axhline(sin.max(), color='#8a887f', lw=1, ls=':', zorder=1,
           label=f'F1 sin ataque, el mayor de los cinco ({sin.max():.3f})')
ax.set_xticks(x, [f'δ = {d} %' for d in DELTAS])
ax.set_xlabel('Intensidad de la alteración (δ) en los 10 calendarios de 2022')
ax.set_ylabel('F1 por estación-día (umbral con 1 % de falsas alarmas)')
ax.set_ylim(0, 0.55)
ax.grid(axis='y', color='#e4e3dd', lw=0.8, zorder=0)
for s in ['top', 'right']:
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, fontsize=8.5, loc='upper right')
ax.set_title('Ninguna forma de imagen TINTO le gana a L0 en 2022\n'
             'promedio de los tres δ: L0 0.355 · estación-día 0.322 · estación-hora 0.315 · red-hora 0.157 · red-día 0.035',
             fontsize=10.5, loc='left')
fig.savefig(EV / 'f1_p99_granularidad.png', dpi=160)
print(EV / 'f1_p99_granularidad.png')
