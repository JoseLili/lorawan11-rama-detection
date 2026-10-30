"""Supervisor local de UNA corrida ya lanzada: respalda y libera su VM al finalizar.

No crea sesiones, sube datos, entrena ni inicia otras tareas. Mantener la laptop
encendida mientras respalda. Sólo detiene la sesión después de descargar y
verificar el resultado terminal. Un error de red conserva la VM para recuperación.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import time

RAIZ = Path(__file__).resolve().parents[2]


def guardar(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cli', type=Path, required=True)
    ap.add_argument('--sesion', required=True)
    ap.add_argument('--salida', type=Path, required=True)
    args = ap.parse_args()
    out = args.salida.resolve()
    out.mkdir(parents=True, exist_ok=True)

    def cli(*cmd):
        r = subprocess.run([str(args.cli), *cmd], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise RuntimeError(r.stderr[-1500:] or r.stdout[-1500:])
        return r.stdout

    fallos = 0
    while True:
        try:
            texto = cli('exec', '-s', args.sesion, '-f', str(RAIZ / 'experiments/anomalias_red/snapshot_paraad_colab.py'))
            lineas = [l for l in texto.splitlines() if l.startswith('{')]
            estado = json.loads(lineas[-1])
            paquete = out / 'snapshot_descarga.tar.gz'
            cli('download', '-s', args.sesion, '/content/paraad_snapshot.tar.gz', str(paquete))
            assert hashlib.sha256(paquete.read_bytes()).hexdigest() == estado['sha256_snapshot']
            # Extraer en carpeta exclusiva de esta ejecución; datos propios, rutas acotadas.
            recuperado = out / 'recuperado'
            recuperado.mkdir(exist_ok=True)
            with tarfile.open(paquete) as tar:
                for m in tar.getmembers():
                    if m.name.startswith('/') or '..' in Path(m.name).parts or not m.isfile():
                        raise ValueError('miembro de snapshot no permitido')
                tar.extractall(recuperado, filter='data')
            for done in recuperado.glob('*/*/completo.json'):
                for name, h in json.loads(done.read_text())['archivos'].items():
                    assert hashlib.sha256((done.parent / name).read_bytes()).hexdigest() == h
            paquete.replace(out / 'snapshot_ultimo.tar.gz')
            estado['actualizado_utc'] = datetime.now(timezone.utc).isoformat()
            estado['sesion'] = args.sesion
            guardar(out / 'estado_supervisor.json', estado)
            print(json.dumps(estado, ensure_ascii=False), flush=True)
            fallos = 0
            if estado['estado']['estado'] in ('completo', 'error'):
                cli('stop', '-s', args.sesion)
                estado['sesion_liberada'] = True
                guardar(out / 'estado_supervisor.json', estado)
                return
        except Exception as e:
            fallos += 1
            mensaje = dict(error=str(e), fallos_consecutivos=fallos,
                           actualizado_utc=datetime.now(timezone.utc).isoformat(), sesion=args.sesion)
            guardar(out / 'error_supervisor.json', mensaje)
            print(json.dumps(mensaje), flush=True)
            if fallos >= 5:
                raise SystemExit('Supervisor detenido tras cinco fallos; revisar sesión antes de liberarla')
        time.sleep(60)


if __name__ == '__main__':
    main()
