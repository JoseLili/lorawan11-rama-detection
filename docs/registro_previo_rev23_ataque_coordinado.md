# Registro previo de la revisión 23: ataque coordinado y error fijo en ppb contra el detector principal

Fecha: 2026-11-07. **Estado: aprobado por el tesista el 2026-11-07** (opción 1: completo, con las dos corridas), con la petición de optimizar todo lo posible sin cambiar el método. Las precisiones y optimizaciones de la sección final se fijaron después de la aprobación y antes de generar planes o matrices. Resultados: [resultados_rev23_ataque_coordinado.md](resultados_rev23_ataque_coordinado.md).

## Pregunta
Ens-Vb-R compara cada estación con sus 4 vecinas. Si el atacante altera **a la vez una estación y sus vecinas**, ¿cuánto pierde Ens-Vb-R, y cuánto pierden los demás detectores? Es el punto ciego esperado de Vb, y la fase 2 del protocolo (§7, episodios simultáneos en k estaciones).

**Esta revisión no elige ni cambia ningún modelo.** Ens-Vb-R sigue siendo el detector principal. El resultado define el **alcance** de lo que se puede afirmar sobre él.

## Datos
- **El banco estándar del protocolo:** 2024, 2025 y enero–julio de 2026, validados (zips de SIMAT), con los 30 calendarios `prueba_2024_01…10`, `final_2025_01…10` y `final_2026_01…10`.
- **Historia:** el año anterior limpio, para el perfil de 14 días, la mediana de 60 días y la ventana de 24 h.
- **Declaración:** estos años ya se usaron en las revisiones 16–21. Aquí sólo se describe un detector congelado bajo estrés, sin decidir nada con ellos, como en las revisiones 18–21.

## Escenarios (pareados: mismos días, signos y duraciones)
| | Qué se altera en cada episodio original de la estación *s* |
|---|---|
| **E1, referencia** | Sólo *s* (los calendarios tal cual) |
| **E2, vecinas** | *s* y **sus vecinas de Vb que son alterables** (hasta 4; HGM no lo es), con los mismos días, el mismo signo y la misma δ. Es el peor caso para Vb |
| **E3, al azar (control)** | *s* y **el mismo número de estaciones que en E2**, elegidas al azar entre las alterables que no son vecinas de *s* (semilla [42, 23, calendario, episodio]). Separa «muchas a la vez» de «justo las vecinas» |

- **Choques:** si una estación añadida ya tiene su propio episodio en esos días, se conserva el propio y se descartan los días traslapados del añadido. Así hay una sola alteración por estación-hora.
- **Dos familias de alteración, con los mismos planes:**
  - **A, proporcional:** x·(1 + δ) o x/(1 + δ), con δ = 100, 50 y 20 % (`ar.aplicar`);
  - **B, error fijo:** x + *a* o max(x − *a*, 0), con *a* = 5, 10, 20 y 40 ppb, redondeado a entero (`ar.aplicar_fijo`, la misma definición de la revisión 21).
- **Combinaciones:**
  - E1 con las dos familias completas: 3 δ + 4 *a*;
  - E2 y E3 con la familia A completa y la B con *a* = 10, 20 y 40 ppb.
  - Se omite 5 ppb en E2 y E3: en la revisión 21 nadie lo distinguía (F1 ≤ 0.047).
- Los planes se generan y se guardan con su SHA-256 antes de puntuar.

## Detectores (congelados, umbrales de 2023 de cada uno)
- **Ens-Vb-R:** principal, definitivos de la revisión 22, umbrales p99 = 0.1525 y p99.9 = 0.6397.
- **Ens-V0-R:** comparador, revisión 22.
- **L0 único:** revisión 14.
- **PARAAD-SA:** revisión 20, puntuado como en la revisión 22, con la calibración de 2023 reproducida.
- **R3:** la regla de vecinas de la revisión 12 con sus umbrales de la revisión 18, **si su implementación corre sin cambios**; si no, se declara.

## Métricas
- **Dentro de cada escenario:** F1, recall y precisión por estación-día con p99 y p99.9; F̄ (media del F1 con δ = 100, 50 y 20 %) y **F̄ppb** (media del F1 con 10, 20 y 40 ppb).
- **Cambio real en ppb:** se reporta el cambio medio real de cada tamaño, porque el recorte en 0 lo deja por debajo de *a*.
- **Entre escenarios, sólo con el recall y el umbral fijo.** Al atacar más estaciones aumentan los positivos, y eso sube la precisión y el F1 aunque el detector no mejore. Las falsas alarmas en limpio son las mismas en los tres escenarios.
- **Por papel:** recall de la estación original *s* y de las estaciones añadidas, por separado.
- **Detección del ataque:** fracción de episodios coordinados con al menos una alarma en alguna estación del grupo mientras dura. Es lo que le importa al operador: enterarse de que hay un ataque.
- **Intervalos:** IC del 95 % por bootstrap pareado de bloques estación × mes (2 000 remuestreos, semilla [42, 23, 1]), con los umbrales fijos.

## Preguntas declaradas (p99)
- **Q1.** En E2, ¿conserva Ens-Vb-R su ventaja sobre Ens-V0-R? Se mide con ΔF̄ (Ens-Vb-R − Ens-V0-R) y su IC del 95 %:
  - **la conserva** si el IC queda por encima de 0;
  - **la pierde** si incluye el 0;
  - **se invierte** si queda por debajo de 0.
- **Q2.** De E1 a E2, ¿cae más el recall de Ens-Vb-R que el de Ens-V0-R (con δ = 50 %)? Se mide con la diferencia de las dos caídas y su IC del 95 %.

- **Q3.** En E1 con error fijo, ¿supera Ens-Vb-R a R3? En la revisión 21, R3 igualó o superó a L0 con este tipo de error. Se mide con ΔF̄ppb (Ens-Vb-R − R3) y su IC del 95 %.
- **Q4.** En E1 con error fijo, ΔF̄ppb (Ens-Vb-R − Ens-V0-R) y su IC del 95 %.

## Predicciones (Claude, antes de generar nada)
1. De E1 a E2, el recall de Ens-Vb-R con p99 y δ = 50 % baja **al menos 0.10**.
2. Ens-V0-R **también baja**, porque sus entradas incluyen las columnas de las vecinas, pero menos que Ens-Vb-R. En Q2, la diferencia de caídas es positiva.
3. En E3 las caídas de los dos son menores que en E2.
4. En Q1, Ens-Vb-R **pierde** su ventaja en E2: el IC incluye el 0.
5. El recall de PARAAD cambia menos de 0.05 entre E1 y E2.
6. **Error fijo en E1:** Ens-Vb-R supera a Ens-V0-R en F̄ppb con p99, con el IC por encima de 0. Un sesgo sumado a una sola estación es justo lo que delata la comparación con las vecinas.
7. **Error fijo en E1:** Ens-Vb-R empata con R3 en F̄ppb (el IC incluye el 0): las dos ideas se basan en las vecinas.
8. **Error fijo en E1:** con 10 ppb, el recall de Ens-Vb-R con p99 es menor que 0.5; con 20 ppb, mayor que 0.8.
9. Con error fijo, la caída de E1 a E2 es mayor que con la familia proporcional: un sesgo coherente en el grupo se parece todavía más a un cambio natural de la red.

## Cómputo
- **No se entrena nada:** sólo se puntúa con modelos congelados.
- **570 matrices:** 30 calendarios × 19 variantes. E1 tiene 7 tamaños (210 matrices); E2 y E3, 6 cada uno (180 y 180). A eso se suman los años limpios.
- **Una matriz** es un año del banco con los episodios de su calendario: 31 estaciones × días × 24 h, unas 271 560 ventanas horarias en un año completo. Cada ventana pasa por **11 modelos neuronales**: 5 de Ens-Vb-R, 5 de Ens-V0-R y L0 único. PARAAD y R3 cuestan poco.
- **Medición (2026-11-07):** se usó la matriz limpia de 2025 y no se calcularon métricas; los puntajes se descartaron.
  - Con 1 proceso de 16 hilos: 1.9 s por modelo y matriz anual, unos 21 s por matriz con los 11 modelos.
  - Fracción de ventanas que cambian respecto a la matriz limpia (2 calendarios de 2025): Vb 89–95 % y V0 31–39 %. Vb cambia casi todo porque su mediana de 60 días y sus vecinas propagan el episodio. Por eso no conviene reutilizar los puntajes limpios.
- **Estimación:** unas 3.3 h por corrida con un solo proceso. Se usan cuatro procesos en paralelo, en segundo plano, con dos corridas de inferencia que deben salir idénticas: en total, unas 4–6 h.

## Precisiones (2026-11-07, antes de generar planes o matrices)
Se fijaron con mediciones que no usan ataques: la matriz limpia de 2025 y la calibración de 2023.

1. **Historia desde 2020-01-01**, con todos los años limpios hasta el anterior, como en la calibración de 2023 de la revisión 22. Sustituye «el año anterior».
   - La razón: la base V0 tiene un respaldo, la media horaria acumulada, que usa toda la historia.
   - Con sólo el año anterior cambian 715 (V0) y 7 797 (Vb) de las 8 760 filas horarias de 2025.
2. **R3** se calcula exactamente como en la revisión 21: historia limpia 2020–2022 más los años limpios hasta el anterior, y umbrales comunes de la revisión 18 (p99 = 1.377631456451165, p99.9 = 2.559263562168503).
   - Así corre sin cambios: reproduce las 2023 de la revisión 20 con diferencia 0 y los mismos umbrales.
   - También reproduce las alarmas en limpio de la revisión 18: 119/3 (2024), 82/8 (2025) y 57/2 (2026) con p99/p99.9, en las mismas 8 977, 8 633 y 4 858 estación-días.
   - Entra como detector.
3. **PARAAD-SA:** integridad del modelo, la escala y el código verificada (SHA-256, LF). Umbrales p99 = 0.6405011077101032 y p99.9 = 0.8366300233950218, con «>» estricto.
4. **Numeración de calendarios** para la semilla de E3: k = 1…30 en el orden 2024_01…10, 2025_01…10, 2026_01…10.
5. **Choques.** Primero se colocan todos los episodios originales. Después, las estaciones añadidas, por número de episodio y en el orden de las vecinas. Los días ya ocupados se descartan, y lo que queda puede partirse en varios tramos.
6. **E3:** se eligen tantas estaciones como vecinas alterables tiene *s* (antes de los choques), entre las alterables que no son *s* ni sus vecinas de Vb.
7. **Estación-días evaluables:** las válidas para los cinco detectores en el año limpio. La validez no cambia con la alteración, porque las horas sin dato siguen sin dato.
8. **Recall entre escenarios (Q2 y predicciones 1–3, 5 y 9):** sobre todas las estación-días alteradas del escenario, la original y las añadidas. El desglose por papel es descriptivo.
9. **Cómo se juzgan las predicciones.**
   - La 5 se evalúa con δ = 50 % y p99.
   - La 9: la caída media de recall de Ens-Vb-R (p99) de E1 a E2 con *a* = 10, 20 y 40 ppb es mayor que con δ = 100, 50 y 20 %.
   - Las 1, 2, 3, 5, 8 y 9 se juzgan con el valor puntual, y se reporta su IC.
10. **Bloques del bootstrap:** estación × mes del banco (31 × 31), con los conteos sumados sobre los calendarios. Los mismos pesos sirven para todos los detectores y escenarios (pareado).

## Optimización (no cambia el método; cada una con su comprobación)
Mediciones en la matriz limpia de 2025, sin métricas.

| | Tiempo por modelo y matriz anual | Comprobación |
|---|---|---|
| `predict` estándar | 1.94 s | referencia |
| **a. XLA y modelos fusionados** (5 de Vb-R en un grafo; 5 de V0-R y L0 único en otro), lotes de 8 192 | 0.65 s | diferencia máx. 8.1e-7 frente a `predict` |
| **b. Sólo horas con dato** (75.6 % en 2025). Las demás se descartan de todos modos al juntar por día | ×0.76 | idéntico (diferencia 0) |
| **c. Sólo las ventanas que cambian** respecto a la matriz limpia del mismo año (Vb ≈ 90 %, V0 ≈ 35 %). El resto se copia del puntaje limpio | | idéntico (el puntaje de una ventana no depende del lote: diferencia 0) |

- **Criterio para a, fijado antes de usarla:** en la calibración de 2023 (la misma matriz de la revisión 22), la diferencia máxima de los puntajes diarios frente a `calibracion_2023.npz` debe ser < 1e-5 en Ens-Vb-R, Ens-V0-R y L0 único, y las alarmas con p99 y p99.9 deben ser idénticas. Si no se cumple, se usa `predict` estándar.
- **Comprobación de c antes de lanzar:** en dos matrices, el puntaje incremental y el completo deben coincidir con diferencia 0.
- **Se reportan las «decisiones frágiles»:** estación-días con |puntaje − umbral| < 1e-5.
- **Sin cambios:** PARAAD (0.5 s por matriz anual) y R3 (≈1 s) se calculan completos.

### Resultado de la comprobación de la optimización a (2026-11-07, antes de puntuar la revisión 23)
- **XLA no cumple el criterio.** En 2023 la diferencia máxima fue pequeña (3.7e-8 en Ens-Vb-R, 2.1e-8 en Ens-V0-R y 4.0e-8 en L0 único), pero con p99 hubo 91 alarmas en vez de 90 en los tres detectores. Con p99.9 coincidieron (9).
- **La causa:** el umbral registrado es uno de los 9 097 puntajes de 2023, porque `umbral_falsas_alarmas` lo elige entre ellos. Esa estación-día tiene puntaje igual al umbral, y cualquier cálculo que no sea idéntico bit a bit puede pasarla de «= u» a «> u».
- **Decisión, la declarada:** no se usa XLA. Se usa `tf.function` por modelo, con lotes fijos de 8 192. En la matriz de 2025 dio diferencia 0 frente a `predict`, y se comprueba en 2023 con diferencia 0 exigida.
- Las optimizaciones b y c se conservan: son exactas (diferencia 0 en las dos matrices de prueba).
- El registro de la comprobación fallida está en `results/linea_base/rev23/validacion_xla_no_cumple.json`.
