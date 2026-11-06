# Registro previo EP1: decisión por episodio con puntajes estandarizados por estación

Fecha: 2026-11-04. Exploratorio, **solo 2022**. **No se entrena nada**: se usan los puntajes ya guardados de LB1 (`results/linea_base/lb1/puntajes_2022.npz`) de Vbr, V0r y el L0 guardado. No se abre 2023–2026.

## Pregunta
Con el umbral estricto, Vbr tiene precisión alta (0.75–0.81) y recall bajo (0.59 con δ = 100 % y 0.36 con δ = 50 %). Los ataques duran de 1 a 7 días, pero hoy cada día se decide por separado.

¿Acumular evidencia entre días seguidos de la misma estación sube el recall sin perder precisión?

## Estandarización (común a todas las reglas)
- Para cada estación s y día d: p(s, d) = (1 + #{días limpios de calibración de s con puntaje ≥ puntaje(s, d)}) / (n_s + 1).
- Sorpresa: e(s, d) = −ln p(s, d).
- **Calibración cruzada por meses**, como en P4: los días de los meses pares usan como referencia los días limpios de los meses impares de 2022, y al revés. La referencia es siempre el 2022 limpio del mismo modelo.
- Los días sin puntaje (menos de 12 horas) no cuentan: S se conserva y la ventana de días se salta ese día.

## Reglas comparadas (fijadas ahora)

| Regla | Definición | Parámetros |
|---|---|---|
| **D: diario** (referencia) | Alerta si p(s, d) ≤ α | α fijado por el nivel de falsas alarmas |
| **C: CUSUM estandarizado** | S_d = max(0, S_{d−1} + e(s, d) − k). Alerta si S_d > h. Sin reinicio | **k = 2**. h fijado por el nivel de falsas alarmas |
| **R: 2 de 3** | Alerta en d si al menos 2 de los últimos 3 días con puntaje de s tienen p ≤ q | q fijado por el nivel de falsas alarmas |

- **Niveles:** el α, h o q de cada regla y modelo se elige para que la tasa de alertas en 2022 limpio sea **1 %** (equivalente a p99) o **0.1 %** (equivalente a p99.9). Se elige en los meses de calibración del pliegue y se aplica en los de medición, en los dos pliegues.
- **Modelos:** las tres reglas se aplican a **Vbr y a V0r** («peras con peras»), con el L0 guardado como referencia.

## Métricas
- **F1, recall y precisión por estación-día** con δ = 100, 50 y 20 %, y su media F̄. Son las mismas estación-días comunes de LB1 y los calendarios 01–10.
- **Por episodio:** fracción de episodios que empiezan en 2022 con al menos una alerta dentro, y retardo mediano en días desde el inicio hasta la primera alerta.
- **Falsas alarmas tras el episodio** (M1, días 1–14 después del fin) y **tasa en 2022 limpio**, para verificar el nivel.
- **Bootstrap pareado** de ΔF̄, con 2000 bloques estación-mes, semilla [42, 29, 3] y umbrales fijos.

## Regla de avance
**C sobre Vbr** pasa a propuesta para el examen final si, frente a **D sobre Vbr**:
- con 0.1 % (principal en EP1, porque la pregunta es el recall con el umbral estricto), ΔF̄ ≥ +0.02 y el IC 95 % no incluye valores menores de 0;
- y con 1 %, F̄ no baja más de 0.01.

R se reporta como contraste y no puede pasar por sí sola. Si R gana a C, se anota como observación para un registro nuevo.

## Predicciones (Claude, antes de calcular)
1. Con 0.1 %, C sobre Vbr sube el recall con δ = 50 % de 0.36 a al menos 0.50.
2. Con 0.1 %, C sobre Vbr llega a F1 ≥ 0.70 con δ = 100 %.
3. Con δ = 20 %, el F1 sigue por debajo de 0.15 con las tres reglas.
4. M1 empeora con C frente a D, por el arrastre al final del episodio.
5. R queda entre D y C en F̄ con 0.1 %.
6. La ventaja de C sobre D es mayor con 0.1 % que con 1 %.
