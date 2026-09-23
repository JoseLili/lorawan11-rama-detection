# Preguntas abiertas para la revisión con el asesor

Este documento registra las decisiones que deben confirmarse antes de cerrar la
gráfica final y continuar con la contramedida de codificación.

## Gráfica final

1. ¿La vulnerabilidad debe definirse como:
   - cambio de banda NOM-172 en cualquier lectura horaria, o
   - posibilidad de fabricar/anular una contingencia de red a partir del
     máximo diario?

2. Cuando se habla de «porcentaje de días vulnerables», ¿el denominador debe
   ser:
   - todos los días del año,
   - días con datos válidos de la estación, o
   - días con datos válidos del máximo de la red?

3. ¿La curva de daño debe mostrar:
   - daño detectado,
   - daño no detectado (100 - detección), o
   - ambas curvas?

4. ¿La detección de la gráfica debe corresponder al LSTM específico de la
   estación que produjo el máximo diario, o basta reportar la detección piloto
   de CCA como referencia?

5. ¿Se deben mostrar por separado las falsas contingencias y las contingencias
   anuladas, o agregarlas como una única medida de impacto operativo?

6. ¿La gráfica debe incluir los bits 3–7 o concentrarse en la zona explotable
   (bits 4–6)?

7. Para fase 2, ¿se debe aplicar explícitamente la condición de permanencia de
   200 ppb durante una hora, o basta presentar el cruce instantáneo como
   análisis exploratorio?

## Estado actual de los datos

- El análisis de 08_proximidad_umbrales.ipynb usa el máximo diario de toda la
  red.
- La tabla results/tabla_eventos_contingencia_red.csv contiene un registro por
  día y bit, incluyendo estación, hora, valor original, valor atacado, cambio
  de banda y falsas/anuladas de fase 1.
- Las cinco fechas de contingencia por O3 están registradas:
  2025-02-26, 2025-03-18, 2025-04-01, 2025-04-23 y 2025-04-25.
- El evento del 2025-01-01 corresponde a PM2.5 y no debe mezclarse con el
  análisis exclusivo de O3.
- La evaluación multiestación del LSTM usa un corte cronológico 80/20; por
  ello, las contingencias de marzo–abril quedan fuera del periodo de prueba.

## Contramedida de codificación

La propuesta discutida consiste en reemplazar el peso binario único de los bits
de mayor impacto por varios fragmentos de igual peso o peso repartido. Antes de
implementarla deben confirmarse:

1. ¿Se conserva exactamente el tamaño del payload CayenneLPP?
2. ¿La transformación se aplica en el sensor, en el Network Server o en el
   Application Server?
3. ¿El receptor reconstruye determinísticamente el valor original?
4. ¿La redundancia ocupa bits actualmente sin utilizar o aumenta la longitud
   del payload?
5. ¿El adversario conoce la nueva distribución de bits?
6. ¿La evaluación comparará el mismo conjunto de ataques y métricas antes y
   después de la recodificación?
7. ¿El objetivo principal es reducir el daño por flip, reducir la probabilidad
   de acertar el fragmento correcto, o ambas cosas?

Estas preguntas deben resolverse con el asesor antes de presentar la gráfica
como resultado definitivo o incorporar la codificación modificada como
contramedida formal.
