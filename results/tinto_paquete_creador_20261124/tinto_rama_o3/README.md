# Ozono de la RAMA (Ciudad de México) para TINTOlib

José Lili — tesis de maestría, PCIC-UNAM. 24 de noviembre de 2026.

Datos horarios de ozono (O3, en ppb) de la Red Automática de Monitoreo Atmosférico (RAMA), publicados
por el SIMAT de la Ciudad de México, 2020–2022. En la tesis buscamos detectar estaciones cuyas
lecturas fueron alteradas durante días completos.

## Contenido

| Carpeta | Qué contiene |
|---|---|
| `1_originales_rama/` | `2020O3.xls`, `2021O3.xls` y `2022O3.xls` tal como los publica la RAMA |
| `2_tabla_que_recibio_tinto/` | La tabla con la que ajustamos el mapa de TINTO (sin etiquetas) |
| `3_piloto_clasificacion/` | Días originales y alterados, con etiqueta, para entrenar y probar |
| `4_nuestro_mapa_y_figura/` | El mapa y la escala que obtuvimos, una figura del proceso y el script que arma la tabla 2 |
| `verificacion.json` | SHA-256 de cada archivo |

## 1. Originales

Una fila por hora (`FECHA`, `HORA` de 1 a 24) y una columna por estación (36). El valor −99 indica
que no hubo medición.

## 2. Tabla que recibió TINTO

Elegimos como unidad la **estación-día**, así que reacomodamos los originales antes de TINTO:

- −99 → vacío. Tomamos HORA 1 como 00:00 y HORA 24 como 23:00 del mismo día. Es un supuesto nuestro
  que no hemos verificado contra la documentación del SIMAT.
- Cada día de cada estación es una fila con 24 columnas `h00 … h23`, en ppb, sin otra transformación.
- 31 estaciones (sin HGM, XAL, COY, SJA ni SFE), solo días completos (24 horas con dato) de 2020–2021.

`ajuste_mapa_2020_2021.csv` tiene 12 146 filas y `clase` = 0 en todas: solo la usamos para ajustar
el mapa. La estación y la fecha de cada fila están en `ajuste_mapa_2020_2021_metadatos.csv`; no
entraron a TINTO. La figura `4_nuestro_mapa_y_figura/que_recibe_tinto.png` muestra el reacomodo.

`python 4_nuestro_mapa_y_figura/armar_tabla.py` rehace esta tabla desde los XLS y la compara con la
entregada (pandas, numpy y xlrd). Nosotros lo corrimos y salen idénticas.

## 3. Piloto de clasificación

Simulamos un sensor alterado durante un día completo: multiplicamos las 24 lecturas por 1.5 o las
dividimos entre 1.5, con el sentido sorteado por día.

| Archivo | Filas | Origen |
|---|---:|---|
| `piloto_ajuste.csv` | 2 048 | 1 024 días completos de 2020–2021, cada uno original (`clase` 0) y alterado (`clase` 1) |
| `piloto_validacion.csv` | 512 | 256 días completos de 2022, igual |

Las columnas son las mismas de la tabla 2. En `*_metadatos.csv` están la estación, la fecha y la
alteración (`original`, `x1.5` o `/1.5`). Cada día y su copia alterada quedan en el mismo archivo, y
los años no se mezclan.

## 4. Configuración de TINTOlib

TINTOlib 1.3.1, ajustado con la tabla 2:

```python
TINTO(problem='classification', pixels=32, algorithm='PCA', blur=False, zoom=1,
      format='npy', random_seed=42)
```

- Escalamos con `MinMaxScaler(clip=False)` y pasamos `transformer=None`. Cargar el CSV con el
  `MinMaxScaler` por defecto da el mismo mapa (`completos_32_mapa.csv`).
- Las 24 horas caen en 24 píxeles distintos, sin choques. No usamos difuminado.
- Congelamos mapa y escala, y generamos con ellos las imágenes de 2022 y las de los días alterados.
- Observamos que PCA acomodó las horas en un anillo que sigue el ciclo diario del ozono.

Con estas imágenes entrenamos una CNN pequeña (34 081 parámetros, 5 épocas). En
`piloto_validacion.csv`, con umbral 0.5, obtuvo ROC-AUC 0.674, precisión 0.672 y recall 0.328.
Fue un piloto de viabilidad, sin ajuste de hiperparámetros.
