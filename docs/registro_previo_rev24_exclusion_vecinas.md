# Registro previo de la revisión 24: excluir vecinas sospechosas (Ens-Vb-X)

Fecha: 2026-11-07. **Estado: aprobado por el tesista el 2026-11-07, con las pruebas completas.** Se corre **antes** que la revisión 23b (D1), para que D1 evalúe también a Ens-Vb-X. Las precisiones del final se fijaron antes de generar planes o puntajes.

## Motivo
En la revisión 23, el recall de Ens-Vb-R (p99, δ = 50 %) cae según cuántas de las 4 vecinas de la estación están alteradas a la vez (análisis exploratorio, no registrado):

| Vecinas alteradas | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Recall | 0.82 | 0.47 | 0.24 | 0.06 | 0.04 |

Idea del tesista: si las vecinas coinciden entre sí salvo una que se desvía **igual que la estación evaluada**, sacar esa vecina del promedio. El objetivo no es ganar recall, sino **no perderlo** cuando 1 o 2 vecinas están comprometidas.

## La regla (Ens-Vb-X)
Se aplica sobre los modelos congelados de Ens-Vb-R: los mismos pesos, sin reentrenar. Es una capa de saneamiento de entradas.

1. **Señal de cada estación *i*:** z_i(t) = media de las últimas 24 h (t − 23 … t, con ≥ 12 h con dato) de la desviación V0, (x_i − perfil propio de 14 días) / σ_i. No depende de las vecinas, así que no es circular.
2. **Para la estación evaluada *s* y cada vecina *n*,** se toma m_n = mediana de z de las **otras** vecinas de *s* (hacen falta ≥ 2 con dato). La vecina *n* se declara **sospechosa** en la hora *t* si se cumplen las tres:
   - |z_n − m_n| > τ: *n* se aparta de las demás vecinas;
   - |z_s − m_n| > τ: *s* también se aparta;
   - signo(z_n − m_n) = signo(z_s − m_n): en la misma dirección.

   Se excluyen como máximo 2 vecinas. Si salen más de 2, no se excluye ninguna.
3. **Efecto:** para los cálculos de *s*, la vecina sospechosa se trata **como dato faltante** en esas horas.
   - En la base Vb de *s* se quita del promedio de perfiles y de x_vecinas (y, por tanto, de la mediana de 60 días).
   - En la columna a14 de *s*.
   - En la ventana de 24 h de *s*, su desviación, su máscara y su a14 pasan a 0, que es justo como el modelo ya ve una vecina sin dato.
4. **Lo que se espera por construcción:**
   - Con 1–2 vecinas comprometidas, la mediana de las otras sigue limpia y la regla actúa.
   - Con ≥ 3 no puede actuar.
   - Si *s* está limpia no actúa (falla la segunda condición), así que un ataque a una vecina no contamina el puntaje de *s*.

## Diseño y elección de τ (sólo 2022)
- **Datos:** los 10 calendarios `entrenamiento_01…10` en 2022, con los **modelos de selección** de Vb-R de la revisión 22 (entrenados con 2020–2021), igual que en la elección de la revisión 22. Los definitivos vieron 2022.
- **Escenarios en 2022:** E1 (tal cual), E2-1 (*s* y 1 vecina alterable al azar) y E2-2 (*s* y 2), con δ = 50 % y +20 ppb. Semilla [42, 24, k, episodio]; los choques se resuelven como en la revisión 23.
- **Candidatos:** τ ∈ {1.0, 1.5, 2.0}, comparados con Ens-Vb-R sin regla. Los umbrales p99 salen de 2022 limpio para cada variante, como en la elección de la revisión 22.
- **Criterio, fijado de antemano:** se elige el τ con mayor recall medio de *s* en E2-1 y E2-2, entre los que cumplan que el F̄ de E1 (δ 100/50/20) no baje más de 0.01 frente a Ens-Vb-R.
  - Si ninguno cumple, **la regla no avanza** y se reporta así.

## Calibración y prueba
- **Calibración:** umbrales p99 y p99.9 de Ens-Vb-X con 2023 limpio y los definitivos, como en la revisión 22.
- **Prueba en el banco 2024–jul 2026 (30 calendarios):**
  - Escenarios: E1, E2-1, E2-2 y E2-4 (= E2 de la revisión 23). Tamaños: δ 100/50/20 y 10/20/40 ppb.
  - Ens-Vb-R se reutiliza de la revisión 23 donde ya existe, y se puntúa en E2-1 y E2-2. PARAAD entra como referencia.
  - Dos corridas que deben salir idénticas.
- **Declaración:** el banco es donde se descubrió la debilidad, pero τ no se ajusta en él.
- **Comprobación descriptiva en la ventana de despliegue ago–sep 2026,** con sus 10 calendarios: que Ens-Vb-X no pierda la ventaja de Ens-Vb-R ahí.

## Pruebas registradas (p99; IC del 95 %, bootstrap pareado estación × mes, semilla [42, 24, 1])
- **T1, no daña:** en E1, ΔF̄ (Ens-Vb-X − Ens-Vb-R) con el límite inferior del IC > −0.02 (margen de no inferioridad).
- **T2, evita perder:** en E2-1 con δ = 50 %, Δrecall de la estación original *s* (X − R) con IC > 0.
- **Regla de adopción:**
  - si T1 y T2 pasan, Ens-Vb-X sustituye a Ens-Vb-R como detector principal;
  - si sólo pasa T1, queda como variante descriptiva;
  - si T1 falla, no se adopta.
- **Descriptivo:** E2-2, E2-4, el error fijo, las falsas alarmas en limpio, la detección del grupo y p99.9.

## Predicciones (Claude, antes de generar nada)
1. T1 pasa: con vecinas limpias la regla casi nunca se activa.
2. T2 pasa: el recall de *s* en E2-1 (δ50) sube de ≈ 0.47 a ≥ 0.65.
3. En E2-2 (δ50) sube de ≈ 0.24 a ≥ 0.45.
4. En E2-4 no cambia (≈ 0.04): no hay mayoría limpia.
5. Con el umbral recalibrado, las falsas alarmas en limpio quedan cerca del nominal, pero la precisión en E1 baja un poco (≤ 0.02). La regla vuelve más sensible a *s* cuando una vecina comparte un evento local real.
6. Con el error fijo, la ganancia en E2-1 es parecida a la proporcional.

## Límites que se declaran desde ya
- **Un atacante que conozca la regla** comprometería ≥ 3 vecinas. La regla sube el costo del ataque de 1 a 3 nodos comprometidos además de *s*; no lo elimina.
- **Las vecinas se eligen con datos públicos de RAMA:** un atacante informado puede reconstruirlas.

## Cómputo estimado
- Diseño en 2022: unas 240 puntuaciones con 5 modelos, ≈ 15 min.
- Calibración: ≈ 2 min.
- Banco: unas 1 080 matrices con 5 modelos, ≈ 70 min por corrida y ≈ 2.3 h con las dos.
- Total ≈ 3 h, en segundo plano, con la misma inferencia idéntica bit a bit de la revisión 23.

## Precisiones (2026-11-07, antes de generar planes o puntajes)
1. **Vecinas añadidas en E2-1 y E2-2 (anidadas y pareadas).** Para cada episodio original se baraja la lista de vecinas alterables de *s* con la semilla [42, 24, k, episodio]. E2-1 toma la primera y E2-2 las dos primeras.
   - k = 1…10 en 2022 (`entrenamiento_01…10`) y k = 1…30 en el banco (el orden de la revisión 23).
   - Si *s* tiene menos vecinas alterables que las pedidas, entran todas las que tiene.
   - Los choques se resuelven como en la revisión 23.
2. **Diseño en 2022.**
   - Se alteran sólo los episodios de los planes `entrenamiento_01…10` que empiezan en 2022. Antes de 2022 la historia es limpia, desde 2020.
   - Escenarios: E1 con δ 100/50/20, y E2-1 y E2-2 con δ 50 y +20 ppb.
   - **Modelos:** los 5 de selección Vb-R de la revisión 22 (`modelos_seleccion`), con su escala de selección. Sus SHA-256 se registran antes de usarlos.
   - **Umbral p99:** de 2022 limpio, en las estación-días válidas para todas las variantes, uno por variante.
   - **Criterio:** el recall medio de *s* sobre {E2-1, E2-2} × {δ50, 20 ppb}.
   - **Restricción:** el F̄ de E1 (δ 100/50/20) no baja más de 0.01. Si dos τ empatan, se elige el mayor, que es más conservador.
3. **Detalles de la regla.**
   - z usa ≥ 12 horas con dato de las últimas 24. m_n necesita ≥ 2 de las otras vecinas con z.
   - La exclusión vale para la base y las entradas de **todas** las estaciones (también HGM puede ser excluida como vecina), pero sólo se puntúan las 31 objetivo.
   - **Comprobación:** con τ = ∞, Ens-Vb-X debe dar exactamente Ens-Vb-R.
4. **Banco.**
   - Escenarios E1, E2-1, E2-2 y E2-4 (= E2 de la revisión 23, con los mismos planes) × δ 100/50/20 y 10/20/40 ppb: 720 matrices por corrida.
   - En cada matriz se puntúan Ens-Vb-R, Ens-Vb-X y PARAAD. En E1 y E2-4, Ens-Vb-R y PARAAD deben coincidir bit a bit con la revisión 23 (comprobación de reproducibilidad).
   - V0, L0 y R3 no se vuelven a puntuar. Sus valores de referencia en E1 y E2-4 están en la revisión 23.
5. **T2** usa el recall de la estación original (papel = original). Bootstrap pareado estación × mes, semilla [42, 24, 1].
6. **Ventana de despliegue** (descriptivo): la misma tubería de la revisión 22, con historia de enero–julio de 2026, datos de SINAICA y los 10 calendarios con δ 100/50/20/10/5. Se reporta ΔF̄ (X − R) con IC, semilla [42, 24, 2].

## Enmienda 1 (2026-11-07, antes de puntuar ataques): escala de τ
- **Error de diseño (de Claude):** τ ∈ {1.0, 1.5, 2.0} estaba en unidades de σ, la desviación estándar **global** de cada estación (≈ 21–28 ppb). La media de 24 h de la desviación V0 casi nunca pasa de 0.9 σ, así que la regla nunca se habría activado.
  - Se detectó en la validación: 0 exclusiones con τ = 1.5 en 2025 limpio y en una matriz E2-1. De esa matriz sólo se miró el conteo de exclusiones, no puntajes ni alarmas.
- **Corrección:** τ son los cuantiles 95, 99 y 99.9 de |z_n − m_n| en **2020–2021 limpio** (1 659 943 valores), sin ataques, sin 2022 y sin el banco: τ = 0.2596, 0.4160 y 0.6857 σ (≈ 6.5, 10 y 17 ppb).
- **Fracción de estación-horas de 2020–2021 limpio con alguna vecina excluida:** 1.40 %, 0.12 % y 0.005 %.
- Todo lo demás (criterio de elección en 2022, pruebas, predicciones) sigue igual. La regla de desempate conserva el sentido: se prefiere el τ mayor, el más conservador.
- Los valores exactos se guardan en `results/linea_base/rev24/grilla_tau.json`.
