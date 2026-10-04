# Laboratorio de codificación del payload

## Estado: distribución B cerrada con resultado no favorable

Se probaron distribuciones del peso de los bits 4 y 5 y se amplió la
comparación final de **Base + LSTM frente a B + LSTM** a 27 estaciones
evaluables, usando predicciones y umbrales guardados, sin reentrenar.
Con 100 campañas por estación y ataques sobre las posiciones 0…15 del
campo de valor, B no mejoró la protección conjunta: los cambios de banda
por lectura sin alerta aumentaron de **255 a 567**, sobre **179 399 intentos
por formato**. Hubo más escapes en 26 estaciones y empate en cero en una.

Se conserva como contramedida intentada sin éxito bajo este protocolo,
no como prueba de que cualquier redistribución sea inútil. La evaluación
cubre datos del 21 de octubre al 31 de diciembre de 2025, no todo el año.
El paso a paso, la interpretación de las tablas y la decisión de cierre
están en [las notas para la junta](cierre_distribucion_pesos.md).

## Recorrido del laboratorio

Primer ejercicio: inspeccionar una medición de 160 ppb y entender un flip del
bit 5 antes de diseñar la representación propuesta por el asesor.

## Archivos del ejemplo

| Archivo | Contenido hexadecimal | Valor decodificado |
|---|---|---:|
| `samples/o3_160ppb.bin` | `01 02 00 A0` | 160 ppb |
| `samples/o3_160ppb_flip_bit5.bin` | `01 02 00 80` | 128 ppb |

Cada archivo contiene **cuatro bytes binarios**, no caracteres que escriban el
hexadecimal. Se generan con las funciones de `src/encoding/cayenne.py`.

Desde la raíz del repositorio puedes reproducirlos y verificar sus valores:

```bash
.venv/bin/python experiments/cayenne_mod/generar_ejemplo.py
```

Usamos el entorno del proyecto porque el paquete de codificación también
importa la dependencia criptográfica PyCryptodome.

El script comprueba los bytes esperados, la decodificación y que sólo cambie un
bit. Conserva las muestras existentes; si modificaste alguna, avisa en lugar
de sobrescribirla.

## Cómo leer el payload

| Desplazamiento en bytes, desde 0 | Hexadecimal | Significado |
|---:|---|---|
| 0 | `01` | Canal 1 |
| 1 | `02` | Tipo Analog Input |
| 2–3 | `00 A0` | Entero de 16 bits con signo, big-endian: 160 |

La tesis reinterpreta ese entero a **1 ppb por unidad**. Es una convención del
proyecto: Analog Input de CayenneLPP normalmente usa escala 0.01. Un
decodificador genérico no interpretaría automáticamente estos bytes como
160 ppb. Véase [la decisión de codificación](../../docs/02_codificacion.md).

El valor 160 se descompone en `128 + 32`: están encendidos los bits 7 y 5.
Numeramos los bits desde 0, empezando por el menos significativo del valor.
El bit 5 está en el último byte del campo, aunque el campo ocupa dos bytes.

```text
original: 00000000 10100000 = 160
máscara:  00000000 00100000 =  32
XOR:      00000000 10000000 = 128
```

XOR invierte la posición seleccionada. Aquí resta 32 porque el bit ya era 1.
Aplicar el mismo flip a 128 lo vuelve 160: el sentido depende del dato.

Usando el umbral experimental de 155 ppb, esta lectura pasa de estar por
encima a quedar por debajo. Eso demuestra un cruce local; para afirmar que se
oculta el cruce de toda la red hay que comprobar las demás lecturas.

Estas muestras son payloads **sin cifrar** para estudiar la representación.
No contienen la trama LoRaWAN completa y este ejercicio aún no ejecuta el
ataque sobre texto cifrado ni implementa la contramedida.

El ejercicio completo, incluyendo la guía de GNU poke y una celda Python
ejecutable, está en [el notebook de inspección](01_inspeccion_payload.ipynb).

## Continuación de los experimentos

1. [Inspección del payload](01_inspeccion_payload.ipynb): entender el cambio 160 → 128.
2. [Repartir el peso del bit 5](02_repartir_peso_bit5.ipynb): primera propuesta V1.
3. [Distribución real de ppb](03_distribucion_real_ppb.ipynb): frecuencias y valores cerca del umbral.
4. [Comparación sobre RAMA 2025](04_comparacion_pesos_rama.ipynb): actual, control de rango, V1 y V2; uno y dos flips sobre las 16 posiciones.

El [resumen para la junta](avance_junta_04.md) explica el resultado del experimento
04: V2 reduce cruces hacia arriba, pero aumenta los cruces hacia abajo entre las
lecturas originalmente altas bajo selección uniforme de máscaras. Los rechazos
se contabilizan aparte. No se ha validado una contramedida definitiva ni se ha
evaluado esta propuesta junto con el LSTM.

## Experimento 05: distribuciones A y B con los detectores del notebook 09

[Abrir el notebook 05](05_distribuciones_A_B_red.ipynb).

- **A:** contribución de 16 → dos bits de 8; contribución de 32 → dos de 16.
- **B:** contribución de 16 → dos bits de 8; contribución de 32 → cuatro de 8.

Se comparan con un control binario de igual dominio 0–255. Se evalúa un flip
por mensaje sobre las 16 posiciones, incluidas las nuevas, conservando los
pesos de 64 y 128. Se cuentan directamente cambios de banda y falsas
excedencias que escapan a los detectores por estación, usando sus predicciones
y p95 guardados; no se entrena ni recalibra. El análisis anual de ocultamientos
se mantiene separado, sin extrapolar detección al año completo.

La única celda ejecutable verifica las fuentes, valida 12 288 escenarios a
través del cifrado y exige dos cálculos idénticos antes de guardar resultados
en `resultados/05/`. No modifica las referencias del 09 ni los experimentos
anteriores. El rango definitivo del formato, otros presupuestos de ataque y
la validación en otro año siguen pendientes.

Pruebas del cálculo:

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_selectiva_red.py -q
```

## Experimento 06: un flip aleatorio dentro del grupo repartido

[Abrir el notebook 06](06_un_flip_en_fragmentos.ipynb).

Este es el análisis enfocado propuesto después del ejemplo de 60 ppb:
misma lectura original y un solo bit elegido uniformemente entre el bit 5 de
la base, sus dos fragmentos en A y los seis derivados de los bits 4 y 5 en B.
El bit 3 de B no se incluye. Los ejemplos de 60 y 28 muestran cuándo el azar
elige posiciones equivalentes y cuándo puede cambiar el sentido del delta.

Se presentan por separado un sorteo por mensaje con semilla 42 y su promedio
exacto, ponderando las opciones por 1, 1/2 y 1/6. No se suman seis intentos para
B. Se reutilizan las predicciones y p95 guardados del notebook 09; el análisis
anual de ocultamientos se hace sin LSTM. Los resultados quedan en
`resultados/06/`, separados del barrido de 16 posiciones del experimento 05.

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_flip_dirigido.py -q
```

## Experimento 07: varios flips y compensación

[Abrir el notebook 07](07_multiflips_compensacion.ipynb).

Enumera todas las combinaciones de N posiciones distintas de un mensaje:
N = 1…7 entre los siete bits de peso 8 de B (incluido el bit 3), y N = 1…16
en el campo completo de Base, A y B. Los promedios suponen selección uniforme
entre máscaras del mismo tamaño; también se informa la peor máscara fija
observada. Se separan cancelaciones, rechazos, daño diario y alertas.

Se reutilizan las predicciones y p95 guardados del notebook 09, sin entrenar
ni ejecutar nueva inferencia. Dos ejecuciones completas dieron tablas
idénticas; N = 1 reproduce el 05. El análisis anual permanece sin LSTM.
Resultados y tres figuras: `resultados/07/`. Interpretación breve:
[avance para la junta](avance_junta_07.md).

La compensación se observa, pero no garantiza una mejora general: depende
del presupuesto y del conjunto de posiciones elegibles. En particular,
cuatro flips en los fragmentos del bit 5 de B recuperan el cambio de ±32.

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_multiflip.py -q
```

## Experimento 08: campañas aleatorias sólo en CCA

[Abrir el notebook 08](08_campanas_aleatorias_CCA.ipynb).

Cada lectura válida del test tiene 5 % de probabilidad de ataque. Si se
selecciona, se sortea N uniformemente entre 1 y 16 y se invierten N posiciones
distintas del campo del valor. Base, A y B comparten momentos, presupuestos
y máscaras. Se ejecutan 100 campañas, semillas 42…141; la 42 es el ejemplo
fijado previamente. Cada ataque atraviesa cifrado/flip/descifrado.

Se reutilizan las predicciones guardadas de CCA del notebook 09, cuyo p95
es 14.748355 ppb; no se mezcla con el piloto anterior de 22.6 ppb ni se
reentrena. Se preservan predicciones y entradas originales: no se modela
propagación temporal. Los máximos diarios combinan todos los ataques de la
campaña y sólo consideran CCA. Un rechazo implica dato ausente, sin alerta
LSTM evaluable. Las alertas no eliminan automáticamente lecturas.

Dos ejecuciones completas produjeron tablas idénticas. Resultados, plan
reproducible, trazas y tres figuras: `resultados/08/`. El
[resumen para la junta](avance_junta_08.md) distingue los efectos por lectura,
los cambios diarios y la pérdida de datos. El notebook explica N y muestra
los primeros cinco ataques paso a paso.

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_campana_cca.py -q
```

## Experimento 09: comparación Base + LSTM frente a B + LSTM en CCA

[Abrir la comparación](09_comparacion_base_B_CCA.ipynb).

Reutiliza las mismas 100 campañas del 08, las predicciones guardadas de CCA
y su p95 de 14.748355 ppb. No genera otros ataques, no reentrena ni cambia
el umbral. Recalcula las alertas y las bandas para verificar las etiquetas,
exige pareado exacto y repite la comparación dos veces.

El resultado principal incluye todos los intentos: 13 cambios de banda
local sin alerta en Base y 19 en B. El diagnóstico distingue los 420
intentos aceptados por ambos (13 frente a 6) y los 791 que sólo B acepta
(13 escapes adicionales en B; pérdida de lectura en Base). Se acompañan
las falsas alarmas y los rechazos, sin presentarlos como datos íntegros.

Los ejemplos explican cuándo B evita cambiar banda, cuándo permite que el
LSTM alerte y cuándo introduce un escape. No se generaliza el beneficio
del subgrupo al conjunto completo. Resultados: `resultados/09/`; explicación
breve: [avance para la junta](avance_junta_09.md).

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_comparacion_base_B.py -q
```

## Experimento 10: daño diario y alertas en CCA

[Abrir el notebook 10](10_dano_diario_base_B_CCA.ipynb).

Segundo punto: compara Base y B en banda del máximo diario y cruces de
155 ppb, usando todas las posiciones 0…15 de las mismas 100 campañas del
08. Reutiliza predicciones y p95 guardados; no entrena ni propaga ataques
a ventanas futuras. Reproduce los máximos y alertas diarios del 08.

Separa cualquier alerta del día de alertas en valores realmente alterados.
Las reconstrucciones con originales permiten examinar si el daño persiste
al restaurar alteraciones detectadas y lecturas rechazadas. Son diagnósticos
del simulador, no políticas operativas. La pérdida de datos queda explícita.

Resultados y figura: `resultados/10/`. El
[resumen para la junta](avance_junta_10.md) distingue días-campaña de fechas
independientes. Ocultamiento de excedencias no evaluable en este test:
máximo limpio CCA de 145 ppb, sin originales ≥155.

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_diario_base_B.py -q
```

## Experimento 11: verificación en las 27 estaciones evaluables

[Abrir el notebook 11](11_verificacion_multiestacion_base_B.ipynb).

Extiende las campañas Base/B a las 27 estaciones con modelo guardado del
09 principal. Conserva 5 % de selección, N uniforme 1…16 y posiciones 0…15,
sin ajustar modelos ni umbrales. CCA reproduce el 08; las demás estaciones
usan sorteos reproducibles separados, siempre pareados entre formatos.

Incluye cobertura y motivos de exclusión de otras seis estaciones,
resultados por estación, agregados con distinta ponderación, falsas alarmas,
rechazos y máximos diarios de cada estación. No calcula el máximo de toda
la red ni evalúa ocultamiento sin originales ≥155. El análisis completo
se repite dos veces; plan, ataques y decisiones quedan en `resultados/11/`.

El notebook lee y verifica las tablas guardadas por defecto; activar
`RECALCULAR` reconstruye todas las campañas dos veces. Interpretación:
[avance para la junta](avance_junta_11.md).

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_campanas_estaciones.py -q
```
