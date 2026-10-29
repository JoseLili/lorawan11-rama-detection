# Prototipos sin sobrescritura — 2026-10-28

## Alcance y registro

Tras la aceptación del siguiente paso por el tesista se estudiaron dos
codificaciones, conservando todas las relativas, máscaras y comparaciones.
No se entrenó ningún detector ni se usaron años de validación o examen.

`prototipos_sin_colisiones.py` guarda configuración y hashes antes de resolver
las asignaciones. Reutiliza PCA y escaladores ajustados en las 19 840 ventanas
de 2020–2021 del barrido previo: modelos de representación CARGADOS de disco;
la asignación única se calcula nueva. No se ajusta de nuevo PCA ni se consultan
etiquetas para colocar características.

## A. PCA con asignación única: variante explícita de TINTO

Se mantienen los puntos PCA continuos de cada variante, pero se sustituye el
redondeo independiente por una asignación uno a uno entre características y
píxeles. Se minimiza la suma de distancias euclidianas cuadradas desde los puntos
PCA a las posiciones de la cuadrícula, bajo la restricción de no compartir píxel.
Se usa `scipy.optimize.linear_sum_assignment` con columnas y píxeles en orden
estable; no se describe como algoritmo voraz ni se asegura identidad entre
versiones distintas del solver ante empates.

Referencia de la optimización:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html

Esta rasterización es una modificación propia, NO el TINTO original de la
biblioteca. Se registra separadamente y el original permanece como control.
Sin difuminado ni interpolación. El mapa es fijo para todas las observaciones,
no se reubican píxeles dependiendo del valor o etiqueta de una imagen nueva.

Se eligieron 32/64 como lados del prototipo antes de calcular resultados:
32 ya dispone de 1024 celdas para 408 o 362 características. Se verificó primero
que la transformación de coordenadas/convención fila-columna reproduce los
mapas redondeados originales guardados.

| Variante | Imagen | Posiciones distintas | Cambios individuales ocultos | Error máximo de recuperación MinMax |
|---|---|---:|---:|---:|
| 408 entradas | 32 × 32 | 408 | 0 | 0 |
| 408 entradas | 64 × 64 | 408 | 0 | 0 |
| 362 entradas | 32 × 32 | 362 | 0 | 0 |
| 362 entradas | 64 × 64 | 362 | 0 | 0 |

Se codificaron y recuperaron las 19 840 ventanas COMPLETAS en cada configuración,
comparándolas elemento a elemento. También se comprobó que cambiar cada columna
por separado modifica exactamente un píxel en la observación ilustrada.
La recuperación exacta se refiere a los valores flotantes ya escalados y al mapa
conocido, no a invertir un PNG ni a recuperar el ozono crudo previo al perfil L0.
El fondo cero no sirve para decidir si una posición corresponde a una característica:
para ello se conserva el mapa de posiciones.

### Coste: la geometría cambia

| Variante | Lado | Desplazamiento medio respecto al píxel original | Desplazamiento máximo | Vecinos PCA conservados, entre cuatro |
|---|---:|---:|---:|---:|
| 408 | 32 | 4.13 píxeles | 8.54 | 31.74 % |
| 408 | 64 | 3.28 píxeles | 7.28 | 33.82 % |
| 362 | 32 | 3.70 píxeles | 8.06 | 33.08 % |
| 362 | 64 | 2.89 píxeles | 6.32 | 35.84 % |

El porcentaje compara los cuatro vecinos más próximos de cada característica
en PCA continuo con sus cuatro vecinos en la cuadrícula asignada; promedio
entre características. Empates resueltos por orden estable de columnas. Es una
medida descriptiva sensible a empates/densidad y no una métrica de detección.
El objetivo optimizado es el desplazamiento cuadrático, NO conservar ese ranking.
Una reasignación global puede mover también puntos que antes no colisionaban.

Por tanto, cero sobrescritura no implica preservar todas las relaciones PCA ni
mejorar la CNN. A 64 la geometría se altera menos en estos diagnósticos, pero
la imagen tiene cuatro veces más píxeles. No se eligió arquitectura ni resolución
para un detector basándose en estos números.

## B. Canales por tipo: control temporal explícito

Los 360 valores de sensores se reorganizan como **24 horas × cinco roles × tres
tipos**. Cada tipo es un canal: relativa, máscara, comparación a14. La hora queda
como bloque aparte, 24 × 2 en la versión original o dos valores finales en la
versión compacta. Los canales solos NO son una entrada completa.

Se comprobó recuperación exacta de las 408 entradas originales juntando los
canales con el bloque horario para las 19 840 ventanas. La compactación horaria
48→2 ya fue validada con tolerancia float32 en la etapa anterior; no se confunde
esa aproximación de redondeo con una igualdad de bits.

Es una reorganización sin proyección PCA, sin ajuste y sin eliminación de
características; técnicamente el control temporal por canales. No es una imagen
TINTO ni un mapa geográfico. Aún falta definir cómo recibirá la hora el futuro
clasificador (rama separada, canales adicionales u otra opción registrada),
antes de entrenarlo. No se oculta esa decisión arquitectónica.

## Lectura de las figuras

Carpeta: `results/exploracion_tinto_2022/prototipos_20261028/corrida1/`.

- `comparacion_asignacion.png`: misma ventana de 362 entradas. Columnas: raster
  original de TINTO frente a asignación única; filas: 32/64. X/Y = posiciones de
  píxel, NO horas o geografía. Color = intensidad MinMax, escala común 0–1.
  Fuente: matrices previas originales y matrices `L0_362/imagen_unica_*.npy`.
  Las manchas de la asignación única NO son difuminado: son píxeles contiguos
  que pertenecen a características diferentes, cada una con su propio valor.
- `canales_sensor.png`: X = rol (objetivo, vecinas ordenadas por distancia);
  Y = desfase −23..0. Paneles: relativa, máscara y comparación a14, con barras
  por tipo. Relativas/comparaciones adimensionales en escala histórica L0;
  máscara binaria. Las escalas de los paneles difieren: no comparar brillo entre
  paneles. Son datos, no probabilidades ni métricas de detección.

Los píxeles reubicados ya no representan necesariamente la misma característica
que el píxel de igual coordenada en el original. Consultar el mapa para seguir
una columna concreta. La forma de la imagen NO se interpreta como silueta de CDMX.

## Reproducibilidad y decisión

Dos corridas completas: trece archivos numéricos/configuración idénticos por
SHA-256; constancia en `prototipos_20261028/reproducibilidad.json`.
Versiones y fuentes están registradas en cada `configuracion.json`.

Estos prototipos resuelven conservación numérica sin quitar más información.
La siguiente fase propuesta puede comparar rasterización TINTO original,
asignación única y control temporal por canales, manteniendo los mismos ejemplos,
etiquetas y evaluación por estación-día. No se afirma ventaja predictiva ni se
cambia automáticamente el diseño principal. Difuminado requiere nuevos controles:
mezclar intensidades puede volver a impedir una inversión exacta aun con centros
únicos. La geografía sigue siendo una alternativa separada, no aplicada aquí.

Ejecutar desde la raíz en un entorno con numpy, pandas, scipy y matplotlib:

```sh
MPLCONFIGDIR=/tmp/tinto-mpl /tmp/tinto-resolucion-venv/bin/python experiments/exploracion_tinto/prototipos_sin_colisiones.py --salida results/exploracion_tinto_2022/prototipos_nuevos/corrida1
```
