# Protocolo: detección de anomalías a nivel de red (parte 2)

**Fecha:** 2026-10-12. **Identificador:** `anomalias_red_v1`.
**Estado:** acordado antes de programar; no contiene resultados.
**Origen:** junta con el asesor del 2026-10-12 (acuerdos L-A1 a L-A12 en
[`progreso.md`](progreso.md)) y decisiones del tesista del mismo día. Es el segundo eje de la
tesis y sustituye a las propuestas de drenado de energía e integridad
([`propuesta_consumo_deteccion_uclm.md`](propuesta_consumo_deteccion_uclm.md),
[`propuestas_reunion_2026-10-12.md`](propuestas_reunion_2026-10-12.md)), que no se adoptaron.
**Referencias que NO se modifican:** V4 multianual (`results/lstm_v4_multianual_v1/`), su
protocolo ([`protocolo_lstm_v4_multianual.md`](protocolo_lstm_v4_multianual.md)) y los
resultados y figuras de la parte 1.

## 1. Pregunta y alcance

¿Puede un detector alertar de que la red de estaciones RAMA tiene una anomalía, y qué tamaño
y qué duración necesita la anomalía para que lo logre?

- El detector **sólo alerta**. No corrige ni retira lecturas.
- **Anomalía:** cualquier alteración de la medición. Puede ser una descalibración, una
  falla, una manipulación física (por ejemplo, una fuente de ozono junto al sensor) o un
  ataque. No se supone intención.
- **Unidad de análisis: la red.** El detector decide cada hora si hay alguna estación
  anómala. Ubicar la estación queda para una etapa posterior (L-A8).
- Se busca hasta dónde se puede empujar el límite de detección, igual que en la parte 1:
  de alteraciones evidentes a sutiles.

**Hipótesis, común con la parte 1:** una alteración que cae dentro de la variabilidad legítima
de la red no se detecta, sin importar la complejidad del detector ni si aprende con etiquetas.

## 2. Relación con la parte 1 (bit flipping)

El aporte es la comparación entre ambas partes. Por eso se deja explícito qué cambia:

| | Parte 1 | Parte 2 |
|---|---|---|
| Alteración | Bit volteado: ±2^k ppb durante una hora | Factor (1 ± δ) sostenido de 1 a 7 días |
| Unidad | Lectura de una estación | Hora de la red |
| Datos y división | 2025 con división dentro del año (inicio); 2020–2026 (V4) | 2020–2026 con la división del V4 |
| Falsas alarmas | p95 por estación (≈ 5 % por lectura) | Fijas por hora de red (§9) |
| Daño | Cambio de banda NOM-172 o de 155 ppb sin alerta | Lo mismo, en las horas anteriores a la alerta |

Detectores en cada parte:

| Detector | Tipo | Parte 1 | Parte 2 |
|---|---|---|---|
| Random Forest | Simple, supervisado | CCA 2025: valor y hora (notebook 06) | Red: 66 columnas de la hora t |
| IsolationForest | Simple, no supervisado | CCA 2025: valor y hora (notebook 06) | Red: 66 columnas de la hora t |
| LSTM V4 | Complejo, no supervisado | 31 estaciones, prueba 2024–2026 | El mismo modelo, con alerta de red |
| LSTM clasificador | Complejo, supervisado | — | Opcional, si hay tiempo |

**Límite de la comparación.** Las celdas de Random Forest e IsolationForest de la parte 1 usan
otro periodo y otra división (2025, con 80/20 cronológico dentro del año). Para que la
comparación sea estricta habría que repetirlas con la división multianual (P3). Además, entre
las dos partes cambian a la vez el tipo de alteración, la unidad y el detector. Probar los
detectores de red también con alteraciones de bit flipping aislaría el efecto del tipo de
alteración (P4).

## 3. Datos y estaciones

- **Matriz:** la del V4 (§3.1 de su protocolo). Una fila por hora, del 2020-01-01 al
  2026-07-31, y 33 columnas (de ACO a XAL). COY, SJA y SFE quedan fuera, como en el V4.
- **XAL:** canal inactivo (valor 0 y máscara 0), como en el V4. El caso de una estación que
  reporta y luego deja de reportar es un experimento posterior (P5).
- **Estaciones que pueden recibir anomalías:** los 31 objetivos del V4. De ellos, 28 son
  principales; TLI, INN y AJM son de baja representatividad y se reportan aparte. HGM no se
  altera, porque no tiene modelo V4, pero sigue entrando como contexto.
- **Huecos conocidos** (verificados el 2026-10-12 en
  `data/processed/o3_2020_2026_ancho.parquet`): ACO sin datos en 2020 y 2024; HGM en
  2021–2022; AJM en 2021; AJU, CHO y FAR en 2026. No se interpolan.
- **Faltantes:** cada estación lleva una columna «tiene dato» (máscara) como entrada, igual
  que el V4. Sólo se alteran horas con dato.

## 4. División temporal

Es la del V4, sin cambios:

| Etapa | Periodo |
|---|---|
| Ajuste inicial | 2020–2021 |
| Validación | 2022 |
| Ajuste definitivo | 2020–2022 |
| Calibración | 2023, siempre limpio; sólo sirve para fijar umbrales |
| Prueba principal | 2024 |
| Pruebas complementarias | 2025 y 2026 (enero a julio) |

No se ajusta nada mirando 2024–2026.

## 5. Modelo de anomalía

- **Valor recibido durante el episodio:** x·(1 + δ) con signo +, y x/(1 + δ) con signo −.
  Con δ = 100 %, el doble frente a la mitad; con δ = 10 %, +10 % frente a −9.1 %. El valor
  nunca llega a cero ni a negativo.
- **δ ∈ {100, 50, 20, 10, 5} %.**
- **Signo:** se sortea una vez por episodio (50/50) y se mantiene durante todo el episodio,
  porque un sensor descalibrado se equivoca siempre hacia el mismo lado.
- **Duración:** días completos, un entero uniforme de 1 a 7. El episodio empieza a las 00 h,
  porque el asesor habló de anomalías «en días completos durante ciertos días». Un episodio
  que rebasa el final del periodo se corta.
- **Forma única:** error proporcional, equivalente a una descalibración de ganancia. Quedan
  fuera de esta versión el valor congelado, la deriva lenta, la repetición de datos viejos y
  los picos breves; se declaran como límite.
- **Efecto esperado:** como el error es proporcional al valor, con δ = 10 % es menor que 1 ppb
  de noche (5–10 ppb de ozono) y se concentra en las horas de la tarde.

## 6. Plan de inyección y tasa

- **Perilla:** la probabilidad p de que una estación empiece un episodio en un día en que no
  tiene uno activo. Las estaciones son independientes.
- **Rango:** p entre 0.10 % y 0.30 % por estación y día, con 0.15 % como base. En cada corrida
  de prueba, p se sortea de manera uniforme dentro del rango (tipo *nonce*). El plan de
  entrenamiento usa la base.
- **Equivalencias** (simulación con 31 estaciones y 200 años simulados, semilla 42; no
  interviene ningún modelo):

| p por estación y día | Episodios en 2024 | Episodios por estación al año | Horas de red con alguna anomalía | Horas con 2 o más a la vez |
|---:|---:|---:|---:|---:|
| 0.10 % | 11 | 0.36 | 11.5 % | 0.8 % |
| 0.15 % | 17 | 0.56 | 17.2 % | 1.5 % |
| 0.30 % | 33 | 1.07 | 30.6 % | 5.1 % |
| 0.50 % | 56 | 1.79 | 46.1 % | 12.3 % |

- **Diseño pareado:** cada corrida tiene un solo plan (estaciones, inicios, duraciones, signos
  y p), y ese mismo plan se aplica con todos los δ. Sólo cambia la magnitud.
- **Corridas:** 10 planes de prueba sobre 2024 y un plan de entrenamiento propio sobre
  2020–2022, independiente de los de prueba. Las semillas se derivan de la semilla maestra 42
  con identificadores estables, sin usar `hash()`, como en el V4 (§7.2).
- **Precisión esperada:** con unos 17 episodios por corrida, el porcentaje de detección de una
  sola corrida tiene un margen de ±23 puntos. Con las 10 corridas (unos 170 episodios), el
  margen baja a unos ±7–8 puntos.
- **Se guarda el plan, no sólo la semilla:** `plan_<corrida>.csv` con estación, inicio, fin,
  signo, p y número de episodio.
- **Coincidencias en la fase 1:** sólo las que surgen por azar (entre el 1 y el 5 % de las
  horas); se reportan.

## 7. Fases

- **Fase 1 (principal):** el plan de §6.
- **Fase 2:** episodios simultáneos a propósito en k estaciones. Antes de ejecutarla hay que
  definir (P2):
  - k (propuesta: 2, 4 y 8);
  - si las k estaciones comparten signo (el caso coherente, que se parece más a un episodio
    real de ozono y es el más peligroso) o no;
  - cómo se eligen las k estaciones.
- **Experimento secundario de prevalencia:** repetir la fase 1 con p = 0.10, 0.30 y 0.50 %.
  Debería mostrar que, con el mismo detector, el F1 cambia mientras la detección con falsas
  alarmas fijas se mantiene.

## 8. Detectores

Todos producen un puntaje por hora de red, y su umbral se fija con 2023 limpio (§9).

| Detector | Entrenamiento | Entrada |
|---|---|---|
| Random Forest | Supervisado, con el ajuste definitivo 2020–2022 y el plan de entrenamiento. Usa la etiqueta de red. Un modelo por δ, como en la parte 1 se entrenaba uno por bit. Hiperparámetros por omisión, `random_state=42`, sin ajuste | 66 columnas de la hora t: 32 valores normalizados, 32 máscaras, y seno y coseno de la hora |
| IsolationForest | No supervisado, con 2020–2022 limpio | Las mismas 66 columnas |
| LSTM V4 | Ya entrenado: se carga de disco y no se reentrena | La suya (24 × 66 por estación). Puntaje de red: el máximo entre estaciones de \|residuo\| / p95 |
| LSTM clasificador | Opcional, supervisado | Por definir |

- La normalización usa la media y la desviación de 2020–2022, como el V4.
- **La etiqueta nunca es entrada del modelo.** La etiqueta de red en la hora t vale 1 si al
  menos una estación tiene una lectura alterada en t. Además se guarda una etiqueta por
  estación, para ubicar la anomalía más adelante.
- **El V4 bajo episodios sostenidos:** hay que repetir la inferencia sobre la matriz alterada.
  En el ataque aislado de la parte 1 (§7.2 del protocolo V4) bastaba con reutilizar la
  predicción limpia; aquí cambian las entradas pasadas y el perfil de 14 días de la propia
  estación. La anomalía contamina el contexto de las vecinas y el perfil la absorbe en parte.
  Se acepta como operación realista y se declara.
- **IsolationForest:** el umbral se calibra en 2023, no con `contamination=0.05` como en la
  parte 1.
- **Variante opcional:** un Random Forest entrenado con una mezcla de deltas, análogo al
  adversario de magnitud variable de la parte 1.

## 9. Umbrales y métricas

Todo lo de esta sección queda fijado antes de programar y no se cambia después de ver los
resultados.

- **Falsas alarmas fijas por hora de red**, calibradas en 2023 limpio, en dos niveles: 5 %
  (principal) y 1 % (operativo; con 5 % habría una falsa alarma cada 20 horas).
- **Ojo:** el 5 % por hora de red no es el 5 % por lectura de la parte 1. Visto por estación,
  es mucho más estricto. Para comparar con la parte 1 se reporta también el V4 con su umbral
  original (p95 por estación) y la tasa de alertas de red que produce.
- **Detección:** un episodio se detecta si hay al menos una alerta de red mientras dura. Sólo
  cuenta la primera alerta.
- **Horas hasta la alerta:** horas de reloj desde el inicio del episodio hasta la primera
  alerta. Se reportan la mediana y la distribución.
- **Episodio no detectado:** termina sin ninguna alerta.
- **Falsas alarmas:** la medida principal se toma sobre 2024 limpio, como el FPR de la parte 1.
  Como medida secundaria se reportan las alertas fuera de episodio en la prueba alterada; ésta
  incluye las alertas residuales que el perfil del V4 puede producir después de un episodio.
- **F1 y precisión:** sólo como contraste, porque dependen de la proporción de anomalías.
- **Desglose:** todo se reporta por δ, por signo y por corrida. Los agregados llevan su margen
  entre corridas, y la baja representatividad va aparte.

## 10. Daño

- Horas alteradas antes de la primera alerta (todas, si nunca hay alerta).
- De esas horas, las que cambian de banda NOM-172 (58, 90, 135 y 175 ppb, con `banda_o3`):
  D = 1[f(x_real) ≠ f(x_recibido)], como en la parte 1.
- Excedencias de 155 ppb creadas (signo +) u ocultadas (signo −) antes de la alerta.
- Se separa por signo: el + puede provocar una contingencia falsa y el − puede ocultar una
  real.

## 11. Gráficas

- Detección según δ (análoga a la detección por bit de la parte 1).
- Horas hasta la alerta según δ.
- Daño no detectado según δ y signo.
- F1 según la tasa (experimento secundario).
- Detección según el número de estaciones que coinciden (fase 2).

## 12. Reproducibilidad

- `fijar_semilla(42)` inmediatamente antes de construir y entrenar cualquier red neuronal
  (CLAUDE.md).
- Se guardan las semillas y los planes de inyección de cada corrida.
- **Verificación:** repetir una corrida completa y exigir el mismo número (CLAUDE.md).
- Cada número reportado indica si viene de un modelo recién entrenado (Random Forest,
  IsolationForest) o cargado de disco (V4).
- No se modifican figuras ni resultados aceptados de la parte 1. Las salidas van a una carpeta
  nueva (propuesta: `results/anomalias_red_v1/`).

## 13. Límites declarados

- **Anomalías reales sin etiquetar.** La RAMA ya las trae: en el entrenamiento quedan como
  «normales», y en la prueba una alerta correcta sobre ellas cuenta como falsa alarma. Por eso
  la tasa de falsas alarmas es un máximo. Como control, se revisan a mano las 10 a 20 falsas
  alarmas de mayor puntaje.
- **Resolución horaria:** una anomalía de minutos se diluye en el promedio de la hora.
- **Una sola forma de anomalía** (§5). Un detector supervisado aprende las anomalías que se le
  muestran; no se afirma que detecte otras formas.
- **Red dispersa:** cada estación tiene pocas vecinas cercanas.
- **2020** incluye el confinamiento por COVID-19 (límite heredado del V4).

## 14. Pendientes antes o durante la ejecución

| # | Pendiente |
|---|---|
| P1 | Leer los antecedentes con ozono (L1 de `progreso.md`) y fijar el diferenciador |
| P2 | Definir la fase 2: k, signo y elección de estaciones |
| P3 | Decidir si las celdas de Random Forest e IsolationForest de la parte 1 se repiten con la división multianual |
| P4 | Decidir si los detectores de red se prueban también con alteraciones de bit flipping |
| P5 | Experimento XAL: una estación que reporta y luego deja de reportar |
| P6 | Vínculo con LoRaWAN y título de la tesis (duda 5 de `progreso.md`) |

## 15. Registro de revisiones

| Revisión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 0 | 2026-10-12 | Versión inicial | — |
