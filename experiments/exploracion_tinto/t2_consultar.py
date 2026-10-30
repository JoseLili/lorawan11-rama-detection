"""Consulta de solo lectura del avance de TINTO T2 en Colab (para `colab exec -f`)."""
from pathlib import Path
import json

SAL = Path('/content/t2/salidas')
estado = SAL / 'ESTADO.json'
print(estado.read_text() if estado.exists() else 'sin ESTADO.json todavía')
for log in sorted(SAL.glob('*.log')):
    lineas = [l for l in log.read_text(errors='replace').splitlines()
              if l.startswith(('Epoch', 'LISTO', 'Traceback', '{"variante')) or 'val_loss' in l or 'Error' in l]
    print(f'--- {log.name}:', *lineas[-4:], sep='\n  ')
print('FIN' if (SAL / 'FIN').exists() else 'en curso')
