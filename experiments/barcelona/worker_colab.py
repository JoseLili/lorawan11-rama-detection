"""Orquestador remoto: entorno aislado, smoke duplicado y entrenamiento CPU."""
import argparse
import fcntl
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import traceback


def main():
    ap=argparse.ArgumentParser();ap.add_argument('detector',choices=['l0','v4','paraad']);args=ap.parse_args()
    root=Path('/content/barcelona'); root.mkdir(exist_ok=True)
    lock=open(root/f'{args.detector}.lock','w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=root/f'estado_{args.detector}.json'
    def guardar(fase,**kw):
        tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(dict(estado=fase,detector=args.detector,pid=os.getpid(),**kw),indent=2)+'\n');tmp.replace(state)
    try:
        guardar('instalando')
        env=Path('/content/barcelona_env')
        if not (env/'bin/python').exists():
            uv=shutil.which('uv')
            if not uv:raise RuntimeError('No se encontró uv para crear un entorno sin ensurepip')
            subprocess.run([uv,'venv','--seed','--python',sys.executable,str(env)],check=True)
        python=str(env/'bin/python')
        subprocess.run([python,'-m','pip','install','--disable-pip-version-check','-r',str(root/'requirements.txt')],check=True)
        entorno={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','TF_DETERMINISTIC_OPS':'1','TF_ENABLE_ONEDNN_OPTS':'0',
                 'TF_NUM_INTRAOP_THREADS':'1','TF_NUM_INTEROP_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONHASHSEED':'42'}
        cmd=[python,'-u','-m','experiments.barcelona.entrenar_colab','--detector',args.detector]
        guardar('smoke')
        subprocess.run(cmd+['--smoke'],cwd=root,env=entorno,check=True)
        assert json.loads((root/'smoke_salidas'/args.detector/'congelado.json').read_text())['igual']
        guardar('entrenando')
        subprocess.run(cmd,cwd=root,env=entorno,check=True)
        final=json.loads((root/'salidas'/args.detector/'congelado.json').read_text())
        assert final['igual'] and not final['smoke']
        guardar('completo')
    except Exception as e:
        guardar('error',tipo=type(e).__name__,error=str(e),traceback=traceback.format_exc())
        raise


if __name__=='__main__': main()
