# Runbook: revisión 8 en la PC del tesista

Instrucciones para la instancia de Claude que corra la revisión 8 del protocolo
`anomalias_red_v1` en la PC de escritorio del tesista (Ryzen 7 7700X). La prepararon el tesista y
Claude el 2026-10-22, en la lap, y se pasó a la PC porque la lap se calentó con la última corrida.

> **Nota (2026-10-23):** el tesista no tiene acceso a la PC, así que el cómputo se hace en Colab
> con `notebooks/colab_revision8.ipynb`, que sigue los mismos pasos sin otra instancia de Claude.
> Este runbook sigue valiendo para cuando se use la PC.

**Antes de hacer nada, lee:**
- `docs/protocolo_anomalias_red_v1.md`, sobre todo las revisiones 7 y 8 del §15;
- la última sección de `docs/progreso.md` (2026-10-22);
- este documento completo.

---

## 1. Reglas que no se rompen

`CLAUDE.md` no está en git: pídele al tesista que lo copie de la lap a la raíz del repo. Mientras
tanto, valen estas reglas:

**Del protocolo y la reproducibilidad:**
- **El diseño no se cambia.** Está fijado en la revisión 8. Cualquier cambio va como fila fechada
  en el §15 y nota en `progreso.md`, **antes** de ver resultados, y con el visto bueno del tesista.
- **Nada se ajusta mirando 2024–2026.** 2022 es validación, 2023 calibración y 2024 examen.
- **La etiqueta nunca es entrada del modelo.**
- **Semilla:** `fijar_semilla(42)` inmediatamente antes de construir cada modelo. Los scripts ya
  lo hacen; no lo quites.
- **Reproducibilidad:** todo resultado nuevo se corre dos veces y debe salir idéntico.
- **Origen de cada número:** al reportarlo, di si viene de un modelo recién entrenado o de uno
  cargado de disco.
- **Si algo falla o no cuadra, detente y avísale al tesista.** No improvises sustitutos (otras
  versiones, otros datos, otros parámetros).

**De la forma de trabajo con el tesista:**
- **Explícale en español sencillo y desde cero.** No domina el aprendizaje automático. Define
  cada métrica (recall, precisión, F1, AUC) y di qué es el azar.
- **Gráficas:** sólo 1 o 2 por semana, y cada una con su ficha en `docs/fichas_graficas.md` (eje
  X, eje Y, de dónde sale cada número, qué tipo de medida es). No hagas gráficas que no pida.
- **Actúa como revisor crítico:** no le des la razón por defecto, y sé neutral y directo.
- **Rastro fechado:** todo se registra en `docs/progreso.md`. Las correcciones van como notas
  fechadas; no se borra nada.
- **Git:**
  - commit y push sólo cuando el tesista lo pida;
  - los PDFs nunca van a git;
  - no subas nada de `experiments/diagnostico_no_no2/` ni de `results/diagnostico_no_no2_2022/`.
- **Umbral de contingencia:** siempre 155 ppb, nunca 154.

---

## 2. Preparar la PC

Lo ideal es **Linux** o **Windows con WSL2 (Ubuntu)**. Los comandos de abajo son de Linux. En
Windows nativo, el intérprete es `.venv\Scripts\python.exe` y el script de bash del paso 6 no
corre: usa WSL2.

1. **El tesista copia de la lap a la PC** (por USB, por ejemplo):
   - los 7 zips `data/raw/20RAMA.zip` … `data/raw/26RAMA.zip`, a `data/raw/` del repo;
   - `CLAUDE.md`, a la raíz del repo.
2. **El repo:**
   ```bash
   git clone git@github.com:JoseLili/lorawan11-rama-detection.git && cd lorawan11-rama-detection
   ```
   Si ya existe, usa `git pull`.
3. **Verifica los zips contra sus SHA-256.** Todos deben decir «OK»:
   ```bash
   grep 'RAMA.zip' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c -)
   ```
4. **El entorno, con las versiones exactas de la lap** (Python 3.14.7):
   ```bash
   python3.14 -m venv .venv
   .venv/bin/python -m pip install -r requirements-lock.txt
   .venv/bin/python -c "import sys, tensorflow as tf, keras, numpy, pandas, sklearn; print(sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__, pandas.__version__, sklearn.__version__)"
   ```
   Debe imprimir `3.14.7 2.22.0-rc0 3.16.0.dev2026092204 2.5.3 3.0.6 1.9.1`. **Si alguna versión no
   se puede instalar, detente y avisa. No uses otras.** Usa sólo el procesador; no instales nada
   para la tarjeta gráfica.
5. **Regenera los planes y las matrices.** No están completos en git; son deterministas.
   ```bash
   .venv/bin/python experiments/anomalias_red/generar_planes.py
   .venv/bin/python experiments/anomalias_red/generar_matrices.py
   git status --short results/anomalias_red_v1/
   ```
   `git status` **no debe mostrar cambios** en `planes/` ni en `resumen_matrices.csv`. Si los
   muestra, la PC no reproduce los datos: detente y avisa.
6. **Corre las pruebas:** `.venv/bin/python -m pytest -q`. Deben pasar las 265 (2026-10-22).

---

## 3. Prueba de equivalencia (~8 minutos en la lap)

Repite en la PC un resultado conocido de la lap: la configuración 3 de la curva de aprendizaje,
con δ = 100 %.

```bash
.venv/bin/python experiments/anomalias_red/diagnostico_curva_aprendizaje_2022.py --delta 100 --solo 3 --salida /tmp/equivalencia
.venv/bin/python - <<'EOF'
import pandas as pd
a = pd.read_csv('results/anomalias_red_v1/curva_aprendizaje_2022/resultados.csv')
a = a[(a.delta_pct == 100) & (a.configuracion == 3)].reset_index(drop=True)
b = pd.read_csv('/tmp/equivalencia/resultados.csv')
c = ['epoca', 'deteccion_2022_fa5_pct', 'auc_2022', 'val_loss']
print(pd.concat([a[c], b[c].add_suffix('_pc')], axis=1).to_string())
print('IDÉNTICO' if a[c].equals(b[c]) else 'DISTINTO')
EOF
```

- **IDÉNTICO:** la PC reproduce la lap. Sigue. Anota en `progreso.md` cuánto tardó, para estimar
  los demás pasos.
- **DISTINTO:**
  - **detente** y enséñale al tesista la tabla de diferencias;
  - él decide si sigue en la PC o regresa a la lap;
  - si sigue en la PC, antes de comparar con la revisión 7 hay que repetirla ahí. Eso va como nota
    en la revisión 8.

---

## 4. Elección de la forma con 2022

En la lap tomaría ~1.3 h por corrida; en la PC, menos. Las dos corridas son el mismo comando con
distinta salida:

```bash
.venv/bin/python experiments/anomalias_red/diagnostico_vecinas_2022.py 2>&1 | tee /tmp/vecinas_1.log
.venv/bin/python experiments/anomalias_red/diagnostico_vecinas_2022.py --salida /tmp/vecinas_c2 2>&1 | tee /tmp/vecinas_2.log
for f in resultados.csv resumen.csv eleccion.json; do cmp -s results/anomalias_red_v1/vecinas_2022/$f /tmp/vecinas_c2/$f && echo "$f idéntico" || echo "$f DISTINTO"; done
```

- **Qué hace:** entrena 5 modelos (la revisión 7 sin vecinas y las 4 formas) × δ = 20 y 100 % ×
  10 épocas.
- **Qué escribe:** `results/anomalias_red_v1/vecinas_2022/` con `resultados.csv` (por época),
  `resumen.csv` y `eleccion.json`. Este último trae la regla aplicada y la forma elegida.
- **Si sale DISTINTO:** detente y avisa.

---

## 5. Registrar la elección y detenerse

1. **En `docs/progreso.md`,** una sección fechada como la de la curva de aprendizaje (2026-10-22):
   - una tabla por δ con la mejor época, la detección (mejor y promedio), la precisión, el F1, el
     AUC y la pérdida de validación de las 5 entradas;
   - la regla aplicada;
   - la comparación con la revisión 7 sin vecinas.

   Los modelos son recién entrenados y no se guardan.
2. **En el protocolo,** al final de la revisión 8, una línea «**Forma elegida con 2022
   (fecha):** …», con la ventaja que la decidió.
3. **Detente:**
   - explícale al tesista el resultado en sencillo;
   - si las vecinas ayudaron con δ = 20 % en 2022, díselo; si no, también;
   - **pide su visto bueno antes del paso 6.**

---

## 6. Corrida completa (con el visto bueno del tesista)

```bash
nohup bash experiments/anomalias_red/correr_revision8.sh <forma> > logs_revision8/total.log 2>&1 &
```

- **Qué corre, por cada δ (100, 50, 20, 10 y 5 %):**
  - el LSTM supervisado con vecinas, dos veces, comparando las salidas;
  - el Random Forest de control, que verifica dentro del script dos entrenamientos idénticos;
  - la regla de vecinas, dos veces.
- **Cuánto tarda:** en la lap serían ~2 h; en la PC, menos. Antes de lanzarlo, evita que la PC se
  suspenda o se apague.
- **Registros:** en `logs_revision8/`, que no va a git.
- **Al terminar:** `logs_revision8/total.log` debe decir «idéntico» en todas las comparaciones y
  terminar con «FIN».
- **Si un δ falla,** se detiene ahí. Revisa el registro de ese δ y avisa.

---

## 7. Registrar los resultados

En `docs/progreso.md`, una sección «Resultado: revisión 8», con el formato de la del 2026-10-18
(δ = 20, 10 y 5 %).

- **Recall por hora:** contra las mismas horas sin alterar, con 5 % y 1 %, para el LSTM con
  vecinas, su Random Forest y la regla, junto a la revisión 7 (`lstm_sup_relativas_20cal`) y el V4
  (`v4`). La función `recall_por_corrida` de
  `experiments/anomalias_red/graficar_recall_delta.py` da ese formato.
- **Las demás medidas:** detección por episodio con su azar, falsas alarmas en 2024 limpio y E por
  δ.
- **Las 6 predicciones de la revisión 8:** cuáles se cumplieron, sin suavizar las que no.
- **El origen:** LSTM y Random Forest recién entrenados; la regla, sin entrenamiento; el V4,
  cargado de disco.

No hagas gráficas nuevas salvo que el tesista lo pida, y siempre con su ficha.

---

## 8. Commit

Sólo cuando el tesista lo pida. Agrega lo de la revisión 8:
- el código;
- `results/anomalias_red_v1/vecinas_2022/`, `lstm_sup_vecinas_*`, `rf_vecinas_*` y
  `regla_vecinas_*`;
- `docs/`.

Las matrices, los `.joblib` y `logs_revision8/` ya están en `.gitignore`. Corre `git status`
antes, y no subas nada que no sea de la revisión 8.
