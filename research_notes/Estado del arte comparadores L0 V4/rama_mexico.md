# Control de calidad y detección de anomalías en RAMA/SIMAT (CDMX) y redes latinoamericanas análogas

Notas del 2026-10-31. Para cada fuente se indica cómo se verificó: **[texto leído]** si se extrajo y leyó el PDF o la página; **[resumen de búsqueda]** si solo se vio el fragmento o resumen del buscador, en cuyo caso los detalles hay que confirmarlos antes de citarlos en la tesis. No se inventó ninguna referencia; lo que no se encontró va en "Gaps".

---

## 1. ¿Cómo valida SIMAT/SEDEMA los datos de la RAMA? (manuales oficiales, NOM-156-SEMARNAT-2012, banderas, informes QA/QC)

### Takeaway
El marco obligatorio es la NOM-156-SEMARNAT-2012, que fija tres pasos de manejo de datos (limpieza con banderas, verificación, validación), prohíbe borrar datos crudos, pide estadística descriptiva para detectar "anomalías potenciales" y exige 75 % de compleción. Todo esto es un proceso basado en reglas y revisión humana, con niveles de validación 0-3 heredados de la US EPA. No es un detector estadístico ni de aprendizaje automático. El procedimiento interno del SIMAT (SA/ADDA/GG/01(00), 2004) está citado en la norma, pero no se encontró público.

### Cited Findings
- **NOM-156-SEMARNAT-2012**, "Establecimiento y operación de sistemas de monitoreo de la calidad del aire", DOF 16-jul-2012, en vigor desde el 16-jul-2013 **[texto leído, PDF de PLATIICA]** — [PDF PLATIICA](https://platiica.economia.gob.mx/wp-content/uploads/sites/2/PDF_Normas_Publicas/156semar2012.pdf); [ficha mley.mx](https://mley.mx/normas/nom-156-semarnat-2012/documentos/dof-5112145/); [DOF/SIDOF](https://sidof.segob.gob.mx/notas/docFuente/5259464)
  - Def. 4.1 "Bandera": código alfanumérico para identificar eventos extraordinarios ajenos a la medición y los datos confiables.
  - Def. 4.30 "Validación de datos": proceso para determinar la calidad analítica de un conjunto de datos según las necesidades del sistema y su plan de aseguramiento de calidad.
  - 10.1: el manejo de datos tiene tres pasos: limpieza, verificación y validación.
  - 10.2.1 (limpieza): definir y asignar banderas, sobre todo a datos *fuera del rango de operación*, e igualar a cero los negativos que estén dentro de la tolerancia.
  - 10.2.2: "no se borrará ningún dato". Los datos dudosos con bandera los verifica después el personal y sirven para revisar el funcionamiento de los equipos.
  - 10.3 (verificación): confirmar o cambiar las banderas usando (10.3.1) las bitácoras de operación, (10.3.2) estadística descriptiva y gráficas para ver la estructura, el patrón de los datos y las **"anomalías potenciales"**, y (10.3.3) las relaciones entre contaminantes y con la meteorología.
  - 10.4.1: análisis según precisión, sesgo, representatividad y compleción. 10.4.2: **compleción mínima de 75 %** para los indicadores de estado y tendencia.
  - 10.5.2: el monitoreo automático manda datos *crudos* en continuo a SINAICA y los *validados* cada seis meses como máximo.
  - 9.4 (control de calidad): visitas de inspección, verificaciones y ajustes, calibraciones, mantenimiento preventivo, bitácora por estación.
  - Bibliografía, ref. 12: "SMA/GDF. Adquisición y validación de datos de contaminantes atmosféricos y parámetros meteorológicos, Procedimiento SA/ADDA/GG/01(00), febrero 2004". Refs. 28-35: guías US EPA (QA Handbook vol. 1-5, 1998; EPA QA/G-8, 1999/2002; Data Quality Assessment QA/G-9).
- Un documento de SIMAT de 2005 (memoria 2001-2006) describe los subprocesos de adquisición, transmisión y validación, y menciona una "Plantilla de Validación" de la EPA para los contaminantes criterio **[resumen de búsqueda]** — [Informe anual calidad del aire y tendencias 2005](http://www.aire.cdmx.gob.mx/descargas/publicaciones/gestion-ambiental-aire-memoria-documental-2001-2006/descargas/informe_anual_calidad_aire_tendencias_2005.pdf)
- La información de RAMA y REDMET se concentra en el Centro de Información de la Calidad del Aire (CICA). Hacia 2000 se buscó integrar monitoreo, transmisión, validación y difusión en un sistema de gestión ISO 9001:2000 **[resumen de búsqueda]** — [Cédula de proyecto SMA, InfoCDMX 2009](https://infocdmx.org.mx/innovaciones/transparencia/2009/2009_15_SMA_CedulaProyecto.pdf)
- El flujo de datos del SIMAT va del datalogger de cada estación RAMA al CICA, con el software AirVision, y de ahí a la difusión horaria en aire.cdmx.gob.mx **[texto leído]** — [Rivera, O. (SEDEMA), presentación CEC, 26-sep-2019](https://www.cec.org/wp-content/uploads/2020/02/olivia_rivera.pdf)
- Funciones según el organigrama de SEDEMA: la Subdirección de Monitoreo supervisa la validación de datos de campo. La JUD de Análisis Estadístico calcula indicadores y métricas para validar los datos **[resumen de búsqueda]** — [SEDEMA estructura 192](https://www.sedema.cdmx.gob.mx/secretaria/estructura/192); [SEDEMA estructura 194](https://sedema.cdmx.gob.mx/secretaria/estructura/194)
- Niveles de validación 0-3 (Knoderer et al., 2003; US EPA) aplicados a SIMAT. Nivel 0: datos crudos sin editar. Nivel 1: revisión de procedimientos, bitácoras y funcionamiento de equipos. Nivel 2: consistencia interna con gráficas y estadística. Nivel 3: comparación con otras variables y otros sitios. La tesis propone pasar de nivel 1 a nivel 2 **[texto leído]** — [Hidalgo Navarro, M. (2011), tesis de maestría, UNAM](https://ru.dgb.unam.mx/bitstream/20.500.14330/TES01000667922/3/0667922_A1.pdf)
- SINAICA (INECC) publica por separado datos crudos, validados y manuales; el paquete `rsinaica` permite descargarlos **[resumen de búsqueda]** — [rsinaica, CRAN](https://cran.r-project.org/web/packages/rsinaica/refman/rsinaica.html)
- Los datos de RAMA están en el portal de datos abiertos de la CDMX (registros por fecha, hora y estación). La última actualización indicada en esa ficha es de junio de 2023 **[resumen de búsqueda]** — [Datos abiertos CDMX, RAMA](https://datos.cdmx.gob.mx/dataset/red-automatica-de-monitoreo-atmosferico)

### Inferences
- La validación oficial busca **fallas instrumentales** (fuera de rango, deriva de calibración, bitácoras) y se apoya en el juicio de un experto. Las "anomalías potenciales" de 10.3.2 se buscan con gráficas y estadística descriptiva, no con un detector que dé un umbral y tasas de error. El V4 y el L0 de la tesis serían una versión automática y cuantificada del paso 10.3 (verificación). En términos de la EPA, el L0 con vecinas se parece al nivel 3 (comparación con otros sitios).
- El escenario de la tesis (multiplicar o dividir por 1+d durante días completos) no es una falla de rango: con d de 5-20 % el dato sigue en rango y no lo marcaría la limpieza de 10.2.1. Este argumento ayuda a justificar la parte 2, aunque es una inferencia y no está documentado.
- Como los datos que usa la tesis (2020-2026) ya pasaron por la validación de SIMAT, el "limpio" de 2023 y 2024 es "limpio según SIMAT". Eso no garantiza que no haya anomalías reales que no se detectaron. Conviene decirlo en la tesis como limitación.

### Gaps
- No se encontró público el procedimiento interno SA/ADDA/GG/01(00) ni un manual de validación vigente del SIMAT. Tampoco se encontró la lista oficial de banderas o códigos de la RAMA, ni cómo aparecen en los archivos de datos (por ejemplo, el valor de faltante o inválido). Habría que pedirlos a SEDEMA por transparencia (PNT) o revisar la sección de descargas de aire.cdmx.gob.mx con un navegador.
- No se encontró un informe QA/QC publicado con auditorías por estación, ni el porcentaje de datos invalidados por estación y año.
- No se encontró un manual de INECC o SINAICA con criterios de validación cuantitativos para ozono.
- La NOM-156 solo se leyó en la versión de PLATIICA. No se cotejó con el DOF ni se revisó si hubo modificaciones posteriores.

---

## 2. Trabajos académicos sobre RAMA/SIMAT: valores atípicos o anomalías, imputación con vecinas, pronóstico ML con detección por residuo, inyección de anomalías sintéticas

### Takeaway
El antecedente directo más cercano es **Lomas-Barrie et al. (2022)**, de IIMAS-UNAM, que aplica detección de anomalías **no supervisada** (LOF, Isolation Forest, SVM de una clase y autoencoder) a datos SIMAT de 2011 a mayo de 2022, estación por estación. Ese trabajo no inyecta anomalías sintéticas, no usa vecinas y no reporta métricas de detección. No se encontró ningún trabajo sobre RAMA que inyecte anomalías sintéticas, que use el residuo de un pronosticador como detector o que use un detector supervisado con estaciones vecinas. Hay trabajos de imputación (BRITS contra Random Forest) y muchos de pronóstico de ozono con ML, pero ninguno los usa para detectar anomalías.

### Cited Findings
**Detección de anomalías en datos SIMAT (antecedente directo)**
- Lomas-Barrie, V.; Alcántara, T.; Mota, S.; Neme, A. (2022). "Unsupervised Learning Algorithms are Able to Identify Relevant Patterns in the Pollution Data in Mexico City". *Research in Computing Science* 151(10), pp. 29-44, ISSN 1870-4069 (CIC-IPN). Recibido el 13-jun-2022 y aceptado el 12-ago-2022 **[texto leído]** — [PDF RCS](https://rcs.cic.ipn.mx/2022_151_10/Unsupervised%20Learning%20Algorithms%20are%20Able%20to%20Identify%20Relevant%20Patterns%20in%20the%20Pollution%20Data.pdf)
  - Datos: SIMAT/RAMA públicos, de 2011 a mayo de 2022. Los autores describen el sistema como de "más de 20" estaciones y siete contaminantes.
  - Métodos (todos no supervisados): Local Outlier Factor, Isolation Forest, SVM y autoencoder.
  - Representación: analizan **cada estación por separado** para "no tomar en cuenta la dinámica espacial". Hay dos variantes: (a) ventana deslizante de k = 6 horas o días por contaminante, embebida en un espacio de 6 dimensiones; (b) un vector de 6 contaminantes por hora (CO, O3, NO, NO2, PM10, SO2). El ejemplo que muestran es la estación Tlalnepantla, con CO y O3.
  - No hay verdad de referencia, ni anomalías inyectadas, ni precision, recall o F1. Los autores interpretan las anomalías como cambios en la dinámica de la contaminación, no como fallas.

**Validación estadística en RAMA (tesis UNAM)**
- Hidalgo Navarro, M. (2011). *Metodología para la validación de datos de calidad del aire generados por una red de monitoreo automático*. Tesis de Maestría en Ingeniería Ambiental (Aire), UNAM. Tutor: M. en C. Vicente Fuentes Gea **[texto leído]** — [PDF, Repositorio DGB-UNAM](https://ru.dgb.unam.mx/bitstream/20.500.14330/TES01000667922/3/0667922_A1.pdf)
  - Usa ozono de una sola estación RAMA (Merced), de enero de 1996 a diciembre de 2005.
  - Método basado en reglas y estadística descriptiva: suficiencia de datos, histogramas, series de tiempo, correlograma (FAC), comportamiento horario y estacional de los máximos, dispersión, y pruebas de Kolmogorov-Smirnov y Shapiro-Wilk. El objetivo es dar a los datos la etiqueta de nivel 2 (EPA).
  - El tesista agradece al personal del SIMAT la información que le dieron.

**Imputación de faltantes en RAMA**
- Díaz-González et al. (2025). "Handling Missing Air Quality Data Using Bidirectional Recurrent Imputation for Time Series and Random Forest: A Case Study in Mexico City". *AI* (MDPI) 6(9), 208. DOI: 10.3390/ai6090208 **[resumen de búsqueda; MDPI devolvió 403, no se pudo leer]** — [DOI](https://doi.org/10.3390/ai6090208)
  - Según el resumen: compara BRITS (red recurrente bidireccional) con Random Forest en estaciones seleccionadas de la red de la CDMX, con datos de 2014 a 2023 aproximadamente, y marca las variables con más de 30 % de faltantes. Dice que BRITS da imputaciones más realistas y que RF a veces genera valores extremos. No se pudo confirmar la lista de autores, las métricas ni cómo se simularon los faltantes.

**Pronóstico de ozono con ML en CDMX (posibles detectores por residuo, aunque ninguno se usó para detectar)**
- "Evaluation of Machine Learning Models for Ozone Concentration Forecasting in the Metropolitan Valley of Mexico". *Applied Sciences* (2024), 14(4), 1408. DOI: 10.3390/app14041408. Compara RF, SVR y Gradient Boosting a 24 h con datos SIMAT **[resumen de búsqueda]** — [DOI](https://doi.org/10.3390/app14041408)
- "A machine learning approach to investigate the build-up of surface ozone in Mexico-City". *Journal of Cleaner Production* (2022). Usa datos horarios de mar-2015 a feb-2016 y SHAP **[resumen de búsqueda]** — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S095965262204210X)
- "Operational ozone forecasting system in Mexico City: A machine learning framework integrating forecasted weather and historical ozone data". *Atmospheric Environment* (2024) **[resumen de búsqueda]** — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1352231024006927)
- "Machine-Learning Models for Surface Ozone Forecast in Mexico City". *Atmosphere* (2025) 16(8), 931. DOI: 10.3390/atmos16080931 **[resumen de búsqueda]** — [DOI](https://doi.org/10.3390/atmos16080931)
- "Proposal of a Modified Loss Function with the Gaussian Copula Density Function to Improve LSTM Predictions of PM10 and PM2.5 Concentrations". *Computers* (2026). DOI: 10.3390/computers15020091. LSTM para PM en las estaciones AJM, CAM, MER y PED **[resumen de búsqueda]** — [DOI](https://doi.org/10.3390/computers15020091)

**Contexto espacial (útil para justificar el uso de vecinas)**
- "Spatio-Temporal Representativeness of Air Quality Monitoring Stations in Mexico City: Implications for Public Health". *Frontiers in Public Health* (2020/2021). Analiza 2009-2018 y concluye que la cobertura es adecuada para la mayoría de los contaminantes, salvo el SO2 **[resumen de búsqueda]** — [PMC7874227](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7874227/); [Frontiers](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2020.536174/full)
- "Estimation of missing air pollutant data using a spatiotemporal convolutional autoencoder". *Neural Computing and Applications* (2022). DOI: 10.1007/s00521-022-07224-2. Imputa la estación objetivo con estaciones cercanas; reporta R² ≥ 0.6 aunque falte toda la serie objetivo, y peor desempeño cuando las vecinas están poco correlacionadas **[resumen de búsqueda; Springer redirige a login. No se confirmó que la red sea la CDMX]** — [Springer](https://link.springer.com/article/10.1007/s00521-022-07224-2)

### Inferences
- **Lugar de la tesis frente a Lomas-Barrie et al. (2022):** ellos y el V4 coinciden en ser no supervisados sobre RAMA. Hay tres diferencias que la tesis puede defender: (1) la evaluación cuantitativa con anomalías inyectadas y plan pareado, que da F1 y F2 con su valor sin ataque; (2) el uso explícito de información espacial (vecinas en el L0), que ellos descartan a propósito; (3) el umbral calibrado con falsas alarmas fijas en un año limpio aparte. Comparabilidad: es **parcial**. Su IF y su LOF sobre ventanas de una estación se parecen al IsolationForest del protocolo, pero no hay números que comparar.
- **Frente a Hidalgo Navarro (2011):** es el antecedente de "validación nivel 2" en RAMA y su ozono. Es descriptivo, de una sola estación y sin detector automático. La tesis puede presentarse como un paso hacia el nivel 3 automatizado (comparación entre sitios).
- No hay en la literatura encontrada un detector supervisado con vecinas (tipo L0) ni un detector por residuo de pronóstico (tipo V4) sobre RAMA. Esto es una **ausencia de evidencia en esta búsqueda**, no una prueba de que no existan. Antes de escribir "primer trabajo", conviene revisar TESIUNAM, Google Scholar y la revista *Atmósfera*.
- Los pronosticadores de ozono con ML para CDMX (RF, GB, SVR, LSTM) son candidatos naturales a "detector por residuo", pero ninguno se evaluó así. Si un sinodal pregunta por qué no se usó su modelo, la respuesta es que el V4 cumple ese papel.

### Gaps
- No se pudo buscar directamente en el catálogo de TESIUNAM (requiere formulario o navegador). Pueden existir tesis de licenciatura o maestría (Facultad de Ingeniería, ICAyCC, IIMAS, PCIC) sobre atípicos en RAMA que no indexa el buscador web.
- No se encontró ningún artículo en la revista *Atmósfera* (UNAM) sobre detección de atípicos o QC automático en RAMA. Faltaría una búsqueda directa en revistascca.unam.mx/atm.
- No se encontraron trabajos del IPN, del CCA-UNAM ni del INECC que inyecten anomalías sintéticas en datos de RAMA.
- No se pudo leer el texto completo de Díaz-González et al. (2025) ni de Neural Comput. Appl. (2022), por lo que faltan autores completos y métricas.
- Las referencias de pronóstico ML (Applied Sciences 2024, JCP 2022, Atmos. Environ. 2024, Atmosphere 2025, Computers 2026) solo se vieron en el buscador. Hay que confirmar autores, volumen y páginas antes de citarlas.

---

## 3. Trabajos análogos en otras redes latinoamericanas (CETESB, SINCA, RMCAB, SIMA Monterrey, otras)

### Takeaway
En las redes latinoamericanas la validación oficial también se basa en reglas: criterios de deriva de cero y span, bases de datos cruda, marcada y filtrada, y niveles de validación operativo y estadístico. Los pocos trabajos de ML que se encontraron son sobre PM2.5 en Bogotá y Panamá, o sobre imputación en Temuco y Monterrey. No se encontró ningún trabajo latinoamericano de detección de anomalías en ozono con inyección sintética, por residuo de LSTM o con vecinas supervisadas.

### Cited Findings
**Bogotá (RMCAB)**
- "Comparative Evaluation of Anomaly Detection Algorithms for PM2.5 Air Quality in Bogotá, Colombia". Capítulo de Springer, DOI 10.1007/978-3-032-16577-0_158. Según el resumen del buscador, compara algoritmos de detección de anomalías sobre PM2.5 horario de las estaciones de Bogotá entre 2014 y 2019 **[resumen de búsqueda; no se pudo abrir y una segunda búsqueda por el título exacto no lo encontró. Tratar como NO VERIFICADO]** — [Springer](https://link.springer.com/chapter/10.1007/978-3-032-16577-0_158)
- "Ozone Trends and Mortality Risk: The Growing Need for Machine Learning Predictions in Bogotá, Colombia". *Earth Systems and Environment* (2026). DOI: 10.1007/s41748-026-01052-3. Según el resumen, revisa la robustez de los datos de ozono de RMCAB con IQR, MAD y detección de cambios de nivel (biblioteca ADTK) **[resumen de búsqueda; no verificado]** — [Springer](https://link.springer.com/article/10.1007/s41748-026-01052-3)
- Colombia (IDEAM): manuales oficiales de validación y consistencia del SISAIRE y una guía de crítica de datos de calidad del aire. Un informe regional (CVC) describe validación de nivel 1 (operativo) y nivel 2 (estadístico) **[resumen de búsqueda]** — [IDEAM, manual de crítica EMSCA](https://ideam.gov.co/sites/default/files/normatividad/m-gci-ea-m019_manual_de_critica_emsca.pdf); [CVC, Informe calidad del aire 2011](https://calidadaire.cvc.gov.co/sites/default/files/2021-04/Informe%20Calidad%20del%20Aire%20A%C3%B1o%202011.pdf)

**Chile (SINCA / redes privadas)**
- Guzmán Bernal, V. A. (2005). *Procedimiento de validación de información de gases para red de monitoreo de calidad del aire*. Tesis de Licenciatura en Química Ambiental, Universidad de Chile. Profesor guía: Rodrigo Saavedra. Trabajo hecho en Cesmec Ltda. **[resumen de la página leído]** — [Repositorio U. de Chile](https://repositorio.uchile.cl/handle/2250/188225)
  - Red de 10 estaciones en el valle del río Huasco; SO2 y NO2; sistema de calidad NCh-ISO 17025.
  - Usa tres bases de datos: cruda; de identificación, donde los datos anómalos se marcan con códigos; y filtrada.
  - Los límites vigentes de deriva eran 15 ppbv en cero y 15 % en span; propone 5 ppbv y 10 %.
- "Use of data imputation tools to reconstruct incomplete air quality datasets: A case-study in Temuco, Chile" (2019). Compara cinco métodos de imputación sobre datos retirados de forma artificial **[resumen de búsqueda]** — [FISABIO](https://fundanet.fisabio.san.gva.es/publicaciones/ProdCientif/PublicacionFrw.aspx?id=12982); [UJI](https://portalcientific.uji.es/documentos/5eef41a42999522e441e7e05)
- Seguel, R. J. (2022). Conjunto de datos de calidad del aire (O3, NO, NO2, CO, PM2.5) de estaciones de Santiago, São Paulo y Bogotá, 2014 a mediados de 2020. PANGAEA, DOI 10.1594/PANGAEA.940288 **[resumen de búsqueda]** — [PANGAEA](https://doi.pangaea.de/10.1594/PANGAEA.940288)

**São Paulo (CETESB)**
- CETESB tiene un curso oficial, "Introdução ao Monitoramento da Qualidade do Ar", que incluye los "critérios de validação dos dados amostrados" de analizadores automáticos. Los promedios llegan por telemetría a un servidor, pasan por validación técnica periódica y se publican cada hora **[resumen de búsqueda]** — [CETESB curso 38 (2026)](https://cetesb.sp.gov.br/cursos-treinamentos/wp-content/uploads/sites/29/2026/02/38_Introducao-ao-Monitoramento-da-Qualidade-do-Ar.pdf)
- Una nota de prensa reporta fallas y "apagões" de datos en estaciones de CETESB **[resumen de búsqueda]** — [Gazeta SP](https://www.gazetasp.com.br/estado/estacoes-da-cetesb-tem-de-falhas-pontuais-a-apagao-de-dados-em/)

**Sudamérica (control de calidad en estudios de tendencias de ozono)**
- "Changes in South American surface ozone trends: exploring the influences of precursors and extreme events". *Atmospheric Chemistry and Physics* 24, 8225 (2024). Aplica criterios de calidad de datos que excluyen algunas estaciones de Santiago y São Paulo **[resumen de búsqueda]** — [ACP](https://acp.copernicus.org/articles/24/8225/2024/)

**Monterrey (SIMA, Nuevo León)**
- Un artículo indexado en Scopus del Tec de Monterrey hace pronóstico de PM2.5 con imputación MICE, variables de tiempo y winsorización del objetivo, con datos horarios de 2015 a 2022. No se confirmó que use SIMA **[resumen de búsqueda]** — [research.tec.mx SCO_85169511614](https://research.tec.mx/vivo-tec/display/AcademicArticleSCO_85169511614)
- Una nota de prensa reporta datos incompletos en estaciones SIMA (San Nicolás, Escobedo) **[resumen de búsqueda]** — [Milenio](https://www.milenio.com/politica/comunidad/modulos-sima-arroja-datos-incompletos-contaminacion-nuevo-leon)

**Panamá**
- Quintero, E.; González, J.; García, F.; Collado, E.; García, A.; Saez, Y. (2025). "Integration of Detection Techniques and Machine Learning to Improve Data Quality in Atmospheric Monitoring". LACCEI 2025, 1(12). DOI: 10.18687/LACCEI2025.1.1.1268. Una sola estación en Panamá con PM; quitan atípicos con IQR y corrigen faltantes con un autoencoder convolucional (MAE 0.1322, R² 0.577). No inyectan anomalías **[página leída]** — [LACCEI](https://proceedings.laccei.org/index.php/laccei/article/view/4051)

**Perú**
- SINIA/MINAM publica "Proceso y validación de datos en la vigilancia sanitaria de la calidad del aire" (registro de calibraciones y fallas) **[resumen de búsqueda]** — [SINIA Perú](https://sinia.minam.gob.pe/documentos/proceso-validacion-datos-vigilancia-sanitaria-calidad-aire)

### Inferences
- En toda la región, el control de calidad operativo es de reglas y bitácoras (deriva de cero y span, fuera de rango, banderas), igual que en la NOM-156. Los trabajos de ML se dividen en dos grupos: **imputación** (Temuco, Monterrey, Panamá, CDMX) y **atípicos univariados o no supervisados** (IQR, MAD, IF en Bogotá y Panamá). Ninguno de los encontrados evalúa con anomalías sintéticas de magnitud controlada ni con umbral de falsas alarmas calibrado. Esa es la contribución metodológica que la tesis puede reclamar, siempre con la cautela de "en la literatura revisada".
- Comparabilidad con V4 y L0: ninguno de los trabajos latinoamericanos encontrados da números directamente comparables (otro contaminante, otra unidad de evaluación, sin verdad de referencia). Solo sirven como contexto, no como línea base cuantitativa.
- El trabajo de Temuco (datos retirados de forma artificial) es lo más parecido metodológicamente a "inyectar y medir". Lo que inyecta son faltantes, no sesgos multiplicativos.

### Gaps
- No se encontró el manual o protocolo oficial de validación del SINCA (MMA Chile) ni el de RMCAB (SDA Bogotá). Faltaría buscar en sinca.mma.gob.cl y en rmcab.ambientebogota.gov.co.
- No se pudo leer el contenido del curso de CETESB con los criterios concretos de validación.
- El capítulo de Bogotá sobre anomalías en PM2.5 (DOI 10.1007/978-3-032-16577-0_158) y el de ozono en Bogotá de 2026 no se verificaron. Pueden tener errores de título o de datos.
- No se encontraron trabajos de detección de anomalías en ozono en São Paulo, Santiago, Monterrey, Guadalajara (SIMAJ) ni Lima.
- Esta búsqueda tuvo un número limitado de consultas. Google Scholar, Scielo y Redalyc no se recorrieron de forma sistemática.
