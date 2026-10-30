# Entrenamiento Barcelona en Colab CPU

Fecha: 2026-10-29. El tesista solicita enviar el experimento a Colab.
Tres sesiones independientes: `bcn-l0-cpu-20261029`, `bcn-v4-cpu-20261029`,
`bcn-paraad-cpu-20261029`. No se duplican workers ni supervisores.

Cierre 2026-10-29: las tres corridas completadas, respaldadas y verificadas;
VMs liberadas. Ver `resultados_entrenamiento_barcelona_v1.md` y
`colab_20261029/verificacion_entrenamiento.json` en resultados Barcelona.

## Paquete y separación

Directorio local `results/barcelona_paraad/colab_20261029/`:

- `barcelona_entrenamiento.tar.gz` (~119 MB): Barcelona en calendario UTC
  hasta 2016, con una hora previa de contexto al comienzo de la rejilla;
  valores, perfiles, máscaras, hora local y escalas limpias, y 50 calendarios
  alterados d50 de ajuste/validación. No contiene datos de calibración 2017
  ni examen 2018–2019, credenciales, PDFs o archivos RAMA de datos/modelos.
- `transferencia.json`: tamaño y SHA-256 del archivo exacto enviado.
- `partes/`: 15 fragmentos de hasta 8 MiB, con hashes individuales.
  La transferencia monolítica fue rechazada; se reconstruye verificando
  primero cada fragmento y luego el SHA-256 del archivo completo.
- `suplemento_fuentes.json`: hashes de dos dependencias transitivas de código
  (`src/ingest/__init__.py`, `rama.py`) incluidas durante el arranque; no son
  datos RAMA ni se invocan sus lectores. El manifiesto remoto agrega sus hashes.
- `lanzar_<detector>.py`: extracción segura y lanzamiento remoto. El estado
  y un bloqueo de proceso evitan iniciar otro worker del mismo detector.

`empaquetar_colab.py` genera el paquete desde los artefactos verificados.
`transferir_colab.py` sube los fragmentos y lanza worker/supervisor por sesión.
Después del primer intento de instalación, V4 y PARAAD reciben el paquete
reducido `barcelona_limpio_entrenamiento.tar.gz` (~3 MB), sin los calendarios
alterados que sólo usa L0. `partes_<detector>/registro.json` registra el hash
exacto enviado a cada sesión. Los registros del primer intento están en
`intento1/`; falló `ensurepip` antes de entrenar y sus VMs se liberaron.
Se comprobó en una sesión piloto la creación del entorno con `uv venv --seed`,
que sustituye a `python -m venv` en el worker corregido.
El entorno remoto aislado fija TensorFlow 2.21.0, Keras 3.13.2, NumPy 2.1.3,
Pandas 2.2.3 y PyArrow 23.0.1. Todas las fechas y valores son del brazo
Barcelona; las fuentes científicas RAMA se reutilizan sin modificarlas.

## Entrenamiento

`experiments/barcelona/entrenar_colab.py` sólo permite L0, V4 o PARAAD.
Verifica el manifiesto del paquete, prohíbe GPU, usa un hilo, desactiva oneDNN
y fija semilla 42 inmediatamente antes de construir y de entrenar cada modelo.
Todos los modelos son **nuevos**, no modelos RAMA cargados para transferencia.

- V4: 13 modelos, uno por objetivo, ventana t−24…t−1 ×26, LSTM64,
  dropout0.2, Dense32, regresión MSE/Adam0.001. Ajuste limpio 2014–2015,
  validación limpia 2016, máximo60 épocas, paciencia8, batch64, shuffleTrue.
  E por mínimo val_loss, primer mínimo. Definitivo limpio 2014–2016 desde cero.
- L0: un modelo compartido, 24×17, arquitectura de `construir_clasificador`,
  BCE/Adam0.001. Sólo d50: 20 calendarios iniciales, 10 de validación y
  20 definitivos. Se muestrea 1 de cada8 posiciones con dato propio y ventana
  temporal válida por calendario/estación, usando `lstm_local.muestra` y
  semillas por uso. Máximo60/paciencia8/batch64/shuffleTrue. E por BCE de 2016,
  primer mínimo. Escalas limpias fijas y perfil alterado causal ya verificado.
- PARAAD: arquitectura SA de `paraad.construir_modelo(sensores=13)`, sin
  alterar el código científico. Dropout{0.1,0.3,0.5}, 500épocas, batch256,
  shuffleFalse, MSE observada/Adam0.01 clipnorm1. Bloques UTC completos sin
  cambio de reloj, con alguna observación. Selección por MSE limpia2016,
  desempate menor dropout/primera época; definitivo limpio2014–2016 desde cero.

Selección y definitivo se ejecutan dos veces por configuración/modelo. Se
exige igualdad exacta de todas las historias, pesos, variables del optimizador
y predicción de control fija de hasta256 ejemplos; se comprueba también la
recarga del modelo guardado. No se afirma identidad entre máquinas/versiones.

Cada sesión realiza primero un smoke de una época y control duplicado,
guardado en `smoke_salidas/`, separado de los resultados científicos `salidas/`.
Sólo al pasar este control inicia la corrida completa. Un smoke L0 prepara
el dataset completo antes de recortarlo a ocho ejemplos; no es un benchmark
de entrenamiento ni un resultado de detección.

## Respaldo y cierre

`worker_colab.py` instala el entorno, ejecuta smoke y entrenamiento; escribe
`/content/barcelona/estado_<detector>.json` con fase/pid/error.
`snapshot_colab.py` respalda sólo unidades completas verificadas, metadatos
atómicos y progreso. No copia un modelo en escritura ni los datos de entrada.
`supervisar_colab.py` descarga y verifica los snapshots cada60s en
`colab_20261029/<detector>/recuperado/`. Un error repetido de conexión conserva
la VM para recuperación. Al completar el entrenamiento y verificar el respaldo,
libera la sesión con `colab stop` y registra `sesion_liberada`. Si el worker
falla, respalda el diagnóstico y detiene el supervisor conservando la VM
para revisión; no reinicia ni duplica automáticamente la corrida.

Consultar primero `estado_supervisor.json`, `error_supervisor.json` y
`supervisor.log` locales. No iniciar otro supervisor ni otra sesión por una
demora de estado. Las unidades completas admiten recuperación; las repeticiones
interrumpidas se reinician desde semilla, no desde un RNG a mitad de época.

Al finalizar, revisar cada `congelado.json`, todos los `verificado.json`,
hashes y selección de épocas. La calibración2017 y la evaluación posterior
son fases separadas. Las pérdidas de entrenamiento no son F1/recall.
