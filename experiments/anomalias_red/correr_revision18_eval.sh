# Revisiones 18 y 18b, evaluación en Colab (sesión rev18b, después de correr_revision18b.sh). Necesita en
# /content eval_rev18.tgz (las matrices de 2020–2026 que usa y los residuos de calibración 2023 del V4, que no
# están en git, con sus SHA-256) y codigo_rev18b.tgz. Corre la evaluación dos veces en paralelo y compara.
set -e
set -o pipefail
cd /content/lorawan11-rama-detection
echo "== evaluación de la revisión 18"; date
tar -xzf /content/eval_rev18.tgz
sha256sum -c --quiet datos_eval_rev18.sha256 && echo "datos OK"
tar -xzf /content/codigo_rev18b.tgz          # el evaluar_revision18.py de la 18b, con los dos V4S
sha256sum experiments/anomalias_red/evaluar_revision18.py | cut -c1-16
lscpu | grep 'Model name'
export PYTHONUNBUFFERED=1 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1
F="^(WARNING|I0000|W0000|E0000|To enable)|retracing|cuda|Source Location"
E=experiments/anomalias_red/evaluar_revision18.py
( .venv/bin/python $E 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval18_1.log ) & p1=$!
( .venv/bin/python $E --salida /content/c2/revision18 2>&1 | grep --line-buffered -v -E "$F" > /content/registros/eval18_2.log ) & p2=$!
s1=0; wait $p1 || s1=$?
s2=0; wait $p2 || s2=$?
echo "== estado: $s1 $s2"; date
[ "$s1" = 0 ] && [ "$s2" = 0 ] || { echo "FALLÓ una corrida"; tail -n 5 /content/registros/eval18_*.log; exit 1; }
A=results/anomalias_red_v1/revision18
for f in resultados.csv curva.csv intervalos.csv falsas_alarmas.csv conteos.csv control_revision17.csv; do
  cmp -s $A/$f /content/c2/revision18/$f && echo "$f idéntico" || echo "$f DISTINTO"
done
for a in 2024 2025 2026; do
  cmp -s <(zcat $A/dias_$a.csv.gz) <(zcat /content/c2/revision18/dias_$a.csv.gz) && echo "dias_$a idéntico" || echo "dias_$a DISTINTO"
done
grep control_revision17_igual $A/configuracion.json
date; echo FIN_EVAL18
