# Tesis: estado de la redacción y guía para continuar

Este archivo sirve para retomar la redacción desde cualquier lugar: otra computadora, otro chat o con el tutor.
Se actualiza al cerrar cada sección. Última actualización: 2026-11-27.

- **Título:** Detección de anomalías en redes de monitoreo atmosférico mediante aprendizaje profundo
- **Dónde vive la tesis:** Overleaf (pdfLaTeX + Biber) es la versión maestra. En el repo hay una copia en
  [`tesis_overleaf/`](../../tesis_overleaf/), que se actualiza al cerrar cada sección. Las fuentes de datos y
  de resultados están en este mismo repo (`JoseLili/lorawan11-rama-detection`).
- **Límite:** 80 páginas, por pedido del tutor.

---

## 1. Reglas fijas (no se discuten de nuevo)

1. **Preámbulo intocable.** El de `Tesis.tex` lo establecieron el PCIC y el tutor. No se cambian paquetes, opciones, estilo de bibliografía (`numeric`), hyperref ni la numeración. La única línea agregada es `\usepackage{colores-tesis}`, debajo de `\usetikzlibrary{positioning, arrows}`.
2. **Estructura de archivos.** `Tesis.tex` (principal) y `capitulos/01_…07_….tex`, que entran con `\include`. Las gráficas van en `figuras/<nombre>.tex`, una por archivo, y entran con `\input`. Completan el proyecto `colores-tesis.sty`, `Referencias.bib` y `UNAM_LOGO2.png`.
3. **Gráficas.** Se hacen en pgfplots y solo con los estilos de `colores-tesis.sty` (`det ensX`, `barra=paraad`, …), nunca con un color suelto. Los dos ejes llevan rótulo y cada número lleva unidad. Un comentario arriba de cada figura dice de qué CSV del repo y de qué filas salen sus números.
4. **Nombres.** En el texto se escriben «NERAD» y «PARAAD-SA», sin macros. Los objetivos no nombran detectores.
5. **En cada revisión se marca** (criterios en la §9):
   - [cursiva]: término en inglés, en `\textit{}` (*bit flipping*, *recall*, *payload*);
   - [abreviatura]: sigla nueva, que se escribe completa la primera vez y se agrega a la lista;
   - [cita]: dónde hace falta una referencia, con su clave o con el aviso de que falta buscarla.
6. **Forma de revisar.** Primero, si la sección está bien. Después, solo los errores reales, con el cambio exacto. Lo demás es opcional y se marca así.

## 2. Cómo trabajamos cada sección

1. Ficha de la sección: qué debe contestar, qué debe tener y el material del repo.
2. Borrador del tesista, aunque sea en viñetas.
3. Revisión marcada como **Error** (cambio exacto) o **Estilo** (opcional, con la regla explicada).
4. Párrafo modelo solo si hay bloqueo; el tesista lo reescribe con sus palabras.

La redacción es del tesista (véase «Uso de herramientas de IA» en el README); el asistente revisa, verifica cifras contra el repo y señala cursivas, siglas y citas.

## 3. Plan por fases

| Fase | Qué | Estado |
|---|---|---|
| 0 | Contrato: hipótesis, objetivo general, objetivos específicos y mapa | **Cerrada** (falta que el tutor valide los específicos) |
| 1 | Revisar las secciones 2.1–2.3 ya escritas | **Cerrada**; en la revisión del 2026-11-27 aparecieron correcciones pendientes (§7) |
| 2 | Cap. 5: NERAD, datos y método | **En curso: sección 5.1** |
| 3 | Cap. 4: Etapa 1, *bit flipping* | Pendiente |
| 4 | Cap. 6: resultados | Pendiente |
| 5 | Resto del cap. 2 y cap. 3 (trabajos relacionados) | Pendiente |
| 6 | Cap. 7, cap. 1 completo, Resumen y Abstract | Pendiente |
| 7 | Revisión global: páginas, términos, números y bibliografía | Pendiente |

Revisiones con el tutor: al cerrar la fase 0, después de los caps. 4 y 5, después del cap. 6 y al final.

### Presupuesto de páginas

| Capítulo | Págs. |
|---|---:|
| 1. Introducción | 7 |
| 2. Sustento teórico | 14 |
| 3. Trabajos relacionados | 6 |
| 4. Etapa 1: *bit flipping* | 9 |
| 5. NERAD: datos y método | 14 |
| 6. Resultados y discusión | 14 |
| 7. Conclusiones | 4 |
| Referencias y apéndices | 8 |
| **Total** | **76** |

## 4. Texto ya acordado (cap. 1)

**Hipótesis** (literal del coloquio, acordada con el tutor):
> Es posible detectar, con un alto grado de confiabilidad, anomalías en la información reportada en redes de sensores utilizando el historial reciente de cada estación y el de sus estaciones vecinas sin incurrir en un exceso de falsos positivos.

**Objetivo general** (literal del coloquio, acordado con el tutor):
> Diseñar un detector de anomalías basado en modelos de aprendizaje profundo que combine la historia temporal de cada estación con la de sus estaciones vecinas, con alta capacidad de detección y una tasa de falsas alarmas acotada, en una red de sensores de ozono.

**Objetivos específicos** (pegados; falta la validación del tutor):
1. Caracterizar el daño y la detectabilidad de los ataques de *bit flipping* en LoRaWAN 1.1 [`loraalliance2017lorawan11`] según la posición del bit modificado, a partir del cambio de banda de calidad del aire definido en la NOM-172-SEMARNAT-2023 [`nom172_semarnat_2024`].
2. Diseñar un detector de anomalías que combine la historia reciente de la estación evaluada con la de sus estaciones vecinas e incorpore un filtro que excluya a las estaciones vecinas sospechosas de estar alteradas.
3. Determinar cuánto aporta a la detección usar a las estaciones vecinas como referencia, frente a usar sólo la historia propia de la estación, con el mismo umbral de falsas alarmas.
4. Evaluar el detector propuesto frente a un detector del estado del arte, mediante el *recall* y los días de falsa alarma al año por estación, en un banco de pruebas y en un periodo de despliegue.
5. Identificar las condiciones en las que el detector propuesto pierde capacidad de detección, como la alteración simultánea de estaciones vecinas o un sesgo sostenido en el tiempo.

**Mapa objetivo → dónde se cumple → dónde se responde** (comentario sobre `\section{Objetivos}`):

| Objetivo | Se cumple en | Se responde en |
|---|---|---|
| Hipótesis | OE3 (con y sin vecinas) y OE4 | Cap. 7, respuesta a la hipótesis |
| OE1 *bit flipping* | Cap. 4 | Cap. 7 |
| OE2 Diseño | Cap. 5, Arquitectura | Cap. 7 |
| OE3 Aporte de las vecinas | Cap. 6, Elección del diseño (2022) | Cap. 7 |
| OE4 Estado del arte | Cap. 6, Una estación y Despliegue | Cap. 7 |
| OE5 Dónde falla | Cap. 6, Coordinado y Sesgo | Cap. 7 |

**Términos que se definen después:**
- Falsa alarma = falso positivo en una estación-día (cap. 2). La hipótesis dice «falsos positivos» y el objetivo dice «falsas alarmas»; el texto acordado no se cambia, se aclara con esta definición.
- *Recall* (cap. 2).
- Estación vecina: las 4 más cercanas (cap. 5).
- La hipótesis habla de «alto grado de confiabilidad». En el cap. 5 se dice cómo se mide (*recall* con umbral p99 y días de falsa alarma al año por estación), y se declara que ese criterio se fijó después de ver los resultados.

**Pendiente del resto del cap. 1:** las secciones Definición del problema, Metodología, Contribución y Descripción del contenido son del enfoque anterior y están marcadas con `% REVISAR`. Se reescriben en la fase 6.

## 5. Fase 1 cerrada: cambios aplicados a 2.1–2.3

- 2.1: se borró la oración que usaba LPWAN antes de definirla; se corrigió «Estas características las hacen»; IoT y LPWAN llevan su expansión en inglés y su cita.
  - **Discrepancia (revisión del 2026-11-27):** en `tesis_overleaf/capitulos/02_marco_teorico.tex`, LPWAN no tiene la expansión en inglés ni la cita `raza2017lpwan`. Véase §7.
- 2.1.1: se agregó la definición de «estación» («En una red de monitoreo atmosférico, cada punto de medición se denomina estación y puede alojar uno o varios sensores.»).
- Citas nuevas en el `.bib`, todas verificadas en CrossRef salvo Hyndman, que no tiene DOI:
  - `atzori2010iot` (IoT)
  - `raza2017lpwan` (LPWAN)
  - `akyildiz2002wsn` (redes de sensores)
  - `teh2020sensor` (fallas de medición)
  - `hyndman2021fpp3` (series temporales; OTexts)
  - `chandola2009anomaly` (definición de anomalía)

## 6. Sección en curso: 5.1 Datos de la RAMA (≈ 2 págs.)

**Debe contestar:** ¿de dónde vienen los datos?, ¿qué periodo y qué estaciones?, ¿qué se hizo con los faltantes?, ¿qué es una estación vecina? y ¿cuál es la unidad de análisis?

| Tema | Dato (del repo) | Por qué |
|---|---|---|
| Fuente | Ozono horario (ppb) de la RAMA, publicado por el SIMAT en archivos anuales | Red real con datos públicos |
| Periodo | Matriz horaria del 2020-01-01 al 2026-07-31; el despliegue (ago–sep 2026) usa los datos validados del SIMAT | Los periodos de cada etapa van en 5.3 |
| Columnas | 33 estaciones, de ACO a XAL: la lista de estaciones con ozono de la referencia de 2025 (`docs/protocolo_lstm_v4_multianual.md`, §3.1) | Ver el motivo de las exclusiones abajo |
| Exclusiones | COY y SJA: el catálogo del SIMAT dice «Finalizó operación en 2017» (`data/reference/cat_estacion_simat.csv`) y no tienen ningún dato en 2020–2026. SFE: deja de reportar en 2023 y no está en la referencia de 2025; incluirla sería otra variante de la matriz (`docs/progreso.md`, verificación del 2026-10-12) | Sin datos en el periodo, o fuera de la referencia |
| Evaluadas | 31 objetivos: 28 principales y 3 de baja representatividad (TLI, INN, AJM), que se reportan aparte | Mínimo por etapa: 2 000 h y 6 meses con dato |
| Solo contexto | HGM (sin datos en 2021–2022) y XAL (canal inactivo) | No hay con qué validarlas |
| Faltantes | `-99` y horas ausentes cuentan como faltantes; no se interpolan; máscara «tiene dato»; solo se alteran horas con dato | No inventar mediciones |
| Vecina | Las 4 estaciones más cercanas por distancia haversine, con las coordenadas del catálogo del SIMAT; fijas | Definición del término |
| Unidad | La estación-día, válida si tiene ≥ 12 horas con dato | Pregunta del operador: «¿qué estación reviso hoy?» |

Fuentes en el repo: `docs/protocolo_anomalias_red_v1.md` (§3 y revisión 8) y `docs/protocolo_lstm_v4_multianual.md` (§3.1–3.2).

**Nota sobre la verificación de SFE:** la matriz horaria (`data/processed/o3_2020_2026_ancho.parquet`) no está versionada, así que el año en que SFE deja de reportar se tomó de `docs/progreso.md` y no se volvió a calcular el 2026-11-27. Antes de escribir el año en la tesis, confirmarlo con la matriz o con los archivos anuales del SIMAT.

## 7. Pendientes abiertos

**Tesista**

1. Redactar 5.1 (4–5 párrafos).
2. Decidir si las siglas van en redonda (RAE, recomendado; véase §9) o en cursiva (como en el borrador). Debe ser igual en toda la tesis.
3. Correcciones de la fase 1 (revisión del 2026-11-27, `capitulos/02_marco_teorico.tex`):
   - Quitar el espacio antes de `~\cite` en 4 lugares («sensores ~\cite», «medición ~\cite», «entorno ~\cite», «causa ~\cite»): el espacio y la tilde juntos dejan un hueco doble.
   - LPWAN: falta la expansión en inglés (*Low-Power Wide-Area Network*) y la cita `raza2017lpwan`, que ya está en el `.bib` pero no se cita.
   - `akyildiz2002wsn` está al final de la definición de «estación», que el artículo no contiene (es una revisión de redes de sensores inalámbricas). La cita va en la primera oración de 2.1.1; la definición de «estación» es una convención de esta tesis y no lleva cita.
   - 2.2, último párrafo: la relación entre las mediciones de estaciones cercanas es la base de la hipótesis y no tiene cita. [cita: falta buscarla, p. ej. la primera ley de Tobler o un trabajo de control de calidad espacial como `lussana2010sct`, ya en `docs/referencias.bib`; se cita solo si se lee].
4. Figura `figuras/recall_banco_p99.tex` y su pie: *Recall* en cursiva, en el rótulo del eje y en el pie; «1\,777 estación-días» → «1\,777 estaciones-día» (en los compuestos de dos sustantivos solo se pluraliza el primero, como en «horas-hombre»). Las cifras sí coinciden con `results/linea_base/rev24/metricas_banco.csv` (verificado el 2026-11-27; tp + fn = 1 777).

**Tutor**

5. Validar los 5 objetivos específicos y confirmar si las 80 páginas incluyen portada, índices y bibliografía.

**Para fases posteriores (no urgentes)**

6. Abreviaturas por agregar: NOM (Norma Oficial Mexicana, ya está), LPWAN, RAMA, SIMAT, ppb, LSTM.
7. Lista de abreviaturas de `Tesis.tex`: *Plaintext* y *Ciphertext* no son abreviaturas (se quitan); las expansiones en inglés van en cursiva; orden alfabético; «AES CTR» → «AES-CTR». Fase 7.
8. Cita por armar: datos de la RAMA/SIMAT (entrada del `.bib`).
9. Al llegar a cada capítulo, pasar al `Referencias.bib` de la tesis las entradas que ya están en `docs/referencias.bib` (PARAAD, STC-RAAD, SCT, TITAN, GDN, Saito, Chicco, etc.), solo las que se hayan leído.
10. Portada y metadatos: la fecha dice «Junio, 2025», y `pdftitle`/`pdfauthor` tienen el texto de la plantilla. Como el preámbulo es intocable, preguntar al tutor antes de cambiar `\hypersetup`; la fecha de la portada está en el cuerpo y se actualiza al final.
11. Mapa `figuras/mapa_estaciones.tex`: las coordenadas (longitud, latitud, altitud) están en `data/reference/cat_estacion_simat.csv` (69 estaciones; el archivo está en Latin-1, no en UTF-8).

## 8. Reglas de redacción (resumen)

1. Un párrafo, una idea. La primera oración dice la idea.
2. Oraciones de 35 palabras como máximo.
3. Precisión sobre adorno: un número con su unidad, no «buen desempeño».
4. Cada número sale de un CSV del repo.
5. Cada afirmación ajena lleva cita, y se cita solo lo que se leyó.
6. Un término, un nombre: estación-día, falsa alarma, estación vecina, NERAD, PARAAD-SA.
7. Siglas completas la primera vez, y en la lista de abreviaturas.
8. Método y resultados en pasado; lo que sigue siendo cierto, en presente.
9. Toda figura o tabla se cita en el texto antes de aparecer, y el texto dice qué hay que ver en ella.
10. Cada objetivo del cap. 1 tiene su respuesta en el cap. 7.

### Orden de escritura

Fase 0 → 2.1–2.3 → cap. 5 → cap. 4 → cap. 6 → resto del cap. 2 → cap. 3 → cap. 7 → cap. 1 completo → Resumen.

## 9. Cursivas, siglas y citas: cuándo

Criterio: *Ortografía de la lengua española* (RAE y ASALE, 2010), §§ sobre extranjerismos y abreviaciones.

### 9.1 Cursiva (`\textit{}`)

| Va en cursiva | Ejemplos de la tesis |
|---|---|
| Palabra extranjera no adaptada al español, **cada vez** que aparece, no solo la primera | *bit flipping*, *recall*, *payload*, *gateway*, *end device*, *dataset* (mejor: «conjunto de datos») |
| La expansión en inglés de una sigla | (LPWAN, por sus siglas en inglés, *Low-Power Wide-Area Network*) |
| Latinismos no adaptados | *a priori*, *et al.* |
| Un término la primera vez que se define (opcional, pero igual en toda la tesis) | Se denomina *estación-día* a… |

| **No** va en cursiva | Ejemplos |
|---|---|
| Siglas, aunque vengan del inglés | IoT, LPWAN, MIC, AES, XOR, LSTM, RAMA, SIMAT |
| Nombres propios: protocolos, productos, programas, organismos, detectores | LoRa, LoRaWAN, CayenneLPP, Python, NERAD, PARAAD-SA |
| Palabras ya incluidas en el diccionario sin marca de extranjerismo | bit, byte, píxel |
| Símbolos y unidades | ppb, h, %, O₃ |

- Si existe un equivalente en español de uso común, se prefiere: «umbral» (no *threshold*), «conjunto de datos», «aprendizaje automático» (no *machine learning*), «ensamble».
- Los nombres de campos de la especificación (FRMPayload, FCnt, DevAddr) se escriben siempre igual; se propone `\texttt{}`. Nunca se anidan cursivas: `\textit{FRM\textit{payload}}` es un error que dejó un reemplazo automático en el cap. 1.

### 9.2 Siglas

1. La primera vez en el cuerpo: forma completa en español y, entre paréntesis, la sigla; si la sigla es del inglés, también la expansión en inglés en cursiva. Ejemplo: «redes de área amplia y bajo consumo (LPWAN, por sus siglas en inglés, *Low-Power Wide-Area Network*)».
2. Después, solo la sigla. No se vuelve a expandir, salvo en el Resumen y el Abstract, que se leen por separado.
3. No se usa una sigla antes de definirla (incluidos títulos de sección y pies de figura que aparezcan antes).
4. El plural de las siglas es invariable: «las LSTM», «los MIC»; nunca «LSTMs».
5. Cada sigla nueva se agrega a la lista de abreviaturas en el mismo momento.
6. Si una sigla aparece una o dos veces en toda la tesis, mejor no crearla y escribir el término completo.

### 9.3 Cuándo poner una cita

| Lleva cita | Ejemplo en la tesis |
|---|---|
| Definición tomada de la literatura | anomalía `chandola2009anomaly`; LSTM (Hochreiter y Schmidhuber, 1997, por agregar) |
| Dato, fecha o cifra ajena | «En 2009 se empezó a desarrollar LoRa» (cap. 1, sin cita) |
| Norma, especificación o fuente de datos | NOM-172, LoRaWAN 1.1, datos de la RAMA/SIMAT |
| Método, algoritmo o herramienta que se usa y no es propio | ensamble, bootstrap por bloques, PARAAD, TINTO |
| Afirmación sobre lo que hicieron o señalaron otros | «trabajos previos han señalado…» (cap. 1, sin cita) |
| Afirmación empírica no obvia sobre el fenómeno | ciclo diario y estacionalidad del ozono |

| **No** lleva cita | Qué se hace en su lugar |
|---|---|
| Resultados propios | Remitir a la figura, tabla o sección (`\ref`) |
| Decisiones propias de diseño | Justificarlas con un argumento o un resultado propio |
| Definiciones propias de la tesis | estación-día, estación vecina, daño |
| Conocimiento común para un lector de maestría | qué es un bit o una operación XOR |

Forma:
- La cita va junto a la afirmación que respalda, antes del punto: `… sensores~\cite{akyildiz2002wsn}.` Sin espacio antes de la tilde.
- Si respalda solo una parte del párrafo, va en esa oración, no al final del párrafo.
- Varias fuentes: `\cite{a,b}`.
- Se cita solo lo que se leyó. Si algo se conoce por una fuente secundaria, se cita la secundaria o se lee la original.
- En los borradores, una cita que falta se marca así: `[cita: falta buscarla]` o `[cita: clave]`.
