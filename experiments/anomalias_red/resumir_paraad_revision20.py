"""Reúne exámenes completos sin entrenar, ajustar umbrales ni abrir matrices."""
from pathlib import Path
import sys
import json
import hashlib

RAIZ=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RAIZ))
import numpy as np
import pandas as pd

BASE=RAIZ/'results/anomalias_red_v1'
OUT=BASE/'revision20/examen'


def main():
    tablas=[];intervalos=[]
    for anio in [2024,2025,2026]:
        folder=OUT/str(anio)
        cfg=json.loads((folder/'finalizado.json').read_text())
        assert cfg['completo'] and cfg['inferencia_duplicada_identica']
        assert hashlib.sha256((folder/'resultados.csv').read_bytes()).hexdigest()==cfg['sha256_resultados']
        nuevo=pd.read_csv(folder/'resultados.csv');tablas.append(nuevo)
        intervalos.append(pd.read_csv(folder/'intervalos.csv'))
        r18=pd.read_csv(BASE/'revision18/resultados.csv')
        r18=r18[(r18.anio==anio)&(r18.dias=='comunes')&r18.detector.isin(['L0_unico','V4S_compartido','R3','V4'])].copy()
        r18['escenario']='original'
        r19=pd.read_csv(BASE/f'revision19/{anio}/resultados.csv')
        refs=pd.concat([r18,r19])
        for (esc,d,punto,v),g in nuevo.groupby(['escenario','delta_pct','punto','evaluacion']):
            esperado=g.iloc[0]
            ref=refs[(refs.escenario==esc)&(refs.delta_pct==d)&(refs.punto==punto)&(refs.evaluacion==v)]
            assert len(ref)==4
            assert ((ref.tp+ref.fn)==esperado.tp+esperado.fn).all()
            assert ((ref.fp+ref.tn)==esperado.fp+esperado.tn).all()
        tablas.append(refs)
    columnas=['anio','escenario','delta_pct','detector','punto','evaluacion','umbral',
              'tp','fp','fn','tn','precision','recall','f1','f2','falsas_alarmas','pr_auc','roc_auc']
    r=pd.concat(tablas,ignore_index=True)[columnas].sort_values(columnas[:6])
    r.to_csv(OUT/'comparacion_completa.csv',index=False)
    pd.concat(intervalos,ignore_index=True).to_csv(OUT/'intervalos_paraad.csv',index=False)
    tabla=r[r.evaluacion=='con ataque'].pivot(index=['anio','escenario','delta_pct','punto'],columns='detector',values='f1')
    tabla.to_csv(OUT/'tabla_f1.csv')
    print(tabla.round(3).to_string())
    # Una figura explicable: 2025 original, dos puntos operativos, F1 por magnitud.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True,layout='constrained')
    deltas=[5,10,20,50,100]
    for ax,punto in zip(axes,['p99','p99.9']):
        for det,label,style in [('PARAAD_SA_adaptado','PARAAD-SA adaptado','-o'),
                                ('V4','V4 (sin etiquetas)','-s'),
                                ('L0_unico','L0 único (supervisado, referencia)','--^')]:
            t=r[(r.anio==2025)&(r.escenario=='original')&(r.evaluacion=='con ataque')&(r.punto==punto)&(r.detector==det)].set_index('delta_pct').reindex(deltas)
            ax.plot(range(5),t.f1,style,label=label)
        ax.set_xticks(range(5),[str(d) for d in deltas]);ax.set_ylim(0,1)
        ax.set(title=f'2025 original · {punto}',xlabel='Magnitud proporcional δ (%)')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('F1 por estación-día');axes[1].legend(fontsize=8)
    fig.savefig(OUT/'comparacion_2025_original.png',dpi=170)


if __name__=='__main__':main()
