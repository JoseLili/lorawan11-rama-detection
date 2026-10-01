# Experimento multiestación V4/p95 — 2026-09-28

## Protocolo fijado antes de ejecutar

Referencia nueva y separada de CCA con corte operativo 22.6 ppb. No se
sobrescriben el modelo piloto ni sus figuras. Archivo de entrada: RAMA O3
2025, 33 estaciones con alguna observación; se reportan objetivos sin
ventanas válidas en vez de asignarles detección cero.

- Un LSTM por objetivo, alimentado por las otras 32 estaciones: 66 features
  (valores normalizados, máscaras y hora seno/coseno), ventanas de 24 horas.
- Arquitectura `construir_modelo`, entrenamiento `entrenar`: semilla 42 antes
  de cada construcción, perfil de 14 días, split cronológico 80/20, validación
  interna 20 %, máximo 60 épocas, batch 64, EarlyStopping paciencia 8.
- Corrección local del respaldo del perfil V4: medias horarias del train,
  no del año completo; si falta una hora, media global del train. En test
  el perfil móvil usa valores anteriores. Se conserva la fórmula de V4;
  los primeros valores y, por tanto, el ajuste pueden diferir del piloto.
  La validación interna conserva el preprocesamiento ajustado al bloque train
  completo, como el protocolo heredado; no es una evaluación independiente.
- p95 de cada objetivo sobre todos sus residuos de entrenamiento limpio,
  incluido el tramo de validación interna. No se ajusta sobre el test.
- Guardado por estación de modelo, p95, preprocesamiento, historia, predicciones
  y hashes. Reanudación sin reentrenar checkpoints completos. Un cambio de
  configuración o código requiere otra referencia, no mezcla de resultados.

## Dos evaluaciones distintas

1. **Muestra pareada al 5 %**, bits 1–7: TP, FP, FN, TN, recall, precisión y
   F2 por estación. La semilla de ataque 42 mantiene los mismos mensajes
   atacados entre bits dentro de una estación. No tienen por qué ser 78 en
   otras estaciones: dependen de sus datos disponibles. Se reporta además
   la tasa de falsas alarmas en todo el test limpio.
2. **Barrido exhaustivo de ataques aislados:** cada mensaje observado del
   periodo común se ataca individualmente, una estación/una hora/un bit por
   escenario. Cadena real encode/cifrar/flip/descifrar/decode, cotejada con XOR.
   Los siete escenarios por mensaje son independientes, nunca simultáneos.
   La predicción se reutiliza: el target está excluido de las entradas y
   el perfil previo no cambia ante una alteración aislada del mensaje actual.

El periodo común empieza 24 horas después del corte 80/20 y termina el
31 de diciembre de 2025. No se atribuye detección a la temporada cálida
entrenada ni a todo el año. Los faltantes no son cero, ni aciertos.

## Decisión de la red y cobertura

Se reemplaza un solo mensaje y se recalcula el máximo diario de TODAS las
observaciones de la red, conservando competidores sin modelo y empates.
Se examinan también estaciones que no tenían el máximo original.

- `falsa_fase1`: máximo diario observado <155 y máximo contrafactual >=155.
- `anulada_fase1`: máximo original >=155 y contrafactual <155.
- `cruce_fase1`: cualquiera de los dos casos.
- `cambio_banda_red`: cambia la banda del máximo diario; también se guarda
  el cambio de banda local, que no necesariamente altera la decisión de red.

Son cambios del **indicador de excedencia del máximo diario observado**,
no activaciones/suspensiones oficiales de contingencias. No se verifica una
regla de persistencia ni se simulan decisiones administrativas. La presencia
de datos faltantes impide afirmar el máximo físico completo de la red.

Un mensaje sin modelo se conserva para calcular el máximo y para contar
oportunidades conocidas SIN evaluación de detección. Nunca se considera
silenciosamente detectado/no detectado. CSVs detallan cobertura por estación,
mensaje y día; los porcentajes evaluables pueden subestimar oportunidades
totales. Se distinguen días vulnerables observados, evaluables y con daño
sin evaluación.

## Figuras

El denominador diario es el mismo conjunto de días de test observado en
todas las curvas rojas. Se cuenta cada día una vez aunque haya múltiples
mensajes dañinos. Un día con un ataque dañino detectado y otro no detectado
sí tiene una oportunidad de daño no detectado.

Se generan dos figuras para cruces de 155 y otras dos para cambios de banda:

- Rojo: % de días con al menos un ataque dañino evaluable; verde: % de
  ataques dañinos evaluables detectados.
- Rojo: % de días con al menos un ataque dañino no detectado; misma verde.

Ambas magnitudes se calculan evento por evento sobre las mismas estaciones
y fechas evaluables, pero sus denominadores (días vs ataques) son distintos.
**No se multiplica oportunidad por recall promedio ni se fuerza monotonicidad
o un máximo interior.** Si no hay ataques dañinos evaluables, la detección es
indefinida (NaN), no 0 ni 100 %. Estas figuras empíricas se nombran
`oportunidad_real` y `dano_no_detectado`: no son las curvas anteriores de
franjas ideales o riesgo compuesto. Un cruce visual no demuestra una frontera.

Ejecución y lectura: `notebooks/09_deteccion_red.ipynb`.
Resultados: `results/multiestacion_v4_p95_2025/`.
Figuras: `docs/img/multiestacion_v4_p95_2025/`.

## Cobertura comprobada en esta corrida

Se pueden evaluar **27 de las 33 estaciones candidatas**. AJU, CHO, FAR,
IZT, MON y TAH tienen datos de entrenamiento, pero ninguna ventana de
prueba; no se entrenan modelos sin posibilidad de evaluación en este periodo.
Siguen siendo vecinas de los otros objetivos, con la máscara de ausencia
cuando no reportan; cada modelo conserva las 66 características originales.

El periodo común es **2025-10-21 a 2025-12-31: 72 días**, no 365.
Se observaron **35,704 mensajes de 57,024 posiciones horarias posibles**
(33 estaciones × 24 horas × 72 días). El máximo observado en ese periodo
fue **152 ppb**: no hubo días con máximo >=155. Por tanto, se pueden
estudiar falsas excedencias, pero **no la anulación de las contingencias
reales de temporada cálida**. Cero anulaciones aquí significa ausencia
de casos, no una garantía de protección.

## Resultados de la ejecución

27 modelos completados, 189 evaluaciones pareadas estación/bit y 249,928
contrafactuales aislados; entrenamiento acumulado de 303.5 segundos.
Todos los mensajes observados del periodo tienen una predicción evaluable;
la cobertura física sigue limitada por los faltantes.

| Bit | Días con falsa excedencia posible | Días con falsa excedencia no detectada | Ataques dañinos detectados / evaluables |
|---:|---:|---:|---:|
| 1 | 0 | 0 | Sin casos |
| 2 | 1 | 0 | 1 / 1 |
| 3 | 0 | 0 | Sin casos |
| 4 | 2 | 1 | 5 / 6 |
| 5 | 9 | 0 | 46 / 46 |
| 6 | 9 | 0 | 46 / 46 |
| 7 | 72 | 0 | 14255 / 14255 |

Para cambios de banda del máximo diario, los días con oportunidades no
detectadas son 0, 4, 10, 15, 16, 9 y 0 (bits 1–7): máximo 22.22 % en bit 5.
No mezclar esta métrica con cruces de 155 ppb ni con cambios de banda locales.
Son oportunidades contrafactuales, no ataques ocurridos ni probabilidades
de éxito de un adversario ciego que selecciona mensajes al azar.

Falsas alarmas en test limpio: **5642/35704 = 15.80 %**, calculado sumando
conteos. Rango por estación: 3.63–26.64 %. El p95 no resuelve por sí solo
el problema de generalización; no se declara una mejora global del detector.

Se verificó recarga de modelos CCA/ACO y coincidencia de predicciones y
alertas para bits 1, 5 y 7; 100 máximos contrafactuales coincidieron con
recalcular literalmente el día completo. Run All fue probado con construcción,
entrenamiento y guardado de modelos bloqueados. Los artefactos previos de
CCA permanecen intactos. La presentación final de las figuras está en la
última celda de código del notebook 09 (leyenda fuera del área de datos).
