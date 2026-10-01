# Revisión de figuras solicitada por el asesor — 2026-09-29

## Qué se conserva y qué cambia

Se conserva **Riesgo compuesto por bit** como indicador del caso base, sin
contramedida. Se reúnen sus componentes en tres curvas, se cambia detección
por **no detección**, y se acortan las leyendas. Las definiciones pasan al pie.
No se cambia la no detección por una métrica diaria distinta ni se fuerza el
cruce de curvas o un máximo en los bits 4–5.

Las figuras previas del notebook 08 permanecen como referencia histórica.
Las nuevas se presentan al final del notebook 09, con nombres y carpeta distintos.
No se reentrena, recalibra ni altera ningún modelo. El bit 0 se evalúa usando
las predicciones persistidas y verificadas de los modelos de red.

## Figuras nuevas

1. **Riesgo compuesto por bit:** días vulnerables (rojo), no detección (verde)
   y riesgo compuesto (azul). El daño aquí es una **falsa excedencia de 155 ppb**.
2. **Días vulnerables y no detección:** los mismos componentes rojo y verde,
   sin el producto. Sustituye la presentación titulada «Oportunidad cruda».
3. **Falsas activaciones y contingencias ocultadas:** porcentaje de días de
   todo 2025 en que existe un ataque aislado capaz de producir cada efecto.
   Este análisis anual mide sólo daño, **sin LSTM**.

Se usan las posiciones **0–7**, pesos 1, 2, 4, 8, 16, 32, 64 y 128 ppb.
Son los ocho bits inferiores del valor de 16 bits, no ocho posiciones 1–8.
Un flip puede sumar o restar: se respeta el estado previo del bit. El campo
experimental tiene resolución 1 ppb/LSB.

## Denominadores y alcance

En las figuras con LSTM se utilizan los mismos **35,704 mensajes de prueba**
y **72 días (21/oct–31/dic/2025)**. Son 27 objetivos evaluables de 33 candidatos;
cada uno conserva su p95 de entrenamiento. No se utiliza el corte operativo
22.6 ppb del piloto CCA para el conjunto de red. El máximo observado del test
es 152 ppb, por lo que no hay ocultamientos evaluables en ese periodo.

- **Días vulnerables:** días con al menos una falsa excedencia posible,
  divididos entre los 72 días. No exige que el atacante conozca cuál mensaje
  elegir; caracteriza la existencia de oportunidades, no su éxito medio.
- **No detección:** todos los ataques no detectados divididos entre todos los
  ataques del bit, sumando conteos por estación. Es el complemento del recall
  exhaustivo, **no del muestreo histórico de 78 ataques en CCA**, ni un promedio
  sin ponderar de recalls. Incluye ataques que no causan el daño considerado.
- **Riesgo compuesto:** días vulnerables (%) × no detección (%) / 100.
  Se conserva como **indicador descriptivo**, no como porcentaje empírico de
  días dañados sin detección ni como probabilidad conjunta demostrada.

El producto mezcla una oportunidad diaria y una tasa por mensaje. Incluso con
el mismo periodo y estaciones, no prueba independencia ni sustituye contar los
eventos concretos. Por eso el CSV incluye además **días con daño no detectado**
contados directamente y **no detección condicionada a causar daño**. Si no hay
ataques dañinos, esta última queda indefinida (celda vacía), no 0 ni 100 %.
La curva verde global sí está definida si existen ataques aunque ninguno cause
una falsa excedencia. No cambiar estos significados para obtener curvas suaves.

Los ejes Y de las dos primeras figuras dicen **Porcentaje (%)**, no «Días (%)»:
la curva verde cuenta ataques. Sólo la tercera usa **Días (%)**, con el mismo
denominador anual para ambas curvas; no usa sólo los días de excedencia como
denominador de ocultamientos.

## Diferencia frente a la franja histórica del notebook 08

La franja `(155 - 2**bit, 155]` era una aproximación que suponía sumar y no
condicionaba al estado del bit. Las nuevas oportunidades se comprueban con el
flip real. **No son una mera modificación estética de los números anteriores.**
Se sustituye un solo mensaje, conservando todas las otras horas y estaciones,
y se recalcula el máximo diario. No basta disminuir el máximo original si otra
lectura sigue por encima del umbral. Una estación que no era el máximo también
puede fabricar una falsa excedencia.

Las curvas no tienen por qué ser monótonas. Tampoco se preserva por obligación
el máximo histórico del bit 4, que combinaba datos anuales y detección piloto.

## Lectura prudente de las contingencias

«Falsa activación» significa que el máximo diario pasa de <155 a ≥155 ppb;
«ocultamiento» significa que pasa de ≥155 a <155 ppb. Son escenarios sobre el
indicador medido, **no simulaciones completas de declaraciones administrativas**,
duración, meteorología o acciones posteriores. Días con excedencia no equivalen
a episodios oficiales. No confundir falsas activaciones del indicador con falsos
positivos del detector. Las falsas alarmas limpias del LSTM de red siguen siendo
15.80 %, y se informan en las figuras; mayor recall no elimina ese coste.

## Archivos y ejecución

Verificación realizada: dos ejecuciones independientes produjeron tablas
idénticas; la celda nueva se ejecutó sin estado previo del notebook. Una segunda
forma de contar directamente desde el XLS confirmó los **2,920 pares día/bit**
del análisis anual. Se superaron **160 pruebas** del repositorio. Las figuras se
inspeccionaron visualmente. Esta verificación no equivale a aprobación de las
figuras por el asesor ni valida el producto como probabilidad conjunta.

- [Celda de presentación](../notebooks/09_deteccion_red.ipynb), al final.
- [Generador](../experiments/graficas_revision/generar.py), independiente del
  código protegido por hashes que entrenó los modelos.
- [Tablas](../results/revision_graficas_bits_0_7/): producto, conteos directos,
  evaluación nueva de bit 0, días anuales por efecto y protocolo con hashes.
- [Figuras](img/revision_graficas_bits_0_7/), sin sobrescribir imágenes previas.

La celda puede reproducir esta revisión. Si cambian las fuentes respecto al
protocolo guardado, se detiene antes de sobrescribirla. El generador verifica
hashes de modelos y predicciones; en el perfil float64 consolidado admite sólo
1e-12 ppb por el paso histórico de lectura/escritura CSV, manteniendo comparación
exacta de claves, predicciones, bases y umbrales. La decisión de detección de
los bits 1–7 se comprueba contra todas las etiquetas guardadas.
