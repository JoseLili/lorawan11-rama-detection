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

---

## Siguiente

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
