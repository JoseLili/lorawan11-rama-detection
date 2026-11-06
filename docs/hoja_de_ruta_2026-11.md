# Hoja de ruta desde el 2026-11-04

Punto de partida: la exploración de líneas base y la revisión LB1
([resultados](resultados_LB1_2022.md)). Vb mejora a L0, pero no pasa su regla con p99
(ΔF̄ = +0.036, IC [−0.018, +0.117]). Con p99.9 la ventaja es grande, pero ese umbral es secundario.

## Reglas que valen para todas las fases
1. **Registro previo antes de programar.** Cada fase lleva definiciones, parámetros, métricas, regla de avance y predicciones, aprobadas por el tesista.
2. **No se abre el holdout final** hasta la fase 4, y se usa una sola vez.
3. **«Peras con peras».** Los modelos que se comparan se entrenan en el mismo entorno, con los mismos calendarios y estación-días.
4. **Cada fase deja:**
   - registro;
   - script en `experiments/`;
   - pruebas en `tests/`;
   - resultados en `results/`;
   - documento de resultados en `docs/`;
   - entrada en `progreso.md`;
   - decisión en `bitacora_decisiones.md`.
5. **Doble corrida** con salidas comparadas antes de aceptar un resultado, como en las revisiones 13–21.

## Fases, en orden

| Fase | Pregunta | Qué se hace | Datos | Costo | Depende de |
|---|---|---|---|---|---|
| **0. Consolidar** (hecho el 2026-11-04) | ¿Está todo reproducible? | Módulo `src/detect/linea_base.py`, scripts `experiments/linea_base/`, pruebas, documentos | 2020–2022 | — | — |
| **1. LB2: semillas** | ¿La ventaja de Vb con p99 sobrevive al azar del entrenamiento? ¿Un ensamble mejora? | 5 semillas de V0r y de Vbr, y el ensamble (media) de cada uno | 2022 | ~2.5 h en CPU local | 0 |
| **2. D1: deriva y sesgo aditivo** | ¿Qué detectores resisten una deriva lenta (el ataque que arrastra el perfil) y el sesgo aditivo de PARAAD? | Nuevas familias en los calendarios: rampa de *r* ppb por día y sesgo aditivo fijo. Detectores congelados: L0, Vbr, R3, V4 y PARAAD. Cierra el escenario aditivo pendiente de Barcelona | 2022 (exploratorio) | ~1 día | 1, por la versión de Vbr |
| **3. Mejoras de entrenamiento** (condicional) | ¿El límite es el fondo repetido? | Una o varias, cada una con su registro: (a) mezcla de familias de anomalía al entrenar; (b) preentrenamiento sin etiquetas + ajuste fino; (c) P4/P5 con estandarización por estación | 2020–2022 | Variable | 1 y 2 |
| **4. Examen final único** | ¿Se sostiene la ventaja fuera de los datos usados? | Candidatos congelados contra L0, R3, V4 y PARAAD. p99 y p99.9 como coprincipales, declarando las dos pruebas. Barcelona como validación externa | Holdout nuevo (decidir antes) | ~1 día | 1–3 cerrados |
| **5. Redacción** | — | Capítulos 4 y 5, y el paper | — | — | 4 |

## Decisiones pendientes del tesista y el asesor
- **Holdout de la fase 4:** RAMA 2017–2019 (disponible ya, pero anterior al entrenamiento) o agosto–diciembre de 2026 (prospectivo, pero hay que esperar su publicación). Hay que decidirlo y registrarlo **antes** de la fase 1, para que nada lo toque.
- **Si p99.9 pasa a coprincipal** en el examen final. Hoy es secundario.
- **La línea Red Team** (deriva para evadir el perfil de 14 días) empieza en la fase 2 como evaluación. La parte ofensiva (el atacante que optimiza contra L0) iría después, con su propio registro.

## Qué no reabrir
NO/NO₂ (diagnóstico negativo), TINTO (T1 y T2 cerrados), modelos de red de 31 salidas (rev. 13 y T2), la compuerta Va (bloqueo medido) y el CUSUM con k común (heterogeneidad medida).
