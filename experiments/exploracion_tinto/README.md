# Aula TINTO: primer ejercicio (2026-10-28)

> **Estado vigente: piloto T1 cerrado (2026-10-29).** Evaluación Colab terminada,
> dos corridas idénticas, resultados descargados y sesión liberada. L0 supera
> el F1/recall de este candidato en las seis condiciones exploratorias.
> Ver [documentación integral](../../docs/cierre_exploracion_tinto_t1.md) e
> [informe de evaluación](informe_evaluacion_colab_20261029.md). Las secciones
> siguientes conservan cronológicamente lo conocido en cada etapa: sus
> menciones a trabajos aún pendientes no describen el estado actual.


Ejecutado con TINTOlib 1.3.1 real, Python 3.14.7 y CPU. Es una demostración
con números inventados: no usa datos RAMA, años de prueba ni modelos de la tesis.
La carpeta de resultados contiene `2022` por la convención de la exploración,
pero este ejercicio NO usa observaciones de 2022.

## Qué hicimos

1. Construimos una tabla de ajuste de 64 filas y ocho características F1–F8.
   Incluye una fila de ceros y otra de unos; las restantes usan números
   pseudoaleatorios con semilla 42. Cada característica abarca exactamente 0–1.
2. Ajustamos TINTO con `fit`: escalado MinMax y mapa PCA de características.
   PCA se aplica a la tabla transpuesta: se ubican las ocho características,
   no las 64 observaciones. Las coordenadas se discretizan en 32 × 32 píxeles.
3. Transformamos tres observaciones nuevas con el mismo mapa:
   - A: ocho valores de 0.25, etiqueta 0.
   - B: iguales, pero F3 pasa de 0.25 a 0.75, etiqueta 0.
   - C: los mismos valores de A, etiqueta 1.
4. Repetimos con difuminado: distancia 1, dos pasos, combinación por máximo.
5. Repetimos todo desde cero en una segunda carpeta.

El escalador se ajusta exclusivamente con las 64 filas iniciales. La etiqueta
se entrega en la última columna según la API de clasificación, pero se separa
de las características. Los nombres F1–F8 se agregaron a la figura para explicar:
no están escritos dentro de las matrices que genera TINTO.

## Cómo leer explicacion.png

- Columnas de paneles: A, B y diferencia numérica B − A.
- Fila superior: sin difuminado; inferior: con difuminado.
- Eje X: columna del píxel, de 0 a 31.
- Eje Y: fila del píxel, de 0 a 31; aumenta hacia abajo.
- Color: valor numérico de la matriz, escala fija 0–1. En la tercera columna
  representa el cambio, con la misma escala. No es probabilidad de anomalía.
- Fuente: las tablas inventadas `ajuste_inventado.csv` y `observaciones.csv`.
- Tipo de medida: intensidades y diferencias de intensidades; no son métricas
  de rendimiento ni valores de ozono.

Los colores se aplican solo al dibujar la explicación. Se guardan las matrices
originales en `.npy` para comprobar los números antes de cualquier conversión
visual o cuantización a PNG. El negro de fondo es cero; un valor cero también
podría corresponder a una característica, por lo que el mapa es necesario.

## Qué verificamos

- Ocho características ocupan ocho posiciones distintas en este ejemplo.
  TINTO no garantiza que siempre ocurra: hay que comprobar colisiones.
- F3 ocupa fila 19, columna 24, con índices desde cero.
- A → B modifica un píxel sin difuminado: 0.25 → 0.75 (diferencia 0.50).
- Con este difuminado, A → B modifica 13 píxeles.
- A y C son numéricamente idénticas: la etiqueta cambia la carpeta, no la imagen.
- Cambiar las etiquetas del conjunto de ajuste tampoco altera las imágenes.
- Las dos corridas tienen matrices exactamente iguales (huellas SHA-256 y
  `verificaciones.json` idénticos).

Origen: transformación PCA recién ajustada en cada corrida; no se cargó ningún
modelo ni se entrenó una CNN. Estas comprobaciones no demuestran capacidad
para detectar anomalías ni superioridad sobre L0.

## Repetir

Desde la raíz del repositorio, usar un entorno separado. El entorno usado en
esta sesión fue `/tmp/tinto-aula-venv`, con acceso a paquetes científicos del
sistema. Es temporal. El entorno y el lock de la tesis no se modificaron.

```sh
python3 -m venv /tmp/tinto-aula-nuevo
/tmp/tinto-aula-nuevo/bin/python -m pip install -r experiments/exploracion_tinto/requirements-aula.txt
MPLCONFIGDIR=/tmp/tinto-mpl /tmp/tinto-aula-nuevo/bin/python experiments/exploracion_tinto/ejemplo_minimo.py --salida results/exploracion_tinto_2022/aula_nueva/corrida1
MPLCONFIGDIR=/tmp/tinto-mpl /tmp/tinto-aula-nuevo/bin/python experiments/exploracion_tinto/ejemplo_minimo.py --salida results/exploracion_tinto_2022/aula_nueva/corrida2
cmp results/exploracion_tinto_2022/aula_nueva/corrida1/verificaciones.json results/exploracion_tinto_2022/aula_nueva/corrida2/verificaciones.json
```

El script exige carpetas nuevas para conservar las corridas anteriores. El archivo
requirements fija las bibliotecas principales; no es un lock completo. Las versiones
observadas se guardan en cada `verificaciones.json`. La igualdad entre máquinas o
versiones distintas debe comprobarse de nuevo.

## Fuentes oficiales consultadas

- https://tintolib.readthedocs.io/en/latest/tinto.html
- https://github.com/oeg-upm/TINTOlib
- Implementación instalada: TINTOlib/tinto.py, abstractImageMethod.py y mappingMethod.py.

Después de comprender este ejercicio podemos pasar a una tabla con relaciones
controladas entre columnas y observar cómo cambia el mapa; luego a ventanas
temporales inventadas. El entrenamiento del detector es una etapa posterior.

## Segundo ejercicio: una ventana temporal inventada

Script: `ventana_inventada.py`. Se ejecuta con el mismo entorno e idéntica
opción `--salida`, siempre a una carpeta nueva.

Usamos 24 horas de cinco sensores (objetivo y cuatro vecinas), es decir, 120
características. Es una simplificación didáctica: NO incluye las relativas,
máscaras y comparaciones de vecinas de las 17 entradas de L0. No usa RAMA.
Las curvas son inventadas, expresadas como ozono en ppb solo para interpretarlas.

- Ajuste PCA: 128 días inventados independientes de los dos casos ilustrados.
- Normal: un día nuevo inventado; alterada: el mismo día con el objetivo ×1.5
  durante las 24 horas. Las cuatro vecinas quedan exactamente iguales.
- Tabla entregada: cada fila es un día; se aplana por hora y luego por sensor.
  Los nombres de columnas incluyen ambos (`h00_Objetivo`, etc.). La etiqueta
  va al final y no forma parte del mapa ni de las intensidades.
- Escala fija: todos los valores se dividen por 100. No normalizamos cada
  imagen por separado. Esto conserva el aumento de amplitud que queremos ver.
- TINTO: PCA, 64 × 64, semilla 42; con y sin difuminado (distancia 1, dos pasos,
  combinación por máximo). Se guardan matrices numéricas NPY.
- Origen: transformación recién ajustada; sin CNN, sin detector entrenado.

### Fichas de las figuras

`01_ventana_temporal.png`: izquierda, hora del día en X y ozono inventado en
ppb en Y; cada línea es un sensor y la discontinua es el objetivo alterado.
Centro/derecha: sensor en X y hora en Y; color = ppb, escala común 0–100.
Fuente: `tabla_normal.csv` y `tabla_alterada.csv`. Son mediciones inventadas,
no métricas de detección.

`02_imagenes_tinto.png`: columnas normal, alterada y diferencia numérica;
filas sin/con difuminado. X/Y son columna/fila del píxel 0–63, no horas ni
coordenadas geográficas. Color = valor dividido por 100, escala común 0–1;
la tercera columna muestra la diferencia en esa misma escala.
Fuente: TINTO aplicado a `entrada_tinto.csv`, con mapa ajustado en
`ajuste_inventado.csv`. No representa probabilidades ni F1.

### Resultado y límite observado

Las 120 características ocupan solo 86 posiciones distintas: 63 características
participan en alguna colisión (no son 63 posiciones). Sin difuminado, la
implementación escribe las características en orden; en posiciones compartidas
la última sobrescribe a las anteriores. Lo comprobamos reconstruyendo la matriz
con el mapa exportado. Por eso 24 valores cambiados de la entrada producen solo
14 píxeles distintos en este caso; con difuminado cambian 201 píxeles.

Esto muestra un límite real de esta configuración. No interpretamos el
ensanchamiento de manchas como evidencia de mejor detección, ni afirmamos que
se preserven todas las características. Revisar resolución, colisiones y
tratamiento de solapamientos es trabajo posterior antes de adoptar una
representación para la tesis.

Las primeras dos corridas produjeron `verificaciones.json` idénticos. Se
acortó después la etiqueta de las barras de color para mejorar su lectura;
las salidas `final1`/`final2` corresponden a esa presentación final.

## Preparación de datos reales de L0 (2026-10-28)

Diseño actualizado: [metodologia_v1.md](metodologia_v1.md).
Auditoría ejecutada dos veces: [auditoria_l0_20261028.md](auditoria_l0_20261028.md).
Extractor y verificaciones: `auditar_entradas_l0.py`.
Se reconstruyó el conjunto de ajuste de selección L0 (2020–2021) y se guardó
una muestra canónica de 19 840 ventanas con sus 408 columnas y etiquetas aparte.
No se entrenó un detector ni se ajustó todavía TINTO sobre esta muestra real.

## Experimento 1 completado: resolución (2026-10-28)

Código: `experimento_resolucion.py`.
Informe y fichas: [resultados_resolucion_20261028.md](resultados_resolucion_20261028.md).
Dos corridas con 41 archivos numéricos idénticos. El control sintético cumple
con 256 × 256; L0 no cumple en ninguno de los tamaños 32/64/128/256.
El siguiente trabajo recomendado es diagnosticar colisiones y redundancia
antes de adoptar resolución y continuar con difuminado.

## Diagnóstico antes de quitar entradas (2026-10-28)

Informe: [redundancia_l0_20261028.md](redundancia_l0_20261028.md).
Código: `analizar_redundancia_l0.py`. Dos corridas idénticas.
Hora: 48 valores reconstruibles desde dos a precisión float32. Comparaciones
con vecinas no son la decisión R3 y pueden aportar contexto externo. Máscaras
no recuperables solo a partir de relativa cero. Geografía requiere separar
estación, tiempo y tipo; todavía no se aplica una representación nueva.

## Hora compacta: experimento autorizado y ejecutado (2026-10-28)

Código: `experimento_hora_compacta.py`.
Informe: [resultados_hora_compacta_20261028.md](resultados_hora_compacta_20261028.md).
Comparación 408 vs 362, mismas ventanas y cuatro resoluciones. Dos corridas,
43 archivos numéricos idénticos. A 256, las mismas 360 columnas de sensores
pasan de 222 cambios ocultos a 212. Ninguna resolución cumple conservación;
la compresión horaria no soluciona por sí sola la disposición de características.

## Prototipos sin sobrescritura (2026-10-28)

Informe: [resultados_prototipos_20261028.md](resultados_prototipos_20261028.md).
Código: `prototipos_sin_colisiones.py`. Asignación única explícita de píxeles
para PCA, en 32/64, con 408/362 entradas: cero sobrescritura y recuperación
exacta de todas las ventanas escaladas. Cambia la geometría y no es TINTO
original. Control temporal 24 × 5 × 3 más hora también recuperable. Dos corridas,
13 archivos numéricos idénticos; aún sin entrenar un detector.

## Piloto técnico CNN (2026-10-29)

Informe: [piloto_cnn_20261029.md](piloto_cnn_20261029.md).
Código: `piloto_cnn_tinto.py`. TINTO-PCA cargado, asignación única propia
32 × 32, 408 entradas. Dos modelos de diagnóstico recién entrenados, dos
corridas reproducibles. Se observa aprendizaje, pero el control sintético no
cumple la pérdida <0.1 prefijada. No es evaluación ni detector definitivo.

## Programa de entrenamiento preparado (2026-10-29)

Configuración: `configuracion_entrenamiento_v1.json`.
Programa: `entrenar_tinto_l0.py`, subcomandos `preparar` y `entrenar`.
Instrucciones y controles: [runbook_entrenamiento_v1.md](runbook_entrenamiento_v1.md).
Caché completa ya preparada y hashes cotejados con L0: 1 357 800 ventanas de
ajuste y 339 450 de validación. Ensayo pequeño de dos épocas repetido con
pesos/historias idénticos y recarga correcta. No se ejecutó aún la selección
completa ni la comparación científica por estación-día.

## Selección T1 cerrada manualmente (2026-10-29)

El tesista pidió detener ambas corridas para ahorrar recursos. Mejor checkpoint
observado: época 5, conservado en `seleccion_tinto_v1/cierre_manual/`.
Historias comunes (ocho épocas) y contenido HDF5 de pesos idénticos. La parada
es manual, no EarlyStopping completado. Informe en
`results/exploracion_tinto_2022/seleccion_tinto_v1/informe_cierre_manual.md`.

## Evaluación preparada para Colab CPU (2026-10-29)

Notebook: `notebooks/colab_tinto_evaluacion_2022.ipynb`.
Instrucciones: [colab_evaluacion_2022.md](colab_evaluacion_2022.md).
Script: `evaluar_2022.py`, sin entrenamiento. Paquete de unos 30.45 MiB
preparado con `empaquetar_evaluacion.py`, manifiesto por archivo.
Prueba local de dos días correcta; evaluación completa y ejecución real en
Colab aún pendientes. No se han subido datos a servicios desde este chat.

## Artefactos versionados y regenerables

El commit de T1 conserva código, metodología, mapas, escaladores, modelos
pequeños, historias, resultados numéricos de evaluación, figuras y verificaciones
de reproducibilidad. Las cachés grandes X/y, la tabla/muestra completa de
entradas de auditoría, manifiestos completos de entrenamiento y los paquetes
tar/zip de transporte se conservan localmente y se excluyen de Git.
Los manifiestos pequeños de muestra y hashes de auditoría sí se versionan.

Para regenerar las entradas, usar `auditar_entradas_l0.py` y el subcomando
`preparar` de `entrenar_tinto_l0.py` según sus runbooks, con los datos RAMA
locales y planes originales. `empaquetar_evaluacion.py` recompone el paquete
para Colab; su gzip/tar puede cambiar de hash por metadatos temporales, por lo
que el manifiesto interno de contenido es la referencia al recomponerlo.
Las 62 tablas diarias de cada evaluación están extraídas y versionadas;
no hace falta el ZIP para consultar o verificar los resultados.
