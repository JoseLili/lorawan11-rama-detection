# Laboratorio de codificación del payload

Primer ejercicio: inspeccionar una medición de 160 ppb y entender un flip del
bit 5 antes de diseñar la representación propuesta por el asesor.

## Archivos del ejemplo

| Archivo | Contenido hexadecimal | Valor decodificado |
|---|---|---:|
| `samples/o3_160ppb.bin` | `01 02 00 A0` | 160 ppb |
| `samples/o3_160ppb_flip_bit5.bin` | `01 02 00 80` | 128 ppb |

Cada archivo contiene **cuatro bytes binarios**, no caracteres que escriban el
hexadecimal. Se generan con las funciones de `src/encoding/cayenne.py`.

Desde la raíz del repositorio puedes reproducirlos y verificar sus valores:

```bash
.venv/bin/python experiments/cayenne_mod/generar_ejemplo.py
```

Usamos el entorno del proyecto porque el paquete de codificación también
importa la dependencia criptográfica PyCryptodome.

El script comprueba los bytes esperados, la decodificación y que sólo cambie un
bit. Conserva las muestras existentes; si modificaste alguna, avisa en lugar
de sobrescribirla.

## Cómo leer el payload

| Desplazamiento en bytes, desde 0 | Hexadecimal | Significado |
|---:|---|---|
| 0 | `01` | Canal 1 |
| 1 | `02` | Tipo Analog Input |
| 2–3 | `00 A0` | Entero de 16 bits con signo, big-endian: 160 |

La tesis reinterpreta ese entero a **1 ppb por unidad**. Es una convención del
proyecto: Analog Input de CayenneLPP normalmente usa escala 0.01. Un
decodificador genérico no interpretaría automáticamente estos bytes como
160 ppb. Véase [la decisión de codificación](../../docs/02_codificacion.md).

El valor 160 se descompone en `128 + 32`: están encendidos los bits 7 y 5.
Numeramos los bits desde 0, empezando por el menos significativo del valor.
El bit 5 está en el último byte del campo, aunque el campo ocupa dos bytes.

```text
original: 00000000 10100000 = 160
máscara:  00000000 00100000 =  32
XOR:      00000000 10000000 = 128
```

XOR invierte la posición seleccionada. Aquí resta 32 porque el bit ya era 1.
Aplicar el mismo flip a 128 lo vuelve 160: el sentido depende del dato.

Usando el umbral experimental de 155 ppb, esta lectura pasa de estar por
encima a quedar por debajo. Eso demuestra un cruce local; para afirmar que se
oculta el cruce de toda la red hay que comprobar las demás lecturas.

Estas muestras son payloads **sin cifrar** para estudiar la representación.
No contienen la trama LoRaWAN completa y este ejercicio aún no ejecuta el
ataque sobre texto cifrado ni implementa la contramedida.

El ejercicio completo, incluyendo la guía de GNU poke y una celda Python
ejecutable, está en [el notebook de inspección](01_inspeccion_payload.ipynb).

## Continuación de los experimentos

1. [Inspección del payload](01_inspeccion_payload.ipynb): entender el cambio 160 → 128.
2. [Repartir el peso del bit 5](02_repartir_peso_bit5.ipynb): primera propuesta V1.
3. [Distribución real de ppb](03_distribucion_real_ppb.ipynb): frecuencias y valores cerca del umbral.
4. [Comparación sobre RAMA 2025](04_comparacion_pesos_rama.ipynb): actual, control de rango, V1 y V2; uno y dos flips sobre las 16 posiciones.

El [resumen para la junta](avance_junta_04.md) explica el resultado del experimento
04: V2 reduce cruces hacia arriba, pero aumenta los cruces hacia abajo entre las
lecturas originalmente altas bajo selección uniforme de máscaras. Los rechazos
se contabilizan aparte. No se ha validado una contramedida definitiva ni se ha
evaluado esta propuesta junto con el LSTM.

## Experimento 05: distribuciones A y B con los detectores del notebook 09

[Abrir el notebook 05](05_distribuciones_A_B_red.ipynb).

- **A:** contribución de 16 → dos bits de 8; contribución de 32 → dos de 16.
- **B:** contribución de 16 → dos bits de 8; contribución de 32 → cuatro de 8.

Se comparan con un control binario de igual dominio 0–255. Se evalúa un flip
por mensaje sobre las 16 posiciones, incluidas las nuevas, conservando los
pesos de 64 y 128. Se cuentan directamente cambios de banda y falsas
excedencias que escapan a los detectores por estación, usando sus predicciones
y p95 guardados; no se entrena ni recalibra. El análisis anual de ocultamientos
se mantiene separado, sin extrapolar detección al año completo.

La única celda ejecutable verifica las fuentes, valida 12 288 escenarios a
través del cifrado y exige dos cálculos idénticos antes de guardar resultados
en `resultados/05/`. No modifica las referencias del 09 ni los experimentos
anteriores. El rango definitivo del formato, otros presupuestos de ataque y
la validación en otro año siguen pendientes.

Pruebas del cálculo:

```bash
.venv/bin/python -m pytest experiments/cayenne_mod/test_selectiva_red.py -q
```
