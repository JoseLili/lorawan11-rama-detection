# Piloto limitado CNN estación-día — 2026-11-09

Dos modelos recién entrenados desde cero en CPU, 34081 parámetros, cinco épocas fijas. Configuración previa en experiments/tinto_raw/protocolo.md. Mapa TINTO nativo32 y escala congelados (ajustados antes con días completos2020–2021). Sin características de L0, máscaras, calendario o identificador como entrada. Solo24 valoresO3 escalados, píxeles float32.

## Muestra y límites

1024 bases estación-día completas de2020–2021: original y copia alterada →2048 imágenes de ajuste. 256 bases de2022:512 imágenes de validación. Muestreo reproducible entre31 objetivos, sin selección por resultado. Copias de una base permanecen en la misma partición cronológica. Ataque d50 con signo por base: x*1.5 o x/1.5. Balance50/50 artificial para diagnóstico, no prevalencia operativa ni calendariosL0. Un día por episodio. No2023–2026. Se excluyen días con faltantes; desempeño no generalizable a ellos.

## Coste observado

Tensores de entrada completos:10MiB (float32). Construcción0.073/0.072s, entrenamiento2.292/2.186s para5épocas, inferencia512 imágenes0.070/0.071s. Entrenamiento no incluye importación inicial de TensorFlow. RSS máximo de proceso940/945MiB aproximadamente, incluye runtime; no confundir10MiB de imágenes con toda la memoria consumida. Tiempos de este equipo/configuración, no garantía para otro volumen o entorno. TF2.22.0-rc0, Keras3.16.0.dev2026092204; entorno distinto del Colab histórico, documentado.

## Aprendizaje y métricas exploratorias

Pérdida ajuste0.6934→0.6603; validación0.6916→0.6498. Umbral0.5 fijado previamente, modelo finalépoca5, sin búsqueda de umbral ni mejorcheckpoint. F1=0.440945, precisión=0.672, recall=0.328125, exactitud=0.583984, ROC-AUC=0.674225, average precision=0.691942. Validación:84TP,41FP,172FN,215TN. Clasificar todo positivo obtieneF1=0.666667 en este conjunto50/50; por ello no se presentaF1delpiloto como éxito. ROC-AUC de scores constantes0.5 y APprior0.5. La separación de scores y descenso de pérdida son señales preliminares, no detección suficiente al umbral fijo. No IC ni examen independiente;2022 reutilizado históricamente.

## Reproducibilidad y conclusión

Pesos numéricos, historias, probabilidades y manifiestos idénticos entre dos ejecuciones; hashes en reproducibilidad_piloto_cnn.json. Modelos finales y probabilidades guardados en piloto_cnn1/2. Tiempo/RSS varían normalmente. No se aumentaron épocas tras ver resultados.

Estación-día es técnicamente manejable en esta muestra. La CNN recibe y aprende algo de las imágenes, pero pierde172 de256 ejemplos alterados al umbral0.5. No se demuestra superioridad a L0, ni al dato tabular, ni ventaja sobre red-día. El F1 no es comparable con p99 histórico. El siguiente estudio requiere fijar previamente muestra/prevalencia/calendarios, regla de selección y calibración; no se inicia automáticamente desde este piloto.
