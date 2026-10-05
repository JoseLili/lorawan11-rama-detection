# Protocolo: entradas restringidas a las vecinas geográficamente cercanas

**Fecha:** 2026-10-04. **Identificador:** `v4k_multianual_33_p95cal2023_v1`.
**Estado:** fijado antes de entrenar; no contiene resultados.
**Origen:** propuesta del tesista: que el detector use las estaciones cercanas y no
reciba ruido de estaciones lejanas o de entornos distintos (bosque frente a tráfico).
Exploración del 2026-10-04 con todas las horas de 2020–2022 (no la prueba): el parecido
de las desviaciones entre estaciones cae con la distancia (correlación con 1 h de retraso:
mediana 0.75 a menos de 10 km, 0.48 a más de 30 km; correlación con la distancia −0.89;
con la diferencia de altitud −0.55). La exploración motiva el experimento; no es un
resultado.
**Referencias que NO se modifican:** V4 multianual (`results/lstm_v4_multianual_v1/`) y la
variante contemporánea (`results/contemporaneo_v1/`).

## 1. Preguntas

1. ¿Restringir las entradas a las k vecinas más cercanas reduce el error y el umbral
   frente al V4 (las 32)?
2. ¿Mejora la detección de los bits 3–5 y de las desactivaciones sin subir las falsas
   alarmas?
3. ¿Qué k elige cada estación y se relaciona con su ubicación (estaciones aisladas o de
   montaña frente a estaciones del valle)?
4. ¿Cambia la robustez frente al atacante simultáneo?

Hipótesis: el V4 aprende lo útil en 1–2 épocas y luego memoriza; menos entradas
irrelevantes podrían reducir ese sobreajuste. Expectativa: mejora modesta. Si no mejora,
ése es el resultado.

## 2. Lo que NO cambia

Todo el protocolo V4 multianual §2–§8: etapas (2020–21 / 2022 / 2020–22 / 2023 /
2024–2026), matriz fija, canal inactivo XAL, normalización, perfil causal, contexto
**pasado** t−24 … t−1, arquitectura LSTM (64, dropout 0.2, densa 32), semilla 42,
`shuffle=True`, selección de E con 2022 (máx. 60, paciencia 8), reentrenamiento desde
cero 2020–2022 durante E épocas, calibración p95 en 2023, mismos 31 objetivos y misma
evaluación de un mensaje y simultánea (mismas semillas y planes).

## 3. Lo que cambia

### 3.1 Vecinas candidatas y orden

- Distancia: haversine entre las coordenadas del catálogo oficial del SIMAT
  (`results/inventario_multianual/estaciones_geografia.csv`), radio 6371 km.
- Candidatas de cada objetivo: las otras estaciones de la matriz **activas** en el ajuste
  definitivo (se excluye XAL, canal inactivo, para no gastar un lugar en un canal siempre
  vacío). Orden por distancia creciente; empates por clave de estación.
- No se usa correlación ni ningún dato de 2023–2026 para ordenar o elegir vecinas.

### 3.2 Selección de k por objetivo (con 2022)

- Rejilla fija k ∈ {4, 8, 16, 32}. k = 32 es exactamente el V4 (todas las vecinas): no se
  reentrena; se toma su `val_loss` mínimo de la fase 1 ya guardado.
- Para k ∈ {4, 8, 16}: fase 1 del V4 (ajuste 2020–2021, validación 2022, EarlyStopping)
  con sólo esas k vecinas (2k + 2 características por hora).
- k* = el de menor `val_loss` mínimo; en empate, el k menor.
- Si k* = 32, el modelo del objetivo **es el V4**: se copian sus artefactos y se anota
  `k = 32 (V4)`. Si k* < 32, se entrena el modelo definitivo con esas vecinas
  (`entrenar_objetivo(..., vecinas=...)`), que repite la fase 1 (determinista) y luego la
  fase 2 durante E épocas.
- Se guarda por objetivo `seleccion_k.csv` (k, val_loss mínimo, E, vecinas).

## 4. Evaluación y comparaciones

- Un mensaje (muestra pareada al 5 % y barrido) y atacante simultáneo, con las mismas
  semillas y planes que la variante contemporánea; el V4 simultáneo ya calculado en
  `results/contemporaneo_v1/simultaneo/` sirve de referencia (mismo plan).
- Recall siempre con FPR y precisión; micro y macro; `principal` y
  `baja_representatividad` aparte; desactivaciones condicionadas a días con excedencia.
- Diferencias descritas como observadas en este conjunto, sin afirmar significancia.

## 5. Lo que no se hace

No se ajusta k, E ni umbrales mirando 2024–2026; no se seleccionan vecinas por
correlación; no se agregan datos de uso de suelo (no disponibles); no se combinan con la
hora t ni con otras variantes.

## 6. Reproducibilidad y salidas

- `fijar_semilla(42)` antes de construir y entrenar cada LSTM (CLAUDE.md).
- Verificación: reentrenar en `verificacion/` el primer objetivo con k* < 32 (CCA si
  aplica) y exigir E, pesos, p95 y predicciones idénticos; si difiere, el script se detiene.
- Ejecución: `experiments/vecinas/ejecutar.py` (reanudable, con bitácora y log).

```text
results/vecinas_cercanas_v1/
  protocolo.json, bitacora.csv, ejecucion.log
  estaciones/<EST>/ seleccion_k.csv, seleccion_k/<k>/historia_seleccion.csv, modelo...
  verificacion/<EST>/
  metricas_*.csv, resumen_dano_*.csv, cobertura_prueba.csv
  simultaneo/plan_<año>.csv, parciales/, metricas_simultaneo*.csv
```

Predicciones y eventos quedan fuera de git (se regeneran desde los modelos).

## 7. Riesgos declarados

- La fase 1 se repite para varios k: la selección usa más veces 2022, lo que aumenta el
  riesgo de elegir k por ruido de validación; por eso la rejilla es corta y fija.
- Con k pequeño, los faltantes simultáneos de pocas vecinas dejan al modelo sin
  información (horas 00–02, rachas largas); el V4 tiene más redundancia.
- La distancia es un sustituto imperfecto del «tipo de zona»; no se dispone de uso de suelo.

## 8. Ejecución y resultado (2026-10-05)

Ejecutado completo (interrumpido por apagado y reanudado sin borrar artefactos; FAC
repitió su selección determinista). CCA (k = 4) reproducible. k elegido: 4 en 21
estaciones, 8 en 7, 16 en 3, 32 en ninguna. Resultado **mixto**: MAE de calibración −3 %,
recall de un mensaje +1.5 a +3.6 puntos en bits 4–5, robusto al atacante simultáneo,
pero más días con cambio de banda de red sin alerta (2025, bit 5: 63 → 80). Se conserva
el V4. Detalle: notebook 16 y `docs/progreso.md`.

