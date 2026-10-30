# Calibración Barcelona 2017 completada

Fecha: 2026-10-29. Se cargaron de disco los 15 modelos definitivos congelados
(L0 compartido, 13 V4 y PARAAD), sin reentrenamiento ni cambios de épocas.
Se siguió `registro_calibracion_barcelona_2017.md`, registrado antes de inferir.
Sólo se envió 2017 limpio con su historia previa; no se abrió el examen2018–2019.

Los tres métodos usan los mismos 4,536 estación-días. Se conserva el mínimo12
horas y la máscara común previamente fijada. Los puntajes son promedio diario
de probabilidad L0, absoluto del promedio firmado del residuo V4 dividido
por p95 horario propio de calibración y MAE observado estandarizado PARAAD.

| Detector | Umbral p99 | Umbral p99.9 |
|---|---:|---:|
| L0 | 0.07939487587039669 | 0.3565703355150459 |
| V4 | 0.8264102280385994 | 1.1151360751459871 |
| PARAAD | 0.6518237442166234 | 0.8184806300948063 |

Con alerta estricta puntaje>umbral, cada método produce 45/4,536 alertas
limpias en p99 (**0.9921%**) y 4/4,536 en p99.9 (**0.0882%**).
La resolución es 1/4,536; estos porcentajes son empíricos de calibración,
no garantías para el futuro ni evidencia de igual capacidad de detección.
Los umbrales numéricos no se comparan directamente porque las escalas de
los puntajes son distintas. «Limpio» significa sin inyección experimental.

Se repitió toda la inferencia dos veces en Colab CPU, TensorFlow2.21.0,
Keras3.13.2 y NumPy2.1.3. Se exigió igualdad exacta de todos los puntajes
diarios, salidas horarias L0/V4, coeficientes p95 y umbrales. Después, la
verificación local releyó hashes y modelos, cotejó la máscara y las agregaciones
horarias y recalculó umbrales/alertas. Las comprobaciones aritméticas locales
entre versiones NumPy/Pandas usan tolerancia1e-12; la duplicación remota sí
es exacta. Los 15 hashes de modelo coinciden con los del entrenamiento.

Artefactos en `results/barcelona_paraad/calibracion_2017_colab/`:

- `verificacion_final.json`: respaldo y controles locales, VM liberada.
- `recuperado/salidas/calibracion/congelado.json`: umbrales y hashes de modelos.
- `recuperado/salidas/calibracion/p95_v4.csv`: normalización de puntaje V4,
  congelada para ambos años de prueba; no altera sus entradas ni sus pesos.
- Misma carpeta: `resumen.csv`, `puntajes_<detector>.csv`, máscaras y salidas
  horarias para auditar la agregación.

```sh
.venv/bin/python -m experiments.barcelona.verificar_calibracion_2017
```

La VM de calibración se liberó tras descargar y verificar el respaldo.
Se cerró el seguimiento. No hay todavía F1/recall de Barcelona. Sigue la
evaluación de los modelos y umbrales congelados en 2018 y 2019 con los
calendarios proporcionales ya fijados, sin usar sus resultados para elegir
configuraciones ni volver a entrenar.
