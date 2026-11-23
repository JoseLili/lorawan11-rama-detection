# STC-RAAD frente a PARAAD como comparador (lectura del 2026-11-23)

Pregunta del tesista: ¿por qué nos comparamos con PARAAD y no con STC-RAAD, y valía más la pena STC-RAAD?

Fuente leída completa: Allka, Ferrer-Cid, Barceló-Ordinas y García-Vidal (2024), *Leveraging Spatiotemporal
Correlations With Recurrent Autoencoders for Sensor Anomaly Detection*, IEEE IoT Journal 11(19), 31144–31152,
doi:10.1109/JIOT.2024.3416525 (versión aceptada en UPCommons, 9 páginas). También la tesis doctoral de Allka
(UPC, doi:10.5821/dissertation-2117-457522), donde STC-RAAD es el capítulo 7. No hay código público de STC-RAAD
(el GitHub de la autora solo tiene PARAAD).

## Por qué se eligió PARAAD (reconstruido de los documentos)

No hubo una comparación técnica entre los dos. El 2026-10-23 PARAAD se leyó completo y de STC-RAAD solo el
resumen; el 2026-10-26 el asesor pidió «el grupo de Barcelona en la misma tabla» y se tomó el que ya se conocía
y cuyos datos ya se tenían (`docs/inicio_paraad.md`). STC-RAAD se marcó el 2026-11-07 como «el comparador
conceptual más cercano», ya con PARAAD hecho.

## Qué es STC-RAAD (del texto)

- **Unidad:** un sensor a la vez. La tesis lo llama el caso «un solo sensor»; PARAAD es el caso «red de
  sensores, detectar y localizar» y viene después (cap. 5 de la tesis).
- **Vecinas:** para cada sensor objetivo se aprende un grafo con el método de Dong et al. (suavidad + dispersión
  de la laplaciana) y se toman los nodos conectados: entre 1 y 4. No usa la distancia: dicen que cercanía no
  implica correlación. Con una sola vecina el recall de sesgo pasa de 0.55 a 0.91 (§IV-G).
- **Modelo:** autoencoder BiLSTM pequeño (capas de 5, 3 y 5 unidades), un modelo por sensor objetivo. Entrada:
  bloques diarios no traslapados (K = 24 h) del sensor y sus vecinas, estandarizados.
- **No supervisado:** se entrena con datos que se suponen limpios (70 % de los datos; 30 % de prueba).
- **Puntaje:** error absoluto medio de reconstrucción del sensor objetivo en el bloque (estación-día).
- **Umbral:** se ajusta en una ventana deslizante de 30 bloques maximizando la exactitud y minimizando la tasa de
  falsos positivos, y se aplica al bloque siguiente. Para maximizar la exactitud hacen falta las etiquetas, así
  que el umbral usa información del ataque (más optimista que nuestro umbral fijo de 2023 limpio; igual que en
  PARAAD).
- **Anomalías sintéticas:** sesgo constante de μ desviaciones típicas, con μ de una normal positiva (σ ≥ 1,
  principal σ = 2), en el 25 % de los bloques de prueba; deriva no lineal en la señal estandarizada durante 5 a
  25 días. Solo se altera el sensor evaluado: **sus vecinas siempre están limpias.**
- **Datos:** 8 estaciones de referencia de Barcelona (O3 y NO2, 2014–2019) y 30 sensores de bajo costo de O3 en
  Taiwán (2020–2022).
- **Resultados O3 Barcelona, sesgo σ = 2 (tabla I):** recall 0.82–0.96 y precisión 0.85–0.91 según el sensor.
  Deriva de 25 días (tabla III): recall 0.83–0.95 y precisión 0.70–0.79.

## Diferencias con nuestro escenario

| | STC-RAAD | Nuestro detector final | PARAAD (como lo corrimos) |
|---|---|---|---|
| Usa vecinas | Sí, 1–4 por grafo aprendido | Sí, 4 por cercanía, con filtro | No |
| Aprendizaje | No supervisado | Supervisado | No supervisado |
| Unidad | Sensor-día | Estación-día | Estación-día |
| Modelos | Uno por sensor | Ensamble compartido | Uno para la red |
| Umbral del artículo | Ajustado con etiquetas cada 30 días | Percentil fijo de 2023 limpio | Ajustado con etiquetas (lo cambiamos a p99 de 2023) |
| Ataque a vecinas | Nunca probado | Escenario 3 | Escenario 3 |
| Proporción de días anómalos | 25 % | 0.77 % | 0.77 % |

## ¿Valía más la pena STC-RAAD?

**Para la pregunta central de la tesis, sí era el comparador más directo.** La tesis defiende que usar a las
vecinas ayuda. STC-RAAD es lo mismo pero sin supervisión: estación-día, bloque diario, 1–4 vecinas. Con él se
habría medido si la supervisión, la forma de elegir vecinas y el filtro aportan algo sobre un método publicado
que ya usa vecinas. PARAAD no responde esa pregunta, porque no usa vecinas.

**PARAAD no fue un error**, por tres razones:
1. Es el trabajo posterior del mismo grupo (en la tesis de Allka, STC-RAAD es el caso de un sensor y PARAAD el
   de la red completa).
2. Fue el que pidió el asesor y ya se tenían sus datos.
3. Dio un hallazgo que STC-RAAD probablemente no daría. Con todas las vecinas atacadas o con un sesgo de más de
   un mes, PARAAD sigue detectando y nuestro detector no. STC-RAAD reconstruye con las vecinas, así que lo más
   probable es que falle igual que el nuestro cuando ellas están alteradas. Es una hipótesis: el artículo no lo
   probó.

**Costo de agregarlo:** moderado. No hay código, pero la arquitectura es pequeña y está descrita: la laplaciana
de Dong et al., 31 autoencoders de 5-3-5 unidades y bloques diarios. Habría que reemplazar su umbral con
etiquetas por el p99 de 2023 limpio, como se hizo con PARAAD, y registrarlo como revisión nueva antes de
correrlo. No es necesario para la presentación.

**Cómo decirlo en la presentación:** PARAAD representa el estado del arte de la red completa del mismo grupo.
STC-RAAD, el más cercano en diseño porque usa vecinas, queda como comparación pendiente y limitación declarada.
Sus cifras (R 0.82–0.96, P 0.85–0.91) se obtuvieron con 25 % de días anómalos, vecinas siempre limpias y umbral
ajustado con etiquetas, así que no se comparan con las nuestras.

## Resultados de STC-RAAD y los nuestros en la misma escala (2026-11-23)

Tablas del artículo (promedio de 25 experimentos por sensor; recall = TPR):

| Caso | Recall STC-RAAD | Precisión STC-RAAD | Mejor rival solo temporal (BiLSTM) |
|---|---|---|---|
| Sesgo σ = 2, O3 Barcelona, 8 sensores (tabla I) | 0.82–0.96 (media 0.88) | 0.85–0.91 (media 0.88) | R 0.52–0.65, P 0.64–0.75 |
| Sesgo σ = 2, NO2 Barcelona / O3 Taiwán (tabla II) | 0.78–0.83 / 0.82–0.95 | 0.85–0.89 / 0.89–0.92 | |
| Deriva de 25 días, O3 Barcelona (tabla III) | 0.83–0.95 (media 0.88) | 0.70–0.79 (media 0.74) | R 0.54–0.66, P 0.34–0.45 |
| Sesgo σ = 1, sensor 1 (fig. 2) | 0.72 | 0.82 | |
| Deriva de 5–10 días, sensor 1 (fig. 3) | 0.72–0.86 | 0.30–0.51 | |
| Sensor 1, sin vecinas → con 1 vecina (fig. 5), sesgo | 0.55 → 0.91 | 0.73 → 0.90 | |

**Traducción del sesgo a ppb en RAMA.** El sesgo de STC-RAAD es μ desviaciones típicas con μ = |N(0, σ²)|. La
desviación típica horaria del O3 en los 31 objetivos (2020–2022) es 25.1 ppb (17.2–29.9). Con σ = 2: media 1.6 dt
≈ 40 ppb, mediana ≈ 34 ppb; 16 % de los sesgos quedan por debajo de 10 ppb, 31 % por debajo de 20 ppb y 57 % por
debajo de 40 ppb. Su σ = 1 tiene media ≈ 20 ppb. Su escenario equivale a nuestro E1 (una estación atacada, vecinas
limpias), con sesgo aplicado a días completos.

**Precisión con su proporción de días anómalos.** La precisión depende de cuántos días están atacados. Con el recall
de E1 (rev24, banco 2024–jul 2026) y la tasa de falsas alarmas de los años limpios, la precisión si el 25 % de los
días estuvieran atacados es P = R·0.25 / (R·0.25 + FA·0.75):

| Detector, umbral | +20 ppb R / P(25 %) | +40 ppb R / P(25 %) | δ100 R / P(25 %) | FA |
|---|---|---|---|---|
| Final, p99 | 0.83 / 0.96 | 0.96 / 0.96 | 0.93 / 0.96 | 1.3 % |
| Final, p99.9 | 0.44 / 0.99 | 0.78 / 0.99 | 0.64 / 0.99 | 0.18 % |
| PARAAD, p99 | 0.57 / 0.88 | 0.92 / 0.92 | 0.68 / 0.90 | 2.6 % |
| PARAAD, p99.9 | 0.25 / 0.92 | 0.79 / 0.97 | 0.51 / 0.96 | 0.77 % |

Recall del detector final p99 sobre la mezcla de sesgos σ = 2 (cotas por interpolación monótona entre 10, 20 y
40 ppb): entre 0.66 y 0.84 (PARAAD: entre 0.56 y 0.77), contra 0.82–0.96 de STC-RAAD.

**Lectura.** Con un sesgo fijo del tamaño típico de su escenario (+40 ppb ≈ su media), el detector final p99 queda
en el mismo nivel que STC-RAAD (R 0.96, P(25 %) 0.96) y con un umbral fijo de 2023 limpio, más estricto que su umbral
ajustado con etiquetas. Con la mezcla de tamaños, la cota baja (0.66) está bajo su rango y la alta (0.84) dentro:
no se puede afirmar que seamos mejores. La precisión re-escalada es un cálculo, no una medición: supone que las falsas
alarmas de los años limpios se mantienen. Son datos, redes y procedimientos distintos; sirve como orden de magnitud,
no como comparación en la misma tabla. La deriva de STC-RAAD (raíz creciente en datos estandarizados) no tiene
equivalente directo en nuestros escenarios.
