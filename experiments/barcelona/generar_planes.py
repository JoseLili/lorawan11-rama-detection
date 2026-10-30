"""Planes positivos de sesgo diario; no altera las series ni entrena modelos."""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import truncnorm

ROOT = Path(__file__).resolve().parents[2]


def rng(uso, *claves):
    return np.random.default_rng([42, 230, int(uso), *map(int, claves)])


def half_up(n):
    return int(np.floor(n + .5))


def generar(dias, escala, codigos, uso, factorial):
    eleg = dias[dias.comun].sort_values(['dia_utc', 'estacion']).copy()
    fechas = pd.DatetimeIndex(sorted(eleg.dia_utc.unique()))
    bloques = {s: pd.DatetimeIndex(eleg[eleg.estacion == s].dia_utc) for s in codigos}
    n = 5 if factorial else (10 if uso == 1 else 20)
    sensores = {a: sorted(rng(uso, 0, a).choice(codigos, half_up(.3 * len(codigos)), replace=False)) for a in range(n)}
    # Campos de magnitud independientes de qué sensores/días se seleccionen.
    ruido = {c: truncnorm.rvs(.2, 2, loc=0, scale=2, size=(len(fechas), len(codigos)),
                             random_state=rng(uso, 2, c)) for c in range(n)}
    configs = itertools.product(range(5), repeat=3) if factorial else ((i, i, i) for i in range(n))
    filas, resumen = [], []
    for numero, (a, b, c) in enumerate(configs, 1):
        total = 0
        for s in sensores[a]:
            j = codigos.index(s)
            disponibles = bloques[s]
            k = half_up(.3 * len(disponibles))
            if k == 0:
                raise ValueError('Estación sin suficientes días de inyección')
            idx = np.sort(rng(uso, 1, b, j).choice(len(disponibles), k, replace=False))
            seleccion = disponibles[idx]
            for dia in seleccion:
                beta = float(ruido[c][fechas.get_loc(dia), j])
                sigma = float(escala.loc[s, 'desv'])
                filas.append(dict(plan=numero, factor_sensores=a, factor_dias=b, factor_ruido=c,
                                  estacion=s, dia_utc=dia, beta=beta, sigma_ajuste=sigma,
                                  desplazamiento_ug_m3=beta * sigma, etiqueta=1))
            total += k
        resumen.append(dict(plan=numero, factor_sensores=a, factor_dias=b, factor_ruido=c,
                            sensores=';'.join(sensores[a]), positivos=total, universo=len(eleg),
                            prevalencia=total / len(eleg)))
    planes, manifest = pd.DataFrame(filas), pd.DataFrame(resumen)
    if planes.duplicated(['plan', 'estacion', 'dia_utc']).any():
        raise ValueError('Caso duplicado en un plan')
    assert planes.beta.between(.4, 4).all()
    assert (planes.desplazamiento_ug_m3 > 0).all()
    assert set(zip(planes.estacion, planes.dia_utc)) <= set(zip(eleg.estacion, eleg.dia_utc))
    return planes, manifest


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'results/barcelona_paraad'
    fuentes = base / 'ventanas_v1'
    reg = json.loads((fuentes / 'registro.json').read_text())
    for nombre, esperado in reg['sha256_salidas'].items():
        assert sha(fuentes / nombre) == esperado, nombre
    dias = pd.read_parquet(fuentes / 'estacion_dias.parquet')
    codigos = reg['orden_estaciones']
    escalas = {fase: pd.read_csv(fuentes / f'escalas_{fase}.csv', index_col=0,
                               dtype={0: str}) for fase in ['seleccion', 'definitivo']}
    for escala in escalas.values():
        escala.index = escala.index.astype(str).str.zfill(8)
    definiciones = [
        ('ajuste_inicial', ['ajuste_inicial'], 0, 'seleccion', False),
        ('validacion', ['validacion'], 1, 'seleccion', False),
        ('ajuste_definitivo', ['ajuste_inicial', 'validacion'], 2, 'definitivo', False),
        ('prueba_2018', ['prueba'], 3, 'definitivo', True),
        ('complementaria_2019', ['complementaria'], 4, 'definitivo', True)]
    preparados = []
    for nombre, etapas, uso, fase, factorial in definiciones:
        sub = dias[dias.etapa.isin(etapas)]
        p, m = generar(sub, escalas[fase], codigos, uso, factorial)
        p2, m2 = generar(sub, escalas[fase], codigos, uso, factorial)
        pd.testing.assert_frame_equal(p, p2, check_exact=True)
        pd.testing.assert_frame_equal(m, m2, check_exact=True)
        preparados.append((nombre, fase, uso, p, m))
    out = base / 'planes_sesgo_v1'
    out.mkdir(parents=True, exist_ok=False)
    resumenes = []
    for nombre, fase, uso, p, m in preparados:
        p.to_csv(out / f'{nombre}_positivos.csv', index=False, float_format='%.17g')
        m.to_csv(out / f'{nombre}_manifiesto.csv', index=False, float_format='%.17g')
        resumenes.append(dict(etapa=nombre, escala=fase, uso_semilla=uso, planes=len(m),
                              positivos_total=len(p), universo_por_plan=int(m.universo.iloc[0]),
                              prevalencia_min=float(m.prevalencia.min()), prevalencia_max=float(m.prevalencia.max()),
                              selecciones_sensores_distintas=int(m.sensores.nunique())))
    pd.DataFrame(resumenes).to_csv(out / 'resumen.csv', index=False)
    entradas = [fuentes / 'registro.json', fuentes / 'estacion_dias.parquet', fuentes / 'mascara_comun.csv',
                fuentes / 'escalas_seleccion.csv', fuentes / 'escalas_definitivo.csv', Path(__file__)]
    archivos = sorted(out.iterdir())
    registro = dict(estado='Planes generados; NO aplicados a series; sin entrenamiento ni evaluación',
                    semilla='[42,230,uso,0/1/2,factor,...]; 0 sensores, 1 días (+índice estación), 2 magnitudes',
                    distribucion='scipy.stats.truncnorm(.2,2,loc=0,scale=2); beta en [.4,4]',
                    frecuencia='4 de 13 sensores; 30% de días comunes propios, half-up sin reemplazo',
                    etiqueta='1 si figura en positivos; 0 sólo para los demás casos comunes del mismo periodo',
                    calibracion='2017 limpio: sin planes',
                    aplicacion='Sumar desplazamiento sólo en horas observadas del día UTC; conservar máscaras, recalcular contexto causal',
                    reproducibilidad_exacta=True, resumen=resumenes,
                    versiones=dict(numpy=np.__version__, pandas=pd.__version__),
                    sha256_entradas={str(p.relative_to(ROOT)): sha(p) for p in entradas},
                    sha256_salidas={p.name: sha(p) for p in archivos})
    (out / 'registro.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
    print(pd.DataFrame(resumenes).to_string(index=False))


if __name__ == '__main__':
    main()
