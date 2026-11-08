# Registro previo de la revisión 25: fusión Ens-Vb-X + PARAAD (retador)

Fecha: 2026-11-08. **Estado: aprobado por el tesista el 2026-11-08** («hagamos la fusión… no como algo definitivo; dirá si nuestro Vb-X es el mejor o no»). Los detalles se fijan aquí antes de calcular cualquier puntaje fusionado.

## Pregunta
Las revisiones 23, 24 y 23b dejaron a Ens-Vb-X con dos huecos medidos, justo donde PARAAD-SA (sin vecinas y sin historia) sigue detectando:
1. el vecindario completo comprometido (recall de la estación atacada ≈ 0.05);
2. el sesgo sostenido de más de ~4 semanas (≈ 0.11 en las semanas 5–8).

¿Una alarma «Ens-Vb-X **o** PARAAD», con el **mismo presupuesto total** de falsas alarmas, es mejor en general que Ens-Vb-X solo? ¿Cuánto cuesta en el caso normal, con un solo nodo alterado?

**Es un retador, no un reemplazo automático.** El resultado se clasifica con las reglas de abajo y la decisión de qué detector se presenta como principal la toma el tesista después, declarándola.

## La regla de fusión
- **Detectores congelados:** Ens-Vb-X (τ = 0.2596 σ, revisión 24) y PARAAD-SA (revisión 20). No se entrena nada.
- **Alarma por estación-día:** (X > u_X(q)) **o** (P > u_P(q)). u_X(q) y u_P(q) son los umbrales de cada detector en **2023 limpio** con la misma tasa individual *q* (`ev.umbral_falsas_alarmas`). Equivale a tomar, para cada estación-día, el más raro de los dos puntajes según su percentil en 2023.
- **Presupuesto total:** *q* es el mayor valor (en una rejilla de 2 001 puntos entre objetivo/2 y objetivo) con el que la tasa de alarmas combinada en 2023 limpio es ≤ 1 % (p99) y ≤ 0.1 % (p99.9).
- **Estación-días de 2023:** las 9 097 comunes de la revisión 22 que además tengan puntaje de PARAAD.
- **PARAAD en 2023** se recalcula con las mismas funciones (Keras 3.15.1) que en el banco, para que todo sea consistente. Se reporta la diferencia con la calibración de la revisión 20 (≈ 1.4e-6).
- **No se usa 2022:** PARAAD se entrenó con 2020–2022.

## Datos (todos ya puntuados; no se puntúa nada nuevo salvo PARAAD en 2023)
- **Banco 2024–jul 2026** (revisión 24, corrida a): E1, E2-1, E2-2 y E2-4 × δ 100/50/20 y 10/20/40 ppb. Estación-días evaluables las de la revisión 24.
- **D1** (revisión 23b, corrida a): escalón, rampa 28 y deriva 56 × 20/40 ppb, con las estación-días evaluables de la 23b.
- **Ventana de despliegue ago–sep 2026,** descriptiva. Ens-Vb-X de la revisión 24 (`despliegue`) y PARAAD de la revisión 22 (`paraad_diario.npz`), en las estación-días válidas para ambos.

## Pruebas (p99; IC del 95 %, bootstrap pareado estación × mes, 2 000 remuestreos)
| | Medida | Pasa si | Semilla |
|---|---|---|---|
| **T1, no daña demasiado** | E1, ΔF̄ (δ 100/50/20) Fusión − Ens-Vb-X | límite inferior del IC > −0.02 | [42, 25, 1] |
| **T2, cubre el coordinado** | E2-4, δ50, Δrecall de la estación original | IC > 0 | [42, 25, 1] |
| **T3, cubre el lento** | D1, escalón +20 ppb, Δrecall en las semanas 5–8 | IC > 0 | [42, 25, 2] |

**Veredicto (clasificación, no adopción automática):**
- **T1, T2 y T3 pasan:** «la fusión es mejor en general que Ens-Vb-X».
- **T2 y T3 pasan pero T1 falla:** «compromiso: Ens-Vb-X es el mejor con un solo nodo; la fusión es un modo de alta cobertura».
- **T2 o T3 falla:** «Ens-Vb-X sigue siendo el mejor; la fusión no cubre los huecos».

**Descriptivo:**
- todas las variantes, F̄ppb, p99.9 y la detección del grupo;
- las falsas alarmas reales en el banco, que pueden pasar del nominal por PARAAD;
- en D1, todas las formas por semana y el rebote;
- en el despliegue, ΔF̄ (Fusión − X) con IC, semilla [42, 25, 3].

## Predicciones (Claude, antes de calcular nada)
Se basan en resultados ya conocidos de cada detector por separado.
1. **T1 falla por poco:** ΔF̄ en E1 entre −0.04 y −0.01, con el límite inferior del IC < −0.02. Ens-Vb-X pasa de p99 a ≈ p99.5 y PARAAD aporta poco con un solo nodo.
2. **T2 pasa:** el recall de la estación original en E2-4 (δ50) sube de ≈ 0.05 a ≥ 0.20.
3. **T3 pasa:** el recall en las semanas 5–8 del escalón de 20 ppb sube de ≈ 0.11 a ≥ 0.40.
4. **Falsas alarmas reales en el banco con p99:** la fusión da entre 1.6 y 2.2 %, frente a 1.30 % de Ens-Vb-X, porque los umbrales de PARAAD se trasladan mal.
5. **Despliegue:** la fusión queda por debajo de Ens-Vb-X en F̄ (punto < 0).
6. **Veredicto esperado:** «compromiso».

## Límites declarados
- **Supervisión distinta:** Ens-Vb-X vio ataques al entrenar y PARAAD no. Esto mide desempeño práctico, no arquitectura.
- **Resolución temporal distinta:** PARAAD decide por día completo, así que la fusión no adelanta alertas por hora con la parte de PARAAD.
- **El banco y D1 no son vírgenes:** los resultados de cada detector por separado ya se conocían.
- **El reparto del presupuesto es fijo** (la misma *q* para los dos) y no se optimiza.
