# Evaluación en Colab CPU — preparada el 2026-10-29

Recomendación: Colab con acelerador **Ninguno**, para dejar libre la laptop.
No se promete que sea más rápido: depende de los recursos asignados. No se
reanuda ni repite entrenamiento. Se cargan TINTO época 5 y L0 selección d50.

## Archivos para el tesista

1. Notebook: `notebooks/colab_tinto_evaluacion_2022.ipynb`.
2. Paquete: `results/exploracion_tinto_2022/preparacion_colab_20261029/tinto_evaluacion_2022_20261029.tar.gz`.

El paquete contiene 136 archivos explícitos, unos 30.45 MiB: código necesario,
modelos pequeños, mapa/escalador, matrices 2020–2022 y planes de ajuste.
No incluye caché de entrenamiento, .git, entorno, credenciales ni matrices de examen.
SHA-256 del paquete:
`41b46b9c2adb386e7683c9848d4c5c0cd7974c8c6dca6073f1d5506542121a54`.

El 2026-10-29, por indicación del tesista, se creó la sesión CPU
`tinto-eval-20261029` mediante su CLI autenticado y se subió el paquete.
No se usa el navegador ni se requiere conectar Google Drive. El notebook queda
como alternativa manual; la ejecución por CLI trabaja en disco local de la VM
y descarga resultados al final.

## Diseño fijado antes de calcular métricas completas

- Solo 2022: limpio y calendarios 01–10 con δ = 100, 50 y 20 %.
- Historia 2020–2022 para características causales y normalización heredada.
- Dos modelos de disco, mismos vectores L0; TINTO aplica escala/mapa congelados.
- Promedio diario sobre horas con dato, mínimo 12. Intersección global de días
  válidos de ambos detectores y todas las matrices del barrido.
- Umbral común por detector, p99 (1 %) y p99.9 (0.1 %), con 2022 limpio en esa
  misma intersección. No se usa 2023 ni se retoca el umbral para favorecer resultados.
- Se guardan TP/FP/FN/TN, precisión, recall, F1, F2, MCC, ROC-AUC, AP y FA;
  métricas globales agrupando observaciones, no promediando F1 de calendarios.
- Control sin ataque con etiquetas de cada calendario sobre puntajes limpios.
- Bootstrap pareado de diferencia TINTO−L0, 2000 remuestreos, bloques estación-mes
  con datos, calendarios juntos, semilla [42,29,3]. Intervalos exploratorios:
  no incluyen incertidumbre del umbral ni semilla de entrenamiento.
- L0 debe reproducir sus puntajes guardados de 2022 dentro de 1e−6, con misma
  disponibilidad. Si no cumple, se detiene el script antes de emitir métricas.
- Dos evaluaciones en el mismo entorno, comparando puntajes diarios y métricas.
  No se entrenan otras variantes ni se elige otra época con estos resultados.

La intersección nueva TINTO/L0 no tiene por qué ser la intersección histórica
L0/R3. Por tanto no comparar números publicados de esas tablas como si tuvieran
exactamente la misma muestra: L0 se recalcula en los días comunes del experimento.
La selección TINTO se cerró manualmente; 2022 ya fue reutilizado. Los resultados
no son un examen independiente ni prueba confirmatoria de superioridad.

## Qué se verificó aquí

- Script `evaluar_2022.py` en modo `--prueba`: dos días limpios y el primer
  calendario d50, modelos cargados y control L0 pasado. No produce métricas.
- Paquete con manifiesto SHA-256 de cada archivo.
- Notebook válido como nbformat y sintaxis de todas las celdas Python comprobada.
- Prueba de extracción aislada en /tmp para confirmar dependencias del paquete.

La preparación inicial no había ejecutado el notebook en Colab. La vía CLI
verifica la instalación remota antes de iniciar la prueba breve. Se exige
Python 3.14.7 y `requirements-lock.txt`; si no se instala una versión, detener
sin sustituirla. No necesita instalar TINTOlib porque ya se carga el mapa ajustado.

## Ejecución en Colab

1. Abrir el notebook y elegir CPU (acelerador Ninguno).
2. Ejecutar celdas en orden; subir solo el paquete cuando lo solicite.
3. Dejar completar instalación del entorno y verificación de hashes.
4. Ejecutar prueba breve; continuar solo si finaliza correctamente.
5. Ejecutar las dos evaluaciones, verificar igualdad y descargar el ZIP final.

El script guarda puntajes por matriz a medida que avanza. No tiene reanudación
parcial automática; si Colab interrumpe una corrida, conservar sus archivos y
repetir en una carpeta nueva. No se añade ningún mecanismo para eludir límites
de sesión. Conservar/descargar resultados antes de desconectar.

Fuentes sobre el entorno Colab:
https://research.google.com/colaboratory/faq.html

## Ejecución por CLI y seguimiento autorizado

El tesista autorizó subir lo necesario, usar paralelismo y comprobar avance
cada cinco minutos. Se usa el CLI instalado en
`/home/kali-lab-jelb/.venvs/colab-cli/bin/colab`, con autenticación ya existente.
La sesión se creó sin acelerador y se confirmó `Hardware: CPU`.

Se preparan dos evaluaciones idénticas en paralelo, con dos hilos TensorFlow
por proceso y BLAS limitado. Los cambios de orquestación no cambian el diseño
científico, los datos ni el paquete sellado. La prueba breve es obligatoria
antes de lanzar las evaluaciones completas. El estado local de la sesión y la
automatización se guarda en
`results/exploracion_tinto_2022/preparacion_colab_20261029/estado_colab.json`.

Se creó una automatización heartbeat en este mismo chat,
`revisar-evaluaci-n-tinto-en-colab`, cada cinco minutos. Consulta mediante CLI,
sin relanzamientos ni avisos repetidos; al terminar debe descargar/verificar
resultados y liberar solamente esta sesión, y desactivar su seguimiento.
El seguimiento local necesita que el equipo y la aplicación puedan ejecutarlo.
No sustituye la preservación de resultados ni impide que Colab cierre la VM.

La instalación remota se verificó con Python 3.14.7, TensorFlow 2.22.0-rc0
y Keras 3.16.0.dev2026092204, sin GPU visible. El supervisor se lanzó como
proceso remoto independiente del cliente CLI; su primera etapa es la prueba
breve. El kernel puede aparecer IDLE mientras los hijos trabajan, por lo que
ese indicador no se interpreta como finalización.

Scripts de orquestación (fuera del paquete científico sellado):

- `preparar_colab_cli.py`: hash/manifiesto e instalación exacta.
- `ejecutar_colab_cli.py`: prueba, dos procesos, comparación exacta y ZIP.
- `inspeccionar_colab_cli.py`: estado real de procesos, marcadores y logs.
- `consultar_colab_cli.py`: celda de consulta para el CLI, sin argumentos del kernel.

Comprobación de seguimiento, desde la raíz del repositorio:

```sh
/home/kali-lab-jelb/.venvs/colab-cli/bin/colab exec -s tinto-eval-20261029 -f experiments/exploracion_tinto/consultar_colab_cli.py
```

La salida remota es
`/content/tinto_evaluacion/results/exploracion_tinto_2022/evaluacion_colab_20261029`.
`DESCARGA.json` da ruta, tamaño y SHA-256 del ZIP, que deben comprobarse tras
la descarga antes de liberar la VM. `FINAL.json` y `REPRODUCIBLE.json`
identifican cierre exitoso; el ZIP de un fallo solo conserva avances.

La prueba breve en Colab pasó antes del lanzamiento completo. Se confirmó
`evaluacion_paralela`, supervisor vivo y dos procesos vivos (corrida1 y
corrida2). Esta comprobación de lanzamiento no implica que las métricas
completas estén listas: la finalización la determinan los marcadores y la
comparación de reproducibilidad. La consulta inicial está preservada en
`results/exploracion_tinto_2022/preparacion_colab_20261029/ultima_consulta_colab.json`.

## Cierre

Las dos corridas terminaron y coincidieron exactamente. Resultados descargados,
hash e integridad verificados y comparación local repetida sin entrenar.
Sesión liberada y automatización eliminada. Ver `informe_evaluacion_colab_20261029.md`
para métricas y límites de interpretación.
