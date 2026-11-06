# Resultados EP1: decisión por episodio con puntajes estandarizados por estación (2022)

- **Registro previo:** [registro_previo_EP1_decision_episodio_Vb.md](registro_previo_EP1_decision_episodio_Vb.md), aprobado por el tesista antes de calcular.
- **Datos:** puntajes guardados de LB1 (`results/linea_base/lb1/puntajes_2022.npz`). No se entrenó nada.
- **Script:** `experiments/linea_base/ep1.py`, que produce `results/linea_base/ep1/` (`metricas.csv`, `bootstrap.csv`, `umbrales.json`).

## Resultado según la regla registrada
**C sobre Vbr no pasa.** Con 0.1 %: ΔF̄ (C − D) = **−0.296**, IC [−0.380, −0.224]. Con 1 %: −0.235, IC [−0.303, −0.180].
La regla 2 de 3 (R) también pierde contra D: −0.083 con 0.1 % y −0.069 con 1 %, con intervalos por debajo de 0.

| Nivel | Modelo y regla | FA limpia lograda | F̄ | F1 δ 100 / 50 / 20 | Recall δ 50 | Episodios detectados, δ 50 |
|---|---|---:|---:|---|---:|---:|
| 0.1 % | Vbr, D | 1.89 % | 0.300 | 0.382 / 0.359 / 0.157 | 0.773 | 0.736 |
| 0.1 % | Vbr, C | 0.20 % | 0.004 | 0.004 / 0.004 / 0.004 | 0.003 | 0.004 |
| 0.1 % | Vbr, R | 2.14 % | 0.217 | 0.272 / 0.258 / 0.120 | 0.611 | 0.656 |
| 1 % | Vbr, D | 2.92 % | 0.246 | 0.304 / 0.289 / 0.146 | 0.825 | 0.784 |
| 1 % | Vbr, C | 0.57 % | 0.011 | 0.014 / 0.012 / 0.008 | 0.013 | 0.022 |
| 1 % | Vbr, R | 3.28 % | 0.178 | 0.218 / 0.204 / 0.111 | 0.642 | 0.674 |

V0r y el L0 guardado muestran el mismo patrón (`metricas.csv`).

## Por qué: dos problemas del diseño registrado (Claude)
1. **Umbral calibrado dentro de la muestra.**
   - Al elegir α, h o q, cada día limpio de calibración formaba parte de su propia referencia. Su e máximo posible era −ln(2/(n + 1)) ≈ 4.42, contra 5.12 fuera de la muestra (n ≈ 166 días por estación).
   - Además, el **2.5 %** de los días limpios de medición supera el máximo de su estación en los meses de calibración. Si los meses fueran intercambiables, se esperaría ≈ 0.6 %: los meses pares e impares no lo son.
   - **Consecuencia:** las tasas de falsas alarmas logradas (1.9–3.3 % con D y R) no respetan los niveles nominales (0.1 % y 1 %). Las cifras de D y R **no son comparables** con las de LB1 (F̄ 0.404 con p99.9).
2. **Autocorrelación de los puntajes limpios (hallazgo).**
   - En 2022 limpio, el CUSUM con k = 2 llega a S = 87, y el 6.4 % de las estación-días limpias tienen S > 10.
   - Hay rachas legítimas de puntaje moderadamente alto que se acumulan igual que un ataque. El umbral resultante (h ≈ 86) deja al CUSUM sin detecciones durante los episodios.
   - Esto no depende del problema 1: dentro de la muestra, los e son menores, y aun así S alcanza 84.

## Predicciones (6)
Fallaron la 1, 2, 5 y 6. La 3 se cumple (δ = 20 % < 0.15). La 4 no aplica en C, porque casi no alerta.

## Lectura y siguiente paso
- **No se adopta** ninguna regla de acumulación entre días.
- **El hallazgo de autocorrelación** indica que acumular días sobre los puntajes de L0 suma también la persistencia del clima. Un CUSUM útil necesitaría preblanquear o reiniciar, y la calibración necesitaría días limpios fuera de la muestra y del mismo régimen (por ejemplo, el año de calibración 2023, como en el protocolo de examen). Sería una revisión nueva (EP1b) y no está recomendada como prioridad.
- **Prioridad recomendada:** LB2 (semillas y ensamble de Vbr y V0r), que ataca directamente la cola de puntajes que fija el umbral estricto.
