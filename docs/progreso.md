# Progreso

Registro cronológico del trabajo. Las decisiones y su fundamento están en
`bitacora_decisiones.md`; los hallazgos del análisis exploratorio, en los
notebooks; los resultados numéricos, en `results/`.

**Seguimiento vigente:** ver [Siguiente: tareas de la última revisión](#siguiente)
y [preguntas para el asesor](preguntas_revision_asesor.md). Las entradas fechadas
conservan lo que se sabía en cada sesión; sus resultados no sustituyen las
referencias posteriores. La estructura de capítulos al final es un registro
anterior, no una verificación del estado actual del documento en Overleaf.

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

## 2026-09-28 — Seguimiento de la última transcripción del asesor

**Fecha de registro, no fecha confirmada de la junta.** Fuente: transcripción
automática compartida por el tesista. Los minutos sirven para volver al audio;
las cantidades contradictorias se registran como dudas, no como acuerdos.
Esta actualización es documental: no cambia código, figuras ni modelos.

### Estado experimental que debemos conservar como referencia

- **Piloto CCA:** modelo reproducible de semilla 42; corte operativo **22.6 ppb**,
  distinto del p95 calculado de 14.748354911804199 ppb. Ver
  [bitácora](bitacora_decisiones.md) y
  [métricas operativas](../results/metricas_operativas_cca_bits_1_7.csv).
- **Experimento de red:** 27 modelos entrenados y guardados de 33 candidatos,
  con p95 propio por estación. AJU, CHO, FAR, IZT, MON y TAH no tuvieron
  ventanas de prueba. No confundir estos umbrales con el operativo de CCA.
- **Alcance del test de red:** 72 días, 21/oct–31/dic/2025; 35,704 mensajes
  observados y 249,928 escenarios aislados. Su máximo limpio es 152 ppb:
  no permite evaluar la anulación de las contingencias de otros meses.
- **Falsas alarmas:** 5642/35704 = 15.80 % en test limpio de la red; no
  presentar aumento de recall como mejora global sin considerar este coste.
- **Redistribución existente:** V1/V2 del experimento 04 son deterministas y
  ya muestran un compromiso entre fabricar cruces y ocultar lecturas altas.
  No son todavía la nueva propuesta de representación aleatoria.

Evidencia: [notebook 09](../notebooks/09_deteccion_red.ipynb),
[protocolo de red](experimento_red_v4_p95.md) y
[avance de codificación 04](../experiments/cayenne_mod/avance_junta_04.md).

### J1. ¿El LSTM realmente recibe las demás estaciones?

**Pregunta del asesor (26:14–38:20):** comprobar si hay una columna por
estación, con las mediciones alineadas por tiempo, o si sólo se está usando
un CSV de una estación consigo misma.

**Respuesta verificada:** sí se usa una matriz de **8,760 horas × 33 estaciones**.
Se construye con `pivot(index='timestamp', columns='station', values='value')`.
Para CCA se excluye su columna de las entradas: el tensor de test tiene forma
**(1684, 24, 66)**. Cada paso contiene 32 valores normalizados, 32 máscaras y
dos componentes de la hora. Máscara 1 = disponible, 0 = faltante. El cero
de relleno no representa una medición de ozono cero. Las etiquetas de ataque
no son entradas del modelo.

**Matices que debemos explicar:**

- Las «vecinas» son las otras 32 estaciones, no una selección geográfica de
  las más cercanas. No se ha demostrado aquí cuáles utiliza más el modelo.
- Se usan las **24 horas anteriores**, no las lecturas contemporáneas de la
  misma hora objetivo. Ejemplo verificado: 20/oct/2025 00:00–23:00 como
  entrada para estimar CCA el 21/oct a las 00:00.
- La historia de CCA está excluida de los canales del LSTM, pero **sí participa
  en su perfil adaptativo**. No afirmar que V4 ignora por completo su pasado.
- La ventana del LSTM es de 24 horas; el perfil adaptativo abarca 14 días.
  No son la misma ventana. Se predice la desviación respecto al perfil;
  el error frente a la lectura recibida se calcula después para detectar.

**Estado:** verificación cerrada; explicación al asesor pendiente.

- [x] Comprobar matriz, exclusión del objetivo, tensor y máscaras.
- [x] Preparar una vista pequeña de la matriz y una ventana con sus fechas
  para mostrar la entrada real, no el CSV de resultados de ataques.
  Exportación del 29/sep: [muestra CCA, 24 × 66](../results/muestra_entrada_lstm_v4_cca/README.md).
- [ ] Preguntar si también desea probar vecinas del instante actual. Sería
  otro experimento, no arreglar una matriz mal construida.

**Evidencia:** [cargar_matriz](../src/detect/experimento_red.py),
[construir_ventanas](../src/detect/windows.py),
[perfil V4 de red](../src/detect/red.py).
**Cierre:** mostrar la entrada comprobada y registrar la decisión sobre
contexto pasado frente a contemporáneo; no reentrenar sólo por esta duda.

### J2. Corregir la gráfica explicativa de los bits críticos

**Indicación (00:00–00:59, 08:26–09:19, 13:28–14:04 y 17:13–18:04):**
mostrar oportunidad de daño, **no detección** y riesgo combinado como tres
curvas; mejorar los nombres y explicar las métricas al pie. La lectura más
clara es invertir la curva verde mediante `100 - recall`, no invertir el eje
ni cambiar la curva roja para forzar un cruce.

**Qué falta resolver antes de editar:**

- [ ] Elegir unidad y denominadores: días o ataques. Si se trabaja por
  ataques, `P(daño y no detección) = P(daño) × P(no detección | daño)`.
  Si se trabaja por días, definir los eventos diarios correspondientes;
  no multiplicar porcentaje de días por recall de mensajes y presentarlo
  como daño observado. La agregación directa del notebook 09 es reutilizable.
- [ ] Acordar qué daño representa cada figura: falsa excedencia de 155 ppb,
  ocultamiento, cambio de banda local o cambio de banda del máximo de red.
  Mantener separados sus resultados.
- [ ] Distinguir la franja ideal del notebook 08, que supone sumar, de los
  cruces reales por flip, cuyo signo depende del estado previo del bit.
- [ ] Usar el mismo conjunto de estaciones, fechas y política de umbrales.
  No trasladar el recall de CCA a toda la red ni el test de 72 días a todo 2025.
- [ ] Rotular denominadores y «sin ataques que produzcan este daño» cuando
  no hay casos. La no detección también es indefinida si su denominador es
  cero: no sustituirla por 0 ni por 100 %.
- [ ] Mostrar la región candidata de bits 4–5 (3 como posible extensión),
  sin imponer un máximo allí. Un cruce visual no prueba optimalidad.

**Estado actualizado al 29/sep:** revisión implementada al final del notebook 09;
pendiente de aceptación visual y metodológica con el usuario/asesor. La lista
anterior registra los puntos de revisión, no todos son ya tareas sin implementar.
Se conserva el producto como indicador descriptivo y se muestra aparte el conteo
real: no se reinterpretó el recall de mensajes como una tasa diaria. Ver
[decisiones, figuras y límites de esta revisión](revision_graficas_2026-09-29.md).
**Cierre:** figura base con tres curvas definidas, tabla subyacente, alcance
temporal y pie comprensibles. Primero sin contramedida. No requiere por sí
mismo otro entrenamiento. La confirmación de usar contexto contemporáneo
en J1 sí podría abrir un experimento nuevo.

### J3. Confirmar los pesos y el tamaño de la nueva representación

**Indicación (09:19–12:25 y 38:47–40:30):** concentrar la redistribución en
bits 4–5 y aprovechar posiciones de igual peso con el bit 3. La transcripción
mezcla pesos de 4/8 ppb y seis/siete fragmentos.

**Propuesta coherente, aún no confirmada como especificación:**

| Bit original, numeración desde 0 | Peso | Reparto |
|---:|---:|---|
| 3 | 8 ppb | 1 posición de 8 |
| 4 | 16 ppb | 2 posiciones de 8 |
| 5 | 32 ppb | 4 posiciones de 8 |

Se obtiene un grupo de **7 posiciones de 8 ppb**: capacidad 56 ppb, igual
a 8+16+32. En el dominio experimental 0–255, conservando los otros cinco
bits, son 12 posiciones activas dentro del campo de 16 bits. Esto no define
todavía qué hacer fuera de ese dominio ni con posiciones reservadas atacadas.

Siete posiciones de 4 sólo cubren 28 ppb. Para cubrir 56 usando posiciones
de 4 se necesitan 14; junto a las otras cinco serían 19, no 16.

- [ ] Confirmar con el audio/asesor **7 × 8 ppb frente a fragmentos de 4**.
- [ ] Fijar dominio, mapa de posiciones físicas, resolución, decodificación
  y política de valores/palabras inválidas o bits reservados.
- [ ] Registrar tamaño del payload. No inferir igualdad de energía total
  sólo de conservar bytes: generación aleatoria y cómputo también tienen coste.

**Estado:** aclaración imprescindible antes de implementar J4.
**Cierre:** tabla de pesos inequívoca y reglas del formato por escrito.

### J4. Implementar la selección aleatoria de posiciones

**Indicación (15:00–16:05 y 39:59–40:30):** al representar una cantidad,
elegir aleatoriamente qué posiciones de igual peso se encienden, no siempre
las primeras. El receptor debe recuperar exactamente la lectura sin ataque.

**Diferencia con lo existente:** `codificar` en el comparador 04 enciende
grupos fijos para V1/V2; no implementa esta representación aleatoria.

- [ ] Tras J3, crear una variante nueva sin sobrescribir V1/V2.
- [ ] Para el grupo candidato de peso 8, si debe aportar 24, elegir tres
  posiciones distintas entre siete. Conservar el resto de la lectura.
- [ ] Especificar la distribución de elección y separar los generadores
  aleatorios de codificación y ataque. Registrar semillas de experimentación.
- [ ] Probar recuperación exacta de cada valor del dominio acordado,
  conservación de longitud y comportamiento de palabras alteradas.

**Estado:** pendiente. **Cierre:** codificador/decodificador aleatorios con
pruebas; semilla experimental no equivale a una garantía de seguridad.

### J5. Diseñar los ataques múltiples y su eje X

**Discusión (12:54–16:05 y 40:30–48:21):** probar varios flips en el grupo
redistribuido. Queda abierta la representación de combinaciones sobre el eje X.

- [ ] Separar dos vistas: bit original para la motivación; **número de flips
  físicos** para la contramedida. Probar k=1 y después k=2…7 si J3 confirma
  el grupo de siete posiciones; elegir posiciones distintas por mensaje.
- [ ] Mostrar la distribución del desplazamiento obtenido, no asumir que
  k flips siempre suman k pesos. Con peso w, `delta = w × (k - 2r)`, donde
  r es el número de posiciones atacadas que estaban encendidas.
- [ ] No llamar «bit 4» a dos flips nuevos sin aclararlo: 1/2/4 flips de
  peso 8 tienen desplazamientos máximos 8/16/32, pero pueden cancelarse.
- [ ] Comparar el mismo presupuesto donde ambos formatos admitan máscaras.
  Si k excede las posiciones del grupo original, declararlo no comparable
  o acordar otro conjunto atacable; no inventar una equivalencia.
- [ ] Evaluar elección uniforme y una máscara fija desfavorable al defensor;
  explicitar qué información tiene el atacante. No conocer el mensaje no
  obliga, por sí solo, a una estrategia uniforme.
- [ ] Elegir enumeración exacta si es manejable; si se muestrea, registrar
  repeticiones, semillas e incertidumbre. No seleccionar la mejor semilla.

**Estado:** diseño pendiente, depende de J3–J4. **Cierre:** presupuestos,
máscaras, ponderaciones y ejes definidos antes de producir comparaciones.

### J6. Evaluar primero la contramedida SIN LSTM

**Prioridad explícita (55:58–57:23):** demostrar si la nueva distribución
reduce el daño por sí sola; después añadir el detector.

- [ ] Comparar formato base y nueva variante sobre las mismas lecturas.
  Se puede usar todo 2025 para el daño sin LSTM, sin atribuirle detección.
- [ ] Separar cruces hacia arriba y ocultamiento hacia abajo; no esconder
  un deterioro en lecturas altas dentro del promedio global.
- [ ] Separar cruces locales de la decisión de red. Para máximos diarios,
  sustituir sólo un mensaje y conservar los otros horarios, estaciones y
  empates, como en el notebook 09.
- [ ] Contar rechazos y pérdida de mensajes por separado: no son corrección
  de la lectura ni daño cero. Mantener controles de rango comparables.
- [ ] Graficar antes/después con zoom del daño y medir los costes del formato.
  La curva más plana es una expectativa, no un resultado que se deba forzar.

**Estado:** V1/V2 exploradas; nueva variante aleatoria pendiente.
**Evidencia reutilizable:** [notebook 04 de codificación](../experiments/cayenne_mod/04_comparacion_pesos_rama.ipynb)
y [su avance](../experiments/cayenne_mod/avance_junta_04.md).
**Cierre:** tabla y figuras sin detector, ambos sentidos del daño, mismo
dominio/presupuesto y una conclusión válida aunque la variante empeore.

### J7. Medir la combinación codificación + detector

**Indicación (18:19–19:15):** de lo que sigue pasando después de la
contramedida, cuantificar qué detecta el LSTM y qué daño escapa a ambos.

- [ ] Reutilizar modelos y umbrales guardados sobre el mismo test. No
  reentrenar automáticamente para favorecer la nueva codificación.
- [ ] Para cada escenario, registrar lectura original, representación,
  máscara, lectura decodificada, daño y alerta. Separar detectados/no
  detectados y dañinos/inocuos; usar denominadores explícitos.
- [ ] Reportar precision, recall, F2, falsas alarmas y daño no detectado.
  Reducir el desplazamiento puede reducir daño y también detección: el
  balance se mide, no se deduce sólo del delta.
- [ ] Reservar otra evaluación temporal para generalización. El test actual
  ya se ha consultado y no contiene las contingencias reales de temporada cálida.

**Estado:** posterior a J6. **Cierre:** comparación pareada con/sin codificación
y con/sin detector, sin mezclar estaciones, periodos o políticas de umbral.

### J8. Persistencia temporal y modelo de amenaza

**Discusión a futuro (19:15–23:37 y 49:31–55:50):** ataques sostenidos,
posible dataset de cinco minutos y alternativas de permutación de posiciones.

- [ ] Consultar disponibilidad del dataset de cinco minutos mencionado por
  el asesor y verificar su definición temporal. No consta que esté disponible
  en este repo ni que exista autorización para usarlo.
- [ ] Verificar la regla temporal de la decisión antes de simularla: datos
  horarios no reconstruyen doce observaciones de cinco minutos. No afirmar
  éxito casi imposible mediante `p**12` sin justificar independencia.
- [ ] Formalizar la posición del adversario, qué puede alterar y qué conoce.
  El formato es público; no agregar como hechos reinicios, claves conocidas
  o un nodo malicioso sólo porque aparecen como alternativas en la conversación.
- [ ] Mantener permutación de pesos distintos/metadatos de orden como una
  línea separada y diferida. La prioridad acordada es redistribución y selección
  aleatoria dentro de posiciones de igual peso, sin metadatos de orden nuevos.

**Estado:** diferido; no bloquea la prueba de un mensaje de J6.
**Cierre:** fuentes, datos y supuestos comprobados antes de extender conclusiones.

---

## 2026-10-03/04 — LSTM V4 multianual (2020–2026)

Línea independiente de J1–J8: poner a prueba el detector V4 fuera de 2025.
Protocolo fijado antes de entrenar: [protocolo_lstm_v4_multianual.md](protocolo_lstm_v4_multianual.md)
(`v4_multianual_33_p95cal2023_v1`, revisión 1).

### Hecho

| Paso | Dónde | Resultado |
|---|---|---|
| Inventario RAMA 2020–2026 y ubicación de estaciones | [notebook 10](../notebooks/10_inventario_multianual.ipynb) | Formato estable (V5 cerrado); 2024 sin 2 renglones; 193 lecturas ≥155 en 47 días |
| Separación temporal y auditoría | [notebook 11](../notebooks/11_protocolo_temporal_multianual.ipynb) | 2020–21 ajuste · 2022 validación · 2023 calibración · 2024/2025/2026 prueba; 27/27 comprobaciones |
| Entrenamiento de 31 objetivos (tesista) | [notebook 12](../notebooks/12_entrenamiento_lstm_v4_multianual.ipynb) | E de 1 a 23; p95 de 18.9 a 32.5 ppb; HGM y XAL fuera; reproducible en CCA y TLI |
| Evaluación limpia y con ataques (tesista) | [notebook 13](../notebooks/13_ataques_dano_v4_multianual.ipynb) | Recalculada en memoria: tablas idénticas |

Todos los números provienen de los modelos **recién entrenados** de
`results/lstm_v4_multianual_v1/estaciones/`, cargados de disco para calibrar y evaluar.
Rastro completo en `results/lstm_v4_multianual_v1/bitacora_entrenamiento.csv`.

### Hallazgos

- **Calibración 2023:** el LSTM reduce el MAE frente al perfil en 30/31 (mediana de reducción 15.9 %);
  AJM, de baja representatividad, no mejora. Subestima en la tarde (12–16 h, mediana
  +3.0 ppb) y su error es mayor ahí (sigma ≈15 ppb).
- **Limpio en prueba:** mejora al perfil en 26/30 estaciones (2024), 30/31 (2025) y
  27/28 (2026 ene–jul). FPR micro incluyendo baja representatividad: 7.06 %, 7.28 %
  y 6.57 %, respectivamente; el ≈5 % de calibración no se mantiene en prueba.
- **Ataques al 5 % (grupo principal):** recall ≈7 % en bits 0–2, cercano a la FPR
  (poca capacidad discriminativa, no identidad de alertas lectura por lectura);
  ≈20–22 % en bit 4, ≈79–80 % en bit 5, >99 % en bit 6 y 100 % en bit 7 en los
  escenarios evaluables registrados. Precisión máxima ≈42–44 %. Curvas agregadas
  parecidas entre años; no se demuestra estabilidad universal ni por estación.
- **Daño no detectado** concentrado en bits 3–5, con el pico en el bit 5 (2024) o en el
  bit 4 (2025 y 2026): en 2024, 15 días con una excedencia fabricable sin alerta y 85 días
  (23 %) con cambio de banda del máximo de red sin alerta (bit 5). El bit 6 también
  deja ese daño en 26, 24 y 15 días de 2024/2025/2026; no tiene detección perfecta.
  **Ocultamiento de excedencias observadas:** sin alerta en 2/17 días con excedencia
  en 2024 (11.8 %), 2/6 en 2025 (33.3 %) y 0/9 en 2026 parcial, con un solo mensaje
  y una sola lectura ≥155 en los cuatro casos sin alerta.
  Son máximos observados, no contingencias oficiales suspendidas. El porcentaje
  sobre todos los días mide frecuencia; sobre días con excedencia mide vulnerabilidad
  condicionada. Ambos son válidos si se explicita el denominador.
- **Frente a la referencia histórica:** precisión bit 5 de 21.6 % frente a 36.8 %
  en el grupo principal de 2024; FPR antigua 15.8 % frente a ≈7 % nueva. Recall
  bit 4 de 40.8 % frente a ≈21 %; bit 5 de 86.7 % frente a ≈80 %.
  No es una comparación controlada: cambiaron modelo, cobertura, periodo y umbral.
  No se atribuye la diferencia sólo a más años ni sólo a la calibración.
- **Estaciones sin detector:** HGM y XAL permiten fabricar una excedencia con bit 7
  en 306/366 días de 2024, sin evaluación posible. ACO tiene modelo pero no lecturas
  ese año: no origina ninguno de esos escenarios.

### Límites

Oportunidad ≠ probabilidad de éxito de un atacante ciego; escenarios de un mensaje;
precisión condicionada al 5 % de ataques; 2026 sólo ene–jul; excedencias del máximo
observado, no contingencias declaradas.

### Cierre del resumen — 2026-10-04

La lectura vigente se consolida en el
[notebook 14](../notebooks/14_resumen_v4_multianual.ipynb). Se corrigieron textos,
títulos y la ilustración de CCA 2023 (signo real del flip, no signo aleatorio),
sin cambiar modelos, umbrales ni tablas experimentales. Las notas previas del
notebook 13 conservan el historial; este cierre precisa sus generalizaciones.

- El máximo observado en bits 4–5 se refiere a días con cambio de banda de red
  sin alerta, no a un óptimo universal ni a todas las métricas de daño.
- El ejemplo CCA 6/may/2024 muestra que 156 → 140 ppb por bit 4 acerca la lectura
  a la predicción 121.15 ppb: el error baja de 34.85 a 18.85, bajo el umbral 24.16.
  El máximo diario pasa de 156 a 153; la alteración oculta la excedencia sin alerta.
- La reproducibilidad de entrenamiento se comprobó en CCA y TLI; no se afirma
  que se hayan reentrenado dos veces los 31 objetivos.
- La **distribución B** se cierra como candidata prioritaria bajo las campañas
  estudiadas: 255 cambios de banda local sin alerta en Base frente a 567 en B,
  con 26 estaciones peores y un empate. Son experimentos con la referencia
  anterior, no una reevaluación B + LSTM multianual. Ver
  [avance del experimento 11](../experiments/cayenne_mod/avance_junta_11.md).
  Otras codificaciones y selección aleatoria no implementada quedan diferidas,
  no falsamente marcadas como demostradas o refutadas por ese resultado.

### Variante contemporánea (J1) — 2026-10-04

Protocolo [protocolo_contemporaneo_v1.md](protocolo_contemporaneo_v1.md), fijado antes de
entrenar; resultados en el [notebook 15](../notebooks/15_contemporaneo_resultados.ipynb) y
`results/contemporaneo_v1/`. Modelos **recién entrenados** (`lstm_t`, `lineal_t`) y V4
cargado de disco; reproducibilidad verificada en CCA para ambas variantes.

- **Calibración 2023 (principales, mediana):** MAE V4 7.78 · `lstm_t` 7.62 (−2 %) ·
  `lineal_t` 8.38 ppb; umbral p95 22.65 · 22.18 · 23.79 ppb. α elegido: 1000 en 22
  estaciones, 3000 en 7 y 300 en 2 (ninguno en el borde de la rejilla ampliada). E de
  `lstm_t`: 1–2 en 18 de 31.
- **Limpio en prueba (FPR micro, principales):** 2024: V4 7.0 · `lstm_t` 7.2 ·
  `lineal_t` 5.9 %; 2025: 7.2 · 7.4 · 6.6 %; 2026: 6.6 · 6.1 · 6.0 %.
- **Un mensaje, muestra pareada (principales, 2024):** bit 4 → 20.9 · 23.3 · 19.3 %;
  bit 5 → 78.7 · 80.6 · 77.8 %. 2025 y 2026 en la misma línea: `lstm_t` +1 a +3 puntos.
- **Desactivaciones sin alerta / días con excedencia:** V4 2/17, 2/6, 0/9; `lstm_t` 2/17,
  3/6, 1/9; `lineal_t` 2/17, 2/6, 1/9. Ninguna variante mejora.
- **Atacante simultáneo (bit 5, principales):** V4 74.2 / 76.2 / 77.3 % (2024/25/26);
  `lstm_t` 41.6 / 42.4 / 42.3 %; `lineal_t` 47.2 / 48.2 / 47.2 %. Bit 6: V4 98.5–99.2 %,
  variantes 88.8–92.4 %. El V4 bajo ataque simultáneo eleva sus falsas alarmas con bits
  grandes (11 % bit 6, 18 % bit 7 en 2024): las horas atacadas contaminan ventanas y
  perfiles de horas posteriores.

**Conclusión:** resultado negativo. Ver a las vecinas en la misma hora casi no reduce el
error y debilita al detector frente a un atacante que altera todas las estaciones a la vez.
Se mantiene el V4. El lineal rinde peor que el V4: el LSTM aporta frente a una línea base
simple. La exploración previa sobreestimó la ganancia por usar sólo horas completas.

### Vecinas cercanas (idea del tesista) — 2026-10-05

Protocolo [protocolo_vecinas_cercanas_v1.md](protocolo_vecinas_cercanas_v1.md), fijado antes
de entrenar; resultados en el [notebook 16](../notebooks/16_vecinas_cercanas_resultados.ipynb)
y `results/vecinas_cercanas_v1/`. Modelos **recién entrenados** comparados con el V4 cargado
de disco; CCA reproducible.

- **k elegido con 2022:** 4 en 21 estaciones, 8 en 7, 16 en 3, **32 en ninguna**. CCA:
  `val_loss` 131.6 con k = 4 frente a 154.0 con las 32.
- **Calibración 2023 (principales, mediana):** MAE V4 7.78 → knn 7.52 ppb (−3 %); umbral
  22.65 → 21.36 ppb; 27 de 30 estaciones bajan su MAE; error en lecturas ≥90 ppb 17.8 →
  16.0 ppb (sesgo +16.1 → +12.0). AJM: 12.51 → 9.73 ppb, ahora mejora al perfil (12.50).
  Empeoran GAM, NEZ y AJU (+0.3 a +0.6 ppb).
- **Limpio (FPR micro, principales):** 2024 7.02 → 6.71 %; 2025 7.22 → 7.12 %;
  2026 6.62 → 7.01 %. Baja representatividad sube (2024 7.39 → 8.52 %).
- **Un mensaje (principales):** bit 4 2024 20.9 → 22.4 %, 2025 22.3 → 23.9 %, 2026
  19.8 → 23.0 %; bit 5 78.7 → 81.5 %, 80.0 → 83.6 %, 80.2 → 82.4 %.
- **Daño (días con cambio de banda del máximo de red sin alerta):** 2024 bit 4 70 → 83,
  bit 5 85 → 92; 2025 bit 5 63 → 80; 2026 bit 5 32 → 35. Excedencia fabricada sin alerta,
  bit 5: 15 → 16 (2024), 7 → 9 (2025), 3 → 9 (2026). Desactivaciones sin alerta: 2/17,
  2/6 y 2/9 frente a 2/17, 2/6 y 0/9 del V4.
- **Detalle por evento (barrido, bit 5):** en 2024 knn deja pasar menos ataques dañinos
  (590 frente a 669) pero repartidos en más días (92 frente a 85); en 2025 más (1038
  frente a 933), sobre todo en PED (+51) y CCA (+34). El 99 % de los no detectados suben
  la lectura.
- **Atacante simultáneo (bit 5, principales):** knn 77.3 / 79.7 / 78.8 % frente a V4 74.2
  / 76.2 / 77.3 % (2024/25/26): no se vuelve frágil (sigue usando sólo el pasado).

**Conclusión:** resultado mixto. Mejor predicción y algo más de recall, robusto al atacante
simultáneo, pero sin reducir el daño no detectado en decisiones (empeora en 2025). Se
conserva el V4. Hallazgo para la tesis: el sesgo del V4 en lecturas altas protegía sin
intención contra ataques que suben la lectura; predecir mejor no basta (interpretación).

## 2026-10-05 — Junta con el asesor: giro hacia un segundo ataque

Registro de la junta posterior a la evaluación multianual. Fuente: transcripción
automática; lo que no pudo confirmarse queda como duda. El README se actualizará
cuando el giro esté más definido.

### Acuerdos

| # | Acuerdo |
|---|---|
| K-A1 | El detector LSTM está **topado** para bit flipping: más años, vecinas de la misma hora y vecinas cercanas apenas mueven el resultado (notebooks 14–16). |
| K-A2 | Lo hecho **no se desecha**: queda como primera parte de la tesis. Si existe bit flipping y se usa un detector LSTM, se detecta hasta cierto punto (bits 6–7 casi siempre; bits 3–5 concentran el daño que escapa). |
| K-A3 | No se espera una contramedida mucho mejor para bit flipping; las distribuciones de pesos probadas no se proponen como estrategia. |
| K-A4 | Lo deseable habría sido **mover el punto ideal del atacante** (subir la detección de los bits 4 y 5). Queda como objetivo sin plan concreto. |
| K-A5 | 155 ppb se usa como **umbral experimental** sobre el máximo observado, igual en todos los años; no se presentan como contingencias reales (los umbrales oficiales cambiaron con el tiempo). |
| K-A6 | Hipótesis del asesor sobre por qué el MIC no es de extremo a extremo: que el Application Server no dependa de LoRaWAN (abstracción por capas) y el costo de cómputo. |

### Nueva dirección: un segundo ataque a LoRaWAN

Ampliar la tesis de «bit flipping» a **ataques a LoRaWAN**, con al menos un segundo
ataque caracterizado igual que el primero: ¿lo encuentra el detector? ¿hasta dónde?

- **Ataque:** drenado de energía aprovechando las ventanas de recepción; por ejemplo,
  interferencia (jamming) que obliga al nodo a usar sus ventanas o reintentos.
- **Modelos de atacante:** agresivo (interfiere todo, debería ser fácil de detectar) y
  uno más inteligente (interfiere a veces).
- **Modelo de energía:** cada encendido del nodo gasta 1 unidad; se compara la vida
  esperada con la real (p. ej., unidades que debían durar días agotadas en 12 horas).
- **Transmisiones realistas:** la recepción no ocurre siempre en el primer intento; sin
  ese azar, cualquier segundo intento delataría el ataque.
- **Datos:** buscar un dataset público con la ventana o intento en que llegó cada
  mensaje. Si no existe, **crearlo** con nodos reales (envíos frecuentes, p. ej. cada
  minuto; registro de llegada y ventana; distintas distancias, 10 m, 20 m…). El asesor
  señaló que ese dataset podría ser por sí mismo una contribución.
- **Propuesta del tesista, aceptada:** reutilizar las lecturas RAMA como contenido y
  agregar una máscara de llegada («llegó / no llegó» y con cuántas ventanas).
- **Detector:** clasificar «hay ataque / no hay ataque»; equivocarse a veces es aceptable.

### Aclaraciones a lo dicho en la junta (verificadas contra el repositorio)

- **Duda del asesor sobre la distribución B** («no debería poder aumentar»). En CCA, con
  los 420 ataques que **ambos** formatos aceptan, B tiene **menos** cambios de banda sin
  alerta (6 frente a 13). El aumento total viene de los **791 ataques que sólo B acepta**
  (+13). En la red, Base acepta 9 800 intentos y B 26 716 (B rechaza 16 916 menos). No es
  un error metodológico: B abre posiciones que Base rechazaba. Ver
  [cierre de la distribución de pesos](../experiments/cayenne_mod/cierre_distribucion_pesos.md)
  y [avance 11](../experiments/cayenne_mod/avance_junta_11.md).
- **Los bits 8–15 no los rechazaba el LSTM** sino el **decodificador** (posiciones
  reservadas en Base). El LSTM sólo ve valores en ppb; reentrenarlo no recupera ese rechazo.
- **La codificación de B usa grupos fijos;** lo aleatorio fue el ataque (qué lecturas,
  cuántos bits y cuáles). Elegir al azar qué posiciones de igual peso encender (J4) **no
  está implementado**.
- **Frente a 2025, la precisión subió** (bit 5: 21.6 % → 36.8 %) y **el recall bajó**
  (bit 4: 40.8 % → ~21 %; bit 5: 86.7 % → ~80 %); comparación no controlada.
- **Los k de vecinas cercanas fueron 4, 8, 16 y 32.**
- **Días con el máximo observado ≥155 ppb** (inventario, notebook 10): 2022: 7 · 2023: 4 ·
  2024: 17 · 2025: 6 · 2026 (ene–jul): 9. El año con más casos es 2024; las cifras dichas
  en la junta (14–15 en 2022, 9 en 2023, 6 en 2024) no coinciden con estos datos.

### Dudas por resolver (resueltas el 2026-10-05)

- **«Las 12 ventanas» — resuelto:** error de transcripción. Se asume **clase A**, la
  obligatoria y la típica de nodos con batería: **2 ventanas de recepción** (RX1 y RX2)
  tras cada envío. Consecuencia para K5: en clase A el atacante no puede hacer que el
  nodo abra más ventanas; el drenado tendría que venir de forzar reenvíos (bloquear
  confirmaciones), alargar la escucha en una ventana o comandos de la red que obliguen a
  gastar más. Cuál de estos es el ataque se fija en el protocolo.
- **«El bit flipping ya está corregido en la versión…» — resuelto:** era una intuición
  del asesor (que en versiones posteriores, como la 1.1, estaría corregido), que él mismo
  descartó en la junta. La vulnerabilidad **sigue** en 1.1: la integridad (MIC) se
  verifica en el Network Server y el payload cifrado llega al Application Server sin
  integridad de extremo a extremo. Coincide con lo que afirma el README.
- **Términos mal transcritos:** «2 55» = 155 ppb; «LCM», «LCTM», «síntesis» = LSTM.

### K3: búsqueda de datasets y trabajo previo (2026-10-05)

Búsqueda web; no exhaustiva. «No encontrado» no significa que no exista.

**Lo más cercano al giro propuesto (afecta la novedad):**

- [Semi-Synthetic LoRaWAN Dataset for Jamming and Battery-Depletion Attack Detection](https://zenodo.org/records/22044142)
  (A. Pourghasem, Zenodo, 21/ago/2026, CC BY 4.0): 230 296 registros de 1 921 dispositivos,
  etiquetados normal / jamming / drenado de batería. Parte de tráfico real (despliegue de
  Brno) con ataques **añadidos de forma sintética**: jamming = RSSI anómalo; drenado =
  caída acelerada de batería. Campos: RSSI, SNR, SF, altitud, batería, velocidad de caída.
  **No** incluye ventanas de recepción, ACK ni reintentos.
- Artículos que lo usan: [Multi-Attribute Physical-Layer Authentication Against Jamming and Battery-Depletion Attacks in LoRaWAN](https://doi.org/10.3390/fi18010038)
  (Future Internet 18(1):38) y [su variante ligera](https://www.mdpi.com/1999-5903/18/9/462)
  (18(9):462): clasificadores (MLP, Random Forest, XGBoost…) en el Network Server; la mejor
  F1 reportada es ≈0.83.
- [Detection and Mitigation of Jamming Attacks in LoRaWAN Using Machine Learning](https://ieeexplore.ieee.org/document/10978351/)
  (IEEE, 2025): **detector LSTM de jamming**.
- [Reactive Jamming Detection for LoRaWAN Based on Meta-Data Differencing](https://dl.acm.org/doi/fullHtml/10.1145/3538969.3543805) (ARES 2022).
- [Energy attack in LoRaWAN: experimental validation](https://urn.fi/URN:NBN:fi-fe202001101701)
  (Mikhaylov et al., ARES 2019): el ataque **fuerza reintentos**; sin claves, aumenta el
  consumo de un evento de comunicación entre 36 % y 576 % según el SF.

**Datasets reales con metadatos de recepción (sin etiqueta de ataque ni ventana):**
[LoED](https://zenodo.org/record/4121430) (Bhatia et al. 2020, 9 gateways, captura pasiva,
CC BY; campos por verificar en los CSV), [LoRaWAN Traffic Analysis Dataset](https://zenodo.org/records/8090619)
(sniffer, CSV/PCAP, 1.2 GB), [propagación urbana](https://www.nature.com/articles/s41597-025-05802-2)
(Scientific Data 2025, RSSI/SNR) y [RSSI en entorno industrial](https://pmc.ncbi.nlm.nih.gov/articles/PMC10859256/).

**Herramientas:** [ChirpOTLE](https://arxiv.org/pdf/2005.11555) (banco de pruebas para
evaluar seguridad de LoRaWAN en la práctica) y simuladores (ns-3, LoRaWANSim) que ya se
usan para generar datos de ACK.

**Implicación para K5:** detectar jamming y drenado con aprendizaje automático, incluso
con LSTM, ya está publicado. Un aporte propio tendría que venir de lo que esos trabajos no
cubren: el **mecanismo** (reintentos, ventanas RX1/RX2, ACK) en lugar de efectos
sintéticos sobre RSSI o batería; un **modelo de energía** por evento; un **dataset medido**
de recepción por ventana; y la caracterización de **qué se detecta y qué no** según el
atacante (agresivo frente a intermitente), en la línea de la primera parte. Discutir con el
asesor antes de escribir el protocolo.

### Lectura del artículo principal: Di Pinto et al., IEEE WCNC 2025

*Detection and Mitigation of Jamming Attacks in LoRaWAN Using Machine Learning* (Sapienza,
DOI 10.1109/WCNC61545.2025.10978351). PDF local en `docs/`, **descargado con la licencia
de UNAM: no se versiona ni se redistribuye** (`*.pdf` en `.gitignore`).

- **Qué hace:** jamming ciego y jamming que escucha el canal, **sólo en ns-3** (250 nodos,
  1 gateway, 1 jammer, 12 × 12 km, envíos cada 20 min, banda europea de 868 MHz). LSTM
  sobre el **número de paquetes por intervalo de 30 min**, entrenado sólo con el jammer
  ciego: exactitud 0.85, precisión 0.93, recall 0.81 en prueba. Mitigación en el gateway
  (cambio de canal por comandos MAC); no funciona contra el jammer que escucha el canal.
- **Qué deja pendiente, según su propio trabajo futuro:** pruebas en entornos reales,
  RSSI/SNR, **evaluación del consumo de energía**, varios gateways y jammers, y
  **detección centralizada en el Network Server**.
- **Qué no hace:** drenado de batería por reintentos, modelo de energía, datos medidos,
  caracterización de qué intensidad de ataque se escapa, detección por nodo.
- **Código público:** [netlab-sapienza/LoRaWANjammer_ns3](https://github.com/netlab-sapienza/LoRaWANjammer_ns3),
  posible base de simulación y línea base de comparación.

### Propuesta para el Doc Jaime: metodología de daño no detectado (2026-10-05)

**Propuesta:** en lugar de analizar ataques por separado, la tesis aporta una
**metodología para cuantificar el daño que escapa a la detección en LoRaWAN**, aplicable a
ataques cuyo efecto se mide como desviación de un comportamiento normal, y **validada en
dos ataques de capas distintas**: bit flipping (integridad, ya hecho) y drenado de energía
(disponibilidad, por hacer). No se afirma que sirva para «cualquier ataque»: dos casos
muy distintos son el argumento de generalidad.

| Paso | Bit flipping (hecho) | Drenado de energía (por hacer) |
|---|---|---|
| 1. Definir el daño operativo | Cambio de decisión NOM-172 o de excedencia de 155 ppb | Energía extra y vida de batería perdida |
| 2. Modelar lo normal | Perfil de 14 días + LSTM con las vecinas | Pérdida natural de paquetes, reintentos y RSSI/SNR del canal |
| 3. Detectar por desviación | Residuo > umbral p95 calibrado en otro año | Desviación de la telemetría normal en el Network Server |
| 4. Variar la intensidad del atacante | Bits 0 a 7 | Porcentaje de ACK o transmisiones interferidas |
| 5. Medir el daño que escapa | Bits 3–5 | Por descubrir |

**Hipótesis común:** un ataque es indetectable cuando su efecto cae dentro de la
variabilidad legítima del sistema. Confirmada en la parte 1 (variabilidad del ozono,
±12–15 ppb); la parte 2 la prueba en otra capa (variabilidad del canal de radio).

**Prioridades del tesista para la parte 2:**

1. **Salir de la simulación:** banco de pruebas real (nodos, gateway, Network Server propio,
   p. ej. ChirpStack). Confirmar el plan de frecuencias aplicable en México (rango
   902–928 MHz; el artículo usa la banda europea de 868 MHz).
2. **Energía cuantificable:** medir la corriente por estado (transmisión según SF, RX1/RX2,
   reposo) y construir un modelo de energía por evento de comunicación.
3. **Datos reales:** las lecturas RAMA como **contenido** de los mensajes del banco de
   pruebas (radio real + datos reales); la medición real es la del radio y la energía.
4. **Detección en el Network Server:** telemetría por nodo (contador de tramas, reintentos,
   ACK, RSSI/SNR, tiempos entre llegadas).
5. **Por definir:** caracterización de límites (intensidad del atacante frente a daño y
   detección, como el punto ideal del atacante de la parte 1).

**Entorno de los experimentos:** sala de señales blindada del IIMAS y laboratorio autorizado.
El jammer, el nodo víctima y el gateway deben quedar dentro del entorno controlado; se
documentan autorización y potencias en la metodología. La emulación del ataque desde el
servidor (suprimir ACK) queda como complemento para repetir patrones exactos.

**Cómo afectaría a la tesis:** título y objetivo general hacia la caracterización del daño no
detectado de ataques a LoRaWAN en una red de monitoreo de calidad del aire; ajustar la
sección 1.6 y los objetivos; capítulos 4 y 5 divididos en 4.1/5.1 (bit flipping) y 4.2/5.2
(drenado), más una comparación final con la hipótesis común; Di Pinto et al. en el capítulo 3.
**Vínculo opcional:** el drenado de las estaciones vecinas reduce el contexto del detector y la
redundancia de la red, lo que podría facilitar el bit flipping. Se deja como discusión o
trabajo futuro salvo que el asesor lo quiera dentro.

**Decisión del tesista:** avanzar sin esperar aprobación formal, **informando** al asesor.
Primero el trabajo útil con cualquier enfoque (banda de frecuencia, inventario de hardware,
ChirpStack, línea base de consumo y pérdida natural, código de Di Pinto et al.); después lo
costoso de deshacer (título y objetivos, compras grandes, detector de la parte 2).

### K9a: banda de frecuencia para México (2026-10-05)

Fuente primaria: [LoRa Alliance RP002-1.0.3](https://lora-alliance.org/wp-content/uploads/2021/05/RP002-1.0.3-FINAL-1.pdf)
(2021), sección 1.2, tabla de países. No se pudo descargar la 1.0.4 (403); por verificar si
cambia algo.

- **México (MX): 902–928 MHz, plan US902-928**, con la nota al pie 1: «AU915-928 also applies
  to this band». Ambos planes son válidos; el sugerido en primer lugar es **US915**. La
  columna de dispositivos certificados con homologación (*Regulatory Type Approval*) está
  **vacía** para México: la homologación ante el IFT es aparte.
- **Regulación local:** el IFT regula 902–928 MHz con la disposición técnica
  **IFT-008-2015** (espectro disperso; sustituyó a la NOM-121-SCT1-2009). Los límites de
  potencia y de tiempo de ocupación del canal en esa disposición están **por verificar**.
  En la sala blindada la emisión queda confinada, pero se documenta igual (ver «Entorno de
  los experimentos»).
- **Parámetros de US915 que importan para el segundo ataque** (RP002-1.0.3, 2.5):
  - Subida: 64 canales de 125 kHz (902.3–914.9 MHz) más 8 de 500 kHz.
  - Bajada: 8 canales de 500 kHz (923.3–927.5 MHz).
  - **RX1 abre 1 s después del envío y RX2 a los 2 s**; RX2 usa por omisión 923.3 MHz con DR8.
  - Potencia máxima: +30 dBm; tiempo máximo en el aire por envío (*dwell time*): 400 ms.
- **Diferencia con Di Pinto et al.:** ellos usan la banda europea de 868 MHz, con límite
  de ciclo de trabajo (*duty cycle*). US915 no tiene ese límite pero sí el de 400 ms, que
  impide usar SF11–SF12 en 125 kHz. Los factores de dispersión disponibles y el costo
  de un reintento cambian; el modelo de energía debe hacerse con los parámetros de US915.
- **Pendiente:** elegir la subbanda (grupo de 8 canales) del gateway. Depende del
  hardware del inventario; ChirpStack se configura con la misma.

### Pendientes

| # | Pendiente | Estado |
|---|---|---|
| K1 | Llevar al asesor la explicación de la distribución B (primera aclaración) | Pendiente |
| K2 | Aclarar «12 ventanas» y la frase sobre la versión corregida | **Resuelto 2026-10-05** (ver «Dudas por resolver») |
| K3 | Buscar un dataset público de recepción por ventana o intento | **Revisado 2026-10-05:** no se encontró uno con ventana/ACK/reintento por mensaje; sí trabajo previo muy cercano (ver «K3: búsqueda de datasets y trabajo previo») |
| K4 | Si no existe, diseñar el experimento con nodos reales (hardware, distancias, frecuencia) | Pendiente |
| K5 | Protocolo del segundo ataque antes de programar: ataque, modelos de atacante, modelo de energía, datos y métricas | Enfoque en borrador (ver «Propuesta para el Doc Jaime»); falta el protocolo |
| K6 | Redactar la primera parte (bit flipping) con los resultados ya obtenidos | Pendiente |
| K7 | Actualizar el README cuando el giro esté definido | Pendiente |
| K8 | Informar al asesor la propuesta de metodología y el inicio del trabajo | Pendiente |
| K9 | Trabajo inicial de la parte 2: banda de frecuencia, inventario de hardware, ChirpStack, línea base de consumo y pérdida natural | **Banda resuelta 2026-10-05** (US915; ver «K9a»). Inventario, ChirpStack y líneas base pendientes |

---

## 2026-10-12 — Junta con el asesor: anomalías a nivel de red

Fuente: transcripción automática de mala calidad. Los hablantes se mezclan, así que la
atribución de cada idea es aproximada. Se llevaron
[dos propuestas](propuestas_reunion_2026-10-12.md) (consumo y detección; integridad y costo
de protección). **Ninguna se adoptó.**

### Contexto

- El Dr. Orozco (UCLM) envió dos artículos. El primero es un IDS con aprendizaje federado
  y supervisado, con F1 ≈ 99 %. El segundo es un *survey* de ataques. En ambos, los
  ataques son **ruidosos** (DoS, jamming, inundaciones) y vienen bien etiquetados. Eso
  explica las métricas altas y los aleja del bit flipping.
- Sugerencia de Orozco, según la explica el asesor: dejar de ver el ataque a **un**
  sensor y ver la **red como un todo**. Se supone un nodo ya malicioso o descompuesto, y
  se usa la información de los demás para detectar que «hace cosas raras». Ejemplo del
  asesor: todos los sensores marcan 28–29 °C y uno marca 50 °C.

### Acuerdos

| # | Acuerdo |
|---|---|
| L-A1 | El bit flipping **se conserva**: ya es una contribución (caracterización formal de qué bits producen daño y cuáles detecta el LSTM). |
| L-A2 | El drenado de energía con banco real **no se sigue por ahora**. Implementarlo «nos va a hacer perder un chorro de tiempo», igual que pasó con el atacante interno en bit flipping. |
| L-A3 | Nueva dirección: **detectar sensores anómalos a nivel de red**, por error de calibración, falla o nodo malicioso. La anomalía no tiene por qué ser maliciosa. |
| L-A4 | Primer paso con datos existentes: las estaciones RAMA. Su lejanía entre sí es una limitación conocida que se acepta. |
| L-A5 | Datos: matriz con **una fila por hora y una columna por estación**. |
| L-A6 | Anomalía inicial: **error de calibración multiplicativo** (+10 % sobre el valor real). Dura un número aleatorio de **1 a 7 días** y se aplica a estaciones elegidas al azar, no siempre la misma. Se etiqueta como «anomalía». Puede haber episodios simultáneos en dos estaciones. |
| L-A7 | Corridas por severidad: muy obvia (×2, ×3, ×4), 50 %, 20 %, 10 % y 5 %. Después, una versión aleatoria entre 10 y 50 %. |
| L-A8 | Primera tarea: **anomalía / no anomalía, sin importar dónde**. Localizar el nodo viene después. |
| L-A9 | División **por años completos**, no al azar (el LSTM necesita historia). Se reutiliza el esquema del protocolo V4: ajuste 2020–2021, validación 2022, ajuste definitivo 2020–2022, calibración 2023, prueba 2024 y complementarias 2025 y 2026. |
| L-A10 | Modelos: del más simple (Random Forest) al más complejo (LSTM). Meta del asesor: una detección «decente», del 80–90 %. |
| L-A11 | Por ahora no se tocan las estaciones sin datos. |
| L-A12 | El asesor pide **investigar si esto ya se hizo**. Él cree que no, al menos con ozono y en este escenario. |

**Descartado en la junta:** la «calculadora de severidad» de ataques (el asesor: «nos
metemos con un montón de ataques»). La idea de poner varios nodos por estación para darle
resiliencia se considera «lo mismo» que detectar el sensor anómalo.

**Idea paralela del asesor, sin compromiso:** montar una red propia de 10–20 estaciones
meteorológicas con celda solar en varios edificios. Guardarían datos durante 1–2 meses sin
necesidad de LoRa; las anomalías se inyectarían después. Pendientes: permisos, una
cotización de tarjeta y un equipo de prueba en camino. Mientras tanto se trabaja con RAMA.

**Plazo:** el asesor señala que el semestre termina en mes y medio y que la meta es
terminar durante la estancia en UCLM.

### Verificaciones contra el repositorio (2026-10-12)

- **Cobertura** (`data/processed/o3_2020_2026_ancho.parquet`, 36 columnas, 2020-01 a
  2026-07): **COY y SJA nunca reportan** (en la junta se dijeron 3). SFE deja de reportar en
  2023. Hay estaciones con años completos vacíos: ACO 2020 y 2024, XAL 2020–2022, HGM
  2021–2022, CHO 2020 y 2026, AJM 2021 y FAR 2026. Sólo el **9.7 %** de las horas tiene
  ≥30 estaciones con dato. La matriz «una columna por estación» tendrá huecos estructurales:
  el conjunto de estaciones activas cambia entre años de ajuste y de prueba.
- **Estimación exploratoria de la detectabilidad de un sesgo de calibración.** No es un
  resultado aceptado. Usa las predicciones limpias **guardadas en disco** del LSTM V4 de
  CCA (`results/lstm_v4_multianual_v1/estaciones/CCA/`, calibración 2023 y prueba 2024);
  **no se entrenó ningún modelo**. Se suma k·valor real al residuo y se promedia por día o
  ventana. El umbral es el p95 del residuo medio limpio de 2023.
  - En 2024 el ozono medio de CCA es 33.8 ppb: un +10 % equivale a **3.4 ppb** en
    promedio (6.5 ppb entre 12 y 18 h). El σ del residuo horario es de 11.8 ppb.
  - Promediar no reduce el ruido tanto como se esperaría, porque el residuo está
    autocorrelacionado: σ diario 6.8 ppb, σ en 7 días 5.1 ppb.

    | Ventana | Limpio (FP) | +5 % | +10 % | +20 % | +50 % | +100 % |
    |---|---:|---:|---:|---:|---:|---:|
    | 1 día | 4.9 % | 9.2 % | 13.6 % | 24.6 % | 69.1 % | 94.5 % |
    | 3 días | 4 % | 7 % | 12 % | 27 % | 75 % | — |
    | 7 días | 5 % | 7 % | 12 % | 30 % | 87 % | — |

  - Es una **cota optimista**. No considera que el perfil base adaptativo de 14 días se
    calcula con los valores de la propia estación, así que un sesgo sostenido se
    incorpora a la base (alrededor de la mitad tras 7 días) y el residuo se encoge.
    Tampoco se probó un detector diseñado para sesgo multiplicativo (por ejemplo,
    pendiente o razón frente a las vecinas). CCA es además la estación con mejor
    cobertura (94 %).
  - **Lectura:** con este detector, un error del 10 % cae dentro del error lento del
    propio modelo. La meta del 80–90 % sólo parece alcanzable para sesgos del 50 % o más.
    Es la misma hipótesis común de la parte 1: lo que cae dentro de la variabilidad
    legítima no se detecta.

### Aclaración del tesista sobre el método (2026-10-12)

La estimación anterior **no evalúa el enfoque acordado**. Mide el detector de la parte 1:
predecir el valor de una estación con las demás y alertar si el residuo pasa un umbral.
El acuerdo de la junta es otro:

- **Unidad de análisis: la red, no un nodo.** El modelo recibe la matriz de todas las
  estaciones y decide si hay anomalía en la red. Localizar la estación viene después.
- **Aprendizaje supervisado con datos etiquetados.** Ya no se estima el valor esperado: el
  modelo aprende qué es el comportamiento estándar de la red a partir de ejemplos
  etiquetados normal/anomalía. El LSTM de la parte 1, entrenado para predecir y sin
  etiquetas, no aprendía a separar bien los casos.
- **Anomalía, no necesariamente ataque:** una alteración de X % (calibración, falla o
  nodo malicioso).
- **Ejes del experimento:** severidad de la alteración (100 %, es decir el doble, y
  menores), **número de estaciones afectadas (N)** y **duración (N tiempo)**.
- **Entrenamiento por años completos** (ver L-A9), no con la división temporal dentro de
  un año que se usó en bit flipping.

La tabla de la estimación anterior queda, a lo sumo, como **línea base de comparación**
del enfoque por residuo. No predice el desempeño del clasificador supervisado.

### Decisiones del tesista sobre el diseño (2026-10-12)

1. **Barrido de lo ruidoso a lo sutil.** Se empieza con alteraciones del 100 % (el doble),
   sabiendo que son ruidosas, para encontrar hasta dónde se puede empujar el límite, igual
   que con bit flipping. La alteración va desde una mala calibración hasta un ataque de
   cualquier tipo; no necesariamente bit flipping.
2. **Varios *runs*, un DS por severidad** (100 %, 50 %, 10 %…). Cada DS lleva alteraciones
   en horas aleatorias y nodos aleatorios. La probabilidad de ataque se sortea por *run*
   (como un *nonce*), dentro de un rango realista: la referencia es el 5 % por lectura de
   la parte 1. Objetivo: que el modelo no aprenda la huella del script.
3. **Exclusiones por ahora:** COY, SJA y SFE. **XAL** queda como experimento posterior
   sobre qué pasa cuando una estación reporta y deja de reportar. Orden: primero lo más
   importante, después lo específico o difícil.
4. **Novedad:** comparar el bit flipping visto por nodo con las anomalías vistas en la
   red, y mostrar que afirmar que un F1 «es exitoso» depende mucho de qué tan ruidoso es
   el ataque y de la calidad del detector, desde modelos fáciles (Random Forest) hasta
   complejos (LSTM). **La parte 1 se conserva:** el aporte es la comparación entre ataques.

**Observaciones de revisión (Claude, 2026-10-12), por resolver en L2:**

- **La probabilidad de ataque debe definirse por ejemplo, no por lectura.** Con 33
  estaciones y 5 % por lectura, el 81.6 % de las horas-red tiene al menos una lectura
  alterada, y casi el 100 % de las ventanas de 24 h. Con 0.5 % por lectura, el 15.2 % de
  las horas y el 98.1 % de las ventanas de 24 h. Cálculo: 1 − (1 − p)^n, con n lecturas
  por ejemplo.
- **Diseño pareado entre severidades.** Si cada DS sortea su propia probabilidad, la
  diferencia de F1 entre el 100 % y el 10 % mezcla severidad y prevalencia. El F1 depende
  de la proporción de positivos. Propuesta: el mismo plan aleatorio (horas, nodos,
  probabilidad) para todas las severidades de un *run*, cambiando sólo la magnitud. Los
  distintos *runs* (semillas) dan la variabilidad. Reportar también recall con una tasa
  fija de falsas alarmas, que no depende de la prevalencia.
- **Reproducibilidad:** guardar la semilla y el plan de inyección de cada *run*
  (CLAUDE.md).
- Distinguir **alteraciones de horas sueltas** (comparables con bit flipping, por lectura)
  de **episodios de 1–7 días** (calibración, L-A6). Son dos tipos de anomalía.
- Para comparar con la parte 1 hace falta fijar algo común entre ambas: magnitud de la
  alteración (ppb o %) y una métrica con tasa fija de falsas alarmas. Entre las dos partes
  cambian a la vez el tipo de ataque, la unidad (nodo o red) y el aprendizaje
  (predicción o supervisado).

### Revisión rápida de novedad (2026-10-12)

Búsqueda web, no exhaustiva; sólo resúmenes. **Hay antecedentes directos**, así que no
puede afirmarse que «nadie lo ha hecho»:

- Detección de niveles anormales de ozono en la red de estaciones de Alta Normandía
  (Francia) con PCA-GLR, PCA-MEWMA y RBM + OCSVM (Harkat, Dairi y coautores).
  [PCA-GLR](https://elmi.hbku.edu.qa/en/publications/detecting-abnormal-ozone-levels-using-pca-based-glr-hypothesis-te/),
  [autores](https://univ-oran.academia.edu/AbdelkaderDairi).
- Estimación de cada sensor a partir de sus vecinos para detectar deriva y *offset* en
  redes ambientales (Jesus, Oliveira y Casimiro, LNEC).
  [P 3231](https://repositorio.lnec.pt/bitstream/123456789/1014234/2/P_3231.pdf).
- Revisión de algoritmos de calibración *in situ* en redes de sensores ambientales
  (Delaine, Lebental y Rivano, IEEE Sensors J. 2019).
  [HAL](https://hal.archives-ouvertes.fr/hal-02174938).
- Detección de deriva con un *proxy* de sitios vecinos en una red de bajo costo
  (Auckland). [Registro](https://researchspace.auckland.ac.nz/handle/2292/41596).
- Control estadístico de procesos para sesgos de instrumentos de ozono (Bologna, 1997).
  [WIT](https://witpress.com/elibrary/wit-transactions-on-ecology-and-the-environment/21/7448).

Posibles diferenciadores, por verificar al leer los textos completos:

- La **frontera de detección por severidad y duración**, medida con el daño operativo
  (cambio de banda NOM-172 o excedencia de 155 ppb) y no con métricas genéricas.
- Una red **dispersa** de referencia (RAMA) frente a las redes densas de bajo costo.
- Tratar en un solo marco un nodo comprometido y un sensor descalibrado: producen la
  misma señal, y eso limita la atribución.

### Dudas para el asesor

1. **Unidad de decisión:** ¿hora-red, día-red o día-estación? Si se inyectan episodios
   «en todas las estaciones», casi toda hora-red tendría alguna anomalía y la etiqueta
   binaria quedaría casi siempre en 1. Hace falta fijar la tasa de episodios por estación
   y año.
2. «Siempre lo vas a cortar en un horario en particular»: ¿el episodio empieza o termina a
   una hora fija, como cuando llega el técnico a recalibrar?
3. ¿El detector supervisado (Random Forest → LSTM) se compara contra el residuo del V4 como
   línea base no supervisada? Las predicciones limpias ya existen para 31 estaciones.
4. Si la estación anómala es también entrada de las demás, contamina el contexto de sus
   vecinas. ¿Se acepta así o se controla?
5. ¿Cómo se integra con el título y los objetivos de la tesis (LoRaWAN)? El asesor dijo
   que encajar las dos partes «no es tanto problema», pero no quedó definido.

### Estado de K1–K9 tras la junta

K4, K5 y K9 (drenado de energía y banco de pruebas) quedan **en pausa** por L-A2. Lo hecho
en K9a se conserva. K6 (redactar la parte 1) **sigue vigente**. K7 espera a que se defina
el encaje. K1 y K8 quedan sin efecto con este giro, salvo que el asesor pida retomarlos.

### Pendientes

| # | Pendiente | Estado |
|---|---|---|
| L1 | Leer los antecedentes de la revisión de novedad y fijar el diferenciador | Pendiente — antes de programar |
| L2 | Escribir el protocolo de inyección: unidad de decisión, tasa, duración, severidades e interacción con faltantes | **Escrito** (2026-10-12): [`protocolo_anomalias_red_v1.md`](protocolo_anomalias_red_v1.md). Ver «L2: protocolo de la parte 2». Quedan sus pendientes P1–P6 |
| L3 | Línea base barata: residuo guardado del V4 por estación con ventanas de 1, 3 y 7 días | **Opcional** (aclaración 2026-10-12): sólo como comparación; no es el método acordado |
| L4 | Clasificador supervisado a nivel de red (primero Random Forest) con la división por años del V4 | Pendiente — después de L2. **Es el método principal** (aclaración 2026-10-12) |
| L5 | Redacción de la parte 1 (antes K6) | Pendiente |
| L6 | Red propia de sensores: cotización, equipo de prueba y permisos | Idea paralela del asesor; sin compromiso |
| L7 | Resolver las dudas para el asesor | Pendiente |

### L2: protocolo de la parte 2 (2026-10-12)

Escrito en [`protocolo_anomalias_red_v1.md`](protocolo_anomalias_red_v1.md) y fijado antes de
programar. Reúne las decisiones del tesista y las recomendaciones de revisión que aceptó el
mismo día. En corto:

| Elemento | Decisión |
|---|---|
| Pregunta | ¿El detector alerta de una anomalía en la red, y con qué tamaño y duración de la anomalía? Sólo alerta, no corrige |
| Estaciones | Matriz del V4 (33 columnas, con XAL inactivo). Se alteran los 31 objetivos del V4 |
| Alteración | x·(1 + δ) con signo + o x/(1 + δ) con signo −; δ = 100, 50, 20, 10 y 5 %. El signo se sortea una vez por episodio |
| Episodios | Días completos, de 1 a 7, desde las 00 h. Sólo se alteran horas con dato |
| Tasa | Probabilidad por estación y día entre 0.10 y 0.30 % (base 0.15 %), sorteada en cada corrida: unos 17 episodios al año en la red y 1.5 % de horas con coincidencias |
| Diseño | Un plan por corrida para todos los δ (pareado). 10 corridas en 2024 y un plan de entrenamiento en 2020–2022 |
| Detectores | Random Forest (supervisado, 66 columnas de la hora t, un modelo por δ), IsolationForest y V4 cargado de disco. LSTM clasificador opcional |
| Umbrales | Falsas alarmas por hora de red de 5 y 1 %, calibradas en 2023 limpio |
| Métricas | Episodios detectados, horas hasta la primera alerta y daño antes de la alerta (bandas NOM-172 y 155 ppb), por δ y por signo. El F1 sólo como contraste |

Las equivalencias de la tasa salen de una simulación (31 estaciones, 200 años, semilla 42) en
la que no interviene ningún modelo.

**Corrección (2026-10-12):** durante la revisión del protocolo se dijo que el 5 % de falsas
alarmas por hora permitía comparar directamente con la parte 1. No es así: el 5 % por hora de
red es mucho más estricto por estación que el p95 por lectura de la parte 1. Por eso el
protocolo también reporta el V4 con su umbral original (§9).

**Dudas para el asesor que resuelve el protocolo:**

- **1. Unidad de decisión:** la hora de red, y en cada episodio sólo cuenta la primera
  alerta.
- **2. Horario de inicio:** días completos desde las 00 h, según lo que el asesor dijo en la
  junta («en días completos durante ciertos días»).
- **3. Línea base no supervisada:** sí, con el V4 y el IsolationForest.
- **4. Contaminación del contexto:** se acepta y se declara.

**Sigue abierta** la 5 (vínculo con LoRaWAN y título), que pasa a ser la P6 del protocolo.

---

## 2026-10-13 — Parte 2: generador de planes de inyección

Es el primer paso de L4 y no depende de P1–P6. **Aquí no interviene ningún modelo:** sólo se
sortean planes y se aplican a la matriz real del V4 (`em.contexto`, con los SHA-256 de los
.xls verificados).

- **Código:** `src/detect/anomalias_red.py` (corridas, plan, anomalía, etiquetas),
  `experiments/anomalias_red/generar_planes.py` y `tests/test_anomalias_red.py` (17 pruebas).
- **Pruebas que pasan:**
  - el mismo plan sale con la misma semilla;
  - el plan es el mismo para todos los δ y sólo cambian horas del plan;
  - las estaciones son independientes entre sí;
  - los episodios son días completos, sin traslapes, y se cortan al final del periodo;
  - +δ multiplica y −δ divide, con redondeo a enteros;
  - las horas sin dato no se tocan;
  - la tasa simulada coincide con la tabla del §6 (≈ 0.56 episodios por estación y año).
- **Salidas** en `results/anomalias_red_v1/`: `planes/plan_<corrida>.csv` (11 planes) y
  `resumen_planes.csv`. Cada plan se generó dos veces y salió idéntico. El script se detiene
  si un plan ya existe y es distinto.

| Corridas | p | Episodios | Evaluables | Horas de red con alguna estación en episodio |
|---|---|---:|---:|---|
| Entrenamiento 2020–2022 | 0.150 % | 61 | 50 | 20.9 % |
| 10 corridas de prueba en 2024 | 0.101–0.286 % (promedio 0.21 %) | 223 (10 a 31 por corrida) | 192 | 10.1–26.0 % |

**Aclaraciones registradas como revisión 1 del protocolo** (antes de entrenar nada):

- Redondeo a ppb enteros, para que los decimales no delaten la anomalía.
- La etiqueta es «la lectura cambió».
- Un episodio es evaluable si tiene al menos una hora con dato.
- Claves de semilla.
- El promedio de p es 0.20 % y no la base de 0.15 %.

**Episodios sin dato.** De los 31 episodios de prueba sin datos, 7 son de ACO (sin datos en
2024). Los demás caen en huecos largos de 13 estaciones. Las de menor cobertura ese año son
CHO, GAM y MPA, con alrededor del 60 % de las horas con dato.

**Siguiente:** construir las 66 columnas por hora de red y entrenar el Random Forest con el
plan de entrenamiento, un modelo por δ (L4).

### Matrices de red para revisión (2026-10-13)

A pedido del tesista se generaron sólo las matrices, sin entrenar nada, para revisarlas por
separado. Tampoco aquí interviene ningún modelo.

- **Código:** `ar.matriz_red` y `ar.leer_matriz` en `src/detect/anomalias_red.py`,
  `experiments/anomalias_red/generar_matrices.py` y 3 pruebas nuevas (20 en total).
- **Salidas:** 58 archivos en `results/anomalias_red_v1/matrices/` (22 MB) y
  `resumen_matrices.csv`. Las matrices no van a git porque se regeneran exactamente desde los
  planes (`.gitignore`).
- **Formato:** una fila por hora, en orden y sin horas faltantes. Las columnas son:
  - 32 `<estación>_valor` en ppb (vacío = sin dato);
  - 32 `<estación>_mascara` (1 = hay dato);
  - `hora_sin` y `hora_cos`;
  - fuera de la entrada del modelo, `anomalia_red` (0/1) y `estaciones_alteradas`.

  XAL queda fuera porque es canal inactivo. La normalización se hará al entrenar.

| Matrices | Periodo | Uso |
|---|---|---|
| `limpia_2020_2022` | 2020–2022 | Entrenamiento del IsolationForest |
| `entrenamiento_d<δ>` (5) | 2020–2022 | Entrenamiento del Random Forest, uno por δ |
| `limpia_2023` | 2023 | Calibración del umbral |
| `limpia_2024` | 2024 | Falsas alarmas |
| `prueba_2024_<k>_d<δ>` (50) | 2024 | Examen: 10 calendarios × 5 δ |

**Comprobaciones:**
- la rejilla horaria es continua y respeta los límites del periodo;
- las máscaras son idénticas a las de la matriz limpia;
- los valores cambian sólo en las lecturas marcadas como alteradas;
- los conteos coinciden con el resumen de episodios.

Una segunda ejecución dio los 58 archivos idénticos (mismo SHA-256 del contenido).

**Nota sobre el 80/20 de la parte 1** (duda del tesista, verificada en
`notebooks/06_deteccion.ipynb`):
- El 80/20 del notebook 06 era cronológico: el primer 80 % de las horas de CCA en 2025 para
  entrenar y el último 20 % para probar. Pero era dentro de un solo año, así que la prueba
  quedó en noviembre y diciembre.
- El mismo notebook comparó contra un `train_test_split` estratificado, que sí es aleatorio.
- En una celda, el IsolationForest se ajusta y se evalúa sobre los mismos datos.
- La parte 2 usa años completos, en orden, como el V4. Repetir esas celdas de la parte 1 con
  la división multianual es la P3 del protocolo.

### Revisión 2 del protocolo: nivel de azar (2026-10-13)

Al programar la evaluación apareció un error de la versión 0 del protocolo, cometido por
Claude. Con falsas alarmas fijas por hora, un episodio largo casi siempre recibe alguna alerta
por azar. Si las alertas fueran independientes, al 5 % el 71 % de los episodios de 1 día y el
99 % de los de 4 días tendrían alguna alerta. Se corrigió **antes de evaluar cualquier
detector**:
- cada detección por episodio lleva su nivel de azar, que son las mismas ventanas evaluadas con
  las alertas del año limpio;
- la detección por hora pasa a ser la métrica principal.

Ver la revisión 2 en el §15 del protocolo.

### Random Forest, δ = 100 % (2026-10-13)

**Modelo recién entrenado** (`experiments/anomalias_red/entrenar_rf.py --delta 100`).
- **Configuración:** hiperparámetros por omisión y `random_state=42`, con `fijar_semilla(42)`
  antes de entrenar.
- **Reproducibilidad:** dos entrenamientos dieron puntajes idénticos.
- **Normalización:** coincide con la del V4.
- **Salidas:** `results/anomalias_red_v1/rf/d100/`. El modelo (`modelo.joblib`, 6.5 MB) no
  va a git porque se regenera en segundos.

| Nivel | Falsas alarmas 2023 / 2024 limpio | Detección por hora | Episodios detectados (azar) | Mediana de horas hasta la alerta (azar) |
|---|---|---:|---|---|
| 5 % | 4.73 % / 3.01 % | 5.4 % | 47.4 % (42.7 %) | 15 (14) |
| 1 % | 0.89 % / 0.18 % | 0.7 % | 11.5 % (12.5 %) | 32 (40) |

Hay 192 episodios evaluables en las 10 corridas.

**Lectura:** con δ = 100 % (el doble o la mitad), el Random Forest está prácticamente al nivel
del azar. No es un error de código:
- **Memoriza:** el AUC dentro del entrenamiento es 1.0, pero en el examen va de 0.51 a 0.68
  según el calendario.
- **Pocos ejemplos:** el entrenamiento tiene 61 episodios (50 con dato). Sólo 29 de las 31
  estaciones tienen alguno, unos 2 por estación.
- **Aprende «cuándo» y no «qué»:** las máscaras pesan el 21 % de la importancia, así que el
  modelo usa los patrones de huecos que identifican periodos concretos.
- **La foto de la hora t no expresa bien la anomalía:** con valores normalizados por estación,
  un 2× de la mañana puede caer en el rango normal de la tarde. Para detectarlo hay que comparar
  con las vecinas, y eso un árbol lo aprende mal con tan pocos ejemplos.

**Riesgo de interpretación (sinodal):** este resultado mide el diseño del Random Forest (la
foto de 66 columnas y unos 50 episodios), no si el doble es detectable en la RAMA. No sirve
para afirmar que «el doble no se detecta».

**Pendiente de decisión del tesista:** seguir con el resto de δ tal cual, o definir una
variante y elegirla con la validación 2022 antes de volver a tocar 2024. Las variantes
posibles son más calendarios de entrenamiento y columnas relativas a las vecinas.

**Verificación pedida por el tesista: ¿el δ = 100 % altera de verdad?** Se compararon las 10
matrices de examen con la matriz de 2024 limpio, sin modelos.
- **Alcance:** 15,976 lecturas alteradas; 8,533 con signo + y 7,443 con signo −.
- **El valor original en las horas alteradas es bajo:** mediana de 28 ppb. Por eso el cambio en
  ppb es moderado:

| | Signo + (doble) | Signo − (mitad) | Todas |
|---|---:|---:|---:|
| Mediana del cambio | 26 ppb | 15 ppb | 19 ppb |
| Cambio ≥ 32 ppb (como el bit 5) | 43 % | 17 % | 31 % |
| Cambio ≥ 64 ppb (como el bit 6) | 16 % | 0 % | 9 % |

- **Daño:** el 33.8 % de las lecturas alteradas cambia de banda NOM-172. Hay 808 cruces de
  155 ppb creados y 3 ocultados. Sobre las mismas lecturas, el bit 5 cambiaría de banda el
  24.5 % y el bit 6 el 100 %.
- **Conclusión:** la alteración se aplica bien y hace daño. En ppb, el δ = 100 % se parece al
  bit 4–5, que es la frontera de la parte 1, y no al bit 6–7. El bit 6 mueve 64 ppb **todas**
  las lecturas, incluso las de la noche; el doble de 10 ppb es 20.

**Random Forest δ = 100 % (recién entrenado), según el tamaño del cambio.** Horas de examen
con etiqueta 1, agrupadas por el mayor cambio en ppb de esa hora; nivel de 5 %:

| Horas | Normales | Cambio 1–16 ppb | 16–32 | 32–64 | ≥ 64 |
|---|---:|---:|---:|---:|---:|
| Cuántas | — | 5,814 | 3,762 | 3,168 | 1,300 |
| Alertan | 2.8 % | 2.5 % | 3.7 % | 6.3 % | 20.5 % |

Aun con cambios de 64 ppb o más, el Random Forest de red alerta sólo el 20.5 % de las horas. En
la parte 1, el Random Forest de CCA detectó el 72.9 % del bit 6 (notebook 06, división
cronológica). La comparación es aproximada, porque allá no había falsas alarmas fijas.

**El diseño pone al Random Forest en desventaja:**
- es **un solo modelo para 32 estaciones con etiqueta de red**, así que no sabe cuál estación
  está alterada;
- tiene **unos 2 episodios por estación**.

En cambio, en la parte 1 había un modelo por estación con unas 340 lecturas atacadas,
repartidas en todo el año, y el V4 tiene un modelo por estación. Comparar ese Random Forest con
el V4 mezclaría la complejidad del detector con el diseño de la tarea. Queda pendiente la
decisión del tesista.

**Corrección (2026-10-13): muchas horas dobladas sí son obvias.** El tesista insistió en que
algo no cuadraba, y tenía razón. Decir que «en ppb el δ = 100 % se parece al bit 4–5» es cierto
en promedio, pero esconde lo importante.

- **Ejemplo de CUT, calendario `prueba_2024_01`:** las lecturas dobladas quedan por encima del
  máximo histórico de CUT a esa hora en marzo–mayo de 2020–2022. A las 03 h llega a 72 ppb
  (máximo histórico 40); a las 15 h, a 232 ppb (máximo 150).
- **El Random Forest les dio un puntaje de 0.43**, apenas encima del umbral de 0.42.
- **CUT tuvo sólo 3 episodios de entrenamiento:** uno con signo + (marzo de 2020) y dos con
  signo −.
- **Un árbol no extrapola:** un valor mayor que todo lo visto cae en la misma hoja que el máximo
  visto, y ese máximo correspondía a días normales.

**Diagnóstico con una regla simple, sin aprendizaje.** No es un detector del protocolo. El
puntaje de una hora es el máximo entre estaciones de |z|, con la media y la desviación de cada
estación a esa hora en 2020–2022, y el umbral se calibra en 2023. Con δ = 100 %:

| Nivel | Falsas alarmas en 2024 limpio | Horas anómalas detectadas | Horas con cambio ≥ 64 ppb detectadas |
|---|---:|---:|---:|
| 5 % | 13.3 % | 28.2 % | 88.0 % |
| 1 % | 4.2 % | 15.9 % | 65.2 % |

Con la misma alteración, el Random Forest detecta el 5.4 % de las horas anómalas y el 20.5 % de
las de cambio ≥ 64 ppb. La anomalía sí es detectable; lo que falla es el Random Forest
supervisado con pocos ejemplos por estación. La regla simple tiene su propio problema: su
umbral de 2023 da 13.3 % de falsas alarmas en 2024.

**Diagnóstico P4: bit flipping en el montaje de red** (2026-10-13). Se usó
`experiments/anomalias_red/diagnostico_bits.py`, con salida en
`results/anomalias_red_v1/diagnostico_bits_rf_red.csv`.
- **Qué se mantiene igual:** los calendarios, el Random Forest de red, la etiqueta de red y el
  umbral con 2023 limpio.
- **Qué cambia:** sólo la alteración. En las horas con dato de cada episodio, el valor pasa a
  ser valor XOR 2^bit, como en la parte 1.
- **Modelos recién entrenados,** uno por bit, entrenados una vez (es un diagnóstico).

| Alteración | Cambio en ppb | Detección por hora, nivel 5 % | Detección por hora, nivel 1 % |
|---|---|---:|---:|
| δ = 100 % | Proporcional; mediana 19 | 5.4 % | 0.7 % |
| Bit 5 | 32, siempre | 12.9 % | 2.4 % |
| Bit 6 | 64, siempre | 46.3 % | 25.4 % |
| Bit 7 | 128, siempre | 86.9 % | 82.0 % |

**Corrección (2026-10-13):** se había atribuido el fracaso sobre todo al montaje (un modelo
para 32 estaciones y unos 2 episodios por estación). El diagnóstico lo desmiente en parte: con
el bit 7, el mismo montaje y los mismos pocos episodios detectan el 87 % de las horas. **La
causa principal es el tamaño de la alteración en ppb, como propuso el tesista.** Hay además una
causa secundaria:
- con δ proporcional, la mayoría de las horas etiquetadas como anomalía tienen cambios chicos,
  indistinguibles de lo normal;
- el modelo recibe etiquetas contradictorias (el ejemplo del «80» del tesista) y alerta poco
  aun con los cambios grandes: sólo el 20.5 % de las horas dobladas con cambio ≥ 64 ppb;
- con el bit 6, todas las horas etiquetadas tienen el mismo cambio de 64 ppb, y detecta el
  46.3 %.

---

## 2026-10-15 — Idea exploratoria: ¿el NO y el NO2 bajarían el error del V4?

**Fuera de protocolo.** Es una idea que surgió en una conversación sobre las limitaciones del
LSTM: si el modelo viera variables que explican el ozono, tendría menos error y umbrales más
bajos. Sólo sirve para decidir si vale la pena dedicarle tiempo; no cambia la parte 1 ni la
parte 2.

- **Qué se hizo** (`experiments/diagnostico_no_no2/diagnostico_2022.py`, salida en
  `results/diagnostico_no_no2_2022/`):
  - se cargaron de disco los **modelos de selección** del V4, entrenados sólo con 2020–2021;
  - se calcularon sus residuos en la validación 2022 (el MAE reproduce el `val_mae` guardado
    en los 31 objetivos);
  - se ajustaron dos modelos auxiliares **recién entrenados** (HistGradientBoosting,
    `random_state=42`, dejando fuera un mes a la vez) para predecir ese residuo: A con la hora
    y B con la hora más el NO y el NO2 de la propia estación a la misma hora.
- **No usa** 2023 ni 2024–2026. Las variables meteorológicas (REDMET) no se descargaron y no
  se probaron.
- **Criterio fijado antes de correrlo:** mediana de los 28 principales de la reducción del p95
  de |residuo| de B frente a A. Con 10 % o más vale la pena explorarlo; entre 3 y 10 % es
  marginal; con menos de 3 % no vale la pena.
- **Reproducibilidad:** dos corridas dieron archivos idénticos.

| Mediana de los 28 principales | Valor |
|---|---:|
| p95 de \|residuo\| del V4 de selección en 2022 | 23.94 ppb |
| p95 tras corregir sólo con la hora (A) | 23.30 ppb |
| p95 tras corregir con la hora, NO y NO2 (B) | 23.38 ppb |
| Reducción del p95, B frente a A | **−0.3 %** |
| Reducción del MAE de la tarde (12–17 h), B frente a A | −1.7 % |

- **Veredicto: no vale la pena**, según el criterio previo. Sin las 3 principales que no tienen
  NO2 en 2022 (AJU, LLA y LPR), la mediana es −0.4 %. Sólo CHO pasa del 10 % (+11.9 %), y hay
  tantas estaciones que empeoran como que mejoran (de −5.1 % en SAG a +11.9 % en CHO).
- **Control con correlaciones:** la correlación de Spearman entre el residuo y el NO2 tiene
  mediana −0.08 (−0.09 con el NO) en las 21 principales con ambos datos. En la tarde es +0.17.
  La relación existe pero es débil.
- **Dónde está el error grande:** el 68 % de las horas con |residuo| mayor que el p95 cae entre
  las 12 y las 17 h, que son el 25 % de todas las horas. Es el error de la fotoquímica de la
  tarde (sol, mezcla, transporte), no el de la destrucción de ozono por el NO.
- **Límites:** la corrección se aplica después del V4, con la hora t de la propia estación. Un
  modelo nuevo que recibiera el NO y el NO2 de las vecinas durante 24 h podría aprovecharlos
  de otra forma. Lo que se muestra es que no hay una señal fácil de sacar, no que sea imposible.
- **Si se retoma:** el candidato más razonable sería la meteorología de la tarde (radiación,
  viento, temperatura) de REDMET, y requiere descargarla y emparejar estaciones. No se propone
  por ahora.

---

## 2026-10-16 — Parte 2: IsolationForest

**Contexto.** Se cerró la duda del tesista de si el ×2 es una anomalía «real». El tipo sí es
real: es un error de ganancia o de calibración del analizador. El tamaño no: la EPA tolera
±7.1 % en las revisiones de 14 días, así que el δ de 5–10 % es la zona realista y el de 100 %
es una falla grave o una manipulación. Los criterios vienen de una plantilla de 2017 y de un
memo de 2023, y falta confirmarlos en la versión vigente de la EPA y en la norma mexicana.
Queda como argumento para el §5 del protocolo; no se ha agregado.

**Revisión 3 del protocolo** (antes de evaluar): un solo IsolationForest para todos los δ,
hiperparámetros por omisión, puntaje −`score_samples` y desglose por tamaño del cambio.

**Predicciones registradas antes de correrlo** (δ = 100 %):
- **Tesista:** los resultados serán parecidos a los del Random Forest y, en parte, a los del
  bit flipping.
- **Claude:**
  1. detección por hora menor que 10 % con el nivel de 5 %, muy por debajo del 28.2 % de la
     regla |z|;
  2. con el signo − (la mitad), cerca del azar;
  3. en las horas con cambio ≥ 64 ppb, más que el 20.5 % del Random Forest, porque no sufre las
     etiquetas contradictorias, pero menos que el 88 % de la regla |z|. Dos razones: normaliza
     por estación sin distinguir la hora, y una sola estación alterada es una de 66 columnas;
  4. muchas alertas caerán en horas con más huecos de lo normal, porque las máscaras son
     entradas.

### Resultado: IsolationForest, δ = 100 % (2026-10-16)

**Modelo recién entrenado** (`experiments/anomalias_red/entrenar_if.py --delta 100`). Es un
solo modelo para todos los δ.
- **Configuración:** hiperparámetros por omisión y `random_state=42`, con `fijar_semilla(42)`
  antes de entrenar. Se entrena con 26,304 horas limpias de 2020–2022.
- **Reproducibilidad:** en cada corrida del script, dos entrenamientos dieron puntajes
  idénticos. El script se corrió tres veces, y las métricas, los episodios y los puntajes
  descomprimidos salieron idénticos. El hash del `.gz` cambia sólo por la fecha que el gzip
  guarda en su encabezado.
- **Normalización:** coincide con la del V4.
- **Salidas:** `results/anomalias_red_v1/if/d100/`. El modelo (`if/modelo.joblib`, 0.4 MB) no va
  a git.

| Nivel | Falsas alarmas 2023 / 2024 limpio | Detección por hora | Episodios detectados (azar) | Mediana de horas hasta la alerta (azar) |
|---|---|---:|---|---|
| 5 % | 5.00 % / 6.43 % | 6.7 % | 70.3 % (70.3 %) | 13 (13) |
| 1 % | 0.99 % / 1.64 % | 2.0 % | 39.6 % (38.5 %) | 16 (16) |

**Por tamaño del cambio**, nivel 5 %. Entre paréntesis, las mismas horas en 2024 limpio
(revisión 4). Los números del Random Forest se calcularon con sus puntajes guardados el
2026-10-13; su modelo fue recién entrenado ese día.

| Detector | Horas sin cambio | 1–16 ppb | 16–32 | 32–64 | ≥ 64 |
|---|---:|---:|---:|---:|---:|
| IsolationForest | 6.4 % | 0.8 % (0.8 %) | 1.8 % (1.8 %) | 10.4 % (10.9 %) | 38.8 % (36.2 %) |
| Random Forest | 2.8 % | 2.5 % (2.4 %) | 3.7 % (3.5 %) | 6.3 % (5.1 %) | 20.5 % (11.1 %) |

**Lectura:**
- **El IsolationForest no reacciona a la alteración.** En cada tramo alerta casi lo mismo con
  ella que sin ella. Por eso su 6.7 % por hora es su tasa de alertas de siempre, y por episodio
  empata con el azar.
- **Lo que marca son horas raras para la red completa:**
  - **la tarde:** en 2024 limpio alerta el 21 % de las horas de las 12 h y el 25 % de las de las
    15 h; de noche, entre 0 y 3 %;
  - **los huecos:** con más de 10 estaciones sin dato alerta el 16 % de las horas; con 6 o
    menos, el 5 %. En 2023, 20 % frente a 3 %.
- **Sus falsas alarmas en 2024 limpio (6.43 %) pasan del 5 % calibrado en 2023,** porque alerta
  por las tardes de ozono alto. Hipótesis sin verificar: 2024 tuvo más tardes así que 2023.
- **Por qué:** normaliza cada estación sin distinguir la hora, así que una tarde normal se ve
  más rara que una noche doblada. Además, una estación alterada es sólo una de 66 columnas, y
  cada árbol usa pocas columnas en cada camino.

**Predicciones:**
- **Tesista:** se cumplió. En el fondo es peor: el IsolationForest ni siquiera reacciona a los
  cambios grandes, y el Random Forest sí, un poco.
- **Claude:** la 1, la 2 y la 4 se cumplieron. La 3 se cumplió en el número (38.8 % frente a
  20.5 %) pero por una razón equivocada: casi todo ese 38.8 % se habría alertado igual sin la
  alteración.

**Corrección (2026-10-16) a la sección del Random Forest:** el 20.5 % de las horas con cambio
≥ 64 ppb incluye un 11.1 % que habría alertado igual sin la alteración, así que la alteración
aporta unos 9 puntos. El 88 % de la regla |z| tampoco tiene este control.

**Lectura para la tesis:** con la foto de 66 columnas de la hora t, ninguno de los dos
detectores simples detecta un error de ganancia, ni siquiera de δ = 100 %. Lo que funcionó en
la regla |z| fue comparar cada estación con lo normal **para ella a esa hora**. Eso es lo que
hace el V4, que predice el valor de cada estación. Por eso el V4 es la prueba que importa.

### Resultado: V4, δ = 100 % (2026-10-16)

**Duda del tesista: ¿hay que reentrenar el V4 ahora que «le pasamos la clasificación»?** No.
El V4 nunca recibe la etiqueta. Predice lo que debería medir cada estación a partir de sus
vecinas y de su perfil de 14 días, y alerta cuando la lectura se aleja de la predicción. La
etiqueta sólo la usamos nosotros, después, para calificar. Lo único nuevo es la regla de red:
el máximo entre estaciones y su umbral. Esa regla se aplica sobre las salidas del modelo, así
que no hay que entrenar nada. El único detector que aprende de las etiquetas es el Random
Forest.

**Modelos cargados de disco** (`experiments/anomalias_red/evaluar_v4.py --delta 100`, revisión
5 del protocolo):
- **Sin cambios:** los 31 modelos de `results/lstm_v4_multianual_v1/estaciones/`, con el
  SHA-256 verificado, y sus p95 de 2023, sin reentrenar ni recalibrar.
- **Inferencia repetida sobre la matriz alterada** de cada calendario.
- **Control:** el 2024 limpio por la misma vía reproduce las predicciones guardadas el
  2026-10-03 (diferencia máxima 1.4 × 10⁻¹⁴ ppb, por el paso por texto). ACO no tiene datos en
  2024 y no tiene predicciones.
- **Reproducibilidad:** dentro del script, dos inferencias del calendario 01 dieron puntajes
  idénticos. El script completo se corrió dos veces con salidas idénticas.
- **Umbrales de red:** 1.73 × p95 al nivel de 5 % y 2.33 × p95 al de 1 %. Con la mediana de los
  p95 (22.7 ppb), un residuo tiene que pasar de unos 39 o 53 ppb.

**Comparación de los tres detectores con δ = 100 %.** Random Forest e IsolationForest recién
entrenados; V4 cargado de disco. Entre paréntesis, el nivel de azar (revisiones 2 y 4).

| Nivel | Detector | Falsas alarmas 2024 limpio | Detección por hora | Episodios detectados | Horas con cambio 32–64 ppb | ≥ 64 ppb |
|---|---|---:|---:|---|---|---|
| 5 % | Random Forest | 3.0 % | 5.4 % | 47.4 % (42.7 %) | 6.3 % (5.1 %) | 20.5 % (11.1 %) |
| 5 % | IsolationForest | 6.4 % | 6.7 % | 70.3 % (70.3 %) | 10.4 % (10.9 %) | 38.8 % (36.2 %) |
| 5 % | **V4** | 9.1 % | **26.1 %** | 94.8 % (88.5 %) | **59.4 % (16.5 %)** | **96.5 % (32.7 %)** |
| 1 % | Random Forest | 0.2 % | 0.7 % | 11.5 % (12.5 %) | 0.5 % (0.6 %) | 6.5 % (1.7 %) |
| 1 % | IsolationForest | 1.6 % | 2.0 % | 39.6 % (38.5 %) | 2.8 % (3.4 %) | 13.9 % (12.5 %) |
| 1 % | **V4** | 2.3 % | **13.8 %** | **83.3 % (54.7 %)** | **25.8 % (4.5 %)** | **80.8 % (7.8 %)** |

**Más del V4:**
- **Signo, nivel 1 %:** con el + (doble) detecta el 100 % de los episodios (azar 57.9 %); con
  el − (mitad), el 67.0 % (azar 51.5 %).
- **Horas hasta la alerta, nivel 1 %:** mediana de 12 (azar 37). Los episodios empiezan a las
  00 h, así que la primera alerta suele llegar a mediodía, cuando el cambio en ppb ya es grande.
- **Ubicación:** en el 77 % (5 %) y el 85 % (1 %) de las horas anómalas detectadas, la estación
  del máximo es la alterada.
- **Contaminación después del episodio:** fuera de los episodios, el examen alerta el 10.2 %
  de las horas, frente al 9.1 % de 2024 limpio (nivel 5 %). Son el perfil de 14 días que
  absorbió la anomalía y las vecinas contaminadas.
- **Umbral original del V4** (alguna estación pasa su p95): alerta en el 35.6 % de las horas
  de 2023 y en el 44.2 % de las de 2024. Como alerta de red no sirve, y por eso se fijaron las
  falsas alarmas por hora de red.

**Advertencias:**
- **Falsas alarmas en 2024:** el umbral de 2023 da 9.1 % (5 %) y 2.3 % (1 %) en 2024. No es
  nuevo: en la parte 1, la mediana por estación en 2024 ya era 7.1 % con el p95 de 2023, y el
  máximo entre 30 estaciones lo amplifica. Por eso los tres detectores no quedan con las mismas
  falsas alarmas en 2024 (RF 3.0 %, IF 6.4 %, V4 9.1 % al nivel de 5 %). La conclusión no
  depende de eso: el V4 al nivel de 1 % tiene menos falsas alarmas (2.3 %) que el Random Forest
  al de 5 % (3.0 %) y aun así detecta mucho más (13.8 % frente a 5.4 % de las horas; 80.8 %
  frente a 20.5 % de las de cambio ≥ 64 ppb). Una curva ROC con las falsas alarmas de 2024
  haría la comparación exacta; queda propuesta.
- **La regla |z| del diagnóstico** detectaba el 28.2 % de las horas con 13.3 % de falsas
  alarmas en 2024. El V4 detecta casi lo mismo con menos falsas alarmas y es mejor en los
  cambios grandes (96.5 % frente a 88.0 %). A la regla no se le calculó el nivel de azar.

**Lectura:**
- **El V4 sí ve el error de ganancia, y los detectores simples no.** La diferencia está en
  comparar cada estación con lo que debería medir a esa hora.
- **El patrón es el del bit flipping de la parte 1:** lo que decide es el cambio en ppb. Casi
  nada por debajo de 16 ppb; casi todo por encima de 64.
- **La detección por hora (26 %) es baja porque el 41 % de las horas alteradas cambia menos de
  16 ppb:** el 88 % de esas horas cae entre las 19 y las 08 h, cuando el doble de 10 es 20. Es
  el caso del «80» y del «doble de 10» del tesista.

**Predicción para los demás δ, registrada antes de correrlos.** Al nivel de 5 %, el residuo
tiene que pasar de unos 39 ppb. Con el signo +, la alteración suma x·δ: con δ = 50 % llega a
39 ppb si el ozono pasa de 78 ppb, lo que pasa en muchas tardes; con δ = 20 % necesitaría
195 ppb, más que el máximo de 187 ppb de 2020–2026.
- **δ = 50 %:** detección por episodio claramente sobre el azar con el signo +, y bastante menor
  con el −.
- **δ = 20, 10 y 5 %:** cerca del azar. La alteración sólo puede empujar sobre el umbral
  residuos que ya eran grandes.
- **Consecuencia para la tesis:** la zona realista (5–10 %, dentro de la tolerancia de la EPA)
  sería invisible para el V4 con estas falsas alarmas. Habría que decirlo así.

**Corrección (2026-10-16): el LSTM supervisado quedó como opcional.** El tesista preguntó por
qué el LSTM no recibe la etiqueta, si el método acordado es supervisado. Según la aclaración
del 2026-10-12 y L4, el método principal es un clasificador supervisado a nivel de red, del
más simple al más complejo (Random Forest → LSTM, L-A10). El V4 sólo debía ser la línea base no
supervisada. Al redactar el protocolo, Claude dejó el «LSTM clasificador» como opcional (§2 y
§8), así que el único detector supervisado que se probó fue el Random Forest. Queda pendiente
de decisión del tesista registrar el LSTM supervisado como detector principal, antes de
entrenarlo.

**Comparación con la parte 1 (V4, 2024, grupo principal, p95 por estación, FPR por lectura
7.0 %):** detectó el 20.9 % de las lecturas con el bit 4 (16 ppb), el 78.7 % con el bit 5, el
99.5 % con el bit 6 y el 100 % con el bit 7 (`metricas_pareadas_agregadas.csv`). En la parte 2,
con el mismo umbral por estación, alerta en el 69.2 % de las horas con cambio de 16–32 ppb, en
el 96.3 % de las de 32–64 y en el 99.9 % de las de 64 o más. La sensibilidad en ppb es la misma.
Los tramos no son bits: un tramo agrupa horas por el mayor cambio, y un bit cambia todas las
lecturas por lo mismo. Lo que cambió entre las partes son los detectores simples, no el V4.

**Decisión del tesista (2026-10-16): se hará un LSTM supervisado de red.** Su argumento: el V4
sigue «infiriendo» la anomalía a partir de un valor predicho, y el método acordado es
supervisado. Lo que se busca es un modelo que aprenda a reconocer la alteración con las
etiquetas.

**Propuesta de diseño de Claude, pendiente de aprobación** (se registraría como revisión 6
antes de entrenar):
- **Entrada:** las 24 horas t−23…t de las 32 estaciones (valores normalizados, máscaras, seno
  y coseno de la hora): 24 × 66. A diferencia del V4, ve la estación alterada y la hora t.
- **Salida:** la probabilidad de que la red tenga una anomalía a la hora t. La etiqueta de red
  sólo se usa para entrenar y calificar; nunca es entrada.
- **Datos:** 10 calendarios nuevos sobre 2020–2022, cada uno con su p sorteada entre 0.10 y
  0.30 %. Dan unos 26 episodios por estación, en lugar de 2. Las claves de semilla
  [42, 2020, 1…10, …] no chocan con las de prueba.
- **División, como el V4:**
  - selección de épocas: se entrena con 2020–2021 y se valida con 2022 (EarlyStopping,
    paciencia 8, máximo 60 épocas);
  - después, un modelo nuevo con 2020–2022 y exactamente E épocas;
  - umbral con 2023 limpio y examen en 2024.
- **Arquitectura:**
  - la del V4 (LSTM de 64 unidades, Dropout 0.2, Dense 32), con salida sigmoide y entropía
    cruzada binaria;
  - Adam con tasa 1e-3 y lotes de 64;
  - `fijar_semilla(42)` antes de construir, y sin ajuste de hiperparámetros.
- **Modelos:** uno por δ, empezando por 100 %.
- **Comparación justa:** un Random Forest con los mismos 10 calendarios. Si el LSTM gana, no
  será sólo por tener más datos.
- **Costo:** se midieron unos 12,500 ejemplos por segundo con datos al azar, así que serían
  unos 20–30 minutos por δ.
- **Riesgo de huella:** los episodios siempre empiezan a las 00 h, y un supervisado podría
  aprender «salto a medianoche» en lugar de la anomalía. Propuesta: una prueba secundaria con
  episodios que empiecen a una hora al azar, para los tres detectores.

**Aprobada tal cual por el tesista (2026-10-16)** y registrada como revisión 6 del protocolo,
con tres predicciones de Claude, antes de entrenar. El tesista opinó que el seno y el coseno de
la hora resuelven el riesgo de la medianoche. Claude respondió que no: le dicen al modelo qué
hora es, y eso es justo lo que le permitiría aprender el atajo. La prueba con hora de inicio al
azar sigue en el plan, después de los resultados principales.

### Resultado: LSTM supervisado y Random Forest con 10 calendarios, δ = 100 % (2026-10-16)

**Datos:** 10 calendarios nuevos (`plan_entrenamiento_01` a `_10`) con 670 episodios, unos 22
por estación. Los 11 planes y las 58 matrices anteriores salieron idénticos byte por byte. Se
agregaron 50 matrices; `resumen_planes.csv` y `resumen_matrices.csv` ganaron filas sin cambiar
las anteriores.

**LSTM supervisado, recién entrenado** (`experiments/anomalias_red/entrenar_lstm_sup.py
--delta 100`):
- **Datos:** 175,210 ventanas de 2020–2021 y 87,600 de 2022; el 17 % tiene etiqueta 1.
- **Selección:** la pérdida de validación fue mínima en la **época 1** (0.635) y después subió
  hasta 1.17, así que EarlyStopping paró en la época 9. El modelo definitivo se entrenó 1 época
  con 2020–2022.
- **Reproducibilidad:** el script completo se corrió dos veces y dio métricas, episodios,
  historias y puntajes idénticos. Cada corrida tardó 3 minutos.
- **Salidas:** `results/anomalias_red_v1/lstm_sup/d100/`. Los modelos `.keras` (0.45 MB) van a
  git, como los del V4.

**Random Forest con los mismos 10 calendarios, recién entrenado** (`entrenar_rf.py --delta 100
--calendarios 10`): 263,040 horas. Dos entrenamientos dentro del script dieron puntajes
idénticos. Salidas en `rf_10cal/d100/`; el modelo (96 MB) no va a git.

**Los cinco detectores con δ = 100 %.** Entre paréntesis, el nivel de azar.

| Nivel | Detector | Origen | Falsas alarmas 2024 limpio | Detección por hora | Episodios | 32–64 ppb | ≥ 64 ppb |
|---|---|---|---:|---:|---|---|---|
| 5 % | Random Forest, 1 calendario | recién entrenado | 3.0 % | 5.4 % | 47.4 % (42.7 %) | 6.3 % (5.1 %) | 20.5 % (11.1 %) |
| 5 % | IsolationForest | recién entrenado | 6.4 % | 6.7 % | 70.3 % (70.3 %) | 10.4 % (10.9 %) | 38.8 % (36.2 %) |
| 5 % | Random Forest, 10 calendarios | recién entrenado | 4.9 % | 12.7 % | 81.2 % (67.7 %) | 17.7 % (8.0 %) | 54.0 % (13.2 %) |
| 5 % | LSTM supervisado | recién entrenado | 4.7 % | 16.4 % | 71.4 % (49.5 %) | 28.3 % (9.3 %) | 53.2 % (8.9 %) |
| 5 % | V4 | cargado de disco | 9.1 % | **26.1 %** | 94.8 % (88.5 %) | **59.4 % (16.5 %)** | **96.5 % (32.7 %)** |
| 1 % | Random Forest, 1 calendario | recién entrenado | 0.2 % | 0.7 % | 11.5 % (12.5 %) | 0.5 % (0.6 %) | 6.5 % (1.7 %) |
| 1 % | IsolationForest | recién entrenado | 1.6 % | 2.0 % | 39.6 % (38.5 %) | 2.8 % (3.4 %) | 13.9 % (12.5 %) |
| 1 % | Random Forest, 10 calendarios | recién entrenado | 1.9 % | 6.8 % | 58.3 % (46.4 %) | 8.3 % (3.5 %) | 40.1 % (8.4 %) |
| 1 % | LSTM supervisado | recién entrenado | 1.3 % | 5.8 % | 44.3 % (19.3 %) | 11.6 % (3.2 %) | 21.5 % (1.1 %) |
| 1 % | V4 | cargado de disco | 2.3 % | **13.8 %** | **83.3 % (54.7 %)** | **25.8 % (4.5 %)** | **80.8 % (7.8 %)** |

**Lectura:**
- **Más episodios ayudan mucho al Random Forest:** con 10 calendarios pasa del 5.4 % al 12.7 %
  de las horas, y del 20.5 % al 54.0 % de las de cambio grande.
- **Con los mismos datos, el LSTM supervisado no le gana con claridad al Random Forest.** Es
  mejor al nivel de 5 % (16.4 % frente a 12.7 % por hora) y peor al de 1 % en los cambios
  grandes (21.5 % frente a 40.1 %).
- **Los dos supervisados quedan por debajo del V4** en todas las medidas.
- **A favor del LSTM supervisado:** su umbral de 2023 se sostiene en 2024 (4.7 % y 1.3 %). El
  del V4 no (9.1 % y 2.3 %).

**Predicciones de Claude (revisión 6):**
1. Que el LSTM supervisado detectaría más horas que el V4: **no se cumplió** (16.4 % frente a
   26.1 %).
2. Que en las horas de 1–16 ppb alertaría claramente más que esas horas sin alterar y que el
   V4: **no claramente**. La dirección es correcta, pero el tamaño es mínimo: 3.3 % frente a
   1.3 % sin alterar y 1.0 % del V4.
3. δ ≤ 20 %: pendiente.

**Diagnóstico de la época 1** (`experiments/anomalias_red/diagnostico_lstm_validacion.py`,
salida en `lstm_sup/d100/diagnostico_validacion_2022.csv`; sólo 2020–2022, sin tocar 2023 ni
2024; modelo recién entrenado con la misma semilla, 10 épocas sin EarlyStopping):

| Época | Pérdida, entrenamiento | Pérdida, validación 2022 | AUC, entrenamiento | AUC, 2022 | Detección 2022 con 5 % de falsas alarmas |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.329 | 0.635 | 0.930 | 0.711 | 23.9 % |
| 3 | 0.155 | 0.778 | 0.973 | 0.742 | 26.2 % |
| 7 | 0.104 | 1.110 | 0.989 | 0.747 | 24.8 % |
| 10 | 0.087 | 1.304 | 0.991 | 0.736 | 21.5 % |

- **Un modelo constante tendría una pérdida de validación de 0.481,** mejor que la mejor época
  del LSTM (0.635).
- **El LSTM aprende de memoria los años de entrenamiento:** su AUC en el entrenamiento llega a
  0.99, y en 2022 se queda en 0.71–0.75.
- **Califica como sospechosas las horas normales de un año que no conoce:** el puntaje medio de
  las horas normales de 2022 es de 0.27 a 0.39, cuando sólo el 16.5 % de las horas de
  entrenamiento tiene etiqueta 1.
- **Hipótesis, no verificada:** ve 10 veces el mismo fondo normal de 2020–2021 y aprende sus
  niveles absolutos, en lugar de aprender qué es una anomalía.
- **El criterio de selección no es el adecuado para el uso.** La pérdida castiga sobre todo esa
  descalibración. El detector sólo usa el orden de los puntajes, porque el umbral se calibra en
  2023, y el orden (AUC) casi no cambia entre épocas. Elegir la época por AUC daría una mejora
  pequeña (de 0.711 a 0.747).

**Interpretación para la tesis:**
- El V4 trae de fábrica una estructura: predecir cada estación con sus vecinas y su propio
  perfil, y medir la diferencia en ppb.
- Un clasificador supervisado con valores crudos tiene que aprender esa estructura de los
  ejemplos, y con sólo dos años de fondo normal aprende los años en lugar de la anomalía.
- La supervisión por sí sola no basta. Esto todavía no demuestra que un supervisado no pueda
  igualar al V4: sólo describe este diseño.

**Variantes posibles,** para elegir con la validación 2022 y registrar antes de volver a 2024:
- **Entradas relativas al perfil:** el valor de cada estación menos su perfil de 14 días a esa
  hora, en lugar del valor crudo. Ataca la causa que sugiere el diagnóstico y no usa el V4.
- **Elegir la época por AUC en 2022** en lugar de por la pérdida.
- **Híbrido:** los residuos del V4 como entrada del clasificador. Riesgo: en 2020–2022 los
  residuos son de ajuste, más chicos que los de 2023–2024.

### Elección del segundo diseño supervisado con 2022 (2026-10-16)

El tesista preguntó si convendría hacer más calendarios. Respuesta: más calendarios dan más
anomalías falsas, pero sobre el mismo fondo normal de 2020–2022, así que no atacan la
memorización. Se comparan, sólo con 2022, ocho configuraciones con δ = 100 %:
- **modelo:** LSTM supervisado o Random Forest;
- **entradas:** valores crudos (los de siempre) o **relativos**: el valor de cada estación menos
  su perfil causal de 14 días a esa hora (la base del V4, con sus respaldos), dividido entre la
  desviación de 2020–2022;
- **calendarios de entrenamiento:** 10 o 20. Los calendarios 11–20 se generan en memoria con
  las mismas reglas y las claves [42, 2020, k, …].

**Fijado antes de correrlo:**
- **Entrenamiento:** horas de 2020–2021 de los calendarios.
- **Validación:** las horas de 2022 de los calendarios 01–10, la misma para las ocho.
- **Criterio principal:** detección de las horas con etiqueta 1 de 2022 con un umbral que deja 5 %
  de falsas alarmas en las horas con etiqueta 0 de esa misma validación. El AUC es secundario.
- **LSTM:** 10 épocas fijas, y se toma la mejor época según el criterio principal.
- **Elección:** se eligen las entradas y el número de calendarios, no el modelo. Decide la
  detección del LSTM supervisado, que es el detector principal; el Random Forest de control
  recibe la misma elección. Si la diferencia con la opción más sencilla (entradas crudas y 10
  calendarios) es menor que 2 puntos, se queda la más sencilla. Lo mismo entre 10 y 20
  calendarios: con menos de 2 puntos de diferencia, se quedan 10.
- **Después:** la ganadora se registra como revisión 7 antes de probarla una vez en 2024. 2023 y
  2024 no se tocan en esta comparación.

**Resultado** (`experiments/anomalias_red/diagnostico_variantes_2022.py`, salida en
`results/anomalias_red_v1/variantes_2022/`; modelos recién entrenados y no guardados):
- **Controles:** el calendario 01 regenerado en memoria es igual a su matriz guardada. La
  configuración «crudas, 10» reprodujo exactamente las 10 épocas del diagnóstico anterior (AUC y
  detección).
- **Tiempo:** 22 minutos.

Detección de las horas con etiqueta 1 de 2022, con 5 % de falsas alarmas en las horas con
etiqueta 0:

| Modelo | Entradas | Calendarios | Mejor época | Detección, mejor época | Detección, rango en 10 épocas | AUC en esa época |
|---|---|---:|---:|---:|---|---:|
| LSTM supervisado | crudas | 10 | 6 | 28.1 % | 21.5–28.1 % | 0.742 |
| LSTM supervisado | crudas | 20 | 10 | 23.0 % | 17.6–23.0 % | 0.738 |
| LSTM supervisado | relativas | 10 | 2 | 27.2 % | 22.1–27.2 % | 0.734 |
| LSTM supervisado | **relativas** | **20** | 1 | **30.2 %** | 25.0–30.2 % | 0.737 |
| Random Forest | crudas | 10 | — | 11.8 % | — | 0.629 |
| Random Forest | crudas | 20 | — | 12.5 % | — | 0.633 |
| Random Forest | relativas | 10 | — | 13.2 % | — | 0.616 |
| Random Forest | relativas | 20 | — | 15.7 % | — | 0.632 |

**Aplicación de la regla fijada antes de correrlo:**
- Gana «relativas, 20»: supera a la opción sencilla («crudas, 10») por 2.1 puntos, apenas por
  encima del margen de 2.
- Entre 10 y 20 calendarios con entradas relativas, la diferencia es de 3.0 puntos, así que se
  quedan 20.
- El Random Forest de control recibe la misma elección.

**Advertencias (Claude):**
- **La ventaja es chica.** La «mejor época» es un máximo entre 10 valores que oscilan de 5 a 7
  puntos, así que exagera un poco.
- **Época por época, la ventaja se sostiene:** «relativas, 20» supera a «crudas, 10» en las 10
  épocas, con un promedio de 27.5 % frente a 24.7 %.
- **El AUC no mejora:** 0.737 frente a 0.742. La ganancia está en la zona de pocas falsas
  alarmas, que es la que usa el detector.
- **La memorización no desaparece.** Con entradas relativas, la mejor época sigue siendo la 1, y
  la pérdida de validación (0.558) sigue peor que la de un modelo constante (0.481).
- Con «relativas, 20», la menor pérdida y la mayor detección caen en la misma época (la 1), así
  que se conserva el criterio de la revisión 6: elegir la época por la pérdida.

**Sobre la pregunta del tesista (¿más calendarios?):**
- **Con entradas crudas,** pasar a 20 calendarios **empeora** al LSTM en 9 de las 10 épocas
  (promedio de 24.7 % a 19.7 %), como se esperaba si memoriza el fondo.
- **Con entradas relativas,** 20 calendarios lo mejoran en las 10 épocas (promedio de 23.7 % a
  27.5 %).
- **En el Random Forest,** más calendarios y entradas relativas ayudan poco en ambos casos (de
  11.8 a 15.7 %).
- **Lectura:** más calendarios sólo sirven cuando las entradas le quitan al modelo los niveles
  propios de cada año.

### Resultado: segundo intento supervisado (revisión 7), δ = 100 % (2026-10-16)

**Antes de entrenar:**
- **Revisión 7:** registrada en el protocolo con tres predicciones de Claude.
- **Calendarios 11–20:** se generaron 10 planes y 50 matrices nuevos; los 11 planes y las 108
  matrices anteriores salieron idénticos. Los calendarios 11 y 20 guardados son iguales a los
  generados en memoria para la comparación de 2022.
- **Control del cambio de código:** con el código nuevo, los modelos guardados de la revisión 6
  (LSTM y los dos Random Forest) reproducen sus puntajes guardados, hasta la precisión con que
  se guardaron (6 cifras).
- **Monitor en vivo** (`experiments/anomalias_red/en_vivo.py`), a pedido del tesista:
  - una página local (http://127.0.0.1:8765/) dibuja las curvas mientras se entrena;
  - no se instaló TensorBoard, para no mover versiones de bibliotecas en el entorno;
  - la carpeta `results/anomalias_red_v1/en_vivo/` no va a git.

**LSTM supervisado, revisión 7, recién entrenado** (`entrenar_lstm_sup.py --delta 100
--entradas relativas --calendarios 20 --en-vivo`):
- **Datos:** 350,420 ventanas de 2020–2021 y 175,200 de 2022.
- **Selección:** E = 1 otra vez. La pérdida de validación fue mínima en la época 1 (0.565) y
  subió hasta 1.00 en la época 9. Un modelo constante tendría unos 0.50 en esta validación, así
  que la descalibración sigue.
- **Reproducibilidad:** dos corridas completas, con métricas, episodios, historias y puntajes
  idénticos. Cada una tardó unos 8 minutos.
- **Salidas:** `lstm_sup_relativas_20cal/d100/`.

**Random Forest de control, revisión 7, recién entrenado** (`entrenar_rf.py --delta 100
--calendarios 20 --entradas relativas`):
- **Falla de la primera corrida:** se detuvo con «dos entrenamientos dieron puntajes
  distintos». Diagnóstico:
  - los 100 árboles salen idénticos en los dos entrenamientos;
  - en cambio, la predicción en paralelo de un mismo modelo varía en 1 × 10⁻¹⁶, porque el orden
    en que se suman los votos depende de los hilos;
  - con estas entradas hay hojas con votos fraccionarios (0.08 %), y ahí la suma no es exacta.
- **Corrección:** se entrena en paralelo y se predice en serie. En los dos Random Forest
  anteriores, la predicción en paralelo y en serie da exactamente lo mismo, así que sus
  resultados no cambian.
- **Corrida definitiva:** dos entrenamientos con puntajes idénticos. Salidas en
  `rf_relativas_20cal/d100/`.

**Los siete detectores con δ = 100 %.** Entre paréntesis, el nivel de azar. Todos están recién
entrenados, salvo el V4, cargado de disco.

| Nivel | Detector | Falsas alarmas 2024 limpio | Detección por hora | Episodios | 1–16 ppb | 32–64 ppb | ≥ 64 ppb |
|---|---|---:|---:|---|---|---|---|
| 5 % | Random Forest, 1 calendario | 3.0 % | 5.4 % | 47.4 % (42.7 %) | 2.5 % (2.4 %) | 6.3 % (5.1 %) | 20.5 % (11.1 %) |
| 5 % | IsolationForest | 6.4 % | 6.7 % | 70.3 % (70.3 %) | 0.8 % (0.8 %) | 10.4 % (10.9 %) | 38.8 % (36.2 %) |
| 5 % | Random Forest, 10 cal., crudas (rev. 6) | 4.9 % | 12.7 % | 81.2 % (67.7 %) | 3.7 % (3.4 %) | 17.7 % (8.0 %) | 54.0 % (13.2 %) |
| 5 % | LSTM supervisado, rev. 6 | 4.7 % | 16.4 % | 71.4 % (49.5 %) | 3.3 % (1.3 %) | 28.3 % (9.3 %) | 53.2 % (8.9 %) |
| 5 % | Random Forest, 20 cal., relativas (rev. 7) | 4.7 % | 16.4 % | 89.6 % (74.5 %) | 2.5 % (2.4 %) | 28.3 % (7.9 %) | 73.4 % (11.6 %) |
| 5 % | **LSTM supervisado, rev. 7** | 4.6 % | **25.5 %** | 72.9 % (31.2 %) | **8.7 % (2.2 %)** | 40.0 % (6.3 %) | 77.9 % (6.4 %) |
| 5 % | V4 | 9.1 % | **26.1 %** | 94.8 % (88.5 %) | 1.0 % (1.0 %) | **59.4 % (16.5 %)** | **96.5 % (32.7 %)** |
| 1 % | Random Forest, 1 calendario | 0.2 % | 0.7 % | 11.5 % (12.5 %) | 0.0 % (0.1 %) | 0.5 % (0.6 %) | 6.5 % (1.7 %) |
| 1 % | IsolationForest | 1.6 % | 2.0 % | 39.6 % (38.5 %) | 0.0 % (0.0 %) | 2.8 % (3.4 %) | 13.9 % (12.5 %) |
| 1 % | Random Forest, 10 cal., crudas (rev. 6) | 1.9 % | 6.8 % | 58.3 % (46.4 %) | 1.0 % (1.0 %) | 8.3 % (3.5 %) | 40.1 % (8.4 %) |
| 1 % | LSTM supervisado, rev. 6 | 1.3 % | 5.8 % | 44.3 % (19.3 %) | 0.5 % (0.2 %) | 11.6 % (3.2 %) | 21.5 % (1.1 %) |
| 1 % | Random Forest, 20 cal., relativas (rev. 7) | 1.6 % | 9.2 % | 73.4 % (54.2 %) | 0.4 % (0.5 %) | 13.9 % (2.8 %) | 57.2 % (5.3 %) |
| 1 % | LSTM supervisado, rev. 7 | 1.1 % | 9.5 % | 53.1 % (12.0 %) | 0.7 % (0.1 %) | 14.3 % (1.9 %) | 50.1 % (2.2 %) |
| 1 % | V4 | 2.3 % | **13.8 %** | **83.3 % (54.7 %)** | 0.1 % (0.1 %) | **25.8 % (4.5 %)** | **80.8 % (7.8 %)** |

**Predicciones de Claude (revisión 7):** se cumplieron las tres.
1. **LSTM supervisado entre la revisión 6 y el V4:** detectó el 25.5 % de las horas, frente al
   16.4 % y al 26.1 %.
2. **Por debajo del V4 en los cambios ≥ 64 ppb:** 77.9 % frente a 96.5 %.
3. **Random Forest de control por encima del de 10 calendarios con entradas crudas:** 16.4 %
   frente a 12.7 %.

**Lectura:**
- **Al nivel de 5 %, el LSTM supervisado de la revisión 7 iguala al V4** en detección por hora
  (25.5 % frente a 26.1 %), con la mitad de falsas alarmas en 2024 (4.6 % frente a 9.1 %).
- **Ve mejor los cambios chicos:** 8.7 % de las horas de 1–16 ppb (azar 2.2 %), frente a 1.0 %
  del V4 (azar 1.0 %); y 21.3 % de las de 16–32 ppb, frente a 12.5 %. Es lo que se esperaba de
  la ventana de 24 horas, que deja recordar la tarde anterior. En la revisión 6 no se había
  visto.
- **Al nivel de 1 % y en los cambios grandes, el V4 sigue mejor:** 80.8 % de las horas ≥ 64 ppb,
  frente a 50.1 %.
- **Las entradas relativas también ayudan al Random Forest:** de 12.7 % a 16.4 % por hora y de
  54.0 % a 73.4 % en los cambios grandes. Aun así, con las mismas entradas y calendarios, el
  LSTM supera al Random Forest al nivel de 5 % (25.5 % frente a 16.4 %) y empata al de 1 %.
- **Falsas alarmas después de los episodios:** fuera de los episodios, el examen alerta el 6.3 %
  de las horas, frente a 4.6 % en 2024 limpio. El perfil de 14 días se contamina con la
  anomalía, como en el V4 (10.2 % frente a 9.1 %).

**Advertencias (Claude):**
- **Dos intentos supervisados.** La revisión 7 se diseñó porque la 6 salió mal en 2024. El
  diseño se eligió sólo con 2022, pero hubo un segundo intento y la tesis debe reportar los dos.
- **Falsas alarmas distintas en 2024** entre el V4 (9.1 %) y los demás (4.6–4.9 %). Para la
  comparación exacta del V4 con el LSTM supervisado hace falta la curva ROC con las falsas
  alarmas de 2024, que sigue propuesta.
- **La memorización sigue,** aunque menos: E = 1 y validación peor calibrada que un modelo
  constante.

### δ = 50 % con los cuatro detectores definitivos (2026-10-16)

Los detectores definitivos son el V4, el LSTM supervisado de la revisión 7, su Random Forest de
control y el IsolationForest. Cada uno se corre dos veces para verificar la reproducibilidad. El
Random Forest lo hace dentro del script.

**Predicción de Claude, antes de correrlo** (nivel 5 %). Con δ = 50 %, el cambio es 0.5·x con el
signo + y x/3 con el signo −. Pasa de 64 ppb sólo si el ozono pasa de 128 ppb (+) o de 192 ppb
(−), así que casi no habrá horas en el tramo ≥ 64.
1. **V4:** detección por hora entre 8 y 15 %. Por episodio, claramente sobre el azar con el
   signo +, y cerca del azar con el − (lo registrado el 2026-10-16).
2. **LSTM supervisado:** detección por hora a menos de 5 puntos de la del V4, y todavía mejor que
   el V4 en el tramo de 1–16 ppb.
3. **Random Forest de control:** por debajo del LSTM supervisado.
4. **IsolationForest:** al nivel del azar, como con δ = 100 %.

**Resultado.** IsolationForest, LSTM supervisado y Random Forest recién entrenados; V4 cargado de
disco.
- **Reproducibilidad:** IsolationForest, V4 y LSTM supervisado se corrieron dos veces cada uno,
  con métricas, episodios, desglose y puntajes idénticos. El Random Forest verificó dentro del
  script dos entrenamientos idénticos.
- **Salidas:** `if/d50/`, `v4/d50/`, `lstm_sup_relativas_20cal/d50/` y `rf_relativas_20cal/d50/`.
- **Las horas alteradas son las mismas 14,044 que con δ = 100 %, pero el cambio es más chico:**

| Tramo del cambio | δ = 100 % | δ = 50 % |
|---|---:|---:|
| 1–16 ppb | 5,814 | 8,542 |
| 16–32 ppb | 3,762 | 3,939 |
| 32–64 ppb | 3,168 | 1,507 |
| ≥ 64 ppb | 1,300 | **56** |

**Detección por hora.** La «diferencia» es la detección menos lo que el mismo detector alerta en
las horas normales del examen: la señal que aporta la alteración.

| Detector | Nivel | δ = 100 %: detección (diferencia) | δ = 50 %: detección (diferencia) | Falsas alarmas 2024 limpio, δ = 50 % |
|---|---|---|---|---:|
| V4 | 5 % | 26.1 % (15.9) | 14.2 % (4.8) | 9.1 % |
| LSTM supervisado, rev. 7 | 5 % | 25.5 % (19.2) | 11.8 % (4.4) | 6.6 % |
| Random Forest, rev. 7 | 5 % | 16.4 % (11.5) | 8.0 % (3.0) | 5.1 % |
| IsolationForest | 5 % | 6.7 % (0.3) | 6.7 % (0.3) | 6.4 % |
| V4 | 1 % | 13.8 % (10.7) | 4.4 % (1.9) | 2.3 % |
| LSTM supervisado, rev. 7 | 1 % | 9.5 % (8.1) | 3.3 % (1.8) | 1.2 % |
| Random Forest, rev. 7 | 1 % | 9.2 % (7.6) | 1.9 % (0.7) | 1.3 % |
| IsolationForest | 1 % | 2.0 % (0.5) | 2.0 % (0.5) | 1.6 % |

**Por episodio con δ = 50 %** (entre paréntesis, el azar):

| Detector | Nivel 5 % | Nivel 1 % | Signo +, nivel 1 % | Signo −, nivel 1 % |
|---|---|---|---|---|
| V4 | 90.6 % (88.5 %) | 68.8 % (54.7 %) | 81.1 % (57.9 %) | 56.7 % (51.5 %) |
| LSTM supervisado, rev. 7 | 52.6 % (31.8 %) | 30.7 % (12.5 %) | 37.9 % (12.6 %) | 23.7 % (12.4 %) |
| Random Forest, rev. 7 | 82.8 % (79.2 %) | 51.6 % (49.5 %) | 56.8 % (47.4 %) | 46.4 % (51.5 %) |
| IsolationForest | 69.8 % (70.3 %) | 39.6 % (38.5 %) | 40.0 % (37.9 %) | 39.2 % (39.2 %) |

**Por tamaño del cambio, nivel 5 %** (entre paréntesis, las mismas horas sin alterar):

| Detector | 1–16 ppb | 16–32 | 32–64 | ≥ 64 (56 horas) |
|---|---|---|---|---|
| V4 | 1.8 % (1.8 %) | 22.0 % (14.5 %) | 61.0 % (32.4 %) | 100 % (64.3 %) |
| LSTM supervisado, rev. 7 | 11.4 % (5.9 %) | 12.4 % (5.1 %) | 12.3 % (3.3 %) | 12.5 % (0 %) |
| Random Forest, rev. 7 | 2.7 % (2.5 %) | 11.6 % (8.4 %) | 26.5 % (14.1 %) | 75.0 % (58.9 %) |

**Predicciones de Claude:**
1. **V4 entre 8 y 15 % por hora:** se cumplió (14.2 %). Por episodio, con el signo − queda en el
   azar, como se predijo. Con el + queda claramente sobre el azar sólo al nivel de 1 % (81.1 %
   frente a 57.9 %); al de 5 % apenas (95.8 % frente a 91.6 %), porque el azar ya es muy alto.
2. **LSTM supervisado a menos de 5 puntos del V4 y mejor en 1–16 ppb:** se cumplió (11.8 % frente
   a 14.2 %; 11.4 % frente a 1.8 %).
3. **Random Forest por debajo del LSTM:** se cumplió (8.0 % frente a 11.8 %).
4. **IsolationForest al nivel del azar:** se cumplió.

**Lectura:**
- **Con la mitad del δ, la señal cae a un tercio o menos.** La diferencia por hora del V4 pasa de
  15.9 a 4.8 puntos, y la del LSTM supervisado, de 19.2 a 4.4. Al nivel de 1 %, todos quedan a
  menos de 2 puntos de lo que alertan en horas normales.
- **Por episodio todavía hay algo:** al nivel de 1 %, el V4 y el LSTM supervisado detectan 14 y 18
  puntos más que el azar. Los episodios duran días, y a veces pasan por una tarde de ozono alto.
- **El LSTM supervisado no reacciona al tamaño del cambio.** Alerta en un 12 % de las horas en
  todos los tramos, y de las 56 horas con cambio ≥ 64 ppb detecta 7. El V4 detecta las 56. En el
  entrenamiento con δ = 50 % casi no hay cambios grandes, y un detector supervisado aprende las
  anomalías que se le muestran (§13). Es una muestra chica, pero apunta a una ventaja del V4:
  marca cualquier desviación grande, aunque no se parezca a lo que vio.
- **El umbral del LSTM supervisado se sostiene peor:** 6.6 % de falsas alarmas en 2024 (con
  δ = 100 %, 4.6 %). Su detección por episodio varía mucho entre calendarios: entre 12 y 70 % al
  nivel de 5 %.
- **La memorización empeora con δ = 50 %:** la pérdida de validación pasa de 0.60 en la época 1
  a 1.61 en la 9.
- **Consecuencia:** con δ = 50 % ya estamos cerca del límite. Para δ = 20, 10 y 5 % se mantiene
  la predicción registrada: cerca del azar.
- **Nota (2026-10-18):** la «diferencia» de esta sección está sesgada cuando δ es chico. En la
  sección siguiente se recalcula contra las mismas horas sin alterar; con δ = 50 % queda V4 +5.3,
  LSTM supervisado +6.4, Random Forest +2.4 e IsolationForest +0.1 al nivel de 5 %.

### δ = 20, 10 y 5 % con los cuatro detectores definitivos (2026-10-18)

A pedido del tesista se corren los tres δ seguidos, con el mismo procedimiento que δ = 50 %: cada
detector dos veces y el Random Forest verificado dentro de su script.

**Tamaño posible del cambio.** El ozono máximo de 2020–2026 es 187 ppb.
- **δ = 20 %:** el + suma 0.2·x y el − resta x/6, así que el cambio no pasa de 37 ppb. Llega a
  32 ppb sólo con el + y ozono sobre 160 ppb.
- **δ = 10 %:** el + suma 0.1·x y el − resta x/11; el cambio no pasa de 19 ppb.
- **δ = 5 %:** el + suma 0.05·x y el − resta x/21; el cambio no pasa de 9 ppb. Con ozono bajo
  20 ppb, el cambio queda bajo 1 ppb y la hora cae en «sin cambio», aunque lleve etiqueta 1.

**Predicción de Claude, antes de correrlo** (nivel 5 %; «diferencia» como en δ = 50 %):
1. **V4:** diferencia por hora menor de 2 puntos con δ = 20 % y menor de 1 con 10 y 5 %. Por
   episodio, a menos de 5 puntos del azar en los tres δ. Al nivel de 1 %, con δ = 20 % y el signo +,
   todavía algo sobre el azar, pero menos de 10 puntos.
2. **LSTM supervisado:** el mejor de los cuatro en diferencia por hora con δ = 20 %, porque aprende
   la forma del cambio en vez de esperar un residuo grande, pero con menos de 3 puntos. Con 10 y
   5 %, menos de 1.5 puntos. La época elegida será E = 1 en los tres δ.
3. **Random Forest de control:** por debajo del LSTM supervisado, con menos de 1.5 puntos en los
   tres δ.
4. **IsolationForest:** al nivel del azar en los tres δ.
5. **Consecuencia:** si se cumple, la zona realista (5–10 %) es invisible para los cuatro
   detectores con estas falsas alarmas.

**Resultado.** IsolationForest, LSTM supervisado y Random Forest recién entrenados; V4 cargado de
disco.
- **Reproducibilidad:** IsolationForest, V4 y LSTM supervisado se corrieron dos veces en cada δ,
  con métricas, episodios, desglose, puntajes e historia del LSTM idénticos. El Random Forest
  verificó dentro del script dos entrenamientos idénticos.
- **Salidas:** `d20/`, `d10/` y `d5/` en `if/`, `v4/`, `lstm_sup_relativas_20cal/` y
  `rf_relativas_20cal/`.
- **Con δ chico hay menos horas con etiqueta 1:** 14,044 con δ = 100 y 50 %; 12,910 con 20 %;
  12,215 con 10 % y 10,931 con 5 %. La RAMA reporta ppb enteros (§5): si el cambio no llega a
  medio ppb, la lectura no cambia y la hora no lleva etiqueta. Con δ = 5 %, eso pasa con ozono
  bajo unos 10 ppb.

| Tramo del cambio | δ = 20 % | δ = 10 % | δ = 5 % |
|---|---:|---:|---:|
| 1–16 ppb | 11,880 | 12,210 | 10,931 |
| 16–32 ppb | 1,025 | 5 | 0 |
| 32–64 ppb | 5 | 0 | 0 |

**Nota (2026-10-18): la «diferencia» usada con δ = 100 y 50 % está sesgada cuando δ es chico.**
Comparaba la detección en las horas alteradas con lo que el detector alerta fuera de episodio.
Con δ chico, las horas que llevan etiqueta son las de más ozono (por el redondeo), y esas horas
alertan más aunque nadie las altere. La prueba es el IsolationForest: es el mismo modelo para
todos los δ, y sus horas alteradas alertan exactamente igual que esas mismas horas sin alterar
(8.2 % y 8.2 % con δ = 5 %). Aun así, su «diferencia» sube de 0.3 a 2.1 puntos. Desde aquí, el
resumen por hora compara contra **las mismas horas sin alterar**: es el azar por tramo de la
revisión 4, sumado sobre todas las horas alteradas. Se decidió **después** de ver estos
resultados. No cambia el protocolo, que no define la «diferencia», y con δ = 100 y 50 % el orden
de los detectores queda igual. El azar por episodio ya era pareado (revisión 2) y no cambia.

**Detección por hora frente a las mismas horas sin alterar.** Formato: detección / azar
(señal en puntos).

| Detector | Nivel | δ = 100 % | δ = 50 % | δ = 20 % | δ = 10 % | δ = 5 % |
|---|---|---|---|---|---|---|
| V4 | 5 % | 26.1 / 8.9 (+17.3) | 14.2 / 8.9 (+5.3) | 10.3 / 9.6 (+0.7) | 10.3 / 10.1 (+0.1) | 11.4 / 11.3 (+0.1) |
| LSTM supervisado, rev. 7 | 5 % | 25.5 / 4.5 (+21.0) | 11.8 / 5.4 (+6.4) | 0.5 / 0.5 (0.0) | 0.4 / 0.4 (0.0) | 1.2 / 1.1 (+0.1) |
| Random Forest, rev. 7 | 5 % | 16.4 / 5.1 (+11.4) | 8.0 / 5.6 (+2.4) | 7.3 / 7.1 (+0.2) | 6.4 / 6.5 (−0.1) | 7.4 / 7.3 (+0.1) |
| IsolationForest | 5 % | 6.7 / 6.6 (+0.1) | 6.7 / 6.6 (+0.1) | 7.2 / 7.2 (0.0) | 7.5 / 7.5 (0.0) | 8.2 / 8.2 (0.0) |
| V4 | 1 % | 13.8 / 2.1 (+11.7) | 4.4 / 2.1 (+2.4) | 2.5 / 2.2 (+0.2) | 2.4 / 2.4 (0.0) | 2.6 / 2.6 (0.0) |
| LSTM supervisado, rev. 7 | 1 % | 9.5 / 0.9 (+8.5) | 3.3 / 1.0 (+2.2) | 0.1 / 0.1 (0.0) | 0.0 / 0.0 (0.0) | 0.1 / 0.1 (0.0) |
| Random Forest, rev. 7 | 1 % | 9.2 / 1.7 (+7.5) | 1.9 / 1.3 (+0.5) | 1.7 / 1.6 (+0.1) | 1.4 / 1.4 (0.0) | 1.7 / 1.7 (0.0) |
| IsolationForest | 1 % | 2.0 / 2.0 (0.0) | 2.0 / 2.0 (0.0) | 2.2 / 2.2 (0.0) | 2.3 / 2.3 (0.0) | 2.6 / 2.6 (0.0) |

Falsas alarmas en 2024 limpio, nivel 5 %: V4 9.1 % en los cinco δ; Random Forest 5.7, 4.9 y 5.5 %
con δ = 20, 10 y 5 %; IsolationForest 6.4 %; LSTM supervisado **0.5, 0.6 y 0.9 %**.

**Por episodio** (entre paréntesis, el azar):

| Detector | δ | Nivel 5 % | Nivel 1 % | Signo +, nivel 1 % |
|---|---|---|---|---|
| V4 | 20 % | 88.5 % (88.5 %) | 58.3 % (54.7 %) | 65.3 % (57.9 %) |
| V4 | 10 % | 87.5 % (88.5 %) | 56.2 % (54.7 %) | 60.0 % (57.9 %) |
| V4 | 5 % | 88.5 % (88.5 %) | 56.2 % (54.7 %) | 60.0 % (57.9 %) |
| LSTM supervisado, rev. 7 | 20 % | 8.9 % (9.4 %) | 2.6 % (4.2 %) | 1.1 % (2.1 %) |
| LSTM supervisado, rev. 7 | 10 % | 7.3 % (9.4 %) | 0.5 % (0.5 %) | 0.0 % (0.0 %) |
| LSTM supervisado, rev. 7 | 5 % | 18.2 % (17.2 %) | 2.1 % (2.1 %) | 3.2 % (3.2 %) |
| Random Forest, rev. 7 | 20 % | 84.9 % (85.4 %) | 49.5 % (54.2 %) | 52.6 % (53.7 %) |
| Random Forest, rev. 7 | 10 % | 82.8 % (81.8 %) | 46.4 % (42.2 %) | 44.2 % (37.9 %) |
| Random Forest, rev. 7 | 5 % | 87.5 % (87.0 %) | 49.0 % (46.9 %) | 50.5 % (49.5 %) |
| IsolationForest | 20 % | 70.3 % (70.3 %) | 39.1 % (38.5 %) | 38.9 % (37.9 %) |
| IsolationForest | 10 % | 69.8 % (70.3 %) | 38.5 % (38.5 %) | 37.9 % (37.9 %) |
| IsolationForest | 5 % | 69.8 % (70.3 %) | 38.5 % (38.5 %) | 37.9 % (37.9 %) |

Cada fila son 192 episodios. El único tramo con algo de señal es 16–32 ppb con δ = 20 %, en el
V4 (41.8 % frente a 37.7 %) y en el Random Forest (22.1 % frente a 19.6 %). Son 1,025 horas.

**El LSTM supervisado con δ ≤ 20 %:**
- La época elegida es E = 1 en los tres δ, y la pérdida de validación 2022 casi no se mueve
  (con δ = 5 %, de 0.419 a 0.425 en 9 épocas).
- Su puntaje casi no varía: con δ = 20 %, el umbral de 5 % es 0.224 y el de 1 % es 0.244. Por
  eso un corrimiento mínimo entre 2023 y 2024 cambia mucho cuántas horas alertan: el umbral deja
  5 % de falsas alarmas en 2023 y sólo 0.5 % en 2024. Casi no alerta.
- **Comparación con un modelo constante,** que da a todas las horas la proporción de etiquetas 1
  de 2020–2021. Con δ = 20 %, la pérdida de validación es igual (0.476 frente a 0.474). Con 10 y
  5 % es un poco menor (0.455 frente a 0.461 y 0.419 frente a 0.431), y aun así no detecta nada
  frente a las mismas horas sin alterar.
- **Explicación probable, no comprobada:** por el redondeo, la etiqueta depende del nivel de
  ozono. Con poco ozono casi nunca hay etiqueta 1, y aprender eso baja la pérdida sin detectar la
  alteración.

**Predicciones de Claude:**
1. **V4:**
   - Diferencia menor de 2 puntos con δ = 20 %: se cumplió (1.3).
   - Menor de 1 con 10 y 5 %: no se cumplió con la medida registrada (1.4 y 2.6), por el sesgo de
     la nota. Contra las mismas horas sin alterar es +0.1.
   - Por episodio a menos de 5 puntos del azar: se cumplió.
   - Al nivel de 1 % con δ = 20 % y signo +, algo sobre el azar y menos de 10 puntos: se cumplió
     (65.3 % frente a 57.9 %).
2. **LSTM supervisado:**
   - El mejor de los cuatro con δ = 20 %: **no se cumplió**. Está en el azar y casi no alerta.
   - E = 1: se cumplió.
   - Menos de 1.5 puntos con 10 y 5 %: se cumplió.
3. **Random Forest:**
   - Por debajo del LSTM: no se cumplió, porque los dos están en el azar.
   - Menos de 1.5 puntos: no se cumplió con la medida registrada (1.8, 1.8 y 2.1), pero sí contra
     las mismas horas sin alterar (+0.2, −0.1 y +0.1).
4. **IsolationForest en el azar:** se cumplió. Fue su «diferencia» la que reveló el sesgo.
5. **La zona de 5–10 % es invisible para los cuatro:** se cumplió.

**Lectura:**
- **El límite está entre δ = 50 % y δ = 20 %.** Contra las mismas horas sin alterar, al nivel de
  5 %, la señal del V4 va 17.3 → 5.3 → 0.7 → 0.1 → 0.1 puntos, y la del LSTM supervisado
  21.0 → 6.4 → 0 → 0 → 0.1.
- **En ppb es el patrón de la parte 1.** Con δ = 20 %, sólo 1,030 horas cambian más de 16 ppb, y
  ahí está la única señal. Por debajo de 16 ppb no detecta nadie.
- **La etiqueta no rescató los δ chicos.** El LSTM supervisado no encontró una forma del cambio de
  20 % que el V4 no viera, contra la predicción.
- **Para la tesis:** una descalibración realista (5–10 %, dentro de la tolerancia de la EPA)
  queda en el azar para los cuatro detectores con estas falsas alarmas, igual que los bits bajos
  en la parte 1.

### Gráfica: detección por hora según δ (2026-10-19)

Es la primera gráfica del §11, la análoga a la detección por bit de la parte 1.
- **Archivos:** `docs/img/anomalias_red_v1/deteccion_por_delta.png`, hecha con
  `experiments/anomalias_red/graficar_curva_delta.py`. La misma información, con la detección por
  episodio, está en `results/anomalias_red_v1/curva_delta.csv`. El script sólo lee resultados; se
  corrió dos veces y dio archivos idénticos.
- **Qué muestra:** la señal contra las mismas horas sin alterar (nota del 2026-10-18), al nivel de
  5 % y de 1 %, con el rango entre las 10 corridas del examen.
- **Eje x:** δ y la mediana del mayor cambio de la hora en las horas alteradas: 2, 3, 6, 12 y
  20 ppb con δ = 5, 10, 20, 50 y 100 %. Es el equivalente de los ±ppb de cada bit en la parte 1.
- **Siguen pendientes del §11:** horas hasta la alerta según δ, daño no detectado según δ y signo
  (requiere el §10), F1 según la tasa y detección según el número de estaciones (fase 2).
- **Nota (2026-10-19):** en la junta esta gráfica no se pudo explicar. Para presentar se sustituye
  por `recall_por_delta.png`, que tiene su ficha en `docs/fichas_graficas.md`. Esta se conserva
  como historial.

### Material para la junta del 2026-10-19

- **Presentación de 13 láminas** con notas para el tesista. Está fuera del repositorio, como
  artefacto privado. Sus números salen de esta sección y de `curva_delta.csv`.
- **Decisiones que se llevan al asesor:** fase 2, ×3/×4 y δ aleatorio, experimentos secundarios,
  meta del 80–90 %, antecedentes (P1) y vínculo con LoRaWAN (P6).
- **Hallazgo al prepararla:** el ×3, el ×4 y el δ aleatorio entre 10 y 50 % se acordaron el
  2026-10-12 (L-A7), pero no están en el protocolo.

---

## 2026-10-19 — Junta con el asesor: sintetizar por día y comparar como imágenes

Fuentes: una transcripción automática de mala calidad (en los primeros 14 minutos las voces se
mezclan) y las notas del tesista. La presentación preparada no se usó.

### Regla nueva del tesista

- Por semana se llevan sólo **1 o 2 gráficas**, y cada una debe entenderse completa: qué es el
  eje X, qué es el eje Y, de dónde sale cada métrica y qué tipo de medida es (recall, F1, etc.).
  También queda en `CLAUDE.md`.
- **Motivo:** en la junta no se pudo explicar la «señal» de la curva por δ, y se dijo que era el
  F1.

### Lo que pidió o propuso el asesor

Son ideas para discutir; ninguna cambia todavía el protocolo.

| # | Idea |
|---|---|
| M-1 | Que el tesista pueda interpretar cada gráfica y validar lo que produce la IA. |
| M-2 | Entrenar con todos los años disponibles, salvo el último. |
| M-3 | Que las vecinas pesen más que la hora: «si dos vecinas marcan 100 y tú 150, hay algo raro». |
| M-4 | Definir con precisión cómo se inyecta la anomalía: por periodos, como un sensor que se descompone. |
| M-5 | Etiquetar por día, no por hora. |
| M-6 | Representar el día de cada estación como una imagen y compararla con otros días y con las estaciones cercanas. Citó VINO. «No es un problema de redes, es de clasificación». |
| M-7 | Probar con promedios. Las horas de la noche importan poco. |
| M-8 | Espera la misma curva, pero más arriba: con 20 %, detectar un 20–30 %. Caracterizar hasta dónde sí y hasta dónde no, buscando circunstancias en las que sí se detecte. |

### Ideas del tesista (de sus notas)

- Sintetizar las 24 horas de cada estación en 1, 2 (día y noche) o 4 (cuartos de 6 h) promedios.
- Usar VINO para crear una imagen por día y compararla con la ventana del LSTM.
- Quitar el entrenamiento temporal, para ver si mejora.
- Usar una ventana de varios días (3 o 7) en vez de 24 horas.
- **Meta común:** bajar el ruido para detectar cambios sutiles (M-8).

### Aclaraciones a lo dicho en la junta (verificadas contra el repositorio)

- **La «señal» no es el F1.** Es la detección por hora menos la de esas mismas horas sin alterar,
  con falsas alarmas fijas. En la parte 2 no se calculó la precisión.
- **Los niveles de 5 % y 1 %** son el p95 y el p99 del puntaje en 2023 limpio: el umbral que deja
  5 % (o 1 %) de las horas normales con alerta. No son una certeza. La tolerancia de la EPA
  (±7.1 %) justifica que δ = 5–10 % sea realista; no justifica estos niveles.
- **Con 50 % todavía hay señal** (V4 +5.3, LSTM supervisado +6.4); llega a cero a partir de 20 %.
- **No hay un residuo de 18 ppb en los resultados.** El umbral p95 por estación del V4 es de
  22.65 ppb (mediana), 21.36 ppb con vecinas cercanas. Al 5 % por hora de red, el residuo tiene
  que pasar de unos 39 ppb.
- **Años de entrenamiento:** la selección entrena con 2020–2021 y valida con 2022; el modelo
  definitivo usa 2020–2022 durante una época. 2024 nunca se usa para entrenar.
- **El ozono de la pandemia no fue «nulo».** Media anual de las 31 estaciones: 31.6 ppb en 2020,
  29.0 en 2021 y 32.8 en 2024. 2024 fue el año alto: 16 días con máximo de red de 155 ppb o más,
  frente a 1 en 2020 y 3 en 2021.
- **Vecinas cercanas:** se probaron k = 4, 8, 16 y 32, no 3, 6, 12 y 32. Las tres vecinas de CCA
  (CU) están a 2.9, 5.2 y 6.9 km. El parecido entre estaciones (correlación de las desviaciones)
  es de 0.75 a menos de 10 km y de 0.48 a más de 30 km.
- **Datos faltantes:** falta el 31.6 % de las lecturas de 00 a 02 h, frente a ~20 % el resto del
  día (2020–2024). El −99 de la RAMA se convierte en «sin dato»; el modelo nunca lo ve.

### VINO

Lo que sigue se verificó con el resumen del artículo, no con el texto completo.
- **Qué es:** VINO (Chen et al., arXiv 2601.02358, enero de 2026) es un generador de imágenes y
  video. Es un modelo de difusión que crea o edita imágenes a partir de texto, imágenes o video.
- **Qué no hace:** no recibe series numéricas ni compara imágenes.
- **Pendiente:** confirmar con el asesor si propone usar VINO mismo o la idea general de convertir
  cada día en una imagen.

### Exploración de Claude: ¿resumir el día baja el ruido?

**Fuera de protocolo:** sólo sirve para juzgar las ideas de la junta.
- **Archivos:** `experiments/exploracion_resumen_diario/explorar.py`, con salidas en
  `results/exploracion_resumen_diario_2020_2022/`.
- **Datos:** sólo 2020–2022. No entrena ni carga modelos.
- **Reproducibilidad:** se corrió dos veces y dio archivos idénticos.

**Qué se mide.** Cada día, cada estación se resume con el promedio de un bloque de horas. Ese
número se compara con su valor de los 14 días previos, de dos formas:
- **propia:** el número de la estación contra su propia historia;
- **frente a vecinas:** la razón entre el número de la estación y el de sus 4 vecinas más
  cercanas, contra esa misma razón en los 14 días previos.

Luego se altera un día completo como en el protocolo, redondeando a ppb enteros, y se mide qué
fracción de los días alterados pasa el umbral.

**Cómo leer las columnas.**
- «Ruido» es cuánto se mueve ese número en un día normal: el σ robusto en por ciento.
- La detección es al 5 % de falsas alarmas por estación y día.
- Es una **cota optimista:** el detector sabe qué estación mirar, las vecinas están limpias y el
  umbral se fija con los mismos años.

| Resumen del día | Ruido, propia | Ruido, frente a vecinas | δ = 5 % | δ = 10 % | δ = 20 % |
|---|---:|---:|---:|---:|---:|
| 1 número: día completo | 24.9 % | 8.3 % | 7.3 % | 14.6 % | 47.2 % |
| 2 números: día y noche | 27.0 % | 11.1 % | 6.1 % | 11.3 % | 42.7 % |
| 4 números: cuartos de 6 h | 31.1 % | 13.8 % | 5.6 % | 8.1 % | 27.2 % |
| 1 número: sólo la tarde (12–17 h) | 29.1 % | 6.6 % | 8.1 % | **20.1 %** | **60.2 %** |
| Una sola hora (15 h) | 36.0 % | 9.9 % | 6.2 % | 10.0 % | 30.4 % |

- Las tres columnas de δ son la detección frente a vecinas.
- **Contra la propia historia,** la detección queda entre 5 y 9 % con todos los resúmenes; el azar
  es 5 %.
- **Con un umbral de 5 %/31 por estación y día** (≈ 5 % por día de red si las estaciones fueran
  independientes), ningún resumen pasa de 0.6 % con δ = 10 %.
- **Acumulando varios días alterados** (sólo la tarde frente a vecinas, 5 % por estación y día):

| Días alterados | δ = 5 % | δ = 10 % | δ = 20 % |
|---:|---:|---:|---:|
| 1 | 8.1 % | 20.1 % | 60.2 % |
| 3 | 11.2 % | 35.4 % | 80.3 % |
| 7 | 14.6 % | 47.8 % | 88.5 % |

- **Las colas son pesadas.** Con el umbral de 5 %/31, la detección de un 10 % se queda en 0.2–0.3 %
  incluso con 7 días. Ese umbral está a 5.9–8.3 σ; si los días normales siguieran una normal,
  estaría a 3.2 σ.

**Observaciones de Claude:**
- **Resumir el día comparando la estación consigo misma no baja el ruido:** su número se mueve
  25–36 % de un día a otro por el clima.
- **Lo que baja el ruido es la referencia:** frente a las vecinas, el ruido baja a 6.6–13.8 %. Es la
  premisa del asesor (M-3).
- **Más números no es mejor:** la noche agrega ruido y casi nada de señal. El mejor resumen es uno
  solo: la tarde frente a las vecinas.
- **Con falsas alarmas al nivel de red, un 10 % sigue sin verse,** ni acumulando 7 días.
- **Si se alteran varias estaciones a la vez** (fase 2), la razón con las vecinas cancelaría la
  anomalía.

---

## 2026-10-22 — Revisión 8 registrada: vecinas en el LSTM supervisado

Se registró antes de programar nada.

**Antes:**
- **Commit:** el tesista pidió revisar todo y subirlo. `f8e33aa` lleva a GitHub la parte 2 con
  los cinco δ, la junta del 2026-10-19 y la ficha de la gráfica. Las 256 pruebas pasan.
- **Lo que queda fuera de git:** las matrices (se regeneran), los modelos `.joblib`, la página en
  vivo y las carpetas del NO y el NO2, que son de otro chat.
- **La revisión de la gráfica con su ficha** se deja para el final, a pedido del tesista, para
  repasarla con todo fresco.

**Propuesta del tesista:** el LSTM supervisado de la revisión 7, más la información de sus
vecinas, con toda la metodología (selección, modelo definitivo, calibración y examen).

**Aclaraciones al discutirla:**
- La revisión 7 ya no recibía ppb: recibía cuánto se aleja cada estación de su perfil de 14 días.
  El que recibía ppb era la revisión 6.
- El LSTM supervisado nunca predice ppb: da la probabilidad de anomalía de la hora. El que predice
  ppb es el V4.
- La exploración del 2026-10-19 sí comprimió el día, en 1, 2 o 4 promedios y en una sola hora.
  Usó datos limpios de 2020–2022, con la alteración aplicada un día a la vez, no con los
  calendarios.

**Recomendaciones de Claude, aceptadas por el tesista:**
- **Vecinas:** las 4 más cercanas por distancia.
- **Información de las vecinas:** una columna nueva por estación, cuya forma se elige con 2022.
- **Un control sin entrenamiento:** la regla de vecinas.
- **Una sola cosa a la vez:** se mantiene la unidad por hora; el paso a días va aparte.
- **2025–2026,** después y para todos los detectores.

**El diseño, la regla de elección con 2022 y las predicciones** están en la revisión 8 del
protocolo (§15).

### Diagnóstico: ¿más años de entrenamiento ayudarían? (2026-10-22, registrado antes de correrlo)

**Preguntas del tesista:**
1. ¿El LSTM entiende que 2020 y 2021 son consecutivos, como el seno y el coseno le dicen que
   después de las 23 h vienen las 00 h?
2. ¿Más años le darían más variedad para no memorizar?

**Respuesta a la 1, verificada en el código** (`entrenar_lstm_sup.py`, `evaluacion_red.py`):
- Cada ejemplo son 24 horas seguidas de una serie continua de 2020 a 2022. El 31 de diciembre de
  2020 a las 23 h va seguido del 1 de enero de 2021 a las 00 h.
- El modelo no recibe el año ni el día del año, y cada ventana es independiente.
- No hay un salto que pueda malinterpretar. El seno y el coseno hacen falta porque la hora sí es
  una entrada.

**Hipótesis de Claude sobre la memorización.** Es una cuenta, no algo comprobado:
- Con 20 calendarios, cada hora real de 2020–2021 aparece 20 veces por época (17,521 ventanas ×
  20 = 350,420).
- Una época equivale a ver 20 veces el mismo ozono real, y eso explicaría que la mejor época
  siempre sea la 1.
- Matiz: con entradas relativas, 20 calendarios salieron mejor que 10 (2026-10-16).

**Pregunta 2: diseño del diagnóstico.**
- **Alcance:** fuera de la revisión 8 y sin cambiar el protocolo. Sólo usa 2020–2022 y no guarda
  modelos.
- **Modelo:** el LSTM supervisado de la revisión 7 tal cual: entradas relativas, arquitectura,
  lotes de 64, barajado y `fijar_semilla(42)` antes de cada modelo.
- **Épocas:** 10 fijas, una sola llamada a `fit`.
- **Validación:** las horas de 2022 de los calendarios 01–10, la misma para todas.
- **Severidades:** δ = 100 % y δ = 20 %, con modelos separados.

| # | Entrena con las horas de | Calendarios | Ventanas | Para qué |
|---|---|---|---:|---|
| 1 | Sólo 2020 | 01–20 | ~175,000 | Un año: el de la pandemia |
| 2 | Sólo 2021 | 01–20 | ~175,000 | Un año |
| 3 | 2020 y 2021 | 01–20 | ~350,000 | Dos años: es la revisión 7 |
| 4 | Sólo 2021 | 01–40 | ~350,000 | Tantos ejemplos como la 3, pero de un solo año: separa «más ejemplos» de «más años distintos» |

Los calendarios 21–40 se generan en memoria con las mismas reglas (clave [42, 2020, k, …]). Como
control, el calendario 01 regenerado debe ser igual a su matriz guardada.

**Medida:**
- **Principal:** la detección de las horas con etiqueta 1 de 2022, con un umbral que deja 5 % de
  falsas alarmas en las horas con etiqueta 0 de esa validación. Es la misma del 2026-10-16.
- **Se reporta:** la mejor de las 10 épocas, el promedio de las 10 y la pérdida de validación.

**Regla de lectura, fijada antes de correrlo.** Con δ = 100 %, donde hay señal que medir; δ = 20 %
sólo se reporta:
- **«Dos años ayudan más que uno»** si la 3 supera a la mejor de la 1 y la 2 por 2 puntos o más.
  Con menos de 2 puntos, no ayudan.
- **«Lo que ayuda es la variedad de años»** si, además, la 3 supera a la 4 por 2 puntos o más. Si
  la 4 queda a menos de 2 puntos de la 3, lo que ayuda es tener más ejemplos, no más años
  distintos.
- **«2020 enseña peor»** si la 1 queda 2 puntos o más por debajo de la 2.
- **Con varias épocas:** las conclusiones se toman con la mejor época, y se confirman con el
  promedio de las 10. Si los dos no coinciden, se reporta como dudoso.

**Predicción de Claude, antes de correrlo** (δ = 100 %):
1. La 3 supera a la mejor de la 1 y la 2 por 2 puntos o más.
2. La 3 y la 4 quedan a menos de 2 puntos entre sí.
3. La 1 y la 2 quedan a menos de 2 puntos entre sí.
4. La mejor época sigue siendo la 1 o la 2 en las cuatro configuraciones.

**Reproducibilidad:** se corre dos veces y los resultados deben salir idénticos. Salida en
`results/anomalias_red_v1/curva_aprendizaje_2022/`.

**Resultado.**
- **Modelos:** recién entrenados y no guardados.
- **Script:** `experiments/anomalias_red/diagnostico_curva_aprendizaje_2022.py`.
- **Ejecución:** dos corridas de 38 minutos cada una, con `resultados.csv` y `resumen.csv`
  idénticos.
- **Controles:** el calendario 01 regenerado en memoria es igual a su matriz guardada. La
  configuración 3 reproduce exactamente la «relativas, 20» de la elección del 2026-10-16 (30.2 %
  en la época 1 y 27.5 % de promedio), aunque viene de otro script.

Detección de las horas con etiqueta 1 de 2022, con 5 % de falsas alarmas en las de etiqueta 0
(5 % es el azar):

| # | Entrena con | Calendarios | δ = 100 %: mejor época | δ = 100 %: promedio de 10 | δ = 20 %: mejor época | δ = 20 %: promedio de 10 |
|---|---|---:|---|---:|---|---:|
| 1 | Sólo 2020 | 20 | 20.6 % (época 10) | 18.8 % | 6.4 % (época 1) | 5.1 % |
| 2 | Sólo 2021 | 20 | 26.3 % (época 1) | 24.8 % | 8.3 % (época 10) | 6.5 % |
| 3 | 2020 y 2021 | 20 | **30.2 %** (época 1) | **27.5 %** | 6.3 % (época 4) | 5.8 % |
| 4 | Sólo 2021 | 40 | 28.6 % (época 1) | 25.1 % | 8.6 % (época 9) | 6.4 % |

La pérdida de validación es mínima en la época 1 en las ocho corridas, salvo la configuración 4
con δ = 20 % (época 4).

**Aplicación de la regla** (δ = 100 %):
- **Dos años ayudan más que uno:** sí. La 3 supera a la 2 por 3.9 puntos con la mejor época y por
  2.7 con el promedio.
- **Si lo que ayuda es la variedad de años:** **dudoso**. Con la mejor época, la 3 supera a la 4
  por 1.6 puntos (menos de 2: no). Con el promedio, por 2.4 (sí). Como no coinciden, la regla
  manda reportarlo como dudoso.
- **2020 enseña peor:** sí. La 1 queda 5.7 puntos por debajo de la 2 con la mejor época, y 6.0
  con el promedio.

**Predicciones de Claude:**
1. La 3 supera a la mejor de la 1 y la 2 por 2 puntos o más: **se cumplió** (3.9).
2. La 3 y la 4 a menos de 2 puntos: **a medias**. Se cumplió con la mejor época (1.6), no con el
   promedio (2.4).
3. La 1 y la 2 a menos de 2 puntos: **no se cumplió**. 2020 enseña claramente peor.
4. La mejor época, 1 o 2 en las cuatro: **no se cumplió** en la configuración 1, cuya mejor
   detección cae en la época 10. Es una serie que oscila entre 16.9 y 20.6 %. En las otras tres
   sí se cumplió.

**Observaciones de Claude:**
- **Con δ = 100 %, más datos ayudan.** Pasar de 20 a 40 calendarios de 2021 sube la mejor época de
  26.3 a 28.6 %, pero casi no mueve el promedio (24.8 → 25.1). Pasar a dos años lo sube más
  (30.2 % y 27.5 %). Parece que ayudan las dos cosas, la cantidad y la variedad, pero el margen no
  alcanza para separarlas.
- **Agregar 2020 ayudó, aunque 2020 enseña peor que 2021.** No se sabe por qué 2020 enseña peor.
  - Los dos años tienen estaciones sin un solo dato (2020: ACO y CHO; 2021: AJM y HGM; XAL en
    ambos), así que eso solo no lo explica.
  - La pandemia es una posibilidad, pero no está comprobada.
- **Con δ = 20 %, ninguna configuración sale del azar con claridad:** los promedios van de 5.1 a
  6.5 %. Las dos de 2021 suben un poco con las épocas (hasta 8.3 y 8.6 % en las épocas 9–10).
  Son unos 3 puntos y la regla no los evalúa, así que no se interpretan.
- **Consecuencia para «más años»:** podrían mejorar los cambios grandes. No hay evidencia de que
  ayuden con los chicos, que es donde está la pregunta de la tesis.

**Recall, precisión, F1 y AUC de la configuración 3, pedidos por el tesista.**
- **Qué configuración:** la 3 (entrena 2020–2021, con 20 calendarios), en la época 1, que es la
  que el protocolo elegiría por la pérdida.
- **Examen de práctica:** 2022, con los calendarios 01–10: 87,600 horas. Con δ = 100 %, 16,224
  tienen anomalía; con δ = 20 %, 14,918.
- **Cómo se calculó:** la precisión y el F1 salen del recall y de las falsas alarmas fijas (5 % de
  las horas normales).

| Métrica | δ = 100 % | δ = 20 % | Azar |
|---|---:|---:|---|
| Recall | 30.2 % | 5.3 % | 5 % |
| Precisión | 57.9 % | 17.8 % | 18.5 % · 17.0 % |
| F1 | 0.40 | 0.08 | 0.08 |
| AUC | 0.74 | 0.53 | 0.50 |

- **La exactitud no se usa:** 83.0 %, frente al 81.5 % de un modelo que diga siempre «normal».
- **La precisión y el F1 dependen de cuántas anomalías hay.** Con la mitad de horas anómalas y el
  mismo detector, la precisión bajaría a ~41 %.
- **Plan acordado con el tesista:** esta configuración es el punto de partida y la referencia de
  la elección de la revisión 8. Por eso se agregaron a la revisión 8 la precisión, el F1 y el AUC
  como contraste.

### Revisión 8 programada y preparada para la PC del tesista (2026-10-22)

**Por qué la PC.**
- El tesista decidió correr la revisión 8 en su PC de escritorio (Ryzen 7 7700X), porque la lap
  se calentó con la curva de aprendizaje.
- Se usa sólo el procesador. La tarjeta RX 7800 XT se descartó: TensorFlow con AMD necesita otras
  versiones, y en tarjeta gráfica los resultados no se repiten exactos.
- Colab también se descartó, por las versiones distintas y porque su tarjeta no es determinista.
- Lo ejecutará otra instancia de Claude en la PC, siguiendo `docs/runbook_pc_revision8.md`.

**Lo que quedó listo:**
- **El código de la revisión 8** (archivos en la nota de implementación de la revisión 8 del
  protocolo):
  - las cuatro formas de la columna de vecinas;
  - la elección con 2022;
  - el LSTM y el Random Forest con `--entradas vecinas --forma`;
  - la regla de vecinas;
  - el script de la corrida completa.
- **Pruebas:**
  - 9 pruebas nuevas; pasan las 265 del proyecto;
  - la elección corrió completa en modo `--prueba` (2 calendarios, 1 época, 1 de cada 50
    ventanas). Sus números no significan nada; sólo comprueba que todo corre;
  - con datos reales de 2020–2023, se revisaron las ventanas de 98 columnas, el modelo, el
    puntaje del LSTM y el de la regla. **No se miró 2024:** la regla y el LSTM no se corrieron
    en el examen antes de elegir la forma.
- **`requirements-lock.txt`:** las 138 versiones exactas del entorno de la lap (Python 3.14.7,
  TensorFlow 2.22.0rc0), para instalar las mismas en la PC.
- **La prueba de equivalencia:** antes de cualquier corrida, la PC repite la configuración 3 de
  la curva de aprendizaje con δ = 100 % (`--solo 3 --delta 100`). Sus 10 épocas deben ser
  idénticas a las de la lap.
- **Lo que el tesista copia a mano:** los 7 zips de `data/raw/` y `CLAUDE.md`. No están en git;
  los zips se verifican con sus SHA-256.

### Cambio a Colab Pro (2026-10-23)

**Motivo:** el tesista está en la universidad, sin acceso remoto a su PC, y tiene Colab Pro.

**`notebooks/colab_revision8.ipynb`:**
- Sigue los pasos del runbook: versiones exactas, SHA-256 de los zips, planes y matrices
  idénticos, las 265 pruebas, la prueba de equivalencia y la elección con 2022 dos veces.
- Se detiene para traer los resultados.
- La corrida completa sólo arranca con `APROBADO = True`.
- Sólo usa el procesador: con la tarjeta gráfica, los números cambian y no se repiten exactos.

**Cómo se reparte el trabajo:**
- El cuaderno sólo calcula.
- Los resultados se descargan como zip, también guardado en Drive, y Claude los revisa y los
  registra en la lap.
- Así Colab no necesita permiso para escribir en GitHub.

**Lo que el tesista sube una vez a Drive:** los 7 zips, a `Mi unidad/tesis_rama/raw/`.

### Revisión 8 en Colab: equivalencia y elección de la forma con 2022 (2026-10-23)

**Cómo se ejecutó.**
- **Herramienta:** el Colab CLI oficial en lugar del cuaderno, en la sesión `rev8`.
- **Máquina:** sólo procesador (8 AMD EPYC 7B12, 50 GB).
- **Igual que en la lap:**
  - las versiones exactas de `requirements-lock.txt`;
  - los 7 zips, con su SHA-256 verificado;
  - los planes y las matrices, idénticos al repo;
  - las 265 pruebas, pasando.

**Equivalencia: salió distinta.**
- **La época 1** casi no cambia: 30.2 % en la lap y 30.4 % en Colab.
- **Las épocas siguientes** se separan hasta 4.8 puntos.
- **Decisión del tesista (opción A):** toda comparación de la revisión 8 se hace dentro de Colab.
  - La revisión 7 y los controles se repiten allá con `correr_revision7_colab.sh`, en una copia
    aparte del repo.
  - El detalle está en la revisión 8 del protocolo.

**Elección de la forma con 2022.**
- **Script:** `experiments/anomalias_red/diagnostico_vecinas_2022.py`.
- **Corridas:** dos, en paralelo, de 14:15 a 18:01 UTC.
  - Compartieron la máquina con la revisión 7 repetida.
  - `resultados.csv`, `resumen.csv` y `eleccion.json` salieron **idénticos**.
  - Se descargaron a `results/anomalias_red_v1/vecinas_2022/`, con el SHA-256 verificado.
- **Modelos:** recién entrenados y no guardados.
- **Medida:**
  - la detección de las horas con etiqueta 1 de 2022, calendarios 01–10;
  - con un umbral que deja 5 % de falsas alarmas en las horas con etiqueta 0 de esa misma
    validación, así que el azar es 5 %;
  - la precisión, el F1 y el AUC son de la mejor época;
  - «sin vecinas» es la revisión 7, entrenada en Colab con los mismos datos.

δ = 20 % (decide):

| Entrada | Mejor época | Detección: mejor | Detección: promedio de 10 | Rango en las 10 | Precisión | F1 | AUC |
|---|---:|---:|---:|---|---:|---:|---:|
| Sin vecinas | 10 | 7.0 % | 6.1 % | 4.9–7.0 % | 22.3 % | 0.11 | 0.55 |
| **a14** | 2 | **12.3 %** | **10.7 %** | 10.0–12.3 % | 33.6 % | 0.18 | 0.61 |
| afija | 1 | 9.8 % | 8.2 % | 7.3–9.8 % | 28.6 % | 0.15 | 0.60 |
| b14 | 10 | 10.6 % | 9.8 % | 9.0–10.6 % | 30.3 % | 0.16 | 0.62 |
| bfija | 3 | 9.9 % | 9.3 % | 8.6–9.9 % | 28.9 % | 0.15 | 0.61 |

δ = 100 % (sólo se reporta):

| Entrada | Mejor época | Detección: mejor | Detección: promedio de 10 | Rango en las 10 | Precisión | F1 | AUC |
|---|---:|---:|---:|---|---:|---:|---:|
| Sin vecinas | 1 | 30.4 % | 24.7 % | 21.7–30.4 % | 58.0 % | 0.40 | 0.74 |
| a14 | 2 | 34.6 % | 32.5 % | 30.6–34.6 % | 61.1 % | 0.44 | 0.79 |
| afija | 5 | 37.0 % | 33.3 % | 31.1–37.0 % | 62.7 % | 0.47 | 0.80 |
| **b14** | 1 | **59.8 %** | **55.9 %** | 53.6–59.8 % | 73.1 % | 0.66 | 0.89 |
| bfija | 5 | 46.4 % | 44.3 % | 41.2–46.4 % | 67.8 % | 0.55 | 0.86 |

La pérdida de validación es mínima en la época 1 en las diez corridas.

**Aplicación de la regla:**
- La mayor detección con δ = 20 % es la de la propia a14, así que su ventaja es 0: **queda a14**.
- La elección no cambia si se usa el promedio de las 10 épocas, ni sólo la época 1:
  - con el promedio, la siguiente es b14, con 0.9 puntos menos;
  - con la época 1, a14 tiene 10.7 % y la siguiente es afija, con 9.8 %.
- Esa robustez vale dentro de Colab. El cambio de máquina movió hasta ~5 puntos las épocas
  posteriores a la 1.

**Comparación con la revisión 7 (no decide).** Con los dos δ, **cada una de las 10 épocas de las
cuatro formas supera a la mejor época sin vecinas.**
- **Con δ = 20 %,** a14 supera a la referencia por 5.3 puntos con la mejor época y por 4.6 con el
  promedio.
- **Con δ = 100 %,** la supera por 4.2 y 7.8.

**Observaciones de Claude:**
- **Con δ = 20 %, las cuatro formas quedan cerca:** entre 9.8 y 12.3 % con la mejor época. Es una
  diferencia parecida a lo que se mueve una misma forma de una época a otra.
- **Con δ = 100 %, la forma importa mucho:** b14 detecta 59.8 % y a14 34.6 %.
  - **Hipótesis, no comprobada:** el cociente logarítmico (b) convierte la anomalía
    multiplicativa en un corrimiento casi constante, sin importar el nivel de ozono. La diferencia
    de desviaciones (a) depende del nivel.
  - Con δ = 20 %, log(1.2) ≈ 0.18 quedaría cerca del ruido. Eso explicaría que la ventaja de b no
    se vea ahí.
- **Tensión con la regla:**
  - la regla elige con δ = 20 %, la zona que se quiere mejorar, y ahí las formas casi empatan;
  - con δ = 100 %, que no decide, gana b14 por 25 puntos;
  - la regla se fijó antes y se aplica tal cual: **queda a14**.
  - Agregar b14 a la corrida completa sería un cambio después de ver 2022, aunque antes de 2024.
    Lo decide el tesista, y si se hace va como fila fechada en el §15.
- **La memorización sigue:**
  - la pérdida de validación es mínima en la época 1 en las diez corridas, y con vecinas crece más
    rápido (a14 con δ = 20 %: 0.72 → 1.57);
  - la detección no siempre cae: b14 con δ = 20 % y afija con δ = 100 % suben con las épocas;
  - la corrida completa elige E con la pérdida, así que tenderá a E = 1.

**Revisión 7 repetida en Colab, parcial** (δ = 100 y 50 %; sigue corriendo):
- **LSTM:** idéntico entre sus dos corridas de Colab y distinto de la lap, como se esperaba.
- **Random Forest:** idéntico a la lap.
- **IsolationForest:**
  - `git diff` lo marca distinto, pero sólo cambia el último decimal de su umbral de 1 %
    (0.6291173013098955 frente a …956, una diferencia de 1e-16);
  - todas sus detecciones y falsas alarmas son idénticas.

### Resultado: revisión 8 (2026-10-23)

**Decisión del tesista antes de lanzarla:** sólo a14, como manda la regla. b14 no se corre.
- **Su razón:** a14 es la que permite juzgar el LSTM con vecinas tal como se registró.
- **Lo que queda de b14:** su resultado de 2022 con δ = 100 % se conserva como observación de la
  elección.

**Ejecución.**
- **Dónde:** en Colab (sesión `rev8`), en el clon principal, en el commit e70b15c. El código de la
  revisión 8 es idéntico al de 19b3994: `git diff` de `src/` y de los cuatro scripts de la
  revisión 8 da 0 líneas.
- **Cómo:** `correr_revision8.sh a14` en tres corridas paralelas (100 y 5 %, 50 y 10 %, 20 %), de
  18:52 a 20:43 UTC.
- **Reproducibilidad:** todas las comparaciones salieron idénticas.
  - LSTM, en los cinco δ: `metricas.csv`, `episodios.csv`, `por_tamano.csv`,
    `historia_definitiva.csv` y puntajes.
  - Regla, en los cinco δ: las mismas salidas.
  - El Random Forest verifica dentro del script dos entrenamientos idénticos.
- **Memoria:** nunca bajó de 19 GB libres.
- **E = 1 en los cinco δ:** la selección corrió 9 épocas en cada uno.
- **Origen de los números:**
  - el LSTM y el Random Forest son recién entrenados (los `.keras` se guardan; los `.joblib` no
    se bajaron);
  - la regla no se entrena;
  - el V4 está cargado de disco y calculado en la lap (ver abajo);
  - el IsolationForest es idéntico en las dos máquinas.
- **Salidas:**
  - `results/anomalias_red_v1/lstm_sup_vecinas_a14_20cal/`, `rf_vecinas_a14_20cal/` y
    `regla_vecinas_a14/`;
  - registros en `logs_revision8/`, que no va a git.

**Revisión 7 repetida en Colab (opción A).**
- **Dónde:** `correr_revision7_colab.sh`, de 14:21 a 18:51 UTC, en la copia aparte
  `/content/rev7_colab`, en el commit 19b3994.
- **LSTM:** idéntico entre sus dos corridas de Colab en los cinco δ y distinto de la lap. E = 1,
  salvo con δ = 5 % (E = 2).
- **Random Forest:** idéntico a la lap en los cinco δ.
- **IsolationForest:** idéntico a la lap, salvo el último decimal del umbral de 1 % (~1e-16).
  Todas sus detecciones y falsas alarmas son iguales.
- **Dónde quedó:** `results/anomalias_red_v1/colab_revision7/`, una carpeta nueva. Las salidas de
  la lap no se tocaron.
- **V4: no se pudo calcular en Colab.**
  - **El primer intento** falló porque las predicciones de calibración 2023 y las de 2024 del V4
    no están en git; se subieron a Colab.
  - **El segundo** no pasa el control de la revisión 5: reproducir las predicciones guardadas con
    10⁻⁹ ppb. La diferencia máxima es 7.6 × 10⁻⁶ ppb, exactamente 2⁻¹⁷, una unidad de redondeo de
    float32 para valores de 64 a 128 ppb. El script se detiene antes de calcular métricas.
  - **Corrección:** un comando auxiliar de Claude imprimió «v4 idéntico a la lap» en los cinco δ,
    y era falso. Sin `pipefail` no detectó la falla, y comparó los archivos de la lap, que no se
    habían tocado.
  - **Decisión pendiente del tesista.** Claude recomienda usar el V4 de la lap: es un modelo
    cargado de disco, sólo hace inferencia, y la diferencia es de una unidad de redondeo.

**Señal = recall por hora menos el de esas mismas horas sin alterar** (examen 2024, 10
calendarios). Entre paréntesis, el azar pareado.

Nivel 5 %: recall por hora (azar pareado) y señal en puntos.

| δ | LSTM con vecinas (a14) | LSTM sin vecinas (rev 7, Colab) | Regla de vecinas | RF con vecinas | RF sin vecinas (Colab) | V4 (lap) | IsolationForest |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100 % | 52.4 (7.8) **+44.6** | 27.0 (5.9) **+21.1** | 34.7 (10.2) **+24.5** | 27.9 (8.3) **+19.6** | 16.4 (5.1) **+11.4** | 26.1 (8.9) **+17.3** | 6.7 (6.6) **+0.1** |
| 50 % | 27.7 (8.1) **+19.6** | 9.9 (5.7) **+4.2** | 20.3 (10.2) **+10.0** | 15.3 (8.4) **+6.8** | 8.0 (5.6) **+2.4** | 14.2 (8.9) **+5.3** | 6.7 (6.6) **+0.1** |
| 20 % | 8.3 (5.1) **+3.2** | 0.7 (0.5) **+0.2** | 12.2 (10.9) **+1.3** | 10.8 (9.6) **+1.2** | 7.3 (7.1) **+0.2** | 10.3 (9.6) **+0.7** | 7.2 (7.2) **+0.0** |
| 10 % | 4.8 (4.4) **+0.5** | 0.6 (0.6) **+0.0** | 11.6 (11.4) **+0.2** | 10.7 (10.3) **+0.4** | 6.4 (6.5) **-0.1** | 10.3 (10.1) **+0.1** | 7.5 (7.5) **-0.0** |
| 5 % | 2.6 (2.6) **+0.0** | 1.0 (0.9) **+0.1** | 12.6 (12.5) **+0.1** | 11.1 (11.1) **+0.1** | 7.4 (7.3) **+0.1** | 11.4 (11.3) **+0.1** | 8.2 (8.2) **+0.0** |

Nivel 1 %: recall por hora (azar pareado) y señal en puntos.

| δ | LSTM con vecinas (a14) | LSTM sin vecinas (rev 7, Colab) | Regla de vecinas | RF con vecinas | RF sin vecinas (Colab) | V4 (lap) | IsolationForest |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100 % | 32.6 (1.6) **+31.0** | 10.3 (1.8) **+8.5** | 22.6 (3.3) **+19.3** | 16.9 (2.0) **+14.9** | 9.2 (1.7) **+7.5** | 13.8 (2.1) **+11.7** | 2.0 (2.0) **+0.0** |
| 50 % | 9.2 (1.6) **+7.6** | 3.2 (1.8) **+1.3** | 9.0 (3.3) **+5.7** | 5.2 (2.0) **+3.1** | 1.9 (1.3) **+0.5** | 4.4 (2.1) **+2.4** | 2.0 (2.0) **+0.0** |
| 20 % | 1.6 (0.8) **+0.8** | 0.1 (0.0) **+0.1** | 4.0 (3.5) **+0.5** | 2.6 (2.3) **+0.3** | 1.7 (1.6) **+0.1** | 2.5 (2.2) **+0.2** | 2.2 (2.2) **+0.0** |
| 10 % | 0.8 (0.9) **-0.1** | 0.1 (0.1) **-0.0** | 3.8 (3.7) **+0.1** | 3.4 (3.1) **+0.3** | 1.4 (1.4) **+0.0** | 2.4 (2.4) **+0.0** | 2.3 (2.3) **+0.0** |
| 5 % | 0.8 (0.7) **+0.0** | 0.0 (0.0) **+0.0** | 4.1 (4.1) **-0.0** | 2.1 (2.2) **-0.1** | 1.7 (1.7) **+0.0** | 2.6 (2.6) **+0.0** | 2.6 (2.6) **+0.0** |

Contraste, nivel 5 %: LSTM con vecinas / LSTM sin vecinas (Colab) / regla de vecinas.

| δ | Precisión | F1 | Falsas alarmas, horas normales del examen | Falsas alarmas, 2024 limpio | Episodios detectados (azar) | Calendarios con señal > 0 |
|---|---|---|---|---|---|---|
| 100 % | 44.3 % / 39.0 % / 38.8 % | 0.48 / 0.32 / 0.37 | 12.6 % / 8.0 % / 10.4 % | 7.9 % / 6.2 % / 8.8 % | 90.6 (50.5) / 78.6 (38.0) / 96.9 (89.6) | 10/10 / 10/10 / 10/10 |
| 50 % | 36.4 % / 23.3 % / 30.4 % | 0.31 / 0.14 / 0.24 | 9.2 % / 6.2 % / 8.8 % | 7.9 % / 6.0 % / 8.8 % | 84.4 (60.4) / 50.5 (30.7) / 93.8 (89.6) | 10/10 / 9/10 / 10/10 |
| 20 % | 23.4 % / 15.6 % / 20.0 % | 0.12 / 0.01 / 0.15 | 4.7 % / 0.7 % / 8.4 % | 4.5 % / 0.6 % / 8.8 % | 55.2 (41.7) / 8.9 (7.8) / 90.6 (89.6) | 9/10 / 5/10 / 9/10 |
| 10 % | 18.2 % / 16.9 % / 18.4 % | 0.08 / 0.01 / 0.14 | 3.5 % / 0.5 % / 8.3 % | 3.6 % / 0.5 % / 8.8 % | 41.7 (37.0) / 12.0 (11.5) / 90.1 (89.6) | 8/10 / 3/10 / 6/10 |
| 5 % | 22.8 % / 13.5 % / 17.9 % | 0.05 / 0.02 / 0.15 | 1.3 % / 0.9 % / 8.2 % | 1.4 % / 0.9 % / 8.8 % | 32.8 (31.8) / 16.7 (14.6) / 90.1 (89.6) | 6/10 / 3/10 / 7/10 |

**La lap contra Colab, en la revisión 7** (LSTM, nivel 5 %):
- la señal sale +21.0 / +21.1 con δ = 100 %, +6.4 / +4.2 con 50 % y −0.0 / +0.2 con 20 %;
- el cambio de máquina mueve la señal hasta 2.2 puntos.

Las ganancias de la revisión 8 frente a la 7 de Colab rebasan ese margen:
- +23.5 puntos con δ = 100 %;
- +15.4 con 50 %;
- +3.0 con 20 %.

**Las 6 predicciones de Claude** (2024, nivel 5 %):
1. **Se cumplió.** Con δ = 100 %, la revisión 8 detecta al menos tanto como la 7: 52.4 % contra
   25.5 % en la lap y 27.0 % en Colab.
2. **Se cumplió.** Con δ = 20 %, la señal queda entre +1 y +5: salió +3.2.
3. **Se cumplió.** Con δ = 5 % y 10 %, la señal queda debajo de 1 punto: salió 0.0 y +0.5.
4. **Se cumplió.** La mejor época es 1 o 2 en los cinco δ: E = 1 en los cinco.
5. **A medias.** La regla queda debajo del LSTM con δ = 100 % (+24.5 contra +44.6), pero no está
   cerca del azar con δ = 20 %: tiene +1.3, por encima del punto que la predicción 3 usa como
   límite. Con 10 % y 5 % sí lo está (+0.2 y +0.1).
6. **Se cumplió.** El Random Forest queda debajo del LSTM con δ = 100 %: +19.6 contra +44.6.

**Lectura de Claude:**
- **Con δ = 100 % y 50 %, las vecinas ayudan claramente.**
  - Con 50 %, la señal pasa de +4.2 a +19.6, y la precisión de 23.3 % a 36.4 %.
  - Es positiva en los 10 calendarios.
  - El límite de detección baja: δ = 50 % ya no es marginal.
- **Con δ = 20 % hay señal por primera vez, pero pequeña.**
  - +3.2 puntos, positiva en 9 de 10 calendarios. Uno quedó en −3.3.
  - Con el nivel de 1 %, apenas +0.8.
  - Por episodio, 55.2 % detectados, contra 41.7 % del azar.
- **Con δ = 10 % y 5 % sigue en el azar.**
- **Gran parte de la ganancia viene de comparar con las vecinas,** aun sin aprender:
  - la regla sin entrenamiento supera al LSTM sin vecinas con δ = 100 % y 50 %;
  - el LSTM con vecinas suma encima de la regla: +20.1 puntos con 100 %, +9.6 con 50 % y +1.9 con
    20 %.
- **Las falsas alarmas reales salen más que lo calibrado:**
  - con δ = 100 %, el LSTM con vecinas da 7.9 % en 2024 limpio y 12.6 % en las horas normales del
    examen alterado, cuando el umbral es de 5 % en 2023;
  - la señal ya lo descuenta, porque compara con las mismas horas sin alterar, pero la precisión
    lo incluye;
  - **hipótesis, no comprobada:** el exceso en el examen alterado viene de los días posteriores a
    cada episodio, cuando la referencia de 14 días todavía contiene los días alterados.
- **El F1 no distingue a los detectores con δ ≤ 20 %:** depende del número de alertas, y el de un
  detector al azar ronda 0.1. Por eso es sólo contraste.
- **Límites:**
  - los 10 calendarios son anomalías sintéticas sobre el mismo 2024 real, no 10 años distintos;
  - 2025–2026 quedan pendientes, para todos los detectores a la vez;
  - es una sola semilla y una sola máquina.

### Análisis de la revisión 8 (2026-10-23, exploratorio, después de ver 2024)

**Alcance:**
- No cambia la revisión 8 ni sus modelos, y no se usa para elegir nada.
- Lee los puntajes, umbrales, planes y matrices guardados: no entrena ni carga modelos.
- **Script:** `experiments/anomalias_red/analisis_revision8.py`.
- **Salidas:** `results/anomalias_red_v1/analisis_revision8/`.
- **Qué compara:** el LSTM con vecinas, el LSTM sin vecinas (revisión 7, Colab) y la regla de
  vecinas, con nivel de 5 % y δ = 100, 50 y 20 %.
- **Control:** el recall por hora recalculado desde los puntajes guardados coincide con
  `metricas.csv` (diferencia 0.000).
- **Señal:** recall menos el de las mismas horas sin alterar, en puntos.

**1. El tamaño del cambio en ppb explica casi todo.**

| δ | Tramo del cambio | Horas | LSTM con vecinas | LSTM sin vecinas | Regla |
|---|---|---:|---:|---:|---:|
| 100 % | 1–16 ppb | 5,814 | +27.3 | +6.4 | +0.5 |
| | 16–32 | 3,762 | +40.9 | +14.6 | +16.3 |
| | 32–64 | 3,168 | +62.2 | +35.4 | +59.2 |
| | ≥ 64 | 1,300 | +89.5 | +70.5 | +70.8 |
| 50 % | 1–16 | 8,542 | +11.3 | +3.4 | +0.6 |
| | 16–32 | 3,939 | +26.7 | +4.4 | +15.3 |
| | 32–64 | 1,507 | +47.0 | +8.3 | +48.8 |
| | ≥ 64 | 56 | +57.1 | +5.4 | +42.9 |
| 20 % | 1–16 | 11,880 | +2.6 | +0.1 | +0.5 |
| | 16–32 | 1,025 | +9.5 | +0.7 | +11.0 |
| | 32–64 | 5 | n/d | n/d | n/d |

- **Con δ = 20 %, el 92 % de las horas alteradas cambia menos de 16 ppb.** Es el tramo más difícil
  para todos los detectores; por eso la señal total es chica.
- **El tramo no lo explica todo.** El mismo tramo de 1–16 ppb se detecta mucho mejor con δ = 100 %
  (+27.3) que con δ = 20 % (+2.6). Con δ = 100 %, esas horas de cambio chico son horas de ozono
  bajo duplicado. El modelo también ve las demás horas del episodio dentro de su ventana de 24 h.
- **La regla sólo ve cambios grandes** (casi nada con menos de 16 ppb). El LSTM con vecinas es el
  único que saca señal de los cambios chicos.

**2. El signo importa:** multiplicar se detecta mejor que dividir.

| δ | x·(1+δ) | x/(1+δ) |
|---|---:|---:|
| 100 % | +64.9 | +25.4 |
| 50 % | +27.8 | +11.5 |
| 20 % | +4.5 | +1.0 |

Son 95 episodios de multiplicar y 97 de dividir, en el LSTM con vecinas. Con el mismo δ, dividir
mueve menos ppb: con 100 %, la mitad del valor contra el doble. Además lleva el valor hacia lo
bajo, que se parece al ozono normal de la noche. Los otros dos detectores muestran la misma
diferencia.

**3. La duración del episodio casi no importa.** Con δ = 100 %, los episodios de 1–2 días dan
+37.4, contra +49.1 y +46.6 de los de 3–4 y 5–7 días. Con 50 % y 20 % no hay un patrón claro.

**4. Las vecinas ayudan más cuando están cerca.**
- Las estaciones se dividen en tres grupos según la distancia media a sus 4 vecinas: 4.6–7.5 km,
  7.6–9.4 km y 10.4–17.8 km.
- Con δ = 20 %, la señal del LSTM con vecinas es +5.7, +2.7 y +0.3. Con 50 %, +24.2, +19.2 y
  +16.7. Con 100 % no es monótona (+50.8, +37.7 y +48.3).
- Correlación de Spearman entre la distancia y la ganancia de cada estación (con vecinas menos sin
  vecinas): −0.50 con δ = 20 %, −0.34 con 50 % y −0.16 con 100 %. Son 30 estaciones; ACO no tiene
  episodios evaluables en 2024.
- Ganan 29 de 30 estaciones con 100 % y 50 %, y 24 de 30 con 20 %.
- Cada estación tiene unos 6 episodios, así que el detalle por estación es ruidoso: sólo se leen
  los grupos.

**5. El exceso de falsas alarmas viene de los días después de cada episodio.** Hipótesis
confirmada. Con δ = 100 %, el LSTM con vecinas da, en las horas normales del examen:

| Tiempo desde el fin del último episodio | Examen alterado | Esas horas en 2024 limpio |
|---|---:|---:|
| 0–1 día | 21.6 % | 5.7 % |
| 1–3 días | 18.7 % | 8.1 % |
| 3–7 días | 16.9 % | 7.0 % |
| 7–14 días | 11.4 % | 8.0 % |
| ≥ 14 días o ninguno | 8.5 % | 8.3 % |

- **Dentro de los 14 días posteriores** a un episodio sobran falsas alarmas. Después, el examen
  alterado y 2024 limpio coinciden.
- **Es lo esperado:** la referencia de 14 días todavía contiene los días alterados.
- **No es exclusivo de las vecinas:** el LSTM sin vecinas (10.4 % contra 5.4 % el primer día) y la
  regla (14.6 % contra 8.4 %) muestran lo mismo, más débil.
- **Con δ = 50 %** el efecto es menor, y con 20 % no aparece.
- **Son dos efectos distintos:**
  - el umbral de 2023 da ~8 % en 2024 limpio, no 5 %; es una deriva entre años que afecta a todos
    los detectores;
  - estas alertas posteriores a los episodios. Por definición son falsas alarmas, pero las provoca
    el ataque.
- **Idea para después, no se adopta:** una referencia que no se contamine, por ejemplo una mediana
  o una que excluya las horas con alerta.

**6. Subir contra bajar, con el mismo cambio en ppb** (pregunta del tesista; script
`experiments/anomalias_red/analisis_signo_revision8.py`, también exploratorio).

Las horas alteradas se agrupan por el cambio de su estación, |alterado − original|. Esto es el
LSTM con vecinas: el % de horas que alertan, y entre paréntesis las que alertarían igual sin
alterar.

| δ | Cambio | Sube | Baja | Ozono original mediano (sube / baja) |
|---|---|---:|---:|---|
| 100 % | 8–16 ppb | 59.6 % (6.9) | 33.0 % (7.2) | 11 / 23 ppb |
| | 16–32 ppb | 71.7 % (7.9) | 36.9 % (7.4) | 23 / 45 ppb |
| | ≥ 32 ppb | 88.7 % (6.7) | 52.9 % (9.5) | 55 / 79 ppb |
| 50 % | 8–16 ppb | 33.2 % (8.7) | 20.4 % (8.9) | 22 / 34 ppb |
| | 16–32 ppb | 44.8 % (8.2) | 31.2 % (11.8) | 44 / 63 ppb |
| 20 % | 8–16 ppb | 13.4 % (6.6) | 7.9 % (6.3) | 53 / 62 ppb |

- **Subir se detecta mejor que bajar aun con el mismo cambio en ppb.** El LSTM sin vecinas
  muestra lo mismo, más débil. La dirección importa por sí misma, no sólo el tamaño.
- **Primera hipótesis de Claude, descartada:** que las estaciones queden naturalmente más seguido
  por debajo de sus vecinas.
  - En 2023 y 2024 limpios, quedan más de 10 ppb abajo de la mediana de sus 4 vecinas el 8.4 % de
    las horas, y más de 10 ppb arriba el 9.2 %.
  - Ya sin su diferencia habitual, en conjunto es simétrico.
- **Lo que sí se encontró:** la asimetría depende del nivel de ozono. Separación natural de una
  estación frente a la mediana de sus vecinas, según el ozono de las vecinas (2023–2024 limpios):

| Ozono de las vecinas | Desviación | 10 % más bajo | 10 % más alto |
|---|---:|---:|---:|
| < 20 ppb | 7.3 | −5.5 | +10.5 |
| 20–40 | 8.1 | −10.0 | +9.0 |
| 40–60 | 8.3 | −11.0 | +8.5 |
| 60–80 | 9.9 | −14.0 | +9.5 |
| 80–100 | 12.8 | −19.5 | +11.0 |
| ≥ 100 | 17.8 | −30.0 | +11.5 |

- **Con mucho ozono es normal que una estación quede muy por debajo de sus vecinas,** hasta 30 ppb,
  pero casi nunca más de ~11 ppb por encima.
  - Con el mismo cambio en ppb, las bajadas caen en horas de más ozono que las subidas.
  - Ahí se confunden con esas lecturas bajas naturales. Una subida, en cambio, sale de lo normal.
- **La causa física no está comprobada.** Posibilidades: la pluma de ozono no cubre a todas las
  estaciones por igual, o el consumo local de ozono por las emisiones del tráfico.

**7. Métricas estándar, pedidas por el tesista** (2026-10-23, después de ver los resultados).
- **Script:** `experiments/anomalias_red/metricas_estandar_revision8.py`.
- **Salida:** `results/anomalias_red_v1/analisis_revision8/metricas_estandar.csv`.
- **Qué calcula:** ROC-AUC, PR-AUC (precisión promedio), y precisión, recall, F1 y MCC con los
  umbrales de 5 y 1 %. Junta los 10 calendarios.
- **El azar pareado:** cada métrica se calcula también con los puntajes de 2024 limpio, en las
  mismas horas y con las mismas etiquetas («sin ataque»).
- **Alcance:** no cambia la métrica principal ni ninguna elección.

| δ | PR-AUC: con vecinas / sin vecinas / regla (sin ataque) | F1 con 5 % | F1 con 1 % | MCC con 5 % |
|---|---|---|---|---|
| 100 % | 0.50 (0.16) / 0.32 (0.16) / 0.39 (0.18) | 0.48 (0.10) / 0.32 (0.09) / 0.37 (0.13) | 0.43 (0.03) / 0.17 (0.03) / 0.32 (0.06) | 0.37 / 0.22 / 0.26 |
| 50 % | 0.31 (0.17) / 0.20 (0.16) / 0.25 (0.18) | 0.32 (0.11) / 0.14 (0.08) / 0.24 (0.13) | 0.15 (0.03) / 0.06 (0.03) / 0.15 (0.06) | 0.21 / 0.05 / 0.14 |
| 20 % | 0.19 (0.16) / 0.17 (0.16) / 0.18 (0.17) | 0.12 (0.08) / 0.01 (0.01) / 0.15 (0.14) | 0.03 (0.02) / 0.00 (0.00) / 0.07 (0.06) | 0.06 / 0.00 / 0.05 |
| 10 % | 0.16 (0.16) / 0.17 (0.17) / 0.17 (0.17) | 0.08 (0.07) / 0.01 (0.01) / 0.14 (0.14) | n/d | 0.02 / 0.01 / 0.04 |
| 5 % | 0.17 (0.17) / 0.16 (0.16) / 0.16 (0.16) | 0.05 (0.05) / 0.02 (0.02) / 0.15 (0.15) | n/d | 0.04 / 0.00 / 0.05 |

**Hallazgos:**
- **Sin el azar pareado, las métricas estándar engañan aquí.**
  - **El ROC-AUC «sin ataque» no es 0.5:** sale 0.55–0.62 con δ ≤ 20 % en todos los detectores, y
    0.45 en el IsolationForest. Por eso un ROC-AUC de 0.62 con δ = 5 % no indica detección: sin
    ataque sale 0.618.
  - **La causa es la ya anotada el 2026-10-18:** con δ chico, el redondeo deja la etiqueta 1 sobre
    todo en horas de ozono alto, que tienen otros puntajes aun sin alterar. La proporción de horas
    atacadas baja de 16.0 % (δ = 100 %) a 12.4 % (δ = 5 %).
- **El F1 premia alertar mucho.** Un detector que alertara siempre tendría F1 = 0.26 con
  δ = 20 % (precisión 14.7 %, recall 100 %), más que cualquiera de los detectores. Y la regla
  tiene F1 de 0.15 con δ = 5 % sólo por coincidencia: sin ataque saca 0.147.
- **Con su versión sin ataque al lado, todas las métricas cuentan la misma historia** que la señal:
  - con δ = 100 % y 50 %, el LSTM con vecinas es el mejor por mucho;
  - con δ = 20 %, la mejora es pequeña;
  - con δ ≤ 10 %, nada.
  - El MCC sin ataque queda casi en 0 con δ ≥ 50 %, así que con δ grande se puede leer sin
    corrección.
- **Referencias** (verificar antes de citar):
  - Youden (1950), índice J = TPR − FPR. La señal del protocolo es una J con la tasa de falsas
    alarmas medida en las mismas horas.
  - Saito y Rehmsmeier (2015, PLoS ONE): PR-AUC con clases desbalanceadas.
  - Chicco y Jurman (2020, BMC Genomics): MCC frente al F1.
  - Kim et al. (2022, AAAI): el F1 por evento infla la detección en series de tiempo.

### Revisión 9 registrada: métricas de presentación (2026-10-23)

**Qué decidió el tesista:**
- presentar el conjunto estándar completo, cada métrica con su valor «sin ataque» y una nota;
- **F1 con 1 %** como principal y **F2** (la de la parte 1) como secundaria;
- la señal por hora se conserva.

Se registró en el §15 del protocolo como revisión 9, después de ver los resultados. No cambia
modelos ni umbrales. Lo calcula `experiments/anomalias_red/metricas_estandar_revision8.py`, que
ahora incluye los conteos TP, FP, FN y TN, la exactitud, la especificidad, el F2 y las
referencias «alertar siempre» y «nunca alertar».

**Resultado con 1 %** (examen; entre paréntesis, sin ataque):

| δ | Detector | TP | FP | FN | Precisión | Recall | F1 | F2 | MCC | PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 % | LSTM con vecinas | 4,578 | 2,754 | 9,466 | 0.62 (0.14) | 0.33 (0.02) | **0.43** (0.03) | 0.36 (0.02) | 0.38 | 0.50 (0.16) |
| | LSTM sin vecinas | 1,446 | 1,599 | 12,598 | 0.47 (0.15) | 0.10 (0.02) | 0.17 (0.03) | 0.12 (0.02) | 0.16 | 0.32 (0.16) |
| | Regla de vecinas | 3,169 | 2,781 | 10,875 | 0.53 (0.19) | 0.23 (0.03) | 0.32 (0.06) | 0.26 (0.04) | 0.27 | 0.38 (0.18) |
| | V4 | 1,935 | 2,238 | 12,109 | 0.46 (0.14) | 0.14 (0.02) | 0.21 (0.04) | 0.16 (0.02) | 0.19 | 0.30 (0.17) |
| 50 % | LSTM con vecinas | 1,295 | 1,509 | 12,749 | 0.46 (0.15) | 0.09 (0.02) | **0.15** (0.03) | 0.11 (0.02) | 0.15 | 0.31 (0.17) |
| | LSTM sin vecinas | 446 | 1,285 | 13,598 | 0.26 (0.17) | 0.03 (0.02) | 0.06 (0.03) | 0.04 (0.02) | 0.04 | 0.20 (0.16) |
| | Regla de vecinas | 1,264 | 2,041 | 12,780 | 0.38 (0.19) | 0.09 (0.03) | 0.15 (0.06) | 0.11 (0.04) | 0.12 | 0.25 (0.18) |
| 20 % | LSTM con vecinas | 205 | 620 | 12,705 | 0.25 (0.14) | 0.02 (0.01) | 0.03 (0.01) | 0.02 (0.01) | 0.03 | 0.19 (0.16) |
| | Regla de vecinas | 520 | 1,953 | 12,390 | 0.21 (0.19) | 0.04 (0.04) | 0.07 (0.06) | 0.05 (0.04) | 0.03 | 0.18 (0.17) |

**Referencias** con δ = 100 %:
- «alertar siempre» saca F1 0.28, F2 0.49, MCC 0 y exactitud 0.16;
- «nunca alertar» saca exactitud 0.84, y el LSTM con vecinas 0.86.

### Estudio de las falsas alarmas (2026-10-23, exploratorio, después de ver 2024)

**Alcance:**
- **Script:** `experiments/anomalias_red/falsas_alarmas_revision8.py`.
- **Salidas:** `results/anomalias_red_v1/analisis_revision8/falsas_alarmas_*.csv` y
  `contexto_2023_2024.csv`.
- **No entrena ni carga modelos.** Sólo recalcula, sin aprender, las columnas de vecinas y las
  entradas relativas.
- **Control:** la regla recalculada coincide con su puntaje guardado (diferencia máxima 5e-5, por
  las 6 cifras con que se guardan los puntajes).
- **Definición:** una falsa alarma es una alarma en una hora con etiqueta de red 0, y se compara
  con esas mismas horas en 2024 limpio.
- **Detectores:** los dos LSTM, el RF con vecinas, la regla, el V4 y el IsolationForest, con
  δ = 100, 50 y 20 %.

**A. Las falsas alarmas de más duran casi exactamente 14 días después de cada ataque.**
- Con δ = 100 % y 5 %, el LSTM con vecinas tiene +15.7 puntos el día 0 y +9 a +11 los días 2–5.
  Baja a +2–3 los días 10–12 y llega a ~0 el día 13–14.
- La regla (+6.1 el día 0) y el V4 (+3.1) siguen la misma curva, más baja.
- El LSTM sin vecinas también, con +5.1 el día 0.
- El RF con vecinas apenas (+1.4), y el IsolationForest nada (0.0).
- Con δ = 50 % el efecto es de un tercio; con 20 % casi no existe.

**B. El exceso depende del ataque anterior.** Lo provocan sobre todo los ataques largos que suben
la lectura. Con δ = 100 % y 5 %, después de un ataque de 5–7 días que sube, el exceso en los 14
días siguientes es:

| Detector | Exceso |
|---|---:|
| LSTM con vecinas | +16.7 |
| Regla | +9.1 |
| V4 | +6.2 |

Después de uno de 1–2 días que sube, el LSTM con vecinas tiene +6.4. Después de los que bajan, de
cualquier duración, +5 a +6.

**C. La estación que dispara la falsa alarma suele ser la que fue atacada.** Se puede ver con la
regla (la estación con la mayor columna) y con el V4 (la estación con el mayor residuo). Con
δ = 100 % y 1 %, de las falsas alarmas en los 14 días posteriores:
- con la regla, el 30.6 % las dispara la estación atacada, contra 2.1 % en esas horas de 2024
  limpio;
- con el V4, el 31.6 %, contra 4.6 %;
- con δ = 20 % no hay diferencia (2.1 % contra 2.1 %).

**Mecanismo, con las entradas del LSTM** (δ = 100 %, estación atacada, examen − limpio):
- **Después de un ataque que sube:** su entrada relativa queda −0.4 desviaciones típicas más baja,
  y su columna de vecinas −1.6, durante 12 días. Se borra en el día 13–14.
- **Después de uno que baja:** +0.2 y +0.7.
- **La explicación:** el perfil de 14 días quedó inflado (o desinflado) por los días alterados, así
  que la lectura real se ve anormal frente a sus vecinas.
- **Por qué la asimetría:** duplicar mueve el promedio más que dividir entre dos.
- **El IsolationForest no tiene el efecto** porque no usa el perfil de 14 días.

**D. Por qué 2024 limpio da más falsas alarmas que 2023.** Con el umbral de 1 %, en 2024 limpio
salen 1.9 % (LSTM con vecinas), 2.8 % (regla) y 2.3 % (V4). Hay dos causas visibles:
- **Mayo de 2024 tuvo mucho más ozono:**
  - el ozono medio fue de 53.5 ppb contra 37.7, y el máximo diario medio de la red, 148 ppb contra
    112;
  - en ese mes, las falsas alarmas con 5 % fueron 19.6 % en la regla (5.1 % en 2023), 18.8 % en el
    V4 (4.0 %) y 19.1 % en el IsolationForest (9.8 %).
- **Hubo más horas con pocas estaciones:**
  - en 2024 hubo 398 horas con sólo 16–19 estaciones con dato, contra 96 en 2023;
  - la cobertura de septiembre fue de 60 % y la de enero de 74 %, contra 74 % y 88 % en 2023;
  - el LSTM con vecinas es el más sensible: con 5 % alerta en el 21.4 % de las horas con 16–19
    estaciones y el 17.1 % con 20–23, contra 6.6 % con 24–27;
  - en 2024 tuvo 25.3 % de falsas alarmas en septiembre y 12.5 % en enero.

**E. Sin las horas normales de los 14 días posteriores a cada ataque** (sólo contraste; la medida
oficial no cambia):

| Detector, δ = 100 % | F1 con 1 % | F1 con 5 % |
|---|---|---|
| LSTM con vecinas | 0.43 → 0.47 | 0.48 → 0.60 |
| Regla | 0.32 → 0.35 | 0.37 → 0.45 |
| V4 | 0.21 → 0.23 | 0.29 → 0.36 |

Con 5 %, las falsas alarmas del LSTM con vecinas en las horas normales que quedan son 8.9 %, cerca
de las de 2024 limpio (7.9 %). El resto del exceso es la diferencia entre 2023 y 2024.

**Lectura:**
- **Las falsas alarmas de más tienen dos fuentes identificadas:**
  - la contaminación de la referencia de 14 días después de cada ataque, que afecta a todos los
    detectores que la usan, más al LSTM con vecinas;
  - las diferencias de 2024: un mayo con ozono excepcional y más horas con pocas estaciones.
- **Las del primer tipo no son azar:** las provoca la estación atacada.
- **Idea para después, no se adopta:** una referencia que excluya las horas con alarma o use la
  mediana. Para el LSTM, entrenar con la cobertura de datos de años con más huecos.

### Generalización de los LSTM supervisados a otro δ (2026-10-23, registrado antes de ver el resultado)

**Por qué:**
- Los LSTM y los RF supervisados tienen un modelo por δ, y cada uno se examinó con su mismo δ. Es
  como si supiera qué tamaño de ataque viene.
- El V4, el IsolationForest y la regla tienen un solo puntaje para todos los δ.
- Para compararlos en igualdad, el tesista pidió examinar cada modelo con los cinco δ.

**Cómo:**
- **Script:** `experiments/anomalias_red/generalizacion_delta_revision8.py`.
- **Modelos:** se cargan de disco los cinco `modelo.keras` del LSTM con vecinas (revisión 8) y del
  LSTM sin vecinas (revisión 7 en Colab). No se entrena nada.
- **Umbrales:** se recalculan en la lap con 2023 limpio, como en `entrenar_lstm_sup.py`.
- **Control:** la diagonal (δ de entrenamiento = δ del examen) se compara con los puntajes
  guardados.
- **Métricas:** las de la revisión 9 (F1 con 1 % como principal), cada una con su valor sin
  ataque.
- **Fuera:** los RF, porque los de la revisión 8 no se bajaron de Colab.

**Predicción de Claude, antes de verlo** (LSTM con vecinas, F1 con 1 %):
1. Con el examen de δ = 100 %, los modelos entrenados con δ = 50 % quedan a menos de 0.10 del F1
   de la diagonal (0.43).
2. Con ese mismo examen, los modelos entrenados con δ ≤ 10 % quedan al menos 0.15 por debajo de la
   diagonal.
3. Con el examen de δ = 20 %, ningún modelo supera en más de 0.03 el F1 de la diagonal (0.03).

**Resultado.**
- **Control:** los puntajes de la diagonal, calculados en la lap con los modelos de Colab,
  coinciden con los guardados (diferencia máxima 6.4e-7, por las 6 cifras con que se guardan). Los
  umbrales difieren en 6e-8.
- **Origen:** modelos cargados de disco, entrenados en Colab.
- F1 con 1 % del LSTM con vecinas (entre paréntesis, sin ataque). Filas = δ del examen; columnas =
  δ del entrenamiento:

| Examen \ Modelo | 100 | 50 | 20 | 10 | 5 |
|---|---|---|---|---|---|
| 100 % | **0.43** (0.03) | 0.29 (0.03) | 0.15 (0.01) | 0.14 (0.02) | 0.08 (0.01) |
| 50 % | **0.21** (0.03) | 0.15 (0.03) | 0.08 (0.01) | 0.06 (0.02) | 0.03 (0.01) |
| 20 % | 0.05 (0.03) | 0.05 (0.03) | 0.03 (0.01) | 0.02 (0.02) | 0.02 (0.01) |
| 10 % | 0.03 (0.03) | 0.03 (0.03) | 0.02 (0.02) | 0.02 (0.02) | 0.01 (0.01) |
| 5 % | 0.03 (0.03) | 0.03 (0.03) | 0.02 (0.02) | 0.02 (0.02) | 0.01 (0.01) |

- **Entrenar con ataques grandes generaliza hacia abajo, y mejor que el modelo del propio δ.**
  - Con el examen de 50 %, el modelo de δ = 100 % saca 0.21 contra 0.15 del de 50 %.
  - Con 5 % de falsas alarmas y el examen de 20 %: 0.15 (0.10) y 0.16 (0.11) los de 100 y 50 %,
    contra 0.12 (0.08) del de 20 %.
- **Entrenar con ataques chicos no sirve,** ni siquiera para su propio δ.
  - Los modelos de δ ≤ 20 % aprenden poco.
  - En el LSTM sin vecinas casi no alertan: F1 de 0.00 a 0.03 en todos los exámenes.
- **Hipótesis, no comprobada:**
  - con δ chico, muchas horas con etiqueta 1 son indistinguibles (cambios de pocos ppb), así que la
    etiqueta es casi ruido;
  - con δ = 100 % el modelo aprende la forma de un ataque, sobre todo la separación de la estación
    frente a sus vecinas, y eso le sirve también con δ menores.
- **Consecuencia para la comparación:** el protocolo de un modelo por δ **no** favorece a los
  supervisados.
  - Un solo modelo, el de δ = 100 %, rinde igual o mejor en todos los exámenes.
  - Elegir ése después de ver 2024 sería una elección *a posteriori*. Pero los modelos de 100 y de
    50 % superan a la diagonal con δ menores, así que la conclusión no depende de esa elección.

**Predicciones de Claude:**
1. **No se cumplió.** El modelo de δ = 50 % en el examen de 100 % quedaría a menos de 0.10 de la
   diagonal: queda 0.14 abajo (0.29 contra 0.43).
2. **Se cumplió.** Los modelos de δ ≤ 10 % quedarían al menos 0.15 abajo: quedan 0.29 y 0.35 abajo.
3. **Se cumplió, por poco.** Con el examen de 20 %, ninguno superaría la diagonal en más de 0.03:
   el máximo es +0.02 (0.05 contra 0.03).

### Comparación general: supervisados contra no supervisados (2026-10-23)

- **Script:** `experiments/anomalias_red/comparacion_general_revision8.py`.
- **Salida:** `results/anomalias_red_v1/analisis_revision8/comparacion_general.csv`.
- **Qué compara:** examen 2024, métricas de la revisión 9. Los LSTM aparecen con el modelo de su δ
  y con un solo modelo para todos los δ (el de δ = 100 %).
- F1 con 1 % (entre paréntesis, sin ataque):

| Detector | Familia | δ = 100 % | δ = 50 % | δ = 20 % | δ ≤ 10 % |
|---|---|---|---|---|---|
| LSTM con vecinas, un modelo | supervisado | **0.43** (0.03) | **0.21** (0.03) | 0.05 (0.03) | = azar |
| LSTM con vecinas, modelo de su δ | supervisado | **0.43** (0.03) | 0.15 (0.03) | 0.03 (0.01) | = azar |
| Regla de vecinas | sin entrenamiento | 0.32 (0.06) | 0.15 (0.06) | 0.07 (0.06) | = azar |
| RF con vecinas, modelo de su δ | supervisado | 0.27 (0.04) | 0.09 (0.04) | 0.05 (0.04) | = azar |
| V4 | no supervisado | 0.21 (0.04) | 0.08 (0.04) | 0.04 (0.04) | = azar |
| LSTM sin vecinas, un modelo | supervisado | 0.17 (0.03) | 0.06 (0.03) | 0.03 (0.03) | = azar |
| IsolationForest | no supervisado | 0.04 (0.04) | 0.04 (0.04) | 0.04 (0.04) | = azar |

- **MCC con 1 %:**

| Detector | δ = 100 % | δ = 50 % |
|---|---|---|
| LSTM con vecinas (un modelo) | 0.38 | 0.20 |
| Regla | 0.27 | 0.12 |
| RF con vecinas | 0.27 | 0.08 |
| V4 | 0.19 | 0.04 |
| LSTM sin vecinas | 0.16 | 0.04 |
| IsolationForest | 0.01 | 0.01 |

**Lectura de Claude:**
1. **El mejor supervisado supera claramente al mejor no supervisado:** el LSTM con vecinas contra
   el V4 da 0.43 contra 0.21 con δ = 100 %, y 0.21 contra 0.08 con 50 %. No depende de saber el δ.
2. **Lo que más pesa es comparar con las vecinas, no el aprendizaje supervisado.**
   - La regla, que no se entrena, es el segundo mejor detector.
   - Supera al V4 y al LSTM supervisado sin vecinas.
   - El LSTM supervisado **sin** vecinas queda por debajo del V4 no supervisado (0.17 contra 0.21
     con δ = 100 %).
   - Lo supervisado suma encima de las vecinas: 0.43 contra 0.32 de la regla.
3. **El IsolationForest no detecta nada** en ningún δ: su F1 es igual sin ataque.
4. **Con δ = 20 % ningún detector se separa del azar** de forma útil con 1 %.
   - Lo más que se ve es +0.02 de F1, en el LSTM con vecinas.
   - Con 5 %, +0.05 en el LSTM de un solo modelo, contra +0.01 de la regla y del V4.
   - Con δ ≤ 10 %, nada.
5. **Límites de la comparación:**
   - **Los supervisados se entrenaron con el mismo tipo de ataque** del examen: multiplicativo, de
     días completos desde las 00 h. Con otro tipo (deriva gradual, desplazamiento fijo, bit
     flipping), no se sabe. Ahí un no supervisado podría generalizar mejor. Es la comparación
     pendiente con la parte 1.
   - **El LSTM con vecinas tiene más falsas alarmas tras los ataques** y es el más sensible a los
     huecos de datos (estudio de falsas alarmas).
   - **Es una sola semilla, un solo año real** (2024) y un solo umbral calibrado con 2023.

**Decisión del tesista sobre el V4 (2026-10-23):**
- en las comparaciones se usa el V4 de la lap (cargado de disco), porque el de Colab no pasa el
  control de 10⁻⁹ ppb por una unidad de redondeo;
- se anotó en la revisión 8 del protocolo.

### Gráfica de la semana: F1 según δ (2026-10-23)

- **Qué es:** `docs/img/anomalias_red_v1/f1_por_delta.png`, con
  `experiments/anomalias_red/graficar_f1_delta.py`. Su ficha está en `docs/fichas_graficas.md`.
- **Qué muestra:**
  - el F1 con 1 % del LSTM con vecinas (el modelo oficial de cada δ, decisión del tesista) y del V4
    (de la lap);
  - el F1 de cada uno sin ataque, en punteada;
  - el rango entre los 10 calendarios.
- **Por qué no lleva los bits de la parte 1:** son otro ataque, con otra unidad y otras falsas
  alarmas. El tesista lo había propuesto, y Claude recomendó no mezclarlos.
- **Colores:** el V4 conserva su naranja y el LSTM con vecinas toma el violeta. El azul queda para
  el LSTM sin vecinas. El par pasa el validador de la skill de visualización, incluida la prueba de
  daltonismo.
- **Control:** los valores coinciden con `metricas_estandar.csv`.
- **Lo que no se sobrescribe:** `recall_por_delta.png` ni `deteccion_por_delta.png`.
- **Simplificada el mismo día, a pedido del tesista:** la primera versión era difícil de leer.
  - El eje Y dice sólo «F1» y la ficha explica qué es un caso.
  - Se quitaron las barras de rango entre calendarios; su conclusión va en la ficha.
  - Las dos líneas punteadas sin ataque se cambiaron por una zona gris de azar.
  - Las etiquetas van directo sobre las líneas, sin leyenda.
  - El título dice la conclusión.
- **Dos ajustes más, propuestos por Claude al revisarla y aprobados por el tesista:**
  - el título dice «casi duplica el F1» en lugar de «detecta el doble», y «ninguno detecta de forma
    útil» en lugar de «ninguno detecta»;
  - el subtítulo aclara que el LSTM se entrenó con ataques de este tipo y que el V4 nunca vio
    ataques.

### Búsqueda en la literatura antes de la revisión 10 (2026-10-23)

Pedida por el tesista antes de decidir qué mejorar. Claude buscó en la web y leyó los resúmenes y,
de PARAAD, el texto completo. No se descargó nada al repo.

**1. PARAAD** (Allka, Ferrer-Cid, Barceló-Ordinas y García-Vidal, IEEE Trans. Network Science and
Engineering 11(6), 2024, doi 10.1109/TNSE.2024.3454459; texto completo en UPCommons). Es el más
parecido a nuestro problema.
- **Datos:** O3 de 8 estaciones de referencia de Barcelona, 2014–2019.
- **Método:** autoencoder no supervisado que mira **bloques de un día** (D = 24 h) de todas las
  estaciones.
- **Anomalías sintéticas:**
  - sesgo: al 30 % de los sensores y al 30 % de sus días se les suma β desviaciones típicas a la
    señal diaria estandarizada, con β ~ |N(0, σ²)| y σ = 2, es decir, ~1.6 desviaciones en
    promedio, todo el día;
  - deriva lenta.
- **Resultados con datos reales:** TPR 0.81 y precisión 0.84 por estación-día, también
  localizando la estación.
- **Ablación:** con bloques de 1 hora la precisión baja (0.70 contra 0.84 en PARAAD-SA; 0.34
  contra 0.79 en PARAAD-MH).
- **Dicen explícitamente** que un sesgo pequeño es indistinguible de los datos normales.
- **Lo que difiere de nosotros:**
  - su sesgo (~1.6 desviaciones típicas, unas decenas de ppb todo el día) es mayor que nuestro
    δ = 100 %, cuyo cambio típico es de 20 ppb;
  - el umbral se optimiza por exactitud en una ventana de 30 días y luego se aplica al siguiente.
    Según el texto parece usar etiquetas, lo que es más optimista que nuestro umbral fijo;
  - mide por estación-día, no por hora de red.

**2. STC-RAAD** (mismo grupo, IEEE Internet of Things Journal 11(19), 2024, doi
10.1109/JIOT.2024.3416525). Autoencoder recurrente que usa explícitamente las estaciones vecinas
para reconstruir cada sensor. Según el resumen, mejora 38 % la detección y 36 % la precisión
frente a otros métodos.

**3. Control de calidad meteorológico** (TITAN de MET Noruega: Båserud et al., Adv. Sci. Res. 17,
2020; Lussana et al., QJRMS 2010).
- El *buddy check* compara cada estación con sus vecinas: es lo que hace nuestra regla de vecinas.
- El *spatial consistency test* estima el valor esperado con interpolación espacial en lugar de un
  promedio simple.

**4. Evaluación** (Kim et al., AAAI 2022, doi 10.1609/aaai.v36i7.20680).
- Con el *point adjustment* (contar un evento como detectado si alguna alarma cae dentro), un
  puntaje **al azar** saca F1 de 0.969 en SWaT.
- Respalda nuestra decisión de comparar siempre con «sin ataque» y de no contar ataques
  encontrados como medida principal.

**5. Cambios pequeños y sostenidos:** la familia de detección secuencial (CUSUM y la detección más
rápida en redes de sensores, por ejemplo arXiv 2012.13027) acumula evidencia en el tiempo. Detecta
corrimientos pequeños y persistentes a cambio de retraso.

**6. Referencia robusta:** la mediana y la MAD son el estimador estándar de la estadística robusta
cuando parte de los datos está contaminada. Va en la línea de la opción C.

**7. Manipulación real de datos de calidad del aire** (Turiel y Kaufmann, PLOS One). Según el
resumen, en ciudades chinas las estaciones locales reportaban menos PM2.5 que las de la embajada de
EE. UU. cuando la contaminación era alta. Es un indicio de que el ataque realista es **bajar** la
lectura en días de alta contaminación, justo la dirección que peor se detecta aquí.

**Lo que cambia para la revisión 10, según Claude:**
- **La opción C (mediana) tiene respaldo** de la estadística robusta.
- **La opción A (decidir por día completo) tiene más respaldo del que Claude le dio:** es lo que
  hace el trabajo más parecido, con mejor precisión que por hora. Pero sus anomalías, como las
  nuestras, duran días completos, así que es igual de favorable al diseño sintético.
- **Ideas nuevas:**
  - evaluar también por estación-día con localización, para compararnos con PARAAD;
  - estimar el valor esperado con interpolación espacial (como el SCT) en vez del promedio de 4
    vecinas;
  - CUSUM para δ chicos.

### Revisión 10 registrada y programada: referencia de 14 días con mediana (2026-10-23)

**Decisión del tesista, tras la búsqueda en la literatura:**
- seguir con la opción C (mediana) y con la decisión por estación-día;
- descartar la opción B (un solo modelo con ataques grandes), porque le pareció forzar la detección.

**Separación propuesta por Claude:**
- **Revisión 10:** sólo la mediana.
- **Revisión 11:** estación-día.
- **Por qué:** el LSTM actual da una sola salida para toda la red y no dice qué estación. Decidir
  por estación-día exige otra salida, otras etiquetas y otra evaluación. Si se cambian dos cosas a
  la vez, no se sabe cuál ayudó.

**Hecho:**
- el diseño y las predicciones en el protocolo (revisión 10);
- el código y las pruebas: 3 nuevas, 268 en total;
- la elección con 2022, probada en modo `--prueba`.

No se ha corrido nada con datos reales.

**Siguiente:** con el visto bueno del tesista, la elección con 2022 en Colab (dos corridas, ~2 h).
Si adopta la mediana, la corrida completa (~2 h más).

**Referencias:** guardadas en `docs/referencias_literatura.md` y `docs/referencias.bib`, con
marcas de «por verificar».

### Revisión 10: elección con 2022 en Colab, no se adopta la mediana (2026-10-23)

**Cómo se ejecutó.**
- **Herramienta:** el Colab CLI, en la sesión `rev10`, de 21:34 a 23:36 (hora local).
- **Máquina:** sólo procesador. Fue un Intel Xeon @ 2.20 GHz (Broadwell, 8 núcleos virtuales,
  50 GB), no el AMD EPYC de la revisión 8.
- **Código:** el repo en el commit 6d417a9 más los archivos de la revisión 10, sin commit, subidos
  como tarball con su SHA-256 verificado.
- **Igual que en la lap:**
  - las versiones exactas;
  - los 7 zips, con su SHA-256;
  - los planes y las matrices, idénticos al repo;
  - las 268 pruebas, pasando.
- **Corridas:** dos de `diagnostico_referencia_2022.py` en paralelo. `resultados.csv`,
  `resumen.csv` y `eleccion.json` salieron **idénticos**.
  - Se descargaron a `results/anomalias_red_v1/referencia_2022/`, con el SHA-256 verificado.
  - Los registros están en `logs_revision10/`.
- **Modelos:** recién entrenados en Colab y no guardados.

**Resultado** (F1 con 1 % en la época de menor pérdida de validación, que fue la 1 en las seis):

| δ | Media | Mediana | Diferencia |
|---:|---:|---:|---:|
| 100 % | 0.263 | 0.208 | −0.055 |
| 50 % | 0.099 | 0.126 | +0.027 |
| **Promedio de 100 y 50 (decide)** | **0.181** | **0.167** | **−0.014** |
| 20 % (sólo se reporta) | 0.042 | 0.041 | −0.002 |

**Aplicación de la regla:**
- la ventaja es −0.014, y hacía falta +0.02;
- **queda la media, y la revisión 10 se cierra sin examinarse con 2024**;
- la decisión no cambia con otra forma de resumir. Con el promedio de las 10 épocas es −0.007, con
  la mejor época −0.001, con el F1 con 5 % −0.006 y con el PR-AUC +0.001.

**Falsas alarmas con 1 % y δ = 100 %:**

| Horas normales | Media | Mediana |
|---|---:|---:|
| De los 14 días posteriores a un ataque | 1.42 % | 1.18 % |
| Las demás | 0.45 % | 0.76 % |

- La mediana sí reparte mejor las falsas alarmas. Antes había 3.2 veces más falsas alarmas después
  de un ataque que en las demás horas; con la mediana hay 1.6 veces.
- **Pero el total queda en 1 % por construcción**, y el F1 no sube.

**Predicciones:**
- la 1 falló: las falsas alarmas tras un ataque bajaron 17 %, no a la mitad;
- la 2 falló;
- la 3 a la 6 eran de 2024 y no se evalúan.

**Equivalencia con la revisión 8: salió distinta, por la máquina.**
- **La diferencia:** la variante con media es la a14 de la revisión 8, con los mismos datos y la
  misma configuración, pero no repite sus épocas.
  - La pérdida de validación difiere hasta 0.14, por ejemplo 0.573 contra 0.552 en la época 1 con
    δ = 100 %.
  - El F1 con 5 % difiere hasta 0.033, y la detección con 5 % hasta 3.3 puntos.
- **El código no es la causa:** en la lap se comprobó que las entradas con media del código de la
  revisión 10 son idénticas bit a bit a las del commit 6d417a9 (sigma, vecinas, escala y las 98
  columnas de dos calendarios).
- **Consecuencia:**
  - el procesador cambia la aritmética del entrenamiento, aunque los dos tengan AVX2 y 8 núcleos;
  - la opción A («todo dentro de Colab») no basta;
  - para comparar contra números de la revisión 8 hace falta el mismo procesador, o repetir la
    revisión 8 en la misma sesión.
  - Esta elección no se afecta, porque las dos variantes se entrenaron en la misma corrida.

**Observaciones de Claude:**
- **El efecto de la mediana es del tamaño del ruido.**
  - Con δ = 100 %, el F1 con 1 % de la misma variante se mueve de una época a otra entre 0.23 y
    0.26 con la media, y entre 0.20 y 0.25 con la mediana.
  - Con 50 % se mueve entre 0.08 y 0.11, y entre 0.09 y 0.13.
  - **No hay evidencia de que la mediana ayude**, ni de que dañe mucho.
- **El límite del diseño de la regla** (lo diseñó Claude):
  - **La diferencia:** la elección fija el umbral con las horas normales de la misma validación
    2022 atacada. El examen lo fija con 2023 limpio.
  - **Por qué importa:** las falsas alarmas tras un ataque castigan en los dos casos, pero por
    caminos distintos. En la elección suben el umbral y bajan el recall; en el examen se suman a
    las falsas alarmas y bajan la precisión. Así que la ganancia no tiene por qué ser del mismo
    tamaño.
  - **No se usa para reabrir la revisión 10:** la regla se fijó antes y se aplica tal cual.
    Probarlo sería una revisión nueva, registrada antes de correrla y reportada junto a este
    resultado negativo.
- **Hipótesis, no comprobada:** la mediana de 14 valores es una referencia más ruidosa que la media
  cuando los datos están limpios. Lo que gana en los días contaminados lo puede perder en todos los
  demás.

**Commit:** dc395f4, con la revisión 10 cerrada y las referencias.

### Revisión 11 redactada y aprobada: decisión por estación-día (2026-10-24)

**Pedido del tesista:** redactar el diseño para revisarlo antes de correr nada.

**Origen:**
- la opción A del 2026-10-23, decidir por día completo;
- PARAAD, que decide por bloques de un día y localiza la estación;
- la decisión del tesista de seguir con estación-día, aparte de la mediana.

**Diseño:** en el protocolo, revisión 11.
- **Caso:** una estación en un día. Se usan las estación-días con al menos 12 horas válidas.
- **Dos formas de juntar el día:** la peor hora (control) y el promedio con signo del día
  (propuesta).
- **Umbral:** uno solo para las 31 estaciones, con 1 y 5 % de falsas alarmas en un año limpio.
- **Fase 1:** sólo la regla de vecinas, con 2022, en la lap.
  - Los umbrales salen de 2021 limpio, para imitar el examen.
  - Si el promedio del día no supera a la peor hora en 0.02 o más de F1 con 1 % (promedio de
    δ = 100, 50 y 20 %), se cierra sin 2024.
- **Fase 2:** la regla y el V4 en 2024.
- **Fase 3:** un LSTM por estación, sólo como esbozo.

**Nota de lectura que salió al diseñarla:**
- las estación-días atacadas son cerca de 0.8 %;
- con 1 % de falsas alarmas, el F1 no pasa de ~0.62 aunque se detecte todo; con 5 %, de ~0.25;
- por eso no se compara uno a uno con la hora de red ni con PARAAD, que altera ~9 %.

**Aprobación:** el tesista la aprobó tal cual el 2026-10-24. Las fases 1 y 2 van en la lap: la regla
no se entrena y el V4 no pasa su control en Colab.

**Siguiente:** programar la fase 1 con sus pruebas y correrla dos veces en la lap.

### Revisión 11, fase 1: el promedio del día le gana a la peor hora en 2022 (2026-10-24)

**Hecho:**
- **El módulo** `src/detect/estacion_dia.py`, con 5 pruebas en `tests/test_estacion_dia.py`.
- **El script** `experiments/anomalias_red/diagnostico_estacion_dia_2022.py`.
- **Las corridas:** dos en la lap, en paralelo, de ~1.5 min cada una. Los cinco archivos
  salieron **idénticos**.
  - Están en `results/anomalias_red_v1/estacion_dia_2022/`.
  - Los registros están en `logs_revision11/`.
  - No entrena ni carga modelos.
- **Aviso:** el modo `--prueba` usa datos reales de 2 calendarios. Su salida, ya con «pasa», se vio
  antes de la corrida completa. No se cambió nada.

**Resultado** (regla de vecinas a14 con media; F1 con 1 % por estación-día, 10 calendarios
juntos):

| δ | Peor hora | Promedio del día | Diferencia |
|---:|---:|---:|---:|
| 100 % | 0.382 | 0.377 | −0.006 |
| 50 % | 0.260 | 0.389 | +0.129 |
| 20 % | 0.057 | 0.098 | +0.041 |
| **Promedio de 100, 50 y 20 (decide)** | **0.233** | **0.288** | **+0.055** |
| 10 % | 0.020 | 0.021 | +0.001 |
| 5 % | 0.014 | 0.008 | −0.006 |

- **Sin ataque,** el F1 con 1 % es 0.005 con la peor hora y 0.003 con el promedio del día.
- **Aplicación de la regla:** la ventaja es +0.055, mayor que 0.02: **se pasa a la fase 2**.

**Falsas alarmas con 1 % y δ = 100 %:**

| Grupo | Peor hora: tasa | Peor hora: parte | Promedio del día: tasa | Promedio del día: parte |
|---|---:|---:|---:|---:|
| Contagio (una vecina atacada ese día) | 9.7 % | 24 % | 19.0 % | 30 % |
| Tras un ataque propio (14 días) | 9.3 % | 19 % | 20.3 % | 26 % |
| Resto | 0.8 % | 57 % | 1.0 % | 45 % |

**Excluidas:**
- 16 % de las estación-días y 18 % de las atacadas;
- en 2022, el 90 % de las exclusiones es porque la propia estación tiene menos de 12 horas con
  dato. Encabezan TLI, AJM y AJU, con 145–168 días cada una.

**Predicciones:** la 1 falló, porque con δ = 100 % la peor hora queda apenas arriba. Se cumplieron
la 2, la 3, la 4 y la 5. La 6 es de 2024.

**Observaciones de Claude:**
- **La ganancia está en δ = 50 y 20 %,** justo la zona que se quería mejorar. Con 50 % el F1 sube
  de 0.26 a 0.39.
- **Con δ = 100 % empatan.** El promedio del día detecta más (recall de 0.82 contra 0.61), pero
  también amplifica los dos sesgos sostenidos:
  - el contagio a las vecinas;
  - el perfil de 14 días contaminado tras un ataque.
  - Juntos son el 55 % de sus falsas alarmas.
- **Con δ ≤ 10 % nada funciona,** igual que por hora de red.
- **Hay techo:** con ~0.8 % de estación-días atacadas, el F1 con 1 % no pasaría de ~0.62.
- **Ideas que esto apunta, fuera de esta revisión:**
  - quedarse con la estación de mayor puntaje del vecindario, contra el contagio;
  - la mediana de 14 días, contra la contaminación tras un ataque. Por hora de red no ayudó, pero
    aquí el exceso tras un ataque propio pesa más.
  - Cualquiera de las dos sería una revisión nueva, registrada antes.
- **No se compara uno a uno con la hora de red.**

**Siguiente:** la fase 2, el examen 2024 por estación-día con la regla y el V4, en la lap. Falta
programarla, y el V4 necesita repetir su inferencia para guardar el residuo por estación.

**Commit:** cc0090a, con la revisión 11 aprobada y la fase 1.

### Revisión 11, fase 2: examen 2024 por estación-día (2026-10-24)

**Hecho:**
- **El script** `experiments/anomalias_red/evaluar_estacion_dia.py`, con `--detector regla|v4`.
- **Las corridas:** dos por detector, en la lap. Los resultados salieron **idénticos**: la regla
  tarda segundos y el V4 unos 10 min por corrida.
  - Están en `results/anomalias_red_v1/estacion_dia/{regla,v4}/`.
  - Los registros están en `logs_revision11/`.
- **Modelos:** la regla no se entrena; el V4 se cargó de disco y repitió su inferencia.
- **Controles:**
  - en los 52 conjuntos (2023 limpio, 2024 limpio y 50 exámenes), el puntaje de red que sale del
    valor por estación reproduce el guardado antes por cada detector, con 6 cifras;
  - el V4 reproduce sus predicciones de 2024 limpio (diferencia máxima 1.4 × 10⁻¹⁴ ppb) y repite
    el primer calendario con residuos idénticos.
- **El modo `--prueba`** de este script no imprime métricas; no se vio nada antes de la corrida
  completa.

**Resultado** (F1 con 1 % por estación-día, 10 calendarios de 2024 juntos; decide el promedio del
día):

| δ | Regla: promedio del día | Regla: peor hora | V4: promedio del día | V4: peor hora |
|---:|---:|---:|---:|---:|
| 100 % | **0.323** | 0.261 | 0.206 | 0.205 |
| 50 % | **0.330** | 0.200 | 0.102 | 0.099 |
| 20 % | **0.116** | 0.047 | 0.029 | 0.024 |
| 10 % | 0.038 | 0.018 | 0.018 | 0.014 |
| 5 % | 0.016 | 0.013 | 0.014 | 0.011 |
| Sin ataque | 0.012 | 0.011 | 0.011 | 0.006 |

**Regla de vecinas con el promedio del día:**
- **Con δ = 50 %:** recall de 0.62 y precisión de 0.23.
- **Con δ = 100 %:** recall de 0.85 y precisión de 0.20.
- **PR-AUC:** 0.58, 0.40 y 0.050 con 100, 50 y 20 %.

**Falsas alarmas con 1 % y δ = 100 %, regla con el promedio del día:**
- contagio: 25 %, con una tasa de 24 %;
- tras un ataque propio: 24 %, con una tasa de 25 %;
- resto: 51 %, con una tasa de 1.4 %.

**Predicciones:** la 6 se cumplió, porque con δ ≥ 50 % la regla supera al V4. En total se
cumplieron 5 de 6.

**Observaciones de Claude:**
- **2024 confirma a 2022 en la regla.** El promedio del día gana en todos los δ, y con fuerza en
  50 % (0.20 a 0.33) y 20 % (0.05 a 0.12).
- **En el V4 casi no cambia,** con +0.003 a +0.005.
  - **Hipótesis, no comprobada:** el residuo del V4 ya compara contra su predicción con las demás
    estaciones, y la deriva del año pesa más en su promedio.
  - Su falsa alarma en 2024 limpio sube a 2.9 % con el promedio del día, contra 2.3 % con la peor
    hora.
- **Cambio de año:** las falsas alarmas en 2024 limpio pasan del 1 % que se fijó con 2023.
  - En la regla son 1.2 % con el promedio y 1.9 % con la peor hora.
  - Es lo mismo que ya se vio por hora de red, con mayo de 2024 excepcional.
- **Casi la mitad de las falsas alarmas de la regla** con δ = 100 % viene de los dos sesgos
  sostenidos: el contagio y la referencia contaminada.
  - Son los blancos naturales de una mejora de la propia regla, que costaría menos que un LSTM.
  - Sería una revisión nueva.
- **Sobre el techo:**
  - las estación-días atacadas válidas son 0.78 %, así que el F1 con 1 % no pasaría de ~0.6;
  - el 0.33 con δ = 50 % está a medio camino de ese techo;
  - **no se compara uno a uno con el 0.15 por hora de red** de la regla con δ = 50 % (revisión 8),
    porque son casos y proporciones distintos;
  - sí se puede decir que, por estación-día, la regla además señala la estación correcta.
- **Lo que no cambia:** con δ ≤ 10 % nada detecta de forma útil, igual que por hora de red.

**Siguiente** (decisión del tesista):
- (a) la fase 3, el LSTM por estación, que se diseña y registra aparte antes de programarlo;
- (b) antes de eso, una revisión de la propia regla contra el contagio y la referencia contaminada;
- (c) la gráfica de la semana con estos resultados.

**Commit:** b957123, con la fase 2.

### Revisión 12 registrada y programada: regla de vecinas robusta (2026-10-24)

**Decisión del tesista:** la opción b, mejorar la regla antes de un LSTM por estación.

**Diseño,** en el protocolo (revisión 12). Dos cambios, uno contra cada sesgo de la fase 2:
- **la mediana de 14 días,** contra la referencia contaminada tras un ataque;
- **la dominancia en el vecindario,** contra el contagio. Una estación-día sólo alerta si su puntaje
  es el mayor entre ella y sus vecinas ese día.

**Variantes y elección:**
- R0 a R3, con los dos cambios por separado y juntos, todas con el promedio del día;
- se eligen sólo con 2022, con el mismo esquema que la fase 1 de la revisión 11;
- hay 7 predicciones registradas.
- **Aclaración agregada al programar, antes de correr:** la variante más sencilla que se prefiera
  también tiene que ser candidata.

**Hecho:**
- `estacion_dia.dominancia`, con una prueba nueva (274 en total);
- el script `diagnostico_regla_robusta_2022.py`, con el control de que R0 reproduzca exactamente
  la fase 1 de la revisión 11;
- las opciones `--referencia` y `--dominancia` en `evaluar_estacion_dia.py`.
  - **Comprobado:** con los valores por defecto, el script reproduce byte por byte los CSV de la
    fase 2 de la revisión 11.
- **El modo `--prueba`** de los dos scripts ya no imprime métricas, y su salida no se miró.
- **No se ha visto ningún resultado de la revisión 12.**

**Siguiente:** con el visto bueno del tesista, correr la elección con 2022 dos veces en la lap
(~2 min). Si se elige una variante, sigue el examen 2024 (~1 min por variante).

### Revisión 12: elección con 2022 y examen 2024 (2026-10-24)

**Aprobada por el tesista** antes de correrla.

**Cómo se corrió:**
- en la lap, dos corridas de cada cosa, con salidas idénticas; no entrena ni carga modelos;
- los registros están en `logs_revision11/`;
- **un tropiezo al lanzarla:** la primera vez, las dos variantes con mediana no corrieron. zsh pasó
  `--referencia mediana` como un solo argumento. Se relanzaron con los argumentos separados; no
  cambió nada del código.

**Controles:**
- R0 reproduce exactamente la fase 1 de la revisión 11 con 2022;
- con los valores por defecto, R0 reproduce byte por byte la fase 2 con 2024.

**Elección con 2022** (F̄ = F1 con 1 %, promedio de δ = 100, 50 y 20 %):

| Variante | F̄ | δ = 100 % | δ = 50 % | δ = 20 % |
|---|---:|---:|---:|---:|
| R0 (revisión 11) | 0.288 | 0.377 | 0.389 | 0.098 |
| R1 (mediana) | 0.297 | 0.413 | 0.385 | 0.093 |
| R2 (dominancia) | 0.324 | 0.461 | 0.414 | 0.096 |
| **R3 (las dos)** | **0.344** | **0.516** | **0.419** | 0.097 |

- **Candidatas:** R2 y R3.
- **Queda R3,** porque R2 está a 0.0201 y la regla pide menos de 0.02.
- **Es una decisión en el límite:** R3 gana por 0.0001.

**Examen 2024** (F1 con 1 % por estación-día; decide R3 contra R0):

| δ | R0 | R1 | R2 | **R3** | Sin ataque |
|---:|---:|---:|---:|---:|---:|
| 100 % | 0.323 | 0.365 | 0.379 | **0.425** | 0.013 |
| 50 % | 0.330 | 0.344 | 0.331 | **0.347** | 0.013 |
| 20 % | 0.116 | 0.108 | 0.109 | 0.109 | 0.013 |
| 10 % | 0.038 | 0.034 | 0.037 | 0.035 | 0.013 |
| 5 % | 0.016 | 0.021 | 0.019 | 0.021 | 0.013 |

**R3 contra R0 con δ = 100 %:**
- la precisión pasa de 0.20 a 0.29 y el recall de 0.85 a 0.83;
- las falsas alarmas por contagio bajan de 598 a 36, y las de tras un ataque propio de 584 a 320;
- el 75 % de las que quedan son «resto»: el cambio de año y los días naturales raros.

**Predicciones:** se cumplieron 5 de 7.
- La 1 falló: la mediana bajó la tasa tras un ataque propio a 11.4 %, no a menos de 10 %.
- La 6 falló: con δ = 50 % en 2024, R3 llegó a 0.347, no a 0.38.

**Observaciones de Claude:**
- **La mejora está casi toda en los ataques grandes.** Con δ = 100 % sube +0.10 en 2024; con
  50 % sube +0.017; con 20 % o menos no cambia.
  - Tiene sentido: los dos sesgos que se quitaron crecen con δ.
- **La dominancia hace lo que se esperaba.** El contagio casi desaparece y cuesta poco recall:
  - las estación-días atacadas que apaga con δ chico casi nunca habrían alertado;
  - en 2022 se perdieron 5–6 alertas verdaderas con 20 %.
- **La mediana ayuda menos de lo que predije.** Con 100 % baja a la mitad las falsas alarmas tras un
  ataque, pero quedan en 11–14 %.
  - Su aporte en 2022 quedó en el límite de la regla.
  - En 2024 se ve en el mismo sentido, como contraste que no decide: R3 queda por encima de R2,
    con 0.425 contra 0.379 y 0.347 contra 0.331.
- **El problema de fondo sigue igual:** con δ ≤ 20 % la regla no detecta de forma útil, aun por
  estación-día. Lo que limita ahí es el «resto», no los dos sesgos.
- **No se compara uno a uno con la hora de red.**

**Siguiente** (decisión del tesista):
- la gráfica de la semana con la estación-día;
- la fase 3 (LSTM por estación);
- redactar.

**Commit:** 364b687, con la revisión 12.

### Revisión 13 redactada y aprobada: LSTM supervisado por estación (2026-10-24)

**Pregunta del tesista:**
- «el LSTM sigue dando el resultado que teníamos, ¿no podemos agregar las mejoras al LSTM?»;
- el modelo debe servir para los años que vienen.

**Respuesta de Claude:**
- de las tres mejoras, sólo la mediana es una entrada, y no ayudó al LSTM por hora de red
  (revisión 10);
- las otras dos, juntar el día y la dominancia, son formas de responder;
- para que el LSTM las use, tiene que responder por estación;
- las dos herramientas sirven para años futuros: la regla, recalibrando su umbral cada año; el
  LSTM, aplicado tal cual. Lo dirá el examen final de 2025–2026, que sigue sin tocarse.

**Diseño,** en el protocolo (revisión 13):
- **El modelo:** el LSTM de la revisión 8 con 31 salidas, etiqueta por estación-hora, y el día
  juntado como en R3.
- **Paso 1, con 2022:** se elige la configuración del LSTM entre las entradas (media o mediana) y
  con o sin dominancia. Son 2 entrenamientos × 2 lecturas.
- **Paso 2:** sólo pasa a 2024 si le gana a R3 por 0.02 o más en 2022.
- **El umbral de 2022 sale de 2022 limpio,** no de 2021, porque el LSTM se entrena con 2021. R3 se
  recalcula con el mismo umbral.
- **En Colab,** con R3 recalculada en la misma sesión.
- **Hay 7 predicciones registradas.**

**Aprobación:** el tesista la aprobó tal cual el 2026-10-24, incluido el paso 2.

**Siguiente:** programarla con sus pruebas, probarla en modo
`--prueba` sin imprimir métricas, y lanzarla en Colab.

### Revisión 13 programada y lanzada en Colab (2026-10-24)

**Pregunta del tesista antes de lanzarla:** ¿vale la pena agregar más años?
- **Respuesta de Claude:**
  - el modelo definitivo ya entrena con 2020–2022;
  - 2023 a 2026 no se pueden usar para entrenar: son la calibración, el examen y el examen final;
  - el diagnóstico del 2026-10-22 mostró que más años ayudan con δ = 100 %, sin evidencia con
    20 %, y que 2020 enseña peor.
- **Recomendación:** primero la revisión 13 con 2020–2022. Más historia (por ejemplo 2017–2019)
  sería una revisión aparte, con su control.

**Hecho:**
- **El código:** el clasificador con varias salidas, las etiquetas por estación-hora, el
  entrenamiento por estación y la elección con 2022. Hay 2 pruebas nuevas, con 276 en total.
- **El modo `--prueba`** de los dos scripts corre completo, y no se miraron sus métricas.
- **Control en la lap:** la R3 recalculada por el script de la elección reproduce la revisión 12.

**Lanzamiento:**
- **Dónde:** en la sesión de Colab `rev13`, el 2026-10-24 a las 08:17 UTC.
- **La máquina:** tocó un **AMD EPYC 7B12, el mismo procesador de la revisión 8**.
- **El código:** el commit 364b687 más un tarball, con su SHA-256 verificado.
- **Cómo corre:** dos corridas en paralelo. Cada una entrena 6 modelos (media y mediana × δ = 100,
  50 y 20 %) con EarlyStopping y luego corre la elección.
- **El guion** compara las dos corridas archivo por archivo.

### Revisión 13: el LSTM por estación pierde contra la regla R3 en 2022 (2026-10-24)

**Cómo se corrió:**
- en Colab, sesión `rev13` (AMD EPYC 7B12), de 08:23 a 09:43 UTC;
- antes de entrenar se comprobó todo:
  - los zips coinciden con su SHA-256;
  - los planes y matrices salieron idénticos a los del repo;
  - pasaron las 276 pruebas;
- las dos corridas en paralelo salieron idénticas archivo por archivo;
- la R3 recalculada en la sesión reproduce la revisión 12;
- los resultados se descargaron como tarball, con el SHA-256 verificado
  (`9e535e7d…`), y la sesión se detuvo con 397.08 unidades;
- los registros están en `logs_revision13/`;
- los números vienen de modelos recién entrenados en esa sesión.

**Elección con 2022** (F1 con 1 %, umbral de 2022 limpio):

| Configuración | F̄ | δ = 100 % | δ = 50 % | δ = 20 % |
|---|---:|---:|---:|---:|
| C0 (media, sin dominancia) | **0.203** | 0.321 | 0.250 | 0.038 |
| C1 (media, con dominancia) | 0.209 | 0.336 | 0.253 | 0.039 |
| C2 (mediana, sin dominancia) | 0.212 | 0.354 | 0.244 | 0.038 |
| C3 (mediana, con dominancia) | 0.219 | 0.382 | 0.240 | 0.035 |
| R3 (regla robusta) | **0.330** | 0.484 | 0.404 | 0.102 |

- **Paso 1:** queda C0. La mejor, C3, le gana por 0.016, y hacía falta 0.02.
- **Paso 2:** C0 queda 0.127 por debajo de R3. **No pasa.** La revisión 13 se cierra sin examinar
  2024, y R3 sigue como detector por estación-día.
- **Predicciones:** de las 5 que se podían evaluar, se cumplieron 3 (la 1, la 2 y la 3).
  - Fallaron la 4 y la 5: predije que el LSTM le ganaría a R3.
  - La 6 y la 7 eran de 2024.

**Un hueco del diagnóstico:**
- el diseño pedía la peor hora como contraste, y el script no la calculó;
- se calculó después en la lap con los puntajes guardados, sin cargar modelos
  (`exploracion_revision13_2022.py`);
- con 1 % da 0.342, 0.246 y 0.041 con la media, y 0.374, 0.249 y 0.041 con la mediana;
- no cambia nada.

**Observaciones de Claude** (lectura de los resultados; no deciden):
- **No es un umbral desafortunado.** El PR-AUC, que no depende del umbral, también es peor:
  - con 100 %, 0.49 contra 0.67;
  - con 50 %, 0.18 contra 0.34.
- **El LSTM localiza peor que la regla.**
  - La dominancia apaga 164 de 770 estación-días atacadas con 100 %; en R3 eran 47–52.
  - O sea, con frecuencia el LSTM le da más puntaje a una vecina que a la estación atacada.
- **Las falsas alarmas que más pesan son «resto»,** lejos de cualquier ataque.
  - En los calendarios atacados, su tasa es de 1.51 % con el LSTM y de 1.00 % con R3.
  - **Hipótesis, sin verificar:** el LSTM ve las 32 estaciones a la vez, así que un ataque en
    cualquier parte de la red mueve un poco las salidas de las demás. La regla sólo mira a 4
    vecinas.
- **Aprende y memoriza muy rápido.**
  - La mejor época fue la 1 en los seis modelos; desde la 2, la pérdida en 2022 sube (con 100 %,
    de 0.026 a 0.043).
  - Con 20 calendarios de 2020–2021, el modelo se aprende esos ataques en concreto, más que una
    regla que sirva para otro año. Pasó igual en la revisión 8.
- **Lo que significa para la tesis:** es un resultado negativo claro y reportable. Con estos datos,
  un LSTM supervisado por estación no supera a una regla física sin entrenamiento, que compara cada
  estación con sus vecinas. Las mejoras de las revisiones 11 y 12 ayudan más que el aprendizaje.

**Siguiente** (decisión del tesista):
- la gráfica de la semana con la estación-día (R0 → R3, y el V4);
- redactar;
- otras opciones, que serían revisiones aparte:
  - más historia (2017–2019);
  - el examen final de 2025–2026 con R3.

**Sin commit todavía.**

### ¿Correr el LSTM por estación en 2024 de todos modos? Opción C (2026-10-24)

**Pregunta del tesista:** «¿no crees que valga la pena entrenarlo?», pues no estamos seguros de que
en verdad no mejore.

**Respuesta de Claude:**
- **Sí se entrenó:** 6 modelos en Colab. Lo que no se hizo fue el modelo definitivo y el examen
  2024.
- **No decidió la predicción, decidió el resultado.** De hecho, la predicción decía que le ganaría a
  R3, y falló.
- **Correrlo en 2024 por haber perdido en 2022** convertiría al examen en otra elección. Además, la
  distancia (−0.127) es de seis veces el margen.
- **Tres opciones:**
  - A, cerrarla;
  - B, 2024 como contraste que no decide;
  - C, una revisión nueva que ataque las causas.
- **Recomendación:** C antes que B, si se quiere darle al LSTM una oportunidad seria, y que sea el
  último intento con 2022.

**Decisión del tesista:** la opción C.

**Exploración** (después de ver la revisión 13 en 2022; con sus puntajes guardados, sin cargar
modelos):
- Se tomaron las falsas alarmas del grupo «resto», con 1 %, y se separaron según si ese día había
  algún objetivo atacado en la red.
- Script: `experiments/anomalias_red/exploracion_revision13_2022.py`, que también calcula la peor
  hora. Corrió dos veces, con el mismo resultado.

| δ | Detector | Resto, día sin ataques en la red | Resto, día con un ataque lejano |
|---:|---|---:|---:|
| 100 % | LSTM C0 | 1.24 % (881 de 71 317) | **2.66 %** (456 de 17 115) |
| 100 % | R3 | 1.00 % | 0.98 % |
| 50 % | LSTM C0 | 1.01 % | 1.44 % |
| 50 % | R3 | 1.00 % | 1.05 % |

- **Se confirma la hipótesis de la revisión 13:** un ataque en cualquier parte de la red le sube las
  falsas alarmas a las estaciones lejanas, porque cada salida del LSTM ve las 32 estaciones. A R3
  no le pasa.

**Revisión 14 redactada** en el protocolo: LSTM local compartido.
- **El modelo:** uno solo, que mira la estación y sus 4 vecinas, 17 columnas por hora, y se aplica a
  las 31.
- **Las configuraciones:** con 20 o con 60 calendarios, a igual número de ventanas por época, y con
  o sin dominancia.
- **Los pasos 1 y 2:** como en la revisión 13.
- **Es el último intento con 2022 para esta línea.**
- **Hay 6 predicciones registradas.** La 6 dice que no pasa el paso 2, aunque se acerca a R3.

**Aprobación:** el tesista la aprobó tal cual el 2026-10-24: «Sí, lo apruebo, hazlo, y si requieres
entrenar algo mándalo a Colab».

### Revisión 14 programada y lanzada en Colab (2026-10-24)

**Hecho en la lap:**
- **El código:** las columnas locales, la muestra de ventanas, el entrenamiento local y la
  elección. Hay 3 pruebas nuevas, con 279 en total.
- **Los calendarios 21–60:** 40 planes y 200 matrices, con `--ampliados`. Los 20 de siempre y sus
  resúmenes no cambiaron.
- **El modo `--prueba`** de los dos scripts corre completo, y no se miraron sus métricas.

**Lanzamiento:**
- **Dónde:** en la sesión de Colab `rev14`, el 2026-10-24 a las 21:20 UTC.
- **La máquina:** tocó un Intel Xeon @ 2.20 GHz. No afecta la elección, que compara todo dentro de
  la sesión.
- **El código:** el commit 364b687 más un tarball, con su SHA-256 verificado. El tarball incluye los
  planes nuevos y los puntajes de 2022 de la revisión 13 para el contraste.
- **Cómo corre:**
  - Colab regenera los planes y las matrices nuevas, y debe dar los mismos SHA-256 que la lap;
  - dos corridas en paralelo, cada una con 6 modelos (20 y 60 calendarios × δ = 100, 50 y 20 %);
  - después corre la elección, y el guion compara las dos corridas archivo por archivo.

**Vista preliminar** (a pedido del tesista, 2026-10-25 02:45 UTC, con 5 de 6 modelos terminados):
- **Qué es:** los puntajes de 2022 de la primera corrida, descargados y medidos en la lap con el
  mismo esquema que la elección. No decide nada, y la regla ya estaba fijada.
- **F1 con 1 %:**
  - L0: 0.508, 0.472 y 0.193 con δ = 100, 50 y 20 %;
  - R3: 0.484, 0.404 y 0.102, iguales a los de la revisión 13.
  - Con 60 calendarios, L2 da 0.487 y 0.470 con 100 y 50 %; faltaba su δ = 20 %.
- **La decisión es la de la elección completa en Colab.**

### Revisión 14: el LSTM local le gana a R3 en 2022 y pasa a 2024 (2026-10-25)

**Cómo se corrió:**
- en Colab, sesión `rev14` (Intel Xeon @ 2.20 GHz), de 21:39 a 03:35 UTC;
- las dos corridas en paralelo salieron idénticas archivo por archivo;
- R3 reproduce la revisión 12, y los calendarios nuevos son iguales a los de la lap;
- los resultados se descargaron con el SHA-256 verificado (`f37f0a5b…`);
- los registros están en `logs_revision14/`;
- los números vienen de modelos recién entrenados en esa sesión.

**Elección con 2022** (F1 con 1 %, umbral de 2022 limpio):

| Configuración | F̄ | δ = 100 % | δ = 50 % | δ = 20 % |
|---|---:|---:|---:|---:|
| **L0 (local, 20 calendarios)** | **0.391** | 0.508 | 0.472 | 0.193 |
| L1 (L0 con dominancia) | 0.398 | 0.515 | 0.479 | 0.198 |
| L2 (local, 60 calendarios) | 0.394 | 0.487 | 0.470 | 0.225 |
| L3 (L2 con dominancia) | 0.398 | 0.491 | 0.474 | 0.228 |
| R3 (regla) | 0.330 | 0.484 | 0.404 | 0.102 |
| C0 de la revisión 13 | 0.203 | 0.321 | 0.250 | 0.038 |

- **Paso 1:** queda L0, porque ninguna otra le gana por 0.02.
- **Paso 2:** L0 le gana a R3 por **0.061**. **Pasa a 2024.**
- **Predicciones:** se cumplieron 4 de 6. Fallaron la 5 (E) y la 6: predije que no pasaría.

**Observaciones de Claude:**
- **El modelo local corrigió las dos causas que se vieron en la revisión 13:**
  - el contagio lejano bajó de 2.66 % a 1.15 %;
  - la dominancia ya casi no le apaga estación-días atacadas: 25 contra 164.
- **Su ventaja es sobre todo de recall:** encuentra más estación-días atacadas con la misma precisión.
  Con 100 % es 0.96 contra 0.83, y con 50 % es 0.79 contra 0.59.
- **Lo que queda débil son los 14 días después de un ataque propio:** 18 % de falsas alarmas, contra
  13 % de R3. Usa las relativas a la media, que se contaminan.
- **Los 60 calendarios no ayudaron,** a igual número de ventanas: memorizar los ataques no era el
  problema.
- **Cautela:** 2022 se ha usado mucho para elegir. La prueba de verdad es 2024.

**Colab:** la sesión `rev14` sigue abierta, a 0.26 unidades por hora (395 de saldo), por si el
tesista aprueba el examen 2024 en la misma máquina.

**Siguiente:** confirmar con el tesista el examen 2024.
- Antes hay que programar la evaluación por estación-día del LSTM local.
- Luego, en Colab: los 5 δ con `--definitivo`, que llevan su etapa de selección; para δ = 10 y 5 %
  es nueva.

### Examen 2024 de la revisión 14: aprobado y lanzado (2026-10-25)

**Pregunta del tesista antes de aprobarlo:** qué es L0 y qué mira.
- **Respuesta:**
  - un LSTM que, para cada estación, ve 24 horas de ella y de sus 4 vecinas, con 3 datos de cada
    una más la hora;
  - responde sólo sobre la estación del centro, y se aplica 31 veces;
  - el «qué tanto se aparta» es su desviación de lo normal menos la de sus vecinas, no una
    distancia; la distancia sólo escoge a las vecinas.

**Aprobación:** «Va, lánzalo en Colab el examen 2024».

**Hecho:**
- `evaluar_lstm_local_2024.py`, probado en modo `--prueba` sin mirar métricas;
- 5 predicciones registradas en el protocolo antes de correrlo;
- lanzado en la sesión `rev14`, la misma de la elección: dos corridas en paralelo con los cinco δ.

**Guiones de Colab en el repo:** los que se corrieron estaban sólo en el scratchpad de la sesión. Ya
quedan en `experiments/anomalias_red/` como copias exactas:
- `correr_revision13.sh`, la elección de la revisión 13;
- `correr_revision14.sh`, la elección de la revisión 14;
- `correr_revision14_examen.sh`, el examen 2024.

### Examen 2024 de la revisión 14: resultado (2026-10-25)

**Cómo se corrió:**
- en Colab, sesión `rev14` (Intel Xeon), de 04:15 a 11:59 UTC;
- las dos corridas salieron idénticas, y la selección repite la de la elección;
- R3 reproduce la revisión 12;
- se descargó con el SHA-256 verificado (`67edf2fe…`) y la sesión se detuvo, con 393.27 unidades;
- los registros están en `logs_revision14/`;
- los números vienen de modelos definitivos recién entrenados.

**F1 con 1 % por estación-día en 2024** (estación-días comunes; umbral de 2023 limpio):

| δ | L0 | R3 | L0 − R3 | V4 |
|---:|---:|---:|---:|---:|
| 100 % | **0.427** | 0.425 | +0.002 | 0.206 |
| 50 % | **0.388** | 0.347 | +0.042 | 0.102 |
| 20 % | **0.158** | 0.109 | +0.049 | 0.029 |
| 10 % | 0.038 | 0.035 | +0.004 | 0.018 |
| 5 % | 0.008 | 0.021 | −0.013 | 0.014 |

- **Lectura:**
  - con 100 % empatan;
  - con 50 y 20 %, L0 gana: encuentra más estación-días atacadas, con una precisión igual o
    mejor;
  - con 10 y 5 % ninguno sirve, porque quedan en el azar.
- **La ventaja promedio** (100, 50 y 20 %) es de +0.031, la mitad de la de 2022 (+0.061).
- **El PR-AUC dice lo mismo:** 0.85 y 0.69, 0.58 y 0.41, 0.083 y 0.046.
- **La debilidad de L0:** las falsas alarmas en los 14 días tras un ataque propio. Con 100 % su
  tasa es de 22.7 %, contra 13.6 % de R3.
- **Predicciones de Claude:** se cumplieron las 5.

**Lo que falta antes de concluir** (lista del 2026-10-25, pendiente de decidir con el tesista y el
asesor):
- intervalos de confianza;
- semillas;
- la prueba con hora de inicio al azar de la revisión 6;
- el modelo de un δ examinado con los demás;
- P4 (bit flipping por los detectores de red);
- el examen único de 2025–2026.

**Exploración: ¿se puede subir la precisión?** (2026-10-25, a pedido del tesista; no decide nada)
- **Qué se hizo:** precisión y recall de L0 y R3 con umbrales más estrictos que el 1 %, con 2022 y no
  con 2024, para no ajustar nada mirando el examen.
- **Script:** `exploracion_precision_umbral_2022.py`. Usa los puntajes guardados y no carga modelos.
- **Con δ = 100 %:**
  - L0 pasa de precisión 0.35 y recall 0.96 con 1 % a precisión 0.81 y recall 0.74 con 0.1 %
    (F1 0.77);
  - R3, con 0.1 %, da precisión 0.76 y recall 0.44.
- **Con δ = 50 % y 0.1 %:** L0 da precisión 0.64 y recall 0.22.
- **Lectura:**
  - la precisión baja con 1 % viene de la proporción de días atacados (0.8 %), no de un defecto
    del detector;
  - cambiar el punto de operación sería una decisión nueva: habría que registrarla antes y
    probarla en 2025–2026.

### Revisión 15 registrada: dos puntos de operación, p99 y p99.9 (2026-10-25)

**Lo que entendió el tesista:**
- la precisión baja viene de la rareza de los ataques;
- un umbral más estricto (p99.9) pierde recall y gana precisión.

**Precisiones de Claude:**
- con p99.9 el detector es el mismo, sólo cambia el umbral;
- no siempre conviene: con δ = 50 % el recall cae mucho;
- el p99.9 se estima con ~10 días de 2023, así que es inestable.

**El orden acordado** (paso 1 aprobado: «Sí, haz paso 1»):
1. la revisión 15: p99 y p99.9 y la curva en 2024, sólo descriptivos;
2. las comprobaciones pendientes: intervalos, hora de inicio al azar, el modelo de un δ con los demás;
3. revisarlo con el asesor, incluido P4;
4. el protocolo del examen final, congelado;
5. el examen final 2025–2026, una sola vez;
6. redactar.

**Registro:** la revisión 15 quedó en el protocolo, con 5 predicciones, antes de calcular p99.9 en
2024.

### Revisión 15: resultado (2026-10-25)

**Cómo se corrió:**
- `puntos_operacion_2024.py`, en la lap, dos veces, con salidas idénticas;
- con 1 y 5 %, L0 y R3 reproducen el examen de la revisión 14, y el V4 la revisión 11;
- no se entrenó nada: L0 son los puntajes de su modelo definitivo, el V4 se cargó de disco y R3 es
  aritmética.

**Con δ = 100 %:**

| Punto | Detector | Recall | Precisión | F1 | Falsas alarmas en la red, por año |
|---|---|---:|---:|---:|---:|
| p99 | L0 | 0.944 | 0.276 | 0.427 | ~174 |
| p99 | R3 | 0.826 | 0.286 | 0.425 | ~144 |
| p99.9 | **L0** | **0.792** | 0.689 | **0.737** | ~25 |
| p99.9 | R3 | 0.559 | **0.802** | 0.659 | ~10 |
| p99.9 | V4 | 0.437 | 0.304 | 0.359 | ~71 |

**Con δ = 50 % y p99.9:**
- L0: recall 0.41, precisión 0.75, F1 0.531;
- R3: recall 0.22, precisión 0.77, F1 0.339.

**Con δ ≤ 20 % y p99.9,** casi nada se detecta.

**Predicciones de Claude:** se cumplieron 3 de 5.
- Falló la 1: el p99.9 de 2023 dio menos falsas alarmas de lo esperado en 2024 limpio, en R3 y en
  L0 con 50 y 20 %.
- Falló la 4: con 50 %, el recall de L0 fue de 0.41, no menor de 0.35.

**Lectura de Claude:**
- con el umbral estricto, la ventaja de L0 se agranda;
- con la misma precisión, L0 encuentra bastante más;
- es descriptivo: la prueba es el examen final.

### Revisión 16 registrada: las tres comprobaciones (2026-10-25)

**Explicación al tesista, antes de aprobarla:**
- **los intervalos** responden «¿la diferencia es real o suerte del sorteo?»;
- **la hora al azar** responde «¿L0 detecta ataques o el inicio a medianoche del simulador?». Se
  registró en la revisión 6 y nunca se corrió;
- **el modelo único** responde «¿sirve si no se sabe el tamaño del ataque?».

**Aprobación:** «Ya entendí, sí, hazlos, tanto para el p99 y p99.9».

**Registro:** quedó en el protocolo, con sus reglas y 9 predicciones, antes de correr nada. Sólo
(2a) elige algo: el modelo único para el examen final, con 2022.

**Cómo se está corriendo:**
- **(1) Intervalos:** en la lap, dos veces, idénticos. El control reproduce el examen de la
  revisión 14.
- **(2) y (3): pasaron a Colab a pedido del tesista,** para no tener la lap al 100 %.
  - Es la sesión `rev16`, con un AMD EPYC 7B12, lanzada a las 19:13 UTC con `correr_revision16.sh`.
  - La primera corrida de (2) en la lap se detuvo a la mitad. Ya había hecho la elección con 2022
    (modelo único: δ = 50 %, F1 medio 0.359 contra 0.346 del de 100 %) y su control de la
    diagonal salió bien.
  - Colab repite todo desde cero, dos veces.
  - **(2) en Colab:** dos corridas idénticas. El control de la diagonal reproduce la elección de la
    revisión 14 y su examen 2024 (diferencia máxima de puntajes 1.1e-16).
  - **(3) falló la primera vez en Colab:** los residuos guardados del V4 (`calibracion_2023` y
    `predicciones_202x`) están en `.gitignore` y no estaban en el clon.
    - Se subieron aparte (`v4_residuos.tgz`), y (3) se relanzó a las 21:23 UTC con `todo_b.sh`,
      anexado a `correr_revision16.sh`.
    - Las 50 matrices de hora al azar ya se habían generado; las dos corridas nuevas comprueban que
      salen iguales.
  - **(3) se detuvo otra vez, en el control del V4.** Su inferencia de 2024 limpio en el AMD de
    Colab difiere de las predicciones guardadas en hasta 7.6e-6 ppb, y la tolerancia del control
    era 1e-9 ppb.
    - Es la precisión float32 de otra CPU, seis órdenes de magnitud por debajo de los residuos
      (~10 ppb). En la lap el control da 1.4e-14.
    - Se agregó a `hora_azar_2024.py` la opción `--tolerancia-v4`; por omisión sigue en 1e-9. Se
      corrió con 1e-4 ppb a las 21:28 UTC (`todo_c.sh`), y la tolerancia queda en su
      `configuracion.json`.
    - **Aplica también al examen final** si el V4 corre en Colab.

### Paso 4 en curso: el protocolo del examen final (2026-10-25)

**Decisión del tesista:** correr los pasos 4 y 5 hoy, domingo, antes de la revisión con el asesor
del lunes, para llegar con resultados fijos.
- P4 no aplica: la parte 2 es otra pregunta.
- Se quedan los dos umbrales, p99 y p99.9.
- Entra la hora al azar como prueba secundaria.

**El modelo único:** el tesista prefiere el de δ = 50 %. El de 100 % estaría «ciego» con ataques
menores, y la meta es mejorar con δ = 20 %.
- **Se verificó en el protocolo:** la revisión 8 dice que δ = 20 % «es la zona donde se busca
  mejorar», y el §1 busca empujar el límite de detección de lo evidente a lo sutil.
- **La regla de la revisión 16, con 2022, ya eligió el de 50 %:** F1 medio de 0.359 contra 0.346
  del de 100 %, en la corrida detenida en la lap. Colab la repite.
- **Matiz de Claude:**
  - lo de «ciego» no está demostrado: en la revisión 8, el modelo de 100 % generalizaba hacia abajo
    mejor que los específicos;
  - la diferencia en 2022 es chica;
  - lo que importa es que lo decidió la regla con 2022 y no cambia con lo que salga en 2024.

**Revisión 16, resultado de (3) hora al azar** (Colab, dos corridas idénticas; 2024, p99):
- L0: 0.427 → 0.433, 0.388 → 0.396 y 0.158 → 0.162 con δ = 100, 50 y 20 %;
- R3: 0.425 → 0.419, 0.347 → 0.329 y 0.109 → 0.099;
- **L0 no aprendió el salto de medianoche.** Las predicciones de la revisión 16 se cumplieron 6 de
  9; el detalle está en el protocolo.
- Los resultados se descargaron con el SHA-256 verificado (`27d63213…`); los registros están en
  `logs_revision16/`.

**Revisión 17:** aprobada por el tesista el 2026-10-25 («Sí, apruebo»), con sus 9 predicciones
registradas antes de generar nada de 2025–2026. Se lanza en Colab al terminar la hora al azar.

**Examen final (revisión 17): resultado** (Colab, 22:17–23:57 UTC; dos corridas idénticas; todos los
controles pasan; 9 de 9 predicciones). F1 con p99, L0 / R3:
- **2025:** 0.457 / 0.475 con 100 %, **0.445 / 0.391** con 50 %, **0.249 / 0.120** con 20 %;
- **2026:** 0.540 / 0.476, **0.502 / 0.390**, **0.242 / 0.092**;
- **con p99.9 y 2025:** 0.756 / 0.632, 0.573 / 0.364 y 0.087 / 0.019;
- **intervalos con los dos años juntos:** L0 gana con 50 y 20 % (p99) y con 100, 50 y 20 % (p99.9);
  con 100 % y p99, empate;
- **el L0 único** pierde un poco con 100 % (−0.054) y gana con 50 y 20 %;
- **la hora al azar** no mueve a L0;
- **el detalle** está en el protocolo (revisión 17) y en `results/anomalias_red_v1/examen_final/`.

**Material para la junta del 2026-10-26:**
- el documento de notas, https://claude.ai/artifact/S7pPvKFDauKTC212ZCv9Td, lleno con lo
  verificado;
- la presentación, https://claude.ai/artifact/NyW3oYBXCGyHjmqJjhgMmT, con 18 diapositivas;
- quedan pendientes las tablas y gráficas del examen final.

**Pregunta del tesista: ¿cuánto mueve un ataque de δ = 20 %?** (descriptivo; con las matrices de
2024 y 2024 limpio, sin detectores)
- **Por lectura:**
  - con signo +, ×1.2: +6.6 ppb en promedio, con mediana de +5;
  - con signo −, ÷1.2: −5.7 ppb, con mediana de −5;
  - el nivel medio de las lecturas alteradas es de ~34 ppb;
  - el 10.8 % de las lecturas no cambia por el redondeo a ppb enteros.
- **Por hora:** de 2–3 ppb de noche a ~13 ppb a las 13–14 h.
- **Por estación-día atacada:** el promedio del día se mueve +6.6 ppb (p10–p90: 3.2 a 10.7) o
  −5.7 ppb (−9.1 a −2.8).
- **Variabilidad natural** en 2024 limpio, con el promedio del día menos la mediana de los 14 días
  anteriores:
  - sola, 5.5 ppb de mediana y 14.5 en el p90;
  - menos la de sus 4 vecinas, 2.5 ppb de mediana y 7.9 en el p90.
- **Lectura:**
  - un ataque de 20 % mueve el día lo mismo que un día normal raro;
  - comparar con las vecinas reduce el ruido a la mitad, y por eso se detecta algo;
  - es lo que plantea la hipótesis del §1.

**Comparación con la parte 1: ¿se empujó el límite?** (2026-10-25, a pedido del tesista;
descriptiva)
- **Script:** `comparacion_parte1_2024.py`.
- **Qué se compara:** el recall con la misma tasa nominal de falsas alarmas (p95 de 2023), en 2024,
  ordenado por el tamaño del cambio en ppb. Se usó recall y no F1, porque la proporción de ataques
  es distinta: 5 % de lecturas contra 0.8 % de estación-días.
- **Parte 1:** el V4 por lectura, grupo principal, con 7.0 % de falsas alarmas en 2024.
  - bit 3 (8 ppb): 10.1 %;
  - bit 4 (16 ppb): 20.9 %;
  - bit 5 (32 ppb): 78.7 %;
  - bit 6 (64 ppb): 99.5 %;
  - la frontera está entre los bits 4 y 5, como ya se había anotado.
- **Parte 2,** por estación-día, recall de L0 / R3 / V4:
  - δ = 10 % (~3.2 ppb): 20.4 / 17.1 / 12.7 %;
  - δ = 20 % (~6.2 ppb): 53.9 / 37.7 / 18.0 %;
  - δ = 50 % (~14.3 ppb): 92.7 / 75.5 / 44.8 %;
  - δ = 100 % (~25.5 ppb): 97.4 / 89.3 / 69.9 %;
  - las falsas alarmas reales son de ~6–7 % para L0 y R3, y de ~10 % para el V4.
- **Lectura:**
  - el ~50 % de recall pasa de entre 16 y 32 ppb (parte 1) a ~6 ppb (L0);
  - L0 con δ = 10 % (~3 ppb) supera al azar lo mismo que el V4 con el bit 4 (16 ppb): +14 puntos;
  - el mismo V4 juntado por día ya mejora, y las vecinas con el LSTM local agregan el resto.
- **No es controlada:** cambian la unidad, la duración, la forma y la información.

**Exploración: ¿dónde detecta L0 y dónde no?** (2026-10-25, a pedido del tesista; 2024, p99;
`exploracion_sesgos_2024.py`)

Recall de L0 / R3:

| | δ = 100 % | δ = 50 % | δ = 20 % |
|---|---|---|---|
| Signo + (sube) | 98.7 / 95.1 | 86.0 / 74.4 | 24.8 / 20.5 |
| Signo − (baja) | 89.7 / 68.5 | 73.0 / 44.5 | 13.0 / 10.0 |
| Episodio de 1 día | 93.1 / 82.8 | **65.5 / 72.4** | **13.8 / 24.1** |
| 2–3 días | 97.4 / 86.0 | 80.7 / 62.3 | 18.4 / 16.7 |
| 4–7 días | 93.9 / 81.9 | 80.5 / 59.3 | 19.7 / 14.9 |

- **La ventaja de L0 está en los episodios de varios días.** Con episodios de un solo día, R3 es
  mejor con δ = 50 y 20 %.
  - Parece que L0 aprovecha la persistencia que aprendió del simulador: episodios de 1 a 7 días,
    y su ventana de 24 horas.
- **Bajar la lectura se detecta peor que subirla,** y ahí es donde L0 más le gana a R3 (73 contra
  44 % con 50 %). Según Turiel y Kaufmann, bajar es la manipulación realista.
- **Por estación,** con δ = 50 %, el recall de L0 va de 43 % (LPR) a 100 %, con mediana de 85 %.
  Baja un poco con la distancia a las vecinas: Spearman de −0.15 a −0.37.

**Sin commit todavía.**

## 2026-10-26 — Junta con el asesor: comparaciones justas («peras con peras»)

**Fuente:** una transcripción automática con mucho ruido (los primeros minutos son otra plática) y
lo que el tesista aclaró después. Lo marcado como «interpretación» se confirmó con el tesista el
2026-10-27.

### Lo que el asesor aceptó

- **Las dos tablas del examen final (p99 y p99.9) se quedan como están:** «ya son resultados
  correctos», con los mismos calendarios para todos.
- **Se quedan los dos umbrales.** La elección depende del usuario: si puede verificar las falsas
  alarmas, p99; si no, p99.9.
- **«No está truqueado»** y «no están tan malos los resultados». Lo más importante es seguir
  avanzando.

### Lo que pidió

| # | Pedido | Estado |
|---|---|---|
| A1 | Mostrar siempre las diapositivas desde el inicio de la junta | Regla para las próximas juntas |
| A2 | Renombrar L0 como «LSTM + reglas»: usa los cálculos de la regla como datos | Paso 2 |
| A3 | Quitar la comparación contra el bit flipping por ppb: lectura contra día, instante contra ataque sostenido, y la media esconde la forma (+100 % convierte 50 en 100, pero 2 en 4) | Paso 2; la sustituye la gráfica de la revisión 18 |
| A4 | Comparar supervisado contra supervisado: L0 contra un V4 con etiquetas | Revisiones 18 y 18b (paso 1) |
| A5 | Escalón de complejidad: primero una sola estación atacada a la vez; muchas estaciones a la vez, al final | Paso 3 |
| A6 | Error fijo en ppb (±10, ±20) en lugar de porcentual: «un sensor se equivoca por una cantidad» | Paso 5, después de lo demás |
| A7 | PARAAD (el grupo de Barcelona) en la misma tabla y en el mismo escenario | Paso 4, de importancia alta |
| A8 | Probar TINTO (tabular → imagen; Castillo-Cara, Talla-Chumpitaz, García-Castro y Orozco-Barbosa, 2023), la idea M-6 del 2026-10-19 | Aparte, en otro chat o con Codex: `docs/inicio_exploracion_tinto.md` |

**Una corrección de Claude:** primero interpretó «tinto» como un color de la gráfica, con el
supuesto de un detector supervisado con sólo la propia estación. El tesista aclaró que era TINTO. Esa
interpretación se descartó.

### Aclaraciones verificadas contra el repositorio

- **¿El V4 de la parte 1 era supervisado?** No. Predice la estación con las 24 horas previas de
  las otras 32, se entrenó sólo con datos limpios, y su tensor «no contiene […] etiquetas de
  ataque» (§4.1 de su protocolo). Tenía razón el tesista.
  - Sí hubo LSTM supervisados a los que les fue mal: las revisiones 6 a 8 (por hora de red) y la
    13 (por estación, viendo toda la red). Probablemente eso recordaba el asesor.
  - El V4 tampoco «sólo se toma en cuenta a sí mismo»: usa a las otras 32 estaciones.
- **¿Cuántas veces se atacan varias estaciones a la vez?** Medido en los calendarios:
  - 2024: 873 estación-días atacadas; el 26 % tiene otra estación atacada ese día y el **4.6 %**,
    una de sus 4 vecinas; como máximo 3 a la vez;
  - 2025–2026: 1 465; 25 % y **5.1 %**; como máximo 4;
  - para L0 y R3, que sólo miran 5 estaciones, el escenario actual ya es casi siempre «una sola
    estación». Lo que sí sería más difícil son ataques coordinados a vecinas.
- **«El F1 se me hace bajo»** (con δ = 100 % y p99):
  - el techo depende de la prevalencia: con 0.7 % de estación-días atacadas y 1 % de falsas
    alarmas, un detector perfecto llega a F1 ≈ 0.59;
  - con las falsas alarmas reales de L0 en 2025 (1.6 %), el techo es ≈ 0.47 y L0 tiene 0.457
    (recall 94 %, precisión 30 %);
  - con p99.9 el techo sube a ≈ 0.93 y L0 llega a 0.756.
- **Un desliz en la junta:** «el 50 o el 20 % son 3 ppb». En realidad 20 % ≈ 6 ppb y 10 % ≈ 3 ppb.

### Decisiones del tesista (2026-10-27)

- **Orden:**
  1. V4 ajustado;
  2. lo que no entrena;
  3. una sola estación (para L0 y el V4);
  4. PARAAD;
  5. error fijo;
  6. TINTO, que después se separó a otro chat.
- **Regla «peras con peras»** para todo lo que sale de la junta (`CLAUDE.md` y revisión 18).
- **Volver a usar 2025–2026** sólo con detectores registrados antes de entrenar, una sola vez, sin
  tocar los números de la revisión 17 (revisión 18).

### Revisión 18 registrada y aprobada: comparación justa con el V4 (2026-10-27)

- **Origen:** la junta con el asesor del 2026-10-26. El registro completo de la junta es el paso 2
  del plan y va aparte.
- **Plan del tesista tras la junta:**
  1. el V4 ajustado (revisión 18);
  2. lo que no entrena: renombrar L0, retirar la gráfica contra el bit flipping y registrar la junta;
  3. una sola estación atacada a la vez, para L0 y el V4;
  4. PARAAD;
  5. error fijo en ppb;
  6. TINTO (Castillo-Cara, Talla-Chumpitaz, García-Castro y Orozco-Barbosa, SoftwareX 2023).
- **Regla del tesista («peras con peras»):** todo lo que sale de la junta compara detectores del
  mismo tipo, en el mismo escenario, con los mismos calendarios y las mismas estación-días. Lo
  demás sólo va como referencia.
- **Revisión 18** (§15 del protocolo):
  - (a) el V4 en las mismas estación-días que los demás;
  - (b) el V4 supervisado (V4S): las 66 entradas del V4 con filas t−23…t más 2 columnas de la
    propia estación, un modelo por estación, los 20 calendarios y las etiquetas de L0, sólo
    δ = 50 % como modelo único;
  - (c) una gráfica del V4S contra el L0 único, sin el V4;
  - evaluación en 2024 y una sola vez en 2025–2026, sin tocar las tablas de la revisión 17.
- **Aprobación:** el tesista aprobó el 2026-10-27 las dos decisiones (sólo δ = 50 % y un modelo
  por estación) y cambió la gráfica: V4S en lugar de V4. Se registró **antes** de programar o
  entrenar nada.

### Revisión 18: V4S entrenado y comprobación con 2022 (2026-10-27)

- **Entrenamiento:**
  - en Colab, sesión rev18, AMD EPYC 7B12, con `correr_revision18.sh`;
  - las 31 estaciones en 3 procesos, en 31 minutos;
  - modelos **recién entrenados**, en `results/anomalias_red_v1/v4_supervisado/d50/`;
  - el SHA-256 de cada modelo coincide al bajarlos a la lap.
- **Control:** la selección de ACO entrenada dos veces da la misma historia y los mismos pesos.
- **Épocas:** 11 de 31 estaciones eligieron E = 1, es decir, la pérdida de 2022 ya no mejora
  después de la primera época (`epocas.csv`).
- **Comprobación de funcionamiento con 2022** (`comprobacion_v4s_2022.py`; no elige nada; no mira
  2023–2026):
  - se usaron los modelos de **selección**, cargados de disco, sobre todas las horas de 2022 de los
    calendarios 01–10 con δ = 50 %;
  - **por hora:** ROC-AUC de 0.626 con todas las estaciones juntas;
  - **por estación:** de 0.418 (AJU) a 0.816 (UAX). Las 11 con E = 1 promedian 0.505, es decir, no
    aprendieron; las otras 20 promedian 0.631;
  - **por estación-día, en las mismas estación-días:** ROC-AUC de 0.648 del V4S contra 0.976 de L0;
    PR-AUC de 0.122 contra 0.474, con azar de 0.008.
- **No es un error del código:**
  - las estaciones que entrenaron varias épocas sí separan (BJU, FAC, UAX y VIF, de 0.77 a 0.82);
  - en PED el modelo aprendió sólo los ataques que suben la lectura: ROC-AUC de 0.841 con signo +
    y de 0.297 con signo −;
  - los AUC menores de 0.5 en estaciones con E = 1 caben en el ruido: son pocos episodios, con
    horas muy correlacionadas.
- **Causa probable:** la desventaja declarada antes de entrenar. Cada modelo ve sólo los ataques de
  su estación, unas 300 ventanas atacadas, y deja de mejorar casi de inmediato. L0, compartido, ve
  31 veces más.
- **Estado:** la evaluación (2024 y 2025–2026) **no se ha corrido**. Se espera la decisión del
  tesista, porque el examen 2025–2026 es de un solo uso.

### Revisión 18b registrada, aprobada y lanzada: V4S compartido (2026-10-27)

- **La duda del tesista:** «no sé cómo hacerlo sin que se vea truqueado, para que al final L0 salga
  victorioso». También preguntó por qué el V4 original no se hizo así.
- **Respuesta de Claude:**
  - la debilidad se declaró antes de entrenar y 2022 sólo la confirmó;
  - no se ha visto 2024–2026 para ningún V4S;
  - el cambio fortalece al rival de L0;
  - **no hay elección:** los dos V4S van al examen.
- **Por qué el V4 era por estación:** era un pronosticador sin etiquetas, con unas 14 000 horas
  normales por estación. La escasez de ejemplos atacados aparece sólo al supervisar.
- **Aprobación:** el tesista aprobó el 2026-10-27 («Va. Hazlo»). Se registró como la revisión 18b
  del protocolo **antes** de programar el compartido, con 3 predicciones más.
- **Código:**
  - `v4_supervisado.orden_por_distancia` y `tensores(..., orden=)`;
  - `entrenar_v4_supervisado.py --compartido`, que cuenta primero y llena arreglos del tamaño exacto
    para no duplicar memoria;
  - `evaluar_revision18.py`, con los cinco detectores;
  - pruebas: 5 de 5.
- **Colab:**
  - la sesión rev18 se cerró sola por inactividad mientras se esperaba la decisión. No se perdió
    nada: los modelos ya estaban en la lap;
  - sesión nueva rev18b con `correr_revision18b.sh`, que prepara todo y entrena el compartido dos
    veces completo, en paralelo.

### Revisión 18b: V4S compartido entrenado y comprobación con 2022 (2026-10-27)

- **Entrenamiento:**
  - en Colab, en 47 minutos;
  - 1 033 120 ventanas de 2020–2021 (0.81 % atacadas), 281 570 de 2022 y 1 596 620 en el
    definitivo;
  - **E = 3** de 11 épocas: desde la época 4 la pérdida de 2022 sube mientras la de entrenamiento
    sigue bajando;
  - modelo **recién entrenado**, en `results/anomalias_red_v1/v4_supervisado_compartido/d50/`, con
    su SHA-256 verificado en la lap.
- **Control:**
  - la segunda corrida en paralelo se quedó sin memoria (código 137) al armar el definitivo, porque
    eran dos procesos de unos 25 GB cada uno;
  - antes de eso, su selección salió idéntica a la principal, época por época;
  - se relanzó sola (`correr_revision18b_control.sh`), con los mismos hilos, para comparar también
    el definitivo;
  - **resultado:** historia de selección, historia del definitivo y pesos del definitivo
    **idénticos** a los de la corrida principal.
- **Evaluación lanzada:** 2026-10-27, 13:26 UTC, con `correr_revision18_eval.sh` en la sesión
  rev18b, dos veces en paralelo. El SHA-256 de `evaluar_revision18.py` coincide con el de la lap.
  - Los umbrales de 2023 en sus propias estación-días reproducen los de la revisión 17: L0 único
    0.1063 / 0.461, R3 1.3776 / 2.5593 y V4 0.7372 / 0.9464.

### Revisiones 18 y 18b: resultado del examen del V4S (2026-10-27)

- **Corrida:**
  - 2 h 7 min en Colab, dos veces en paralelo, con todos los archivos idénticos;
  - el control contra la revisión 17 es verdadero: L0 único, R3 y V4 en sus propias estación-días
    dan los mismos TP, FP, FN y TN;
  - 2025–2026 queda usado una vez para los V4S;
  - resultados en `results/anomalias_red_v1/revision18/` y registros en `logs_revision18/`.
- **Origen:**
  - V4S por estación y compartido, recién entrenados (revisiones 18 y 18b) y cargados de disco;
  - L0 único y V4, cargados de disco;
  - R3, sin entrenamiento.
- **Peras con peras: L0 único contra V4S compartido,** F1 con 2025 y 2026 juntos e intervalo del
  95 %:

  | δ | p99 | p99.9 |
  |---|---|---|
  | 100 % | 0.421 vs 0.352: **+0.069** (+0.014 a +0.128) | 0.600 vs 0.354: **+0.246** (+0.189 a +0.303) |
  | 50 % | 0.466 vs 0.225: **+0.241** (+0.183 a +0.302) | 0.569 vs 0.115: **+0.454** (+0.397 a +0.511) |
  | 20 % | 0.195 vs 0.041: **+0.153** (+0.112 a +0.197) | 0.076 vs 0.014: **+0.062** (+0.033 a +0.092) |
  | 10 y 5 % | nadie supera el azar | nadie supera el azar |

  - Excepción por año: 2026 con 100 % y p99, V4S compartido 0.502 contra L0 0.452. Es un empate
    (−0.050, de −0.133 a +0.040).
- **Recall y precisión, 2025, p99** (L0 único / V4S compartido / V4):
  - con 100 %: recall 0.91 / 0.60 / 0.58 y precisión 0.26 / 0.20 / 0.10;
  - con 50 %: 0.82 / 0.32 / 0.33 y 0.31 / 0.12 / 0.07;
  - falsas alarmas reales en 2025 limpio: 1.0 / 1.6 / 3.4 %.
- **Supervisar con las entradas del V4 casi no cambia el orden de los puntajes:** PR-AUC en 2025 con
  100 / 50 / 20 %, V4S compartido 0.355 / 0.110 / 0.015 contra V4 0.387 / 0.095 / 0.012. Mejora la
  precisión con p99, pero con p99.9 detecta menos que el V4.
- **El V4S por estación queda último:** F1 de 0.032 con 50 % y p99 en 2025.
- **Predicciones:** 5 de 6. Falla la 2: el V4S por estación no le gana al V4.
- **Respuesta a la crítica del asesor:**
  - L0 le gana a un V4 supervisado entrenado igual, con los mismos calendarios, etiquetas, ventanas
    y modelo único;
  - la ventaja viene sobre todo de las entradas de L0 (su perfil y sus vecinas), no de tener
    etiquetas;
  - con ataques de 100 % y p99, la ventaja es pequeña: +0.069, y empate en 2026.
- **Hipótesis, no comprobada:** con valores absolutos de 32 estaciones, el V4S memoriza los
  calendarios (E = 3, con la pérdida de 2022 subiendo desde la época 4).
- **Comprobación con 2022** (`comprobacion_v4s_2022.py --compartido`; no elige nada):

  | | V4S por estación | V4S compartido | L0 |
  |---|---|---|---|
  | ROC-AUC por hora, todas | 0.626 | **0.811** | — |
  | ROC-AUC por hora, signo + / signo − | 0.662 / 0.593 | 0.777 / 0.843 | — |
  | Estaciones con ROC-AUC < 0.55 | 13 de 31 | **0 de 31** (mínimo 0.686) | — |
  | ROC-AUC por estación-día (comunes) | 0.648 | **0.873** | 0.976 |
  | PR-AUC por estación-día (azar 0.008) | 0.122 | 0.245 | 0.474 |

- **Lectura:**
  - el compartido sí aprende en las 31 estaciones y en los dos signos. Se cumple la predicción 4;
  - la causa del fallo del V4S por estación era la escasez de ejemplos por modelo, no las entradas
    del V4;
  - en 2022, L0 sigue arriba del V4S compartido. Es optimista para los dos, porque 2022 se usó para
    el EarlyStopping, así que no sustituye al examen.

---

## Siguiente

**Actualización 2026-10-12:** la junta del 2026-10-12 sustituye el segundo ataque
(drenado de energía) por la **detección de sensores anómalos a nivel de red**. La lista
vigente es **L1–L7**. Las tablas K y de 2026-10-04 que siguen quedan como historial.

**Actualización 2026-10-05:** la junta del 2026-10-05 reorienta la tesis hacia un segundo
ataque. Sus pendientes **K1–K7** (sección anterior) tienen prioridad sobre las filas 2–3
de esta tabla, que quedan en pausa hasta definir el giro; la fila 4 (redacción) sigue,
ahora como K6.

**Lista vigente al cierre del 2026-10-04.** J1–J8 arriba conservan las preguntas
y planes de la junta anterior; sus estados históricos no sustituyen esta lista.

| Orden | Entregable / asunto | Estado |
|---:|---|---|
| 1 | Cerrar presentación multianual y resultado negativo de B | Resumen corregido; revisión del tesista y presentación al asesor pendientes |
| 2 | Medir aportación de estaciones y contrastarla con distancia | Abierto; el repaso de la matriz no demuestra cuáles estaciones utiliza el modelo |
| 3 | Comparar LSTM V4 con CNN-1D | Dataset/protocolo temporal disponibles; falta fijar arquitectura y ejecutar comparación pareada |
| 4 | Redactar metodología, resultados y límites | En paralelo; incluir el resultado negativo de la codificación |

**Realizado:** repaso de entradas/perfil/ventana y CSV para el asesor (J1), figuras
base revisadas (J2), inventario, protocolo y primera evaluación multianual, y
evaluación de las distribuciones probadas, y variante contemporánea (J1) evaluada:
resultado negativo, se mantiene el V4; vecinas cercanas evaluadas: resultado mixto,
se mantiene el V4. No reabrir entrenamientos por cambios
de redacción. Queda recoger la revisión del asesor sobre las figuras y el alcance.

**Diferido o condicionado:** nuevas codificaciones J3–J7, persistencia y varios
nodos J8, datos de cinco minutos, cobertura
de HGM/XAL, otras semillas y análisis adicional de falsas alarmas. Un control
con menos años y el mismo test es necesario si se quiere atribuir una mejora a
más historia, pero no se presenta como ya ejecutado. SIMAT/HORA, V11 y V10 siguen
abiertos. No son tareas automáticamente autorizadas por el cierre del resumen.

**Para la próxima junta:** resumen corregido, ejemplo de ocultamiento y propuesta
del análisis de aportación espacial; después, diseño de la comparación CNN-1D.

### Cola anterior — conservada como historial de 2026-09-01

No es la lista vigente: disponibilidad, máscaras y LSTM ya se abordaron.
La prioridad de esta lista es histórica. La secuencia vigente es la de la tabla
anterior; se conserva el texto original para no perder su contexto:

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
| V5 | Estabilidad del formato RAMA en años anteriores | **CERRADO 2020–2026** — mismo formato; 2024 sin 2 renglones horarios. Ver [notebook 10](../notebooks/10_inventario_multianual.ipynb) |
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
