#!/bin/bash
# Revisión 7 y controles repetidos en Colab, para comparar ahí la revisión 8 en la misma máquina
# (protocolo, revisión 8, opción A del 2026-10-23).
#
#   bash experiments/anomalias_red/correr_revision7_colab.sh [δ ...]
#
# Se corre en una COPIA APARTE del repo en la máquina de Colab, porque reemplaza (--sustituir) las
# salidas de la lap que están en git; así las de la lap no se tocan. Por cada δ:
#   - LSTM supervisado de la revisión 7 dos veces y comparación entre las dos corridas de Colab;
#   - Random Forest de la revisión 7 (verifica dentro del script dos entrenamientos idénticos);
#   - IsolationForest una vez y, al final, el V4 (cargado de disco), sin detener nada si no reproduce la lap.
# Para cada uno se reporta también si sus métricas son idénticas a las de la lap (git diff). Registros en
# logs_revision7_colab/ (no van a git). Se detiene en el primer error.
set -eo pipefail
cd "$(dirname "$0")/../.."
DELTAS=${*:-100 50 20 10 5}
PY=${PY:-.venv/bin/python}
R=results/anomalias_red_v1
L=logs_revision7_colab
mkdir -p $L
F="^(WARNING|I0000|To enable|W0000|E0000|=== Source|external/xla|$)"

frente_a_la_lap () {   # carpeta
  git diff --quiet -- "$1/metricas.csv" "$1/episodios.csv" "$1/por_tamano.csv" \
    && echo "  $1: idéntico a la lap" || echo "  $1: distinto de la lap"
}

for d in $DELTAS; do
  echo "== δ = $d %: lstm (revisión 7)"; date
  out=$R/lstm_sup_relativas_20cal/d$d
  $PY experiments/anomalias_red/entrenar_lstm_sup.py --delta $d --entradas relativas --calendarios 20 --sustituir \
    2>&1 | grep -v -E "$F" > $L/d${d}_lstm_1.log
  rm -rf $L/d${d}_lstm_c1 && cp -r $out $L/d${d}_lstm_c1
  $PY experiments/anomalias_red/entrenar_lstm_sup.py --delta $d --entradas relativas --calendarios 20 --sustituir \
    2>&1 | grep -v -E "$F" > $L/d${d}_lstm_2.log
  for f in metricas.csv episodios.csv por_tamano.csv historia_definitiva.csv; do
    cmp -s $L/d${d}_lstm_c1/$f $out/$f && echo "  $f idéntico entre las dos corridas" || { echo "  $f DISTINTO entre las dos corridas"; exit 1; }
  done
  frente_a_la_lap $out
  echo "== δ = $d %: rf (revisión 7)"; date
  $PY experiments/anomalias_red/entrenar_rf.py --delta $d --calendarios 20 --entradas relativas --sustituir \
    2>&1 | grep -v -E "$F" > $L/d${d}_rf.log
  frente_a_la_lap $R/rf_relativas_20cal/d$d
  echo "== δ = $d %: if"; date
  $PY experiments/anomalias_red/entrenar_if.py --delta $d --sustituir 2>&1 | grep -v -E "$F" > $L/d${d}_if.log
  frente_a_la_lap $R/if/d$d
done
# El V4 al final y sin detener nada: su control exige reproducir las predicciones guardadas de la lap con
# 1e-9 ppb (revisión 5), y en otro procesador puede no lograrlo. Si falla, se anota y se decide aparte.
for d in $DELTAS; do
  echo "== δ = $d %: v4"; date
  if $PY experiments/anomalias_red/evaluar_v4.py --delta $d --sustituir 2>&1 | grep -v -E "$F" > $L/d${d}_v4.log; then
    frente_a_la_lap $R/v4/d$d
  else
    echo "  v4: no reproduce las predicciones guardadas de la lap ($(grep -o 'máx. [^)]*' $L/d${d}_v4.log | head -1))"
  fi
done
date; echo FIN
