# TINTO: esquemas de anomalías y mejoras progresivas

Decisión del tesista posterior al primer autoencoder. Aplica a futuros ejercicios;
no modifica protocolos registrados, modelos ni métricas de experimentos terminados.

## Dos esquemas

1. Proporcional: delta de 100%, 50%, 20% y 5%. Para aumentos,
   x_alterado = x * (1 + delta): factores 2, 1.5, 1.2 y 1.05.
2. Error aditivo positivo: x_alterado = x + b, con b de 5, 10, 20 y 40 ppb.

El tesista confirmó mantener aumentos y reducciones con la convención anterior:
aumento x*(1+delta), reducción x/(1+delta), NO x*(1-delta).
Delta identifica la intensidad del esquema multiplicativo, no el porcentaje
efectivo de disminución. Reportar fórmula y cambio efectivo para evitar ambigüedad.

| Delta | Factor de aumento | Factor de reducción | Disminución efectiva |
|---|---:|---:|---:|
| 100% | 2 | 1/2 | 50% |
| 50% | 1.5 | 1/1.5 | 33.3333% |
| 20% | 1.2 | 1/1.2 | 16.6667% |
| 5% | 1.05 | 1/1.05 | 4.7619% |

No introducir errores aditivos negativos: los desplazamientos solicitados son positivos.

Aplicar las alteraciones en ppb antes del escalado congelado, solo a mediciones
observadas. No modificar faltantes ni recortar valores escalados fuera de [0,1].
Conservar los originales y registrar familia, magnitud, fórmula, estación, fechas
y horas afectadas. La máscara de inyección es evidencia externa para evaluación,
no entrada al detector. Separar métricas por esquema, magnitud y signo; conservar
controles originales. Duración, soporte temporal y selección de episodios deben
quedar registrados por experimento; esta decisión no fija nuevos calendarios.

## Hipótesis y dirección de trabajo

Convención de informes solicitada por el tesista: acompañar cada percentil con
la tasa nominal, N originales evaluados, conteo teórico N*(1-p/100) y conteo
observado de alertas originales. Aclarar unidad estación-día, redondeo y que la
tasa futura no está garantizada. No sumar falsas alarmas repetidas entre escenarios
que comparten los mismos originales ni entre percentiles anidados.

Mantener imágenes estación-día como unidad. Introducir gradualmente ideas de los
detectores recientes/finales sin importar sus matrices ni características completas.

La falta de contexto es una hipótesis, no un resultado probado. El mapa auditado
conserva las 24 lecturas, pero la imagen aislada no informa explícitamente de días
anteriores ni de estaciones vecinas. Una lectura inusual respecto a ese contexto
puede resultar plausible para el modelo compartido. El cuello de botella del
autoencoder sí comprime la entrada; ausencia de colisiones TINTO no garantiza
conservación dentro del modelo ni detección.

También hay una hipótesis sobre el criterio de anomalía: en el primer ensayo las
reducciones tendieron a producir menor error de reconstrucción. El score MSE alto
no identifica necesariamente toda alteración. Añadir información o capacidad no
garantiza resolverlo.

Secuencia propuesta, aún no ejecutada:

1. Evaluar el modelo base congelado con los dos esquemas para obtener referencia
   común, incluyendo delta5 y desplazamientos aditivos.
2. Examinar reconstrucciones y errores por hora y estación, sin cambiar el score
   retrospectivamente para mejorar los ataques ya observados.
3. Probar contexto temporal mediante secuencias de imágenes estación-día previas;
   registrar objetivo de reconstrucción/predicción y evitar información futura.
4. Probar por separado contexto espacial con imágenes de estaciones vecinas;
   evitar rasterizar toda la red en un solo mapa con sobrescrituras.

Cambiar una idea por experimento, mantener soporte de evaluación comparable,
documentar diferencias de elegibilidad y reportar falsas alarmas y recall.
Toda comparación en 2022 permanece exploratoria. No abrir 2023–2026 por esta nota.
