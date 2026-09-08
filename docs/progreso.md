# Progreso

Registro cronológico del trabajo. Las decisiones y su fundamento están en
`bitacora_decisiones.md`; los hallazgos del análisis exploratorio, en los
notebooks; los resultados numéricos, en `results/`.

---

## 2026-08-22 — Fijación de la función de decisión y EDA

### Hecho

- Repositorio inicializado: estructura, `.gitignore`, `requirements.txt`,
  entorno virtual, kernel de Jupyter registrado.
- Datos RAMA 2025 (9 contaminantes) en `data/raw/`, no versionados. Integridad
  registrada en `docs/checksums_2025.txt`.
- **Función de decisión fijada: NOM-172-SEMARNAT-2023**, Tabla 6 para O₃.
  Umbrales 58 / 90 / 135 / 175 ppb.
- Notebook `01_inspeccion_rama.ipynb`: inspección cruda, cuantificación del
  centinela `-99`, cobertura y rachas por estación, distribución de bandas,
  perfil del ciclo diurno.
- **Estación piloto seleccionada: CCA.**

### Hallazgos

**Los faltantes no son aleatorios.** 58 de 70 bloques miden exactamente 3 h, y
las horas 1–3 registran 61 faltantes cada una. No existe ningún bloque de 1 h.
Hipótesis (V11, sin verificar): calibración programada del analizador.

**Ocurren de madrugada**, cuando el O₃ es bajo y estable. La franja de faltantes
no interacciona con los umbrales de decisión.

**El 30.61% de faltantes estaba inflado.** `COY`, `SFE` y `SJA` no operaron en
2025 y aportan 26,280 celdas de `-99` puras. Excluyéndolas, la cifra real de la
red operativa es **24.30%**.

**La cobertura sola es un criterio insuficiente.** CAM tiene mejor cobertura que
UIZ (90.45% vs 88.09%) pero rachas 2.4× más largas (464 h vs 195 h).

**CCA es una categoría aparte**: 96.93% de cobertura y racha máxima de 17 h,
frente a 134 h de la siguiente. Única estación sin periodo prolongado fuera de
operación en 2025.

**CCA está más expuesta que el promedio**: 7.11% de horas en banda "Mala" frente
a 4.17%. No hay conflicto entre calidad de datos y exposición.

**Ventana de ataque.** Un desplazamiento de 16 ppb alcanza al 10.4% de las
lecturas para τ=58; uno de 32 ppb, al 26.5%. Ambos dentro de la variabilidad
legítima horaria.

**τ=175 fuera de alcance.** Máximo de CCA en 2025: 149 ppb.

**Ciclo diurno bien definido.** Mínimo 6.24 ppb a las 7 h, pico 82.58 ppb a las
15 h: factor 13×. Desviación estándar en factor 5 a lo largo del día
(5.79 → 28.75).

**Ventana óptima de ataque: 15–17 h.** Coinciden máxima variabilidad legítima
(ocultamiento) y máxima proximidad a umbrales (daño).

**Techo nocturno.** Entre 22 h y 8 h el máximo de 2025 es 61 ppb. La banda
"Mala" es inalcanzable de noche por medios legítimos: un ataque que sostenga
valores altos nocturnos produce una configuración sin precedente.

---

## 2026-08-23 — Módulos de ingesta, decisión y codificación

### Hecho

- **`src/ingest/rama.py`** — carga, formato largo, detección de rachas,
  segmentación, interpolación (desactivada, ver D8), split cronológico.
- **`src/decision/nom172.py` + `damage.py`** — función `f` y métrica de daño,
  severidad con signo, clasificación inflado/ocultamiento.
- **`src/encoding/cayenne.py` + `crypto.py`** — CayenneLPP Analog Input y
  AES-CTR con bloque A_i según Figura 17 de la especificación 1.1.
- **`docs/02_codificacion.md`**.

### Verificación cruzada

Los módulos reproducen independientemente los resultados calculados a mano:

- Ingesta sobre CCA/2025: 68 filas descartadas, 6 segmentos, 201 interpoladas.
- Decisión: 77.470% / 15.181% / 7.113% / 0.236% / 0.000%.

### Errores encontrados y corregidos

**`groupby.apply` en pandas 3.** La columna de agrupación ya no se pasa a la
función. Producía `KeyError`. Prueba de regresión añadida.

**`segment_id` duplicados entre estaciones.** El `cumsum()` se reiniciaba por
estación. **No producía error**: habría generado resultados sutilmente
incorrectos. Encontrado por revisión de código.

**`daño()` fallaba con entrada escalar.** `banda_o3` es polimórfica; `.astype()`
no existe en `bool`.

### Decisiones

| ID | Decisión | Fundamento |
|---|---|---|
| **D7** | Codificación: Analog Input `0x02` reinterpretado a 1 ppb/LSB | CayenneLPP no define tipo para gases. 1 ppb coincide con la resolución normativa y con la nativa de RAMA |
| **D8** | La ausencia de dato no se imputa: se representa como ausencia de mensaje | Ningún centinela funciona (`0` es valor real). `-99` es artefacto de SIMAT, no de LoRaWAN. Se añade `delta_t` |

**Nota sobre `0x7D` (Concentration).** Evaluado como alternativa semánticamente
correcta, pero **no aparece en la tabla oficial de myDevicesIoT/CayenneLPP**.
Descartado por credibilidad. Confirmado independientemente por el asesor.

---

## 2026-08-30 — Generación de ataques y detección (Capa 1)

### Hecho

- **`src/attack/blind.py`** — generador de dataset atacado. El ataque pasa por
  el cifrado real, no por una simulación del flip sobre el entero.
- 13 datasets (bits 0–12), tasa 5%, semilla fija: los mismos mensajes se atacan
  en todos, aislando el efecto del bit.
- Dataset de adversario de magnitud variable (bits 3-4-5).
- Detección no supervisada (IsolationForest) y supervisada (DecisionTree,
  RandomForest, KNeighbors).
- Notebooks `05_ataque.ipynb` y `06_deteccion.ipynb`.
- Resultados persistidos en `results/` como CSV versionado.
- Gráficas en `docs/img/`.

### Hallazgos

**El daño no depende de la magnitud del flip, sino de la distancia al umbral.**
Un flip de 32 ppb sobre 10 ppb no produce daño —ambos en banda "Buena"—,
mientras que un flip de 2 ppb sobre 57 ppb cruza a "Aceptable". Justifica
definir `D = 1[f(x_real) ≠ f(x_recibido)]`.

**El atacante ciego no controla el signo.** Voltear el bit *k* lo conmuta: suma
si estaba apagado, resta si estaba encendido. Verificado empíricamente sobre el
bit 5: 232 ataques subieron el valor, 102 lo bajaron. El reparto no es 50/50
porque la mediana de CCA (26 ppb) sitúa la mayoría de lecturas por debajo de 32.

**Asimetría inflado/ocultamiento.** De 97 ataques con daño en el bit 5, 66
inflaron y 31 ocultaron. Causa estructural: el 77% de las lecturas ya está en la
banda más baja y no puede descender.

**Frontera de detección entre los bits 4 y 5.** El recall salta de 8.6% a 41.4%
en un solo bit. Los tres modelos supervisados coinciden en el mismo límite, lo
que indica que la frontera es propiedad del problema y no del algoritmo.

**Óptimo del adversario: bit 6.** Daño en el 100% de los ataques con 72.9% de
detección → **27.1% de daño no detectado**, el máximo de la curva. Por debajo
del bit 5 el ataque es invisible pero inútil; por encima del 7 es efectivo pero
evidente.

**Bits 0–4 en nivel de azar.** Recalls de 2.9% a 8.6% frente a una línea base de
5%. KNeighbors registra **0.0%** en los bits 0 y 3.

**Bits 8+ se autodelatan.** Detección total, y producen valores fuera del rango
físicamente observado (máximo histórico: 149 ppb).

**El adversario de magnitud variable degrada la detección.** Con bits 3-4-5
mezclados: recall de 11.4%, frente a 18.1% de promedio de los escenarios
individuales y **41.4% del bit 5 aislado**. La mezcla no promedia: degrada. No
existe un umbral único que separe simultáneamente ataques de 8 y de 32 ppb del
tráfico normal.

**Falsos positivos sobre datos limpios: 340 (5.01%).** El valor está determinado
por `contamination=0.05`, que obliga a marcar esa fracción exista o no ataque.
La suma FP + detectados es constante en ~340 en todos los escenarios: el modelo
no decide cuántos marcar, solo cuáles.

**El detector usa efectivamente la hora.** Los mensajes marcados se apartan
30.2 ppb del perfil horario, frente a 11.6 ppb de los no marcados. No marca
valores extremos: marca valores incongruentes con la hora.

**La tasa de falsos positivos varía por mes: de 1.10% (julio) a 10.42%
(junio)**, correlacionada inversamente con la concentración media. El detector
aprende un perfil horario global y carece de información estacional, por lo que
interpreta el desplazamiento de la distribución mensual como anomalías
individuales. **Consecuencia metodológica: evaluar sobre un único periodo no es
representativo del año.**

**El clasificador supervisado no es aplicable sobre datos limpios.** Sin
ejemplos positivos no hay clase que aprender. Diferencia estructural frente al
enfoque no supervisado.

### Comparación de estrategias de partición

| bit | Cronológico | Estratificado |
|---|---|---|
| 3 | 4.3% | 7.5% |
| 4 | 8.6% | 6.0% |
| 5 | 41.4% | 28.4% |
| 6 | 72.9% | 70.1% |

*Recall, DecisionTree.*

**El estratificado no era necesario.** El split cronológico ya produce conjuntos
equilibrados: 4.86% de ataques en entrenamiento (264 ejemplos) contra 5.15% en
prueba. Descartada la falta de ejemplos como causa del fallo en bits bajos.

**Y produce recalls inferiores en tres de los cuatro bits**, contrario a lo
esperado si barajar introdujera fuga temporal. Hipótesis pendiente (V18): el
conjunto de prueba cronológico (nov–dic) podría ser un periodo favorable.

### Nota metodológica

Las métricas por defecto de LazyPredict usan `average='weighted'`. Con
desbalance del 5%, la columna `Recall` coincide exactamente con `Accuracy` en
cada fila y no informa. Un clasificador que respondiera «ningún mensaje está
atacado» obtendría 95% de accuracy.

Todas las métricas de este trabajo se reportan con `pos_label=1`, sobre la clase
atacada. La línea base de precision es la prevalencia (5%), no el 50%.

---

## 2026-09-01 — Revisión con el asesor

### Confirmado

- **Estratificación innecesaria.** Aceptada la verificación empírica.
- **Series temporales requeridas.** *«Necesitamos sí o sí las series
  temporales.»* La degradación frente al adversario de magnitud variable
  funcionó como justificación.
- **Modelos aprobados: LSTM y CNN-1D.**
- **El detector alerta, no bloquea.** *«Ahorita solo vamos a detectar.»*

### Corrección al análisis de métricas

Se había priorizado el recall por asimetría de costos, considerando únicamente
el escenario de inflado (contingencia falsa). **El asesor señaló que el ataque
tiene dos direcciones y ambas producen daño:**

- Inflado no detectado → se activa una contingencia que no correspondía
- Ocultamiento no detectado → no se activa una contingencia que sí correspondía

Por tanto **ambas métricas importan**, y la tesis debe justificar explícitamente
por qué cada una es relevante para este caso de uso, no adoptar una prioridad
genérica.

### Dato operativo aportado por el asesor

En operación real, los valores de O₃ en la ZMVM rondan los umbrales en lugar de
estar lejos de ellos: lo habitual es alcanzar 100–110 ppb, y de 140 a 150 basta
un bit de bajo orden para cruzar. Análogamente, se rebasa el umbral por 151–152
ppb, no por 300.

**Refuerza el hallazgo de la distancia al umbral con evidencia operativa:** los
bits difíciles de detectar son suficientes en el rango donde el sistema
realmente opera.

### Nueva dirección: análisis multiestación

Indicación de saltar directamente al análisis temporal con todas las estaciones:

- **Cargar todas las estaciones**, sin preselección. *«Los modelos tienen que
  aprender eso»* — qué estaciones son relevantes para cada una.
- **Atacar una sola estación.** Con varias atacadas el modelo se pierde y las
  métricas caen.
- **Las demás alimentan el contexto**, sin análisis propio.

Razonamiento: si una estación presenta un salto y sus vecinas no, es señal de
manipulación. Si todas suben coordinadamente, es un evento real.

Conecta con el hallazgo de que la agregación por máximo hace vulnerable al
sistema: **la redundancia espacial es la defensa natural.**

### Arquitectura acordada

**Predicción con residuo**, no clasificación: el modelo predice el valor
esperado de la estación objetivo a partir de sus vecinas, y la anomalía se
detecta por la magnitud del residuo.

Ventajas: es no supervisado (entrena solo con datos limpios) y distingue
**eventos espacialmente coherentes** (contaminación real) de **manipulaciones
aisladas**.

### Observación pendiente de plantear al asesor

Ni LSTM ni CNN-1D descubren estructura espacial de forma explícita. LSTM modela
dependencia temporal; CNN-1D convoluciona sobre el eje temporal y trata las
estaciones como canales independientes.

Pueden **usar** información de otras estaciones si se les proporciona, pero no
identifican qué estaciones son vecinas. La familia que sí lo hace son las redes
de grafos (GNN, GAT).

Dos salidas: calcular las correlaciones entre estaciones y proporcionarlas como
característica, o proporcionar los datos crudos y evaluar si el modelo
aprovecha la redundancia.

---

## Siguiente

1. **Verificar la disponibilidad conjunta de ventanas.** Con coberturas del 27%
   al 97%, la probabilidad de que todas las estaciones tengan dato simultáneo
   durante 24 h consecutivas puede ser baja. **Define la arquitectura y puede
   invalidar el diseño.** Prioridad máxima.
2. Decidir el tratamiento de faltantes en el contexto multiestación. Una red
   neuronal requiere un tensor completo; el enmascaramiento (rejilla completa
   más canal booleano) puede volverse inevitable, lo que tensiona D8.
3. Implementar LSTM y CNN-1D con arquitectura de predicción.
4. Barrer tamaños de ventana (24 h, 48 h).
5. **Redacción.** Material sin escribir acumulado: metodología del Escenario B
   (Capítulo 4) y resultados de Capa 1 (Capítulo 5).

---

## Pendientes abiertos

| ID | Descripción | Estado |
|---|---|---|
| V1 | Oscilación vs. deriva bajo flip repetido | **CERRADO** — verificado: el flip conmuta, el desplazamiento neto de un atacante ciego es cero |
| V5 | Estabilidad del formato RAMA en años anteriores | Abierto |
| V8 | Efecto de la compleción horaria (≥45 min) | Diferido |
| V9 | Tabla de conversión de la NADF-009-AIRE-2017 | Abierto — bloquea el Sistema B |
| V10 | Mapeo de las 37 estaciones a las cinco zonas de la ZMVM | Abierto |
| V11 | Confirmar la hipótesis de calibración con documentación del SIMAT | Abierto |
| V12 | Verificar por qué el mínimo diario está a las 7 h y no a medianoche | Abierto |
| V13 | Resolución de Analog Input | **CERRADO** — 2 bytes, 0.01, con signo |
| V14 | Construcción del bloque contador A_i en LoRaWAN 1.1 | **CERRADO** — Figura 17 |
| V15 | Oficialidad del tipo `0x7D` | **CERRADO** — no está en la tabla oficial |
| V16 | Daño acumulado sobre estadísticos agregados. El 71% de los ataques no cambia la banda pero sí desplaza el valor | Abierto |
| V17 | Sistema de Pronóstico de la CAMe como superficie de ataque | Fuera de alcance |
| V18 | ¿Es nov–dic un periodo favorable para el detector? | Abierto |
| V19 | Julio rompe el patrón de FP mensuales | Abierto |
| V20 | Probar `class_weight='balanced'` en los supervisados | Abierto |
| V21 | Barrer `contamination` para cuantificar el compromiso recall/FP | Abierto |
| V22 | Añadir característica de estacionalidad (mes o día del año) | Abierto |
| V23 | Verificar qué modelo usa Alizadeh & Bidgoly antes de justificar LSTM como estado del arte | Abierto |

Cerrados en sesiones anteriores: V2, V3, V4.

---

## Estructura de la tesis

Definida con el asesor. **Pendiente de resolver:** la estructura se acordó
cuando existía un solo escenario. Con dos escenarios, la opción más limpia es
subdividir los capítulos 4 y 5 (4.1 Escenario A, 4.2 Escenario B), pero requiere
confirmación porque afecta la sección 1.6 ya redactada.

| Cap. | Contenido | Estado |
|---|---|---|
| 1 | Problema, hipótesis, objetivos, metodología, contribución | Completo |
| 2 | Sustento teórico | Estructura definida, sin redactar |
| 3 | Estado del arte | Pendiente |
| 4 | Propuesta y metodología detallada | Pendiente |
| 5 | Resultados y análisis | Pendiente |
| 6 | Conclusiones (o dentro del 5) | Sin decidir |

**Dónde encaja el trabajo del Escenario B:**

- Capítulo 2.1.2 y 2.1.3 → maleabilidad de AES-CTR y mecanismo del bit flipping
  (`docs/02_codificacion.md`)
- Capítulo 4 → NOM-172 como función de decisión, selección de estación,
  codificación, generador de ataques, tratamiento de faltantes. Toda la bitácora
  de decisiones
- Capítulo 5 → frontera de detección, zona explotable, falsos positivos
  mensuales, degradación por magnitud variable

---

## Fuera de alcance

- **Envenenamiento del modelo de pronóstico** que activa la Fase Preventiva del
  PPRCAA. Es *data poisoning* contra un modelo cuya arquitectura no es
  observable desde la posición NS↔AS.
- **Descubrimiento de CVE** en el manejo de contadores de implementaciones
  LoRaWAN (bitácora D6).
- **Extensión a PM10 y PM2.5.** El contraste entre agregación horaria (O₃) y
  ventana de 12 h (PM) demostraría que la resistencia del sistema depende de
  cómo agrega la aplicación. Segunda fase.
- **Cruce con datos meteorológicos (REDMET)** para explicar la variación
  mensual de falsos positivos. La causa física es secundaria frente a la
  consecuencia sobre el detector.
