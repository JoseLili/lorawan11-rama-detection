"""Ventanas Barcelona sin ataques: índices auditables y tensores por lotes.

No importa modelos ni ajusta hiperparámetros. Reutiliza el recorte de L0/RAMA.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def etapa(index):
    y = index.year
    return np.select([np.isin(y, [2014, 2015]), y == 2016, y == 2017,
                      y == 2018, y == 2019],
                     ['ajuste_inicial', 'validacion', 'calibracion', 'prueba', 'complementaria'],
                     default='fuera')


def perfil_local(v):
    """Media de los 14 días LOCALES previos a la misma hora, sin usar t.

    Una fila por fecha local y hora; las transiciones excluidas son NaN.
    Respaldo: historia de esa hora, luego historia global estrictamente pasada.
    No se cuentan sólo los últimos 14 días con dato: se conservan días vacíos.
    """
    local = v.index.tz_convert('Europe/Madrid').tz_localize(None)
    fechas, horas = local.normalize(), local.hour
    dias = pd.date_range(fechas.min(), fechas.max(), freq='D')
    base = pd.DataFrame(np.nan, index=v.index, columns=v.columns)
    for h in range(24):
        sel = horas == h
        diario = v.loc[sel].set_axis(fechas[sel]).groupby(level=0).mean().reindex(dias)
        pasado = diario.shift(1)
        b = pasado.rolling(14, min_periods=1).mean().fillna(pasado.expanding().mean())
        base.loc[sel] = b.reindex(fechas[sel]).to_numpy()
    return base.fillna(v.shift(1).expanding().mean())


def vecinas_geo(geo):
    lat, lon = np.radians(geo.latitud.to_numpy()), np.radians(geo.longitud.to_numpy())
    a = np.sin((lat[:, None] - lat[None, :]) / 2) ** 2
    a += np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin((lon[:, None] - lon[None, :]) / 2) ** 2
    dist = 6371 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    codes = geo.codigo.tolist()
    return {s: sorted([t for t in codes if t != s],
                      key=lambda t: (dist[codes.index(s), codes.index(t)], t))[:4] for s in codes}


def preparar(r, codigos):
    if r.duplicated(['timestamp_utc', 'codi_eoi']).any():
        raise ValueError('Duplicados de estación-timestamp')
    v = r.pivot(index='timestamp_utc', columns='codi_eoi', values='o3').reindex(columns=codigos).sort_index()
    if not v.index.equals(pd.date_range(v.index[0], v.index[-1], freq='h')):
        raise ValueError('Rejilla horaria incompleta: no comprimir huecos')
    reloj = r.drop_duplicates('timestamp_utc').set_index('timestamp_utc').reindex(v.index)
    ex = r.pivot(index='timestamp_utc', columns='codi_eoi', values='excluida_cambio_reloj').reindex(index=v.index, columns=codigos)
    if ex.isna().any().any() or not ex.eq(ex.iloc[:, 0], axis=0).all().all():
        raise ValueError('Exclusión temporal debe ser común a todas las estaciones')
    excluida = ex.iloc[:, 0].astype(bool)
    if v.loc[excluida].notna().any().any():
        raise ValueError('Hay valores en horas excluidas')
    base = perfil_local(v)
    seguro_l0 = (~excluida).rolling(24, min_periods=24).sum().eq(24)
    seguro_v4 = seguro_l0.shift(1, fill_value=False) & ~excluida
    l0 = v.notna().mul(seguro_l0, axis=0)
    v4 = (v.notna() & base.notna()).mul(seguro_v4, axis=0)
    filas = []
    dias = v.index.normalize()
    for dia in dias.unique():
        pos = np.flatnonzero(dias == dia)
        completo = len(pos) == 24 and v.index[pos[0]].hour == 0 and v.index[pos[-1]].hour == 23
        bloque_seguro = completo and not excluida.iloc[pos].any()
        for j, s in enumerate(codigos):
            npresentes = int(v.iloc[pos, j].notna().sum())
            nl0, nv4 = int(l0.iloc[pos, j].sum()), int(v4.iloc[pos, j].sum())
            comun = bloque_seguro and min(npresentes, nl0, nv4) >= 12
            motivo = ('bloque_incompleto' if not completo else
                      'cambio_reloj_en_bloque' if not bloque_seguro else
                      'menos_12_observaciones' if npresentes < 12 else
                      'menos_12_horas_con_contexto' if min(nl0, nv4) < 12 else '')
            filas.append(dict(dia_utc=dia, estacion=s, etapa=etapa(pd.DatetimeIndex([dia]))[0],
                              inicio_pos=int(pos[0]), fin_pos=int(pos[-1]), bloque_completo=completo,
                              bloque_seguro=bool(bloque_seguro), horas_observadas=npresentes,
                              horas_l0=nl0, horas_v4=nv4, comun=bool(comun), motivo=motivo))
    return v, base, reloj, l0, v4, pd.DataFrame(filas)


def ajustar(v, base, vecinas, corte):
    """Parámetros sólo del ajuste autorizado; no calcula métricas de examen."""
    fit = (v.index.year >= 2014) & (v.index.year <= corte)
    mu, sigma = v.loc[fit].mean(), v.loc[fit].std(ddof=1).replace(0, 1)
    if not np.isfinite(mu).all() or not np.isfinite(sigma).all():
        raise ValueError('Escala de ajuste no disponible')
    rel = (v - base) / sigma
    col = pd.DataFrame(index=v.index)
    for s in v.columns:
        n = rel[vecinas[s]]
        col[s] = (rel[s] - n.mean(axis=1)).where(rel[s].notna() & n.notna().sum(axis=1).ge(2))
    escala_vec = col.loc[fit].std(ddof=1).replace(0, 1).fillna(1)
    escala = pd.DataFrame(dict(media=mu, desv=sigma, escala_a14=escala_vec))
    return escala, rel, col / escala_vec


def matrices(v, base, reloj, vecinas, corte):
    escala, rel, a14 = ajustar(v, base, vecinas, corte)
    mascara = v.notna().to_numpy(np.float32)
    hora = reloj[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    z = ((v - escala.media) / escala.desv).fillna(0).to_numpy(np.float32)
    # Orden exacto que espera lstm_local.indices_locales, con n=13.
    F = np.concatenate([rel.fillna(0).to_numpy(np.float32), mascara, hora,
                        a14.fillna(0).to_numpy(np.float32)], axis=1)
    return escala, z, F


def ventana_v4(z, observado, hora, objetivo, posiciones):
    from src.detect.lstm_red import ventanas
    otros = [j for j in range(z.shape[1]) if j != objetivo]
    F = np.concatenate([z[:, otros], observado[:, otros], hora], axis=1)
    # La función reutilizada termina en t: desplazar el final a t−1 para V4.
    return ventanas(F, np.asarray(posiciones) - 1)


def ventana_l0(F, codigos, vecinas, objetivo, posiciones):
    from src.detect.lstm_local import ventanas_locales
    return ventanas_locales(F, codigos, vecinas, objetivo, np.asarray(posiciones))


def bloque_paraad(z, observado, inicios):
    p = np.asarray(inicios)[:, None] + np.arange(24)[None, :]
    if p.size and (p.min() < 0 or p.max() >= len(z)):
        raise ValueError('Bloque incompleto')
    return z[p].transpose(0, 2, 1), observado[p].transpose(0, 2, 1).astype(bool)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = ROOT / 'results/barcelona_paraad'
    fuente = root / 'tiempo_utc_v1/rejilla_utc.parquet'
    cohorte = ROOT / 'data/reference/barcelona_paraad/cohorte13.csv'
    geo = pd.read_csv(cohorte, dtype={'codigo': str})
    codigos = geo.codigo.tolist()
    r = pd.read_parquet(fuente)
    resultado = preparar(r, codigos)
    control = preparar(r, codigos)
    for a, b in zip(resultado, control):
        pd.testing.assert_frame_equal(a, b, check_exact=True)
    v, base, reloj, l0, v4, dias = resultado
    vec = vecinas_geo(geo)
    out = root / 'ventanas_v1'
    # Evita reemplazar una máscara que ya pudiera haberse utilizado.
    out.mkdir(parents=True, exist_ok=False)
    v.to_parquet(out / 'valores.parquet')
    base.to_parquet(out / 'perfiles_causales.parquet')
    reloj[['hora_local', 'hora_sin', 'hora_cos', 'excluida_cambio_reloj']].to_parquet(out / 'reloj.parquet')
    l0.to_parquet(out / 'horas_validas_l0.parquet')
    v4.to_parquet(out / 'horas_validas_v4.parquet')
    dias.to_parquet(out / 'estacion_dias.parquet', index=False)
    dias.pivot(index='dia_utc', columns='estacion', values='comun').reindex(columns=codigos).to_csv(out / 'mascara_comun.csv')
    cobertura = dias.groupby(['estacion', 'etapa']).agg(
        dias_calendario=('comun', 'size'), dias_comunes=('comun', 'sum'),
        dias_24_observaciones=('horas_observadas', lambda x: int(x.eq(24).sum())))
    cobertura.to_csv(out / 'cobertura_estacion_etapa.csv')
    dias[~dias.comun].groupby(['etapa', 'motivo']).size().rename('estacion_dias').to_csv(out / 'exclusiones.csv')
    eleg = []
    for s in codigos:
        for e in ['ajuste_inicial', 'validacion', 'calibracion']:
            sel = etapa(v.index) == e
            ok = v4.loc[sel, s] & l0.loc[sel, s]
            meses = len(set(zip(ok.index[ok].year, ok.index[ok].month)))
            eleg.append(dict(estacion=s, etapa=e, horas_efectivas=int(ok.sum()),
                             meses_con_ejemplos=meses, cumple_2000h_6meses=bool(ok.sum() >= 2000 and meses >= 6)))
    pd.DataFrame(eleg).to_csv(out / 'elegibilidad_etapas.csv', index=False)
    observado = v.notna().to_numpy(np.float32)
    hora = reloj[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    checks = []
    for nombre, corte in [('seleccion', 2015), ('definitivo', 2016)]:
        escala, z, F = matrices(v, base, reloj, vec, corte)
        esc2, z2, F2 = matrices(v, base, reloj, vec, corte)
        pd.testing.assert_frame_equal(escala, esc2, check_exact=True)
        np.testing.assert_array_equal(z, z2)
        np.testing.assert_array_equal(F, F2)
        escala.to_csv(out / f'escalas_{nombre}.csv')
        np.save(out / f'z_{nombre}.npy', z, allow_pickle=False)
        np.save(out / f'l0_features_{nombre}.npy', F, allow_pickle=False)
        for s in codigos:
            pos = np.flatnonzero((v4[s] & l0[s]).to_numpy())[:3]
            x4 = ventana_v4(z, observado, hora, codigos.index(s), pos)
            x0 = ventana_l0(F, codigos, vec, s, pos)
            assert x4.shape == (len(pos), 24, 26) and x0.shape == (len(pos), 24, 17)
            assert np.isfinite(x4).all() and np.isfinite(x0).all()
        inicios = dias.loc[dias.comun, 'inicio_pos'].drop_duplicates().to_numpy()[:3]
        xp, mp = bloque_paraad(z, observado, inicios)
        assert xp.shape == mp.shape == (len(inicios), 13, 24)
        checks.append(dict(fase=nombre, v4=[24, 26], l0=[24, 17], paraad=[13, 24]))
    (out / 'vecinas.json').write_text(json.dumps(vec, indent=2) + '\n')
    archivos = sorted(p for p in out.iterdir() if p.is_file())
    fuentes = [fuente, cohorte, Path(__file__), ROOT / 'src/detect/lstm_red.py', ROOT / 'src/detect/lstm_local.py']
    registro = dict(estado='Ventanas indexadas sin ataques ni modelos; no métricas de detección',
                    orden_estaciones=codigos, formatos=checks, ventana_v4='t−24..t−1', ventana_l0='t−23..t',
                    perfil='14 fechas locales previas, respaldo histórico hora y global; estrictamente causal',
                    escala_seleccion='2014–2015 UTC', escala_definitiva='2014–2016 UTC',
                    faltantes='Máscara observada; relleno 0 tras normalizar; no exigir vecinas completas',
                    comun='Bloque UTC completo sin cambios de reloj; >=12 observadas y >=12 horas válidas por detector',
                    soporte='Datos compartidos + índices; funciones ventana_v4, ventana_l0 y bloque_paraad materializan lotes',
                    advertencia='Bajo ataque se deben recalcular perfiles y características causales; conservar escalas y máscara común',
                    reproducibilidad_exacta=True, elegibilidad_todas_etapas=bool(pd.DataFrame(eleg).cumple_2000h_6meses.all()),
                    sha256_entradas={str(p.relative_to(ROOT)): sha(p) for p in fuentes},
                    sha256_salidas={p.name: sha(p) for p in archivos})
    (out / 'registro.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2) + '\n')
    print(dias.groupby('etapa').comun.agg(['size', 'sum']).to_string())
    print('Todas las estaciones cumplen en ajuste/validación/calibración:', registro['elegibilidad_todas_etapas'])


if __name__ == '__main__':
    main()
