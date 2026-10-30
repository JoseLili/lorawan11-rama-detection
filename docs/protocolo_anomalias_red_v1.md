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
| 12 | 2026-10-24 | Regla de vecinas robusta, por estación-día: la mediana de 14 días (contra la referencia contaminada tras un ataque) y la **dominancia en el vecindario** (contra el contagio a las vecinas), por separado y juntas, con el promedio del día. Se eligen sólo con 2022, con una regla fijada aquí. La revisión 11 se conserva | La fase 2 de la revisión 11 (`progreso.md`, 2026-10-24): con δ = 100 %, el contagio y la referencia contaminada dan casi la mitad de las falsas alarmas de la regla. Pedida por el tesista (opción b). Se registró **después** de ver la fase 2 de la revisión 11 y **antes** de programarla. **Aprobada por el tesista el 2026-10-24**, antes de correrla |
| 13 | 2026-10-24 | LSTM supervisado **por estación** (fase 3 de la revisión 11): la misma arquitectura con una salida por estación, etiqueta por estación-hora, y el día juntado como en la regla robusta (promedio del día y dominancia). Se elige sólo con 2022 y sólo pasa a 2024 si le gana a la regla robusta (R3) por 0.02 o más. Las revisiones 6 a 12 se conservan | Pedida por el tesista: llevar al LSTM las mejoras de las revisiones 11 y 12, que sólo se pueden aplicar si el modelo responde por estación. Se registró **después** de ver la revisión 12 en 2024 y **antes** de programarla. **Aprobada por el tesista el 2026-10-24**, con el paso 2 tal cual |
| 14 | 2026-10-24 | LSTM **local compartido** por estación: un solo modelo que mira una estación y sus 4 vecinas (17 columnas) y se aplica a las 31, con 20 o con 60 calendarios de entrenamiento (con el mismo número de ventanas). El día se junta como en R3. Se elige sólo con 2022 y sólo pasa a 2024 si le gana a R3 por 0.02 o más. Es el **último** intento supervisado por estación-día con 2022. Las revisiones 6 a 13 se conservan | La revisión 13 perdió contra R3 en 2022 (F̄ 0.203 contra 0.330). La exploración del 2026-10-24 con sus puntajes de 2022 mostró la causa: un ataque en cualquier parte de la red le sube las falsas alarmas a las estaciones lejanas. Pedida por el tesista (opción C). Se registró **después** de ver la revisión 13 en 2022 y **antes** de programarla. **Aprobada por el tesista el 2026-10-24**, tal cual |
| 15 | 2026-10-25 | Un segundo punto de operación para la estación-día: además del umbral p99 (1 % de falsas alarmas en 2023 limpio), el **p99.9** (0.1 %), y la curva de recall y precisión según el umbral, para L0, R3 y el V4 en 2024. No elige detector ni umbral, y no cambia nada de las revisiones 11 a 14 | Pedida por el tesista, para entender la balanza entre recall y precisión. Se registró **después** de ver el examen 2024 con p99 y una ilustración con p99.9 en 2022 (`exploracion_precision_umbral_2022.py`), y **antes** de calcular p99.9 en 2024. Por eso su número de 2024 es descriptivo; la prueba independiente es el examen final de 2025–2026. Aprobada por el tesista el 2026-10-25 |
| 16 | 2026-10-25 | Tres comprobaciones antes del examen final, con p99 y p99.9: (1) intervalos de confianza de L0 − R3 en 2024 por bootstrap; (2) un solo modelo L0 para todos los δ, elegido con 2022 y examinado en 2024 con los cinco δ; (3) la prueba con hora de inicio al azar de la revisión 6, que nunca se corrió. No entrena nada. Sólo (2) elige algo: el modelo único que irá al examen final, con una regla sobre 2022 | Pedida por el tesista. Se registró **después** de ver el examen 2024 de la revisión 14 y la revisión 15, y **antes** de correr estas tres comprobaciones. Aprobada por el tesista el 2026-10-25 |
| 17 | 2026-10-25 | **Examen final** de la estación-día con 2025 (enero a diciembre) y 2026 (enero a julio), una sola vez: detectores congelados (L0 por δ, el L0 único de la revisión 16, R3 y V4), umbrales p99 y p99.9 de 2023 limpio, 10 calendarios nuevos por año, con su versión de hora de inicio al azar, e intervalos de confianza. No se elige ni se ajusta nada | El paso 4 del plan del 2026-10-25. Se registró **antes** de generar cualquier calendario o matriz de 2025–2026 para la parte 2. **Aprobada por el tesista el 2026-10-25**, antes de la revisión con el asesor, por decisión suya |
| 18 | 2026-10-26 | Comparación justa con el V4 tras la junta con el asesor: (a) el V4 calificado en las mismas estación-días que L0 y R3; (b) un **V4 supervisado** (V4S): las entradas y la arquitectura del V4 más la propia estación, entrenado con los calendarios y las etiquetas de L0; (c) una gráfica del V4S contra el L0 único en el mismo escenario de δ, que sustituye a la comparación con el bit flipping. Se evalúa en 2024 y una sola vez en 2025–2026. Las tablas del examen final no se tocan | El asesor (2026-10-26) señaló que comparar L0 (supervisado) contra el V4 (no supervisado) es injusto, y que la gráfica contra el bit flipping compara alteraciones distintas. Se registró **después** de ver el examen final y **antes** de programar o entrenar nada. Borrador de Claude a pedido del tesista, **aprobado por el tesista el 2026-10-27** con la regla «peras con peras» |
| 18b | 2026-10-27 | Un segundo V4S, **compartido**: un solo modelo para las 31 estaciones, como L0, con las mismas entradas del V4 pero las otras 32 estaciones ordenadas por distancia. Los dos V4S van al examen, sin elegir entre ellos. La comparación principal, fijada por principio y no por resultados, es L0 único contra el V4S compartido; el V4S por estación queda como contraste | La comprobación con 2022 del V4S por estación (`progreso.md`, 2026-10-27): 11 de 31 modelos no aprendieron (ROC-AUC de 0.505), la desventaja declarada en la revisión 18 antes de entrenar. El cambio fortalece al rival de L0. Se registró **después** de ver el V4S por estación en 2022 y **antes** de programar el compartido o de evaluar cualquier V4S en 2023–2026. **Aprobada por el tesista el 2026-10-27** («Va. Hazlo») |
| 19 | 2026-10-27 | Dos escenarios de «una sola estación», con detectores congelados: (B) **una a la vez**, con los mismos calendarios de prueba quitando los episodios que se enciman (comparación pareada); (A) **un solo nodo comprometido**, con calendarios nuevos donde sólo una estación se altera en todo el año, con más episodios. 2024, 2025 y 2026; principal L0 único contra V4S compartido | Pedido del asesor (2026-10-26): primero una sola estación atacada y después escenarios más complejos. La transcripción admite las dos lecturas, así que se hacen las dos. Se registró **antes** de programar o generar nada. **Aprobada por el tesista el 2026-10-27** |

| T1 | 2026-10-29 | Exploración TINTO-PCA con asignación única propia 32 × 32, 408 entradas idénticas a L0; una CNN de 34 081 parámetros, selección 2020–2021/2022 y dos entrenamientos reproducibles. Sin años de examen | Solicitada por el asesor y desarrollada con el tesista; configuración y código registrados antes del entrenamiento completo. Autorizada por el tesista en este chat el 2026-10-29. Los números 20/21 reservados a otras líneas no se ocupan |
| 20 | 2026-10-27 | **PARAAD-SA en la RAMA:** el método publicado (Allka et al. 2024), adaptado a las 32 estaciones, entrenado sin etiquetas con 2020–2022, umbrales p99 y p99.9 de 2023 limpio, examinado en 2024–2026 en los escenarios original, B y A con detectores congelados. Comparación principal sin etiquetas: PARAAD contra V4; L0 como referencia supervisada | Pedido del asesor (A7, 2026-10-26). Diseño en `docs/revision20_paraad_diseno.md` y registro previo del examen en `docs/registro_examen_paraad_revision20.md` (2026-10-28). Trabajado en otro chat (Codex) e integrado aquí el 2026-10-29. Los documentos de registro no tuvieron commit antes del examen: su fecha la respalda el propio texto, no git |
| 20b | 2026-10-29 | **L0, V4 y PARAAD en Barcelona:** modelos nuevos con 13 estaciones del AMB (O₃ de la Generalitat, `tasf-thgu`), ajuste 2014–2016, calibración 2017, examen 2018 (principal) y 2019, con las anomalías proporcionales de este protocolo. El escenario de sesgo sumado del artículo quedó registrado pero no evaluado | Complemento de la revisión 20: los métodos propios con los datos de la otra ciudad. Metodología en `docs/metodologia_barcelona_paraad_v1.md` y registro previo en `docs/registro_examen_barcelona_2018_2019.md`. No es una reproducción del artículo: otras estaciones, otro umbral y otra anomalía |
| 20c | 2026-10-29 | **El sesgo de PARAAD en Barcelona:** los modelos congelados de la 20b (L0, V4 y PARAAD), con los planes de sesgo diario ya registrados (`planes_sesgo_v1`: 125 calendarios en 2018 y 125 en 2019; desplazamiento β·σ, β de una normal truncada en 0.4–4). Sin entrenar ni recalibrar | Completa «su anomalía en su ciudad», pendiente de la 20b. Se registró **antes** de aplicar el sesgo a los datos de examen. **Aprobada por el tesista el 2026-10-29** |
| 21 | 2026-10-29 | **Error fijo en ppb:** los mismos calendarios de prueba (2024 y 2025–2026), con la lectura más o menos a ppb (a ∈ {5, 10, 20, 40}) en lugar de un porcentaje; detectores congelados L0 único, V4S compartido, R3, V4 y PARAAD (revisión 20) | Pedido del asesor (2026-10-26): «un sensor se equivoca por una cantidad, no por un porcentaje». También es el tipo de anomalía de PARAAD. Se registró **antes** de programar o generar nada. **Aprobada por el tesista el 2026-10-29** (tamaños 5, 10, 20 y 40; PARAAD incluido) |

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

**Resultado de la fase 2 (2026-10-24): examen 2024 por estación-día.**
- **Cómo se corrió:**
  - en la lap, dos corridas por detector, con salidas idénticas;
  - la regla no se entrena;
  - el V4 se cargó de disco y repitió su inferencia.
- **Controles:**
  - en los 52 conjuntos de cada detector, el puntaje de red reproduce el guardado por
    `evaluar_regla_vecinas.py` o `evaluar_v4.py`;
  - el V4 reproduce sus predicciones de 2024 limpio (diferencia máxima 1.4 × 10⁻¹⁴ ppb) y repite
    el primer calendario con residuos idénticos.
- **F1 con 1 %, regla de vecinas** (promedio del día, que decide, y peor hora):
  - 0.323 y 0.261 con 100 %;
  - 0.330 y 0.200 con 50 %;
  - 0.116 y 0.047 con 20 %;
  - 0.038 y 0.018 con 10 %;
  - 0.016 y 0.013 con 5 %.
- **F1 con 1 %, V4** (promedio del día y peor hora):
  - 0.206 y 0.205 con 100 %;
  - 0.102 y 0.099 con 50 %;
  - 0.029 y 0.024 con 20 %;
  - 0.018 y 0.014 con 10 %;
  - 0.014 y 0.011 con 5 %.
- **Sin ataque,** con el mismo umbral, el F1 con 1 % va de 0.006 a 0.012.
- **Falsas alarmas en 2024 limpio con el umbral de 1 % de 2023:**
  - regla: 1.2 % con el promedio del día y 1.9 % con la peor hora;
  - V4: 2.9 % y 2.3 %.
- **Falsas alarmas con 1 % y δ = 100 %, regla con el promedio del día:**
  - contagio: 25 %, con una tasa de 24 %;
  - tras un ataque propio: 24 %, con una tasa de 25 %;
  - resto: 51 %, con una tasa de 1.4 %.
- **En el V4, el contagio pesa poco:** 4 % de sus falsas alarmas.
- **Excluidas:** 21 % de las estación-días en la regla y 19 % en el V4. Incluye todo ACO, que no
  tiene datos en 2024.
- **Predicciones:** la 6 se cumplió, porque con δ ≥ 50 % la regla supera al V4. En total se
  cumplieron 5 de 6.
- **No se compara uno a uno con la hora de red.**
- **Detalle:** en `progreso.md` (2026-10-24) y en `results/anomalias_red_v1/estacion_dia/`.

### Revisión 12 (2026-10-24): regla de vecinas robusta por estación-día

**Estado:**
- la registró Claude a pedido del tesista (opción b), antes de programarla;
- el tesista la aprobó el 2026-10-24, antes de correrla con datos reales.

**Por qué.** En la fase 2 de la revisión 11, con δ = 100 % y el promedio del día, casi la mitad de
las falsas alarmas de la regla viene de dos sesgos sostenidos:
- **el contagio:** una vecina atacada ese día. Es el 25 % de las falsas alarmas, con una tasa de
  24 %. La columna (a) resta el promedio de las vecinas, así que un ataque en una de ellas mueve a
  la estación limpia como ~1/4 del ataque, en sentido contrario.
- **la referencia contaminada:** los 14 días siguientes a un ataque propio. Es el 24 %, con una
  tasa de 25 %. El perfil de 14 días con la media absorbe los días atacados.

**Qué cambia.** Dos cambios, uno contra cada sesgo:
- **Cambio 1, la mediana de 14 días:**
  - la columna a14 usa el perfil de 14 días con la mediana (`referencia='mediana'`, ya programado
    y probado en la revisión 10);
  - con episodios de 1 a 7 días, menos de la mitad de los 14 días queda atacada, así que la
    mediana casi no se mueve;
  - **nota honesta:** en la revisión 10, la mediana no pasó la elección del LSTM por hora de red.
    Aquí la pregunta es otra, la regla por estación-día, donde el exceso tras un ataque propio es
    mucho mayor (una tasa de 25 % contra 1.4 % en el resto).
- **Cambio 2, la dominancia en el vecindario:**
  - una estación-día sólo puede alertar si su puntaje del día es el mayor entre ella y sus vecinas
    evaluadas ese día, dentro de los 31 objetivos; si alguna vecina tiene uno mayor, el suyo pasa a
    0, y con empate se quedan las dos;
  - **por qué funciona:** la estación atacada se mueve ~4 veces más que la vecina contagiada, así
    que casi siempre gana;
  - **el costo:** si dos vecinas están atacadas el mismo día, una puede apagarse. Se reporta
    cuántas estación-días atacadas se apagan así;
  - se aplica igual en la calibración, en el examen y en el «sin ataque».
- **Variantes,** todas con el promedio del día de la revisión 11:
  - R0: la regla de la revisión 11 (media, sin dominancia);
  - R1: mediana;
  - R2: dominancia;
  - R3: mediana y dominancia.

**Qué no cambia:**
- la unidad, las etiquetas, el mínimo de 12 horas, el umbral común para las 31 estaciones, las
  métricas de la revisión 9, los grupos de falsas alarmas y la división de años;
- el V4 no entra: su contagio es chico (4 %), y su referencia no se puede cambiar sin reentrenarlo.

**Elección con 2022, fijada antes de correrla:**
- **Datos:** como la fase 1 de la revisión 11.
  - La escala de la columna se ajusta con 2020–2021 limpio, con la referencia de cada variante.
  - Los umbrales salen de las estación-días de 2021 limpio, con la misma transformación.
  - El examen usa 2022 de los calendarios 01–10, y el «sin ataque», 2022 limpio.
- **Severidades:** δ = 100, 50 y 20 % deciden; 10 y 5 % sólo se reportan.
- **Medida:** F̄ es el F1 con 1 %, promediado entre los tres δ que deciden.
- **Regla:**
  1. son candidatas las variantes con F̄ de al menos el de R0 + 0.02; si no hay ninguna, la
     revisión 12 se cierra y **no se examina con 2024**;
  2. entre las candidatas, se elige la de mayor F̄;
  3. si una candidata con menos cambios (R1 o R2 frente a R3) queda a menos de 0.02 de la
     elegida, se elige esa; si las dos quedan, la de mayor F̄. Tiene que ser candidata, es decir,
     cumplir también el paso 1. Esta aclaración se agregó al programarla, antes de correrla.
- **Contraste, que no decide:**
  - el F1 con 5 %, el PR-AUC, el recall y la precisión;
  - las falsas alarmas por grupo;
  - las estación-días atacadas que apaga la dominancia.
- **Controles:**
  - se corre dos veces y debe salir idéntica;
  - R0 debe reproducir exactamente el promedio del día de la fase 1 de la revisión 11.

**Examen 2024, sólo si se elige una variante** (en la lap, con `evaluar_estacion_dia.py`):
- **Qué corre:** las cuatro variantes, como en la fase 2 de la revisión 11.
- **Qué decide:** sólo la comparación entre la elegida y R0. Las otras dos se reportan como
  contraste.
- **Control:** R0 debe reproducir exactamente la regla de la fase 2 de la revisión 11.

**Predicción de Claude, antes de correrla:**
1. En 2022, con δ = 100 %, la mediana baja la tasa de falsas alarmas tras un ataque propio de ~20 %
   a menos de 10 %.
2. En 2022, con δ = 100 %, la dominancia baja la tasa de falsas alarmas por contagio de ~19 % a
   menos de 5 %.
3. Se elige R3.
4. En 2022, el F̄ de R3 supera al de R0 en 0.05 o más.
5. La ganancia es menor con δ = 20 % que con 100 y 50 %, porque los dos sesgos crecen con δ.
6. En 2024, con δ = 50 %, la variante elegida llega a un F1 con 1 % de 0.38 o más (R0: 0.33).
7. Con δ ≤ 10 %, ninguna variante cambia el F1 con 1 % en 0.02 o más.

**Implementación prevista:**
- **Función** `estacion_dia.dominancia`, con sus pruebas:
  - las vecinas asimétricas;
  - los empates;
  - las vecinas sin puntaje.
- **Script** `experiments/anomalias_red/diagnostico_regla_robusta_2022.py`, para la elección.
- **Opciones** `--referencia` y `--dominancia` en `evaluar_estacion_dia.py`. Sus valores por
  defecto deben reproducir la revisión 11 byte por byte.
- **Salidas:**
  - `results/anomalias_red_v1/regla_robusta_2022/`;
  - `results/anomalias_red_v1/estacion_dia/regla_<variante>/`.

**Elección con 2022 (2026-10-24): R3, mediana y dominancia.**
- **Cómo se corrió:** en la lap, dos corridas idénticas. R0 reproduce exactamente el promedio del día
  de la fase 1 de la revisión 11.
- **F̄,** el F1 con 1 % promediado entre δ = 100, 50 y 20 %:
  - R0: 0.288;
  - R1: 0.297;
  - R2: 0.324;
  - R3: 0.344.
- **Aplicación de la regla:**
  - son candidatas R2 (+0.036) y R3 (+0.056). R1 queda fuera, con +0.009;
  - la de mayor F̄ es R3;
  - la candidata más sencilla, R2, queda a 0.0201 de R3, y la regla pide menos de 0.02, así que
    **queda R3**;
  - **es una decisión en el límite:** R3 gana por 0.0001.
- **F1 con 1 % por δ** (R0, R1, R2, R3):
  - 0.377, 0.413, 0.461 y 0.516 con 100 %;
  - 0.389, 0.385, 0.414 y 0.419 con 50 %;
  - 0.098, 0.093, 0.096 y 0.097 con 20 %.
- **Falsas alarmas con δ = 100 % y 1 %:**
  - la dominancia baja la tasa por contagio de 19.0 % a 0.9 %;
  - la mediana baja la tasa tras un ataque propio de 20.3 % a 11.4 %.
- **Lo que apaga la dominancia:** de 770 estación-días atacadas válidas, se apagan 47–52 con
  δ = 100 % (18–22 alertas verdaderas perdidas) y 294–309 con 20 % (5–6 alertas perdidas).

**Examen 2024 (2026-10-24).**
- **Cómo se corrió:** en la lap, dos corridas por variante, idénticas. Con los valores por defecto,
  R0 reproduce byte por byte la fase 2 de la revisión 11.
- **F1 con 1 % por estación-día** (R0, R1, R2, **R3**):
  - 0.323, 0.365, 0.379 y **0.425** con 100 %;
  - 0.330, 0.344, 0.331 y **0.347** con 50 %;
  - 0.116, 0.108, 0.109 y **0.109** con 20 %;
  - 0.038, 0.034, 0.037 y 0.035 con 10 %;
  - 0.016, 0.021, 0.019 y 0.021 con 5 %.
- **Sin ataque,** el F1 con 1 % es de 0.012–0.013.
- **R3 contra R0 con δ = 100 %:**
  - la precisión pasa de 0.20 a 0.29, y el recall de 0.85 a 0.83;
  - las falsas alarmas por contagio bajan de 598 a 36, y las de tras un ataque propio de 584 a 320.
- **Predicciones:**
  - se cumplieron la 2, la 3, la 4, la 5 y la 7;
  - falló la 1: la tasa tras un ataque propio bajó a 11.4 %, no a menos de 10 %;
  - falló la 6: con δ = 50 % llegó a 0.347, no a 0.38.
  - En total se cumplieron 5 de 7.
- **Detalle:** en `progreso.md` (2026-10-24), `results/anomalias_red_v1/regla_robusta_2022/` y
  `results/anomalias_red_v1/estacion_dia/regla_*`.

### Revisión 13 (2026-10-24): LSTM supervisado por estación

**Estado:**
- la redactó Claude a pedido del tesista;
- el tesista la aprobó el 2026-10-24, con el paso 2 tal cual;
- se corrió la elección con 2022 el 2026-10-24: **no pasa el paso 2, se cierra sin 2024** (abajo).

**Por qué.**
- **Lo que ayudó en las revisiones 11 y 12 es la forma de responder,** no una entrada:
  - juntar el día por estación;
  - la dominancia entre vecinas.
- **El LSTM de la revisión 8 no puede usar esas mejoras:** da una sola respuesta por hora para
  toda la red.
- **Esta revisión le cambia la salida:** una probabilidad por estación cada hora. Así recibe las
  mismas mejoras que la regla y responde la misma pregunta.
- **La pregunta:** ¿el LSTM supervisado por estación le gana a la regla robusta (R3), que no se
  entrena?

**Qué cambia.**
- **Salida:** 31 salidas sigmoides, una por objetivo. HGM no tiene salida, porque nunca se altera.
- **Etiqueta por estación-hora:** 1 si la lectura de esa estación fue alterada en esa hora; sale
  de `estaciones_alteradas` de la matriz. La etiqueta nunca es entrada.
- **Pérdida:** la entropía cruzada binaria promediada sobre las 31 salidas, sin pesos de clase.
- **Valor por hora y estación:** la probabilidad de esa salida.
  - Las horas válidas son las que tienen dato de la estación.
  - El día se junta con el **promedio del día**, el promedio de las probabilidades de las horas
    válidas. La peor hora se reporta como contraste.
  - Hacen falta al menos 12 horas válidas.
- **Dominancia:** la de la revisión 12, sobre los puntajes del día y con las mismas vecinas.

**Qué no cambia:**
- **Del LSTM de la revisión 8:**
  - la ventana t−23…t con las 98 columnas;
  - la arquitectura: LSTM de 64, dropout de 0.2 y una densa de 32, salvo la capa de salida;
  - Adam con 1e-3, lotes de 64 y barajado;
  - `fijar_semilla(42)` inmediatamente antes de construir;
  - los 20 calendarios y un modelo por δ.
- **De la estación-día:** las etiquetas por estación-día, el umbral común para las 31 estaciones,
  las métricas de la revisión 9, los grupos de falsas alarmas y la división de años.

**Configuraciones que se comparan** (2 entrenamientos × 2 lecturas del día):
- **Entradas:** con la media de 14 días (las de la revisión 8) o con la mediana (las de la
  revisión 10).
- **Dominancia:** sin ella o con ella. Se aplica después de entrenar, así que no requiere otro
  entrenamiento.
- **De la más sencilla a la más compleja:** media sin dominancia; luego media con dominancia o
  mediana sin dominancia; luego mediana con dominancia.

**Elección con 2022, fijada antes de correrla** (en Colab, sólo procesador):
- **Modelo de selección:** como la primera etapa de la revisión 8.
  - Entrena con 2020–2021 de los 20 calendarios.
  - Usa EarlyStopping con la pérdida de validación en 2022 de los calendarios 01–10, con
    paciencia 8, máximo 60 épocas y los pesos de la mejor época.
- **Umbral: con las estación-días de 2022 limpio,** con 1 y 5 % de falsas alarmas.
  - No es el de 2021 que usaron las revisiones 11 y 12, porque el LSTM se entrenó con 2021 y su
    umbral saldría optimista.
  - Para comparar en igualdad, la regla R3 se recalcula con este mismo umbral.
- **Examen:** 2022 de los calendarios 01–10.
- **Severidades:** δ = 100, 50 y 20 % deciden. Con 10 y 5 % no se entrena modelo de selección.
- **Medida:** F̄, el F1 con 1 % promediado entre los tres δ, en las estación-días válidas para el
  LSTM y para la regla a la vez.
- **Paso 1, la configuración del LSTM:**
  - la más sencilla queda, salvo que otra la supere en 0.02 o más;
  - si varias la superan, se elige la de mayor F̄;
  - pero si una con menos cambios queda a menos de 0.02 de ella y también supera a la más
    sencilla en 0.02, se elige esa.
- **Paso 2, el LSTM contra la regla:**
  - la configuración elegida pasa a 2024 sólo si su F̄ supera al de R3 en **0.02 o más**;
  - si no, la revisión 13 se cierra, **no se examina con 2024**, y la regla robusta queda como el
    detector por estación-día.
- **Contraste, que no decide:**
  - el F1 por δ, el F1 con 5 %, el PR-AUC, la peor hora y las falsas alarmas por grupo;
  - las estación-días que apaga la dominancia y la época E de cada δ.
- **Reproducibilidad:** dos corridas en paralelo en la misma sesión, que deben salir idénticas.
- **Máquina:**
  - en la misma sesión se recalcula la regla R3 con 2022, y debe reproducir la lap;
  - si no la reproduce, la comparación usa la R3 recalculada en la sesión, y se anota.

**Examen 2024, sólo si pasa el paso 2:**
- **Cómo se entrena:** como la revisión 8, en los cinco δ.
  - E sale del EarlyStopping con 2020–2021 contra 2022.
  - El modelo definitivo se entrena con 2020–2022 y exactamente E épocas.
  - Se entrena dos veces en la misma sesión y se compara.
- **Umbrales:** con las estación-días de 2023 limpio. El examen usa los 10 calendarios de 2024 y
  el «sin ataque», 2024 limpio.
- **Comparación que decide:**
  - el LSTM contra R3, en las estación-días válidas para los dos;
  - R3 se recalcula en la misma sesión y debe reproducir la revisión 12.
- **Contraste:** cada detector en sus propias estación-días válidas, y el V4 por estación-día.
- **Se guardan** los modelos (`modelo.keras`) y las probabilidades por estación-hora, para el examen
  final de 2025–2026.

**Predicción de Claude, antes de correrla:**
1. En 2022, la dominancia cambia el F̄ del LSTM en menos de 0.02. El LSTM ve a todas las
   estaciones y aprende a no culpar a las vecinas.
2. En 2022, las entradas con mediana cambian el F̄ en menos de 0.02, como en la revisión 10.
3. Se elige la configuración más sencilla: media sin dominancia.
4. En 2022, con δ = 100 %, el LSTM supera a R3 por 0.05 o más; con δ = 20 %, no la supera.
5. El LSTM pasa el paso 2.
6. En 2024, con δ = 100 %, el F1 con 1 % del LSTM por estación-día es de 0.50 o más (R3: 0.425).
7. Con δ ≤ 10 %, el F1 con 1 % queda por debajo de 0.10.

**Implementación prevista:**
- **Funciones,** con sus pruebas:
  - `lstm_red.construir_clasificador(..., salidas=1)`. Con 1 da la arquitectura actual, comprobado
    por el número de parámetros; con 31 da 31 sigmoides;
  - `estacion_dia.etiquetas_por_hora(matriz, estaciones)`, a partir de `estaciones_alteradas`.
- **Script** `experiments/anomalias_red/entrenar_lstm_estacion.py`:
  - la etapa de selección por δ y entradas;
  - con `--definitivo`, la revisión 8 completa;
  - guarda las probabilidades por estación-hora.
- **Script** `experiments/anomalias_red/diagnostico_lstm_estacion_2022.py`, con los pasos 1 y 2.
- **El examen 2024** con `evaluar_estacion_dia.py --detector lstm`, que lee las probabilidades
  guardadas.
- **Colab:** un guion como `correr_revision10.sh`, con los archivos subidos como tarball y su
  SHA-256, y dos corridas por paso.
- **Tiempo estimado:**
  - la elección son 6 entrenamientos con EarlyStopping, ~2 h por corrida, y las dos van en
    paralelo;
  - el examen 2024 son 5 δ, ~3 h.
- **Salidas:** `results/anomalias_red_v1/lstm_estacion_2022/` y `results/anomalias_red_v1/lstm_estacion/`.

**Implementación (2026-10-24, antes de correrla).**
- **Aclaraciones al programarla:**
  - en la etapa de selección, la escala de la columna de vecinas se ajusta con 2020–2021 limpio,
    como en las elecciones de las revisiones 8, 10 y 12. El modelo definitivo usa 2020–2022 limpio;
  - **no se guardan las probabilidades por estación-hora:** pesan demasiado. Se guardan los
    modelos (`modelo_seleccion.keras` y `modelo.keras`) y los puntajes por estación-día con las
    dos formas de juntar el día. Las probabilidades por hora se regeneran con el modelo.
- **Código:**
  - `lstm_red.construir_clasificador(..., salidas=)`;
  - `estacion_dia.etiquetas_por_hora`;
  - `entrenar_lstm_estacion.py`;
  - `diagnostico_lstm_estacion_2022.py`.
- **Pruebas:** 2 nuevas, con 276 en total. Con una salida, el clasificador tiene exactamente los
  parámetros de siempre.
- **Control previo en la lap:** la R3 que recalcula `diagnostico_lstm_estacion_2022.py` reproduce
  la revisión 12. Si en Colab no la reproduce, la diferencia es de la máquina.

**Elección con 2022 (2026-10-24): queda C0, pierde contra R3. La revisión 13 se cierra y no se
examina con 2024; R3 sigue como el detector por estación-día.**
- **F1 con 1 %** (umbral de 2022 limpio, estación-días válidas para los dos):

  | Configuración | F̄ | δ = 100 % | δ = 50 % | δ = 20 % |
  |---|---:|---:|---:|---:|
  | C0 (media, sin dominancia) | 0.203 | 0.321 | 0.250 | 0.038 |
  | C1 (media, con dominancia) | 0.209 | 0.336 | 0.253 | 0.039 |
  | C2 (mediana, sin dominancia) | 0.212 | 0.354 | 0.244 | 0.038 |
  | C3 (mediana, con dominancia) | 0.219 | 0.382 | 0.240 | 0.035 |
  | **R3 (regla robusta)** | **0.330** | **0.484** | **0.404** | **0.102** |

- **Paso 1:** ninguna llega a F̄(C0) + 0.02 = 0.223; la más cercana es C3, con +0.016. Queda C0.
- **Paso 2:** C0 queda 0.127 por debajo de R3, y hacía falta +0.02. Aun la mejor configuración, C3,
  queda 0.111 por debajo.
- **R3 con este umbral:** su F̄ es 0.330, contra 0.344 con el umbral de 2021 de la revisión 12. El
  umbral de 2022 también es más estricto para la regla, así que la comparación es pareja.
- **Contraste, que no decide:**
  - **PR-AUC** (C0 y R3): 0.49 y 0.67 con 100 %; 0.18 y 0.34 con 50 %; 0.016 y 0.039 con 20 %.
    El LSTM ordena peor en todos los umbrales, no sólo en el de 1 %.
  - **ROC-AUC con 100 %:** 0.92 y 0.96.
  - **Con 100 % y 1 %:** el recall es 0.66 y 0.83, y la precisión 0.21 y 0.34.
  - **F1 con 5 % y 100 %:** 0.13 y 0.21.
  - **Peor hora:** el diagnóstico no la calculó, aunque el diseño la pedía como contraste. Se
    calculó después, en la lap, con los puntajes guardados (sin cargar modelos), con
    `exploracion_revision13_2022.py`. Con 1 % da 0.342,
    0.246 y 0.041 con la media y 0.374, 0.249 y 0.041 con la mediana. Queda igual de lejos de R3.
- **Falsas alarmas con 100 % y 1 %** (C0, C3 y R3):
  - **Contagio:** 212, 58 y 25.
  - **Tras un ataque propio:** 361, 276 y 323.
  - **Resto:** 1337, 1220 y 880. En los calendarios atacados, la tasa del resto es de 1.51 % con
    C0 y de 1.00 % con R3; el umbral da 1 % en 2022 limpio.
- **Lo que apaga la dominancia:** de 770 estación-días atacadas válidas, apaga 164 (C1) y 145 (C3)
  con 100 %, y 555–612 con 20 %. Con R3 eran 47–52 con 100 %.
- **Época E:** fue la 1 en las seis corridas, de 9 ejecutadas, como en la revisión 8.
- **Predicciones:** de las 5 que se podían evaluar con 2022, se cumplieron 3.
  - Se cumplieron la 1, la 2 y la 3. La dominancia cambia el F̄ en +0.006/+0.007, la mediana en
    +0.009/+0.010, y queda C0.
  - Falló la 4: con 100 %, el LSTM queda 0.16 por debajo de R3, no 0.05 por encima.
  - Falló la 5: no pasa el paso 2.
  - La 6 y la 7 eran de 2024 y no se evalúan.
- **Reproducibilidad:**
  - las dos corridas en paralelo salieron idénticas archivo por archivo: historias, puntajes,
    configuraciones y los seis archivos de la elección;
  - los números vienen de modelos **recién entrenados** en Colab (sesión `rev13`, AMD EPYC 7B12),
    guardados como `modelo_seleccion.keras`.
- **Máquina:** la R3 recalculada en la sesión reproduce la revisión 12 (TP, FP, FN y TN iguales).
- **Detalle:** en `progreso.md` (2026-10-24), `results/anomalias_red_v1/lstm_estacion_2022/` y
  `results/anomalias_red_v1/lstm_estacion/`.

### Revisión 14 (2026-10-24): LSTM local compartido por estación

**Estado:**
- la redactó Claude a pedido del tesista (opción C);
- el tesista la aprobó tal cual el 2026-10-24, con lo que haya que entrenar en Colab.
- la elección con 2022 se corrió el 2026-10-25: **queda L0 y pasa el paso 2** (abajo);
- el examen 2024 se corrió el 2026-10-25 con la aprobación del tesista (abajo).

**Por qué: lo que mostró la revisión 13 en 2022.**
- **Un ataque lejano mueve a toda la red.** Lo mostró la exploración del 2026-10-24
  (`exploracion_revision13_2022.py`), con los puntajes
  guardados de 2022, en las estación-días normales del grupo «resto». Ahí no hay ninguna vecina
  atacada y la estación no tuvo un ataque propio en los 14 días anteriores:
  - con δ = 100 % y 1 %, la tasa de falsas alarmas del LSTM es de 1.24 % los días sin ataques en
    la red y de **2.66 %** los días con un ataque en otra parte;
  - la de R3 es de 1.00 % y 0.98 %;
  - con 50 %, el LSTM pasa de 1.01 % a 1.44 %, y R3 de 1.00 % a 1.05 %.
  - Es lo esperable: cada salida del LSTM ve las 98 columnas de las 32 estaciones; la regla sólo
    mira 4 vecinas.
- **Localiza mal.** La dominancia apaga 164 de 770 estación-días atacadas con 100 %; en R3 eran
  47–52.
- **Memoriza pronto.** La mejor época fue la 1 en los seis modelos. Con 20 calendarios, el modelo
  se aprende esos ataques en particular.

**Qué cambia frente a la revisión 13.**
- **Modelo local compartido:** un solo LSTM que, para cada objetivo s y cada hora t, mira la ventana
  t−23…t con **17 columnas**:
  - de s, sus 3 columnas de la revisión 8: la relativa (valor menos el perfil de 14 días con media,
    entre σ), la máscara y la columna de vecinas a14;
  - las mismas 3 de cada una de sus 4 vecinas (las de R3), en orden de distancia;
  - el seno y el coseno de la hora.
- **Salida:** una sigmoide, ¿la lectura de s fue alterada en la hora t? La etiqueta es la de la
  revisión 13, por estación-hora, y nunca es entrada.
- **Se comparten los pesos:** el mismo modelo se aplica a las 31 estaciones, sin identificador de
  estación. Así cada estación aporta ejemplos al mismo modelo, y el modelo sirve para cualquier
  estación con 4 vecinas.
- **Más calendarios:** se generan `entrenamiento_21` … `entrenamiento_60` con el mismo generador y
  la misma regla de semillas. Los calendarios 01–20 no cambian, y se comprueba. Los nuevos sólo se
  usan en esta revisión.
- **Ventanas de entrenamiento:** dos ventanas de horas seguidas comparten 23 de sus 24 horas. Por
  eso se toma una parte de las horas de cada calendario y estación, sin reemplazo y con una semilla
  que se deriva de 42 y del par, sin `hash()`:
  - con 20 calendarios, 1 de cada 8 horas;
  - con 60, 1 de cada 24;
  - en los dos casos son unas 1.36 millones de ventanas por época, así que la comparación aísla la
    **variedad de ataques** con los mismos ejemplos y el mismo cómputo;
  - la validación del EarlyStopping usa 1 de cada 8 horas de 2022 de los calendarios 01–10;
  - los puntajes para la elección usan todas las horas.

**Qué no cambia:**
- **Del entrenamiento** de la revisión 13:
  - la arquitectura: LSTM de 64, dropout de 0.2 y una densa de 32;
  - Adam con 1e-3, lotes de 64 y barajado;
  - `fijar_semilla(42)` inmediatamente antes de construir;
  - un modelo por δ;
  - la pérdida, que aquí es de una sola salida, sin pesos de clase;
  - la referencia de las entradas: la media, que quedó en el paso 1 de la revisión 13.
- **Cómo se junta el día:** el promedio del día con al menos 12 horas válidas, la dominancia, las
  etiquetas por estación-día, el umbral común, las métricas de la revisión 9 y la división de años.

**Configuraciones** (2 entrenamientos × 2 lecturas del día):
- **L0:** local, 20 calendarios, sin dominancia. Es la más sencilla.
- **L1:** local, 20 calendarios, con dominancia.
- **L2:** local, 60 calendarios, sin dominancia.
- **L3:** local, 60 calendarios, con dominancia.

**Elección con 2022:** como la de la revisión 13, fijada antes de correrla.
- **Modelo de selección:** se entrena con 2020–2021 y usa EarlyStopping con 2022 de los calendarios
  01–10, con paciencia 8, máximo 60 épocas y los pesos de la mejor época.
- **Umbral:** con 2022 limpio. R3 se recalcula con el mismo umbral, en las estación-días válidas
  para los dos.
- **Medida:** F̄, el F1 con 1 % promediado entre δ = 100, 50 y 20 %.
- **Paso 1:** queda L0, salvo que otra la supere en 0.02 o más. Entre las candidatas, la de mayor
  F̄, salvo una con menos cambios a menos de 0.02.
- **Paso 2:** la elegida pasa a 2024 sólo si su F̄ supera al de R3 en 0.02 o más.
- **Si no pasa:**
  - la revisión 14 se cierra sin 2024;
  - **se cierra la línea supervisada por estación-día**: no habrá otra elección con 2022 para ella;
  - R3 queda como el detector por estación-día;
  - las revisiones 13 y 14 se reportan como resultado negativo.
- **Contraste, que no decide:**
  - el F1 por δ, el F1 con 5 %, el PR-AUC y la peor hora. Esta vez el diagnóstico la calcula;
  - las falsas alarmas por grupo, con el «resto» separado en días con y sin ataque en la red;
  - lo que apaga la dominancia y la época E;
  - el C0 de la revisión 13 con el mismo umbral, que ya está guardado.
- **Reproducibilidad y máquina:** dos corridas en paralelo en Colab, que deben salir idénticas. R3 se
  recalcula en la sesión y debe reproducir la revisión 12.

**Examen 2024, sólo si pasa el paso 2:** como el previsto en la revisión 13.
- Se entrena el modelo definitivo con 2020–2022 y E épocas, en los cinco δ. Los δ = 10 y 5 % llevan
  antes su etapa de selección para obtener E.
- El umbral sale de 2023 limpio.
- Decide la comparación contra R3, recalculada en la misma sesión. El V4 va de contraste.
- Se guardan los modelos para el examen final de 2025–2026.

**Límites declarados:**
- 2022 ya se usó para elegir en las revisiones 8, 10, 11, 12 y 13. Cada elección nueva con el mismo
  año le resta confianza a la que gana; por eso ésta es la última para esta línea.
- El diseño se basa en lo que se vio de la revisión 13 en 2022, el mismo año con el que se elige.
- Los 60 calendarios comparten el mismo fondo limpio de 2020–2021. Ayudan contra la memoria de los
  ataques, no contra la de los días naturales raros de esos años.

**Predicción de Claude, antes de correrla.** En la revisión 13 fallé por optimista.
1. L0 supera al C0 de la revisión 13 en 0.05 o más de F̄ (de 0.203 a 0.253 o más).
2. Con L0, δ = 100 % y 1 %, la tasa del «resto» en días con un ataque en la red baja de 2.66 % a
   menos de 1.5 %.
3. La dominancia cambia el F̄ en menos de 0.02.
4. Los 60 calendarios cambian el F̄ en menos de 0.02, así que queda L0.
5. Con 20 calendarios, la época E es 2 o más en al menos dos de los tres δ.
6. La elegida **no pasa el paso 2**, pero queda a menos de 0.05 de R3 (F̄ entre 0.280 y 0.350).

**Implementación prevista:**
- **Funciones,** con sus pruebas:
  - las 17 columnas locales a partir de las 98;
  - la muestra de ventanas por calendario y estación, reproducible.
- **Script** `experiments/anomalias_red/entrenar_lstm_local.py`, con la etapa de selección y, con
  `--definitivo`, la del examen.
- **La elección** en `diagnostico_lstm_local_2022.py`, con los pasos 1 y 2.
- **Los calendarios 21–60:** con una opción del generador de planes y matrices. El número por
  defecto, 20, no cambia, para que las revisiones 7, 8 y 13 sigan iguales.
- **Colab:** un guion como el de la revisión 13, con dos corridas en paralelo.
- **Tiempo estimado:** unas 4 h si la mejor época sale pronto. Puede llegar a ~10 h si el modelo
  sigue mejorando muchas épocas.
- **Salidas:** `results/anomalias_red_v1/lstm_local/` y `results/anomalias_red_v1/lstm_local_2022/`.

**Implementación (2026-10-24, antes de correrla).**
- **Código:**
  - `src/detect/lstm_local.py`, con `indices_locales`, `muestra` y `ventanas_locales`;
  - la constante `anomalias_red.CALENDARIOS_AMPLIADOS = 60`;
  - la opción `--ampliados` de `generar_planes.py` y `generar_matrices.py`: escribe sólo los
    calendarios 21–60 y sus resúmenes (`resumen_planes_revision14.csv` y
    `resumen_matrices_revision14.csv`); sin ella, todo sale igual que antes;
  - `entrenar_lstm_local.py` y `diagnostico_lstm_local_2022.py`.
- **Pruebas:** 3 nuevas, con 279 en total.
  - Las 17 columnas salen de su lugar en las 98.
  - La muestra es reproducible, sin reemplazo y distinta por par.
  - Los calendarios 01–20 no cambian.
  - El clasificador local tiene los parámetros esperados.
- **Aclaraciones al programarla:**
  - la semilla de la muestra es `default_rng([42, 14, uso, número del calendario, índice de la
    estación])`, con uso 0 para la selección, 1 para la validación y 2 para el definitivo;
  - el C0 de la revisión 13 se lee de sus puntajes guardados.
- **Comprobaciones en la lap:**
  - los 40 planes y las 200 matrices nuevas se generaron;
  - los planes y resúmenes de siempre no cambiaron;
  - el modo `--prueba` de los dos scripts corre completo, y no se miraron sus métricas.
- **Colab:**
  - la sesión `rev14` tocó un **Intel Xeon @ 2.20 GHz**, no el AMD EPYC de las revisiones 8 y 13;
  - la elección no se afecta, porque compara todo dentro de la misma sesión, y R3 es aritmética;
  - el guion comprueba que Colab genera los mismos planes y matrices nuevas que la lap, con el
    SHA-256 de cada matriz.

**Elección con 2022 (2026-10-25): queda L0 y le gana a R3 por +0.061. Pasa a 2024.**
- **F1 con 1 %** (umbral de 2022 limpio, estación-días válidas para todos):

  | Configuración | F̄ | δ = 100 % | δ = 50 % | δ = 20 % |
  |---|---:|---:|---:|---:|
  | **L0 (20 calendarios, sin dominancia)** | **0.391** | **0.508** | **0.472** | **0.193** |
  | L1 (20 calendarios, con dominancia) | 0.398 | 0.515 | 0.479 | 0.198 |
  | L2 (60 calendarios, sin dominancia) | 0.394 | 0.487 | 0.470 | 0.225 |
  | L3 (60 calendarios, con dominancia) | 0.398 | 0.491 | 0.474 | 0.228 |
  | R3 (regla robusta) | 0.330 | 0.484 | 0.404 | 0.102 |
  | C0 de la revisión 13 (contraste) | 0.203 | 0.321 | 0.250 | 0.038 |

- **Paso 1:** ninguna llega a F̄(L0) + 0.02 = 0.411; la más cercana es L3, con +0.007. Queda L0.
- **Paso 2:** L0 supera a R3 por 0.061, y hacía falta 0.02. **Pasa a 2024.**
- **El C0 de la revisión 13** sale igual que en su elección: 0.321, 0.250 y 0.038.
- **Contraste, que no decide** (L0 y R3):
  - **PR-AUC:** 0.84 y 0.67 con 100 %; 0.48 y 0.34 con 50 %; 0.10 y 0.04 con 20 %.
  - **Con 1 %:** el recall es 0.96 y 0.83 con 100 %, 0.79 y 0.59 con 50 %, y 0.24 y 0.12 con 20 %.
    La precisión es parecida o mejor: 0.35 y 0.34 con 100 %.
  - **F1 con 5 %:** 0.214 y 0.214 con 100 %; 0.209 y 0.195 con 50 %; 0.148 y 0.091 con 20 %.
  - **Peor hora de L0:** 0.516, 0.456 y 0.181. El promedio del día queda por encima con 50 y 20 %.
  - **Sin ataque,** el F1 con 1 % es de 0.004–0.014 con L0 y de 0.001 con R3: nivel de azar.
- **Falsas alarmas con 100 % y 1 %** (L0, C0 de la revisión 13 y R3):
  - **Contagio:** 58, 212 y 25.
  - **Tras un ataque propio:** 457, 361 y 323. **Es la debilidad que queda:** con las relativas a
    la media, el perfil de 14 días se contamina tras el ataque. La tasa es de 18.4 % contra 13.0 %
    de R3, que usa la mediana.
  - **Resto en días con un ataque en la red:** 1.15 %, 2.66 % y 0.98 %. El contagio lejano casi
    desaparece con el modelo local.
- **Lo que apaga la dominancia:** de 770 estación-días atacadas, apaga 25 (L1) con 100 %, contra
  164 en la revisión 13. Ahora el LSTM sí localiza la estación.
- **Época E:** con 20 calendarios fue la 3 con 100 % y la 1 con 50 y 20 %; con 60 calendarios fue la
  1 en los tres δ.
- **Predicciones:** se cumplieron 4 de 6.
  - Se cumplió la 1: L0 sube a 0.391 desde 0.203.
  - Se cumplió la 2: el resto en días con ataque baja de 2.66 % a 1.15 %.
  - Se cumplió la 3: la dominancia suma +0.007.
  - Se cumplió la 4: los 60 calendarios suman +0.003, y queda L0.
  - Falló la 5: E ≥ 2 sólo con 100 %.
  - Falló la 6: predije que no pasaría el paso 2, y lo pasa por 0.061.
- **Reproducibilidad:**
  - las dos corridas en paralelo salieron idénticas archivo por archivo;
  - los números vienen de modelos **recién entrenados** en Colab (sesión `rev14`, Intel Xeon
    @ 2.20 GHz), guardados como `modelo_seleccion.keras`;
  - una vista preliminar, pedida por el tesista con 5 de 6 modelos, se midió en la lap y coincide
    con estos puntajes.
- **Máquina:**
  - la R3 recalculada en la sesión reproduce la revisión 12;
  - Colab generó los 40 planes y las 200 matrices nuevas iguales a los de la lap.
- **Cautela:**
  - 2022 ya se usó para elegir en seis revisiones, y el EarlyStopping del LSTM también usa 2022;
  - la ventaja tiene que confirmarse en 2024, con el examen ya registrado.
- **Detalle:** en `progreso.md` (2026-10-25), `results/anomalias_red_v1/lstm_local_2022/` y
  `results/anomalias_red_v1/lstm_local/`.

**Examen 2024: implementación y predicciones (2026-10-25, aprobado por el tesista, antes de correrlo).**
- **Entrenamiento:**
  - `entrenar_lstm_local.py --calendarios 20 --definitivo` con los cinco δ;
  - cada δ repite su etapa de selección (nueva con 10 y 5 %) y entrena el modelo definitivo con
    2020–2022 y E épocas;
  - las salidas van a `results/anomalias_red_v1/lstm_local_examen/`, para no pisar la elección;
  - con δ = 100, 50 y 20 %, su selección debe salir idéntica a la de la elección.
- **Evaluación:** `evaluar_lstm_local_2024.py`, en la misma sesión.
  - Recalcula R3 como la fase 2 de la revisión 12, y debe reproducirla.
  - Mide L0 y R3 en las estación-días válidas para los dos.
  - Los umbrales de cada detector salen de 2023 limpio en esas estación-días.
  - El contraste del V4 es su resultado guardado de la fase 2 de la revisión 11.
  - Salidas en `results/anomalias_red_v1/lstm_local_2024/`.
- **Reproducibilidad:** dos corridas en paralelo en la sesión `rev14`, la misma máquina de la
  elección. Se comparan archivo por archivo.
- **No se elige nada con 2024.** Se reporta L0 contra R3.
- **Predicción de Claude, antes de correrlo** (F1 con 1 %, estación-días comunes):
  1. Con δ = 50 y 20 %, L0 supera a R3.
  2. La ventaja promedio de L0 en δ = 100, 50 y 20 % es positiva pero menor que la de 2022: entre
     0 y +0.061.
  3. Con δ = 100 %, la diferencia entre L0 y R3 es menor de 0.05, a favor de cualquiera.
  4. Con δ = 10 y 5 %, los dos quedan por debajo de 0.10.
  5. Con 100 %, L0 da más falsas alarmas que R3 tras un ataque propio.

**Examen 2024 (2026-10-25): L0 iguala a R3 con δ = 100 % y le gana con 50 y 20 %.**
- **F1 con 1 % por estación-día** (estación-días válidas para los dos; umbral de 2023 limpio):

  | δ | **L0** | R3 | L0 − R3 | Sin ataque (L0 / R3) | V4, sus propias estación-días |
  |---:|---:|---:|---:|---:|---:|
  | 100 % | **0.427** | 0.425 | +0.002 | 0.013 / 0.013 | 0.206 |
  | 50 % | **0.388** | 0.347 | +0.042 | 0.016 / 0.013 | 0.102 |
  | 20 % | **0.158** | 0.109 | +0.049 | 0.017 / 0.013 | 0.029 |
  | 10 % | 0.038 | 0.035 | +0.004 | 0.010 / 0.013 | 0.018 |
  | 5 % | 0.008 | 0.021 | −0.013 | 0.009 / 0.013 | 0.014 |

  - Promediado entre 100, 50 y 20 %: 0.324 contra 0.294, o sea **+0.031**. En 2022 era +0.061.
  - En sus propias estación-días válidas, L0 da 0.433, 0.386, 0.159, 0.039 y 0.008. R3 da lo mismo
    que en la revisión 12.
- **Contraste, que no decide** (L0 y R3):
  - **Con 100 % y 1 %:** el recall es 0.94 y 0.83, y la precisión 0.28 y 0.29. Encuentra 662
    estación-días atacadas contra 579, con más falsas alarmas.
  - **Con 50 %:** el recall es 0.80 y 0.60, y la precisión 0.26 y 0.24.
  - **F2 con 1 %:** 0.636 y 0.600 con 100 %; 0.562 y 0.466 con 50 %; 0.177 y 0.133 con 20 %.
  - **PR-AUC:** 0.85 y 0.69 con 100 %; 0.58 y 0.41 con 50 %; 0.083 y 0.046 con 20 %.
  - **F1 con 5 %:** 0.183 y 0.166 con 100 %; 0.169 y 0.143 con 50 %; 0.120 y 0.076 con 20 %.
  - **Peor hora de L0:** 0.430, 0.360 y 0.144.
  - **Con 10 y 5 %,** los dos quedan casi en su valor sin ataque, es decir, en el azar.
- **Falsas alarmas con 100 % y 1 %** (L0 y R3):
  - **Contagio:** 81 y 36, con tasas de 3.2 % y 1.4 %.
  - **Tras un ataque propio:** 536 y 320, con tasas de **22.7 %** y 13.6 %. Es la debilidad de L0, y
    en 2024 es mayor que en 2022.
  - **Resto en días con un ataque en la red:** 1.36 % y 1.49 %. El contagio lejano de la revisión
    13 ya no aparece.
- **Época E de los δ nuevos:** 2 con 10 % (de 10 épocas) y 6 con 5 % (de 14).
- **Predicciones:** se cumplieron las 5.
  - 1: L0 le gana a R3 con 50 y 20 %.
  - 2: la ventaja promedio es positiva y menor que la de 2022.
  - 3: con 100 % la diferencia es de 0.002.
  - 4: con 10 y 5 % los dos quedan por debajo de 0.10.
  - 5: L0 da más falsas alarmas tras un ataque propio.
- **Reproducibilidad:**
  - las dos corridas en paralelo salieron idénticas archivo por archivo: las historias, los
    puntajes de 2022 y de 2024, las configuraciones y las cuatro salidas del examen;
  - con 100, 50 y 20 %, la selección repite byte por byte la de la elección;
  - los números vienen de modelos definitivos **recién entrenados** en Colab (sesión `rev14`, Intel
    Xeon @ 2.20 GHz), guardados como `modelo.keras`.
- **Máquina:** la R3 recalculada en la sesión reproduce la revisión 12.
- **Límites para la lectura:**
  - **una sola semilla y sin intervalos:** no se sabe todavía si +0.04 o +0.05 superan el ruido;
  - **2024 no es del todo limpio para esta línea:** la revisión 12 se diseñó viendo 2024, y L0
    hereda sus ideas;
  - **falta la prueba con hora de inicio al azar** registrada en la revisión 6: todos los ataques
    empiezan a las 00 h y duran días enteros, como la estación-día;
  - **un modelo por δ:** cada modelo conoce el tamaño del ataque.
- **Detalle:** en `progreso.md` (2026-10-25), `results/anomalias_red_v1/lstm_local_2024/` y
  `results/anomalias_red_v1/lstm_local_examen/`.

### Revisión 15 (2026-10-25): dos puntos de operación, p99 y p99.9

**Estado:** la pidió el tesista y la aprobó el 2026-10-25; registrada antes de calcular p99.9 en 2024. Calculada el 2026-10-25 (abajo).

**Por qué.**
- **Con 1 % de falsas alarmas, la precisión tiene un techo de ~0.44,** aunque el detector encuentre
  todos los ataques. Es por la proporción de estación-días atacadas (0.8 %).
- **Un umbral más estricto cambia recall por precisión.** La ilustración con 2022
  (`progreso.md`, 2026-10-25) lo muestra: con δ = 100 % y 0.1 %, L0 da recall 0.74 y precisión 0.81.
- **El punto de operación depende de cuántas falsas alarmas se toleren,** no de una métrica.
  Conviene reportar más de uno, y la curva.

**Qué se calcula** (sin entrenar; L0 y el V4 se cargan de disco, y R3 es aritmética):
- **Detectores:**
  - L0, el modelo definitivo de la revisión 14;
  - R3, recalculada como en la fase 2 de la revisión 12;
  - el V4 por estación-día, con la inferencia repetida como en la fase 2 de la revisión 11.
- **Puntos de operación,** con umbrales sacados de las estación-días de 2023 limpio:
  - **p99:** 1 % de falsas alarmas, el de siempre;
  - **p99.9:** 0.1 %.
- **Dónde se mide:**
  - L0 y R3 en las estación-días válidas para los dos, como el examen de la revisión 14;
  - el V4 en sus propias estación-días válidas, como en la revisión 11.
- **Métricas:** las de la revisión 9, cada una con su valor sin ataque, en los cinco δ. Se agregan:
  - cuántas estación-días de 2023 limpio quedan por encima del umbral;
  - la tasa de falsas alarmas que resulta en 2024 limpio.
- **Curva:** recall, precisión y tasa de falsas alarmas en 2024, con umbrales de 2023 limpio de 10,
  5, 2, 1, 0.5, 0.2, 0.1 y 0.05 %.
- **Controles:**
  - con p99, L0 y R3 deben reproducir el examen de la revisión 14, y el V4 la fase 2 de la
    revisión 11 (TP, FP, FN y TN iguales);
  - se corre dos veces y debe salir igual.
- **No se elige nada:** ni detector ni umbral. Lo que se reporta es la balanza.

**Límites declarados:**
- **El p99.9 se estima con ~10 estación-días de 2023 limpio,** así que la tasa real en otro año
  puede variar mucho. Con p99, la tasa fijada en 1 % salió de 1.3–2 % en 2024.
- **El número de 2024 es descriptivo,** porque ya se vio p99.9 en 2022 y p99 en 2024. El examen
  final de 2025–2026 llevará los dos umbrales congelados desde antes.

**Predicción de Claude, antes de calcularlo** (estación-días comunes de L0 y R3):
1. Con p99.9, la tasa de falsas alarmas en 2024 limpio queda por encima de 0.1 %, entre 0.1 y 0.4 %,
   para L0 y para R3.
2. Con δ = 100 % y p99.9, L0 tiene precisión entre 0.5 y 0.85, y recall entre 0.6 y 0.85.
3. Con δ = 100 %, la ventaja de recall de L0 sobre R3 es mayor con p99.9 que con p99, donde es de
   0.12.
4. Con δ = 50 % y p99.9, el recall de L0 queda por debajo de 0.35.
5. Con δ ≤ 20 % y p99.9, el recall de los tres detectores queda por debajo de 0.10.

**Implementación:**
- el script `experiments/anomalias_red/puntos_operacion_2024.py`, en la lap;
- salidas en `results/anomalias_red_v1/puntos_operacion_2024/`.

**Resultado (2026-10-25).**
- **Cómo se corrió:**
  - en la lap, dos veces, con salidas idénticas;
  - con 1 y 5 %, L0 y R3 reproducen el examen de la revisión 14, y el V4 la fase 2 de la revisión
    11;
  - el V4 se cargó de disco y reproduce sus predicciones de 2024 limpio;
  - L0 son los puntajes guardados de su modelo definitivo, recién entrenado en Colab (`rev14`).
- **Los umbrales:** con p99.9 quedan por encima 8 de las 8 802 estación-días de 2023 limpio (9 de
  9 097 en el V4). Con p99 quedan 88 (90 en el V4).

**Con δ = 100 %** (L0 y R3 en las estación-días comunes; el V4 en las suyas):

| Punto | Detector | TP | FP | FN | Recall | Precisión | F1 | F2 | Falsas alarmas en 2024 limpio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| p99 | L0 | 662 | 1 740 | 39 | 0.944 | 0.276 | 0.427 | 0.636 | 1.35 % |
| p99 | R3 | 579 | 1 444 | 122 | 0.826 | 0.286 | 0.425 | 0.600 | 1.33 % |
| p99 | V4 | 415 | 2 902 | 295 | 0.585 | 0.125 | 0.206 | 0.337 | 2.90 % |
| p99.9 | **L0** | 555 | 251 | 146 | **0.792** | 0.689 | **0.737** | **0.769** | 0.16 % |
| p99.9 | R3 | 392 | 97 | 309 | 0.559 | **0.802** | 0.659 | 0.595 | 0.03 % |
| p99.9 | V4 | 310 | 709 | 400 | 0.437 | 0.304 | 0.359 | 0.402 | 0.61 % |

**F1 con p99.9 en los demás δ** (L0, R3 y V4; entre paréntesis, el recall):
- **50 %:** 0.531 (0.41), 0.339 (0.22) y 0.157 (0.16). La precisión es de 0.75, 0.77 y 0.16.
- **20 %:** 0.044 (0.02), 0.027 (0.01) y 0.023 (0.02).
- **10 y 5 %:** de 0.000 a 0.017; nada.
- **Sin ataque:** de 0.000 a 0.014.

**La curva** (`curva.csv`, umbrales de 10 a 0.05 %):
- **Con 100 y 50 %, L0 queda por encima de R3 en casi todos los puntos:** más recall con la misma
  precisión.
  - Con precisión ~0.8 y δ = 100 %, L0 encuentra el 75 % de los ataques (umbral de 0.05 %) y R3 el
    56 % (0.1 %).
- **El V4 queda muy por debajo.**
  - En 2024 su tasa de falsas alarmas sale de 2.9 % con p99 y de 0.6 % con p99.9: casi el triple y
    el séxtuple de lo fijado.
  - Es lo que ya se vio en la revisión 11, con mayo de 2024 excepcional.

**Predicciones:** se cumplieron 3 de 5.
- **Falló la 1:** con p99.9, la tasa en 2024 limpio quedó por debajo de 0.1 % en R3 (0.03 %) y en
  L0 con 50 y 20 % (0.07 % y 0.06 %). Sólo L0 con 100 % cayó en el rango (0.16 %). El umbral es
  inestable, pero hacia los dos lados.
- **Se cumplió la 2:** con 100 % y p99.9, L0 tiene precisión 0.69 y recall 0.79.
- **Se cumplió la 3:** la ventaja de recall de L0 sobre R3 sube de 0.12 a 0.23.
- **Falló la 4:** con 50 %, el recall de L0 fue de 0.41, no menor de 0.35.
- **Se cumplió la 5:** con δ ≤ 20 % el recall queda por debajo de 0.03.

**Lectura:**
- con un umbral estricto, la ventaja de L0 sobre R3 se hace más grande, no más chica;
- en número de falsas alarmas, L0 con p99.9 da unas 25 al año en la red (251 en 10 calendarios),
  y R3 unas 10.
- **Es descriptivo:** el número que vale como prueba saldrá del examen final.
- **Detalle:** en `results/anomalias_red_v1/puntos_operacion_2024/` y `progreso.md` (2026-10-25).

### Revisión 16 (2026-10-25): tres comprobaciones antes del examen final

**Estado:** la pidió el tesista y la aprobó el 2026-10-25, con p99 y p99.9. Registrada antes de
correr nada. Corrida el 2026-10-25; resultado al final de esta sección.

**Común a las tres:**
- **Detectores y lugar de medición:**
  - L0: los modelos definitivos de la revisión 14, cargados de disco;
  - R3: recalculada como en la fase 2 de la revisión 12;
  - L0 y R3 se miden en las estación-días válidas para los dos;
  - el V4, cuando entra, en las suyas.
- **Umbrales:** p99 y p99.9, con las estación-días de 2023 limpio de cada detector, como en la
  revisión 15.
- **Métricas:** F1, recall y precisión, con su valor sin ataque.
- **Reproducibilidad:** todo corre dos veces en la lap y debe salir igual. No se entrena nada.

**(1) Intervalos de confianza de la diferencia L0 − R3 en 2024.**
- **Bootstrap por bloques.**
  - Un bloque es una estación en un mes, con sus 10 calendarios juntos: 31 × 12 = 372 bloques.
  - Así quedan juntos los días seguidos de un episodio, y los días normales que se repiten en los
    10 calendarios.
- **Cómo se calcula:**
  - 2 000 remuestreos con reemplazo, con la semilla `default_rng([42, 16, 1])`;
  - en cada uno se calculan el F1, el recall y la precisión de L0 y de R3, y su diferencia, con
    los umbrales fijos;
  - se reporta el intervalo del 2.5 al 97.5 %, para los cinco δ y los dos puntos.
- **Regla de lectura:** la diferencia se sostiene si su intervalo del 95 % no incluye el 0.
- **No cubre:**
  - la incertidumbre del umbral de 2023;
  - la semilla del entrenamiento: otra semilla requiere reentrenar.

**(2) Un solo modelo L0 para todos los δ.**
- **(2a) La elección, con 2022:**
  - cada modelo de selección (`lstm_local_examen/c20/d<m>/seleccion/modelo_seleccion.keras`,
    entrenado con 2020–2021) se examina con 2022 de los calendarios 01–10 y δ = 100, 50 y 20 %;
  - el umbral sale de 2022 limpio, en las estación-días comunes con R3, como en la elección de la
    revisión 14;
  - **el modelo único es el de mayor F1 con 1 % promediado entre esos tres δ.** Si dos empatan a
    menos de 0.005, gana el de mayor δ;
  - control: la diagonal reproduce los puntajes guardados de la selección.
- **(2b) El examen en 2024:**
  - cada modelo definitivo se examina con los calendarios de los cinco δ, una tabla de 5 × 5, con
    su propio umbral de 2023 limpio;
  - control: la diagonal reproduce el examen de la revisión 14.
- **Lo que decide:** sólo el modelo único que va al examen final, elegido en (2a). Los modelos por
  δ se reportan también.

**(3) Hora de inicio al azar: la prueba secundaria de la revisión 6.**
- **Calendarios:** los mismos 10 de 2024, con las mismas estaciones, signos y duraciones.
- **El recorrido:**
  - cada episodio se recorre una hora h entre 0 y 23;
  - hay **una h por calendario y estación**: la primera extracción de
    `default_rng([42, 2024, k, 2, índice de la estación])`;
  - todos los episodios de una estación se recorren igual, para que no se traslapen;
  - el episodio dura lo mismo en horas y se corta al final de 2024.
- **Etiqueta:**
  - una estación-día está **atacada si 12 horas o más** caen dentro de un episodio;
  - es **normal si ninguna**;
  - las que tienen de 1 a 11 horas se excluyen de las métricas, y se reporta cuántas son.
- **Detectores:**
  - L0, cada modelo con su δ;
  - el modelo único de (2a);
  - R3 y el V4;
  - todos con los umbrales de siempre, sin reentrenar.
- **Regla de lectura:** la ventaja de L0 no depende del inicio a medianoche si, con hora al azar y
  p99, L0 sigue por encima de R3 en F1 con δ = 50 y 20 %. Se reporta además cuánto baja cada uno.

**Predicción de Claude, antes de correrlas:**
1. Con p99, el intervalo de L0 − R3 excluye el 0 con δ = 50 y 20 %, y lo incluye con 100 %.
2. Con p99.9, el intervalo excluye el 0 con δ = 100 y 50 %.
3. Con p99 y δ = 50 %, el intervalo de L0 − R3 mide entre 0.02 y 0.08 de ancho.
4. El modelo único que sale de 2022 es el de δ = 100 o el de 50 %.
5. En 2024, con p99, el modelo único queda a menos de 0.03 del modelo de su propio δ, o por
   encima, con δ = 50 y 20 %.
6. En 2024, con p99 y δ = 50 %, el modelo único le gana a R3.
7. Con hora al azar, δ = 100 % y p99, los tres detectores bajan su F1.
8. Con hora al azar, p99 y δ = 50 %, L0 sigue por encima de R3.
9. Con hora al azar, δ = 100 % y p99, L0 baja menos de 0.10 de F1.

**Implementación:**
- **Funciones,** con sus pruebas:
  - `anomalias_red.recorrer_plan(plan, k)`;
  - `anomalias_red.aplicar_horas`, como `aplicar` pero sin exigir días completos.
- **Scripts:** `intervalos_2024.py`, `modelo_unico_delta.py` y `hora_azar_2024.py`.
- **Salidas:** en `results/anomalias_red_v1/comprobaciones_2024/`.

**Resultado (2026-10-25).**
- **Cómo se corrió:**
  - (1) en la lap; (2) y (3) en Colab (`rev16`, AMD EPYC 7B12; `correr_revision16.sh`);
  - todo dos veces, con salidas idénticas;
  - no se entrenó nada: L0 y el V4 se cargaron de disco;
  - (3) se detuvo dos veces por controles antes de correr completa:
    - faltaban los residuos guardados del V4, que no están en git;
    - el V4 en otra CPU difiere 7.6e-6 ppb de sus predicciones guardadas, así que se agregó
      `--tolerancia-v4` (1e-4 ppb).
- **(1) Intervalos del 95 % de L0 − R3 (F1):**
  - con p99: +0.002 (−0.049 a +0.052) con 100 %; +0.042 (−0.005 a +0.088) con 50 %; **+0.049
    (+0.014 a +0.091) con 20 %**;
  - con p99.9: **+0.078 (+0.005 a +0.141) con 100 %**; **+0.192 (+0.125 a +0.261) con 50 %**;
  - con 10 y 5 % no hay diferencias útiles. Con 5 % y p99, R3 queda por encima (−0.013, de −0.026 a
    −0.001), pero los dos están en el azar.
- **(2) Modelo único:**
  - **(2a) La elección con 2022:** F1 medio de 0.359 con el de 50 %, 0.346 con el de 100 %, 0.287 con
    el de 20 %, 0.172 con el de 10 % y 0.109 con el de 5 %. **El modelo único es el de δ = 50 %.**
  - **Controles:** la diagonal reproduce los conteos de la elección de la revisión 14 y de su examen
    2024, con una diferencia de puntajes de 1.1e-16.
  - **(2b) En 2024, F1 con p99 del L0 único:** 0.377, 0.388, 0.137, 0.030 y 0.023 con δ = 100, 50, 20,
    10 y 5 %. R3 da 0.425, 0.347, 0.109, 0.035 y 0.021.
  - **Con p99.9:** 0.637 y 0.531 con 100 y 50 %; R3, 0.659 y 0.339.
  - **El modelo de 100 % no generaliza hacia abajo en L0:** 0.077 con δ = 20 %, por debajo de R3. Con
    el LSTM de la revisión 8 había sido al revés.
- **(3) Hora de inicio al azar** (F1 con p99, medianoche → hora al azar):
  - **L0:** 0.427 → 0.433 con 100 %, 0.388 → 0.396 con 50 %, 0.158 → 0.162 con 20 %;
  - **R3:** 0.425 → 0.419, 0.347 → 0.329, 0.109 → 0.099;
  - **V4:** 0.206 → 0.195, 0.102 → 0.096, 0.029 → 0.028;
  - con p99.9, L0 queda igual (0.737 → 0.738, 0.531 → 0.530);
  - de las estación-días atacadas, 169 quedan con 1 a 11 horas y se excluyen;
  - **L0 no depende del inicio a medianoche.** Su ventaja sobre R3 se mantiene, y crece un poco.
- **Predicciones:** se cumplieron 6 de 9.
  - Falló la 1: con p99 y 50 %, el intervalo incluye el 0 por 0.005.
  - Falló la 3: ese intervalo mide 0.093, no menos de 0.08.
  - Falló la 7: con hora al azar L0 no bajó, subió 0.006.
- **Lo que cambia para el examen final:** nada. El modelo único (δ = 50 %) y la hora al azar ya
  estaban en su borrador.
- **Detalle:** en `results/anomalias_red_v1/comprobaciones_2024/` y `progreso.md` (2026-10-25).

### Revisión 17 (2026-10-25): examen final con 2025 y 2026

**Estado:**
- borrador de Claude, a pedido del tesista;
- **aprobada por el tesista el 2026-10-25** («Sí, apruebo»), después de ver las comprobaciones (2) y
  (3) de la revisión 16 y con las 9 predicciones ya escritas;
- **por decisión del tesista se corre antes de la revisión con el asesor** del lunes 2026-10-26.
  - Sus razones: llegar con resultados fijos. P4 no aplica, porque la parte 2 es otra pregunta:
    detección supervisada de anomalías a nivel de red, no detección de bit flipping a nivel de nodo.
  - Los dos puntos de operación bastan.
- Hasta que se apruebe, no se genera nada de 2025–2026 para la parte 2.

**Por qué una sola vez:**
- 2022 y 2024 ya se usaron para elegir y para diseñar;
- 2025–2026 es el único periodo que la parte 2 no ha visto;
- lo que aquí no quede fijado antes de correr, no puede cambiarse después.

**Lo que se congela:**
- **Detectores,** todos cargados de disco o sin entrenamiento; sus SHA-256 se registran antes de
  correr:
  - **L0 por δ:** los 5 `modelo.keras` de `results/anomalias_red_v1/lstm_local_examen/c20/`
    (revisión 14). Es la comparación principal, la misma del examen 2024;
  - **L0 único:** el modelo que eligió la regla de la revisión 16 con 2022, para todos los δ. Es el
    caso realista, cuando no se sabe el tamaño del ataque;
  - **R3**, como en la fase 2 de la revisión 12;
  - **el V4**, con la inferencia repetida, como en la revisión 11.
- **Umbrales:**
  - p99 y p99.9, con las estación-días de 2023 limpio de cada detector;
  - L0 y R3 en las estación-días válidas para los dos;
  - son exactamente los del examen 2024, y se comprueba.
- **Contexto de las entradas:**
  - para 2025, la historia limpia de 2020 a 2024;
  - para 2026, la de 2020 a 2025;
  - lo mismo para R3 y para el perfil de 14 días.

**Los datos nuevos:**
- **Calendarios:** 10 por año, `final_2025_01…10` y `final_2026_01…10`.
  - El mismo generador y las mismas reglas que los de 2024: los 31 objetivos, p uniforme en
    0.10–0.30 % por día y episodios de 1 a 7 días desde las 00 h, cortados al final del periodo.
  - Las semillas salen de 42 y del año, sin `hash()`: `[42, año, k, uso, estación]`.
- **Matrices:** los 5 δ, más 2025 limpio y 2026 limpio.
- **Hora de inicio al azar:**
  - la misma versión recorrida de cada calendario, con `recorrer_plan` (una h por calendario y
    estación);
  - la etiqueta de la revisión 16: 12 horas o más es atacada, ninguna es normal, y en medio se
    excluye.

**Qué se reporta, por año** (2025 y 2026 por separado, y los dos juntos como contraste):
- **Principal:** el F1 con p99 y con p99.9 de L0 por δ contra R3, en las estación-días comunes,
  con el intervalo del 95 % de la diferencia.
  - El bootstrap es por bloques de estación × mes, con 2 000 remuestreos y la semilla
    `[42, 17, año]`.
- **Secundario:**
  - el L0 único contra R3;
  - el V4;
  - la versión con hora al azar;
  - el recall, la precisión, el F2, el MCC, el PR-AUC y las falsas alarmas por grupo y por año;
  - cada métrica con su valor sin ataque (el año limpio).
- **No se elige nada.** No hay margen ni paso de selección: es la medición final.

**Controles:**
- se corre dos veces, y debe salir igual;
- los umbrales son idénticos a los del examen 2024;
- los SHA-256 de los modelos son los registrados;
- los planes y las matrices se generan dos veces y deben salir iguales;
- la inferencia del V4 en el año limpio sale de sus mismos modelos de la parte 1.
  - Si corre en otra máquina, el control contra sus predicciones guardadas usa una tolerancia de
    1e-4 ppb en lugar de 1e-9: la inferencia float32 difiere ~1e-5 ppb entre CPUs (revisión 16).

**Límites declarados:**
- **2026 sólo tiene enero a julio.**
- **La parte 1 ya evaluó al V4 con 2025–2026** (bit flipping), así que el año limpio no es nuevo
  para el V4. Sí lo es para L0 y para R3, y ningún ataque de la parte 2 se ha generado en esos
  años.
- **Los umbrales de 2023 pueden desviarse** dos y tres años después. Eso es parte de lo que se mide.
- **Una sola semilla de L0.**

**Predicción de Claude, antes de generar nada de 2025–2026** (escrita después de las comprobaciones
(2) y (3) de la revisión 16; F1, estación-días comunes salvo el V4):
1. En 2025, con p99, L0 por δ le gana a R3 con δ = 50 y 20 %.
2. En 2025, con p99 y δ = 100 %, L0 y R3 quedan a menos de 0.05 entre sí.
3. Con p99.9 y los dos años juntos, L0 le gana a R3 con δ = 100 y 50 %, y el intervalo del 95 % de
   la diferencia excluye el 0 con δ = 50 %.
4. Con δ ≤ 10 %, los cuatro detectores quedan por debajo de 0.10 en los dos años.
5. En 2025 limpio, con p99, la tasa real de falsas alarmas de L0 y de R3 queda entre 0.8 y 2.0 %.
6. Con p99 y δ ≥ 20 %, el V4 tiene el F1 más bajo de los cuatro en 2025.
7. En 2025, con p99 y δ = 50 %, el L0 único le gana a R3.
8. En 2025, con p99 y δ = 50 %, el F1 de L0 con hora al azar cambia menos de 0.03 frente al de
   medianoche.
9. En 2026 (enero a julio), con p99 y δ = 50 %, el orden es L0 > R3 > V4, como en 2025.

**Implementación (2026-10-25, antes de generar nada de 2025–2026):**
- **Código:**
  - `anomalias_red.corridas_finales()`: `final_2025_01…10` y `final_2026_01…10`, con p de
    `[42, año, k, 0]`;
  - `evaluar_v4.residuos(..., etapa)`, con `prueba_2025` y `prueba_2026_parcial` (las etapas del V4);
  - la opción `--final` de `generar_planes.py` y `generar_matrices.py` (`limpia_2025`, `limpia_2026`
    y 100 matrices);
  - `examen_final.py`; con `--solo-generar` hace las 100 matrices de hora al azar.
- **Detectores congelados:** los SHA-256 de los 5 `modelo.keras` de L0 quedan en
  `results/anomalias_red_v1/examen_final_modelos_congelados.json`.
  - El script se detiene si no coinciden.
  - El V4 se verifica contra los SHA-256 de su `configuracion.json`.
  - SHA-256 de L0:
    - d100: `9a2ec7c9…`
    - d50: `cfbdf84f…`
    - d20: `f7f25190…`
    - d10: `3e0ec801…`
    - d5: `dec9ca56…`
- **Detalles fijados al programarlo:**
  - L0 por δ usa, para cada δ, su propio modelo; el L0 único usa el de δ = 50 % con todos los δ;
  - los umbrales de L0, L0 único y R3 salen de las estación-días de 2023 limpio válidas para L0 y R3;
    los del V4, de las suyas;
  - el bootstrap de los dos años juntos usa bloques estación × mes de cada año y la semilla
    `[42, 17, 0]`;
  - las falsas alarmas por grupo se reportan para L0, L0 único y R3.
  - la curva de recall y precisión con los umbrales de 2023 de 10 a 0.05 % (como la revisión 15), con
    inicio a medianoche, para la gráfica G2.
- **Prueba del código:**
  - el modo `--prueba` corre todo con 2024, 1 calendario y δ = 100 %, en la lap, sin tocar 2025–2026;
  - los SHA-256 coinciden;
  - los umbrales igualan a los del examen 2024 (diferencia relativa 4.8e-8, por la inferencia en otra
    máquina);
  - el V4 reproduce sus predicciones de 2024 (1.4e-14 ppb).
- **Dónde:** en Colab, en la misma sesión `rev16` (AMD EPYC 7B12), con `correr_revision17.sh`:
  1. los planes y las matrices de 2025–2026;
  2. las matrices de hora al azar, dos veces, la segunda sólo comprueba;
  3. dos corridas del examen en paralelo, con `--tolerancia-v4 1e-4`, que deben salir idénticas.
- **Salidas:** en `results/anomalias_red_v1/examen_final/`.

**Resultado del examen final (2026-10-25).**
- **Cómo se corrió:**
  - en Colab, sesión `rev16` (AMD EPYC 7B12), de 22:17 a 23:57 UTC, con `correr_revision17.sh`;
  - las dos corridas salieron idénticas en los seis archivos de resultados;
  - las 100 matrices de hora al azar se generaron dos veces, iguales;
  - los SHA-256 de los 5 modelos L0 coinciden con los registrados;
  - los umbrales son los del examen 2024 (diferencia relativa 4.2e-15);
  - el V4 reproduce sus predicciones de 2025 y 2026 a 7.6e-6 ppb, dentro de la tolerancia de 1e-4;
  - los resultados se descargaron con el SHA-256 verificado (`623a3487…`);
  - no se entrenó nada.
- **F1 por estación-día, L0 / R3 / V4** (L0 y R3 en las estación-días comunes; el V4 en las suyas):

  | Año | Umbral | δ = 100 % | δ = 50 % | δ = 20 % | δ = 10 % | δ = 5 % |
  |---|---|---|---|---|---|---|
  | 2025 | p99 | 0.457 / 0.475 / 0.177 | **0.445** / 0.391 / 0.106 | **0.249** / 0.120 / 0.032 | 0.070 / 0.026 / 0.016 | 0.011 / 0.014 / 0.011 |
  | 2025 | p99.9 | **0.756** / 0.632 / 0.329 | **0.573** / 0.364 / 0.153 | **0.087** / 0.019 / 0.024 | 0.009 / 0.000 / 0.008 | 0.005 / 0.000 / 0.007 |
  | 2026 | p99 | 0.540 / 0.476 / 0.315 | **0.502** / 0.390 / 0.199 | **0.242** / 0.092 / 0.062 | 0.045 / 0.020 / 0.031 | 0.014 / 0.010 / 0.019 |
  | 2026 | p99.9 | **0.821** / 0.647 / 0.471 | **0.561** / 0.300 / 0.264 | **0.054** / 0.005 / 0.035 | 0.005 / 0.000 / 0.016 | 0.000 / 0.000 / 0.008 |

  - Sin ataque, el F1 queda entre 0.000 y 0.016.
  - En negritas, donde el intervalo del 95 % de L0 − R3 excluye el 0 con los dos años juntos.
- **Intervalos de L0 − R3, con los dos años juntos:**
  - **p99:** +0.012 (−0.037 a +0.061) con 100 %, un empate; **+0.075 (+0.027 a +0.129)** con 50 %;
    **+0.138 (+0.096 a +0.181)** con 20 %;
  - **p99.9:** **+0.143 (+0.086 a +0.201)** con 100 %; **+0.228 (+0.176 a +0.279)** con 50 %;
    **+0.060 (+0.034 a +0.089)** con 20 %;
  - por año, con p99 y 50 %: +0.054 (−0.008 a +0.118) en 2025 y +0.112 (+0.035 a +0.195) en 2026.
- **L0 único** (δ = 50 %, para cualquier tamaño):
  - con p99, F1 de 0.404, 0.445 y 0.176 en 2025 con δ = 100, 50 y 20 %;
  - contra R3 con los dos años juntos: −0.054 (−0.098 a −0.009) con 100 %, +0.075 con 50 % y
    **+0.086 (+0.052 a +0.123)** con 20 %;
  - es decir, pierde un poco con los ataques grandes y gana con los medianos.
- **Recall y precisión con p99, 2025** (L0 / R3 / V4):
  - con 100 %, recall 0.94 / 0.84 / 0.57 y precisión 0.30 / 0.33 / 0.10;
  - con 50 %, 0.82 / 0.60 / 0.31 y 0.30 / 0.29 / 0.06;
  - con 20 %, 0.29 / 0.15 / 0.09 y 0.22 / 0.10 / 0.02.
- **Falsas alarmas reales en el año limpio** (L0 / R3 / V4):
  - 2025: 1.04 / 0.95 / 3.36 % con p99 y 0.16 / 0.09 / 0.87 % con p99.9;
  - 2026: 0.87 / 1.18 / 1.48 % con p99 y 0.10 / 0.04 / 0.18 % con p99.9.
- **Hora de inicio al azar** (F1 con p99, medianoche → hora al azar, 2025):
  - L0: 0.457 → 0.475, 0.445 → 0.459 y 0.249 → 0.254;
  - R3: 0.475 → 0.463, 0.391 → 0.381 y 0.120 → 0.112;
  - en 2026, igual: L0 cambia de −0.025 a +0.017.
- **Predicciones:** se cumplieron las 9.
- **Lectura:**
  - en los dos años nuevos, L0 le gana a R3 con δ = 50 y 20 % con los dos umbrales, y con 100 %
    con p99.9;
  - con 100 % y p99 empatan;
  - con 20 % la ventaja es más clara que en 2024 (0.249 contra 0.120 en 2025);
  - con 10 y 5 % ninguno sirve;
  - el V4 queda último, y su umbral de 2023 se desvía a 3.4 % en 2025.
- **Detalle:** en `results/anomalias_red_v1/examen_final/`, `logs_revision17/` y `progreso.md`
  (2026-10-25).

### Revisión 18 (2026-10-26): comparación justa con el V4

**Estado:**
- borrador de Claude, a pedido del tesista, después de la junta con el asesor del 2026-10-26;
- **aprobado por el tesista el 2026-10-27**, antes de programar o entrenar nada:
  - entrenar sólo δ = 50 %, como modelo único: aprobado;
  - un modelo por estación, como el V4: aprobado;
  - cambio del tesista en (c): la gráfica no lleva al V4, sino al V4S;
- **regla del tesista para todo lo que sale de la junta («peras con peras»):**
  - cada comparación pone frente a frente detectores del mismo tipo: supervisado contra
    supervisado, el mismo modelo único contra modelo único, en el mismo escenario, con los mismos
    calendarios y las mismas estación-días;
  - lo que no sea del mismo tipo puede ir en una tabla como referencia, nunca como la
    comparación principal;
- es el paso 1 del plan del tesista tras la junta:
  1. el V4 ajustado (esta revisión);
  2. lo que no entrena: renombrar L0, retirar la gráfica contra el bit flipping y registrar la junta;
  3. una sola estación atacada a la vez;
  4. PARAAD;
  5. error fijo en ppb;
  6. TINTO.

  Los pasos 3 a 6 tendrán su propia revisión antes de programarse.

**Por qué:**
- **Supervisado contra no supervisado:** L0 aprende con etiquetas y el V4 nunca las vio (§4.1 de
  su protocolo). Parte de la ventaja de L0 puede venir sólo de eso.
- **La gráfica contra la parte 1 no es justa:** compara una lectura con un día, un instante con un
  ataque sostenido y un cambio fijo de ±2^k ppb con uno proporcional. El promedio en ppb esconde
  la forma: con +100 %, 50 ppb pasa a 100, pero 2 ppb pasa a 4.
- **Días distintos:** en el examen final, el V4 se calificó en sus propias estación-días válidas
  (88 220 en 2025 con δ = 50 %, 651 atacadas) y L0 y R3 en las comunes (86 330, 634 atacadas).

**(a) El V4 en los mismos días:**
- se califica en las estación-días válidas para los cuatro detectores (L0, R3, V4 y V4S);
- los umbrales p99 y p99.9 salen de 2023 limpio en esas mismas estación-días;
- no entrena ni carga nada nuevo: el V4 sigue cargado de disco, con la inferencia repetida.

**(b) El V4 supervisado (V4S):**
- **Entradas (24 × 68):**
  - las 66 del V4: las otras 32 estaciones normalizadas con la μ y la σ del V4, sus máscaras, y el
    seno y el coseno de la hora; XAL sigue inactivo;
  - con las filas t−23…t (la variante `incluir_t=True` que ya existe), porque se juzga la hora t;
  - más 2 columnas de la estación objetivo: (lectura − base) / σ, con la base del V4 (perfil causal
    de 14 días con media), y su máscara;
  - el V4 nunca ve la lectura de su estación, porque es un pronosticador. Un clasificador sin esas
    2 columnas no podría ver el ataque.
- **Salida:** una probabilidad (sigmoide), con entropía cruzada binaria y sin pesos de clase.
- **Lo que no cambia del V4:**
  - LSTM de 64, dropout de 0.2 y densa de 32;
  - Adam con 1e-3, lotes de 64 y barajado;
  - **un modelo por estación** (31);
  - sólo las horas en que la estación tiene dato y base.
- **Lo que no cambia de L0:**
  - los mismos 20 calendarios de 2020–2022;
  - la misma etiqueta por estación-hora, que nunca es entrada;
  - 1 de cada 8 horas por calendario y estación, con semilla `[42, 18, uso, calendario, estación]`;
  - selección con 2020–2021 y EarlyStopping sobre 2022 de los calendarios 01–10 (paciencia 8,
    máximo 60 épocas, pesos de la mejor);
  - definitivo con 2020–2022 y exactamente E épocas, la E de cada estación;
  - `fijar_semilla(42)` inmediatamente antes de construir cada modelo.
- **Sólo δ = 50 %:** un modelo único para los cinco δ, como el L0 único de la revisión 16. Se compara
  contra el L0 único. Cuesta la quinta parte que un modelo por δ.
- **El día:** promedio de las probabilidades de las horas válidas (mínimo 12), sin dominancia, como
  L0.
- **Desventaja declarada antes de entrenar:**
  - cada modelo del V4S ve sólo las ventanas de su estación;
  - L0, al ser compartido, ve las de las 31, con unas 31 veces más ejemplos atacados;
  - si el V4S pierde, ésta es una causa posible y no se podrá separar de las entradas.

**(c) La gráfica («peras con peras»):**
- recall y F1 por δ del **V4S contra el L0 único**, con p99 y p99.9: los dos supervisados, los dos
  un modelo único entrenado con δ = 50 %, con los mismos calendarios y las mismas etiquetas;
- en las estación-días comunes de 2025, con 2026 como complemento;
- el V4 y R3 no van en la gráfica: quedan como referencia en la tabla de (a);
- la comparación descriptiva con la parte 1 por ppb (`comparacion_parte1_*.csv`) se conserva en
  disco, pero deja de presentarse como comparación.

**Evaluación:**
- 2024 (los 10 calendarios) y el examen final 2025–2026 (los 20), con los detectores congelados;
- **regla para volver a usar 2025–2026:**
  - sólo para detectores registrados aquí antes de entrenarse, diseñados sin mirar 2024–2026;
  - se evalúan **una sola vez**;
  - los números de L0, R3 y V4 de la revisión 17 no se modifican: (a) y (c) son tablas nuevas;
  - en la tesis se declara que el V4S y la tabla común se agregaron después de la junta del
    2026-10-26.
- Las métricas, el bootstrap y las falsas alarmas por grupo, como en la revisión 17.

**Controles:**
- se entrena dos veces el V4S de la primera estación (la selección), y los pesos deben salir iguales;
- la evaluación se corre dos veces, y debe salir igual;
- el V4 en sus propias estación-días debe reproducir la revisión 17.

**Predicciones (Claude), escritas antes de entrenar:**
1. el F1 del V4 en las estación-días comunes cambia menos de 0.02 respecto a la revisión 17;
2. con δ = 50 % y p99 en 2025, el V4S le gana al V4 en F1;
3. con δ = 50 % y p99 en 2025, el L0 único le gana al V4S en F1.

### Revisión 18b (2026-10-27): V4S compartido

**Estado:**
- borrador de Claude a pedido del tesista;
- **aprobada por el tesista el 2026-10-27** («Va. Hazlo»), antes de programar o de entrenar el V4S
  compartido;
- ningún V4S se ha evaluado en 2023–2026.

**Por qué:**
- **Lo que mostró 2022.** El V4S por estación de la revisión 18 se entrenó en Colab. La comprobación
  de funcionamiento con 2022, que no elige nada, mostró que:
  - 11 de 31 modelos eligieron E = 1 y no aprendieron: su ROC-AUC por hora promedia 0.505;
  - por estación-día, el V4S tiene ROC-AUC de 0.648 y L0 de 0.976.
- **No es un error del código.** Los modelos que entrenaron varias épocas sí separan, de 0.77 a
  0.82.
- **Es la desventaja declarada antes de entrenar:** cada modelo ve sólo unas 300 ventanas
  atacadas de su estación. L0 ve 31 veces más.
- **Por qué no es truqueado:**
  - la causa se escribió antes de entrenar y 2022 sólo la confirmó;
  - no se ha visto 2024–2026 para ningún V4S;
  - el cambio **fortalece al rival** de L0;
  - **no hay elección:** los dos V4S van al examen y se reportan los dos;
  - la comparación principal se fija ahora por el principio «peras con peras»: el V4S compartido
    entrena como L0. No depende de ningún resultado.
- **Por qué el V4 de la parte 1 era por estación:**
  - era un pronosticador sin etiquetas, que aprendía con todas las horas normales (unas 14 000 por
    estación), así que no le faltaban datos;
  - la escasez aparece sólo al supervisar, con ataques en el 0.8 % de las horas.

**Qué es el V4S compartido:**
- **Entradas (24 × 68):** las mismas del V4S por estación, pero con las otras 32 estaciones (sus
  valores y sus máscaras) **ordenadas por distancia** al objetivo. La primera es la más cercana,
  con empates por clave (`vecinas.vecinas_cercanas` con k = 32). XAL, inactiva, queda en su lugar
  por distancia y siempre vale 0. Al final van el seno, el coseno y las 2 columnas del objetivo.
- **Un solo modelo para las 31 estaciones,** sin identificador de estación, como L0.
- **Las mismas ventanas que el V4S por estación:** la misma muestra de 1 de cada 8 horas por
  calendario y estación, con la misma semilla, juntadas para las 31.
- **Todo lo demás, idéntico al V4S por estación:**
  - arquitectura, salida sigmoide y pérdida;
  - normalización inicial en la selección y definitiva en el modelo final;
  - EarlyStopping con 2022 de los calendarios 01–10;
  - E épocas en el definitivo;
  - sólo δ = 50 %;
  - el día con el promedio de las horas válidas.

**Evaluación** (la de la revisión 18, con cinco detectores):
- L0 único, V4S compartido, V4S por estación, R3 y V4, en las estación-días válidas para los
  cinco;
- **principal:** L0 único − V4S compartido;
- **contraste:** L0 único − V4S por estación;
- intervalos por bootstrap como en la revisión 18;
- la gráfica de (c) lleva al L0 único y al V4S compartido.

**Controles:**
- el V4S compartido se entrena **dos veces completo** (selección y definitivo), en paralelo, y
  los pesos deben salir iguales;
- la comprobación de funcionamiento con 2022 se repite para el compartido, también sin elegir
  nada.

**Predicciones (Claude), escritas antes de entrenar el compartido:**
4. en 2022 (comprobación), el V4S compartido tiene un ROC-AUC por estación-día mayor que el del
   V4S por estación (0.648);
5. con δ = 50 % y p99 en 2025, el V4S compartido le gana en F1 al V4S por estación y al V4;
6. con δ = 50 % y p99 en 2025, el L0 único le gana en F1 al V4S compartido.

**Resultado de las revisiones 18 y 18b** (2026-10-27; examen del V4S corrido una sola vez):
- **Origen de los modelos:**
  - V4S por estación y V4S compartido **recién entrenados** en Colab y luego cargados de disco
    para evaluar;
  - L0 único y V4 cargados de disco; R3 sin entrenamiento.
- **Controles:**
  - las dos corridas de la evaluación salieron idénticas en todos los archivos;
  - en sus propias estación-días, L0 único, R3 y V4 reproducen la revisión 17 (TP, FP, FN y TN);
  - los umbrales de 2023 son los de la revisión 17;
  - el V4S compartido entrenado dos veces da los mismos pesos.
- **Mismas estación-días:** son las de L0 y R3, que ya estaban dentro de las del V4. Los números de
  L0 único y R3 son los de la revisión 17; el F1 del V4 cambia como mucho 0.012.
- **F1 en 2025 con δ = 100 / 50 / 20 %** (L0 único / V4S compartido / V4S por estación / V4):
  - p99: 0.404 / 0.295 / 0.126 / 0.176; 0.445 / 0.179 / 0.032 / 0.108; 0.176 / 0.036 / 0.007 / 0.033;
  - p99.9: 0.588 / 0.325 / 0.049 / 0.339; 0.573 / 0.111 / 0.000 / 0.157; 0.074 / 0.021 / 0.000 / 0.024.
- **Principal, L0 único − V4S compartido, con 2025 y 2026 juntos** (intervalo del 95 %):
  - p99: **+0.069** (+0.014 a +0.128) con 100 %; **+0.241** (+0.183 a +0.302) con 50 %;
    **+0.153** (+0.112 a +0.197) con 20 %;
  - p99.9: **+0.246** (+0.189 a +0.303); **+0.454** (+0.397 a +0.511); **+0.062** (+0.033 a +0.092);
  - con 10 y 5 % nadie supera el azar; el F1 sin ataque llega hasta 0.016;
  - por año, la única excepción es 2026 con 100 % y p99: el V4S compartido tiene 0.502 y L0 0.452.
    La diferencia es −0.050, con intervalo de −0.133 a +0.040, es decir, empate.
- **V4S compartido contra V4:** la supervisión con las entradas del V4 casi no mejora el orden de
  los puntajes. Con 2025 y δ = 100 / 50 / 20 %:
  - PR-AUC: 0.355 / 0.110 / 0.015 del V4S compartido contra 0.387 / 0.095 / 0.012 del V4;
  - con p99 gana el V4S compartido, sobre todo por la precisión, porque su umbral de 2023 se
    sostiene mejor: falsas alarmas reales de 1.6 % contra 3.4 % del V4 en 2025;
  - con p99.9 detecta menos que el V4: recall de 0.080 contra 0.180 con 50 %.
- **Predicciones:** se cumplen 5 de 6. Falla la 2: el V4S por estación no le gana al V4 (0.032
  contra 0.108).
- **Lectura:**
  - L0 le gana al V4 supervisado entrenado exactamente igual, con los mismos calendarios,
    etiquetas, ventanas y modelo único;
  - la ventaja de L0 no viene principalmente de la supervisión, sino de sus entradas: la lectura
    contra su perfil de 14 días y la comparación con sus 4 vecinas, que son los ingredientes de R3;
  - **hipótesis, no comprobada:** con valores absolutos de 32 estaciones, el V4S memoriza los
    calendarios de entrenamiento (E = 3) en lugar del patrón relativo.
- **Detalle:** en `results/anomalias_red_v1/revision18/`, `logs_revision18/` y `progreso.md`
  (2026-10-27).

### Revisión 19 (2026-10-27): escenarios de una sola estación

**Estado:**
- borrador de Claude a pedido del tesista;
- **aprobada por el tesista el 2026-10-27**, antes de programar o generar nada:
  - «hacer ambas»: la lectura A y la B;
  - en A, entre 1 y 2 % por día para el nodo comprometido;
  - los episodios siguen sorteándose al azar con semillas fijas.

**Por qué:**
- el asesor pidió un escalón de complejidad: primero una sola estación atacada; luego el escenario
  actual, con estaciones al azar e independientes; y al final, ataques coordinados;
- **el escenario actual no es de una sola estación:**
  - en 2024, el 26 % de las estación-días atacadas tiene otra estación atacada ese día, y el 4.6 %
    una de sus 4 vecinas;
  - en 2025–2026, el 25 % y el 5.1 %;
  - hay hasta 4 estaciones atacadas a la vez;
- **«una sola estación» admite dos lecturas** y se hacen las dos.

**(B) Una a la vez: pareado con los calendarios de prueba:**
- **Calendarios:** `prueba_2024_01…10`, `final_2025_01…10` y `final_2026_01…10`.
- **Regla, sin azar:**
  - los episodios se recorren por fecha de inicio, con los empates por el orden de la matriz fija;
  - se conserva un episodio si no comparte ningún día con uno ya conservado, en cualquier estación;
  - los demás se quitan.
- **Resultado:** a lo más una estación alterada en toda la red en cada día. Los días de los episodios
  quitados quedan como días normales.
- **Plan y matrices:** `plan_unavez_<corrida>.csv` y `matriz_unavez_<corrida>_d<δ>`.
- **Control:**
  - en las horas de los episodios conservados, la matriz es idéntica a la del calendario original;
  - en el resto, idéntica al año limpio.
- **Medida principal, pareada:** el recall en las estación-días de los episodios conservados, en el
  escenario original (puntajes de la revisión 18, que ya están calculados) contra este.
- **También:**
  - las falsas alarmas en las estación-días normales en los dos escenarios, por grupo;
  - las métricas completas con su valor sin ataque;
  - el intervalo de L0 único − V4S compartido.
- **Cautela:** quitar episodios baja la proporción de días atacados, y con ella la precisión y el F1,
  aunque el detector sea igual de bueno. Por eso la medida principal es el recall pareado.

**(A) Un solo nodo comprometido: calendarios nuevos:**
- **Calendarios:** uno por estación objetivo y por periodo (2024, 2025 y enero–julio de 2026), `nodo_<año>_<estación>`.
  Son 31 por periodo y 93 en total.
- **En cada uno, sólo esa estación se altera.**
- **La tasa, mayor que la actual para que haya qué medir:**
  - p uniforme entre 1.0 y 2.0 % por día, sorteada por calendario;
  - da unos 4 a 7 episodios por año, unos 150 a 200 en las 31 estaciones;
  - la actual es de 0.10 a 0.30 %: con ella, un nodo tendría menos de un episodio al año.
- **Todo lo demás, como hoy (`plan_episodios`):** episodios de 1 a 7 días desde las 00 h, signo +
  o − al 50 %, cortados al final del periodo, y los cinco δ con el mismo plan.
- **Semillas:**
  - la tasa, `clave(42, inicio, 100 + j, USO_TASA)`;
  - los episodios, `plan_episodios(..., numero = 100 + j)`;
  - j es la posición de la estación en los 31 objetivos;
  - los números 101 a 131 no los usa ningún otro calendario.
- **Matrices:** `matriz_nodo_<año>_<estación>_d<δ>`.
- **No es pareado** con el escenario actual.
- **La proporción de días atacados es muy distinta:** muchos en una estación y ninguno en las demás.
  El recall se compara; la precisión y el F1, sólo dentro de A.

**Lo común:**
- **Detectores congelados, sin entrenar:**
  - principal («peras con peras»): **L0 único contra V4S compartido**;
  - referencias: R3 y V4;
  - el V4S por estación no entra, porque no aprendió (revisión 18b).
- **Igual que en la revisión 18:** los umbrales p99 y p99.9 de 2023 limpio, las estación-días válidas
  para los cuatro, la historia limpia anterior a cada año, los cinco δ y el promedio del día.
- **2025–2026, con la regla de la revisión 18:** registrado antes y evaluado una sola vez.
- **Intervalos:** L0 único − V4S compartido por bootstrap de bloques estación × mes, 2 000
  remuestreos, semilla `[42, 19, año]`. Igual para la diferencia pareada de recall en B.
- **Controles:**
  - los planes y las matrices se generan dos veces y deben salir iguales;
  - la evaluación se corre dos veces;
  - en B se comprueban las matrices contra las originales.

**Predicciones (Claude), escritas antes de generar nada:**
1. B conserva entre el 65 y el 85 % de las estación-días atacadas.
2. B, δ = 50 %, p99: el recall pareado de L0 único y de R3 cambia menos de 0.03.
3. B: el recall pareado del V4S compartido y del V4 cambia más, en valor absoluto, que el de L0
   único.
4. B: bajan las falsas alarmas en las estación-días normales en los dos escenarios, sobre todo las
   de contagio.
5. B y A, δ = 50 %, p99, 2025: L0 único le gana en F1 al V4S compartido.
6. A, δ = 50 %, p99, 2025: el recall de L0 único queda a menos de 0.05 de su recall en B.

**Resultado de la revisión 19** (2026-10-27 y 2026-10-28; 2025–2026 usado una sola vez para estos
escenarios):
- **Origen:** todos los detectores cargados de disco (L0 único, V4S compartido y V4) o sin
  entrenamiento (R3). No se entrenó nada.
- **Controles:**
  - en cada año, las dos corridas idénticas;
  - umbrales y puntajes del año limpio iguales a los de la revisión 18 (diferencia ≤ 8 × 10⁻¹⁶);
  - todo en Colab con AMD EPYC 7B12. Un intento de 2026 en Intel Xeon se detuvo solo, porque sus
    puntajes diferían en 3.5 × 10⁻⁸, y se repitió en AMD.
- **Generación:**
  - B conserva el 81.2, 80.3 y 79.4 % de las estación-días atacadas (2024, 2025 y 2026);
  - A tiene 143, 166 y 89 episodios, y en 2026 dos nodos (FAR y VIF) no sacaron ninguno.
- **(B) Pareado, la medida principal:**
  - en los mismos episodios, quitar los ataques simultáneos cambia el recall como mucho 0.026, en
    todos los detectores, δ y umbrales;
  - con δ = 50 % y p99, L0 único pasa de 0.806 a 0.816, de 0.845 a 0.845 y de 0.862 a 0.882;
  - R3, de 0.594 a 0.601, de 0.635 a 0.635 y de 0.626 a 0.646;
  - el V4S compartido y el V4 cambian 0.007 o menos.
- **(B) Falsas alarmas en las estación-días normales en los dos escenarios:**
  - bajan poco, sobre todo tras el ataque propio: L0 en 2025 pasa de 14.5 a 12.5 % en esos días;
  - el total con δ = 50 % y p99 baja de 1.82 / 1.39 / 1.31 % a 1.76 / 1.33 / 1.21 % para L0 único.
- **(A) Un solo nodo:**
  - recall de L0 único con δ = 50 % y p99: 0.776, 0.872 y 0.873, contra 0.816, 0.845 y 0.882 en B;
  - el F1 es menor que en B por la menor proporción de días atacados, como se declaró.
- **L0 único − V4S compartido (F1, δ = 100, 50 y 20 %, dos umbrales, tres años):**
  - L0 único va arriba en 34 de 36 combinaciones; el intervalo excluye el 0 en 32;
  - empates: B 2024 con 100 % y p99 (+0.024), B 2026 con 100 % y p99 (−0.060, el V4S compartido
    arriba), A 2024 con 20 % y p99.9, y A 2026 con 50 % y p99 (+0.038).
- **Como en la revisión 17:** con δ = 100 % y p99, R3 tiene más F1 que L0 único en varios años y
  escenarios.
- **Predicciones:**
  - se cumplen la 1, la 2, la 5 y la 6;
  - falla la 3: el V4S compartido y el V4 cambian todavía menos que L0;
  - la 4 se cumple a medias: bajan las falsas alarmas, pero sobre todo tras el ataque propio, no
    por contagio.
- **Lectura:**
  - el escenario actual ya era, en la práctica, «una estación a la vez» para los detectores, y los
    resultados de las revisiones 17 y 18 no cambian;
  - un solo nodo comprometido se detecta con el mismo recall;
  - L0 sigue por encima del V4S compartido;
  - queda para después el escalón difícil: ataques coordinados a estaciones vecinas.
- **Detalle:** en `results/anomalias_red_v1/revision19/<año>/`, `logs_revision19/` y `progreso.md`.


### Revisión T1 (2026-10-29): selección TINTO-PCA con asignación única

**Autorización:** el tesista pidió continuar con registro y selección completa
(«Perfecto, entonces vamos con la siguiente parte»). Registro previo a entrenar
el conjunto completo; esta etapa NO permite evaluar 2023–2026.

- Un solo candidato: 408 entradas de L0, no hora compacta ni canales. Mapa PCA
  de TINTO y escalador congelados del ajuste con 19 840 ventanas auditadas de
  2020–2021; asignación uno a uno propia a píxeles 32 × 32, sin difuminado.
  Esta variante modifica la rasterización de TINTO, no se presenta como su
  implementación original. Los valores fuera del rango MinMax no se recortan.
- Mismas ventanas/etiquetas/muestreo que L0: 1 357 800 de ajuste 2020–2021,
  veinte calendarios d50, y 339 450 de validación 2022 de calendarios 01–10.
  Se conserva sigma heredada L0 2020–2022 y escala a14 con 2020–2021 limpio.
- CNN: Conv2D 8/16 filtros 3 × 3, same, ReLU, cada una seguida de MaxPool 2;
  Flatten, densa 32 ReLU, dropout 0.2, sigmoide (34 081 parámetros).
  Adam 0.001, BCE, batch 64, semilla 42, CPU, barajado sin reemplazo por ciclo,
  sin pesos de clase, sin balanceo y sin aumentación.
- Máximo 60 épocas, EarlyStopping sobre val_loss, paciencia 8, min_delta 0,
  mejores pesos. E es la primera época con mínimo val_loss. Dos corridas,
  mismos datos/configuración, comparar pesos/historias/probabilidades de control.
- Se conserva el piloto sintético no aprobado bajo su límite de pérdida <0.1.
  La revisión verificó conversión, etiquetas y aprendizaje; no se cambia ese
  límite ni se usa su exactitud de entrenamiento para afirmar detección.
- Comparador futuro: L0 único d50 de SELECCIÓN, cargado de disco, mismas
  estación-días (promedio diario, mínimo 12 horas), p99/p99.9 exploratorios en
  2022 limpio. Esta ejecución selecciona E, no prueba superioridad ni decide
  acceso al examen. 2022 ya fue reutilizado: la comparación será exploratoria.
- Antes de resultados científicos no se modifica arquitectura, época por gusto,
  mapa o escalador. Se guardan avances y mejor checkpoint; solo el criterio
  val_loss registrado decide la parada. No se lanzan otros candidatos.
- Fuentes congeladas: `experiments/exploracion_tinto/configuracion_entrenamiento_v1.json`,
  `entrenar_tinto_l0.py` y `runbook_entrenamiento_v1.md` en esa carpeta;
  hashes previos en `results/exploracion_tinto_2022/seleccion_tinto_v1/registro_previo.json`.
  Las salidas no sustituyen modelos ni tablas de L0/V4/V4S.


**Ajuste técnico T1, antes de la primera época completa (2026-10-29):**
la prueba local de CPU mostró menor tiempo por lote con oneDNN habilitado;
dos repeticiones pequeñas con ese entorno dieron pesos y probabilidades
idénticos. Se interrumpieron las dos corridas originales antes de completar
una época o calcular resultados de validación completos. Se reinician como
`corrida_cpu1/2`, con `TF_ENABLE_ONEDNN_OPTS=1`, dos hilos intra-op y uno
inter-op, solo CPU; operación determinista solicitada. No cambia arquitectura,
datos ni regla de parada y no se selecciona por métricas. XLA no se adopta:
la prueba técnica indicó que el modelo no lo admite. Registro adicional
`registro_runtime_cpu.json`; se conserva el registro anterior y las salidas
parciales. Comparación final entre las dos corridas del mismo entorno.

**Cierre manual T1, 2026-10-29, por indicación del tesista:** se interrumpen las
dos corridas para ahorrar CPU y tokens, sin esperar ocho épocas sin mejora.
La primera completó ocho épocas y estaba validando la novena; la segunda
completó nueve y comenzó la décima. La mejor observada en ambas fue la 5.
Se conserva ese checkpoint; ocho épocas comunes tienen historia idéntica y
el contenido interno HDF5 de ambos checkpoints es idéntico por SHA-256.
No se carga otro modelo ni se continúa entrenando para esta verificación.
Se documenta como parada manual posterior a observar el avance, NO como
cumplimiento de EarlyStopping ni como prueba de que no habría mejoras futuras.
Constancia y modelos preservados en `seleccion_tinto_v1/cierre_manual/`.

### T1 — cierre documentado el 2026-10-29

La selección terminó manualmente por indicación del tesista; se conservó la
época5, sin presentar EarlyStopping completado. Evaluación posterior autorizada
solo2022: dos corridas CPU idénticas con TINTO/L0 cargados, diez calendarios,
δ100/50/20 y p99/p99.9; L0 supera F1/recall en seis condiciones. F̄ p99
descriptiva0.3083/0.3550. No se convierte retrospectivamente en adoptada la
regla propuesta de avance, ni se autoriza usar examen por este cierre.
Se conservan todos los resultados y límites. Ver
[cierre integral T1](cierre_exploracion_tinto_t1.md), incluidas fichas de las
imágenes reales solicitadas por el tesista. No cambia ninguna revisión previa.

### Revisiones 20 y 20b (2026-10-27 a 2026-10-29): PARAAD en la RAMA y los tres detectores en Barcelona

**Estado:**
- diseñadas, registradas y corridas en otro chat (Codex), a pedido del tesista;
- documentadas en sus propios archivos;
- integradas a este protocolo el 2026-10-29, ya con resultados, y su commit es `f931246`.

**Por qué:** el asesor pidió poner al grupo de Barcelona «en la misma tabla, en el mismo
escenario». Se hicieron las dos direcciones:
- **(20)** su método con nuestros datos;
- **(20b)** nuestros métodos con sus datos.

**Desviaciones que hay que declarar:**
- **Entorno de software distinto:** TensorFlow 2.21 y Keras 3.13 (Python 3.13), por la dependencia
  de atención de PARAAD, no el `requirements-lock.txt` del repo. Dentro de cada experimento todos
  los detectores usan el mismo entorno.
- **Registro previo:** los documentos de registro de la revisión 20 no tuvieron commit antes del
  examen. Lo que respalda su fecha es el propio texto, no git.
- **No es una reproducción del artículo:**
  - no son sus 8 estaciones, sino otras 13;
  - no es su umbral móvil con etiquetas, sino umbrales fijos de un año limpio;
  - la 20b sólo evaluó nuestras anomalías proporcionales; su sesgo sumado está pendiente.
- **PARAAD contra L0 no es «peras con peras»:** supervisado contra no supervisado. La comparación
  principal es PARAAD contra V4.

**Resultado (20, RAMA)**, detalle en `docs/resultados_examen_paraad_revision20.md`:
- PARAAD cargado de disco, con dropout 0.3 y 499 épocas, umbrales p99 0.6405 y p99.9 0.8366;
- L0 único tiene mayor F1 que PARAAD en las 36 combinaciones de δ = 100 y 50 %;
- con δ = 50 % y p99, PARAAD / V4 / L0: 0.128 / 0.101 / 0.388 en 2024, 0.208 / 0.108 / 0.445 en
  2025 y 0.140 / 0.193 / 0.502 en 2026;
- **PARAAD − V4:** +0.100 en 2025, con intervalo que excluye el 0; empate en 2024 y en 2026, con
  el V4 arriba en el valor puntual de 2026;
- las alertas de PARAAD en los años limpios se desvían del 1 % fijado: 3.4, 1.7 y 3.0 % con p99.

**Resultado (20b, Barcelona)**, detalle en `docs/resultados_examen_barcelona_2018_2019.md`:
- F1 con p99, L0 / V4 / PARAAD:
  - δ = 100 %: 0.484 / 0.412 / 0.500 en 2018 y 0.442 / 0.236 / 0.313 en 2019;
  - δ = 50 %: 0.500 / 0.252 / 0.304 y 0.435 / 0.106 / 0.191;
  - δ = 20 %: 0.144 / 0.052 / 0.071 y 0.107 / 0.024 / 0.058;
- **L0 le gana a los dos** con δ = 50 y 20 % en ambos años, con intervalos positivos;
- con δ = 100 % en 2018, PARAAD queda arriba en el valor puntual, pero L0 − PARAAD incluye el 0;
- **PARAAD le gana al V4** en el valor puntual en todos los casos con p99; es significativo en 2019
  con δ = 100, 50, 20 y 10 %, y en 2018 ningún intervalo excluye el 0;
- en 2019 suben las alertas limpias de los tres; PARAAD llega a 2.5 % con p99.

**Lectura conjunta:**
- el orden se repite en las dos ciudades: L0 arriba con los ataques medianos (δ = 50 y 20 %), y
  PARAAD igual o algo mejor que el V4 entre los no supervisados;
- con ataques grandes (δ = 100 %) no hay un ganador claro;
- con δ ≤ 10 % nadie detecta.

**Pendiente:** el sesgo sumado del artículo, que se conecta con la revisión 21 (error fijo en ppb).

### Revisión 21 (2026-10-29): error fijo en ppb

**Estado:**
- aprobada por el tesista el 2026-10-29, antes de programar o generar nada;
- tamaños 5, 10, 20 y 40 ppb, con PARAAD incluido.

**Anomalía:**
- con los planes de `prueba_2024_01…10`, `final_2025_01…10` y `final_2026_01…10`, sin cambiar
  episodios, estaciones, días ni signos;
- en las horas con dato de un episodio, signo + da x + a y signo − da max(x − a, 0);
- se redondea a entero, como siempre, y las horas sin dato siguen sin dato;
- a ∈ {5, 10, 20, 40} ppb;
- matrices `matriz_fijo_<corrida>_a<a>`;
- control: fuera de los episodios, la matriz es igual al año limpio; dentro, el cambio es
  exactamente ±a, salvo el recorte en 0.

**Detectores congelados, sin entrenar:**
- L0 único, V4S compartido, R3 y V4, como en la revisión 19;
- PARAAD-SA de la revisión 20, con sus umbrales congelados y calificado en su entorno registrado
  (TensorFlow 2.21) con `puntuar_paraad.py`.

**Comparaciones:**
- **principal «peras con peras»:** L0 único − V4S compartido (supervisados) y PARAAD − V4 (sin
  etiquetas);
- F1, recall y precisión con intervalo del 95 %, por bootstrap de bloques estación × mes, 2 000
  remuestreos, semilla `[42, 21, año]`;
- **pareada contra el escenario proporcional:** el recall de cada detector en los mismos
  episodios con error fijo y con δ, usando los puntajes de la revisión 18 y, para PARAAD, los de la
  revisión 20;
- también se reporta el cambio medio en ppb de cada escenario.

**Lo demás:**
- los umbrales p99 y p99.9 de 2023 limpio, las estación-días comunes y la historia limpia
  anterior a cada año;
- 2025–2026 se evalúa una sola vez, con la regla de la revisión 18;
- la evaluación se corre dos veces y debe salir igual.

**Predicciones (Claude), escritas antes de generar nada:**
1. con 20 y 40 ppb y p99, el recall de L0 único es de al menos 0.5 en 2025;
2. con 5 ppb, ningún detector supera claramente su valor sin ataque (F1 menor de 0.05 con p99);
3. con 10 ppb, el recall de L0 único es mayor o igual que con δ = 50 % (unos 14 ppb de cambio
   medio) en los mismos episodios, en 2025 y con p99. El error fijo también mueve las horas de
   ozono bajo; el proporcional casi no;
4. L0 único le gana en F1 al V4S compartido con 10, 20 y 40 ppb y p99 en 2025.

**Resultado de la revisión 21** (2026-10-30; 2025–2026 usado una sola vez para este escenario):
- **Origen:** todos los detectores cargados de disco (L0 único, V4S compartido, V4 y PARAAD) o sin
  entrenamiento (R3).
- **Controles:**
  - en Colab con AMD EPYC, las dos corridas idénticas;
  - umbrales y años limpios iguales a la revisión 18 (diferencia ≤ 8 × 10⁻¹⁶);
  - PARAAD, en su entorno registrado (TensorFlow 2.21.0 y Keras 3.13.2), difiere de su año limpio de
    la revisión 20 en ≤ 1.8 × 10⁻⁶, sin ninguna alarma distinta;
  - dos intentos previos se detuvieron solos: uno con 3 hilos en lugar de 4, que dio diferencias de
    2 × 10⁻⁸, y otro por un entorno ya creado.
- **Cambio medio real:** 4.8, 9.3, 17.6 y 32 ppb para a = 5, 10, 20 y 40, por el recorte en 0.
- **F1 con p99, 2025** (L0 único / R3 / V4S compartido / V4 / PARAAD):
  - 5 ppb: 0.033 / 0.044 / 0.014 / 0.022 / 0.013;
  - 10 ppb: 0.203 / 0.286 / 0.035 / 0.058 / 0.048;
  - 20 ppb: 0.443 / 0.479 / 0.119 / 0.137 / 0.303;
  - 40 ppb: 0.389 / 0.479 / 0.296 / 0.219 / 0.443.
- **Recall con p99, 2025:** L0 único 0.04 / 0.28 / 0.83 / 0.91 y R3 0.05 / 0.39 / 0.84 / 0.95.
- **Con error fijo, R3 queda arriba de L0 en F1 en casi todos los casos** con 10 y 40 ppb, en los
  dos umbrales (por ejemplo, 0.767 contra 0.572 con 40 ppb y p99.9 en 2025). Con 20 ppb y p99.9,
  L0 queda arriba (0.571 contra 0.531 en 2025). L0 aprendió con anomalías proporcionales y R3 no
  aprende nada: la regla generaliza mejor a una forma de anomalía nueva.
- **L0 único − V4S compartido:** L0 arriba con 10 y 20 ppb en los tres años y los dos umbrales,
  con intervalo que excluye el 0. Con 40 ppb y p99 empata en 2024, gana en 2025 y pierde en 2026
  (−0.078).
- **PARAAD − V4:**
  - en 2025 PARAAD gana con 20 y 40 ppb (+0.17 y +0.22 con p99);
  - en 2024 gana poco con 20 y 40 ppb y p99;
  - en 2026 pierde en todos los tamaños, con intervalo que excluye el 0;
  - no hay una ventaja estable.
- **Contra el proporcional, en los mismos episodios** (recall de L0 único, p99, 2025): δ = 50 %
  (~14 ppb de cambio medio) da 0.823, y 10 ppb da 0.279. El cambio proporcional, con el mismo
  promedio, se detecta mucho mejor, porque altera más las horas altas. Es lo que dijo el asesor
  sobre los picos.
- **Predicciones:**
  - se cumplen la 1 (recall de L0 de 0.83 y 0.91 con 20 y 40 ppb), la 2 (F1 máximo con 5 ppb de
    0.047) y la 4;
  - **falla la 3:** con 10 ppb el recall de L0 es 0.279, contra 0.823 con δ = 50 %.
- **Lectura:**
  - un error fijo de 10 ppb ya se detecta en parte, y uno de 20 ppb se detecta bien (recall de
    ~0.83 con p99);
  - 5 ppb no se distingue;
  - con este tipo de anomalía, la regla R3 iguala o supera a L0. La ventaja de L0 depende de que
    la anomalía se parezca a la de su entrenamiento;
  - entre los no supervisados, PARAAD y el V4 no tienen un orden estable.
- **Detalle:** en `results/anomalias_red_v1/revision21/<año>/` y `logs_revision21/`.

### Revisión 20c (2026-10-29): el sesgo de PARAAD en Barcelona

**Estado:** aprobada por el tesista el 2026-10-29, antes de aplicar el sesgo a los años de examen.

**Diseño:**
- **modelos congelados de la 20b:** L0 único (entrenado con δ = 50 % proporcional), los 13 V4 y
  PARAAD-SA, sin entrenar ni recalibrar;
- **umbrales:** p99 y p99.9 de 2017;
- **planes:** los de `results/barcelona_paraad/planes_sesgo_v1/`, ya generados y registrados en
  `docs/planes_sesgo_barcelona_v1.md`:
  - 125 calendarios para la prueba 2018 y 125 para 2019;
  - en cada uno, 4 de las 13 estaciones y el 30 % de sus días;
  - desplazamiento β·σ de ajuste constante en el día, con β de `truncnorm(0.2, 2, scale=2)`, es
    decir, entre 0.4 y 4;
- **métricas, intervalos y control sin inyección:** como en la 20b;
- **comparación principal:** PARAAD − V4 (sin etiquetas); L0 como referencia supervisada que nunca
  vio esta anomalía.

**Cautela:** la prevalencia del sesgo es de ~9 %, contra menos del 1 % en el escenario
proporcional. La precisión y el F1 no se comparan entre escenarios.
