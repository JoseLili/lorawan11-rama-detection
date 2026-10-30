"""Aplica los planes registrados y recalcula contexto con escalas limpias fijas."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.barcelona.preparar_ventanas import perfil_local

ROOT = Path(__file__).resolve().parents[2]
LIMITES = {'ajuste_inicial': ('2014-01-01', '2015-12-31'),
           'validacion': ('2016-01-01', '2016-12-31'),
           'ajuste_definitivo': ('2014-01-01', '2016-12-31'),
           'prueba_2018': ('2018-01-01', '2018-12-31'),
           'complementaria_2019': ('2019-01-01', '2019-12-31')}


def aplicar(v, plan, delta):
    if delta not in (1., .5, .2, .1, .05):
        raise ValueError('Delta no registrado')
    a = v.copy()
    programada = pd.DataFrame(False, index=v.index, columns=v.columns)
    for ep in plan.itertuples():
        if ep.estacion not in v.columns:
            raise ValueError('Estación fuera de cohorte')
        sel = (v.index >= ep.inicio) & (v.index <= ep.fin)
        if programada.loc[sel, ep.estacion].any():
            raise ValueError('Episodios superpuestos')
        if ep.signo not in (-1, 1):
            raise ValueError('Signo inválido')
        programada.loc[sel, ep.estacion] = True
        x = v.loc[sel, ep.estacion]
        a.loc[sel, ep.estacion] = np.floor((x * (1 + delta) if ep.signo == 1 else x / (1 + delta)) + .5)
    cambiada = v.notna() & a.ne(v)
    assert a.notna().equals(v.notna())
    assert not (cambiada & ~programada).any().any()
    pd.testing.assert_frame_equal(a.where(~programada), v.where(~programada), check_exact=True)
    return a, cambiada, programada


def caracteristicas(a, escala, reloj, vec):
    """Nunca ajusta escalas: todas vienen de los datos limpios autorizados."""
    base = perfil_local(a)
    rel = (a - base) / escala.desv
    cols = []
    for s in a:
        n = rel[vec[s]]
        cols.append(((rel[s] - n.mean(axis=1)).where(rel[s].notna() & n.notna().sum(axis=1).ge(2)) /
                     escala.loc[s, 'escala_a14']).fillna(0).to_numpy(np.float32))
    z = ((a - escala.media) / escala.desv).fillna(0).to_numpy(np.float32)
    F = np.concatenate([rel.fillna(0).to_numpy(np.float32), a.notna().to_numpy(np.float32),
                        reloj[['hora_sin', 'hora_cos']].to_numpy(np.float32), np.column_stack(cols)], axis=1)
    assert np.isfinite(F).all() and np.isfinite(z).all()
    return base, z, F


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def comprobar_registro(carpeta):
    r = json.loads((carpeta / 'registro.json').read_text())
    for name, h in r['sha256_salidas'].items():
        assert sha(carpeta / name) == h, name
    return r


def main():
    raiz = ROOT / 'results/barcelona_paraad'
    w, planes = raiz / 'ventanas_v1', raiz / 'planes_proporcionales_v1'
    rw, rp = comprobar_registro(w), comprobar_registro(planes)
    v = pd.read_parquet(w / 'valores.parquet')
    reloj = pd.read_parquet(w / 'reloj.parquet')
    vec = json.loads((w / 'vecinas.json').read_text())
    dias = pd.read_parquet(w / 'estacion_dias.parquet')
    man = pd.read_csv(planes / 'manifiesto.csv')
    escalas = {}
    for fase in ('seleccion', 'definitivo'):
        esc = pd.read_csv(w / f'escalas_{fase}.csv', index_col=0)
        esc.index = esc.index.astype(str).str.zfill(8)
        escalas[fase] = esc.reindex(v.columns)
    ins = [Path(__file__), ROOT / 'experiments/barcelona/preparar_ventanas.py',
           w / 'registro.json', planes / 'registro.json']
    entradas = {str(p.relative_to(ROOT)): sha(p) for p in ins}
    out = raiz / 'ataques_proporcionales_v1'
    out.mkdir(exist_ok=True)
    firma = dict(sha256_entradas=entradas, historia='Limpia antes del inicio del periodo; alterada dentro del periodo',
                 calendario='70 planes: 50 de ajuste/validación a d50, 20 de prueba a cinco deltas')
    if (out / 'entrada.json').exists():
        assert json.loads((out / 'entrada.json').read_text()) == firma
    else:
        (out / 'entrada.json').write_text(json.dumps(firma, ensure_ascii=False, indent=2) + '\n')
    resumen = []
    total = 150
    for fila in man.itertuples():
        inicio, fin = LIMITES[fila.uso]
        inicio = pd.Timestamp(inicio, tz='UTC')
        fin = pd.Timestamp(fin, tz='UTC') + pd.Timedelta(hours=23)
        limpio = v.loc[:fin]
        r = reloj.loc[limpio.index]
        fase = 'seleccion' if fila.uso in ('ajuste_inicial', 'validacion') else 'definitivo'
        escala = escalas[fase]
        plan = pd.read_csv(planes / f'plan_{fila.calendario}.csv', dtype={'estacion': str},
                           parse_dates=['inicio', 'fin'], float_precision='round_trip')
        deltas = (1., .5, .2, .1, .05) if fila.uso in ('prueba_2018', 'complementaria_2019') else (.5,)
        for delta in deltas:
            unidad = out / fila.calendario / f'd{round(delta * 100)}'
            completo = unidad / 'completo.json'
            if completo.exists():
                previo = json.loads(completo.read_text())
                for name, h in previo['sha256_salidas'].items():
                    assert sha(unidad / name) == h
                resumen.append(previo['resumen'])
                continue
            if unidad.exists():
                raise RuntimeError(f'Salida parcial pendiente de revisar: {unidad}')
            a, y, programada = aplicar(limpio, plan, delta)
            a2, y2, p2 = aplicar(limpio, plan, delta)
            for x, z in [(a, a2), (y, y2), (programada, p2)]:
                pd.testing.assert_frame_equal(x, z, check_exact=True)
            base, z, F = caracteristicas(a, escala, r, vec)
            b2, z2, F2 = caracteristicas(a2, escala, r, vec)
            pd.testing.assert_frame_equal(base, b2, check_exact=True)
            np.testing.assert_array_equal(z, z2)
            np.testing.assert_array_equal(F, F2)
            assert base.notna().equals(pd.read_parquet(w / 'perfiles_causales.parquet').loc[a.index].notna())
            # Sólo se almacena el periodo y sus 24 horas previas para ventanas.
            pos0 = max(0, int(a.index.searchsorted(inicio)) - 24)
            sl = slice(pos0, len(a))
            propios = a.index >= inicio
            ad = a.iloc[sl]
            dy = programada.groupby(programada.index.normalize()).any()
            sd = dias[(dias.dia_utc >= inicio) & (dias.dia_utc <= fin)].copy()
            sd['etiqueta'] = [bool(dy.loc[t, s]) for t, s in zip(sd.dia_utc, sd.estacion)]
            sd['inicio_pos'] -= pos0
            sd['fin_pos'] -= pos0
            unidad.mkdir(parents=True)
            ad.to_parquet(unidad / 'valores_alterados.parquet')
            base.iloc[sl].to_parquet(unidad / 'perfiles_causales.parquet')
            y.iloc[sl].to_parquet(unidad / 'etiquetas_hora.parquet')
            programada.iloc[sl].to_parquet(unidad / 'episodio_hora.parquet')
            sd.to_parquet(unidad / 'estacion_dias.parquet', index=False)
            np.save(unidad / 'z.npy', z[sl], allow_pickle=False)
            np.save(unidad / 'l0_features.npy', F[sl], allow_pickle=False)
            info = dict(calendario=fila.calendario, uso=fila.uso, delta=delta, escala=fase,
                        filas=len(ad), offset_global=pos0,
                        lecturas_programadas=int((programada.loc[propios] & limpio.loc[propios].notna()).to_numpy().sum()),
                        lecturas_cambiadas=int(y.loc[propios].to_numpy().sum()),
                        estacion_dias_comunes=int(sd.comun.sum()),
                        estacion_dias_positivos_comunes=int((sd.comun & sd.etiqueta).sum()),
                        reproducibilidad_exacta=True)
            archivos = sorted(unidad.iterdir())
            registro = dict(resumen=info, sha256_salidas={p.name: sha(p) for p in archivos})
            completo.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
            resumen.append(info)
            print(f'{len(resumen)}/{total} {fila.calendario} d{round(delta*100)}: {info["lecturas_cambiadas"]} lecturas cambiadas', flush=True)
    tabla = pd.DataFrame(resumen)
    assert len(tabla) == total
    tabla.to_csv(out / 'resumen.csv', index=False)
    registro = dict(estado='150 matrices alteradas y contexto recalculado; sin modelos ni métricas de detección',
                    unidades=total, reproducibilidad_exacta=True, mascara_comun_sha256=sha(w / 'mascara_comun.csv'),
                    entrada=firma, versiones=dict(numpy=np.__version__, pandas=pd.__version__),
                    sha256_completos={str(p.relative_to(out)): sha(p) for p in sorted(out.glob('*/*/completo.json'))},
                    sha256_resumen=sha(out / 'resumen.csv'))
    (out / 'registro.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
    print('FINALIZADO: 150 unidades verificadas', flush=True)


if __name__ == '__main__':
    main()
