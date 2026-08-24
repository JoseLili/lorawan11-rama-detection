# Progreso

Registro cronológico. Las decisiones y su fundamento están en
`bitacora_decisiones.md`; los hallazgos del EDA, en los notebooks.

---

## 2026-08-22 — Fijación de la función de decisión y EDA inicial

### Hecho

- Repositorio inicializado. Estructura, `.gitignore`, `requirements.txt`,
  entorno virtual, kernel de Jupyter registrado.
- Datos RAMA 2025 (9 contaminantes) en `data/raw/`, no versionados.
  Integridad en `docs/checksums_2025.txt`.
- **Función de decisión fijada: NOM-172-SEMARNAT-2023**, Tabla 6 para O₃.
  Umbrales 58 / 90 / 135 / 175 ppb. Cierra V2, V3, V4.
- Notebook `01_inspeccion_rama.ipynb`: inspección cruda, centinela `-99`,
  cobertura y rachas por estación, distribución de bandas en CCA.
- **Estación piloto seleccionada: CCA.**

### Decisiones

| Decisión | Fundamento |
|---|---|
| NOM-172 como `f` principal | Verificada, cuatro umbrales, alcance federal. El PPRCAA (~154 ppb) no se alcanza nunca en CCA/2025: cero eventos de daño posible |
| PPRCAA como escalón de severidad | Daño más severo, pero bloqueado por V9 y superficie casi nula |
| Estación piloto: CCA | 96.93% de cobertura y racha máxima de 17 h; gana en ambos criterios, con margen de un orden de magnitud sobre la siguiente |
| Excluir COY, SFE, SJA | Sin operación en 2025. Inflaban el porcentaje de faltantes del 24.30% al 30.61% |
| Conservar el resto de estaciones | La agregación es por máximo (5.4.2); eliminar estaciones alteraría artificialmente el índice agregado |
| Interpolar bloques ≤5 h, segmentar ≥10 h | No existe ningún bloque entre 5 y 10 h; el corte no es arbitrario |
| Codificación a 1 ppb/LSB | La Tabla 2 de la norma especifica 3 decimales en ppm = 1 ppb. Coincide con la resolución nativa de RAMA |

### Hallazgos

- Los faltantes de CCA **no son aleatorios**: 58 de 70 bloques miden
  exactamente 3 h, y las horas 1–3 registran 61 faltantes cada una.
  Hipótesis (sin verificar): calibración programada del analizador.
- Como ocurren de madrugada, cuando el O₃ es bajo y estable, la
  interpolación no sesga las lecturas cercanas a los umbrales.
- CCA registra 1.7× más horas en banda "Mala" que el promedio de la red.
  No hay conflicto entre calidad de datos y exposición.
- Ventana de ataque: un desplazamiento de 16 ppb alcanza al 10.4% de las
  lecturas; uno de 32 ppb, al 26.5%. **Ambos están dentro de la
  variabilidad legítima horaria.**

### Siguiente

- Celda 8: perfil del ciclo diurno de CCA (media, std y máximo por hora).
  Determina el margen del atacante para ocultarse en cada franja horaria.
- Formalizar el criterio de tratamiento de faltantes en `src/ingest/`.
- Módulo `src/decision/` con `f` y la métrica de daño, con tests para el
  comportamiento en los bordes de banda.

### Pendientes abiertos

| ID | Descripción |
|---|---|
| V1 | Oscilación vs. rampa bajo flip repetido — sin verificar |
| V5 | Estabilidad del formato RAMA en años anteriores |
| V8 | Efecto de la compleción horaria (≥45 min) — diferido hasta tener el simulador |
| V9 | Tabla de conversión de la NADF-009-AIRE-2017 |
| V10 | Mapeo de las 37 estaciones a las cinco zonas de la ZMVM |
| V11 | Confirmar la hipótesis de calibración con documentación del SIMAT |

### Fuera de alcance (registrado para trabajo futuro)

- Envenenamiento del modelo de pronóstico que activa la Fase Preventiva del
  PPRCAA. Coherente con el modelo de adversario, pero es *data poisoning*
  contra un modelo cuya arquitectura no es observable desde la posición
  NS↔AS. Es otra tesis.
- Descubrimiento de CVE en el manejo de contadores de implementaciones
  LoRaWAN (bitácora D6).
