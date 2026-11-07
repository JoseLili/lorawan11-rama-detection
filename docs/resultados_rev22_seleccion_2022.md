# Resultados de la revisión 22, fase de elección (2022)

Fecha: 2026-11-07. Registro: `registro_previo_rev22_mas_anios.md`, aprobado antes de entrenar.

**En una línea:** más años de fondo mejoran a la base V0 de forma consistente (5 de 5 semillas). Pero la regla registrada manda al examen a **Vb-R y Vb-M1**, porque Vb vuelve a ganar con claridad en 2022.

## Cómo se corrió
- **Cómputo:** 30 modelos de selección (2 bases × 3 casillas × 5 semillas) en el PC del tesista (CPU, TensorFlow 2.21), con 4 procesos de 4 hilos y paciencia 3.
  - Entrenamiento: 99.8 min.
  - Puntaje de 2022: 33 min.
  - Total: 133 min.
- **Fondo:** 8 años extra elegibles (2012–2019), con 964 245 ventanas por base.
- **Control de la tubería (pasa):**
  - Ens-V0-R, reentrenado con la tubería nueva, queda a +0.0003 de F̄ del Ens-V0r de LB2 con p99 y a +0.016 con p99.9;
  - la tolerancia era ±0.03.

## F̄ y F1 de los ensambles en 2022

Umbral sobre 2022 limpio de cada modelo, en las estación-días comunes a los 36 modelos.

| Ensamble | F̄ p99 | F1 δ100 | F1 δ50 | F1 δ20 | F̄ p99.9 | F1 δ100 | F1 δ50 | F1 δ20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ens-V0-R (comparador) | 0.361 | 0.454 | 0.476 | 0.152 | 0.268 | 0.497 | 0.301 | 0.007 |
| Ens-V0-M1 | 0.380 | 0.466 | 0.487 | 0.186 | 0.330 | 0.598 | 0.377 | 0.016 |
| Ens-V0-M2 | 0.364 | 0.466 | 0.481 | 0.145 | 0.320 | 0.582 | 0.360 | 0.018 |
| Ens-Vb-R | 0.404 | 0.546 | 0.514 | 0.152 | **0.516** | **0.839** | 0.647 | 0.062 |
| Ens-Vb-M1 | 0.402 | 0.560 | 0.517 | 0.128 | 0.453 | 0.741 | 0.578 | 0.041 |
| Ens-Vb-M2 | 0.399 | 0.552 | 0.508 | 0.136 | 0.410 | 0.696 | 0.504 | 0.030 |

## Regla de avance contra Ens-V0-R
Una casilla avanza si ΔF̄ ≥ +0.02 y gana en al menos 4 de 5 semillas, en p99 o en p99.9. Los IC del 95 % son descriptivos.

| Casilla | ΔF̄ p99 [IC 95 %] | Semillas | ΔF̄ p99.9 [IC 95 %] | Semillas | Avanza |
|---|---|---:|---|---:|---|
| V0-M1 | +0.019 [−0.003, +0.039] | 5/5 | +0.062 [+0.046, +0.078] | 5/5 | Sí (por p99.9) |
| V0-M2 | +0.003 [−0.012, +0.018] | 3/5 | +0.052 [+0.037, +0.067] | 3/5 | No |
| Vb-R | +0.043 [−0.011, +0.100] | 5/5 | +0.248 [+0.202, +0.293] | 5/5 | Sí |
| Vb-M1 | +0.041 [−0.015, +0.106] | 5/5 | +0.185 [+0.146, +0.223] | 5/5 | Sí |
| Vb-M2 | +0.038 [−0.019, +0.109] | 5/5 | +0.142 [+0.100, +0.183] | 5/5 | Sí |

**Al examen van las dos con mayor ΔF̄ en p99: Vb-R (+0.043) y Vb-M1 (+0.041).** V0-M1 avanza, pero no entra entre las dos primeras.

## Predicciones
1. Al menos 6 años extra elegibles, entre ellos 2016–2019: **se cumplió** (8).
2. Avanza al menos una casilla M, la ganancia se concentra en δ = 100 y 50 %, y δ = 20 % cambia menos de 0.02: **a medias.**
   - Avanzan tres casillas M.
   - Con V0, el F1 con δ = 20 % sube +0.034 con p99 (más de 0.02) y +0.009 con p99.9.
3. M2 supera a M1 con las dos bases: **no se cumplió.** Con las dos bases, M1 ≥ M2.
4. Las casillas con Vb superan a las de V0: **se cumplió** en los tres entrenamientos y los dos umbrales.
5. Con M1, E ≥ 2 en al menos 3 de 5 semillas: **se cumplió.** V0-M1 elige E = 2, 4, 2, 1 y 4; Vb-M1, E = 2, 3, 3, 3 y 3. Los modelos anteriores elegían casi siempre E = 1.
6. a 8. Pendientes del examen.

## Lectura
1. **Más años de fondo ayudan a V0, y de forma estable.** V0-M1 gana en las 5 semillas con los dos umbrales, y con p99.9 su IC excluye el 0. Además, la mejor época sube de 1 a 2–4: el modelo deja de memorizar el fondo de 2020–2021.
2. **Con Vb pasa lo contrario en p99.9:** al agregar años, su ventaja de 2022 baja (0.516 → 0.453 → 0.410).
   - Una explicación posible, **no comprobada**, es que parte de la ventaja de Vb sea propia de las condiciones de 2020–2022.
   - Encaja con su reprobación en 2017–2019.
3. **Preentrenar y afinar (M2) no supera a mezclar todo (M1).**
4. **Vb-R es la misma receta que Ens-Vbr,** que no se adoptó en el examen de 2017–2019. La regla registrada lo manda al examen de todos modos; ese antecedente se reporta junto a su resultado.
5. **2022 es optimista para todos por igual,** porque también es el conjunto del EarlyStopping. Estas cifras no sustituyen al examen.

## Siguiente paso (registrado)
- **Modelos definitivos: hechos** el 2026-11-07, en 29 min. Son los 15 de Vb-R, Vb-M1 y del comparador V0-R, con 2020–2022 (+ fondo en M1) y exactamente la E de cada semilla. Sus SHA-256 están en `results/linea_base/rev22/modelos_definitivos_sha256.json`, y quedan congelados antes de abrir el examen.
- **Calibración** en 2023 limpio.
- **Examen de despliegue:** del 2026-08-01 al último mes completo publicado, cuando el tesista suba el 26RAMA.zip actualizado.

Salidas: `results/linea_base/rev22/` (`metricas_2022.csv`, `pruebas_seleccion_2022.csv`, `control_lb2.csv`, `decision_seleccion.json`, `auditoria_cobertura.csv` y configuraciones e historiales en `modelos_seleccion/`).
