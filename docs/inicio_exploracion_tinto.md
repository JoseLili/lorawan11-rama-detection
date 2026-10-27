# Inicio de exploración: TINTO (datos tabulares convertidos en imágenes)

Documento para arrancar esta línea en **otro chat o con Codex**, separada del trabajo principal.
Redactado por Claude el 2026-10-27, a pedido del tesista. Es un punto de partida, no un protocolo
aprobado.

## 1. Contexto en tres líneas

- **Tesis (PCIC-UNAM), parte 2:** detectar anomalías en las estaciones de ozono de la RAMA (CDMX),
  por **estación-día**: ¿esta estación estuvo alterada este día?
- **Mejor detector actual:** **L0**, un LSTM supervisado que mira la estación y sus 4 vecinas
  más cercanas. La comparación principal es su **modelo único**, el entrenado con δ = 50 %.
- **Por qué TINTO:** el asesor (Dr. José Jaime Camacho Escoto, junta del 2026-10-26) pidió probarlo.
  Es la idea de "representar el día como imagen" que planteó desde el 2026-10-19 (idea M-6 en
  `docs/progreso.md`).
  - TINTO es del grupo del Dr. Orozco (UCLM): Castillo-Cara, Talla-Chumpitaz, García-Castro y
    Orozco-Barbosa, *SoftwareX*, 2023.
  - Según la transcripción, que tiene ruido, el asesor espera que TINTO quede un poco por encima de
    L0. Hay que confirmarlo con el tesista.

## 2. Qué es TINTO (por verificar con el artículo y la documentación)

- **El método:** convierte cada fila de una tabla (un vector de características) en una imagen 2D
  y la clasifica una red convolucional.
- **Cómo hace la imagen:** acomoda las características en el plano con una reducción de
  dimensión de las columnas (PCA o t-SNE), opcionalmente con "difuminado".
- **La biblioteca:** TINTOlib, en Python, licencia Apache 2.0. Además de TINTO incluye otros
  métodos (IGTD, REFINED, BarGraph, DistanceMatrix, SuperTML, Fotomics, DeepInsight…).
  Comprobar la lista y la API en su repositorio antes de usarla.
- **Referencias:**
  - TINTO (2023): <https://cris.ulima.edu.pe/en/publications/tinto-converting-tidy-data-into-image-for-classification-with-2-d/>
  - TINTOlib (SoftwareX, 2025): <https://portalcientifico.uned.es/documentos/69c6d284aed3973af89035c5>
  - Ejemplos: <https://github.com/manwestc/TINTOlib-Examples-SoftX>
- **Pregunta abierta:** TINTO está pensado para datos tabulares sin orden temporal, y nuestra
  entrada es una ventana de 24 horas. Ver las opciones de la §4.

## 3. Reglas que no se negocian (del protocolo de la tesis)

Fuente de verdad: `docs/protocolo_anomalias_red_v1.md`, y `CLAUDE.md` en la raíz.

- **Años:**
  - ajuste 2020–2022 (selección con 2020–2021 y validación 2022);
  - 2023 limpio solo para umbrales;
  - **2024 a 2026 no se miran en esta exploración**: ni para elegir, ni para ver, ni para ajustar.
    La exploración vive **solo en 2020–2022**.
- **Anomalía:**
  - x·(1+δ) con signo + o x/(1+δ) con signo −, con δ ∈ {100, 50, 20, 10, 5} %;
  - el signo se sortea por episodio;
  - episodios de 1 a 7 días completos desde las 00 h, solo en los 31 objetivos y solo en horas
    con dato;
  - ya están hechos: son los calendarios `entrenamiento_01…20` (planes y matrices en
    `results/anomalias_red_v1/`).
- **La etiqueta nunca es entrada.**
- **Semilla:** `fijar_semilla(42)` de `src/detect/lstm.py` inmediatamente antes de construir y de
  entrenar cualquier modelo.
- **Reproducibilidad:** correr todo dos veces y confirmar el mismo número. Decir siempre si un
  modelo es recién entrenado o cargado de disco.
- **«Peras con peras»** (regla del tesista desde el 2026-10-27): TINTO se compara contra el L0 único
  con lo mismo:
  - la misma información de entrada (§4);
  - el mismo δ = 50 % de entrenamiento;
  - los mismos 20 calendarios y la misma muestra de horas (1 de cada 8);
  - la misma etiqueta por estación-hora;
  - la misma forma de juntar el día (promedio de las probabilidades de las horas con dato,
    mínimo 12);
  - las mismas estación-días.
  
  Lo único que cambia es la representación: imagen + CNN en lugar de secuencia + LSTM.
- **No tocar** nada de `results/` ni de `docs/protocolo_anomalias_red_v1.md` fuera de la carpeta
  propia. No hacer commits, salvo que el tesista lo pida. Los PDF nunca van a git.
- **Si la exploración sale prometedora,** pasarla a 2024–2026 requiere una revisión nueva del
  protocolo, registrada y aprobada por el tesista **antes** de mirar esos años.

## 4. Diseño mínimo propuesto para la primera exploración

**Entrada (la misma información que L0):**
- Para cada (estación s, hora t), la ventana t−23…t con las 17 columnas de L0:
  - para s y cada una de sus 4 vecinas: la relativa al perfil de 14 días, la máscara y la columna
    de vecinas;
  - más el seno y el coseno de la hora.
- Se arma con `src/detect/lstm_local.py` (`indices_locales`, `ventanas_locales`) sobre las 98
  columnas de `evaluacion_red.entradas_de('vecinas', ...)`, con `parametros_vecinas('a14', ...,
  'media')`, igual que `experiments/anomalias_red/entrenar_lstm_local.py`.

**Tres formas de hacer la imagen.** Elegir una sola para la primera prueba y dejar las otras
anotadas:
- **(A) TINTO directo** sobre la fila aplanada de 24 × 17 = 408 valores. Es la más fiel a TINTO.
  La pregunta es qué tanto se pierde el orden temporal.
- **(B) La ventana como imagen** de 24 × 17 (horas × columnas) y una CNN 2D. No es TINTO, pero es
  el control natural de (A).
- **(C) Una imagen TINTO por hora** (17 características) y una secuencia de 24 imágenes. Es más
  cara; dejarla para después.

**Entrenamiento:**
- con 2020–2021 de los 20 calendarios con δ = 50 %, 1 de cada 8 horas por calendario y estación
  (como `lstm_local.muestra`, pero con su propia semilla derivada de 42, sin `hash()`);
- validación y EarlyStopping con 2022 de los calendarios 01–10 (paciencia 8, máximo 60 épocas).

**Comparación justa, solo en 2022:**
- **El comparador:** el modelo de selección de L0 con δ = 50 %, cargado de disco
  (`results/anomalias_red_v1/lstm_local/c20/d50/seleccion/modelo_seleccion.keras`). Sus puntajes de
  2022 ya están en `seleccion/dias_2022.csv.gz`.
  - Como referencia, ya calculado: con 1 % de falsas alarmas en 2022 limpio y δ = 50 %, L0 tiene
    F1 0.472, recall 0.790 y precisión 0.337 (R3: 0.404).
  - Para comparar con δ = 100 y 20 %, aplicar ese mismo modelo de L0 cargado de disco a esos
    calendarios.
- **Umbral:** el de 1 % (p99) y el de 0.1 % (p99.9) de falsas alarmas en 2022 limpio, en las
  estación-días válidas para los dos. Es el esquema de
  `experiments/anomalias_red/diagnostico_lstm_local_2022.py`.
- **Métricas:** F1, recall, precisión y PR-AUC, cada una con su valor "sin ataque" (2022 limpio).

**Salidas:**
- código en `experiments/exploracion_tinto/`;
- resultados en `results/exploracion_tinto_2022/`;
- una nota fechada para que el tesista la pase a `docs/progreso.md`.

## 5. Cuidados prácticos

- **Entorno:** el del repo es Python 3.14.7, TensorFlow 2.22 rc y Keras 3.16 dev, con
  `requirements-lock.txt`. **No modificar el lock.** Si TINTOlib necesita otras versiones (por
  ejemplo PyTorch), usar un entorno aparte y anotarlo.
- **Datos:** las matrices (`results/anomalias_red_v1/matrices/`) y los zips de la RAMA (`data/raw/`)
  no están en git: están en la laptop del tesista. Desde la nube hay que subirlos o regenerarlos
  con `experiments/anomalias_red/generar_planes.py` y `generar_matrices.py`, y comprobar que salen
  idénticos.
- **Cómputo:** sin GPU, porque cambia los números entre corridas. En la tesis se usa Colab Pro solo
  con CPU.
- **Explicar todo desde cero y en español:** el tesista no domina ML.
- **Cada gráfica con su ficha:** qué es el eje X, qué es el eje Y, de dónde sale cada métrica y
  qué tipo de medida es.

## 6. Preguntas para resolver al inicio

1. ¿El asesor quiere TINTO tal cual (forma A) o la idea general de "día como imagen" (B o C)?
2. ¿La imagen debe representar una hora con su historia (como L0) o un día completo de la estación
   y sus vecinas?
3. ¿Qué tan lejos ir en 2022 antes de decidir si vale una revisión del protocolo?
