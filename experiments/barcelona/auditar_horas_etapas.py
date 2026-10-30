"""Amplía auditoría por fechas/horas de fuente; no inventa timestamps UTC."""
import calendar,json,hashlib
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/barcelona_paraad/auditoria'


def resumen_cambio_horario(d):
 filas=[]
 for y in range(2014,2020):
  for mes in [3,10]:
   dia=max(w[calendar.SUNDAY] for w in calendar.monthcalendar(y,mes))
   fecha=pd.Timestamp(year=y,month=mes,day=dia)
   t=d[d.fecha==fecha]
   for h in range(1,25):
    s=t[t.hora_fuente==h]
    filas.append(dict(fecha=str(fecha.date()),mes=mes,hora_fuente=h,estaciones_con_fila=len(s),con_valor=int(s.o3.notna().sum())))
 return pd.DataFrame(filas)


def elegibilidad_ajuste(d,c):
 s=c[c.anio.isin([2014,2015])].groupby(['codigo','nombre']).agg(horas_ajuste=('horas_presentes','sum'),horas_posibles=('horas_posibles','sum'))
 s['cobertura_ajuste_pct']=100*s.horas_ajuste/s.horas_posibles
 meses=d[(d.fecha.dt.year<=2015)&d.o3.notna()].assign(mes=lambda t:t.fecha.dt.to_period('M')).groupby('codi_eoi').mes.nunique()
 s['meses_ajuste']=meses.reindex(s.index.get_level_values('codigo')).fillna(0).to_numpy().astype(int)
 s['elegible_provisional_2000h_6meses']=(s.horas_ajuste>=2000)&(s.meses_ajuste>=6)
 return s


def main():
 d=pd.read_parquet(OUT/'observaciones_hora_fuente.parquet')
 c=pd.read_csv(OUT/'cobertura_estacion_anio.csv',dtype={'codigo':str})
 resumen_cambio_horario(d).to_csv(OUT/'horas_cambio_estacional.csv',index=False)
 s=elegibilidad_ajuste(d,c);s.to_csv(OUT/'elegibilidad_provisional_ajuste.csv')
 fuentes=ROOT/'data/reference/barcelona_paraad'
 items=list(fuentes.glob('*.json'))+list((ROOT/'data/raw/barcelona_paraad').glob('*.json.gz'))
 checks={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in items}
 for p in [Path(__file__),ROOT/'experiments/barcelona/descargar_auditar.py']:
  checks[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 (OUT/'checksums_fuentes.json').write_text(json.dumps(checks,indent=2)+'\n')
 print('Elegibles provisionales:',int(s.elegible_provisional_2000h_6meses.sum()),'de',len(s))


if __name__=='__main__':main()
