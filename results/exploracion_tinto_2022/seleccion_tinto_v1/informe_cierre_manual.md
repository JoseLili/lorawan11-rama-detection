# Cierre manual de selección TINTO — 2026-10-29

El tesista pidió detener el entrenamiento para evitar el coste de esperar ocho
épocas sin mejora. Ambas corridas fueron interrumpidas (exit 130). No quedan
entrenamientos de esta selección activos y no se reanudarán automáticamente.

- Corrida CPU1: ocho épocas completas; interrumpida durante validación de la novena.
- Corrida CPU2: nueve épocas completas; interrumpida al comienzo de la décima.
- Mejor época observada en ambas: **5**, val_loss 0.026396678760647774.
- Ocho épocas completas comunes: historias exactamente iguales.
- Los checkpoints de la época 5 tienen idéntico contenido interno de pesos HDF5,
  verificado por SHA-256 sin cargar TensorFlow ni hacer más entrenamiento/inferencia.
- Se conservaron copias como `cierre_manual/corrida1/modelo_mejor_observado.keras`
  y la equivalente de corrida2, junto a historias parciales y metadatos.

La selección terminó por decisión de recursos, no por cumplir el EarlyStopping
original. No se afirma que la época 5 sea la mejor que habría alcanzado un
entrenamiento más largo. Los modelos son los mejores observados en este recorrido
truncado, con estado completo del checkpoint guardado al terminar esa época.

No se calculó precisión, recall o F1 contra L0, ni se evaluaron años 2023–2026.
No se presenta esta pérdida como porcentaje de errores. El registro de parada
manual conserva la regla original y añade esta decisión posterior explícitamente.
No se ejecutó una inferencia final adicional; la evidencia de reproducción aquí
es historia común y contenido de pesos guardados, no probabilidades finales.
