"""Descarga respaldos disponibles con hash. No lanza ni modifica experimentos."""
from pathlib import Path
import argparse,subprocess,json,hashlib,time,os
CLI='/home/kali-lab-jelb/.venvs/colab-cli/bin/colab'
def run(session,out,watch):
 out.mkdir(parents=True,exist_ok=True);(out/'PID_RESPALDO').write_text(str(os.getpid()))
 for _ in range(720 if watch else 1):
  for key,remote in [('corrida1','corrida1.json'),('corrida2','corrida2.json'),('final','DESCARGA.json')]:
   done=out/(key+'_verificado.json')
   if done.exists():continue
   meta=out/(key+'.json.tmp')
   p=subprocess.run([CLI,'download','-s',session,'/content/s12/'+remote,str(meta)],capture_output=True,timeout=120)
   if p.returncode:continue
   m=json.loads(meta.read_text());assert m['ruta'] in ['/content/s12/corrida1.tar.gz','/content/s12/corrida2.tar.gz','/content/s12/resultados.tar.gz']
   dst=out/Path(m['ruta']).name;tmp=dst.with_suffix('.tmp')
   p=subprocess.run([CLI,'download','-s',session,m['ruta'],str(tmp)],capture_output=True,timeout=240)
   if p.returncode:continue
   assert tmp.stat().st_size==m['bytes'] and hashlib.sha256(tmp.read_bytes()).hexdigest()==m['sha256']
   tmp.replace(dst);meta.replace(out/(key+'.json'));done.write_text(json.dumps(m,indent=2)+'\n')
   print('Respaldo verificado:',key,flush=True)
  if (out/'final_verificado.json').exists():return
  if watch:time.sleep(60)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sesion',required=True);p.add_argument('--salida',type=Path,required=True);p.add_argument('--vigilar',action='store_true');a=p.parse_args();run(a.sesion,a.salida,a.vigilar)
