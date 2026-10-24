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
| LSTM supervisado | Complejo, supervisado | — | Red: ventana de 24 horas × 66 columnas (revisión 6) |

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
| LSTM supervisado | **Principal desde la revisión 6.** Supervisado, con 10 calendarios de entrenamiento sobre 2020–2022 y la división del V4. Un modelo por δ | Las 66 columnas de las horas t−23…t |

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
| 1 | 2026-10-13 | Aclaraciones de implementación del §5, §6 y §8 (abajo). No cambian el diseño | Surgieron al programar el generador, antes de entrenar o evaluar cualquier detector |
| 2 | 2026-10-13 | Nivel de azar para la detección por episodio y detección por hora como métrica principal (§9) | Con falsas alarmas por hora, un episodio largo casi siempre recibe alguna alerta por azar. Se registró antes de evaluar cualquier detector |
| 3 | 2026-10-16 | Aclaraciones de implementación del IsolationForest (§8) y desglose de la detección por hora según el tamaño del cambio (§9). No cambian el diseño | Surgieron al programarlo, antes de evaluarlo |
| 4 | 2026-10-16 | Nivel de azar en el desglose por tamaño del cambio | Se agregó **después** de ver el IsolationForest con δ = 100 %. Sólo puede bajar la detección aparente; no cambia umbrales ni métricas principales |
| 5 | 2026-10-16 | Aclaraciones de implementación del V4 (§8 y §9): cómo recibe la matriz alterada, puntaje y umbrales de red, control de reproducción y diagnóstico de ubicación. No cambian el diseño | Surgieron al programarlo, antes de evaluarlo |
| 6 | 2026-10-16 | El LSTM supervisado pasa de opcional a detector principal (§2 y §8), con 10 calendarios de entrenamiento. Se agregan un Random Forest con los mismos calendarios y una prueba secundaria con hora de inicio al azar | Corrige el protocolo para que siga lo acordado el 2026-10-12 (método supervisado, del Random Forest al LSTM). Aprobado por el tesista antes de entrenar |
| 7 | 2026-10-16 | Segundo intento supervisado: entradas relativas al perfil de 14 días y 20 calendarios de entrenamiento, para el LSTM supervisado y su Random Forest de control. La revisión 6 y sus resultados se conservan | Se registró **después** de ver la revisión 6 en 2024. El diseño se eligió sólo con la validación 2022, con una regla fijada antes de compararlo (`progreso.md`, 2026-10-16) |
| 8 | 2026-10-22 | Tercer intento supervisado: las entradas de la revisión 7 más una columna por estación que la compara con sus 4 vecinas más cercanas, para el LSTM supervisado y su Random Forest de control. Se agrega un control sin entrenamiento (la comparación con vecinas, sin modelo). Las revisiones 6 y 7 se conservan | Propuesta del tesista, con la premisa del asesor del 2026-10-19 y la exploración de ese día con 2020–2022. Se registró **después** de ver las revisiones 6 y 7 en 2024 y **antes** de programarla. La forma de la columna nueva se elige sólo con 2022, con una regla fijada aquí |
| 9 | 2026-10-23 | Métricas de presentación: el conjunto estándar completo (TP, FP, FN, TN, exactitud, precisión, recall, especificidad, tasa de falsas alarmas, F1, F2, MCC, ROC-AUC y PR-AUC), cada métrica con su valor «sin ataque» y una nota de lectura. Principal: F1 con 1 % de falsas alarmas; secundaria: F2, la de la parte 1. La señal por hora de la revisión 2 se conserva | Pedido del tesista, para comparar con la literatura y con la parte 1. Se registró **después** de ver la revisión 8 en 2024. No elige ni cambia ningún modelo, umbral o forma |
| 10 | 2026-10-23 | Referencia robusta: el perfil de 14 días con la **mediana** en lugar de la media, en las entradas relativas y en la columna de vecinas (forma a14) del LSTM supervisado con vecinas y de la regla de vecinas. Se elige contra la revisión 8 sólo con 2022. Las revisiones 6 a 9 se conservan | El estudio de las falsas alarmas (`progreso.md`, 2026-10-23) mostró que la media de 14 días se contamina con los días atacados y provoca falsas alarmas durante los 14 días siguientes. La mediana es el estimador estándar con datos contaminados. Se registró **después** de ver la revisión 8 en 2024 y **antes** de correrla con datos reales. Aprobada en lo general por el tesista |
| 11 | 2026-10-24 | Segunda unidad de evaluación: la **estación-día** (¿esta estación estuvo alterada este día?), con dos formas de juntar el día (peor hora contra promedio del día). Primero sólo con la regla de vecinas y 2022; después, si pasa, la regla y el V4 en 2024; un LSTM por estación queda como esbozo. La hora de red y las revisiones 6 a 10 se conservan y se reportan aparte | La opción A del 2026-10-23 (decidir por día completo) y PARAAD (Allka et al. 2024), que decide por bloques de un día y localiza la estación. Se registró **después** de ver las revisiones 8 y 10 y **antes** de programarla. Redactada por Claude a pedido del tesista y **aprobada por el tesista el 2026-10-24**, tal cual, antes de programarla |

### Revisión 1 (2026-10-13)

Implementación: `src/detect/anomalias_red.py`, `experiments/anomalias_red/generar_planes.py` y
`tests/test_anomalias_red.py`.

- **Redondeo (§5).** El valor alterado se redondea al ppb entero más cercano, con las mitades
  hacia arriba, porque la RAMA reporta enteros. Sin redondeo, sólo las horas alteradas tendrían
  decimales, y un detector supervisado podría aprender esa huella en lugar de la anomalía. Como
  consecuencia, con δ chico las lecturas bajas pueden no cambiar: con δ = 5 %, ninguna lectura
  menor que 10 ppb cambia, y en los datos el 24 % de las lecturas está por debajo de 10 ppb.
- **Etiqueta (§8).** La «lectura alterada» es la que cambió de valor (recibido ≠ original). Una
  hora del episodio que el redondeo deja igual no se etiqueta, para no enseñarle al modelo
  supervisado filas idénticas a las normales con etiqueta 1.
- **Episodio evaluable (§9).** Un episodio se evalúa si tiene al menos una hora con dato. El
  criterio no depende de δ, así que el denominador de la detección es el mismo con todos los δ.
  Los episodios sin dato se reportan aparte. ACO no tiene datos en 2024, así que sus episodios
  de prueba nunca son evaluables.
- **Semillas (§6).** Cada generador usa la clave de cinco enteros [42, año de inicio del
  periodo, número de corrida, uso, índice de la estación en la matriz]. El uso 0 sortea la p de
  la corrida y el uso 1 el plan de la estación. Los sorteos de cada día se hacen por adelantado,
  así que el plan de una estación no cambia si se quitan otras.
- **Promedio de p (§6).** La base de 0.15 % no es el promedio del rango: una p uniforme entre
  0.10 y 0.30 % promedia 0.20 %. Las 10 corridas de 2024 sacaron p entre 0.101 y 0.286 %
  (promedio 0.21 %), con 223 episodios en total, de los cuales 192 son evaluables. Son más que
  los «unos 17 por corrida» del §6. El plan de entrenamiento usa la base: 61 episodios, de los
  cuales 50 son evaluables. No se cambia el diseño: entrenar con una tasa y probar con otra
  parecida es realista, y más episodios reducen el margen.

### Revisión 2 (2026-10-13): nivel de azar y detección por hora

Esta revisión se registró antes de evaluar cualquier detector. El error es de la versión 0, y
lo cometió Claude al redactarla.

**Problema.** Con falsas alarmas fijas por hora de red, un episodio de varias horas casi
siempre tiene alguna alerta por puro azar. Si las alertas fueran independientes, un detector
que alerta al azar «detectaría» la proporción 1 − (1 − α)^horas de los episodios:

| α por hora de red | 1 día | 2 días | 4 días | 7 días |
|---|---:|---:|---:|---:|
| 5 % | 71 % | 91 % | 99 % | 100 % |
| 1 % | 21 % | 38 % | 62 % | 82 % |

Así, la regla «detectado si hay alguna alerta mientras dura» del §9 no distingue un buen
detector de uno que alerta al azar.

**Cambios en las métricas** (los umbrales del §9 no cambian):

- **Nivel de azar.** Cada detección por episodio se reporta junto a la de las mismas ventanas
  evaluadas con las alertas del mismo detector en 2024 limpio. Esta medida es empírica y
  conserva la correlación temporal real de las alertas. Lo que aporta el detector es la
  diferencia entre las dos. Las horas hasta la primera alerta llevan también su par al azar.
- **Detección por hora como métrica principal.** Es el porcentaje de horas de red con etiqueta
  1 que alertan, con las falsas alarmas fijas. No sufre el problema anterior y es la medida más
  cercana al recall por lectura de la parte 1.
- La detección por episodio y las horas hasta la alerta se conservan, siempre con su nivel de
  azar al lado.

### Revisión 3 (2026-10-16): IsolationForest

Se registró antes de evaluar el IsolationForest. Implementación:
`experiments/anomalias_red/entrenar_if.py`.

- **Un solo modelo para todos los δ.** Se entrena con la matriz limpia de 2020–2022, que no
  tiene anomalías. Por eso el modelo, sus puntajes en 2023 y 2024 limpios y sus umbrales son
  los mismos con todos los δ; sólo cambia el examen. El Random Forest, en cambio, necesita un
  modelo por δ porque aprende de las anomalías etiquetadas.
- **Hiperparámetros.** Los de omisión de scikit-learn (100 árboles, 256 horas por árbol, todas
  las columnas), con `random_state=42`. Son los de la parte 1, salvo `contamination`, que no se
  usa (§8).
- **Puntaje.** Es −`score_samples`: mayor puntaje, hora más anómala. No depende de
  `contamination`.
- **Desglose por tamaño del cambio.** La detección por hora se reporta también según el mayor
  cambio en ppb de esa hora entre estaciones: 1–16, 16–32, 32–64 y ≥ 64 ppb. Es el mismo
  desglose que se usó para diagnosticar el Random Forest. Es descriptivo y no cambia los
  umbrales ni las métricas principales.

### Revisión 4 (2026-10-16): nivel de azar por tamaño del cambio

A diferencia de las anteriores, ésta se agregó **después** de ver un resultado: el del
IsolationForest con δ = 100 %.

**Problema.** El desglose de la revisión 3 mezcla dos cosas: cuánto reacciona el detector a la
alteración y qué horas prefiere de por sí. Los cambios de 64 ppb o más sólo ocurren cuando el
ozono ya es alto, es decir, por la tarde. Un detector que alerta mucho por la tarde «detecta»
esas horas aunque no se hubieran alterado.

**Cambio.** Cada tramo se reporta junto a la proporción de esas mismas horas que alertan en 2024
limpio, con el mismo detector y el mismo umbral. Lo que aporta la alteración es la diferencia.
Es la misma idea del nivel de azar de la revisión 2, aplicada a las horas en lugar de a los
episodios. Esta medida sólo puede bajar la detección aparente, y no cambia los umbrales ni las
métricas principales del §9.

### Revisión 5 (2026-10-16): V4 sobre la matriz alterada

Se registró antes de evaluar el V4. Implementación: `experiments/anomalias_red/evaluar_v4.py`.

- **Cómo recibe la matriz alterada.** Se reconstruye la serie completa del V4 (2020-01-01 a
  2026-07-31, 33 estaciones, leída de los zip con su SHA-256). Sólo se sustituyen las horas de
  2024 de las 32 columnas de la matriz de red por las de la matriz de examen. El contexto de
  24 horas y el perfil de 14 días usan el pasado limpio hasta 2023 y, dentro de 2024, los
  valores alterados. XAL sigue como canal inactivo.
- **Sin reentrenar ni recalibrar.** Se cargan de disco los 31 modelos y sus umbrales p95 de
  2023, tal cual. Sólo se predice la etapa `prueba_2024`.
- **Puntaje de red.** En cada hora es el máximo de |residuo| / p95 entre las estaciones con
  predicción. Una hora sin ninguna predicción recibe 0 y no puede alertar.
- **Umbrales de red.** Los de 5 y 1 % se calibran con los residuos de 2023 guardados en disco
  (`calibracion_2023.csv.gz`). Además se reporta el nivel original del V4 (puntaje > 1, es
  decir, alguna estación pasa su p95) con la tasa de alertas de red que produce (§9).
- **Control de reproducción.** El 2024 limpio, pasado por esta misma vía, debe reproducir las
  predicciones guardadas (`predicciones_2024.csv.gz`) de las 31 estaciones.
- **Diagnóstico de ubicación.** Se guarda qué estación da el máximo en cada hora. Se reporta en
  qué proporción de las horas anómalas con alerta esa estación es una de las alteradas. Es
  descriptivo.

### Revisión 6 (2026-10-16): LSTM supervisado de red

Se registró antes de entrenarlo y la aprobó el tesista. Corrige un error de la versión 0, que
cometió Claude al redactarla: el acuerdo del 2026-10-12 hace del clasificador supervisado el
método principal (del Random Forest al LSTM), y el protocolo había dejado el LSTM como opcional.
Implementación: `src/detect/lstm_red.py` y `experiments/anomalias_red/entrenar_lstm_sup.py`.

- **Entrada:** las horas t−23…t de la matriz de red, con las 66 columnas de siempre (32
  valores normalizados, 32 máscaras, seno y coseno de la hora). A diferencia del V4, la ventana
  incluye la hora t y a la propia estación alterada. Para las primeras 23 horas de 2023 y de
  2024, el contexto sale de la matriz limpia del año anterior.
- **Salida:** la probabilidad de que la red tenga una anomalía a la hora t. Se aprende con la
  etiqueta de red de la hora t, que nunca es entrada.
- **Datos de entrenamiento:** 10 calendarios nuevos, `entrenamiento_01` a `entrenamiento_10`,
  sobre 2020-01-01 a 2022-12-31. Cada uno tiene su p uniforme en el rango del §6, con la clave
  [42, 2020, k, uso, índice] y k = 1…10. No chocan con el plan de entrenamiento original
  (k = 0) ni con los de prueba (año 2024). Se aplican los mismos δ, el mismo redondeo y la
  misma etiqueta.
- **División, como el V4:**
  - selección de épocas: se entrena con las horas t de 2020–2021 de los 10 calendarios y se
    valida con las de 2022 (EarlyStopping sobre la pérdida de validación, paciencia 8, máximo
    60 épocas); E es la primera época con la menor pérdida;
  - modelo definitivo: un modelo nuevo con todas las horas de 2020–2022 y exactamente E épocas;
  - umbrales de 5 y 1 % con 2023 limpio, y examen con los 10 calendarios de 2024.
- **Arquitectura:**
  - la del V4: LSTM de 64 unidades, Dropout 0.2, Dense 32 con ReLU y Dense 1, aquí con
    sigmoide y entropía cruzada binaria;
  - Adam con tasa 1e-3, lotes de 64 y barajado;
  - sin ajuste de hiperparámetros ni pesos por clase;
  - `fijar_semilla(42)` inmediatamente antes de construir cada modelo.
- **Un modelo por δ,** como el Random Forest.
- **Control de datos:** un Random Forest con los mismos 10 calendarios (por omisión,
  `random_state=42`), entrenado con las 66 columnas de la hora t. Separa el efecto del modelo
  del efecto de tener más episodios.
- **Métricas:** las del §9 y las revisiones 2 a 4, con los mismos umbrales.
- **Prueba secundaria: hora de inicio al azar.** Riesgo: todos los episodios empiezan a las
  00 h, y un detector supervisado podría aprender ese salto en lugar de la anomalía. Diseño:
  - se usan los mismos 10 calendarios de prueba, con las mismas estaciones, signos y días;
  - cada episodio se recorre una hora h sorteada entre 0 y 23 con la clave
    [42, 2024, k, 2, índice de la estación];
  - el episodio dura lo mismo en horas (24 × días) y se corta al final de 2024;
  - se evalúa con los modelos ya entrenados, sin reentrenar, en los tres detectores;
  - se corre después de los resultados principales y no cambia los umbrales.
- **Predicción de Claude, antes de entrenar** (δ = 100 %, nivel 5 %):
  1. el LSTM supervisado detectará más horas anómalas que el V4 (26.1 %);
  2. en las horas con cambio de 1–16 ppb alertará claramente más que esas mismas horas sin
     alterar y más que el V4 (1.0 %), porque la ventana de 24 horas le deja recordar la tarde
     anterior;
  3. con δ ≤ 20 % quedará cerca del azar, como se espera del V4 (hipótesis del §1).

### Revisión 7 (2026-10-16): segundo intento supervisado

Se registró antes de entrenar estos modelos, pero **después** de ver los resultados de la
revisión 6 en 2024. Por eso se reporta como segundo intento, junto al primero y sin sustituirlo.

**Origen.** El LSTM supervisado de la revisión 6 memorizó los años de entrenamiento: AUC de 0.99
en 2020–2021 y de 0.74 en 2022. El diseño nuevo se eligió entre ocho configuraciones, usando
sólo la validación 2022 y la regla fijada antes de compararlas (`progreso.md`, 2026-10-16).
Ganó por 2.1 puntos de detección, con un margen exigido de 2.

**Cambios respecto a la revisión 6** (todo lo demás sigue igual: arquitectura, ventana,
división, EarlyStopping sobre la pérdida de validación, umbrales y métricas):

- **Entradas relativas:**
  - en lugar del valor normalizado, cada estación entra como (valor − perfil causal de 14 días
    a esa hora) / σ de 2020–2022;
  - el perfil es la base del V4 (`perfil_causal`), con sus respaldos, y se calcula sobre la
    serie que recibe el detector, alterada si es el caso;
  - un hueco o una hora sin historia valen 0. Las máscaras y la hora no cambian;
  - para 2023 y 2024, el perfil usa la historia limpia desde 2020.
- **20 calendarios de entrenamiento** (`entrenamiento_01` a `_20`), con las mismas reglas y
  claves [42, 2020, k, …]. Los 10 primeros no cambian.
- **Random Forest de control:** la misma elección (entradas relativas de la hora t y 20
  calendarios).
- **Monitor en vivo** (`experiments/anomalias_red/en_vivo.py`): sólo registra las curvas para
  verlas en el navegador y no cambia el entrenamiento.

**Predicción de Claude, antes de entrenar** (δ = 100 %, 2024, nivel 5 %):
1. el LSTM supervisado detectará más horas anómalas que en la revisión 6 (16.4 %) y menos que el
   V4 (26.1 %);
2. en las horas con cambio ≥ 64 ppb seguirá por debajo del V4 (96.5 %);
3. el Random Forest de control detectará más horas que el de 10 calendarios con entradas crudas
   (12.7 %).

### Revisión 8 (2026-10-22): vecinas cercanas en las entradas del LSTM supervisado

Se registró **antes** de programarla, pero **después** de ver las revisiones 6 y 7 en 2024. Por
eso se reporta como tercer intento supervisado, junto a los dos primeros y sin sustituirlos.

**Origen.**
- **La propuesta es del tesista (2026-10-22):** la revisión 7 con la información de las vecinas.
- **La premisa es del asesor (2026-10-19):** «si tus vecinas marcan 100 y tú 150, hay algo raro».
- **La exploración del 2026-10-19,** que sólo usó 2020–2022 y no entrenó modelos
  (`experiments/exploracion_resumen_diario/`), encontró que comparar cada estación con sus
  vecinas baja el ruido de un día normal de ~25–36 % a ~7–14 %.
- **La revisión 7 compara cada estación sólo consigo misma,** con su perfil de 14 días. Aquí se
  le agrega la comparación con sus vecinas.

**Cambios respecto a la revisión 7.** Todo lo demás sigue igual: la arquitectura, la ventana
t−23…t, los 20 calendarios de entrenamiento, la división, el EarlyStopping sobre la pérdida de
validación, los umbrales y las métricas.
- **Vecinas:** las 4 estaciones más cercanas de cada columna de la matriz de red, por distancia
  haversine con las coordenadas del catálogo del SIMAT. Son las mismas del experimento de vecinas
  cercanas de la parte 1 (`src/detect/vecinas.py`, `vecinas_cercanas(..., k=4)`). XAL, como canal
  inactivo, no es vecina. HGM sí puede serlo, porque es una entrada. Las vecinas se fijan una vez
  y no dependen de los datos.
- **Columna nueva:** una por cada una de las 32 columnas de la matriz, que se suma a las 66 de la
  revisión 7, para un total de 98 por hora. Si la estación no tiene dato, o tiene menos de 2
  vecinas con dato, la columna vale 0.
- **Forma de la columna.** Hay dos decisiones, que se eligen con 2022 (abajo):
  - **cómo se compara:**
    - (a) diferencia de desviaciones: la entrada relativa de la estación menos el promedio de las
      entradas relativas de sus vecinas;
    - (b) cociente: log((x + 10) / (promedio de las vecinas + 10)), con x en ppb. Los 10 ppb
      evitan que el cociente se dispare de noche, cuando hay muy poco ozono. Es una constante
      fija; no se ajusta;
  - **contra qué se mide lo típico:**
    - (14 d) adaptativo: el perfil causal de 14 días de la revisión 7 en (a), y la mediana del
      cociente a esa hora en los 14 días anteriores en (b);
    - (fija) un valor por estación y hora del día que no cambia: el promedio de x en (a) y la
      mediana del cociente en (b). Se calcula con los años limpios de ajuste: 2020–2021 para la
      elección y 2020–2022 para los modelos definitivos. No absorbe un error que dure varios días,
      que es el punto ciego del perfil de 14 días.
  - **Escala:** cada columna nueva se divide entre su desviación en los mismos años limpios de
    ajuste.
- **Random Forest de control:** la misma elección, con las 98 columnas de la hora t y 20
  calendarios.
- **Control sin entrenamiento («regla de vecinas»):**
  - el puntaje de red de cada hora es el mayor |columna nueva| entre las estaciones, con la forma
    elegida;
  - no aprende de las anomalías: es un solo puntaje para todos los δ, y sus umbrales de 5 y 1 % se
    calibran con 2023 limpio, como los del IsolationForest;
  - si el LSTM no le gana, el modelo no aporta nada sobre la comparación directa.

**Elección de la forma con 2022.** Se fija aquí, antes de programarla:
- **Datos:** el entrenamiento usa las horas de 2020–2021 de los 20 calendarios. La validación
  usa las horas de 2022 de los calendarios 01–10, la misma para todas las variantes. 2023 y 2024
  no se tocan.
- **Variantes:** las cuatro combinaciones (a, 14 d), (a, fija), (b, 14 d) y (b, fija). Además se
  entrena, con los mismos datos, la revisión 7 sin vecinas, como referencia.
- **Criterio principal:** la detección de las horas con etiqueta 1 de 2022, con un umbral que
  deja 5 % de falsas alarmas en las horas con etiqueta 0 de esa misma validación, con
  **δ = 20 %**. Es la zona donde se busca mejorar. Como en la revisión 7, el LSTM se entrena 10
  épocas fijas y se toma la mejor.
- **Criterio secundario:** la misma detección con δ = 100 %. Sólo se reporta; no decide.
- **Contraste (agregado el 2026-10-22, antes de programarla):** para cada variante se reportan
  también la precisión, el F1 y el AUC en esa misma validación, con el mismo umbral. Son la
  tabla que el tesista pidió para la configuración 3 del diagnóstico de la curva de aprendizaje.
  No deciden.
- **Regla:**
  - gana la variante con mayor detección;
  - si su ventaja sobre la más sencilla, (a, 14 d), es menor que 2 puntos, se queda (a, 14 d);
  - el Random Forest de control y la regla de vecinas reciben la misma forma;
  - la comparación con la revisión 7 se reporta, pero no decide si se continúa: la revisión 8 se
    corre completa de todos modos, porque la pregunta es si las vecinas ayudan en el examen.
- **Después:** se anota la forma elegida en esta revisión antes de entrenar los modelos
  definitivos.

**Ejecución, como la revisión 7.**
1. **Selección:** se elige E por δ con EarlyStopping: entrenamiento 2020–2021, validación 2022,
   paciencia 8, máximo 60 épocas.
2. **Modelo definitivo:** 2020–2022 durante E épocas, uno por δ.
3. **Umbrales:** de 5 y 1 %, con 2023 limpio.
4. **Examen:** 2024, con los 10 calendarios y los cinco δ.
5. **Reproducibilidad:** cada detector se corre dos veces y debe dar salidas idénticas.

Las métricas son las del §9 y las revisiones 2 a 4, con el resumen por hora contra las mismas
horas sin alterar (`progreso.md`, 2026-10-18). Los años 2025–2026 quedan para después, para
todos los detectores de la parte 2 a la vez.

**Predicción de Claude, antes de programarla.** Para 2024 y el nivel de 5 %. La «señal» es el
recall por hora menos el de esas mismas horas sin alterar.
1. **Con δ = 100 %,** el LSTM de la revisión 8 detectará al menos tantas horas como el de la
   revisión 7 (25.5 %).
2. **Con δ = 20 %,** su señal quedará entre +1 y +5 puntos (la revisión 7 tuvo 0).
3. **Con δ = 5 % y 10 %,** su señal quedará por debajo de 1 punto.
4. **La memorización seguirá:** la mejor época será 1 o 2 en los cinco δ.
5. **La regla de vecinas,** sin entrenamiento, quedará por debajo del LSTM de la revisión 8 con
   δ = 100 % y cerca del azar con δ ≤ 20 %.
6. **El Random Forest de control** quedará por debajo del LSTM de la revisión 8 con δ = 100 %.

**Implementación (2026-10-22, antes de correrla).** No cambia el diseño.

Archivos:
- `src/detect/evaluacion_red.py`: `vecinas_de`, `ajustar_vecinas`, `columnas_vecinas`,
  `entradas_vecinas` y `entradas_de('vecinas', …)`;
- `tests/test_evaluacion_red.py`: pruebas de la columna nueva;
- `experiments/anomalias_red/diagnostico_vecinas_2022.py`: la elección con 2022;
- `entrenar_lstm_sup.py` y `entrenar_rf.py`, con `--entradas vecinas --forma <f>`;
- `evaluar_regla_vecinas.py`: la regla;
- `correr_revision8.sh`: la corrida completa.

Detalles que se fijan al programarla:
- **(b, 14 d):** la referencia es la mediana causal de los 14 días anteriores a esa hora, con al
  menos un valor. Sin historia, la columna vale 0.
- **Huecos:** sin dato propio, o con menos de 2 vecinas con dato, la columna vale 0. En las
  matrices de entrenamiento pasa en ~25 % de las celdas, por los huecos de los datos.
- **Años de ajuste:**
  - en la elección con 2022, la referencia fija y la escala se ajustan con 2020–2021 limpio;
  - en la corrida completa, con 2020–2022 limpio, tanto para elegir E como para el modelo
    definitivo. Es lo mismo que se hace con μ y σ.
- **Regla de vecinas:** el puntaje es el mayor |columna| entre las estaciones, con los huecos
  como 0. Su referencia y su escala salen de 2020–2022 limpio, y para 2024 el contexto es
  2020–2023 limpio.
- **Salidas:** `vecinas_2022/` (la elección), `lstm_sup_vecinas_<forma>_20cal/`,
  `rf_vecinas_<forma>_20cal/` y `regla_vecinas_<forma>/`.
- **Dónde corre:** en la PC del tesista (Ryzen 7 7700X, sólo con el procesador), con las
  versiones exactas de `requirements-lock.txt`. Se pasó ahí porque la lap se calentó con la
  curva de aprendizaje.
- **Prueba de equivalencia, antes de cualquier corrida en la PC:**
  - la configuración 3 de la curva de aprendizaje, con δ = 100 %, debe dar en sus 10 épocas
    exactamente lo mismo que en la lap;
  - si no, se detiene, y el tesista decide si sigue en la PC (y entonces se repite ahí la
    revisión 7 para comparar) o regresa a la lap;
  - el procedimiento está en `docs/runbook_pc_revision8.md`.
- **Cambio de máquina (2026-10-23, antes de correrla):**
  - el tesista no tiene acceso a la PC, así que la corre en Colab Pro, sólo con el procesador,
    con `notebooks/colab_revision8.ipynb`;
  - son las mismas versiones (Python 3.14.7, `requirements-lock.txt`) y la misma prueba de
    equivalencia;
  - el cuaderno sólo calcula: el análisis y el registro los hace Claude en la lap, con los
    resultados descargados.
- **Ejecución con el Colab CLI y resultado de la equivalencia (2026-10-23, antes de la elección).**
  - Se usó el Colab CLI oficial en lugar del cuaderno: sesión `rev8`, sólo procesador (8 AMD EPYC
    7B12, 50 GB), las mismas versiones, los 7 zips con su SHA-256 verificado, los planes y las
    matrices idénticos al repo y las 265 pruebas pasando.
  - **La prueba de equivalencia salió distinta.** En la época 1 la detección fue de 30.2 % en la
    lap y 30.4 % en Colab. Las épocas siguientes se separan hasta 4.8 puntos; el promedio de las 10
    fue 27.5 % y 24.7 %.
  - En las dos máquinas la menor pérdida está en la época 1. La causa probable es que los dos
    procesadores redondean distinto: la lap es Intel con AVX-512 y Colab es AMD sin ellas.
- **Decisión del tesista (opción A).** Se sigue en Colab y **toda comparación de la revisión 8 se
  hace dentro de Colab:**
  - la elección con 2022 ya entrena ahí la revisión 7 como referencia;
  - para el examen de 2024, la revisión 7 completa (LSTM y Random Forest) se repite en Colab, y la
    revisión 8 se compara con esa, no con la de la lap;
  - los resultados de la lap se conservan.
- **Advertencia para la lectura:** sólo el cambio de máquina mueve hasta ~5 puntos las épocas
  posteriores a la 1. Es más que el margen de 2 puntos de las reglas de elección cuando se usan
  esas épocas, así que esas decisiones son frágiles. La época 1, que es la que elige el protocolo,
  casi no cambió.

**Forma elegida con 2022 (2026-10-23): a14.**
- **Por qué:** con δ = 20 %, a14 tuvo la mayor detección en la mejor de sus 10 épocas (12.3 %, en
  la época 2), así que su ventaja sobre a14 es 0.
- **Las demás formas:** b14 10.6 %, bfija 9.9 % y afija 9.8 %.
- **La revisión 7 sin vecinas,** entrenada en Colab con los mismos datos: 7.0 %.
- **Con δ = 100 %** (sólo se reporta, no decide): b14 59.8 %, bfija 46.4 %, afija 37.0 %, a14
  34.6 % y sin vecinas 30.4 %.
- Las dos corridas salieron idénticas. El detalle está en `progreso.md` (2026-10-23) y en
  `results/anomalias_red_v1/vecinas_2022/`.

**V4 en las comparaciones (2026-10-23, decisión del tesista).**
- **El problema:** en Colab, el V4 no pasa su control de reproducción (revisión 5). Difiere de las
  predicciones guardadas en 7.6 × 10⁻⁶ ppb como máximo (2⁻¹⁷, una unidad de redondeo de float32),
  y la tolerancia es 10⁻⁹. Por eso no calcula métricas allá.
- **La decisión:** en las comparaciones de la revisión 8 se usa el V4 calculado en la lap. Es una
  excepción a la opción A: es un modelo cargado de disco, sólo hace inferencia, y la diferencia es
  de redondeo, no de entrenamiento.

### Revisión 9 (2026-10-23): métricas de presentación

Se registró después de ver la revisión 8 en 2024, a pedido del tesista, para presentar con las
métricas que usa la literatura y que usó la parte 1 (F2, §7.3 de su protocolo). No elige ni
cambia ningún modelo, umbral, forma ni calendario. Cálculo:
`experiments/anomalias_red/metricas_estandar_revision8.py`.

**Cómo se calculan:**
- **Unidad:** la hora de red, con la clase positiva = hora atacada (`anomalia_red`).
- **Calendarios:** se juntan los 10 del examen 2024.
- **Umbrales:** los de siempre, con 1 % y 5 % de falsas alarmas en 2023 limpio.
- **Valor «sin ataque»:** cada métrica se calcula también con los puntajes de 2024 limpio, en las
  mismas horas y con las mismas etiquetas. Es lo que daría el detector aunque no viera el ataque.
  Se reporta siempre al lado.
- **Referencias sin detector:** «alertar siempre» y «nunca alertar».

**Métrica principal: F1 con 1 %. Secundaria: F2 con 1 %.** También se reportan con 5 %.

**Nota de lectura de cada métrica** (se reporta junto con ella):

| Métrica | Qué mide | Nota |
|---|---|---|
| TP, FP, FN, TN | Conteos de horas | Siempre con sus denominadores, como en la parte 1 |
| Exactitud | Horas bien clasificadas | Casi no informa: «nunca alertar» saca 0.84–0.88 porque la mayoría de las horas es normal. Sólo por completitud |
| Precisión | De las alarmas, cuántas eran ataques | Depende de la proporción de horas atacadas (12–16 %). No se compara con otra proporción |
| Recall | De las horas atacadas, cuántas alertaron | Se lee con su valor sin ataque |
| Especificidad y tasa de falsas alarmas | Horas normales sin alarma y con alarma | El umbral apunta a 1 % o 5 % en 2023; en 2024 sale más (§ análisis de la revisión 8) |
| F1 | Media armónica de precisión y recall, con el mismo peso | Premia alertar mucho: «alertar siempre» saca 0.22–0.28 |
| F2 | Como el F1, pero el recall pesa más (β = 2) | Premia alertar todavía más: «alertar siempre» saca 0.42–0.49. Es la de la parte 1 |
| MCC | Correlación entre alarma y ataque | 0 = azar, también para «alertar siempre». Es la menos engañosa con clases desbalanceadas |
| ROC-AUC | Separación de puntajes, sin umbral | Sin ataque no da 0.5, sino 0.51–0.62, por el redondeo con δ chico (`progreso.md`, 2026-10-18) |
| PR-AUC | Precisión promedio a lo largo de todos los umbrales | Su azar es la proporción de horas atacadas (0.12–0.16); sin ataque sale 0.12–0.18 |

**Comparación con la literatura:** se iguala el método (definiciones, conteos y cómo se fijó el
umbral), no los valores. El F1 depende del problema, de la proporción de ataques y de cómo se
elige el umbral.

### Revisión 10 (2026-10-23): referencia de 14 días con mediana

**Por qué.**
- **El problema:** en la revisión 8, las entradas relativas y la columna de vecinas a14 comparan
  cada lectura con la **media** de esa hora en los 14 días anteriores. Cuando una estación estuvo
  atacada varios de esos días, la media queda inflada o desinflada, y la lectura ya normal se ve
  anómala.
- **Lo que mostró el estudio de las falsas alarmas:**
  - el exceso dura casi exactamente 14 días;
  - lo dispara la estación atacada;
  - con δ = 100 % y 5 % llega a +16 puntos el primer día.
- **La solución:** la mediana casi no se mueve si menos de la mitad de los 14 días está alterada.
- **El techo:** sin esas horas, el F1 con 5 % de la revisión 8 pasaría de 0.48 a 0.60 con δ = 100 %.
  Es un límite superior, no una predicción.

**Qué cambia (y sólo eso):**
- **El perfil de 14 días** (`evaluacion_red.perfil_mediana`, `relativas(..., referencia='mediana')`):
  - en cada hora, la mediana de los 14 valores anteriores de esa misma hora;
  - si no hay ninguno, la mediana histórica de esa hora y luego la global;
  - siempre con observaciones estrictamente anteriores.
- **Dónde se usa:** en las 32 entradas relativas y en la columna de vecinas a14 del LSTM supervisado
  con vecinas y de la regla de vecinas.
- **Lo que no cambia:**
  - las 98 columnas, la arquitectura, la semilla, los 20 calendarios y la división de años;
  - los umbrales de 1 y 5 % con 2023 limpio, las métricas de la revisión 9 y las vecinas;
  - el valor por defecto (`'media'`), así que los detectores anteriores dan lo mismo.
- **El Random Forest de control no se repite:** ya quedó por debajo del LSTM en las revisiones 7 y 8.

**Elección con 2022, fijada antes de correrla**
(`experiments/anomalias_red/diagnostico_referencia_2022.py`):
- **Variantes:**
  - a14 con media: es la revisión 8, y se reentrena en la misma corrida y la misma máquina;
  - a14 con mediana.
- **Datos:** como la elección de la revisión 8. Se entrena con 2020–2021 de los 20 calendarios y
  se valida con 2022 de los calendarios 01–10. La escala de la columna se ajusta con 2020–2021
  limpio. Son 10 épocas fijas.
- **Severidades:** δ = 100 y 50 % deciden, porque ahí está la contaminación. δ = 20 % sólo se
  reporta.
- **Medida:**
  - el F1 con un umbral que deja 1 % de falsas alarmas en las horas con etiqueta 0 de la
    validación;
  - en la época de **menor pérdida de validación**, la que elegiría el EarlyStopping del modelo
    definitivo.
- **Contraste:**
  - el F1 con 5 %, el recall, la precisión, el PR-AUC, la mejor época y el promedio de las 10;
  - las falsas alarmas con 1 % en las horas normales de los 14 días posteriores a un ataque y en
    las demás.
- **Regla:**
  - se adopta la mediana si su F1 con 1 %, promediado entre δ = 100 y 50 %, supera al de la media
    en **0.02 o más**;
  - si no, se queda la media, la revisión 10 se cierra con ese resultado y **no se examina con
    2024**.
- **Reproducibilidad:** se corre dos veces y debe salir idéntica.

**Ejecución si se adopta** (`experiments/anomalias_red/correr_revision10.sh`, en Colab):
- **Qué corre:** el LSTM con vecinas y mediana, y la regla de vecinas con mediana, cada uno dos
  veces y comparados, en los cinco δ.
- **Cómo:** igual que la revisión 8: E por EarlyStopping con 2020–2021 contra 2022, modelo
  definitivo con 2020–2022, umbrales con 2023 limpio y examen 2024.
- **Comparación:** con la revisión 8 de Colab, con las métricas de la revisión 9 y su valor sin
  ataque, y con el estudio de las falsas alarmas repetido.

**Predicción de Claude, antes de correrla:**
1. Con 2022 y δ = 100 %, la mediana baja al menos a la mitad las falsas alarmas con 1 % en las
   horas normales de los 14 días posteriores a un ataque.
2. La regla de elección adopta la mediana.
3. En 2024 con δ = 100 %, el F1 del LSTM con vecinas sube a 0.46 o más con 1 % (revisión 8: 0.43)
   y a 0.53 o más con 5 % (revisión 8: 0.48).
4. En 2024 con δ ≤ 20 %, el F1 con 1 % cambia menos de 0.02 frente a la revisión 8.
5. E = 1 en los cinco δ.
6. La regla de vecinas con mediana sube su F1 con 1 % con δ = 100 % en 0.02 o más (revisión 8: 0.32).

**Implementación (2026-10-23):**
- **Código:** `src/detect/evaluacion_red.py` (con `REFERENCIAS`, `perfil_mediana` y
  `referencia=`); `entrenar_lstm_sup.py` y `evaluar_regla_vecinas.py` (con `--referencia mediana`);
  `diagnostico_referencia_2022.py`; `correr_revision10.sh`.
- **Pruebas:** 3 nuevas, con 22 en total en `tests/test_evaluacion_red.py`:
  - con 5 de 14 días al doble, la media hace parecer baja a la estación y la mediana no;
  - la mediana es causal;
  - el respaldo funciona tras 16 días sin dato;
  - el valor por defecto no cambia.
- **Modo `--prueba` de la elección:** corre completo.
- **Salidas:** `results/anomalias_red_v1/referencia_2022/` (la elección),
  `lstm_sup_vecinas_a14_mediana_20cal/` y `regla_vecinas_a14_mediana/`.

**Referencia elegida con 2022 (2026-10-23): la media. La revisión 10 se cierra y no se examina con
2024.**
- **La regla:**
  - se usa el F1 con 1 % en la época de menor pérdida de validación, que fue la 1 en las seis
    corridas;
  - promediado entre δ = 100 y 50 %, da 0.181 con la media y 0.167 con la mediana;
  - la ventaja de la mediana es −0.014, y hacía falta +0.02.
- **Por δ** (media y mediana):
  - 0.263 y 0.208 con 100 %;
  - 0.099 y 0.126 con 50 %;
  - 0.042 y 0.041 con 20 %, que sólo se reporta.
- **Contraste, que no decide:** ninguna otra forma de resumir llega a +0.02.
  - El promedio de las 10 épocas da −0.007.
  - La mejor época da −0.001.
  - El F1 con 5 % da −0.006.
  - El PR-AUC da +0.001.
- **Falsas alarmas con 1 % y δ = 100 %:**
  - en las horas normales de los 14 días posteriores a un ataque, bajaron de 1.42 % a 1.18 %;
  - en las demás horas normales, subieron de 0.45 % a 0.76 %;
  - el total queda en 1 % por construcción del umbral.
- **Predicciones:**
  - la 1 falló: las falsas alarmas tras un ataque bajaron 17 %, no a la mitad;
  - la 2 también falló;
  - la 3, la 4, la 5 y la 6 eran de 2024 y no se evalúan.
- **Reproducibilidad:**
  - las dos corridas en paralelo salieron idénticas;
  - los modelos se entrenaron en la corrida, en Colab (sesión `rev10`), y no se guardaron.
- **Máquina:**
  - fue un Intel Xeon @ 2.20 GHz (Broadwell, 8 núcleos virtuales), no el AMD EPYC 7B12 de la
    revisión 8;
  - la variante con media no repite época por época la elección de la revisión 8: la pérdida de
    validación difiere hasta 0.14 y el F1 con 5 % hasta 0.033;
  - en la lap se comprobó que sus entradas son idénticas bit a bit a las del código del commit
    6d417a9, así que la diferencia viene de la máquina;
  - la regla no se afecta, porque compara las dos variantes en la misma corrida.
- **Consecuencia para lo que sigue:**
  - hacer las comparaciones «dentro de Colab» (opción A) no basta;
  - para comparar contra números de la revisión 8 hace falta el mismo procesador, o repetir la
    revisión 8 en la misma sesión.
- **Detalle:** en `progreso.md` (2026-10-23) y en `results/anomalias_red_v1/referencia_2022/`.

### Revisión 11 (2026-10-24): decisión por estación-día

**Estado:**
- la redactó Claude a pedido del tesista;
- el tesista la aprobó tal cual el 2026-10-24, antes de programarla;
- las fases 1 y 2 se calculan en la lap; Colab sólo haría falta para la fase 3.

**Por qué.**
- **La pregunta cambia:**
  - hoy cada caso es una hora de red, y el detector sólo dice si en esa hora hay alguna estación
    alterada, no cuál;
  - aquí cada caso es **una estación en un día**, por ejemplo «CUT, 25 de abril de 2022», y la
    pregunta es si esa estación estuvo alterada ese día.
- **De dónde sale:**
  - **la opción A del 2026-10-23,** decidir por día completo: los episodios duran días enteros,
    así que el día junta 24 horas de evidencia;
  - **PARAAD** (Allka et al. 2024), el trabajo más parecido al nuestro:
    - decide por bloques de un día y reporta por estación-día, localizando la estación;
    - en su ablación, con bloques de 1 hora la precisión baja de 0.84 a 0.70 (PARAAD-SA);
  - **la decisión del tesista del 2026-10-23** de seguir con estación-día, aparte de la mediana.
- **Para qué:**
  - saber si juntar el día ayuda;
  - decir qué estación es;
  - poder comparar con PARAAD.

**Qué cambia.**
- **Unidad:** la estación-día, en los 31 objetivos. HGM no entra, porque nunca se altera.
- **Etiqueta:**
  - vale 1 si el día está dentro de un episodio de esa estación en el plan;
  - como los episodios son días completos que empiezan a las 00 h, cada estación-día queda
    entera dentro o entera fuera.
- **Horas válidas:** las horas del día en que existe el valor de esa estación en el detector.
  - Una estación-día se usa sólo si tiene **al menos 12 horas válidas**.
  - Las demás se excluyen de la calibración, del examen y del «sin ataque». Se reporta cuántas
    son, y cuántas de ellas estaban atacadas.
  - El ataque no cambia qué horas tienen dato, así que las estación-días son las mismas con
    ataque y sin él.
- **Valor por hora y estación:** el que cada detector ya calcula antes de tomar el máximo de la
  red.
  - **En la regla de vecinas:** la columna a14 de la estación, ya escalada. Usa la media, porque
    la revisión 10 se cerró sin adoptar la mediana.
  - **En el V4:** el residuo de la estación, con signo, dividido entre su p95 de 2023, el mismo
    del puntaje de red.
- **Dos formas de juntar el día, fijadas aquí:**
  - **peor hora (control):** el mayor |valor| entre las horas válidas. Es lo que haría un detector
    por hora que señalara la estación;
  - **promedio del día (propuesta):** |promedio con signo de las horas válidas|.
    - Aprovecha que el signo del ataque es el mismo durante todo el episodio.
    - El ruido de una hora a otra se cancela en parte; el corrimiento, no.
- **Umbrales:**
  - uno solo para las 31 estaciones, que deja 1 % y 5 % de falsas alarmas en las estación-días de
    un año limpio;
  - un umbral por estación sería inestable, porque con 365 días por estación el 1 % son 3 o 4
    días;
  - los valores ya vienen escalados por estación.
- **Métricas:**
  - las de la revisión 9, con la estación-día como caso: F1 con 1 % como principal, F2 como
    secundaria y las demás;
  - cada una con su valor «sin ataque»: las mismas estación-días del año sin alterar, con el
    mismo umbral y las mismas etiquetas.
- **Falsas alarmas, desglosadas.** Con 1 % y en los datos atacados, en tres grupos que no se
  enciman, en este orden:
  - **contagio:** alguna de las 4 vecinas de la estación está atacada ese día.
    - Con la forma (a), la columna resta el promedio de las vecinas.
    - Así, un ataque de +100 % en una vecina mueve la columna de la estación limpia como un ataque
      de unos 25 % en sentido contrario.
  - **tras un ataque propio:** dentro de los 14 días posteriores al fin de un episodio de la misma
    estación;
  - **resto.**

**Qué no cambia.**
- El modelo de anomalía, los planes, las matrices, los 31 objetivos y la división de años.
- La regla de vecinas a14 con media, y el V4 cargado de disco, sin reentrenar.
- Las revisiones 6 a 10 y sus métricas por hora de red. Se conservan y se reportan aparte.
- **La estación-día no reemplaza a la hora de red, y sus números no se comparan uno a uno:**
  son casos distintos, con proporciones de ataque distintas.

**Nota de lectura: el techo del F1.**
- **Las estación-días atacadas son pocas:** cerca de 0.8 %.
  - Son 94 por calendario en la validación 2022 y 87 en el examen 2024.
  - Ese conteo incluye días sin dato, así que es aproximado.
- **El techo:**
  - con 1 % de falsas alarmas, aun detectando todo, la precisión no pasaría de ~0.45 y el F1 de
    ~0.62;
  - con 5 %, no pasarían de ~0.14 y ~0.25.
- **Cómo se lee:** el F1 por estación-día se lee contra ese techo.
- **PARAAD no se compara directo:**
  - altera cerca de 9 % de las estación-días (30 % de los sensores × 30 % de los días);
  - elige su umbral de otra forma;
  - así que su precisión de 0.84 no es comparable uno a uno.

**Fase 1: elección con 2022, sólo con la regla de vecinas, en la lap.** Se fija aquí, antes de
programarla.
- **Por qué sólo la regla:**
  - no se entrena;
  - es aritmética determinista, así que no depende del procesador;
  - 2022 no entra en nada que haya aprendido de los ataques;
  - el V4, en cambio, se ajustó con 2020–2022, así que 2022 no le sirve de validación.
- **Datos:**
  - la escala de la columna se ajusta con 2020–2021 limpio, como en las elecciones de las
    revisiones 8 y 10;
  - los umbrales salen de las estación-días de **2021 limpio**;
  - el examen usa las estación-días de 2022 de los calendarios 01–10;
  - el «sin ataque» usa 2022 limpio.
- **Por qué el umbral de 2021:**
  - imita al examen: el umbral sale de un año limpio anterior y la prueba es el siguiente;
  - corrige el límite que se vio en la elección de la revisión 10, donde el umbral salía de la
    misma validación atacada;
  - 2021 también entra en el ajuste de la escala. Se acepta, porque la escala es sólo una
    desviación y no ve etiquetas.
- **Severidades:** δ = 100, 50 y 20 % deciden; 10 y 5 % sólo se reportan.
- **Regla:**
  - se pasa a la fase 2 si el F1 con 1 % del promedio del día, promediado entre δ = 100, 50 y
    20 %, supera al de la peor hora en **0.02 o más**;
  - si no, la revisión 11 se cierra con ese resultado y **no se examina con 2024**.
- **Contraste, que no decide:**
  - el F1 con 5 %, el recall, la precisión, el PR-AUC y el MCC;
  - las falsas alarmas desglosadas;
  - las estación-días excluidas.
- **Reproducibilidad:** se calcula dos veces y debe salir idéntica.

**Fase 2: examen 2024, sólo si pasa la fase 1, en la lap.**
- **Detectores:** la regla de vecinas y el V4, por estación-día.
- **Formas de juntar el día:** las dos. Decide la que eligió la fase 1; la otra se reporta.
- **Ajuste, como en la revisión 8:**
  - la escala de la regla se ajusta con 2020–2022 limpio;
  - el V4 se usa tal cual.
- **Umbrales:** con las estación-días de 2023 limpio.
- **Examen:** los 10 calendarios de 2024 juntos.
- **«Sin ataque»:** 2024 limpio.
- **El V4** repite la inferencia en la lap, con su control de reproducción de la revisión 5.

**Fase 3: LSTM supervisado por estación (sólo un esbozo).**
- **Cuándo:** sólo si la fase 2 muestra algo útil.
- **Qué sería:**
  - un LSTM con una salida por estación, con etiqueta por estación-hora y la forma de juntar el
    día que se elija;
  - entrenado en Colab con los 20 calendarios.
- **Su diseño** se registra aparte, fechado, antes de programarlo.
- **Sus comparaciones** con la regla y el V4 no dependen de la máquina: esos dos se calculan en la
  lap y no se entrenan.

**Lo que no entra, ideas para después:**
- localizar quedándose con la estación de mayor puntaje del vecindario, para quitar el contagio;
- la interpolación espacial del *spatial consistency test*;
- el CUSUM.

**Predicción de Claude, antes de correrla:**
1. En 2022, el promedio del día supera a la peor hora en el F1 con 1 % en los tres δ que deciden.
2. La regla pasa a la fase 2.
3. Con δ = 20 % y el promedio del día, el F1 con 1 % queda por debajo de 0.30. Hay días naturales
   raros, como los de CUT del 25 y 26 de abril, cerca de 17–20 % por debajo de sus vecinas sin
   ataque.
4. Con δ = 100 % y el promedio del día, al menos un cuarto de las falsas alarmas en los datos
   atacados son de contagio.
5. Con δ = 10 y 5 %, el F1 con 1 % queda por debajo de 0.10 con las dos formas de juntar el día.
6. En 2024, si se llega, con δ ≥ 50 % la regla de vecinas supera al V4 en el F1 con 1 % por
   estación-día, como pasó por hora de red.

**Implementación prevista:**
- **Módulo** `src/detect/estacion_dia.py`, con:
  - las etiquetas por estación-día a partir del plan;
  - las horas válidas;
  - las dos formas de juntar el día;
  - el desglose de las falsas alarmas.
- **Scripts:** `experiments/anomalias_red/diagnostico_estacion_dia_2022.py` para la fase 1 y
  `evaluar_estacion_dia.py` para la fase 2.
- **Pruebas:**
  - un episodio que cruza de un año a otro;
  - la exclusión con menos de 12 horas;
  - el promedio con signo contra la peor hora, en un ejemplo pequeño;
  - el orden del desglose de las falsas alarmas.
- **Salidas:** `results/anomalias_red_v1/estacion_dia_2022/` y
  `results/anomalias_red_v1/estacion_dia/`.

**Resultado de la fase 1 (2026-10-24): pasa a la fase 2.**
- **Cómo se corrió:** en la lap, dos corridas en paralelo, con salidas idénticas. No entrena ni
  carga modelos.
- **La regla:**
  - F1 con 1 %, promediado entre δ = 100, 50 y 20 %: 0.233 con la peor hora y 0.288 con el
    promedio del día;
  - la ventaja es +0.055, y se pedía +0.02.
- **Por δ** (peor hora y promedio del día):
  - 0.382 y 0.377 con 100 %;
  - 0.260 y 0.389 con 50 %;
  - 0.057 y 0.098 con 20 %;
  - 0.020 y 0.021 con 10 %;
  - 0.014 y 0.008 con 5 %.
- **Sin ataque,** con el mismo umbral, el F1 con 1 % es 0.005 y 0.003.
- **Contraste, que no decide:**
  - el PR-AUC es 0.46 y 0.58 con 100 %, 0.19 y 0.33 con 50 %, y 0.020 y 0.043 con 20 %;
  - el recall con 1 % y δ = 100 % es 0.61 y 0.82.
- **Falsas alarmas con 1 % y δ = 100 %, promedio del día:**
  - contagio: 30 % de las falsas alarmas, con una tasa de 19 % en esas estación-días;
  - tras un ataque propio: 26 %, con una tasa de 20 %;
  - resto: 45 %, con una tasa de 1.0 %.
- **Estación-días excluidas:**
  - 16 % de las estación-días (18 400 de 113 150) y 18 % de las atacadas (167 de 937);
  - en 2022, el 90 % de las exclusiones es porque la propia estación tiene menos de 12 horas con
    dato.
- **Predicciones:**
  - la 1 falló: con δ = 100 % la peor hora queda apenas arriba, 0.382 contra 0.377;
  - la 2, la 3, la 4 y la 5 se cumplieron;
  - la 6 es de 2024.
- **Aviso:** el modo `--prueba` usa datos reales de 2 calendarios, y su salida, ya con «pasa», se
  vio antes de la corrida completa. No se cambió nada, porque la regla y las predicciones estaban
  fijadas.
- **Detalle:** en `progreso.md` (2026-10-24) y en `results/anomalias_red_v1/estacion_dia_2022/`.
