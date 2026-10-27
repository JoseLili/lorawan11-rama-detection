# Revisión 18, entrenamiento del V4 supervisado (V4S, δ = 50 %) en Colab (sesión rev18, 2026-10-27).
# Se ejecuta con nohup setsid bash; necesita en /content codigo_rev18.tgz (código nuevo, sin commit, y las
# 20 matrices de entrenamiento con δ = 50 % de la lap con sus SHA-256) y zips.tgz (los 7 zips de la RAMA).
set -e
set -o pipefail
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "058b7d1" ] || { echo "FALLÓ: HEAD distinto de 058b7d1"; exit 1; }
echo "== código de la revisión 18 y matrices de la lap"
tar -xzf /content/codigo_rev18.tgz && git status --short | grep -v '^?? results/' || true
sha256sum -c --quiet /content/lorawan11-rama-detection/matrices_rev18.sha256 && echo "matrices OK"
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
echo "== pruebas del V4S"; date
.venv/bin/python -m pytest -q tests/test_v4_supervisado.py 2>&1 | tail -1
echo "== entrenamiento: 3 grupos de estaciones y el control (selección de ACO otra vez), en paralelo"; date
export PYTHONUNBUFFERED=1 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
E=experiments/anomalias_red/entrenar_v4_supervisado.py
G1=MER,UAX,PED,MGH,NEZ,TAH,SAG,LPR,IZT,TLI,CHO
G2=CAM,BJU,INN,ATI,UIZ,CUT,VIF,MPA,AJU,ACO,AJM
G3=TLA,FAC,CCA,SAC,GAM,FAR,MON,CUA,LLA
( .venv/bin/python $E --estaciones $G1 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4s_1.log ) & p1=$!
( .venv/bin/python $E --estaciones $G2 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4s_2.log ) & p2=$!
( .venv/bin/python $E --estaciones $G3 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4s_3.log ) & p3=$!
( .venv/bin/python $E --estaciones ACO --solo-seleccion --salida /content/c2/v4_supervisado 2>&1 \
    | grep --line-buffered -v -E "$F" > /content/registros/v4s_control.log ) & p4=$!
s=""; for p in $p1 $p2 $p3 $p4; do r=0; wait $p || r=$?; s="$s $r"; done
echo "== estado de los procesos:$s"; date
[ "$s" = " 0 0 0 0" ] || { echo "FALLÓ un proceso"; tail -n 5 /content/registros/v4s_*.log; exit 1; }
echo "== control: la selección de ACO dos veces"
A=results/anomalias_red_v1/v4_supervisado/d50/ACO/seleccion; B=/content/c2/v4_supervisado/d50/ACO/seleccion
cmp -s $A/historia_seleccion.csv $B/historia_seleccion.csv && echo "historia idéntica" || echo "historia DISTINTO"
.venv/bin/python -c "
import numpy as np
from tensorflow import keras
a = keras.models.load_model('$A/modelo_seleccion.keras', compile=False).get_weights()
b = keras.models.load_model('$B/modelo_seleccion.keras', compile=False).get_weights()
print('pesos idénticos' if all(np.array_equal(x, y) for x, y in zip(a, b)) else 'pesos DISTINTO')
" 2>&1 | grep -v -E "$F"
echo "== resumen de épocas"; date
.venv/bin/python $E 2>&1 | grep -v -E "$F" | tail -1
cat results/anomalias_red_v1/v4_supervisado/d50/epocas.csv
date; echo FIN_V4S
