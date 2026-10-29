# Experimento: 408 entradas frente a hora compacta (362) — 2026-10-28

## Pregunta y diseño

El tesista autorizó probar si comprimir la repetición horaria reduce las
colisiones de TINTO. No se entrenó clasificador ni se modificó el L0 existente.

- Original: 408 columnas de L0.
- Compacta: mismas 360 columnas de sensores y solo seno/coseno de la hora final,
  total 362. Se retiraron las 46 columnas horarias de desfases 23..1.
- Mismas 19 840 ventanas auditadas de 2020–2021 y misma observación base.
- Se repitió la comprobación de que la hora final permite reconstruir las otras
  horas a tolerancia absoluta 1e−7, sin exigir igualdad de bits float32.
- MinMax por columna en las mismas filas de entrenamiento, sin recorte.
- TINTOlib 1.3.1 real, PCA semilla 42, sin difuminado, zoom 1, NPY float64.
- Cuatro lados registrados antes de fit: 32/64/128/256.
- Un mapa PCA NUEVO por variante, porque cambia el conjunto de características;
  coordenadas continuas exactamente iguales entre resoluciones de la misma variante.
- Una perturbación individual por característica (+/-0.125 escalado, inversión
  binaria en máscaras), comprobada mediante imágenes generadas por TINTO.
  Estas pruebas son de codificación, no episodios de ataque físicamente coherentes.

La reducción fue explícita y autorizada para esta prueba. No se eliminaron máscaras
ni comparaciones a14 ni se introdujeron coordenadas o decisiones de R3.

## Resultados sobre cada vector completo

| Lado | Posiciones original / 408 | Cambios ocultos original | Posiciones compacta / 362 | Cambios ocultos compacta |
|---|---:|---:|---:|---:|
| 32 | 23 | 385 | 21 | 341 |
| 64 | 40 | 368 | 40 | 322 |
| 128 | 81 | 327 | 88 | 274 |
| 256 | 151 | 257 | 150 | 212 |

Ninguna resolución cumple el criterio fijado de conservar separadas todas las
características no constantes. En particular, 212 de las 362 perturbaciones
quedan ocultas a 256. Esto no es una tasa de anomalías no detectadas.

Comparar 257 contra 212 directamente exagera la mejora atribuible al mapa:
la segunda variante tiene 46 entradas menos. Tampoco conviene interpretar el
RMSE global de ambos vectores como una comparación sobre las mismas variables,
ya que cambia la composición del promedio.

## Comparación justa: las mismas 360 columnas de sensores

Se restringe la medida a las 120 relativas, 120 máscaras y 120 comparaciones
que se conservaron SIN cambio en ambas representaciones.

| Lado | Cambios ocultos original | Cambios ocultos compacta | Balance |
|---|---:|---:|---|
| 32 | 339 | 341 | Empeora en 2 |
| 64 | 323 | 322 | Mejora en 1 |
| 128 | 285 | 274 | Mejora en 11 |
| 256 | 222 | 212 | Mejora en 10 |

A 256 hay 58 columnas de sensores que dejan de estar sobrescritas y 48 que
pasan a estarlo con el mapa nuevo, balance neto de diez. No es una mejora
uniforme para todas las columnas. Las dos columnas horarias finales se conservan
visibles en ambos mapas en estas cuatro resoluciones.

Conclusión: compactar la hora conserva su información y reduce columnas, pero
NO resuelve las colisiones de los sensores en PCA-TINTO. Aumentar resolución y
quitar repetición horaria no bastaron en este barrido. No se adopta una
resolución ni se declara mejora de detección.

## Coste y controles

Para un mismo lado, la matriz de imagen conserva el mismo tamaño: 362 entradas
no hacen automáticamente más pequeña una imagen 256 × 256. NPY float64 sigue
ocupando 524 416 bytes por imagen en ambas variantes a esa resolución.
Los tiempos locales de ajuste y escritura están en `tiempos.csv`; no son medidas
reproducibles exactas ni costes de entrenamiento de una CNN.

- El control original de 408 reprodujo EXACTAMENTE los mapas y las matrices base
  del experimento previo, para los cuatro tamaños.
- Las dos ejecuciones nuevas dieron los mismos hashes de 43 archivos numéricos;
  se excluyeron los tiempos. Se incluye configuración, mapas, escalas, matrices,
  comprobaciones individuales y resúmenes.
- No se ajustó con 2022 ni se accedió a años de examen. Se usaron las entradas
  previamente construidas bajo la normalización histórica de L0 ya documentada.

## Archivos y fichas

Código: `experimento_hora_compacta.py`.
Carpeta: `results/exploracion_tinto_2022/hora_compacta_20261028/`.

- `corrida*/configuracion.json`: parámetros fijados antes de ajustar y hashes.
- `corrida*/resoluciones.csv`: resultados globales por variante y resolución.
- `corrida*/comparacion_columnas_comunes.csv`: mismas columnas en ambos mapas,
  incluyendo recuperadas y nuevas ocultas.
- `corrida*/control_original.json`: reproducción del control previo y verificación horaria.
- `corrida*/L0_362/mapa_*.csv`: nombres, posiciones y columna que sobrescribe.
- `reproducibilidad.json`: constancia de la igualdad entre corridas.

`resolucion_y_perdida.png`: X = lado en píxeles. Izquierda Y = número de cambios
individuales invisibles en cada vector completo; derecha Y = porcentaje con
respecto a 408 o 362, según variante. Fuente `resoluciones.csv`. Las bases de los
porcentajes son distintas; para comparar sensores usar la tabla común de 360.
No representa F1, recall ni información independiente perdida.

`imagenes_comparadas.png`: arriba original, abajo compacta, una columna por
resolución. X/Y = posición del píxel, no coordenadas geográficas ni horas.
Color = valor MinMax en escala visual común 0–1; fuente = imágenes base NPY.
El mapa cambia por variante, por lo que no se interpretan intensidades de un
mismo píxel como si representaran siempre la misma característica.

## Siguiente decisión propuesta

Conservar ambas variantes y detener nuevas eliminaciones por intuición.
El cuello de botella observado está en la disposición y discretización de las
características del mapa. Antes de pasar a detección, proponer una representación
que asigne posiciones distintas a las características, o separe tipo/tiempo en
canales, y compararla con TINTO original como variante explícita. La geografía
puede estudiarse en ese diseño, pero no separa por sí sola las 72 entradas de
cada sensor. No se aplica automáticamente ninguna de estas modificaciones.

Repetir con entorno separado que contenga TINTOlib:

```sh
MPLCONFIGDIR=/tmp/tinto-mpl /tmp/tinto-resolucion-venv/bin/python experiments/exploracion_tinto/experimento_hora_compacta.py --salida results/exploracion_tinto_2022/hora_compacta_nueva/corrida1
```
