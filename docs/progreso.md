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
