# Entrenamiento Barcelona completado

Fecha: 2026-10-29. Modelos **recién entrenados en Colab CPU**, no cargados
de RAMA. Las tres corridas terminaron, sus respaldos completos están locales
y sus VMs fueron liberadas. No se realizó calibración ni evaluación de detección.

## Selección y ajuste definitivo

Ajuste inicial 2014–2015, selección exclusivamente con 2016 y ajuste definitivo
desde cero con 2014–2016, en calendario UTC registrado. No se enviaron datos
de calibración 2017 ni prueba 2018–2019 a estas sesiones.

| Detector | Configuración seleccionada | Pérdida mínima de validación |
|---|---|---:|
| L0 compartido | δ50, dropout0.2, 2 épocas | BCE 0.023046273738145828 |
| V4 | 13 modelos por estación, dropout0.2, 3–8 épocas | MSE por estación, tabla CSV |
| PARAAD-SA | dropout0.1, 481 épocas | MSE observada 0.17447622913744953 |

No se comparan estas pérdidas entre métodos: BCE, MSE física del residuo V4
y MSE estandarizada de reconstrucción PARAAD miden objetivos distintos.
La elección de dos épocas de L0 es el mínimo de validación de la regla fijada,
no un fallo ni un motivo para aumentar épocas mirando resultados posteriores.

La selección L0 ejecutó diez épocas, no sólo dos: BCE de validación fue
0.023926 en la primera, 0.023046 en la segunda y no mejoró durante las ocho
siguientes; EarlyStopping conservó la segunda. La pérdida de ajuste sí siguió
bajando. Esto motiva la parada prevista, sin demostrar todavía desempeño de
detección. Durante selección L0 tuvo 546,500 ventanas/batch64 (8,540
actualizaciones por época), frente a unos cientos de bloques/batch256 de
PARAAD (tres actualizaciones por época). Las épocas no son una unidad común
de trabajo ni los objetivos BCE y reconstrucción representan la misma tarea.

PARAAD evaluó los tres candidatos registrados durante 500 épocas cada uno:

| Dropout | Época de mínimo | MSE limpia 2016 |
|---|---:|---:|
| 0.1 | 481 | 0.17447622913744953 |
| 0.3 | 457 | 0.18625790260353142 |
| 0.5 | 481 | 0.17550450925017802 |

L0 usó 546,500 ventanas iniciales (4,196 positivas) y 135,320 de validación
(1,056 positivas), tras muestrear 1 de cada8 horas por calendario/estación.
Estos son conteos de preparación, no medidas de detección. Sólo L0 recibió
ataques y etiquetas durante el ajuste; V4 y PARAAD usaron datos limpios.

## Reproducibilidad y respaldo

Entorno CPU de un hilo: Python3.13.18, TensorFlow2.21.0, Keras3.13.2,
NumPy2.1.3. Semilla42 inmediatamente antes de construir y de entrenar.
Se verificaron 32 pares (64 entrenamientos científicos): selección y definitivo
de L0, selección y definitivo de los 13 V4 y los tres candidatos de selección
más definitivo de PARAAD. Los smoke quedan separados de estos conteos.

En cada par son exactamente iguales las historias completas, todos los pesos,
variables del optimizador y la predicción de control fija de hasta256 ejemplos.
También se verificó la recarga del modelo guardado. No se afirma identidad
numérica entre hardware/versiones ni se presentan estos controles como una
evaluación completa de inferencia de prueba.

`experiments/barcelona/verificar_entrenamiento_colab.py` releyó los artefactos
descargados, comprobó los hashes del paquete y suplemento de fuentes, entradas,
snapshots, unidades completas y controles, y confirmó el número definitivo
de épocas. No importó TensorFlow ni abrió datos de calibración/prueba.

Base: `results/barcelona_paraad/colab_20261029/`:

- `verificacion_entrenamiento.json`: control global de los 32 pares,
  15 modelos definitivos y tres VMs liberadas.
- `seleccion_modelos_verificada.csv`: épocas/pérdidas y SHA-256 de cada modelo.
- `<detector>/recuperado/salidas/<detector>/`: resultados científicos,
  selecciones, `congelado.json` y subcarpetas de repeticiones.
- L0/PARAAD definitivo: `definitivo/r1/modelo.keras` (r2 es control).
- V4 definitivo: `<código EOI>/definitivo/r1/modelo.keras` (r2 es control).
- `intento1/`: diagnóstico del fallo de instalación previo a entrenar,
  conservado como historial; no se mezcla con las corridas completas.

```sh
.venv/bin/python -m experiments.barcelona.verificar_entrenamiento_colab
```

## Lo que puede concluirse y siguiente fase

La preparación permite entrenar los tres detectores en las 13 estaciones
con separación temporal y reproducibilidad verificadas. Todavía **no hay
F1, recall ni comparación de capacidad de detección en Barcelona**.

Sigue cargar estos modelos congelados y calibrar p99/p99.9 con 2017 limpio
sobre la máscara común de 4,536 estación-días. Después se evaluarán 2018 y
2019 con los calendarios/deltas registrados, sin ajustar hiperparámetros.
No se inició esa fase durante el seguimiento del entrenamiento.

Permanece la limitación de alcance: 13 estaciones propias de la misma fuente,
convención temporal operativa, máscaras y umbrales distintos de la configuración
exacta de ocho estaciones del artículo. El experimento es controlado y no se
presenta como reproducción literal de sus tablas publicadas.
