"""Orquesta un detector del examen, sin entrenar ni recalibrar."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback


def main():
    ap=argparse.ArgumentParser();ap.add_argument('detector',choices=['l0','v4','paraad']);args=ap.parse_args()
    root=Path('/content/barcelona');lock=open(root/f'{args.detector}.lock','w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=root/f'estado_{args.detector}.json'
    def guardar(fase,**kw):
        tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(dict(estado=fase,detector=args.detector,pid=os.getpid(),**kw),indent=2)+'\n');tmp.replace(state)
    try:
        guardar('instalando')
        env=Path('/content/barcelona_env')
        if not (env/'bin/python').exists():
            subprocess.run([shutil.which('uv'),'venv','--seed','--python',sys.executable,str(env)],check=True)
        py=str(env/'bin/python')
        subprocess.run([py,'-m','pip','install','--disable-pip-version-check','-r',str(root/'requirements.txt')],check=True)
        guardar('evaluando')
        subprocess.run([py,'-u','-m','experiments.barcelona.evaluar_examen_colab','--detector',args.detector],cwd=root,check=True,
                       env={**os.environ,'PYTHONHASHSEED':'42'})
        final=json.loads((root/'salidas'/args.detector/'congelado.json').read_text())
        assert final['igual'] and final['unidades_examen']==102
        guardar('completo')
    except Exception as e:
        guardar('error',tipo=type(e).__name__,error=str(e),traceback=traceback.format_exc());raise


if __name__=='__main__':main()
