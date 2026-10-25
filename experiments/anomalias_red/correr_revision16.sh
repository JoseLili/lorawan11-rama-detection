# Revisión 16, comprobaciones (2) y (3) en Colab (sesión rev16, 2026-10-25). Copia exacta del guion que se corrió
# (SHA-256 del original: 78bbcb299da21ca2…). Necesita en /content codigo_rev16.tgz y zips.tgz.
set -e
set -o pipefail
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "db65037" ] || { echo "FALLÓ: HEAD distinto de db65037"; exit 1; }
echo "== código de las revisiones 15 y 16 (sin commit todavía)"
tar -xzf /content/codigo_rev16.tgz && git status --short
echo "== uv y Python 3.14.7"; date
pip -q install uv
uv python install 3.14.7
uv venv -q --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt 2>&1 | tail -2
.venv/bin/python -c "import sys, tensorflow as tf, keras, numpy, pandas, sklearn; print('VERSIONES', sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__, pandas.__version__, sklearn.__version__)"
lscpu | grep -E 'Model name|^CPU\(s\)'
echo "== zips y SHA-256"; date
tar -xzf /content/zips.tgz
grep -E '  [0-9]{2}RAMA\.zip$' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c -)
echo "== planes y matrices de siempre"; date
.venv/bin/python experiments/anomalias_red/generar_planes.py 2>&1 | tail -1
.venv/bin/python experiments/anomalias_red/generar_matrices.py 2>&1 | tail -1
echo "== git status de los datos (debe estar vacío)"
git status --short results/anomalias_red_v1/planes results/anomalias_red_v1/resumen_planes.csv results/anomalias_red_v1/resumen_matrices.csv
echo "== fin git status"
echo "== pruebas"; date
.venv/bin/python -m pytest -q 2>&1 | tail -1
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
echo "== (2) modelo único, dos corridas en paralelo"; date
( .venv/bin/python experiments/anomalias_red/modelo_unico_delta.py 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/unico_1.log ) & p1=$!
( .venv/bin/python experiments/anomalias_red/modelo_unico_delta.py --salida /content/c2/modelo_unico 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/unico_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ el modelo único"; tail -5 /content/registros/unico_*.log; exit 1; }
A=results/anomalias_red_v1/comprobaciones_2024
for f in eleccion_2022.csv examen_2024.csv eleccion.json; do
  cmp -s $A/modelo_unico/$f /content/c2/modelo_unico/$f && echo "modelo_unico/$f idéntico" || echo "modelo_unico/$f DISTINTO"
done
echo "== (3) hora de inicio al azar, dos corridas seguidas"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py 2>&1 | grep -v -E "$F" > /content/registros/hora_1.log
echo "-- segunda"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py --salida /content/c2/hora_azar 2>&1 | grep -v -E "$F" > /content/registros/hora_2.log
for f in resultados.csv conteos.csv comparacion_medianoche.csv; do
  cmp -s $A/hora_azar/$f /content/c2/hora_azar/$f && echo "hora_azar/$f idéntico" || echo "hora_azar/$f DISTINTO"
done
cmp -s <(cut -d, -f1,2,4 $A/hora_azar/matrices.csv) <(cut -d, -f1,2,4 /content/c2/hora_azar/matrices.csv) && echo "matrices idénticas" || echo "matrices DISTINTO"
diff -rq $A/hora_azar/planes /content/c2/hora_azar/planes && echo "planes idénticos" || echo "planes DISTINTO"
grep -c "ya existía, idéntico" /content/c2/hora_azar/matrices.csv
date; echo FIN_TODO

# ---- Continuación (todo_b.sh, SHA-256 30648c14efec81c3…), después de que la primera corrida de (3) falló porque
# los residuos guardados del V4 (calibracion_2023 y predicciones_202x) no están en git: se subieron como v4_residuos.tgz.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
echo "== residuos guardados del V4 (no están en git)"; date
tar -xzf /content/v4_residuos.tgz && ls results/lstm_v4_multianual_v1/estaciones/*/calibracion_2023.csv.gz | wc -l
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
A=results/anomalias_red_v1/comprobaciones_2024
echo "== (3) hora de inicio al azar, dos corridas seguidas"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py 2>&1 | grep -v -E "$F" > /content/registros/hora_1.log || { echo "FALLÓ hora_azar 1"; tail -5 /content/registros/hora_1.log; exit 1; }
echo "-- segunda"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py --salida /content/c2/hora_azar 2>&1 | grep -v -E "$F" > /content/registros/hora_2.log || { echo "FALLÓ hora_azar 2"; tail -5 /content/registros/hora_2.log; exit 1; }
for f in resultados.csv conteos.csv comparacion_medianoche.csv; do
  cmp -s $A/hora_azar/$f /content/c2/hora_azar/$f && echo "hora_azar/$f idéntico" || echo "hora_azar/$f DISTINTO"
done
cmp -s <(cut -d, -f1,2,4 $A/hora_azar/matrices.csv) <(cut -d, -f1,2,4 /content/c2/hora_azar/matrices.csv) && echo "matrices idénticas" || echo "matrices DISTINTO"
diff -rq $A/hora_azar/planes /content/c2/hora_azar/planes && echo "planes idénticos" || echo "planes DISTINTO"
date; echo FIN_TODO

# ---- Segunda continuación (todo_c.sh, SHA-256 9bfbf906ba5627c3…): el control del V4 contra sus predicciones guardadas
# falló por 7.6e-6 ppb (otra CPU, float32); se agregó --tolerancia-v4 a hora_azar_2024.py y se corrió con 1e-4 ppb.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
echo "== residuos guardados del V4 (no están en git)"; date
cp /content/hora_azar_2024.py experiments/anomalias_red/ && sha256sum experiments/anomalias_red/hora_azar_2024.py | cut -c1-16
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
A=results/anomalias_red_v1/comprobaciones_2024
echo "== (3) hora de inicio al azar, dos corridas seguidas"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py --tolerancia-v4 1e-4 2>&1 | grep -v -E "$F" > /content/registros/hora_1.log || { echo "FALLÓ hora_azar 1"; tail -5 /content/registros/hora_1.log; exit 1; }
echo "-- segunda"; date
.venv/bin/python experiments/anomalias_red/hora_azar_2024.py --tolerancia-v4 1e-4 --salida /content/c2/hora_azar 2>&1 | grep -v -E "$F" > /content/registros/hora_2.log || { echo "FALLÓ hora_azar 2"; tail -5 /content/registros/hora_2.log; exit 1; }
for f in resultados.csv conteos.csv comparacion_medianoche.csv; do
  cmp -s $A/hora_azar/$f /content/c2/hora_azar/$f && echo "hora_azar/$f idéntico" || echo "hora_azar/$f DISTINTO"
done
cmp -s <(cut -d, -f1,2,4 $A/hora_azar/matrices.csv) <(cut -d, -f1,2,4 /content/c2/hora_azar/matrices.csv) && echo "matrices idénticas" || echo "matrices DISTINTO"
diff -rq $A/hora_azar/planes /content/c2/hora_azar/planes && echo "planes idénticos" || echo "planes DISTINTO"
date; echo FIN_TODO
