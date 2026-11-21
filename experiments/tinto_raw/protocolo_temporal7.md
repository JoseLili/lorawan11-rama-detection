# Predicción temporal TINTO de siete días — 2026-11-11

Autorizado por el tesista. Registro antes del entrenamiento. Diagnóstico pequeño:
auditoría de elegibilidad encontró 139 ajuste, 38 selección, 175 evaluación.
No hay secuencias elegibles de 2020; ajuste/selección quedan en 2021. No imputar.

- Requerir ocho días consecutivos completos de la misma estación. Entradas: siete
  imágenes anteriores, en canales cronológicos t-7..t-1; objetivo: imagen de t.
  CNN de canales temporales, no LSTM ni autoencoder de reconstrucción del día actual.
- Mismo mapa/escala completos32 congelados. Sin imágenes del día objetivo como
  entrada, identidad de estación, fechas, máscaras ni ataques de entrenamiento.
- Encoder Conv8 3 same relu, Pool2, Conv16 3 same relu, Pool2, Flatten, Dense8;
  decoder Dense1024 relu, reshape8x8x16, upsample2, Conv8 relu, upsample2, Conv1 lineal.
- MSE 24 píxeles ocupados, Adam .001, batch32, máximo30 épocas, paciencia5,
  val_loss, restaurar mejor época. Semilla42, CPU, dos corridas desde cero.
- Partición por fecha objetivo: hasta septiembre2021 ajuste; octubre–diciembre2021
  selección; 2022 evaluación. Historial siempre anterior; puede cruzar fronteras
  temporales como contexto disponible. Ventanas se solapan; no son independientes.
  El preprocesamiento congelado ya usó todo2020–2021, incluida selección.
- 12 escenarios acordados, aplicados solo al objetivo; historia original intacta.
  Estudia inicio aislado, no ataque sostenido. Puntuación MSE en escala congelada.
- Comparador: autoencoder guardado, mismos175 objetivos. Recalibrar ambos con sus
  originales elegibles2022, función histórica, p95/98/99/99.9, score>umbral.
  p99 principal. No comparar directamente con métricas de7154 bases.
- Reportar precisión,recall,F1,AUC/AP, conteos TP/FP/FN/TN, falsas alarmas teóricas
  y observadas; tamaños y estaciones, historias,predicciones,pesos/hashes, entorno.
- Cambian objetivo de aprendizaje, canales y muestra de entrenamiento: no es una
  ablación que aísle causalmente temporalidad. No afirmar superioridad general.
  Sin años2023–2026. Sin búsqueda posterior de ventanas, hiperparámetros o umbral.
