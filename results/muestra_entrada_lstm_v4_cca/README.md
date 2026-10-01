# Entrada real del LSTM V4 — ejemplo CCA

Exportación para revisión con el asesor. Objetivo: **CCA, 21/oct/2025 a las
12:00**, según la convención horaria actual del pipeline. Usa el piloto del
notebook 07 y su preprocesamiento guardado, no un entrenamiento nuevo ni los
artefactos del experimento de red del notebook 09.

## Qué abrir y en qué orden

| Archivo | Contenido | ¿Entra directamente al LSTM? |
|---|---|---|
| [01_ventana_mediciones_ppb.csv](01_ventana_mediciones_ppb.csv) | 24 horas anteriores, timestamp y 33 estaciones en ppb | No: es la vista de origen. CCA se excluye al construir X. |
| [02_entrada_exacta_lstm.csv](02_entrada_exacta_lstm.csv) | Matriz numérica de **24 filas × 66 columnas**, en el orden real de los canales | **Sí**, añadiendo la dimensión de ejemplo: `(1, 24, 66)`. |
| [03_perfil_cca_14_dias.csv](03_perfil_cca_14_dias.csv) | CCA a las 12:00 del 7 al 20/oct | No: se promedia fuera de la red. |
| [04_objetivo_y_contexto.csv](04_objetivo_y_contexto.csv) | Fecha objetivo, perfil, lectura real y desviación real `y` | No: son contexto y respuesta para evaluar, no características. |
| [05_diccionario_caracteristicas.csv](05_diccionario_caracteristicas.csv) | Significado y orden de cada canal; estadísticas de normalización guardadas | No: documentación del preprocesamiento. |

Los CSV tienen encabezados, separador coma, punto decimal y codificación UTF-8
con BOM. Excel y LibreOffice pueden abrirlos; si todo aparece en una columna,
usar **Importar texto/CSV**, separador **coma** y punto decimal. Para la revisión
visual pueden mostrarse cuatro decimales sin modificar el archivo original.

## Cómo se relacionan

Las filas de `02` corresponden, una a una y en el mismo orden, a las de `01`:
20/oct 12:00 hasta 21/oct 11:00. El timestamp no se incluyó en `02` porque no es
un canal del LSTM. Tampoco se incluyen CCA, el perfil, la lectura objetivo ni
etiquetas de ataque. Los encabezados son nombres explicativos, no texto que
procese la red.

Los 66 canales son: **32 mediciones normalizadas**, **32 indicadores de
disponibilidad**, **seno y coseno de la hora**. Las otras 32 estaciones se
mantienen en el orden del preprocesamiento guardado, sin seleccionar sólo las
geográficamente cercanas.

- En `01` y `03`, una celda vacía significa dato faltante; no cero ppb.
- En `02`, un faltante se representa con medición normalizada de relleno 0 e
  indicador 0. Si hay dato, el indicador es 1. Es información adicional que
  aprende el modelo, no una capa que ignore automáticamente ese canal.
- Un número normalizado negativo no significa ozono negativo: significa una
  lectura por debajo de la media de entrenamiento de esa estación.
- La media y la desviación para normalizar vienen del entrenamiento guardado,
  no se recalculan con esta ventana de prueba.

En este ejemplo, las 14 lecturas de `03` suman 882 ppb: el **perfil es 63 ppb**.
CCA realmente midió **69 ppb**, por lo que la desviación real `y` es **+6 ppb**.
Ésta es la respuesta con la cual se evalúa el ejemplo, **no una salida del
modelo**. La corrección estimada por el LSTM sería otra cantidad; se suma al
perfil para construir una predicción y después se compara con la lectura.
Esta exportación no ejecuta inferencia ni contiene una predicción recién calculada.

El perfil se calcula fuera del LSTM. No se añaden sus 14 días como filas a la
ventana ni su promedio como una característica número 67. El ejemplo pertenece
a prueba: no se usa aquí para entrenar pesos.

## Alcance y salvedades

Esta muestra ilustra una ventana, no exporta todo el año ni demuestra por sí
sola el desempeño del detector. Los nombres de las horas siguen el código:
`HORA=1` se interpreta como 00:00; esa convención requiere confirmación con la
especificación de origen. El perfil del piloto conserva el respaldo histórico
con promedio global cuando falta historia; **este ejemplo no lo necesita**,
pues tiene 14 lecturas previas disponibles.

## Reproducibilidad

Generador: [exportar_entrada_cca.py](../../experiments/inspeccion_lstm_v4/exportar_entrada_cca.py).
Se reconstruyen dos veces las tablas y se exige igualdad exacta. Se comprueba
que el CSV `02`, leído de nuevo como float32, conserva exactamente la matriz X.
Los hashes de los archivos fuente quedan en [fuentes_sha256.json](fuentes_sha256.json).
El programa se detiene si los CSV de destino ya existen: no sobrescribe
exportaciones aceptadas. No modifica notebooks, modelos ni umbrales.
