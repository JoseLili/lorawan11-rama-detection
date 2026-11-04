# Benchmarks con anomalias etiquetadas y literatura de ataques de integridad en sensado ambiental / LoRaWAN

Notas de investigacion (2026-10-31). Contexto: tesis sobre integridad de ozono RAMA (CDMX) por LoRaWAN 1.1; parte 1 bit flipping en CayenneLPP con LSTM no supervisado (V4); parte 2 alteraciones multiplicativas sostenidas x(1+-d) por estacion-dia con LSTM supervisado de vecinas (L0) y comparacion con PARAAD (Allka et al. 2024) en CDMX y Barcelona.

Convencion: "[verificado]" = leido en la fuente primaria en esta sesion; "[solo fragmento]" = visto solo en el resumen del buscador o en un listado secundario; "[no verificado]" = conocimiento previo no comprobado en esta sesion.

## 1. Datasets publicos de calidad del aire con anomalias etiquetadas o protocolo estandar de inyeccion

### Takeaway
No existe un benchmark estandar de calidad del aire con ataques de integridad etiquetados. El mas cercano es AirWare-Haikou (Scientific Data 2025): 95 estaciones horarias, 6 contaminantes incluido O3, etiquetas derivadas de alarmas de estacion y aumento sintetico sin magnitudes documentadas; sus etiquetas son de "evento/alarma", no de manipulacion, por lo que no permite comparar numeros con L0/V4 de forma directa. El resto (UCI Beijing, CREA) son datos sin verdad de terreno, y la practica comun es inyectar anomalias propias, igual que la tesis.

### Cited Findings
**AirWare-Haikou (el candidato mas serio)** [verificado]
- Liu, Zhi, Zhou, Zhao, Tian, Gao, Luo, Cui, Wang, "A holistic air monitoring dataset with complaints and POIs for anomaly detection and interpretability tracing", Scientific Data 12, art. 1288 (2025), DOI 10.1038/s41597-025-05591-8 — [Nature](https://www.nature.com/articles/s41597-025-05591-8); [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Contenido: 95 estaciones en 4 distritos de Haikou (Hainan, China), datos horarios del 2021-05-26 al 2023-03-11; PM2.5, PM10, CO, NO2, SO2, O3 + 5 variables meteorologicas (11 variables). Ademas POI y un corpus de quejas ciudadanas (1,172 instantes unicos; el olor es la fuente mas citada, 278 veces) usado como evidencia externa para trazar anomalias — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Etiquetas: generadas a partir de alarmas en tiempo real de las estaciones (el texto menciona AQI y en otro lugar alarmas de PM2.5; el criterio exacto es ambiguo). Aumento de anomalias por recorte temporal, generacion sintetica y adicion de ruido, SIN tipos ni magnitudes documentadas — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Proporcion de anomalias (original -> aumentado): MTSAM_01 6.67 % -> 22.23 %; MTSAM_02 9.02 % -> 28.40 %; MTSAM_03 4.23 % -> 15.00 %; MTSAM_04 6.45 % -> 21.62 %. Media por estacion 1,555 puntos anomalos (min 20, max 6,317) — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Division aleatoria 6:2:2 (p. ej., MTSAM_01: 228,103 / 76,035 / 76,035 muestras) — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Lineas base (tabla 9; precision, recall, F1, exactitud, ROC-AUC): DsRL-Net F1 0.883/0.939/0.940/0.907; Anomaly Transformer 0.877/0.929/0.928/0.911; USAD 0.898/0.924/0.930/0.885; TranAD 0.777/0.925/0.862/0.886; NPSR 0.577-0.704. DsRL-Net promedio: exactitud 0.958, precision 0.9525, recall 0.883, F1 0.917 — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031)
- Acceso: Zenodo DOI 10.5281/zenodo.15379915, v3 del 2025-05-10, acceso abierto, CC BY 4.0, 210.2 MB (Airware-Haikou.zip 196.5 MB + CODE.zip 13.6 MB); hay una version mas nueva del registro — [Zenodo](https://zenodo.org/records/15379915). Nota: el articulo esta bajo CC BY-NC-ND 4.0 y el registro de datos bajo CC BY 4.0 — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12290031); [Zenodo](https://zenodo.org/records/15379915)
- El formato del aumento sigue la convencion de PSM y UCR (benchmarks genericos) — [Nature](https://www.nature.com/articles/s41597-025-05591-8)

**CREA "Anomaly detection" challenge (estaciones que sub/sobre-reportan)** [verificado]
- Centre for Research on Energy and Clean Air: PM2.5 y PM10 horarios de estaciones oficiales de India, China, Alemania y EUA, 2021-2023 (mas paises/anios a peticion). Objetivo: identificar estaciones que sistematicamente sub-reportan, sobre-reportan o no reportan, sobre todo sub-reporte en concentraciones altas, usando vecinas espaciales y temporales. Sin etiquetas de verdad de terreno, sin metrica definida, sin fecha limite; salida = indice de confiabilidad por estacion, codigo bajo licencia abierta; acceso por formulario — [CREA](https://energyandcleanair.org/challenge/anomaly-detection/)

**UCI Beijing Multi-Site Air Quality** [solo fragmento]
- 12 sitios nacionales de Beijing (Beijing Municipal Environmental Monitoring Center), horario, 420,768 instancias, con faltantes, CC BY 4.0. No trae anomalias etiquetadas ni protocolo de inyeccion — [UCI](https://archive.ics.uci.edu/dataset/501/beijingmultisiteairqualitydata)
- La busqueda no encontro un benchmark "Beijing multi-site con anomalias inyectadas" estandar — [UCI](https://archive.ics.uci.edu/dataset/501); [IEEE DataPort multi-site AQI, DOI 10.21227/d7c0-8f79](https://ieee-dataport.org/documents/multisiteaqidataset)

**Sensores de bajo costo** [solo fragmento]
- AQ-SDR (articulo "Veli", arXiv 2508.02724): 23,737 sensores de bajo costo y de referencia, >6 anios; pensado para correccion/calibracion, no para fallas etiquetadas — [arXiv](https://arxiv.org/pdf/2508.02724)
- EPA, conjunto sobre degradacion de sensores de PM de bajo costo (DOI 10.23719/1528083): deriva/envejecimiento, sin clases de falla etiquetadas segun el listado — [data.gov](https://catalog.data.gov/dataset/metadata-an-analysis-of-degradation-in-low-cost-particulate-matter-sensors)
- Sistema de control de calidad de la UE para sensores ciudadanos de PM2.5: correlacion con vecinos en radio de 30 km y 30 dias, y bandera de valor congelado (<=0.1 ug/m3 durante 8 h). Es control de fallas, no de manipulacion — [Comision Europea](https://environment.ec.europa.eu/news/air-pollution-data-citizen-operated-sensors-improved-novel-quality-control-system-2025-11-06_en)

**Trabajos que inyectan anomalias propias en estaciones reales** [solo fragmento]
- Cartagena (SciTePress 2026): inyecta picos, desplazamientos (offsets que persisten horas, tipo deriva) y caidas sobre datos de estaciones verificados manualmente; Monte Carlo sobre varias semanas base; Prophet + Isolation Forest — [SciTePress](https://www.scitepress.org/Papers/2026/150729/150729.pdf)
- Delhi (38 estaciones, 2019-2022): marco probabilistico con comparacion contra vecinas; F1 0.878 en datos sinteticos con anomalias inyectadas — [ResearchGate](https://www.researchgate.net/publication/384571288_A_probabilistic_framework_for_identifying_anomalies_in_urban_air_quality_data) (no se pudo confirmar revista ni DOI)

### Inferences
- AirWare-Haikou es el unico dataset de calidad del aire publicado en una revista de datos con etiquetas y lineas base numericas, e incluye O3 y 95 estaciones (densidad comparable o superior a RAMA). Pero sus etiquetas son alarmas de contaminacion (eventos reales altos), no alteraciones de integridad; un F1 ~0.9 ahi NO es comparable con el F1 de L0 en x(1+-d). Ademas usa division aleatoria 6:2:2 (fuga temporal), contraria a la division cronologica de la tesis. Sirve para citar como "no existe benchmark de integridad", y opcionalmente para correr L0/R3 con el protocolo de inyeccion de la tesis sobre sus datos limpios (una tercera ciudad, como Barcelona).
- El reto de CREA es conceptualmente el mas cercano al escenario de la parte 2 (estacion que sesga sistematicamente frente a sus vecinas), pero sin verdad de terreno. Respalda la motivacion de la tesis: el problema real existe y no tiene benchmark.
- La practica dominante es inyeccion sintetica propia (picos, offsets, deriva, congelamiento). La tesis sigue la misma practica; su diferencia es la anomalia multiplicativa sostenida por dias, un plan pareado y umbrales calibrados en un anio limpio, que no aparecen documentados en estos trabajos.

### Gaps
- No se encontro ningun dataset publico de calidad del aire con manipulacion/ataque etiquetado (ni con magnitudes multiplicativas tipo x(1+-d)).
- No se verifico el DOI exacto de UCI Beijing ni si existe un trabajo que lo use con protocolo de inyeccion estandar.
- No se encontro un dataset publico de fallas etiquetadas de sensores de bajo costo de calidad del aire (los encontrados con etiquetas son de HVAC).
- Articulos de Cartagena y Delhi: solo fragmento; falta autoria, revista y DOI confirmados.

## 2. Benchmarks genericos de anomalias en series de tiempo (TSB-UAD, UCR, NAB, SMD, SWaT/WADI): contenido ambiental y relevancia

### Takeaway
Los benchmarks genericos casi no contienen datos ambientales (en UCR solo ~5 % es temperatura del aire) y son univariados o industriales; ademas tienen criticas metodologicas publicadas. SWaT/WADI (agua) si contienen ataques de manipulacion de sensores reales, pero en sistemas de control industrial, no en redes de monitoreo atmosferico. Son relevantes solo para justificar por que no se usan.

### Cited Findings
- UCR Anomaly Archive: 250 series univariadas; ~64 % medicina, 22 % biologia, 9 % industria, 5 % temperatura del aire; cada serie tiene exactamente una anomalia tras un instante dado — [Wu y Keogh, arXiv 2009.13807](https://arxiv.org/pdf/2009.13807)
- Wu y Keogh sostienen que los benchmarks actuales (Yahoo, Numenta, NASA, OMNI) tienen fallas (trivialidad, densidad irreal de anomalias, etiquetas erroneas, sesgo de posicion) que crean "ilusion de progreso" — [arXiv 2009.13807](https://arxiv.org/pdf/2009.13807) (titulo verificado; detalle de las cuatro fallas [no verificado] en esta sesion)
- TSB-UAD: 13,766 series univariadas etiquetadas en el articulo (VLDB vol. 15, p. 1697); la version publica en GitHub tiene 10,828 series (92 datasets); los conjuntos sinteticos/artificiales se construyen a partir de UCR — [VLDB](https://www.vldb.org/pvldb/vol15/p1697-paparrizos.pdf); [GitHub](https://github.com/TheDatumOrg/TSB-UAD)
- Dominios listados en UCR/TSB-UAD: temperatura del aire, presion arterial, astronomia, EPG, ECG, marcha, demanda electrica, respiracion, acelerometro; otras fuentes: SMD (industria/servidores), LTDB, SVDB (salud), IOPS, WSD (web), YAHOO — [arXiv 2511.12147](https://arxiv.org/pdf/2511.12147)
- SWaT (iTrust, SUTD, 2015): planta de tratamiento de agua a escala; 11 dias (7 normales, 4 con ataques); 36 ataques MITM entre PLC y SCADA en la version A1&A2; algunos ataques falsean lecturas de sensores (p. ej., sensor de nivel del tanque de alimentacion de osmosis inversa) — [SoK, arXiv 2311.02929](https://arxiv.org/pdf/2311.02929); [MAD-GAN, arXiv 1901.04997](https://arxiv.org/pdf/1901.04997)
- WADI.A1: 16 dias (14 normales, 2 con ataque), 123 sensores y actuadores, 15 ataques; versiones posteriores quitan lecturas inestables y agregan archivo de etiquetas. Ejemplo: lectura de nivel de tanque cambiada de 76 % a 10 % — [iTrust](https://www.sutd.edu.sg/itrust/itrust-labs/datasets/dataset-characteristics/wadi/); [arXiv 1901.04997](https://arxiv.org/pdf/1901.04997)
- El SoK de evaluaciones en IDS industriales senala que el momento exacto de los ataques en estos datasets es dificil de fijar, lo que complica la evaluacion — [arXiv 2311.02929](https://arxiv.org/pdf/2311.02929)
- NAB (Numenta Anomaly Benchmark) contiene series como "ambient_temperature_system_failure" y "machine_temperature" [no verificado en esta sesion]

### Inferences
- Ninguno de estos benchmarks contiene una red espacial de estaciones con la misma variable (que es lo que explotan L0, R3 y PARAAD). Un detector de vecinas no tiene donde aplicarse en UCR/TSB-UAD/NAB; reportar numeros ahi no seria "peras con peras".
- SWaT/WADI son la referencia canonica de "falsificacion de lecturas de sensores" y conviene citarlos como analogia (ataque a la integridad del dato medido con etiquetas), aclarando que es un sistema de control cerrado, con dinamica fisica determinista, no una red atmosferica.
- La critica de Wu y Keogh apoya la decision de la tesis de usar azar/linea "sin ataque", division cronologica y umbrales calibrados fuera de prueba.

### Gaps
- No se verifico en esta sesion el contenido exacto de NAB ni de SMD.
- No se reviso TSB-AD (version multivariada mas reciente) para saber si incluye datos ambientales.

## 3. Deteccion de inyeccion de datos falsos / manipulacion en monitoreo ambiental, calidad del aire o redes de sensores IoT

### Takeaway
Hay tres lineas: (a) demostraciones de ataque en redes de calidad del aire de bajo costo sin detector (Luo et al. 2018); (b) deteccion de FDIA en redes de sensores por correlacion entre sensores (Illiano y Lupu 2015; Hau y Lupu 2019; Hu et al. 2024), casi siempre con datos no ambientales; y (c) evidencia empirica de manipulacion real de datos de calidad del aire (China, Greenstone et al. 2022). No se encontro ningun trabajo que evalue un detector supervisado contra alteraciones multiplicativas sostenidas en una red oficial de calidad del aire.

### Cited Findings
**Ataques demostrados en calidad del aire** [verificado]
- Luo, Zhang, Pearson, Ling, Yu, Fu, "On the Security and Data Integrity of Low-Cost Sensor Networks for Air Quality Monitoring", Sensors 18(12):4451 (2018), DOI 10.3390/s18124451 — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6308815/)
- Red analizada: red popular de PM2.5 de bajo costo (sensor de doble laser con ESP8266; datos a su servidor y a ThingSpeak). Ataques: MITM con ARP spoofing + mitmproxy que llevo el AQI mostrado a 151 con lectura real ~0; suplantacion de sensor con su MAC (el servidor promedia datos reales y falsos; el intervalo de envio falso se ajusto para ocultar fluctuaciones); captura de MAC por wardriving (espera media ~6.18 s); enumeracion de MAC a gran escala (~0.2 s por consulta, ~1,000 USD de computo) — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6308815/)
- No propone detector; recomienda IDs derivados de claves, TLS con autenticacion mutua, arranque seguro, verificacion de ubicacion, actualizaciones seguras — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6308815/)

**Manipulacion real de datos de calidad del aire** [verificado por resumen del editor]
- Greenstone, He, Jia, Liu, "Can Technology Solve the Principal-Agent Problem? Evidence from China's War on Air Pollution", American Economic Review: Insights 4(1):54-70 (2022), DOI 10.1257/aeri.20200373; datos y codigo en OpenICPSR DOI 10.3886/e125321 — [AEA](https://www.aeaweb.org/research/charts/air-pollution-principal-agent-china); [LSE](https://eprints.lse.ac.uk/124670/); [OpenICPSR](https://www.openicpsr.org/openicpsr/project/125321)
- 654 diseños de regresion discontinua por fecha de automatizacion del monitoreo en cada ciudad; el PM10 reportado subio 35 % de forma inmediata y sostenida tras la automatizacion; estimaciones positivas en >70 % de las ciudades — [AEA](https://www.aeaweb.org/research/charts/air-pollution-principal-agent-china)
- Seguimiento (AEJ: Economic Policy, 2024, Yang, Lin, Wang, Peng, DOI 10.1257/pol.20220810): los gobiernos locales respondieron reduciendo contaminacion cerca de los monitores (-3.2 % junto a monitores automatizados) — [AEA](https://www.aeaweb.org/doi/10.1257/pol.20220810) [solo fragmento]

**Deteccion de inyecciones maliciosas en redes de sensores** 
- Illiano y Lupu, "Detecting Malicious Data Injections in Wireless Sensor Networks: A Survey", ACM Computing Surveys 48(2):24 (2015), DOI 10.1145/2818184; clasifica enfoques y senala que la deteccion es mas dificil cuando varios sensores coluden y simulan comportamiento plausible — [Imperial SPIRAL](https://spiral.imperial.ac.uk/entities/publication/5ab44d91-c262-4a52-b844-c47bd26a303e); [dblp](https://dblp.dagstuhl.de/pid/167/8102.html) [solo fragmento]
- Hau y Lupu, "Exploiting Correlations to Detect False Data Injections in Low-Density Wireless Sensor Networks", CPSS@AsiaCCS 2019, pp. 1-12; usa correlaciones entre sensores y modela ataques coordinados en varios sensores — [Imperial SPIRAL](https://spiral.imperial.ac.uk/entities/publication/b134f12c-acc9-466e-a2f3-c72069ea4b56); [dblp](https://dblp1.uni-trier.de/rec/conf/cpss/HauL19.html) [solo fragmento]
- Hu, Yang, Yang, "A Framework for Detecting False Data Injection Attacks in Large-Scale Wireless Sensor Networks", Sensors 24(5):1643 (2024), DOI 10.3390/s24051643 [verificado] — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10935136/):
  - Datos: demanda electrica horaria por subregion (EIA 2020), no ambiental; datos "a peticion".
  - Ataques: FDIA simple (+50 % aleatorio en un sensor, es decir multiplicativo como x(1+0.5)); FDIA sigilosa (subida lenta bajo el umbral, "rana hervida", periodica); FDIA sigilosa y colusoria (segundo sensor con senal similar).
  - Metodo: agrupamiento por correlacion cruzada (K-means), prediccion ARIMA, prueba de consistencia y voto mayoritario por grupo.
  - Resultados (100 experimentos por escenario, contra SCCR): simple >=99 % deteccion con FP ~0 (ambos); sigilosa >=99 %, FP ~0 contra hasta 14 % de SCCR; colusoria >=95 %, FN hasta 5 %, FP <=3 % contra hasta 19 %. Falla si los sensores colusorios superan 50 %.
- Cui et al., "Spatio-Temporal Correlation based Anomaly Detection and Identification Method for IoT Sensors" (IEEE): correlacion espaciotemporal + logica difusa para separar nodo defectuoso de evento ambiental real — [IEEE Xplore 9074607](https://ieeexplore.ieee.org/document/9074607/) [solo fragmento]
- XAI para asegurar datos de la capa de percepcion en sistemas IoT de deteccion de peligros ambientales (MITM/spoofing en sensores de gas), Future Internet 18(8):385 — [DOI 10.3390/fi18080385](https://doi.org/10.3390/fi18080385) [solo fragmento]
- IEEE DataPort lista un dataset (2024) de deteccion TinyML de ataques de congelamiento (freeze) y repeticion (replay) en monitores IoT de calidad del aire con MQTTS, 11 clases de ciberataque — [IEEE DataPort](https://ieee-dataport.org/keywords/data-integrity-attack) [solo fragmento; falta titulo y DOI exactos]

### Inferences
- Luo et al. 2018 es la cita natural de "el ataque a la integridad del dato de calidad del aire es factible y puede ocultarse"; Greenstone et al. 2022 es la cita de "la manipulacion de datos oficiales de calidad del aire ocurrio a gran escala y fue sesgo sostenido" (un 35 % de sub-reporte equivale aproximadamente a x/(1+d) con d ~0.35-0.5 en terminos de la tesis; esta equivalencia es inferencia propia, no del articulo). Juntas motivan la parte 2.
- Hu et al. 2024 es el comparador metodologico mas parecido (correlacion entre sensores + prediccion + voto, y un ataque +50 % multiplicativo), pero en datos electricos; sus numeros (>=95-99 %) se obtienen con un sensor atacado en series suaves y no son comparables con el F1 de L0 por estacion-dia en ozono.
- El limite de "colusion > 50 %" de Hu et al. es el mismo fenomeno que la tesis estudio en la revision 19 (ataques simultaneos en vecinas); vale la pena citarlo para enmarcar ese resultado.
- La literatura de FDIA en sensores es mayormente no supervisada (prediccion + umbral, correlacion); un detector supervisado entrenado con calendarios de inyeccion (L0) es menos comun.

### Gaps
- No se encontro trabajo que detecte FDIA en una red oficial de calidad del aire (estaciones de referencia) con magnitudes reportadas y F1/recall.
- Faltan magnitudes y metricas de Hau y Lupu 2019 y de Cui et al. (solo fragmentos).
- El dataset TinyML freeze/replay de IEEE DataPort no se pudo identificar con titulo/DOI.

## 4. Bit flipping / corrupcion de payload en LoRaWAN y verificacion de integridad de datos LoRaWAN

### Takeaway
El bit flipping en LoRaWAN esta bien documentado como ataque (Lee et al. 2018; revision sistematica 2021) y hay al menos un detector con aprendizaje profundo (Alizadeh y Bidgoly 2023, 99.84 % de exactitud). Los IDS y detectores de jamming para LoRaWAN usan datos semisinteticos o simulados (trazas de Brno, gateway de Lisboa, ns-3) y operan sobre metadatos de red, no sobre el valor fisico medido; no existe un dataset publico estandar de ataques LoRaWAN.

### Cited Findings
**Bit flipping**
- Revision sistematica de seguridad en LoRaWAN: el MIC de 4 bytes deja el payload expuesto a fuerza bruta y bit flipping — [arXiv 2105.00384](https://arxiv.org/pdf/2105.00384) [solo fragmento]
- Lee et al., IoTDI 2018: analizan cinco ataques en LoRaWAN, incluido bit flipping y modificacion maliciosa de mensajes, con prueba de concepto en un entorno controlado — [TU Delft](https://pure.tudelft.nl/ws/files/46032668/IoTDI2018.pdf) [solo fragmento]
- Explicacion: el atacante cambia bits del texto cifrado sin descifrar (AES-CTR) conociendo la posicion de cada campo; el alcance del cifrado y el del chequeo de integridad no coinciden en la red/servidor — [SciTePress 2020](https://www.scitepress.org/Papers/2020/95611/95611.pdf); [UCSC](https://cmpe259-spring18-01.courses.soe.ucsc.edu/system/files/attachments/Security%20Vulnerabilities%20in%20LoRaWAN.pdf) [solo fragmento]
- Alizadeh y Bidgoly, "Bit flipping attack detection in low power wide area networks using a deep learning approach", Peer-to-Peer Networking and Applications, 2023 (num. 4): deteccion por aprendizaje sin aumentar el payload ni la energia del emisor; hasta 99.84 % de exactitud en varios modos de ataque, aplicaciones y entornos — [Springer Professional](https://www.springerprofessional.de/en/bit-flipping-attack-detection-in-low-power-wide-area-networks-us/25484114) [solo fragmento; DOI no confirmado]
- Mismos autores, Computer Networks 2020: re-sincronizacion de clave de encadenamiento de cifrado en LPWAN con aprendizaje profundo — [Springer Professional](https://www.springerprofessional.de/en/bit-flipping-attack-detection-in-low-power-wide-area-networks-us/25484114) [solo fragmento]
- Testbed de seguridad LoRaWAN (VUT Brno): bit flipping via MITM sobre OTAA — [VUT](https://dspace.vut.cz/items/8207f2da-45cf-4884-a1e4-9dfa88d01ec6) [solo fragmento]

**IDS / jamming / spoofing en LoRaWAN**
- Pourghasem et al., Future Internet 18:38 (2026), autenticacion de capa fisica multiatributo contra jamming y agotamiento de bateria: dataset semisintetico desde trazas publicas de Brno, 230,296 registros de 1,921 dispositivos en 13.68 dias; MLP F1 0.8260, AUC-ROC 0.8953; Random Forest comparable — [UH Research Archive](https://uhra.herts.ac.uk/id/eprint/26430/) [solo fragmento]
- Esteves et al., IoT 5(4) (dic. 2024): ML (KNN) integrado en Suricata adaptado a LoRaWAN — [Repositorio IPL](https://repositorio.ipl.pt/entities/publication/7c550223-abc5-4d5a-a2b1-155986b86769/full) [solo fragmento]
- Tesis IPL Lisboa: paquetes de un gateway LoRaWAN (2020) con anomalias sinteticas inyectadas; mejor metodo HBOS; validacion con ataques reales como trabajo futuro — [Repositorio IPL](https://repositorio.ipl.pt/bitstreams/1d346c51-6e48-4d57-9e04-afad44c63942/download) [solo fragmento]
- Di Pinto et al., WCNC 2025: detector LSTM de jamming con simulaciones ns-3 — [Sapienza IRIS](https://iris.uniroma1.it/handle/11573/1740415) [solo fragmento]
- Ruotsalainen, ARES 2022: deteccion de jamming reactivo por desviaciones de metadatos (no ML), hasta 99 % para distinguir jamming de colision — mencionado en [resultados de busqueda](https://phaidra.ustp.at/o:5179) [solo fragmento]
- Deteccion de jammers LoRa moviles (DTU) — [DTU](https://people.compute.dtu.dk/chaorf/doc/Detection_of_Mobile_LoRa_Jammers.pdf) [solo fragmento]
- Spoofing en LoRaWAN (Future Internet, feb. 2025): dataset parcialmente sintetizado desde "LoRa at the Edge"; RF con la mejor exactitud — [UH Research Archive](https://uhra.herts.ac.uk/id/eprint/11772/1/futureinternet-17-00068.pdf) [solo fragmento]
- Tesis UCLouvain 2023: metodologia para capturar/simular ataques LoRaWAN y generar datasets (incluye trafico DoS) — [DIAL UCLouvain](https://dial-mem.test.bib.ucl.ac.be/handle/2078.2/34195) [solo fragmento]

### Inferences
- Alizadeh y Bidgoly 2023 es el comparador directo de la parte 1; su 99.84 % es exactitud (no F1 ni recall con falsas alarmas fijas) y probablemente sobre datos de aplicacion distintos de ozono; no es comparable sin replicar su protocolo. Conviene leer el articulo completo (tipo de bits volteados, si el detector ve el valor o el cifrado, conjunto de datos).
- Los IDS LoRaWAN encontrados trabajan con metadatos de radio y red (RSSI, SNR, conteos, tiempos), es decir detectan jamming/DoS/spoofing de dispositivo, no alteraciones del valor medido dentro de un paquete autentico. La aportacion de la tesis (detector a nivel del dato fisico, con vecinas) es complementaria a ellos.
- Ningun dataset publico LoRaWAN encontrado incluye cargas utiles de sensores ambientales con bit flipping etiquetado.

### Gaps
- No se encontro DOI del articulo de Alizadeh y Bidgoly 2023 ni su texto completo; tampoco detalles de sus datos y metricas.
- No se verifico si LoRaWAN 1.1 (vs 1.0.x) cambia la exposicion al bit flipping en estos trabajos.
- No se encontraron trabajos de IDS federado especificos para LoRaWAN (la busqueda no los arrojo; quedaria por buscar "federated learning intrusion detection LoRaWAN").
- Las fuentes de la seccion 4 se vieron mayoritariamente como fragmentos de busqueda; revisar texto completo antes de citar cifras en la tesis.
