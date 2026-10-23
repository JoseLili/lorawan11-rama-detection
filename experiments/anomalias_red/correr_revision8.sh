#!/bin/bash
# Corrida completa de la revisión 8 con la forma ya elegida con 2022 (docs/runbook_pc_revision8.md, paso 6).
#
#   bash experiments/anomalias_red/correr_revision8.sh <forma> [δ ...]      p. ej.: ... a14   o   ... a14 100 50
#
# Por cada δ: LSTM supervisado con vecinas dos veces (la segunda con --sustituir) y comparación de
# salidas; Random Forest de control (verifica dentro del script dos entrenamientos idénticos); regla
# de vecinas dos veces y comparación. Registros en logs_revision8/ (no van a git). Se detiene en el
# primer error.
set -eo pipefail
cd "$(dirname "$0")/../.."
FORMA=${1:?falta la forma elegida con 2022: a14, afija, b14 o bfija}
shift
DELTAS=${*:-100 50 20 10 5}
PY=${PY:-.venv/bin/python}
R=results/anomalias_red_v1
L=logs_revision8
mkdir -p $L
F="^(WARNING|I0000|To enable|W0000|E0000|=== Source|external/xla|$)"

comparar () {   # carpeta copia1 archivos...
  local out=$1 c1=$2; shift 2
  for f in "$@"; do cmp -s "$c1/$f" "$out/$f" && echo "  $f idéntico" || { echo "  $f DISTINTO"; return 1; }; done
  [ "$(zcat "$c1/puntajes.csv.gz" | sha256sum)" = "$(zcat "$out/puntajes.csv.gz" | sha256sum)" ] \
    && echo "  puntajes idénticos" || { echo "  puntajes DISTINTOS"; return 1; }
}
dos_veces () {  # δ nombre carpeta archivos-a-comparar -- comando...
  local d=$1 nombre=$2 out=$3 archivos=$4; shift 5
  echo "== δ = $d %: $nombre"; date
  "$@" 2>&1 | grep -v -E "$F" > $L/d${d}_${nombre}_1.log
  rm -rf $L/d${d}_${nombre}_c1 && cp -r "$out" $L/d${d}_${nombre}_c1
  "$@" --sustituir 2>&1 | grep -v -E "$F" > $L/d${d}_${nombre}_2.log
  comparar "$out" $L/d${d}_${nombre}_c1 $archivos
}

for d in $DELTAS; do
  dos_veces $d lstm $R/lstm_sup_vecinas_${FORMA}_20cal/d$d "metricas.csv episodios.csv por_tamano.csv historia_definitiva.csv" -- \
    $PY experiments/anomalias_red/entrenar_lstm_sup.py --delta $d --entradas vecinas --forma $FORMA --calendarios 20
  echo "== δ = $d %: rf"; date
  $PY experiments/anomalias_red/entrenar_rf.py --delta $d --calendarios 20 --entradas vecinas --forma $FORMA \
    2>&1 | grep -v -E "$F" > $L/d${d}_rf.log
  dos_veces $d regla $R/regla_vecinas_${FORMA}/d$d "metricas.csv episodios.csv por_tamano.csv" -- \
    $PY experiments/anomalias_red/evaluar_regla_vecinas.py --delta $d --forma $FORMA
done
date; echo FIN
