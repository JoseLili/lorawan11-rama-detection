# Auditoría de entradas L0 para TINTO — 2026-10-28

## Alcance y origen

Se reconstruyó X del entrenamiento de SELECCIÓN de L0 usando las funciones
originales de `entrenar_lstm_local.py`. Se procesaron los veinte calendarios
d50, objetivos en su orden original y posiciones seleccionadas por
`lstm_local.muestra` (1/8, semilla histórica). No se entrenó ni cargó un
clasificador para inferencia. No se calcularon métricas de detección.

Se leyó la matriz limpia 2020–2022 para reproducir la sigma histórica de L0 y
la historia de las matrices d50. Las ventanas de ajuste auditadas terminan
únicamente en 2020–2021. El ajuste de a14 utiliza 2020–2021 limpio.
Se conservaron perfiles causales e imputación originales.

## Resultados

| Comprobación | Resultado |
|---|---:|
| Ventanas de ajuste | 1 357 800 |
| Calendarios | 20 |
| Objetivos | 31 |
| Forma por ventana | 24 × 17 |
| Columnas aplanadas | 408 |
| Etiquetas positivas | 8 310 (0.6120194 %) |
| Ventanas guardadas en muestra | 19 840 |
| Positivas en muestra | 114 |
| Columnas constantes en ajuste completo | 0 |
| Grupos de columnas exactamente duplicadas en muestra | 0 |
| Ventanas de ajuste sin lectura del objetivo en t | 324 705 |

La cantidad total coincide con la configuración guardada del L0 canónico.
No se afirma que no existan duplicados fuera de la muestra: esa prueba se
limitó a sus 19 840 filas. Constantes y rangos sí se midieron sobre TODO Xtr.

Las ventanas sin lectura propia final son parte de la ruta original de
entrenamiento L0; no se retiraron a posteriori. En predicción L0 enmascara
horas sin lectura y el promedio diario exige al menos 12 horas válidas.
Cambiar la elegibilidad solo para TINTO rompería la comparación pareada.

| Tipo | Columnas aplanadas | Mínimo global | Máximo global |
|---|---:|---:|---:|
| Relativa | 120 | −3.909335 | 5.850293 |
| Máscara | 120 | 0 | 1 |
| Comparación con vecinas | 120 | −21.001709 | 19.748590 |
| Seno de hora | 24 | −1 | 1 |
| Coseno de hora | 24 | −1 | 1 |

Estos números son adimensionales, no ppb ni probabilidades. No se pueden pasar
como si todas las intensidades fueran positivas entre cero y uno: antes del
experimento de representación se comprobará el escalador adicional propuesto.
Máscaras binarias y seno² + coseno² = 1 verificados en todo el tensor de ajuste.
Todos los valores de entrada son finitos.

## Igualdad y trazabilidad

- X de referencia: ruta original `entrenar_lstm_local.ejemplos`, por calendario.
- Reconstrucción independiente de ventanas: 32 índices uniformemente espaciados
  DENTRO de la muestra original de cada estación/calendario, sin nuevo sorteo.
- Las 19 840 ventanas reconstruidas son iguales elemento a elemento al X de
  referencia; se cotejó el orden de los 17 canales con los índices originales.
- Se comprobaron las etiquetas de TODAS las ventanas contra la etiqueta del
  objetivo en t, y se guardó su manifiesto completo.
- No se agregaron claves, fechas ni etiquetas a las 408 columnas numéricas.
- SHA-256 de Xtr completo en orden original:
  `abf546c60dee618b02d2a0da794a5e547ad1633f0a476d49c9214810df8b8938`.
- SHA-256 de ytr completo:
  `e72aba28b3bae4eb154f533c7b3150187bee52c2cf3995c97ad3c6f997832560`.

El script calcula Xtr por bloques de calendario para evitar guardar el tensor
completo. La tabla guardada es una MUESTRA, no todo el conjunto de ajuste.
No utilizarla como sustituto del entrenamiento completo ni afirmar que representa
exactamente la frecuencia de positivos de Xtr.

## Archivos

Código: `auditar_entradas_l0.py`. Ejecución desde la raíz:

```sh
MPLCONFIGDIR=/tmp/tinto-mpl .venv/bin/python experiments/exploracion_tinto/auditar_entradas_l0.py --salida results/exploracion_tinto_2022/auditoria_l0_nueva/corrida1
```

Salidas de esta auditoría en
`results/exploracion_tinto_2022/auditoria_l0_20261028/corrida1/` y `corrida2/`:

- `diccionario_408.csv`: posición, nombre, desfase, rol, tipo y escala.
- `X_muestra.npy`: 19 840 × 24 × 17, valores numéricos float32.
- `tabla_408_muestra.csv`: mismos números en formato tabular, sin etiqueta.
- `y_muestra.npy`: etiquetas en archivo separado.
- `manifiesto_muestra.csv`: clave, ventana temporal, etiqueta y observación del objetivo.
- `manifiesto_entrenamiento.csv.gz`: IDs y etiquetas de las 1 357 800 ventanas.
- `auditoria_columnas.csv`: rangos, medias, desviación y constantes en Xtr completo.
- `vecinas_y_escalas.json`: lista/orden de objetivos, vecinas y escalas.
- `verificaciones.json`: controles, versiones y hashes de fuentes/código.
- `hashes.json`: hashes de los archivos generados.

## Siguiente paso

Usar la muestra canónica para la primera comprobación de resolución, manteniendo
el mapa y el escalado ajustados solo con datos de entrenamiento. La auditoría
sobre Xtr completo no equivale a que el futuro mapa TINTO ya haya sido ajustado
con todo Xtr: habrá que registrar explícitamente qué filas se usan para ese fit.
La proyección de columnas con PCA puede resultar costosa con 1.36 millones de
observaciones; cualquier submuestra para ese ajuste debe predefinirse y quedar
en su manifiesto antes de comparar detectores.

## Reproducibilidad comprobada

Las corridas 1 y 2 finalizaron correctamente. Los SHA-256 de los diez archivos
generados son idénticos entre ambas: muestra NPY/CSV, etiquetas, diccionario,
manifiestos, estadísticas, duplicados, vecinas/escalas y verificaciones.
Constancia: `auditoria_l0_20261028/reproducibilidad.json` en resultados.
