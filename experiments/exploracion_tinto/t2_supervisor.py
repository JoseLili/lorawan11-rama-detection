"""Supervisor remoto de TINTO T2: pruebas breves en GPU y luego 4 variantes × 2 corridas.

Se lanza con Popen desde el kernel de Colab y sigue solo. No relanza fallos. Al terminar empaqueta
los resultados en /content/t2_resultados.tar.gz para descargarlos.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import tarfile
import time

ROOT = Path('/content/t2')
PAQ = ROOT / 'paquete'
SAL = ROOT / 'salidas'
SCRIPT = ROOT / 't2_colab.py'
TRABAJOS = [(v, c) for v in ['EH', 'RH', 'ED', 'RD'] for c in (1, 2)]   # los largos primero
PARALELO = 4


def estado(**kw):
    tmp = SAL / 'ESTADO.json.tmp'
    tmp.write_text(json.dumps(dict(actualizado=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()), **kw),
                              indent=1, ensure_ascii=False) + '\n')
    tmp.replace(SAL / 'ESTADO.json')


def lanzar(v, c, prueba=False):
    nombre = f'{"prueba_" if prueba else ""}{v}_c{c}'
    log = open(SAL / f'{nombre}.log', 'w')
    cmd = [sys.executable, '-u', str(SCRIPT), '--paquete', str(PAQ), '--variante', v, '--corrida', str(c),
           '--salida', str(SAL / nombre)] + (['--prueba'] if prueba else [])
    env = dict(os.environ, TF_CPP_MIN_LOG_LEVEL='2', PYTHONUNBUFFERED='1')
    return nombre, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)


def main():
    SAL.mkdir(parents=True, exist_ok=False)
    try:
        for v in ['EH', 'ED', 'RH', 'RD']:
            estado(fase='prueba', variante=v)
            nombre, p = lanzar(v, 1, prueba=True)
            assert p.wait() == 0 and (SAL / nombre / 'LISTO').exists(), f'falló la prueba {v}'
        pendientes, vivos, hechos = list(TRABAJOS), {}, {}
        while pendientes or vivos:
            while pendientes and len(vivos) < PARALELO:
                v, c = pendientes.pop(0)
                nombre, p = lanzar(v, c)
                vivos[nombre] = p
            for nombre, p in list(vivos.items()):
                code = p.poll()
                if code is not None:
                    hechos[nombre] = code
                    del vivos[nombre]
            estado(fase='entrenamiento', vivos=sorted(vivos), terminados=hechos, pendientes=[f'{v}_c{c}' for v, c in pendientes])
            time.sleep(30)
        estado(fase='terminado', terminados=hechos, fallidos=[n for n, c in hechos.items() if c != 0])
    except BaseException as e:
        estado(fase='error', error=repr(e))
    finally:
        with tarfile.open('/content/t2_resultados.tar.gz.tmp', 'w:gz') as t:
            t.add(SAL, arcname='salidas')
        Path('/content/t2_resultados.tar.gz.tmp').replace('/content/t2_resultados.tar.gz')
        (SAL / 'FIN').write_text('ok\n')


if __name__ == '__main__':
    main()
