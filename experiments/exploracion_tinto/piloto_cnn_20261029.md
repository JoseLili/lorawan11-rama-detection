# Piloto técnico TINTO-PCA + asignación única + CNN — 2026-10-29

## Objetivo y alcance

El tesista confirmó mantener TINTO como línea principal. Se ejecutó una prueba
pequeña de extremo a extremo, no la comparación científica con L0.
Se conserva el mapa PCA que TINTOlib ajustó sobre entrenamiento 2020–2021 y se
carga la variante documentada de asignación única 32 × 32, con 408 entradas.
No se usa TINTO original como sinónimo de esta variante modificada.

La codificación de la CNN usa mapas/escalas guardados; no vuelve a ajustar
TINTO por clase, imagen o subconjunto. Cada valor conserva su posición única.
Se comprobó recuperación exacta de la entrada escalada tras convertir a float32.
No se usaron 2022 ni años posteriores para evaluar ni seleccionar.

## Configuración registrada antes de entrenar

Archivo `configuracion_previa.json` en cada corrida, con hashes de fuentes y código.

- CNN: convolución 8 filtros 3 × 3, pooling 2, convolución 16 filtros 3 × 3,
  pooling 2, Flatten, densa 32 ReLU, dropout 0.2, sigmoide.
- 34 081 parámetros; arquitectura de DIAGNÓSTICO, no detector adoptado.
- Adam 0.001, entropía cruzada binaria, lote 64, 60 épocas, CPU.
- Semilla 42 según `fijar_semilla` antes de construir y entrenar.
- Barajado explícito en tf.data, semilla 42, sin pesos de clase. El aviso Keras
  de que ignora su argumento shuffle para Dataset no significa ausencia de
  barajado: se aplica mediante Dataset.shuffle antes de formar el lote.
- Dos modelos nuevos independientes, uno por etapa del piloto. No se transfieren
  los pesos sintéticos al modelo real ni se cargan como detector definitivo.

### Etapas y criterios fijados

1. Sintética: 64 vectores inventados, 32 por clase. Señal conocida en las 24
   relativas del objetivo (valores 0.1/0.9) y ruido 0.4–0.6 en las otras columnas.
   Prueba artificial, no anomalías físicamente coherentes ni máscaras válidas.
   Criterio: pérdida final <0.1 y exactitud de entrenamiento >=95 %.
2. Real: 64 ventanas de 2020, 32 positivas y 32 negativas, tomadas sin reemplazo
   de la muestra auditada con semilla [42,29,0]. Criterio: pérdidas/predicciones
   finitas, pesos distintos al inicio y pérdida final inferior a la inicial.

Este balance es SOLO diagnóstico de aprendizaje/memorización; difiere del 0.612 %
de positivos del entrenamiento principal. No se cambia ese entrenamiento ni se
estima rendimiento real a partir del balance del piloto.

## Resultados, sin modificar el criterio tras observarlos

| Etapa | Pérdida inicial | Pérdida final | Acierto en los MISMOS ejemplos entrenados | Criterio |
|---|---:|---:|---:|---|
| Inventada | 0.690167 | 0.139956 | 100 % | No cumple: pérdida no baja de 0.1 |
| Real, memorización | 0.693583 | 0.446592 | 78.125 % | Cumple el control técnico definido |

Pérdidas inicial/final evaluadas sin dropout sobre entrenamiento. La historia
por época corresponde a entrenamiento con dropout; no confundir ambas curvas.
Los pesos cambian y las cantidades son finitas. El 100 % de acierto sintético
no implica que las probabilidades estén lo bastante cerca de sus etiquetas
para cumplir el límite de pérdida. El umbral 0.5 se usa solo para este control
artificial, no sustituye p99/p99.9 del detector científico.

Interpretación: el circuito valores → imagen → CNN → etiquetas funciona y
produce aprendizaje sobre los ejemplos usados. El criterio sintético completo
NO se alcanzó; el piloto no se declara aprobado en su conjunto. No se aumentaron
épocas ni se cambiaron filtros, señal, umbral o criterio para hacerlo pasar.
La elección <0.1 fue un requisito técnico del piloto, no una ley de viabilidad
de TINTO ni una prueba de que el método falle en detección.

No se calculan precisión/recall/F1, no hay separación independiente y no se
presenta ese 78.125 % como capacidad de detectar anomalías nuevas. El mapa y
escalas anteriores ya incluyen estas ventanas, coherente con un diagnóstico
sin pretensión de generalización.

## Tiempo y memoria

Una imagen float32 de 32 × 32 ocupa 4096 bytes. Almacenar de una vez todas las
1 357 800 imágenes requeriría unos 5.56 GB solo para el tensor, antes de
etiquetas, datos base y estado de entrenamiento. Recomendar generación por lotes.

La mediana observada de una época caliente de UN lote en el subconjunto real
fue ~0.012 s. Extrapolada linealmente a 21 216 lotes, sugiere ~251 s por época
solo de entrenamiento. Es una aproximación de esta máquina y configuración:
no mide preparación completa, I/O, validación, épocas de EarlyStopping ni
segunda ejecución. No se promete ese tiempo para Colab u otra CPU.

## Reproducibilidad y fuentes

Dos corridas completas: pesos, historias, probabilidades, selección de ventanas
identificadas y resúmenes idénticos; nueve archivos numéricos/configuración con
SHA-256 iguales. Los tiempos y el contenedor Keras no se comparan byte a byte;
los pesos de los modelos sí se comparan mediante hash.

Un primer intento de preparación se detuvo antes de entrenar al consultar
metadatos del paquete `keras`: el entorno usa `keras-nightly`. Se corrigió el
nombre de distribución y se ejecutaron final1/final2 sin cambios de arquitectura
ni criterios. La carpeta inicial quedó sin resultados de entrenamiento.

Código: `piloto_cnn_tinto.py`.
Salidas: `results/exploracion_tinto_2022/piloto_cnn_20261029/final1/` y `final2/`.
- `configuracion_previa.json`: diseño previo y versiones.
- `manifiesto_piloto.csv`: las 64 ventanas reales seleccionadas.
- `resultados.json`: controles y origen de cada modelo.
- `sintetica/` y `real_memorizacion/`: modelos PILOTO, historias y probabilidades.
- `tiempos.csv`: mediciones variables de tiempo.
- `../reproducibilidad.json`: constancia de repetición.

## Recomendación

Mantener TINTO-PCA con asignación única como línea candidata. Antes de la
comparación completa, revisar la configuración de aprendizaje del diagnóstico
y decidir cómo cerrar el control sintético fallido, registrando cualquier nueva
prueba por separado. No tomar el resultado de memorización como justificación
para pasar directamente al examen ni usar estos modelos piloto como detectores.
La comparación principal seguirá usando las ventanas y frecuencias originales
L0 y su modelo de selección guardado, con arquitectura/presupuesto registrados.

## Revisión posterior de probabilidades, sin nuevo entrenamiento

Se reconstruyó el conjunto sintético con su semilla registrada y se verificó
que las 24 características de señal llegan a sus píxeles sin modificación y
sus etiquetas corresponden a la señal. En los 64 ejemplos, la probabilidad
asignada a la clase correcta va de 0.8362 a 0.9158, mediana 0.8704. Se
recalculó la pérdida como −promedio(log(probabilidad de clase correcta)) y
coincide con 0.139956.

Esto explica que todos los aciertos a umbral 0.5 puedan coexistir con pérdida
mayor a 0.1. No se encontró un fallo de conversión/etiquetado en este control.
El criterio prefijado sigue sin cumplirse: no se cambia a posteriori ni se
presenta el piloto global como aprobado. Tampoco se interpreta ese incumplimiento
como evidencia de incapacidad de TINTO para clasificar. Esta revisión permite
preparar la decisión sobre el diseño científico, distinguiendo criterio técnico
de probabilidades y rendimiento de generalización. Constancia:
`piloto_cnn_20261029/diagnostico_probabilidades_20261029.json` en resultados.
