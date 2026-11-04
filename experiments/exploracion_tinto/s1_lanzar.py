from pathlib import Path
import hashlib,tarfile,subprocess,sys,json
p=Path('/content/paquete_b12.tar.gz')
with p.open('wb') as out:
 for i in range(10):out.write(Path(f'/content/b12_parte_{i:02d}').read_bytes())
assert hashlib.sha256(p.read_bytes()).hexdigest()=='6f4a66e52a1b9bb59c31dd43cdeb6970a60e28ff430478f53a6ac441607f4ad9'
r=Path('/content/s1');assert not r.exists();r.mkdir()
with tarfile.open(p) as t:t.extractall(r,filter='data')
for name,h in json.loads((r/'paquete/SHA256.json').read_text()).items():assert hashlib.sha256((r/'paquete'/name).read_bytes()).hexdigest()==h
extra=Path('/content/s1_adicional.tar.gz')
assert hashlib.sha256(extra.read_bytes()).hexdigest()=='e36af0f5b1ac935e310e8311bfba407ae30cc51d77325f1b5845bac951cc4da9'
with tarfile.open(extra) as t:t.extractall(r,filter='data')
with (r/'supervisor.log').open('w') as log:
 proc=subprocess.Popen([sys.executable,'-u',str(r/'s1_supervisor.py')],stdout=log,stderr=subprocess.STDOUT,cwd=r)
(r/'PID').write_text(str(proc.pid))
print('Supervisor iniciado',proc.pid)
