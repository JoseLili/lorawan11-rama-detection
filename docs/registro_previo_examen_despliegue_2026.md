> **Estado: borrador sustituido** por `registro_previo_rev22_mas_anios.md` (2026-11-07). No se ejecutó; se conserva por transparencia del proceso de registro.

# Registro previo del examen de despliegue: Ens-V0r contra L0 en 2026 (agosto en adelante, uso único)

Fecha: 2026-11-07. **Estado: borrador para aprobación del tesista.** Nadie ha visto ningún dato posterior al 2026-07-31.

## Para qué es este examen
El examen final simula el **despliegue**: un detector congelado opera sobre el año en curso, que todavía no termina, con los datos conforme se publican. Así se hizo en la revisión 17 con enero–julio de 2026, y este examen es su continuación. Las etapas del protocolo (§4) no cambian:

| Etapa | Años |
|---|---|
| Entrenamiento definitivo | 2020–2022, ya hecho, sin reentrenar |
| Calibración | 2023 limpio |
| Historia, nunca evaluada | enero–julio de 2026 |
| **Examen de uso único** | **del 2026-08-01 al último día del último mes completo publicado** |

- **Datos:** el tesista descarga de SIMAT el zip 26RAMA actualizado. Al subirlo se registra su SHA-256 y **se fija el fin de la ventana**, antes de cualquier puntaje.
- **Auditoría:** sólo formato, sin modelos. Debe haber 24 horas por día, y la cobertura de cada estación se reporta.
- **M y C (revisión 22) quedan en pausa.** Si se retoman, su examen será la siguiente ventana de despliegue (los meses posteriores a ésta), con su propio registro.

## Detectores, congelados antes de abrir el examen

| Detector | Qué es | Papel |
|---|---|---|
| **Ens-V0r** | Media del puntaje diario de los 5 L0 definitivos con línea base V0 (semillas 42, 1, 2, 3 y 4), en `results/linea_base/examen_final/modelos/` | **Candidato principal** |
| **L0** | `modelo.keras` definitivo de δ = 50 % de la revisión 14, el «L0 único» | Comparador |
| L0 por δ, R3 y V4 | Como en la revisión 17 | Descriptivos, para continuidad |

- Se verifican los SHA-256 de los 6 modelos antes de puntuar.
- **No se entrena nada.**

## Umbrales
- **p99 y p99.9:** salen de los puntajes de 2023 limpio ya guardados (`calibracion_2023.npz`), en las estación-días comunes a Ens-V0r y L0 con 12 horas o más.
- **L0 por δ, R3 y V4:** usan sus umbrales de 2023 de la revisión 17.

## Calendarios de ataque
- **10 calendarios**, `plan_episodios`, con la semilla maestra 42 y la clave [2026, 8]. Empiezan el 2026-08-01; un episodio que rebasa el fin de la ventana se corta.
- **Igual que el protocolo:**
  - p uniforme en (0.0010, 0.0030), episodios de 1 a 7 días y signo ±;
  - las 31 estaciones alterables;
  - δ = 100, 50, 20, 10 y 5 %, con el mismo plan (diseño pareado).
- Los planes se guardan con su SHA-256 antes de puntuar.

## Métricas
- **Unidades:** estación-días comunes a Ens-V0r y L0 (≥ 12 horas). R3 y V4 se miden en las suyas, como en la revisión 17.
- **Punto principal: p99.**
  - Con unos tres meses (≈ 2 850 estación-días limpias), el p99.9 esperaría unas 3 falsas alarmas: demasiado ruido para decidir.
  - El p99.9 y la curva de operación (0.05 a 5 %) se reportan como descriptivos.
- **Por δ:** F1, recall y precisión, con F̄ = media del F1 con δ = 100, 50 y 20 %.
- **También se reportan:**
  - la tasa de falsas alarmas lograda en la ventana limpia;
  - M1 (falsas alarmas a 1–14 días de un episodio);
  - las alarmas por estación al mes.

## Regla de adopción (una sola prueba, en p99)
**Por qué no inferioridad y no superioridad:**
- en 2017–2019, Ens-V0r y L0 quedaron prácticamente empatados (F̄ 0.380 frente a 0.363 en p99, y 0.416 frente a 0.413 en p99.9);
- la razón para preferir el ensamble es otra: no depende de una sola semilla en un modelo que siempre elige E = 1 (LB2).

**Ens-V0r se adopta como detector principal** si el límite inferior del IC del 95 % de ΔF̄ (Ens-V0r − L0) en p99 es mayor que **−0.02**:
- bootstrap pareado de 2000 remuestreos;
- bloques estación × mes (31 × número de meses);
- umbrales fijos y semilla [42, 23, 1].

Además:
- **Si el límite inferior también es mayor que 0,** se reporta como **superior**.
- **Si no se cumple,** L0 sigue como principal. Se reporta como resultado negativo y no se repite con otros parámetros.

**Reproducibilidad:** dos corridas de inferencia que deben salir idénticas.

## Predicciones (Claude, antes de abrir)
1. La prueba de no inferioridad pasa.
2. La de superioridad no: el IC de ΔF̄ incluye el 0.
3. La tasa de falsas alarmas lograda con p99 queda entre 0.5 y 1.5 % para los dos.
4. Con p99 y δ = 100 %, Ens-V0r logra F1 ≥ 0.40, como en 2025 (0.404) y 2017–2019 (0.457).
5. Con δ = 20 %, F1 < 0.25 para los dos con p99.
