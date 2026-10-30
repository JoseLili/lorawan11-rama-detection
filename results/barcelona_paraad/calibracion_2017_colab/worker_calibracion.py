import subprocess,sys,shutil,json,traceback,os
from pathlib import Path
root=Path('/content/barcelona');state=root/'estado_calibracion.json'
def guardar(s,**kw):
 p=state.with_suffix('.tmp');p.write_text(json.dumps(dict(estado=s,detector='calibracion',pid=os.getpid(),**kw),indent=2)+'\n');p.replace(state)
try:
 guardar('instalando')
 env=Path('/content/barcelona_env')
 subprocess.run([shutil.which('uv'),'venv','--seed','--python',sys.executable,str(env)],check=True)
 py=str(env/'bin/python')
 subprocess.run([py,'-m','pip','install','--disable-pip-version-check','-r',str(root/'requirements.txt')],check=True)
 guardar('calibrando')
 subprocess.run([py,'-u','-m','experiments.barcelona.calibrar_2017_colab'],cwd=root,check=True)
 assert json.loads((root/'salidas/calibracion/congelado.json').read_text())['igual']
 guardar('completo')
except Exception as e:
 guardar('error',error=str(e),traceback=traceback.format_exc());raise
