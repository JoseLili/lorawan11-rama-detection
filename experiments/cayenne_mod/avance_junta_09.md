# Primera comparación: Base + LSTM frente a B + LSTM en CCA

La distribución B muestra beneficios en algunos ataques comparables, pero
no reduce el total de cambios de banda local sin alerta bajo el protocolo
actual. El análisis separa ese resultado global del mecanismo de mejora.

Se reutilizan las predicciones y el p95 **guardados de CCA del notebook 09
principal**, sin entrenamiento ni inferencia nueva. Umbral: 14.748355 ppb.
Se comparan las mismas 100 campañas del experimento 08, con 5 % de selección
por lectura y N uniforme entre 1 y 16. Mismos datos, momentos, N, posiciones
y detector. Los conteos acumulados reutilizan el mismo periodo; no son
100 periodos independientes.

Base es el control binario de dominio 0…255, con posiciones 8…15 reservadas.
B usa posiciones 0…11 y reserva 12…15. No es una comparación contra un
decodificador Analog Input estándar sin restricción de rango.

## Resultado global

| Conteo en 100 campañas | Base + LSTM | B + LSTM |
|---|---:|---:|
| Intentos de ataque | 8 377 | 8 377 |
| Lecturas rechazadas | 7 957 | 7 166 |
| Ataques aceptados | 420 | 1 211 |
| Valor intacto por cancelación | 0 | 29 |
| Valores alterados | 420 | 1 182 |
| Valores alterados con alerta | 279 | 772 |
| Cambios de banda local | 210 | 574 |
| Cambios de banda local sin alerta | 13 | 19 |

B permite recibir más mensajes, pero muchos están alterados. Perder menos
lecturas no implica conservar más datos correctos. El resultado principal
no muestra una mejora global de B en daño por lectura sin alerta.

## Diagnóstico: mismos intentos aceptados por ambos

Los 420 ataques que Base acepta también son aceptados por B. En ese grupo,
los cambios de banda sin alerta bajan de 13 a 6:

- Cinco ataques cambian banda y escapan en ambos formatos.
- En cuatro escapes de Base, B evita que la lectura cambie de banda.
- En otros cuatro escapes de Base, B cambia la banda, pero el LSTM alerta.
- B introduce un escape nuevo que Base no tenía.

Así, Base tiene 5 + 4 + 4 = 13 escapes y B tiene 5 + 1 = 6.
Este diagnóstico identifica mecanismos complementarios, pero no reemplaza
el resultado principal. Su selección depende de aceptación del formato,
no de un resultado favorable del ataque.

En ese grupo el cambio absoluto medio pasa de 52.30 a 47.56 ppb, mientras
la detección entre valores alterados pasa de 66.43 % a 58.85 %. La reducción
del daño sin alerta puede coexistir con menor detección global de cambios.
Además, con varios flips, B no reduce necesariamente el cambio neto de
cada ataque: puede reducir una contribución que compensaba a otra.

## Por qué el resultado global se invierte

B acepta otros 791 intentos que Base rechaza. De ellos, 27 conservan el
valor y 764 lo alteran. Trece producen cambios de banda sin alerta en B.

Por ello, el total de B es **6 + 13 = 19**, frente a 13 de Base. Los
791 rechazos adicionales de Base siguen siendo pérdida de datos: no son
lecturas correctas ni detecciones del LSTM.

## Costos que acompañan la comparación

Las falsas alarmas en lecturas no atacadas son idénticas entre formatos:
341.74 por campaña en promedio. La referencia limpia de CCA tiene 21.38 %
de falsas alarmas. La distribución no cambia ese costo del detector.

El máximo diario disponible cambia de banda en 1.33 días por campaña en
Base y 3.66 en B. Estos conteos incluyen cambios detectados: no deben
presentarse como días de daño sin alerta. Las alertas no retiran lecturas
automáticamente en el protocolo actual.

B tiene menos escapes por lectura que Base en 8 campañas, empata en 81 y
tiene más en 11. Los eventos son escasos; no se declara superioridad
estadística ni generalización a otro periodo.

## Cierre del primer punto para CCA

Se documenta una **mejora condicionada en el grupo común**, junto a un
resultado global que no favorece a B bajo N uniforme de 1…16. No se altera
el detector ni el protocolo para obtener un resultado favorable.

Siguen pendientes la separación completa de decisiones por lectura, día
y excedencias, suficientes excedencias originales para probar ocultamiento,
y la validación en otras estaciones y otro periodo. Aquí el máximo limpio
es 145 ppb: no hay excedencias originales de 155 para evaluar su ocultamiento.

Verificación: dos ejecuciones idénticas de esta comparación, coincidencia
con los conteos del 08 y pruebas de pareado, transición y aceptación común.
Se mantienen fijas las predicciones; no se simulan entradas futuras dañadas.

[Notebook ejecutado](09_comparacion_base_B_CCA.ipynb),
[tablas](resultados/09/resumen.csv),
[ejemplos por ataque](resultados/09/ejemplos.csv),
[protocolo y fuentes](resultados/09/protocolo.json).
