# Temporalidad explícita: dos días

4625 ajuste,884 selección,3449 evaluación. Dos réplicas por arquitectura y recarga verificadas. Cada secuencia tiene48 horas consecutivas, misma estación y cruce23→00 auditados contra la tabla original. No se modifica la convención horaria heredada.

## Recall p99 (%)

| Escenario | Autoencoder | CNN + GRU diaria | GRU horaria |
|---|---:|---:|---:|
| d100_aumento | 37.92 | 85.50 | 84.17 |
| d100_reduccion | 0.00 | 3.19 | 6.35 |
| d50_aumento | 12.73 | 43.81 | 41.17 |
| d50_reduccion | 0.03 | 0.38 | 0.93 |
| d20_aumento | 3.94 | 8.55 | 8.84 |
| d20_reduccion | 0.20 | 0.03 | 0.14 |
| d5_aumento | 1.45 | 2.03 | 1.94 |
| d5_reduccion | 0.67 | 0.32 | 0.41 |
| ppb_5 | 1.19 | 3.13 | 2.93 |
| ppb_10 | 1.71 | 9.51 | 9.63 |
| ppb_20 | 2.06 | 70.08 | 64.19 |
| ppb_40 | 1.88 | 100.00 | 100.00 |

## Falsas alarmas

Por detector, sobre3449 originales: p95 teóricas172.45, p98 68.98, p99 34.49,p99.9 3.449. Conteos observados y umbrales individuales en umbrales.csv. No sumar escenarios ni modelos.

## Alcance

Nota posterior: conteos observados por detector en calibración p95/p98/p99/p99.9:
172/68/34/3. Los resultados completos y hashes se verificaron después de un fallo
de impresión final en consola Windows (Unicode de la flecha); el fallo ocurrió
después de guardar todos los artefactos. Reproducir con `python -X utf8`.

La prueba de invertir48 horas aumenta MSE0.01356→0.02155; invertir días en
CNN-GRU diaria lo aumenta0.01273→0.01644. Sensibilidad al orden y recencia,
no prueba aislada de la transición de medianoche. Las dos réplicas de cada
arquitectura tienen pesos, historias y predicciones idénticos.

Historia original y ataques solo al objetivo: inicio aislado. No evalúa ataques sostenidos. La GRU horaria recibe48 valores en orden; la CNN+GRU resume cada día y tiene dos pasos. La inversión de orden es diagnóstico de sensibilidad y también altera recencia: no demuestra comprensión específica de medianoche. TINTO es reversible en el brazo horario, no se afirma ventaja de imágenes.
Calibración y evaluación originales reutilizan2022. Pares50/50, ventanas solapadas. Autoencoder entrenado en otra muestra y tarea; comparar aquí no aísla causalmente temporalidad. Las dos arquitecturas nuevas comparten soporte y tarea, pero distinta capacidad. Sin años2023–2026.
