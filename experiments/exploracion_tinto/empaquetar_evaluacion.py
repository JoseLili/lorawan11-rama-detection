"""Paquete local explícito para Colab; no sube nada ni incluye credenciales."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]


def build(dest):
    if dest.exists():raise FileExistsError(dest)
    paths=set(ROOT.glob('src/**/*.py'))|set(ROOT.glob('experiments/anomalias_red/*.py'))
    names=['requirements-lock.txt','experiments/exploracion_tinto/evaluar_2022.py',
        'experiments/exploracion_tinto/configuracion_entrenamiento_v1.json',
        'results/inventario_multianual/estaciones_geografia.csv',
        'results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1/vecinas_y_escalas.json',
        'results/exploracion_tinto_2022/prototipos_20261028/corrida1/L0_408/mapa_unico_32.csv',
        'results/exploracion_tinto_2022/hora_compacta_20261028/corrida1/L0_408/escalador.csv',
        'results/exploracion_tinto_2022/seleccion_tinto_v1/cierre_manual/corrida1/modelo_mejor_observado.keras',
        'results/exploracion_tinto_2022/seleccion_tinto_v1/cierre_manual.json',
        'results/anomalias_red_v1/lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras',
        'results/anomalias_red_v1/lstm_local_examen/c20/d50/seleccion/dias_2022.csv.gz',
        'results/anomalias_red_v1/matrices/matriz_limpia_2020_2022.csv.gz']
    names += [f'results/anomalias_red_v1/matrices/matriz_entrenamiento_{i:02d}_d{d}.csv.gz' for i in range(1,11) for d in [100,50,20]]
    names += [f'results/anomalias_red_v1/planes/plan_entrenamiento_{i:02d}.csv' for i in range(1,11)]
    paths|={ROOT/n for n in names}
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(dest,'w:gz') as t:
        for p in sorted(paths):
            assert p.is_file() and not p.is_symlink(),p
            t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
        import io
        b=(json.dumps(manifest,indent=2)+'\n').encode()
        info=tarfile.TarInfo('MANIFIESTO.json');info.size=len(b)
        t.addfile(info,io.BytesIO(b))
    print(json.dumps({'archivo':str(dest),'MiB':dest.stat().st_size/1024**2,'archivos':len(paths),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();build(a.salida)
