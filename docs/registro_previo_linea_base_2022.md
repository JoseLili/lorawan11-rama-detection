# Registro previo: línea base protegida (P1), umbral por estación (P4) y CUSUM (P5), sobre 2022

Fecha: 2026-11-04. Exploratorio, **solo 2022**. No abre 2023–2026, no entrena ni reentrena nada.
Este documento se escribe antes de calcular cualquier resultado de las variantes.

## Lo que ya se hizo (controles, sin resultados de variantes)
- Los zips 20–26 coinciden con `docs/checksums_2020_2026.txt`. Solo se abrieron 20, 21 y 22.
- Se regeneraron 31 matrices:
  - `limpia_2020_2022`;
  - los calendarios `entrenamiento_01…10` con δ = 100, 50 y 20 %.

  Las 31 son idénticas por SHA-256 a `resumen_matrices.csv`.
- Se cargó L0 de selección (`lstm_local_examen/c20/d50/seleccion/modelo_seleccion.keras`) y se reprodujeron los puntajes guardados en `dias_2022.csv.gz`:
  - diferencia máxima de 3.7 × 10⁻⁸ en `limpia_2022` y `entrenamiento_01`;
  - el mismo patrón de NaN.
- Entorno: TensorFlow 2.21.0, Keras 3.15.1, Windows, CPU AMD Ryzen 7 7700X (8 núcleos, 16 hilos). Es distinto del de Colab, lo que hay que declarar.

## Detector y evaluación (comunes a todo)
- **Modelo:** L0 de selección δ = 50 %, siempre el mismo, congelado.
- **Datos:** las horas de 2022 de los calendarios 01–10, con δ = 100, 50 y 20 %, y 2022 limpio.
- **Decisión:** `promedio_dia`, con un mínimo de 12 horas por estación-día y las mismas estación-días comunes para todas las variantes.
- **Umbral:** p99 común, propio de cada variante, sobre sus estación-días de 2022 limpio (`umbral_falsas_alarmas`), como en el repo.
- **Restricción:** las variantes solo cambian la línea base de la que salen la columna relativa y la a14. Arquitectura, pesos, σ y escala a14 no cambian.

## P1 — Las tres variantes de línea base
La línea base actual (V0) es la media de la misma hora en los 14 días anteriores (`perfil_causal`). Cada variante se aplica igual a las 32 estaciones, porque la a14 también usa la línea base de las vecinas.

| Variante | Definición exacta | Parámetros fijados ahora |
|---|---|---|
| **V0** | Actual | — |
| **Va: compuerta** | Si el puntaje diario de L0 de una estación supera *u*, ese día no entra a su perfil. El perfil es la media de esa hora en sus **últimos 14 días aceptados**, buscando hacia atrás. Se calcula día por día, de forma causal. | *u* = 0.0578, el p99 de V0 en 2022 limpio. Tope: tras **10** días seguidos excluidos, el siguiente se acepta. Calentamiento: la compuerta actúa desde el 1 de diciembre de 2021, así que los episodios de finales de 2021 también se filtran. |
| **Vb: anclada en vecinas** | base_s(t) = media de los perfiles de 14 días de sus 4 vecinas a esa hora + desfase_s(h). El desfase es la **mediana** de (x_s − media de las vecinas) a esa hora en los 60 días anteriores. | 60 días, con mediana: un episodio de 7 días mueve poco la mediana de 60. |
| **Vc: dos velocidades** | Se usa el perfil de 14 días, salvo que se aleje de la mediana de 60 días a esa hora más de τ_s; entonces se usa la de 60. | τ_s = p99 de \|P14 − Mediana60\| por estación, en **2020–2021 limpio**, sin mirar 2022. |

**Métricas, con δ = 100, 50 y 20 %:**
- **M1 (principal):** la tasa de falsa alarma en las estación-días normales a 1–14 días del fin de un episodio propio. En V0 con δ = 50 % es 10.7 % (282 de 2 632).
- **M2:** la tasa de falsa alarma en el resto de las estación-días normales de los calendarios atacados.
- **M3:** F1, recall y precisión por estación-día. También F̄, la media de F1 en los tres δ, con la misma definición de T1/T2.
- **M4:** el recall en los días ≥ 3 de un episodio. Mide el «acostumbramiento» durante el ataque.
- **Diagnóstico de Va:** cuántas veces se activó el tope de 10 días.

**Criterio de éxito de una variante:**
- M1 baja al menos a la mitad que en V0 con δ = 50 %;
- M2 no sube más de 0.2 puntos porcentuales;
- F̄ no baja.

Si M2 sube más, el modelo congelado no tolera la variante. Habría que reentrenar, y eso sería otra revisión.

**Predicciones (Claude, antes de calcular):**
1. Va y Vc reducen M1 al menos a la mitad con δ = 50 %. Vb lo reduce menos, porque cambia más las entradas del modelo.
2. El día 1 después del episodio sigue por encima del 15 % en todas: es la ventana de 24 horas, no el perfil.
3. Vb es la que más mueve M2.
4. El cambio en F̄ es pequeño, entre −0.01 y +0.03, porque las falsas alarmas tras el episodio son el 23 % del total.
5. M4 sube en Va y Vc.

## P4 — Umbral por estación (sobre los puntajes de V0; no requiere modelo)
- **Validación cruzada de 2022 limpio:** se ajusta con los meses impares y se mide en los pares, y luego al revés.
- **Umbral:** u_s = w_s · q_s + (1 − w_s) · u.
  - q_s es el p99 de la estación en los meses de ajuste;
  - u es el p99 común;
  - w_s = n_s / (n_s + 200), con n_s los días de ajuste de la estación.
- **Métricas:**
  - la dispersión entre estaciones de la tasa de falsa alarma en los meses de medición (desviación estándar y número de estaciones con 0 % o más de 2 %);
  - el F1 con δ = 100, 50 y 20 % en los calendarios, con el mismo esquema de meses.
- **Predicción:** la desviación estándar entre estaciones baja al menos 30 %, y el F̄ cambia menos de ±0.02.

## P5 — CUSUM por estación (sobre los puntajes de V0; no requiere modelo)
- **Fórmula:** y_d = log(puntaje diario) y S_d = max(0, S_{d−1} + y_d − k). Se alerta cuando S_d > h. Un día sin puntaje deja S igual.
- **Parámetros:**
  - k = p90 de y en 2022 limpio, común a todas las estaciones;
  - h tal que el 1 % de las estación-días limpias alerten;
  - los dos se ajustan con el esquema de meses impares y pares de P4.
- **Métricas:**
  - el F1 por estación-día con δ = 100, 50 y 20 %;
  - el retardo de detección, en días desde el inicio del episodio hasta la primera alerta;
  - M1.
- **Predicciones:**
  - el F1 con δ = 20 % sube frente a V0;
  - M1 **empeora**, porque CUSUM acumula el rastro de la línea base contaminada. Por eso P5 se repetiría sobre la mejor variante de P1.
