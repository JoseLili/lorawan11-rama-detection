"""Inventario restringido a ajuste 2020–2022; no abre datos de otros años."""
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'experiments/exploracion_tinto/inventario_datos_20261028.json'
base = ROOT/'results/anomalias_red_v1'
clean_path = base/'matrices/matriz_limpia_2020_2022.csv.gz'
x = pd.read_csv(clean_path, index_col=0)
ts = pd.to_datetime(x.index)
assert ts.min().year == 2020 and ts.max().year == 2022
values = [c for c in x if c.endswith('_valor')]
mask = [c for c in x if c.endswith('_mascara')]
files = [base/f'matrices/matriz_entrenamiento_{k:02d}_d50.csv.gz' for k in range(1,21)]
plans = [base/f'planes/plan_entrenamiento_{k:02d}.csv' for k in range(1,21)]
headers = {}
for path in files:
    if path.exists():
        with gzip.open(path, 'rt') as f:
            headers[path.name] = f.readline().strip().split(',')
report = {
    'alcance': 'Solo matriz limpia 2020–2022 y cabeceras de entrenamiento_01..20 d50; no evaluación de detectores',
    'limpia': {'archivo': str(clean_path.relative_to(ROOT)), 'filas': len(x),
               'primera_hora': str(ts.min()), 'ultima_hora': str(ts.max()),
               'rejilla_horaria_continua': bool(ts.equals(pd.date_range(ts.min(), ts.max(), freq='h'))),
               'columnas': list(x.columns), 'estaciones_valor': [c.removesuffix('_valor') for c in values],
               'columnas_valor':len(values), 'columnas_mascara':len(mask),
               'lecturas_faltantes_por_estacion': x[values].isna().sum().to_dict(),
               'sha256_archivo':hashlib.sha256(clean_path.read_bytes()).hexdigest()},
    'matrices_d50_presentes': [str(p.relative_to(ROOT)) for p in files if p.exists()],
    'matrices_d50_faltantes': [str(p.relative_to(ROOT)) for p in files if not p.exists()],
    'planes_presentes':sum(p.exists() for p in plans),
    'cabeceras_entrenamiento': headers,
    'catalogo_geografico_presente':(ROOT/'data/reference/cat_estacion_simat.csv').exists(),
    'modelo_L0_seleccion_presente':(base/'lstm_local/c20/d50/seleccion/modelo_seleccion.keras').exists(),
    'puntajes_L0_2022_presentes':(base/'lstm_local/c20/d50/seleccion/dias_2022.csv.gz').exists(),
}
OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['limpia','cabeceras_entrenamiento','matrices_d50_presentes']}, indent=2))
print({k:v for k,v in report['limpia'].items() if k not in ['columnas','estaciones_valor','lecturas_faltantes_por_estacion','sha256_archivo']})
