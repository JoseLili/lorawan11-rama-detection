"""Verifica artefactos terminados sin volver a entrenar; genera informe."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['TF_ENABLE_ONEDNN_OPTS']='0'
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from tensorflow import keras
ROOT=Path(__file__).resolve().parents[2]
r=ROOT/'results/tinto_autoencoder_20261109'
x=np.load(r/'originales.npy',mmap_mode='r')
m=pd.read_csv(r/'manifiesto.csv')
assert x.shape==(19300,32,32,1) and np.isfinite(x).all()
assert not m.duplicated(['fecha','estacion']).any()
coords=pd.read_csv(ROOT/'results/tinto_raw_20261109/representacion1/completos_32_mapa.csv')[['row','column']].to_numpy(int)
idx=np.flatnonzero(m.particion.eq('evaluacion'))[:32]
for run in [1,2]:
    model=keras.models.load_model(r/f'corrida{run}/modelo.keras',compile=False)
    a=np.array(x[idx]); b=model(a,training=False).numpy()
    scores=((a[:,coords[:,0],coords[:,1],0]-b[:,coords[:,0],coords[:,1],0])**2).mean(axis=1)
    stored=pd.read_csv(r/f'corrida{run}/scores.csv').original.to_numpy()[:32]
    np.testing.assert_allclose(scores,stored,rtol=1e-4,atol=1e-7)
s1=pd.read_csv(r/'corrida1/scores.csv'); s2=pd.read_csv(r/'corrida2/scores.csv')
pd.testing.assert_frame_equal(s1,s2,check_exact=True)
t=pd.read_csv(r/'metricas.csv'); selected=t[(t.corrida==1)&(t.tasa_objetivo==.01)]
h=pd.read_csv(r/'corrida1/historia.csv')
lines=['# Autoencoder estación-día: primer experimento','',
'Entrenado solo con originales sin ataques inyectados. CPU; dos corridas desde cero.',
'',f'19300 imágenes originales float32, {x.nbytes/2**20:.2f} MiB. Ajuste: 10334; selección interna: 1812; evaluación 2022: 7154.',
f'Épocas ejecutadas: {len(h)}; mejor época: {int(selected.iloc[0].mejor_epoca)}. Pérdida de selección inicial: {h.val_loss.iloc[0]:.6g}; mínima: {h.val_loss.min():.6g}.',
'','## Evaluación exploratoria, umbral p99','',
'| Factor aplicado al día | Recall | Precisión | F1 | ROC-AUC | Falsa alarma original |',
'|---|---:|---:|---:|---:|---:|']
for row in selected.itertuples():
    lines.append(f'| {row.factor:.4g} | {row.recall:.4f} | {row.precision:.4f} | {row.f1:.4f} | {row.roc_auc:.4f} | {row.falsa_alarma:.4f} |')
lines += ['', '## Interpretación','',
'La reconstrucción mejora, pero no demuestra detección suficiente: a p99 se detecta aproximadamente 12.09% de aumentos x1.5 y solo 0.014% de reducciones /1.5. Las reducciones producen scores menores y ROC-AUC inferior a 0.5 con la dirección predefinida. No se invierte el score ni se cambia el umbral después de ver ataques. Este autoencoder no resuelve la detección bidireccional; cualquier alternativa debe registrarse como nuevo experimento.',
'', '## Alcance y verificación','',
'Umbral calibrado en los mismos originales 2022: falsa alarma descriptiva, no validación independiente. Pares 50/50 por factor; precisión/F1 no extrapolables a prevalencia operativa. Originales pueden contener anomalías reales. Sin años 2023–2026 ni calendarios L0.',
'Mapa/escala congelados ajustados previamente en todo 2020–2021, incluido el periodo de selección interna. La pérdida y el score usan los 24 píxeles ocupados, no el fondo. No se entrega máscara de ataque.',
'Modelos guardados recargados y scores contrastados. Scores originales y todos los ataques idénticos entre réplicas; ver reproducibilidad.json para pesos e historias.',
'','## Reproducción','',
'Desde raíz, usar el entorno registrado en entorno.txt y ejecutar experiments/tinto_raw/autoencoder.py. La salida debe no existir: el script rechaza sobrescribirla. Para otra ejecución, cambiar explícitamente OUT a una carpeta nueva. Los tensores son regenerables; no requieren ZIP raw ni reajustar TINTO.']
(r/'informe.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
files=[p for p in r.rglob('*') if p.is_file() and p.name not in ['checksums.json','verificacion.log']]
(r/'checksums.json').write_text(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
print('\n'.join(lines)); print((r/'reproducibilidad.json').read_text())
