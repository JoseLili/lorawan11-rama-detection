# Revisión 19, evaluación de un año en Colab (sesiones rev19_<año>, 2026-10-27). Uso: bash correr_revision19.sh AÑO
# Necesita en /content: codigo_rev19.tgz (todo lo cambiado desde 058b7d1, sin subir al remoto), datos_rev19_<año>.tgz
# (matrices, residuos de calibración del V4 y puntajes de la revisión 18 del año, con sus SHA-256) y zips.tgz.
# Corre la evaluación dos veces en paralelo y compara.
set -e
set -o pipefail
A_=$1
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "058b7d1" ] || { echo "FALLÓ: HEAD distinto de 058b7d1"; exit 1; }
tar -xzf /content/codigo_rev19.tgz && tar -xzf /content/datos_rev19_$A_.tgz
sha256sum -c --quiet datos_rev19_$A_.sha256 && echo "datos OK"
sha256sum experiments/anomalias_red/evaluar_revision19.py | cut -c1-16
echo "== uv y Python 3.14.7"; date
pip -q install uv
uv python install 3.14.7
uv venv -q --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt 2>&1 | tail -2
.venv/bin/python -c "import sys, tensorflow as tf, keras, numpy, pandas, sklearn; print('VERSIONES', sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__, pandas.__version__, sklearn.__version__)"
lscpu | grep 'Model name'
tar -xzf /content/zips.tgz
grep -E '  [0-9]{2}RAMA\.zip$' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c --quiet -) && echo "zips OK"
.venv/bin/python -m pytest -q tests/test_revision19.py tests/test_v4_supervisado.py 2>&1 | tail -1
echo "== evaluación $A_, dos veces en paralelo"; date
export PYTHONUNBUFFERED=1 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
E=experiments/anomalias_red/evaluar_revision19.py
( .venv/bin/python $E --anio $A_ 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval19_1.log ) & p1=$!
( .venv/bin/python $E --anio $A_ --salida /content/c2/revision19/$A_ 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval19_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -n 5 /content/registros/eval19_*.log; exit 1; }
for f in resultados.csv intervalos.csv falsas_alarmas.csv pareado_recall.csv pareado_falsas_alarmas.csv conteos.csv; do
  cmp -s results/anomalias_red_v1/revision19/$A_/$f /content/c2/revision19/$A_/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
grep control results/anomalias_red_v1/revision19/$A_/configuracion.json
tar -czf /content/eval19_$A_.tgz results/anomalias_red_v1/revision19/$A_ && sha256sum /content/eval19_$A_.tgz
date; echo FIN_EVAL19
