# Orden temporal explícito — 2026-11-11

Registro antes de entrenamiento; autorizado para corregir el procesamiento temporal.
Auditoría sin métricas: ventanas1/2/3/7 días dejan ajuste7168/4625/2549/139,
selección1311/884/526/38 y evaluación5101/3449/2125/175. Elegir2 días para incluir
un cruce23→00 dentro de la entrada y conservar más ejemplos que3/7 días.

Dos candidatos, dos réplicas semilla42, sin búsqueda:
- CNN diaria compartida: Conv8 relu3 same,Pool2,Conv16 relu3 same,Pool2,
  Flatten,Dense8; TimeDistributed sobre2 imágenes, GRU16, Dense24 lineal.
- GRU horaria: extraer los24 valores por día del mapa TINTO en orden h00..h23,
  concatenar48 pasos de un valor, GRU16,Dense24 lineal. Es un comparador horario:
  TINTO es reversible y no se atribuye valor añadido a la imagen en este brazo.
- Ambos predicen las24 lecturas escaladas del día siguiente. MSE, Adam.001,
  batch64, máximo30 épocas, paciencia5,val_loss, restaurar mejor época.
- Días completos consecutivos de la misma estación, sin imputar. Ajuste por fecha
  objetivo hasta septiembre2021, selección último trimestre2021,evaluación2022.
  Historia pasada puede cruzar particiones; no objetivo ni futuro en entrada.
- Mapas y escalas congelados; los valores horarios conservan escala por hora
  del mapa original. No coordenadas, estación, máscaras ni ataques de entrenamiento.
- Verificar timestamp de cada paso y cruces23→00 con diferencia exacta1h,
  índices del mapa h00..h23 y equivalencia tensor↔tabla original escalada.
  Esto NO valida convención SIMAT HORA1→00 ni demuestra aprendizaje.
- Diagnóstico de orden predefinido sobre originales2022: invertir orden de días;
  además invertir48 horas en GRU horaria. Medir cambio de predicción y MSE;
  inversión cambia recencia además de orden, no prueba causal aislada de23→00.
- 12 ataques de día completo solo al objetivo, historia original. p95/98/99/99.9
  en originales elegibles2022 por modelo; p99 principal, score>umbral histórico.
  Autoencoder guardado como referencia en idéntico soporte, recalibrado allí.
- Guardar manifiestos, cobertura, historias,modelos,predicciones,scores,métricas,
  FA teóricas y observadas, entorno y hashes. Dos réplicas y recarga de modelos.
- Originales2022 se usan para calibrar y evaluar: exploratorio, no independiente.
  Ventanas se solapan; positivos50/50 artificiales. Cambian arquitectura y objetivo
  frente al autoencoder: no atribuir diferencias exclusivamente a temporalidad.
  No reentrenar según ataques, no abrir2023–2026 ni alterar resultados anteriores.
