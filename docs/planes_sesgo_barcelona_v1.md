# Calendarios de sesgo diario Barcelona

Fecha: 2026-10-29. Planes generados antes de aplicar anomalías, entrenar o
calcular puntajes de detección. Reglas registradas en
`metodologia_barcelona_paraad_v1.md`, apartado de calendarios previo a inyección.

## Aplicación prevista

Cada calendario elige cuatro de las 13 estaciones, y sin reemplazo el 30%
de los días comunes propios de cada una (redondeo half-up). Se permiten
simultaneidad y días consecutivos. Un desplazamiento positivo independiente
por estación-día permanece constante en sus horas observadas:

`alterado = observado + beta * sigma_ajuste`

Beta usa `scipy.stats.truncnorm(.2, 2, loc=0, scale=2)`, soporte 0.4–4.
No es un porcentaje de la concentración ni una normal absoluta. El resultado
físico está en µg/m³. Los faltantes no se convierten en lecturas, no se redondea
a ppb y no se cambia la máscara de disponibilidad. Una estación-día positiva
altera únicamente su propia señal; una vecina atacada no hace positiva la
etiqueta del objetivo. Los efectos sobre contexto se conservarán al recalcularlo.

El archivo de positivos contiene `plan`, factores, estación, día UTC, beta,
desviación de ajuste, desplazamiento físico y etiqueta 1. Los casos restantes
de la máscara común de ese periodo son negativos; los excluidos no lo son.
El mismo archivo será utilizado por los tres detectores, sin sorteos propios.

## Separación y conteos

| Uso | Calendarios | Universo común por calendario | Positivos sumados entre calendarios |
|---|---:|---:|---:|
| Ajuste L0 2014–2015 | 20 | 9,149 | 16,869 |
| Validación L0 2016 | 10 | 4,538 | 4,197 |
| Ajuste definitivo L0 2014–2016 | 20 | 13,687 | 25,244 |
| Prueba 2018, tres métodos | 125 | 4,549 | 52,975 |
| Complementaria 2019, tres métodos | 125 | 4,567 | 52,675 |

La prevalencia por plan está aproximadamente entre 9.0% y 9.5%, según las
estaciones elegidas, sus días disponibles y el redondeo. No son 30% de todos
los casos: se altera el 30% de los días de cuatro de las 13 estaciones.
Los positivos sumados contienen realizaciones repetidas de los mismos casos
ambientales; no representan observaciones ambientales independientes nuevas.

Los periodos son UTC. Ajuste inicial y validación usan la escala 2014–2015;
definitivo y pruebas la escala 2014–2016. Los usos tienen semillas separadas
y no comparten fechas entre ajuste y prueba. Definitivo incorpora deliberadamente
ajuste y validación, después de seleccionar épocas, como en RAMA. Calibración
2017 permanece limpia. PARAAD y V4 se ajustarán sin estos ataques.

Prueba y complementaria tienen 5 selecciones de estaciones × 5 de días × 5
campos de magnitud. Cada campo asigna beta a todos los estación-días comunes;
luego se consulta el valor seleccionado. Por tanto, un mismo factor de ruido
conserva beta del mismo caso al cambiar otros factores. Se obtuvieron cinco
selecciones de sensores distintas en cada año. En los 20 calendarios iniciales
hay 19 subconjuntos de sensores distintos, un resultado permitido por el sorteo
independiente registrado; no se volvió a sortear para modificarlo.

## Reproducibilidad y archivos

Generador: `experiments/barcelona/generar_planes.py`, usa semillas enteras
derivadas de 42 sin `hash()`. Salida `results/barcelona_paraad/planes_sesgo_v1/`:
cinco archivos `*_positivos.csv`, cinco `*_manifiesto.csv`, `resumen.csv` y
`registro.json`. Se verificaron primero los hashes de todas las salidas del
generador de ventanas y se guardan hashes de las entradas y de estos planes.
La generación se repitió dos veces con igualdad exacta. También se comprobaron
los CSV exportados, unidades, magnitudes positivas, ausencia de duplicados y
los años de prueba. SciPy utilizado: 1.18.1; NumPy/Pandas constan en el registro.

Pasan 15 pruebas Barcelona, incluidas dos nuevas para planes: factorial,
frecuencias por estación, soporte de beta, soporte común, relación física,
reproducibilidad y separación de usos aleatorios.

```sh
.venv/bin/python -m experiments.barcelona.generar_planes
.venv/bin/python -m pytest tests/test_barcelona_planes.py -q
```

El generador rechaza sobrescribir salidas existentes. No se generaron matrices
alteradas ni métricas de detección. El siguiente paso será aplicar y verificar
las inyecciones por plan: se preservan escalas y máscara, pero perfiles y
características se recalculan causalmente sobre la serie alterada.
