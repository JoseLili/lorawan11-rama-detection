# PARAAD-SA adaptado: calibración limpia 2023 completada

Fecha de la sesión: 2026-10-28. Origen: modelo definitivo cargado de disco,
sin entrenar, sin ajustar arquitectura y sin evaluar ataques.

## Universo común

Se exportaron **8,802 estación-días** de 2023, de 31 objetivos, según los
criterios de las revisiones 18/19. Se usaron únicamente matrices limpias
2020–2022 como historia y 2023 como calibración.

L0 se puntuó con su modelo único d50 congelado; R3 se calculó con su mediana
causal y dominancia; V4 usa sus residuos de calibración guardados. El soporte
horario de ambos V4S es idéntico al de V4 por `ejemplos_validos`/`tensores`:
objetivo observado, base disponible y ventana temporal existente. Se cotejó
ese criterio con la disponibilidad de cada residuo V4 guardado. Ordenar las
vecinas o agregar las columnas propias no añade exclusiones de horas en V4S.

Como control, los umbrales recalculados de L0, R3 y V4 coinciden con los
umbrales comunes históricos de la revisión 18, con diferencias de lectura
decimal de hasta aproximadamente 1e-16. PARAAD cubre todas las filas de esta
máscara; no se recortó el universo para favorecerlo.

## Umbrales congelados

Puntaje: MAE diario por estación, sólo sobre horas observadas, en espacio
estandarizado con la escala definitiva 2020–2022. No está expresado en ppb.
Se alerta si el puntaje es **estrictamente mayor** que el umbral.

| Punto | Umbral | Alertas limpias / 8,802 | Tasa observada |
|---|---:|---:|---:|
| p99 | 0.6405011077101032 | 88 | 0.999773% |
| p99.9 | 0.8366300233950218 | 8 | 0.090888% |

Son umbrales globales sobre el conjunto común de estación-días, como los
comparadores; no se calibró un umbral independiente para cada estación.
La función existente elige el umbral más bajo cuya tasa limpia no exceda
1% o 0.1%, respectivamente. La segunda tasa queda por debajo de 0.1% por
el tamaño discreto de la muestra. Estas tasas son de **estación-día**, no
de hora de red ni la probabilidad de tener alguna alerta diaria en la red.

Las alertas sobre 2023 limpio son falsas alarmas operativas bajo la referencia
del protocolo, no prueba de fallas reales de sensores. No permiten medir
recall, F1 o precisión de detección de ataques.

## Reproducibilidad y entorno

Se preparó un entorno temporal local `/tmp/paraad-tf221`, separado de `.venv`,
con TensorFlow 2.21.0, Keras 3.13.2, NumPy 2.1.3 y pandas 2.2.3, para conservar
las versiones principales de Colab. No se abrió otra sesión Colab ni se
transfirieron datos adicionales al exterior.

Las ocho pruebas de PARAAD pasaron en ese entorno. Se ejecutaron dos
calibraciones completas independientes: registros, puntajes, umbrales y
alertas quedaron idénticos byte a byte. Cada ejecución además repite la
inferencia desde el modelo cargado de disco y exige igualdad exacta.

El cotejo con las reconstrucciones de ajuste guardadas en Colab mostró una
diferencia máxima de 2.0862e-6 en valores estandarizados y de 9.6361e-7 en MAE
por bloque. Por tanto, no se afirma identidad entre CPUs distintas. Un
chequeo inicial con tolerancia absoluta 1e-6 y relativa 1e-5 no pasó en 36 de
841,728 celdas. Se conserva la diferencia medida y se aplica el requisito
del proyecto de identidad entre repeticiones dentro del mismo entorno;
no se modificaron los pesos ni se ajustaron los umbrales para compensarla.
La evaluación futura debe conservar este entorno de inferencia y estos
umbrales, o verificar explícitamente cualquier cambio de entorno.

## Evidencia

En `results/anomalias_red_v1/revision20/`:

- `comunes_2023/mascara.csv`, `cobertura.csv`, `control_umbrales.csv` y
  `registro.json`: universo y controles de comparadores.
- `calibracion_2023/registro.json`: umbrales y hashes de modelo, escala,
  matriz limpia y máscara.
- `calibracion_2023/puntajes.csv`, `alertas_p99.csv`, `alertas_p99.9.csv` y
  `resumen.csv`: puntajes, alertas y tasas logradas.
- `calibracion_2023_control/`: segunda ejecución independiente.
- `verificacion_calibracion_duplicada.json`: identidad de las ejecuciones.
- `verificacion_entorno_calibracion.json`: diferencias entre CPUs y
  repetición local exacta.

Código de máscara: `experiments/anomalias_red/preparar_comunes_paraad_2023.py`.
Puntuador: `experiments/anomalias_red/puntuar_paraad.py`, con `--modelo` apuntando
a `colab_20261028/recuperado/definitivo` y `--comunes` a la máscara anterior.

## Continuación

El modelo y ambos umbrales quedan congelados. Falta registrar la evaluación
en los documentos compartidos cuando esté coordinado el cierre de revisión 19,
integrar la evaluación conjunta con los calendarios existentes y calcular
métricas de detección e intervalos. Esta calibración no abrió matrices ni
puntajes de examen 2024–2026; únicamente consultó los umbrales históricos de
calibración almacenados en la tabla de revisión 18 como control.
