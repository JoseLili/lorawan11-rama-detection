"""Ejecutar con colab exec: snapshot verificable de la corrida CPU aislada."""
from pathlib import Path
import hashlib
import json
import tarfile

out = Path('/content/paraad_r20/results/anomalias_red_v1/revision20')
archivos = {p for p in out.glob('*') if p.is_file() and p.suffix != '.tmp'}
for fase in ['auditar', 'smoke', 'benchmark', 'seleccion', 'definitivo']:
    folder = out / fase
    if folder.exists():
        archivos.update(p for p in folder.glob('*') if p.is_file() and p.suffix != '.tmp')
        for done in folder.glob('*/completo.json'):
            meta = json.loads(done.read_text())
            archivos.add(done)
            for nombre, esperado in meta['archivos'].items():
                p = done.parent / nombre
                assert hashlib.sha256(p.read_bytes()).hexdigest() == esperado
                archivos.add(p)
name = Path('/content/paraad_snapshot.tar.gz')
with tarfile.open(str(name) + '.tmp', 'w:gz') as tar:
    for p in sorted(archivos):
        tar.add(p, arcname=str(p.relative_to(out)))
Path(str(name) + '.tmp').replace(name)
estado = json.loads((out / 'estado_entrenar.json').read_text())
progreso = {str(p.relative_to(out)): json.loads(p.read_text())
            for p in out.glob('*/*/progreso.json')}
print(json.dumps({'estado': estado, 'progreso': progreso,
                  'sha256_snapshot': hashlib.sha256(name.read_bytes()).hexdigest(),
                  'bytes': name.stat().st_size}))
