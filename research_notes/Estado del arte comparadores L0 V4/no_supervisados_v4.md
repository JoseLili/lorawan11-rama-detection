# Estado del arte: detectores NO supervisados comparables al V4 (y a PARAAD) en redes multiestacion de calidad del aire

Notas de investigacion (2026-10-31). Alcance: metodos no supervisados de deteccion de anomalias o fallas en redes
de varias estaciones (ozono preferente) que usan vecinas espaciales, por pronostico, reconstruccion o monitoreo
estadistico. Convencion: "[verificado]" = lo lei en el texto completo o en el resumen oficial durante esta sesion;
"[solo resumen]" = solo vi resumen o ficha; "[NO VERIFICADO]" = no pude confirmarlo. Los DOI se confirmaron con
Crossref salvo donde se indica.

## 1. Familia Harrou / Nounou (PCA, GLRT, MEWMA) sobre la red de ozono francesa: referencias exactas, datos, magnitudes de falla y metricas

### Takeaway
La linea de Harrou y coautores usa la red de ozono de Alta Normandia (Air Normand, 7 estaciones, datos cada 15 min de
2006) y modela la red con PCA y detecta con GLR o MEWMA sobre los residuos. El articulo de revista que revise completo
(PSEP 2016) NO inyecta fallas sinteticas: compara contra los episodios de ozono que declararon los expertos de Air
Normand y detecta 17 de 24. No encontre el "~20 % sensor fault" en ningun texto que pudiera leer (ver Gaps).

### Cited Findings
- **Harrou, Nounou y Nounou (2013), IEEE CIDM 2013, pp. 95-102, doi:10.1109/CIDM.2013.6597223** [solo resumen]: "PCA-based GLR" aplicado al ozono de Alta Normandia, con dos casos de estudio: una falla de sensor y un episodio de contaminacion por ozono troposferico en varias estaciones. Segun el resumen, da menos falsas alarmas que el PCA convencional. El resumen no da magnitudes ni tasas — [HBKU](https://elmi.hbku.edu.qa/en/publications/detecting-abnormal-ozone-levels-using-pca-based-glr-hypothesis-te/); DOI confirmado en [Crossref](https://api.crossref.org/works?query.bibliographic=Harrou+ozone+PCA+GLR).
- **Harrou, Fillatre, Bobbia y Nikiforov (2013), "Statistical detection of abnormal ozone measurements based on Constrained Generalized Likelihood Ratio test", 52nd IEEE CDC, pp. 4997-5002, doi:10.1109/CDC.2013.6760673** [solo ficha]. Entre los coautores esta M. Bobbia (Air Normand). No pude leer el resumen — [Crossref](https://doi.org/10.1109/CDC.2013.6760673).
- **Harrou, Nounou y Nounou (2013), "A statistical fault detection strategy using PCA based EWMA control schemes", 9th ASCC, pp. 1-4, doi:10.1109/ASCC.2013.6606311** [solo ficha] — [Crossref](https://doi.org/10.1109/ASCC.2013.6606311).
- **Harrou, Nounou y Nounou (2012), "Statistical detection of abnormal ozone levels using principal component analysis", Int. J. Engineering & Technology 12(6):54-59** [referencia tomada de la bibliografia de PARAAD; sin DOI; NO VERIFICADO de forma independiente] — [PARAAD, preprint UPC](https://upcommons.upc.edu/bitstreams/b277ed89-9983-4698-bd95-c74c31b199c9/download).
- Hay una extension de 2013 con filtrado multiescala de los residuos del PCA, tambien sobre el ozono de Alta Normandia ("Enhanced monitoring using PCA-based GLR fault detection and multiscale filtering"). No pude confirmar su DOI — [HBKU](https://elmi.hbku.edu.qa/en/publications/enhanced-monitoring-using-pca-based-glr-fault-detection-and-multi/).
- **Harrou, Kadri, Khadraoui y Sun (2016), "Ozone measurements monitoring using data-based approach", Process Safety and Environmental Protection 100:220-231, doi:10.1016/j.psep.2016.01.015** [verificado, texto completo en HAL]. Es el metodo PCA-MEWMA:
  - Datos: red Air Normand de 7 estaciones de ozono (industriales, periurbanas y urbanas), con ozono cada 15 min. El modelo PCA se ajusta con 773 observaciones del 11 al 19 de agosto de 2006, se retienen 2 componentes (86.88 % y 4.34 % de la varianza) y la prueba usa tres periodos de 2006 (27, 21 y 29 dias) — [HAL hal-02292084](https://hal.science/hal-02292084v1/document).
  - Control de falsas alarmas: el umbral del MEWMA es h(α)=9.65, con suavizado r=0.25 y probabilidad de falsa alarma α=0.005, calibrado con datos sin falla — [HAL](https://hal.science/hal-02292084v1/document).
  - Evaluacion: no hay inyeccion sintetica. Se compara contra 24 episodios de ozono declarados por los expertos de Air Normand (picos de unos 115 a 244 µg/m³ que duran de 45 min a 3 h). En la Tabla 2 cuento 17/24 detectados con PCA-MEWMA, 6/24 con PCA-Q y 2/24 con PCA-T². La tabla no informa cuantas falsas alarmas hubo en las horas normales — [HAL](https://hal.science/hal-02292084v1/document).
  - Nota: las "anomalias" de ese articulo son sobre todo episodios reales de contaminacion (picos de ozono), no fallas de sensor — [HAL](https://hal.science/hal-02292084v1/document).
- **Harrou, Dairi, Sun y Kadri (2018), "Detecting abnormal ozone measurements with a deep learning-based strategy", IEEE Sensors J. 18(17):7222-7232, doi:10.1109/JSEN.2018.2852001** [solo resumen, segun un buscador]. Combina una deep belief network (que modela el ozono) con un one-class SVM (que decide la anomalia) y es no supervisado. No pude confirmar los datos ni las magnitudes — [Crossref](https://doi.org/10.1109/JSEN.2018.2852001); [ficha SDL](https://sindex.sdl.edu.sa/esploro/outputs/journalArticle/Detecting-Abnormal-Ozone-Measurements-With-a/9941021908331).
- **Harrou, Dairi, Sun y Senouci (2018), "Reliable detection of abnormal ozone measurements using an air quality sensors network", IEEE Int. Conf. Environmental Engineering (EE), pp. 1-5, doi:10.1109/EE1.2018.8385265** [solo ficha] — [Crossref](https://doi.org/10.1109/EE1.2018.8385265).
- Variantes del grupo Nounou y Mansouri, en redes de calidad del aire de varios contaminantes:
  - **Harkat, Mansouri, Nounou y Nounou (2018), "Enhanced data validation strategy of air quality monitoring network", Environmental Research 160:183-194, doi:10.1016/j.envres.2017.09.023** [solo resumen]: GLRT+EWMA para detectar y MRPCA (PCA de intervalos) para aislar; datos reales de PM, O3, NOx y CO. La ficha no da magnitudes ni tasas — [HBKU](https://elmi.hbku.edu.qa/en/publications/enhanced-data-validation-strategy-of-air-quality-monitoring-netwo/).
  - **Baklouti, Ben Hamida, Mansouri y Nounou (2016/2017), "Fault detection of an air quality monitoring network", STA 2016, pp. 229-233, doi:10.1109/STA.2016.7952051** [solo resumen]: PCA con ondeletas (WPCA) mas GLRT — [HBKU](https://elmi.hbku.edu.qa/en/publications/fault-detection-of-an-air-quality-monitoring-network/).
  - **Baklouti, Mansouri, Nounou, Nounou y Ben Hamida (2017), "Recursive kernel PCA-based GLRT for fault detection: Application to an air quality monitoring network", SM2C 2017, pp. 152-155, doi:10.1109/SM2C.2017.8071839** [solo ficha] — [Crossref](https://doi.org/10.1109/SM2C.2017.8071839).
  - **Lahdhiri, Said y Taouali (2019), "Sensor fault detection using a new online reduced rank kernel PCA for monitoring an air quality monitoring network", IC_ASET 2019, doi:10.1109/ASET.2019.8871046** [solo resumen]: probado sobre la red AIRLOR simulada — [Crossref](https://doi.org/10.1109/ASET.2019.8871046).
- Otra linea, de Estados Unidos, por monitoreo estadistico: **Xie, Qian y Qiu (2024), "Online monitoring of air quality using PCA-based sequential learning", Annals of Applied Statistics 18(1):600-625, doi:10.1214/23-AOAS1803** [solo resumen]. Es PCA mas aprendizaje secuencial para ozono en Houston-Galveston-Brazoria. Admite una distribucion en control que cambia con el tiempo, correlacion serial y una distribucion no parametrica, y usa datos meteorologicos — [Crossref/S2](https://doi.org/10.1214/23-AOAS1803); [Project Euclid](https://projecteuclid.org/journals/annals-of-applied-statistics/volume-18/issue-1/Online-monitoring-of-air-quality-using-PCA-based-sequential-learning/10.1214/23-AOAS1803.full).
- **Xie y Qiu (2023), "Control charts for dynamic process monitoring with an application to air pollution surveillance", AOAS 17:47-66, doi:10.1214/22-AOAS1615** [solo resumen]: una carta de control dinamica para el PM2.5 diario de Beijing (deteccion de aumentos; es de una sola serie, no de red) — [DOI](https://doi.org/10.1214/22-AOAS1615).

### Inferences
- El PCA-MEWMA (o PCA-GLR) de Harrou es un comparador no supervisado barato y bien definido para RAMA. Se ajusta un PCA sobre las 31 (o 32) estaciones con datos limpios de 2020-2022, se calcula el residuo Q o el estadistico MEWMA por hora de red y el umbral se calibra en 2023 limpio con la misma tasa de falsas alarmas por hora de red (5 % y 1 %). Asi se compara "peras con peras" con el V4. A diferencia del articulo original, el umbral no saldria de la teoria (α=0.005) sino del año de calibracion, como en el V4.
- El PCA lineal sobre el ozono crudo con ciclo diario tendra residuos estacionales. Harrou mismo menciona que hay que quitar la periodicidad de 24 h. Para no darle desventaja artificial convendria alimentarlo con las mismas entradas relativas al perfil de 14 dias que usa el V4.
- Para localizar la estacion (no solo "hay anomalia en la red"), el Q del PCA se descompone en contribuciones por variable. Eso es compatible con la estacion-dia de la revision 11 en adelante.
- El xie-qian-qiu 2024 (PCA con aprendizaje secuencial y distribucion en control que cambia) es el pariente estadistico mas cercano al perfil adaptativo de 14 dias del V4. Sirve para la discusion aunque no se implemente.

### Gaps
- No encontre texto completo de CIDM 2013 ni de CDC 2013, asi que no puedo confirmar que inyectaron una falla de sensor de "~20 %" ni con que magnitud. La cifra del 20 % queda NO VERIFICADA. Para confirmarla hay que leer el PDF de IEEE (doi:10.1109/CIDM.2013.6597223) o la tesis doctoral de Harrou (Universidad de Tecnologia de Troyes, sin verificar).
- No tengo las metricas cuantitativas (tasa de deteccion, falsas alarmas, ARL) de los articulos de 2013, de IEEE Sensors 2018 ni de Environmental Research 2018.
- No encontre si alguno de estos trabajos publica codigo. No vi ningun repositorio.
- No consulte la lista completa de publicaciones de Harrou (KAUST); pueden faltar variantes (kernel PCA, MSPCA) sobre la misma red.

## 2. Control de calidad por mediana de vecinas, prediccion espacial o kriging en operacion (Air Normand PM10 y similares) y su desempeño

### Takeaway
El trabajo canonico en operacion es el de Bobbia y coautores (2015) para el PM10 de Normandia: compara cada medicion con
una prediccion espacial robusta tipo jackknife, sea la mediana ponderada de las vecinas mas cercanas o el kriging de
incrementos, y Air Normand lo tiene implementado en su control de calidad. El otro antecedente muy cercano para ozono es
el de Miskell y coautores (2016): compara 72 h moviles contra estaciones proxy y apunta a derivas de ±30 % en
pendiente o ±5 ppb en offset, magnitudes casi identicas a las de nuestro protocolo.

### Cited Findings
- **Bobbia, Misiti, Misiti, Poggi y Portier (2015), "Spatial outlier detection in the PM10 monitoring network of Normandy (France)", Atmospheric Pollution Research 6(3):476-483, doi:10.5094/APR.2015.053** [solo resumen]:
  - Datos: PM10 horario de 22 estaciones (urbanas de fondo o rurales) de Baja y Alta Normandia y regiones vecinas, con resultados numericos del 1 de enero al 31 de mayo de 2013 — [Crossref/S2](https://doi.org/10.5094/APR.2015.053); [AGRIS](https://agris.fao.org/search/en/records/65df381e0f3e94b9e5d6284b).
  - Metodo: enfoque tipo jackknife que compara la medicion real con una prediccion espacial robusta. Hay dos predicciones: (a) la mediana de las concentraciones ponderadas de las estaciones vecinas mas cercanas (no estacionaria) y (b) el kriging de incrementos (estacionario), en lugar de las pseudo-innovaciones usuales — [S2 abstract](https://doi.org/10.5094/APR.2015.053).
  - Operacion: los dos metodos estan totalmente implementados por Air Normand en su proceso de control de calidad de las mediciones — [S2 abstract](https://doi.org/10.5094/APR.2015.053).
  - Umbral: segun el resumen del buscador, sale de la distribucion temporal de los residuos de prediccion. No hay metricas de deteccion con inyeccion sintetica en el resumen [solo resumen] — [AGRIS](https://agris.fao.org/search/en/records/65df381e0f3e94b9e5d6284b).
  - Existe una presentacion previa en congreso (2014), con titulo "...air quality monitoring network of Normandy" — [Aisberg UniBG](https://aisberg.unibg.it/handle/10446/31665).
- **Miskell, Salmond, Alavi-Shoshtari, Bart, Ainslie, Grange et al. (2016), "Data verification tools for minimizing management costs of dense air-quality monitoring networks", Environmental Science & Technology 50(2):835-846, doi:10.1021/acs.est.5b04421** [verificado, resumen de Europe PMC]:
  - Red hibrida de instrumentos de ozono (bajo costo y referencia) en el Lower Fraser Valley (Canada).
  - Metodos estadisticos simples, sin grandes datos de entrenamiento: comparacion movil de 72 h de los datos horarios del instrumento contra "proxies" (estaciones elegidas por criterios de uso de suelo).
  - Objetivo explicito: detectar derivas de calibracion de mas de ±30 % en pendiente o ±5 ppb en offset, en pocos dias — [Europe PMC / Crossref](https://doi.org/10.1021/acs.est.5b04421).
- Antecedentes de vecindario que cita STC-RAAD: Adam, Janeja y Atluri (2004, ACM SAC, deteccion de anomalias por vecindario en datos espacio-temporales) y Dereszynski y Dietterich (2011, ACM TOSN 8(1), modelos espacio-temporales para anomalias en campañas de monitoreo ambiental) [solo referencia bibliografica; DOI no verificado] — [STC-RAAD, preprint UPC](https://upcommons.upc.edu/bitstreams/7a81c84b-ed5e-4070-9ed9-2de7ebba5312/download).
- Ottosen y Kumar (2019), "Outlier detection and gap filling methodologies for low-cost air quality measurements", Environ. Sci.: Processes & Impacts 21(4):701-713 [solo referencia en PARAAD; DOI no verificado] — [PARAAD preprint](https://upcommons.upc.edu/bitstreams/b277ed89-9983-4698-bd95-c74c31b199c9/download).
- Proyecto ECMWF Code for Earth "DAAQS" (Detect Anomaly in Air Quality Station): agrupamiento para dar puntajes de confiabilidad y representatividad por estacion, con codigo en github.com/esowc/DAAQS. La pagina no dice que datos usa ni da resultados, y el año que muestra (2026) es dudoso [NO VERIFICADO] — [ECMWF Code for Earth](https://codeforearth.ecmwf.int/project/detect-anomaly-in-air-quality-station-daaqs/).

### Inferences
- La "regla de vecinas" del proyecto (R0-R3, con mediana de 14 dias y dominancia en el vecindario, revisiones 8 y 12) ya es, en esencia, el metodo de mediana ponderada de vecinas de Bobbia et al. 2015. Conviene citarlo como antecedente operativo directo y decir que R3 es una variante de esa familia. Agregar el kriging de incrementos daria un segundo comparador "operativo" casi sin entrenamiento.
- Miskell et al. 2016 es el antecedente mas comparable en magnitudes: ±30 % en pendiente equivale a d=20-50 % del protocolo (x*(1+d) es justamente una falla de pendiente o ganancia), y su ventana de 72 h se parece a los episodios de 1-7 dias. Implementar su prueba de 72 h contra proxies (vecinas de RAMA) con umbral calibrado en 2023 seria un comparador justo, no supervisado y facil de explicar al asesor.
- Ninguno de los dos trabajos informa F1 ni recall con inyeccion controlada en el resumen, asi que no hay numeros publicados contra los cuales comparar directamente. Habria que reimplementarlos.

### Gaps
- No pude abrir el PDF de Bobbia et al. 2015 (ScienceDirect devolvio una pagina HTML y UniBG dio 403), asi que no tengo sus tasas de deteccion, su numero de valores atipicos señalados ni el detalle de sus cuantiles de umbral.
- No encontre otras redes oficiales (AURN del Reino Unido, AirNow de EE. UU., redes alemanas) con un metodo de control de calidad espacial publicado y su desempeño. No sale en esta busqueda; queda abierto.
- No pude leer la revision de Kim y Moon (2025, Atmosphere 16:1136, doi:10.3390/atmos16101136; MDPI dio 403), que dedica una seccion a marcos espacio-temporales de control de calidad y podria listar mas metodos operativos — [S2 abstract](https://doi.org/10.3390/atmos16101136).

## 3. Aprendizaje profundo (LSTM/GRU por residuo de pronostico, autoencoders, GNN, transformers) aplicado a calidad del aire: cuales inyectan anomalias sinteticas y cuales usan redes multiestacion

### Takeaway
Los trabajos verdaderamente multiestacion y con inyeccion sintetica controlada son pocos: STC-RAAD y PARAAD (UPC,
Barcelona), Lin et al. 2022 (Con-GAE) y Masmoudi et al. 2024 (A3T-GCN por pronostico). Wei et al. y Park et al. son
de un solo sensor interior. TranAD y AnomalyBERT solo aparecen como lineas base genericas: no encontre aplicaciones
publicadas a redes de estaciones de calidad del aire. Ademas, los umbrales de STC-RAAD, PARAAD y Masmoudi se ajustan
maximizando exactitud o el ROC sobre datos con etiqueta. Eso es menos estricto que el V4, que calibra en 2023 limpio
con una tasa de falsas alarmas fija.

### Cited Findings
**Autoencoders recurrentes con vecinas (UPC):**
- **Allka, Ferrer-Cid, Barcelo-Ordinas y Garcia-Vidal (2024), "Leveraging spatiotemporal correlations with recurrent autoencoders for sensor anomaly detection" (STC-RAAD), IEEE Internet of Things Journal 11(19):31144-31152, doi:10.1109/JIOT.2024.3416525** [verificado, preprint completo]:
  - Datos D.1: 8 estaciones de referencia de Barcelona con O3 (enero 2014 a diciembre 2019) y NO2 (junio 2014 a diciembre 2019), horarios.
  - Datos D.2: 30 sensores de bajo costo de O3 en Taiwan (junio 2020 a octubre 2022).
  - Division: 70 % entrenamiento y 30 % prueba, con bloques de K=24 h.
  - Vecinas: aprendidas con un grafo (GSP, laplaciano de Dong et al.), de 1 a 4 vecinas.
  - Falla de sesgo: se perturba el 25 % de los bloques de prueba sumando µ~|N(0,σ²)| en unidades estandarizadas, con σ≥1 (σ=2 en las tablas principales).
  - Falla de deriva: g(t)=√(δ0+δ1·t), con δ0=0.01 y δ1=0.005, durante 5 a 25 dias.
  - Metricas: TPR y precision.
  - Umbral: se elige en una ventana de W=30 bloques "maximizando la exactitud y minimizando la FPR", es decir, con informacion de la etiqueta.
  - Resultado: con σ=2 en O3 D.1, STC-RAAD da TPR de 0.82 a 0.96 y precision de 0.85 a 0.91 en las 8 estaciones. Las lineas base (osPCA, OCSVM, ECOD, LUNAR, Transformer, BiLSTM) quedan en TPR de 0.46 a 0.77.
  - Con deriva de 5 a 10 dias, STC-RAAD detecta alrededor de 72-86 % con precision de 30-51 %.
  - Fuente: [preprint UPC](https://upcommons.upc.edu/bitstreams/7a81c84b-ed5e-4070-9ed9-2de7ebba5312/download); [ficha UPCommons](https://upcommons.upc.edu/entities/publication/48877315-e692-4af4-b083-d4914ed69b7a).
- **PARAAD (Allka et al. 2024, IEEE TNSE 11(6):6372-6381, doi:10.1109/TNSE.2024.3454459)** [verificado, preprint completo; ya conocido por el tesista]. Datos que importan para comparar con el V4:
  - D.1 es la misma red de 8 estaciones de Barcelona (2014-2019); D.2 es sintetica (hasta 50 nodos).
  - Division: 90 % entrenamiento y 10 % prueba.
  - Sesgo: β~|N(0,σ²)|, σ≥1, en el 30 % de los bloques de 24 h.
  - Deriva: g(t)=√(δ0+δ1·t) con δ1 de 0.005, 0.007 o 0.01, de 5 a 30 dias, en el 10 % de los sensores.
  - Umbral: elegido entre candidatos como el que maximiza la exactitud.
  - Codigo: el preprint dice "URL will be given if the paper is accepted" (no vi repositorio).
  - Fuente: [preprint UPC](https://upcommons.upc.edu/bitstreams/b277ed89-9983-4698-bd95-c74c31b199c9/download).
- **Allka X., tesis doctoral UPC, "Enhancing data quality in IoT monitoring sensor networks", doi:10.5821/dissertation-2117-457522** [solo resumen]: reune ESOD (valores atipicos en el borde), STC-RAAD y PARAAD — [UPCommons](https://upcommons.upc.edu/bitstreams/01ee1d8f-7889-420b-8b98-cf10c8e911e7/download).

**GNN:**
- **Lin, Wang, Guo y Mei (2022), "A deep learning approach using graph neural networks for anomaly detection in air quality data considering spatiotemporal correlations", IEEE Access 10:94074-94088, doi:10.1109/ACCESS.2022.3204284** [solo resumen]:
  - Construye un grafo espacio-temporal: una matriz de adyacencia ponderada para lo espacial y una de rasgos para lo temporal. Los cambios en los nodos se traducen en cambios en los pesos de las aristas.
  - Usa Con-GAE (Context augmented Graph Autoencoder).
  - Se evalua en conjuntos de prueba sinteticos construidos a partir de datos reales.
  - Fuente: [S2/Crossref](https://doi.org/10.1109/ACCESS.2022.3204284).
- Con-GAE proviene de trafico: **Hu, Qu y Work (2022), "Detecting extreme traffic events via a context augmented graph autoencoder", ACM TIST 13:1-23, doi:10.1145/3539735** [solo ficha] — [Crossref](https://doi.org/10.1145/3539735).
- **Masmoudi, Garnier, Savard, Itier, Sauvage y Bulot (2024), "Enhanced sensor environment graph based deep learning approach for air quality anomaly detection", EUSIPCO 2024, pp. 2252-2256, doi:10.23919/EUSIPCO63174.2024.10715088** [verificado, texto completo en HAL]:
  - Enhanced-A3T-GCN (atencion + GRU + GCN) que pronostica PM2.5. El grafo incluye el "entorno" de cada sensor.
  - Datos: 24 de 100 sensores NextPM3 cerca de Aix-en-Provence, cada 15 min, en 2023.
  - Detecta por distancia de Mahalanobis del error de pronostico.
  - Anomalias inyectadas: 100 valores consecutivos sumados, con distribucion Poisson(λ=8), locales (un sensor) o globales (un grupo).
  - Resultado: AUC 0.98 (local) y 0.97 (global).
  - Umbral: el "optimo" de la curva ROC, es decir, con etiqueta.
  - Fuente: [HAL hal-04751177](https://imt-nord-europe.hal.science/hal-04751177v1/document).
- Revision de metodos sobre grafos: **Ferrer-Cid, Barcelo-Ordinas y Garcia-Vidal (2025), "A review of graph-powered data quality applications for IoT monitoring sensor networks", J. Network and Computer Applications 236:104116, doi:10.1016/j.jnca.2025.104116** [solo resumen]: cubre GSP y GNN para imputacion, deteccion de valores atipicos y sensado virtual — [Crossref/S2](https://doi.org/10.1016/j.jnca.2025.104116).
- GDN (Deng y Hooi 2021, AAAI 35(5):4027-4035, doi:10.1609/aaai.v35i5.16523) es el detector GNN generico por pronostico mas usado en series multivariadas. No encontre una aplicacion publicada a redes de calidad del aire [ficha Crossref] — [DOI](https://doi.org/10.1609/aaai.v35i5.16523).

**Autoencoders de un solo sensor (interiores):**
- **Wei, Jang-Jaccard, Xu, Sabrina, Camtepe y Boulic (2023), "LSTM-autoencoder-based anomaly detection for indoor air quality time-series data", IEEE Sensors J. 23(4):3787-3800, doi:10.1109/JSEN.2022.3230361** [solo resumen]: LSTM-AE sobre CO2 de escuelas de Dunedin (Nueva Zelanda), con umbral por perdida de reconstruccion. Informa 99.50 % de exactitud. Es de un solo sensor, sin vecinas — [S2](https://doi.org/10.1109/JSEN.2022.3230361); [arXiv 2204.06701](https://arxiv.org/pdf/2204.06701).
- **Park, Seo y Cho (2023), "Unsupervised outlier detection for time-series data of indoor air quality using LSTM autoencoder with ensemble method", Journal of Big Data 10, doi:10.1186/s40537-023-00746-z** [solo resumen]: LSTM-AE mas un detector sobre los rasgos latentes, combinados en un ensamble, con pruebas de laboratorio. Es interior y de un solo sensor — [S2](https://doi.org/10.1186/s40537-023-00746-z).

**Transformers:**
- **TranAD: Tuli, Casale y Jennings (2022), PVLDB 15(6):1201-1214, doi:10.14778/3514061.3514067** [ficha]. Es un detector generico multivariado y se evaluo en seis bancos publicos, ninguno de calidad del aire — [Crossref](https://doi.org/10.14778/3514061.3514067); [arXiv 2201.07284](https://arxiv.org/pdf/2201.07284v4).
- AnomalyBERT (Jeong et al.) solo aparece citado en la revision del estado del arte de PARAAD. No encontre aplicacion a calidad del aire ni verifique su referencia completa — [PARAAD preprint](https://upcommons.upc.edu/bitstreams/b277ed89-9983-4698-bd95-c74c31b199c9/download).
- **Wang, Li, Zhi, Liu, He y Di (2024), "Deep smooth random sampling and association attention for air quality anomaly detection" (DSRS-AAT), Mathematics 12(13):2048, doi:10.3390/math12132048** [solo resumen]: transformer con atencion de asociacion (tipo Anomaly Transformer). Agrupa estaciones por entorno geografico, con 95 estaciones de Haikou. Lineas base: OmniAnomaly, THOC — [Crossref](https://doi.org/10.3390/math12132048).
- En STC-RAAD el "Transformer" de reconstruccion con dos cabezas y correlacion espacial es una linea base y queda por debajo (TPR de 0.51 a 0.67 en O3 D.1 con σ=2) — [preprint UPC](https://upcommons.upc.edu/bitstreams/7a81c84b-ed5e-4070-9ed9-2de7ebba5312/download).

### Inferences
- Para comparar contra el V4 con justicia (no supervisado contra no supervisado, misma unidad y mismo umbral), los candidatos de aprendizaje profundo con mas sentido son:
  - (a) **STC-RAAD**, el hermano por estacion de PARAAD, con BiLSTM-AE y 1 a 4 vecinas. Ya hay infraestructura de PARAAD en el repositorio (revisiones 20 y 20b), asi que adaptarlo seria barato.
  - (b) **Un detector GNN por pronostico** tipo GDN o A3T-GCN, que es el analogo grafico directo del V4 (pronostico mas residuo).
  - (c) **Un LSTM-AE de una sola estacion** (Wei et al.), como ablacion de "sin vecinas".
- Ninguno de estos trabajos usa una anomalia multiplicativa x*(1+d) por episodios de dias: todos usan sesgo aditivo en unidades estandarizadas o deriva √t. El sesgo σ=2 de STC-RAAD y PARAAD equivale a unas dos desviaciones estandar del ozono, una magnitud grande, comparable o superior a nuestro d=100 %. Sus resultados altos (TPR >0.8) no deben contrastarse con nuestros d=20 % o d=5 %.
- La diferencia metodologica mas defendible frente a STC-RAAD, PARAAD y Masmoudi es el umbral: ellos lo ajustan con etiquetas (maximo de exactitud o el optimo del ROC); el V4 lo fija con una tasa de falsas alarmas en un año limpio. Al reimplementarlos hay que imponerles la regla del V4 (calibracion en 2023 limpio, falsas alarmas fijas por hora de red); si no, la comparacion los favorece.

### Gaps
- No pude leer el texto completo de Lin et al. 2022 (IEEE Xplore no entrega el PDF por esta via), asi que no se la ciudad ni el numero de estaciones, ni el tipo y magnitud de las anomalias, ni las metricas o si hay codigo.
- No confirme si el codigo de PARAAD o STC-RAAD es publico. El preprint de PARAAD promete una URL que no vi.
- No encontre ningun trabajo publicado que aplique TranAD o AnomalyBERT a redes de estaciones de calidad del aire con inyeccion controlada.
- No encontre trabajos de LSTM o GRU por residuo de pronostico desde vecinas para ozono en redes de referencia (el analogo exacto del V4) con evaluacion por inyeccion y falsas alarmas fijas. Puede existir en revistas de atmosfera; la busqueda no lo saco.

## 4. Trabajos que citan PARAAD (2024-2026) y proponen metodos o comparaciones nuevas

### Takeaway
Segun Semantic Scholar (consulta del 2026-10-31), PARAAD tiene 8 citas y STC-RAAD 6. Ninguna es un metodo nuevo de
calidad del aire de red que se compare contra PARAAD: son revisiones, aplicaciones a otros dominios (6G, estructuras,
blockchain) o sistemas de calidad del aire interior. Hasta donde llega esta busqueda, no hay un "sucesor" publicado que
compita con PARAAD en redes de estaciones.

### Cited Findings
- Citas de PARAAD (doi:10.1109/TNSE.2024.3454459), segun la API de Semantic Scholar — [S2 API](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/TNSE.2024.3454459/citations?fields=title,authors,year,externalIds,venue&limit=100):
  - Kim y Moon (2025), "Machine learning-based quality control for low-cost air quality monitoring: a comprehensive review of the past decade", Atmosphere 16:1136, doi:10.3390/atmos16101136. Es una revision, no un metodo.
  - Rajule et al. (2025), "Hybrid ensemble-LSTM framework for indoor air quality forecasting using multi-sensor data fusion and anomaly detection", FusionX Global, doi:10.5220/0014623400004852. Es interior.
  - Chaidee et al. (2026), "Design and implementation of a low-cost IoT-based indoor air quality monitoring system", ECTI DAMT & NCON 2026, doi:10.1109/ECTIDAMTNCON67592.2026.11460041. Es interior.
  - Otras citas fuera de dominio: Ameur et al. 2025 (deriva de modelos en 6G, doi:10.1109/TMLCN.2025.3576727); An et al. 2026 (tubos de acero rellenos, doi:10.1016/j.aei.2025.103924); Küçük y Ertam 2025 (VAE en blockchain, doi:10.1109/ISCTrkiye68593.2025.11224810); Sobran et al. 2025 (sistema de tres tanques, doi:10.54554/ijeeas.2025.8.02.018); Wang et al. 2026 (LSTM en sistemas aereos, doi:10.3390/electronics15153438).
- Citas de STC-RAAD (doi:10.1109/JIOT.2024.3416525), segun la misma API — [S2 API](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/JIOT.2024.3416525/citations?fields=title,authors,year,externalIds,venue&limit=100):
  - Ferrer-Cid et al. (2025), revision en JNCA, doi:10.1016/j.jnca.2025.104116. Es del mismo grupo.
  - Xiang et al. (2026), correccion colaborativa en calidad del agua de drenajes, IEEE Sensors J., doi:10.1109/JSEN.2025.3641560.
  - Qi et al. (2026), sensores de incendio con completado de bajo rango y RV-GAN, Informatica, doi:10.31449/inf.v50i9.11360.
  - Zeng et al. (2026), CADiS (IIoT), IEEE IoT J., doi:10.1109/JIOT.2026.3663198.
  - Ademas, dos trabajos de IoT o hidrogeno no relacionados.

### Inferences
- Para la tesis, esto deja a PARAAD y STC-RAAD como el estado del arte publicado mas reciente en autoencoders de red para estaciones de calidad del aire. Es razonable decir que "a la fecha de la busqueda no encontramos trabajos posteriores que comparen contra PARAAD en redes de referencia", con la fecha y la fuente (Semantic Scholar).
- Kim y Moon 2025 es la revision mas util para completar el mapa de metodos de control de calidad, si se consigue el texto.

### Gaps
- No consulte la lista de citas de Google Scholar (suele tener mas citas que Semantic Scholar). Es posible que existan tesis, preprints o congresos que la comparen y no esten indexados en S2.
- No lei Kim y Moon 2025 (MDPI devolvio 403).

## 5. Ficha comparativa: datos, tipo y magnitud de anomalia, metricas, control de falsas alarmas, codigo y comparabilidad con el V4

### Takeaway
Por comparabilidad con el V4 (pronostico o reconstruccion no supervisada, red de referencia, ozono, umbral calibrado
sin etiquetas), el orden es: (1) PCA-MEWMA/GLR de Harrou, el unico con umbral por probabilidad de falsa alarma fijada
en datos limpios y en una red de ozono; (2) STC-RAAD/PARAAD, con red de referencia de ozono en Barcelona pero umbral
con etiquetas; (3) mediana de vecinas o kriging de Bobbia y prueba de 72 h de Miskell, los dos operativos y sin
entrenamiento; (4) los GNN (Lin, Masmoudi) y los transformers (DSRS-AAT), menos comparables por su tipo de dato
(sensores de bajo costo o PM2.5) y su umbral.

### Cited Findings
| Trabajo | Datos | Anomalia y magnitud | Metricas | Control de falsas alarmas | Codigo | Comparabilidad con el V4 |
|---|---|---|---|---|---|---|
| Harrou et al. 2016 PSEP, PCA-MEWMA ([HAL](https://hal.science/hal-02292084v1/document)) | Air Normand, 7 estaciones de O3, cada 15 min, 2006 | Episodios reales declarados por expertos (24), sin inyeccion | Detectados 17/24 (PCA-Q 6/24, T² 2/24) | α=0.005, h=9.65, en datos limpios | No visto | Alta en red, pronostico/residuo y umbral; baja en evaluacion (sin inyeccion ni falsas alarmas informadas) |
| Harrou et al. 2013 CIDM, PCA-GLR ([HBKU](https://elmi.hbku.edu.qa/en/publications/detecting-abnormal-ozone-levels-using-pca-based-glr-hypothesis-te/)) | O3, Alta Normandia | Falla de sensor y episodio (magnitud NO VERIFICADA) | Menos falsas alarmas que el PCA (cualitativo) | GLR | No visto | Alta en concepto; faltan datos |
| Bobbia et al. 2015 APR ([DOI](https://doi.org/10.5094/APR.2015.053)) | 22 estaciones de PM10, ene-may 2013 | Valores atipicos espaciales reales | No visto | Umbral por distribucion de residuos (NO VERIFICADO en detalle) | No visto (operativo en Air Normand) | Equivale a la regla de vecinas R0-R3 |
| Miskell et al. 2016 ES&T ([DOI](https://doi.org/10.1021/acs.est.5b04421)) | Red hibrida de O3, Lower Fraser Valley | Deriva de ±30 % en pendiente o ±5 ppb en offset | Deteccion en pocos dias | Pruebas estadisticas en 72 h contra proxies | No visto | Muy alta en magnitudes (multiplicativa); la red mezcla bajo costo |
| STC-RAAD 2024 IoT-J ([preprint](https://upcommons.upc.edu/bitstreams/7a81c84b-ed5e-4070-9ed9-2de7ebba5312/download)) | Barcelona, 8 estaciones de referencia (O3/NO2, 2014-2019); Taiwan, 30 sensores de bajo costo de O3 | Sesgo |N(0,σ²)| estandarizado, σ=2, en 25 % de bloques; deriva √(δ0+δ1 t), 5-25 dias | TPR, precision | Umbral que maximiza la exactitud (con etiqueta) | No visto | Alta en arquitectura y datos; umbral no comparable |
| PARAAD 2024 TNSE ([preprint](https://upcommons.upc.edu/bitstreams/b277ed89-9983-4698-bd95-c74c31b199c9/download)) | Barcelona, 8 estaciones de referencia (2014-2019); red sintetica de 20-50 nodos | Sesgo σ≥1 en 30 % de bloques; deriva lenta, media o rapida, 5-30 dias | TPR, precision, tasa de localizacion | Umbral que maximiza la exactitud | "URL si se acepta" | Ya implementado (revisiones 20 y 20b) |
| Lin et al. 2022 IEEE Access, Con-GAE ([DOI](https://doi.org/10.1109/ACCESS.2022.3204284)) | Datos reales de calidad del aire (detalle NO VERIFICADO) | Sinteticas (detalle NO VERIFICADO) | No visto | No visto | No visto | Media: GNN de reconstruccion por grafo |
| Masmoudi et al. 2024 EUSIPCO ([HAL](https://imt-nord-europe.hal.science/hal-04751177v1/document)) | 24 sensores de PM2.5 de bajo costo, Aix-en-Provence, 2023 | 100 pasos + Poisson(λ=8), local o global | AUC 0.98 / 0.97 | Umbral optimo del ROC (con etiqueta) | No visto | Media: pronostico por GNN con residuo, igual que el V4; PM2.5 de bajo costo |
| Wang et al. 2024 Mathematics, DSRS-AAT ([DOI](https://doi.org/10.3390/math12132048)) | 95 estaciones de Haikou | No visto | No visto | No visto | No visto | Baja a media |
| Wei et al. 2023 / Park et al. 2023 ([DOI](https://doi.org/10.1109/JSEN.2022.3230361), [DOI](https://doi.org/10.1186/s40537-023-00746-z)) | CO2 interior / interior de laboratorio | No visto | Exactitud 99.5 % (Wei) | Umbral por reconstruccion | arXiv (Wei) | Baja: sin vecinas, solo como ablacion |
| Xie, Qian y Qiu 2024 AOAS ([DOI](https://doi.org/10.1214/23-AOAS1803)) | O3 de Houston-Galveston-Brazoria, con meteorologia | No visto | No visto | Carta de control con distribucion en control que cambia | No visto | Media a alta en lo conceptual (perfil adaptativo) |

### Inferences
- Comparadores recomendados como "peras con peras" no supervisados, en orden de costo y beneficio:
  1. **PCA-Q/MEWMA (Harrou)**: barato, citable y con umbral por probabilidad de falsa alarma, igual que el V4.
  2. **Prueba de 72 h contra vecinas (Miskell)**: sus magnitudes coinciden con las del protocolo.
  3. **Kriging de incrementos (Bobbia)**: complementa a R3.
  4. **STC-RAAD**: reusa la infraestructura de PARAAD.
- En todos se impone la regla del V4: ajuste 2020-2022, umbral en 2023 limpio con falsas alarmas fijas por hora de red, prueba en 2024 y el mismo plan pareado de episodios.
- El argumento de originalidad del protocolo frente a la literatura tiene tres partes: (a) anomalia multiplicativa por episodios de dias completos con magnitud graduada d=5-100 %; (b) umbral calibrado sin etiquetas con falsas alarmas fijas; (c) evaluacion en una red de referencia grande (31 estaciones) y varios años. Ninguno de los trabajos revisados reune las tres.
- Cualquier cifra publicada de esos trabajos (por ejemplo, TPR >0.8 de PARAAD o STC-RAAD) no es comparable numericamente con nuestras F1, por la diferencia de magnitud (σ=2 estandarizado), de tipo de falla (aditiva) y de umbral (con etiqueta). En la tesis se deben comparar solo los metodos reimplementados bajo el protocolo.

### Gaps
- Faltan las magnitudes exactas de Harrou 2013 (el "~20 %"), los detalles de Lin 2022 y las metricas de Bobbia 2015. En los tres casos se necesita el PDF del editor.
- No verifique la disponibilidad de codigo de ninguno de los metodos de red. Solo vi la promesa del preprint de PARAAD y el repositorio del proyecto DAAQS.
- No se reviso Google Scholar ni la lista de publicaciones de Harrou en KAUST.
