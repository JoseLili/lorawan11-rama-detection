# Auditoría de datos de Barcelona para la comparación con PARAAD

Fecha de sesión: 2026-10-28. No se entrenó ningún detector ni se calcularon
métricas de detección sobre estos datos.

## Resultado y decisión del tesista

Se descargaron las series públicas O3 de 2014–2019 de las 14 estaciones del
catálogo ubicadas en municipios de la [AMB administrativa](https://www.amb.cat/en/web/area-metropolitana/municipis-metropolitans).
El tesista eligió **continuar con las 13 estaciones con cobertura de ajuste**,
como comparación controlada con datos de la misma fuente. No se afirma que
sean las ocho estaciones exactas de PARAAD.

La elegibilidad provisional se calculó exclusivamente con 2014–2015:
al menos 2,000 horas y seis meses con observaciones. Trece estaciones tienen
datos en los 24 meses, con cobertura entre 95.20% y 99.08%. Observatori Fabra
no tiene observaciones de ajuste y comienza en 2018: queda fuera por ese
criterio, sin utilizar rendimiento de prueba para excluirla.

| Código EOI | Estación | Cobertura 2014–2015 |
|---|---|---:|
| 08015021 | Badalona | 99.08% |
| 08019043 | Barcelona (Eixample) | 97.53% |
| 08019044 | Barcelona (Gràcia - Sant Gervasi) | 96.83% |
| 08019050 | Barcelona (Ciutadella) | 96.92% |
| 08019054 | Barcelona (Parc Vall Hebron) | 96.44% |
| 08019057 | Barcelona (Palau Reial) | 95.56% |
| 08089005 | Gavà | 95.20% |
| 08125002 | Montcada i Reixac | 98.64% |
| 08169009 | El Prat de Llobregat (Sagnier) | 96.40% |
| 08194008 | Sant Adrià de Besòs | 96.39% |
| 08205002 | Sant Cugat del Vallès | 98.68% |
| 08263001 | Sant Vicenç dels Horts (Ribot) | 98.37% |
| 08301004 | Viladecans - Atrium | 96.65% |

El orden queda fijado por código EOI. Las coordenadas se toman de la primera
fila disponible del ajuste, no de prueba. La definición administrativa AMB
es una elección explícita de este estudio; el artículo no especifica que su
expresión «área metropolitana» equivalga exactamente a este límite.

## Descarga y calidad observada

- Fuente: [dataset `tasf-thgu`](https://analisi.transparenciacatalunya.cat/es/Medi-Ambient/Qualitat-de-l-aire-als-punts-de-mesurament-autom-t/tasf-thgu),
  enlazado por el [portal oficial](https://mediambient.gencat.cat/es/05_ambits_dactuacio/atmosfera/qualitat_de_laire/vols-saber-que-respires/descarrega-de-dades/descarrega-dades-automatiques/).
- Se descargaron seis respuestas anuales, con consultas y SHA-256 guardados.
- Las 14 candidatas aportan 28,752 filas diarias y 675,398 valores horarios
  presentes. No hay duplicados estación-fecha ni valores negativos en esta descarga.
- Todas las observaciones declaran µg/m³. Se mantienen esas unidades.
  Los faltantes se conservan, sin interpolar ni etiquetarlos como ataques.
- Los nombres son estables; las pequeñas variaciones decimales de coordenadas
  se conservan en el inventario, sin interpretarlas como mudanzas confirmadas.
- La cobertura anual de cada estación está en `cobertura_estacion_anio.csv`;
  incluso con buen ajuste existen diferencias posteriores: por ejemplo, Palau
  Reial tiene 82.3% en 2018 y Viladecans 84.3% en 2017. Se reportan como
  disponibilidad, no se usan para elegir al detector ni eliminar estaciones.

Los periodos propuestos 2014–2015/2016/2017/2018/2019 tienen observaciones en
la cohorte de 13 estaciones. Falta auditar las máscaras comunes de ventanas y
bloques con la convención horaria definitiva antes de congelar el protocolo.

## Búsqueda del subconjunto original

Se volvió a inspeccionar el árbol completo del
[repositorio de la autora](https://github.com/XhensildaAllka/PARAAD), commit
`6dbb5a9144a043d7825d63f49463a442ae60165b`: sólo contiene arquitecturas,
funciones auxiliares y README, sin datos procesados ni lista de estaciones.

Se localizó además la tesis abierta de Allka,
[Enhancing data quality in IoT monitoring sensor networks](https://upcommons.upc.edu/entities/publication/dea8b3e3-ed1b-4478-87a9-7d2499b597c5),
DOI 10.5821/dissertation-2117-457522. En §2.1.1, página impresa 14 (PDF 29),
se repiten ocho estaciones y 24,192 muestras O3; al inspeccionar visualmente
las figuras 2.1/2.2 aparecen Badalona, Ciutadella, Eixample y Sant Adrià.
Esto aporta cuatro nombres, pero **no completa ni demuestra una lista de ocho**;
pueden ser figuras ilustrativas. No se concluye que fueran sólo cuatro.
El PDF se consultó localmente en `/tmp`, sin incorporarlo a Git ni contactar
a los autores. El subconjunto exacto y su orden siguen sin identificarse.

## Hallazgo horario: no asumir UTC

Los metadatos describen `h01`…`h24` como valores de las horas 01…24, pero no
precisan zona horaria ni inicio/fin del intervalo. No se asignaron timestamps
UTC al crear el formato largo: se preservan `fecha` y `hora_fuente` 1…24.

Dos comprobaciones:

1. En todos los últimos domingos de marzo de 2014–2019, `h02` carece de
   observaciones en todas las estaciones con fila. En algunos años también
   faltan valores de `h03`. En octubre no existe una columna 25 para representar
   por separado las horas repetidas. Esto impide asumir 24 intervalos físicos
   uniformes a lo largo de todos los cambios estacionales.
2. El [informe oficial de incidencias de ozono de 2020](https://mediambient.gencat.cat/web/.content/home/ambits_dactuacio/atmosfera/qualitat_de_laire/avaluacio/ozo-troposferic/informes_ozo_anys_anteriors/documents/Informe-incidencies-CAMPANYA-O3-2020_definitiu.pdf)
   sitúa 239 µg/m³ en Palau Reial el 10/07/2020, intervalo 01:00–02:00 UTC.
   La fila del portal coloca ese máximo en `h04`, no en `h02`. Es compatible
   con una etiqueta local al final del intervalo en verano; un ejemplo no
   basta para certificar la semántica de toda la serie.

El contraste 2020 es auxiliar para estudiar el formato y no forma parte de
los datos de ajuste, calibración o prueba del estudio Barcelona 2014–2019.
No se usó para entrenar ni para decidir hiperparámetros.

Antes de construir ventanas de 24 horas debe registrarse una solución:
confirmar la convención con documentación adicional, o definir explícitamente
bloques de posiciones horarias de fuente y excluir de forma común las ventanas
afectadas por cambios de reloj, sin presentarlas como UTC reconstruido.
No se fabricarán 24 horas físicas en días de 23/25 horas.

## Archivos y ejecución reproducible

- `data/raw/barcelona_paraad/o3_amb_<año>.json.gz`: respuestas originales,
  no versionadas por la regla del repositorio.
- `data/reference/barcelona_paraad/descarga_<año>.json`: consultas y hashes.
- `data/reference/barcelona_paraad/metadatos_tasf_thgu.json`: esquema original.
- `data/reference/barcelona_paraad/cohorte13.csv` y `cohorte13_registro.json`:
  conjunto aprobado y criterio basado en ajuste.
- `results/barcelona_paraad/auditoria/`: cobertura por estación/año,
  metadatos, elegibilidad, horas de cambio estacional, hashes y observaciones
  largas con fecha/hora de fuente. El parquet de la cohorte conserva faltantes.
- `experiments/barcelona/descargar_auditar.py`: descarga y auditoría básica.
- `experiments/barcelona/auditar_horas_etapas.py`: chequeos temporales.
- `tests/test_barcelona_auditoria.py`: dos pruebas sintéticas de elegibilidad
  sin fuga desde prueba y conservación de las horas de fuente; ambas pasan.

La descarga ya existe: los scripts reutilizan las respuestas verificadas
por hash; no sobrescriben silenciosamente una respuesta distinta.

## Estado para continuar

**Cohorte de 13 aprobada y datos disponibles.** La siguiente tarea es cerrar
la convención de horas/ventanas y actualizar las dimensiones: PARAAD 13×24;
V4 usa otras 12 estaciones, máscaras y sin/cos (26 características); L0
mantiene cuatro vecinas y 17 características. El 30% de sensores se traduce
a cuatro por configuración (4/13=30.77%), declarado como fracción efectiva.
No se inicia entrenamiento con timestamps inventados o subconjunto ambiguo.
