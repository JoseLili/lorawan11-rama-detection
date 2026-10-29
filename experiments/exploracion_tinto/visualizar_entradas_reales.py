"""Ilustra entradas reales del experimento sellado; no ajusta ni predice modelos."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

os.environ.setdefault('MPLCONFIGDIR', '/tmp/tinto-mpl')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from src.detect import evaluacion_red as ev, lstm_local as ll, anomalias_red as ar

BASE = ROOT/'results/exploracion_tinto_2022'
MAP = BASE/'prototipos_20261028/corrida1/L0_408/mapa_unico_32.csv'
SCALE = BASE/'hora_compacta_20261028/corrida1/L0_408/escalador.csv'
FROZEN = BASE/'auditoria_l0_20261028/corrida1/vecinas_y_escalas.json'


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    matrices = ROOT/'results/anomalias_red_v1/matrices'
    sources = [matrices/'matriz_limpia_2020_2022.csv.gz',
               matrices/'matriz_entrenamiento_01_d50.csv.gz', MAP, SCALE, FROZEN,
               ROOT/'results/anomalias_red_v1/planes/plan_entrenamiento_01.csv']
    clean, altered = [ar.leer_matriz(p) for p in sources[:2]]
    assert clean.index.equals(altered.index)
    assert clean.index.min().year == 2020 and clean.index.max().year == 2022
    frozen = json.loads(FROZEN.read_text())
    stations = ev.estaciones_de(clean)
    _, sigma = ev.normalizacion(clean)
    geo = pd.read_csv(ROOT/'results/inventario_multianual/estaciones_geografia.csv', index_col='station')
    neighbors = ev.vecinas_de(stations, geo)
    par = ev.ajustar_vecinas('a14', clean.loc['2020':'2021'], sigma, neighbors, 'media')
    assert par.vecinas == frozen['vecinas']
    plan = pd.read_csv(sources[-1], parse_dates=['inicio', 'fin'])
    # Selección ilustrativa fijada sin mirar puntajes: primer episodio 2022,
    # primera ventana de 24 h totalmente dentro con >=12 datos objetivo.
    episodes = plan[(plan.inicio.dt.year == 2022)&plan.estacion.isin(frozen['objetivos'])]
    chosen = None
    for _, ep in episodes.sort_values(['inicio', 'estacion', 'episodio']).iterrows():
        for end in pd.date_range(ep.inicio+pd.Timedelta(hours=23), ep.fin, freq='h'):
            ix = clean.index.get_loc(end)
            obs = clean.iloc[ix-23:ix+1][f'{ep.estacion}_mascara'].eq(1)
            if obs.sum() >= 12 and obs.iloc[-1]:
                chosen = ep, ix
                break
        if chosen is not None: break
    assert chosen is not None
    ep, ix = chosen
    target = ep.estacion
    local = [target]+par.vecinas[target]
    times = clean.index[ix-23:ix+1]
    vectors = []
    for matrix in [clean, altered]:
        F = ev.entradas_de('vecinas', matrix, None, sigma, par)
        vectors.append(ll.ventanas_locales(F, stations, par.vecinas, target, np.array([ix]))[0])
    mapping, scaler = pd.read_csv(MAP), pd.read_csv(SCALE)
    assert mapping.feature.tolist() == scaler.feature.tolist()
    rc = mapping[['row', 'column']].to_numpy(int)
    assert len(np.unique(rc, axis=0)) == 408
    scaled = [(x.reshape(408).astype(np.float64)*scaler.scale.to_numpy()+scaler.offset.to_numpy()).astype(np.float32) for x in vectors]
    images = []
    for name, x, v in zip(['limpia', 'alterada'], vectors, scaled):
        im = np.zeros((32, 32), np.float32)
        im[rc[:, 0], rc[:, 1]] = v
        np.testing.assert_array_equal(im[rc[:, 0], rc[:, 1]], v)
        np.save(out/f'entrada_{name}_24x17.npy', x)
        np.save(out/f'imagen_{name}_32x32.npy', im)
        images.append(im)
    diff = images[1]-images[0]
    np.save(out/'diferencia_32x32.npy', diff)
    table = mapping.copy()
    for name, x, v in zip(['limpia', 'alterada'], vectors, scaled):
        table[name+'_L0'] = x.reshape(408)
        table[name+'_pixel'] = v
    table['diferencia_pixel'] = scaled[1]-scaled[0]
    table.to_csv(out/'trazabilidad_408.csv', index=False)
    raw = pd.DataFrame(index=times)
    for station in local:
        for name, matrix in [('limpia', clean), ('alterada', altered)]:
            raw[f'{station}_{name}_ppb'] = matrix.loc[times, f'{station}_valor'].where(matrix.loc[times, f'{station}_mascara'].eq(1))
    raw.to_csv(out/'ventana_ozono_ppb.csv', index_label='hora')
    lo = min(0., float(min(x.min() for x in images)))
    hi = max(1., float(max(x.max() for x in images)))
    bound = max(float(np.abs(diff).max()), 1e-9)
    plt.rcParams.update({'font.size': 11, 'axes.titleweight': 'bold'})
    fig = plt.figure(figsize=(14, 8.6), layout='constrained')
    gs = fig.add_gridspec(2, 3, height_ratios=[.8, 1.3])
    ax = fig.add_subplot(gs[0, :])
    for station in local[1:]:
        ax.plot(range(24), raw[f'{station}_limpia_ppb'], lw=1.3, alpha=.65, label=f'{station} limpia')
    ax.plot(range(24), raw[f'{target}_limpia_ppb'], color='black', lw=2.3, label=f'{target} limpia')
    ax.plot(range(24), raw[f'{target}_alterada_ppb'], color='#c43030', lw=2.3, ls='--', label=f'{target} alterada')
    ax.set(xlabel='Posición dentro de la ventana de 24 horas', ylabel='Ozono observado (ppb)',
           title=f'{target} y sus cuatro vecinas · calendario 01 · δ = 50 % · signo {int(ep.signo):+d}')
    ax.set_xticks([0, 6, 12, 18, 23], [times[j].strftime('%d/%m %H h') for j in [0, 6, 12, 18, 23]])
    ax.legend(ncol=3, fontsize=9)
    for j, (im, title) in enumerate(zip(images+[diff], ['Entrada limpia', 'Entrada alterada', 'Cambio: alterada − limpia'])):
        ax = fig.add_subplot(gs[1, j])
        kwargs = dict(cmap='RdBu_r', vmin=-bound, vmax=bound) if j == 2 else dict(cmap='viridis', vmin=lo, vmax=hi)
        plotted = ax.imshow(im, interpolation='nearest', **kwargs)
        ax.set(title=title, xlabel='Columna del píxel', ylabel='Fila del píxel')
        ax.set_xticks([0, 8, 16, 24, 31]); ax.set_yticks([0, 8, 16, 24, 31])
        fig.colorbar(plotted, ax=ax, shrink=.8, label='Δ intensidad' if j == 2 else 'Intensidad escalada')
    fig.suptitle('Una imagen por estación y hora · TINTO-PCA + asignación única · 32 × 32', fontsize=15)
    fig.savefig(out/'01_comparacion_real.png', dpi=160)
    plt.close(fig)
    kinds = ['rel', 'mascara', 'vecinas', 'hora_sin', 'hora_cos']
    kind_image = np.full((32, 32), np.nan)
    lag_image = np.full((32, 32), np.nan)
    for _, row in mapping.iterrows():
        kind = next(k for k in kinds if row.feature.endswith('_'+k))
        kind_image[row.row, row.column] = kinds.index(kind)
        lag_image[row.row, row.column] = -int(row.feature[3:5])
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.4), layout='constrained')
    cm = ListedColormap(['#3288bd', '#e6ab02', '#d53e4f', '#66a61e', '#984ea3'])
    cm.set_bad('#eeeeee')
    im = axs[0].imshow(kind_image, cmap=cm, norm=BoundaryNorm(np.arange(-.5, 5.5), 5), interpolation='nearest')
    cb = fig.colorbar(im, ax=axs[0], ticks=range(5), shrink=.8)
    cb.ax.set_yticklabels(['Relativa', 'Máscara', 'Comparación a14', 'Hora: seno', 'Hora: coseno'])
    tm = plt.get_cmap('cividis').copy(); tm.set_bad('#eeeeee')
    im = axs[1].imshow(lag_image, cmap=tm, vmin=-23, vmax=0, interpolation='nearest')
    fig.colorbar(im, ax=axs[1], shrink=.8, label='Desfase respecto a la hora evaluada')
    for ax, title in zip(axs, ['Tipo de característica', 'Hora representada por cada píxel']):
        ax.set(title=title, xlabel='Columna del píxel', ylabel='Fila del píxel')
    fig.suptitle('Mapa fijo: 408 posiciones ocupadas y 616 vacías · sin difuminado', fontsize=14)
    fig.savefig(out/'02_leyenda_mapa.png', dpi=160)
    plt.close(fig)
    report = dict(objetivo=target, vecinas=local[1:], calendario='entrenamiento_01', delta_pct=50,
        episodio=int(ep.episodio), signo=int(ep.signo), inicio=str(times[0]), fin=str(times[-1]),
        seleccion='Primer episodio 2022 por inicio/estación/id; primera ventana completa con >=12 observaciones objetivo y dato final; sin mirar predicciones',
        pixeles_ocupados=408, vacios=616, pixeles_cambiados=int(np.count_nonzero(diff)),
        escala_visual_comun=[lo, hi], escala_diferencia=[-bound, bound],
        valores_fuera_0_1=[int(np.count_nonzero((v<0)|(v>1))) for v in scaled],
        modelos_cargados=False, entrenamiento=False, predicciones_nuevas=False,
        fuentes_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        versiones={'numpy':np.__version__, 'pandas':pd.__version__, 'matplotlib':matplotlib.__version__})
    (out/'metadatos.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida', type=Path, required=True)
    args = p.parse_args()
    run(args.salida)
