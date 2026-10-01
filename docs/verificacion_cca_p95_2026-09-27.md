# Verificación de CCA: reparación del notebook 07

Fecha: 2026-09-27. Estado: **detenido en el paso 1 por discrepancia de recall**.

## Reparación

- En la copia guardada, `atacar_serie` seguía definida en el notebook y no existía en `src/attack/blind.py`. Se trasladó al módulo y la celda quedó como un import.
- El módulo ya contenía NumPy, encode_o3, decode_o3, flip_bit, encrypt y decrypt; APPSKEY y DEVADDR están definidos allí. No se cambiaron claves, contadores ni selección de ataques.
- La primera ejecución con kernel limpio falló antes del ataque: dos celdas esperaban cinco resultados de construir_ventanas, que actualmente devuelve seis: X, y, timestamps, base, mu, sigma. Se corrigieron ambas llamadas de entrenamiento y prueba. La base se ignora explícitamente en las versiones de predicción absoluta.
- Se corrigió únicamente la impresión de la máscara para excluir seno y coseno; no se alteraron los tensores por ese cambio.
- La comparación del AST confirmó que el cuerpo de atacar_serie es idéntico al original salvo documentación. Los NaN no consumen números aleatorios, igual que antes.
- Las 115 pruebas automatizadas pasaron, incluidas 49 nuevas comprobaciones de muestreo, cifrado, signo, contadores y preservación del original.

## Corrida real y condición de parada

Se inició un kernel nuevo con el entorno .venv y se ejecutó secuencialmente desde la primera celda. La ejecución corregida alcanzó la celda 23 (índice desde cero), después de entrenar V1–V4 y completar el barrido de ventanas. Allí se detuvo por la comprobación obligatoria; **no se completó el notebook entero**, ni se ejecutaron los entrenamientos multiestación posteriores.

Se mantuvieron el procedimiento, tasa 0.05, seed 42 del ataque, ventana 24, perfil de 14 días, split cronológico 80/20 y calibración p95 sobre residuos de entrenamiento limpio. No se fijó una semilla nueva para el entrenamiento ni se buscaron semillas para obtener la referencia.

| Bit | Recall esperado (%) | Recall obtenido (%) | TP | Ataques evaluados |
|---:|---:|---:|---:|---:|
| 3 | 9.0 | 20.5 | 16 | 78 |
| 4 | 20.5 | 42.3 | 33 | 78 |
| 5 | 84.6 | 92.3 | 72 | 78 |
| 6 | 98.7 | 100.0 | 78 | 78 |
| 7 | 100.0 | 100.0 | 78 | 78 |

Umbral p95 obtenido: **16.014379501342773 ppb**. La referencia guardada en results/deteccion_lstm.csv reporta **22.6 ppb**, redondeado a un decimal. Este es el umbral del detector, no el de contingencia, que para la tarea es **155 ppb**.

La semilla del ataque no fija la inicialización, dropout ni barajado del entrenamiento. El notebook piloto no fija semillas de entrenamiento antes de V4. No se encontraron pesos .keras/.h5 guardados en los archivos examinados del repositorio. Por ello, los mismos parámetros de entrenamiento no garantizan recuperar el modelo histórico. La diferencia no puede atribuirse al traslado de la función: su lógica se conservó.

La tabla completa está en [verificacion_recall_cca_p95.csv](../results/verificacion_recall_cca_p95.csv). El CSV histórico permanece intacto. No se calcularon recalls de bits 1–2, no se generaron las figuras finales ni se modificó el notebook 08.

Para continuar hace falta recuperar el modelo histórico y su calibración, o autorización para establecer una nueva referencia reproducible y reportarla como tal. No corresponde combinar los recalls históricos de 3–7 con recalls nuevos de 1–2 de otro modelo.

## Artefactos de ejecución

Las corridas se hicieron con datos y código del repositorio, pero con directorios de salida aislados para proteger figuras y CSV existentes:

- Notebook original ejecutado hasta su fallo: /tmp/lorawan07-audit-1Ukc2o/original/07_ejecutado.ipynb
- Notebook corregido ejecutado hasta la comprobación: /tmp/lorawan07-audit-1Ukc2o/corregido/07_ejecutado.ipynb

Estas rutas son temporales; los tracebacks completos se preservan debajo en este documento.

## Traceback completo: fallo original

```text
Traceback (most recent call last):
  File "/tmp/lorawan07-audit-1Ukc2o/run_notebook.py", line 40, in <module>
    client.execute()
    ~~~~~~~~~~~~~~^^
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/jupyter_core/utils/__init__.py", line 165, in wrapped
    return loop.run_until_complete(inner)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/usr/lib/python3.14/asyncio/base_events.py", line 720, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 709, in async_execute
    await self.async_execute_cell(
        cell, index, execution_count=self.code_cells_executed + 1
    )
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 1062, in async_execute_cell
    await self._check_raise_for_error(cell, cell_index, exec_reply)
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 918, in _check_raise_for_error
    raise CellExecutionError.from_cell_and_msg(cell, exec_reply_content)
nbclient.exceptions.CellExecutionError: An error occurred while executing the following cell:
------------------
from src.detect.windows import construir_ventanas

# Split cronologico ANTES de normalizar
corte = int(len(matriz) * 0.8)
mat_tr, mat_te = matriz.iloc[:corte], matriz.iloc[corte:]

Xtr, ytr, ts_tr, mu, sigma = construir_ventanas(mat_tr, 'CCA', ventana=24)
Xte, yte, ts_te, _, _ = construir_ventanas(mat_te, 'CCA', ventana=24,
                                           mu=mu, sigma=sigma)

print(f"Entrenamiento: {Xtr.shape}   y: {ytr.shape}")
print(f"Prueba:        {Xte.shape}   y: {yte.shape}")
print(f"\nRango temporal train: {ts_tr[0]} -> {ts_tr[-1]}")
print(f"Rango temporal test:  {ts_te[0]} -> {ts_te[-1]}")
print(f"\nFraccion de datos reales en X (media de la mascara): "
      f"{Xtr[:, :, 32:].mean():.3f}")
------------------


---------------------------------------------------------------------------
ValueError                                Traceback (most recent call last)
Cell In[5], line 7
      3 # Split cronologico ANTES de normalizar
      4 corte = int(len(matriz) * 0.8)
      5 mat_tr, mat_te = matriz.iloc[:corte], matriz.iloc[corte:]
      6 
----> 7 Xtr, ytr, ts_tr, mu, sigma = construir_ventanas(mat_tr, 'CCA', ventana=24)
      8 Xte, yte, ts_te, _, _ = construir_ventanas(mat_te, 'CCA', ventana=24,
      9                                            mu=mu, sigma=sigma)
     10 

ValueError: too many values to unpack (expected 5, got 6)
```

## Traceback completo: parada de verificación

```text
Traceback (most recent call last):
  File "/tmp/lorawan07-audit-1Ukc2o/run_notebook.py", line 40, in <module>
    client.execute()
    ~~~~~~~~~~~~~~^^
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/jupyter_core/utils/__init__.py", line 165, in wrapped
    return loop.run_until_complete(inner)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/usr/lib/python3.14/asyncio/base_events.py", line 720, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 709, in async_execute
    await self.async_execute_cell(
        cell, index, execution_count=self.code_cells_executed + 1
    )
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 1062, in async_execute_cell
    await self._check_raise_for_error(cell, cell_index, exec_reply)
  File "/home/kali-lab-jelb/MaestriaPCIC/Tesis/lorawan11-rama-detection/.venv/lib/python3.14/site-packages/nbclient/client.py", line 918, in _check_raise_for_error
    raise CellExecutionError.from_cell_and_msg(cell, exec_reply_content)
nbclient.exceptions.CellExecutionError: An error occurred while executing the following cell:
------------------
from sklearn.metrics import precision_score, recall_score, fbeta_score

# Serie limpia de CCA en el periodo de prueba
cca_te = mat_te['CCA'].copy()

res_det = []
for bit in [3, 4, 5, 6, 7]:
    atacada, etiq = atacar_serie(cca_te.values, bit, tasa=0.05, seed=42)

    mat_atk = mat_te.copy()
    mat_atk['CCA'] = atacada          # solo CCA se ataca

    Xa, ya, tsa, Ba, _, _ = construir_ventanas(
        mat_atk, 'CCA', ventana=24, mu=mu4, sigma=sg4,
        perfil=perf_te, predecir_desviacion=True)

    # Alinear etiquetas con las ventanas construidas
    idx = pd.Series(etiq, index=cca_te.index).reindex(pd.to_datetime(tsa)).values

    recibido = Ba + ya
    predicho = Ba + modelo4.predict(Xa, verbose=0).flatten()
    residuo = np.abs(recibido - predicho)

    for p, u in umbrales.items():
        marcado = (residuo > u).astype(int)
        res_det.append({
            'bit': bit, 'delta_ppb': 2**bit, 'percentil': p,
            'umbral_ppb': round(u, 1),
            'recall_%': round(recall_score(idx, marcado, zero_division=0)*100, 1),
            'precision_%': round(precision_score(idx, marcado, zero_division=0)*100, 1),
            'f2_%': round(fbeta_score(idx, marcado, beta=2, zero_division=0)*100, 1),
            'fp': int(((marcado == 1) & (idx == 0)).sum()),
            'tp': int(((marcado == 1) & (idx == 1)).sum()),
            'n_atacados': int((idx == 1).sum()),
        })

det = pd.DataFrame(res_det)
# Puerta de validacion: no sobrescribir resultados historicos si no coinciden.
referencia = pd.Series({3: 9.0, 4: 20.5, 5: 84.6, 6: 98.7, 7: 100.0},
                       name='recall_esperado_pct')
validacion_recall = (det.loc[det.percentil == 95]
                    .set_index('bit')[['recall_%', 'tp', 'n_atacados']]
                    .rename(columns={'recall_%': 'recall_obtenido_pct'})
                    .join(referencia))
validacion_recall['umbral_p95_ppb'] = float(umbrales[95])
validacion_recall['coincide'] = (validacion_recall.recall_obtenido_pct
                               == validacion_recall.recall_esperado_pct)
print('Verificacion obligatoria CCA: recall p95, redondeado a un decimal')
print(validacion_recall.to_string())
validacion_recall.to_csv('../results/verificacion_recall_cca_p95.csv')
if not validacion_recall['coincide'].all():
    raise RuntimeError(
        'El recall CCA no reproduce la referencia validada. Detener: '
        'no evaluar bits 1-2 ni generar figuras finales. '
        'Consultar results/verificacion_recall_cca_p95.csv. '
        'Los resultados historicos de deteccion_lstm.csv NO se sobrescribieron.')
det.to_csv('../results/deteccion_lstm.csv', index=False)

det.pivot_table(index=['bit', 'delta_ppb'], columns='percentil',
                values='recall_%')
------------------

----- stdout -----
Verificacion obligatoria CCA: recall p95, redondeado a un decimal
     recall_obtenido_pct  tp  n_atacados  recall_esperado_pct  umbral_p95_ppb  coincide
bit                                                                                    
3                   20.5  16          78                  9.0        16.01438     False
4                   42.3  33          78                 20.5        16.01438     False
5                   92.3  72          78                 84.6        16.01438     False
6                  100.0  78          78                 98.7        16.01438     False
7                  100.0  78          78                100.0        16.01438      True
------------------

---------------------------------------------------------------------------
RuntimeError                              Traceback (most recent call last)
Cell In[19], line 52
     48 print('Verificacion obligatoria CCA: recall p95, redondeado a un decimal')
     49 print(validacion_recall.to_string())
     50 validacion_recall.to_csv('../results/verificacion_recall_cca_p95.csv')
     51 if not validacion_recall['coincide'].all():
---> 52     raise RuntimeError(
     53         'El recall CCA no reproduce la referencia validada. Detener: '
     54         'no evaluar bits 1-2 ni generar figuras finales. '
     55         'Consultar results/verificacion_recall_cca_p95.csv. '

RuntimeError: El recall CCA no reproduce la referencia validada. Detener: no evaluar bits 1-2 ni generar figuras finales. Consultar results/verificacion_recall_cca_p95.csv. Los resultados historicos de deteccion_lstm.csv NO se sobrescribieron.
```
