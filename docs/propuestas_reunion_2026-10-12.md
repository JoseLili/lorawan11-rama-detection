# Propuestas para discutir con el tutor y preparar la colaboración con UCLM

> **Nota 2026-10-12:** propuesta **no adoptada** en la junta de ese día. El asesor optó por la detección de sensores anómalos a nivel de red; ver [progreso, 2026-10-12](progreso.md#2026-10-12--junta-con-el-asesor-anomalías-a-nivel-de-red). Se conserva como historial. El protocolo vigente de la parte 2 es [`protocolo_anomalias_red_v1.md`](protocolo_anomalias_red_v1.md).

Preparado el 11 de octubre de 2026 para la reunión del día siguiente.
Documento de discusión: no modifica los objetivos acordados ni constituye un
compromiso de participación de UCLM. Las duraciones son estimaciones de trabajo.

## Decisión propuesta

Llevar **dos alternativas excluyentes como ampliación principal**. Priorizar la
propuesta 1 mediante un piloto de dos semanas y decidir su continuidad, como
máximo, al terminar la cuarta semana. Conservar la propuesta 2 como alternativa
de alcance. Escribir desde ahora los resultados de bit flipping.

| | Propuesta 1: consumo y detección | Propuesta 2: integridad y costo de protección |
|---|---|---|
| Pregunta | ¿Qué información permite detectar consumo anómalo antes de acumular un daño relevante y cuánto cuesta obtenerla? | ¿Qué costo tiene autenticar las mediciones y cómo cambia el resultado de la aplicación frente al detector existente? |
| Trabajo nuevo principal | Banco de pruebas, un ataque de energía, telemetría y evaluación de detección | Autenticación de aplicación, evaluación de rechazo/faltantes y costo de comunicación |
| Reutilización | Protocolo de daño y falsas alarmas; bit flipping como primer caso de tesis | Datos, ataques, predicciones y decisiones de la primera parte |
| Encaje potencial | Comunicaciones y energía de Orozco; IDS de los autores del artículo enviado | Sensores ambientales y LoRaWAN de Orozco; su sugerencia explícita de integridad extremo a extremo |
| Incertidumbre principal | Reproducción en el firmware, instrumentación y evidencia visible para el detector | Contribución adicional frente a mecanismos existentes y comportamiento ante datos rechazados |
| Recomendación | Primera opción para continuar el acuerdo de estudiar un segundo ataque | Opción de menor ampliación conceptual para cerrar la tesis |

No incluir como requisitos una puntuación universal, aprendizaje federado,
costos monetarios de contingencias ni un tercer ataque. La entrega de tesis no
dependerá de que un artículo sea aceptado.

## Fundamento del encaje con UCLM

La captura de Google Scholar muestra trabajo de Orozco en comunicaciones,
modelado, consumo y aprendizaje automático. Los títulos no bastan para atribuir
experiencia en un ataque específico ni para inferir qué proyecto quiere asumir.

- **BeeGOns!** incluye sensores de calidad del aire y una comparación de consumo
  de LoRaWAN y ZigBee; Orozco es coautor. Es una conexión directa con la aplicación
  ambiental y la evaluación energética. [Manuscrito institucional](https://oai.e-spacio.uned.es/server/api/core/bitstreams/9efd6d68-8fee-43c5-83f9-6576608ca476/content).
- **ODIF (2025)** reúne a Jaime Camacho Escoto, Javier Gómez y Orozco en un
  trabajo sobre descubrimiento de vecinos y selección del ciclo de actividad.
  Existe una colaboración previa pertinente. [Publicación](https://doi.org/10.1109/OJCOMS.2025.3620270),
  [registro de UNAM](https://web.siia.unam.mx/siia-publico/c/crear_pdf.php?id=154578).
- **PermGrad (2026)** confirma participación de Orozco en aprendizaje sobre
  datos tabulares e interpretabilidad. No justifica por sí mismo sustituir el
  LSTM de esta tesis. [Registro de UNED](https://e-spacio.uned.es/entities/publication/8a3f3c2d-862b-461e-8973-50a8d4e56a86/full).
- **García-Sáez y coautores** trabajan en IDS federados; su artículo de 2026
  aborda heterogeneidad de datos. Otros integrantes del equipo publican también
  detección no supervisada mediante eventos. Hay afinidad con evaluación de IDS,
  sin necesidad de comprometer una arquitectura federada.
  [Trabajo federado de 2026](https://www.sciencedirect.com/science/article/pii/S1389128626002173),
  [detección no supervisada](https://link.springer.com/article/10.1007/s11276-022-03219-y).
- Otro equipo de **UCLM** publicó un banco LoRaWAN Clase B con mediciones de
  sincronización y consumo. Demuestra experiencia experimental en la institución;
  no confirma disponibilidad de sus equipos ni participación en esta propuesta.
  [Artículo](https://www.sciencedirect.com/science/article/abs/pii/S138912862600280X).

La identidad del colega que escribió el correo sigue sin confirmarse. No se
atribuyen sus sugerencias a García-Sáez ni a otro autor concreto.

## Propuesta 1: detección de consumo anómalo con costo de telemetría medido

El [desarrollo detallado de esta propuesta](propuesta_consumo_deteccion_uclm.md)
incluye modelo de amenaza, banco de pruebas, piloto, métricas, objeciones y una
tabla para registrar las decisiones de la reunión con el Dr. Jaime.

**Título provisional del estudio:** Información y costo energético para detectar
ataques de consumo en LoRaWAN.

**Pregunta:** ¿Cómo cambia la energía adicional acumulada antes de una alerta
al incorporar telemetría del nodo a la información habitual del servidor, y
cuánto cuesta esa telemetría?

**Hipótesis de trabajo:** en el escenario elegido, algunas observaciones locales
del nodo podrían reducir el tiempo hasta detectar consumo anómalo con una carga
de falsas alarmas acotada. Debe medirse si su costo adicional es aceptable.
La hipótesis puede resultar falsa; no se presupone que un modelo complejo ayude.

### Experimento mínimo

1. Configurar un nodo Clase A, gateway y servidor propio. Registrar versiones de
   firmware y protocolo, región y configuración. El CubeCell no se dará por
   compatible con LoRaWAN 1.1 sin comprobarlo: la pila oficial documenta 1.0.2.
   [Repositorio de Heltec](https://github.com/HelTecAutomation/CubeCell-Arduino).
2. Pilotar **un ataque de prolongación de recepción**, en el entorno controlado
   previsto por el laboratorio. La viabilidad en el hardware disponible está
   pendiente. La referencia experimental usa mensajes no confirmados; no debe
   confundirse con supresión de ACK. [Mikhaylov et al., 2019](https://cc.oulu.fi/~kmikhayl/site-assets/pdfs/2019_conf_ARES19_preprint.pdf).
3. Medir consumo normal y bajo ataque con un instrumento externo. Esa medición
   establece la referencia experimental; no se entrega al detector salvo que
   se declare un escenario que realmente disponga de ella.
4. Comparar información habitual del servidor con información adicional del
   nodo, por ejemplo duración de recepción o conteos de paquetes rechazados,
   según lo que permita exponer el firmware. Medir su costo de adquisición y
   transmisión. Distinguir registros disponibles de variables deseadas.
5. Evaluar una regla sencilla y, si existe señal temporal útil, un detector
   secuencial. Un método del equipo UCLM puede sustituir a la segunda opción si
   aportan código y encaja con los datos. No añadir una colección de modelos.
6. Separar sesiones completas para ajuste, calibración y prueba. Incluir
   actividad legítima de recepción y variaciones benignas pertinentes. Evitar
   dividir aleatoriamente ventanas solapadas de la misma campaña.

### Resultados que deben entregarse

- Energía adicional por evento y por horizonte fijo, con repeticiones e
  incertidumbre. Comparar ataque y normalidad bajo la misma defensa.
- Tiempo hasta alerta y energía adicional acumulada hasta ese momento. Cuando
  no exista alerta, reportar el daño hasta el horizonte de observación y
  contabilizar explícitamente el caso sin detección.
- Falsas alarmas por nodo y día, además de la tasa por ventana.
- Costo de la telemetría en operación normal: energía, bytes y tiempo en el aire.
- Trazas sincronizadas y procedimiento reproducible, respetando las condiciones
  de publicación de datos y código que se acuerden.

No equiparar una alerta con ahorro de energía: el ahorro solo puede medirse si
se implementa una respuesta. La vida de batería sería una estimación secundaria
con un modelo explícito, incluyendo reposo y frecuencia real de transmisión.
Un aumento por evento no equivale al mismo aumento de consumo diario.

### Aporte candidato y límites

El ataque y la idea de observar paquetes inválidos tienen antecedentes. El aporte
que se debe verificar frente a la literatura es la **evaluación conjunta de daño
acumulado, falsas alarmas y costo de información**, bajo actividad legítima y
ataques intermitentes. Revisar especialmente
[la caracterización de ataques de energía publicada en IEEE Sensors Journal](https://doi.org/10.1109/JSEN.2024.3504259).

Si ataque e interferencia benigna producen las mismas observaciones, el estudio
podrá detectar consumo anómalo, pero no atribuir intención maliciosa a partir de
esas variables. Un banco con un nodo víctima tampoco permite afirmar validez
para todos los dispositivos ni escalabilidad de una red.

**Relación con la tesis:** segundo caso de un protocolo compartido: adversario,
observaciones, referencia sin ataque, consecuencia, detector, falsas alarmas e
incertidumbre. Los cambios de decisión y la energía conservan unidades propias.
El artículo conjunto puede centrarse en este segundo caso.

**Colaboración propuesta:** Orozco en modelado y evaluación de comunicaciones;
un colaborador de IDS en observaciones, detector y evaluación. La distribución
de trabajo debe acordarse; no se presume disponibilidad.

### Criterio de continuidad

Al terminar dos semanas, buscar una traza normal, una traza bajo ataque y una
lista de observaciones realmente disponibles. Como máximo en la cuarta semana,
decidir con el tutor si hay efecto repetible, acceso a medición y diferencia
investigable frente a antecedentes. Si falta alguno y no hay solución concreta,
cerrar el piloto y reconsiderar el alcance.

## Propuesta 2: protección de integridad y consecuencias sobre la aplicación

**Título provisional del estudio:** Costo y consecuencias de proteger mediciones
ambientales transportadas por LoRaWAN.

**Pregunta:** ¿Qué costo de comunicación y energía tiene verificar la integridad
en la aplicación, y cómo afecta a la disponibilidad de datos y a las decisiones
frente al detector estadístico existente?

### Experimento mínimo

1. Fijar un adversario con capacidad de alterar el contenido después de la
   verificación del NS, sin controlar el nodo, el AS o las claves de protección
   de aplicación. Precisar el componente comprometido. TLS no se supone roto.
2. Implementar una protección de aplicación con primitivas existentes, incluyendo
   gestión de claves y protección contra repetición apropiadas. No proponer un
   nuevo algoritmo criptográfico. La revisión de mecanismos previos es parte
   del diseño. [OSCORE como antecedente de seguridad extremo a extremo](https://datatracker.ietf.org/doc/html/rfc8613).
3. Comparar el sistema actual, la protección de integridad y su combinación con
   el detector cuando exista una razón definida para mantenerlo. Reutilizar los
   mensajes y predicciones guardados; fijar cómo se trata una lectura rechazada.
4. Medir bytes y tiempo en el aire para configuraciones relevantes, y energía
   si se dispone de instrumentación. US915 DR0 permite hasta 11 bytes de
   aplicación sin FOpts; el formato completo debe caber o declarar su costo
   adicional. [Parámetros regionales](https://read.uberflip.com/i/1540208-rp002-1-0-5-lorawan-regional-parameters/44).
5. Evaluar lecturas alteradas aceptadas, lecturas legítimas rechazadas, faltantes
   y decisiones afectadas. La pérdida de la única lectura que mostraba una
   excedencia requiere un tratamiento explícito; descartarla no restaura su valor.

### Aporte candidato y límites

La protección criptográfica de integridad es conocida. El aporte sería una
evaluación que conecte su costo real y sus efectos sobre la disponibilidad con
las consecuencias de aplicación ya caracterizadas. Si solo se muestra que una
etiqueta detecta modificaciones, el resultado adicional sería insuficiente.

La autenticación no impide que un sensor comprometido emita datos falsos ni
garantiza su exactitud física. La probabilidad de falsificación se fundamenta en
las propiedades y supuestos del mecanismo, no en observar cero éxitos en unas
pocas pruebas. No se traduce un cambio de banda en una contingencia oficial.

**Colaboración propuesta:** relacionar el estudio con la experiencia ambiental
de BeeGOns! y la sugerencia de integridad de Orozco; acordar una evaluación o
validación adicional con UCLM.

**Dependencia compartida:** esta alternativa también necesita instrumentación
si se promete energía medida. Si no se consigue, el alcance deberá acordar
explícitamente mediciones de comunicación y estimaciones energéticas, sin
presentarlas como consumo experimental.

## Calendario orientativo y decisiones para la reunión

| Periodo desde la elección | Entrega |
|---|---|
| Semanas 1–2 | Piloto y revisión de novedad del estudio elegido; comenzar redacción de la parte 1 |
| Semanas 3–4 | Decisión de continuidad, protocolo cerrado y propuesta de participación para UCLM |
| Meses 2–3 | Implementación acotada y campañas experimentales |
| Mes 4 | Evaluación final, incertidumbre y cierre de resultados esenciales |
| Mes 5 | Borrador completo de tesis y primer borrador del artículo |
| Meses 6–8 | Revisiones, trámites y margen para incidencias; sin depender de aceptación editorial |

En la reunión con el tutor conviene resolver:

1. ¿Se mantiene como preferencia un segundo ataque, con el piloto y plazo de
   decisión propuestos, o se prefiere cerrar sobre integridad?
2. ¿Quién facilita la medición de corriente y el acceso al firmware?
3. ¿Qué investigador de UCLM puede asumir una parte concreta del experimento?
4. ¿Qué resultados mínimos bastan para cerrar la tesis aunque la colaboración
   o la revisión editorial se retrasen?

## Texto breve para presentar al tutor

> Propongo conservar la primera parte y estudiar un solo ataque de consumo.
> La pregunta sería cuánta energía adicional se acumula antes de detectarlo y
> qué costo tiene la información necesaria para hacerlo. Encaja con el trabajo
> de Orozco en comunicaciones y energía y con la experiencia en IDS del equipo
> que nos compartió. Planteo un piloto de dos semanas y una decisión definitiva
> durante el primer mes. Como alternativa de menor ampliación conceptual,
> propongo evaluar integridad extremo a extremo y su efecto sobre las decisiones
> y los datos disponibles. La tesis y el artículo compartirían resultados, con
> un alcance de graduación independiente del proceso editorial.
