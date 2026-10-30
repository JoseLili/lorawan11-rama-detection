# Registro previo: calibración Barcelona 2017

Fecha: 2026-10-29. El tesista solicita continuar después de completar y
verificar los tres entrenamientos. Se cargan modelos congelados de disco;
no se construyen modelos nuevos ni se ajustan pesos, épocas o arquitecturas.

La calibración usa exclusivamente 2017 limpio, con pasado limpio disponible
desde 2014 para perfiles y ventanas. Las escalas definitivas 2014–2016 y los
perfiles causales ya registrados se conservan. Se exporta un paquete separado
sin observaciones 2018–2019. Su fuente es un corte temporal explícito y
sus hashes quedan guardados antes de iniciar la inferencia.

Universo: la misma máscara común, 4,536 estación-días de 2017 para los tres
métodos, sin modificar exclusiones por modelo ni por puntaje obtenido.

Puntajes, siguiendo la construcción RAMA:

- L0: promedio diario de probabilidades de las horas válidas propias.
- V4: absoluto del promedio diario firmado de residuos (observado−base−corrección),
  dividido por el p95 horario absoluto de cada estación en 2017 limpio.
  Se conserva esta normalización por estación de la referencia RAMA
  (`entrenamiento_multianual.umbral_p95`, percentil lineal); es una escala
  de puntaje de calibración, no un parámetro de entrada o entrenamiento.
  Se estima una vez con 2017 y queda congelada para los dos años de prueba.
  Si algún p95 es cero/no finito, detener; no seleccionar una solución con test.
- PARAAD: MAE diario observado en unidades estandarizadas de cada estación.

Se usan las máscaras horarias propias ya verificadas; mínimo12 horas por
estación-día e intersección diaria común. Se repite toda la inferencia dos
veces en el mismo entorno CPU y se exige igualdad exacta de puntajes,
coeficientes V4 y umbrales. Se registran modelos cargados, versiones y hashes.

Umbral global por método para p99 y p99.9, mediante la misma función
`evaluacion_red.umbral_falsas_alarmas`, con alerta estricta puntaje>umbral.
Con N=4,536, los máximos empíricos son 45 y 4 alertas respectivamente si
no hay empates; la resolución es 1/4,536. Son falsas alarmas empíricas de
calibración, no garantías en años posteriores. No hay ataques ni TP/FN/F1
de detección en esta etapa.

Después se congelan los modelos, escalas, p95 V4, máscara y umbrales. No se
abre el examen durante la calibración ni se elige un umbral observando ataques.
