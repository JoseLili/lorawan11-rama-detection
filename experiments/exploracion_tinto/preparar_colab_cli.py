"""Preparación remota de evaluación Colab; ejecutable por CLI en el kernel."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile

EXPECTED_SHA256 = '41b46b9c2adb386e7683c9848d4c5c0cd7974c8c6dca6073f1d5506542121a54'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def prepare(archive,root,venv):
    assert sha(archive)==EXPECTED_SHA256,'El paquete no coincide con el SHA-256 acordado'
    root.mkdir(parents=True,exist_ok=True)
    marker=root/'MANIFIESTO.json'
    if not marker.exists():
        assert not any(root.iterdir()),'Carpeta parcial sin manifiesto: conservar y revisar antes de repetir'
        with tarfile.open(archive) as t:t.extractall(root,filter='data')
    manifest=json.loads(marker.read_text())
    for name,expected in manifest.items():
        p=root/name
        assert p.resolve().is_relative_to(root.resolve()),name
        assert p.is_file() and sha(p)==expected,name
    print('Paquete verificado:',len(manifest),'archivos',flush=True)
    subprocess.run([sys.executable,'-m','pip','install','-q','uv'],check=True)
    uv=shutil.which('uv')
    assert uv,'No está disponible uv después de instalarlo'
    subprocess.run([uv,'python','install','3.14.7'],check=True)
    if not venv.exists():subprocess.run([uv,'venv','--python','3.14.7',str(venv)],check=True)
    python=str(venv/'bin/python')
    subprocess.run([uv,'pip','install','--python',python,'-r',str(root/'requirements-lock.txt')],check=True)
    env=os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='-1',TF_ENABLE_ONEDNN_OPTS='1',TF_NUM_INTRAOP_THREADS='2',
        TF_NUM_INTEROP_THREADS='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1',MPLCONFIGDIR='/tmp/tinto-mpl')
    check="""import sys,json,tensorflow as tf,keras
assert sys.version_info[:3]==(3,14,7),sys.version
assert not tf.config.get_visible_devices('GPU')
print(json.dumps({'python':sys.version.split()[0],'tensorflow':tf.__version__,'keras':keras.__version__}))
"""
    result=subprocess.run([python,'-c',check],env=env,check=True,text=True,capture_output=True)
    print(result.stdout,flush=True)
    # Solo valores explícitos de la configuración, nunca todo el entorno del kernel.
    versions=json.loads(result.stdout.strip().splitlines()[-1])
    report=dict(paquete_sha256=EXPECTED_SHA256,archivos_verificados=len(manifest),python=python,
        versiones=versions,solo_CPU=True,modelos_entrenados=False)
    temp=root/'PREPARACION_COLAB_OK.tmp'
    temp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    temp.replace(root/'PREPARACION_COLAB_OK.json')
    print(json.dumps(report,indent=2,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--paquete',type=Path,default=Path('/content/tinto_evaluacion_2022_20261029.tar.gz'))
    p.add_argument('--root',type=Path,default=Path('/content/tinto_evaluacion'))
    p.add_argument('--venv',type=Path,default=Path('/content/tinto_eval_env'))
    a=p.parse_args();prepare(a.paquete,a.root,a.venv)
