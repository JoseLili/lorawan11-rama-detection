# Revisión 14, examen 2024 en Colab (sesión rev14, 2026-10-25), después de correr_revision14.sh.
# Copia exacta del guion que se corrió (SHA-256 del original: d5a95ac84095d92e…). Se ejecuta en Colab con
# nohup setsid bash; necesita en /content los tarballs que se indican.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
echo "== examen 2024 de la revisión 14"; date
cp /content/evaluar_lstm_local_2024.py experiments/anomalias_red/
sha256sum experiments/anomalias_red/evaluar_lstm_local_2024.py experiments/anomalias_red/entrenar_lstm_local.py
lscpu | grep 'Model name'
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
corrida() {   # $1 = salida de los LSTM, $2 = salida del examen
  for d in 100 50 20 10 5; do
    echo "-- entrenar δ = $d (selección y definitivo)"; date
    .venv/bin/python experiments/anomalias_red/entrenar_lstm_local.py --delta $d --calendarios 20 --definitivo --salida $1
  done
  echo "-- examen"; date
  .venv/bin/python experiments/anomalias_red/evaluar_lstm_local_2024.py --lstm $1 --salida $2
}
( corrida results/anomalias_red_v1/lstm_local_examen results/anomalias_red_v1/lstm_local_2024 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/examen_1.log ) & p1=$!
( corrida /content/c2/lstm_local_examen /content/c2/lstm_local_2024 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/examen_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado de las corridas: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -5 /content/registros/examen_*.log; exit 1; }
A=results/anomalias_red_v1; B=/content/c2
for d in 100 50 20 10 5; do
  x=lstm_local_examen/c20/d$d
  for f in seleccion/historia_seleccion.csv historia_definitiva.csv; do
    cmp -s $A/$x/$f $B/$x/$f && echo "$x $f idéntica" || echo "$x $f DISTINTO"
  done
  for f in seleccion/dias_2022.csv.gz dias_examen.csv.gz; do
    cmp -s <(zcat $A/$x/$f) <(zcat $B/$x/$f) && echo "$x $f idénticos" || echo "$x $f DISTINTO"
  done
  cmp -s <(grep -v fecha $A/$x/configuracion.json) <(grep -v fecha $B/$x/configuracion.json) && echo "$x configuración idéntica" || echo "$x configuración DISTINTO"
done
for d in 100 50 20; do                        # la selección repite la de la elección con 2022
  cmp -s $A/lstm_local/c20/d$d/seleccion/historia_seleccion.csv $A/lstm_local_examen/c20/d$d/seleccion/historia_seleccion.csv \
    && cmp -s <(zcat $A/lstm_local/c20/d$d/seleccion/dias_2022.csv.gz) <(zcat $A/lstm_local_examen/c20/d$d/seleccion/dias_2022.csv.gz) \
    && echo "d$d selección igual a la de la elección" || echo "d$d selección DISTINTO de la elección"
done
for f in resultados.csv falsas_alarmas.csv propias_validas.csv resumen.json; do
  cmp -s $A/lstm_local_2024/$f $B/lstm_local_2024/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
date; echo FIN_EXAMEN
