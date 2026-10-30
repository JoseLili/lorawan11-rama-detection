# Escenario principal proporcional de Barcelona

Registro previo a inyección y entrenamiento: 2026-10-29. El tesista aprueba
conservar los ataques RAMA como escenario principal sobre Barcelona y dejar
el sesgo aditivo como escenario complementario. No se borran ni se sustituyen
los planes aditivos ni sus registros históricos. Esta decisión precede a
cualquier puntaje de detección o entrenamiento de Barcelona.

## Reglas fijadas

- δ en {100%, 50%, 20%, 10%, 5%}. Signo positivo: x×(1+δ);
  negativo: x/(1+δ). No es x×(1−δ).
- Todas las 13 estaciones pueden recibir episodios. Probabilidad p uniforme
  entre 0.001 y 0.003 por calendario. Cada estación libre puede iniciar un
  episodio cada día con esa p. Duración entera uniforme 1–7 días; signo ±
  equiprobable, fijo durante el episodio. Inicio 00 UTC, fin 23 UTC del último
  día. Se permiten simultaneidad entre estaciones y episodios adyacentes,
  pero no superposición en la misma estación. Se recorta al final del periodo.
- El calendario se sortea sobre todos los días del periodo, sin consultar
  concentraciones, ventanas elegibles ni desempeño. Episodios sin datos o sin
  casos comunes se conservan y se informan; no se vuelven a sortear. Esto
  difiere del 30% de días elegibles de cuatro estaciones del sesgo aditivo.
- Los cinco δ reutilizan fechas, estaciones, duración y signo del mismo plan.
  L0, V4 y PARAAD comparten exactamente la serie alterada correspondiente.
- La inspección de las respuestas originales de 2014–2015 encontró 221,223
  lecturas O3, todas enteras (inventario de 14 candidatas). Como en RAMA,
  al aplicar se redondeará con `floor(x_alterado+0.5)`, aquí en **µg/m³**,
  sin convertir a ppb. No se introduce una marca decimal exclusiva de ataque.
- Se alteran sólo valores observados, incluso fuera de la máscara común si
  forman parte del contexto. Los días apartados por cambios de reloj permanecen
  sin dato utilizable. La evaluación conserva la máscara estación-día fijada.
- Etiqueta horaria supervisada: lectura efectivamente cambiada tras redondear;
  se informan lecturas programadas sin cambio, especialmente en δ pequeños.
  Etiqueta estación-día: pertenencia al episodio diario, como en RAMA; no se
  redefine la máscara común según δ. Los faltantes no son lecturas alteradas.

## Entrenamiento y separación

Un único L0 principal recién entrenado con δ=50%, evaluado con los cinco δ.
No se transportan pesos ni umbrales de RAMA y no se entrena un modelo por δ.
V4 y PARAAD se ajustan sobre datos sin inyecciones. Sólo L0 recibe etiquetas
de ataque, separadas de sus entradas.

Se conservan los usos independientes por etapa del diseño Barcelona:
20 calendarios de ajuste inicial 2014–2015, 10 de validación 2016 y 20 nuevos
de ajuste definitivo 2014–2016, tras seleccionar épocas. Prueba 2018:
10 calendarios; complementaria 2019: otros 10. El número de prueba reproduce
las diez corridas RAMA; los 125 planes pertenecen al complemento aditivo.
La calibración de 2017 permanece limpia. La selección de épocas usa sólo 2016.

Semillas: `[42,231,uso,calendario,canal,estacion]`, enteros sin `hash()`.
Usos 0–4: ajuste, validación, definitivo, prueba, complementaria. Canal 0:
p del calendario; canal 1: sorteos de estación, usando código EOI como entero.
Se pregeneran inicio/duración/signo por fecha para que quitar una estación
no cambie los episodios de las restantes.

## Complemento aditivo

Se conservan los 125 planes por año ya generados y sus cinco factores de
sensores/días/magnitudes como experimento adicional, sin mezclar sus métricas
con las proporcionales. Para estudiar transferencia del L0 principal a otro
tipo de ataque se usará el mismo L0 entrenado proporcionalmente a δ50, congelado.
Entrenar otro L0 especializado en sesgo sería una pregunta distinta y requeriría
registro adicional. Los planes aditivos de entrenamiento ya generados se
conservan como evidencia de la propuesta anterior y no se usarán para ajustar
el L0 principal actual.

## Artefactos

`experiments/barcelona/generar_planes_proporcionales.py` adapta el algoritmo de
`src/detect/anomalias_red.py` a los códigos/etapas Barcelona; no modifica RAMA.
Genera `results/barcelona_paraad/planes_proporcionales_v1/`: un CSV por
calendario, manifiesto, registro de reglas y hashes. No aplica inyecciones.
Los conteos de soporte no son métricas de detección. La generación duplicada
debe ser idéntica antes de aceptar los planes.
