# Revisión 21 (error fijo en ppb), un año en Colab (sesiones rev21_<año>, 2026-10-29). Uso: bash correr_revision21.sh AÑO
# Necesita en /content: codigo_rev21.tgz (lo cambiado desde 058b7d1; el remoto está en f931246), datos_rev21_<año>.tgz (matrices,
# residuos de calibración del V4, puntajes de las revisiones 18 y 20 del año, modelo y umbrales de PARAAD, con SHA-256) y
# zips.tgz. L0, V4S, R3 y V4 se evalúan dos veces en paralelo con el entorno del repo; PARAAD se califica con su
# entorno registrado (TensorFlow 2.21.0 y Keras 3.13.2), y su año limpio se compara con el de la revisión 20.
set -e
set -o pipefail
A_=$1
mkdir -p /content/registros && cd /content
echo "== clonar"; date
[ -d lorawan11-rama-detection ] || git clone -q https://github.com/JoseLili/lorawan11-rama-detection.git
cd lorawan11-rama-detection && git log --oneline -1
[ "$(git rev-parse --short HEAD)" = "f931246" ] || { echo "FALLÓ: HEAD distinto de f931246"; exit 1; }
tar -xzf /content/codigo_rev21.tgz && tar -xzf /content/datos_rev21_$A_.tgz
sha256sum -c --quiet datos_rev21_$A_.sha256 && echo "datos OK"
sha256sum experiments/anomalias_red/evaluar_revision21.py experiments/anomalias_red/resumir_revision21.py | cut -c1-16
lscpu | grep 'Model name'
echo "== entorno del repo (Python 3.14.7)"; date
pip -q install uv
uv python install 3.14.7
[ -x .venv/bin/python ] || uv venv -q --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt 2>&1 | tail -1
tar -xzf /content/zips.tgz
grep -E '  [0-9]{2}RAMA\.zip$' docs/checksums_2020_2026.txt | (cd data/raw && sha256sum -c --quiet -) && echo "zips OK"
.venv/bin/python -m pytest -q tests/test_revision19.py tests/test_v4_supervisado.py 2>&1 | tail -1
echo "== entorno de PARAAD (TensorFlow 2.21.0, Keras 3.13.2)"; date
PY=python3
if [ "$($PY -c 'import tensorflow as tf, keras; print(tf.__version__, keras.__version__)' 2>/dev/null)" != "2.21.0 3.13.2" ]; then
  uv venv -q --python 3.13 /content/paraad_env
  uv pip install --python /content/paraad_env/bin/python tensorflow-cpu==2.21.0 keras==3.13.2 numpy==2.1.3 pandas scipy scikit-learn pyarrow pycryptodome 2>&1 | tail -1
  PY=/content/paraad_env/bin/python
fi
$PY -c 'import sys, tensorflow as tf, keras, numpy; print("PARAAD", sys.version.split()[0], tf.__version__, keras.__version__, numpy.__version__)'
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
echo "== L0, V4S, R3 y V4 dos veces en paralelo, y PARAAD a la vez"; date
E=experiments/anomalias_red/evaluar_revision21.py
( TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1 .venv/bin/python $E --anio $A_ 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval21_1.log ) & p1=$!
( TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1 .venv/bin/python $E --anio $A_ --salida /content/c2/revision21/$A_ 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval21_2.log ) & p2=$!
(
  M=results/anomalias_red_v1/revision20/colab_20261028/recuperado/definitivo
  C=results/anomalias_red_v1/revision20/examen/$A_/mascara_comun.csv
  U=results/anomalias_red_v1/revision20/calibracion_2023/registro.json
  O=results/anomalias_red_v1/revision21/paraad/$A_
  case $A_ in 2024) L=limpia_2024;; 2025) L=limpia_2025;; 2026) L=limpia_2026;; esac
  $PY experiments/anomalias_red/puntuar_paraad.py --modelo $M --matriz results/anomalias_red_v1/matrices/matriz_$L.csv.gz \
      --comunes $C --umbrales $U --examen-registrado --salida $O/control_$L
  for f in results/anomalias_red_v1/matrices/matriz_fijo_*${A_}_*_a*.csv.gz; do
    n=$(basename $f .csv.gz); n=${n#matriz_}
    $PY experiments/anomalias_red/puntuar_paraad.py --modelo $M --matriz $f --comunes $C --umbrales $U --examen-registrado --salida $O/$n
    echo "PARAAD $n listo"
  done
) 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/paraad21.log & p3=$!
s=""; for p in $p1 $p2 $p3; do r=0; wait $p || r=$?; s="$s $r"; done
echo "== estado:$s"; date
[ "$s" = " 0 0 0" ] || { echo "FALLÓ una corrida"; tail -n 5 /content/registros/eval21_*.log /content/registros/paraad21.log; exit 1; }
for f in resultados.csv intervalos.csv falsas_alarmas.csv contra_proporcional.csv conteos.csv mascara_comun.csv; do
  cmp -s results/anomalias_red_v1/revision21/$A_/$f /content/c2/revision21/$A_/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
cmp -s <(zcat results/anomalias_red_v1/revision21/$A_/dias_$A_.csv.gz) <(zcat /content/c2/revision21/$A_/dias_$A_.csv.gz) && echo "dias idéntico" || echo "dias DISTINTO"
grep control results/anomalias_red_v1/revision21/$A_/configuracion.json
echo "== PARAAD: año limpio contra la revisión 20"
.venv/bin/python - <<PYEOF
import pandas as pd, numpy as np, json
L = {2024: 'limpia_2024', 2025: 'limpia_2025', 2026: 'limpia_2026'}[$A_]
a = pd.read_csv(f'results/anomalias_red_v1/revision21/paraad/$A_/control_{L}/puntajes.csv', index_col='dia')
b = pd.read_csv(f'results/anomalias_red_v1/revision20/examen/$A_/puntajes/{L}.csv', index_col='dia')
u = json.load(open('results/anomalias_red_v1/revision20/calibracion_2023/registro.json'))['umbrales']
d = float(np.nanmax(np.abs(a.to_numpy() - b.to_numpy())))
cambios = {p: int(((a > v) != (b > v)).to_numpy()[~np.isnan(b.to_numpy())].sum()) for p, v in u.items()}
print('PARAAD limpio: diferencia máxima', d, 'alertas distintas', cambios)
json.dump(dict(diferencia_maxima=d, alertas_distintas=cambios), open('results/anomalias_red_v1/revision21/paraad/$A_/control_revision20.json', 'w'))
PYEOF
echo "== resumen con PARAAD"; date
.venv/bin/python experiments/anomalias_red/resumir_revision21.py --anio $A_ 2>&1 | grep -v -E "$F" | tail -2
tar -czf /content/eval21_$A_.tgz results/anomalias_red_v1/revision21/$A_ results/anomalias_red_v1/revision21/paraad/$A_ && sha256sum /content/eval21_$A_.tgz
date; echo FIN_EVAL21
