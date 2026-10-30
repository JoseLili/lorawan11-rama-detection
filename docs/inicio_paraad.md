# Inicio: PARAAD en nuestro escenario (paso 4)

Preparado por Claude el 2026-10-27, a pedido del tesista, mientras corría la revisión 19. Es el
punto de partida para diseñar la revisión 20. **No es un protocolo aprobado:** antes de programar,
el diseño se registra y lo aprueba el tesista.

## 1. Contexto

- **El pedido del asesor (junta del 2026-10-26, A7):** poner al grupo de Barcelona en la misma tabla
  que L0, R3 y el V4, **en el mismo escenario**. Hay dos caminos: correr su método con nuestros
  datos, o el nuestro con los suyos. Si su método no usa percentil, va la misma fila en las dos
  tablas (p99 y p99.9).
- **Por qué importa:** es la comparación con un método publicado que hoy le falta a la tesis. Ese
  hueco se había señalado como debilidad.
- **El trabajo:** PARAAD. Allka, Ferrer-Cid, Barceló-Ordinas y García-Vidal (2024), *Pattern-Based
  Attention Recurrent Autoencoder for Anomaly Detection in Air Quality Sensor Networks*, IEEE Trans.
  Network Science and Engineering 11(6), 6372–6381, doi:10.1109/TNSE.2024.3454459.
  - El texto completo está en [UPCommons](https://upcommons.upc.edu/entities/publication/d4d25d74-89d7-4e15-8c8e-41bd923bafa2).
  - Ficha en `docs/referencias_literatura.md`; resumen en `docs/progreso.md` (búsqueda del
    2026-10-23).

## 2. Lo que ya sabemos de PARAAD (de nuestras notas; verificar contra el texto)

- **Datos:** O₃ de 8 estaciones de referencia de Barcelona, 2014–2019.
- **Método:** un autoencoder recurrente con atención, **no supervisado**, que mira **bloques de un
  día** (24 h) de todas las estaciones. Hay dos variantes: PARAAD-SA y PARAAD-MH.
  - Un autoencoder aprende a reconstruir días normales. Si un día se reconstruye mal, es
    sospechoso.
- **Anomalías sintéticas:**
  - **sesgo:** al 30 % de los sensores y al 30 % de sus días se les suma β desviaciones típicas a la
    señal diaria estandarizada, con β ~ |N(0, σ²)| y σ = 2, es decir, ~1.6 desviaciones en
    promedio, todo el día;
  - **deriva lenta.**
- **Resultados con datos reales:** TPR (recall) de 0.81 y precisión de 0.84 por estación-día,
  localizando la estación.
- **Ablación:** con bloques de 1 hora la precisión baja (0.70 contra 0.84 en PARAAD-SA; 0.34
  contra 0.79 en PARAAD-MH).
- **Umbral:** según nuestras notas, se optimiza por exactitud en una ventana de 30 días y se aplica
  al siguiente. Parece usar etiquetas, lo que es más optimista que nuestro umbral fijo de 2023
  limpio. **Hay que confirmarlo.**
- **Dicen explícitamente** que un sesgo pequeño es indistinguible de los datos normales.
- **Código:** no se encontró un repositorio público (búsqueda del 2026-10-27). Habría que
  reprogramarlo a partir del texto, o escribirles a los autores.
- **Sus datos:** el tesista dijo en la junta que ya los tiene. **Falta saber dónde están y en qué
  formato.**

## 3. Lo que se quiere lograr

1. **Una fila de PARAAD en las tablas,** con los mismos años, calendarios, estación-días, umbrales
   y métricas que L0, R3, V4 y V4S.
2. **«Peras con peras»:**
   - PARAAD es **no supervisado**, igual que el V4. Su comparación principal es **PARAAD contra el
     V4**: los dos sin etiquetas;
   - L0 y R3 quedan como referencia;
   - si PARAAD le gana al V4, la tesis puede decir que un método publicado mejora la línea base,
     y medir cuánto más aporta L0.
3. **Saber si los números de PARAAD en Barcelona se trasladan a la RAMA.** Son 32 estaciones contra 8
   y anomalías más chicas: nuestro δ = 100 % mueve unos 25 ppb, contra ~1.6 desviaciones todo el
   día de ellos.

## 4. Cómo lograrlo

### Camino recomendado: su método con nuestros datos

1. **Leer el texto completo** y anotar:
   - la arquitectura: capas, atención y qué es exactamente el «patrón»;
   - los hiperparámetros y la normalización;
   - cómo convierten el error de reconstrucción en puntaje por estación-día;
   - cómo fijan el umbral.

   Sin esto, no se programa.
2. **Prueba de fidelidad, muy recomendable si tenemos sus datos:**
   - reproducir aproximadamente su resultado (TPR 0.81 y precisión 0.84) en Barcelona, con su
     inyección de sesgo y su umbral;
   - así se defiende ante un sinodal que lo comparado es PARAAD y no «una mala versión nuestra»;
   - si no sale parecido, se declara y se investiga antes de seguir.
3. **Registrar la revisión 20,** antes de programar con datos de la RAMA:
   - **entrenamiento no supervisado** con 2020–2022 limpio, con 2022 como validación de la pérdida
     de reconstrucción, sin mirar 2024–2026;
   - **entrada:** bloques de 24 h de las 32 estaciones de la matriz;
   - **puntaje:** el error de reconstrucción de cada estación en su día;
   - **umbrales:** p99 y p99.9 de 2023 limpio, como todos. Su umbral original se puede reportar
     aparte, como contraste;
   - `fijar_semilla(42)` inmediatamente antes de construir y de entrenar, y todo dos veces;
   - **elección con 2022:** si el artículo deja algo abierto (por ejemplo SA contra MH), se elige
     sólo con 2022 y con una regla escrita antes.
4. **Código:**
   - `src/detect/paraad.py` (el modelo);
   - `experiments/anomalias_red/entrenar_paraad.py`;
   - una evaluación que reuse la de las revisiones 18 y 19;
   - pruebas de forma y de reproducibilidad.
5. **Colab, sólo CPU** (la GPU no es determinista): entrenamiento y control repetidos.
6. **Evaluación con los detectores congelados:**
   - 2024, y 2025–2026 una sola vez (regla de la revisión 18);
   - el escenario actual y los dos de la revisión 19 (una a la vez y un solo nodo);
   - los cinco δ.

### Camino complementario: los nuestros con sus datos

- Correr L0, R3 y el V4S en los datos de Barcelona, con su tipo de anomalía.
- Es más trabajo:
  - hay que generar calendarios con su inyección;
  - hay que entrenar L0 y el V4S otra vez, porque son supervisados;
  - con 8 estaciones, cada una tiene 7 posibles vecinas en lugar de 31.
- Se decide después del camino recomendado, según los datos y el tiempo.

### Conexión con el paso 5 (error fijo)

- Su anomalía de sesgo es **sumada**, no proporcional, igual que el error fijo de ±10 o ±20 ppb que
  pidió el asesor.
- Conviene diseñar el paso 5 de modo que también evalúe a PARAAD: es el escenario más parecido al
  suyo.

## 5. Preguntas para el tesista antes de empezar

1. ¿Dónde están los datos de Barcelona y qué traen? ¿O₃ horario de las 8 estaciones? ¿Con las
   anomalías ya inyectadas o limpios?
2. ¿Tienes el PDF del artículo (con la licencia UNAM)? Si no, se lee el de UPCommons. El PDF no va a
   git.
3. ¿El asesor espera el camino recomendado, el complementario o los dos?
4. ¿Escribimos a los autores para pedir el código? Si contestan, ahorra la reprogramación y la
   duda de fidelidad.

## 6. Riesgos y lo que hay que declarar

- **Reimplementación propia:** aunque se haga con cuidado, no es su código. Por eso es importante
  la prueba de fidelidad (paso 2).
- **El umbral:** si el suyo usa etiquetas, sus números publicados no son comparables con los
  nuestros. En nuestra tabla va con nuestro umbral.
- **Escala:** con 32 estaciones y 24 horas, la entrada es más grande que la suya (8 × 24). Puede
  necesitar ajustes, que se deciden sólo con 2022.
- **No supervisado contra supervisado:** PARAAD contra L0 no es «peras con peras». Se presenta
  como referencia, y la comparación principal es contra el V4.
- **Cómputo:** un autoencoder con atención sobre bloques de 24 × 32 en CPU puede tardar horas. Se
  mide con una prueba corta antes de lanzar.
