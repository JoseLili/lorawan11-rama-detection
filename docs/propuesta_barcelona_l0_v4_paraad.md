# Propuesta complementaria: L0 y V4 en el escenario de PARAAD

2026-10-28. Propuesta preparada ante la pregunta del tesista, posterior al
examen RAMA de revisión 20. No se inició entrenamiento ni se asignó número de
revisión; la 21 sigue reservada al error fijo en ppb. Se preservan los resultados
RAMA y sus modelos congelados.

## Pregunta

¿Se mantiene el comportamiento relativo de los métodos al cambiar RAMA y sus
alteraciones proporcionales por Barcelona y las anomalías del artículo?
Es una validación complementaria de transferencia de los métodos, no una
segunda oportunidad para seleccionar PARAAD mirando el examen RAMA.

## Métodos y significado de la transferencia

- Entrenar nuevos modelos en Barcelona; no aplicar directamente los pesos
  RAMA ni su escala o sus umbrales. V4 tiene entradas dependientes del número
  de estaciones y requiere una adaptación de dimensiones.
- Comparación principal PARAAD–V4: ninguno recibe etiquetas de anomalías
  durante el ajuste. V4 sigue prediciendo el objetivo desde las otras estaciones
  y su contexto causal; PARAAD sigue reconstruyendo el bloque de la red.
- L0 conserva su arquitectura local con cuatro vecinas y modelo compartido;
  requiere coordenadas y señales de las ocho estaciones. Recibe ejemplos
  sintéticos sólo dentro de entrenamiento. Sus calendarios de entrenamiento
  y los de prueba son independientes. Declarar esa supervisión adicional.
- PARAAD debe ejecutarse de nuevo sobre los mismos datos; no comparar nuestros
  resultados nuevos exclusivamente contra los números impresos en el artículo.

## Qué igualar

Mismas estaciones, intervalos, particiones, bloques/días válidos, anomalías
inyectadas, etiquetas y métricas para todos. Las normalizaciones se ajustan
exclusivamente con entrenamiento. Los días de prueba con falta de predicción
causal de V4 se identifican antes de medir desempeño, con una máscara común.
La línea temporal debe conservarse aun si se descartan días al construir el
dataset; no concatenar días separados como si fueran horas contiguas.

Hay dos análisis distintos que deben quedar identificados:

1. **Fidelidad al artículo:** precisar estaciones, fechas, partición 90/10,
   preprocesamiento e inyección originales, y reproducir PARAAD hasta donde
   permitan las fuentes. La selección móvil del umbral usa etiquetas previas;
   cualquier implementación debe ser causal y compartir exactamente esa
   información entre métodos, sin usar la etiqueta del bloque actual.
2. **Comparación controlada:** partición cronológica registrada, validación y
   calibración separadas de la prueba y umbral fijado a la misma tasa de falsas
   alarmas para los tres métodos. Requiere reservar datos para calibración y
   por ello no es automáticamente la partición original 90/10 del artículo.

No mezclar los umbrales móviles del artículo para PARAAD con umbrales fijos
para V4/L0 y atribuir las diferencias exclusivamente al modelo.

## Anomalías

Primero sesgo aditivo positivo diario, con los porcentajes del artículo;
después deriva si el tiempo y la fidelidad del material lo permiten. Preservar
los calendarios y desplazamientos exactos para todos los detectores. Definir
antes los redondeos con ocho sensores (30% no es un número entero).

Resolver antes la discrepancia entre el artículo y el código público:
`biasAnomalies` emplea una normal truncada entre 0.2σ y 2σ. No sustituirla
por una normal absoluta suponiendo que son equivalentes. Documentar la
selección de sensores, bloques y las 125 repeticiones del trabajo original.
L0 puede entrenar con sesgos independientes en su periodo de ajuste; no usar
las anomalías de prueba ni elegir su intensidad con sus resultados.

## Información pendiente que impide afirmar una reproducción exacta

El artículo proporciona ocho estaciones metropolitanas, 2014–2019 y 24,192
observaciones horarias por sensor (1,008 bloques diarios), pero no los ocho
códigos EOI, sus fechas exactas y orden ni un ejecutor completo de preparación.
El catálogo público agregado que consultamos sólo identifica seis estaciones
del municipio Barcelona en ese periodo; no autoriza a elegir dos adicionales
por conveniencia. Área metropolitana y municipio no son equivalentes.

El repositorio público contiene las arquitecturas y funciones auxiliares,
sin el subconjunto procesado. Primero buscar los códigos/fechas en material
adicional o en una copia del dataset del tesista. Si no aparecen, una selección
propia debe registrarse como **experimento con datos de la misma fuente**, no
como reproducción exacta. Contactar a autores requeriría autorización expresa
para enviarles un mensaje; no se contactó a nadie.

Fuente de datos: catálogo `tasf-thgu` de la Generalitat, ya documentado en
`revision20_paraad_diseno.md` y en
`data/reference/paraad_catalogo_o3_2014_2019.json`. No hay descarga de las series
horarias de Barcelona ni entrenamiento nuevo en esta propuesta.

## Secuencia propuesta

1. Identificar el subconjunto y auditar fechas, horas, unidades, coordenadas,
   faltantes y continuidad. Evitar convertir µg/m³ a ppb sin justificar las
   condiciones de conversión; se puede trabajar en unidades originales y
   estandarizar los tres métodos de forma coherente.
2. Registrar particiones, información permitida para los umbrales, adaptación
   de dimensiones y regla de selección antes de entrenar.
3. Ejecutar PARAAD y V4, dos veces en CPU; L0 como referencia supervisada.
4. Evaluar los mismos sesgos y, de acordarse, derivas; presentar métricas
   estación-día, control limpio e intervalos pareados.
5. Interpretar conjuntamente las dos direcciones: método publicado en RAMA y
   métodos propios en Barcelona, sin atribuir el efecto sólo a la ciudad.
