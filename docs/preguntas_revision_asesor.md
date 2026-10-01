# Preguntas abiertas para la revisión con el asesor

Este documento registra las decisiones que deben confirmarse antes de cerrar la
gráfica final y continuar con la contramedida de codificación.

## Estado al 2026-09-29

- **J1:** repaso realizado con el tesista y [CSV de una ventana real exportados](../results/muestra_entrada_lstm_v4_cca/README.md).
  Falta presentarlos al asesor y confirmar si pide también contexto contemporáneo.
- **J2:** [revisión de figuras implementada](revision_graficas_2026-09-29.md), al final
  del notebook 09: bits 0–7, no detección y tres curvas, leyendas breves. No se
  reentrenó. El producto se conserva como indicador descriptivo, no como daño
  conjunto observado; los conteos reales se reportan aparte. Revisión visual y
  aceptación metodológica pendientes. El análisis anual sin LSTM separa falsas
  activaciones y ocultamientos; no se extrapola la detección del test a todo 2025.

## Actualización de seguimiento — 2026-09-28

Fecha de registro de la transcripción, no fecha confirmada de la junta.
El detalle, la evidencia y los criterios de cierre se centralizan en
[progreso.md, tareas J1–J8](progreso.md#siguiente). La lista antigua se conserva
abajo como historial; no todas sus preguntas siguen abiertas.

### Respuestas ya verificadas para comunicar al asesor

- **J1 — Entrada LSTM:** sí hay una columna por estación y alineación horaria.
  Para CCA, ventanas de 24 horas × 66 características de sus 32 vecinas,
  máscaras y hora. Se excluye CCA como canal, pero su pasado sí interviene
  en el perfil adaptativo. No se usan etiquetas de ataque como entradas.
- **J1 — Tiempo:** son las 24 horas anteriores de las vecinas, no sus
  mediciones contemporáneas. El perfil de 14 días es un componente distinto.
- **J2 — Alcance:** no basta transferir el recall de CCA a toda la red.
  Ya hay 27 modelos evaluables de 33 candidatos y análisis mensaje por
  mensaje; el test común de 72 días no incluye las contingencias de marzo–abril.
- **J4 — Codificación existente:** V1/V2 usan grupos fijos, no la elección
  aleatoria de posiciones de igual peso propuesta en esta junta.

### Preguntas que sí debemos resolver ahora

1. **J2 — Tres curvas:** la lectura del audio es oportunidad de daño,
   porcentaje NO detectado y riesgo combinado. ¿La unidad común será día
   o ataque? ¿Qué daño queremos priorizar? No mezclar días y mensajes al
   multiplicar ni llamar cruce real a una franja que supone sumar siempre.
2. **J3 — Pesos:** ¿confirmamos un grupo de **siete posiciones de 8 ppb**?
   Bit 3 = 8, bit 4 = 2×8, bit 5 = 4×8. El audio también menciona 4 ppb,
   pero siete posiciones de 4 no conservan el rango de esos tres bits.
   Fijar además dominio, posiciones reservadas y política de rechazo.
3. **J1 — Contexto:** ¿se solicita una variante que use vecinas de la misma
   hora objetivo, además de comprobar el modelo temporal ya implementado?
4. **J5 — Comparación:** ¿aceptamos número de flips físicos como eje X para
   la contramedida, con desplazamientos resultantes aparte? Dos flips no
   equivalen siempre a atacar un bit original de peso doble.
5. **J7 — Detector:** documentar qué política se conserva en la comparación
   combinada: piloto CCA a 22.6 ppb o red con p95 por estación. Son referencias
   distintas, no un único umbral intercambiable.

### Dirección recogida de la junta, pendiente de ejecutar

- Corregir primero la figura base y sus nombres; no forzar cruces o máximos.
- Evaluar la nueva distribución **sin LSTM primero**, en ambos sentidos del
  daño; después combinarla con los detectores guardados.
- El atacante conoce el formato; sus posibilidades no se restringen sólo
  porque no vea el valor claro. Especificar las estrategias comparadas.
- Dejar ataques sostenidos y permutación de pesos distintos como extensiones.
  Obtener datos/fuentes antes de concluir sobre doce ataques consecutivos.

---

## Lista anterior — historial, no lista vigente

Se preserva para seguir la evolución de las preguntas. Las respuestas y
pendientes actuales son los de la sección anterior y J1–J8 de `progreso.md`.

### Gráfica final

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

### Estado de los datos cuando se redactó la lista anterior

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

### Contramedida de codificación

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

Esta lista registraba las preguntas de esa etapa. Para no reabrir las ya
resueltas ni perder las nuevas, consultar el seguimiento vigente J1–J8.
