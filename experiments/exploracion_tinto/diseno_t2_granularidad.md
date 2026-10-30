# TINTO T2 — ¿qué imagen conviene? Registro previo (2026-10-29)

Escrito **antes** de entrenar o mirar cualquier resultado de T2. Pedido del tesista el 2026-10-29:
(1) reentrenar T1 sin parada manual y (2) comparar cuatro formas de armar la imagen. El tesista
autorizó Colab con GPU para esta exploración: la reproducibilidad exacta entre corridas deja de ser
requisito aquí (la GPU no es determinista); se reporta la variación entre dos corridas en su lugar.

## Pregunta

¿Alguna forma de convertir los datos en imagen TINTO le gana a L0 en 2022? Si ninguna, ¿cuál es la
menos mala y cuánto pesa la forma de la imagen?

## Las cuatro variantes

Todas usan las mismas columnas que L0: las 98 de `evaluacion_red.entradas_de('vecinas', ...)`
(relativa al perfil de 14 días, máscara y columna de vecinas a14 de las 32 estaciones, más seno y
coseno de la hora), con la normalización heredada de L0. La etiqueta nunca es entrada.

| Clave | Una imagen por… | Contenido | Entradas | Imagen | Salidas |
|---|---|---|---|---|---|
| **EH** | estación y hora (= T1) | horas t−23…t, estación + 4 vecinas (17 col.) | 408 | 32 × 32 | 1 |
| **ED** | estación y día | horas 00…23 del día, estación + 4 vecinas | 408 | 32 × 32 | 1 |
| **RH** | hora, toda la red | horas t−23…t, las 98 columnas | 2 352 | 64 × 64 | 31 |
| **RD** | día, toda la red | horas 00…23 del día, las 98 columnas | 2 352 | 64 × 64 | 31 |

- **EH** es el reentreno de T1: mismo mapa, misma escala y mismas ventanas de ajuste (1 de cada 8
  horas por estación, `lstm_local.muestra`) y de validación. Ahora con EarlyStopping completo.
- **ED** usa el mapa y la escala de T1 (las 408 columnas significan lo mismo). Etiqueta: la
  estación-día está dentro de un episodio (`estacion_dia.etiquetas`). Solo estación-días con al
  menos 12 horas con dato de la estación, como en la evaluación.
- **RH y RD** usan un mapa nuevo: TINTO-PCA (TINTOlib 1.3.1, sin difuminado) ajustado con una muestra
  de 20 000 ventanas de red de 2020–2021 de los calendarios d50, MinMax sin recorte, y la misma
  asignación única de T1 (mínima suma de distancias, `linear_sum_assignment`) en 64 × 64. RD reusa el
  mapa de RH. Una salida por objetivo, en el orden de los 31 objetivos.
  - RH: todas las horas de 2020–2021 (ajuste) y de 2022 de los calendarios 01–10 (validación).
    Etiqueta por hora como L0 (`etiquetas_por_hora`), sin enmascarar.
  - RD: todos los días. Pérdida enmascarada en las estación-días con menos de 12 horas con dato.

## Entrenamiento (igual para las cuatro)

- 20 calendarios con δ = 50 %; ajuste 2020–2021; validación 2022 con los calendarios 01–10.
- CNN de la misma familia que T1: Conv 8 (3×3) → pool 2 → Conv 16 (3×3) → pool 2 → densa 32 →
  dropout 0.2 → sigmoide (1 o 31 salidas). Adam 0.001, entropía cruzada binaria, lote 64.
  Con 64 × 64 la densa tiene más pesos; se informa el número de parámetros.
- EarlyStopping sobre la pérdida de validación, paciencia 8, máximo 60 épocas, se restauran los
  mejores pesos. **Sin parada manual.**
- `fijar_semilla(42)` antes de construir y antes de entrenar. GPU de Colab.
- **Dos corridas por variante** con la misma semilla. En GPU no salen idénticas: la diferencia mide
  el ruido del entrenamiento.

## Evaluación (igual que T1)

- 2022 limpio y calendarios 01–10 con δ = 100, 50 y 20 %.
- EH y RH: probabilidad por hora, sólo horas con dato del objetivo, promedio del día con mínimo 12
  horas. ED y RD: una probabilidad por estación-día directamente.
- **Las mismas 9 661 estación-días comunes de T1** (`dias_comunes.csv`), para comparar contra los
  puntajes de L0 ya guardados (cargado de disco, sin reentrenar) y contra T1 época 5.
- Umbral propio de cada detector con 2022 limpio en esos días: p99 (1 %) y p99.9 (0.1 %).
- F1, recall y precisión agrupando los 10 calendarios; control sin ataque; IC95 bootstrap pareado
  contra L0 (2000 remuestreos, bloques estación-mes, semilla [42, 29, 3]).

## Regla de decisión (fijada ahora)

- Medida principal: **F̄ = promedio del F1 con p99 en δ = 100, 50 y 20 %**. L0 en estos días: 0.3550.
- Una variante **merece pasar a un protocolo propio** sólo si F̄ ≥ 0.3550 + 0.02 = **0.3750 en sus dos
  corridas** (el margen de 0.02 es el mismo de las revisiones 10 y 13).
- Si ninguna llega: TINTO queda cerrado como resultado negativo; se reporta el orden de las cuatro
  variantes como descripción, no como elección.
- La forma de la imagen "importa" si la mejor variante supera a la peor por más que la diferencia
  entre las dos corridas de cada una.
- No se agregan variantes, épocas ni umbrales después de ver resultados. No se abren 2023–2026.

## Límites que se declaran desde ahora

- 2022 se usa para el EarlyStopping y para la evaluación (igual que en L0 y en T1): sirve para
  comparar, no como desempeño absoluto.
- Una sola arquitectura pequeña por variante; no hay búsqueda de hiperparámetros.
- RD tiene pocas imágenes de ajuste (731 días × 20 calendarios = 14 620); si pierde, puede ser por
  falta de ejemplos y no por la forma de la imagen.
- Sin difuminado: es TINTO-PCA modificado (asignación única), no TINTO tal cual.
