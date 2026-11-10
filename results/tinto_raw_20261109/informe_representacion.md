# Representación raw estación-día — 2026-11-09

TINTOlib 1.3.1 nativo, PCA, sin difuminado, mapas y MinMax recién ajustados exclusivamente con 2020–2021 sin ataques inyectados. Entrada: 24 valores O3 de una estación por día. Un mapa compartido entre 31 objetivos históricos; HGM y XAL excluidos. 12146 días completos en el control; 22661 días incluyendo incompletos en cada brazo de relleno. No hay máscaras ni etiquetas de ataque en la entrada. Columna ficticia constante requerida por API excluida de PCA.

| Brazo | Lado | Píxeles únicos / 24 | Cambios individuales +1 ppb ocultos |
|---|---:|---:|---:|
| Días completos |32|24|0|
| Días completos |64|23|1|
| Relleno 0 |32|24|0|
| Relleno 0 |64|24|0|
| Relleno 99 |32|20|4|
| Relleno 99 |64|23|1|

Se verificó con transform de TINTO que, sin difuminado, las colisiones usan la última escritura. Aumentar la resolución no garantiza monotonía de las colisiones por redondeo. Las pruebas +1 ppb son sobre el primer día completo SAC de 2022, seleccionado cronológicamente; no constituyen evaluación de detección.

PCA sitúa columnas (horas) completas, no separa cada celda ausente de cada celda observada. Un faltante y una medición real de 0 o 99 en la misma columna quedan indistinguibles tras rellenar; ninguna CNN puede recuperar esa distinción solo del valor. El relleno 0 sin colisiones en esta prueba no demuestra que sea una imputación adecuada ni que detecte ataques. Rellenar puede alterar tanto la escala como las relaciones aprendidas por PCA. La diferencia frente al control incluye distinta muestra de ajuste.

Dos ejecuciones con todos los archivos idénticos (incluida figura), hashes en reproducibilidad_representacion.json. La figura usa escala MinMax propia por brazo: colores entre brazos no equivalen necesariamente a los mismos ppb. Dentro de cada brazo se conserva mapa/escala entre ejemplos. Fechas exactas en configuracion.json. Sin entrenamiento de CNN, métricas F1 ni apertura de 2023–2026. No se selecciona imputación por este resultado.
