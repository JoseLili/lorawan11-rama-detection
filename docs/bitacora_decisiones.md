# Bitácora de decisiones

## 2026-09-28 — Experimento de red independiente del piloto CCA

Se autoriza V4 por estación con p95 propio, como **experimento nuevo**;
no sustituye el corte operativo 22.6 ppb de CCA. Se reutilizan arquitectura,
ventana y entrenamiento, fijando semilla 42 por objetivo. El respaldo inicial
del perfil se ajusta sólo al train para no usar el test futuro. Se guarda
cada modelo y se reanudan checkpoints completos sin volver a entrenar.

Se evalúan 27 objetivos con datos en ambos tramos; seis carecen de test.
El análisis de red usa ataques aislados a cada mensaje observado, recalcula
el máximo conservando todos los competidores y cruza daño con detección
en el mismo mensaje. No asigna el recall promedio de una estación a un día.
Los mensajes faltantes o sin modelo no se contabilizan como detecciones.

El test común abarca 72 días (21/oct–31/dic), con máximo observado de 152 ppb.
No permite evaluar anulación de las contingencias reales de otros meses.
Las gráficas nuevas miden oportunidad real y daño no detectado empíricos;
se conservan aparte las anteriores de oportunidad ideal y riesgo compuesto.
Ver [protocolo y limitaciones](experimento_red_v4_p95.md) y notebook 09.

## 2026-09-28 — Umbral operativo fijo: 22.6 ppb

Se adopta **22.6 ppb por decisión metodológica**, con el modelo reproducible
de semilla 42 ya guardado en `results/modelo4_lstm.keras`. No se reentrena.
El detector operativo marca `abs(recibido - predicho) > 22.6` y lee el corte
de [umbral_operativo_cca.txt](../results/umbral_operativo_cca.txt).
El p95 calculado de **14.748354911804199 ppb** permanece intacto en
`umbral_p95_cca.txt`, como referencia de calibración, **no como punto de operación**.

La elección mantiene 78/78 ataques detectados (100 % de recall) para los
bits 6–7, sin pérdida frente al p95 recalibrado, y reduce falsas alarmas:

| Modelo y corte | FP / mensajes limpios del test atacado | Tasa FP |
|---|---:|---:|
| Modelo histórico, 22.6 ppb | 131 / 1606 | 8.16 % |
| Modelo semilla 42, p95 de 14.75 ppb | 350 / 1606 | 21.79 % |
| **Modelo semilla 42, operativo de 22.6 ppb** | **163 / 1606** | **10.15 %** |

Así se evita buena parte del incremento de falsas alarmas observado al pasar
de la referencia histórica al p95 recalibrado, sin beneficio de recall en
bits 6–7. **No se recupera exactamente el 8.16 % histórico**: modelo y corte
son factores distintos. El 21.38 % de la auditoría anterior tenía otro
denominador: 1684 mensajes de test completamente limpio, no 1606.

En bits menores sí disminuye el recall. Este punto preserva el mejor recall
observado para 6–7 entre los dos cortes comparados, **no demuestra un óptimo
global**. La decisión se tomó después de examinar el test; las métricas son
descriptivas y queda pendiente una validación independiente y acordar un
límite operativo aceptable de falsas alarmas.

La última sección del notebook 07 recalcula TP, FP, FN, TN, recall, precisión
y F2 para los mismos 78 ataques pareados por bit y guarda
[metricas_operativas_cca_bits_1_7.csv](../results/metricas_operativas_cca_bits_1_7.csv).
Las secciones p95 anteriores se conservan únicamente como auditoría.
Las dos figuras finales del notebook 08 consumen exclusivamente la tabla
operativa y rotulan el corte como **22.6 ppb**, nunca como p95 actual.
El umbral experimental de contingencia permanece en **155 ppb**.
Las figuras son indicadores compuestos de oportunidad anual de la red y
recall de CCA en test; no constituyen validación de detección multiestación.

## 2026-09-27 — Referencia CCA reproducible y evaluación sin reentrenamiento

Se fijó semilla 42 para el entrenamiento V4. Su p95 pasó de **22.6 a
14.75 ppb** (valor exacto persistido: **14.748354911804199**). Los recalls
de los bits 3 y 4 aumentaron de **9.0 a 25.6 %** y de **20.5 a 38.5 %**.
Esto mejora el recall, pero no demuestra una mejora global del detector.

Se decidió separar entrenamiento de evaluación: el notebook 07 carga por
defecto el modelo, preprocesamiento y p95 guardados. Sólo `REENTRENAR=True`
permite reentrenar V4 y actualizar la referencia. V1–V3, barrido y modelos
multiestación requieren además sus flags explícitos. Las figuras históricas
también quedan desactivadas por defecto. Si faltan artefactos o sus hashes
no coinciden, el notebook se detiene; nunca reentrena como alternativa.

### Control de falsos positivos con tasa de ataque cero

El antecedente **340/6788** corresponde a **IsolationForest**, con
`contamination=0.05`, sobre entrenamiento limpio (notebook 06), no al LSTM.
Se repitieron el generador `generar_dataset(..., tasa=0.0, seed=42)` y el
split cronológico, usando el LSTM cargado de disco y su p95, sin recalibrar.

| Detector / conjunto | Mensajes válidos | Evaluados | Sin ventana | FP | Tasa FP |
|---|---:|---:|---:|---:|---:|
| IsolationForest histórico / train | 6788 | 6788 | 0 | 340 | 5.01 % |
| LSTM actual / train limpio | 6788 | 6764 | 24 | 339 | 5.01 % |
| LSTM actual / test limpio | 1703 | 1684 | 19 | 360 | 21.38 % |

Las exclusiones son mensajes sin las 24 horas de contexto previo exigidas
por el protocolo; no se cuentan como verdaderos negativos. El ~5 % de
entrenamiento es esperable por la calibración p95 sobre ese conjunto:
no acredita generalización. La prueba limpia de test difiere del experimento
con tasa 5 %, que tenía 350 FP entre sus 1606 mensajes no atacados.

**Pendiente confirmar con el asesor que los falsos positivos no crecieron
en una proporción operativamente inaceptable.** Ya se midió un 21.38 % en
test limpio: no puede afirmarse aceptabilidad sólo por reproducir el 5.01 %
de entrenamiento. Hace falta acordar un límite aceptable y evaluar el
compromiso recall–falsas alarmas sin ajustar sobre el test.

Datos completos: [falsos_positivos_lstm_tasa0.csv](../results/falsos_positivos_lstm_tasa0.csv).
Referencia: [nota de semilla 42](referencia_lstm_cca_semilla42.md).
No se regeneraron las figuras para esta decisión.
