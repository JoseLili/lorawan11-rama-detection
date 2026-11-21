# Autoencoder estación-día — 2026-11-09

Autorizado en conversación por el tesista. Nueva línea: aprendizaje de reconstrucción con originales sin ataques inyectados; no se presume que estén libres de anomalías reales. Se preserva el piloto supervisado.

Configuración registrada antes del entrenamiento:

- Todas las 19300 bases completas de las 31 estaciones históricas, 2020–2022. Tabla auditada y mapa/escala completos32 congelados. Sin imputación, recorte, identificador de estación ni máscara de ataque de entrada.
- Entrenamiento: 2020 hasta septiembre 2021. Selección: octubre–diciembre 2021 sin inyección. El mapa/escala ya usaron todo 2020–2021: selección interna no independiente del preprocesamiento. No reentrenar posteriormente en este primer diagnóstico.
- Encoder Conv8 3×3 ReLU, Pool2, Conv16 3×3 ReLU, Pool2, Flatten, Dense8 lineal. Decoder Dense1024 ReLU, reshape8×8×16, upsample2, Conv8 ReLU, upsample2, Conv1 lineal. Cuello de botella de ocho valores, sin conexiones de salto.
- MSE únicamente en los 24 píxeles ocupados, tanto para pérdida como score. Soporte espacial fijo derivado del mapa, NO máscara de ataque ni de disponibilidad. Salida lineal admite valores fuera de [0,1].
- Adam 0.001, batch128, máximo30 épocas, early stopping val_loss paciencia5, min_delta0, restaurar mejor época. CPU, semilla42, dos réplicas desde cero. No cambiar configuración tras resultados.
- 2022 original: calibración exploratoria p99 principal y p99.9 secundario, función histórica umbral_falsas_alarmas, regla score > umbral. La falsa alarma en esos mismos originales es descriptiva por construcción, no estimación independiente.
- Evaluar todas las bases 2022: original y alteraciones de día completo x1.2, x1.5, x2 y sus recíprocos. Cada signo/intensidad por separado, sin entrenar con ataques. Pares artificiales 50/50; no prevalencia operativa ni calendarios L0.
- Guardar tensores originales, manifiestos, hashes, modelos, historias, scores, métricas, entorno y comparación de réplicas. Reportar recall, precisión, F1, ROC-AUC/AP y falsa alarma. No abrir 2023–2026, no afirmar superioridad a L0.
