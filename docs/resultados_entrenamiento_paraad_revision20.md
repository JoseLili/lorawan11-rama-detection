# PARAAD-SA en RAMA: entrenamiento completado

2026-10-28, comprobación local al terminar Colab. Origen: modelos recién
entrenados en CPU, recuperados del disco remoto; no se reentrenaron al revisar.
Todavía no se calibró 2023 ni se evaluaron ataques o años de examen.

## Selección con 2022 limpio

Ajuste inicial exclusivamente con 2020–2021. Criterio predefinido: menor media
de MSE por bloque observado en validación, sobre valores estandarizados;
faltantes excluidos de la pérdida. Cada candidato se entrenó 500 épocas,
dos veces, semilla 42. No se usaron métricas de ataques para elegir.

| Dropout | Época del mínimo | MSE de validación |
|---|---:|---:|
| 0.1 | 494 | 0.16425904560459842 |
| **0.3** | **499** | **0.15061787126400517** |
| 0.5 | 458 | 0.16514702625166439 |

La configuración 0.3 reduce el error aproximadamente 8.3% frente a 0.1.
No equivale a mejora de F1 ni a mejora frente a L0; aquí no se compararon
detectores sobre ataques. La época seleccionada queda muy cerca del límite
de 500: no demuestra convergencia definitiva ni justifica ampliar la búsqueda
después de ver examen. Se respeta el presupuesto registrado.

## Ajuste definitivo y reproducibilidad

- Dos ajustes nuevos con 2020–2022, dropout 0.3 y exactamente 499 épocas.
- MSE de entrenamiento final: 0.12514112889766693, idéntica en las dos corridas.
  No se compara directamente con la validación de la fase anterior: cambió
  el conjunto y se recalculó la escala con todo el ajuste definitivo.
- Comprobaciones en Colab: igualdad exacta de pesos, historias y puntajes.
  Además, igualdad de reconstrucciones al guardar y volver a cargar cada modelo.
- Comprobación independiente local: SHA-256 del respaldo, escala, modelo,
  selección, fuentes y checkpoints; historias y reconstrucciones definitivas
  idénticas; los 92 tensores guardados en los archivos de pesos/optimizador
  de ambos `.keras` son idénticos. No se exige identidad de los contenedores
  ZIP `.keras`, que pueden contener metadatos distintos.
- El entrenamiento definitivo tardó 1,356.21 s (22.6 min) para las dos
  repeticiones, incluyendo el trabajo de guardado y verificación de esa fase.
- Hubo una interrupción transitoria al descargar el respaldo final; el
  supervisor recuperó la descarga, validó hashes y liberó la VM.
  Las tres sesiones de esta corrida están liberadas; el CLI no muestra
  sesiones activas al verificar el cierre.

La curva definitiva tiene una pérdida inicial muy alta antes de descender;
todos los valores aceptados son finitos. La figura usa eje logarítmico para
mostrar también ese transitorio, sin ocultarlo ni cambiar el entrenamiento.

## Evidencia y ubicación

Directorio: `results/anomalias_red_v1/revision20/colab_20261028/`.

- `verificacion_final_local.json`: comprobación independiente.
- `recuperado/seleccion/seleccion.json`: elección y controles de selección.
- `recuperado/definitivo/congelado.json`: manifiesto del modelo definitivo.
- `recuperado/definitivo/modelo_r1.keras`: modelo a usar; r2 es control.
- `recuperado/definitivo/escala.csv`: estandarización congelada.
- `snapshot_ultimo.tar.gz`: respaldo final verificado.
- `curvas_entrenamiento.png`: curvas de validación y ajuste.

Ficha de figura: X=época; Y=MSE estandarizada, con escala logarítmica; izquierda
son mínimos elegibles de validación limpia 2022 de tres candidatos; derecha
son pérdidas de ajuste definitivo 2020–2022 de dos repeticiones que se superponen.
No hay azar pareado de detección porque aquí no se evalúan ataques. No es F1,
recall, precisión ni una comparación con L0.

## Próximo paso

Integrar la máscara común de los comparadores congelados y calibrar p99/p99.9
en 2023 limpio. Registrar el examen de revisión 20 en los documentos compartidos
cuando corresponda y evaluar después los calendarios existentes. Conservar la
distinción entre PARAAD-SA adaptado a faltantes/umbral RAMA y el experimento
original de Barcelona. No modificar hiperparámetros a partir de 2024–2026.
