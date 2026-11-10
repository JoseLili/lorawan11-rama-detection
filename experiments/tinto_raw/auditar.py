"""Auditoría de O3 original 2020–2022; sin imputación ni características."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.detect.multianual import cargar_o3_zips,leer_checksums,ESTACIONES

def main(out):
 out.mkdir(parents=True,exist_ok=False)
 long,sources=cargar_o3_zips(ROOT/'data/raw',leer_checksums(ROOT/'docs/checksums_2020_2026.txt'),anios=[2020,2021,2022])
 assert not long.duplicated(['timestamp','station']).any()
 wide=long.pivot(index='timestamp',columns='station',values='value').reindex(pd.date_range('2020-01-01','2022-12-31 23:00',freq='h',name='timestamp'))
 wide.to_csv(out/'o3_raw_ppb.csv',float_format='%.17g')
 check=pd.read_csv(out/'o3_raw_ppb.csv',index_col=0,parse_dates=True)
 pd.testing.assert_frame_equal(wide,check,check_dtype=False,check_names=False,check_freq=False,check_exact=True)
 context=[s for s in ESTACIONES if s!='XAL']
 rows=[];coverage=[]
 for year in [2020,2021,2022]:
  x=wide.loc[str(year)];z=x.reindex(columns=context)
  rows.append(dict(anio=year,horas=len(x),horas_completas_red32=int(z.notna().all(axis=1).sum()),dias_completos_red32=int(z.notna().all(axis=1).resample('D').sum().eq(24).sum())))
  for station in wide.columns:
   a=x[station];coverage.append(dict(anio=year,estacion=station,observaciones=int(a.notna().sum()),faltantes=int(a.isna().sum()),dias_24h=int(a.notna().resample('D').sum().eq(24).sum())))
 pd.DataFrame(coverage).to_csv(out/'cobertura.csv',index=False)
 report=dict(fuentes=sources,periodo=['2020','2021','2022'],entrada='Solo mediciones O3 ppb; NaN preservados',resumen=rows,estaciones=list(wide.columns),hash_matriz=hashlib.sha256((out/'o3_raw_ppb.csv').read_bytes()).hexdigest(),relectura_exacta=True,modelo='ninguno; auditoría sin entrenamiento')
 (out/'informe.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(rows))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--salida',type=Path,required=True);main(p.parse_args().salida)
