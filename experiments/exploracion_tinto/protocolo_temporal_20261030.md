# TINTO: bloques temporales y secuencias — protocolo metodológico v1

Fecha: 2026-10-30. Estado: registrado por solicitud del tesista; sin ejecución nueva.
Este registro autoriza documentar, no inicia entrenamiento ni sesiones remotas.
El manifiesto técnico de ejecución descrito al final debe completarse antes de entrenar.

## 1. Antecedente y alcance

T1 y T2 se conservan íntegros. T2 ya evaluó estación-día (ED), estación-hora
(EH) y red completa; ninguna variante cumplió su regla principal. Este estudio
es una nueva exploración solicitada después de conocer esos resultados, no una
reclasificación del cierre negativo de T2 ni un registro anterior a toda evidencia.
Referencias: `diseno_t2_granularidad.md`, `resultados_t2_granularidad.md`,
`../../docs/auditoria_uso_tintolib_20261030.md`.

Pregunta: ¿cómo cambia la detección al representar las mismas 24 horas mediante
una imagen, dos imágenes de 12 horas o 24 imágenes horarias, y al incorporar una
secuencia explícita? Ninguna alternativa se considera ganadora por intuición.
Se distingue viabilidad técnica, utilidad predictiva y costo computacional.

## 2. Datos y objetivo comunes

- Estación objetivo y cuatro vecinas geográficas; mismas 17 características de
  L0 por hora, incluidos disponibilidad, comparaciones a14 y seno/coseno horario.
  No se eliminan máscaras ni se agregan coordenadas en esta comparación.
- Ajuste 2020–2021, 20 calendarios d50; selección exploratoria 2022, calendarios
  01–10. Evaluación 2022 limpio y calendarios 01–10 d100/d50/d20. No abrir
  2023–2026. Perfiles causales y planes de alteración heredados, sin cambios.
- Unidad principal: estación-día, información 00:00–23:00 disponible al cierre
  del día. Etiqueta diaria heredada de `estacion_dia.etiquetas`, separada de X.
  La prueba principal es retrospectiva, no una alerta disponible a medianoche.
- Soporte de evaluación: los mismos 9 661 estación-días de T1/T2, fijados por su
  manifiesto, sin eliminar ejemplos según predicciones o fallos de un candidato.
  Si alguna variante no puede puntuarlos, registrar fallo de cobertura.
- El brazo por bloques usa etiquetas auxiliares: en cada bloque, al menos una
  lectura observada del objetivo realmente alterada según `etiquetas_por_hora`.
  Bloques sin observaciones del objetivo se excluyen de su pérdida y agregación.
  Documentar discrepancias entre etiqueta de episodio diaria y alteración real.
- Los ataques históricos duran días completos: esto limita lo que se puede
  concluir sobre localización de ataques breves. No introducir nuevos ataques
  después de ver resultados para favorecer una variante.

## 3. Matriz de experimentos comprometida

| ID | Representación por estación-día | Modelo y salida | Contraste principal |
|---|---|---|---|
| D24 | Una imagen con 24 × 17 = 408 valores | CNN, score diario | Referencia visual diaria ED de T2 |
| B12 | Dos imágenes, 00–11 y 12–23; 204 valores cada una | Misma CNN para ambos bloques, dos scores | Dividir el día sin recurrencia |
| S12 | Las mismas dos imágenes que B12, en orden | CNN compartida → dos vectores → LSTM → score diario | Secuencia de dos bloques |
| S1 | 24 imágenes, 17 valores cada una, en orden | CNN compartida → 24 vectores → LSTM → score diario | Secuencia horaria explícita |
| L0 | Ventanas temporales originales | LSTM congelada; agregación diaria original | Referencia histórica de utilidad |

B12 produce el score diario como media de scores de bloques ponderada por
cantidad de horas observadas del objetivo; pesos y cobertura se guardan.
Así un bloque sin datos no inventa un voto. B12 permite revisar cada mitad,
pero sus métricas por bloque son secundarias y no se mezclan con F1 diario.
S12 recibe vectores de características de la CNN, no solamente sus dos scores.
S1 y S12 se entrenan conjuntamente extremo a extremo con etiqueta diaria.
No se transfiere el mejor checkpoint de B12 a S12 en el contraste principal:
esa transferencia introduciría otro cambio. Se reutilizan código y mapas.

Todas las imágenes usan 32 × 32 × 1, float32, sin difuminado, TINTO-PCA con
asignación única propia, explícitamente distinguida de TINTO nativo. Hay
408/204/17 píxeles ocupados respectivamente. Mantener resolución facilita
compartir la familia CNN, pero cambia la densidad; se reporta como limitación.
Un mapa fijo por granularidad; B12 y S12 comparten exactamente mapa/escalador.
Las dos mitades usan el mismo mapa con posiciones relativas 0–11 y la hora
absoluta codificada por seno/coseno. S1 comparte mapa en las 24 horas.
PCA y escalador se ajustan solo con entrenamiento; nunca por imagen ni por día.
No se usan PNG coloreados como entrada ni etiquetas/máscaras de ataque en X.

L0 histórico tiene contexto previo al comienzo del día en sus ventanas; por ello
es una referencia operacional, no un control que aísle exactamente arquitectura.
También B12 frente a S12 cambia supervisión por bloque frente a diaria. Sus
diferencias no se atribuirán exclusivamente a la LSTM. D24/S12/S1 constituyen
el contraste diario de igual contenido, aunque cambian arquitectura y geometría.

## 4. Orden y qué alimenta la etapa siguiente

1. **Auditoría sin entrenamiento.** Inventariar datasets, checkpoints ED/L0,
   versiones y hashes. Construir manifiestos comunes y etiquetas. Reutilizar ED
   solo si se verifica compatibilidad; si no, documentar el motivo y registrar
   un control D24 compatible antes de ejecutar los candidatos.
2. **Representación.** Construir D24/B12/S1, recuperar todas sus características
   y verificar precisión, correspondencia temporal y ausencia de etiquetas en X.
   Esto entrega mapas, escaladores y ejemplos auditados a todos los modelos.
3. **B12.** Entrenar y evaluar las dos imágenes diarias con CNN compartida.
   Entrega un control sin recurrencia y medidas de costo; no determina si se
   permite ejecutar S12 o S1.
4. **S12.** Añadir secuencia explícita sobre exactamente los bloques auditados.
   Reutilizar infraestructura y estimación de recursos, sin seleccionar nuevos
   hiperparámetros por las métricas de B12.
5. **S1.** Ejecutar la secuencia horaria predefinida independientemente de que
   S12 gane o pierda. Comparar costo, cobertura y desempeño en el mismo soporte.
6. **Informe conjunto.** Publicar todos los brazos, fallos incluidos. Cualquier
   hipótesis surgida de ellos queda como siguiente protocolo, no parche del actual.

Solo un fallo técnico bloquea entrenamiento dependiente. Reparaciones requieren
bitácora y repetir las comprobaciones afectadas. Si recursos obligan a detener,
reportar estudio incompleto, nunca declarar vencedora la última variante ejecutada.

## 5. Comprobaciones previas de aceptación

- 50 y 51: pasar ambos valores por la cadena real de preparación manteniendo
  contexto causal fijo. Verificar diferencia en la característica objetivo y
  su píxel float32, registrar magnitud y error frente a float64. Incluir valores
  reales y cambios ±1 en el rango observado. No confundir resolución instrumental
  con precisión de almacenamiento ni exigir que el ojo distinga los colores.
- Recuperar exactamente cada característica float32 desde sus píxeles; comparar
  contra la matriz escalada canónica. Cero colisiones, NaN o infinitos. Sin clip
  silencioso; registrar valores fuera del rango de ajuste.
- Reconstruir las 24 horas desde los dos bloques sin duplicados ni pérdidas.
  Verificar metadatos de hora, estación y cuatro vecinas con hashes.
- Mostrar cambios de píxeles en pares limpios/alterados preseleccionados por una
  regla cronológica sin mirar scores. La diferencia es diagnóstico, no entrada.
- Verificar continuidad de timestamps 23→00 y seno/coseno. **Los modelos diarios
  reinician estado entre días:** ni S12 ni S1 observan la transición de un día al
  siguiente dentro de una muestra. La auditoría no prueba que hayan aprendido
  continuidad entre días. Ventanas deslizantes que crucen medianoche serían un
  estudio adicional con objetivo horario y controles propios.
- Repetir preparación y comprobar hashes; pruebas de flujo mínimas no se usan
  como resultados científicos ni para escoger arquitectura por F1.

## 6. Evaluación y decisiones

Principal: media de F1 diario con p99 en d100/d50/d20, todos los calendarios
agrupados como T1/T2. Umbral propio por detector sobre los mismos días limpios
2022, comparación estricta `score > umbral`. Secundarias: p99.9, precisión,
recall, falsas alarmas empíricas, cobertura, métricas por bloque B12, parámetros,
tiempo/memoria e inferencia por estación-día. Un percentil nominal no garantiza
idéntica tasa empírica ni en datos futuros.

Dos ejecuciones con determinismo habilitado, semilla 42 inmediatamente antes de construir
y entrenar. Verificar igualdad de historias, pesos y scores antes de aceptar.
Esto comprueba reproducibilidad, no variabilidad entre semillas. Bootstrap
pareado estación-mes, 2 000 remuestreos, semilla [42,29,3], diferencias contra
D24 y L0 y S12−B12/S1−S12. Intervalos descriptivos, no pruebas confirmatorias
tras selección múltiple ni estimación de incertidumbre de entrenamiento.

Éxito técnico: supera auditorías, entrena, puntúa todo el soporte y reproduce.
Utilidad exploratoria para proponer un protocolo independiente: media F1 p99
≥ L0 + 0.02 en ambas ejecuciones, sin cambiar este criterio a p99.9 después.
Se reportan diferencias aunque no cumplan ese margen; no se requiere superar
el margen para ejecutar la siguiente variante. Si varias lo cumplen, ordenar
por métrica principal y reportar también costo; empates exactos favorecen menor
tiempo de inferencia medido bajo condiciones iguales.

2022 ya fue utilizado repetidamente: resultados exploratorios, no examen nuevo.
Ni éxito técnico ni superioridad puntual garantizan generalización. El fallo de
una implementación tampoco demuestra que toda la familia TINTO sea inútil.

## 7. Manifiesto técnico pendiente antes de entrenamiento

Este documento registra preguntas, brazos, orden y decisiones; no es todavía
un runbook ejecutable. Antes de entrenar, anexar configuración versionada con:
arquitectura exacta CNN/embedding/LSTM y parámetros, optimizador/lote/pérdidas,
máximo de épocas/EarlyStopping, presupuesto por brazo y entorno CPU/GPU; reglas
exactas de muestreo de PCA/escalador y entrenamiento; hashes de particiones,
etiquetas, mapas y fuentes; tratamiento completo de faltantes; compatibilidad
del control ED. Fijarlos por requisitos técnicos antes de obtener scores nuevos,
sin barrido adaptativo. Autorización nueva del tesista (2026-10-30): puede usarse Colab con GPU para
acelerar esta línea separada de L0/V4. Registrar hardware/versiones y verificar
reproducibilidad; si no se consigue igualdad, declarar el fallo y registrar una
enmienda antes de aceptar resultados, sin atribuirlo a variación entre semillas.

Los informes finales distinguirán modelos cargados de disco, modelos nuevos,
comprobaciones realizadas y propuestas no ejecutadas. Figuras: una de conservación
numérica/temporal y una de resultados/costo, cada una con fuente, ejes y unidades.

## 8. Auditoría inicial completada (2026-10-30)

Ver `informe_precision_tiempo_20261030.md`. Dos ejecuciones locales idénticas;
sin entrenamiento. Conservación D24 y particiones temporales superadas; mapas
B12/S1 y manifiesto de entrenamiento siguen pendientes. GPU autorizada para
esta línea por nueva instrucción del tesista; no modifica protocolos L0/V4.

## 9. Paso 1 cerrado y configuración previa del paso 2 (2026-10-30)

El tesista solicita cerrar el paso 1 y continuar. Se marca COMPLETADO con el
alcance del informe: conservación numérica y temporal, no aprendizaje del reloj.
Antes de calcular mapas nuevos se fija: TINTOlib 1.3.1 real, PCA, semilla 42,
MinMax sin recorte, 32×32, asignación única por mínima distancia cuadrática.
Fuente de ajuste: las 19 840 ventanas auditadas de 2020–2021 ya disponibles.
B12 agrupa sus dos mitades en 39 680 bloques; S1 agrupa sus 476 160 horas.
Estos son bloques de ventanas móviles de entrenamiento, no necesariamente
alineados a medianoche; se emplean para ajustar una transformación común a
cualquier hora. Los ejemplos diarios de inspección sí se parten 00–11/12–23.
MinMax se ajusta sobre todos esos bloques/horas de entrenamiento; PCA sobre
20 000 filas elegidas sin reemplazo con default_rng(42), índices ordenados.
Se guardan índices de origen; las etiquetas no participan. B12 y S12 compartirán
los mismos artefactos. Se conserva D24 congelado, sin reajustarlo.
Se verifica recuperación float32 de todos los bloques/horas de la muestra de
entrenamiento y del ejemplo limpio/alterado previamente seleccionado (SAC,
2022-01-16). Cambios artificiales de una columna deben afectar solo su píxel.
Dos ejecuciones idénticas requeridas. No CNN/LSTM, predicciones ni métricas.
La normalización previa heredada de L0 se conserva con sus límites históricos;
solo los nuevos MinMax/PCA aquí ajustados excluyen 2022.

## 10. Cierre del paso 2 (2026-10-30)

Representaciones B12/S12 y S1 construidas y auditadas, dos ejecuciones idénticas.
Ver `informe_mapas_temporales_20261030.md`. Paso 1 y construcción/auditoría del
paso 2 COMPLETADOS; todavía no hay entrenamiento ni evaluación predictiva.
La preparación de etiquetas, cobertura y configuración exacta del detector
permanece como requisito previo de la siguiente etapa, no se declara realizada.

## 11. Paso 3 B12: configuración congelada antes de entrenar (2026-10-30)

Paso 2 LISTO: mapas propios con 204/17 posiciones únicas; 8 094 720 valores
recuperados por variante, 19 archivos idénticos en dos procesos. Resultados y
figura en `informe_mapas_temporales_20261030.md`.

Se ejecuta B12, no S12/S1 todavía. CNN compartida: Conv2D 8 filtros 3×3 same
ReLU, MaxPool2, Conv2D 16 filtros 3×3 same ReLU, MaxPool2, Flatten, Dense32
ReLU, Dropout0.2, Dense1 sigmoide (34 081 parámetros). Adam0.001, BCE, lote64,
máximo60 épocas, paciencia8 sobre val_loss, min_delta0, checkpoint mejor.
Dos corridas deterministas semilla42; sin transferir pesos ED/T1. Presupuesto
máximo6 horas por proceso; excederlo es ejecución incompleta, no selección nueva.
GPU Colab autorizada, registrar versiones y dispositivo. Prueba técnica previa
3000 ejemplos por partición, 2 épocas, sin usar sus métricas para elegir ajustes.

Preparación reutiliza F/observaciones/etiquetas horarias del paquete T2 y verifica
estas últimas contra las matrices fuente d50. Bloques fijos 00–11 y12–23, todos
los días completos 2020–2021 (20 calendarios) y2022 (10). Para entrenar/validar
solo días con >=12 observaciones objetivo y bloques con al menos una; etiqueta
positiva si existe lectura observada realmente alterada dentro del bloque.
Sin balanceo, sobremuestreo ni retirada de características. Media diaria ponderada
por horas observadas de cada bloque; evaluación exige cobertura diaria>=12.
Solo el conjunto común predefinido se utiliza para métricas. Puntajes por bloque
se guardan para diagnóstico. El escalado se calcula float64 y convierte después
a float32 como en la auditoría, no se aproxima con constantes float32.
No se añade mapa limpio, autoencoder ni cambio de umbral al presente brazo.

## 12. Reintento B12 autorizado (2026-10-30)

Tras pérdida de acceso a la sesión sin artefactos recuperados, el tesista pide
retomar. Se repiten pruebas y ambas corridas desde cero con idéntica configuración
científica, sin seleccionar según la época5 observada. Se preserva intento previo.
Sesión nueva tinto-b12-r1-20261030; resultados en b12_20261030/reintento1.
Cambio operativo: empaquetar al terminar cada corrida y descargar localmente
con verificación SHA256, además del paquete final. Los respaldos locales
requieren que esta PC permanezca encendida y conectada; no son persistencia
externa automática si se apaga. No se altera L0/V4 ni se inicia S12/S1.

## Cierre B12 (2026-10-30, hora local)

Paso3 COMPLETADO: reintento íntegro descargado, pesos/historias/scores iguales;
evaluación repetida idéntica. Media F1 p99 B12=0.3096, ED=0.3224, L0=0.3550;
no pasa margen+0.02. VM liberada tras verificar archivos. S12/S1 pendientes,
no iniciados. Ver `resultados_b12_20261030.md`.

## 13. S12: configuración previa (2026-10-31)

El tesista autoriza ejecutar el siguiente brazo. Imágenes y escalador B12
congelados, en orden 00–11/12–23, etiqueta diaria de episodio como ED;
>=12 observaciones objetivo por día. Bloques sin dato se conservan con sus
máscaras, sin Masking de vector ni estado recurrente entre días.
Arquitectura fijada: TimeDistributed de la CNN B12 sin su sigmoide (Conv8,
pool2, Conv16, pool2, Flatten, Dense32ReLU, Dropout0.2), seguido LSTM32
(tanh/sigmoid, sin dropout recurrente, use_cudnn=False para ejecución explícita
reproducible), Dense1sigmoid. Entrenamiento conjunto desde cero, no pesos B12.
Adam0.001, BCE, lote64, máximo60épocas, paciencia8/min_delta0; dos corridas
con semilla42 antes de construir/entrenar y determinismo habilitado. GPU L4,
presupuesto6h por proceso, dos pruebas técnicas3000 ejemplos/2épocas antes.
Mismos datos2020–2021/selección2022, veinte/diez calendarios d50; mismo soporte,
31matrices de evaluación y criterios p99/p99.9 registrados. No buscar ajustes
según el F1 de B12. Evaluación compara con B12, ED y L0 históricos. Cambia
supervisión además de arquitectura: no atribuir causalmente todo a la LSTM.
Se cotejan etiquetas diarias contra planes y secuenciaTF contra NumPy, incluidos
orden y recuperación de las204 características por bloque. Se guardan imágenes
reales de ambas mitades para inspección, misma selecciónSAC2022-01-16 previa,
sin elegir casos por score. Respaldo por corrida y final, verificado antes de
liberar VM. No se inicia S1 dentro del supervisorS12.

## Cierre S12 (2026-10-31)

Paso4 COMPLETADO: dos corridas16épocas/mejor8, pesos/historias/scores iguales;
evaluación repetida idéntica. MediaF1p99 S12=0.3299, B12=0.3096, ED=0.3224,
L0=0.3550. Mejora descriptiva frente B12/ED, no pasa reglaL0+0.02. Resultados
asegurados y sesión liberada. S1 pendiente, no iniciado. Informe:
`resultados_s12_20261031.md`.

## 14. S1: configuración previa (2026-10-31)

Autorizado por el tesista tras S12. Se conservan días/etiquetas/particiones y
arquitectura S12 (CNN8/16, Dense32, Dropout0.2, LSTM32 use_cudnn=False,
sigmoide), cambiando entrada a24 imágenes32×32×1,17 características porhora.
Mapa/escaladorS1 ya auditados en paso2, sin nuevo ajuste. Secuencia00…23,
máscaras de disponibilidad conservadas, sin estado entre días. Mismos Adam/BCE,
lote64,60épocas máximas/paciencia8, semilla42 y dos corridas deterministas desde
cero. Pruebas3000ejemplos/2épocas repetidas, presupuesto6h por proceso. Para
memoria, lotes validación/inferencia128; no cambian ejemplos ni objetivo.
Se coteja conversión TF/NumPy y orden de las24 imágenes contra fuentes. Se
conserva ejemploSAC2022-01-16 con figura horaria, sin selección por score.
Evaluación2022 contraS12/B12/ED/L0, soporte9661días y criterios existentes;
no se abre examen ni se modifica la regla según resultados previos. GPU L4 y
respaldos por corrida/final antes de liberar sesión. No iniciar otros brazos.
