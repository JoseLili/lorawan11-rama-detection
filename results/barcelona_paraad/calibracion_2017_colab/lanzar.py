import pathlib,hashlib,tarfile,subprocess,sys,json
root=pathlib.Path("/content/barcelona");root.mkdir(exist_ok=True)
partes=[{'nombre': 'cal_parte_00.bin', 'sha256': 'fdd9dccaa2dcac6d17347a448da550a1b4a3c5cde7ab3a905fbd95c086a4ae79'}, {'nombre': 'cal_parte_01.bin', 'sha256': '25ac02866f52739d9593c398f034a7dd7521895b0bea76e0a0ed059a4c29866b'}]
p=pathlib.Path("/content/calibracion_2017.tar.gz")
with p.open("wb") as f:
 for row in partes:
  b=(pathlib.Path("/content")/row["nombre"]).read_bytes()
  assert hashlib.sha256(b).hexdigest()==row["sha256"]
  f.write(b)
assert hashlib.sha256(p.read_bytes()).hexdigest()=='db168c88c0bfe471571aa3b864fbeeb706ae00900767b4d0362e053afd1536e8'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith("/") and ".." not in pathlib.Path(m.name).parts
 t.extractall(root,filter="data")
(root/"worker.py").write_text("import subprocess,sys,shutil,json,traceback,os\nfrom pathlib import Path\nroot=Path('/content/barcelona');state=root/'estado_calibracion.json'\ndef guardar(s,**kw):\n p=state.with_suffix('.tmp');p.write_text(json.dumps(dict(estado=s,detector='calibracion',pid=os.getpid(),**kw),indent=2)+'\\n');p.replace(state)\ntry:\n guardar('instalando')\n env=Path('/content/barcelona_env')\n subprocess.run([shutil.which('uv'),'venv','--seed','--python',sys.executable,str(env)],check=True)\n py=str(env/'bin/python')\n subprocess.run([py,'-m','pip','install','--disable-pip-version-check','-r',str(root/'requirements.txt')],check=True)\n guardar('calibrando')\n subprocess.run([py,'-u','-m','experiments.barcelona.calibrar_2017_colab'],cwd=root,check=True)\n assert json.loads((root/'salidas/calibracion/congelado.json').read_text())['igual']\n guardar('completo')\nexcept Exception as e:\n guardar('error',error=str(e),traceback=traceback.format_exc());raise\n")
assert not (root/"estado_calibracion.json").exists()
log=open(root/"worker.log","ab")
p=subprocess.Popen([sys.executable,"-u",str(root/"worker.py")],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
print(json.dumps(dict(pid=p.pid,paquete_verificado=True)))
