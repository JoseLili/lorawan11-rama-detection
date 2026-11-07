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


## 2026-11-04 — Línea base anclada en vecinas (Vb): candidata, no adoptada

Se exploraron tres líneas base alternativas para L0 con el modelo congelado, y después se reentrenó L0 con Vb (revisión LB1). Las dos fases tuvieron registro previo aprobado y se evaluaron solo en 2022.

- **No se adopta Vb todavía.** Con p99, ΔF̄ = +0.036 tiene un IC del 95 % que incluye valores menores de 0.
- **Se mantiene como candidata.** Reduce a menos de la mitad las falsas alarmas tras un episodio, mejora el PR-AUC con δ = 100 y 50 %, y su ventaja con p99.9 es grande. Pasa a la revisión LB2 (semillas y ensamble).
- **Se descartan** la compuerta Va (bloqueo) y el CUSUM con k común (heterogeneidad entre estaciones).
- **El umbral por estación (P4)** queda como mejora menor opcional.
- **El holdout del examen final** debe decidirse y registrarse antes de LB2.


## 2026-11-04 — Vb pasa a ser el detector candidato principal

**Decisión del tesista**, tomada después de ver los resultados de LB1 y declarada como tal. A partir de ahora, **L0 con la línea base anclada en vecinas (Vbr)** es el detector sobre el que se construyen LB2, D1 y el examen final. V0r (L0 con la base de 14 días) queda como comparador principal.

- **Motivo.** El asesor fijó como meta un F1 de aproximadamente 0.70–0.80. Con p99.9 y δ = 100 %, Vbr obtuvo F1 de 0.683 (recall 0.592, precisión 0.808), contra 0.530 de V0r. Con δ = 50 %: 0.488 contra 0.320.
- **Lo que no cambia.** Vbr **no está adoptado**: no pasó la regla registrada de LB1 con p99 (ΔF̄ = +0.036, IC [−0.018, +0.117]). Su adopción depende de LB2 (semillas) y del examen final sobre un holdout de un solo uso. Esta designación no reinterpreta la regla de LB1.
- **Cautelas a declarar.**
  - Los números son de 2022, que también fue validación del EarlyStopping, así que son optimistas para todos los modelos.
  - Hay una sola semilla, con E = 1.
  - Con δ = 20 % no hay mejora (F1 de 0.040 con p99.9).
- **Pendiente con el asesor:** definir la métrica de la meta (qué δ, estación-día o episodio, prevalencia y umbral) antes del examen final.


## 2026-11-04 — No se adopta la acumulación entre días (EP1)
EP1 no pasó su regla. Además, mostró que los puntajes diarios de L0 están autocorrelacionados en días limpios, así que acumular días también acumula la persistencia del clima. No se reabre sin un registro nuevo (EP1b), que calibre con días limpios fuera de la muestra y trate la autocorrelación. La prioridad pasa a LB2.


## 2026-11-04 — LB2: la ventaja de Vb es estable entre semillas; queda pendiente del examen final
Vbr le gana a V0r con p99 en las 5 semillas (+0.036 a +0.046), así que la ventaja no es azar del entrenamiento. El ensamble no pasó R2 porque su IC con p99 incluye valores menores de 0, y ese ancho viene de la muestra de 2022. **Ens-Vbr pasa a ser el candidato para el examen final**, con Ens-V0r como comparador. Sigue sin adoptarse hasta ese examen, que debe registrarse con su holdout antes de abrirlo.


## 2026-11-06 — Examen final: Vb no se adopta; el detector principal sigue siendo L0 con la base de 14 días
Según la regla registrada (dos pruebas, IC 97.5 %), Ens-Vbr no supera a Ens-V0r en 2017–2019, y el examen no se repite sobre estos años. Vb queda en la tesis como resultado negativo de generalización. Ens-V0r y el L0 de la rev. 14 obtienen, con p99.9 y δ = 100 %, F1 de 0.654 y 0.619 sobre un holdout de uso único. Esa es la cifra creíble para el paper, junto con la curva de operación completa.

## 2026-11-07 — Revisión del apego al protocolo

- **Contexto:** el tesista pidió revisar si el trabajo de línea base se había alejado de la metodología del repo.
- **Resultado:** LB1, EP1 y LB2 la respetan (elección en 2022, umbrales de 2023). El examen de 2017–2019 es adicional al protocolo, cuyo examen final ya era 2025–2026 (revisión 17). Se declararon cuatro desvíos y se agregó la comparación con la revisión 17, que se reproduce.
- **Decisión:** el resultado principal de la tesis es la revisión 17. La revisión 22 vuelve a las etapas del protocolo, con examen prospectivo en agosto–diciembre de 2026. Los años extra sólo entran como fondo de entrenamiento o, en el caso de 2017–2019, como desarrollo.

## 2026-11-07 — Revisión 22: elección en 2022

- **Decisión, por la regla registrada:** van al examen de despliegue **Vb-R y Vb-M1**, las dos con mayor ΔF̄ en p99. Avanzan también V0-M1 y Vb-M2. V0-M2 no avanza.
- **Antecedente que se reporta junto:** Vb-R es la receta de Ens-Vbr, no adoptado en 2017–2019.
- **Hallazgo:** más años de fondo mejoran a V0 en todas las semillas y suben la mejor época de 1 a 2–4.
