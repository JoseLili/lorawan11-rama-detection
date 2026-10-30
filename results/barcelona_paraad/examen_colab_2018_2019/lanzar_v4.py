import pathlib,hashlib,tarfile,subprocess,sys,json
root=pathlib.Path("/content/barcelona");root.mkdir(exist_ok=True)
partes=[{'nombre': 'examen_parte_000.bin', 'sha256': '5aac2b9f971f5fe6cebafe1ea1b61c583a50d3ebe01908e5f5ee8064e585108b'}, {'nombre': 'examen_parte_001.bin', 'sha256': '0209ab547301941a089df305a93ad66d0cd431379149ab6a0b655669453c5cc8'}, {'nombre': 'examen_parte_002.bin', 'sha256': '9e4f5789840b4f5a442914bb37579866d5a378c0bb15444767caa9023a1989e3'}]
p=pathlib.Path("/content/examen_barcelona.tar.gz")
with p.open("wb") as f:
 for row in partes:
  b=(pathlib.Path("/content")/row["nombre"]).read_bytes()
  assert hashlib.sha256(b).hexdigest()==row["sha256"]
  f.write(b)
assert hashlib.sha256(p.read_bytes()).hexdigest()=='55cd9327916c385106496b55257347a5670c5441e4e3941aa9af27297e47f85e'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith("/") and ".." not in pathlib.Path(m.name).parts
 t.extractall(root,filter="data")
(root/"worker.py").write_text('"""Orquesta un detector del examen, sin entrenar ni recalibrar."""\nimport argparse\nimport fcntl\nimport json\nimport os\nfrom pathlib import Path\nimport shutil\nimport subprocess\nimport sys\nimport traceback\n\n\ndef main():\n    ap=argparse.ArgumentParser();ap.add_argument(\'detector\',choices=[\'l0\',\'v4\',\'paraad\']);args=ap.parse_args()\n    root=Path(\'/content/barcelona\');lock=open(root/f\'{args.detector}.lock\',\'w\')\n    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n    state=root/f\'estado_{args.detector}.json\'\n    def guardar(fase,**kw):\n        tmp=state.with_suffix(\'.tmp\');tmp.write_text(json.dumps(dict(estado=fase,detector=args.detector,pid=os.getpid(),**kw),indent=2)+\'\\n\');tmp.replace(state)\n    try:\n        guardar(\'instalando\')\n        env=Path(\'/content/barcelona_env\')\n        if not (env/\'bin/python\').exists():\n            subprocess.run([shutil.which(\'uv\'),\'venv\',\'--seed\',\'--python\',sys.executable,str(env)],check=True)\n        py=str(env/\'bin/python\')\n        subprocess.run([py,\'-m\',\'pip\',\'install\',\'--disable-pip-version-check\',\'-r\',str(root/\'requirements.txt\')],check=True)\n        guardar(\'evaluando\')\n        subprocess.run([py,\'-u\',\'-m\',\'experiments.barcelona.evaluar_examen_colab\',\'--detector\',args.detector],cwd=root,check=True,\n                       env={**os.environ,\'PYTHONHASHSEED\':\'42\'})\n        final=json.loads((root/\'salidas\'/args.detector/\'congelado.json\').read_text())\n        assert final[\'igual\'] and final[\'unidades_examen\']==102\n        guardar(\'completo\')\n    except Exception as e:\n        guardar(\'error\',tipo=type(e).__name__,error=str(e),traceback=traceback.format_exc());raise\n\n\nif __name__==\'__main__\':main()\n')
assert not (root/"estado_v4.json").exists()
log=open(root/"worker.log","ab")
p=subprocess.Popen([sys.executable,"-u",str(root/"worker.py"),'v4'],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
print(json.dumps(dict(detector='v4',pid=p.pid,paquete_verificado=True)))
