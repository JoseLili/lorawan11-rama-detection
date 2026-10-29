# Evaluación exploratoria TINTO frente a L0 — Colab CPU, 2026-10-29

Las dos ejecuciones completaron 31 matrices cada una. Los puntajes diarios
(62 archivos por corrida), métricas, umbrales e intervalos coinciden exactamente,
comprobados también después de descargar. Ambos modelos se cargaron de disco:
TINTO-PCA con asignación única 32×32, época 5 del cierre manual, y L0 selección d50.
No hubo entrenamiento nuevo.

Se evaluó 2022 limpio y diez calendarios pareados, δ100/50/20; 9661 estación-días
comunes por calendario. Promedio diario con mínimo 12 horas observadas. Umbrales
por detector sobre 2022 limpio en los mismos días. Los perfiles son causales y
usan historia 2020–2022; no se abrieron 2023 ni los años de examen.

| δ | Umbral | F1 TINTO | F1 L0 | Recall TINTO | Recall L0 |
|---|---|---|---|---|---|
| 100% | p99 | 0.4282 | 0.4519 | 0.8865 | 0.9056 |
| 100% | p99.9 | 0.4473 | 0.4996 | 0.3355 | 0.3788 |
| 50% | p99 | 0.4105 | 0.4663 | 0.6556 | 0.7755 |
| 50% | p99.9 | 0.2035 | 0.3219 | 0.1276 | 0.2156 |
| 20% | p99 | 0.0862 | 0.1467 | 0.1008 | 0.1760 |
| 20% | p99.9 | 0.0091 | 0.0158 | 0.0051 | 0.0089 |

L0 tiene mayor F1 y recall en las seis condiciones observadas. TINTO conserva
señal, sobre todo con alteraciones grandes, pero esta configuración no supera
a L0. Esto demuestra viabilidad de la conversión y del flujo de inferencia;
no demuestra ventaja de convertir las entradas a imágenes ni descarta otras
configuraciones de TINTO.

El F1 sin ataque fue 0.0023 TINTO y 0.0080 L0 en p99, y 0 para ambos en p99.9
(con las mismas etiquetas de episodios sobre puntajes limpios).

Los IC95 exploratorios de diferencia F1 TINTO−L0, por bootstrap pareado de
2000 remuestreos de bloques estación-mes con calendarios juntos, fueron:

| δ | Umbral | IC95 diferencia F1 |
|---|---|---|
| 100% | p99 | [-0.0497, 0.0001] |
| 100% | p99.9 | [-0.0827, -0.0235] |
| 50% | p99 | [-0.0888, -0.0230] |
| 50% | p99.9 | [-0.1525, -0.0851] |
| 20% | p99 | [-0.0889, -0.0364] |
| 20% | p99.9 | [-0.0175, 0.0001] |

Estos intervalos no incluyen incertidumbre de entrenamiento ni umbral. 2022 ya
se usó para selección y el entrenamiento TINTO terminó por decisión manual:
no es un examen independiente ni una prueba confirmatoria de superioridad.

Entorno remoto: Python3.14.7, TensorFlow2.22.0-rc0, Keras3.16.0.dev2026092204,
solo CPU, dos procesos paralelos. Control L0 frente a puntajes históricos:
diferencia máxima 3.5478955218160024e-08, inferior a tolerancia1e-6.

ZIP descargado: tinto_evaluacion_2022_resultados_20261029.zip, 11419256 bytes.
SHA256: 4ae17a844981f53ab71735f3bb1464e0e080483329c0ea5984ee188eff9b69bc.
Integridad CRC, hash y reproducibilidad local verificadas. La sesión
`tinto-eval-20261029` se liberó después de asegurar los archivos. Se eliminó la
automatización de seguimiento porque la evaluación terminó.
