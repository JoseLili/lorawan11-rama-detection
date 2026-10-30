"""Ejecutado en VM: respaldo de unidades cerradas y estado, sin datos de entrada."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

root=Path('/content/barcelona')
estados=list(root.glob('estado_*.json'))
assert len(estados)==1
estado=json.loads(estados[0].read_text())
archivos=[estados[0]]
for carpeta in ['salidas','smoke_salidas']:
    b=root/carpeta
    for listo in b.glob('**/completo.json'):
        meta=json.loads(listo.read_text())
        for n,h in meta['sha256'].items():
            p=listo.parent/n
            assert hashlib.sha256(p.read_bytes()).hexdigest()==h
            archivos.append(p)
        archivos.append(listo)
    archivos.extend(p for p in b.glob('**/*.json') if p.name!='completo.json')
log=root/'worker.log'
ultimas=log.read_text(errors='replace').splitlines()[-12:] if log.exists() else []
target=Path('/content/barcelona_snapshot.tar.gz')
with tarfile.open(target,'w:gz') as tar:
    for p in sorted(set(archivos)):
        tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
    raw=('\n'.join(ultimas)+'\n').encode();m=tarfile.TarInfo('log_ultimo.txt');m.size=len(raw);tar.addfile(m,io.BytesIO(raw))
progresos=sorted((root/'salidas').glob('**/progreso.json'),key=lambda p:p.stat().st_mtime)
print(json.dumps(dict(estado=estado,ultimo_progreso=json.loads(progresos[-1].read_text()) if progresos else None,
                      sha256_snapshot=hashlib.sha256(target.read_bytes()).hexdigest(),archivos=len(set(archivos))),ensure_ascii=False))
