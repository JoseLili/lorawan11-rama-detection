# Ventanas y disponibilidad común de Barcelona

Fecha: 2026-10-29. Preparación sin anomalías, modelos ni puntajes de detección.
Se conserva la cohorte aprobada de 13 estaciones y la convención operativa
horaria de `metodologia_barcelona_paraad_v1.md`.

## Código y ventanas

El repositorio contiene `src/detect/windows.py`,
`src/detect/entrenamiento_multianual.py`, `src/detect/lstm_red.py` y
`src/detect/lstm_local.py`. Los generadores multianuales completos dependen de
estaciones/etapas RAMA y extraen la hora del índice. No se usan directamente
sobre UTC porque aquí se acordó mantener la hora local como característica.

El adaptador `experiments/barcelona/preparar_ventanas.py` reutiliza
`lstm_red.ventanas` y `lstm_local.ventanas_locales`, incluido el orden de sus
17 columnas. No modifica fuentes científicas ni resultados RAMA.

| Método | Forma | Recorte |
|---|---|---|
| PARAAD | 13×24 | Bloque UTC 00–23; máscara observada aparte |
| V4 | 24×26 | t−24…t−1; otras 12 estaciones, máscaras y seno/coseno local |
| L0 | 24×17 | t−23…t; objetivo y cuatro vecinas, tres columnas por estación y seno/coseno local |

La representación es indexada: cada hora y característica se guarda una vez.
Las funciones `ventana_v4`, `ventana_l0` y `bloque_paraad` materializan lotes
por posición, sin almacenar copias repetidas de todas las ventanas solapadas.
El directorio ocupa aproximadamente 27 MB.

Los perfiles son medias de los 14 días **locales** anteriores a la misma hora,
con respaldo histórico de esa hora y global estrictamente anterior a t.
Los días vacíos permanecen: no son los últimos 14 días con dato. La historia
cruza las etapas causalmente. Los días apartados por cambio de reloj no se
recuperan mediante el perfil.

La relativa es (observado−perfil)/desviación. La columna a14 es la diferencia
entre esa relativa y la media de las relativas de las cuatro vecinas; requiere
al menos dos vecinas con relativa disponible y se escala con su desviación
de ajuste. Los faltantes se rellenan con cero después de normalizar y se
conservan sus máscaras observadas; no se exige que todas las vecinas tengan dato.

Se guardan escalas separadas: selección sólo 2014–2015 UTC; definitivo sólo
2014–2016 UTC. Las vecinas se calculan con las coordenadas de ajuste de la
cohorte ya registrada, con desempate por código EOI. No se entrenó ningún modelo.

## Máscara común y conteos

Cada estación-día requiere bloque completo UTC sin horas excluidas por cambio
de reloj, al menos 12 observaciones propias para PARAAD, al menos 12 horas
con ventana válida para L0 y al menos 12 con base causal y ventana válida para
V4. Una ventana que toca una hora excluida no es válida, incluso cuando ésta
está en el día anterior. Los huecos ordinarios conservan sus máscaras.
Se comparten estación-días y se mantienen los soportes horarios propios de
cada método, como en RAMA; no se añade una intersección de horas.

| Etapa UTC | Estación-días calendario | Comunes |
|---|---:|---:|
| Ajuste inicial 2014–2015 | 9,490 | 9,149 |
| Validación 2016 | 4,758 | 4,538 |
| Calibración 2017 | 4,745 | 4,536 |
| Prueba 2018 | 4,745 | 4,549 |
| Complementaria 2019 | 4,745 | 4,567 |
| Total de etapas | 28,483 | 27,339 |

El ajuste definitivo tiene 13,687 casos comunes, unión de ajuste y validación.
La rejilla contiene además una hora UTC del 31/12/2013: su bloque incompleto
queda fuera de las etapas. El 31/12/2019 tampoco está completo en UTC y se
excluye sin fabricar la hora faltante. Cada bloque pertenece a una sola etapa;
el contexto anterior sí puede cruzar el corte.

Las 13 estaciones cumplen al menos 2,000 ejemplos efectivos y seis meses en
cada etapa obligatoria. Los mínimos entre estaciones son 16,470 horas/24 meses
en ajuste, 7,703/12 en validación y 7,339/11 en calibración. Los conteos de
2018–2019 sólo describen disponibilidad; no se usaron para elegir estaciones
ni se calcularon puntajes de detección.

Los motivos de exclusión tienen prioridad: bloque incompleto, cambio de reloj
en bloque, menos de 12 observaciones, menos de 12 horas con contexto. Son
categorías excluyentes, no conteos de todos los fallos de un mismo caso.

## Artefactos y control

Directorio `results/barcelona_paraad/ventanas_v1/`:

- `valores.parquet`, `reloj.parquet`, `perfiles_causales.parquet` y
  `vecinas.json`: base compartida, en orden fijo de códigos EOI.
- `horas_validas_l0.parquet` y `horas_validas_v4.parquet`: posición t válida
  por objetivo, alineada con las filas de `valores.parquet`.
- `estacion_dias.parquet`: inicio/fin posicional del bloque, conteos y motivos.
- `mascara_comun.csv`: universo estación-día previo a cualquier ataque.
- `cobertura_estacion_etapa.csv`, `exclusiones.csv` y
  `elegibilidad_etapas.csv`: tablas completas por estación y etapa.
- `z_<fase>.npy`: valores estandarizados hora×13; máscaras desde
  `valores.parquet.notna()`. Fases: `seleccion` y `definitivo`.
- `l0_features_<fase>.npy`: hora×41: relativas, máscaras, dos columnas de hora
  local y a14. El recorte local produce 17 columnas.
- `escalas_<fase>.csv` y `registro.json`: parámetros, reglas y hashes.

Se repitieron ambas transformaciones completas (datos/perfiles/máscaras y
características de las dos fases) con igualdad exacta. Se comprobaron las
formas de los tres métodos para las 13 estaciones; se releyeron los arrays
guardados para comprobar finitud y formas y se verificaron los hashes de
entradas/salidas. Pasan 13 pruebas de auditoría, tiempo y ventanas, incluyendo
causalidad, escalas sin validación, recortes V4/L0, contexto entre etapas y máscaras.

Desde la raíz del repositorio:

```sh
.venv/bin/python -m experiments.barcelona.preparar_ventanas
.venv/bin/python -m pytest tests/test_barcelona_auditoria.py tests/test_barcelona_tiempo.py tests/test_barcelona_ventanas.py -q
```

El generador rechaza sobrescribir una salida existente. La conversión temporal
sigue siendo una convención operativa, no una recuperación certificada de las
horas ambiguas de la fuente. La máscara todavía no ha sido usada para evaluar.

## Siguiente paso

Registrar y generar planes de sesgo independientes por etapa y compartidos
entre métodos. Bajo ataque se mantienen esta máscara, vecinas y escalas, pero
se **recalculan perfiles y características sobre la serie alterada**. Las
características limpias no sustituyen esa inferencia. PARAAD y V4 se ajustan
sin inyecciones; L0 recibe ataques sólo en ajuste, con validación independiente.
