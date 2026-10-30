# Redacción: V4 → V4S → L0 como escalera de ablación

Borrador de Claude, 2026-10-27, a pedido del tesista, para recuperarlo al redactar la tesis o al
preparar la defensa. Los números salen de las revisiones 18 y 18b (`docs/protocolo_anomalias_red_v1.md`,
`results/anomalias_red_v1/revision18/`). Son del examen 2025, con modelos cargados de disco.

## La idea central

No se cuenta como una "evolución" ("fuimos mejorando el V4"). Se cuenta como **una comparación
escalonada**: V4, V4 supervisado y L0, ordenados de menos a más parecido a L0.

**Corrección del 2026-10-30 (revisión externa del deck):** la versión anterior decía que cada peldaño
«cambia un solo factor». No es cierto. Del V4 al V4S compartido cambian a la vez la supervisión, el
objetivo (predecir contra clasificar), el acceso a la propia lectura de la estación, la ventana
(hasta t−1 contra hasta t) y el modelo compartido con estaciones ordenadas por distancia
(`src/detect/v4_supervisado.py`). Por eso la escalera **no separa** cuánto aportan las etiquetas, el
perfil o las vecinas. Lo que sí sostiene: dar etiquetas al comparador implementado no elimina la
ventaja de L0.

## Párrafo para la tesis

> La comparación directa entre L0 (supervisado) y el V4 (no supervisado) mezcla el uso de etiquetas
> con otras diferencias de diseño. Para acotar esa objeción se construyó un comparador supervisado a
> partir del V4 (V4S compartido), entrenado con los mismos calendarios, el mismo modelo único
> (δ = 50 %), y evaluado en las mismas estación-días y con los mismos umbrales que L0:
>
> 1. **V4:** las entradas de la parte 1, sin etiquetas; predice la lectura siguiente.
> 2. **V4S compartido:** las entradas del V4 más la lectura de la propia estación, con etiquetas, un
>    solo modelo para las 31 estaciones (las demás ordenadas por distancia).
> 3. **L0:** el mismo entrenamiento supervisado que el V4S, con entradas relativas al perfil de 14
>    días y a las 4 vecinas.
>
> Del V4 al V4S cambian varias cosas a la vez y el resultado se movió poco (PR-AUC 0.39 → 0.36 con
> δ = 100 %; 0.10 → 0.11 con δ = 50 %); del V4S a L0 cambian las entradas y la diferencia fue grande
> (F1 con δ = 50 % y p99: 0.18 → 0.45). Se concluye que la ventaja de L0 no desaparece cuando el
> comparador también recibe etiquetas. El diseño no permite atribuir esa ventaja a un factor
> específico (etiquetas, perfil o vecinas); que R3, una regla sin entrenamiento basada en el perfil y
> las vecinas, también supere al V4 es consistente con que las entradas importen, pero no lo demuestra.

## El tropiezo del V4S por estación, sin esconderlo

> Una primera versión del V4S conservó el esquema del V4 de un modelo por estación. En la
> validación de 2022, 11 de 31 modelos no aprendieron: cada uno veía unas 300 horas atacadas. Esta
> limitación se había declarado antes de entrenar. Se agregó entonces una versión compartida,
> equivalente en entrenamiento a L0, y ambas se evaluaron en el examen. La comparación principal
> se fijó por diseño antes de ver resultados.

## Respuesta corta para el sinodal: ¿por qué se hizo?

> "Porque mi asesor señaló que comparar un método supervisado contra uno no supervisado no
> permite saber de dónde viene la ventaja. Diseñé una comparación en la que solo cambia una cosa a
> la vez. El resultado mostró que lo que funciona es comparar cada estación con su propia historia
> y con sus vecinas; las etiquetas aportan poco por sí solas."

## Por qué no es truqueado (argumentos)

1. **El examen no se usó para diseñar.** El V4S se registró antes de entrenar y 2024–2026 se miró
   una sola vez. Git guarda las fechas.
2. **El único cambio a medio camino (18b) fortaleció al rival.**
3. **No hubo elección a conveniencia.** Los dos V4S se reportan, y la comparación principal se fijó
   antes de los resultados.
4. **Las predicciones no salieron todas a favor:** se cumplieron 5 de 6.
5. **Los controles salieron idénticos:** entrenamientos y evaluación repetidos, y la revisión 17
   reproducida.
6. **Se reporta lo que no favorece a L0:** el empate con δ = 100 % y p99 en 2026, y que con
   δ ≤ 10 % nadie detecta.

## Límites que conviene declarar uno mismo

1. **Asimetría de esfuerzo.** L0 salió de unas 9 revisiones (de la 6 a la 14) y el V4S tuvo 2
   intentos. Atenuante: la misma arquitectura y los mismos hiperparámetros, heredados del V4, sin
   ajuste para ninguno. Lo que L0 tuvo de más fue diseño de entradas, que es lo que la tesis
   afirma que importa.
2. **El V4S compartido se sobreajusta rápido (E = 3).** No se probó regularización ni otro orden de
   columnas.
3. **Ordenar por distancia fue una sola opción,** sin alternativas probadas.
4. **Anomalías sintéticas y una sola semilla.**

## Para la redacción: cómo blindar la tesis contra «se ve truqueado» (2026-10-27)

Pedido del tesista: tenerlo a la mano cuando se pase a escribir.

**Lo que tumba una tesis** no es haber iterado. Es que el sinodal descubra algo no declarado, o
afirmar más de lo que la evidencia sostiene.

**El punto delicado que hay que decir primero:**
- algunas revisiones de L0 (7, 8 y 10) se registraron **después de ver resultados de 2024**,
  como dice la sección 15 del protocolo;
- por eso 2024 no es un examen totalmente limpio para L0;
- **el examen independiente es 2025–2026**, que no se usó para ninguna decisión.

Redacción sugerida:

> El periodo 2024 se utilizó como prueba durante el desarrollo y orientó algunas revisiones del
> diseño; la evaluación independiente corresponde a 2025–2026, que no se utilizó para ninguna
> decisión.

**Sobre el «cambio de enfoque»:**
- sí puede contarse que **la pregunta cambió**: de «¿el V4 sirve para anomalías de red?» a «¿qué
  necesita ver un detector para separar un ataque del clima?». Es legítimo y es la aportación;
- no debe usarse como disfraz para que no se note que L0 tuvo más intentos que el V4S.

**Cinco medidas concretas:**
1. **Afirmar sólo lo demostrado:**
   - sí: «con este entrenamiento y estas condiciones, L0 supera al comparador supervisado derivado
     del V4»; no: «la ventaja se debe a la representación y no a las etiquetas»;
   - no: «L0 es mejor que cualquier V4 supervisado posible».
2. **El historial de revisiones como anexo,** con la columna «registrada antes o después de ver
   qué». Es la mejor defensa, porque es transparente.
3. **Separar explícitamente desarrollo y examen:** 2020–2022 y 2024 para desarrollar; 2025–2026
   como examen único.
4. **Declarar la asimetría de esfuerzo como límite,** con su atenuante: la misma arquitectura y los
   mismos hiperparámetros para los dos; lo que L0 tuvo de más fue diseño de entradas, que es lo
   que la tesis afirma.
5. **Opcional, como seguro:** 2 o 3 intentos razonables más del V4S compartido (por ejemplo, más
   regularización) **sólo con 2022**, registrados antes, sin tocar el examen. Si ninguno se acerca
   a L0 en 2022 (hoy ROC-AUC de 0.873 contra 0.976), la crítica «no te esforzaste con el rival»
   pierde fuerza. No se ha decidido hacerlo.

## Idea pendiente

Una gráfica de tres barras por δ (V4 → V4S compartido → L0), con su ficha, para mostrar la
escalera en una sola imagen.
