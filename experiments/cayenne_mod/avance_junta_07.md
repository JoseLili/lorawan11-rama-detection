# Experimento 07: compensación con varios flips

La compensación propuesta **sí aparece**, pero no garantiza una mejora
general frente a ataques de varios flips. El resultado depende del número
de bits modificados, sus estados iniciales y las posiciones elegibles.

Se usaron las **predicciones y p95 por estación guardados del notebook 09**,
sin entrenamiento ni inferencia nueva: 35 704 mensajes en 72 días. Cada
escenario modifica un mensaje; conserva las otras lecturas, la predicción
y el perfil. Las máscaras del mismo tamaño tienen igual probabilidad.
Los resultados son promedios exactos, no una muestra aleatoria.

## Siete bits de peso 8 de B

| Flips distintos | Lectura intacta | Cambios de banda sin alerta, esperados |
|---:|---:|---:|
| 1 | 0 % | 10.57 |
| 2 | 27.12 % | 28.90 |
| 3 | 0 % | 85.91 |
| 4 | 15.60 % | 96.97 |
| 5 | 0 % | 76.38 |
| 6 | 10.63 % | 57.57 |
| 7 | 0 % | 30.00 |

La última columna es el número esperado de oportunidades entre los
35 704 mensajes, evaluados **por separado**; no representa días ni ataques
simultáneos a toda la red. Aquí se incluye el bit 3, a diferencia de los
seis fragmentos elegibles del experimento 06.

Con N impar, las contribuciones ±8 no pueden sumar cero. Con N par pueden
cancelarse, pero no siempre. Por ejemplo, invertir los bits 3 y 11 conserva
28 ppb y transforma 60 en 44 ppb: los estados iniciales son distintos.

Al aumentar N, también crece el daño posible. En este grupo, el mayor
promedio de cambios de banda sin alerta aparece con cuatro flips. La tasa
de alertas entre valores alterados sube de 21.64 % con un flip a 72.86 %
con cuatro, pero no alcanza a compensar el crecimiento del daño.

## Comparación en las 16 posiciones del valor

| N | Base: banda sin alerta / todos | B: banda sin alerta / todos | Base: banda sin alerta / aceptados | B: banda sin alerta / aceptados |
|---:|---:|---:|---:|---:|
| 1 | 0.0714 % | 0.0324 % | 0.1428 % | 0.0432 % |
| 2 | 0.0482 % | 0.0445 % | 0.2064 % | 0.0810 % |
| 3 | 0.0223 % | 0.0563 % | 0.2232 % | 0.1432 % |
| 4 | 0.0076 % | 0.0494 % | 0.1984 % | 0.1815 % |
| 5 | 0.0019 % | 0.0359 % | 0.1472 % | 0.1980 % |

Con tres flips, B tiene mayor riesgo entre todos los intentos que la base,
aunque mantiene menor riesgo entre los aceptados. La base rechaza el 90 %
de los intentos y B el 60.71 %: esa diferencia afecta la comparación.
Con cinco flips B también tiene mayor riesgo entre los aceptados. No hay
una ventaja uniforme para todos los presupuestos.

Rechazar una lectura no equivale a que el LSTM detecte el ataque. La pérdida
de datos y su efecto posterior no se simulan. El campo de 16 posiciones se
refiere al valor, no a todos los campos de una trama LoRaWAN.

## Atacante que elige posiciones

Ver texto cifrado no obliga al atacante a seleccionar bits uniformemente.
Si conoce la distribución, puede invertir los cuatro fragmentos del bit 5
en B: posiciones 5, 9, 10 y 11. Recupera exactamente el cambio de ±32 del
bit 5 original, sin necesitar conocer su estado previo.

Esa máscara de cuatro flips produce 228 oportunidades de cambiar banda sin
alerta en este test, igual que invertir el bit 5 de la base con un solo flip.
Esto indica un aumento del costo en flips para reproducir ese ataque, no
su eliminación. La peor máscara fija es una sensibilidad retrospectiva;
no es una estimación validada del comportamiento futuro de un atacante.

## Alcance de las conclusiones

El detector responde a `residuo_limpio + cambio_neto`. Un cambio grande
puede acercar la lectura a la predicción; no garantiza alerta. El MAE no es
el umbral operativo y aquí se utilizan p95 distintos por estación.

El test tiene máximo limpio de 152 ppb: no permite evaluar con LSTM el
ocultamiento de excedencias originales de 155 ppb. El análisis anual
incluye seis días con esas excedencias y se presenta aparte, sin detector;
no constituye una validación independiente porque incluye el test.

La conclusión defendible es que **repartir pesos permite compensación y
aumenta el número de flips necesario para ciertos cambios dirigidos, pero
su beneficio frente al daño no detectado depende del modelo de ataque**.
Falta validar en otro periodo, estudiar ataques a varios mensajes y evaluar
la pérdida de lecturas y la propagación a predicciones futuras.

Verificación: dos ejecuciones completas con tablas exactamente iguales,
589 815 transformaciones cifradas verificadas y reproducción del experimento
05 para N = 1. Notebook y datos: [07](07_multiflips_compensacion.ipynb),
[resumen de test](resultados/07/test_resumen.csv),
[protocolo y fuentes](resultados/07/protocolo.json).
