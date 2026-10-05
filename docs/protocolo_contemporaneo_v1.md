# Protocolo: vecinas de la misma hora (variante contemporánea) y línea base lineal

**Fecha:** 2026-10-04. **Identificador:** `v4c_multianual_33_p95cal2023_v1`.
**Estado:** fijado antes de entrenar; no contiene resultados.
**Revisión 1 (2026-10-04, antes de entrenar):** se amplía la rejilla de α. En una corrida
de humo, CCA eligió α = 1000, el extremo de la rejilla original; en 2022 (validación, no
prueba) el MSE de CCA, PED y TLI tiene su mínimo entre 1000 y 10 000. Se agregan 300,
3000, 10 000 y 100 000 para que el óptimo quede dentro. Observación registrada en la misma
revisión: con todas las horas de 2022, `lineal_t` de CCA tuvo MSE 162.6 frente a 154.0 del
V4 (fase 1); la ganancia de la exploración (horas con vecinas completas) puede no
sostenerse. No se cambia nada más.
**Origen:** pregunta J1 del asesor («probar vecinas del instante actual») y exploración
del 2026-10-04 sobre 2023 (no sobre la prueba): con 8 vecinas de la misma hora, una
regresión lineal redujo el MAE de CCA de 6.8 (V4) a 4.2 ppb en las horas con vecinas
completas. Esa exploración motiva el experimento; no es un resultado.
**Referencia que NO se modifica:** `v4_multianual_33_p95cal2023_v1`
([protocolo_lstm_v4_multianual.md](protocolo_lstm_v4_multianual.md)) y sus modelos en
`results/lstm_v4_multianual_v1/`.

## 1. Preguntas

1. ¿Usar la lectura de las vecinas **a la misma hora t** reduce el error de predicción y
   el umbral de alerta frente al V4 (que usa hasta t−1)?
2. ¿Eso mejora la detección de los bits del punto ideal (3–5) y de las desactivaciones de
   fase 1, sin aumentar las falsas alarmas?
3. ¿Hace falta el LSTM o una regresión lineal con la misma información rinde igual?
4. ¿Cuánto pierde cada detector si el atacante voltea el mismo bit en **todas** las
   estaciones a la misma hora? (La variante contemporánea depende de que las vecinas
   digan la verdad, y el atacante entre NS y AS ve el tráfico de todas.)

No se promete mejora. Si la variante no mejora, o mejora sólo frente al atacante de un
mensaje y empeora frente al simultáneo, ése es el resultado.

## 2. Lo que NO cambia respecto al V4 multianual

Se reutiliza sin modificación todo el §2–§6 del protocolo V4 multianual:

- Etapas por fecha del objetivo: ajuste inicial 2020–2021, validación 2022, ajuste
  definitivo 2020–2022, calibración 2023, prueba 2024 / 2025 / 2026 (ene–jul).
- Matriz fija de 33 estaciones, canal inactivo XAL, sin interpolación.
- Normalización sólo con las etapas de ajuste; perfil causal de 14 días con respaldo.
- Elegibilidad: los mismos 31 objetivos (HGM y XAL fuera; AJM, INN y TLI de baja
  representatividad, reportados aparte).
- Calibración: p95 de |residuo| en 2023, alerta si |residuo| > umbral.
- Evaluación de un mensaje: muestra pareada al 5 % (bits 0–7, semilla 42, mismo plan) y
  barrido exhaustivo; mismas definiciones de daño (§7–§8).

## 3. Lo que cambia

### 3.1 Variante A — `lstm_t` (LSTM contemporáneo)

Idéntica al V4 salvo la ventana: filas **t−23 … t** de las 32 vecinas en lugar de
t−24 … t−1. Sigue siendo 24 × 66; la última fila contiene a las vecinas a la hora t
(valores normalizados, máscaras y seno/coseno de la hora t). La estación objetivo
**nunca** es entrada. Misma arquitectura, semilla 42, `shuffle=True`, selección de E con
2022 (máximo 60, paciencia 8) y reentrenamiento desde cero con 2020–2022 durante E
épocas. Implementación: `entrenar_objetivo(..., incluir_t=True)`.

### 3.2 Variante B — `lineal_t` (línea base lineal)

Regresión ridge con **sólo la fila t**: las mismas 66 características (32 valores
normalizados con relleno 0, 32 máscaras, seno/coseno), objetivo `lectura − perfil`.

- α se elige en la rejilla fija {0.01, 0.1, 1, 10, 100, 300, 1000, 3000, 10 000, 100 000}
  (revisión 1) por el menor MSE en 2022,
  ajustando con 2020–2021 y la normalización inicial.
- Con el α elegido se reajusta con 2020–2022 y la normalización definitiva.
- Coeficientes guardados en `modelo_lineal.npz` (sin pickle). Determinista.

### 3.3 Atacante simultáneo (evaluación nueva, para V4, `lstm_t` y `lineal_t`)

- En cada año de prueba se elige al azar el 5 % de las **horas** (no de los mensajes),
  con un generador `default_rng([42, 777, año])`, guardado como plan.
- En cada hora elegida se voltea **el mismo bit k** en todos los mensajes observados de las
  33 estaciones, con la cadena real cotejada con XOR. Un atacante ciego: el signo del
  cambio depende de cada lectura.
- Con la matriz atacada se recalculan, para cada objetivo con modelo, el perfil (que
  también ve las lecturas atacadas de su pasado), las entradas y las predicciones de todo
  el año. Umbrales y modelos **no** cambian.
- Positivo = mensaje del objetivo en una hora atacada. Se reportan TP, FP, FN, TN, recall,
  precisión, F2 y FPR por bit, año y grupo, micro y macro.
- Es más realista que el ataque aislado (contamina ventanas y perfiles), pero sigue siendo
  ciego: no modela a un atacante que elija estaciones o signos.

## 4. Comparaciones permitidas

- Las tres familias (V4, `lstm_t`, `lineal_t`) en las mismas lecturas, etapas, planes de
  ataque y umbral p95 de 2023 propio de cada modelo/estación.
- Recall siempre junto con FPR y precisión. Una ganancia de recall con más falsas alarmas
  no se reporta como mejora.
- Agregados micro y macro, con `principal` y `baja_representatividad` separados.
- Las desactivaciones se reportan **condicionadas a los días con excedencia real**.
- Una diferencia se describe como diferencia observada en este conjunto; no se afirma
  significancia estadística sin análisis adicional.

## 5. Lo que no se hace

- No se modifica ningún archivo de `results/lstm_v4_multianual_v1/` salvo leer modelos.
- No se ajusta nada (α, E, umbrales, estaciones, vecinas) mirando 2024–2026.
- No se seleccionan vecinas por distancia ni por correlación: se usan las 32, como en V4.
- No se prueba CNN-1D ni otros tamaños de ventana en este protocolo.

## 6. Reproducibilidad y salidas

- `fijar_semilla(42)` inmediatamente antes de construir y entrenar cada LSTM (CLAUDE.md).
- Antes de aceptar: reentrenar `lstm_t` de CCA en `verificacion/` y comparar E, pesos, p95
  y predicciones; `lineal_t` es determinista y se verifica igual.
- La evaluación se ejecuta con el script `experiments/contemporaneo/ejecutar.py`,
  reanudable (salta lo ya guardado) y con registro en la bitácora.

```text
results/contemporaneo_v1/
  protocolo.json, bitacora.csv, ejecucion.log
  lstm_t/estaciones/<EST>/ ...         # mismo formato que el V4 multianual
  lstm_t/verificacion/CCA/
  lineal_t/estaciones/<EST>/ ...       # modelo_lineal.npz en lugar de modelo.keras
  <familia>/metricas_limpias.csv, metricas_pareadas*.csv, resumen_dano_*.csv
  simultaneo/plan_<año>.csv, metricas_simultaneo.csv, metricas_simultaneo_agregadas.csv
```

Las predicciones y los eventos de daño quedan fuera de git (se regeneran desde los modelos).

## 7. Riesgos declarados

- La exploración usó horas con 8 vecinas completas; la ganancia real en todas las horas
  puede ser menor.
- Entre 00:00 y 02:00 faltan muchas estaciones a la vez: ahí la información contemporánea
  casi no existe y la variante debería rendir como el V4.
- Operativamente, revisar la lectura de la hora t exige esperar los mensajes de las vecinas
  de esa hora (minutos).
- Un atacante que comprometa estaciones de forma coordinada y elija signos no está
  cubierto por este protocolo.
