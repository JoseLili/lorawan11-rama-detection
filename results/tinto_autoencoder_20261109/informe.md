# Autoencoder estación-día: primer experimento

Entrenado solo con originales sin ataques inyectados. CPU; dos corridas desde cero.

19300 imágenes originales float32, 75.39 MiB. Ajuste: 10334; selección interna: 1812; evaluación 2022: 7154.
Épocas ejecutadas: 30; mejor época: 27. Pérdida de selección inicial: 0.00942121; mínima: 0.000946153.

## Evaluación exploratoria, umbral p99

| Factor aplicado al día | Recall | Precisión | F1 | ROC-AUC | Falsa alarma original |
|---|---:|---:|---:|---:|---:|
| 1.2 | 0.0361 | 0.7842 | 0.0690 | 0.6342 | 0.0099 |
| 0.8333 | 0.0021 | 0.1744 | 0.0041 | 0.3679 | 0.0099 |
| 1.5 | 0.1209 | 0.9241 | 0.2138 | 0.7793 | 0.0099 |
| 0.6667 | 0.0001 | 0.0139 | 0.0003 | 0.2294 | 0.0099 |
| 2 | 0.3550 | 0.9728 | 0.5202 | 0.9081 | 0.0099 |
| 0.5 | 0.0000 | 0.0000 | 0.0000 | 0.1063 | 0.0099 |

## Interpretación

La reconstrucción mejora, pero no demuestra detección suficiente: a p99 se detecta aproximadamente 12.09% de aumentos x1.5 y solo 0.014% de reducciones /1.5. Las reducciones producen scores menores y ROC-AUC inferior a 0.5 con la dirección predefinida. No se invierte el score ni se cambia el umbral después de ver ataques. Este autoencoder no resuelve la detección bidireccional; cualquier alternativa debe registrarse como nuevo experimento.

## Alcance y verificación

Umbral calibrado en los mismos originales 2022: falsa alarma descriptiva, no validación independiente. Pares 50/50 por factor; precisión/F1 no extrapolables a prevalencia operativa. Originales pueden contener anomalías reales. Sin años 2023–2026 ni calendarios L0.
Mapa/escala congelados ajustados previamente en todo 2020–2021, incluido el periodo de selección interna. La pérdida y el score usan los 24 píxeles ocupados, no el fondo. No se entrega máscara de ataque.
Modelos guardados recargados y scores contrastados. Scores originales y todos los ataques idénticos entre réplicas; ver reproducibilidad.json para pesos e historias.

## Reproducción

Desde raíz, usar el entorno registrado en entorno.txt y ejecutar experiments/tinto_raw/autoencoder.py. La salida debe no existir: el script rechaza sobrescribirla. Para otra ejecución, cambiar explícitamente OUT a una carpeta nueva. Los tensores son regenerables; no requieren ZIP raw ni reajustar TINTO.
