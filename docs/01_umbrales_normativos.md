# Umbrales normativos y funciones de decisión

Última actualización: 2026-08-22

## Por qué este documento

La métrica de daño del Escenario B (bitácora D4) es:

```
D = 1[ f(x_recibido) ≠ f(x_real) ]
```

`f` es la función de decisión de la aplicación. Sin `f` y sus umbrales
verificados, la métrica carece de fundamento. Este documento fija `f`.

---

## Hallazgo central: existen DOS funciones de decisión

Operan sobre los mismos datos del SIMAT, pero son sistemas distintos, con
escalas distintas y consecuencias distintas.

| | **Sistema A — Índice AIRE Y SALUD** | **Sistema B — PPRCAA** |
|---|---|---|
| Norma | NOM-172-SEMARNAT-2023 (federal) | NADF-009-AIRE-2017 (local CDMX) |
| Responsable | Gobiernos que operan el monitoreo | CAMe |
| Escala | Concentración → banda (sin valor adimensional) | Concentración → **puntos** de índice |
| Salida | 5 bandas de calidad del aire | Fase preventiva / I / II / II combinada |
| Agregación | Máximo entre estaciones | Máximo entre **5 zonas** de la ZMVM |
| Consecuencia | Comunicación de riesgo, recomendaciones | Restricciones **obligatorias** |
| Estado | **VERIFICADO** (norma en mano) | **PARCIAL** (falta tabla de puntos, V9) |

**Decisión pendiente:** elegir cuál es la `f` principal de la tesis. El Sistema B
produce daño más severo (restricción vehicular, suspensión de actividades); el
Sistema A está completamente verificado y es implementable hoy. Se pueden
reportar ambos como niveles de severidad.

---

## Sistema A — Índice AIRE Y SALUD (NOM-172-SEMARNAT-2023)

Publicada en el DOF el 25/01/2024. Sustituye a la NOM-172-SEMARNAT-2019.

### No hay puntos de índice

Cita textual del Anexo B: *"El índice utiliza las concentraciones y establece las
categorías para cada contaminante por separado y con el propósito de facilitar su
entendimiento, en esta actualización no se asignó un valor adimensional."*

**Consecuencia:** `f` es una simple tabla de intervalos. No hay interpolación
lineal por tramos. Cualquier tabla de puntos 0–50 / 51–100 / etc. corresponde a
la versión 2019 o al Sistema B, no a esta norma.

### Umbrales de O₃ (Tabla 6) — concentración base: promedio horario

| Banda | Intervalo (ppm) | Equivalente (ppb) |
|---|---|---|
| Buena | <0.058 | <58 |
| Aceptable | >0.058 a 0.090 | 58 – 90 |
| Mala | >0.090 a 0.135 | 90 – 135 |
| Muy Mala | >0.135 a 0.175 | 135 – 175 |
| Extremadamente Mala | >0.175 | >175 |

### Umbrales de PM10 (Tabla 4) — promedio móvil ponderado de 12 h

| Banda | Al entrar en vigor | Desde ene 2024 | Desde ene 2026 |
|---|---|---|---|
| Buena | <45 | <45 | <45 |
| Aceptable | >45 a 70 | >45 a 60 | >45 a 50 |
| Mala | >70 a 132 | >60 a 132 | >50 a 132 |
| Muy Mala | >132 a 213 | >132 a 213 | >132 a 213 |
| Ext. Mala | >213 | >213 | >213 |

### Umbrales de PM2.5 (Tabla 5) — promedio móvil ponderado de 12 h

| Banda | Al entrar en vigor | Desde ene 2024 | Desde ene 2026 |
|---|---|---|---|
| Buena | <15 | <15 | <15 |
| Aceptable | >15 a 41 | >15 a 33 | >15 a 25 |
| Mala | >41 a 79 | >33 a 79 | >25 a 79 |
| Muy Mala | >79 a 130 | >79 a 130 | >79 a 130 |
| Ext. Mala | >130 | >130 | >130 |

**Nota:** los umbrales cambian en enero de 2026. Los datos son de 2025, por lo
que aplica la columna "desde enero de 2024". Documentar la elección.

### Umbrales de CO (Tabla 9) — promedio móvil de 8 h

Buena <5.00 ppm | Aceptable >5.00 a 9.00 | Mala >9.00 a 12.00 | Muy Mala >12.00
a 16.00 | Ext. Mala >16.00.

**CO queda descartado como caso de uso:** el máximo observado en RAMA 2025 es
6.09 ppm. Solo cruza el primer umbral y nunca alcanza las bandas altas.

### Concentración base por contaminante (Tabla 3)

| Contaminante | Reporte horario |
|---|---|
| PM10, PM2.5 | Promedio móvil ponderado de 12 h |
| CO | Promedio móvil de 8 h |
| NO₂, O₃, SO₂ | Promedio horario |

**Implicación para el modelo de ataque:** O₃ se evalúa sobre la lectura horaria
directa, por lo que es susceptible a manipulación puntual. PM se evalúa sobre
ventana de 12 h, por lo que la manipulación de una hora se diluye y exige ataque
sostenido. *La resistencia del sistema depende de su ventana de agregación, no
sólo del umbral.*

### Resolución normativa (Tabla 2)

| Contaminante | Unidad | Cifras decimales |
|---|---|---|
| O₃, NO₂, SO₂ | ppm | 3 |
| CO | ppm | 2 |
| PM10, PM2.5 | µg/m³ | 0 |

**3 decimales en ppm = 1 ppb.** La resolución entera con que RAMA reporta O₃ es
exactamente la resolución normativa. Esto justifica la elección de codificación
en CayenneLPP a 1 ppb/LSB sin arbitrariedad.

### Promedio móvil ponderado de 12 h (numeral 5.2.5.3)

```
C̄ = [ Σ(Ci · W^(i-1)) / Σ(W^(i-1)) ] · FA

W = w   si w > 0.5          w = 1 − (Cmax − Cmin) / Cmax
W = 0.5 si w ≤ 0.5

FA = 0.694 para PM2.5
FA = 0.714 para PM10

N = 12;  i = 1 es la hora más reciente
```

Condiciones de validez:
- Se requieren datos de al menos **dos de las tres horas más recientes**. Si no,
  no se calcula el subíndice de esa hora.
- El índice `i` se mantiene aunque falten horas intermedias (si sólo hay datos
  en las horas 1 y 3, se usa C₁w⁰ y C₃w², no C₃w¹).

Ejemplos completos en el Anexo A de la norma.

### Compleción de datos

- Promedio horario: al menos 75% de los registros de la hora (≥45 min).
- Promedio móvil de 8 h: al menos 75% de las horas (≥6 h).
- Promedio de 24 h: al menos 75% (≥18 h).

### Agregación entre estaciones (numeral 5.4.2) — CRÍTICO

> *"El Índice AIRE Y SALUD que se difundirá a la población será el que indique el
> mayor deterioro de la calidad del aire y el riesgo a la salud asociado, para
> cada una de las estaciones que conforman el Sistema de Monitoreo."*

**La función de agregación es un MÁXIMO.** No hay promedio, votación ni
confirmación cruzada entre estaciones.

Implicación directa para el modelo de adversario: **comprometer una sola
estación basta para determinar el índice difundido a toda la población.** No se
requiere coordinación entre nodos.

Esto es un resultado en sí mismo: la política de agregación por máximo, adoptada
como criterio conservador de protección a la salud, es simultáneamente el peor
caso desde la perspectiva de integridad de datos.

---

## Sistema B — PPRCAA (CAMe)

Programa para Prevenir y Responder a Contingencias Ambientales Atmosféricas.
Responsable de la activación: Comisión Ambiental de la Megalópolis.

### Escala: puntos, no concentración

Los valores de activación y desactivación usan la escala del índice de calidad
del aire de la **NADF-009-AIRE-2017**. Ésta sí define una conversión
concentración → puntos.

**V9 (pendiente):** obtener la tabla de conversión de la NADF-009-AIRE-2017. Sin
ella no se puede implementar `f` para este sistema.

### Fases

Cuatro etapas: Fase preventiva, Fase I, Fase II y Fase II combinada.

Valores conocidos (requieren verificación contra el Acuerdo publicado):

| Fase | O₃ | PM2.5 |
|---|---|---|
| Preventiva | 140 puntos | 135 puntos |
| I, II, II combinada | pendiente (V9) | pendiente (V9) |

La Fase Preventiva por ozono se activa por **pronóstico**: cuando el modelo
estima probabilidad mayor a 70% de rebasar 140 puntos al día siguiente. Esto
introduce una superficie de ataque distinta (envenenamiento del modelo de
pronóstico) que queda fuera del alcance actual.

### Agregación por zonas

> *"Se considerarán los valores del Índice de Calidad del Aire más altos
> registrados por el SIMAT [...] en cualquiera de las cinco zonas en que se
> divide la Zona Metropolitana del Valle de México: Noreste, Noroeste, Centro,
> Sureste y Suroeste."*

Otra vez **máximo**, ahora sobre cinco zonas. La activación se decreta en el
transcurso de la hora siguiente al registro.

**V10 (pendiente):** mapeo de las 37 claves de estación de RAMA a las cinco zonas
de la ZMVM. Necesario para modelar la agregación zonal.

### Caso real de activación (validación empírica)

Enero de 2026: se registró una concentración horaria máxima de 160 ppb de O₃ en
la estación Cuajimalpa (CUA) y se activó la Fase 1 de contingencia ambiental por
ozono.

**Relevancia:** una sola estación, una sola hora, 160 ppb → restricción vehicular
en toda la ZMVM. Es el escenario de daño de la tesis, documentado en la
realidad.

---

## Distribución observada de bandas — O₃, RAMA 2025

Calculado sobre 218,823 lecturas horarias válidas, todas las estaciones,
umbrales del Sistema A:

| Banda | Fracción |
|---|---|
| Buena | 81.257% |
| Aceptable | 14.425% |
| Mala | 4.174% |
| Muy Mala | 0.144% |
| Extremadamente Mala | 0.000% |

En 2025 el máximo registrado fue 168 ppb: la banda superior nunca se alcanzó.

---

## Ventana de vulnerabilidad recalculada — O₃, Sistema A

Probabilidad de que un flip del bit *k* cambie la banda reportada, con
codificación a 1 ppb/LSB (resolución nativa y normativa).

| bit | Δ (ppb) | Sube de banda | Baja de banda |
|---|---|---|---|
| 0 | 1 | 0.90% | 0.87% |
| 1 | 2 | 1.83% | 1.75% |
| 2 | 4 | 3.78% | 3.42% |
| 3 | 8 | 7.94% | 6.47% |
| 4 | 16 | 17.74% | 11.64% |
| 5 | 32 | 44.85% | 18.40% |
| 6 | 64 | 100.00% | 18.74% |
| 7 | 128 | 100.00% | 18.74% |

**Resultado 1 — hay gradiente, no acantilado.** El análisis previo con τ=154 ppb
(umbral incorrecto, del Sistema B mal aplicado) producía un salto de dos órdenes
de magnitud entre bits consecutivos. Con los umbrales correctos del Sistema A la
transición es suave, y los bits 3–5 constituyen una zona explotable:
desplazamientos de 8 a 32 ppb, plausibles dentro de la variabilidad legítima del
O₃, con probabilidad de daño entre 8% y 45%.

Esto **rescata el flip único** como vector viable, que se había descartado.

**Resultado 2 — asimetría de dirección.** En el bit 6, inflar la banda funciona
el 100% de las veces; desinflarla, sólo el 18.74%. La causa es estructural: el
81% de las lecturas ya está en la banda más baja y no puede descender más.

*El sistema es intrínsecamente más vulnerable a la falsa alarma que al
ocultamiento.* Consecuencia directa para el modelo de adversario: incluso un
atacante ciego, que no controla el signo del flip, produce sesgo neto hacia
arriba.

Script: `notebooks/` (pendiente de formalizar en `src/`).

---

## Pendientes

| ID | Descripción | Estado |
|---|---|---|
| V2 | Ventana de agregación NowCast para partículas | **CERRADO** — 12 h ponderadas, fórmula en 5.2.5.3, ejemplos en Anexo A |
| V3 | Tabla de puntos de corte del índice | **CERRADO** — Tablas 4–9 de la NOM-172-2023; no hay escala de puntos en este sistema |
| V4 | Umbral vigente de O₃ | **CERRADO** — 58 / 90 / 135 / 175 ppb (Tabla 6). El valor de 154 ppb pertenecía al Sistema B, mal aplicado |
| V7 | Criterio de activación del PPRCAA | **PARCIAL** — estructura y agregación confirmadas; faltan valores por fase |
| V8 | Efecto de la compleción horaria (≥45 min) sobre el modelo de ataque | **DIFERIDO** — no evaluable hasta tener el simulador de tramas |
| V9 | Tabla de conversión concentración → puntos de la NADF-009-AIRE-2017 | **ABIERTO** — bloquea la implementación del Sistema B |
| V10 | Mapeo de las 37 estaciones RAMA a las 5 zonas de la ZMVM | **ABIERTO** |

---

## Fuentes

- NOM-172-SEMARNAT-2023, DOF 25/01/2024. Copia local: `docs/normas/`.
- NADF-009-AIRE-2017 (pendiente de obtener).
- Acuerdo del PPRCAA para la ZMVM, publicado por los gobiernos de CDMX y Estado
  de México.
- Portal SIMAT: http://www.aire.cdmx.gob.mx