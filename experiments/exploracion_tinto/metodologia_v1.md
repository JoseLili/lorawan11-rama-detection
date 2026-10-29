# Metodología de exploración TINTO — propuesta v1.1

Fecha: 2026-10-28. Revisión v1.1: contrastada con V4 y revisiones 14–18b.
Estado: diseño propuesto a partir de la conversación; no es
una revisión adoptada del protocolo de la tesis. No se ejecutó entrenamiento
ni selección con datos reales. Se hicieron ejemplos sintéticos y un inventario.

Nota de conversación (2026-10-28): el tesista aceptó seguir la recomendación
de conservar la metodología común y comenzar por la auditoría de entradas.
Esta autorización permite ejecutar esa preparación; la CNN exacta y el registro
de la revisión para entrenamiento real siguen pendientes. No se habilitan años
de examen ni se modifican los protocolos históricos con esta nota.

## 1. Pregunta y alcance

Pregunta principal: con la misma información y los mismos ejemplos de L0,
¿la representación TINTO seguida de un clasificador de imágenes mejora la
clasificación por estación-día en la exploración de 2022?

Preguntas previas: ¿cuánta información pierde la rasterización?, ¿qué cambia
el difuminado?, ¿el comportamiento de las estaciones conserva relaciones
geográficas? Estas preguntas no se responden contando manchas visibles.

La exploración usa solo 2020–2022. No abrir 2023 ni 2024–2026 para esta fase.
2022 es validación ya utilizada en el proyecto, no un examen independiente.
El paso posterior a años de examen requiere una revisión del protocolo
registrada y aprobada antes de mirarlos. No modificar los resultados aceptados.

## 2. Qué datos usar: decisión propuesta

Fuente común: lecturas RAMA de ozono, máscaras, hora y catálogo de estaciones.
Pero cada detector transforma y selecciona información de forma diferente:

| Familia | Entrada por ejemplo | Información y objetivo |
|---|---|---|
| L0 | 24 × 17 = 408 valores | Objetivo y cuatro vecinas; tres características por sensor más seno/coseno. Supervisa si el objetivo está alterado en t. |
| V4 | 24 × 66 = 1584 valores | Otras 32 estaciones del esquema fijo, sus máscaras y seno/coseno, t−24..t−1. Predice el residuo del objetivo sin usar su lectura como entrada; el detector contrasta después con la lectura observada. |
| V4S | 24 × 68 = 1632 valores | Contexto de V4 pero t−23..t, más relativa y máscara del objetivo. Clasifica con etiquetas. Variante compartida ordena las otras estaciones por distancia. |

Recomendación: familia principal TINTO-L0. Se reutiliza exactamente X de L0,
no se mezclan sus características con las de V4S ni se agregan lecturas crudas.
V4/V4S son posibles familias futuras, cada una con su comparador correspondiente.
Cambiar entrada y representación simultáneamente impide atribuir la diferencia
a la representación. V4 es referencia no supervisada, no control supervisado.

### Contrato de entrada principal

Unidad: (calendario, estación objetivo s, hora final t). Ventana t−23..t.

| Bloque | Columnas por hora |
|---|---:|
| Objetivo: relativa, máscara, comparación con vecinas | 3 |
| Vecina 1 (más cercana): las mismas tres | 3 |
| Vecina 2: las mismas tres | 3 |
| Vecina 3: las mismas tres | 3 |
| Vecina 4: las mismas tres | 3 |
| Seno y coseno de hora | 2 |
| Total | 17 |

Relativa = (lectura − perfil causal de 14 días, media por hora) / sigma de la
estación. La comparación a14 es la diferencia entre esa relativa y el promedio
de las relativas de sus vecinas, dividida por su escala; requiere al menos dos
vecinas con dato. Reutilizar funciones existentes, no reescribir estas fórmulas.
Las cuatro vecinas visibles tienen a su vez comparaciones calculadas usando sus
propios vecindarios: el contexto indirecto de L0 puede exceder cinco estaciones.

La máscara conserva la distinción entre ausencia y un cero numérico imputado.
Usar exactamente la imputación y elegibilidad de L0. No llenar huecos por una
regla nueva. Construir las características sobre la serie con su historia causal
antes de cortar ventanas; nunca usar observaciones futuras para los perfiles.

TINTO recibe una fila de 408 columnas, aplanado por hora y luego característica:
`lag23_obj_rel`, `lag23_obj_mascara`, `lag23_obj_vecinas`,
`lag23_v1_rel`, ..., `lag23_hora_cos`, `lag22_obj_rel`, ..., `lag00_hora_cos`.
Guardar diccionario con nombre, desfase, rol, tipo, unidad/escala y procedencia.
Una imagen representa una estación-hora con historia, no un día calendario fijo.

IDs, fecha absoluta, clave de estación, coordenadas, delta, signo, duración y
columnas de ataque quedan en un manifiesto externo. La etiqueta también es
externa al vector: si la API exige última columna, comprobar que la separa antes
del ajuste y la imagen. No entrenar leyendo el nombre de carpeta de clase.

### Muestras idénticas y normalización heredada

Reutilizar `lstm_local.muestra` con la misma semilla, índices y orden de objetivos
que L0; no basta seleccionar otra muestra de la misma fracción. El documento
inicial sugería una semilla propia; para una comparación estrictamente pareada
esta propuesta fija las MISMAS ventanas. Guardar manifiesto de IDs y SHA-256.

Detalle observado en el código: L0 de selección calcula sigma con la matriz
limpia 2020–2022, heredada del V4; la escala de la columna de vecinas se ajusta
solo con 2020–2021 limpio. Por tanto no describir la comparación existente como
si todo su preprocesamiento se hubiera ajustado exclusivamente con 2020–2021.
Reproducir esa convención en ambos brazos principales y declararla.
V4 y V4S, en cambio, usan normalización inicial 2020–2021 y definitiva
2020–2022 (`entrenamiento_multianual.contexto`). No son idénticos en este punto.

Los ajustes NUEVOS de TINTO (escalador adicional y proyección) usan únicamente
X de entrenamiento 2020–2021. Una sensibilidad con normalización completamente
2020–2021 requeriría volver a entrenar también el control L0 dentro de esta
exploración, sin sobrescribirlo; no mezclarla con el comparador guardado.

## 3. Fase 0: auditoría previa y manifiesto

1. Verificar archivos, hashes, rango temporal, rejilla y catálogo de coordenadas.
2. Reconstruir una muestra pequeña de X usando `entradas_de('vecinas', ...)`,
   `parametros_vecinas('a14', ..., 'media')` y `ventanas_locales`.
3. Comparar elemento a elemento con la construcción de `entrenar_lstm_local`.
   Confirmar 24 × 17, orden de vecinas, extremos de ventana y etiquetas en t.
4. Enumerar columnas constantes, máscaras, duplicadas y rango de continuas.
   No eliminar columnas silenciosamente ni usar 2022 para decidir cómo tratarlas.
5. Guardar muestra canónica, manifiesto y diccionario de 408 columnas; repetir.

Comparador canónico: `results/anomalias_red_v1/lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras`.
Se usa el de SELECCIÓN al comparar en 2022; nunca el definitivo, que aprendió
con 2022. Revisión 2026-10-28: ambos directorios `lstm_local` y
`lstm_local_examen` tienen configuraciones de selección coincidentes y tablas
`dias_2022` numéricamente idénticas (diferencia máxima 0). Los archivos Keras
no tienen el mismo SHA-256; esto no demuestra diferencia de pesos y la auditoría
no la evaluó. Congelar un solo artefacto, el de `lstm_local_examen`, y su hash
`e088514ec45c9939cefd66d850435dec4991d61791ea1440eb18bf6c6be1e932`.

El inventario inicial está en `inventario_datos_20261028.json`: 26 304 horas
limpias, 2020-01-01..2022-12-31, rejilla continua, 32 columnas de valor y 32
máscaras; presentes los 20 archivos d50, los 20 planes, catálogo, modelo de
selección L0 y puntajes 2022. Se leyeron la matriz limpia y cabeceras de d50;
la igualdad numérica se verificó después en la auditoría de 2026-10-28,
con 19 840 ventanas reconstruidas y estadísticas sobre Xtr completo
(ver `auditoria_l0_20261028.md`).

### Escalado nuevo de imágenes

Propuesta inicial: MinMax por columna ajustado una sola vez en X de entrenamiento,
sin recortar valores posteriores fuera de [0,1], sin normalización por imagen.
Guardar mínimos, máximos, columnas constantes y porcentaje fuera de rango.
No interpretar las intensidades de estas imágenes como ppb.

Guardar NPY con números flotantes y comprobar entrada efectiva al clasificador.
PNG/colores solo para visualizar con límites comunes. El control temporal recibe
el MISMO escalado nuevo que TINTO. L0 guardado conserva su escalado original.
La comparación L0 vs imagen cambia también arquitectura y escalado adicional;
los controles de imagen son necesarios para estudiar la representación.

## 4. Experimento 1: resolución y pérdida por colisión

Objetivo: medir conservación de información ANTES de entrenar detectores.

1. Repetir sobre la tabla sintética guardada; después sobre X canónico de L0.
2. Ajustar PCA con entrenamiento solamente. Mantener las coordenadas continuas
   fijas; variar solo su discretización en 32, 64, 128 y 256 píxeles por lado.
   Mantener `zoom=1` y `blur=False`; verificar igualdad de coordenadas PCA.
3. Para cada resolución contar posiciones distintas, grupos de colisión y sus
   miembros (rol, desfase y tipo). Separar constantes de variables.
4. Hacer una prueba numérica por característica no constante: perturbar solo esa
   entrada en el espacio ya escalado, manteniendo las otras 407 fijas; comprobar
   si cambia la matriz. Es una prueba de codificación, no un ataque físico.
5. Registrar proporción de perturbaciones totalmente ocultas y error de
   reconstrucción en el caso sin difuminado. No confundir píxeles modificados
   con detectabilidad del clasificador.
6. Registrar tiempo y tamaño en disco/memoria por imagen. Duplicar el lado
   cuadruplica el número de píxeles, aunque no las características.

Criterio propuesto: elegir la menor resolución sin colisiones que involucren
columnas no constantes y sin perturbaciones ocultas. Reportar además TODAS las
colisiones de constantes. Si ninguna candidata cumple, declarar el límite;
no elegir una por F1 de 2022. Analizar posiciones continuas coincidentes y
alternativas explícitas (mayor resolución o reubicación determinista). Reubicar
sería una variante modificada, que se registra por separado antes de evaluarla.

Salida: tabla resolución/colisiones/perturbaciones ocultas/coste y una figura
con posiciones y grupos compartidos. Esta fase no adopta t-SNE para buscar una
mejor figura: estudiar otro algoritmo sería una comparación adicional.

## 5. Experimento 2: difuminado con mapa y resolución fijos

Objetivo: comprobar qué cambia al extender valores, independiente del umbral.

1. Con la resolución del experimento 1, mantener mapa, entradas y escalado.
2. Tres configuraciones registradas: sin difuminado; distancia 1/pasos 1;
   distancia 1/pasos 2. Misma amplificación pi y combinación por máximo.
3. Comparar perturbaciones individuales y ventanas pareadas normal/alterada;
   contar cambios, medir amplitud, extensión y mezcla entre características.
4. Comprobar tratamiento de valores negativos/fuera de rango en la versión
   instalada, bordes y solapamientos; si no es válido, registrar el fallo y
   corregir el diseño ANTES de entrenar, sin recorte oculto de datos.
5. Conservar las tres variantes para la comparación de detección. No afirmar
   que la de manchas más grandes es mejor ni elegir por inspección visual.

Los parámetros se expresan en píxeles. No cambiar a la vez resolución y radio
para atribuir una diferencia únicamente al difuminado. p99/p99.9 se aplican
después al puntaje diario y no controlan el radio de estas manchas.

## 6. Experimento 3: relación con geografía (diagnóstico separado)

Problema: en TINTO-L0, v1 significa vecina más cercana al objetivo de cada
ventana, no una clave fija. Las 408 posiciones no forman un mapa de la ZMVM.
Un modelo compartido no puede interpretar cada posición como una estación fija.

Pregunta acotada: ¿el comportamiento temporal de las estaciones guarda
relación con su cercanía geográfica?

1. Usar únicamente 2020–2021 limpio y el catálogo congelado de L0
   (`results/inventario_multianual/estaciones_geografia.csv`): una columna por estación,
   una fila por hora, una variable comparable (relativa al perfil causal).
   Documentar estaciones incluidas, huecos y máscaras. No usar etiquetas de ataque.
2. Ajustar PCA de esas columnas para obtener UNA posición por estación, antes de
   rasterizar. Esto es un diagnóstico distinto del mapa principal de 408 columnas.
3. Comparar vecinos geográficos (haversine) con vecinos del plano; registrar
   proporción compartida entre los cuatro más cercanos y correlación de rangos
   entre distancias. Reportar ambas con sus definiciones.
4. Contrastar por 999 permutaciones de etiquetas de estación, semilla derivada de
   42, preservando la geometría de ambos mapas. Las parejas de estaciones no son
   observaciones independientes: no usar un test que suponga eso.
5. Mostrar mapas con claves, unidades y ejes; no inferir correspondencia por la
   silueta o por orientación (PCA puede invertir o girar ejes).

Una imagen colocada con latitud/longitud sería una familia geográfica explícita.
No incorporarla al clasificador principal por defecto: añade información y,
con todas las estaciones, cambia el contexto. Diseñarla después como extensión
con controles que reciban las mismas estaciones y coordenadas. Esta fase es
exploratoria y no selecciona el ganador de detección.

## 7. Experimento 4: detección supervisada en 2022

### Brazos propuestos y qué permiten concluir

- L0 de selección d50 cargado de disco: comparador principal existente.
- CNN sobre matriz temporal 24 × 17: control que conserva el orden horario.
- CNN sobre TINTO: las tres variantes de difuminado del experimento 2, usando
  la resolución elegida por conservación de información, no por F1.

Máximo inicial: cuatro CNN nuevas. Compartir salida sigmoide, pérdida,
optimizador, presupuesto de selección y criterios de parada. Heredar de L0/V4S:
Adam learning rate 0.001, batch 64, `shuffle=True`, entropía cruzada binaria,
sin pesos de clase ni sobremuestreo de positivos; dropout 0.2 y densa de 32
como componentes de referencia para la cabeza clasificadora. La salida es una
sigmoide. La CNN sustituye a la LSTM: sus filtros y capas aún deben fijarse,
no se afirma igualdad de capacidad por compartir optimizador. Definir la CNN,
escalado y configuración completa antes de entrenar. Usar una arquitectura que
admita ambos tamaños (por ejemplo pooling global), registrar número de pesos,
coste y campo receptivo. Una matriz rectangular y una cuadrada inducen distintas
vecindades: compartir arquitectura no vuelve idénticos todos los efectos.
No introducir ViT, híbridos, V4S u otras entradas en este primer barrido.

La diferencia TINTO-CNN vs temporal-CNN informa sobre representación;
TINTO-CNN vs L0 informa sobre los sistemas completos, no prueba por sí sola
que la mejora se deba únicamente al mapa TINTO.

### Datos, selección y métricas

1. Ajustar con 2020–2021, veinte calendarios d50, mismas ventanas de 1/8 de L0.
   Alteraciones siempre sobre lecturas originales antes de recalcular entradas,
   con signos y episodios de los planes existentes. No alterar directamente las
   408 características como sustituto de estos ataques.
2. TINTO fit y escalador nuevo sobre Xtr solamente, compartiendo un mapa para
   todos los objetivos/calendarios; transform para validación. Nunca fit por
   estación, imagen, clase, calendario de validación o intensidad de prueba.
3. Validación/época con 2022 de calendarios 01–10, mismo muestreo de L0,
   `val_loss`, `min_delta=0`, paciencia 8 y máximo 60 épocas, restaurando
   mejores pesos. E es la primera época con mínimo `val_loss`, no la última
   ejecutada; cada variante selecciona su propia E, no se impone la E de L0. Todas las variantes conservan sus resultados;
   elegir por F1 no convierte la validación en un examen independiente.
4. Predicción por estación-hora y promedio de probabilidades de horas con dato,
   mínimo 12 por día, mismas estación-días para todos los brazos.
5. Umbrales exploratorios por detector: p99 principal y p99.9 secundario, usando
   los mismos días de 2022 limpio. Usar el umbral común a las 31 estaciones,
   calculado por `evaluacion_red.umbral_falsas_alarmas`, y alerta estricta `s > u`;
   no reemplazarlo por otro percentil interpolado ni calibrar por estación. No aplicar el valor numérico del umbral de L0
   a otro modelo. Reportar FA nominal y observada; calibración y validación 2022
   se reutilizan y se declara esa limitación.
6. Un solo modelo entrenado con d50; evaluar d100/d50/d20 para la medida
   agregada heredada F̄ = media de F1 a p99 entre esos tres tamaños. Reportar
   además cada delta por separado; d50 es el escenario central, no sustituye F̄
   si se adopta una regla de selección como la histórica. d10/d5 son contraste
   descriptivo del mismo modelo, como en revisiones posteriores, sin seleccionar.
   Guardar F1, recall, precisión, F2, MCC, ROC-AUC y average precision
   (`average_precision_score`, la columna histórica `pr_auc`, no área trapezoidal
   PR), TP/FP/FN/TN y FA observada. Reutilizar `con_umbral` del proyecto.
   Control sin ataque: mismo calendario de etiquetas aplicado al puntaje limpio.
7. Desglosar errores por estación, ausencia de datos y contagio de vecinas;
   no seleccionar modelos diferentes por estación a posteriori.
8. Para incertidumbre en diferencias de F1, bootstrap pareado por bloques
   estación-mes, 2 000 remuestreos, percentiles 2.5–97.5, mismos remuestreos
   para todos los brazos y umbrales fijos; mantener juntas sus repeticiones de
   calendario. Reutilizar la lógica de revisiones 16–18 con una semilla derivada
   de 42 propia de TINTO, registrada antes de calcular, sin usar un número de
   revisión aún no asignado. No cubre incertidumbre de umbral ni entrenamiento; declarar que
   los calendarios comparten señal de fondo y que hay dependencia espacial.
   Es exploratorio, no evidencia confirmatoria de superioridad.

### Regla de selección y eventual fase definitiva

Conservar el precedente de favorecer simplicidad, pero separar regla histórica
de propuesta nueva. En revisión 14 el margen 0.02 se aplicaba entre L0–L3 y
frente a R3; en revisión 16 se elegía el delta de entrenamiento por mayor F̄,
con empate <0.005 a favor del mayor delta; revisión 18b reportaba ambos V4S
sin elegir. No existe una única regla que se pueda copiar literalmente.

Recomendación para fijar ANTES de entrenar TINTO: comparar las tres variantes
con F̄ a p99; dejar la variante sin difuminado salvo que alguna la supere en
al menos 0.02 de F̄. Entre candidatas, preferir la más sencilla si queda a menos
de 0.02 de la mejor. CNN temporal es control, no se oculta si supera a TINTO.
Proponer avance de TINTO solo si supera al L0 único en al menos 0.02 de F̄;
p99.9 y delta individuales se reportan sin seleccionar el umbral favorable.
Este margen y esta extensión del precedente son PROPUESTA, no aprobación
heredada de revisión 14. Si no se adopta la regla, el barrido es descriptivo.

La revisión 14 limitaba nuevas elecciones con 2022; TINTO es una exploración
posterior solicitada por el asesor. Declarar explícitamente esa reutilización y
registrar su revisión antes del entrenamiento real según el protocolo vigente.
El cumplimiento del margen no autoriza automáticamente volver a usar el examen.

Si se acuerda una fase definitiva posterior, mantener el ciclo de V4/L0/V4S:
modelo nuevo con 2020–2022 durante exactamente la E seleccionada, sin
EarlyStopping ni validación nueva; recalcular preprocesamiento de ajuste
(incluido mapa TINTO y escala) solo en ese conjunto y congelarlo. Preservar
resolución/difuminado/arquitectura elegidos y verificar otra vez colisiones del
mapa definitivo: si no cumple el criterio, registrar el problema antes de evaluar.
Calibrar con 2023 limpio únicamente los umbrales de los modelos definitivos,
p99 y p99.9 por estación-día, en días comunes; el p95 por residuo del V4
original pertenece a otra etapa/unidad y no se traslada a TINTO. Evaluar cargando
modelos congelados, una sola vez según la revisión que se adopte. Esta fase
se documenta aquí para coherencia, no se ejecuta en la exploración actual.

## 8. Reproducibilidad, trazabilidad y secuencia de ejecución

- CPU; `fijar_semilla(42)` inmediatamente antes de construir y entrenar modelos,
  conforme a CLAUDE.md. Semillas derivadas sin `hash()` para controles.
- Repetir pipeline numérico y entrenamiento; comparar mapas, X, etiquetas,
  matrices, pesos y puntajes, antes de interpretar diferencias pequeñas.
- Versionar la propuesta, configuración, entorno, hashes y manifiestos; indicar
  modelo recién entrenado o cargado. Mantener el lock de tesis y entorno aparte.
- Carpeta propia: código/diseño en `experiments/exploracion_tinto/`, salidas en
  `results/exploracion_tinto_2022/`, sin sobrescribir resultados existentes.
- Figura siempre con fuente, X/Y, escala, unidades, métrica y limitaciones.
- Orden: adoptar el diseño de exploración según el protocolo → auditoría X →
  resolución → difuminado → diagnóstico geográfico → congelar CNN y regla de
  selección → entrenar/evaluar solo 2022 → informe para decidir siguiente fase.

Siguiente trabajo concreto: extractor canónico de 408 columnas, manifiesto de
ventanas idénticas a L0 y auditoría de constantes/rangos. El inventario prueba
presencia de archivos, no sustituye esa verificación.

## 9. Fuentes dentro del repositorio

- `docs/protocolo_lstm_v4_multianual.md`: separación inicial/definitiva y normalización.
- `docs/inicio_exploracion_tinto.md`: punto de partida, no protocolo adoptado.
- `docs/protocolo_anomalias_red_v1.md`: reglas y revisiones 14, 18 y 18b.
- `src/detect/lstm_local.py`: contrato 17 columnas, orden y muestreo.
- `src/detect/evaluacion_red.py`: relativas, normalización y comparación a14.
- `experiments/anomalias_red/entrenar_lstm_local.py`: construcción real de X.
- `src/detect/entrenamiento_multianual.py`: V4, 66 columnas y desfases.
- `src/detect/v4_supervisado.py`: V4S, 68 columnas y roles por distancia.
- `src/detect/estacion_dia.py`: agregación y etiquetas.
- https://tintolib.readthedocs.io/en/latest/tinto.html : parámetros de representación.


## 10. Conciliación v1.1 (2026-10-28)

Revisión documental y de código, sin inferencia nueva ni acceso a matrices de
examen: se mantienen división temporal, perfiles causales, máscaras, etiquetas,
muestreo, agregación diaria, controles sin ataque y reproducibilidad existentes.
Se precisaron optimizador/lotes/pérdida, métricas completas, umbral discreto,
bootstrap, artefacto canónico de L0 y ciclo definitivo futuro.

Lo nuevo es el mapa/escala TINTO, resolución, difuminado y CNN, más un diagnóstico
geográfico separado. No se trasladan la salida MSE del predictor V4 ni su p95 de
errores a un clasificador. No se cambian protocolos ni artefactos de V4/V4S/L0.
La regla 0.02 para TINTO y el ciclo futuro son propuestas explícitas para adoptar
antes de ejecutar, no decisiones ya aprobadas por otras revisiones.


## 11. Ejecución del experimento 1 (2026-10-28)

Autorizado por el tesista después de la auditoría. Se ajustaron escalador y PCA
sobre las 19 840 ventanas canónicas de entrenamiento, sin ajuste con validación.
Ninguna resolución 32/64/128/256 cumple el criterio fijado para L0. Se preserva
el criterio y el resultado negativo; no se adopta resolución ni se ejecuta aún
el barrido de difuminado de detección. El siguiente diagnóstico propuesto debe
separar colisiones de características diferentes y redundancia horaria, antes
de registrar cualquier cambio de rasterización. Informe completo:
`resultados_resolucion_20261028.md`.

## 12. Diagnóstico de redundancia (2026-10-28)

Solicitado antes de eliminar entradas. Reconstrucción horaria 48→2 validada
sobre la muestra con error máximo 1.72e−8. Se distinguió a14 de L0 frente a
R3; reconstruir a14 del objetivo requiere escala externa y disponibilidad de
perfil, y la de las vecinas generalmente usa contexto fuera del grupo visible.
No se declara eliminable ninguna a14 por su sola relación algebraica. Máscaras
siguen distinguiendo ceros observados de ceros imputados. Geografía es otra
codificación que debe separar estación/tiempo/tipo. Se propone, sin ejecutarlo
aún, comparar mapa original de 408 contra hora compacta de 362. Informe:
`redundancia_l0_20261028.md`. No se modificaron entradas ni modelos originales.

## 13. Comparación 408 frente a 362 (2026-10-28)

Autorizada por el tesista tras el diagnóstico. Mismo conjunto auditado de ajuste,
PCA propio por variante y resoluciones 32/64/128/256, sin difuminado. Se conservó
hora final y se validó reconstrucción horaria, sin retirar otros bloques.
Ambas variantes fallan el criterio de conservación en los cuatro tamaños.
La medida sobre las mismas 360 columnas de sensores mejora diez columnas a 256,
no las 45 que sugeriría comparar conteos totales con diferente número de entradas.
Se mantiene el resultado sin seleccionar resolución. Informe:
`resultados_hora_compacta_20261028.md`. Ningún modelo L0 se modificó.

## 14. Prototipos de conservación (2026-10-28)

Aceptado estudiar asignación única y canales antes de retirar más entradas.
Se probó una variante explícita de rasterización PCA mediante asignación de
coste mínimo a píxeles únicos, lados 32/64 para 408/362 entradas. Cero cambios
individuales ocultos, reconstrucción exacta en escala MinMax sobre la muestra
completa; cambia vecindades PCA y no demuestra mejora de detección. También se
verificó el control temporal 24 × 5 × 3 con hora aparte, sin pérdida numérica.
Dos corridas idénticas. No se aplica difuminado ni se entrena una CNN. Informe:
`resultados_prototipos_20261028.md`. Se conserva original como control.

## 15. Piloto técnico antes del entrenamiento científico (2026-10-29)

Confirmada la prioridad de mantener TINTO. Se probó la variante PCA + asignación
única 32 × 32 con 408 entradas y una CNN pequeña, solo para funcionamiento.
Dos corridas idénticas en pesos/historias; sin validación independiente ni
comparación con L0. El control sintético cumplió aciertos pero no la pérdida
<0.1 prefijada, por lo que NO se declara superado todo el piloto ni se habilita
el examen. Configuración, excepción inicial de metadatos de keras-nightly y
resultados documentados en `piloto_cnn_20261029.md`. La arquitectura es piloto,
no se adopta como detector científico definitivo por estos resultados.

## 16. Configuración y programa preparados (2026-10-29)

Se concretó un único candidato: 408 entradas, mapa PCA y escalador congelados
del ajuste sobre 19 840 ventanas, asignación única 32 × 32 sin difuminado,
CNN 8/16 filtros + densa 32/dropout 0.2/sigmoide (34 081 parámetros).
`configuracion_entrenamiento_v1.json` y `runbook_entrenamiento_v1.md` fijan
la preparación y entrenamiento de selección. Caché completa cotejada con
hashes X/y de L0; prueba de flujo de dos épocas repetida, sin diferencias.
El entrenamiento completo y las métricas contra L0 todavía no se ejecutan.
Se preserva el resultado del piloto sintético, sin cambiar su criterio.


## 17. Registro T1 y cierre manual (2026-10-29)

Se registró T1 antes de entrenar y se ejecutaron dos corridas completas de
selección con CPU optimizada y configuración fija. Por solicitud posterior
del tesista se detuvieron antes de cumplir paciencia 8: ocho épocas completas
en una y nueve en la otra. Se preserva el checkpoint de época 5, mejor observado
en ambas. Historias de ocho épocas comunes e internos HDF5 de checkpoints
idénticos. Cierre manual documentado; no es selección terminada por la regla
original ni evidencia de superioridad. No se continúa automáticamente.
Informe: `results/exploracion_tinto_2022/seleccion_tinto_v1/informe_cierre_manual.md`.

## 18. Cierre de evaluación y alcance real (2026-10-29)

T1 se evaluó en Colab CPU con modelos de disco (TINTO época5 y L0 d50),
sin reentrenar. Dos corridas idénticas: 31 matrices por corrida, 9661
estación-días comunes por calendario, diez calendarios y δ100/50/20,
p99/p99.9 de limpio2022. L0 tiene mayor F1 y recall en las seis condiciones.
F̄ p99 descriptiva: TINTO0.3083 frente a L00.3550. Se conserva la parada
manual y reutilización de2022 como límites. Barrido de difuminado, análisis
geográfico cuantitativo y CNN temporal permanecieron como propuestas, no
experimentos completados; este cierre no los requiere ni autoriza examen.

Por solicitud del tesista se documenta el conjunto y se visualiza una ventana
real limpia/alterada usando el mapa y escalador congelados, sin predicciones
nuevas. Referencia vigente y fichas: `docs/cierre_exploracion_tinto_t1.md`.
