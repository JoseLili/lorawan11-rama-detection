# Revisión 20: PARAAD-SA adaptado frente a los detectores de RAMA

Fecha de sesión: 2026-10-28. Evaluación posterior al registro separado
`registro_examen_paraad_revision20.md`, con modelo y umbrales congelados.
Origen: PARAAD cargado de disco, sin entrenar; comparadores históricos de
revisiones 18/19, también congelados. No se ajustó nada con estos resultados.

## Alcance y controles

- Se evaluaron 2024, 2025 y enero–julio de 2026, los escenarios original,
  B (una a la vez) y A (un solo nodo), y δ=100/50/20/10/5%.
- 765 matrices alteradas y tres limpias, todas con dos inferencias idénticas.
  Se guardaron 768 artefactos de puntajes con hash y controles por matriz.
- Las máscaras comunes contienen 8,977, 8,633 y 4,858 estación-días por año,
  respectivamente. Se fijaron a partir de los cuatro comparadores en el año
  limpio; PARAAD cubre todas esas filas. No se modificó el universo al puntuar
  ataques. Cada calendario reutiliza esas mismas unidades.
- Los totales de casos atacados/normales coinciden con revisiones 18/19.
  Además, 60 controles reconstruyen exactamente TP/FP/FN/TN históricos de
  L0 único y V4 usados en los intervalos pareados del escenario original.
- Parámetros congelados: dropout 0.3, 499 épocas; p99=0.6405011077101032 y
  p99.9=0.8366300233950218, error absoluto medio estandarizado por estación-día.
- CPU local con TensorFlow 2.21.0 y Keras 3.13.2; mismo entorno de inferencia
  que la calibración local. No se abrió una nueva sesión Colab.
- Una dependencia auxiliar faltante (`pycryptodome`, importada al reutilizar
  las vecinas) detuvo el primer arranque de 2024 tras puntuar el año limpio.
  Se instaló en el entorno temporal y se recuperó ese checkpoint intacto.
  No se cambiaron modelo, umbrales, código científico ni criterios de decisión.

## Resultado central

**PARAAD detecta cambios grandes, pero no muestra una mejora estable frente
a V4 entre años. L0 obtiene mayor F1 en las 36 combinaciones de δ100/δ50,
tres escenarios, tres años y dos umbrales.** El contraste L0–PARAAD es práctico
y tiene distinta supervisión: L0 aprendió con anomalías sintéticas d50;
PARAAD se entrenó sólo con observaciones normales. No es una ablación pura.

F1 en el escenario original, δ=50%, p99:

| Año | PARAAD-SA adaptado | V4 | L0 único |
|---|---:|---:|---:|
| 2024 | 0.128 | 0.101 | 0.388 |
| 2025 | 0.208 | 0.108 | 0.445 |
| 2026 parcial | 0.140 | 0.193 | 0.502 |

IC del 95% de la diferencia de F1 en esas mismas unidades:

| Año | PARAAD − V4 | IC95% | PARAAD − L0 | IC95% |
|---|---:|---|---:|---|
| 2024 | +0.027 | [−0.005, +0.066] | −0.261 | [−0.322, −0.204] |
| 2025 | +0.100 | [+0.054, +0.157] | −0.237 | [−0.307, −0.165] |
| 2026 parcial | −0.053 | [−0.119, +0.034] | −0.363 | [−0.456, −0.258] |

La ventaja de PARAAD sobre V4 con δ50/p99 en 2025 tiene un intervalo que
excluye cero; no ocurre así en 2024. En 2026 el punto favorece a V4, pero su
intervalo también incluye cero. Se evita generalizar una victoria de un año.
Son intervalos por bootstrap de bloques estación×mes según el registro, no
una prueba de superioridad universal ni un ajuste por comparaciones múltiples.

## Sensibilidad a la magnitud

PARAAD en 2025 original, p99:

| δ | Precisión | Recall | F1 |
|---|---:|---:|---:|
| 100% | 0.233 | 0.688 | 0.348 |
| 50% | 0.143 | 0.377 | 0.208 |
| 20% | 0.024 | 0.055 | 0.033 |
| 10% | 0.009 | 0.021 | 0.013 |
| 5% | 0.007 | 0.016 | 0.010 |

El recall cae al reducir la magnitud. No se traslada el recall 0.81/precisión
0.84 de Barcelona como expectativa numérica: cambian datos, anomalías,
prevalencia, tratamiento de faltantes y umbral. Aquí se evalúa explícitamente
una adaptación del método publicado. No se ha reproducido su tabla original.

## Escenarios de una sola estación

F1 con δ50 y p99:

| Año | Escenario | PARAAD | V4 | L0 único |
|---|---|---:|---:|---:|
| 2024 | B | 0.106 | 0.084 | 0.356 |
| 2025 | B | 0.186 | 0.095 | 0.407 |
| 2026 parcial | B | 0.116 | 0.169 | 0.464 |
| 2024 | A | 0.030 | 0.029 | 0.149 |
| 2025 | A | 0.079 | 0.033 | 0.233 |
| 2026 parcial | A | 0.045 | 0.065 | 0.235 |

Se comparan detectores dentro de cada escenario. La reducción de F1 en A no
demuestra por sí sola peor sensibilidad: cambia la prevalencia. Para comparar
B con original, `pareado_recall.csv` usa los mismos episodios conservados,
con intervalos de la diferencia de recall. Los IC individuales de PARAAD están
en `intervalos.csv`. No se inventan IC pareados de diferencias con L0/V4 en
A/B: sus puntajes por día no se conservaron en revisión 19, sólo sus agregados.

## Alertas en datos limpios fuera de calibración

Porcentaje de todas las estación-días comunes del año limpio que alertan:

| Año limpio | Umbral p99 | Umbral p99.9 |
|---|---:|---:|
| 2024 | 3.420% | 0.869% |
| 2025 | 1.656% | 0.348% |
| 2026 parcial | 3.005% | 1.379% |

La calibración cumplió 1%/0.1% en 2023, pero esos límites no garantizan la
misma tasa en otros años. Esto afecta la precisión y debe mostrarse junto
con el recall. No se recalibró con los años de examen. Las tablas `sin ataque`
usan el año limpio con las mismas etiquetas de los calendarios como control
pareado; las falsas alarmas por grupo se conservan en archivos separados.

## Lectura defendible para la tesis

En el escenario evaluado de RAMA, PARAAD-SA adaptado detecta anomalías
proporcionales grandes y puede mejorar la referencia no supervisada V4 en
algunas condiciones. Esa mejora no es uniforme entre años. L0 conserva
mayor F1 en los cambios grandes y medianos considerados, con el beneficio
adicional de su entrenamiento supervisado sobre ataques del escenario.
Los cambios pequeños siguen siendo difíciles para PARAAD.

Estos resultados no aíslan la causa de la diferencia: cambian la arquitectura,
supervisión, representación de vecinas y tratamiento de faltantes. No demuestran
que el tamaño urbano sea la causa, ni que el método publicado sea inferior
en su escenario original. No se ajustará PARAAD para mejorar estos resultados
usando 2024–2026; cualquier experimento nuevo necesita un registro separado.

## Archivos y figura

En `results/anomalias_red_v1/revision20/examen/`:

- `comparacion_completa.csv`: cinco detectores, tres escenarios, cinco δ,
  dos umbrales, tres años y versiones con/sin ataque.
- `tabla_f1.csv`: tabla compacta para los tres años.
- `intervalos_paraad.csv`: IC individuales y diferencias pareadas en original.
- `control_referencias_pareadas.csv`: 60 controles históricos idénticos.
- `<año>/`: puntajes, hashes, conteos, falsas alarmas por grupo, recall pareado
  original/B, manifiestos y finalización comprobada.
- `comparacion_2025_original.png`: una figura de dos paneles, p99 y p99.9.

Ficha: X=magnitud proporcional δ, en categorías 5/10/20/50/100%; Y=F1 por
estación-día de 2025 original, diez calendarios. Umbrales calibrados sólo con
2023 limpio y universo común. PARAAD y V4 se entrenaron sin etiquetas; L0
se identifica como referencia supervisada. Los valores sin ataque y los IC
se consultan en las tablas, no se representan en esa figura. El año se fijó
en el script de resumen antes de terminar el examen; la tabla completa evita
seleccionar sólo ese año para concluir.
