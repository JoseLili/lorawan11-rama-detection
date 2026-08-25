# Progreso

Registro cronológico del trabajo. Las decisiones y su fundamento están en
`bitacora_decisiones.md`; los hallazgos del análisis exploratorio, en los
notebooks.

---

## 2026-08-22 — Fijación de la función de decisión y EDA

### Hecho

- Repositorio inicializado: estructura, `.gitignore`, `requirements.txt`,
  entorno virtual, kernel de Jupyter registrado.
- Datos RAMA 2025 (9 contaminantes) en `data/raw/`, no versionados. Integridad
  registrada en `docs/checksums_2025.txt`.
- **Función de decisión fijada: NOM-172-SEMARNAT-2023**, Tabla 6 para O₃.
  Umbrales 58 / 90 / 135 / 175 ppb.
- Notebook `01_inspeccion_rama.ipynb`: inspección cruda, cuantificación del
  centinela `-99`, cobertura y rachas por estación, distribución de bandas,
  perfil del ciclo diurno.
- **Estación piloto seleccionada: CCA.**

### Hallazgos

**Los faltantes no son aleatorios.** 58 de 70 bloques miden exactamente 3 h, y
las horas 1–3 registran 61 faltantes cada una. No existe ningún bloque de 1 h.
Hipótesis (V11, sin verificar): calibración programada del analizador.

**Ocurren de madrugada**, cuando el O₃ es bajo y estable. La franja de faltantes
no interacciona con los umbrales de decisión: el primer corte (58 ppb) nunca se
alcanza a esa hora.

**El 30.61% de faltantes estaba inflado.** `COY`, `SFE` y `SJA` no operaron en
2025 y aportan 26,280 celdas de `-99` puras. Excluyéndolas, la cifra real de la
red operativa es **24.30%**.

**La cobertura sola es un criterio insuficiente.** CAM tiene mejor cobertura que
UIZ (90.45% vs 88.09%) pero rachas 2.4× más largas (464 h vs 195 h). Para series
temporales UIZ es mejor estación, algo que el porcentaje oculta.

**CCA es una categoría aparte**, no sólo la mejor: 96.93% de cobertura y racha
máxima de 17 h, frente a 134 h de la siguiente. Es la única estación de la red
sin ningún periodo prolongado fuera de operación en 2025.

**CCA está más expuesta que el promedio de la red**: 7.11% de horas en banda
"Mala" frente a 4.17%. No hay conflicto entre calidad de datos y exposición.

**Ventana de ataque.** Un desplazamiento de 16 ppb alcanza al 10.4% de las
lecturas para τ=58; uno de 32 ppb, al 26.5%. Ambos están dentro de la
variabilidad legítima horaria: **el ataque efectivo no necesita producir un
valor anómalo.**

**τ=175 queda fuera de alcance.** El máximo de CCA en 2025 es 149 ppb.

**Ciclo diurno bien definido.** Mínimo a las 7 h (6.24 ppb), pico a las 15 h
(82.58 ppb): factor de 13×. La desviación estándar varía en factor 5 a lo largo
del día (5.79 → 28.75).

**Ventana óptima de ataque: 15–17 h.** Coinciden máxima variabilidad legítima
(margen de ocultamiento) y máxima proximidad a los umbrales (potencial de daño).
No hay que elegir entre ambas.

**Techo nocturno.** Entre las 22 h y las 8 h, el máximo histórico de 2025 no
supera los 61 ppb. La banda "Mala" es inalcanzable de noche por medios
legítimos. Un ataque que sostenga valores altos nocturnos produce una
configuración sin precedente en el registro, detectable con un modelo
condicionado por hora.

### Decisiones

| ID | Decisión | Fundamento |
|---|---|---|
| — | NOM-172 como `f` principal | Verificada, cuatro umbrales, alcance federal. El PPRCAA (~154 ppb) no se alcanza nunca en CCA/2025: cero eventos de daño posible |
| — | PPRCAA como escalón de severidad | Daño más severo, pero bloqueado por V9 y con superficie casi nula |
| — | Estación piloto: CCA | Gana en cobertura y en racha simultáneamente, con margen de un orden de magnitud |
| — | Excluir COY, SFE, SJA | Sin operación en 2025 |
| — | Conservar el resto de estaciones | La agregación es por máximo (5.4.2); eliminarlas alteraría el índice agregado |
| — | Sólo O₃, un contaminante | Su decisión se toma sobre lectura horaria directa. PM requiere ventana de 12 h y es otro experimento |
| — | Sólo 2025 | Suficiente para todas las capas. El módulo soporta multi-año; extender es cambiar un argumento |

---

## 2026-08-23 — Módulos de ingesta y decisión

### Hecho

- **`src/ingest/rama.py`** — carga, formato largo, detección de rachas,
  segmentación, interpolación (desactivada, ver D8), split cronológico.
  16 pruebas.
- **`src/decision/nom172.py`** — función `f`: concentración en ppb → banda del
  Índice AIRE Y SALUD.
- **`src/decision/damage.py`** — métrica de daño, severidad con signo,
  clasificación inflado/ocultamiento. 29 pruebas.
- Notebooks `02_ingesta.ipynb` y `03_decision.ipynb` de verificación.
- **`docs/02_codificacion.md`** — decisión de codificación del payload.

### Verificación cruzada

Ambos módulos reproducen independientemente los resultados calculados a mano en
el EDA:

- Ingesta sobre CCA/2025: 68 filas descartadas, 6 segmentos, 201 interpoladas,
  0 NaN restantes.
- Decisión sobre CCA/2025: 77.470% / 15.181% / 7.113% / 0.236% / 0.000%.

### Errores encontrados y corregidos

**`groupby.apply` en pandas 3.** La columna de agrupación ya no se pasa a la
función. Producía `KeyError: 'station'`. Corregido iterando explícitamente sobre
los grupos. Prueba de regresión añadida.

**`segment_id` duplicados entre estaciones.** El `cumsum()` se reiniciaba en
cada estación, de modo que CCA y TLA compartían identificadores. **No producía
ningún error**: habría generado resultados sutilmente incorrectos de forma
silenciosa. Encontrado por revisión de código, no por ejecución. Prueba de
regresión añadida.

**`daño()` fallaba con entrada escalar.** `banda_o3` es polimórfica y devuelve
`int` para escalares; `.astype()` no existe en `bool`. Encontrado por las
pruebas. Prueba de regresión añadida.

### Decisiones

| ID | Decisión | Fundamento |
|---|---|---|
| **D7** | Codificación: Analog Input `0x02` reinterpretado a 1 ppb/LSB | CayenneLPP no define tipo para gases. 1 ppb coincide con la resolución normativa (NOM-172, Tabla 2) y con la nativa de RAMA. Detalle en `docs/02_codificacion.md` |
| **D8** | La ausencia de dato no se imputa: se representa como ausencia de mensaje | Ningún valor centinela funciona (`0` es un valor real). `-99` es artefacto del formato SIMAT, no de LoRaWAN: un nodo fuera de servicio no transmite. Se añade `delta_t` como característica |

**Nota sobre `0x7D` (Concentration).** Se evaluó como alternativa
semánticamente correcta, pero **no aparece en la tabla oficial del repositorio
de myDevices**. La única evidencia es un foro de TTN de 2019 y librerías de
terceros. Descartado por credibilidad. El hecho de que exista un tipo no oficial
en circulación refuerza el hallazgo de que el formato no cubre el dominio.

---

## Siguiente

1. **`src/encoding/`** — el módulo más crítico del proyecto. Produce el *ground
   truth*: si tiene error de endianness, escala o signo, todos los resultados
   posteriores son incorrectos sin fallo visible.
   - Codificación ppb → trama CayenneLPP
   - Construcción del bloque contador A_i (pendiente V14)
   - Cifrado y descifrado AES-CTR
   - Flip de bit en posición arbitraria
   - Prueba de extremo a extremo de la maleabilidad
2. **`delta_t`** — definir el tratamiento de la primera fila de cada segmento,
   donde no está definida.
3. **`src/attack/`** — modelos de adversario (ciego, informado, calibrado).
4. **V1** — verificación empírica de oscilación vs. deriva. Bloquea las
   afirmaciones sobre ataque sostenido.

---

## Pendientes abiertos

| ID | Descripción | Estado |
|---|---|---|
| V1 | Oscilación vs. deriva bajo flip repetido | Abierto — bloquea afirmaciones sobre ataque sostenido |
| V5 | Estabilidad del formato RAMA en años anteriores | Abierto |
| V8 | Efecto de la compleción horaria (≥45 min) | Diferido hasta tener el simulador |
| V9 | Tabla de conversión de la NADF-009-AIRE-2017 | Abierto — bloquea el Sistema B |
| V10 | Mapeo de las 37 estaciones a las cinco zonas de la ZMVM | Abierto |
| V11 | Confirmar la hipótesis de calibración con documentación del SIMAT | Abierto |
| V12 | Verificar por qué el mínimo diario está a las 7 h y no a medianoche | Abierto |
| V13 | Resolución de Analog Input | **CERRADO** — 2 bytes, 0.01, con signo |
| V14 | Construcción del bloque contador A_i en LoRaWAN 1.1 | Abierto — bloquea `src/encoding/` |
| V15 | Oficialidad del tipo `0x7D` | **CERRADO** — no está en la tabla oficial |

Cerrados en sesiones anteriores: V2, V3, V4 (con la NOM-172 en mano).

---

## Fuera de alcance

Registrado para trabajo futuro, no se persigue en esta tesis:

- **Envenenamiento del modelo de pronóstico** que activa la Fase Preventiva del
  PPRCAA. Coherente con el modelo de adversario, pero es *data poisoning* contra
  un modelo cuya arquitectura no es observable desde la posición NS↔AS.
- **Descubrimiento de CVE** en el manejo de contadores de implementaciones
  LoRaWAN (bitácora D6). La superficie identificada es la disciplina de
  contador, no el cifrado.
- **Extensión a PM10 y PM2.5.** El contraste entre agregación horaria (O₃) y
  ventana de 12 h (PM) demostraría que la resistencia del sistema depende de
  cómo agrega la aplicación. Segunda fase, no punto de partida.