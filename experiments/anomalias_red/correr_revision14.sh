# Revisión 14, elección con 2022 en Colab (sesión rev14, 2026-10-24).
# Copia exacta del guion que se corrió (SHA-256 del original: 41e2edb7df4bb978…). Se ejecuta en Colab con
# nohup setsid bash; necesita en /content los tarballs que se indican.
set -e
set -o pipefail
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "364b687" ] || { echo "FALLÓ: HEAD distinto de 364b687"; exit 1; }
echo "== código de las revisiones 13 y 14 (sin commit todavía)"
tar -xzf /content/codigo_rev14.tgz && git status --short | grep -v plan_entrenamiento_
mkdir -p /content/lap && cp results/anomalias_red_v1/resumen_*_revision14.csv /content/lap/
echo "== uv y Python 3.14.7"; date
pip -q install uv
uv python install 3.14.7
uv venv -q --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt 2>&1 | tail -2
.venv/bin/python -c "import sys, tensorflow as tf, keras, numpy, pandas, sklearn; print('VERSIONES', sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__, pandas.__version__, sklearn.__version__)"
lscpu | grep -E 'Model name|^CPU\(s\)'
free -g | head -2
echo "== zips y SHA-256"; date
tar -xzf /content/zips.tgz
grep -E '  [0-9]{2}RAMA\.zip$' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c -)
echo "== planes y matrices de siempre"; date
.venv/bin/python experiments/anomalias_red/generar_planes.py 2>&1 | tail -1
.venv/bin/python experiments/anomalias_red/generar_matrices.py 2>&1 | tail -1
echo "== git status de los datos (debe estar vacío)"
git status --short results/anomalias_red_v1/planes results/anomalias_red_v1/resumen_planes.csv results/anomalias_red_v1/resumen_matrices.csv | grep -v '^?? ' || true
echo "== fin git status"
echo "== calendarios 21–60 (revisión 14)"; date
.venv/bin/python experiments/anomalias_red/generar_planes.py --ampliados 2>&1 | grep -c "ya existía, idéntico"
.venv/bin/python experiments/anomalias_red/generar_matrices.py --ampliados 2>&1 | tail -1
for f in resumen_planes_revision14.csv resumen_matrices_revision14.csv; do
  cmp -s results/anomalias_red_v1/$f /content/lap/$f && echo "$f igual al de la lap" || { echo "FALLÓ: $f distinto del de la lap"; exit 1; }
done
echo "== pruebas"; date
.venv/bin/python -m pytest -q 2>&1 | tail -1
echo "== elección con 2022, dos corridas en paralelo"; date
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
corrida() {   # $1 = salida de los LSTM, $2 = salida de la elección
  for n in 20 60; do
    for d in 100 50 20; do
      echo "-- entrenar $n calendarios δ = $d"; date
      .venv/bin/python experiments/anomalias_red/entrenar_lstm_local.py --delta $d --calendarios $n --salida $1
    done
  done
  echo "-- elección"; date
  .venv/bin/python experiments/anomalias_red/diagnostico_lstm_local_2022.py --lstm $1 --salida $2
}
( corrida results/anomalias_red_v1/lstm_local results/anomalias_red_v1/lstm_local_2022 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eleccion_1.log ) & p1=$!
( corrida /content/c2/lstm_local /content/c2/lstm_local_2022 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eleccion_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado de las corridas: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -5 /content/registros/eleccion_*.log; exit 1; }
A=results/anomalias_red_v1; B=/content/c2
for n in 20 60; do for d in 100 50 20; do
  x=lstm_local/c$n/d$d
  cmp -s $A/$x/seleccion/historia_seleccion.csv $B/$x/seleccion/historia_seleccion.csv && echo "$x historia idéntica" || echo "$x historia DISTINTO"
  cmp -s <(zcat $A/$x/seleccion/dias_2022.csv.gz) <(zcat $B/$x/seleccion/dias_2022.csv.gz) && echo "$x puntajes idénticos" || echo "$x puntajes DISTINTO"
  cmp -s <(grep -v fecha $A/$x/configuracion.json) <(grep -v fecha $B/$x/configuracion.json) && echo "$x configuración idéntica" || echo "$x configuración DISTINTO"
done; done
for f in resultados.csv falsas_alarmas.csv apagadas.csv epocas.csv control_r3.csv eleccion.json; do
  cmp -s $A/lstm_local_2022/$f $B/lstm_local_2022/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
date; echo FIN_TODO
