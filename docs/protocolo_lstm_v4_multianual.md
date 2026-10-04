# Protocolo LSTM V4 multianual y base común para CNN-1D

**Fecha:** 2026-10-03. **Identificador:** `v4_multianual_33_p95cal2023_v1`.
**Estado:** protocolo acordado antes del entrenamiento; no contiene resultados nuevos.
**Revisión 1 (2026-10-03, antes de entrenar):** canal inactivo (§4.1), mínimos de
elegibilidad (§3.2), `shuffle=True` con semilla (§5), nota sobre E (§5) y límites
de representatividad de 2020 (§2). Ningún modelo se había entrenado con la versión
anterior, por lo que se conserva el identificador. Ver §11.
**Responsable de ejecución:** el tesista, mediante notebooks y artefactos reproducibles.

## 1. Objetivo y límites

Evaluar un predictor LSTM V4 por estación con varios años de O₃, medir su
capacidad de detectar bit flipping y estudiar qué estaciones aportan información.
Preparar el mismo conjunto de evaluación para una comparación posterior con CNN-1D.

Preguntas principales:

1. ¿Cómo funciona V4 en años posteriores, incluyendo temporada de ozono alto?
2. ¿Qué falsas alarmas produce y qué ataques dañinos deja pasar?
3. ¿Detecta ataques que crean u ocultan excedencias observadas de **155 ppb**?
4. ¿Qué estaciones utiliza para estimar cada objetivo y cómo se relaciona esa
   utilidad con la distancia geográfica?

Se conserva el inventario multianual aportado por el tesista, sin repetirlo.
Fuentes: `docs/checksums_2020_2026.txt` y
`results/inventario_multianual/estaciones_geografia.csv`.
V5 queda resuelto para el formato inventariado de 2020–2026.

No se promete que más años mejoren el detector. Para atribuir una mejora a la
cantidad de historia haría falta un control con menos años y el **mismo test**;
comparar contra las métricas antiguas de otro periodo no demuestra esa mejora.
Ese control queda como extensión, no como requisito de esta primera referencia.

No incluye redistribución de pesos, entrenamiento con ataques, ataques sostenidos,
compromiso simultáneo de nodos ni decisiones administrativas reales de contingencia.

## 2. Separación temporal congelada

Los intervalos incluyen todas las horas disponibles de las fechas indicadas.

| Etapa | Periodo | Uso permitido |
|---|---|---|
| Ajuste inicial | 2020-01-01 a 2021-12-31 | Aprender pesos y ajustar normalización inicial |
| Validación | 2022 completo | Seleccionar número de épocas; sin ajustar pesos con estos ejemplos |
| Ajuste definitivo | 2020-01-01 a 2022-12-31 | Entrenar desde cero durante las épocas seleccionadas |
| Calibración | 2023 completo | Calcular p95 de errores limpios por estación y modelo |
| Prueba principal | 2024 completo | Evaluación final limpia y atacada |
| Prueba complementaria | 2025 completo | Evaluación posterior; año ya explorado en el proyecto |
| Prueba parcial adicional | 2026-01-01 a 2026-07-31 | Evaluación posterior de siete meses, no año completo |

- Se utiliza **todo 2024**, no sólo febrero–mayo. Se desglosan temporada,
  meses, horas y días con excedencias, sin sustituir el resultado anual.
- Se declara que 2024 se eligió con conocimiento de su cobertura de excedencias,
  no por un mejor resultado del detector. El inventario de otros años también
  se conoce: no se describen como datos absolutamente ciegos.
- 2023 no sirve para elegir arquitectura ni estaciones. No se ajusta el umbral
  para mejorar resultados observados de 2024–2026.
- No hay split aleatorio de fechas. La pertenencia de una ventana a una etapa
  depende de la fecha de su **objetivo**, no de la primera hora de su contexto.
- Al cambiar de año se conserva el pasado disponible: el 1 de enero puede
  utilizar contexto de diciembre. No se descartan 24 horas en cada corte.
- Cualquier modificación tras observar el test se registra como protocolo nuevo;
  ese test ya no puede presentarse como validación independiente de la modificación.
- **Representatividad del ajuste inicial.** 2020 incluye el confinamiento por
  COVID-19, con emisiones atípicas, y es la mitad del ajuste inicial. Además, en
  2020 sólo el 39.4 % de las horas tiene ≥25 de las 33 estaciones con dato, frente
  a 66–78 % en 2022–2025: el modelo aprende con más máscaras de las que verá en
  prueba. No invalida la separación; se declara como límite y no se corrige.

## 3. Matriz temporal y estaciones

### 3.1 Columnas fijas

La lista y el orden se toman de la referencia de 2025:

```text
ACO AJM AJU ATI BJU CAM CCA CHO CUA CUT FAC FAR GAM HGM INN IZT
LLA LPR MER MGH MON MPA NEZ PED SAC SAG TAH TLA TLI UAX UIZ VIF XAL
```

Una fila por hora continua entre el inicio de 2020 y el 31/jul/2026; una columna
por estación. No eliminar columnas totalmente vacías dentro de un año.

- `-99`, columnas ausentes y renglones ausentes se convierten en faltantes.
- Conservar aparte el origen del faltante para auditoría. No es una entrada del modelo.
- Reindexar a la rejilla horaria: las dos horas sin renglón de 2024 no se omiten
  ni se comprimen. Una ventana de 24 filas debe representar 24 horas consecutivas.
- No interpolar mediciones ni rellenar objetivos con valores sintéticos.
- SFE queda fuera de esta referencia de 33 estaciones; COY y SJA también.
  Incluir SFE será otra variante, no una modificación silenciosa de esta matriz.
- La convención heredada `HORA=1 → 00:00`, `HORA=24 → 23:00` se conserva como
  **convención provisional**, no confirmación del SIMAT. Mantener FECHA/HORA
  originales y registrar esta limitación en resultados por hora y cruces de fecha.
  No afirmar que la causa del faltante de madrugada sea calibración documentada.

### 3.2 Elegibilidad por objetivo

Son 33 objetivos candidatos, **no una promesa de 33 modelos evaluables**.
Exigir ejemplos válidos del objetivo en ajuste inicial, validación y calibración.
Si falta una etapa necesaria, no inventar etiquetas ni seleccionar épocas con el test:
registrar el motivo y dejar ese objetivo fuera de la referencia principal.

**Mínimos fijados antes de entrenar.** Cada etapa obligatoria (ajuste inicial
2020–2021, validación 2022 y calibración 2023) debe tener, para el objetivo,
**al menos 2 000 horas con lectura válida y al menos 6 meses calendario con algún dato**.

- Cero ejemplos en una etapa obligatoria: el objetivo queda **fuera** (no hay
  con qué seleccionar E o calibrar).
- Hay ejemplos pero no se alcanza el mínimo: el objetivo se entrena con el mismo
  protocolo, pero se marca `baja_representatividad` con la etapa y el motivo.
  Sus resultados se reportan **aparte** de los agregados principales; no se borran
  ni se reincorporan después según su desempeño.

Aplicado al inventario (horas válidas / meses con datos), antes de entrenar:

| Objetivo | Situación | Clasificación |
|---|---|---|
| HGM | 0 h en validación 2022 | fuera |
| XAL | 0 h en 2020–2022 | fuera |
| TLI | calibración 2023: 1 509 h, 3 meses | baja representatividad |
| INN | calibración 2023: 2 950 h, 5 meses | baja representatividad |
| AJM | ajuste inicial: 2 490 h, 4 meses | baja representatividad |
| Restantes 28 | cumplen ambos mínimos | referencia principal |

La tabla definitiva se genera con código en `cobertura_etapas.csv` sobre los
ejemplos efectivos (objetivo válido y base disponible), que pueden ser algo
menos que las horas válidas; si difiere de esta tabla, prevalece el archivo
generado y la diferencia se documenta. Los mínimos no se ajustan después.

La disponibilidad de test se informa por año. Un modelo se puede evaluar en un
año y no en otro. No excluirlo de todos porque falten datos de un solo año.
Reportar conteos, cobertura mensual y rachas sin datos en cada etapa; existencia
de ejemplos no equivale a representatividad estadística.

Las estaciones sin modelo siguen aportando lecturas como contexto cuando existen
y siguen contando para el máximo observado de la red de 33 estaciones.

## 4. Entrada y perfil adaptativo

### 4.1 Entrada del LSTM

Para predecir la estación S a la hora t:

- Contexto: horas **t−24 a t−1** de las otras 32 estaciones, nunca su lectura en t.
- 32 valores normalizados, 32 máscaras y seno/coseno de la hora de cada fila.
- Máscara **1 = dato observado; 0 = faltante**. Rellenar con 0 sólo después de
  normalizar; ese relleno no representa una medición de 0 ppb.
- Tensor por ejemplo: **24 × 66**. No contiene coordenadas, etiquetas de ataque,
  identificadores del bit atacado ni el valor actual de la estación objetivo.

Normalización por estación de entrada: media y desviación de observaciones del
ajuste inicial para la fase inicial; recalcularlas con 2020–2022 para el ajuste
definitivo. Congelarlas después. Nunca usar 2023–2026 para ajustarlas.
Si una desviación es cero, usar 1.

**Canal inactivo.** Si una estación de entrada no tiene ninguna observación en el
ajuste definitivo (2020–2022), su canal se declara inactivo y se fuerza a
**valor 0 y máscara 0 en todas las etapas**, incluidas calibración y prueba,
aunque después existan lecturas. Motivo: durante el ajuste ese canal vale siempre
0, por lo que sus pesos no reciben gradiente y quedan en su valor aleatorio inicial;
si en prueba recibiera datos reales introduciría una perturbación arbitraria en la
predicción. En esta referencia el único canal inactivo es **XAL**. Su lectura sigue
contando para el máximo observado de la red (§8); sólo se oculta como entrada.
Se aplica a la fase inicial con el mismo criterio sobre 2020–2021.

HGM sí tiene historia (8 meses de 2020) y no se inactiva, pero se registra como
canal con poca historia: el modelo lo vio poco y no se afirmará que lo aprovecha.

### 4.2 Perfil de la estación objetivo

La base es la media de las observaciones disponibles de S a la misma hora
durante los **14 días naturales anteriores**, excluyendo el día actual.
Con rejilla horaria completa, desplazar una posición dentro de cada grupo horario
antes de aplicar la media móvil. No convertir «14 días» en «14 observaciones válidas».

Regla causal de respaldo de esta referencia:

1. Usar la media de esa hora en los 14 días anteriores, con al menos un dato.
2. Si no hay ninguno, usar la media histórica de esa hora **estrictamente anterior a t**.
3. Si tampoco existe, usar la media de todas las lecturas del objetivo anteriores a t.
4. Si no existe historia, declarar base no disponible y excluir el ejemplo.

Guardar el origen de cada base y cuántos ejemplos usan cada respaldo. No rellenar
el comienzo de la serie con medias del año completo ni del train completo: para
los ejemplos iniciales esas medias contendrían observaciones futuras.
Esta regla hace explícito un cambio respecto al respaldo de referencias anteriores;
no se espera identidad numérica con sus predicciones.

El objetivo del entrenamiento es `lectura_original − base`; la estimación final
es `base + correccion_predicha`. El detector compara esa estimación con lo recibido.
La historia propia participa en la base, aunque no entre en los canales del LSTM.

En evaluación limpia se permite actualizar el perfil con observaciones pasadas
de calibración/test, como en operación secuencial, sin reentrenar pesos ni umbral.
En los ataques aislados la historia previa permanece limpia: no se modela su
contaminación futura ni la de los detectores de otras estaciones.

## 5. Entrenamiento y reproducibilidad

Referencia arquitectónica: `src/detect/lstm.py::construir_modelo`.

| Parámetro | Valor inicial fijado |
|---|---|
| LSTM | 64 unidades |
| Dropout | 0.2 |
| Capa densa intermedia | 32 unidades, ReLU |
| Salida | 1 valor lineal |
| Pérdida / optimizador | MSE / Adam, learning rate 0.001 |
| Batch | 64 |
| Semilla | 42 |
| Máximo en selección de épocas | 60 |
| EarlyStopping | `val_loss`, paciencia 8, `min_delta=0`, restaurar mejores pesos |
| Orden de batches | `shuffle=True`, explícito, dependiente de la semilla 42 |

Por cada estación:

1. Limpiar sesión de Keras y llamar `fijar_semilla(42)` inmediatamente antes
   de construir el modelo y entrenar con 2020–2021; validar explícitamente en 2022.
2. Elegir E como la primera época con el menor `val_loss`, numerada desde 1.
   Guardar historia y E; no confundir mejor época con última época ejecutada.
3. Limpiar sesión y fijar semilla otra vez. Recalcular normalización definitiva,
   construir un modelo nuevo y entrenar con 2020–2022 durante exactamente E épocas,
   sin validación interna ni EarlyStopping en esta segunda fase.
   El ajuste definitivo tiene unas 1.5 veces más ejemplos, de modo que E épocas
   equivalen a más pasos de gradiente que en la selección. Se mantiene E sin
   reescalar (práctica habitual) y se declara.
4. Guardar modelo y preprocesamiento. Calibrar y evaluar **cargando ese modelo**;
   no volver a entrenarlo al ejecutar las celdas de evaluación.

**Orden de los batches.** `shuffle` sólo decide en qué orden se presentan los
ejemplos de entrenamiento **dentro de cada época**. No mezcla etapas: las ventanas
de 2022, 2023 o 2024 nunca entran al entrenamiento. Cada ejemplo ya lleva sus
24 horas de contexto, así que mezclarlos no rompe el orden temporal dentro de una
ventana. Con `shuffle=False` cada época recorre siempre de enero de 2020 a diciembre
de 2022 y los últimos ajustes de pesos son siempre con diciembre de 2022, lo que
sesga el modelo hacia ese régimen justo antes de calibrar. Se usa `shuffle=True`,
que además coincide con lo que hacía `entrenar()` (valor por defecto de Keras).
El orden depende de la semilla fijada por `fijar_semilla(42)`; la reproducibilidad
se verifica igual que el resto (dos corridas independientes).

**Advertencia de implementación:** `entrenar()` actualmente divide X mediante
`val_frac` y usa `fit` sin fijar `shuffle`. No llamarlo tal cual para este protocolo:
se necesita una ruta nueva con validación externa y otra de ajuste de épocas fijas.
Conservar la función y los artefactos históricos para no romper su reproducibilidad.

El notebook nuevo debe cargar resultados por defecto. Exigir un flag explícito
para entrenar faltantes y otro consentimiento para sustituir una referencia.
Un cambio de configuración, fuentes o código produce una versión nueva.

Registrar versiones, hardware, semillas, hashes y política determinista.
Verificar dos ejecuciones independientes del entrenamiento de referencia antes
de aceptar su reproducibilidad; comparar predicciones, umbrales y métricas, no
sólo el hash del contenedor `.keras`. Verificar también inferencia tras cargar
desde disco. Si difieren, registrar y resolver la discrepancia sin escoger la
corrida más favorable. La semilla no garantiza igualdad entre entornos distintos.

## 6. Calibración, sin confundir los dos umbrales

- **155 ppb:** umbral experimental de excedencia de O₃.
- **Umbral del detector:** p95 de `abs(original − predicho)` en ejemplos limpios
  válidos de **2023**, separado para cada estación y arquitectura.

Calcular el percentil con `numpy.percentile(..., 95, method='linear')`, guardar
el valor completo y declarar alerta si **residuo absoluto > umbral**.
La igualdad no genera alerta. No redondear antes de decidir.

El p95 se calcula aquí fuera del entrenamiento: no es el p95 histórico del piloto.
No imponer 22.6 ni 14.748354911804199 ppb a estos modelos nuevos.
Los archivos históricos de CCA permanecen intactos.

Guardar número de ejemplos y distribución mensual de calibración. Si no hay
errores válidos no existe umbral evaluable. Un p95 no asegura 5 % de falsas
alarmas en otro año: medirlo, no corregirlo usando el test.

## 7. Evaluación limpia y atacada

### 7.1 Antes de atacar

Por estación y año: n de ejemplos válidos, cobertura, MAE, sesgo
`mean(original − predicho)`, sigma del residuo (`ddof=0`), falsas alarmas,
total limpio y FPR. Desglosar por mes y hora sin cambiar umbrales.
Informar también el error de **usar sólo el perfil adaptativo**, para comprobar
si la corrección aprendida mejora ese predictor sencillo en el mismo conjunto.

### 7.2 Dos evaluaciones que no se mezclan

**A. Muestra pareada para clasificación.** En cada estación/año, seleccionar
cada mensaje original observado con probabilidad 0.05, antes de filtrar por
disponibilidad del detector. Usar un plan reproducible común para bits 0–7 y
para ambos modelos. Generar flujos por estación/año con semilla maestra 42 e
identificadores estables (no usar `hash()` de Python). Guardar el plan, no sólo
la semilla. Informar ataques seleccionados y ataques finalmente evaluables.

Es correcto que todos los bits tengan el mismo número de ataques: es pareado.
No forzar el conteo histórico de 78 ni usar sorteos nuevos entre arquitecturas.

**B. Barrido exhaustivo de daño.** Cada lectura observada de test, cada bit
0–7, un escenario independiente: una estación, una hora, un bit modificado.
Esto caracteriza oportunidades de daño; no representa una campaña simultánea
ni una prevalencia real de ataques. No calcular precisión con este conjunto
de sólo ataques y confundirla con la de la muestra al 5 %.

En ambos casos usar la codificación original y la cadena existente
encode/cifrar/flip/descifrar/decode, verificada frente a XOR del valor entero.
Con numeración desde cero, los pesos son **1, 2, 4, 8, 16, 32, 64 y 128 ppb**.
El signo depende del estado del bit; no se sustituye el flip por una suma.
No aplicar la contramedida de redistribución ni restringir silenciosamente
el dominio del decodificador a 0–255. Conservar contador y parámetros de
cifrado reproducibles; documentar cualquier rechazo por separado.

Reutilizar la predicción limpia para un ataque aislado actual es válido porque
no cambian ni las entradas pasadas ni la base anterior. No propagar ese ataque
a otro escenario; no retirar automáticamente lecturas que generan alerta.

### 7.3 Métricas por bit

En la muestra pareada, clase positiva = ataque:

```text
recall    = TP / (TP + FN)
precision = TP / (TP + FP)
F2        = 5*TP / (5*TP + 4*FN + FP)
FPR       = FP / (FP + TN)
```

Reportar TP, FP, FN, TN y denominadores, además de porcentajes.
Si el denominador es cero, usar NA con motivo; no inventar 0 o 100 %.
No mezclar precisión al 5 % con otra prevalencia de ataques.

## 8. Daño local, daño de red y figuras

Usar la función de bandas existente `banda_o3` como decisión experimental
uniforme, documentando su versión. Esto no reconstruye normas históricas
distintas aplicadas administrativamente en cada año.

Separar por escenario:

1. Cambio de banda de la lectura atacada.
2. Cambio de banda del máximo diario observado de la red de 33 estaciones.
3. Falsa excedencia: máximo original <155 y máximo después del ataque >=155.
4. Ocultamiento: máximo original >=155 y máximo después del ataque <155.

Recalcular el máximo después de reemplazar **sólo el mensaje atacado**,
conservando todas las otras lecturas, incluso las de estaciones sin detector.
Ejemplo: bajar 167 a 135 no oculta la excedencia si otra lectura permanece en 166.
Mantener empates y otras horas del día; no atacar únicamente la lectura máxima.

Estos eventos son excedencias del máximo **observado**, no declaraciones ni
suspensiones oficiales de contingencia. No validan persistencia subhoraria.
Si un día queda sin observaciones, su decisión es indefinida, no «sin excedencia».

Para cada tipo de daño informar oportunidades observadas, evaluables, detectadas,
no detectadas y sin evaluación. Un mensaje sin modelo no se considera protegido.
En días contar una vez cada fecha por bit/tipo/año; un día puede tener escenarios
detectados y otros no detectados. «Hay una oportunidad» no significa que un
atacante ciego pueda identificar y ejecutar ese escenario con certeza.

Denominador diario principal: días con al menos una lectura observada de la red
en el periodo. Informar también días calendario, días sin datos y cobertura.
Mostrar aparte ocultamientos / días con excedencia original; no confundir ese
porcentaje condicionado con ocultamientos / todos los días observados.

Figuras y tablas se generan directamente de los eventos, con bits 0–7,
leyendas breves y denominadores en el pie. No multiplicar porcentaje de días
por recall promedio para llamarlo daño observado. Si se conserva el indicador
compuesto histórico, rotularlo como descriptivo y separarlo del conteo empírico.
No forzar cruces, máximos interiores ni monotonicidad.

Separar años completos de 2026 parcial. Para comparar estacionalmente, añadir
enero–julio de cada año sin sustituir sus resultados anuales. Informar agregados
micro (suma de conteos) y macro (igual peso por estación evaluable), con su cobertura.

## 9. Aportación de estaciones y comparación CNN-1D

Esta sección fija el alcance, no autoriza ajustar la referencia con resultados de test.

- Las coordenadas son descriptivas. Calcular distancias a **cada objetivo**;
  la distancia a CCA del inventario no sirve para ordenar vecinos de todos.
- El LSTM puede aprovechar dependencias entre señales sin conocer geografía.
  No deducir importancia directamente de magnitudes de pesos de sus capas.
- Usar el modelo inicial y 2022 para diseñar diagnósticos: comparar entrada
  completa con ocultamiento de una estación (valor normalizado 0, máscara 0),
  después grupos. Es una prueba de dependencia frente a faltantes artificiales,
  no una medida causal ni un porcentaje de contribución física.
- Estaciones correlacionadas pueden sustituirse; una caída pequeña al retirar
  una no demuestra inutilidad. Las correlaciones para seleccionar entradas
  se calculan sólo con ajuste, nunca con todo el periodo multianual.
- No imponer que una estación lejana o de otro entorno sea irrelevante.
  Contrastar distancia, disponibilidad y efecto sobre predicción/detección.
- Comparar modelos reentrenados con conjuntos de estaciones distintos requiere
  una variante predefinida; no modificar las 33 entradas de la referencia.

Antes de ejecutar CNN-1D fijar su arquitectura y presupuesto de selección en
un protocolo complementario. Debe recibir los mismos tensores, perfiles, fechas,
planes de ataque y etiquetas de daño. Utilizar la misma política de calibración,
pero **un p95 propio de cada modelo/estación**, no el valor numérico del LSTM.
Reportar métricas en la intersección evaluable común y cobertura excluida.
No concluir superioridad sólo por recall si también aumenta FPR.

## 10. Entregables y ejecución por etapas

Crear una referencia nueva; no sobrescribir notebooks, modelos ni resultados
aceptados de 2025. Rutas propuestas para la implementación:

```text
results/lstm_v4_multianual_v1/
  protocolo.json                  # Parámetros, fechas, columnas, versiones, semillas
  fuentes_sha256.json              # Datos, código y copia del protocolo usado
  cobertura_etapas.csv             # Objetivo, etapa, meses, n, motivo de exclusión
  auditoria_temporal.csv           # Horas, cortes y causalidad de las ventanas/bases
  planes_ataque/                   # Selección pareada persistida por estación/año
  estaciones/<ESTACION>/
    seleccion/                    # Modelo inicial, historia 2022 y mejor época E
    modelo.keras                  # Ajuste definitivo 2020–2022
    preprocesamiento.npz           # Orden de canales y normalización definitiva
    configuracion.json             # E, semillas, respaldos y hashes propios
    historia_definitiva.csv
    umbral_p95_cal2023.txt
    calibracion_2023.csv.gz        # Fecha, original, base, predicción y residuo
    predicciones_<ANIO>.csv.gz     # Incluye origen de base y alerta limpia
  metricas_limpias.csv
  metricas_pareadas.csv
  eventos_dano/                    # Detalle comprimido, particionado por año/bit
  resumen_dano_mensajes.csv
  resumen_dano_dias.csv
  verificacion_reproducibilidad.md
docs/img/lstm_v4_multianual_v1/
```

Los tensores pueden construirse por lotes para evitar cargar toda la red y
todos los años en memoria. Conservar los índices de ejemplos y suficiente
información para reconstruirlos exactamente; no es obligatorio guardar todos los X.
Ejecutar primero CCA como comprobación técnica, **sin mirar el test para ajustar**,
y después los objetivos elegibles con el mismo protocolo.

### Lista de cierre

- [x] Guardar configuración y copia/hash de este protocolo antes de entrenar.
  `protocolo.json` y `fuentes_sha256.json` (notebook 11).
- [x] Construir matriz fija y comprobar causalidad, continuidad y faltantes.
  `auditoria_temporal.csv`: 27/27 comprobaciones; salidas idénticas en dos corridas.
- [x] Exportar un ejemplo real de ventana/base/objetivo de cada etapa para revisión.
  CCA, `ejemplos_etapas/`.
- [x] Generar cobertura y elegibilidad sin asignar resultados a objetivos ausentes.
  `cobertura_etapas.csv`: 28 principales, 3 baja representatividad, 2 fuera.
- [ ] Implementar entrenamiento con validación externa y ajuste definitivo separado.
- [ ] Seleccionar E por estación, reentrenar y guardar checkpoints nuevos.
- [ ] Calibrar con 2023 y congelar umbrales.
- [ ] Verificar reproducibilidad y carga desde disco antes de aceptar resultados.
- [ ] Evaluar limpio y ataques pareados en 2024, 2025 y 2026 parcial por separado.
- [ ] Completar barrido de daño con máximos de red y cobertura explícita.
- [ ] Guardar tablas que sustentan todas las figuras y redactar límites/resultados.
- [ ] Diseñar diagnóstico espacial sin usar test para seleccionar entradas.
- [ ] Fijar arquitectura CNN-1D y ejecutar la comparación común en una etapa posterior.

**No bloquean el primer entrenamiento, pero permanecen abiertos:** confirmación
SIMAT de HORA y faltantes de madrugada (V11), zonas ZMVM (V10), variante con
SFE, contexto contemporáneo, otras semillas como análisis de estabilidad y
ataques persistentes. No presentar ninguno como evaluado por este protocolo.

## 11. Registro de revisiones

| Revisión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 0 | 2026-10-03 | Versión inicial | — |
| 1 | 2026-10-03 | Canal inactivo XAL (§4.1) | Sin historia en 2020–2022: pesos sin entrenar recibirían datos en prueba |
| 1 | 2026-10-03 | Mínimos de 2 000 h y 6 meses por etapa (§3.2) | Evitar decidir la inclusión después de ver resultados |
| 1 | 2026-10-03 | `shuffle=False` → `shuffle=True` con semilla (§5) | Evitar sesgo hacia diciembre de 2022; coincide con `entrenar()` |
| 1 | 2026-10-03 | Nota sobre E y límites de 2020 (§2, §5) | Declarar, no corregir |

Todas las revisiones son anteriores a cualquier entrenamiento con este protocolo.
