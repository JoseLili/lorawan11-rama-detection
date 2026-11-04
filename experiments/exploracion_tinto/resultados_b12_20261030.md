# B12: dos imágenes de 12 horas — resultado exploratorio

Cierre: 2026-10-30, hora de Ciudad de México (verificación UTC 2026-10-31).
Paso 3 COMPLETADO en su reintento autorizado. Se conserva el intento anterior
sin artefactos recuperados; no se sustituyen ni se ocultan sus incidencias.

## Procedencia e integridad

B12: una única CNN aplicada a ambos bloques, recién entrenada dos veces desde cero en GPU L4, TF2.21.0/Keras3.13.2.
Cada corrida completó 13 épocas por paciencia8 y seleccionó la época5;
val_loss=0.028816280886530876. Duración con inferencia: 7.9293 y7.9913 minutos.
No es parada manual. Pesos internos HDF5, historias, 31 matrices de scores
por día y 31 de scores por bloque idénticos entre corridas; comprobado localmente.
No se reentrenó L0 ni ED: se cargaron sus puntajes históricos guardados.

Resultados descargados y verificados antes de detener exclusivamente la sesión
`tinto-b12-r1-20261030`. TAR de 10 407 456 bytes, SHA256:
`d8d1f0ed709aab0991c26ee52141155fb38046901318f396c7f51a1abed94fcc`.
También se conservan respaldos intermedios de cada corrida. Raíz de artefactos:
`results/exploracion_tinto_2022/b12_20261030/reintento1/`.
`reproducibilidad_local.json`, `respaldos/`, `resultados_descargados/salidas/`
y `evaluacion/` contienen evidencia y modelos; no hacen falta nuevas descargas.

## Métricas por estación-día

Mismo soporte de 9 661 estación-días, diez calendarios y umbral propio por
modelo calibrado con limpio2022. F1 agrupado sobre calendarios; B12 diario
es la media ponderada por horas observadas de los scores de sus dos bloques.
Las dos corridas B12 dan los mismos números.

| Detector | F1 p99 d100 | F1 p99 d50 | F1 p99 d20 | Media principal |
|---|---:|---:|---:|---:|
| B12 (dos imágenes) | 0.4366 | 0.4083 | 0.0838 | 0.3096 |
| ED (una imagen diaria, histórico) | 0.4460 | 0.4120 | 0.1092 | 0.3224 |
| L0 (histórico) | 0.4519 | 0.4663 | 0.1467 | 0.3550 |

Con p99.9 (secundario), F1 B12 d100/d50/d20=0.5645/0.2708/0.0114;
ED=0.6355/0.4014/0.0136; L0=0.4996/0.3219/0.0158. El caso d100 supera
puntualmente L0 en ese umbral, pero no cambia el criterio principal registrado.
Tablas completas con precision, recall, falsas alarmas, AP e intervalos pareados
contra L0/ED se conservan en evaluacion; no seleccionar umbrales a posteriori.

Regla previa: media F1 p99 >= L0+0.02 =0.3749505 en ambas corridas.
B12 NO PASA (0.3095582; diferencia frente a L0=-0.0453923).
Frente a ED, diferencia de medias=-0.0128146. Estas son diferencias descriptivas,
no afirmaciones de significancia global ni rendimiento fuera de2022.

## Qué concluye y qué no

La representación de dos bloques es técnicamente viable y reproducible.
Esta CNN y agregación no mejoraron el criterio principal frente a ED ni L0.
No demuestra que dividir el día sea inútil para cualquier arquitectura:
B12 y ED difieren también en supervisión por bloque/diaria y mapas; L0 usa
contexto previo al día. Las pruebas con episodios de días completos tampoco
certifican localizar ataques breves o aprender el paso23→00.

2022 se reutilizó para selección y evaluación: todo sigue siendo exploratorio,
no examen independiente. Dos corridas de igual semilla acreditan reproducción,
no variabilidad entre semillas. No se abrieron2023–2026.

Según el orden registrado, el siguiente brazo es S12 (dos imágenes → CNN
compartida → LSTM). No se descarta por este resultado, pero NO se inició
ni se ajustó su arquitectura mirando estas métricas. Requiere completar su
configuración técnica previa. S1 también permanece pendiente.

Evaluación local repetida: todos los archivos numéricos idénticos por SHA256.
