# Registro previo LB2: semillas y ensamble de Vbr y V0r

Fecha: 2026-11-04. Exploratorio, **solo 2020–2022**. No abre 2023–2026. Se corre en el PC del tesista (Windows, CPU AMD Ryzen 7 7700X, TensorFlow 2.21 y Keras 3.15), en la sesión de Python.

## Preguntas
1. **Robustez:** ¿la ventaja de Vbr sobre V0r con p99 (+0.036 en LB1, con una sola semilla) se mantiene con otras semillas de entrenamiento?
2. **Ensamble:** ¿promediar 5 modelos mejora el detector y permite que Vbr pase la regla de LB1?

## Qué se entrena
- **Semillas nuevas: 1, 2, 3 y 4** para V0r y para Vbr, es decir, 8 modelos. La semilla 42 es la de LB1 y se reutiliza cargada de disco, sin volver a entrenarla.
- **Lo único que cambia es `fijar_semilla(s)`**, justo antes de construir el modelo: cambia la inicialización, el barajado y el dropout.
- **El muestreo de ventanas queda fijo** (`lstm_local.muestra` con semilla 42), así que todas las semillas ven exactamente las mismas 1 357 800 ventanas.
- **Todo lo demás, igual que LB1:**
  - 20 calendarios con δ = 50 %;
  - validación con 2022;
  - EarlyStopping con paciencia 8, máximo 60 épocas y pesos de la mejor época;
  - la escala a14 de cada base, ajustada con 2020–2021 limpio.
- **Ensamble:** la media de los puntajes diarios de las 5 semillas de cada base. Todas comparten las mismas máscaras y estación-días.

## Evaluación (igual que LB1)
- **Datos:** 2022, calendarios 01–10 con δ = 100, 50 y 20 %, `promedio_dia` y las estación-días comunes a todos los modelos.
- **Umbral:** p99 (principal) y p99.9 (secundario), propios de cada modelo, sobre su 2022 limpio.
- **Bootstrap pareado** de bloques estación-mes, con 2000 remuestreos, semilla [42, 29, 3] y umbrales fijos.

## Reglas de decisión
- **R1, robustez (pregunta 1):** la ventaja es robusta si ΔF̄ con p99 (Vbr_s − V0r_s) es > 0 en **al menos 4 de las 5** semillas y su media es ≥ +0.02.
- **R2, ensamble (pregunta 2, la principal):** Vbr pasa a «adoptado para el examen final» si, en Ens-Vbr − Ens-V0r con p99, ΔF̄ ≥ +0.02 **y** el IC 95 % no incluye valores menores de 0.
  - Una ventaja solo con p99.9 se reporta como secundaria, igual que en LB1.
- **Descriptivo:** el ensamble frente a la media de sus semillas individuales, para cada base.

**Advertencia:** 2022 sirve también para el EarlyStopping de cada semilla, así que los números son optimistas para todos por igual. La cifra para el paper debe salir del examen final.

## Predicciones (Claude, antes de entrenar)
1. Al menos 7 de los 8 modelos nuevos eligen E = 1 o E = 2.
2. ΔF̄ con p99 es positivo en al menos 4 de 5 semillas.
3. Con p99, Ens-Vbr − Ens-V0r tiene ΔF̄ entre +0.02 y +0.06, con un IC que no incluye valores menores de 0 (R2 pasa).
4. El ensamble sube el F̄ con p99 de cada base al menos 0.01 frente a la media de sus semillas.
5. Con p99.9, Ens-Vbr llega a F1 ≥ 0.68 con δ = 100 %.
