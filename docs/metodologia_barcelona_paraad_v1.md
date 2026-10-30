# Metodología Barcelona: comparación de PARAAD, V4 y L0

Fecha: 2026-10-28. Identificador provisional: `barcelona_paraad_comparacion_v1`.
Estado al 2026-10-29: **cohorte aprobada, convención temporal operativa y
ventanas preparadas; escenario proporcional RAMA aprobado como principal**.
Actualización 2026-10-29: el tesista aprueba δ={100,50,20,10,5}%, episodios
1–7 días y un L0 principal entrenado sólo con δ50. El sesgo aditivo pasa a
complementario. Las secciones originales de sesgo quedan como historial y
diseño del complemento; no rigen el entrenamiento del L0 principal. Prevalece
`escenario_proporcional_barcelona_v1.md` para estas reglas y los calendarios.
El tesista solicita trasladar la metodología RAMA al escenario de PARAAD.
Actualización de esta sesión: tras la auditoría, el tesista elige continuar
con 13 estaciones de municipios AMB con cobertura suficiente en 2014–2015.
Ver `auditoria_barcelona_paraad_2014_2019.md` y
`data/reference/barcelona_paraad/cohorte13_registro.json`. Ésta será la cohorte
del estudio controlado, no la lista original de ocho aún sin identificar.
Las menciones a ocho estaciones en el diseño inicial quedan como antecedente:
las dimensiones pasan a PARAAD 13×24 y V4 26 características (12 vecinas,
sus máscaras y sin/cos); L0 conserva cuatro vecinas y 17 características.
El redondeo de 30% se fija en cuatro sensores (30.77%). Las fechas propuestas
tienen cobertura. La convención de hora operativa y las ventanas se describen
abajo y en `ventanas_barcelona_paraad_v1.md`; se obtuvieron 27,339
estación-días comunes y todas las estaciones cumplen los mínimos de contexto.
No se inició entrenamiento ni examen nuevos. La revisión 21 queda reservada
al experimento RAMA de error fijo; no se reasigna su número.

## 1. Pregunta y comparación principal

¿Cómo se comportan PARAAD-SA, V4 y L0 ante las mismas anomalías aditivas en
las estaciones de Barcelona, con separación temporal, calibración y evaluación
comunes? Se conserva la metodología de control de RAMA, adaptando las
dimensiones y los datos, sin reutilizar sus pesos ni umbrales.

Comparación principal: **PARAAD-SA contra V4**, sin etiquetas de ataque en el
ajuste. L0 es referencia supervisada: recibe ejemplos de anomalías en su
entrenamiento. Un mejor resultado de L0 no demuestra por sí solo que su
arquitectura sea superior. V4S no se incluye en esta primera comparación;
es supervisado y podría añadirse mediante registro separado.

Este estudio es una comparación controlada en el contexto de PARAAD, no
automáticamente una reproducción exacta de sus tablas. La reproducción del
artículo (partición 90/10 y umbral móvil) se considera un análisis de fidelidad
separado, sin mezclar sus condiciones con las de esta comparación.

## 2. Datos, procedencia y condición previa

- O3 horario de 2014–2019, fuente Generalitat `tasf-thgu`, con código EOI,
  nombre, coordenadas, unidades y metadatos temporales.
- Prioridad: identificar los ocho códigos y el subconjunto de 24,192 horas
  por sensor descrito en el artículo. Todavía no están identificados.
- El municipio Barcelona no equivale a su área metropolitana: el catálogo
  consultado enumera seis estaciones municipales, lo cual no permite completar
  las ocho escogiendo otras dos por conveniencia.
- Si no se recupera el subconjunto original, registrar antes del modelado un
  conjunto propio basado en delimitación geográfica documentada y cobertura
  de ajuste, sin usar rendimiento ni valores de examen para seleccionarlo.
  Su nombre será «datos de la misma fuente», no «dataset exacto de PARAAD».
- Guardar consulta, fecha, respuesta original, SHA-256, códigos y orden fijo.
  Auditar duplicados, sentinelas, fechas, continuidad y coordenadas.
- Mantener µg/m³ si son las unidades originales. No trasladar 155 ppb ni las
  reglas de contingencia de Ciudad de México. La evaluación aquí es detección
  de anomalías, no activación de contingencias.
- «Limpio» significa sin inyección experimental. No garantiza que las estaciones
  reales estén libres de errores o fallas previas, igual que en RAMA.

## 3. Separación temporal propuesta

La siguiente traducción conserva los papeles de las etapas de RAMA. **Las
fechas son una propuesta condicionada a la auditoría**, no un supuesto de que
los 1,008 días del artículo cubran todos esos años.

| Etapa | Periodo propuesto | Uso permitido |
|---|---|---|
| Ajuste inicial | 2014–2015 | Pesos y escalas iniciales |
| Validación | 2016 | Seleccionar épocas/configuración con regla previa |
| Ajuste definitivo | 2014–2016 | Entrenar desde cero con selección congelada |
| Calibración | 2017 limpio | Umbrales p99 y p99.9, sin seleccionar arquitectura |
| Prueba principal | 2018 | Evaluación limpia y alterada |
| Prueba complementaria | 2019 | Evaluación posterior con todo congelado |

No dividir aleatoriamente horas o días. Conservar la historia pasada disponible
al cruzar etapas; jamás concatenar dos días separados como si fueran contiguos.
Si el subconjunto original no permite esta división, detener y registrar una
alternativa cronológica basada en fechas/cobertura antes de entrenar. No cambiar
las fechas después de observar desempeño. Las comprobaciones de disponibilidad
no se confunden con seleccionar mediante puntajes de examen.

## 4. Tiempo, faltantes y unidad común

1. Resolver con los metadatos la semántica de `h01`…`h24`, zona horaria,
   horario de verano y si las observaciones corresponden al inicio o al fin
   de cada intervalo. No asumir que `h24` es simplemente la siguiente fecha.
2. Construir una rejilla horaria documentada. Fijar una definición de bloque
   de 24 horas para los tres métodos antes de programar; no forzar a ciegas
   días civiles de 23/25 horas a 24 horas. Si se usa UTC o una convención
   horaria fija, declarar que puede diferir del día del artículo.
3. En la comparación controlada, conservar faltantes y máscaras como en RAMA.
   PARAAD recibe relleno neutral estandarizado y usa pérdida/MAE observados;
   V4/L0 conservan sus máscaras y perfiles causales. No interpolar unos métodos
   sí y otros no sin declarar que cambia la información disponible.
4. La evaluación es **estación-bloque diario**, mínimo 12 horas válidas, con
   decisión al cierre del bloque. La máscara común se determina con el dato
   limpio y las reglas de disponibilidad, se guarda y se mantiene bajo ataque.
5. La prueba de fidelidad podrá usar el descarte/interpolación del artículo,
   por separado y con una única política común. No aplicar su descarte global
   si deja sin ejemplos el escenario controlado.

### Aclaración del paso 1: disponibilidad (2026-10-29)

El tesista solicita seguir el criterio de disponibilidad de L0/V4 antes de
generar ventanas o anomalías. Se distingue la elegibilidad de la estación
de la elegibilidad de cada estación-día:

- Se conserva la cohorte aprobada de 13 estaciones, seleccionada con
  2014–2015: mínimo 2,000 horas y seis meses observados. Su cobertura de
  ajuste es 95.20–99.08%; no hace falta escoger un subconjunto por rendimiento.
  Validación y calibración requieren después comprobar ejemplos efectivos
  y disponibilidad de contexto, como establece el protocolo V4. La aprobación
  de la cohorte no sustituye esa comprobación.
- Se conserva el mínimo de 12 horas válidas por estación-día, como en RAMA.
  Tener un episodio definido para todo el día no significa que las 24 lecturas
  deban estar presentes: se altera sólo lo observado y se mantienen las máscaras.
  No se exige ahora 24/24 ni se cambia el mínimo mirando resultados.
- Se informarán por separado días con 24 posiciones observadas, días con
  12–23 y días con menos de 12. Si más adelante se desea una prueba limitada
  a días completos o ataques que comiencen a cualquier hora, se registrará
  como escenario separado antes de ejecutarlo.
- La máscara común final se calculará con los datos sin inyección y con
  los requisitos de contexto de los tres métodos. No basta contar lecturas
  del objetivo; los conteos actuales no son todavía ventanas evaluables.

Comprobación descriptiva de ajuste, obtenida de
`results/barcelona_paraad/auditoria/cobertura_estacion_anio.csv`, filtrando
los códigos de `cohorte13.csv` y los años 2014–2015: 9,490 estación-días
calendario, 8,292 con 24 posiciones observadas, 1,023 con 12–23 y 175 con
menos de 12 (incluidos días sin fila). Los días con 24 posiciones representan
el 87.38% del calendario. Son posiciones de la fuente; no certifican por sí
solas 24 intervalos físicos durante los cambios de reloj. La convención
horaria y el contexto pueden reducir estos conteos. No se generaron ataques
ni se entrenaron modelos para esta comprobación.

### Homologación temporal operativa (2026-10-29)

El tesista autoriza usar timestamps UTC para la continuidad y la hora local
para las entradas cíclicas de L0/V4. Se implementa en
`experiments/barcelona/preparar_tiempo.py`, sin entrenamiento ni inyección.

- Convención operativa: `h01` representa el intervalo local 00–01 y `h24`
  el intervalo 23–24 de la fecha fuente; el timestamp identifica el inicio.
  Es compatible con el contraste oficial de Palau Reial registrado en la
  auditoría. **No se presenta como semántica oficialmente certificada para
  toda la descarga**. No se añade una `Z` a las horas originales sin convertir.
- Se localizan las horas en `Europe/Madrid` y se convierten a UTC. La hora
  local de inicio determina seno/coseno; la fecha completa no es característica
  de entrada. UTC determina la duración y continuidad de las ventanas.
- Se apartan los días locales completos de transición de marzo/octubre,
  para todas las estaciones. Sus filas originales se conservan por separado;
  no se elige arbitrariamente una de las horas repetidas ni se interpola.
  La rejilla UTC conserva los 23/25 intervalos físicos correspondientes,
  marcados como excluidos y sin valores utilizables.
- Las futuras ventanas deben rechazar cualquier intervalo marcado como
  excluido, tanto del objetivo como del contexto requerido. El perfil causal
  no puede recuperar esas observaciones del respaldo: usa sólo datos retenidos.
  Los faltantes ordinarios mantienen sus máscaras; no se confunden con esta
  exclusión temporal. La máscara común final sigue pendiente de implementar.
- Los bloques de comparación previstos son 00–24 UTC, para los tres métodos,
  con anomalías definidas sobre ese mismo bloque. Se recortarán bloques
  incompletos de los extremos y bloques que mezclen etapas; las etapas se
  asignarán por calendario UTC. La correspondencia de las filas fuente en
  los extremos de año se conserva y se verificará antes de separar etapas.
  Este bloque puede diferir del día local del artículo original.

Salida `results/barcelona_paraad/tiempo_utc_v1/`: rejilla de 683,592 filas
(52,584 horas por estación), 656,916 observaciones retenidas y 3,535
observaciones apartadas por cambios de reloj. La suma reproduce las 660,451
observaciones de la cohorte original. Incluye registro de supuestos, versiones
y SHA-256 de entradas y salidas. Se ejecutó dos veces la transformación
completa con igualdad exacta de ambos DataFrames y se verificó su lectura
desde disco. Ocho pruebas cubren auditoría y conversión temporal, incluyendo
transiciones, desfases, duplicados y conservación del respaldo.

Esto resuelve una convención ejecutable para el estudio controlado; no recupera
las horas ambiguas de la fuente ni demuestra reproducción exacta del artículo.

## 5. Qué conserva cada detector

| Detector | Adaptación a las 13 estaciones aprobadas | Información de entrenamiento |
|---|---|---|
| PARAAD-SA | Entrada bloque×13×24; atención y cuello de botella del código contrastado; reconstruye las 13 señales | Observaciones sin ataques inyectados |
| V4 | Un predictor por objetivo; otras 12 estaciones, sus máscaras y sin/cos: 26 columnas por hora; ventana previa de 24 h y base causal de 14 días del objetivo | Concentraciones legítimas como respuesta de regresión, sin etiquetas de ataque |
| L0 | Un clasificador compartido; objetivo y cuatro vecinas por distancia, las mismas 17 características locales y ventana de 24 h de RAMA | Lecturas alteradas y etiquetas sólo del periodo de ajuste |

Las 13 estaciones serán objetivos y contexto si cumplen la elegibilidad
registrada. No existe un equivalente automático de HGM o XAL. Mantener el orden
de estaciones fijo, especialmente porque PARAAD recorre la secuencia de sensores.
Detener si una estación no tiene datos suficientes para ajustar su escala/modelo;
no eliminarla silenciosamente del examen. Los mínimos exactos de elegibilidad
se fijan con la auditoría antes del entrenamiento y se aplican a todos.

Se conservan los puntajes propios: MAE diario de PARAAD, absoluto del promedio
firmado del residuo V4 y promedio diario de probabilidades de L0. Igualar la
unidad y calibración no obliga a convertir los tres en el mismo algoritmo.
PARAAD usa la señal actual del objetivo para reconstruir; V4 excluye ese
objetivo de sus entradas de predicción. Es una diferencia del método que se declara.

## 6. Ajuste y selección

- Escalas y perfiles iniciales exclusivamente con el ajuste permitido; perfiles
  móviles estrictamente causales. Escala definitiva sólo con 2014–2016 si se
  confirma esa división. Ninguna normalización con todos los años juntos.
- PARAAD: misma búsqueda de dropout {0.1,0.3,0.5}, máximo 500 épocas, lote 256,
  pérdida MSE observada. Elegir por menor MSE de validación; empates por menor
  dropout y primera época. No transportar la elección 0.3/499 de RAMA como si
  fuera óptima en Barcelona ni elegirla por su examen RAMA.
- V4: conservar arquitectura y regla de selección temporal de épocas de RAMA,
  con configuración registrada antes de correr; cambiar sólo dimensiones.
- L0: conservar arquitectura local compartida y 20 calendarios de entrenamiento;
  elegir épocas con validación etiquetada independiente y regla de pérdida
  registrada. No barrer ataques/configuraciones para ganar en el test.
- Entrenar desde cero el definitivo con los parámetros seleccionados y la unión
  de ajuste+validación. Sólo CPU, `fijar_semilla(42)` inmediatamente antes de
  construir y entrenar. Dos ejecuciones del proceso completo en el mismo entorno.
- Guardar modelos, escalas, coordenadas/vecinas, fechas, versiones, hashes e
  historias. Identificar siempre modelos nuevos frente a modelos cargados.

## 7. Anomalías: primero el sesgo aditivo de PARAAD

Experimento principal propuesto: desplazamiento positivo constante durante
un bloque diario. Usar el **mismo plan y desplazamiento** para todos.

- Red aprobada de 13 sensores: `round_half_up(0.30*13)=4` por configuración.
  Declarar la fracción efectiva **30.77%**, no llamarla exactamente 30%.
- En cada sensor seleccionado, 30% de los bloques elegibles según la máscara
  común, con redondeo half-up. El plan guarda bloques, etiquetas y magnitudes.
- Para la versión que reproduce la función pública de sesgo, β se obtiene
  con normal truncada entre 0.2σ y 2σ, σ=2, en unidades estandarizadas del
  sensor. Desplazamiento en unidades físicas: β por su desviación de ajuste.
  No usar |N| ni tratar el soporte truncado como una normal no truncada.
- 125 planes factoriales: cinco configuraciones de sensores × cinco de bloques
  × cinco de desplazamientos. Semillas derivadas de 42 con claves enteras
  documentadas, sin `hash()`. Los tres métodos reciben exactamente cada matriz.
- Inyección sólo sobre horas observadas. No redondear a ppb ni aplicar los
  factores proporcionales de RAMA a este escenario. Guardar el valor físico
  alterado y comprobar que la etiqueta representa la inyección definida.
- Los 20 calendarios de L0 se generan exclusivamente dentro de ajuste con claves
  independientes de los de validación y prueba. No se comparte ninguna matriz
  ni etiqueta de prueba con el entrenamiento. Registrar la intensidad de ajuste
  antes de entrenar, sin elegirla con el examen.
- Deriva: extensión registrada por separado una vez se cierre el sesgo, con
  tasas/duraciones y signos fijados a partir del artículo. No mezclarla en la
  primera tabla ni añadirla según cuál detector gane.

La prevalencia aproximada de esta inyección es distinta de la de RAMA. No
atribuir un cambio de F1 entre ciudades únicamente a capacidad del detector;
depende también de la proporción de casos alterados y de su intensidad.

## 8. Calibración y examen

### Registro de calendarios previo a la inyección (2026-10-29)

Se autoriza generar los planes tras aceptar las ventanas. No se aplican aún
a las series ni se entrenan modelos. Se fija un β independiente por
estación-día, constante en sus horas observadas, mediante
`scipy.stats.truncnorm(a=0.2, b=2, loc=0, scale=2)`: soporte β entre 0.4 y 4.
El desplazamiento físico es β por la desviación limpia de la fase, no un
porcentaje de la lectura. No se selecciona intensidad con resultados.

L0: 20 calendarios de ajuste inicial 2014–2015, 10 de validación 2016
(como su regla RAMA), y 20 nuevos de ajuste definitivo 2014–2016 una vez
seleccionadas las épocas. Validación usa escala inicial; ajuste definitivo y
pruebas usan escala definitiva. PARAAD y V4 no reciben estos ataques al ajustar
pesos. Calibración 2017 permanece limpia, sin calendario de inyección.

Prueba 2018 y complementaria 2019: 125 planes por año, producto factorial de
cinco selecciones de cuatro estaciones, cinco selecciones de días por estación
y cinco campos de magnitudes. Cada campo de magnitudes se genera para toda
la máscara del periodo y luego se consulta por estación-día: cambiar sensores
o días no cambia la magnitud del mismo caso dentro del mismo factor de ruido.
No se impone que las cinco selecciones aleatorias de sensores sean distintas;
se informará su número efectivo, sin volver a sortear para favorecer cobertura.

En cada estación seleccionada se elige sin reemplazo el 30% de sus días
comunes de la etapa, redondeo half-up. Se permiten días consecutivos y ataques
simultáneos entre estaciones; no se exigen inicios a horas aleatorias en este
experimento diario. Un caso ausente del plan tiene etiqueta 0 sólo si está en
la máscara común: un caso excluido no se transforma en negativo.

Las semillas usan listas enteras `[42, 230, uso, factor, ...]`, sin `hash()`;
usos 0–4 separados para ajuste, validación, definitivo, prueba y complementaria.
Los sufijos 0/1/2 separan sensores/días/magnitudes. Se guardan manifiestos,
conteos, escala física y hashes. Los modelos comparten el mismo plan, sin
sorteos internos por detector. Esta generación no revela métricas de examen.

- Calibrar en el periodo limpio reservado p99 (1%) y p99.9 (0.1%) de cada método
  sobre el mismo conjunto de estación-días. Umbral global como RAMA; declarar
  que difiere del umbral móvil por sensor de PARAAD original.
- Usar la misma función de umbral, criterio estricto `puntaje > umbral`, y
  reportar la tasa limpia lograda y su incertidumbre/resolución muestral.
  Si hay menos de 1,000 casos de calibración, p99.9 sólo admite cero alertas
  con ese criterio: advertir su escasa resolución, no simular precisión mayor.
- Congelar modelo, escala, umbrales y planes antes de abrir las métricas de
  prueba. Repetir inferencia dos veces por matriz, sin usar esa repetición para
  modificar el método. Conservar checkpoints completos y sus hashes.
- Métricas: TP/FP/FN/TN, precisión, recall, F1 principal con p99, F2 secundaria,
  p99.9 como segundo punto, falsas alarmas, PR-AUC y ROC-AUC. Conservar las
  mismas etiquetas al puntuar el dato limpio como control «sin ataque».
- IC del 95% y diferencias pareadas mediante bootstrap de bloques estación×mes,
  2,000 remuestreos con semilla predefinida. Las 125 inyecciones no se tratan
  como 125 muestras ambientales independientes: al remuestrear un bloque,
  conservar conjuntamente sus realizaciones de inyección.
- Comparar V4–PARAAD como principal y L0 como referencia supervisada. Reportar
  las dos pruebas temporales, estaciones/cobertura y todos los planes previstos,
  sin seleccionar el año o umbral que favorezca a un detector.

## 9. Entregables y criterios de avance

1. Inventario Barcelona con estaciones identificadas, procedencia y cobertura
   por etapa; decisión explícita sobre subconjunto original frente a conjunto propio.
2. Protocolo congelado, con fechas, horas y faltantes resueltos. Este borrador
   todavía no sustituye ese registro ni autoriza afirmar fidelidad exacta.
3. Ingesta y generación pareada, con pruebas de unidades, horas, fuga temporal,
   inyección, etiquetas y reproducibilidad.
4. Entrenamiento CPU duplicado y calibración limpia, con notebook y respaldos.
5. Examen congelado, tablas, diferencias pareadas y una figura con ficha.

Se avanza ahora en metodología e identificación de datos. No se inicia el
entrenamiento mientras no se resuelvan las estaciones, la cronología y la
convención horaria. Los resultados RAMA quedan como el otro brazo del estudio;
no se reabren para elegir esta configuración ni se sobrescriben.
