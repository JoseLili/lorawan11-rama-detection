"""Verificación independiente de conteos y reporte del piloto terminado."""
import json,hashlib,argparse
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(r):
    hashes=json.loads((r/'checksums.json').read_text())
    for k,v in hashes.items():assert sha(r/k)==v,k
    z=np.load(r/'original_2025.npz');mask=z['comun'];dates=pd.DatetimeIndex(z['dias']);stations=z['estaciones'].tolist();plan=pd.read_csv(r/'plan_base.csv',parse_dates=['inicio','fin'])
    label=pd.DataFrame(False,index=dates,columns=stations)
    for ep in plan.itertuples():label.loc[ep.inicio.normalize():ep.fin.normalize(),ep.estacion]=True
    y=label.to_numpy()[mask];t=pd.read_csv(r/'metricas.csv');u=json.loads((r/'umbrales_comunes.json').read_text())
    assert len(t)==96
    for s in t.escenario.unique():
        archive=np.load(r/f'{s}.npz')
        for name in ['TINTO','Ens-Vb-X']:
            score=archive[name][mask];assert np.isfinite(score).all()
            for p in [95,98,99,99.9]:
                key=str(p);threshold=u[name][key];pred=score>threshold
                row=t[(t.modelo==name)&(t.escenario==s)&(t.percentil==p)].iloc[0]
                assert (int((pred&y).sum()),int((pred&~y).sum()),int((~pred&y).sum()),int((~pred&~y).sum()))==tuple(int(row[k]) for k in ['tp','fp','fn','tn'])
    reg=json.loads((r/'regresion_calibracion.json').read_text());assert all(abs(v-reg['referencia']['umbrales'][k])<1e-5 for k,v in reg['umbrales_obtenidos'].items())
    frozen=ROOT/'results/tinto_congelado_20261111'
    for k,v in json.loads((frozen/'checksums.json').read_text()).items():assert sha(frozen/k)==v
    ref=ROOT/'results/linea_base/rev22';defs=json.loads((ref/'modelos_definitivos_sha256.json').read_text())
    for seed in [42,1,2,3,4]:
        key=f'Vb_R_s{seed}';assert sha(ref/f'modelos_definitivos/{key}.keras')==defs[key]
    fa=pd.read_csv(r/'falsas_alarmas_originales.csv');coverage=pd.read_csv(r/'cobertura.csv');cost=pd.read_csv(r/'costos.csv')
    lines=['# Piloto pareado congelado: TINTO-CNN-GRU-D2 y Ens-Vb-X','',
    'No se entrenó ni ajustó ningún modelo. Calibración2023; evaluación2025 con historia2020–2024. Primer calendario histórico final_2025_01; doce variantes de signo/intensidad fijadas antes de resultados. Ataques sostenidos entran en la historia de ambos modelos.','',
    f'Soporte común2025: {len(y)} estación-días, {int(y.sum())} alteradas y {int((~y).sum())} normales por escenario. El calendario tiene {len(plan)} episodios antes de filtrar elegibilidad. No se equilibran clases.','',
    '## Recall y precisión con p99 (%)','', '| Escenario | Recall TINTO | Recall Ens-Vb-X | Precisión TINTO | Precisión Ens-Vb-X |','|---|---:|---:|---:|---:|']
    for s in t.escenario.unique():
        a=t[(t.escenario==s)&(t.percentil==99)].set_index('modelo')
        vals=[a.loc[m,c]*100 for c in ['recall','precision'] for m in ['TINTO','Ens-Vb-X']]
        lines.append('| '+s+' | '+' | '.join(f'{v:.2f}' for v in vals)+' |')
    lines+=['','## Falsas alarmas en originales2025','', '| Percentil | N | Nominal teórico | TINTO observado | Ens-Vb-X observado |','|---|---:|---:|---:|---:|']
    for p in [95,98,99,99.9]:
        a=fa[fa.percentil==p].set_index('modelo');row=a.loc['TINTO']
        lines.append(f'| {p} | {int(row.n_eval)} | {row.fa_eval_teoricas:.3f} | {int(row.fa_eval)} | {int(a.loc["Ens-Vb-X","fa_eval"])} |')
    lines+=['','La tabla anterior usa originales sin inyección. Los FP de metricas.csv cuentan días normales dentro de cada calendario alterado: incluyen posibles efectos posteriores al episodio y en otras estaciones. No intercambiar esos conteos para calcular precisión. Los percentiles son nominales de2023: la tasa efectiva de2025 puede diferir.','',
    '## Cobertura y complejidad','', '| Año | Detector | Días elegibles propios | Comunes |','|---|---|---:|---:|']
    for row in coverage.itertuples():lines.append(f'| {row.anio} | {row.modelo} | {row.elegibles} | {row.comunes} |')
    lines+=['','TINTO:11104 parámetros, un modelo. Ens-Vb-X:115525 parámetros en cinco modelos de23105, además del cálculo de referencias vecinales y exclusión. No equivale a una razón de memoria/latencia. Bytes.keras y hashes en el paquete congelado.',
    'Costos medidos en costos.csv incluyen preparación y puntuación en CPU. Ens-Vb-X puntúa más casos por su elegibilidad; en ataques usa caché incremental. TINTO puntúa sus casos elegibles completos. Estos tiempos no son un benchmark de latencia por entrada equivalente.','',
    '## Verificación y límites','',
    'ZIP/XLS contrastados con hashes del repositorio; matriz2020–2022 idéntica al hash histórico; calibración completa Ens-Vb-X reproduce los umbrales guardados dentro de1e-5; conteos de96 filas recalculados desde puntajes; pesos congelados intactos.',
    'Un solo calendario, muestra positiva pequeña y ventanas dependientes. Año ya utilizado por el proyecto, no examen virgen. No declarar superioridad general ni elegir modificaciones con este piloto como prueba final. No cambiar umbrales para igualar retrospectivamente falsas alarmas2025.',
    'La calibración se restringió al soporte común y por eso sus umbrales difieren de los históricos calculados sobre9097 casos. Las inyecciones nuevas no redondean ni mezclan signos, a diferencia del banco histórico. No comparar directamente con sus tablas agregadas.',
    'El modelo TINTO recibió menos años y ejemplos de entrenamiento; no se reentrenó para igualarlos, por instrucción de congelamiento. La comparación evalúa los dos artefactos existentes, no una ablación de arquitectura.',
    '', '## Reproducción','', 'Protocolo: experiments/tinto_raw/protocolo_pareado_final.md. Ejecutar comparar_final.py con python -X utf8, --raw carpeta_ZIP y --salida carpeta_nueva. Los modelos fuente deben coincidir con hashes. No requiere entrenamiento.']
    (r/'informe.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (r/'verificacion_independiente.json').write_text(json.dumps(dict(conteos_96_filas_recalculados=True,pesos_ambos_detectores_intactos=True,regresion_calibracion=True),indent=2))
    hashes.update({p.name:sha(p) for p in r.iterdir() if p.is_file() and p.name!='checksums.json'})
    (r/'checksums.json').write_text(json.dumps(hashes,indent=2));print('\n'.join(lines))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('carpeta',type=Path);main(p.parse_args().carpeta)
