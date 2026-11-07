# Registro previo de la revisión 22: Vb y más años de fondo (M1, M2) bajo la metodología principal

Fecha: 2026-11-07. **Estado: aprobado por el tesista el 2026-11-07, antes de entrenar.** Los detalles de cómputo de §3.1 (puntos 3 y 6) y la auditoría de §2.1 se añadieron después de la aprobación y antes de entrenar. No se ha entrenado nada ni se han abierto los zips de 2000–2015. Nadie ha visto datos posteriores al 2026-07-31.

Versión 3. Sustituye a los borradores anteriores. La recalibración C queda fuera.

## 1. Etapas: la metodología principal, desde cero

| Etapa | Años |
|---|---|
| Ajuste inicial | 2020–2021 + años extra elegibles |
| Validación (aquí se elige) | 2022, igual que siempre |
| Ajuste definitivo | 2020–2022 + años extra elegibles |
| Calibración | 2023 limpio, igual |
| 2024 y 2025–jul 2026 | No se tocan para decidir; enero–julio de 2026 sólo como historia |
| **Examen de uso único** | **Desde el 1 de agosto de 2026, hacia adelante en el tiempo** |

- **Ventana del examen (despliegue):**
  - va del 2026-08-01 al último día del último mes completo publicado por SIMAT cuando el tesista suba el zip 26RAMA actualizado;
  - el fin de la ventana y el SHA-256 del zip se registran **antes** de cualquier puntaje;
  - lo que se publique después (hasta el 31 de diciembre) queda como una segunda ventana de despliegue, con su propio registro.
- **Los resultados anteriores no condicionan esta revisión.** El examen de 2017–2019 (Ens-Vbr no adoptado) y los de 2024–2026 de revisiones previas quedan en el historial de la tesis, y aquí todo se decide de nuevo en 2022.

## 2. Dónde van los años extra
- **2000–2019, sólo como fondo de entrenamiento** de M1 y M2. Nunca para validar, calibrar ni examinar.
- **2016–2019:** ya están subidos y auditados. 2017–2019 ya cumplieron su único uso como examen, así que ahora pueden ser fondo.
- **2000–2015:** el tesista los sube y se auditan sólo en formato, sin modelos.
- **Regla de elegibilidad, fijada antes de abrir los zips:**
  - estación-año elegible si su cobertura de O₃ es ≥ 0.75. Sólo sus horas generan ventanas; si no cumple, queda como hueco (máscara = 0) en las entradas de las demás;
  - año elegible si tiene al menos 16 de los 31 objetivos elegibles;
  - las vecinas, σ y la escala a14 siguen siendo las de 2020–2022.

### 2.1 Resultado de la auditoría (2026-11-07, sin modelos)
- **SHA-256** de 00RAMA–15RAMA y de sus archivos internos, en `docs/checksums_2000_2015.txt`, registrados antes de abrirlos.
- **Años elegibles: 2012–2019**, con 18, 20, 20, 18, 25, 27, 24 y 24 objetivos elegibles respectivamente.
- **2000–2011 no entran:** tienen entre 9 y 12 objetivos con cobertura ≥ 0.75, por debajo de los 16 que pide la regla.
- **Planes:** 40 planes de fondo (8 años × 5), con sus SHA-256 en `results/linea_base/rev22/planes_sha256.json`.
- **Ventanas por base:** 964 245 de fondo, 1 357 800 de 2020–2021 y 339 450 de validación 2022.
- **Predicción 1** (al menos 6 años, entre ellos 2016–2019): **se cumplió** (8).

## 3. Qué se entrena: un diseño de 2 × 3

| | R: sólo 2020–2021 | **M1**: agrupado | **M2**: preentrenar y afinar |
|---|---|---|---|
| **V0** (base actual de 14 días) | Ens-V0-R | Ens-V0-M1 | Ens-V0-M2 |
| **Vb** (base anclada en vecinas) | Ens-Vb-R | Ens-Vb-M1 | Ens-Vb-M2 |

- **M1:** una sola corrida con los años extra y 2020–2021 mezclados.
- **M2:** primero sólo los años extra, como preentrenamiento; luego continúa con 2020–2021 con tasa de aprendizaje de 0.0001. Es el «fine-tuning». Cada etapa usa el mismo EarlyStopping.
- **Calendarios de los años extra:**
  - 5 por año, con δ = 50 %;
  - `plan_episodios` con la semilla maestra 42 y la clave del año, con p base de 0.15 %;
  - se guardan con su SHA-256 antes de entrenar;
  - 2020–2021 conservan sus 20 calendarios.
- **Lo demás, igual que la revisión 14 y LB1/LB2:**
  - arquitectura: LSTM 64, dropout 0.2, densa 32 y sigmoide;
  - Adam, BCE, batch 64 y `shuffle`;
  - EarlyStopping sobre val_loss de 2022, con **paciencia 3** (antes 8) y máximo 60 épocas (ver §3.1);
  - 1 de cada 8 horas por calendario y estación;
  - semillas 42, 1, 2, 3 y 4.
- **Cómputo:** 20 modelos de selección (4 casillas × 5 semillas) y, después, los definitivos **sólo de las casillas que avancen** (como máximo 2 × 5). Las optimizaciones de §3.1 bajan la estimación a unas **3 horas** de CPU en el PC del tesista, si hay unos 10 años extra elegibles. Es una estimación, no una medida.

### 3.1 Optimización del cómputo (no cambia qué se calcula)
1. **Paciencia 3 en vez de 8.**
   - En los 10 entrenamientos existentes (LB1 y LB2), la paciencia 3 elige **la misma época** que la paciencia 8 en los 10 casos (E = 1 en ocho y E = 2 en dos).
   - Termina en 4–5 épocas en vez de 9–10.
   - Si una casilla nueva mejora después de 3 épocas sin avance, eso se pierde. Es el costo declarado de la optimización.
2. **Cuatro entrenamientos en paralelo,** con 4 hilos cada uno, lanzados desde el kernel `tf-l0`.
   - Prueba del 2026-11-07, con una LSTM del mismo tamaño y batch 64: 333 pasos/s con un proceso de 16 hilos y 976 pasos/s en total con 4 procesos, unas 2.9 veces más.
   - El número de hilos puede cambiar los decimales del entrenamiento frente a Ens-V0r, que usó 16 hilos. Se declara.
3. **Ventanas construidas una vez y leídas de disco por lotes.**
   - Las ventanas se guardan una vez en disco y cada proceso las lee por lotes (`keras.utils.PyDataset`).
   - Prueba del 2026-11-07: el `fit` de Keras con un arreglo de 2.1 GB ocupó 4.7 GB por proceso; leyendo por lotes, 0.54 GB.
   - Los lotes son de 64, con una permutación nueva en cada época, con la clave [semilla, 22, etapa, época], en lugar del `shuffle` interno de Keras.
   - Las ventanas de 2020–2021 son **idénticas** a las de LB1/LB2: 1 357 800, con el contenido comprobado en el calendario 01.
4. **Definitivos sólo para las casillas que avanzan.** Ens-V0r y Ens-Vbr ya tienen los suyos.
5. **Todo corre en segundo plano.** El tesista no tiene que vigilarlo.
6. **Validación en lotes de 2048.** La val_loss es la media sobre todas las ventanas, así que no depende del tamaño del lote.

## 4. Elección en 2022 (validación)
**Igual que LB1/LB2:**
- calendarios 01–10 con δ = 100, 50 y 20 %;
- p99 y p99.9 sobre 2022 limpio de cada modelo;
- estación-días comunes;
- bootstrap pareado de 2000 bloques estación-mes, semilla [42, 22, 0];
- la misma advertencia: 2022 también es el conjunto del EarlyStopping, así que es optimista para todos por igual.

**Las seis casillas compiten igual, contra Ens-V0r (el detector actual):**
- **Las seis casillas se entrenan con la misma tubería (§3.1), incluidas V0-R y Vb-R,** para que la comparación sea peras con peras. V0-R y Vb-R repiten la receta de LB2 (Ens-V0r y Ens-Vbr).
- **Control de la tubería:** Ens-V0-R debe quedar a ±0.03 de F̄ del Ens-V0r de LB2, en p99 y en p99.9. Si no, se reporta, y la comparación sigue siendo dentro de la tubería nueva.
- **Avanza una casilla** si, en p99 o en p99.9:
  - ΔF̄ (casilla − Ens-V0r) ≥ +0.02;
  - y la semilla supera a V0r con la misma semilla en al menos 4 de las 5.
- **Al examen van como máximo dos:** las dos que avancen con mayor ΔF̄ en p99.
- Si ninguna avanza, la revisión se cierra como resultado negativo y Ens-V0r sigue como detector principal.

## 5. Examen de despliegue (desde agosto de 2026)
- **Modelos:** los definitivos (2020–2022 + años extra), congelados y con su SHA-256 antes de abrir el examen.
- **Calendarios:**
  - 10, con `plan_episodios`, la semilla maestra 42 y la clave [2026, 8];
  - p uniforme en (0.0010, 0.0030), episodios de 1 a 7 días y signo ±;
  - δ = 100, 50, 20, 10 y 5 % con el mismo plan;
  - un episodio que rebasa el fin de la ventana se corta.
- **Umbrales:** p99 y p99.9 de 2023 limpio.
- **Detectores:**
  - **principales:** los candidatos contra **Ens-V0r** (ensamble contra ensamble);
  - **de referencia, en tabla:** L0 único, L0 por δ, R3 y V4; PARAAD si su código de la revisión 20 corre sin cambios.
- **Punto principal: p99.**
  - Con unos tres meses (≈ 2 850 estación-días limpias), el p99.9 esperaría unas 3 falsas alarmas.
  - El p99.9 y la curva de operación (0.05 a 5 %) son descriptivos.
- **Métrica:** F̄, la media del F1 con δ = 100, 50 y 20 %.
- **Prueba:** una por candidato (como máximo dos), con IC del **97.5 %** (Bonferroni):
  - bootstrap pareado de 2000 remuestreos;
  - bloques estación × mes;
  - semilla [42, 22, 1] y umbrales fijos.
- **Un candidato se adopta** si ΔF̄ ≥ +0.02 contra Ens-V0r en p99 y el IC no incluye valores menores de 0. Si no, se reporta como resultado negativo y no se repite con otros parámetros.
- **Reproducibilidad:** dos corridas de inferencia que deben salir idénticas.

## 6. Vista de despliegue (descriptiva, no decide)
Para responder cómo se comporta el detector día a día, en orden cronológico dentro de la ventana del examen, con el umbral p99 fijo de 2023, para los candidatos, Ens-V0r y L0 único:
1. **Mes a mes:**
   - falsas alarmas logradas en el mes limpio;
   - recall del mes con δ = 100 y 50 %.

   Muestra si el umbral de 2023 se desvía con el tiempo.
2. **Día de la primera alerta en cada episodio:** 1 = el mismo día en que empieza. Se reporta su distribución.
3. **Alerta en curso, hora a hora:**
   - a cada hora h ≥ 12 del día, se compara la media de las probabilidades horarias acumuladas hasta h con el mismo umbral diario;
   - da las **horas desde el inicio del episodio hasta la primera alerta**, la medida del §9 del protocolo;
   - sus falsas alarmas en el año limpio se reportan junto, porque una media parcial es más ruidosa.
4. **Una línea de tiempo por estación:** puntaje diario, umbral y episodios, para una estación típica y una heterogénea (CAM).

## 7. Predicciones (Claude, antes de abrir nada)
1. Al menos 6 años extra son elegibles, entre ellos 2016–2019.
2. En 2022 avanza al menos una casilla M. La ganancia se concentra en δ = 100 y 50 %, y el F1 con δ = 20 % cambia menos de 0.02.
3. En 2022, M2 supera a M1 con las dos bases.
4. En 2022, las casillas con Vb superan a las de V0, como en LB1/LB2.
5. Con M1, la mejor época es E ≥ 2 en al menos 3 de las 5 semillas.
6. En el examen, ningún candidato cumple la regla de adopción: el efecto esperado (+0.02 a +0.04) es del tamaño de la incertidumbre de tres meses.
7. Las falsas alarmas logradas de Ens-V0r con p99 quedan entre 0.5 y 1.5 % en la ventana.
8. En la vista hora a hora, la mediana de horas hasta la primera alerta con δ = 100 % es ≤ 24 h.
