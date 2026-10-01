# Referencia vigente de CCA — semilla 42

**Actualización operativa, 2026-09-28:** se conserva el mismo modelo, pero
el corte vigente es **22.6 ppb**, leído de `results/umbral_operativo_cca.txt`.
Las métricas operativas están en
[metricas_operativas_cca_bits_1_7.csv](../results/metricas_operativas_cca_bits_1_7.csv).
El p95 de 14.75 y la tabla siguiente se conservan como auditoría de calibración,
**no son el punto operativo ni los valores de las figuras vigentes**.
La decisión y sus límites están en [la bitácora](bitacora_decisiones.md).

El modelo LSTM se reentrenó con semilla fija el **2026-09-27**. Los recalls
reportados en sesiones previas (9.0/20.5/84.6/98.7/100.0 para bits 3–7) no
son reproducibles a partir del entrenamiento original sin semilla fijada;
los valores vigentes desde ahora son los de este documento.

Se mantuvo el protocolo V4: 32 estaciones vecinas, 66 características,
ventana de 24 horas, perfil de 14 días, split cronológico 80/20, validación
interna de 20 %, batch 64, hasta 60 épocas y EarlyStopping. Se ejecutaron
30 épocas. La semilla 42 fija Python, NumPy, TensorFlow y Keras, con
operaciones deterministas. La semilla del ataque también es 42; tasa 5 %.

## Verificación y resultados de calibración p95 (no operativos)

Se ejecutaron los bloques de carga, ventanas, V4, calibración y ataques del
notebook 07 en **dos kernels limpios independientes**. No se repitieron los
entrenamientos históricos V1–V3 ni el barrido ni los modelos multiestación.
Los pesos, las predicciones, el p95 y las métricas fueron idénticos entre
ambas corridas. También se recargó cada `.keras` y se verificó igualdad
exacta de predicciones. Esto acredita reproducibilidad en el entorno
registrado, no igualdad entre cualquier versión o hardware.

**p95 = 14.7483549118042 ppb**, sobre residuos absolutos de todo el
entrenamiento limpio, incluido su tramo de validación interna.
Detección: `abs(recibido - predicho) > p95`. No detección: `<= p95`.
Este corte del detector no debe confundirse con **155 ppb**, el umbral
experimental de contingencia utilizado en ambas figuras.

| Bit | Delta ppb | Ataques | TP | FN | FP | TN | Recall % | Precisión % | F2 % | Recall histórico % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 78 | 14 | 64 | 350 | 1256 | 17.9 | 3.8 | 10.4 | No medido |
| 2 | 4 | 78 | 16 | 62 | 350 | 1256 | 20.5 | 4.4 | 11.8 | No medido |
| 3 | 8 | 78 | 20 | 58 | 350 | 1256 | 25.6 | 5.4 | 14.7 | 9.0 |
| 4 | 16 | 78 | 30 | 48 | 350 | 1256 | 38.5 | 7.9 | 21.7 | 20.5 |
| 5 | 32 | 78 | 73 | 5 | 350 | 1256 | 93.6 | 17.3 | 49.7 | 84.6 |
| 6 | 64 | 78 | 78 | 0 | 350 | 1256 | 100.0 | 18.2 | 52.7 | 98.7 |
| 7 | 128 | 78 | 78 | 0 | 350 | 1256 | 100.0 | 18.2 | 52.7 | 100.0 |

Los bits 1 y 2 se midieron después de los bits 3–7, sin reentrenar ni
recalibrar entre bits. Los conteos y fracciones sin redondear se conservan
en [recall_cca_bits_1_7.csv](../results/recall_cca_bits_1_7.csv).
La comparación histórica completa está en
[referencia_cca_p95.csv](../results/referencia_cca_p95.csv).

**Limitaciones:** 350/1606 = 21.8 % de falsas alarmas en mensajes no
atacados del test. Un recall mayor no prueba una mejora global del detector.
Los 78 ataques por bit son una muestra, no una garantía de detección universal.
Se conservó el perfil adaptativo heredado: su respaldo inicial usa un promedio
global de la serie, por lo que no debe presentarse como estrictamente causal.
Corregir ese respaldo sería otro protocolo y requeriría nueva evaluación.

## Figuras y tablas finales

Desde 2026-09-28 usan el **corte operativo fijo de 22.6 ppb** y la tabla
operativa, no los recalls de la tabla p95 anterior. Se cargó el mismo modelo
guardado sin reentrenar. Los FP son 163/1606 (10.15 %); el 8.16 % correspondía
al modelo histórico, no al modelo actual con este corte.

Las definiciones compartidas y la celda independiente de generación están al
final del [notebook 08](../notebooks/08_proximidad_umbrales.ipynb).
Se combinan los máximos diarios de las 33 estaciones durante 2025 (365 días)
con el recall de CCA del test. No es una medición conjunta evento por evento:
su transferencia entre estaciones y periodos es una hipótesis del indicador.

La oportunidad usa literalmente `(155 - 2**bit, 155]`, sin filtro por
estado del bit ni por episodios declarados. Este intervalo incluye lecturas
ya en 155 y no es el intervalo exacto para provocar una nueva excedencia
con una suma ideal. No debe llamarse conteo de contingencias falsas reales.

- [Riesgo compuesto por bit](img/riesgo_compuesto_por_bit.png) y
  [tabla completa](../results/riesgo_compuesto_por_bit.csv).
- [Oportunidad cruda frente a detección](img/oportunidad_cruda_por_bit.png) y
  [tabla completa](../results/oportunidad_cruda_por_bit.csv).

El máximo del riesgo compuesto operativo es **7.2 % en el bit 4**, sin imponerlo.
La oportunidad y el recall son monótonos no decrecientes en esta corrida.
El máximo interior aparece al multiplicar oportunidad por **1 − recall**,
no por recall. Se calculó con fracciones completas; el redondeo a un decimal
se aplica solamente a las figuras y tablas mostradas.

## Artefactos para reutilizar el mismo experimento

- [Modelo guardado](../results/modelo4_lstm.keras).
- [Umbral exacto](../results/umbral_p95_cca.txt).
- [Preprocesamiento](../results/preprocesamiento_modelo4_cca.npz): orden de
  vecinas, medias, escalas, perfil, timestamps y corte.
- [Metadatos](../results/metadatos_modelo4_cca.json): semillas, versiones,
  configuración y hashes del dataset y modelo.

Entorno de la corrida: Python 3.14.7, NumPy 2.5.3, TensorFlow 2.22.0-rc0 y
Keras 3.16.0.dev2026092204, CPU. Conservar estas versiones para replicación.
Los hashes del archivo `.keras` pueden diferir entre guardados por metadatos
de serialización aunque los pesos sean idénticos; la comparación entre las
dos corridas se realizó sobre sus arrays, no sobre esos hashes.
