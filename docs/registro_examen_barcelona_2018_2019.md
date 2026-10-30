# Registro previo al examen Barcelona 2018–2019

Fecha: 2026-10-29. El tesista autoriza evaluar los dos años después de congelar
entrenamiento y calibración. No se habían calculado métricas de detección de
Barcelona al registrar este documento.

## Diseño congelado

Modelos: L0 único entrenado d50, 13 V4 y PARAAD-SA dropout0.1/481 épocas.
Se cargan los definitivos r1 ya verificados, sin entrenar ni modificar pesos,
épocas, escalas o umbrales. Calibración 2017: p99 y p99.9 de
`calibracion_2017_colab/recuperado/salidas/calibracion/congelado.json`, y p95
por estación V4 del mismo directorio. Se registran hashes en el paquete.

Prueba principal 2018 y complementaria 2019: diez calendarios por año,
δ={100,50,20,10,5}%, mismos planes, signos, valores alterados y máscara para
los tres métodos. Son 100 matrices alteradas y dos limpias, no nuevos sorteos.
Universos previamente fijados: 4,549 estación-días2018 y 4,567 estación-días2019.
Etiqueta positiva diaria: pertenencia al episodio programado. No se modifica
por δ ni por cuál detector produzca alerta. Los ceros/lecturas que no cambian
tras redondear se conservan y constan en los controles de inyección.

Puntajes y agregación idénticos a calibración: probabilidad media diaria L0;
absoluto de media firmada de residuo V4 dividido por p95 propio congelado;
MAE observado estandarizado PARAAD. Mínimo12 horas y soporte común diario
preexistente. Alerta estricta puntaje>umbral, sin recalibración en 2018/2019.
El historial antes de cada año es limpio; el contexto dentro de cada variante
incluye sus ataques pasados, como en las matrices ya generadas.

## Ejecución y controles

Sólo CPU, entorno TensorFlow2.21.0/Keras3.13.2 y determinismo de calibración.
Se repite toda la inferencia dos veces por matriz y se exige igualdad exacta
en el mismo entorno. No se reutilizan predicciones de otra matriz por una
aproximación de contexto. Los modelos se pueden cargar una vez por proceso:
son recurrentes sin estado entre ventanas y siempre se llama training=False.

Para reducir transferencia, se permite codificar las entradas como matriz
limpia más parches dispersos de valores/perfiles/z/características. Cada
reconstrucción debe coincidir **bit a bit** con los arrays ya generados y
verificados, comprobando forma, dtype y SHA-256 de sus bytes. Es compresión
de representación, sin cambiar entradas, escalas ni resultados. Se incluyen
los metadatos/etiquetas y las 24 horas previas necesarias para recortar ventanas;
los perfiles ya incorporan todo su pasado causal.

Se verifica el control limpio2017 contra puntajes congelados para detectar
cambios de implementación/entorno. La duplicación interna exige igualdad
exacta; la comparación con otra VM admite tolerancia numérica1e-6 (rtol/atol),
registrando diferencia máxima y número de alertas que cambien por redondeo
numérico cerca del umbral. No se desplazan umbrales para corregir diferencias.
Si se supera esa tolerancia, detener antes del examen e investigar el entorno.

## Métricas y comparación

- TP, FP, FN, TN, precisión, recall, F1 principal p99 y F2 secundaria;
  p99.9 como segundo punto. Precision/recall/F si su denominador es cero
  se informan como0, con conteos para interpretarlo; áreas sin ambas clases
  son indefinidas y se dejan como NaN.
- PR-AUC se especifica como average precision, ROC-AUC por rangos con empates.
- Métricas por calendario y agregadas por suma de confusiones de los diez
  calendarios de cada año/δ/umbral. El mismo caso ambiental aparece diez
  veces; no se trata como diez muestras independientes.
- Control «sin ataque»: puntuar la matriz limpia usando las mismas etiquetas
  programadas de cada calendario. Separado de la tasa limpia anual, donde
  todos los casos son negativos experimentales.
- IC95% mediante2,000 remuestreos de bloques estación×mes observados,
  semilla `[42,238,año]`. Cada bloque mantiene juntas sus diez realizaciones
  y los tres detectores; mismos pesos de remuestreo para diferencias pareadas.
  Se calculan IC de F1/precisión/recall y diferencias de F1 L0−V4,
  L0−PARAAD y V4−PARAAD. No se elige año, δ ni umbral según quién gane.
- Comparación principal sin etiquetas: V4–PARAAD. L0 es referencia supervisada;
  una ventaja suya no aísla arquitectura de información supervisada.

Se preservan todos los planes/resultados. Las figuras de F1 tendrán ficha con
ejes, universo, umbral y origen de modelos. No se mezclan los planes aditivos
en estas tablas. No se abre ni modifica RAMA2024–2026 y no se hace commit.
