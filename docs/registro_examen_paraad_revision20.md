# Registro previo: examen PARAAD-SA adaptado a RAMA, revisión 20

Fecha de sesión: 2026-10-28. El tesista autoriza continuar tras congelar modelo
y calibración. Registro separado antes de ejecutar o inspeccionar resultados
PARAAD de examen; se preservan los documentos compartidos mientras se cierra
el commit de revisión 19. No se crea la revisión 21.

Modelo: `results/anomalias_red_v1/revision20/colab_20261028/recuperado/definitivo/modelo_r1.keras`.
SHA-256: `1e859d91dacde32de794bc7d08aec90d5f30df4449a3ac55af93523b171eba1e`.
Escala definitiva 2020–2022, dropout 0.3, 499 épocas. No se entrena.
Calibración: `revision20/calibracion_2023/registro.json`, 8,802 estación-días;
p99=0.6405011077101032; p99.9=0.8366300233950218. Comparación estricta `>`.
Entorno local CPU TensorFlow 2.21.0, Keras 3.13.2, NumPy 2.1.3.

## Alcance fijado

- Años 2024, 2025 y enero–julio de 2026; escenarios original, B (una a la vez)
  y A (un solo nodo), los calendarios ya existentes, cinco δ=100/50/20/10/5.
- Una sola evaluación registrada, con dos inferencias idénticas por matriz
  como control numérico. No se decide arquitectura, épocas, escala o umbrales
  a partir de estos resultados; no son años totalmente inéditos porque ya
  se conocen resultados de otros detectores y revisiones.
- Días de reloj y 31 objetivos, con exactamente la máscara común que se obtiene
  de los cuatro comparadores congelados sobre el año limpio (puntajes guardados
  de revisión 18). Se controla contra sus conteos y tamaños históricos.
- MAE observado por estación-día, mínimo de 12 horas, reconstrucción recalculada
  sobre cada red alterada. La etiqueta nunca entra al modelo. No dominancia
  adicional ni promedio firmado para PARAAD.
- Se reutilizan las mismas etiquetas de planes existentes y los grupos de
  falsas alarmas. Para los dos nodos sin episodios de 2026 se admite el plan
  vacío ya definido, sin inventar anomalías.
- F1, F2, precisión, recall, falsas alarmas, TP/FP/FN/TN, PR-AUC y ROC-AUC;
  control sin ataque con puntajes del año limpio y etiquetas del calendario.
- Comparación principal entre ajustes sin etiquetas: PARAAD–V4. L0 único,
  V4S compartido y R3 son referencias; L0–PARAAD compara desempeño práctico
  con distinta supervisión y no demuestra superioridad de arquitectura.
- Intervalos del 95% de PARAAD por bootstrap estación × mes, 2,000 remuestreos,
  semillas [42,20,año,escenario]. En original se agrupan calendarios como revisión
  18; en A/B se conserva la separación de calendario como revisión 19.
- Para original se calculan además diferencias pareadas PARAAD−V4 y PARAAD−L0
  con los puntajes por día guardados de revisión 18. Para A/B no se inventan
  diferencias pareadas: sus archivos históricos sólo contienen agregados.
  Se reportan tablas comparativas y los IC individuales de PARAAD. Si se requiere
  la diferencia pareada A/B, hará falta recuperar o recalcular puntajes de los
  comparadores congelados, sin volver a escoger PARAAD.
- B: recall en los episodios conservados frente a los mismos episodios del
  original, con intervalo pareado. Precisión y F1 se interpretan dentro del
  escenario porque cambia la prevalencia. Se conservan los cinco δ.

## Trazabilidad y ejecución

Código nuevo `experiments/anomalias_red/evaluar_paraad_revision20.py`;
pruebas con datos sintéticos antes de abrir matrices de examen.
Resultados en `revision20/examen/<año>/`, con puntajes por calendario, hashes,
manifiesto de entrada y control de repetición. La recuperación sólo reutiliza
artefactos completos del mismo código, modelo, escala, máscara y matrices;
no equivale a una segunda selección del experimento. Nunca se sobrescriben
resultados históricos de otras revisiones. No se hace commit en esta sesión.
