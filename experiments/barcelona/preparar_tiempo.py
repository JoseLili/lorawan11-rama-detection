"""Rejilla UTC con convención explícita; no genera ataques ni ventanas de modelos."""
import calendar
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ZONA = 'Europe/Madrid'


def dias_cambio(inicio, fin):
    dias = []
    for anio in range(pd.Timestamp(inicio).year, pd.Timestamp(fin).year + 1):
        for mes in (3, 10):
            dia = max(s[calendar.SUNDAY] for s in calendar.monthcalendar(anio, mes))
            dias.append(pd.Timestamp(anio, mes, dia))
    return pd.DatetimeIndex(dias)


def preparar(d, codigos, inicio='2014-01-01', fin='2020-01-01'):
    """h01 = intervalo local 00–01, h24 = 23–24: supuesto operativo registrado.

    Se excluye el día local entero de cada transición antes de localizar horas.
    No se resuelve una ambigüedad escogiendo arbitrariamente verano/invierno.
    """
    d = d.copy()
    d['fecha'] = pd.to_datetime(d.fecha)
    if d.duplicated(['codi_eoi', 'fecha', 'hora_fuente']).any():
        raise ValueError('Claves de fuente duplicadas')
    if not d.hora_fuente.between(1, 24).all():
        raise ValueError('Hora fuera de 1..24')
    if not set(d.codi_eoi) <= set(codigos):
        raise ValueError('Estación fuera de cohorte')
    if not ((d.fecha >= pd.Timestamp(inicio)) & (d.fecha < pd.Timestamp(fin))).all():
        raise ValueError('Fecha fuera de periodo')
    cambios = dias_cambio(inicio, fin)
    excluidas = d[d.fecha.isin(cambios)].copy().reset_index(drop=True)
    validas = d[~d.fecha.isin(cambios)].copy()
    local = pd.DatetimeIndex(validas.fecha + pd.to_timedelta(validas.hora_fuente - 1, unit='h'))
    validas['timestamp_utc'] = local.tz_localize(ZONA, ambiguous='raise', nonexistent='raise').tz_convert('UTC')
    if validas.duplicated(['codi_eoi', 'timestamp_utc']).any():
        raise ValueError('Timestamps duplicados')
    indice = pd.date_range(pd.Timestamp(inicio, tz=ZONA).tz_convert('UTC'),
                           pd.Timestamp(fin, tz=ZONA).tz_convert('UTC'), freq='h', inclusive='left')
    loc = indice.tz_convert(ZONA)
    reloj = pd.DataFrame({'timestamp_utc': indice,
                         'fecha_local': loc.tz_localize(None).normalize(),
                         'hora_local': loc.hour,
                         'hora_sin': np.sin(2 * np.pi * loc.hour / 24),
                         'hora_cos': np.cos(2 * np.pi * loc.hour / 24)})
    reloj['excluida_cambio_reloj'] = reloj.fecha_local.isin(cambios)
    rejilla = pd.DataFrame({'codi_eoi': list(codigos)}).merge(reloj, how='cross')
    rejilla = rejilla.merge(validas, on=['codi_eoi', 'timestamp_utc'], how='left', validate='one_to_one')
    rejilla['observado'] = rejilla.o3.notna()
    return rejilla, excluidas


def huella(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base = ROOT / 'results/barcelona_paraad'
    fuente = base / 'auditoria/observaciones_cohorte13_hora_fuente.parquet'
    cohorte = ROOT / 'data/reference/barcelona_paraad/cohorte13.csv'
    codigos = pd.read_csv(cohorte, dtype={'codigo': str}).codigo.tolist()
    d = pd.read_parquet(fuente)
    r, e = preparar(d, codigos)
    # Repetición completa en memoria, antes de aceptar y exportar.
    r2, e2 = preparar(d, codigos)
    pd.testing.assert_frame_equal(r, r2, check_exact=True)
    pd.testing.assert_frame_equal(e, e2, check_exact=True)
    out = base / 'tiempo_utc_v1'
    out.mkdir(parents=True, exist_ok=True)
    archivos = {'rejilla_utc.parquet': r, 'fuente_excluida_cambio_reloj.parquet': e}
    for nombre, frame in archivos.items():
        p = out / nombre
        if p.exists():
            pd.testing.assert_frame_equal(pd.read_parquet(p), frame, check_exact=True)
        else:
            frame.to_parquet(p, index=False)
    reporte = dict(
        convencion='h01 intervalo local 00–01; h24 intervalo local 23–24; timestamp al inicio',
        estatus='Supuesto operativo sustentado en contraste oficial; no certificación de toda la fuente',
        zona=ZONA, eje='UTC', hora_entrada_modelos='local al inicio del intervalo',
        transiciones='Excluir día local completo, todas las estaciones; conservar fuente aparte',
        faltantes='Sin interpolación; la rejilla conserva cada hora física, incluso las excluidas',
        ventanas='Pendientes: rechazar cualquier ventana que cruce horas excluidas; aplicar además contexto y mínimo diario común',
        bloques='Previstos 00–24 UTC; no mezclar años de etapas dentro de un bloque',
        estaciones=len(codigos), filas_rejilla=len(r), observaciones_fuente=int(d.o3.notna().sum()),
        observaciones_retenidas=int(r.observado.sum()), observaciones_excluidas=int(e.o3.notna().sum()),
        horas_rejilla_por_estacion=int(len(r) // len(codigos)),
        dias_locales_excluidos=[str(x.date()) for x in dias_cambio('2014-01-01', '2019-12-31')],
        reproducibilidad_exacta_dos_ejecuciones=True,
        versiones=dict(pandas=pd.__version__, numpy=np.__version__),
        sha256_entradas={str(p.relative_to(ROOT)): huella(p) for p in [fuente, cohorte, Path(__file__)]},
        sha256_salidas={nombre: huella(out / nombre) for nombre in archivos})
    assert reporte['observaciones_fuente'] == reporte['observaciones_retenidas'] + reporte['observaciones_excluidas']
    (out / 'registro.json').write_text(json.dumps(reporte, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: reporte[k] for k in ['filas_rejilla', 'observaciones_retenidas', 'observaciones_excluidas', 'reproducibilidad_exacta_dos_ejecuciones']}))


if __name__ == '__main__':
    main()
