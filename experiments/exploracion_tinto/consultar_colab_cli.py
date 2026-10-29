"""Celda de consulta para colab exec -f: solo lectura, sin argparse del kernel."""
from pathlib import Path
import json
import runpy

remote = runpy.run_path('/content/inspeccionar_colab_cli.py', run_name='inspector_colab')
output = Path('/content/tinto_evaluacion/results/exploracion_tinto_2022/evaluacion_colab_20261029')
report = remote['inspect'](output)
setup = Path('/content/tinto_evaluacion/PREPARACION_COLAB_OK.json')
report['preparacion_completa'] = setup.exists()
if setup.exists():
    report['preparacion'] = json.loads(setup.read_text())
if not setup.exists():
    log = Path('/content/preparacion_tinto.log')
    report['preparacion_log_final'] = log.read_text(errors='replace')[-2500:] if log.exists() else ''
print(json.dumps(report, indent=2, ensure_ascii=False))
