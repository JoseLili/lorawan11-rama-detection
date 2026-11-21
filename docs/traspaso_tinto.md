# TINTO — documento general y traspaso a la PC principal

## Modelo provisional congelado y piloto pareado terminado — 2026-11-11

Paquete congelado: `results/tinto_congelado_20261111/`, CNN+GRU diaria D2,
réplica1, mejor época16,11104 parámetros; mapa,escala,protocolo y hashes incluidos.
No reentrenar ni sustituir este paquete para mejorar la comparación.

Se recibieron ZIP2020–2026 en la carpeta externa
`../drive-download-20261104T005948Z-1-001/` relativa a BDRAMA (no al repo).
Se verificaron y usaron O3 de2020–2025. Comparador: Ens-Vb-X definitivo, cinco
modelos Vb_R (115525 parámetros totales) y tau0.259588868885851, sin cambios.

Protocolo: `experiments/tinto_raw/protocolo_pareado_final.md`. Ejecución:
`comparar_final.py`; verificación independiente e informe: `resumir_pareado.py`.
Resultados completos válidos: `results/tinto_pareado_final_20261111_v2/`.
La carpeta sin v2 corresponde a preparación interrumpida por dependencia y
cambio del código de verificación; no es otra corrida científica.

Calibración2023 sobre3446 casos comunes, evaluación2025 sobre3109; primer
calendario histórico final_2025_01 (36 episodios antes de elegibilidad), doce
escenarios separados.42 estación-días positivos y3067 negativos por escenario.
Ataques sostenidos entran en historia de ambos; no balance50/50.96 métricas
recalculadas desde scores, fuentes/modelos verificados y umbrales históricos
Ens-Vb-X reproducidos con discrepancia menor que1e-5. No reentrenamiento.

P99, recall/precisión TINTO frente a Ens-Vb-X: x2=71.43/28.30% frente a
100/58.33%;x1.5=40.48/19.10% frente a90.48/59.38%;+20ppb=33.33/15.73%
frente a97.62/61.19%;+40ppb=59.52/23.81% frente a100/60.00%.
FA en originales2025 (TINTO/Ens-Vb-X):p95=222/130,p98=102/44,p99=73/21,
p99.9=7/0; teóricas sobre3109=155.45/62.18/31.09/3.109. No confundir con
FP dentro de calendarios alterados, que incluyen efectos posteriores.

Conclusión limitada: en este piloto no supera al detector final. TINTO usa menos
parámetros y no necesita vecinas, pero tiene menor cobertura (3109 frente a8822
días elegibles propios de Ens-Vb-X), más falsas alarmas y peor detección general.
Un calendario, pocos positivos, ventanas dependientes y año ya usado: no examen
independiente ni veredicto universal. No cambiar umbrales con resultados2025.

## Orden temporal explícito — 11 de noviembre de 2026

Se completó `experiments/tinto_raw/orden_temporal.py`, registrado en
`protocolo_orden_temporal.md` en la misma carpeta. Resultados:
`results/tinto_orden_temporal_20261111/`. Dos días previos elegidos por cobertura,
antes de resultados:4625 ajuste,884 selección,3449 evaluación. CNN compartida por
día + GRU diaria y GRU horaria de48 pasos; salida24 lecturas futuras en ambos.
El comparador horario recupera valores por el mapa: no demuestra aporte de TINTO.

Todas las secuencias se contrastaron con la tabla auditada: misma estación,
48 horas consecutivas,23→00 separado1h, sin objetivo/futuro de entrada. Esto no
valida la convención SIMAT heredada HORA1→00. Dos réplicas idénticas por modelo,
recarga verificada. Invertir48 horas eleva MSE horario0.01356→0.02155; sensibilidad
al orden/recencia, no demostración aislada de aprendizaje de medianoche.

En soporte común, recall p99 (AE/CNN-GRU diaria/GRU horaria):
x2=37.92/85.50/84.17%;x1.5=12.73/43.81/41.17%;
+20ppb=2.06/70.08/64.19%;+40ppb=1.88/100/100%. Reducciones aún débiles.
FA por modelo sobre3449: p95=172,p98=68,p99=34,p99.9=3; teóricas
172.45/68.98/34.49/3.449. Calibración reutiliza2022; historia sin ataque.
No atribuir ganancia únicamente a temporalidad: cambian tarea y arquitectura.
Se guardaron144 evaluaciones y checksums verificados. La consola falló únicamente
al imprimir el resumen final (flecha Unicode); archivos completos ya guardados.
Para reproducir usar `python -X utf8 ...` y una salida nueva.

## Continuación temporal — 11 de noviembre de 2026

Experimento autorizado y terminado: siete imágenes estación-día anteriores como
canales cronológicos para predecir el día objetivo, sin ataques de entrenamiento.
Protocolo: `experiments/tinto_raw/protocolo_temporal7.md`; código: `temporal7.py`
en esa carpeta. Resultados válidos: `results/tinto_temporal7_20261111_final/`.
La carpeta sin sufijo `_final` conserva un intento fallido al clonar/guardar el
modelo por la pérdida personalizada; se corrigió solo el guardado antes de repetir.

La exigencia de ocho días completos consecutivos dejó139 ajuste,38 selección y175
evaluación; ninguna secuencia2020. Evaluación:11 estaciones,91/175 bases deLLA.
Dos corridas idénticas, early stopping tras10 épocas, mejor época5; modelos
recargados y predicciones verificadas. Comparador autoencoder congelado sobre los
mismos175 objetivos y umbrales recalibrados en ese soporte para cada detector.

A p99, recall temporal/autoencoder: x2=51.43/65.14%, x1.5=17.14/32.00%,
+20ppb=15.43/9.14%, +40ppb=100/6.86%; reducciones fuertes siguen en0%.
No es superioridad general ni ablación pura: cambian objetivo, canales y número
de ejemplos de ajuste. Historia sin ataque: solo inicio aislado, no persistencia.
Falsas alarmas originales para ambos: p95=8,p98=3,p99=1,p99.9=0 sobre175.
La muestra pequeña y solapada impide interpretación operativa de p99.9.

## Criterio para próximos experimentos

Evaluación congelada de los 12 escenarios completada: protocolo
`experiments/tinto_raw/protocolo_evaluacion_12.md`, código
`experiments/tinto_raw/evaluar_12.py`, informe
`results/tinto_ae_12_escenarios/informe.md`. Se evaluaron 7154 originales de 2022
con p95/p98/p99/p99.9, sin entrenamiento; ambos modelos dieron reconstrucciones
idénticas y las métricas anteriores se reprodujeron. A p99, recall x2=35.505%,
x1.5=12.091%, +40ppb=1.663%, /2=0%. A p95, x2=60.092% y +40ppb=9.128%.
Las reducciones bajan el error respecto al original en más del 99.95% de las bases
para cada delta. Los desplazamientos aditivos tampoco generan alerta suficiente.
Se conservan diagnósticos por hora/estación y puntuaciones pareadas; estos resultados
no prueban que falte contexto. Falsa alarma medida sobre la misma calibración 2022.

El tesista fijó dos esquemas: delta porcentual 100/50/20/5% y error aditivo
positivo +5/+10/+20/+40 ppb. Aumentos y reducciones proporcionales confirmados:
x*(1+delta) y x/(1+delta), respectivamente. Fórmulas y cambios efectivos en
`experiments/tinto_raw/anomalias_futuras.md`. Esa nota registra también la dirección
de mejoras graduales: mantener estación-día y explorar ideas de contexto temporal
y espacial sin copiar las matrices del detector final. La falta de contexto sigue
siendo una hipótesis; no se ha demostrado como causa del bajo recall.

## Continuación en PC principal — autoencoder autorizado (2026-11-09)

El tesista autorizó continuar con un autoencoder convolucional entrenado solo con
originales estación-día, sin ataques inyectados. Esta decisión sustituye la
restricción histórica a supervisado descrita más abajo; el resto del documento
preserva el estado del traspaso anterior. No se modifican sus resultados.
Protocolo nuevo: `experiments/tinto_raw/protocolo_autoencoder.md`.
Implementación: `experiments/tinto_raw/autoencoder.py`.
Resultados de esta continuación: `results/tinto_autoencoder_20261109/`.
Estado: dos corridas completadas, 30 épocas, mejor época 27; pesos, historias y
scores idénticos. Modelos recargados y verificados. Informe:
`results/tinto_autoencoder_20261109/informe.md`. A p99, recall x1.5 ≈12.09%,
/1.5 ≈0.014%; la reconstrucción mejora pero la detección es insuficiente,
especialmente ante reducciones. No se cambió la regla tras observar ataques.
Se preparan 19300 originales completos: 5574 de 2020, 6572 de 2021 y 7154 de 2022.
El último trimestre de 2021 se reserva para selección interna; 2022 se usa para
calibración y evaluación exploratorias, sin abrir 2023–2026.

Actualización: 9 de noviembre de 2026. Este documento permite continuar sin el chat.
**Entrada recomendada para el siguiente asistente: leer este archivo completo y
`experiments/tinto_raw/protocolo.md` antes de ejecutar.**

## 1. Qué se está investigando y decisión vigente

Tesis sobre detección de anomalías en ozono de la red RAMA. TINTO transforma una
tabla numérica en imágenes; no detecta ataques por sí mismo. Una CNN posterior
aprende a clasificarlas. El tesista y su tutor solicitaron reiniciar con **O3 crudo
en ppb**, sin las características de L0. Se decidió continuar **supervisado y con
imágenes estación-día**. La alternativa autoencoder se explicó, pero NO se adoptó
ni se ejecutó. No está autorizado cambiar a no supervisado por iniciativa propia.

La última actividad ejecutada es un piloto CNN pequeño de cinco épocas. La
ampliación con calendarios L0 y calibración por percentiles está PROPUESTA, no
implementada ni ejecutada. No hay entrenamiento remoto que continuar ni monitor
TINTO activo de este chat al cierre documentado.

## 2. Dos líneas diferentes que no deben mezclarse

### Historia: TINTO con características de L0 (octubre)

Entrada estación local con cuatro vecinas, ventana24h:17 características porhora,
408 valores (relativas al perfil causal, disponibilidad, comparación vecinal,
seno/coseno). No eran ppb crudos. PCA nativo producía colisiones, por lo que varias
variantes usaron asignación propia de coste mínimo a píxeles únicos. Esa
modificación no debe describirse como rasterización TINTO nativa.

| Experimento | Representación/modelo | Estado y resultado exploratorio |
|---|---|---|
| T1 | Ventana local24h → CNN32×32, asignación única | Cierre manual, checkpoint época5; mediaF1p99≈0.3083 frente a L0≈0.3550 |
| T2 EH/ED/RH/RD | Estación-hora/día y red-hora/día, CNN | ED mejor de estas variantes, mediaF1p99≈0.3224; no superó L0 |
| B12 | Dos imágenes12h, CNN y agregación diaria | Dos corridas reproducibles; mediaF1p99≈0.3096 |
| S12 | Dos imágenes12h, CNN–LSTM con salida diaria | Dos corridas reproducibles; mediaF1p99≈0.3299 |
| S1 | 24 imágenes de una hora, CNN–LSTM | INCOMPLETO: sesión Colab desapareció; primera corrida rescatada, segunda no recuperada. No F1 final validado |

Referencias: `experiments/exploracion_tinto/resultados_t2_granularidad.md`,
`resultados_b12_20261030.md`, `resultados_s12_20261031.md`,
`protocolo_temporal_20261030.md` y
`results/exploracion_tinto_2022/s1_20261031/reintento1/incidente_20261104.md`.
L0/TINTO histórico reutilizaron2022 para selección/calibración/evaluación: números
exploratorios, no prueba independiente. No comparar esosF1 con el piloto raw50/50.
Las imágenes históricas solicitadas están en
`results/exploracion_tinto_2022/galeria_20261105/`.

### Línea activa: TINTO raw (noviembre)

Código: `experiments/tinto_raw/`. Resultados: `results/tinto_raw_20261109/`.
No reutilizar como entrada las matrices de características históricas. Reutilizar
mapas antiguos de408 características tampoco sería válido para las24 lecturas.

## 3. Fuente, fechas y faltantes

Solo O3: originales `data/raw/20RAMA.zip`, `21RAMA.zip`, `22RAMA.zip`, con XLS
internos2020O3.xls/2021O3.xls/2022O3.xls. El lector verifica hashes contra
`docs/checksums_2020_2026.txt`. Se extrajo una tabla de mediciones originales:
`results/tinto_raw_20261109/auditoria1/o3_raw_ppb.csv`. Se incluye para continuar
las representaciones sin necesitar copiar inmediatamente los ZIP originales.

Los ZIP raw están ignorados por Git: **un git pull NO los descarga**. Copiarlos
por separado a data/raw si se quiere repetir la ingesta desde la fuente. No hace
falta copiar años2023–2026 para continuar esta exploración. La tabla exportada
mantiene NaN y todas las estaciones originales; la selección de columnas se hace
explícitamente en cada experimento. Dos extracciones idénticas, valores re-leídos
comprobados exactamente contra los XLS.

| Etapa común con L0 | Periodo | Uso actual |
|---|---|---|
| Ajuste inicial |2020–2021|Mapas, escaladores y piloto CNN|
| Validación exploratoria |2022|Ejemplos y validación piloto|
| Ajuste definitivo futuro |2020–2022|No ejecutado para raw|
| Calibración futura |2023|No abierto para raw|
| Exámenes históricos |2024–2026|No abiertos para raw; ya usados por otras líneas|

RAMA usa-99 como ausencia. En la auditoría se convirtió en NaN, no en medición.
El tesista autorizó comparar relleno0 y99; finalmente los ejemplos incompletos
usan0 idéntico en original y alterado. No introducir máscaras como entrada.
La disponibilidad puede guardarse afuera para auditoría y elegibilidad. No afirmar
que PCA identifica por sí mismo el faltante: una medición real0/99 queda
indistinguible del mismo valor usado para rellenar.

Convención horaria HEREDADA del lector: HORA1→00:00, HORA24→23:00. Su
interpretación contra SIMAT figura como supuesto pendiente en src/ingest/rama.py;
no presentarla como validación nueva. Las tablas anotadas preservan HORA original.

No hay hora completa en las32 estaciones históricas simultáneamente2020–2022.
Sí hay días individuales completos. SAC:204 en2020,224 en2021,220 en2022.
El piloto CNN usa exclusivamente días completos; no demuestra desempeño con huecos.

## 4. Cómo se generan las imágenes activas

TINTOlib1.3.1, PCA, semilla42, blur=False, zoom1, salida numérica. **Mapa nativo**,
sin asignación única propia en esta nueva línea. Escalado MinMax por columna,
ajustado solo con2020–2021, sin recortar valores fuera de[0,1]. Etiqueta ficticia
constante requerida por API excluida de PCA; nunca una etiqueta de ataque de entrada.

Estación-día:24 columnas h00..h23. Un mapa compartido entre31 objetivos
(históricos sinHGM/XAL), una imagen32×32 por estación y día. No se pasa nombre,
fecha, hora seno/coseno, coordenadas, vecinas ni perfiles como características.
La posición de columna conserva implícitamente la identidad de la hora.
Mapa: `representacion1/completos_32_mapa.csv`; escala:
`representacion1/completos_escala.csv` dentro de la raíz de resultados raw.

PCA produce coordenadas y TINTO las rasteriza. Ejes de imagen=columna/fila de
píxel, NO estación/hora ni mapa geográfico. El mapa queda fijo entre días y
estaciones. El color cambia según medición; mismo color entre distintas horas no
necesariamente equivale a los mismosppb porque el escalado es porcolumna.
Los números y textos de las figuras son anotaciones humanas: CNN recibe float32,
no PNG con etiquetas/colores. Los 24 valores se conservan sin colisión en este mapa.

## 5. Experimentos raw ejecutados

### Representación y relleno, dos ejecuciones idénticas

| Entrada | Lado | Posiciones distintas/24 | Cambios individuales+1ppb ocultos |
|---|---:|---:|---:|
| Días completos |32|24|0|
| Días completos |64|23|1|
| Relleno0 |32|24|0|
| Relleno0 |64|24|0|
| Relleno99 |32|20|4|
| Relleno99 |64|23|1|

TINTO sinblur usa última escritura en las colisiones, comprobado con transform.
Mayor resolución no garantiza reducción monótona por redondeo. Control completo
ajusta12146 días; rellenos22661. Cambian muestra y escala, no se atribuye todo al
valor de relleno. No se eligió imputación por desempeño de un detector.
Informe: `informe_representacion.md`.

### Episodio pareado en ppb e imágenes

Primera semana de enero2022 enSAC; ataque+50% días3–5 sobre valores observados.
Se intentó primero la regla de siete días completos consecutivos; no había caso
SAC2022 y se registró alternativa primera semana con0 antes de visualizar.
Tres faltantes: 69 mediciones modificadas y69 cambios de píxel, cero cambios
perdidos, error inverso máximo≈1.42e-14ppb. Fuera del episodio imágenes idénticas.
No se reajustó mapa/escala. Dos ejecuciones idénticas. La diferencia usa original
conocido: diagnóstico controlado, no información disponible al detector real.
Informe: `informe_episodio.md`.

![Semana SAC: original, alterado, diferencia](../results/tinto_raw_20261109/episodio_primera_semana1/secuencia.png)

![Curva en ppb y leyenda de horas](../results/tinto_raw_20261109/episodio_primera_semana1/curva_y_mapa.png)

Comparación individual del03enero:21 observaciones y3 valores-99 originales
(HORA1,2,3), rellenados0. No confundirlos con ceros reales. Se generaron también
CCA yPED, fecha prefijada, ataque+50% independiente en cada ejemplo, mismo mapa.
`horas_estaciones/` contiene PNG anotados y CSV hora/píxel/ppb.

![SAC original y ataque con horas](../results/tinto_raw_20261109/horas_estaciones/SAC_horas.png)

### Red-día y pérdida de información

32 estaciones incluyendoHGM, excluyendoXAL, ×24h=768 columnas. Mapas y escalas
propios ajustados con731 días2020–2021, relleno0. Ejemplo03enero2022: soloSAC+50%.

| Lado | Posiciones únicas/768 | Sobrescritas | Cambios SAC visibles/21 |
|---|---:|---:|---:|
|32|240|528|4|
|64|475|293|16|

Cinco cambios desaparecen incluso del tensor64, no solo visualmente. Dos corridas
finales idénticas en `red_dia_final1/2`; `red_dia1/2` son intentos con fallo al
serializar int64 en JSON, no nuevos resultados científicos. No usarlos para seguir.
Mayor resolución y asignación única son alternativas propuestas, NO ejecutadas
para resolver este nuevo mapa. Prioridad elegida por usuario: estación-día.

![Red-día](../results/tinto_raw_20261109/red_dia_final1/comparacion_64.png)

## 6. Piloto CNN supervisado ya ejecutado

Registro previo en protocolo.md. CPU; CNN compartida34081parámetros:
Conv8(3,same,relu)→Pool2→Conv16→Pool2→Flatten→Dense32relu→Dropout.2→sigmoide.
Adam.001, BCE, batch64, cinco épocas fijas, modelo final época5. Semilla42 justo
antes de construir y de fit, determinismo. No selección por métricas ni continuación
para mejorar resultado. Imágenes generadas desde mapa congelado, sin fitTINTO nuevo.

-1024 bases completas2020–2021, muestreadas sin reemplazo: original+alterada=2048 imágenes.
-256 bases completas2022: original+alterada=512 imágenes.
-Signo sorteado porbase: x*1.5 o x/1.5; etiqueta externa0/1;50%positivos.
-Duración1día permitida; NO calendarios L0, NO prevalencia operativa.
-Bases originales/copia permanecen en misma partición; años separados.

| Medida | Resultado |
|---|---:|
|Entrenamiento5épocasCPU|2.19–2.29s, sin importar TensorFlow|
|Inferencia512imágenes|≈0.07s|
|Tensores de imágenes|10MiB|
|RSS proceso completo|≈940–945MiB, incluido runtime|
|Pérdida validación época1→5|0.6916→0.6498|
|Umbral de clasificación|0.5 fijo, **no percentil**|
|TP/FP/FN/TN|84/41/172/215|
|Recall|0.328125|
|Precisión|0.672|
|F1|0.440945|
|ROC-AUC|0.674225|
|Average precision|0.691942|

Control todo-positivo daF1=0.666667 por el balance50/50, por lo queF1piloto NO es
éxito. ROC-AUC constante0.5 y APprior0.5. La pérdida baja y hay separación parcial,
pero pierde172/256alteraciones al umbral fijo. No comparable con L0p99. No IC.
Dos corridas con pesos/historias/probabilidades exactas: `piloto_cnn1/2/`,
modelos `modelo_final.keras`, `pesos.npz`, manifiestos y probabilidades guardados.
Informe: `informe_piloto_cnn.md`; comprobación: `reproducibilidad_piloto_cnn.json`.

Conclusión limitada: número de imágenes manejable para este piloto, no evidencia
de recall suficiente. Conservación de información NO equivale a recall del modelo.

## 7. Cómo continuar desde otra PC

1. Clonar/actualizar `git@github.com:JoseLili/lorawan11-rama-detection.git`, rama main.
   Leer este documento, el protocolo raw y la fuente general
   `docs/protocolo_anomalias_red_v1.md` (revisiones posteriores a L0 incluidas).
2. Los resultados raw, mapas, tablas y modelos pequeños de este traspaso van enGit.
   No dependen de/tmp ni de una sesiónColab. Los ZIP originales están excluidos;
   copiarlos por separado para volver a auditar fuente. Los paquetes/cachés grandes
   históricos también están excluidos según.gitignore y deben regenerarse.
3. Crear entorno aislado; no sustituir dependencias de los modelos históricos.
   Versiones exactas observadas en `experiments/tinto_raw/entorno_piloto.txt`.
   TensorFlow/Keras son versiones preliminares; otro hardware/versión puede cambiar
   números. No asumir reproducibilidad bit a bit entre equipos. Verificar primero
   que se cargan artefactos; si no están disponibles las versiones, registrar entorno
   nuevo y ejecutar ambas réplicas antes de comparar. TINTOlib1.3.1 debe estar
   instalado en el entorno usado; los scripts no requieren la antigua ruta/tmp.
4. Desde la raíz del repo, con el Python del entorno activo, comandos:

```bash
# Repite ingesta SOLO si copiaste los tres ZIP raw originales:
python experiments/tinto_raw/auditar.py --salida results/tinto_raw_pc/auditoria1
# Estos leen la tabla auditada y mapas incluidos en results/tinto_raw_20261109:
python experiments/tinto_raw/representar.py --salida results/tinto_raw_pc/representacion1
python experiments/tinto_raw/red_dia.py --salida results/tinto_raw_pc/red_dia1
python experiments/tinto_raw/episodio_visual.py --salida results/tinto_raw_pc/episodio1
python experiments/tinto_raw/piloto_cnn.py --salida results/tinto_raw_pc/piloto1
python experiments/tinto_raw/piloto_cnn.py --salida results/tinto_raw_pc/piloto2
```

Las rutas fuente congeladas están explícitas en los scripts; cambiar salida no
cambia el mapa de entrada. Usar carpetas nuevas para no sobrescribir evidencias.
`horas_estaciones.py` y `comparacion_par.py` regeneran figuras en sus rutas fijas;
no ejecutarlos inadvertidamente si se desea conservar los PNG versionados.

## 8. Siguiente experimento propuesto, todavía pendiente

Mantener estación-día supervisado. Ampliar con2020–2021 y calendarios históricosL0,
entrenamiento d50, validación exploratoria2022 con d100/d50/d20 y controles sin
inyección. Antes de programar/entrenar dejar cerrado:

1. Cohorte, mínimos de observación/día y relleno0. El piloto solo vio días completos;
   ampliar a incompletos es un cambio explícito. No máscara de ataque como entrada.
2. Etiqueta diaria y uso de episodios de planes L0. No copiar etiqueta de última
   hora de L0 si se predice todo el día. Mismo soporte al comparar detectores.
3. Muestra/calendarios y prevalencia, manifestados. No usar pares50/50 del piloto
   como sustituto silencioso del escenario operativo.
4. Máximo de épocas/paciencia/min_delta, selección por pérdida2022 y dos réplicas.
5. Calibración exploratoria con2022original, p99principal/p99.9secundario, regla
   estricta `score > umbral`; reutilizar función histórica, no percentil interpolado
   improvisado. Reportar FA observada, recall, precisión,F1 y controles sin inyección.
   Declara reutilización2022; aún no abrir2023–2026.
6. Presupuesto/CPU oGPU, entorno, respaldo por corrida. GPU previamente permitida
   por usuario paraTINTO, pero cambios de entorno no garantizan igualdad. Si se
   vuelve aColab, **CLI autenticado, nunca navegador**. No crear sesiones hasta
   tener concreto paquete/configuración; descargar y verificar antes de cerrar.

No está demostrado que conservar24píxeles garantice detección. No se ha elegido
nuevo modelo definitivo, umbral operativo o reemplazo deL0. No reanudarS1histórico
ni otros experimentos automáticamente. No modificar resultados V4/L0 aceptados.

## 9. Instrucción lista para pegar en otro chat

> Estamos continuando los experimentos TINTO de tesis. Lee docs/traspaso_tinto.md
> y experiments/tinto_raw/protocolo.md y verifica los artefactos incluidos antes
> de actuar. Línea vigente: O3 raw, imagen estación-día, CNN supervisada compartida.
> Piloto cinco épocas ya hecho; el entrenamiento ampliado con calendariosL0 está
> pendiente de concretar. Preserva resultados y no abras años de examen. Quiero
> continuar desde la sección8, sin depender del chat anterior.
