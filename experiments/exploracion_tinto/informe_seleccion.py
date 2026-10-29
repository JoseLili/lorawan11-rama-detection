"""Informe descriptivo de selección completa, solo cuando ambas corridas terminan."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from resumir_seleccion import resumen

ROOT=Path(__file__).resolve().parents[2]


def generar(root):
    r=resumen(root)
    assert r['terminadas']==2,'Faltan corridas completas'
    (root/'reproducibilidad_final.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    cache=json.loads((ROOT/'results/exploracion_tinto_2022/preparacion_20261029/cache_completa/LISTO.json').read_text())
    p=cache['positivas']['tr']/cache['conteos']['tr']
    q=cache['positivas']['va']/cache['conteos']['va']
    constant_loss=-q*np.log(p)-(1-q)*np.log1p(-p)
    h=pd.read_csv(root/'corrida_cpu1/historia.csv')
    e=r['verificacion_final']['E'];best=h[h.epoca==e].iloc[0]
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    ax.plot(h.epoca,h.loss,'o-',label='Ajuste 2020–2021 (con dropout)')
    ax.plot(h.epoca,h.val_loss,'o-',label='Validación 2022 (sin dropout)')
    ax.axhline(constant_loss,color='gray',linestyle=':',label='Referencia: probabilidad constante aprendida de la frecuencia de ajuste')
    ax.axvline(e,color='black',linestyle='--',label=f'Época seleccionada E={e}')
    ax.set(xlabel='Época',ylabel='Pérdida binaria promedio (adimensional)',title='TINTO-PCA + asignación única 32 × 32 · selección\nDos entrenamientos con resultados numéricos idénticos')
    ax.legend(fontsize=8)
    fig.savefig(root/'curva_seleccion.png',dpi=160);plt.close(fig)
    report={'E':e,'epocas_ejecutadas':r['verificacion_final']['epocas_ejecutadas'],
        'perdida_ajuste_en_E':float(best.loss),'perdida_validacion_en_E':float(best.val_loss),
        'frecuencia_positivas_ajuste':p,'frecuencia_positivas_validacion':q,
        'perdida_validacion_probabilidad_constante_p_ajuste':float(constant_loss),
        'referencia_constante_no_es_L0':True,'modelo':'CNN recién entrenada, selección; pesos de E restaurados',
        'reproducibilidad':r['verificacion_final'],
        'limite':'No precisión/recall/F1, no calibración p99/p99.9, no comparación aún con L0.'}
    (root/'resumen_seleccion.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    text=f'''# Selección TINTO-PCA con asignación única — 2026-10-29

Dos entrenamientos completos finalizaron con pesos, historia y probabilidades
idénticos. CNN de 34 081 parámetros, mapa/escalador previamente ajustados sobre
entrenamiento y congelados; 408 entradas, asignación única 32 × 32.

- Ajuste: 1 357 800 ventanas de 2020–2021, veinte calendarios d50, muestra L0 exacta.
- Validación: 339 450 ventanas de 2022, calendarios 01–10.
- Época seleccionada E: **{e}**; épocas ejecutadas: **{report['epocas_ejecutadas']}**.
- Pérdida de ajuste en E: {best.loss:.8f}; pérdida de validación en E: {best.val_loss:.8f}.
- Pesos de E restaurados, modelo guardado y recarga verificada.

La pérdida no es porcentaje de aciertos ni precisión de anomalías. La frecuencia
positiva es solo {100*p:.4f} % en ajuste. Como contexto, una probabilidad
constante igual a esa frecuencia tendría pérdida de validación ~{constant_loss:.6f}
sin distinguir un caso de otro. Esta referencia NO es el L0 y no se presenta
como un detector competidor entrenado ni como prueba de superioridad.

No comparar el criterio sintético de pérdida <0.1, definido sobre clases
balanceadas, con estas pérdidas de clases muy desbalanceadas. El piloto conserva
su incumplimiento registrado. La selección completa usa la regla val_loss ya fijada.

## Reproducibilidad

SHA-256 de los pesos finales: `{r['verificacion_final']['sha256_pesos']}`.
Dos corridas válidas: `corrida_cpu1/` y `corrida_cpu2/`. Los primeros intentos
`corrida1/2` se interrumpieron antes de completar una época para habilitar la
optimización CPU, con cambio registrado antes de validación completa.
Los contenedores Keras pueden tener metadatos distintos; la igualdad se refiere
a pesos, historias y probabilidades de control, no tiempos ni metadatos de archivo.

## Ficha de la figura

`curva_seleccion.png`: X = época; Y = pérdida binaria promedio adimensional.
Líneas ajuste/validación de `corrida_cpu1/historia.csv` (la segunda es idéntica).
Vertical = E por mínimo val_loss; horizontal = referencia constante descrita.
Ajuste incluye dropout y validación no, por lo que sus pérdidas no se comparan
como si ambos cálculos fueran idénticos. No son tasas de falsas alarmas ni F1.

## Alcance y siguiente etapa

Se terminó la selección y quedó un modelo candidato reproducible. No se calculó
la comparación de detección con L0 ni se evaluaron 2023–2026. La siguiente etapa
será inferencia completa en 2022 limpio y calendarios alterados, puntuación por
estación-día, calibración exploratoria p99/p99.9 y comparación pareada con el L0
de selección cargado. Las métricas de esa etapa, no la pérdida sola, dirán qué
tan útil es el candidato. El mapa sigue siendo una variante explícita de TINTO.
'''
    (root/'informe_seleccion.md').write_text(text)
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raiz',type=Path,required=True)
    a=p.parse_args();generar(a.raiz)
