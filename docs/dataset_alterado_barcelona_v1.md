# Dataset de Barcelona con ataques proporcionales aplicados

Fecha: 2026-10-29. Aplicación autorizada por el tesista, posterior al registro
de `escenario_proporcional_barcelona_v1.md`. No entrena modelos ni calcula
métricas de detección. Se preservan datos limpios y calendarios originales.

Estado: **completadas las 150 variantes**, con igualdad exacta entre dos
ejecuciones de aplicación/perfiles/características por variante. La verificación
independiente de los archivos escritos confirmó hashes, faltantes, etiquetas,
soporte común, alineación de índices y finitud de entradas. Control guardado en
`results/barcelona_paraad/ataques_proporcionales_v1/verificacion_final.json`.
Pasan las 21 pruebas Barcelona, incluidas las tres de inyección.

## Qué se genera

`experiments/barcelona/aplicar_ataques_proporcionales.py` aplica los 70 planes:

| Uso | Calendarios | Deltas aplicados | Variantes |
|---|---:|---|---:|
| Ajuste inicial L0 2014–2015 | 20 | 50% | 20 |
| Validación L0 2016 | 10 | 50% | 10 |
| Ajuste definitivo L0 2014–2016 | 20 | 50% | 20 |
| Prueba 2018 | 10 | 100%, 50%, 20%, 10%, 5% | 50 |
| Complementaria 2019 | 10 | 100%, 50%, 20%, 10%, 5% | 50 |
| Total | 70 | | 150 |

Se usa x×(1+δ) o x/(1+δ) según el signo, redondeo `floor(alterado+0.5)`
en µg/m³. Sólo se alteran valores observados. Se conservan todas las horas
de la rejilla y los faltantes, incluidos los días apartados por cambio de reloj.
No se fuerza una lectura baja a cambiar si el redondeo conserva su valor.

Cada variante parte de los datos limpios y su propio calendario, sin acumular
ataques de otros calendarios. El historial anterior al inicio del periodo es
limpio; dentro del periodo los perfiles ven los ataques pasados de esa misma
variante, también después de terminar el episodio. Esto mantiene los efectos
sobre contexto y evita usar perfiles limpios para puntuar señales alteradas.

## Escalas y ventanas

Se recalculan los perfiles de 14 días locales, relativas y columnas a14.
**Las medias, desviaciones, escalas a14 y vecinas permanecen congeladas**:
selección 2014–2015 para ajuste inicial/validación, y definitivo 2014–2016
para ajuste definitivo/pruebas. La función de aplicación no ajusta parámetros.

Se mantiene la máscara común de estación-días del dataset limpio. Como los
faltantes y la disponibilidad de las bases causales no cambian, tampoco
cambia el soporte evaluable. La regla temporal de exclusión sigue vigente.

La señal alterada y su matriz estandarizada son comunes a los tres detectores.
Se conserva la representación compacta por horas e índices: las funciones de
ventanas existentes materializan lotes V4 24×26, L0 24×17 y PARAAD 13×24.
Los datos de ajuste con ataques son para L0; V4 y PARAAD deben entrenarse
con los artefactos limpios de `ventanas_v1/`, nunca con estas variantes.
Calibración 2017 sigue siendo exclusivamente limpia.

## Archivos por variante

Ruta `results/barcelona_paraad/ataques_proporcionales_v1/<calendario>/d<δ>/`:

- `valores_alterados.parquet`: concentraciones físicas con ataques aplicados.
- `perfiles_causales.parquet`: perfil recalculado sobre la historia alterada.
- `etiquetas_hora.parquet`: lectura efectivamente cambiada, separada de X.
- `episodio_hora.parquet`: pertenencia al episodio, incluso en una hora sin dato.
- `estacion_dias.parquet`: misma máscara común y etiqueta de pertenencia diaria
  al episodio; inicio/fin posicional trasladados a las filas de esta variante.
- `z.npy`: concentraciones estandarizadas hora×13, faltantes rellenados con cero.
- `l0_features.npy`: hora×41, recortable a las 17 columnas locales. No contiene
  etiquetas. V4 usa z de las otras estaciones, máscaras y hora local.
- `completo.json`: control de igualdad entre dos ejecuciones, conteos y hashes.

Cada variante guarda su periodo y hasta 24 horas previas de contexto para el
recorte de ventanas. Los perfiles se calculan primero con **todo el pasado
disponible** desde el principio de la rejilla, no sólo esas 24 horas guardadas.
`offset_global` permite alinear estas filas con el reloj/índices originales.

La raíz contiene `entrada.json`, `resumen.csv` y, al completar las 150 variantes,
`registro.json`. El proceso puede reutilizar variantes completas sólo después
de verificar sus hashes y las mismas entradas. Se detiene ante una carpeta
parcial; no pisa una salida sin revisar.

## Comprobaciones

Cada aplicación y cada transformación de características se ejecuta dos veces
y debe coincidir exactamente. Se verifica conservación de faltantes, igualdad
fuera de episodios, cambios restringidos a lecturas programadas, finitud de X
y misma disponibilidad de las bases causales. El registro global enlaza los
controles y hashes de cada variante, la máscara común y los registros previos.

Las pruebas sintéticas comprueban ambos signos (60→90 y 60→40 con δ50),
faltantes intactos, ceros/valores bajos sin cambio por redondeo y contaminación
causal del perfil después del episodio sin reajustar escalas. Los conteos de
lecturas cambiadas y etiquetas no son resultados de precisión, recall o F1.

```sh
.venv/bin/python -m experiments.barcelona.aplicar_ataques_proporcionales
.venv/bin/python -m experiments.barcelona.verificar_dataset_alterado
.venv/bin/python -m pytest tests/test_barcelona_inyeccion.py -q
```

El siguiente paso científico es entrenar con la separación registrada y
calibrar después sobre 2017 limpio. La existencia de matrices de prueba no
autoriza seleccionar hiperparámetros usando sus resultados.
