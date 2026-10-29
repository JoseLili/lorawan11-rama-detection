# Diagnóstico de redundancia de entradas L0 — 2026-10-28

Alcance: análisis del código y de las 19 840 ventanas auditadas de 2020–2021,
no entrenamiento, no selección con 2022 y no modificación de las entradas.
Las propuestas de retirar o reorganizar características siguen siendo hipótesis.
Código: `analizar_redundancia_l0.py`. Resultados en
`results/exploracion_tinto_2022/redundancia_20261028/final1/` y `final2/`.

## 1. Inventario y criterio

Cada ventana tiene 120 relativas, 120 máscaras, 120 comparaciones horarias a14
y 48 valores de hora (24 senos + 24 cosenos), total 408.

Redundancia por construcción: la característica se puede reconstruir con las
otras entradas y las constantes disponibles, no solo predecir aproximadamente
porque haya correlación. Redundancia empírica: similitud observada en esta muestra,
sin garantía fuera de ella. Utilidad predictiva: requiere comparar detectores;
este análisis NO la mide. Una característica derivada puede facilitar el aprendizaje
incluso cuando no aporta información independiente.

## 2. Hora: repetición demostrada, conservar la fase final

La ventana es una rejilla continua de 24 horas y cada desfase es conocido.
Con seno/coseno en t y un desfase k, las horas anteriores son:

- sin(hora t−k) = sin(hora t) cos(2πk/24) − cos(hora t) sin(2πk/24).
- cos(hora t−k) = cos(hora t) cos(2πk/24) + sin(hora t) sin(2πk/24).

Se reconstruyeron los 48 valores en todas las ventanas. Error máximo absoluto:
1.711427111139585e−8 para seno y coseno, compatible con las entradas float32.
No es identidad de bits: redondeos de la codificación original persisten.

Conclusión: se pueden representar estas 48 columnas mediante las dos de t,
conservando la fase horaria a esa precisión. Propuesta: 408−46 = 362 entradas.
El número de columnas no equivale al rango matricial exacto en coma flotante;
se guardaron los valores singulares, sin afirmar rango exacto dos a toda tolerancia.

No se valida quitar TODA la hora. Que se repita cada día no la hace deducible
del ozono o de la posición relativa de la ventana. Un modelo que recibe ventanas
terminadas a distintas horas necesita conocer la fase o inferirla de otras señales.
Seno/coseno no codifican día del año ni calendario de 365/366 días.

Una entrada más compacta no garantiza que una CNN aprenda igual: cambia la
facilidad de acceso a la información. El control original de 408 se conserva.

## 3. La comparación de L0 NO es la decisión R3

L0 recibe la comparación horaria a14 con perfil causal de MEDIA. R3 usa perfil
causal de MEDIANA, agregación por día y dominancia frente a otras estaciones.
La alarma R3, su umbral y su decisión diaria no se entregan a L0.

En L0, para una estación s, relativa r_s y escala a_s:

    a14_s = (r_s − promedio de r_vecinas disponibles) / a_s

Requiere relativa propia disponible y al menos dos relativas vecinas disponibles;
si no, queda NaN antes del relleno con cero. La máscara de lectura NO siempre
indica si ya existe historia suficiente para calcular la relativa.

### Objetivo: derivable solo bajo condiciones adicionales

Sus cuatro vecinas están explícitas en la ventana. Intentamos reconstruir a14
del objetivo usando sus relativas y máscaras, más la escala del objetivo tomada
del manifiesto (dato externo al tensor). Tolerancia: atol=rtol=1e−5.

- Coinciden 476 129 de 476 160 celdas estación-hora (24 por ventana).
- Hay 31 discrepancias, algunas con error apreciable (máximo 1.355344).
- Se inspeccionaron las matrices originales de cada caso, solo entrenamiento
  2020–2022: las 31 se explican por lecturas observadas SIN perfil causal disponible.
- Recalculando con disponibilidad del perfil sin imputar, todos los casos
  reproducen a14 guardada dentro de la tolerancia.

Por tanto, no afirmar que a14 del objetivo es una copia eliminable sin más.
La escala depende de la estación real y NO es una columna explícita del modelo
compartido sin identificador de estación; la disponibilidad del perfil tampoco
siempre se deduce de la máscara de lectura. El éxito de una reconstrucción que
usa metadatos no demuestra reconstruibilidad exclusiva desde las restantes X.
Además, reconstruir una característica derivada puede imponer trabajo adicional
al clasificador y cambiar el rendimiento aunque no se pierda información.

### Vecinas: contexto que no está completamente en la ventana

Cada vecina tiene SU PROPIO vecindario. Entre los 31 objetivos × cuatro roles
vecinos = 124 casos, 120 requieren alguna estación externa al grupo local de cinco.
Ejemplo de ACO:

- Grupo visible: ACO, LLA, SAG, MON y VIF.
- La comparación de LLA usa SAG, LPR, VIF y FAR.
- LPR y FAR no son canales explícitos de esa ventana, pero influyen en a14 de LLA.

Quitar las cuatro comparaciones de vecinas puede retirar contexto adicional,
no solamente expresiones repetidas de las relativas visibles. El resultado de
huellas geográficas es estructural y no depende del valor de correlaciones.
Archivo: `dependencias_vecindarios.csv`.

## 4. Máscaras: ambigüedad observada, conservarlas como referencia

En las 2 380 800 celdas sensor-hora de la muestra (cinco roles por ventana):

- 525 369 tienen máscara 0 y relativa 0.
- 9 849 tienen máscara 1 y relativa 0.

El segundo grupo incluye relativas cero legítimas y también lecturas sin perfil
que se imputaron: no se interpreta todo ese grupo como lectura igual a su perfil.
En ambos grupos el valor numérico cero por sí solo no permite recuperar la máscara.
Archivo: `ambiguedad_cero_y_mascaras.csv`, separado por rol.

No se demostró redundancia de máscaras; quitar un cero o dejar huecos no es una
codificación de ausencia definida para TINTO. Alternativa futura: máscara en otro
canal, preservando la señal, en lugar de eliminarla. Eso es una representación
nueva, no una reducción demostrada como inocua.

## 5. Geografía: puede reorganizar, no elimina redundancia

Se comprobaron solo claves/latitud/longitud del catálogo congelado de L0:
32 estaciones con coordenadas, 32 ubicaciones distintas. Los 31 objetivos tienen
cinco ubicaciones distintas en su grupo visible.

Usar coordenadas para colocar sensores es viable como diseño, pero en cada
ubicación tendríamos 24 horas × tres tipos = 72 valores. Superponerlos en un único
píxel repetiría la colisión. Hay que separar al menos tres dimensiones:

- Estación: posición geográfica o rol local.
- Tiempo: desfase de 0 a 23 horas.
- Tipo: relativa, máscara y comparación.

Una posible familia geográfica usaría cuadrícula de estaciones y canales para
hora/tipo. También necesita una regla explícita para dos estaciones que caigan
en la misma celda al discretizar. Aquí solo se comprobó que las coordenadas
continuas son distintas; no se validó ninguna cuadrícula geográfica.

Como la identidad de v1..v4 cambia por objetivo, una geografía absoluta no es el
mapa de roles compartido de L0. La posición puede revelar identidad/ubicación
que el tensor original no explicita. Debe declararse y compararse con controles
que reciban la misma información. Una imagen geográfica no es TINTO-PCA original.

## 6. Recomendación basada en lo validado

| Bloque | Evidencia | Acción propuesta, aún no aplicada |
|---|---|---|
| Hora repetida | Reconstrucción 48→2 validada con error float32 | Probar 362 entradas, conservando hora final |
| a14 del objetivo | Reconstrucción casi completa CON escala externa y disponibilidad de perfil | No declararla eliminable; estudiar como ablación separada |
| a14 de vecinas | Contexto externo en 120/124 casos | Conservar por ahora |
| Máscaras | Cero ambiguo en observados y faltantes | Conservar, o reubicar en otro canal en variante explícita |
| Geografía | Cinco ubicaciones únicas por grupo; 72 valores por ubicación | Diseño alternativo que separa estación/tiempo/tipo, no sustituto automático |

Próximo experimento propuesto: comparar 408 originales frente a 362 con hora
compacta, ajustando mapas solo en entrenamiento y midiendo colisiones. No se
asegura que esta compresión por sí sola resuelva el problema de PCA. Aún no se
retiran bloques ni se cambia el comparador L0. Si posteriormente se estudian
ablaciones predictivas, el modelo temporal de control debe recibir la misma
entrada modificada y declararse como control nuevo, sin sobrescribir L0.

## 7. Limitaciones y reproducción

No hay pruebas de rendimiento predictivo ni decisiones sobre examen. Las
estadísticas descriptivas de correlación entre los 17 canales se guardan como
contexto; una correlación alta no autoriza retirar entradas. Las ventanas se
solapan, por lo que no se presentan p-valores ni se asumen independientes.

Repetir desde la raíz con `.venv/bin/python`:

```sh
.venv/bin/python experiments/exploracion_tinto/analizar_redundancia_l0.py --salida results/exploracion_tinto_2022/redundancia_nueva/corrida1
```

Fuentes de definición: `lstm_local.indices_locales`, `evaluacion_red.relativas`,
`_sin_escala`, `columnas_vecinas`, revisión 12 del protocolo de anomalías y el
catálogo geográfico congelado. La revisión 14 define entradas con media; la
revisión 12 define R3 con mediana y dominancia: no se intercambian.

Las dos ejecuciones finales terminaron correctamente: los diez archivos de
resultados/configuración tienen SHA-256 idénticos. Constancia en
`results/exploracion_tinto_2022/redundancia_20261028/reproducibilidad.json`.
