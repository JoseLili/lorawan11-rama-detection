# Predicción temporal de siete días

Diagnóstico exploratorio: 139 ajuste, 38 selección, 175 evaluación. Ninguna secuencia elegible en 2020. Dos corridas idénticas; modelos recargados y verificados. Historia original, ataque solo al objetivo.

## Recall (%) en soporte común

| Escenario | AE p95 | Temporal p95 | AE p99 | Temporal p99 |
|---|---:|---:|---:|---:|
| d100_aumento | 81.71 | 72.00 | 65.14 | 51.43 |
| d100_reduccion | 0.00 | 0.57 | 0.00 | 0.00 |
| d50_aumento | 50.29 | 33.71 | 32.00 | 17.14 |
| d50_reduccion | 0.00 | 0.00 | 0.00 | 0.00 |
| d20_aumento | 18.29 | 10.86 | 7.43 | 6.29 |
| d20_reduccion | 0.00 | 0.57 | 0.00 | 0.00 |
| d5_aumento | 6.29 | 6.29 | 1.14 | 2.29 |
| d5_reduccion | 2.29 | 4.00 | 0.00 | 0.57 |
| ppb_5 | 9.71 | 7.43 | 1.71 | 3.43 |
| ppb_10 | 20.00 | 10.86 | 8.57 | 5.71 |
| ppb_20 | 20.00 | 41.71 | 9.14 | 15.43 |
| ppb_40 | 20.57 | 100.00 | 6.86 | 100.00 |

## Falsas alarmas

| Detector | Percentil | N | Teóricas | Observadas |
|---|---:|---:|---:|---:|
| temporal7 | 95.0 | 175 | 8.750 | 8 |
| temporal7 | 98.0 | 175 | 3.500 | 3 |
| temporal7 | 99.0 | 175 | 1.750 | 1 |
| temporal7 | 99.9 | 175 | 0.175 | 0 |
| autoencoder | 95.0 | 175 | 8.750 | 8 |
| autoencoder | 98.0 | 175 | 3.500 | 3 |
| autoencoder | 99.0 | 175 | 1.750 | 1 |
| autoencoder | 99.9 | 175 | 0.175 | 0 |

## Límites

Lectura posterior: el temporal mejora mucho ante +40ppb y parcialmente ante
+20ppb, pero no mejora globalmente. Pierde recall en aumentos porcentuales grandes
y no resuelve las reducciones. La evaluación abarca11 estaciones:91/175 ejemplos
son deLLA (52%). El autoencoder también cambia notablemente de rendimiento al
restringirse a este soporte: no comparar estas tasas con la tabla de7154 bases.
Early stopping tras10 épocas, mejor época5 en ambas corridas.

Incidente técnico: el intento en la carpeta sin sufijo `_final` falló al clonar
el modelo compilado por la pérdida personalizada. Se cambió solo el guardado,
se conservó el intento y se repitieron ambas corridas con configuración intacta.

Calibración y evaluación originales reutilizan2022. p99.9 permite cero alertas en175 casos y se apoya en el máximo; no garantiza cero falsas alarmas futuras. Ventanas solapadas, pocas estaciones, sin intervalos de confianza. Pares artificiales50/50. No prueba independiente ni evidencia causal de temporalidad: cambian objetivo, canales y muestra de entrenamiento. Modelo temporal ve139 bases, autoencoder previo10334. Predicción no usa el objetivo; ataques sostenidos que contaminan historia quedan pendientes. No abrir2023–2026.

Precisión, recall, F1 y conteos completos en metricas.csv (96 filas). Manifiesto registra índices de los siete antecedentes. Archivos originales preservados.
