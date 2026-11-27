import os
assert os.path.exists("tesis_overleaf/guia_redaccion.md")
doc = r"""# Tesis: estado de la redacción y guía para continuar

Este archivo sirve para retomar la redacción desde cualquier lugar: otra computadora, otro chat o con el tutor.
Se actualiza al cerrar cada sección. Última actualización: 2026-11-27.

- **Título:** Detección de anomalías en redes de monitoreo atmosférico mediante aprendizaje profundo
- **Dónde vive la tesis:** Overleaf (pdfLaTeX + Biber). Las fuentes de datos y de resultados están en el repo `JoseLili/lorawan11-rama-detection`.
- **Límite:** 80 páginas, por pedido del tutor.

---

## 1. Reglas fijas (no se discuten de nuevo)

1. **Preámbulo intocable.** El de `Tesis.tex` lo establecieron el PCIC y el tutor. No se cambian paquetes, opciones, estilo de bibliografía (`numeric`), hyperref ni la numeración. La única línea agregada es `\usepackage{colores-tesis}`, debajo de `\usetikzlibrary{positioning, arrows}`.
2. **Estructura de archivos.** `Tesis.tex` (principal) y `capitulos/01_…07_….tex`, que entran con `\include`. Las gráficas van en `figuras/<nombre>.tex`, una por archivo, y entran con `\input`. Completan el proyecto `colores-tesis.sty`, `Referencias.bib` y `UNAM_LOGO2.png`.
3. **Gráficas.** Se hacen en pgfplots y solo con los estilos de `colores-tesis.sty` (`det ensX`, `barra=paraad`, …), nunca con un color suelto. Los dos ejes llevan rótulo y cada número lleva unidad. Un comentario arriba de cada figura dice de qué CSV del repo y de qué filas salen sus números.
4. **Nombres.** En el texto se escriben «NERAD» y «PARAAD-SA», sin macros. Los objetivos no nombran detectores.
5. **En cada revisión se marca:**
   - [cursiva]: término en inglés, en `\textit{}` (*bit flipping*, *recall*, *payload*);
   - [abreviatura]: sigla nueva, que se escribe completa la primera vez y se agrega a la lista;
   - [cita]: dónde hace falta una referencia, con su clave o con el aviso de que falta buscarla.
6. **Forma de revisar.** Primero, si la sección está bien. Después, solo los errores reales, con el cambio exacto. Lo demás es opcional y se marca así.

## 2. Cómo trabajamos cada sección

1. Ficha de la sección: qué debe contestar, qué debe tener y el material del repo.
2. Borrador del tesista, aunque sea en viñetas.
3. Revisión marcada como **Error** (cambio exacto) o **Estilo** (opcional, con la regla explicada).
4. Párrafo modelo solo si hay bloqueo; el tesista lo reescribe con sus palabras.

## 3. Plan por fases

| Fase | Qué | Estado |
|---|---|---|
| 0 | Contrato: hipótesis, objetivo general, objetivos específicos y mapa | **Cerrada** (falta que el tutor valide los específicos) |
| 1 | Revisar las secciones 2.1–2.3 ya escritas | **Cerrada** (cambios aplicados) |
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
| Columnas | 33 estaciones, de ACO a XAL; SFE, COY y SJA quedan fuera de la lista de referencia | **Pendiente:** confirmar el motivo |
| Evaluadas | 31 objetivos: 28 principales y 3 de baja representatividad (TLI, INN, AJM), que se reportan aparte | Mínimo por etapa: 2 000 h y 6 meses con dato |
| Solo contexto | HGM (0 h en 2022) y XAL (canal inactivo) | No hay con qué validarlas |
| Faltantes | `-99` y horas ausentes cuentan como faltantes; no se interpolan; máscara «tiene dato»; solo se alteran horas con dato | No inventar mediciones |
| Vecina | Las 4 estaciones más cercanas por distancia haversine, con las coordenadas del catálogo del SIMAT; fijas | Definición del término |
| Unidad | La estación-día, válida si tiene ≥ 12 horas con dato | Pregunta del operador: «¿qué estación reviso hoy?» |

Fuentes en el repo: `docs/protocolo_anomalias_red_v1.md` (§3 y revisión 8) y `docs/protocolo_lstm_v4_multianual.md` (§3.1–3.2).

## 7. Pendientes abiertos

1. **Tesista:** redactar 5.1 (4–5 párrafos).
2. **Tesista:** motivo de la exclusión de SFE, COY y SJA.
3. **Tesista:** decidir si las siglas van sin cursiva (RAE, recomendado) o en cursiva (como en el borrador). Debe ser igual en toda la tesis.
4. **Tesista:** pasar las coordenadas de las estaciones del catálogo del SIMAT, para el mapa `figuras/mapa_estaciones.tex`.
5. **Abreviaturas por agregar:** NOM (Norma Oficial Mexicana), LPWAN, RAMA, SIMAT, ppb.
6. **Cita por armar:** datos de la RAMA/SIMAT (entrada del `.bib`).
7. **Tutor:** validar los 5 objetivos específicos y confirmar si las 80 páginas incluyen portada, índices y bibliografía.
8. **Repo:** verificar que el README siga al día con NERAD (al 2026-11-27 lo estaba).

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
"""
open("tesis_overleaf/guia_redaccion.md","w",encoding="utf-8").write(doc)
print(len(doc.split()))
