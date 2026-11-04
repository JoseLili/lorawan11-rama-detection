from pathlib import Path
import json,subprocess
r=Path('/content/s12')
for p in [r/'salidas/ESTADO.json',r/'salidas/control_codificador.json',r/'DESCARGA.json']:
 if p.exists():print(str(p),p.read_text())
for p in sorted((r/'salidas').glob('*.log')) if (r/'salidas').exists() else []:
 print(p.name,'\n'.join(p.read_text(errors='replace').splitlines()[-5:]))
print(subprocess.run(['pgrep','-af','s12_(colab|supervisor)'],capture_output=True,text=True).stdout)
