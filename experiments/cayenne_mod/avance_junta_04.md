# Avance para la junta: redistribución de pesos

Fecha: 28 de septiembre de 2026. Resultado exploratorio sobre RAMA 2025.

**Hallazgo principal:** repartir pesos puede reducir mucho la fabricación de
cruces hacia arriba y, al mismo tiempo, aumentar la facilidad de ocultar una
lectura que ya estaba sobre el umbral. Reducir el delta máximo no basta para
afirmar que la representación es más segura.

## Qué se hizo

Se evaluaron 218 823 lecturas válidas de 33 estaciones, sin interpolar. El umbral
experimental es **valor ≥155 ppb**. Solo 25 lecturas cumplen esa condición; no
son necesariamente eventos independientes ni declaraciones de contingencia.

Se compararon:

- **Actual:** interpretación del entero con signo de 16 bits del repositorio.
- **Control binario:** mismos bytes, agregando rechazo fuera del rango 0–255.
- **V1:** divide el peso 32 en dos posiciones de 16, como en el experimento 02.
- **V2:** conserva V1 y divide 64 en dos posiciones de 32 y 128 en cuatro de 32.

V1 y V2 conservan resolución de 1 ppb y el campo de 16 bits, dentro de cuatro
bytes de payload. Recuperan exactamente 0–255 ppb sin ataques, pero cambian la
semántica del formato. El rango definitivo del sensor sigue por decidir.

Cada escenario altera **un mensaje**: se enumeran las 16 máscaras de un flip y,
por separado, las 120 parejas de dos flips. Se incluyen posiciones reservadas;
cuando un formato las rechaza, se contabiliza el rechazo explícitamente.
Agrupar por valor exacto reproduce los conteos de escenarios locales sin
simular millones de mensajes repetidos. No hay muestreo, semillas ni LSTM.

## Resultados que conviene presentar

Esta tabla supone una elección **uniforme entre las 16 posiciones físicas**
para un solo flip. No es una tasa de ataques observada en una red.

| Formato | Cruces arriba entre originales <155 | Cruces abajo entre originales ≥155 | Rechazos entre todos los escenarios |
|---|---:|---:|---:|
| Actual | 46.7311 % | 24.25 % | 0.00 % |
| Control binario 0–255 | 2.9811 % | 18.00 % | 50.00 % |
| V1 | 2.9736 % | 21.25 % | 43.75 % |
| V2 | 0.0962 % | **40.00 %** | 18.75 % |

Denominadores: 218 798 × 16 escenarios para la segunda columna, 25 × 16 = 400
para la tercera y 218 823 × 16 para los rechazos. Los rechazos permanecen en los
denominadores de cruces, pero nunca se cuentan como una lectura corregida.

El resultado de la representación actual está fuertemente influido por
aceptar valores fuera del dominio experimental después de invertir los bits
altos. El control muestra por qué sería incorrecto atribuir toda diferencia
frente a esa referencia únicamente a la redistribución de pesos.

**V2 frente al control binario:** los cruces globales pasan de 104 434 a 3 528
entre 3 501 168 escenarios de un flip (2.9828 % a 0.1008 %). Pero los cruces
hacia abajo pasan de **72 a 160 de 400**. El resultado global está dominado por
las muchísimas lecturas que originalmente estaban bajo el umbral.

Con dos flips aparece el mismo compromiso:

| Formato | Cruces arriba / originales <155 | Cruces abajo / originales ≥155 | Rechazos / total |
|---|---:|---:|---:|
| Control binario | 3.4131 % | 11.4333 % | 76.6667 % |
| V1 | 3.8192 % | 13.4000 % | 70.0000 % |
| V2 | 0.3002 % | **35.0667 %** | 35.0000 % |

Los resultados no se limitan a una elección uniforme: si el atacante usa la
**peor máscara fija** para el total de cruces, el control y V1 alcanzan
46.9882 % con un flip, y V2 0.3153 %. Con dos flips son 88.2942 % y 4.0023 %,
respectivamente. Es una selección retrospectiva sobre 2025, no una garantía
ante cualquier estrategia ni una máscara distinta para cada lectura.

## Por qué pueden aumentar los cruces hacia abajo

Para una lectura de **160 ppb**, todos los formatos recuperan 160 sin ataque:

| Formato | Posiciones cuyo flip hace bajar de 155 | Número de posiciones |
|---|---|---:|
| Control binario | 5, 7 | 2 de 16 |
| V1 | 5, 7, 8 | 3 de 16 |
| V2 | 5, 7, 8, 10, 11, 12 | 6 de 16 |

En V2, cualquiera de cuatro fragmentos de 32 puede llevar 160 a 128; cualquiera
de los dos fragmentos de 16 puede llevarlo a 144. Cada modificación es menor
que la del antiguo bit de 128, pero hay más posiciones capaces de cruzar el
umbral. Esta es una explicación del mecanismo, no una estimación adicional.

## Qué está demostrado y qué sigue abierto

Se verificaron los 256 valores sin ataque, la equivalencia con la V1 previa,
el efecto de cada posición y los conteos agrupados frente a una enumeración
mensaje por mensaje. Pasaron **16 pruebas**. Los conteos por estación suman
exactamente los globales. El notebook se ejecutó en un kernel limpio.

Esto **no demuestra una contramedida definitiva**: se estudian cruces locales,
no el efecto en máximos de red, contingencias oficiales ni ataques cifrados de
extremo a extremo. No se modela qué decisión toma el sistema si falta una
lectura rechazada. Tampoco se midieron energía, latencia o detección LSTM.
La escasez y posible dependencia temporal de las 25 lecturas altas limita
especialmente cualquier generalización sobre ocultamiento.

Para la siguiente etapa propongo discutir:

1. **Objetivo:** tratar por separado cruces falsos hacia arriba y ocultamiento
   hacia abajo; no elegir pesos usando solo la tasa global.
2. **Rango y rechazo:** acordar el rango que debe conservarse y el coste de
   perder un mensaje. V2 es una candidata sencilla, no una distribución óptima.
3. **Nueva candidata:** estudiar cómo proteger la decisión cerca del umbral,
   incluyendo si la discordancia entre fragmentos debe provocar rechazo. Eso
   cambiaría el mecanismo y requeriría otro control experimental.
4. **Validación:** fijar el diseño antes de evaluarlo en otro año. Después,
   medir el daño que escapa al LSTM guardado, sin confundir menos delta con
   mejor detección.

Una frase posible para la junta:

> La redistribución reduce la perturbación máxima y los cruces falsos hacia
> arriba, pero encontramos un compromiso: multiplicar los fragmentos también
> puede multiplicar las posiciones que ocultan una lectura cercana al umbral.
> Por eso estamos evaluando ambos sentidos y el coste de rechazo por separado.

## Archivos y reproducción

- [Notebook ejecutado](04_comparacion_pesos_rama.ipynb).
- [Gráfica principal](resultados/04/comparacion.png).
- [Riesgo por posición](resultados/04/cruces_por_bit.png).
- [Resultados globales y por estación](resultados/04/resumen.csv).
- [Conteos por máscara física](resultados/04/por_mascara.csv).
- [Frecuencias exactas](resultados/04/frecuencias.csv).
- [Versiones, parámetros y hashes de los datos y código](resultados/04/metadatos.json).

Ejecuta la única celda del notebook desde el kernel del proyecto para regenerar
los resultados. Este resumen corresponde a la ejecución del 28 de septiembre;
debe revisarse si se cambian los datos, pesos o protocolo.

Para comprobar el cálculo desde la raíz:

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_comparar_pesos.py -q
```
