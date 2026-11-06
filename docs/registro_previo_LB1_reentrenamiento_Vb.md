# Registro previo LB1: reentrenar L0 con la línea base anclada en vecinas (Vb)

Fecha: 2026-11-04. Exploratorio, **solo 2020–2022**. No abre 2023–2026.

Antecedente: en la exploración previa, Vb redujo de 10.7 % a 3.2 % las falsas alarmas tras un episodio, con el mismo PR-AUC que V0 (0.477 contra 0.474). Con el modelo congelado bajó el F̄ por calibración: el p99 limpio pasó de 0.058 a 0.133. LB1 prueba si reentrenar corrige eso.

## Qué se entrena
Dos modelos, en la misma máquina, con el mismo código y la misma semilla. Así la comparación es «peras con peras» y ninguna diferencia viene del entorno.

| Modelo | Línea base de las entradas | Para qué |
|---|---|---|
| **L0-V0r** | Actual (`perfil_causal`, 14 días) | Comparador principal: L0 reentrenado aquí |
| **L0-Vb** | Vb: media de los perfiles de 14 días de las 4 vecinas + mediana causal de 60 días de (x_s − media de las vecinas) a esa hora; si falta, la base actual | Candidato |

**Igual que la fase de selección de la revisión 14 (`entrenar_lstm_local.py`):**
- **Datos de entrenamiento:**
  - 20 calendarios `entrenamiento_01…20` con δ = 50 %;
  - horas de 2020–2021, 1 de cada 8 por calendario y estación (`lstm_local.muestra`), en total 1 357 800 ventanas.
- **Validación:** 1 de cada 8 horas de 2022 de los calendarios 01–10.
- **Arquitectura y entrenamiento:**
  - LSTM 64, dropout 0.2, densa 32 y sigmoide;
  - Adam 0.001, BCE, batch 64 y `shuffle`;
  - `fijar_semilla(42)` justo antes de construir el modelo;
  - EarlyStopping sobre val_loss, paciencia 8, máximo 60 épocas y pesos de la mejor época.
- **Ajuste de la escala:**
  - σ, la misma que hoy;
  - la escala a14, ajustada con 2020–2021 limpio **con la línea base de cada modelo**. Para Vb se recalcula, porque sus entradas cambian.
- **Sin fase definitiva** (2020–2022): esta revisión no va a examen.

**Entorno:** TensorFlow 2.21.0, Keras 3.15.1, Windows, CPU AMD Ryzen 7 7700X (8 núcleos, 16 hilos). El L0 original es de Colab x86_64, del 2026-10-25.

## Control de reproducción (L0-V0r contra el L0 guardado)
El L0 guardado eligió E = 1 (val_loss 0.02245, 9 épocas). Como un modelo de una época es sensible al entorno, solo se exige cercanía:
- E entre 1 y 3;
- val_loss mínimo dentro de ±10 % de 0.02245;
- F̄ con p99 dentro de ±0.03 de 0.355.

Si no se cumple, se reporta y la comparación principal sigue siendo Vb contra V0r, que comparten entorno.

## Evaluación (sobre 2022, igual que la exploración previa)
- **Datos:** todas las horas de 2022 de los calendarios 01–10 con δ = 100, 50 y 20 %, y 2022 limpio.
- **Decisión:** `promedio_dia`, con un mínimo de 12 horas y las estación-días comunes a todos los modelos.
- **Umbrales:**
  - **p99 (principal)** y **p99.9 (secundario)**, propios de cada modelo, sobre su 2022 limpio;
  - el p99.9 descansa en unas 11 excedencias, así que es inestable y se reporta, pero no decide por sí solo.
- **Métricas:**
  - F̄ (media del F1 con δ = 100, 50 y 20 %), y F1, recall y precisión por δ, con los dos umbrales;
  - M1 (falsas alarmas a 1–14 días del fin de un episodio propio) y M2 (resto de días normales);
  - PR-AUC y M4 (recall en el día ≥ 3 del episodio).
- **Incertidumbre:** bootstrap pareado de ΔF̄ (Vb − V0r), con 2000 remuestreos de bloques estación-mes, los calendarios juntos y los umbrales fijos, semilla [42, 29, 3]. El esquema es el de T1.

**Advertencia:** 2022 también es el conjunto del EarlyStopping. Los números son optimistas para **los dos** modelos por igual y no sustituyen a un examen.

## Regla de avance
Vb pasa a proponer un protocolo de examen propio, sobre un holdout nuevo de un solo uso, si:
- ΔF̄ con p99 ≥ +0.02 en el valor puntual, y el intervalo del 95 % no incluye valores menores de 0;
- y M1 con δ = 50 % es como mucho la mitad del de V0r.

Una ventaja que aparezca solo con p99.9 se reporta como observación secundaria, no adoptable, igual que en T2.

## Predicciones (Claude, antes de entrenar)
1. V0r cumple el control de reproducción.
2. Con δ = 50 %, M1 de Vb ≤ 4 %, y M1 de V0r entre 8 y 13 %.
3. El p99 limpio de Vb queda a menos de 1.3 veces el de V0r. El reentrenamiento corrige la calibración.
4. ΔF̄ con p99 entre 0 y +0.04.
5. ΔF̄ con p99.9 es mayor que con p99.
6. El PR-AUC de Vb con δ = 50 % es ≥ al de V0r.
