# Ozono (O3) de la RAMA en formato tabular para TINTOlib

José Lili — tesis de maestría PCIC-UNAM. Paquete preparado el 2026-11-24.

## Origen de los datos

- Red Automática de Monitoreo Atmosférico (RAMA), Ciudad de México, datos públicos del SIMAT.
  Archivos originales `2020O3.xls`, `2021O3.xls` y `2022O3.xls`.
- Concentración horaria de ozono en **ppb, sin transformar**. El valor −99 de la RAMA (sin medición)
  se convirtió en vacío (NaN). No se imputó nada.
- 31 estaciones (las 33 activas menos HGM y XAL). Convención horaria usada: HORA 1 del archivo
  original = columna `h00`, …, HORA 24 = `h23`.

## Una fila = una estación en un día

Cada fila tiene 24 características, `h00` … `h23`: el ozono de esa estación en cada hora del día.
La columna `clase` va al final, como pide TINTOlib. La estación y la fecha **no** son
características: van en el archivo `*_metadatos.csv` correspondiente, en el mismo orden de filas.

## Archivos

| Archivo | Filas | Qué es |
|---|---:|---|
| `ajuste_mapa_2020_2021.csv` | 12 146 | **Exactamente la tabla con la que ajustamos TINTO**: todos los días completos (24 horas con dato) de 2020–2021. `clase` = 0 en todas las filas, porque solo se usó para ajustar el mapa |
| `piloto_ajuste.csv` | 2 048 | Clasificación: 1 024 días completos de 2020–2021 originales (`clase` 0) y los mismos días alterados (`clase` 1) |
| `piloto_validacion.csv` | 512 | Igual, con 256 días completos de 2022 |
| `o3_estacion_dia_2020_2022.csv` | 33 976 | Todas las estación-días de 2020–2022, con NaN donde no hubo medición (19 300 completas). Incluye estación, fecha y horas con dato |
| `completos_32_mapa.csv` | 24 | Posición (fila, columna) de cada hora en la imagen 32 × 32 que obtuvimos |
| `completos_escala.csv` | 24 | Escala MinMax por columna, ajustada con `ajuste_mapa_2020_2021.csv` |
| `verificacion.json` | — | Conteos y SHA-256 de cada archivo |

**La alteración del piloto** simula un sensor manipulado durante un día completo. Las 24 lecturas
se multiplican por 1.5 o se dividen entre 1.5; el sentido se sortea por día (columna `alteracion` de
los metadatos). El día original y su copia alterada siempre quedan en el mismo conjunto, y los años
están separados: ajuste 2020–2021, validación 2022.

## Cómo generamos las imágenes

TINTOlib 1.3.1:

```python
TINTO(problem='classification', pixels=32, algorithm='PCA', blur=False, zoom=1,
      format='npy', random_seed=42)
```

- Ajustamos el mapa con `ajuste_mapa_2020_2021.csv`, escalado con MinMax por columna (sin recortar
  valores fuera de [0, 1]). Lo hicimos nosotros y pasamos `transformer=None`. Comprobamos que cargar
  el CSV y usar el `MinMaxScaler` por defecto da **el mismo mapa**.
- Con 32 × 32 las 24 horas caen en 24 píxeles distintos: no hay sobrescritura.
- **Sin difuminado** (`blur=False`): cada imagen tiene 24 píxeles con dato y 1 000 en cero.
- El mapa y la escala se congelaron. Las imágenes de 2022 y las alteradas usan ese mismo mapa, sin
  volver a ajustar TINTO.
- Para entrenar colocamos cada valor escalado en su píxel con nuestro propio código. Comprobamos que
  el resultado es idéntico al de `TINTO.transform`.

## Qué obtuvimos con estos datos (piloto)

CNN pequeña (Conv 8 → Pool → Conv 16 → Pool → Dense 32 → Dropout 0.2 → sigmoide; 34 081
parámetros), 5 épocas, Adam 0.001, lote 64. En `piloto_validacion.csv`, con umbral 0.5:
ROC-AUC 0.674, precisión 0.672 y recall 0.328 (detecta 84 de 256 días alterados).
Era un piloto de viabilidad, sin ajuste de hiperparámetros.

Después usamos las mismas imágenes estación-día como entrada de otros modelos (un autoencoder y un
pronosticador CNN+GRU del día siguiente). Esos experimentos no son clasificación directa con TINTO.
