"""Calendarios RAMA adaptados a Barcelona; sin aplicar ataques ni entrenar."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DELTAS = (1., .5, .2, .1, .05)


def rng(uso, numero, canal, estacion=0):
    return np.random.default_rng([42, 231, uso, numero, canal, int(estacion)])


def generar(inicio, fin, codigos, uso, numero, p=None):
    p = float(rng(uso, numero, 0).uniform(.001, .003)) if p is None else p
    if not 0 < p < 1:
        raise ValueError('Probabilidad inválida')
    dias = pd.date_range(inicio, fin, freq='D', tz='UTC')
    filas = []
    for s in codigos:
        g = rng(uso, numero, 1, s)
        u = g.random(len(dias))
        duracion = g.integers(1, 8, len(dias))
        positivo = g.random(len(dias)) < .5
        libre = 0
        for j in np.flatnonzero(u < p):
            if j < libre:
                continue
            efectivos = min(int(duracion[j]), len(dias) - j)
            filas.append(dict(estacion=s, inicio=dias[j],
                              fin=dias[j] + pd.Timedelta(days=efectivos) - pd.Timedelta(hours=1),
                              dias_sorteados=int(duracion[j]), dias=efectivos,
                              signo=1 if positivo[j] else -1, p=p))
            libre = j + int(duracion[j])
    plan = pd.DataFrame(filas, columns=['estacion', 'inicio', 'fin', 'dias_sorteados', 'dias', 'signo', 'p'])
    plan = plan.sort_values(['inicio', 'estacion']).reset_index(drop=True)
    plan.insert(0, 'episodio', np.arange(1, len(plan) + 1))
    return plan, p


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'results/barcelona_paraad'
    fuente = base / 'ventanas_v1'
    reg = json.loads((fuente / 'registro.json').read_text())
    for name, h in reg['sha256_salidas'].items():
        assert sha(fuente / name) == h, name
    codes = reg['orden_estaciones']
    d = pd.read_parquet(fuente / 'estacion_dias.parquet')
    definiciones = [
        ('ajuste_inicial', '2014-01-01', '2015-12-31', 0, 20),
        ('validacion', '2016-01-01', '2016-12-31', 1, 10),
        ('ajuste_definitivo', '2014-01-01', '2016-12-31', 2, 20),
        ('prueba_2018', '2018-01-01', '2018-12-31', 3, 10),
        ('complementaria_2019', '2019-01-01', '2019-12-31', 4, 10)]
    preparados, resumen = [], []
    for uso_nombre, inicio, fin, uso, n in definiciones:
        for num in range(1, n + 1):
            plan, p = generar(inicio, fin, codes, uso, num)
            control, pc = generar(inicio, fin, codes, uso, num)
            pd.testing.assert_frame_equal(plan, control, check_exact=True)
            assert p == pc
            caso = d[(d.dia_utc >= pd.Timestamp(inicio, tz='UTC')) &
                     (d.dia_utc <= pd.Timestamp(fin, tz='UTC'))]
            positivos, sin_soporte = 0, 0
            for ep in plan.itertuples():
                soporte = caso[(caso.estacion == ep.estacion) &
                               (caso.dia_utc >= ep.inicio) & (caso.dia_utc <= ep.fin)]
                ncom = int(soporte.comun.sum())
                positivos += ncom
                sin_soporte += int(ncom == 0)
            nombre = f'{uso_nombre}_{num:02}'
            preparados.append((nombre, plan))
            resumen.append(dict(calendario=nombre, uso=uso_nombre, numero=num, p=p,
                                episodios=len(plan), episodios_sin_caso_comun=sin_soporte,
                                dias_programados=int(plan.dias.sum()), estacion_dias_positivos_comunes=positivos,
                                universo_comun=int(caso.comun.sum()),
                                positivos=int(plan.signo.eq(1).sum()), negativos=int(plan.signo.eq(-1).sum())))
    out = base / 'planes_proporcionales_v1'
    out.mkdir(parents=True, exist_ok=False)
    for nombre, plan in preparados:
        plan.to_csv(out / f'plan_{nombre}.csv', index=False, float_format='%.17g')
    man = pd.DataFrame(resumen)
    man.to_csv(out / 'manifiesto.csv', index=False, float_format='%.17g')
    entradas = [fuente / 'registro.json', fuente / 'estacion_dias.parquet', Path(__file__),
                ROOT / 'docs/escenario_proporcional_barcelona_v1.md']
    registro = dict(estado='Sólo calendarios: sin matrices alteradas, entrenamiento ni métricas',
                    deltas=DELTAS, delta_entrenamiento_L0=.5, calibracion='2017 limpio',
                    semilla='[42,231,uso,calendario,canal,EOI]', orden_estaciones=codes,
                    reproducibilidad_exacta=True,
                    formulas=dict(positivo='x*(1+delta)', negativo='x/(1+delta)',
                                  redondeo='floor(alterado+0.5), µg/m³'),
                    metadatos='No depende de concentraciones ni de disponibilidad para sortear episodios',
                    versiones=dict(numpy=np.__version__, pandas=pd.__version__),
                    sha256_entradas={str(p.relative_to(ROOT)): sha(p) for p in entradas},
                    sha256_salidas={p.name: sha(p) for p in sorted(out.iterdir())})
    (out / 'registro.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
    print(man.groupby('uso')[['episodios','episodios_sin_caso_comun','estacion_dias_positivos_comunes']].sum().to_string())
    print('Calendarios:', len(man))


if __name__ == '__main__':
    main()
