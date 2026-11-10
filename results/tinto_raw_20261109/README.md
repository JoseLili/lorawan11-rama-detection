# Auditoría inicial TINTO raw O3

Fuente: XLS originales dentro de 20RAMA.zip, 21RAMA.zip y 22RAMA.zip, hashes comprobados. Solo mediciones originales; -99 convertido a ausencia (NaN), sin imputación ni características. Dos extracciones con archivos idénticos: reproducibilidad.json.

Las 32 estaciones históricas de contexto no tienen ninguna hora completa de red en 2020, 2021 o 2022. Entre otras ausencias, ACO y CHO no tienen observaciones en 2020, AJM y HGM en 2021, HGM en 2022. No se debe rellenar automáticamente con cero.

Sí hay días completos individuales: SAC tiene 204 en 2020, 224 en 2021 y 220 en 2022. Esto permite estudiar estación-día sin imputación, declarando selección por disponibilidad. La cobertura detallada está en auditoria1/cobertura.csv. No se ha ajustado TINTO ni entrenado CNN. Pendiente: fijar cohorte y tratamiento de huecos para red antes de generar imágenes; no confundir exclusión de filas con ausencia de sesgo de selección.
