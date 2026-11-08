# Registro previo de la revisión 23b (D1): sesgo sostenido y deriva lenta

Fecha: 2026-11-07. **Estado: aprobado por el tesista el 2026-11-07.** Se corre **después** de la revisión 24. No se ha generado ningún plan, matriz ni puntaje de esta revisión; sólo se contaron fechas en los calendarios para saber cuántos episodios caben.

## Pregunta
El ataque «lento» de red team consiste en alterar una estación poco a poco, o durante semanas, para que las bases se acostumbren. Las bases que lo pueden absorber son el perfil de 14 días de V0, la mediana de 60 días de Vb y la mediana de 14 días de R3. La revisión pregunta:
1. **Persistencia:** con un sesgo constante de varias semanas, ¿hasta cuándo detecta cada detector?
2. **Rampa:** si el sesgo crece despacio, ¿se escapa?
3. **Rebote:** cuando el ataque termina, ¿la base contaminada genera falsas alarmas?

Es la fase 2 (D1) de la hoja de ruta. El sesgo fijo corto ya se midió en la revisión 23 (episodios de 1–7 días). **No se elige ni se cambia ningún modelo.**

## Datos y planes
- **Banco:** 2024, 2025 y enero–julio de 2026, validados, con historia desde 2020 (como en la revisión 23).
- **Episodios largos derivados de los 30 calendarios del banco.** Se recorren los episodios de cada calendario en orden de inicio, conservando la estación, el día de inicio y el signo. La duración se fija en **L = 56 días** (8 semanas). Un episodio se conserva sólo si:
  - cabe completo en el año (en 2026, termina a más tardar el 31 de julio);
  - ni la misma estación ni ninguna de sus vecinas de Vb (en las dos direcciones) tiene otro episodio conservado a menos de 60 días. Así la historia previa y el periodo de rebote están limpios, y no hay ataques coordinados.
- **Resultado del conteo de fechas:** 240 episodios, 99 en 2024, 90 en 2025 y 51 en 2026. Los planes se generan y se guardan con su SHA-256 (LF) antes de puntuar.

## Formas de la alteración
Las tres son aditivas en ppb. Se aplica x + o(t) con signo + y max(x − o(t), 0) con signo −. Se redondea a entero como `ar.aplicar_fijo` y las horas sin dato siguen sin dato. *h* = horas desde el inicio del episodio.

| Forma | o(t) | Qué imita |
|---|---|---|
| **Escalón** | A desde la primera hora | Sesgo sostenido; es el error fijo de la revisión 23, pero de 8 semanas |
| **Rampa 28** | A · min(1, h / (28 · 24)): sube 28 días y se mantiene 28 | Arranque lento hasta un sesgo fijo |
| **Deriva 56** | A · h / (56 · 24): sube las 8 semanas | Deriva de calibración, o ataque que nunca se detiene |

- **Magnitudes:** A = 20 y 40 ppb. En la revisión 23 eran las que se detectaban bien en episodios cortos.
- **Matrices:** 30 calendarios × 3 formas × 2 magnitudes = **180** por corrida, más los años limpios.
- **Comprobación antes de puntuar:** el escalón debe dar exactamente lo mismo que `ar.aplicar_fijo` con los mismos planes.

## Detectores
Los mismos de la revisión 23, congelados y con sus umbrales de 2023: Ens-Vb-R, Ens-V0-R, L0 único, R3 y PARAAD-SA. La inferencia es idéntica bit a bit a la de la calibración.

## Métricas
- **Etiquetas:** los 56 días de cada episodio son positivos, incluidos los primeros días de la rampa, cuando el cambio aún es pequeño. Los días posteriores son negativos.
- **Recall por semana desde el inicio (1–8),** con p99 y p99.9, por detector, forma y A. Se acompaña del cambio real medio de cada semana (ppb).
- **Detección del episodio:** fracción de episodios con al menos una alarma, y mediana del día de la primera alarma.
- **Rebote:** tasa de alarmas de la estación en las 8 semanas posteriores al fin del episodio, por semana, frente a su tasa en el año limpio.
- F1, recall y precisión por variante. Sólo se comparan detectores dentro de la misma variante.
- **Estación-días evaluables:** como en la revisión 23 (válidas para los cinco detectores).
- **Intervalos:** bootstrap pareado de bloques estación × mes, 2 000 remuestreos, semilla [42, 23, 2].

## Preguntas declaradas (p99, IC del 95 %)
- **Q1, persistencia:** escalón con A = 20, recall en las semanas 5–8, PARAAD − Ens-Vb-R.
- **Q2, rampa:** rampa 28 con A = 20, recall en las semanas 1–4, Ens-Vb-R − Ens-V0-R.
- **Q3, rebote:** escalón con A = 20, tasa de alarmas de Ens-Vb-R en las 4 semanas posteriores al fin, menos su tasa en limpio.
- **Q4, deriva:** deriva 56 con A = 40, recall de las 8 semanas, Ens-Vb-R − PARAAD.

## Predicciones (Claude, antes de generar nada, según cómo se construyen las bases)
1. **Escalón A = 20:** Ens-Vb-R detecta la semana 1 (recall ≥ 0.7) y queda ciego en las semanas 5–8 (≤ 0.3). La mediana de 60 días resiste hasta que más de la mitad de sus días están alterados, unos 30 días.
2. **Ens-V0-R, L0 único y R3 se ciegan antes:** recall ≤ 0.3 ya en la semana 3, porque su base de 14 días absorbe el sesgo en 1–2 semanas.
3. **PARAAD casi no cambia con el tiempo,** porque no usa historia: |semanas 5–8 − semana 1| < 0.10. En Q1 le gana a Ens-Vb-R (IC > 0).
4. **Q2 > 0 (IC > 0):** en la rampa, Vb resiste mejor que V0, porque la mediana de 60 días sigue limpia mientras la rampa sube.
5. **Q3 > 0 (IC > 0):** al terminar un escalón, Ens-Vb-R tiene un rebote de falsas alarmas de ≥ 3× su tasa en limpio en las 4 semanas siguientes. En V0 el rebote dura menos (≈ 2 semanas).
6. **Deriva 56:** con A = 20, el recall de Ens-Vb-R en las 8 semanas es < 0.3. Con A = 40, PARAAD le gana (Q4 < 0, IC < 0).

## Límites declarados desde ya
- **El banco no es virgen** (revisiones 16–23). Esto describe detectores congelados; no se elige nada.
- **Sólo hay error aditivo.** La deriva de ganancia (multiplicativa) queda fuera.
- **Barcelona (rev.20c) no entra:** el escenario de sesgo de PARAAD en sus datos queda como opcional.
- **Episodios aislados de sus vecinas:** lo coordinado ya se midió en la revisión 23.

## Cómputo estimado
180 matrices por corrida, con la misma tubería de la revisión 23 (4 procesos × 4 hilos): ≈ 25 min por corrida y ≈ 50 min con las dos. Más ≈ 30 min de implementación.

## Enmienda (2026-11-07, antes de generar nada): Ens-Vb-X entra como detector
- **Ens-Vb-X entra como sexto detector,** con el τ y los umbrales de 2023 que fije la revisión 24, salga como salga su regla de adopción. Si se adopta, es el detector principal; si no, es descriptivo.
- **Predicción 7:** Ens-Vb-X ≈ Ens-Vb-R en D1 (|Δrecall| < 0.03 en cada semana del escalón con A = 20).
  - La regla sólo actúa si una vecina se desvía junto con *s*, y aquí las vecinas están limpias.
  - Además, no toca la mediana de 60 días, que es la que absorbe el sesgo sostenido.

## Precisiones (2026-11-07, antes de generar planes o puntajes)
1. **Semana *w*:** los días 7(*w* − 1) + 1 … 7*w* desde el inicio del episodio, donde el día 1 es el del inicio. Las semanas posteriores al fin se cuentan igual, desde el día siguiente al último del episodio.
2. **Estación-días evaluables:** las válidas en el año limpio para todos los detectores de la revisión, incluido Ens-Vb-X si la revisión 24 fija su τ.
3. **Rebote.**
   - Tasa de alarmas de la estación atacada en sus días posteriores al fin.
   - Por construcción, ni ella ni sus vecinas tienen otro episodio en los 60 días siguientes, así que esos días son limpios.
   - **Duración del rebote:** el número de semanas posteriores consecutivas, desde la primera, con una tasa ≥ 2 × la tasa del detector en el año limpio.
   - La predicción 5 se cumple si Q3 > 0 (IC > 0), si la razón de Ens-Vb-R en las semanas 1–4 es ≥ 3 y si la duración de Ens-V0-R es menor que la de Ens-Vb-R.
4. **Q3 en el bootstrap:** las tasas tras el fin y en limpio usan los mismos pesos de bloque estación × mes.
5. **Cómo se juzgan las predicciones.**
   - Las 1, 2, 6 (A = 20) y 7 se juzgan con valores puntuales.
   - Las 3, 4, 5 y 6 (A = 40) incluyen la condición del IC indicada.
6. **Comprobación sin puntajes:** el escalón debe dar `rec` y `cam` idénticos a `ar.aplicar_fijo` con A = 20 y 40 en todos los planes largos.
