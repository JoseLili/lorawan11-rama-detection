#!/bin/bash
# Corrida completa de la revisión 10 (mediana de 14 días, forma a14), sólo si la elección con 2022
# (diagnostico_referencia_2022.py) eligió la mediana. Igual que correr_revision8.sh:
#
#   bash experiments/anomalias_red/correr_revision10.sh [δ ...]      p. ej.: ... 100 5   o   ... 50 10
#
# Por cada δ: LSTM supervisado con vecinas y mediana dos veces (la segunda con --sustituir) y
# comparación de salidas; regla de vecinas con mediana dos veces y comparación. El Random Forest no
# se repite (revisión 10 del protocolo). Registros en logs_revision10/ (no van a git). Se detiene en
# el primer error.
set -eo pipefail
cd "$(dirname "$0")/../.."
DELTAS=${*:-100 50 20 10 5}
PY=${PY:-.venv/bin/python}
R=results/anomalias_red_v1
L=logs_revision10
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
  dos_veces $d lstm $R/lstm_sup_vecinas_a14_mediana_20cal/d$d "metricas.csv episodios.csv por_tamano.csv historia_definitiva.csv" -- \
    $PY experiments/anomalias_red/entrenar_lstm_sup.py --delta $d --entradas vecinas --forma a14 --referencia mediana --calendarios 20
  dos_veces $d regla $R/regla_vecinas_a14_mediana/d$d "metricas.csv episodios.csv por_tamano.csv" -- \
    $PY experiments/anomalias_red/evaluar_regla_vecinas.py --delta $d --forma a14 --referencia mediana
done
date; echo FIN
