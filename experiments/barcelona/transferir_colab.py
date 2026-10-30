"""Transfiere por partes, inicia workers y supervisores; no imprime credenciales."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/barcelona_paraad/colab_20261029'
CLI='/home/kali-lab-jelb/.venvs/colab-cli/bin/colab'


def sesion(detector):
    name=f'bcn-{detector}-cpu-20261029'
    log=OUT/detector;log.mkdir(exist_ok=True)
    for f in sorted((OUT/f'partes_{detector}').glob('parte_*.bin')):
        for intento in range(3):
            r=subprocess.run([CLI,'upload','-s',name,str(f),'/content/'+f.name],capture_output=True,text=True,timeout=180)
            if r.returncode==0:break
            print(f'{detector}: reintento {intento+1} de {f.name} (detalle de autenticación omitido)',flush=True)
            time.sleep(2)
        if r.returncode:raise RuntimeError(f'{detector}: falló la transferencia de {f.name}')
        print(f'{detector}: {f.name} transferida',flush=True)
    r=subprocess.run([CLI,'exec','-s',name,'-f',str(OUT/f'lanzar_{detector}.py')],capture_output=True,text=True,timeout=180)
    if r.returncode:raise RuntimeError(f'{detector}: falló el arranque remoto; revisar sin exponer URLs de autenticación')
    estados=[json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]
    assert estados and estados[-1]['paquete_verificado']
    (log/'lanzamiento.json').write_text(json.dumps(estados[-1],indent=2)+'\n')
    f=open(log/'supervisor.log','ab')
    p=subprocess.Popen([sys.executable,'-u','-m','experiments.barcelona.supervisar_colab','--sesion',name,'--detector',detector],
                       cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    (log/'supervisor_pid.json').write_text(json.dumps(dict(pid=p.pid,sesion=name))+'\n')
    print(f'{detector}: worker y supervisor iniciados',flush=True)


if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as e:
        for resultado in e.map(sesion,['l0','v4','paraad']):pass
