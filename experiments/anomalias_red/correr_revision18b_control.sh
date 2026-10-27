# Revisión 18b: el control de reproducibilidad otra vez, solo (la segunda corrida en paralelo se quedó sin memoria
# al llegar al definitivo). Mismos hilos que la principal.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
export PYTHONUNBUFFERED=1 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
A=results/anomalias_red_v1/v4_supervisado_compartido/d50
echo "== la selección de la corrida 2 (antes de quedarse sin memoria) contra la principal"
cmp -s $A/seleccion/historia_seleccion.csv /content/c2/v4_supervisado_compartido/d50/seleccion/historia_seleccion.csv && echo "historia de selección idéntica" || echo "historia de selección DISTINTO"
echo "== control completo, solo"; date
.venv/bin/python experiments/anomalias_red/entrenar_v4_supervisado.py --compartido --salida /content/c3/v4_supervisado_compartido 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/v4sc_3.log
B=/content/c3/v4_supervisado_compartido/d50
for f in seleccion/historia_seleccion.csv historia_definitiva.csv; do cmp -s $A/$f $B/$f && echo "$f idéntico" || echo "$f DISTINTO"; done
.venv/bin/python -c "
import numpy as np
from tensorflow import keras
a = keras.models.load_model('$A/modelo.keras', compile=False).get_weights()
b = keras.models.load_model('$B/modelo.keras', compile=False).get_weights()
print('pesos del definitivo idénticos' if all(np.array_equal(x, y) for x, y in zip(a, b)) else 'pesos DISTINTO')
" 2>&1 | grep -v -E "$F"
date; echo FIN_CONTROL18B
