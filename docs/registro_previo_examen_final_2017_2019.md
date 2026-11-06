# Registro previo del examen final: Ens-Vbr sobre RAMA 2017–2019 (uso único)

Fecha: 2026-11-04. **Estado: borrador para aprobación del tesista.** No se ha abierto ningún puntaje de 2017–2019.

## Datos
- **Holdout:** RAMA O₃ del 1 de enero de 2017 al 31 de diciembre de 2019. Ningún modelo ni decisión los ha usado. Sus SHA-256 están en `checksums_2017_2019.txt`.
- **Auditoría (solo formato, sin modelos):**
  - 8 760 horas por año, sin faltar ninguna;
  - FAR y SAC no existen en 2017–2018;
  - en 2019, CAM y CHO tienen una cobertura de 0.50 y 0.32.
- **Historia:** se usa `16RAMA.zip` (con SHA-256 registrado) solo como calentamiento del perfil de 14 días, de la mediana de 60 días y de la ventana de 24 horas. **Nunca se evalúa.**
- **Calibración:** 2023 limpio, con 2022 como historia, igual que en las revisiones 14–21.
- **Estaciones:** las 32 columnas de entrada de L0 (sin XAL), con los mismos σ y vecinas de 2020–2022. Una estación sin dato cuenta como hueco (máscara = 0).

## Detectores (congelados antes de abrir el holdout)

| Detector | Qué es |
|---|---|
| **Ens-Vbr** (candidato) | Media de 5 modelos L0 con línea base Vb. Semillas 42, 1, 2, 3 y 4 |
| **Ens-V0r** (comparador principal) | Lo mismo con la línea base actual V0 |
| L0 de la rev. 14 (referencia) | El `modelo.keras` definitivo δ = 50 % guardado en el repo |

- **Versiones definitivas:** cada semilla se reentrena con 2020–2022, en el modo `definitivo` de la revisión 14: 1 de cada 8 horas, exactamente su E y la escala a14 de 2020–2022 limpio.
  - E de V0r: 1, 1, 1, 1 y 1;
  - E de Vbr: 1, 1, 2, 2 y 1 (semillas 42, 1, 2, 3 y 4, de LB1 y LB2).
- **Cómputo:** en el PC del tesista (CPU), con dos corridas de inferencia del examen comparadas.

## Calendarios de ataque (generados antes de abrir el holdout)
- 10 calendarios por año, `plan_episodios` con la semilla maestra 42 y la clave del año (2017, 2018, 2019). No chocan con ningún calendario existente.
- p uniforme en (0.0010, 0.0030), episodios de 1 a 7 días, signo ±, las 31 estaciones alterables de siempre.
- **δ = 100, 50 y 20 %** proporcionales, con el mismo plan para los tres (diseño pareado).
- Los planes se guardan con su SHA-256 antes de puntuar.

## Métricas
1. **Curva de operación**, el resultado principal para el operador. Para cada tasa de falsas alarmas fijada en 2023 limpio (0.05, 0.1, 0.2, 0.5, 1, 2 y 5 % de las estación-días):
   - recall, precisión y F1 por δ;
   - la tasa de falsas alarmas **lograda** en 2017–2019 limpio;
   - las alarmas por estación al año.
2. **Dos puntos declarados para la prueba:** p99 (1 %) y p99.9 (0.1 %).
3. PR-AUC por δ, M1 (falsas alarmas a 1–14 días de un episodio) y las métricas por año.

Las unidades son las estación-días comunes a los tres detectores (≥ 12 horas), igual que en LB1 y LB2.

## Regla de adopción (dos pruebas, con corrección de Bonferroni)
**Ens-Vbr se adopta** si, en **al menos uno** de los dos puntos declarados:
- ΔF̄ (Ens-Vbr − Ens-V0r) ≥ +0.02;
- y el **IC del 97.5 %** (bootstrap pareado, 2000 bloques estación-mes, semilla [42, 29, 3], umbrales fijos) no incluye valores menores de 0.

El IC es del 97.5 % porque α = 0.05 se reparte entre las dos pruebas. El resto de la curva es descriptivo. Si no se cumple, se reporta como resultado negativo y **no se repite el examen** con otros parámetros.

## Predicciones (Claude, antes de abrir)
1. Con p99.9, Ens-Vbr supera a Ens-V0r con un IC del 97.5 % por encima de 0 (la regla pasa).
2. Con p99, ΔF̄ es positivo, pero su IC del 97.5 % puede incluir valores menores de 0.
3. Ens-Vbr con p99.9 y δ = 100 % logra F1 ≥ 0.65 (menos que el 0.752 de 2022, que fue optimista).
4. La tasa de falsas alarmas lograda en 2017–2019 limpio difiere de la nominal en más de un 30 % relativo, por el cambio entre 2023 y 2017–2019.
5. δ = 20 % sigue con F1 < 0.15 en todos los detectores.
