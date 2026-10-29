# Cierre de la exploración TINTO T1 — 2026-10-29

## Conclusión y alcance

La variante TINTO-PCA con asignación única propia conserva las 408 entradas de
L0 en una imagen 32 × 32 y permite entrenar/evaluar una CNN. En la evaluación
exploratoria de 2022, L0 tiene mayor F1 y recall en las seis condiciones
δ100/50/20 × p99/p99.9. Se cierra este piloto sin abrir nuevas variantes ni
años de examen. La evaluación se repitió con resultados exactamente iguales.

Esta conclusión corresponde al sistema completo probado: representación,
arquitectura y checkpoint. No aísla el efecto del mapa frente al de la CNN,
ni permite generalizar a todos los métodos tabular-imagen o a toda TINTOlib.

## Qué se hizo y qué quedó como propuesta

| Etapa | Estado y hallazgo |
|---|---|
| Ejemplos inventados | Demostración de mapa, escala, etiquetas separadas y difuminado; sin evidencia de detección real |
| Auditoría L0 | 1 357 800 ventanas de ajuste; muestra canónica de 19 840 ventanas |
| Resolución original | 32/64/128/256: ninguna conserva todas las características L0 sin sobrescritura |
| Redundancia | Hora 48→2 reconstruible; 408→362 no soluciona por sí sola las colisiones; máscaras y a14 se conservan |
| Asignación única | 408/362 y lados 32/64 sin sobrescritura; modifica las vecindades del PCA original |
| Canales por tipo | Control de conservación prototipado; sin entrenamiento de este brazo |
| Difuminado y geografía | Ejercicio didáctico de difuminado; barrido de detección y contraste geográfico cuantitativo no ejecutados |
| Piloto CNN | Aprendizaje observado; el control sintético no alcanzó la pérdida<0.1 prefijada; se conserva ese resultado |
| Selección T1 | Un candidato 408/32×32, dos entrenamientos; cierre manual, checkpoint época 5 |
| Evaluación Colab | Dos inferencias completas idénticas; modelos de disco, 2022, diez calendarios y tres intensidades |

La propuesta inicial de cuatro experimentos evolucionó hacia un solo candidato
por decisión del tesista. No se presentan todos los brazos inicialmente
propuestos como ejecutados. Tampoco se entrenó la CNN temporal de control,
necesaria si se quisiera aislar representación frente a arquitectura.

## Contrato de entrada e imagen

Una imagen corresponde a **una estación objetivo y una hora final t**. Contiene
las 24 horas t−23…t; no es una imagen agregada por día ni una imagen global de
las 31 estaciones. Hay cinco roles: objetivo y sus cuatro vecinas por distancia.

Por hora: relativa, máscara y comparación a14 de cada uno de los cinco roles,
más seno y coseno de la hora: 5×3+2=17 características. Se aplana 24×17=408,
en orden hora→rol→tipo, con la hora cíclica al final de cada fila. La etiqueta
se mantiene separada. No se incluye un identificador de estación en los píxeles.
La geografía determina el vecindario, pero las coordenadas de los píxeles
proceden de PCA y de la asignación de coste mínimo, no de latitud/longitud.

Mapa y MinMax propios ajustados sobre la muestra de 19 840 ventanas de
2020–2021 y cargados congelados durante la evaluación. Se conservó la
normalización histórica L0: sigma de 2020–2022 limpio y escala a14 ajustada
con 2020–2021. Esta herencia debe declararse; no se afirma que todos los
estadísticos de preprocesamiento se hayan ajustado exclusivamente con 2020–2021.
Los perfiles temporales se calculan de forma causal como en L0.

La conversión usada es `pixel = float32(float64(valor_L0)*scale + offset)`.
Cada característica tiene su posición fija; 408 píxeles ocupados y 616 vacíos
con cero. No hay difuminado, estirado por imagen ni recorte nuevo a[0,1].
Un cero puede ser fondo o un valor válido: el mapa permite distinguirlos.
Las matrices float32 en memoria alimentan la CNN; los colores de las figuras
son una presentación y no entran al clasificador. No se cuantiza a PNG para
la inferencia. La asignación única es una modificación explícita; no es la
rasterización original sin cambios de TINTOlib.

## Modelo, parada y evaluación

CNN: Conv8/pooling2, Conv16/pooling2, flatten, densa32, dropout 0.2 y sigmoide;
34 081 parámetros, Adam 0.001, BCE, batch 64. Ajuste con veinte calendarios d50
y las mismas ventanas L0 de 2020–2021; validación 2022. Regla inicial:
máximo 60 épocas y paciencia 8. El tesista pidió detener por coste de recursos:
una corrida completó ocho épocas y otra nueve; ambas tienen el mínimo observado
en época 5, val_loss 0.02639667876. No se declara EarlyStopping completado.
Las ocho historias comunes y los pesos internos del checkpoint son idénticos.

Evaluación: TINTO época 5 y L0 selección d50, ambos cargados de disco. Colab CPU,
dos ejecuciones paralelas, sin entrenar. Cada ejecución procesó limpio 2022 y
diez calendarios para cada δ100/50/20. Salida por estación-hora, enmascarada
según dato objetivo y promediada por estación-día con mínimo 12 horas observadas.
Se usaron 9661 estación-días comunes globalmente para ambos modelos y todas
las matrices; métricas agrupadas sobre los diez calendarios, no media de F1.

Umbral común a estaciones, propio de cada detector, sobre los mismos días
limpios de 2022; alerta estricta `s > u`. p99 y p99.9 corresponden a niveles
nominales de falsas alarmas 1 % y 0.1 %; no son parámetros de difuminado ni
garantías de tasas futuras. Se guardaron métricas completas, contingencias,
puntajes diarios y control sin ataque. Bootstrap pareado de 2000 bloques
estación-mes con calendarios juntos y umbrales fijos; semilla[42,29,3].

## Resultados y límites

| δ | F1 TINTO p99 | F1 L0 p99 | F1 TINTO p99.9 | F1 L0 p99.9 |
|---|---|---|---|---|
|100%|0.4282|0.4519|0.4473|0.4996|
|50%|0.4105|0.4663|0.2035|0.3219|
|20%|0.0862|0.1467|0.0091|0.0158|

Media descriptiva F̄ de F1 p99 entre los tres δ: TINTO 0.3083 y L0 0.3550,
diferencia −0.0466. Se informa sin convertir retrospectivamente una regla
propuesta de avance en un criterio adoptado. La conservación uno a uno evita
sobrescritura, pero no garantiza mayor rendimiento ni conserva el orden temporal
o la geometría de las relaciones originales.

2022 se reutilizó para selección y evaluación exploratoria; la parada fue
manual. No es examen independiente. Los intervalos no incluyen incertidumbre
de entrenamiento ni umbral y conservan dependencia espacial de fondo. No se
afirma superioridad confirmatoria ni se autoriza por este cierre reutilizar
los años de examen. Una fase posterior requeriría protocolo y autorización
propios antes de examinar resultados, respetando el historial de años ya usados.

## Imágenes reales y fichas para explicarlas

Figuras en `results/exploracion_tinto_2022/imagenes_reales_20261029/corrida1/`.
Selección ilustrativa sin mirar predicciones: primer episodio 2022 de calendario 01
ordenado por inicio/estación/id y primera ventana totalmente dentro de él con
≥12 observaciones del objetivo y dato en la hora final. Resultado: SAC,
16 de enero de 2022, 00–23h, episodio 44, signo+, δ 50 %; vecinas NEZ/UIZ/UAX/TAH.
Se usa la matriz alterada ya evaluada y se recalculan las características
completas; no se altera directamente una imagen.

1. **01_comparacion_real.png.** Arriba, X=horas de la ventana y Y=ozono en ppb:
   lecturas limpias de las cinco estaciones y SAC alterada. Abajo, limpia,
   alterada y diferencia: X/Y=columna/fila 0–31; color=intensidad adimensional,
   misma escala 0–1 para las dos entradas. Diferencia con escala simétrica
   ±0.272962, rojo=aumento y azul=descenso. No es probabilidad, atribución de
   la CNN ni indicador de qué píxel provocó una alerta.
2. **02_leyenda_mapa.png.** X/Y=columna/fila; izquierda, color categórico de
   relativa/máscara/a14/hora_sin/hora_cos; derecha, desfase −23…0horas.
   Fondo gris=posición vacía. No son canales separados del modelo; es una
   leyenda de su único canal. La silueta no representa un mapa de la ZMVM.

En el ejemplo cambian las 24 lecturas de SAC, y cero lecturas de sus cuatro
vecinas. Cambian96 píxeles: 24 `obj_rel`, 24 `obj_vecinas`, 24 `v1_vecinas`
y 24 `v4_vecinas`. Algunas a14 de vecinas cambian porque recalculan su contexto,
aunque sus propias lecturas no cambien. Hora y máscaras permanecen iguales;
las regiones amarillas persistentes corresponden a máscaras con valor 1.
Es un caso ilustrativo: no se eligió por acierto y no se hizo inferencia nueva.

La fuente exacta, hashes y reglas se guardan en `metadatos.json`; tablas de
lecturas y correspondencia de 408 valores/píxeles en CSV; entradas24×17 e imágenes
32×32 en NPY. Dos ejecuciones deben coincidir antes de aceptar las figuras.
Conservar estas dos figuras con sus fichas para la presentación al asesor.

## Índice de evidencias

- [Metodología y cambios cronológicos](../experiments/exploracion_tinto/metodologia_v1.md).
- [Auditoría de entradas](../experiments/exploracion_tinto/auditoria_l0_20261028.md).
- [Resolución](../experiments/exploracion_tinto/resultados_resolucion_20261028.md),
  [redundancia](../experiments/exploracion_tinto/redundancia_l0_20261028.md),
  [hora compacta](../experiments/exploracion_tinto/resultados_hora_compacta_20261028.md),
  [prototipos](../experiments/exploracion_tinto/resultados_prototipos_20261028.md).
- [Configuración congelada](../experiments/exploracion_tinto/configuracion_entrenamiento_v1.json)
  y [cierre manual](../results/exploracion_tinto_2022/seleccion_tinto_v1/informe_cierre_manual.md).
- [Evaluación: métricas, intervalos y controles](../experiments/exploracion_tinto/informe_evaluacion_colab_20261029.md).
- [Ejecución, paquete y seguimiento Colab](../experiments/exploracion_tinto/colab_evaluacion_2022.md).
- [Código de visualización](../experiments/exploracion_tinto/visualizar_entradas_reales.py).

Resultados Colab descargados en
`results/exploracion_tinto_2022/preparacion_colab_20261029/resultados_descargados/`;
`verificacion_descarga.json` conserva el cierre de integridad/reproducibilidad.
La sesión fue liberada y su automatización eliminada. No queda entrenamiento
ni evaluación pendiente en ejecución para T1.

Verificación de figuras completada: dos ejecuciones con todos los archivos
idénticos byte a byte, incluidos PNG, NPY, CSV y metadatos; recuperación de los
408 valores escalados desde sus píxeles comprobada contra NPY float32. El CSV
es consulta decimal; NPY conserva los valores exactos. Registro:
`results/exploracion_tinto_2022/imagenes_reales_20261029/verificacion_figuras.json`.
