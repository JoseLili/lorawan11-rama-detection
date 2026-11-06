# Resultados del examen final: Ens-Vbr sobre RAMA 2017–2019 (uso único)

- **Registro previo:** [registro_previo_examen_final_2017_2019.md](registro_previo_examen_final_2017_2019.md), aprobado por el tesista antes de abrir el holdout.
- **Script:** `experiments/linea_base/examen_final.py` (etapas planes → modelos → calibración → holdout a/b → métricas). Resultados en `results/linea_base/examen_final/`.
- **Cómputo:** PC del tesista (CPU AMD Ryzen 7 7700X).

## Controles
- Los 30 planes se guardaron con su SHA-256 antes de construir datos del holdout, y se verificaron antes de puntuar (`planes_sha256.json`).
- Los 10 modelos definitivos (V0r y Vbr × semillas 42, 1–4) se entrenaron con 2020–2022 (2 036 700 ventanas) con su E registrado.
- Los umbrales salen de 2023 limpio, con 2020–2022 como historia. 2016 solo se usó como historia y no se evaluó.
- **Las dos corridas del holdout** (a: años en orden; b: en orden inverso) son **idénticas**: la diferencia máxima es de 0.0.
- **Corrección durante la ejecución:** `comun.bases` usaba el índice de fechas de 2020–2022 para la mediana de 60 días de Vb. Falló, sin producir resultados, al calibrar con 2020–2023, y se corrigió para usar el índice de cada matriz. No cambia LB1, LB2 ni EP1, porque allí la matriz siempre era 2020–2022.

## Resultado según la regla registrada: **Ens-Vbr no se adopta**

| Prueba declarada | ΔF̄ (Ens-Vbr − Ens-V0r) | IC 97.5 % |
|---|---:|---|
| p99 (1 %) | +0.004 | [-0.042, +0.057] |
| p99.9 (0.1 %) | -0.029 | [-0.082, +0.025] |

Ninguno de los dos puntos alcanza +0.02 con un IC por encima de 0. **Según el registro, el examen no se repite.**

## Puntos declarados, 2017–2019 juntos

| Nivel nominal | Detector | FA limpia lograda | Alarmas por estación y año | F̄ | F1 δ 100 % (R / P) | F1 δ 50 % (R / P) | F1 δ 20 % |
|---|---|---:|---:|---:|---|---|---:|
| 1 % | Ens-Vbr | 1.13 % | 4.1 | 0.383 | 0.515 (0.95 / 0.35) | 0.484 (0.84 / 0.34) | 0.151 |
| 1 % | Ens-V0r | 0.84 % | 3.1 | 0.380 | 0.457 (0.94 / 0.30) | 0.500 (0.83 / 0.36) | 0.181 |
| 1 % | L0rev14 | 0.97 % | 3.5 | 0.363 | 0.428 (0.93 / 0.28) | 0.472 (0.84 / 0.33) | 0.191 |
| 0.1 % | Ens-Vbr | 0.31 % | 1.1 | 0.387 | 0.646 (0.67 / 0.62) | 0.477 (0.44 / 0.52) | 0.038 |
| 0.1 % | Ens-V0r | 0.16 % | 0.6 | 0.416 | 0.654 (0.71 / 0.60) | 0.552 (0.47 / 0.67) | 0.042 |
| 0.1 % | L0rev14 | 0.19 % | 0.7 | 0.413 | 0.619 (0.69 / 0.56) | 0.559 (0.50 / 0.64) | 0.061 |

## Curva de operación: F1 con δ = 100 % según el nivel de falsas alarmas elegido en 2023

| Detector | 0.05 % | 0.1 % | 0.2 % | 0.5 % | 1 % | 2 % | 5 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ens-Vbr | 0.622 | 0.646 | 0.683 | 0.600 | 0.515 | 0.405 | 0.256 |
| Ens-V0r | 0.657 | 0.654 | 0.624 | 0.530 | 0.457 | 0.336 | 0.215 |
| L0rev14 | 0.630 | 0.619 | 0.611 | 0.518 | 0.428 | 0.336 | 0.205 |

Detalle completo, por δ y por año, en `curva_operacion_2017_2019.csv` y `metricas_por_anio.csv`.

## Predicciones (5)

| # | Predicción | Resultado |
|---|---|---|
| 1 | Ens-Vbr gana con p99.9 (la regla pasa) | ✗ ΔF̄ = −0.029 |
| 2 | Con p99, ΔF̄ positivo, con un IC que puede incluir valores menores de 0 | ✓ +0.004, IC [−0.042, +0.057] |
| 3 | Ens-Vbr con p99.9 y δ = 100 % logra F1 ≥ 0.65 | ✗ 0.646, apenas debajo |
| 4 | La FA limpia lograda difiere de la nominal en más de un 30 % relativo | A medias: sí con 0.1 % (0.31 % y 0.16 %), no con 1 % (1.13 % y 0.84 %) |
| 5 | δ = 20 % con F1 < 0.15 en todos | ✗ con p99, V0r da 0.181, L0 rev. 14 da 0.191 y Vbr 0.151 |

## Lectura (descriptiva; no cambia la decisión)
1. **La ventaja de Vb en 2022 no se transfirió a 2017–2019.** Con p99 empatan; con p99.9, V0r queda puntualmente arriba.
2. **Vb calibra peor fuera de su año de calibración.** Con un nivel nominal de 0.1 %, Vbr logra 0.31 % de falsas alarmas en 2017–2019 limpio, contra 0.16 % de V0r. Más falsas alarmas significan menos precisión con el mismo umbral.
3. **El efecto cambia por año.** En 2018, Vbr gana (F̄ con p99 de 0.414 contra 0.345, PR-AUC con δ = 50 % de 0.588 contra 0.562). En 2017 y 2019 pierde. La ausencia de FAR y SAC en 2017–2018 no lo explica, porque Vbr también pierde en 2019.
4. **El rendimiento absoluto sí es fuerte en todos los L0.** Con 0.1 % y δ = 100 %, el F1 es de 0.62–0.65 (recall de 0.67–0.71, precisión de 0.56–0.62). En la curva, el mejor punto observado de Ens-Vbr es 0.683 con 0.2 %, aunque esto es descriptivo y no fue una prueba declarada. Con 1 % y δ = 100 %, el recall es de 0.93–0.95.
5. **La cifra de 2022 (F1 de 0.752) era optimista**, como se había advertido: 2022 se usó para elegir épocas y comparar variantes.

## Qué queda para la tesis
- **Detector principal:** sigue siendo L0 con la base de 14 días (Ens-V0r o el L0 de la rev. 14), con su curva de operación sobre un holdout limpio.
- **Vb:** se reporta como resultado negativo de generalización. Reduce las falsas alarmas tras un episodio en el año de desarrollo, pero no mejora en años no vistos y calibra peor.
- **Ensamble:** Ens-V0r con p99.9 obtiene F̄ de 0.416 contra 0.413 del L0 de la rev. 14 (sin prueba registrada).
