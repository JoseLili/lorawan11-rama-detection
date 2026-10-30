# Resultados del examen Barcelona: L0, V4 y PARAAD

Fecha: 2026-10-29. **Fase proporcional completada**, sin reentrenamiento ni
recalibración. Todos los modelos se cargaron de disco. Los tres respaldos
terminales están verificados y las tres VMs se liberaron.

## Diseño y controles

Se siguió `registro_examen_barcelona_2018_2019.md`: 13 estaciones propias de
municipios AMB, O3 en µg/m³, 2018 principal y 2019 complementario. Diez
calendarios por año, episodios de1–7 días, signo± y δ={100,50,20,10,5}%.
L0 fue entrenado sólo con δ50; V4 y PARAAD sin inyecciones de entrenamiento.
Umbrales p99/p99.9 y p95 horario V4, fijados con2017 limpio, se conservaron.

Los universos son4,549 estación-días en2018 y4,567 en2019. Los diez planes
suman368 positivos experimentales en2018 (0.8090% de45,490 exposiciones)
y417 en2019 (0.9131% de45,670). Son realizaciones de los mismos casos
ambientales, no diez muestras ambientales independientes.

Se evaluaron102 matrices por detector (100 alteradas y dos limpias), más
el control2017. Cada inferencia se repitió dos veces con igualdad exacta:
306 pares de examen y tres pares de control. La comparación2017 contra la
calibración congelada dio **diferencia máxima0 y cero cambios de alerta** en
los tres métodos. Los parches de transferencia reconstruyen bit a bit las
entradas ya generadas. No se cambió ningún parámetro mirando estos resultados.

Hubo una corrección de representación temporal us/ns en el control previo,
y fallos intermitentes de conexión del supervisor. Los intentos/diagnósticos
se conservaron; los workers continuaron en sus VMs, sin reiniciar la inferencia
por las interrupciones de respaldo. Se verificaron snapshots, unidades completas,
hashes, soporte diario y cierre de todas las VMs.

## F1 principal: p99

| Año | δ | L0 supervisado | V4 | PARAAD |
| --- | --- | --- | --- | --- |
| 2018 | 100% | 0.4839 | 0.4118 | 0.4995 |
| 2018 | 50% | 0.5000 | 0.2519 | 0.3043 |
| 2018 | 20% | 0.1437 | 0.0516 | 0.0706 |
| 2018 | 10% | 0.0269 | 0.0185 | 0.0224 |
| 2018 | 5% | 0.0082 | 0.0124 | 0.0150 |
| 2019 | 100% | 0.4424 | 0.2364 | 0.3128 |
| 2019 | 50% | 0.4353 | 0.1056 | 0.1911 |
| 2019 | 20% | 0.1071 | 0.0243 | 0.0582 |
| 2019 | 10% | 0.0165 | 0.0066 | 0.0270 |
| 2019 | 5% | 0.0104 | 0.0100 | 0.0168 |

La estimación se obtiene sumando TP/FP/FN/TN de los diez calendarios, no
promediando F1. No se eligió un δ o año para presentar sólo ventajas.

### Detalle en δ50

| Año | Detector | Precisión | Recall | F1 [IC95%] | AP | ROC-AUC |
| --- | --- | --- | --- | --- | --- | --- |
| 2018 | L0 | 0.3673 | 0.7826 | 0.5000 [0.4178, 0.5855] | 0.6637 | 0.9762 |
| 2018 | V4 | 0.2413 | 0.2636 | 0.2519 [0.1792, 0.3316] | 0.2284 | 0.8101 |
| 2018 | PARAAD | 0.2500 | 0.3886 | 0.3043 [0.2253, 0.4020] | 0.2789 | 0.8379 |
| 2019 | L0 | 0.3034 | 0.7698 | 0.4353 [0.3597, 0.5161] | 0.6127 | 0.9704 |
| 2019 | V4 | 0.0760 | 0.1727 | 0.1056 [0.0694, 0.1464] | 0.0611 | 0.7615 |
| 2019 | PARAAD | 0.1265 | 0.3909 | 0.1911 [0.1376, 0.2565] | 0.1179 | 0.8231 |

AP es average precision; no área trapezoidal de la curva PR. ROC-AUC puede
ser alta aun con precisión moderada porque los positivos son escasos.

## Comparaciones pareadas

IC95% percentiles de2,000 bootstrap estación×mes, semilla `[42,238,año]`.
Cada uno de los156 bloques observados conserva juntas las diez realizaciones
y los tres detectores. Se usan los mismos remuestreos para las diferencias.
Los intervalos son por contraste, sin corrección por multiplicidad.

| Año | δ | PARAAD−V4 [IC95%] | L0−PARAAD [IC95%] | L0−V4 [IC95%] |
| --- | --- | --- | --- | --- |
| 2018 | 100% | +0.0878 [-0.0091, +0.2027] | -0.0156 [-0.1216, +0.0746] | +0.0722 [-0.0227, +0.1675] |
| 2018 | 50% | +0.0523 [-0.0231, +0.1373] | +0.1957 [+0.1045, +0.2798] | +0.2481 [+0.1502, +0.3459] |
| 2018 | 20% | +0.0191 [-0.0180, +0.0636] | +0.0731 [+0.0260, +0.1242] | +0.0921 [+0.0405, +0.1505] |
| 2018 | 10% | +0.0039 [-0.0174, +0.0269] | +0.0045 [-0.0261, +0.0332] | +0.0084 [-0.0173, +0.0345] |
| 2018 | 5% | +0.0027 [-0.0141, +0.0209] | -0.0068 [-0.0293, +0.0120] | -0.0041 [-0.0201, +0.0116] |
| 2019 | 100% | +0.0764 [+0.0155, +0.1524] | +0.1296 [+0.0388, +0.2112] | +0.2060 [+0.1369, +0.2780] |
| 2019 | 50% | +0.0855 [+0.0399, +0.1437] | +0.2442 [+0.1540, +0.3294] | +0.3297 [+0.2583, +0.4121] |
| 2019 | 20% | +0.0339 [+0.0110, +0.0618] | +0.0489 [+0.0061, +0.0961] | +0.0828 [+0.0432, +0.1293] |
| 2019 | 10% | +0.0204 [+0.0030, +0.0407] | -0.0105 [-0.0321, +0.0106] | +0.0099 [-0.0040, +0.0264] |
| 2019 | 5% | +0.0068 [-0.0127, +0.0246] | -0.0064 [-0.0230, +0.0087] | +0.0005 [-0.0173, +0.0156] |

La comparación principal sin etiquetas es PARAAD–V4. PARAAD tiene F1 puntual
mayor que V4 en las cinco intensidades de ambos años con p99. En2018 los
cinco intervalos de diferencia incluyen0, por lo que no se sostiene una
ventaja concluyente en esa prueba principal. En2019 excluyen0 a favor de
PARAAD para δ100,50,20 y10; δ5 sigue sin separación clara.

L0 supera a ambos en δ50 yδ20 con intervalos de diferencia positivos en
los dos años, con p99. Enδ100 de2018, PARAAD tiene el mayor F1 puntual
(0.4995 frente a0.4839 de L0), pero el intervalo L0−PARAAD incluye0.
En2019δ100 L0 queda por encima de ambos con intervalos positivos.
Estas ventajas de L0 incluyen el efecto de su entrenamiento supervisado;
no prueban que su arquitectura aislada sea superior.

Conδ5 yδ10 los F1 absolutos son bajos (aproximadamente0.007–0.027). No se
concluye capacidad sólida de detectar perturbaciones pequeñas por observar
un valor puntual ligeramente mayor que otro. Véanse los controles siguientes.

## Control sin inyección

Los mismos modelos puntúan la matriz limpia y se conservan las etiquetas
programadas de cada calendario. Este control mide coincidencias con el plan
sin alterar la señal; **no es la tasa limpia anual de falsas alarmas**.
Como los planes se comparten entre intensidades, su F1 es el mismo en los
cincoδ de cada año/umbral:

| Año | Umbral | L0 | V4 | PARAAD |
| --- | --- | --- | --- | --- |
| 2018 | p99 | 0.0110 | 0.0123 | 0.0100 |
| 2018 | p99.9 | 0.0000 | 0.0000 | 0.0123 |
| 2019 | p99 | 0.0104 | 0.0117 | 0.0116 |
| 2019 | p99.9 | 0.0000 | 0.0000 | 0.0178 |

Enδ5, varios resultados están cerca de estos controles. No se han calculado
intervalos ataque−sin ataque: los IC pareados publicados comparan detectores
bajo cada condición, por lo que no se atribuye significación a esas pequeñas
diferencias contra el control sin un contraste adicional registrado.

## Estabilidad de falsas alarmas

Aquí todos los casos del año limpio son negativos experimentales. El target
se fijó con2017:45/4,536 alertas p99 y4/4,536 p99.9. No se garantiza la
misma tasa en años posteriores:

| Año | Detector | Casos | Tasa limpia p99 (alertas) | Tasa limpia p99.9 (alertas) |
| --- | --- | --- | --- | --- |
| 2018 | L0 | 4549 | 0.7914% (36) | 0.0659% (3) |
| 2018 | V4 | 4549 | 0.6155% (28) | 0.0000% (0) |
| 2018 | PARAAD | 4549 | 0.9453% (43) | 0.2638% (12) |
| 2019 | L0 | 4567 | 1.1824% (54) | 0.1314% (6) |
| 2019 | V4 | 4567 | 1.7079% (78) | 0.3503% (16) |
| 2019 | PARAAD | 4567 | 2.4743% (113) | 0.8102% (37) |

En2019 aumenta la tasa limpia de los tres métodos. PARAAD llega a2.4743%
con p99 y0.8102% con p99.9; el nominal de calibración era1%/0.1%. Este
cambio debe acompañar cualquier afirmación sobre recall o F1; no se corrige
recalibrando con el examen. «Limpio» significa sin inyección, sin certificar
que las series originales no contengan fallos reales.

## Segundo umbral registrado: p99.9

| Año | δ | L0 supervisado | V4 | PARAAD |
| --- | --- | --- | --- | --- |
| 2018 | 100% | 0.6644 | 0.4878 | 0.6112 |
| 2018 | 50% | 0.6019 | 0.2120 | 0.2740 |
| 2018 | 20% | 0.0633 | 0.0108 | 0.0403 |
| 2018 | 10% | 0.0100 | 0.0054 | 0.0204 |
| 2018 | 5% | 0.0050 | 0.0000 | 0.0164 |
| 2019 | 100% | 0.6597 | 0.2776 | 0.4341 |
| 2019 | 50% | 0.6033 | 0.1113 | 0.2494 |
| 2019 | 20% | 0.0448 | 0.0069 | 0.0522 |
| 2019 | 10% | 0.0042 | 0.0000 | 0.0203 |
| 2019 | 5% | 0.0000 | 0.0000 | 0.0203 |

L0δ50 obtiene F1 de0.6019/0.6033 en2018/2019 con este umbral. Su precisión
es0.6964/0.6492 y recall0.5299/0.5635: reduce alertas y pierde recall respecto
a p99. Se conserva p99 como análisis principal, tal como se registró.
Los IC de este segundo umbral y las métricas por calendario están en los CSV.

## Alcance de las conclusiones

Este brazo confirma que la metodología RAMA puede ejecutarse en Barcelona
con modelos nuevos, planes y evaluación comunes. En estas condiciones,
L0 supervisado aporta una ventaja en δ20% y δ50% con p99; entre los métodos
sin etiquetas, PARAAD muestra mejor estimación puntual que V4 y una ventaja
separada por los intervalos en varias condiciones de2019. No hay un ganador
universal para cualquier intensidad, año o umbral.

No es una reproducción literal del artículo: son13 estaciones propias,
calendario cronológico y bloques UTC con exclusión temporal explícita,
máscaras de faltantes y umbral limpio fijo. No son las ocho estaciones ni
el umbral móvil con etiquetas del trabajo original. La comparación no aisla
el efecto de ciudad, prevalencia, supervisión o arquitectura. Los bloques
estación×mes capturan dependencia temporal intrabloque; no resuelven toda
la dependencia espacial o entre meses. No se interpretan los múltiples
contrastes como una prueba global única.

La fase proporcional está cerrada. El escenario aditivo quedó registrado
como complemento, pero **no se evaluó en estas tablas**. No se hace commit
ni se alteran los resultados RAMA o los modelos/umbrales congelados.

## Artefactos y figura

- [Figura F1 p99](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/f1_barcelona_p99.png) y [ficha](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/ficha_figura.md); inspeccionadas visualmente, ejes y leyenda legibles.
- [Métricas agregadas completas](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/metricas.csv).
- [Métricas por calendario](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/por_calendario.csv).
- [IC de F1/precisión/recall](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/intervalos.csv).
- [Diferencias pareadas, ambos umbrales](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/diferencias_pareadas.csv).
- [Tasas limpias anuales](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/tasa_limpia.csv).
- [Verificación final](/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/results/barcelona_paraad/examen_colab_2018_2019/resumen/verificacion_final.json).

`resumir_examen.py` calculó las métricas e intervalos dos veces con igualdad
exacta, usando los mismos puntajes congelados. Se guardan120 filas agregadas,
1,200 por calendario,360 intervalos y120 diferencias pareadas, incluidos
los controles sin ataque. No se han reutilizado los años de examen para
seleccionar nuevas configuraciones.
