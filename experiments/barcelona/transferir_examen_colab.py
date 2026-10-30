"""Transfiere examen por partes y lanza una VM por detector con supervisor."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/barcelona_paraad/examen_colab_2018_2019'
CLI='/home/kali-lab-jelb/.venvs/colab-cli/bin/colab'


def enviar(detector):
    sesion=f'bcn-eval-{detector}-cpu-20261029';out=OUT/detector;out.mkdir(exist_ok=True)
    for f in sorted(OUT.glob('examen_parte_*.bin')):
        for intento in range(3):
            r=subprocess.run([CLI,'upload','-s',sesion,str(f),'/content/'+f.name],capture_output=True,text=True,timeout=180)
            if r.returncode==0:break
            time.sleep(2)
        if r.returncode:raise RuntimeError(f'{detector}: fallo de transferencia; URLs de autenticación omitidas')
        print(detector,f.name,'transferida',flush=True)
    r=subprocess.run([CLI,'exec','-s',sesion,'-f',str(OUT/f'lanzar_{detector}.py')],capture_output=True,text=True,timeout=180)
    if r.returncode:raise RuntimeError(f'{detector}: fallo de arranque; URLs de autenticación omitidas')
    estados=[json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]
    assert estados[-1]['paquete_verificado']
    (out/'lanzamiento.json').write_text(json.dumps(estados[-1],indent=2)+'\n')
    f=open(out/'supervisor.log','ab')
    p=subprocess.Popen([sys.executable,'-u','-m','experiments.barcelona.supervisar_colab','--sesion',sesion,
                        '--detector',detector,'--salida',str(out)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL,start_new_session=True)
    (out/'supervisor_pid.json').write_text(json.dumps(dict(pid=p.pid,sesion=sesion))+'\n')
    print(detector,'worker y supervisor iniciados',flush=True)


if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as e:
        for _ in e.map(enviar,['l0','v4','paraad']):pass
