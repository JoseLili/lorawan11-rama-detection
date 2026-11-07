> **Estado: borrador sustituido** por `registro_previo_rev22_mas_anios.md` (2026-11-07). No se ejecutó; se conserva por transparencia del proceso de registro.

# Registro previo de la revisión 22: más años de fondo (M) y recalibración mensual del umbral (C)

Fecha: 2026-11-07. **Estado: borrador para aprobación del tesista.** No se ha entrenado nada, no se han abierto los zips de 2000–2015 y agosto–diciembre de 2026 todavía no está publicado.

**De dónde viene:**
- En el diagnóstico del 2026-10-22, pasar de uno a dos años de fondo subió la detección con δ = 100 % unos 4 puntos. Con δ = 20 % no se movió.
- L0 siempre elige E = 1, porque los 20 calendarios comparten el mismo ozono real de 2020–2021.
- En 2017–2019, los umbrales de 2023 se desviaron (0.1 % nominal → 0.16 % logrado con Ens-V0r, 0.31 % con Ens-Vbr).

**Dos preguntas, con una prueba cada una:**
- **M:** ¿más años de fondo mejoran a L0?
- **C:** ¿una recalibración mensual sin etiquetas mantiene las falsas alarmas en su nivel nominal sin perder F1?

## 1. Años: las etapas del protocolo (§4), sin cambios

| Etapa | Años | Qué cambia en esta revisión |
|---|---|---|
| Ajuste inicial | 2020–2021 **+ años extra elegibles** | M agrega fondo; sólo se entrena con él |
| Validación (elección de M) | 2022 | Igual |
| Ajuste definitivo | 2020–2022 **+ años extra elegibles** | Igual, más los años extra |
| Calibración | 2023 limpio | Igual |
| Prueba principal (ya usada) | 2024 | No se toca |
| Examen final del protocolo (ya usado, rev. 17) | 2025 y enero–julio de 2026 | Enero–julio de 2026 sólo como historia del examen nuevo |
| **Examen de esta revisión (uso único)** | **2026-08-01 a 2026-12-31** | Nuevo y prospectivo; es la opción que ya traía la hoja de ruta |

### Dónde van los años extra
- **2000–2019, fondo de entrenamiento de M.** Nunca sirven para validar, calibrar ni examinar.
- **2017–2019 también son fondo.** Su único uso como examen ya ocurrió (2026-11-06).
- **2017–2019 son además el desarrollo de C**, con los modelos definitivos que ya existen (entrenados con 2020–2022, que no vieron esos años). No es un examen, porque ya se vieron.
- **Por qué C no se desarrolla en 2022:** los modelos de selección se entrenaron con 2020–2021, así que no queda un año de calibración fuera de muestra antes de 2022. La pregunta de C es justamente el traslado del umbral entre años.

### Regla de elegibilidad, fijada antes de abrir los zips
La auditoría revisa sólo el formato, sin modelos:
- **Cobertura:** fracción de horas con O₃ válido de cada objetivo en cada año.
- **Estación-año elegible:** cobertura ≥ 0.75. Sólo sus horas generan ventanas de entrenamiento. Una estación que no cumple queda como hueco (máscara = 0) en las entradas de las demás.
- **Año elegible:** al menos 16 de los 31 objetivos son estación-años elegibles.
- Se reporta la tabla completa, año × estación. Las vecinas, σ y la escala a14 siguen siendo las de 2020–2022, para que las entradas no cambien de definición.

## 2. M: más años de fondo

**Igual que la revisión 14 y LB1:**
- entradas V0 (17 columnas por objetivo);
- arquitectura: LSTM 64, dropout 0.2, densa 32 y sigmoide;
- Adam, BCE, batch 64 y `shuffle`;
- EarlyStopping sobre val_loss de 2022, paciencia 8, máximo 60 épocas;
- δ = 50 % en el entrenamiento y 1 de cada 8 horas por calendario y estación.

**Calendarios de los años extra:**
- **5 por año**, con `plan_episodios`, la semilla maestra 42 y la clave del año, con p base de 0.15 % como en todo plan de entrenamiento (§6);
- 2020–2021 conservan sus 20 calendarios;
- los planes se guardan con su SHA-256 antes de entrenar.

**Candidatos:**

| | Cómo se entrena |
|---|---|
| **M1, agrupado** | Una sola corrida con los años extra y 2020–2021 mezclados |
| **M2, preentrenar y afinar** | Primero sólo los años extra; después continúa con 2020–2021 con tasa de aprendizaje de 0.0001. Cada etapa usa el mismo EarlyStopping |

- **Semillas:** 42, 1, 2, 3 y 4. Se forman Ens-M1 y Ens-M2.
- **Comparador:** Ens-V0r de LB2, ya entrenado con 2020–2021.
- **Fase definitiva:** cada semilla se reentrena con los años extra + 2020–2022, con exactamente su E (en M2, su E de cada etapa), en el modo `definitivo` de la revisión 14.
- **Cómputo estimado:** unas 2.5 veces las ventanas de LB2, es decir del orden de 15 a 25 horas de CPU en el PC del tesista, en segundo plano. Es una estimación, no una medida.

### Evaluación y regla de avance (2022)
- **Igual que LB1 y LB2:**
  - calendarios 01–10, δ = 100, 50 y 20 %;
  - umbrales p99 y p99.9 sobre 2022 limpio de cada modelo;
  - estación-días comunes;
  - bootstrap pareado de 2000 bloques estación-mes, semilla [42, 22, 0].
- **Un candidato avanza** si, en p99 o en p99.9:
  - ΔF̄ (Ens-M − Ens-V0r) ≥ +0.02;
  - y el F̄ de la semilla supera al de V0r con la misma semilla en al menos 4 de las 5 semillas.
- **Si los dos cumplen,** avanza el de mayor ΔF̄ en p99.
- **Si ninguno cumple,** M se cierra como resultado negativo y no va a examen.
- **Advertencia, la misma de LB1:** 2022 también es el conjunto del EarlyStopping, así que es optimista para todos por igual.

## 3. C: recalibración mensual del umbral, sin etiquetas

**Definición, fijada ahora y sin ajustar después:**
- **Umbral fijo u_q:** el del protocolo, de 2023 limpio (q = p99 o p99.9).
- **Referencia:** Q90_ref es el percentil 90 de las estación-días de 2023 limpio.
- **Recalibración:** el día 1 de cada mes m, Q90_m es el percentil 90 de **todas** las estación-días de los 60 días anteriores del flujo en operación. Ese flujo puede contener ataques: no se usan etiquetas, como haría un operador.
- **Nuevo umbral:** logit(u_q,m) = logit(u_q) + logit(Q90_m) − logit(Q90_ref).
- **Pocos datos:** si los 60 días tienen menos de 30 días con puntaje, se usa u_q.
- **Por qué el percentil 90 y no el p99:**
  - las estación-días atacadas son menos del 1 % (p ≤ 0.30 % diario y de 1 a 7 días), así que casi no mueven el percentil 90;
  - para moverlo, un atacante tendría que alterar más del 10 % de las estación-días. Ese límite se reporta como el punto débil frente a la deriva lenta de la línea Red Team.

**Desarrollo en 2017–2019 (ya visto):**
- **Modelos:** Ens-V0r y L0 rev.14 definitivos, sin reentrenar.
- **Puntajes:** los guardados en `holdout_a`, más noviembre–diciembre de 2016 limpio como historia de enero–febrero de 2017.
- **C avanza** si, para Ens-V0r:
  - la desviación |ln(FA lograda / FA nominal)| baja en p99 y en p99.9;
  - y F̄ no baja más de 0.01 en ninguno de los dos.
- **Si no cumple,** C se cierra como resultado negativo y no va a examen.

## 4. Examen de uso único: agosto–diciembre de 2026

**Datos:**
- el zip 26RAMA completo, cuando SIMAT publique diciembre (previsiblemente en enero de 2027);
- se registra su SHA-256 al subirlo y la auditoría es sólo de formato;
- enero–julio de 2026 sirven sólo de historia: perfil de 14 días, ventana de 24 h y los 60 días de C.

**Calendarios:**
- 10, con la semilla maestra 42 y la clave [2026, 8];
- **empiezan el 2026-06-01**, para que la historia de C contenga ataques como en operación, pero sólo se evalúan agosto–diciembre;
- p uniforme en (0.0010, 0.0030), episodios de 1 a 7 días y signo ±;
- δ = 100, 50, 20, 10 y 5 % con el mismo plan; F̄ usa 100, 50 y 20 %, como hasta ahora.

**Detectores congelados antes de abrir el examen:**
- el candidato M que avance (Ens-M, definitivo);
- Ens-V0r definitivo, el comparador;
- Ens-V0r + C, si C avanza;
- L0 rev.14;
- y, como en la revisión 17, R3 y V4;
- PARAAD entra si su código de la revisión 20 corre sin cambios en el periodo; si no, se declara.

**Punto principal: p99.**
- Con unas 4 700 estación-días limpias, el p99.9 esperaría unas 5 falsas alarmas. Sería demasiado ruidoso para decidir.
- El p99.9 y la curva de operación completa (0.05 a 5 %) se reportan como descriptivos.

**Pruebas, con Bonferroni.** El IC es siempre del 97.5 %, con bootstrap pareado de 2000 bloques estación-mes, semilla [42, 22, 1]:
- **T-M:** M se adopta si ΔF̄ (Ens-M − Ens-V0r) ≥ +0.02 en p99 y su IC no incluye valores menores de 0.
- **T-C:** C se adopta si, en p99:
  - baja la desviación |ln(FA lograda / 1 %)| de Ens-V0r;
  - y el límite inferior del IC de ΔF̄ (C − fijo) es mayor que −0.02, una prueba de no inferioridad.
- Lo que no avanzó a examen no se prueba.
- Si una prueba falla, se reporta como resultado negativo y no se repite.

**Reproducibilidad:** dos corridas de inferencia que deben salir idénticas.

## 5. Predicciones (Claude, antes de abrir nada)
1. Al menos 6 años extra son elegibles, entre ellos 2016–2019.
2. En 2022 avanza al menos un candidato M. La ganancia se concentra en δ = 100 y 50 %, y el F1 con δ = 20 % cambia menos de 0.02.
3. M2 supera a M1 en F̄ con p99 en 2022.
4. Con M1, la mejor época es E ≥ 2 en al menos 3 de las 5 semillas: más variedad de fondo reduce la memorización.
5. En 2017–2019, C acerca a la nominal la FA lograda de Ens-V0r en p99.9, y F̄ cambia menos de 0.01.
6. En el examen, la FA lograda del umbral fijo p99 queda entre 0.5 y 1.5 %.
7. En el examen, el IC de T-M incluye el 0: el efecto esperado (+0.02 a +0.04) es del tamaño de la incertidumbre con cinco meses.
