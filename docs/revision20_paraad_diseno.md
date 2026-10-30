# Revisión 20 — PARAAD: lectura contrastada y diseño propuesto

Fecha: 2026-10-27. Estado al 2026-10-28: **selección iniciada en Colab CPU,
tras comprobaciones satisfactorias; sin calibración ni examen**.
Actualización 2026-10-28: el tesista confirma llevar PARAAD a RAMA como ruta de
comparación y solicita explicar las diferencias entre ambos trabajos. La elección
de ruta no se presenta como una reproducción exacta del experimento de Barcelona.
Tras discutir la comparación, el tesista solicita «empecemos a preparar todo
para traer a PARAAD». Se procede con la adaptación descrita aquí, con el rastro
de sus diferencias y sin volver a solicitar la misma autorización.
Todavía no hay resultados nuevos de detección. La revisión 21 queda reservada
para el error fijo en ppb. Este documento nuevo no modifica el protocolo ni el progreso
compartidos mientras se cierra la revisión 19.

## 1. Fuentes verificadas

- Allka et al. (2024), *Pattern-Based Attention Recurrent Autoencoder for Anomaly
  Detection in Air Quality Sensor Networks*, DOI: [10.1109/TNSE.2024.3454459](https://doi.org/10.1109/TNSE.2024.3454459).
  Se leyó el PDF publicado disponible localmente en `docs/`; no se incorpora a Git.
- [Repositorio de la primera autora](https://github.com/XhensildaAllka/PARAAD),
  commit inspeccionado `6dbb5a9144a043d7825d63f49463a442ae60165b`, de 2023-10-01.
  Contiene cinco archivos Python y un README mínimo, sin datos, ejecutor completo,
  dependencias fijadas ni archivo LICENSE en la raíz. Es anterior al artículo final:
  no damos por hecho que sea exactamente la versión de sus tablas.
- [Portal de datos indicado por el tesista y el artículo](https://mediambient.gencat.cat/es/05_ambits_dactuacio/atmosfera/qualitat_de_laire/vols-saber-que-respires/descarrega-de-dades/descarrega-dades-automatiques/).
  Enlaza el [dataset `tasf-thgu`](https://analisi.transparenciacatalunya.cat/es/Medi-Ambient/Qualitat-de-l-aire-als-punts-de-mesurament-autom-t/tasf-thgu).
  Metadatos consultados mediante `https://analisi.transparenciacatalunya.cat/api/views/tasf-thgu.json`.
  Hay código EOI, estación, municipio, fecha, contaminante, unidades, columnas
  `h01`…`h24` y coordenadas. Tener acceso a esta fuente no identifica todavía
  el subconjunto procesado usado por los autores.

Estas verificaciones corrigen las notas preliminares de `inicio_paraad.md`, sin
reescribirlas ni atribuirles certeza que expresamente no tenían.

### Comparación conceptual solicitada el 2026-10-28

| Característica | PARAAD publicado | Nuestro escenario RAMA / L0 |
|---|---|---|
| Datos reales | O3 horario, ocho estaciones, 2014–2019; 1,008 bloques por sensor reportados | O3 horario, 2020–2026 parcial; 32 estaciones de contexto y 31 objetivos; disponibilidad desigual |
| Uso de vecinas | Reconstruye conjuntamente las ocho estaciones con atención; no selecciona cuatro por distancia | L0 usa la estación objetivo y sus cuatro vecinas geográficas; un modelo compartido entre objetivos |
| Aprendizaje | Reconstrucción de observaciones normales, sin etiquetas de ataque en el ajuste del autoencoder | Clasificación supervisada con calendarios de anomalías sintéticas |
| Tiempo | Un día como patrón de 24 valores por sensor; BiLSTM recorre sensores | Ventanas horarias de 24 pasos; se reúnen los puntajes horarios por estación-día |
| Anomalías | Sesgo aditivo positivo y deriva progresiva; también experimentos con datos sintéticos | Incremento o reducción proporcional, cinco magnitudes, episodios de 1–7 días; escenarios con concurrencia y de una sola estación |
| Decisión | Error de reconstrucción y umbral móvil por sensor seleccionado por exactitud | Probabilidad media diaria de L0 y umbrales fijos calibrados en 2023 limpio |
| Faltantes | Interpolación limitada y descarte de bloques | Se preservan huecos con máscaras; mínimo de 12 horas válidas por estación-día |

Más estaciones no implica automáticamente más información útil: importan la
cobertura, las distancias y la relación entre las series. Tampoco se atribuye una
ventaja a «megalópolis contra ciudad pequeña»: no se identifican todavía las ocho
estaciones exactas de PARAAD y no se ha medido su distribución espacial frente a
RAMA. Meteorología, topografía y régimen de O3 son hipótesis explicativas que
requieren datos, no conclusiones de esta comparación.

Al ejecutar ambos detectores sobre RAMA se fija el territorio. La comparación
mide el desempeño bajo datos, ataques, calendarios y criterios comunes; no aísla
un efecto de tamaño urbano. L0–PARAAD es contraste práctico con distinta
supervisión; V4–PARAAD contrasta dos ajustes sin etiquetas de ataque. Ninguno
constituye por sí solo una ablación de arquitectura.

## 2. Qué implementa PARAAD y qué falta resolver

| Aspecto | Artículo publicado | Código público inspeccionado / consecuencia |
|---|---|---|
| Entrada | M bloques × S sensores × D horas; D=24 | Las clases construyen secuencias de sensores con 24 características. Sin embargo, `DataConcatDaily` devuelve días × horas × sensores: falta el ejecutor que aclare la transposición. Debemos verificar ejes explícitamente. |
| Variantes | SA, MH y Ba | Están las tres; nuestras notas sólo mencionaban dos. |
| Codificador | Atención y dos BiLSTM | Primera BiLSTM: 7 unidades por dirección, activación lineal y secuencia de salida (14 características). Segunda: 2 por dirección, ReLU, sin secuencia (vector total de 4). El texto describe D2=4; no implementaremos por accidente 4 por dirección. |
| Decodificador | Atención, BiLSTM y salida de D valores | Repite el vector latente S veces, aplica atención, BiLSTM de 7 por dirección y Dense(24) por sensor. |
| Atención SA | Ecuación de producto punto escalado | Código usa `keras_self_attention.SeqSelfAttention`, anchuras 24 y 4, `attention_activation='sigmoid'`. No sustituir silenciosamente por atención de producto punto: verificar implementación y versión de esa dependencia antes de reproducir SA. |
| Atención MH | 2–3 cabezas según tamaño | `key_dim=24` al entrar y 4 después del cuello de botella. |
| Optimización | Adam 0.01 y MSE | SA: 0.01, `clipnorm=1`; Ba: 0.01; MH: cadena `'adam'`, sin usar el argumento `learning_rate`. Hay discrepancia para MH. |
| Entrenamiento real | 500 épocas, lote 256; dropout entre 0.1 y 0.5 | `shuffle=False`, dropout sólo a la entrada. No se publica la tasa concreta de cada experimento. |
| Puntaje | Ecuación (5): MAE por sensor y bloque | Promedio de errores absolutos, **no** absoluto del promedio firmado que usa el V4. La pérdida MSE y el puntaje MAE cumplen funciones distintas. |
| Umbral | Por sensor, maximiza exactitud en ventana previa W=30, aplica al bloque siguiente | La selección descrita requiere etiquetas para calcular exactitud; no aparece implementada en los archivos publicados. El autoencoder puede entrenar sin etiquetas, pero ese procedimiento de umbral no es calibración sólo con datos normales. |
| Sesgo | 30% de sensores, 30% de bloques, desplazamiento no negativo; σ=2 | `biasAnomalies` usa `scipy.stats.truncnorm.rvs(0.2,2,0,scale=sigma_Sens[sensor])`, no valor absoluto de una normal. Para σ=2, soporte 0.4–4.0. La elección de sensores se deja a `sigma_Sens`; no está el ejecutor. |

La BiLSTM recorre sensores, con el día representado por 24 características; no es
una LSTM recorriendo las 24 horas. El orden de estaciones, por ello, debe quedar
guardado y ser idéntico en ajuste e inferencia.

## 3. Barcelona: acceso confirmado, reproducción aún no identificada

El artículo describe ocho estaciones, años 2014–2019 y 24,192 observaciones por
sensor: equivalen a 1,008 bloques de 24 h, no a seis años completos. Describe
interpolar un faltante aislado por bloque con los valores anterior y posterior,
y descartar bloques con más faltantes; no queda completamente especificada la
alineación conjunta de sensores. Tampoco proporciona los ocho códigos EOI, sus
fechas exactas, el orden, el ajuste preciso de la estandarización o un ejecutor
que reconstruya la partición 90/10.

Para la reproducción se necesita:

1. Identificar estaciones y fechas; preservar unidades originales y aclarar la
   convención horaria de `h01`…`h24` antes de asignar timestamps.
2. Descargar únicamente O3 y el periodo necesario, guardar consulta, fecha,
   respuesta original y SHA-256. Auditar duplicados, faltantes y unidades.
3. Resolver las diferencias artículo/código; documentar cada decisión. Si no se
   identifica el subconjunto, llamarlo reconstrucción propia con datos de la
   misma fuente, no reproducción exacta de sus tablas.
4. Contrastar aproximadamente la tabla I sólo después de cerrar esas decisiones;
   no ajustar hasta conseguir sus números. No trasladar sus métricas publicadas
   directamente a la tabla RAMA.

No se ha contactado a los autores. Una consulta sobre estaciones/fechas y versión
de código sería útil si el material disponible no lo resuelve.

Consulta agregada realizada: el portal devuelve 50 combinaciones de código,
nombre, municipio y unidad para O3 entre 2014 y 2019; seis pertenecen al municipio
Barcelona (Eixample, Gràcia–Sant Gervasi, Ciutadella, Parc Vall Hebron, Palau Reial
y Observatori Fabra). Esto no basta para identificar las ocho del artículo:
no asumir que «Barcelona» limita la selección al municipio. Se conserva el
catálogo con consulta y fecha en `data/reference/paraad_catalogo_o3_2014_2019.json`.
Los conteos del catálogo son filas, no garantizan 24 horas válidas. Sus unidades
para esas seis estaciones son µg/m³, no ppb.

## 4. Auditoría de viabilidad en RAMA (sólo 2020–2022)

Se consultó `data/processed/o3_2020_2026_ancho.parquet` con filtro de lectura
`2020-01-01 <= timestamp < 2023-01-01`, las columnas de `ESTACIONES` menos XAL,
y rejilla horaria continua. No se inspeccionaron datos ni métricas de examen
para tomar esta decisión. Los recuentos son cobertura, no resultados de un modelo.

| Año | Días | Días con 32 sensores completos | Días con ≥23 h en cada sensor | Sensores sin ninguna observación ese año |
|---|---:|---:|---:|---|
| 2020 | 366 | 0 | 0 | ACO, CHO |
| 2021 | 365 | 0 | 0 | AJM, HGM |
| 2022 | 365 | 0 | 0 | HGM |

Exigir bloques completos para toda la red deja **cero ejemplos** incluso
tolerando un faltante por estación. Eliminar estaciones cambiaría el escenario
y dejaría fuera objetivos de la comparación. Por eso hace falta una adaptación
explícita a faltantes, no lanzar directamente el entrenamiento del artículo.

## 5. Propuesta concreta para aprobación: PARAAD-SA adaptado a RAMA

### Qué se conserva

- Entrenamiento sin etiquetas de ataque. Comparación principal con V4;
  L0 único d50, V4S compartido y R3 como referencias, identificando su supervisión.
- Un modelo de red; días 00–23; entrada `(día, 32, 24)`, orden `ESTACIONES` sin
  XAL; HGM sólo contexto y 31 objetivos evaluados. PARAAD compartido y V4 por
  estación no tienen igual número de modelos: se declara, no es ablación pura.
- Arquitectura SA del código referenciado, tras verificar la dependencia de
  atención; BiLSTM 7/2/7 por dirección, repetición del vector de 4 valores,
  salida de 24, Adam 0.01, clipnorm 1, lote 256, `shuffle=False`.
- MSE para ajustar; MAE para puntuar. PARAAD reconstruye también la lectura
  observada del objetivo; V4 predice desde otras estaciones y contexto previo.
  Esta diferencia es parte de los métodos y se declara.

### Adaptación mínima a faltantes propuesta

- Estandarizar cada sensor con media y desviación (`ddof=1`, como RAMA) de
  observaciones de ajuste. Desviación cero se sustituye por 1; sensor sin dato
  en todo el ajuste detiene la preparación para resolverlo antes de entrenar.
- Rellenar faltantes con 0 **en espacio estandarizado**. Es un valor de entrada
  neutral equivalente a la media del ajuste; no interpolar ni inventar etiquetas.
- Conservar una máscara de observación aparte. No añadirla a las 24 características
  en esta propuesta: se mantiene la forma de entrada. La limitación es que el
  encoder no distingue una media observada de un faltante relleno.
- Pérdida: suma de errores cuadrados sólo observados dividida por su número,
  por bloque; promedio entre bloques no vacíos. Excluir bloques completamente
  vacíos, con registro explícito. El relleno no es objetivo de reconstrucción.
- Puntaje por estación-día: MAE sobre horas observadas; no puntuar con menos
  de 12 horas. La máscara depende sólo de disponibilidad, nunca de etiquetas
  ni de valores del puntaje. Usar estandarización congelada también bajo ataque.
- En las tablas usar exactamente la máscara común de las revisiones 18/19;
  comprobar que PARAAD produce puntaje en todas esas filas. Si no, detener y
  documentar: no comparar filas diferentes ni reducir la tabla en silencio.
- Nombre de resultados: **PARAAD-SA adaptado (faltantes y umbral RAMA)**.
  No presentarlo como ejecución idéntica del artículo.

### Selección y congelación antes del examen

1. Ajuste inicial 2020–2021, validación limpia 2022. Normalización sólo de
   2020–2021 en esta fase. Se fija SA de antemano; no se elige variante por F1.
2. Propuesta de búsqueda pequeña: dropout `{0.1, 0.3, 0.5}`, 500 épocas cada
   candidato. Elegir candidato y época por menor MSE enmascarada global de
   validación; empates: menor dropout, después primera época. No usar ataques
   de 2022 para seleccionar este modelo no supervisado.
3. Ajuste definitivo desde cero con 2020–2022, normalización recalculada sólo
   allí, dropout y número de épocas elegidos. Guardar modelo, orden, configuración,
   versiones, datos/checksums e historial. No escoger entre semillas.
4. Sólo CPU. Limpiar sesión antes de `fijar_semilla(42)`; llamar la función
   inmediatamente antes de construir y nuevamente antes de entrenar. Ejecutar
   dos veces todo el proceso y verificar igualdad de selección, pesos y puntajes
   en el mismo entorno. El hash del contenedor `.keras` por sí solo no demuestra
   igualdad numérica. El tesista ejecutará el entrenamiento largo.
5. Calibrar 2023 limpio con la función existente de falsas alarmas, sobre las
   mismas estación-días comunes: p99 y p99.9. Congelar ambos umbrales. Se cambia
   expresamente el umbral original del artículo; por eso no se repite una única
   fila en ambas tablas. No optimizar exactitud con etiquetas de examen.
6. Registrar en protocolo y progreso cuando el tesista cierre la revisión 19,
   **antes del examen**. Ejecutar 2024 y la extensión registrada 2025–2026 una
   sola vez con modelo/umbrales congelados. Esos años ya tienen resultados
   conocidos de otros métodos; no llamarlos un examen totalmente nuevo e intacto.
7. Reutilizar los calendarios existentes, cinco δ, escenario original y escenarios
   A/B de revisión 19. Calcular de nuevo las reconstrucciones de la red alterada.
   Conservar F1/F2, precisión, recall, falsas alarmas, control sin ataque e IC
   con las mismas definiciones y unidades que los comparadores.

## 6. Entregables siguientes tras aprobar la adaptación

- `src/detect/paraad.py`: modelo, pérdida enmascarada y puntajes; nombres y formas
  explícitos; no modificar `src/detect/anomalias_red.py`.
- `experiments/anomalias_red/entrenar_paraad.py`: selección y ajuste definitivo
  en etapas separadas, sin cargar 2024–2026 durante selección.
- Evaluación nueva que reutilice calendarios, máscaras y métricas existentes;
  directorio exclusivo `results/anomalias_red_v1/revision20/`.
- Pruebas necesarias: orientación sensor/hora, pérdida/MAE con faltantes,
  separación temporal, serialización y repetición determinista de una prueba
  pequeña en CPU. Notebook de ejecución con entrenamiento desactivado por defecto.

Decisión solicitada: aprobar o corregir la adaptación de faltantes y la regla
de selección anterior. `docs/inicio_paraad.md` exige registrar y aprobar el diseño
antes de programar. El acceso al dataset ya está aclarado; esta decisión nueva
surge de la cobertura nula de bloques completos, no de una falta de acceso.

## 7. Preparación implementada el 2026-10-28

La solicitud anterior queda atendida por la autorización de preparación de esta
fecha. Ver `docs/runbook_paraad_revision20.md` para comandos y límites actuales.

- Se verificó la atención en CyberZHG/keras-self-attention, commit
  `f3bf21dbb1f3251b5417a8bb254dd91807b1aec5`, archivo
  `keras_self_attention/seq_self_attention.py`. Es aditiva por defecto, con
  32 unidades internas, inicialización Glorot normal, sesgos cero, sigmoid
  de la emisión y después softmax local. Se implementa esa fórmula con
  TensorFlow actual, comprobada contra una implementación NumPy independiente.
  No se conoce la versión exacta utilizada por los autores en 2023.
- Las anchuras 24 y 4 son ventanas sobre **sensores**, no horas. En 32 sensores
  la primera atención no abarca todas las parejas; se conservan las anchuras
  publicadas sin ampliarlas después de ver resultados. El orden fijo importa.
- Dropout usa semilla 42 en lugar del 2 explícito del código público; se aplica
  la regla de reproducibilidad del proyecto. No se afirma identidad numérica
  con modelos entrenados por los autores.
- La validación minimiza la media de MSE por bloque observado (la misma
  ponderación de la pérdida de entrenamiento), no una media que dé más peso
  a bloques con más observaciones. Se eliminan únicamente bloques enteramente
  vacíos del entrenamiento, registrando su número.
- Selección y definitivo se ejecutan dos veces automáticamente. Se compara la
  historia completa, pesos finales y predicciones; la elección de época queda
  determinada por la historia idéntica. El definitivo además compara los MAE.
- La auditoría real sólo abrió 2020–2022. La prueba de entrenamiento y
  serialización usó cuatro días **sintéticos**, una época y CPU; igualdad exacta.
  No son resultados de detección ni un estimador de F1.
- El puntuador admite matrices existentes de RAMA y una máscara común externa
  producida por los comparadores. No calcula métricas nuevas de los otros
  detectores ni sustituye la evaluación conjunta de revisiones 18/19. Su
  integración final y los IC se ejecutarán después de congelar el modelo.
- No se modificaron los archivos compartidos protegidos de la revisión 19.

## 8. Expectativas previas, no resultados de PARAAD en RAMA

El artículo, tabla I para datos reales y sesgo σ=2, reporta PARAAD-SA con
recall 0.81 y precisión 0.84. Son resultados de otro conjunto de datos,
prevalencia, inyección y umbral; no constituyen una predicción de F1 en RAMA.

Se consultaron únicamente resultados **ya registrados** de L0 para responder
la pregunta del tesista, no para elegir PARAAD: revisión 18, L0 único,
2025, estación-días comunes, con ataque, p99. F1: d100=0.404, d50=0.445,
d20=0.176, d10=0.030, d5=0.018 (redondeados). La fuente es
`results/anomalias_red_v1/revision18/resultados.csv`; L0 cargado de disco.

Hipótesis previas: mayor señal ante cambios grandes; dificultad en d10/d5;
posible competencia con V4, sin asegurar ventaja. L0 podría beneficiarse de
haber entrenado con los ataques del escenario; PARAAD podría reconstruir
parcialmente una anomalía y reducir su propio error. Cualquiera de esos
efectos debe medirse, no asumirse. Más estaciones también elevan las exigencias
de una compresión de cuatro valores y el impacto de datos ausentes.

La precisión depende de la prevalencia: con 1% de positivos, recall 0.8 y
falsas alarmas 0.01, la precisión sería 0.008/(0.008+0.0099)≈0.447.
Es sólo un ejemplo aritmético, no una estimación de PARAAD. No se anticipa
un valor numérico de desempeño ni se ajustará el método para cumplir estas expectativas.
