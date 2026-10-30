# Examen Barcelona 2018–2019 en Colab CPU

Fecha: 2026-10-29. Autorización explícita del tesista después de calibración.
Registro científico: `registro_examen_barcelona_2018_2019.md`, anterior a
cualquier métrica de detección. No se entrena ni se recalibra durante el examen.

**Cierre 2026-10-29:** tres detectores completados,103 unidades por detector,
respaldos verificados y tres VMs liberadas. Métricas/IC duplicados, figura
inspeccionada y reporte en `resultados_examen_barcelona_2018_2019.md`.

## Preparación y ejecución

`empaquetar_examen.py` prepara tres bases limpias (control2017 y prueba2018/2019)
y100 parches dispersos. Se verificó reconstrucción bit a bit, incluidos NaN y
ceros con signo, contra las150 matrices originales ya auditadas (sólo se
usan aquí las100 matrices de prueba). Se empaquetan15 modelos congelados,
p95/umbrales y puntajes2017 para control, máscara común y etiquetas fijas.
Tamaño comprimido ~20.7MB; tres fragmentos de hasta8MiB.

Sesiones CPU independientes: `bcn-eval-l0-cpu-20261029`,
`bcn-eval-v4-cpu-20261029`, `bcn-eval-paraad-cpu-20261029`.
Cada una ejecuta `worker_examen_colab.py` y `evaluar_examen_colab.py` para un
detector sobre ambos años. Un hilo, semilla42, TensorFlow2.21.0/Keras3.13.2.
Primero se repite control limpio2017 contra la calibración congelada; sólo
si pasa se abren las matrices del examen. No se aproximan predicciones por
similitud de ventanas: toda la inferencia se ejecuta dos veces por matriz.

Por detector:103 unidades cerradas, una de control2017 y102 del examen
(dos limpias y100 atacadas). Cada unidad guarda `puntajes.npy`, `datos.json`
y `completo.json`; `congelado.json` enlaza hashes de las103. Las entradas
se reconstruyen de los parches comprobando forma, dtype y SHA-256 de bytes.

## Incidencia corregida antes del examen

El primer control produjo puntajes duplicados, pero la comprobación de
identidad del índice rechazó la distinta resolución temporal CSV(ns)/Parquet(us)
de los mismos instantes. No se habían generado puntajes de2018/2019 en ese intento.
Se corrigió sólo la comparación de timestamps: UTC y resolución común ns,
exigiendo la misma secuencia de instantes y orden de estaciones. Una prueba
acepta us/ns equivalentes y rechaza un desfase real de una hora o zona ausente.
No se modificaron datos, modelos, umbrales ni tolerancia de comparación numérica.

Diagnósticos iniciales en `examen_colab_2018_2019/intento1/`; en cada VM se
conservó `intento1/` antes de reiniciar. `actualizacion_codigo.json` registra
hashes anteriores y nuevos; el manifiesto local/remoto recibió el mismo cambio
de código. Los fragmentos originales permanecen como evidencia de transferencia.

## Seguimiento y finalización

Base local: `results/barcelona_paraad/examen_colab_2018_2019/`.
`transferir_examen_colab.py` transfiere/lanza workers y supervisores sin imprimir
URLs de autenticación. No repetirlo si los workers ya existen.
Consultar primero `<detector>/estado_supervisor.json` y `recuperado/`.
Los supervisores respaldan cada minuto; el seguimiento del chat es cada5min,
en silencio salvo incidencia o finalización. Un kernel IDLE puede tener el
worker en ejecución como subprocess. No duplicar sesiones ni supervisores.

Durante la corrida hubo interrupciones de conexión del CLI: se conservaron
los respaldos previos y los workers siguieron evaluando en las mismas VMs.
Se restablecieron sólo supervisores detenidos. Para evitar proxies caducados,
el supervisor consulta `colab status` antes de cada snapshot y, tras cinco
fallos, continúa con reintentos cada5min en lugar de abandonar el respaldo.
Los errores recuperados se archivan en `incidencias/` tras un respaldo válido.
Esto cambia únicamente la supervisión, sin tocar inferencia, datos o umbrales.

Al completar, las VMs se liberan sólo después de descargar/verificar snapshots.
Ante error, el supervisor respalda y se detiene conservando la VM para revisión.
Las unidades completas pueden reutilizarse sólo con los mismos hashes de entrada.

Cuando terminen los tres:

```sh
.venv/bin/python -m experiments.barcelona.resumir_examen
```

Este programa verifica los103 cierres por detector, hashes, modelos/calibración
congelados y soporte común; calcula métricas dos veces con igualdad exacta,
IC95% pareados por estación×mes (2,000 remuestreos) y produce `resumen/` con
CSV, figura y ficha. Revisar visualmente `f1_barcelona_p99.png` antes de presentar.
Escribir un reporte separado de resultados con alcances y limitaciones, sin
reentrenar ni seleccionar según el examen. No mezclar el complemento aditivo.
