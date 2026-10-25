# Revisión 17, examen final en Colab (sesión rev16, después de correr_revision16.sh). Copia exacta del guion
# (SHA-256 del original: 37931e36936627fe…). Necesita en /content codigo_rev17.tgz.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
echo "== examen final (revisión 17)"; date
tar -xzf /content/codigo_rev17.tgz && sha256sum experiments/anomalias_red/examen_final.py results/anomalias_red_v1/examen_final_modelos_congelados.json | cut -c1-16
lscpu | grep 'Model name'
export PYTHONUNBUFFERED=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
echo "== planes y matrices de 2025–2026"; date
.venv/bin/python experiments/anomalias_red/generar_planes.py --final 2>&1 | grep -c "(nuevo)" || { echo "FALLÓ planes"; exit 1; }
.venv/bin/python experiments/anomalias_red/generar_matrices.py --final 2>&1 | tail -1 || { echo "FALLÓ matrices"; exit 1; }
echo "== matrices de hora al azar (la segunda vez sólo comprueba)"; date
.venv/bin/python experiments/anomalias_red/examen_final.py --solo-generar 2>&1 | grep -v -E "$F" | tail -1 || { echo "FALLÓ hora al azar 1"; exit 1; }
.venv/bin/python experiments/anomalias_red/examen_final.py --solo-generar --salida /content/c2/examen_final 2>&1 | grep -v -E "$F" | tail -1 || { echo "FALLÓ hora al azar 2"; exit 1; }
grep -c "ya existía, idéntico" /content/c2/examen_final/matrices_hora_azar.csv
echo "== examen, dos corridas en paralelo"; date
( .venv/bin/python experiments/anomalias_red/examen_final.py --tolerancia-v4 1e-4 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/final_1.log ) & p1=$!
( .venv/bin/python experiments/anomalias_red/examen_final.py --tolerancia-v4 1e-4 --salida /content/c2/examen_final 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/final_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -5 /content/registros/final_*.log; exit 1; }
A=results/anomalias_red_v1/examen_final
for f in resultados.csv hora_azar.csv falsas_alarmas.csv intervalos.csv conteos.csv curva.csv; do
  cmp -s $A/$f /content/c2/examen_final/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
diff -rq $A/planes /content/c2/examen_final/planes && echo "planes idénticos" || echo "planes DISTINTO"
date; echo FIN_FINAL
