# Cierre de versionado de PARAAD y Barcelona

29 de octubre de 2026. El tesista solicitó commit y subida al remoto únicamente
de PARAAD, Barcelona y el informe integrado. Revisión 19, TINTO T2 y diagnóstico
NO/NO₂ permanecen fuera de este cambio.

Se conservan código, pruebas, cohortes y procedencia, diseños y registros,
planes e inyecciones, modelos y repeticiones, historias, escalas, umbrales,
puntajes, métricas, comprobantes de hashes e igualdad, figuras y el informe
editable de `docs/informes/`. Los resultados son los ya cerrados; esta operación
no reentrena, recalibra ni cambia decisiones con datos de examen.

Los paquetes `.tar.gz`, fragmentos `.bin` y carpetas `paquete/` y `partes*/`
de Barcelona son copias de transporte regenerables y permanecen locales,
fuera de Git. Lo mismo ocurre con los snapshots comprimidos de revisión 20;
se versiona su contenido científico extraído. Las fuentes crudas permanecen
en `data/raw/`, excluida por la política existente del repositorio. El PDF de
la publicación y las configuraciones privadas tampoco se distribuyen.

## Dependencias de la evaluación RAMA

La evaluación PARAAD de revisión 20 usa referencias de las revisiones 18 y 19.
`evaluar_paraad_revision20.py` requiere los planes y tablas de revisión 19 y
la función `corridas_nodo` de `src/detect/anomalias_red.py`. Esos cambios
pertenecen a la línea de revisión 19 y no se incluyen en este commit por el
alcance indicado. Para volver a ejecutar esa evaluación en un clon se debe
integrar primero el cierre de revisión 19 y recuperar las matrices de datos.
Los resultados cerrados y sus referencias de hashes quedan conservados aquí.

Barcelona dispone de sus scripts independientes en `experiments/barcelona/`.
Los runbooks registran el entorno de ejecución y las comprobaciones exigidas.
El entorno local de pruebas puede diferir del de Colab; la igualdad científica
aceptada es la que documentan las repeticiones en el entorno registrado.

## Validación previa al commit

Las diez suites específicas de PARAAD y Barcelona completaron 37 pruebas,
todas aprobadas, el 29 de octubre de 2026. Keras emitió advertencias de
compatibilidad de la interfaz NumPy, sin fallos. La inspección de los archivos
seleccionados no encontró patrones de credenciales. Los paquetes de transporte
no se incorporan y ningún archivo seleccionado supera 100 MiB.
