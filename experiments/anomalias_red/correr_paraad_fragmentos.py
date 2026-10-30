"""Dos procesos CPU de un hilo en una VM de dos vCPU; verifica identidad al acabar."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'results/anomalias_red_v1/revision20'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dropout', type=float, choices=[.3, .5], required=True)
    d = ap.parse_args().dropout
    OUT.mkdir(parents=True, exist_ok=True)
    def estado(**kw):
        p = OUT / 'estado_entrenar.json'
        t = p.with_suffix('.tmp')
        t.write_text(json.dumps(kw)); t.replace(p)
    estado(estado='ejecutando', fase=f'fragmentos_{d}', pid=os.getpid())
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', TF_ENABLE_ONEDNN_OPTS='0',
               TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1', PYTHONUNBUFFERED='1',
               MPLCONFIGDIR='/tmp/mpl_paraad')
    procesos = []
    for r in (1, 2):
        f = (OUT / f'fragmento_r{r}.log').open('a')
        cmd = [sys.executable, str(BASE / 'experiments/anomalias_red/entrenar_paraad_fragmento.py'),
               '--dropout', str(d), '--repeticion', str(r)]
        procesos.append(subprocess.Popen(cmd, env=env, cwd=BASE, stdout=f, stderr=subprocess.STDOUT))
        f.close()
    codigos = [p.wait() for p in procesos]
    if any(codigos):
        estado(estado='error', codigos=codigos, dropout=d)
        raise SystemExit(1)
    # Verificar pesos/historia/reconstrucción antes de transferir; mismo host.
    os.environ.update({k: env[k] for k in ('CUDA_VISIBLE_DEVICES','TF_ENABLE_ONEDNN_OPTS',
                                         'TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')})
    import entrenar_paraad as e
    try:
        a, b = [OUT / f'seleccion/dropout{d}_r{r}' for r in (1, 2)]
        ma, mb = [e.tf.keras.models.load_model(p / 'modelo.keras') for p in (a, b)]
        e.iguales(ma, mb)
        e.pd.testing.assert_frame_equal(*[e.pd.read_csv(p/'historia.csv', float_precision='round_trip')
                                         for p in (a,b)], check_exact=True)
        e.np.testing.assert_array_equal(*[e.np.load(p/'reconstruccion.npy') for p in (a,b)])
        e.guardar(OUT / 'fragmentos_verificados.json', dict(dropout=d, igual=True,
                    entrada=json.loads((BASE/'esperado.json').read_text()),
                    sha256_wrapper=e.sha(Path(__file__)),
                    sha256_fragmento=e.sha(BASE/'experiments/anomalias_red/entrenar_paraad_fragmento.py')))
        estado(estado='completo', dropout=d, igual=True)
    except Exception:
        estado(estado='error', dropout=d, motivo='no se pudo verificar igualdad')
        raise


if __name__ == '__main__':
    main()
