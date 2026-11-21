# Piloto pareado congelado: TINTO-CNN-GRU-D2 y Ens-Vb-X

No se entrenó ni ajustó ningún modelo. Calibración2023; evaluación2025 con historia2020–2024. Primer calendario histórico final_2025_01; doce variantes de signo/intensidad fijadas antes de resultados. Ataques sostenidos entran en la historia de ambos modelos.

Soporte común2025: 3109 estación-días, 42 alteradas y 3067 normales por escenario. El calendario tiene 36 episodios antes de filtrar elegibilidad. No se equilibran clases.

## Recall y precisión con p99 (%)

| Escenario | Recall TINTO | Recall Ens-Vb-X | Precisión TINTO | Precisión Ens-Vb-X |
|---|---:|---:|---:|---:|
| d100_aumento | 71.43 | 100.00 | 28.30 | 58.33 |
| d100_reduccion | 7.14 | 95.24 | 3.85 | 54.05 |
| d50_aumento | 40.48 | 90.48 | 19.10 | 59.38 |
| d50_reduccion | 0.00 | 78.57 | 0.00 | 52.38 |
| d20_aumento | 11.90 | 35.71 | 6.49 | 41.67 |
| d20_reduccion | 0.00 | 23.81 | 0.00 | 30.30 |
| d5_aumento | 2.38 | 0.00 | 1.37 | 0.00 |
| d5_reduccion | 2.38 | 0.00 | 1.37 | 0.00 |
| ppb_5 | 2.38 | 7.14 | 1.37 | 15.00 |
| ppb_10 | 7.14 | 33.33 | 4.00 | 41.18 |
| ppb_20 | 33.33 | 97.62 | 15.73 | 61.19 |
| ppb_40 | 59.52 | 100.00 | 23.81 | 60.00 |

## Falsas alarmas en originales2025

| Percentil | N | Nominal teórico | TINTO observado | Ens-Vb-X observado |
|---|---:|---:|---:|---:|
| 95 | 3109 | 155.450 | 222 | 130 |
| 98 | 3109 | 62.180 | 102 | 44 |
| 99 | 3109 | 31.090 | 73 | 21 |
| 99.9 | 3109 | 3.109 | 7 | 0 |

La tabla anterior usa originales sin inyección. Los FP de metricas.csv cuentan días normales dentro de cada calendario alterado: incluyen posibles efectos posteriores al episodio y en otras estaciones. No intercambiar esos conteos para calcular precisión. Los percentiles son nominales de2023: la tasa efectiva de2025 puede diferir.

## Cobertura y complejidad

| Año | Detector | Días elegibles propios | Comunes |
|---|---|---:|---:|
| 2023 | Ens-Vb-X | 9097 | 3446 |
| 2023 | TINTO | 3446 | 3446 |
| 2025 | Ens-Vb-X | 8822 | 3109 |
| 2025 | TINTO | 3109 | 3109 |

TINTO:11104 parámetros, un modelo. Ens-Vb-X:115525 parámetros en cinco modelos de23105, además del cálculo de referencias vecinales y exclusión. No equivale a una razón de memoria/latencia. Bytes.keras y hashes en el paquete congelado.
Costos medidos en costos.csv incluyen preparación y puntuación en CPU. Ens-Vb-X puntúa más casos por su elegibilidad; en ataques usa caché incremental. TINTO puntúa sus casos elegibles completos. Estos tiempos no son un benchmark de latencia por entrada equivalente.

## Verificación y límites

ZIP/XLS contrastados con hashes del repositorio; matriz2020–2022 idéntica al hash histórico; calibración completa Ens-Vb-X reproduce los umbrales guardados dentro de1e-5; conteos de96 filas recalculados desde puntajes; pesos congelados intactos.
Un solo calendario, muestra positiva pequeña y ventanas dependientes. Año ya utilizado por el proyecto, no examen virgen. No declarar superioridad general ni elegir modificaciones con este piloto como prueba final. No cambiar umbrales para igualar retrospectivamente falsas alarmas2025.
La calibración se restringió al soporte común y por eso sus umbrales difieren de los históricos calculados sobre9097 casos. Las inyecciones nuevas no redondean ni mezclan signos, a diferencia del banco histórico. No comparar directamente con sus tablas agregadas.
El modelo TINTO recibió menos años y ejemplos de entrenamiento; no se reentrenó para igualarlos, por instrucción de congelamiento. La comparación evalúa los dos artefactos existentes, no una ablación de arquitectura.

## Reproducción

Protocolo: experiments/tinto_raw/protocolo_pareado_final.md. Ejecutar comparar_final.py con python -X utf8, --raw carpeta_ZIP y --salida carpeta_nueva. Los modelos fuente deben coincidir con hashes. No requiere entrenamiento.
