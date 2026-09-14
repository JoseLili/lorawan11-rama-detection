# Detección con LSTM multiestación — resultados

Notebook: `07_multiestacion.ipynb`. Resultados: `results/deteccion_lstm.csv`.

---

## 1. Configuración evaluada

**Modelo v4** (perfil adaptativo de 14 días), el único de las cuatro
iteraciones sin sesgo sistemático en la franja de mayor relevancia.

```
Entrada:   24 h × 66 columnas
           32 estaciones vecinas (valores normalizados)
         + 32 máscaras de validez
         +  2 de hora del día (seno, coseno)

Salida:    desviación respecto al perfil adaptativo de CCA

Detección: residuo |x_recibido − x_predicho| > umbral
```

**CCA se excluye de su propia entrada.** Dos razones: evitar que el modelo copie
el valor, e impedir que un ataque sostenido contamine la ventana y el modelo
aprenda a predecir el valor ya manipulado.

**Sólo se ataca CCA.** Las 32 vecinas permanecen íntegras, conforme a la
premisa del escenario: el adversario compromete un único nodo.

Entrenamiento no supervisado: el modelo nunca ve un ataque.

---

## 2. Calibración del umbral

El modelo produce un residuo continuo. Convertirlo en decisión binaria exige un
corte, y ese corte se calcula sobre los residuos del **conjunto de
entrenamiento limpio** — nunca sobre datos atacados, información de la que no
se dispone en producción.

| Percentil | Umbral | Interpretación |
|---|---|---|
| 90 | 17.2 ppb | Marca el 10% más anómalo de la operación normal |
| 95 | 22.6 ppb | Marca el 5% |
| 97 | 26.9 ppb | Marca el 3% |
| 99 | 36.6 ppb | Marca el 1% |

Es la misma limitación que el parámetro `contamination` del IsolationForest,
con una ventaja: permite reportar el compromiso completo en lugar de un único
punto de operación.

---

## 3. Resultado principal

Recall sobre la clase atacada, tasa de ataque del 5%, conjunto de prueba
(nov–dic, 1,684 ventanas).

| bit | Δ ppb | p90 | p95 | p97 | p99 |
|---|---|---|---|---|---|
| 3 | 8 | 16.7% | 9.0% | 2.6% | 2.6% |
| 4 | 16 | 33.3% | 20.5% | 11.5% | 5.1% |
| **5** | **32** | **89.7%** | **84.6%** | 67.9% | 20.5% |
| **6** | **64** | **100%** | **98.7%** | **98.7%** | **97.4%** |
| 7 | 128 | 100% | 100% | 100% | 100% |

### Comparación con la Capa 1

La Capa 1 (notebook 06) evalúa lecturas aisladas mediante clasificadores
supervisados sobre `received_value` y la hora.

| bit | Δ ppb | Capa 1 | LSTM p95 | Diferencia |
|---|---|---|---|---|
| 3 | 8 | 4.3% | 9.0% | +4.7 |
| 4 | 16 | 8.6% | 20.5% | +11.9 |
| **5** | **32** | **41.4%** | **84.6%** | **+43.2** |
| **6** | **64** | **72.9%** | **98.7%** | **+25.8** |
| 7 | 128 | 97.1% | 100% | +2.9 |

**El bit 5 duplica su detección.** El bit 6 alcanza el 98.7%.

La mejora se concentra precisamente en la región que el notebook 06 identificó
como zona explotable.

---

## 4. La zona explotable se cierra

Producto de la tasa de daño (notebook 05) por la fracción no detectada.

**Con Capa 1:**

| bit | Daño | Detección | Daño no detectado |
|---|---|---|---|
| 4 | 11.4% | 8.6% | 10.4% |
| 5 | 29.0% | 41.4% | 17.0% |
| **6** | **100%** | **72.9%** | **27.1%** |
| 7 | 100% | 97.1% | 2.9% |

**Con LSTM espacial (p95):**

| bit | Daño | Detección | Daño no detectado |
|---|---|---|---|
| **4** | **11.4%** | **20.5%** | **9.1%** |
| 5 | 29.0% | 84.6% | 4.5% |
| 6 | 100% | 98.7% | 1.3% |
| 7 | 100% | 100% | 0% |

**El óptimo del adversario se desplaza del bit 6 (27.1%) al bit 4 (9.1%)**, una
reducción de dos tercios. Y en el bit 4 el daño absoluto es marginal: sólo el
11.4% de los ataques cambia la banda reportada.

El adversario pierde su posición ventajosa.

---

## 5. Análisis del compromiso recall–precisión

### Bit 6: sin compromiso

| Percentil | Umbral | Recall | Precision | F2 | FP |
|---|---|---|---|---|---|
| 90 | 17.2 | 100% | 23.6% | 60.7 | 252 |
| 95 | 22.6 | 98.7% | 37.0% | 74.0 | 131 |
| 97 | 26.9 | 98.7% | 48.1% | 81.6 | 83 |
| **99** | **36.6** | **97.4%** | **67.9%** | **89.6** | **36** |

**El umbral más estricto domina en todas las métricas salvo un 2.6% de recall.**

La causa: un desplazamiento de 64 ppb produce residuos que superan ampliamente
incluso el percentil 99 (36.6 ppb). No existe compromiso que negociar.

Punto de operación recomendado: **p99** — 97.4% de recall con 67.9% de
precisión y 36 falsas alarmas.

### Bit 5: compromiso real

| Percentil | Umbral | Recall | Precision | F2 | FP |
|---|---|---|---|---|---|
| 90 | 17.2 | 89.7% | 21.7% | 55.2 | 252 |
| **95** | **22.6** | **84.6%** | **33.5%** | **64.8** | **131** |
| 97 | 26.9 | 67.9% | 39.0% | 59.2 | 83 |
| 99 | 36.6 | 20.5% | 30.8% | 22.0 | 36 |

El máximo de F2 se sitúa en **p95**. Al ponderar el recall al doble, prefiere
84.6% de detección aunque cueste precisión.

**El desplome en p99 es revelador:** el umbral (36.6 ppb) excede la magnitud del
ataque (32 ppb). Sólo se detectan los casos en que el residuo del modelo ya era
elevado por causas propias.

### Bit 4: fuera de alcance

Precisión entre 9.4% y 10.9% en todos los percentiles, frente a una prevalencia
del 5%. Apenas el doble del azar.

**El desplazamiento de 16 ppb es indistinguible del ruido del modelo**
(σ ≈ 13 ppb, y ≈ 19 ppb en el pico vespertino). Era el comportamiento previsto.

No constituye un fallo: es el límite de resolución del método.

---

## 6. Selección del punto de operación

El percentil óptimo depende del bit atacado:

| Bit | Percentil con mejor F2 |
|---|---|
| 5 | p95 |
| 6 | p99 |

**En producción no se conoce el bit atacado**, por lo que debe fijarse un único
umbral.

**Se adopta p95** como compromiso: 84.6% de recall en el bit 5 y 98.7% en el
bit 6, con 131 falsos positivos.

---

## 7. Limitaciones

### Falsos positivos

131 falsos positivos sobre 1,684 horas de prueba equivalen a **aproximadamente
2 alarmas falsas diarias en una sola estación**. Escalado a 33 estaciones, el
volumen sería inmanejable sin agregación o verificación adicional.

Es la contrapartida directa del umbral fijado en p95.

### Límite de resolución

El método no distingue desplazamientos comparables al ruido del modelo. Con
σ ≈ 13 ppb, los ataques por debajo de ~20 ppb quedan fuera de alcance.

Reducir ese ruido exigiría mejorar la precisión de predicción, que las cuatro
iteraciones documentadas no lograron llevar por debajo de ~9 ppb de MAE.

### Supuesto de nodo único comprometido

El diseño asume que el adversario ataca una sola estación. Si comprometiera
varias de forma coordinada, la coherencia espacial dejaría de delatarlo.

Esta limitación es inherente al enfoque y debe declararse.

### Un solo tipo de adversario

Evaluado únicamente contra el atacante ciego de bit fijo. Pendiente: el
adversario de magnitud variable, que degradó la Capa 1 de 41.4% a 11.4%.

---

## 8. Conclusión

> El contexto espacial permite detectar manipulaciones que resultan
> indistinguibles al evaluar lecturas aisladas. Un desplazamiento de 32 ppb se
> confunde con la variabilidad legítima del ozono cuando se observa un único
> valor, pero rompe la coherencia entre estaciones cuando se contrasta con el
> resto de la red.
>
> La detección del bit 5 pasa de 41.4% a 84.6%, y la del bit 6 de 72.9% a
> 98.7%. El daño no detectado en el óptimo del adversario se reduce de 27.1% a
> 9.1%.
>
> El mecanismo es explicable y no depende del clasificador: las estaciones
> vecinas no fueron atacadas y siguen reportando el estado real de la
> atmósfera.

---

## 9. Pendientes

| ID | Descripción |
|---|---|
| V28 | Evaluar contra el adversario de magnitud variable (bits 3-4-5 mezclados) |
| V29 | CNN-1D como comparación arquitectónica |
| V30 | Generalizar a las 33 estaciones: un modelo por estación, o salida multivariada |
| V31 | Inspeccionar los pesos por estación — ¿identifica el modelo la vecindad geográfica? |
| V32 | Curva ROC completa, barriendo el umbral de forma continua |
| V33 | Comportamiento con más de un nodo comprometido |
| V26 | Barrer la longitud de ventana (12 / 24 / 48 h) — 24 h sigue siendo supuesto |