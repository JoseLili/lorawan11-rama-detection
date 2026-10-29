# Preparación del entrenamiento TINTO-L0 — 2026-10-29

## Estado

Estado actualizado: la selección completa se inició y fue detenida manualmente
por indicación del tesista para ahorrar recursos. Se conserva la mejor época
observada, la 5, en `seleccion_tinto_v1/cierre_manual/`. No se completó la regla
de EarlyStopping ni se calculó F1 contra L0. No hay reanudación automática.
La configuración y caché quedan preservadas; los comandos siguientes son
referencia histórica, no una indicación de volver a lanzarlos.

Este documento concreta la variante priorizada por el tesista: **TINTO-PCA con
asignación única propia, 32 × 32, 408 entradas, sin difuminado**. Canales y otros
modelos quedan fuera de esta ejecución. La arquitectura del primer candidato
se fija aquí sin seleccionar por las pérdidas del ensayo pequeño.

El piloto previo sigue sin cumplir su límite sintético de pérdida <0.1. La
revisión confirmó señal/etiquetas correctas y funcionamiento del circuito;
no se cambia ese criterio ni se declara aprobado. Preparar datos/programa no
es reetiquetar el piloto ni evidencia de generalización del clasificador.

## Diseño fijado

`configuracion_entrenamiento_v1.json` contiene el contrato. Se congela su hash
en la caché y el entrenamiento verifica que no cambió.

- CNN de 34 081 parámetros: Conv 8 (3 × 3, same, ReLU), MaxPool 2, Conv 16
  (3 × 3, same, ReLU), MaxPool 2, Flatten, densa 32 ReLU, dropout 0.2, sigmoide.
- Adam 0.001, entropía cruzada binaria, batch 64, semilla 42, CPU.
- Sin pesos de clase, sin balanceo, sin aumento artificial de imágenes.
- Ajuste 2020–2021, veinte calendarios d50, misma muestra y orden canónico L0.
- Validación 2022, calendarios 01–10, muestra 1/8 por estación como L0.
- Máximo 60 épocas, EarlyStopping val_loss/paciencia 8/min_delta 0, mejores pesos.
  E = primera época con menor val_loss, no la última ejecutada.
- Sigma heredada de L0 2020–2022 y a14 con escala 2020–2021, media causal.
- Se cargan mapa PCA y escalador ya ajustados sobre las 19 840 ventanas de
  entrenamiento auditadas. No se ajustan otra vez en la caché completa y no
  se usa validación para cambiar mínimos, máximos, posiciones ni resolución.
- Escalado adicional por columna sin recorte. La caché guarda X L0 ANTES de ese
  escalado; al formar un lote se escala y se coloca cada columna en su píxel.
- Comparador futuro: modelo SELECCIÓN L0 d50 en `lstm_local_examen`, cargado de
  disco, no el definitivo que ya aprendió con 2022.

El mapa por roles no es un mapa geográfico de CDMX. La asignación única no es
la rasterización original TINTO. La CNN cambia arquitectura además de formato
respecto a L0; la comparación se interpreta entre sistemas completos.

## Datos preparados y verificaciones

Caché:
`results/exploracion_tinto_2022/preparacion_20261029/cache_completa/`.

| Subconjunto | Ventanas | Positivas |
|---|---:|---:|
| Ajuste 2020–2021 | 1 357 800 | 8 310 |
| Validación 2022 | 339 450 | 2 225 |

Se reconstruyen mediante `entrenar_lstm_local.ejemplos`, con índices verificados
contra `ventanas_locales` y `lstm_local.muestra`. Los hashes del X e y completos
de ajuste coinciden EXACTAMENTE con los de la auditoría previa de L0. Cada
manifiesto conserva calendario, objetivo, hora final, posición de matriz y etiqueta.
Etiquetas y metadatos no entran a la imagen.

`LISTO.json` se escribe solo al completar conteos, hashes y guardado. El programa
de entrenamiento exige ese archivo, verifica configuración, mapas, escalador y
hashes de las cuatro matrices NPY antes de entrenar. No reutilizar una caché
incompleta que carezca de ese marcador. Carpetas existentes nunca se sobrescriben.

En Xtr completo, aplicar el escalador congelado da rango aproximado
[−1.0681, 1.8264]; 36 913 de 553 982 400 valores quedan fuera de [0,1] (~0.00666 %).
Se conservan esos números. No es un error de MinMax: se ajustó sobre una muestra,
no sobre todos los extremos de entrenamiento. No se recortan silenciosamente ni
se cambia el escalador por ver esta auditoría. Fuente:
`preparacion_20261029/rango_escalado_entrenamiento.json`.

## Comprobación pequeña del programa

Caché `cache_smoke1`: dos calendarios para ajuste, uno para validación, las 31
estaciones, ocho posiciones repartidas a lo largo de la muestra original por
estación/calendario. 496 ventanas de ajuste y 248 de validación, dos positivas
en cada subconjunto. No es un muestreo representativo para estimar métricas.

Se ejecutaron `modelo_smoke1` y `modelo_smoke2`, dos épocas cada uno:

- 8 lotes completos por época en ambas; sin agotarse el generador entre épocas.
- Imagen float32 recupera exactamente el vector escalado float32.
- Modelos guardados y recargados dan predicciones idénticas.
- Pesos, historias y predicciones idénticos entre ejecuciones.
- No se interpretan las pérdidas de este ensayo como evaluación científica.

Una primera comprobación usó las primeras ocho posiciones y no contenía
positivos; se cambió el muestreo SOLO del ensayo de software a ocho posiciones
uniformemente repartidas, sin consultar etiquetas. No cambió el muestreo completo
L0, arquitectura ni reglas de selección. El ensayo final usa dos épocas para
verificar reiteración y cobertura de lotes, no para elegir parámetros.

## Ejecución

Desde la raíz con el entorno del repositorio. Se necesita espacio para unos
2.8 GB de matrices crudas X/y, más manifiestos y modelos. Las matrices se abren
con mmap; no se materializan de golpe los ~5.56 GB de imágenes completas.
Un lote de 64 imágenes ocupa 256 KiB antes de activaciones de la CNN.
El coste total incluye buffers y memoria que el sistema reserva a páginas de disco.

### Preparar (ya realizado)

```sh
MPLCONFIGDIR=/tmp/tinto-mpl .venv/bin/python experiments/exploracion_tinto/entrenar_tinto_l0.py preparar --salida results/exploracion_tinto_2022/preparacion_20261029/cache_completa
```

Para repetir, usar OTRA carpeta: el comando anterior rechazará la ya existente.

### Entrenamiento completo de selección (aún no ejecutado)

```sh
MPLCONFIGDIR=/tmp/tinto-mpl .venv/bin/python experiments/exploracion_tinto/entrenar_tinto_l0.py entrenar --cache results/exploracion_tinto_2022/preparacion_20261029/cache_completa --salida results/exploracion_tinto_2022/seleccion_tinto_v1/corrida1
```

Repetir con `corrida2` y comparar pesos, historia y probabilidades de control.
La semilla de entrenamiento es la misma; el barajado no necesita reproducir el
orden de minibatches de la LSTM para conservar los mismos ejemplos. Se usa una
permutación sin reemplazo por ciclo y el Dataset repite ciclos con pasos
explícitos por época. La validación conserva el orden y completa sus pasos.

El piloto previo sugirió varios minutos de cómputo por época completa en esta
CPU, sin preparación/validación. No se promete duración total: depende de E,
EarlyStopping, máquina, I/O y repetición. Este ensayo de software no es un
benchmark del entrenamiento completo.

### Ensayo pequeño reproducible

```sh
MPLCONFIGDIR=/tmp/tinto-mpl .venv/bin/python experiments/exploracion_tinto/entrenar_tinto_l0.py preparar --prueba --salida results/exploracion_tinto_2022/prueba_nueva/cache
MPLCONFIGDIR=/tmp/tinto-mpl .venv/bin/python experiments/exploracion_tinto/entrenar_tinto_l0.py entrenar --cache results/exploracion_tinto_2022/prueba_nueva/cache --salida results/exploracion_tinto_2022/prueba_nueva/modelo
```

Las salidas indican `prueba=true`: no se mezclan con selección completa.

## Después del entrenamiento

Este programa prepara y entrena; todavía NO implementa el informe comparativo
por estación-día. La siguiente etapa calculará puntajes horarios completos en
2022 limpio y calendarios de validación, promedio diario mínimo 12 horas,
misma muestra de días y umbrales p99/p99.9 por detector; comparación con L0.
Se reportarán F1/recall/precisión y sus controles sin ataque, no la exactitud
sobre entrenamiento. No se selecciona por las métricas del ensayo pequeño.

Los años 2023–2026 siguen fuera de este programa. Antes de entrenamiento
científico y comparación, incorporar esta configuración al registro de la
exploración/protocolo que corresponda; esta preparación no modifica ni reutiliza
los resultados aceptados de L0/V4/V4S ni habilita nuevos exámenes.

## Registro y ejecución completa T1 (2026-10-29)

El tesista autorizó registro y selección completa. Se añadió T1 al protocolo
y una nota de progreso antes de iniciar. `seleccion_tinto_v1/registro_previo.json`
conserva los hashes anteriores al arranque.

Tras dos ensayos técnicos de rendimiento, se habilitó oneDNN para CPU antes de
completar la primera época. La medición de 40 lotes calientes mostró ~0.0165 s
por lote frente a ~0.0272 s sin la optimización, con carga concurrente; no es
un benchmark independiente ni se usaron pérdidas de validación para decidir.
Dos pruebas pequeñas con el entorno optimizado dieron pesos y predicciones
idénticos. XLA no se usa: la prueba técnica indicó que el modelo no lo admite.

Las primeras `corrida1/2` fueron interrumpidas antes de cualquier época o
validación completas (exit 130); se conservan sus archivos parciales. Las
corridas completas válidas son `corrida_cpu1/2`, con el mismo código y entorno
entre ellas. No se mezclan checkpoints entre intentos. Los cambios afectan
runtime y registro del avance, no arquitectura/datos/regla de selección.
Constancias: `registro_runtime_cpu.json` e `interrupcion_tecnica_previa.json`.

Comando vigente para una carpeta nueva:

```sh
TF_ENABLE_ONEDNN_OPTS=1 MPLCONFIGDIR=/tmp/tinto-mpl PYTHONUNBUFFERED=1 .venv/bin/python experiments/exploracion_tinto/entrenar_tinto_l0.py entrenar --cache results/exploracion_tinto_2022/preparacion_20261029/cache_completa --salida results/exploracion_tinto_2022/seleccion_tinto_v1/corrida_cpu1
```

La variable externa prevalece sobre el valor por defecto del programa y queda
registrada en su configuración, junto con dos hilos intra-op y uno inter-op.
Se solicita determinismo y se comprueba la repetición final; habilitar la
optimización no sustituye esa comprobación.

Cada corrida escribe `progreso.json` por fases/lotes, `historia_en_curso.csv`
por época, y `mejor_hasta_ahora.keras` al mejorar val_loss. Al terminar conserva
el modelo de selección con pesos restaurados y sus probabilidades de control.
El mejor checkpoint en curso no se usa como si fuera el resultado final.

Seguimiento compacto (no entrena):

```sh
.venv/bin/python experiments/exploracion_tinto/resumir_seleccion.py --raiz results/exploracion_tinto_2022/seleccion_tinto_v1
```

Cuando terminen ambas, `--guardar` verifica igualdad de pesos, historias y
probabilidades y guarda `reproducibilidad_final.json`. Las diferencias en
segundos de ejecución no se consideran fallos de reproducción.
