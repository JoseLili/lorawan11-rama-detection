# TINTO con O3 crudo — reinicio 2026-11-09

Autorizado por el tesista; solo ozono. Línea independiente de TINTO-L0.
Primera fase: auditoría de fuente y representación, sin entrenamiento de CNN.

## Contrato

Leer directamente 2020O3.xls, 2021O3.xls y 2022O3.xls dentro de los ZIP RAMA,
verificando los hashes del repositorio. Conservar mediciones en ppb. No usar
relativas, perfiles, comparaciones de vecinas, R3, máscaras, seno/coseno ni
coordenadas como entradas. Fecha, estación, procedencia y disponibilidad son
metadatos externos. -99 representa ausencia: se convierte en NaN, nunca cero.
No interpolar ni imputar en la auditoría. Conservar las estaciones originales
para inventario y reportar aparte las 32 de contexto históricas (sin XAL).

## Separación temporal

Ajuste inicial: 2020–2021; validación exploratoria: 2022. Ajuste definitivo futuro:
2020–2022; calibración futura: 2023; examen histórico: 2024 y complementarios
2025–2026. Esta fase abre únicamente 2020–2022. Los años de examen ya fueron
utilizados por otros experimentos y no constituyen un examen nuevo independiente.
Cualquier escala y mapa nuevos se ajustarán solo con 2020–2021 sin inyección.
2022 no se usa para decidir imputación o seleccionar estaciones por desempeño.

## Secuencia

1. Auditar cobertura y reconstrucción exacta de mediciones desde raw; repetir
   extracción y comparar hashes. Informar filas completas por red y días completos
   por estación antes de resolver faltantes para TINTO.
2. Registrar tablas de entrada: red-hora (estaciones como columnas), estación-día
   (24 mediciones como columnas) y red-día (estación × hora como columnas).
   Una medición estación-hora aislada es un escalar, no una estructura PCA útil.
   Comparar tamaños de imagen prefijados 32/64, sin cambiar a asignación única
   silenciosamente. Usar TINTO nativo y auditar colisiones y recuperación numérica.
   Fijar manejo de faltantes explícitamente antes de ajustar; datos completados no
   se denominarán crudos sin aclaración. No excluir estaciones mirando 2022.
3. Con mapa y escala congelados: original sin inyección, ejemplo alterado y
   diferencia. Ataque proporcional según protocolo común, solo valores observados;
   seleccionar ejemplo por regla temporal previa, nunca por apariencia/resultados.
   Escala visual compartida; medir cambios perdidos, no solo inspeccionar colores.
4. Solo después de validar representación, especificar detector, etiquetas,
   entrenamiento y métricas en una ampliación registrada. No asumir que entrenar
   con normales enseña clasificación binaria. No producir F1 de imágenes solas.

PCA organiza características; los ejes de píxel no son estación y hora.
La escala numérica necesaria para representación se documentará separada del raw.
La convención horaria heredada HORA 1→00:00 y 24→23:00 es una hipótesis del
lector histórico; conservar HORA original y advertirla al interpretar ciclos.

## Ampliación autorizada: relleno 0/99 (2026-11-09, antes de resultados)

Comparación estación-día compartida entre las 31 estaciones objetivo: 24 columnas
(h00..h23), solo O3. Control: días completos. Brazos: todas las filas rellenadas
con 0 o 99 ppb. Se preservan raw y disponibilidad fuera de la entrada. No se afirma
que PCA separe faltantes: cada hora puede ser observada en una fila y ausente en
otra, pero conserva un único píxel. Sin ataques durante ajuste. MinMax por columna
ajustado en cada brazo 2020–2021, mapa PCA nativo 32/64, blur=False, semilla42.
Primera fecha completa SAC de 2022 para comparación común y primera fecha SAC
con mezcla de observaciones/ausencias para visualizar relleno. Selección previa
por calendario, sin mirar mapas. Prueba +1 ppb en cada columna del ejemplo completo;
medir si cambia imagen. Comparación entre brazos descriptiva: también cambia la
muestra de ajuste al incluir días incompletos. Dos ejecuciones y hashes iguales.

## Episodio visual sobre ppb (2026-11-09, registrado antes de ejecutar)

Usar mapa y escala del control completo 32×32 ya auditado, sin reajuste.
Elegir la primera secuencia de siete días completos consecutivos de SAC en 2022;
si no existe, informar y no sustituir caso por apariencia. Alterar los días 3–5
con x*1.5 (+50 %), desde 00:00 a 23:00; signo positivo y duración tres días fijos
para demostración, no muestra aleatoria de desempeño. Días 1–2 y 6–7 controles.
Generar imágenes originales, alteradas y diferencia, curva horaria en ppb y
leyenda hora→píxel. Una imagen por estación-día, no mosaico como entrada.
No imputar en este ejemplo. Medir cambios efectivos, cambios visibles en tensor,
error de reconstrucción en ppb y valores fuera de [0,1] sin recorte. Escala visual
común que incluya todos los valores; diferencia con su propia escala explícita.
Repetir y comparar hashes. Sin entrenamiento, F1 ni selección por resultados.

Resultado de elegibilidad: SAC no tiene siete días completos consecutivos en 2022.
Antes de generar imágenes se registra alternativa: primera semana calendario de
2022, relleno0 autorizado solo para imágenes, mapa completo congelado sin refit.
Ataque días3–5 solo sobre observados; curva ppb mantiene NaN como huecos.
El relleno se compara idéntico en original y alterado. No se cambia de estación.

## Red-día raw (2026-11-09, antes de ejecutar)

32 estaciones históricas de contexto (incluye HGM, excluye XAL), 24 horas:
768 columnas estación-hora, orden hora y estación. Faltantes rellenados0 según
 autorización; disponibilidad solo en auditoría externa. MinMax por columna y
TINTO-PCA nativo ajustados con los 731 días originales 2020–2021. Semilla42,
sin difuminado, resoluciones prefijadas32/64; figura principal64, conservar ambas
sin seleccionar por resultado. Ejemplo fijo2022-01-03, ataque +50% solo SAC y
solo observados, como el ejemplo estación-día. Mismo mapa/escala entre versiones.
Auditar colisiones, sobrescrituras y cambios físicos que llegan a imagen. Repetir
pipeline dos veces; sin detector, F1 ni examen. No imponer ejes estación/tiempo.

## Piloto CNN estación-día limitado (2026-11-09, antes del entrenamiento)

Autorizado por el tesista. Prueba de viabilidad CPU, cinco épocas fijas, dos
corridas desde cero semilla42. No selección de arquitectura, época ni umbral.
Mapa nativo completo32 y MinMax de2020–2021 congelados. 31 objetivos, solo días
completos: seleccionar sin reemplazo1024 días-estación de2020–2021 y256 de2022
con RNG[42,1109,1] y[42,1109,2]. Cada base genera original negativo y copia
alterada positiva d50; signo +/- sorteado por base con las mismas RNG, x*1.5 o
x/1.5. Etiqueta externa, ninguna máscara/hora/estación como entrada. Un día es
el episodio de este piloto (duración permitida1 día); no se usan los20 calendarios
L0 ni prevalencia operativa: conjunto pareado50/50 para diagnóstico. No cruzar
bases entre años. El mapa se ajustó en más datos2020–2021 que la muestra CNN.

CNN compartida: Conv8(3,same,relu),MaxPool2,Conv16(3,same,relu),MaxPool2,
Flatten,Dense32relu,Dropout.2,Dense1sigmoid. Adam.001,BCE,batch64,5 épocas.
Llamar fijar_semilla42 inmediatamente antes de construir y antes de fit.
Guardar modelo final, historia, manifiestos, probabilidades y pesos. Validación
no cambia el entrenamiento; umbral fijo0.5, F1/precisión/recall/exactitud,
ROC-AUC/AP y controles siempre-positivo/clase prior. F1 no comparable con L0
ni p99 histórico. Sin calibración operativa ni examen2023–2026.

Medir preparación, entrenamiento e inferencia, tamaño de tensores float32 y RSS
máximo del proceso (incluye TensorFlow, no solo CNN). Dos corridas con igualdad
exacta de pesos/historias/predicciones para aceptar reproducibilidad; los tiempos
pueden variar. Si no aprende, conservar resultado sin aumentar épocas automáticamente.
