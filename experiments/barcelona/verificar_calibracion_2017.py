"""Verifica respaldo, soporte, puntajes agregados y falsas alarmas; sin examen."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.detect.evaluacion_red import umbral_falsas_alarmas

ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    b=ROOT/'results/barcelona_paraad/calibracion_2017_colab';r=b/'recuperado/salidas/calibracion'
    estado=json.loads((b/'estado_supervisor.json').read_text())
    assert estado['estado']['estado']=='completo' and estado['sesion_liberada']
    assert sha(b/'snapshot_ultimo.tar.gz')==estado['sha256_snapshot']
    for n,h in json.loads((r/'completo.json').read_text())['sha256'].items():assert sha(r/n)==h,n
    c=json.loads((r/'congelado.json').read_text());assert c['igual'] and c['casos']==4536 and c['anio']==2017
    modelos=pd.read_csv(ROOT/'results/barcelona_paraad/colab_20261029/seleccion_modelos_verificada.csv',dtype={'estacion':str})
    for m in modelos.itertuples():
        n=f'v4_{m.estacion}.keras' if m.detector=='v4' else f'{m.detector}.keras'
        assert c['modelos'][n]==m.sha256_modelo
    mask=pd.read_csv(r/'mascara_comun.csv',index_col='dia_utc',parse_dates=['dia_utc'])
    assert mask.isin([True,False]).all().all() and int(mask.to_numpy().sum())==4536
    assert set(mask.index.year)=={2017}
    p95=pd.read_csv(r/'p95_v4.csv',dtype={'estacion':str},float_precision='round_trip').set_index('estacion').iloc[:,0]
    assert sha(r/'p95_v4.csv')==c['sha256_p95_v4']
    resumen=pd.read_csv(r/'resumen.csv',float_precision='round_trip')
    for detector in ['l0','v4','paraad']:
        s=pd.read_csv(r/f'puntajes_{detector}.csv',index_col='dia_utc',parse_dates=['dia_utc'],float_precision='round_trip')
        assert s.notna().equals(mask) and np.isfinite(s.to_numpy()[mask.to_numpy()]).all()
        if detector!='paraad':
            nombre='l0' if detector=='l0' else 'v4_residuo'
            horas=pd.read_parquet(r/f'horas_{nombre}.parquet')
            assert set(horas.index.year)=={2017}
            if detector=='l0':assert horas.stack().dropna().between(0,1).all()
            diario=horas.groupby(horas.index.normalize()).mean()
            if detector=='v4':
                for col in horas:
                    np.testing.assert_allclose(np.percentile(horas[col].dropna().abs(),95,method='linear'),p95[col],rtol=1e-12,atol=1e-12)
                diario=diario.abs()/p95
            # El CSV proviene de otro entorno Pandas/NumPy: comprobación numérica
            # de la agregación; la duplicación remota ya exigió igualdad exacta.
            np.testing.assert_allclose(diario.reindex_like(s).to_numpy()[mask.to_numpy()],
                                       s.to_numpy()[mask.to_numpy()],rtol=1e-12,atol=1e-12)
        vals=s.to_numpy()[mask.to_numpy()]
        for punto,fa in [('p99',.01),('p99.9',.001)]:
            u=umbral_falsas_alarmas(vals,fa);assert u==c['umbrales'][detector][punto]
            fila=resumen[(resumen.detector==detector)&(resumen.punto==punto)].iloc[0]
            assert int((vals>u).sum())==fila.alertas and fila.casos==4536
            assert fila.alertas/4536<=fa
    resultado=dict(igual=True,casos=4536,modelos_congelados_intactos=15,hashes_correctos=True,
                    mascara_y_agregaciones_verificadas=True,umbrales_y_alertas_verificados=True,vm_liberada=True,
                    sha256_congelado=sha(r/'congelado.json'),sha256_verificador=sha(Path(__file__)))
    (b/'verificacion_final.json').write_text(json.dumps(resultado,indent=2)+'\n')
    print(resumen.to_string(index=False))
    print(json.dumps(resultado,indent=2))


if __name__=='__main__':main()
