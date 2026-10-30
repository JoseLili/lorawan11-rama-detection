# PARAAD-SA en RAMA — preparación y ejecución CPU

2026-10-28. Implementación propia contrastada con el código publicado;
adaptación de faltantes y umbral documentada en `revision20_paraad_diseno.md`.
No hay modelo definitivo ni resultados de examen de PARAAD todavía.

## Archivos

- `src/detect/paraad.py`: atención SA, autoencoder, bloques, pérdida observada,
  MAE por estación-día y comprobación del universo común.
- `experiments/anomalias_red/entrenar_paraad.py`: auditoría, smoke sintético,
  selección y definitivo duplicados. Establece CPU antes de importar TensorFlow.
- `experiments/anomalias_red/puntuar_paraad.py`: inferencia duplicada desde disco,
  calibración 2023 y exportación de puntajes/alertas.
- `notebooks/colab_paraad_revision20.ipynb`: comandos con entrenamiento apagado.
- `tests/test_paraad.py`: contratos de ejes, faltantes, fórmula de atención,
  separación temporal, universo común y calibración sintética.

## Secuencia desde la raíz del repositorio

```bash
.venv/bin/python -m pytest tests/test_paraad.py -q
.venv/bin/python experiments/anomalias_red/entrenar_paraad.py --fase auditar
.venv/bin/python experiments/anomalias_red/entrenar_paraad.py --fase smoke
```

La auditoría sólo lee 2020–2022 del parquet; el smoke sólo usa datos sintéticos.
Por defecto, invocar el entrenador sin argumentos sólo audita. Cada fase crea
una carpeta exclusiva y falla si existe: no sobrescribe corridas previas.
Para una repetición completa usar `--salida OTRA_CARPETA`, sin borrar evidencia.

Actualización para Colab (2026-10-28): `--reanudar` recupera **repeticiones
completas**, verificadas mediante hashes de modelo, historia y reconstrucción,
y exige el mismo código, entorno y datos. Una repetición interrumpida se vuelve
a ejecutar desde semilla 42; no se restaura a mitad de época para no depender
de la recuperación del generador de Dropout. Se conserva el progreso cada 25
épocas. Una prueba comprueba recuperación completa, repetición de una unidad
incompleta e identificación de archivos corruptos.

`--fase benchmark` mide cinco épocas con 2020–2021 y dropout fijo 0.1, sin
validación ni elección de parámetros. Incluye tiempo de compilación.

## Ejecución Colab mediante CLI, autorizada el 2026-10-28

CLI local: `/home/kali-lab-jelb/.venvs/colab-cli/bin/colab`.
Sesión CPU: `paraad-r20-cpu-20261028`; 2 CPU virtuales y aproximadamente 12.7 GiB
de RAM. Entorno detectado: Python 3.13.18, TensorFlow 2.21.0, Keras 3.13.2,
NumPy 2.1.3, pandas 2.2.3, pyarrow 23.0.1, pytest 8.4.2.

Se preparó una copia aislada en `/content/paraad_r20` con los módulos necesarios,
las pruebas y un parquet recortado a 2020–2022. No se transfieren los datos reales
2023–2026, PDFs, credenciales ni el repositorio completo. El usuario autorizó
explícitamente el paquete de aproximadamente 780 KB después de que la revisión
automática pidiera esa precisión. Sus hashes están en
`results/anomalias_red_v1/revision20/colab_20261028/envio.json`.

`correr_paraad_colab.py --accion comprobar` ejecuta pruebas, auditoría, smoke y
benchmark. Sólo después de comprobar su éxito, `--accion entrenar` ejecuta
selección y definitivo, ambos con dos repeticiones. El orquestador guarda
estado y tiempos, y se detiene al primer error.

Los resultados de `/content` son temporales. Durante la ejecución, el cliente
descarga snapshots al disco local; sólo las unidades con marcador `completo.json`
y hashes válidos se consideran recuperables. Al terminar se descargan y validan
los resultados antes de liberar la VM. Si se pierde la VM, restaurar el último
snapshot en otra sesión con el mismo entorno y ejecutar con `--reanudar`;
lo que estaba incompleto se repite desde cero. No se promete recuperación de
épocas individuales ni persistencia autónoma si se pierde también el cliente.

El entrenamiento largo fue autorizado para ejecución por el asistente mediante
CLI en esta conversación; sustituye para esta corrida la instrucción previa de
que lo lanzara manualmente el tesista.

Comprobaciones en esa sesión: ocho pruebas pasaron (53 s), auditoría 2020–2022
correcta, smoke repetido idéntico. Benchmark de 731 días de ajuste, cinco épocas:
19.88 s incluyendo compilación, sin validación; no extrapolar linealmente como
una promesa de duración total. La selección completa se inició después.

El supervisor local `supervisar_paraad_cli.py` consulta y descarga cada 60 s,
verifica el SHA-256 del snapshot y de las repeticiones completas, y libera
exclusivamente la sesión indicada tras recuperar el estado terminal (éxito o
error). Tras cinco errores de comunicación se detiene conservando la sesión
para recuperación manual. Estado local:
`results/anomalias_red_v1/revision20/colab_20261028/estado_supervisor.json`;
respaldo extraído en `recuperado/`, archivo en `snapshot_ultimo.tar.gz`.
Mantener la laptop encendida y con red para que funcione este supervisor.

El tesista lanza después, en el mismo entorno CPU:

```bash
.venv/bin/python experiments/anomalias_red/entrenar_paraad.py --fase seleccion
.venv/bin/python experiments/anomalias_red/entrenar_paraad.py --fase definitivo
```

Selección: 3 dropout × 500 épocas × 2 repeticiones, con 2020–2021 para ajuste
y 2022 limpio para validación. No entrena con ataques ni selecciona por F1.
Definitivo: dos ajustes nuevos sobre 2020–2022, con el dropout y época elegidos.
Ambas fases escriben su comprobante de igualdad sólo cuando todos los controles
pasan. El segundo modelo no se usa para escoger un resultado más favorable.

La prueba local utilizó Python 3.14.7, TensorFlow 2.22.0-rc0 y Keras
3.16.0.dev2026092204. Colab puede tener otras versiones: ejecutar allí las
pruebas y las dos repeticiones; no se exige igualdad entre máquinas distintas.
El script registra versiones y hashes y exige continuidad entre selección y
definitivo. No instala ni modifica el entorno por sí mismo. Dependencias:
TensorFlow/Keras, NumPy, pandas, pyarrow y pytest; no requiere keras-self-attention.

## Después de congelar el modelo

El puntuador consume las matrices ya generadas (`*_valor`, `*_mascara`) y un
CSV de máscara común con `dia` y las 31 columnas de objetivos, en orden fijo,
con valores 0/1. **Esa máscara debe exportarse desde los comparadores congelados
de las revisiones 18/19**, no inventarse con las filas que le convengan a PARAAD.
La exportación de la máscara 2023 y la evaluación conjunta son la siguiente
integración pendiente; los comandos siguientes son interfaces preparadas,
no una afirmación de que esos archivos ya existen.

```bash
.venv/bin/python experiments/anomalias_red/puntuar_paraad.py \
  --matriz results/anomalias_red_v1/matrices/matriz_limpia_2023.csv.gz \
  --comunes RUTA_A_MASCARA_COMUN_2023.csv \
  --salida results/anomalias_red_v1/revision20/calibracion
```

Produce puntajes, alertas y `registro.json` con umbrales p99/p99.9 y hashes.
Comprueba que 2023 no contiene etiquetas de ataque. No utiliza etiquetas como
entrada ni para optimizar exactitud. Carga únicamente `modelo_r1.keras`, tras
verificar que coincide con el manifiesto congelado.

El examen permanece separado y sólo se habilita tras registrar la revisión 20
en el protocolo compartido (cuando se cierre la 19), con `--examen-registrado`
y `--umbrales .../calibracion/registro.json`. Se aplica a cada matriz/calendario
existente, sin generar ataques distintos ni reajustar la escala. Reunir después
los puntajes con las mismas etiquetas y métricas de las revisiones 18/19,
incluido control sin ataque, cinco δ, escenarios original/A/B e IC. No interpretar
una corrida aislada como resultado definitivo ni usar 2024–2026 para cambiar
la arquitectura o repetir selección.

## Qué queda demostrado ahora

Los controles técnicos y la repetición sintética no validan la calidad del
detector. La equivalencia de atención se comprueba contra la fórmula publicada
en la dependencia; no es una reproducción numérica del entrenamiento de Barcelona.
Quedan pendientes el entrenamiento largo, la integración conjunta de evaluación
y sus resultados. Se preservan todos los modelos y resultados anteriores.

## Paralelización autorizada el 2026-10-28

Para reducir espera se añadieron las sesiones CPU `paraad-r20-d03-cpu` y
`paraad-r20-d05-cpu`. Cada una ejecuta sus dos repeticiones simultáneamente,
con un hilo por proceso, a través de `correr_paraad_fragmentos.py` y
`entrenar_paraad_fragmento.py`. Se reutiliza exactamente el entrenador congelado;
no se cambia su hash, época máxima, semilla, lote ni candidatos.

Cada proceso verifica versiones, fuentes y hash de datos contra `esperado.json`
(copia del manifiesto original). Al finalizar la pareja se comparan pesos,
historias y reconstrucciones antes de escribir `fragmentos_verificados.json`.
Los supervisores respaldan en `colab_20261028_d03/` y `colab_20261028_d05/`.
La sesión inicial conserva el trabajo de dropout 0.1. El seguimiento de este
chat coordina la integración de checkpoints completos en el flujo inicial,
con `--reanudar`, evitando copiar sobre carpetas que se estén escribiendo.
Si el flujo inicial ya empezó trabajo redundante, se conserva toda evidencia,
se detiene únicamente esa ejecución redundante y se relanza desde los
checkpoints completos tras la importación. Los resultados parciales no cuentan
como unidades reproducibles. Las VMs auxiliares se liberan tras recuperar sus
resultados, y la principal después del definitivo.

Integración del 2026-10-28, alrededor de las 10:37 (Ciudad de México): las dos
sesiones auxiliares completaron sus parejas con identidad exacta y se liberaron
tras recuperar sus resultados. Se verificaron sus manifiestos y hashes contra
la entrada original, se conservaron las dos repeticiones de dropout 0.1, se
archivó la ejecución parcial redundante de dropout 0.3 y se relanzó el flujo
original con las cuatro unidades auxiliares completas, sin modificar los tres
archivos científicos congelados. La evidencia de integración queda en
`integracion_paralela.json` de la corrida principal, recuperable por supervisor.
