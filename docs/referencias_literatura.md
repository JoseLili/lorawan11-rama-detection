# Referencias de la literatura (parte 2)

Búsqueda del 2026-10-23, antes de la revisión 10. Para cada trabajo: qué es, por qué nos importa y
qué leer primero.

- **El BibTeX** está en `docs/referencias.bib`.
- **«Verificado»:** el dato se leyó en la fuente (texto completo o registro oficial).
- **«Por verificar»:** salió de un resumen o de un buscador. Confírmalo antes de citarlo.
- **Los PDFs no van a git:** bájalos de los enlaces.

## 1. Lo más parecido a nuestro problema

| Trabajo | Por qué importa | Qué leer primero | Estado |
|---|---|---|---|
| **PARAAD.** Allka, Ferrer-Cid, Barceló-Ordinas y García-Vidal (2024). *Pattern-Based Attention Recurrent Autoencoder for Anomaly Detection in Air Quality Sensor Networks*. IEEE Trans. Network Science and Engineering 11(6), 6372–6381. doi:10.1109/TNSE.2024.3454459. [UPCommons, con texto completo](https://upcommons.upc.edu/entities/publication/d4d25d74-89d7-4e15-8c8e-41bd923bafa2) | O3 de 8 estaciones de Barcelona, anomalías sintéticas de sesgo y deriva, modelo no supervisado **por bloques de un día**. Es el mejor punto de comparación | §V-A y V-D (cómo meten el sesgo: β ~ \|N(0, σ²)\| desviaciones típicas, σ = 2), Tabla I (TPR 0.81, precisión 0.84) y Tabla II (bloques de 1 h contra 24 h) | Verificado (texto completo) |
| **STC-RAAD.** Allka, Ferrer-Cid, Barceló-Ordinas y García-Vidal (2024). *Leveraging Spatiotemporal Correlations With Recurrent Autoencoders for Sensor Anomaly Detection*. IEEE Internet of Things Journal 11(19). doi:10.1109/JIOT.2024.3416525. [UPCommons](https://upcommons.upc.edu/entities/publication/48877315-e692-4af4-b083-d4914ed69b7a) | Usa explícitamente las **estaciones vecinas** para reconstruir cada sensor de calidad del aire | Cómo eligen y usan a las vecinas, y el tamaño de las anomalías | Resumen verificado; páginas por verificar |
| **Dereszynski y Dietterich (2011).** *Spatiotemporal models for data-anomaly detection in dynamic environmental monitoring campaigns*. ACM Trans. Sensor Networks. [Preprint](https://web.engr.oregonstate.edu/~tgd/publications/dereszynski-dietterich-spatiotemporal-models-for-data-anomaly-detection-in-dynamic-environmental-monitoring-campaigns-tosn2010preprint.pdf) | Clásico: modelo bayesiano espacio-temporal. Combinar vecinas y tiempo supera a usar sólo uno de los dos | Introducción y comparación espacial contra temporal | Volumen, número y páginas por verificar |

## 2. Control de calidad con vecinas (meteorología)

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Båserud et al. (2020).** *TITAN automatic spatial quality control of meteorological in-situ observations*. Advances in Science and Research 17, 153–163. [Copernicus](https://asr.copernicus.org/articles/17/153/2020/) | El *buddy check* (comparar con las vecinas) es nuestra regla de vecinas; el *spatial consistency test* es la versión con interpolación espacial | Revista y páginas verificadas; lista de autores por verificar |
| **Lussana, Uboldi y Salvati (2010).** *A spatial consistency test for surface observations from mesoscale meteorological networks*. Quarterly Journal of the Royal Meteorological Society 136. | Origen del *spatial consistency test*: valor esperado de cada estación a partir de sus vecinas | Título, volumen y páginas por verificar |

## 3. Cómo evaluar sin engañarse

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Kim, Choi, Choi, Lee y Yoon (2022).** *Towards a Rigorous Evaluation of Time-Series Anomaly Detection*. AAAI 36(7), 7194–7201. doi:10.1609/aaai.v36i7.20680. [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/20680) · [arXiv](https://arxiv.org/abs/2109.05257) | Contar un evento como detectado si alguna alarma cae dentro infla el F1: un puntaje al azar saca 0.969 en SWaT. Respalda nuestro «sin ataque» | Verificado (registro) |
| **Saito y Rehmsmeier (2015).** *The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets*. PLoS ONE 10(3): e0118432. | Por qué el PR-AUC con clases desbalanceadas | Por verificar (de memoria de Claude) |
| **Chicco y Jurman (2020).** *The advantages of the Matthews correlation coefficient (MCC) over F1 score and accuracy in binary classification evaluation*. BMC Genomics 21: 6. | Por qué el MCC | Por verificar (de memoria de Claude) |
| **Youden (1950).** *Index for rating diagnostic tests*. Cancer 3(1), 32–35. | Índice J = TPR − FPR, el pariente de nuestra «señal» | Por verificar (de memoria de Claude) |

## 4. Modelos que aprenden la red de sensores

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Deng y Hooi (2021).** *Graph Neural Network-Based Anomaly Detection in Multivariate Time Series* (GDN). AAAI 35(5), 4027–4035. doi:10.1609/aaai.v35i5.16523. [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/16523) | Aprende qué sensores se parecen entre sí, en lugar de fijar las vecinas por distancia; ataques a sensores de una planta de agua (SWaT) | Verificado (registro) |

## 5. Ataques chicos y sostenidos

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Page (1954).** *Continuous inspection schemes*. Biometrika 41(1/2), 100–115. | Origen del CUSUM: acumula evidencia para detectar cambios pequeños pero persistentes | Por verificar (de memoria de Claude) |
| *Quickest Detection over Sensor Networks with Unknown Post-Change Distribution*. [arXiv:2012.13027](https://arxiv.org/pdf/2012.13027) | CUSUM en redes de sensores cuando sólo cambian unos pocos sensores | Autores y año por verificar |

## 6. Inyección de datos falsos en sensores

| Trabajo | Por qué importa | Estado |
|---|---|---|
| *A Framework for Detecting False Data Injection Attacks in Large-Scale Wireless Sensor Networks*. Sensors 24(5), 1643 (2024). [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10935136/) | Agrupa sensores por correlación espacio-temporal y vota por mayoría dentro de cada grupo | Autores por verificar |

## 7. Referencia robusta (opción C de la revisión 10)

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Rousseeuw y Croux (1993).** *Alternatives to the Median Absolute Deviation*. Journal of the American Statistical Association 88(424), 1273–1283. | La mediana y la MAD resisten datos contaminados. Es el argumento para cambiar el promedio de 14 días por la mediana | Por verificar (de memoria de Claude) |
| *Robustness of Anomaly Detection Models for Industrial Control Systems under Training-Time Data Contamination*. [arXiv:2608.23547](https://arxiv.org/pdf/2608.23547) | Datos contaminados cambian el orden de los detectores | Autores y año por verificar |

## 8. Manipulación real de datos de calidad del aire

| Trabajo | Por qué importa | Estado |
|---|---|---|
| **Turiel y Kaufmann** (PLOS ONE). Comparan el PM2.5 reportado por gobiernos locales chinos con el de la embajada de EE. UU. [Nota de prensa](https://airqualitynews.com/fuels/air-pollution-in-china-might-be-under-reported-study-suggests) | Según el resumen, lo local se reportaba **más bajo** justo con contaminación alta. El ataque realista sería bajar la lectura en días altos, la dirección que peor detectamos | Título exacto, año y volumen por verificar: buscar el artículo original |
| **Stoerk (2016).** *Statistical corruption in Beijing's air quality data has likely ended in 2012*. Atmospheric Environment. [Working paper LSE](https://www.lse.ac.uk/GranthamInstitute/wp-content/uploads/2015/05/Working-Paper-194-Stoerk.pdf) | Otro análisis estadístico de posible manipulación de datos de Pekín | Título y revista por verificar |
