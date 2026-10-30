# Inicio: revisión 20c, el sesgo de PARAAD en Barcelona

Preparado por Claude el 2026-10-29 para el chat que construyó la tubería de Barcelona (revisión 20b).
El diseño está **registrado y aprobado** en `docs/protocolo_anomalias_red_v1.md`, en la fila 20c y la
sección «Revisión 20c». Aquí sólo se resume qué correr.

## Qué es

- Los modelos **congelados** de la 20b (L0 único entrenado con δ = 50 % proporcional, los 13 V4 y
  PARAAD-SA), sin entrenar ni recalibrar.
- Los umbrales p99 y p99.9 de 2017 (`calibracion_2017_colab/recuperado/salidas/calibracion/congelado.json`)
  y el p95 horario del V4.
- **Los planes ya generados y registrados:** `results/barcelona_paraad/planes_sesgo_v1/`, con
  `prueba_2018` (125 calendarios) y `complementaria_2019` (125), descritos en
  `docs/planes_sesgo_barcelona_v1.md`:
  - 4 de 13 estaciones y el 30 % de sus días;
  - alterado = observado + β·σ de ajuste, con β de `truncnorm(0.2, 2, scale=2)`;
  - en µg/m³, sin redondear a ppb.

## Qué falta programar

1. **Aplicar el sesgo** con esos planes. Es el equivalente aditivo de
   `experiments/barcelona/aplicar_ataques_proporcionales.py`:
   - sólo en las horas observadas;
   - las máscaras no cambian;
   - el contexto se recalcula con las escalas limpias fijas.
2. **Evaluar** los tres detectores con la misma tubería del examen 20b:
   - los mismos universos (4 549 y 4 567 estación-días);
   - dos inferencias idénticas por matriz;
   - el control 2017.
3. **Métricas:** las mismas de la 20b:
   - F1, recall, precisión, AP y ROC-AUC;
   - el control sin inyección;
   - las tasas limpias;
   - intervalos pareados por bootstrap estación × mes con 2 000 remuestreos, y una semilla nueva
     derivada de 42 y del año.
4. **Comparación principal:** PARAAD − V4. L0 es la referencia supervisada que nunca vio esta
   anomalía.

## Cautelas ya registradas

- **La prevalencia del sesgo es de ~9 %** (contra menos del 1 % en el proporcional). La precisión
  y el F1 no se comparan entre escenarios; el recall sí.
- **No es una reproducción del artículo:** otras estaciones y umbral fijo.
- **No se ajusta nada mirando 2018–2019,** y todo se corre dos veces.

## Al terminar

- Escribir `docs/resultados_examen_barcelona_sesgo_2018_2019.md`.
- Avisar al tesista para integrar el resultado en el protocolo, como se hizo con la 20b.
