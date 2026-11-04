# Auditoría del uso de TINTOlib — 2026-10-30

## Dictamen

El uso inicial de la API de TINTO para ajustar PCA y generar imágenes sigue el
contrato revisado. No se encontró, en los puntos comprobados, transposición
incorrecta de la entrada, doble MinMax ni inclusión de etiquetas en píxeles.
El detector T1 evaluado usa una modificación propia de la rasterización:
TINTO-PCA + asignación única por SciPy. Su resultado frente a L0 no es una
evaluación del método TINTO original sin cambios ni de toda TINTOlib.

Se revisaron documentación, scripts de T1 y fuente del wheel publicado
TINTOlib 1.3.1, descargado sin instalar ni modificar el entorno de tesis.
La documentación latest muestra rótulos 1.3.0 y algunas páginas 0.1: las
afirmaciones sobre la ejecución histórica se contrastaron con 1.3.1.
Este es un análisis de contrato y un control sintético pequeño; no una nueva
evaluación de anomalías ni una certificación exhaustiva de la librería.

## Biblioteca y método

TINTOlib reúne métodos tabular-imagen: TINTO, IGTD, REFINED, DeepInsight,
Fotomics y otros. T1 empleó `from TINTOlib.tinto import TINTO`, con PCA.
No probó todos los métodos de la biblioteca. La CNN es un componente separado:
`TINTO.fit` ajusta la transformación, no entrena nuestro clasificador de ataques.

## Contraste con el código

| Aspecto | Contrato/fuente 1.3.1 | Uso T1 | Dictamen |
|---|---|---|---|
| Entrada | DataFrame/CSV numérico, sin NaN; en clasificación última columna=objetivo | 19 840 filas × 408 características + etiqueta ficticia final | Conforme en scripts y registros; matriz original no se repitió en esta auditoría |
| Etiqueta | `_split_features_targets` separa última columna; `_fitAlg` de TINTO obtiene coordenadas solo de X | Etiqueta ficticia 0 durante fit; etiquetas reales aparte para CNN | Conforme; cambiar etiqueta no cambia los píxeles del control |
| Escala | MinMax por defecto; transformer=None desactiva escalado interno | MinMax externo por columna y luego transformer=None | Sin doble escalado; equivalencia comprobada en control |
| PCA | La librería transpone X internamente, aplica PCA de 2 componentes a las características | Se entrega tabla filas=ventanas, columnas=características, sin transponer antes | Conforme; las2 coordenadas colocan características, no sustituyen todos los valores por 2 entradas |
| Ajuste/transformación | fit prepara mapa/escala; transform los reutiliza | Mapa y escala de muestra 2020–2021 congelados en validación | Conforme para estos componentes |
| Sin difuminado | blur=False es opción válida y predeterminada | blur=False | Conforme; no es obligatorio usar blur |
| Resolución | pixels cambia discretización; zoom repite píxeles al guardar | pixels 32/64/128/256; zoom1 | Se probó resolución real; aumentar zoom no evitaría colisiones |
| Formato | NPY guarda matriz float64; cmap interviene en PNG, no NPY | Diagnóstico NPY; CNN matrices float32 de un canal | Formato válido; conversión float32 es decisión propia y documentada |
| Colisiones sin blur | Escritura secuencial, última característica reemplaza valores anteriores | Diagnóstico cotejado con transform real | Hallazgo confirmado en fuente y nuevo control |
| Asignación única | TINTO.__init__ no tiene relocate/assignment_method | linear_sum_assignment en prototipos_sin_colisiones.py | Modificación propia; no parámetro de TINTO original |
| Inferencia final | API nativa transform genera imágenes según su rasterización | Entrenamiento/evaluación escriben directamente valores en mapa único guardado | Implementación propia del codificador, no ejecución de transform nativo por cada imagen |

Fuentes locales clave:

- `experiments/exploracion_tinto/experimento_hora_compacta.py`: MinMax externo,
  tabla con etiqueta final, constructor TINTO, fit, transform y pruebas de pérdida.
- `experiments/exploracion_tinto/prototipos_sin_colisiones.py`: reasignación de
  coordenadas a píxeles únicos minimizando suma de distancias cuadradas.
- `experiments/exploracion_tinto/entrenar_tinto_l0.py`, alrededor de líneas 144–153:
  escala y escritura propia en tensores 32×32×1.
- `experiments/exploracion_tinto/evaluar_2022.py`, alrededor de líneas 76–78:
  mismo codificador durante inferencia.

## Colisiones y opciones de otros métodos

Resultados históricos originales de 408 características: 23 posiciones en 32×32;
40 en 64×64;81 en 128×128;151 en 256×256. Estos conteos no afirman que todas las
columnas coincidentes aporten información independiente: sí prueban que no hay
correspondencia uno a uno y que algunas perturbaciones quedan ocultas.

La opción `option='mean'/'maximum'` de TINTO interviene en las ramas de
difuminado; no corrige la escritura simple con blur=False. No se puede asumir
que activar option='mean' resuelva esas colisiones sin cambiar el proceso.

DeepInsight y Fotomics pertenecen a la misma biblioteca y documentan
`relocate=True` y `algorithm_opt='linear_sum'`. DeepInsight con PCA también
usa relevancia de características al reubicar. Son alternativas nativas de
otros métodos; no equivalen automáticamente a nuestra asignación ni son
opciones admitidas por el constructor TINTO. Revisarlas no autoriza un nuevo
barrido ni permite renombrar retrospectivamente T1 como DeepInsight.

## Control técnico ejecutado

64 filas inventadas ×8 características, lado 2 para forzar colisiones. No se
usaron matrices RAMA, modelos ni entrenamiento. Fuente: wheel 1.3.1, SHA256
`fa390d87c07b7665000039204e61a820d070a5323d96c62af12074806b82894b`.

Control de referencia:
`results/exploracion_tinto_2022/auditoria_api_20261030/entorno_compatible_final/verificacion.json`.
NumPy 2.4.6, pandas 2.3.3 y scikit-learn 1.9.1. Se comprobó:

- MinMax externo + transformer=None da el mismo mapa y la imagen base del
  control que el preprocesamiento interno.
- Cambiar etiquetas mantiene exactamente el mapa discreto y las imágenes;
  las coordenadas continuas difieren hasta 2.66e−15, dentro de tolerancia
  técnica prefijada en el control final 1e−12. La fuente confirma que y no
  interviene en PCA. Esto no es igualdad binaria universal entre ejecuciones.
- Una perturbación de una característica sobrescrita no altera la imagen.
- La matriz nativa coincide con la reconstrucción de última escritura.
- NPY del control tiene forma 2×2, dtype float64 y conserva intensidad 0.25.

Se preservan intentos: el primero usó pandas 3.0.6, fuera del requisito declarado
pandas<3 de TINTOlib 1.3.1, y no se adopta como control de entorno compatible.
El primer intento compatible exigía igualdad bit a bit de coordenadas PCA y
falló por 2.66e−15; se conservó su carpeta y se ejecutó otro control, separando
equivalencia numérica de coordenadas y exactitud del mapa discreto. No se
alteró ningún criterio ni resultado del experimento científico T1.

## Límites metodológicos y siguiente decisión

La normalización sigma heredada de L0 usa 2020–2022 limpio. Aunque mapa/MinMax
TINTO usan 2020–2021, no se presenta todo el preprocesamiento como ajustado
solo con entrenamiento. La reutilización de 2022, la parada manual y la ausencia
de CNN temporal de control siguen limitando atribución y generalización.

La comprobación responde que la API se utilizó de forma coherente en lo
revisado, pero no reemplaza un brazo de detección con `TINTO.fit/transform`
sin reasignación propia. Si el objetivo es medir TINTO original, esa sería una
comparación nueva que debe registrarse antes de entrenar y conservar T1 como
variante modificada. No se inicia entrenamiento ni se cambian resultados aquí.

## Documentación oficial consultada

- [Introducción y formatos](https://tintolib.readthedocs.io/en/latest/installation.html).
- [Método TINTO](https://tintolib.readthedocs.io/en/latest/tinto.html).
- [Clases base](https://tintolib.readthedocs.io/en/latest/baseclasses.html).
- [DeepInsight](https://tintolib.readthedocs.io/en/latest/deepInsight.html).
- [Fotomics](https://tintolib.readthedocs.io/en/latest/fotomics.html).
- [Repositorio oficial](https://github.com/oeg-upm/TINTOlib).
