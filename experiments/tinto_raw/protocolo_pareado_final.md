# Piloto pareado congelado TINTO / Ens-Vb-X — 2026-11-11

Autorizado por el tesista; ZIP2020–2026 proporcionados. Se usan2020–2025 solamente.
TINTO-CNN-GRU-D2 congelado antes de abrir calibración2023/evaluación2025.
Ens-Vb-X definitivo: cinco Vb_R semillas42,1,2,3,4 entrenados2020–2022 y tau
0.259588868885851. No usar definitivo sobre2022 como comparación de generalización.

Piloto de factibilidad pareada, no veredicto de superioridad:
- Calibración2023 originales; evaluación2025; historia continua desde2020,
  incluyendo2024. Modelo TINTO entrenado2021 y selección2021; mapa2020–2021.
- Primer calendario histórico final_2025_01, por número, sin elegir por resultado.
  Preservar estaciones, fechas y duraciones1–7 días. Sustituir signos por escenario:
  ocho multiplicativos x*(1+d),x/(1+d),d=1,.5,.2,.05; cuatro aditivos positivos
  +5/+10/+20/+40ppb. Sin redondeo ni clipping; mismos valores exactos para ambos.
  No equivale a métricas históricas redondeadas/con signos mezclados.
- Ataques a toda hora observada del episodio; historia alterada fluye a ambos
  detectores, sin reset después del episodio. Originales y todos los días normales
  de2025 permanecen, sin balancear clases. No inyectar ataques para entrenar.
- Soporte principal: intersección de elegibilidad diaria. TINTO requiere objetivo
  y dos días previos completos; Ens-Vb-X≥12 horas válidas. Fijar soporte por datos
  originales antes de métricas; reportar cobertura propia y común.
- Umbrales separados por detector en mismo soporte2023: p95,p98,p99,p99.9,
  función histórica, alerta score>umbral. p99 principal. Congelar antes de ataques.
- Reportar TP/FP/FN/TN,recall,precisión,F1,AUC/AP; falsas alertas sobre originales
  y normales dentro de calendarios alterados, incluidas14 jornadas posteriores
  al episodio de esa estación. Cantidades teóricas=Nneg*(1-p/100), no garantía.
- Misma decisión al final del día. TINTO predice antes y contrasta al final;
  Ens-Vb-X agrega sus probabilidades horarias al final. Mantener preprocesamiento
  histórico de cada detector. Reutilizar motor rev24 sin modificar fuente.
- Verificar hashes, recarga, regresión de calibración completa Ens-Vb-X contra
  umbrales guardados2023 (tolerancia numérica1e-5), forma y finitud de puntajes,
  integridad final de modelos; guardar planes, soporte, puntajes y costos.
- Costos descriptivos CPU mismo proceso: preparación+inferencia por detector,
  tamaño archivos y parámetros; no confundir tiempos de caché/incrementales con
  despliegue ni archivo.keras con memoria RAM. No usar tiempos para elegir modelo.
- Un calendario y año ya utilizados por el proyecto: resultados exploratorios,
  no prueba independiente, no IC de superioridad con este piloto. El resto de
  calendarios queda pendiente de una ampliación, sin cambiar modelos por métricas.
