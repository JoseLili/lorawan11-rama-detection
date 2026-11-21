# Evaluación congelada: 12 escenarios y cuatro percentiles

Registrado antes de ejecutar, por autorización del tesista. Sin entrenamiento.

- Modelo corrida1 del primer autoencoder; corrida2 como verificación de inferencia.
- Las mismas 7154 bases completas estación-día de 2022, mismo orden del manifiesto.
- O3 original auditado, mapa completo32 y escala congelados; sin reajuste ni clipping.
- Ataque a todas las 24 horas del día: x*(1+d) y x/(1+d), d=1,.5,.2,.05;
  x+b, b=5,10,20,40 ppb. No se mezclan escenarios. Sin máscaras como entrada.
- Score: MSE de los 24 píxeles ocupados. p95,p98,p99,p99.9 sobre originales,
  función histórica umbral_falsas_alarmas; alerta estricta score > umbral.
  p99 principal. No calibrar por estación ni seleccionar umbral tras ver ataques.
- Reportar TP/FP/FN/TN, recall, precisión,F1, ROC-AUC, AP, falsa alarma por
  escenario/percentil; desglose por estación con los mismos umbrales globales.
- Diagnóstico horario: error de reconstrucción escalado y en ppb, originales
  y alterados; diferencias pareadas de scores. Horas son la convención heredada.
- Guardar lecturas alteradas, reconstrucciones de las 24 horas, scores,
  manifiesto, configuración, hashes y entorno. Las imágenes se regeneran
  exactamente desde lecturas y mapa, sin guardar doce copias de fondos vacíos.
- Verificar fuentes contra hashes previos, alineación de originales, colisiones,
  finitud, equivalencia de métricas previas y dos modelos con pesos idénticos.
- Pares diagnósticos 50/50 por escenario. Calibración y evaluación originales
  reutilizan 2022; falsas alarmas descriptivas, no estimación independiente.
  Sin examen 2023–2026 ni conclusión causal sobre falta de contexto.
