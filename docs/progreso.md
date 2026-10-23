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
