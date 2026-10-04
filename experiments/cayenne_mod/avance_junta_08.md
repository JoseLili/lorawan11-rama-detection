# Experimento 08: CCA, 5 % de ataques y N aleatorio

B pierde menos lecturas por rechazo que el control binario, pero esta
campaña no muestra una reducción clara del daño por lectura que escapa al
LSTM. La distribución uniforme de N entre 1 y 16 produce muchos rechazos;
ese efecto debe separarse de la capacidad de detección.

## Protocolo

- CCA: 1 684 lecturas válidas en 72 días, 21 de octubre a 31 de diciembre
  de 2025; 44 horas ausentes en el raw, no atacadas.
- Predicciones y p95 **guardados de CCA del notebook 09**, sin entrenamiento
  ni inferencia nueva. Umbral: 14.748355 ppb. Los 22.6 ppb corresponden al
  piloto anterior, otra referencia.
- Probabilidad independiente de ataque por lectura: 5 %. N es la cantidad
  de bits distintos invertidos en un mensaje; se elige uniformemente de
  1 a 16. Después se eligen las posiciones sin reemplazo.
- Se incluyen las posiciones reservadas y los pesos 64 y 128. No se atacan
  otros campos de la trama. Se aplica cifrar/flip/descifrar al payload.
- Base, A y B comparten momentos de ataque, N y posiciones físicas.
- 100 campañas, semillas 42…141. Ejemplo visual fijado previamente: 42.
- Predicciones congeladas; no se modela contaminación de entradas futuras.
  El modelo del 09 ya utilizaba variables de red: sólo se evalúa CCA, no se
  entrena un modelo univariable nuevo.

## Resultados por lectura

Promedios por campaña sobre las mismas 1 684 lecturas:

| Resultado | Base | A | B |
|---|---:|---:|---:|
| Ataques intentados | 83.77 | 83.77 | 83.77 |
| Rechazados: lecturas perdidas | 79.57 | 76.68 | 71.66 |
| Ataques aceptados | 4.20 | 7.09 | 12.11 |
| Cancelación: valor intacto | 0.00 | 0.05 | 0.29 |
| Valor alterado | 4.20 | 7.04 | 11.82 |
| Valor alterado con alerta | 2.79 | 4.44 | 7.72 |
| Banda local alterada sin alerta | 0.13 | 0.16 | 0.19 |

Las últimas cifras equivalen a **13, 16 y 19 eventos**, respectivamente,
acumulados en las 100 campañas. No son 100 periodos de contaminación
independientes: se repite el mismo test con otros sorteos de ataque.

Al comparar B y Base dentro de cada semilla, B tuvo menos eventos de banda
local sin alerta en 8 campañas, empató en 81 y tuvo más en 11. Son pocos
eventos; estos resultados no justifican una conclusión de superioridad
estadística ni una generalización a otro periodo.

El denominador también importa. Entre todos los ataques, la proporción de
banda local sin alerta fue 0.155 % en Base y 0.227 % en B. Entre ataques
aceptados fue 3.095 % en Base y 1.569 % en B. B admite más ataques, por lo que
una menor proporción dentro de los aceptados no asegura menos escapes en
total. Los resultados por N están disponibles para separar presupuestos.

Sin ataques, el detector guardado genera 360 alarmas en 1 684 lecturas
(21.38 %). En las campañas quedan, en promedio, 341.74 falsas alarmas sobre
lecturas no atacadas, idénticas entre formatos. No deben confundirse con
detecciones exitosas de ataques.

La semilla 42 contiene 81 ataques y cero cambios de banda local sin alerta
en los tres formatos. Las otras semillas muestran que ese cero particular
no significa que el escape sea imposible.

## Efecto diario, distinto del escape por lectura

Se combinan todos los ataques de cada campaña y se calcula el máximo de
CCA con las lecturas disponibles. Rechazos como ausentes, nunca como cero.
Una alerta por sí sola no elimina la lectura.

| Promedio de días por campaña (72 días) | Base | A | B |
|---|---:|---:|---:|
| Banda distinta con recibidos disponibles | 1.33 | 2.17 | 3.66 |
| Banda distinta considerando sólo alteraciones aceptadas | 1.04 | 1.89 | 3.40 |
| Banda distinta considerando sólo pérdidas por rechazo | 0.29 | 0.27 | 0.26 |

Las dos últimas filas son referencias del simulador que utiliza originales
para separar efectos, no políticas operativas del receptor. Pueden
interactuar y no tienen por qué sumar la primera fila.

Estos son días con daño independientemente de la alerta: **no son días de
daño no detectado**. El experimento mide la detección por lectura, y deja
sin definir la política que responde a las alertas.

## Interpretación

Al seleccionar N uniformemente de 1 a 16, la mitad de los ataques invierte
entre 9 y 16 posiciones. Muchos incluyen bits reservados. Por eso la baja
cantidad de escapes no debe atribuirse sólo al LSTM o a la distribución de
pesos. Un rechazo significa que se perdió un dato.

B admite más tramas alteradas y presenta más días con banda distinta en
este escenario. La compensación existe, pero aquí no basta para establecer
una mejora global. Sigue pendiente analizar la sensibilidad a otras
probabilidades de N y la propagación temporal, manteniendo este resultado
como referencia reproducible.

El máximo original de CCA en test es 145 ppb: no hay casos originales de
155 ppb o más para medir ocultamiento de excedencias con el detector. Sí
hubo una falsa excedencia sin alerta en B al reunir las 100 campañas; cero
en Base y A. No se extrapola ese conteo a otros periodos.

## Validación y archivos

Dos ejecuciones completas dieron tablas exactamente iguales. Se verificaron
25 131 transformaciones cifradas por ejecución. Pasaron 26 pruebas de los
experimentos 05–08, incluyendo ataques simultáneos del mismo día, rechazo
con alerta indefinida y cancelación sin acreditarla como detección.

- [Notebook ejecutado y explicación paso a paso](08_campanas_aleatorias_CCA.ipynb).
- [Plan de ataques](resultados/08/plan_ataques.csv).
- [Resultados por semilla](resultados/08/resumen_por_semilla.csv).
- [Resultados por N](resultados/08/resumen_por_n.csv).
- [Protocolo y fuentes](resultados/08/protocolo.json).
