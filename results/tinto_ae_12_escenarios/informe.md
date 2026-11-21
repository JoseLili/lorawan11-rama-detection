# Autoencoder congelado: 12 escenarios

7154 originales estación-día de 2022; sin reentrenamiento. Dos modelos con pesos idénticos producen reconstrucciones idénticas en los 13 conjuntos (original y 12 alteraciones).

## Recall (%)

| Escenario | p95 | p98 | p99 | p99.9 |
|---|---:|---:|---:|---:|
| d100_aumento | 60.092 | 45.946 | 35.505 | 16.368 |
| d100_reduccion | 0.000 | 0.000 | 0.000 | 0.000 |
| d50_aumento | 29.368 | 18.102 | 12.091 | 3.467 |
| d50_reduccion | 0.266 | 0.042 | 0.014 | 0.000 |
| d20_aumento | 12.413 | 6.500 | 3.606 | 0.797 |
| d20_reduccion | 1.398 | 0.475 | 0.210 | 0.014 |
| d5_aumento | 6.598 | 2.656 | 1.426 | 0.238 |
| d5_reduccion | 3.550 | 1.440 | 0.741 | 0.042 |
| ppb_5 | 6.039 | 2.264 | 1.160 | 0.084 |
| ppb_10 | 8.037 | 3.033 | 1.580 | 0.154 |
| ppb_20 | 8.778 | 3.578 | 1.831 | 0.252 |
| ppb_40 | 9.128 | 3.704 | 1.663 | 0.238 |

## Calibración

- p95.0: umbral 0.00324589456; 357/7154 alertas (4.9902%).
- p98.0: umbral 0.00427658297; 143/7154 alertas (1.9989%).
- p99.0: umbral 0.00518831704; 71/7154 alertas (0.9925%).
- p99.9: umbral 0.00822170824; 7/7154 alertas (0.0978%).

## Límites e interpretación

Nota de presentación posterior, sin recalibración ni nuevas inferencias:

| Percentil | Tasa nominal | Conteo teórico sobre 7154 | Alertas originales observadas |
|---|---:|---:|---:|
| p95 | 5% | 357.70 | 357 |
| p98 | 2% | 143.08 | 143 |
| p99 | 1% | 71.54 | 71 |
| p99.9 | 0.1% | 7.154 | 7 |

Conteo teórico = N*(1-p/100), referencia nominal, no garantía futura. La unidad
es imagen estación-día, no hora ni episodio. Con la regla empírica utilizada, el
conteo de calibración no excede la parte entera del objetivo, y puede ser menor
por empates. Los mismos originales se comparten en los 12 escenarios: no sumar
estos conteos doce veces. Tampoco sumar percentiles, cuyas alertas están anidadas.

Los umbrales son globales, calibrados en los mismos originales 2022; falsas alarmas descriptivas, no estimación independiente. Pares 50/50 por escenario: precisión y F1 no son valores operativos. Original no significa ausencia garantizada de anomalías reales.
Delta de reducción usa división entre 1+delta, no resta del porcentaje. Todas las alteraciones abarcan el día completo. No hay calendarios L0 ni años 2023–2026.
La comparación pareada cuantifica si la alteración reduce el error. El diagnóstico por hora/estación conserva errores escalados, MAE en ppb y sesgo de reconstrucción. No se cambió score, modelo ni umbrales para mejorar los resultados. Estos datos no demuestran que la falta de contexto sea la causa.

## Archivos

- metricas.csv: 48 combinaciones; metricas_estacion.csv: desglose con umbrales globales.
- scores.csv y comparacion_pareada.csv: puntuaciones y cambios por escenario.
- diagnostico_hora_estacion.csv: errores por hora y estación, incluyendo agregado TODAS.
- lecturas_y_reconstrucciones.npz: originales, alterados y reconstrucciones en ppb; orden de manifiesto.csv.
- fuentes.json, verificaciones.json, entorno.txt y checksums.json: trazabilidad y verificación.

Reproducción: python experiments/tinto_raw/evaluar_12.py --salida results/NUEVA_CARPETA. Rechaza sobrescribir resultados.
