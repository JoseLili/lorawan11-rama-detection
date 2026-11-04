# Auditoría inicial de precisión y tiempo — 2026-10-30

Sin modelos cargados, predicciones ni entrenamiento. Dos ejecuciones locales CPU
con archivos idénticos por SHA-256. Programa: `auditar_precision_tiempo.py`.
Artefactos: `results/exploracion_tinto_2022/auditoria_precision_tiempo_20261030/`
desde la raíz del repositorio; incluye ambos informes, tabla de precisión por
estación/desfase, trazabilidad horaria, ejemplos NumPy y verificación de hashes.

## Resultados observados

- 31 objetivos × 365 días limpios 2022 = 11 315 ventanas diarias auditadas.
  Este universo incluye días de baja cobertura para revisar almacenamiento; no
  reemplaza las 9 661 estación-días comunes de evaluación predictiva.
- 4 616 520 características float32 recuperadas exactamente desde los píxeles
  del mapa D24 congelado, sin colisiones ni valores no finitos.
- 16 227 504 comparaciones numéricas entre 50/51, lectura real/lectura+1 y
  lectura real/lectura−1, sobre observaciones válidas 2022, 31 objetivos y los
  24 escalados de desfase del objetivo. Cero pares colapsados. Estas son pruebas
  numéricas repetidas por escalado, no ejemplos independientes de detección.
- Menor diferencia escalada 50→51: 0.0045417845249176025 en float32.
- Máximo error de conversión de imágenes de float64 a float32:
  5.952963277877643e-08 unidades de intensidad escalada.
- 225 valores fuera de [0,1], conservados sin clipping. Una visualización con
  escala fija puede saturarlos; el tensor entregado al modelo no los recorta.
- Las 8 760 horas de 2022 forman días de 24 y bloques de 12 sin huecos ni
  duplicados. Partición y recomposición exactas de todas las ventanas en dos
  mitades y en 24 pasos horarios.
- 1 095 transiciones 23→00 verificadas en la matriz continua 2020–2022.
  Seno/coseno coinciden con la hora del índice con tolerancia absoluta 1e-14.

## Alcance y límites

La prueba 50/51 conserva el perfil causal y sigma de cada contexto observado;
usa la fórmula real de `entradas_relativas`, incluyendo su conversión float32,
y el escalador congelado de T1. Comprueba el canal relativo objetivo, no ejecuta
una nueva inyección completa que recalcule a14 o perfiles futuros. Los cambios
±1 son controles numéricos; no definen un nuevo escenario de ataque ni umbral.

La precisión queda acreditada para esa cadena y rango auditados. No prueba que
la CNN clasifique correctamente una diferencia de 1 ppb, ni aumenta la precisión
instrumental de las mediciones. La normalización es la heredada del piloto,
no un nuevo ajuste del futuro experimento temporal.

D24 se verificó con el mapa existente. B12/S1 se verificaron como particiones
sin pérdida de los tensores de características: todavía NO tienen nuevos mapas
TINTO auditados. Su ajuste con entrenamiento y comprobaciones de rasterización
son la etapa 2. La continuidad del índice no significa que un modelo diario
observe el cambio de día: su estado se reinicia y esa transición queda fuera
de cada muestra. No se ha entrenado ni aprobado un híbrido.

## Siguiente paso

Construir mapas/escaladores B12/S1 con datos de ajuste únicamente y configuración
previamente congelada, verificando conservación tras rasterizar. Completar
manifiestos de etiquetas, soporte común y compatibilidad del control ED antes
de entrenar. Colab GPU queda autorizado por el tesista para esta línea; no fue
necesario usarlo en esta auditoría.
