"""Supervisor local: respaldo verificado, sin entrenar; libera VM al terminar."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tarfile
import time

ROOT=Path(__file__).resolve().parents[2]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sesion',required=True);ap.add_argument('--detector',required=True)
    ap.add_argument('--salida',type=Path);args=ap.parse_args()
    cli='/home/kali-lab-jelb/.venvs/colab-cli/bin/colab'
    out=args.salida or ROOT/'results/barcelona_paraad/colab_20261029'/args.detector;out.mkdir(exist_ok=True)
    def call(*cmd):
        r=subprocess.run([cli,*cmd],capture_output=True,text=True,timeout=180)
        if r.returncode:raise RuntimeError(f'CLI {cmd[0]} terminó con código {r.returncode}; consultar estado sin exponer URLs de autenticación')
        return r.stdout
    fallos=0
    while True:
        try:
            # Renueva la información del proxy antes de abrir el websocket.
            # Sólo consulta la asignación existente; no crea ni reinicia la VM.
            call('status','-s',args.sesion)
            texto=call('exec','-s',args.sesion,'-f',str(ROOT/'experiments/barcelona/snapshot_colab.py'))
            info=json.loads([l for l in texto.splitlines() if l.startswith('{')][-1])
            p=out/'descarga.tar.gz'
            call('download','-s',args.sesion,'/content/barcelona_snapshot.tar.gz',str(p))
            assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256_snapshot']
            rec=out/'recuperado';rec.mkdir(exist_ok=True)
            with tarfile.open(p) as t:
                for m in t.getmembers():
                    assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
                t.extractall(rec,filter='data')
            for listo in rec.glob('**/completo.json'):
                for n,h in json.loads(listo.read_text())['sha256'].items():
                    assert hashlib.sha256((listo.parent/n).read_bytes()).hexdigest()==h
            p.replace(out/'snapshot_ultimo.tar.gz')
            info.update(actualizado_utc=datetime.now(timezone.utc).isoformat(),sesion=args.sesion)
            if info['estado']['estado']=='completo':
                call('stop','-s',args.sesion);info['sesion_liberada']=True
            tmp=out/'estado_supervisor.tmp';tmp.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n');tmp.replace(out/'estado_supervisor.json')
            error=out/'error_supervisor.json'
            if error.exists():
                archivo=out/'incidencias';archivo.mkdir(exist_ok=True)
                shutil.copyfile(error,archivo/('conexion_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json'))
                error.unlink()
            print(json.dumps(info,ensure_ascii=False),flush=True);fallos=0
            if info.get('sesion_liberada') or info['estado']['estado']=='error':return
        except Exception as e:
            fallos+=1
            (out/'error_supervisor.json').write_text(json.dumps(dict(error=str(e),fallos=fallos,actualizado_utc=datetime.now(timezone.utc).isoformat()),ensure_ascii=False,indent=2)+'\n')
            if fallos>=5:
                # Mantiene un único supervisor durante interrupciones de red.
                # El heartbeat puede diagnosticarlo; no se duplican procesos.
                time.sleep(300)
                continue
        time.sleep(60)


if __name__=='__main__': main()
