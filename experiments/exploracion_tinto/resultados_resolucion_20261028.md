# Experimento 1: resolución de TINTO — 2026-10-28

## Diseño ejecutado

Se ejecutó `experimento_resolucion.py` con TINTOlib 1.3.1 real en un entorno
separado. Transformación recién ajustada, sin clasificador ni inferencia L0.

Antes de calcular resultados se guardó `configuracion.json` en cada corrida:
PCA, semilla 42, `blur=False`, `zoom=1`, lados 32/64/128/256; MinMax por columna
ajustado una vez por tabla, sin recorte. No se reajusta el escalado por imagen.
Se verificó igualdad EXACTA de las coordenadas continuas PCA entre resoluciones.

Dos conjuntos, sin datos de validación ni examen:

- Sintético: 128 días inventados de 24 × 5; 120 columnas. El nuevo MinMax
  sustituye la división fija por 100 del ejercicio anterior. Por eso los conteos
  de este barrido no deben compararse directamente con el antiguo mapa sintético.
- L0: las 19 840 ventanas auditadas de 2020–2021; 408 columnas. No es un fit
  con las 1 357 800 ventanas completas. Se guardan hash y manifiesto de la muestra.

La etiqueta utilizada por la API es cero para todas las filas; las etiquetas
reales no intervienen en el mapa. Se probaron una observación base y cambios
individuales: +/-0.125 en escala MinMax, o inversión 0/1 en máscaras. Cada imagen
se generó con `TINTO.transform`, se guardó temporalmente en NPY y se leyó para
comprobar el cambio. No se sustituyó TINTO por un rasterizador propio.

Estas perturbaciones verifican codificación, no son ataques físicos: cambiar
una sola columna de hora o máscara no reproduce una ventana temporal coherente.
Los criterios estaban fijados antes del barrido; no se eligió por métricas de 2022.

## Resultados L0

| Imagen | Posiciones distintas / 408 | Columnas sobrescritas = cambios individuales ocultos | Porcentaje de columnas | RMSE de reconstrucción MinMax |
|---|---:|---:|---:|---:|
| 32 × 32 | 23 | 385 | 94.36 % | 0.239472 |
| 64 × 64 | 40 | 368 | 90.20 % | 0.209254 |
| 128 × 128 | 81 | 327 | 80.15 % | 0.180085 |
| 256 × 256 | 151 | 257 | 62.99 % | 0.135168 |

Una columna sobrescrita pierde su modificación individual en esta representación
sin difuminado: en cada píxel prevalece la última característica que TINTO escribe.
Se verificó el valor de cada píxel base contra esa regla y cada una de las 408
perturbaciones contra la imagen real generada. El número de posiciones no es el
número de píxeles no negros: un píxel asignado puede contener un valor cero.

RMSE se calcula sobre las 19 840 filas a escala MinMax, recuperando el valor de
cada característica desde su píxel y comparándolo con la entrada. No es un error
de ozono ni una métrica de detección. La regla de recuperación se validó en las
imágenes generadas. La fracción de columnas sobrescritas NO equivale al porcentaje
de información estadísticamente independiente perdida ni al recall del detector.

A 256 × 256, las sobrescrituras afectan:

| Tipo | Columnas | Sobrescritas |
|---|---:|---:|
| Relativas | 120 | 81 |
| Comparación con vecinas | 120 | 71 |
| Máscaras | 120 | 70 |
| Seno de hora | 24 | 17 |
| Coseno de hora | 24 | 18 |

No se trata exclusivamente de variables horarias repetidas: también coinciden
posiciones de relativas, comparaciones y máscaras. No se retiraron columnas.

## Control sintético

| Imagen | Posiciones distintas / 120 | Cambios individuales ocultos |
|---|---:|---:|
| 32 × 32 | 92 | 28 |
| 64 × 64 | 111 | 9 |
| 128 × 128 | 119 | 1 |
| 256 × 256 | 120 | 0 |

La resolución sí puede separar estas 120 características en este mapa. No
permite trasladar 256 como resolución suficiente para las 408 entradas L0.

## ¿Por qué no basta aumentar el tamaño?

PCA coloca las características de L0 en zonas muy concentradas. La cuadrícula
puede seguir asignando varias al mismo píxel aunque haya muchos píxeles vacíos.
No se distribuyen uniformemente por toda la imagen. La causa concreta de la
concentración por tipo de variable requiere un diagnóstico adicional; no se
atribuye a geografía ni a una falla del detector.

Además, se observaron ocho pares de características horarias con coordenadas
continuas exactamente iguales (400 posiciones continuas diferentes para 408
columnas). Un aumento de resolución no separa esos pares en este mapa.
Sus valores de entrada solo difieren hasta 1.84e-16: son codificaciones horarias
prácticamente redundantes, correspondientes a seno/coseno con desfases.
Por eso estas ocho coincidencias no demuestran por sí mismas pérdida de
información útil independiente. El criterio estricto de columnas separadas sigue
sin cumplirse, y las otras colisiones deben analizarse por separado.

## Coste y reproducibilidad

| Lado | Memoria de una matriz float64 | Tamaño de NPY |
|---|---:|---:|
| 32 | 8 KiB | 8 320 bytes |
| 64 | 32 KiB | 32 896 bytes |
| 128 | 128 KiB | 131 200 bytes |
| 256 | 512 KiB | 524 416 bytes |

Cada duplicación del lado multiplica memoria por cuatro. Estos tamaños excluyen
lotes, activaciones y entrenamiento de una red; float32 usaría la mitad para el
array. `tiempos.csv` registra ajuste PCA y generación/escritura local; son
mediciones de máquina y archivos temporales, no benchmarks de CNN. No se exige
que los tiempos de dos corridas sean idénticos.

Las dos corridas finalizaron y coincidieron los SHA-256 de 41 archivos numéricos:
mapas, escaladores, coordenadas PCA, matrices base, perturbaciones, resúmenes,
configuración y decisiones. Los tiempos quedaron fuera de esa igualdad.

## Decisión y siguiente trabajo

Resultado conforme al criterio previamente fijado: sintético elegible a 256;
ninguna candidata elegible para L0. No hay resolución adoptada para entrenar
TINTO-L0. No se pasa automáticamente al experimento de difuminado como si se
hubiera resuelto la conservación de características.

Recomendación: extender el diagnóstico del experimento 1 antes de entrenar:
separar coincidencias de señales redundantes de colisiones entre señales
diferentes, y estudiar si basta otra rasterización. La reubicación determinista
para reservar posiciones únicas sería una variante explícita de TINTO que debe
registrarse antes de evaluarla, comparándola con la implementación original.
Más resolución podría reducir otras colisiones, pero no elimina los ocho pares
continuos idénticos ni sustituye ese diagnóstico. No modificar silenciosamente
el criterio de conservación ni eliminar columnas para obtener un aprobado.

## Fichas de figuras y archivos

Carpeta: `results/exploracion_tinto_2022/resolucion_20261028/`.

- `corrida1/resolucion_y_perdida.png`: X = lado en píxeles. Izquierda Y = cantidad
  de características con cambio individual invisible, sobre 120/408 según tabla;
  derecha Y = memoria teórica de la matriz float64 en KiB. Fuente:
  `resoluciones.csv`. No son F1 ni tasas de detección.
- `corrida1/imagenes_L0.png`: misma ventana en cuatro tamaños, sin difuminado.
  X/Y = columna/fila de píxel, no hora ni geografía; color = intensidad MinMax
  con escala visual común 0–1. Fondo cero no significa necesariamente ausencia
  de característica. Fuente: matrices `L0_408/imagen_base_*.npy`.
- `reproducibilidad_y_diagnostico.json`: igualdad y ocho pares coincidentes,
  incluyendo diferencias numéricas de sus entradas.
- `sobrescritura_por_tipo_256.csv`: desglose de la tabla anterior.
- `corrida*/L0_408/mapa_*.csv`: posición, tamaño de grupo, si se sobrescribe y
  nombre de la característica que escribe al final en ese píxel.
- `corrida*/L0_408/perturbaciones_*.csv`: comprobación individual de cada columna.

Repetir desde la raíz con entorno que tenga las dependencias del aula:

```sh
MPLCONFIGDIR=/tmp/tinto-mpl /tmp/tinto-resolucion-venv/bin/python experiments/exploracion_tinto/experimento_resolucion.py --salida results/exploracion_tinto_2022/resolucion_nueva/corrida1
```

El entorno temporal puede desaparecer; reinstalar TINTOlib en uno separado si
es necesario. Los archivos de configuración guardan las versiones reales de
esta ejecución y los hashes de entrada/código.
