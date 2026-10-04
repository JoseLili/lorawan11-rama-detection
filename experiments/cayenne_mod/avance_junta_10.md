# Segundo punto: CCA, daño diario y relación con las alertas

Se reutilizan las **predicciones y p95 guardados de CCA**, sin entrenamiento
ni inferencia nueva: 1 684 lecturas en 72 fechas, 100 campañas del 08, mismo
5 % de selección y N uniforme 1…16 sobre posiciones 0…15. Base y B reciben
los mismos ataques. Umbral del detector: 14.748355 ppb.

Cada conteo siguiente corresponde a días-campaña acumulados en 100 sorteos:
hay 7 200 por formato, pero sólo 72 fechas originales. No se interpreta
como 7 200 días independientes ni se extrapola a otros años.

## Banda del máximo diario observado de CCA

| Medida | Base + LSTM | B + LSTM |
|---|---:|---:|
| Días-campaña con banda distinta | 133 | 366 |
| Con daño y sin ninguna alerta del día | 5 | 5 |
| Con daño y sin alerta en valores alterados | 32 | 29 |
| Daño persiste al restaurar alterados detectados | 33 | 31 |
| Daño persiste sólo con alteraciones sin alerta | 4 | 5 |

Estas filas no son sumables. Los días dañados pueden tener alertas; en el
protocolo actual las alertas no retiran automáticamente las lecturas.
Una falsa alarma en una lectura limpia del mismo día no se acredita como
detección de la alteración que produjo daño.

La tercera fila incluye días dañados por pérdida de datos: el LSTM no puede
evaluar una lectura rechazada. El decodificador sí registra el rechazo.
Por ello, menos días en esa fila no bastan para declarar superioridad de B.

Las dos últimas filas son reconstrucciones explicativas con originales
conocidos por el simulador. Primero se restauran los valores alterados que
generaron alerta, conservando los rechazos. Después también se restauran
los rechazados, dejando sólo alteraciones aceptadas sin alerta. Se cuenta
persistencia únicamente en días que ya tenían daño en la campaña real.
Esto no simula una corrección disponible al receptor, ni una política de
eliminación de mensajes. La diferencia entre 4 y 5 casos es pequeña y no
se presenta como evidencia de superioridad estadística.

## Origen del cambio de banda

De los 133 días-campaña dañados de Base, en 104 las alteraciones de valor
por sí solas bastan para cambiar la banda y en 29 bastan las pérdidas.

De los 366 de B, en 339 bastan las alteraciones de valor, en 25 bastan las
pérdidas, en uno bastaría cualquiera de los dos componentes por separado,
y en otro se requiere su interacción. Las categorías son exclusivas en
esta clasificación; no se suman los dos contrafactuales directamente.

Ejemplo de interacción: originales 60, 59 y 20; se rechaza 60 y se modifica
59 a 27. El máximo final es 27. Cada acción aislada dejaría 59 o 60, en la
banda original, pero juntas cambian la banda. Un rechazo nunca se imputa
como cero. No hubo días completamente sin datos en estas campañas; el
código los reconoce como decisión indefinida y las pruebas cubren ese caso.

## Cruces de 155 ppb

| Medida diaria | Base + LSTM | B + LSTM |
|---|---:|---:|
| Falsas excedencias del máximo | 57 | 208 |
| Sin ninguna alerta del día | 0 | 0 |
| Sin alerta en valores alterados | 0 | 1 |
| Persiste sólo con alteraciones sin alerta | 0 | 1 |

En el caso silencioso de B sí hay alguna otra alerta en el día. Por eso
contar cualquier alerta habría ocultado que el ataque no generó una señal
en valores alterados. Los cruces del máximo observado de CCA no equivalen
a activar oficialmente una contingencia.

El máximo limpio de CCA es 145 ppb. No hay excedencias originales ≥155 y
por tanto **no es evaluable el ocultamiento de excedencias en este test**.
Sus ceros se conservan para auditoría, sin atribuir protección perfecta.

## Conclusión y continuidad

No se demuestra una mejora global de B en estas campañas. Es necesario
mantener separados daño por valores, daño por pérdidas y alertas del
detector. El efecto diario tampoco puede inferirse sumando cambios de
banda de lecturas aisladas.

Se completa este análisis diario de CCA bajo el protocolo actual. El tercer
punto exige un conjunto con excedencias originales suficientes y un corte
temporal válido para evaluar ocultamiento con el detector. Validar otras
estaciones y años y simular propagación a futuras entradas sigue pendiente.

Validación: dos ejecuciones idénticas; máximos, daños y conteos de alertas
reproducen el 08. Las pruebas cubren falsas alarmas ajenas al ataque,
alteraciones detectadas que no explican todo el daño, múltiples ataques,
interacciones con pérdida, días sin datos y el límite de 155 ppb.

[Notebook ejecutado](10_dano_diario_base_B_CCA.ipynb),
[resumen numérico](resultados/10/resumen.csv),
[ejemplos diarios](resultados/10/ejemplos.csv),
[protocolo](resultados/10/protocolo.json).
