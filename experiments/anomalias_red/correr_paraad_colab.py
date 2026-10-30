"""Orquestador CPU: comprobaciones separadas del entrenamiento; estado persistente.

Ejecutar en una copia aislada del repo con sólo datos 2020–2022. El cliente CLI
descarga snapshots mientras corre; esta VM no se considera almacenamiento duradero.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

RAIZ = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--accion', choices=['comprobar', 'entrenar'], required=True)
    ap.add_argument('--salida', type=Path, required=True)
    args = ap.parse_args()
    out = args.salida.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', TF_ENABLE_ONEDNN_OPTS='0',
               TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1',
               MPLCONFIGDIR='/tmp/mpl_paraad', PYTHONUNBUFFERED='1')
    estado = out / f'estado_{args.accion}.json'

    def escribir(**kw):
        tmp = estado.with_suffix('.tmp')
        tmp.write_text(json.dumps(kw, indent=2))
        tmp.replace(estado)

    def ejecutar(nombre, cmd):
        escribir(estado='ejecutando', fase=nombre, pid=os.getpid())
        inicio = time.monotonic()
        with (out / f'{nombre}.log').open('a') as f:
            r = subprocess.run(cmd, cwd=RAIZ, env=env, stdout=f, stderr=subprocess.STDOUT)
        with (out / 'tiempos.jsonl').open('a') as f:
            f.write(json.dumps(dict(fase=nombre, segundos=time.monotonic()-inicio, codigo=r.returncode))+'\n')
        if r.returncode:
            escribir(estado='error', fase=nombre, codigo=r.returncode)
            raise SystemExit(r.returncode)

    fases = ['auditar', 'smoke', 'benchmark'] if args.accion == 'comprobar' else ['seleccion', 'definitivo']
    if args.accion == 'comprobar':
        ejecutar('tests', [sys.executable, '-m', 'pytest', 'tests/test_paraad.py', '-q'])
    else:
        if json.loads((out / 'estado_comprobar.json').read_text())['estado'] != 'completo':
            raise ValueError('primero deben pasar las comprobaciones')
    for fase in fases:
        ejecutar(fase, [sys.executable, 'experiments/anomalias_red/entrenar_paraad.py',
                        '--fase', fase, '--datos', 'data/processed/paraad_2020_2022.parquet',
                        '--salida', str(out), '--reanudar'])
    escribir(estado='completo', fases=fases)


if __name__ == '__main__':
    main()
