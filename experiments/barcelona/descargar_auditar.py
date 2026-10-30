"""Descarga pública y auditoría sin modelado ni selección por rendimiento.

AMB administrativa: se consideran todas las estaciones O3 del catálogo 2014–19
cuyos municipios pertenecen a la lista oficial AMB; no son las ocho de PARAAD.
"""
import argparse,calendar,datetime,gzip,hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
API='https://analisi.transparenciacatalunya.cat/resource/tasf-thgu.json'
MUNICIPIOS_CON_O3={'Badalona','Barcelona','Gavà','Montcada i Reixac','Prat de Llobregat, el','Sant Adrià de Besòs','Sant Cugat del Vallès','Sant Vicenç dels Horts','Viladecans'}
SOURCE_AMB='https://www.amb.cat/en/web/area-metropolitana/municipis-metropolitans'
H=[f'h{i:02d}' for i in range(1,25)]


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--descargar',action='store_true');args=ap.parse_args()
 ref=ROOT/'data/reference/barcelona_paraad';raw=ROOT/'data/raw/barcelona_paraad';out=ROOT/'results/barcelona_paraad/auditoria'
 for p in [ref,raw,out]:p.mkdir(parents=True,exist_ok=True)
 catalogo=json.loads((ROOT/'data/reference/paraad_catalogo_o3_2014_2019.json').read_text())['estaciones']
 cand=[c for c in catalogo if c['municipi'] in MUNICIPIOS_CON_O3];codes=sorted({c['codi_eoi'] for c in cand})
 pd.DataFrame(cand).to_csv(ref/'estaciones_candidatas_amb.csv',index=False)
 (ref/'criterio_geografico.json').write_text(json.dumps(dict(fuente=SOURCE_AMB,municipios_con_o3=sorted(MUNICIPIOS_CON_O3),codigos=codes,alcance='Todas las estaciones de municipios AMB presentes en catálogo; no identificación del subconjunto del artículo'),ensure_ascii=False,indent=2)+'\n')
 fuentes=[];partes=[]
 for y in range(2014,2020):
  path=raw/f'o3_amb_{y}.json.gz';meta=ref/f'descarga_{y}.json'
  if not path.exists():
   if not args.descargar:raise FileNotFoundError(path)
   q={'$select':','.join(['codi_eoi','nom_estacio','data','contaminant','unitats','municipi','latitud','longitud']+H),'$where':f"contaminant='O3' AND data >= '{y}-01-01T00:00:00' AND data < '{y+1}-01-01T00:00:00' AND codi_eoi in ("+','.join("'"+c+"'" for c in codes)+')','$order':'codi_eoi,data','$limit':'10000'}
   u=API+'?'+urllib.parse.urlencode(q)
   for intento in range(3):
    try:
     with urllib.request.urlopen(u,timeout=60) as f:b=f.read()
     rows=json.loads(b);assert len(rows)<10000;break
    except Exception:
     if intento==2:raise
     time.sleep(2)
   compressed=gzip.compress(b,mtime=0);path.write_bytes(compressed)
   meta.write_text(json.dumps(dict(url=u,consulta=q,consultado_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),filas=len(rows),sha256=hashlib.sha256(compressed).hexdigest()),ensure_ascii=False,indent=2)+'\n')
  m=json.loads(meta.read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256']
  rows=json.loads(gzip.decompress(path.read_bytes()));df=pd.DataFrame(rows)
  assert not df.empty and set(df.codi_eoi)<=set(codes)
  assert set(df.contaminant)=={'O3'}
  df['fecha']=pd.to_datetime(df['data']);assert (df.fecha.dt.year==y).all()
  assert not df.duplicated(['codi_eoi','fecha']).any()
  for h in H:
   if h not in df:df[h]=np.nan
   df[h]=pd.to_numeric(df[h],errors='raise')
  fuentes.append(dict(anio=y,**m));partes.append(df)
  print(y,'filas',len(df),flush=True)
 df=pd.concat(partes,ignore_index=True)
 filas=[]
 for s in codes:
  for y in range(2014,2020):
   t=df[(df.codi_eoi==s)&(df.fecha.dt.year==y)];v=t[H]
   filas.append(dict(codigo=s,nombre=next(c['nom_estacio'] for c in cand if c['codi_eoi']==s),anio=y,
    dias_calendario=366 if calendar.isleap(y) else 365,filas=len(t),horas_presentes=int(v.notna().sum().sum()),
    horas_posibles=(366 if calendar.isleap(y) else 365)*24,dias_24h=int(v.notna().sum(axis=1).eq(24).sum()),
    dias_min23h=int(v.notna().sum(axis=1).ge(23).sum()),dias_min12h=int(v.notna().sum(axis=1).ge(12).sum()),
    negativos=int(v.lt(0).sum().sum()),unidades=';'.join(sorted(t.unitats.unique())) if len(t) else ''))
 cobertura=pd.DataFrame(filas);cobertura['cobertura_pct']=100*cobertura.horas_presentes/cobertura.horas_posibles
 cobertura.to_csv(out/'cobertura_estacion_anio.csv',index=False)
 cambios=df.groupby('codi_eoi').agg(nombres=('nom_estacio',lambda s:';'.join(sorted(s.unique()))),unidades=('unitats',lambda s:';'.join(sorted(s.unique()))),latitudes=('latitud',lambda s:';'.join(sorted(s.dropna().unique()))),longitudes=('longitud',lambda s:';'.join(sorted(s.dropna().unique()))))
 cambios.to_csv(out/'metadatos_estaciones.csv')
 # Sólo posición de columna; no se asigna zona horaria ni inicio/fin del intervalo.
 largo=df.melt(id_vars=['codi_eoi','fecha'],value_vars=H,var_name='columna_hora',value_name='o3')
 largo['hora_fuente']=largo.columna_hora.str[1:].astype(int)
 largo=largo.drop(columns='columna_hora').sort_values(['codi_eoi','fecha','hora_fuente'])
 largo.to_parquet(out/'observaciones_hora_fuente.parquet',index=False)
 print(cobertura.pivot(index='nombre',columns='anio',values='cobertura_pct').round(1).to_string())
 (out/'registro.json').write_text(json.dumps(dict(fuentes=fuentes,estaciones=len(codes),filas_originales=len(df),horas_presentes=int(largo.o3.notna().sum()),duplicados=0,convencion_horaria='sin resolver: fecha y hora_fuente 1..24, sin conversión',subconjunto_paraad_identificado=False,sha256_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
