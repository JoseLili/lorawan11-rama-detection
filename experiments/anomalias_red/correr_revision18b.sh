# Revisión 18b, V4S compartido en Colab (sesión rev18b, 2026-10-27; la sesión rev18 se cerró sola). Necesita en
# /content: codigo_rev18.tgz y zips.tgz (los de correr_revision18.sh), codigo_rev18b.tgz (el código de la 18b, sin
# commit) y v4s_rev18.tgz (los 31 V4S por estación ya entrenados, para la evaluación). Prepara la sesión como
# correr_revision18.sh, entrena el compartido dos veces completo, en paralelo, y compara.
set -e
set -o pipefail
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "058b7d1" ] || { echo "FALLÓ: HEAD distinto de 058b7d1"; exit 1; }
echo "== código de las revisiones 18 y 18b, matrices de entrenamiento y V4S por estación"
tar -xzf /content/codigo_rev18.tgz && tar -xzf /content/codigo_rev18b.tgz && tar -xzf /content/v4s_rev18.tgz
sha256sum -c --quiet matrices_rev18.sha256 && echo "matrices OK"
sha256sum src/detect/v4_supervisado.py experiments/anomalias_red/entrenar_v4_supervisado.py | cut -c1-16
echo "== uv y Python 3.14.7"; date
pip -q install uv
uv python install 3.14.7
uv venv -q --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt 2>&1 | tail -2
.venv/bin/python -c "import sys, tensorflow as tf, keras, numpy, pandas, sklearn; print('VERSIONES', sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__, pandas.__version__, sklearn.__version__)"
free -g | head -2
echo "== zips y SHA-256"; date
tar -xzf /content/zips.tgz
grep -E '  [0-9]{2}RAMA\.zip$' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c -)
.venv/bin/python -c "
import json, hashlib
from pathlib import Path
ok = all(hashlib.sha256((d / 'modelo.keras').read_bytes()).hexdigest() == json.loads((d / 'configuracion.json').read_text())['sha256']['modelo']
         for d in Path('results/anomalias_red_v1/v4_supervisado/d50').iterdir() if d.is_dir())
print('V4S por estación: SHA-256 de los 31 modelos', 'OK' if ok else 'DISTINTO')
"
echo "== V4S compartido (revisión 18b)"; date
.venv/bin/python -m pytest -q tests/test_v4_supervisado.py 2>&1 | tail -1
lscpu | grep 'Model name'
export PYTHONUNBUFFERED=1 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
E=experiments/anomalias_red/entrenar_v4_supervisado.py
( .venv/bin/python $E --compartido 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4sc_1.log ) & p1=$!
( .venv/bin/python $E --compartido --salida /content/c2/v4_supervisado_compartido 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4sc_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -n 5 /content/registros/v4sc_*.log; exit 1; }
A=results/anomalias_red_v1/v4_supervisado_compartido/d50; B=/content/c2/v4_supervisado_compartido/d50
for f in seleccion/historia_seleccion.csv historia_definitiva.csv; do
  cmp -s $A/$f $B/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
.venv/bin/python -c "
import numpy as np
from tensorflow import keras
a = keras.models.load_model('$A/modelo.keras', compile=False).get_weights()
b = keras.models.load_model('$B/modelo.keras', compile=False).get_weights()
print('pesos del definitivo idénticos' if all(np.array_equal(x, y) for x, y in zip(a, b)) else 'pesos DISTINTO')
" 2>&1 | grep -v -E "$F"
date; echo FIN_V4SC
