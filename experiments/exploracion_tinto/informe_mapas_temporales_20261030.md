# Paso 2: mapas temporales construidos y auditados

Fecha: 2026-10-30. Paso 1 COMPLETADO con alcance de conservación, no comprensión
horaria. Paso 2 COMPLETADO para construcción y auditoría de representaciones.
No se entrenó detector ni se calcularon predicciones. CPU local; GPU no necesaria.

Configuración fijada antes de ejecutar en §9 de `protocolo_temporal_20261030.md`.
Programa reproducible: `construir_mapas_temporales.py`, argumentos `--wheel` y
`--salida`. Artefactos desde raíz del repo:
`results/exploracion_tinto_2022/mapas_temporales_20261030/`.

## Ajuste y resultados

TINTOlib 1.3.1 real, PCA, semilla 42, MinMax externo sin clip, transformer=None,
32×32 y asignación única propia por mínima distancia cuadrática. No es la
rasterización nativa de TINTO. Escaladores nuevos ajustados solo con las 19 840
ventanas de entrenamiento 2020–2021 auditadas, agrupadas en bloques o pasos;
PCA usa 20 000 filas por variante, elegidas sin reemplazo con semilla 42.
Los índices guardados permiten volver a la estación, calendario y tiempo de
cada ventana fuente. Etiquetas no entran en PCA; última columna auxiliar cero
solo satisface la API. El preprocesamiento anterior sigue siendo el heredado L0.

| Variante | Imágenes por día | Valores por imagen | Filas auditadas de ajuste | Valores recuperados exactamente | Píxeles distintos nativos / asignación propia |
|---|---:|---:|---:|---:|---:|
| B12 / S12 | 2 | 204 | 39 680 | 8 094 720 | 22 / 204 |
| S1 | 24 | 17 | 476 160 | 8 094 720 | 10 / 17 |

Las dos mitades usan el mismo mapa y escalador; lo mismo ocurre con las 24
horas. Se guarda un mapa por granularidad, nunca uno por observación. Los
bloques empleados en ajuste proceden de ventanas móviles y no están todos
alineados al comienzo del día; esta selección fue fijada antes de ejecutar.
D24 conserva su mapa previo sin reajuste.

Cada valor float32 se recuperó exactamente desde su píxel. Perturbar una
columna a la vez cambió exactamente un píxel, cero cambios ocultos. Dos
procesos independientes produjeron los 19 archivos idénticos byte a byte,
incluyendo mapas, escaladores, ejemplos y figura; hashes en reproducibilidad.json.
La igualdad verifica reproducción, no estabilidad estadística entre semillas.

## Ejemplo y ficha de figura

Fuente: SAC, 2022-01-16, ventana limpia y alterada d50 del calendario 01,
seleccionada previamente por criterio cronológico sin mirar scores.
La figura `corrida1/bloques_12h.png` tiene primera fila 00–11 y segunda 12–23;
columnas limpia, alterada y resta alterada−limpia. Ejes: fila/columna de píxel,
no latitud/longitud ni orden horario. Color: intensidad MinMax adimensional,
no probabilidad. Escala común entre mitades; diferencias con escala simétrica.
Se ven cambios en 96 posiciones del conjunto del día en ambas representaciones.
La resta es diagnóstico y no entrada del futuro detector. Los puntos amarillos
pueden ser máscaras de disponibilidad; no marcan ataques. Archivos NumPy
conservan números, sin conversión RGB/PNG para el modelo.

## Límites y siguiente etapa

Éxito de representación, no de detección. Solo muestra auditada de entrenamiento
y ejemplo real limpio/alterado; no se afirma cobertura de todos los calendarios
ni evaluación 2022 completa. No hay modelo que haya aprendido el paso 23→00.
La cuadrícula horaria tiene 17 píxeles ocupados de 1 024: se reporta su escasez,
pero no se descarta por intuición. No se demuestra precisión 50/51 para todos
los nuevos contextos únicamente por recuperar float32: repetir el control de
la cadena completa con nuevos escaladores al integrar el pipeline.

Antes de entrenar B12: congelar arquitectura y presupuesto, comprobar etiquetas
por bloque, construir manifiestos de días/horas y cobertura, verificar soporte
común y compatibilidad ED, registrar hashes. Luego dos corridas de entrenamiento
con la autorización Colab GPU nueva, sin cambiar L0/V4 ni abrir años de examen.
