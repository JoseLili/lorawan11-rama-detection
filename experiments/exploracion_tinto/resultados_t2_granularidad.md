# TINTO T2 — resultados: reentreno de T1 y cuatro formas de imagen (2026-10-29)

Diseño y regla registrados antes de entrenar: [diseno_t2_granularidad.md](diseno_t2_granularidad.md).
Resultados en `results/exploracion_tinto_2022/t2_granularidad/evaluacion/`.

## Origen de cada número

- **EH, ED, RH y RD:** CNN **recién entrenadas** en Colab con GPU NVIDIA L4 (TensorFlow 2.21,
  Keras 3.13), dos corridas cada una con `fijar_semilla(42)`. Las dos corridas salieron
  **idénticas** (pérdidas, épocas y puntajes): el determinismo de TensorFlow funcionó también en GPU.
- **L0 y T1 época 5:** cargados de disco; se reusan sus puntajes diarios guardados de la evaluación
  de T1 (no se recalcularon).
- Antes de entrenar se comprobó que el armado nuevo de imágenes reproduce los puntajes guardados de
  T1 época 5 (diferencia máxima 9 × 10⁻⁸). El evaluador reproduce exactamente los F1 publicados de T1.

## Entrenamiento (EarlyStopping completo, sin parada manual)

| Variante | Imágenes de ajuste | Parámetros | Épocas | Mejor época | Pérdida de validación |
|---|---:|---:|---:|---:|---:|
| EH estación-hora | 1 357 800 | 34 081 | 15 | 7 | 0.02572 |
| ED estación-día | 356 420 | 34 081 | 16 | 8 | 0.02542 |
| RH red-hora | 350 420 | 133 375 | 19 | 11 | 0.03980 * |
| RD red-día | 14 620 | 133 375 | 11 | 3 | 0.04749 * |

\* RH y RD promedian 31 salidas por imagen: su pérdida no se compara directamente con EH y ED.
Referencias: T1 con parada manual 0.02640 (época 5); L0 0.02245 (época 1).

**El reentreno de T1 (EH) confirma el cierre anterior.** Con EarlyStopping completo eligió la época 7
y mejoró un poco (F̄ 0.308 → 0.315), pero sigue por debajo de L0.

## F1 por estación-día en 2022 (10 calendarios, 9 661 estación-días comunes)

| Detector | p99 δ100 | p99 δ50 | p99 δ20 | **F̄ p99** | p99.9 δ100 | p99.9 δ50 | p99.9 δ20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **L0** (referencia) | 0.452 | 0.466 | 0.147 | **0.355** | 0.500 | 0.322 | 0.016 |
| T1 época 5 (cierre anterior) | 0.428 | 0.411 | 0.086 | 0.308 | 0.447 | 0.204 | 0.009 |
| EH estación-hora | 0.433 | 0.417 | 0.096 | 0.315 | 0.481 | 0.248 | 0.009 |
| ED estación-día | 0.446 | 0.412 | 0.109 | 0.322 | **0.636** | **0.401** | 0.014 |
| RH red-hora | 0.278 | 0.166 | 0.026 | 0.157 | 0.400 | 0.150 | 0.005 |
| RD red-día | 0.060 | 0.029 | 0.016 | 0.035 | 0.065 | 0.018 | 0.007 |

F1 sin ataque con p99: 0.013 o menos para todos.

## Aplicación de la regla registrada

- Para pasar se necesitaba F̄ ≥ 0.375 (L0 + 0.02) en las dos corridas. **Ninguna variante pasa.**
  La mejor es ED con 0.322, es decir 0.033 **por debajo** de L0.
- Diferencia entre corridas: 0 en las cuatro. La distancia entre la mejor variante (ED 0.322) y la
  peor (RD 0.035) es mucho mayor que ese ruido: **la forma de la imagen sí importa**, pero en contra
  de la red completa, no a favor de TINTO.
- **TINTO queda cerrado como resultado negativo** según la regla.

## Lo que se ve (descripción, no elección)

1. **Estación (EH, ED) contra red completa (RH, RD).** Meter las 31 estaciones en una imagen con 31
   salidas hunde el resultado: RH queda a la mitad de L0 y RD casi en el azar. Pasó lo mismo con el
   LSTM de 31 salidas de la revisión 13. Con una imagen de toda la red, el modelo tiene que aprender
   en qué píxeles está cada estación, y cada estación tiene pocos ejemplos alterados.
   RD además tiene solo 14 620 imágenes de ajuste y paró en la época 3: ahí la falta de ejemplos y la
   forma de la imagen están mezcladas, y no se pueden separar.
2. **Hora contra día (EH contra ED).** Casi lo mismo con p99 (0.315 contra 0.322, IC de ED contra L0
   que en δ = 50 y 20 % queda por debajo de cero).
3. **Observación secundaria, no adoptable: ED con p99.9.** Con el umbral de 0.1 % de falsas alarmas,
   ED supera a L0 en δ = 100 % (0.636 contra 0.500, IC95 de la diferencia [+0.084, +0.188]) y en
   δ = 50 % (0.401 contra 0.322, IC95 [+0.037, +0.124]). No cambia la decisión, por tres razones:
   - la medida principal registrada es p99, y ahí ED pierde;
   - el umbral p99.9 sale de los ~10 puntajes más altos de 9 661 estación-días limpias, así que es
     muy inestable;
   - se notó después de ver los resultados, sobre el mismo 2022 que eligió la época.

   Lo honesto es reportarlo como hipótesis: un detector que mira el día completo podría separar mejor
   los casos más claros. Probarlo requeriría un protocolo propio y datos que no se hayan visto.

## Límites

- 2022 se usó para el EarlyStopping y para evaluar, igual que en L0 y en T1: vale para comparar,
  no como desempeño absoluto.
- Una sola arquitectura pequeña por variante, sin búsqueda de hiperparámetros ni pesos de clase.
- Es TINTO-PCA con asignación única y sin difuminado. Con TINTO original en 64 × 64, 2 261 de las
  2 352 entradas de red compartirían píxel con otra entrada, así que la asignación única era
  indispensable.
- Los intervalos no incluyen la incertidumbre del umbral.

## Ficha de la gráfica `f1_p99_granularidad.png`

- **Qué compara:** L0 contra las cuatro formas de imagen TINTO, con el mismo umbral relativo.
- **Eje X:** intensidad de la alteración δ (100, 50 y 20 %) en los calendarios 01–10 de 2022.
- **Eje Y:** F1 por estación-día. Positivo = la estación estuvo dentro de un episodio ese día.
  Alerta = el puntaje diario pasa el umbral del detector.
- **Umbral:** el de cada detector, calculado para dar 1 % de falsas alarmas en 2022 limpio (p99),
  en las mismas 9 661 estación-días.
- **Puntaje diario:** EH, RH y L0 promedian la probabilidad de las horas con dato (mínimo 12); ED y RD
  dan una probabilidad por día directamente.
- **Tipo de medida:** F1, la media armónica de precisión y recall, juntando los 10 calendarios.
- **Línea punteada:** el F1 que sale sin ataque (mismas etiquetas aplicadas a 2022 limpio). Es el piso
  del azar; el mayor de los cinco es 0.013.
- **Origen:** L0 cargado de disco; EH, ED, RH y RD recién entrenados en GPU (dos corridas idénticas).
  Se grafica la corrida 1.
- **Tabla de la gráfica:** la sección "F1 por estación-día" de este documento.
