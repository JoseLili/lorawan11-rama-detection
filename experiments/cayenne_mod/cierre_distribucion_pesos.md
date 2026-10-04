# Cierre de la distribución de pesos — notas para la junta

## Qué concluyo por ahora

Mi idea era repartir el peso de algunos bits para que un flip hiciera menos daño, y dejar que el LSTM detectara los cambios grandes. Después de probarlo, **la propuesta B no dio una mejora conjunta frente a Base + LSTM bajo el protocolo que usamos**. En la comparación de las 27 estaciones, las lecturas que cambiaron de banda sin alerta pasaron de **255 en Base a 567 en B**, con los mismos intentos de ataque.

Por eso cierro esta propuesta como un resultado no favorable y la dejo documentada. Sí hubo casos donde ayudó, pero no alcanzaron para compensar lo que perdimos al considerar todos los intentos. No estoy concluyendo que cualquier distribución de pesos sea inútil; estoy cerrando esta implementación y este experimento.

Los resultados de esta nota vienen de **predicciones y umbrales guardados de modelos ya entrenados**, usados como referencia en el notebook 09 principal. No entrené otro LSTM ni ajusté sus umbrales para esta comparación. Los notebooks 09, 10 y 11 de esta carpeta son los experimentos de comparación, no ese notebook principal.

## 1. Qué quería probar

Lo que me interesaba era reducir alteraciones que cambiaran la banda de una lectura o la banda del máximo diario y que además no fueran detectadas. También revisé falsas excedencias de 155 ppb.

La idea salió de que los cambios pequeños tendían a pasar más desapercibidos para el detector, mientras que los grandes eran más fáciles de detectar en las pruebas anteriores. Quise reducir el daño de los bits 4 y 5 repartiendo su peso:

| Aporte original | Base | Propuesta A | Propuesta B |
|---|---:|---:|---:|
| Bit 3 | 8 | 8 | 8 |
| Bit 4 | 16 | 2 bits de peso 8 | 2 bits de peso 8 |
| Bit 5 | 32 | 2 bits de peso 16 | 4 bits de peso 8 |

En B hay **seis bits de peso 8 derivados de los bits 4 y 5**, y **siete contando el bit 3 original**. No son siete ataques: son siete posiciones físicas con el mismo peso. Los otros pesos, incluidos 64 y 128, se conservan.

Una lectura limpia representa el mismo valor en los tres formatos. Lo que cambia es cómo se reparte ese valor entre los bits. Por ejemplo, si parto de 60 y apago una contribución encendida del grupo del bit 5, obtengo 28 en Base, 44 en A y 52 en B. Aquí sí estoy comparando la misma lectura original: 60 − 32, 60 − 16 y 60 − 8.

Esto es una adaptación experimental de la codificación CayenneLPP para nuestros datos en ppb; la distribución propuesta no es una propiedad del formato estándar.

## 2. Cómo fui ampliando el experimento

Primero revisé la codificación y los flips básicos, y después pasé de ataques muy específicos a campañas más amplias:

| Paso | Qué hice | Qué me permitió revisar |
|---|---|---|
| [05: A y B](05_distribuciones_A_B_red.ipynb) | Comparé distribuciones con las referencias guardadas del LSTM. | Separar cambio de valor, alerta y rechazo. |
| [06: un flip](06_un_flip_en_fragmentos.ipynb) | Ataqué un bit del grupo elegido en cada formato. | Ver si bajar el peso de un flip reducía el daño. Era una prueba restringida. |
| [07: varios flips](07_multiflips_compensacion.ipynb) | Revisé combinaciones de posiciones y cantidades de flips. | Ver cuándo los cambios se sumaban y cuándo se cancelaban. |
| [08: campañas en CCA](08_campanas_aleatorias_CCA.ipynb) | Seleccioné lecturas al azar y apliqué varios flips en el campo de 16 bits. | Pasar de casos aislados a varios ataques dentro de una serie. |
| [09: Base frente a B](09_comparacion_base_B_CCA.ipynb) | Comparé todos los intentos y, aparte, los aceptados por ambos. | Entender por qué una mejora en un subconjunto no se mantenía en el total. |
| [10: efecto diario](10_dano_diario_base_B_CCA.ipynb) | Calculé máximos, bandas diarias y cruces de 155 ppb. | Separar daño por valores alterados, pérdida de datos y alertas. |
| [11: 27 estaciones](11_verificacion_multiestacion_base_B.ipynb) | Repetí la comparación con todas las estaciones evaluables. | Comprobar si lo observado en CCA cambiaba al ampliar la cobertura. |

Con varios flips sí puede haber compensación: apagar un bit de peso 8 y encender otro del mismo peso deja el valor igual. Pero si ambos se apagan o ambos se encienden, sus efectos se suman. La compensación depende de qué bits estaban encendidos y de cuáles se atacan; no es una protección garantizada.

## 3. Qué significa el protocolo de las campañas

Para leer los resultados necesito tener claras estas reglas:

1. Cada campaña empieza desde los mismos datos limpios. Una campaña no hereda los ataques de la anterior.
2. Cada lectura tiene una probabilidad del 5 % de ser atacada. No obligo a que exactamente el 5 % termine atacado.
3. Si selecciono una lectura, sorteo **N entre 1 y 16** con igual probabilidad. N es la cantidad de bits que voy a invertir en ese mensaje.
4. Selecciono N posiciones distintas entre **0 y 15**, sin repetir posición dentro de ese ataque.
5. Base y B reciben los mismos instantes atacados, la misma N y las mismas posiciones dentro de cada estación y campaña.
6. Decodifico, registro rechazos, evalúo los valores aceptados con la referencia fija del LSTM y calculo el daño por lectura y por día.

**100 campañas son 100 sorteos del ataque, no 100 modelos ni 100 módulos.** Usé las semillas 42 a 141 para poder repetirlos. Tampoco son 100 años de información independiente.

El ataque abarca el **campo de valor de 16 bits**, no todo el FRMPayload. En Base, los bits 8 a 15 están reservados; activarlos provoca rechazo. En B se usan los bits 0 a 11 y quedan reservados del 12 al 15. Esto explica parte de la diferencia: B admite alteraciones que Base rechaza.

En el experimento se verifica el recorrido cifrar → invertir bits → descifrar → decodificar. Eso comprueba la transformación simulada, pero no demuestra por sí solo que una modificación pueda atravesar todas las verificaciones de una implementación real de LoRaWAN.

Elegir N de forma uniforme también es una decisión experimental. No sabemos si un atacante real elegiría esa distribución. La comparación ya incluye las 16 posiciones, pero sus conclusiones siguen correspondiendo a este modelo de ataque.

## 4. Cómo leo los resultados sin mezclar cosas

| Término | Qué significa aquí |
|---|---|
| Intento de ataque | Seleccioné una lectura y apliqué la máscara de flips, aunque después se rechace o el cambio se cancele. |
| Rechazo | El decodificador no admite la lectura. Pierdo ese dato; no cuenta como detección del LSTM. |
| Cancelación | El ataque se acepta, pero el valor final queda igual al original. |
| Lectura alterada | El valor se acepta y cambia numéricamente. |
| Alerta del LSTM | El residuo supera el umbral guardado de ese detector. No implica retirar automáticamente el dato. |
| Cambio de banda sin alerta | La lectura aceptada cae en otra banda y no genera alerta. Éste es el daño no detectado por lectura que comparo. |
| Día-campaña | Una fecha dentro de un sorteo concreto. La misma fecha puede aparecer en muchas campañas. |
| Día-estación-campaña | Lo anterior, distinguiendo también la estación. No es un máximo de toda la red. |

Un `NA` no significa necesariamente que faltó ejecutar una celda. Si el mensaje se rechaza, no hay valor recibido válido ni una decisión del LSTM para esa lectura. En ese caso, `NA` significa **no evaluable**, mientras que `False` significa que sí se evaluó y no generó alerta. En tasas, también puede faltar un valor porque el grupo no tiene casos para calcularla.

## 5. Primera tabla para explicar: CCA, todos los intentos

Son 100 campañas sobre 1 684 lecturas originales de CCA, repartidas en 72 fechas. Estos conteos acumulan las campañas:

| Resultado por lectura | Base + LSTM | B + LSTM |
|---|---:|---:|
| Intentos de ataque | 8 377 | 8 377 |
| Lecturas rechazadas | 7 957 | 7 166 |
| Ataques aceptados | 420 | 1 211 |
| Cancelaciones entre los aceptados | 0 | 29 |
| Lecturas alteradas | 420 | 1 182 |
| Lecturas alteradas que generan alerta | 279 | 772 |
| Lecturas que cambian de banda | 210 | 574 |
| Lecturas que cambian de banda sin alerta | **13** | **19** |

Fuente: [resumen del 09](resultados/09/resumen.csv), filas del grupo `todos`.

Yo la leería así: con los mismos 8 377 intentos, B rechaza menos mensajes, pero deja pasar más valores alterados. Detecta más alteraciones en números absolutos porque también recibe muchas más. Lo que me interesa para comparar protección es que los cambios de banda sin alerta suben de 13 a 19.

Las filas no se suman todas entre sí. Por ejemplo, las lecturas que cambian de banda sin alerta ya están incluidas dentro de las que cambian de banda.

### Por qué antes parecía que B ayudaba

Si miro únicamente los **420 ataques que ambos formatos aceptan**, Base tiene 13 cambios de banda sin alerta y B tiene 6. Ahí sí aparece una mejora.

Pero hay otros **791 ataques que sólo B acepta**. En ese grupo, B añade 13 cambios de banda sin alerta. Por eso, en el total termina con **6 + 13 = 19**. La prueba no estaba limitada a atacar del bit 0 al 7; esa restricción aparecía al seleccionar el subconjunto aceptado por ambos.

Ésa es la diferencia que necesito explicar: un beneficio dentro de ese subconjunto no basta para decir que B protege mejor frente a todos los intentos.

## 6. Segunda tabla: qué pasa con el máximo diario de CCA

Aquí la unidad cambia. Son **7 200 días-campaña = 72 fechas × 100 campañas**. Por eso puede haber 366 casos sin que el año tenga 366 fechas evaluadas.

| Resultado diario | Base + LSTM | B + LSTM |
|---|---:|---:|
| Días-campaña donde cambia la banda del máximo | **133** | **366** |
| De ellos, sin ninguna alerta en todo el día | 5 | 5 |
| De ellos, sin alerta en valores alterados | 32 | 29 |
| Daño que persiste dejando sólo alteraciones sin alerta | 4 | 5 |
| Días-campaña con falsa excedencia de 155 ppb | 57 | 208 |
| Falsas excedencias sin alerta en valores alterados | 0 | 1 |

Fuente: [resultados y explicación del 10](avance_junta_10.md), [tabla guardada](resultados/10/resumen.csv).

Paso a paso, la leo así:

1. **133 y 366** cuentan cuándo el máximo diario recibido termina en una banda distinta a la del máximo original. Incluyen daño aunque se haya generado una alerta, porque alertar no elimina el valor automáticamente.
2. **5 y 5** son casos dañados donde no hubo ninguna alerta en todo el día, ni siquiera en lecturas limpias.
3. **32 y 29** son casos dañados donde no hubo alerta en valores alterados. Sí pudo haber alertas en otras lecturas del día. Además, esta fila incluye daño por pérdida de datos rechazados: no puedo interpretarla como si todos fueran ataques aceptados que escaparon al LSTM.
4. **4 y 5** vienen de una reconstrucción para entender el daño: restauro los originales de los mensajes rechazados y de las alteraciones detectadas, y dejo sólo las alteraciones aceptadas sin alerta. Cuento en cuántos días ya dañados sigue cambiando la banda. Puedo hacerlo porque el simulador conoce los originales; no es una corrección disponible para el receptor.
5. **57 y 208** son casos donde el máximo original no llegaba a 155 ppb y el recibido sí. De esos casos, **0 y 1** no tuvieron alerta en valores alterados.

Ojo: **29 no significa que en esos días no hubo ninguna alerta**. Significa que no hubo alerta en valores alterados. Las filas se solapan y no deben sumarse.

También puedo cambiar el máximo al perder una lectura alta por rechazo. Por eso no trato el rechazo como si fuera una lectura correcta, ni sustituyo su valor por cero.

Aquí el cruce de 155 ppb es una medida experimental sobre el máximo observado de la estación. No equivale a demostrar que se activó oficialmente una contingencia.

## 7. Tabla principal para cerrar: las 27 estaciones

Amplié la comparación para revisar si CCA era un caso particular. Usé **35 704 lecturas originales del 21 de octubre al 31 de diciembre de 2025**, con 100 campañas por estación. No es una evaluación de todo el año 2025.

| Acumulado por lectura, todas las estaciones y campañas | Base + LSTM | B + LSTM |
|---|---:|---:|
| Intentos de ataque | **179 399** | **179 399** |
| Lecturas rechazadas | 169 599 | 152 683 |
| Ataques aceptados | 9 800 | 26 716 |
| Cancelaciones | 0 | 544 |
| Lecturas alteradas | 9 800 | 26 172 |
| Lecturas alteradas que generan alerta | 6 094 | 15 623 |
| Lecturas que cambian de banda | 4 434 | 11 885 |
| Lecturas que cambian de banda sin alerta | **255** | **567** |
| Intentos que terminan en ese daño sin alerta | **0.1421 %** | **0.3161 %** |

Fuente: [totales del 11](resultados/11/micro.csv). Los porcentajes de la última fila usan todos los intentos como denominador, no sólo los aceptados.

En **26 estaciones B tiene más cambios de banda sin alerta**. En una, ACO, empatan en cero. No hubo ninguna estación con menos escapes acumulados en B. ACO sólo tiene 59 lecturas originales y 254 intentos acumulados, así que ese empate no demuestra equivalencia.

Si doy el mismo peso a cada estación, en vez de juntar todos los intentos, la dirección tampoco cambia: el promedio de las tasas por estación es **0.1414 % en Base y 0.3122 % en B**. Esto evita que mi conclusión dependa únicamente de las estaciones con más datos.

B pierde menos lecturas por rechazo, pero ese beneficio de disponibilidad no se tradujo en menos daño no detectado. Tampoco redujo las falsas alarmas en lecturas limpias: los dos formatos tienen 535 814 sobre las mismas 3 391 001 lecturas no atacadas acumuladas. Son observaciones repetidas en campañas, no millones de mediciones originales distintas.

Para mostrar el patrón por estación puedo usar la [gráfica del 11](resultados/11/comparacion_estaciones.png) y respaldarla con la [tabla por estación](resultados/11/pareados.csv).

### Respaldo diario para la junta

| Acumulado diario de las 27 estaciones | Base + LSTM | B + LSTM |
|---|---:|---:|
| Cambio de banda del máximo | 3 827 | 9 106 |
| De ellos, sin alerta en valores alterados | 958 | 872 |
| Daño que persiste dejando sólo alteraciones sin alerta | **71** | **150** |
| Falsas excedencias de 155 ppb | 1 176 | 4 050 |
| Falsas excedencias sin alerta en valores alterados | 0 | 1 |

Fuente: [totales del 11](resultados/11/micro.csv) y [explicación del 11](avance_junta_11.md).

Aquí son **días-estación-campaña**, 155 000 por formato. Aplican las mismas definiciones de la tabla diaria de CCA. El descenso de 958 a 872 no basta para decir que B ganó: esa fila incluye daño por pérdidas, y la reconstrucción que deja sólo alteraciones sin alerta pasa de 71 a 150. No sumo estas filas ni las presento como fechas independientes.

## 8. Cómo explico lo que pasó

Mi interpretación inicial fue que B metía más ruido al LSTM. Para la junta lo diría con más precisión: **B cambia qué alteraciones llegan al detector y permite aceptar más máscaras de ataque**. El LSTM y sus umbrales se mantuvieron fijos.

Repartir pesos puede bajar el cambio causado por un flip aislado. Ese cambio puede producir menos daño, pero también quedar dentro de lo que el detector tolera. Con varios flips, los efectos pueden sumarse o cancelarse. Por eso no puedo atribuir todo el resultado a que cada ataque se volvió pequeño: en las campañas completas eso no está garantizado.

La combinación que esperaba no se consiguió. No basta con reducir algunos deltas si, al mismo tiempo, llegan más alteraciones aceptadas y aumenta el daño que no genera alerta.

Tampoco debo usar “aproximadamente ±22 ppb” como una garantía de detección en esta comparación. El umbral guardado de CCA para estas pruebas es **14.748355 ppb**; el valor de 22.6 ppb corresponde al piloto anterior. El MAE no es por sí mismo el umbral de alerta, y cada estación tiene su referencia guardada. Además, un ataque puede acercar el valor a la predicción, así que un delta grande no implica automáticamente una alerta.

## 9. Qué queda fuera de esta conclusión

- Se evaluaron las 27 estaciones con referencia disponible. AJU, CHO, FAR, IZT, MON y TAH no tenían ventanas de prueba en esta referencia; no cuentan como estaciones protegidas.
- El máximo limpio de este conjunto es 152 ppb. No había excedencias originales de 155 ppb, así que **no pude evaluar su ocultamiento**. Un cero en esa métrica no demuestra protección perfecta.
- Las predicciones permanecieron fijas. No simulé cómo un ataque contaminaría ventanas futuras o entradas de otros detectores.
- No probé una política operativa que retire automáticamente las lecturas alertadas. Los diagnósticos con originales restaurados sólo ayudan a explicar resultados.
- Las campañas repiten los mismos datos y las estaciones pueden estar relacionadas. Estos conteos no son observaciones totalmente independientes ni demuestran por sí solos significancia estadística por estación.
- Quedan otros periodos, años y modelos de ataque por estudiar. La validación de vecinos y una comparación con CNN son pendientes separados, no resultados de esta prueba.

Sobre mi idea de **aumentar el peso**: la dejo como hipótesis sin probar. Que reducirlo no haya funcionado no demuestra que aumentarlo sí funcione. Un cambio mayor puede ser más visible, pero también más dañino si pasa sin alerta; además, habría que definir cómo conservar el rango y la resolución de las mediciones.

## 10. Cómo lo presentaría al doc

1. Empiezo con la idea: repartir 16 y 32 para disminuir el efecto de un flip, conservando la lectura limpia.
2. Explico que primero hubo pruebas restringidas y después ataques sobre cualquiera de las 16 posiciones del campo de valor.
3. Muestro la tabla por lectura de CCA y el contraste entre el subconjunto aceptado por ambos y todos los intentos. Ahí se entiende por qué el beneficio inicial no bastaba.
4. Muestro la tabla de las 27 estaciones como resultado principal y la gráfica por estación. Uso las tablas diarias como respaldo, explicando sus unidades antes de leer los números.
5. Cierro con la decisión: **probé la contramedida, comprobé que no mejoró el resultado conjunto en este escenario y dejo de priorizar B**. Conservo código, resultados y explicación para que quede claro qué se intentó y por qué no continué por ahí.

Mi frase de cierre sería: “La distribución sí puede reducir el efecto de ciertos flips, pero en las campañas que probé no compensó la mayor aceptación de alteraciones. Con los mismos intentos terminé con más cambios de banda sin alerta. Por eso no la presento como una mejora del sistema”.

## Archivos de respaldo

Esta nota reúne resultados guardados; no genera otro entrenamiento ni otra campaña. La verificación del 11 documenta dos ejecuciones completas con tablas idénticas.

- [Comparación y explicación de CCA](avance_junta_09.md).
- [Daño diario de CCA](avance_junta_10.md).
- [Verificación en 27 estaciones](avance_junta_11.md).
- [Protocolo final](resultados/11/protocolo.json), [cobertura](resultados/11/cobertura.csv) y [promedios por estación](resultados/11/macro.csv).
