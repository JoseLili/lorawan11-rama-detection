# Verificación de Base + LSTM frente a B + LSTM en 27 estaciones

La ampliación no rescata la propuesta B bajo el protocolo estudiado:
en 26 estaciones aumenta el conteo de lecturas que cambian de banda sin
alerta, y en una hay empate en cero. No aparece ninguna estación con menos
escapes acumulados en B. Este patrón describe el experimento, no una prueba
de superioridad estadística para cada estación por separado.

## Protocolo y cobertura

Se reutilizan las **predicciones y p95 guardados de cada estación del
notebook 09 principal**, sin entrenamiento, nueva inferencia ni ajuste de
umbrales. Son 35 704 lecturas originales del 21 de octubre al 31 de diciembre
de 2025; se respeta la cobertura observada de cada estación.

Se ejecutan 100 campañas por estación con 5 % de selección por lectura,
N uniforme 1…16 y posiciones 0…15 sin reemplazo. Base y B reciben idénticos
ataques dentro de cada estación y semilla. CCA conserva sus sorteos del 08;
las demás estaciones usan flujos reproducibles separados. Las predicciones
permanecen fijas: no se propagan ataques a futuras ventanas ni a entradas
de otros detectores.

Se incluyen todas las 27 estaciones con referencia evaluable. AJU, CHO,
FAR, IZT, MON y TAH no tienen ventanas de prueba en esta referencia y se
documentan como excluidas, no como estaciones protegidas. La cobertura es
desigual: ACO sólo tiene 59 lecturas y 254 intentos acumulados, por lo que
su empate en cero no demuestra equivalencia.

Base es el control binario de dominio 0…255 con bits 8…15 reservados. B
utiliza 0…11 y reserva 12…15. El alcance es el campo del valor, no toda
la trama. Cada ataque se verifica mediante cifrar/flip/descifrar.

## Resultado principal: todos los intentos

| Acumulado de las campañas y estaciones | Base + LSTM | B + LSTM |
|---|---:|---:|
| Intentos de ataque | 179 399 | 179 399 |
| Lecturas rechazadas | 169 599 | 152 683 |
| Lecturas que cambian de banda sin alerta | 255 | 567 |
| Porcentaje de intentos con ese daño sin alerta | 0.1421 % | 0.3161 % |

Dar el mismo peso a cada estación tampoco invierte el resultado: el
promedio de tasas por estación es 0.1414 % en Base y 0.3122 % en B.

B pierde 16 916 lecturas menos por rechazo, pero esa reducción no se
traduce en menos daño no detectado. Se consideran todos los intentos,
sin seleccionar sólo los aceptados por ambos formatos. Los rechazos se
contabilizan como pérdida de datos, no como lecturas correctas ni éxitos
del LSTM.

Ambos formatos tienen 535 814 falsas alarmas en las mismas 3 391 001
lecturas no atacadas acumuladas. Son las mismas observaciones repetidas
con distintas selecciones de ataque, no millones de lecturas originales
independientes. La distribución de pesos no corrige esas falsas alarmas.

## Resultado diario, separado del resultado por lectura

Los siguientes conteos corresponden a días-estación-campaña. Hay 155 000
por formato: se repiten las fechas con datos de cada estación en las 100
campañas. No son días independientes ni el máximo conjunto de la red.

| Medida diaria por estación | Base + LSTM | B + LSTM |
|---|---:|---:|
| Banda del máximo distinta de la original | 3 827 | 9 106 |
| De ellos, sin alerta en valores alterados | 958 | 872 |
| Daño persiste sólo con alteraciones sin alerta | 71 | 150 |
| Falsas excedencias de 155 ppb | 1 176 | 4 050 |
| Falsas excedencias sin alerta en valores alterados | 0 | 1 |

La segunda fila incluye daño por rechazo y no acredita por sí sola mayor
protección de B. La tercera es una reconstrucción diagnóstica: se restauran
los originales de alteraciones detectadas y rechazados, conservando sólo
alteraciones aceptadas sin alerta en días ya dañados. No representa una
corrección que el receptor pueda aplicar. Las filas se solapan y no se suman.

Una alerta no elimina automáticamente el valor recibido. Por tanto, los
totales de cambio de banda y falsa excedencia incluyen ataques detectados.
El cruce de 155 es un umbral experimental sobre el máximo observado, no
una declaración oficial de contingencia.

El máximo limpio de las estaciones evaluables es 152 ppb. La ampliación
no incorpora excedencias originales de 155: **sigue sin ser evaluable el
ocultamiento de esas excedencias** con este conjunto de prueba.

## Decisión recomendada

Conservar la distribución B como resultado negativo documentado bajo este
escenario y dejar de priorizarla como candidata a mejora general del LSTM.
No seleccionar estaciones favorables ni modificar umbrales para rescatarla:
en esta verificación no aparece una mejora acumulada en ninguna estación.

Esto no demuestra que cualquier distribución sea inútil ni cubre ataques
dirigidos, otros presupuestos, otros años o entradas futuras contaminadas.
Sí ofrece evidencia más amplia que CCA para no presentar B como una mejora
global bajo el protocolo actual. La búsqueda de periodos con excedencias
reales y la validación externa del detector siguen siendo tareas separadas.

## Reproducibilidad

Dos ejecuciones completas produjeron tablas exactamente iguales. CCA
reproduce los conteos del 08. Se verifican las fuentes guardadas y el raw;
el cálculo diario vectorizado coincide con casos de referencia del 10,
incluidos daño por pérdida, interacción y ausencia total de datos.

[Notebook ejecutado](11_verificacion_multiestacion_base_B.ipynb),
[comparación por estación](resultados/11/pareados.csv),
[cobertura](resultados/11/cobertura.csv),
[protocolo](resultados/11/protocolo.json).
