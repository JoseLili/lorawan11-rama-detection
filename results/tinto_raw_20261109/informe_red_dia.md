# Red-día raw — 2026-11-09

TINTOlib1.3.1 PCA nativo sin blur; 32 estaciones×24 horas =768 características O3. MinMax y mapa recién ajustados con731 días2020–2021 sin ataques, faltantes0. Ejemplo fijo03 enero2022, +50% solo SAC (21 observaciones), ninguna otra estación alterada. Ejes fila/columna del píxel, no geografía ni tiempo. Escala por característica, no color ppb universal. Sin detector ni F1.

32×32:240 posiciones distintas,528 características sobrescritas;4 de21 cambios llegan a la imagen. 64×64:475 posiciones distintas,293 sobrescritas;16 de21 cambios llegan a la imagen y5 quedan ocultos. La última característica escrita en cada píxel prevalece, verificado frente a transform de TINTO. La comparación de diferencias exige el original conocido, solo diagnóstico.

Dos ejecuciones finales idénticas incluyendo figuras. Carpetas red_dia1/2 son intentos con fallo de serialización JSON de enteros NumPy al guardar informe; se corrigió solo la conversión a int y se repitió en carpetas nuevas. Resultados finales en red_dia_final1/2, hashes en reproducibilidad_red_dia.json. Se conservan ambos tamaños, no se reajustó mapa para mejorar la figura. Este resultado muestra pérdida real en esta representación de red, sin demostrar desempeño de detección.
