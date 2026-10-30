"""Control de los puntajes históricos usados en diferencias pareadas; no infiere."""
import sys
from pathlib import Path
RAIZ=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RAIZ))
import numpy as np
import pandas as pd
from src.detect import anomalias_red as ar,estacion_dia as ed


def main():
    base=RAIZ/'results/anomalias_red_v1';out=base/'revision20/examen';filas=[]
    r=pd.read_csv(base/'revision18/resultados.csv',float_precision='round_trip')
    r=r[(r.dias=='comunes')&(r.evaluacion=='con ataque')]
    for anio in [2024,2025,2026]:
        mask=pd.read_csv(out/f'{anio}/mascara_comun.csv',index_col='dia',parse_dates=['dia']).astype(bool)
        ok=mask.to_numpy().ravel();dias=mask.index;objetivos=mask.columns.tolist()
        ref=pd.read_csv(base/f'revision18/dias_{anio}.csv.gz',parse_dates=['dia'],float_precision='round_trip')
        cals=ar.corridas().corrida.tolist()[1:] if anio==2024 else [c for c in ar.corridas_finales().corrida if str(anio) in c]
        y=np.concatenate([ed.etiquetas(ar.leer_plan(base/f'planes/plan_{c}.csv'),dias,objetivos).to_numpy().ravel()[ok] for c in cals])
        for d in [100,50,20,10,5]:
            for det in ['L0_unico','V4']:
                s=np.concatenate([ref[(ref.conjunto==f'{c}_d{d}')&(ref.detector==det)].set_index('dia').reindex(dias)[objetivos].to_numpy().ravel()[ok] for c in cals])
                assert np.isfinite(s).all()
                for punto in ['p99','p99.9']:
                    f=r[(r.anio==anio)&(r.delta_pct==d)&(r.detector==det)&(r.punto==punto)].iloc[0]
                    a=s>f.umbral
                    calc={'tp':int((a&y).sum()),'fp':int((a&~y).sum()),'fn':int((~a&y).sum()),'tn':int((~a&~y).sum())}
                    assert all(calc[k]==f[k] for k in calc),(anio,d,det,punto,calc)
                    filas.append(dict(anio=anio,delta_pct=d,detector=det,punto=punto,igual=True,**calc))
    pd.DataFrame(filas).to_csv(out/'control_referencias_pareadas.csv',index=False)
    print(f'{len(filas)} controles de TP/FP/FN/TN históricos idénticos')


if __name__=='__main__':main()
