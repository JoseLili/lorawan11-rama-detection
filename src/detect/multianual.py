"""Protocolo temporal común V4 multianual (docs/protocolo_lstm_v4_multianual.md).

Matriz fija de 33 estaciones sobre la rejilla horaria 2020-01-01 a 2026-07-31,
asignación de etapas por fecha del objetivo, canal inactivo, perfil causal con
respaldo explícito y cobertura por etapa. No entrena ni carga modelos.
"""
from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from src.ingest.rama import load_wide, to_long

PROTOCOLO = 'v4_multianual_33_p95cal2023_v1'

# Orden de la referencia de 2025 (§3.1). No se eliminan columnas vacías por año.
ESTACIONES = (
    'ACO AJM AJU ATI BJU CAM CCA CHO CUA CUT FAC FAR GAM HGM INN IZT '
    'LLA LPR MER MGH MON MPA NEZ PED SAC SAG TAH TLA TLI UAX UIZ VIF XAL'
).split()

INICIO, FIN = pd.Timestamp('2020-01-01 00:00'), pd.Timestamp('2026-07-31 23:00')

# Etapas excluyentes por fecha del objetivo (§2). El ajuste definitivo es la
# unión de ajuste inicial y validación; se deriva, no es una etiqueta propia.
ETAPAS = {
    'ajuste_inicial': ('2020-01-01', '2021-12-31'),
    'validacion': ('2022-01-01', '2022-12-31'),
    'calibracion': ('2023-01-01', '2023-12-31'),
    'prueba_2024': ('2024-01-01', '2024-12-31'),
    'prueba_2025': ('2025-01-01', '2025-12-31'),
    'prueba_2026_parcial': ('2026-01-01', '2026-07-31'),
}
AJUSTE_DEFINITIVO = ('ajuste_inicial', 'validacion')
OBLIGATORIAS = ('ajuste_inicial', 'validacion', 'calibracion')

MIN_HORAS, MIN_MESES = 2000, 6    # §3.2, fijados antes de entrenar
VENTANA, PERFIL_DIAS = 24, 14


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leer_checksums(path) -> dict[str, str]:
    """`docs/checksums_2020_2026.txt` → {'20RAMA.zip:2020O3.xls': sha, ...}."""
    out = {}
    for linea in Path(path).read_text().splitlines():
        if linea.strip() and not linea.startswith('#'):
            h, nombre = linea.split(maxsplit=1)
            out[nombre] = h
    return out


def cargar_o3_zips(raw, checksums, anios=range(2020, 2027)):
    """Lee O3 de cada `YYRAMA.zip`, verificando el SHA-256 del .xls interno.

    Devuelve (long, fuentes): formato largo con -99 → NaN y origen del dato,
    y la lista de archivos con su hash.
    """
    largos, fuentes = [], []
    for anio in anios:
        z = f'{str(anio)[2:]}RAMA.zip'
        interno = f'{anio}O3.xls'
        with zipfile.ZipFile(Path(raw) / z) as zf:
            b = zf.read(interno)
        h = sha256(b)
        esperado = checksums.get(f'{z}:{interno}')
        if h != esperado:
            raise ValueError(f'{z}:{interno} no coincide con checksums ({h} != {esperado})')
        crudo = pd.read_excel(BytesIO(b), header=0)
        centinela = crudo.melt(id_vars=['FECHA', 'HORA'], var_name='station', value_name='v')
        largo = to_long(load_wide(BytesIO(b)), 'O3')
        largo['origen'] = np.where(largo['value'].notna(), 'observado', 'centinela_-99')
        assert (centinela['v'] == -99).sum() == (largo['origen'] == 'centinela_-99').sum()
        largos.append(largo)
        fuentes.append(dict(zip=z, archivo=interno, sha256=h))
    return pd.concat(largos, ignore_index=True), fuentes


def matriz_fija(long: pd.DataFrame):
    """Rejilla horaria continua × 33 estaciones fijas.

    Devuelve (valores, origen). `origen` distingue observado, centinela -99,
    renglón ausente del .xls y columna ausente del año. Sólo para auditoría:
    no es entrada del modelo.
    """
    rejilla = pd.date_range(INICIO, FIN, freq='h', name='timestamp')
    long = long[long['station'].isin(ESTACIONES)]
    valores = (long.pivot(index='timestamp', columns='station', values='value')
                   .reindex(index=rejilla, columns=ESTACIONES))
    origen = (long.pivot(index='timestamp', columns='station', values='origen')
                  .reindex(index=rejilla, columns=ESTACIONES))
    filas_presentes = rejilla.isin(long['timestamp'].unique())
    columna_anio = (long.assign(anio=long['timestamp'].dt.year)
                        .groupby('anio')['station'].unique().map(set))
    for anio, presentes in columna_anio.items():
        en_anio = (rejilla.year == anio) & filas_presentes
        for s in set(ESTACIONES) - presentes:
            origen.loc[en_anio, s] = 'columna_ausente'
    origen[origen.isna()] = 'renglon_ausente'
    valores.columns.name = origen.columns.name = 'station'
    return valores, origen


def etapa_de(ts) -> pd.Series:
    """Etapa por fecha del OBJETIVO; NaN fuera del periodo del protocolo."""
    ts = pd.DatetimeIndex(ts)
    etiqueta = pd.Series(pd.NA, index=ts, dtype='object')
    for nombre, (ini, fin) in ETAPAS.items():
        dentro = (ts >= pd.Timestamp(ini)) & (ts <= pd.Timestamp(fin) + pd.Timedelta(hours=23))
        etiqueta[dentro] = nombre
    return etiqueta


def mascara_etapas(index, etapas) -> np.ndarray:
    return etapa_de(index).isin(list(etapas)).to_numpy()


def canales_inactivos(valores: pd.DataFrame, etapas=AJUSTE_DEFINITIVO) -> list[str]:
    """Estaciones sin ninguna observación en el ajuste (§4.1)."""
    m = mascara_etapas(valores.index, etapas)
    return [s for s in valores.columns if valores.loc[m, s].notna().sum() == 0]


def normalizacion(valores: pd.DataFrame, etapas, inactivos=()):
    """Media y desviación por estación sólo con las etapas de ajuste.

    Desviación con ddof=1 (pandas), como `construir_ventanas`; 0 → 1.
    Canales inactivos: media 0, desviación 1.
    """
    m = mascara_etapas(valores.index, etapas)
    mu, sigma = valores.loc[m].mean(), valores.loc[m].std().replace(0, 1.0)
    for s in inactivos:
        mu[s], sigma[s] = 0.0, 1.0
    return mu, sigma


def entradas_modelo(valores: pd.DataFrame, inactivos) -> pd.DataFrame:
    """Copia de la matriz con canales inactivos forzados a faltante (valor 0, máscara 0).

    Se usa SÓLO para construir entradas. El máximo de red se calcula con `valores`.
    """
    x = valores.copy()
    x[list(inactivos)] = np.nan
    return x


def perfil_causal(serie: pd.Series, dias: int = PERFIL_DIAS) -> pd.DataFrame:
    """Base del objetivo con la regla de respaldo del §4.2.

    Requiere rejilla horaria continua: `dias` posiciones por grupo horario son
    `dias` días naturales, aunque falten lecturas. Para cada t usa sólo
    observaciones estrictamente anteriores.

    Devuelve DataFrame con `base` y `origen_base`:
    '14d' | 'historico_hora' | 'historico_global' | 'sin_historia' (base NaN).
    """
    if not serie.index.equals(pd.date_range(serie.index[0], serie.index[-1], freq='h')):
        raise ValueError('perfil_causal requiere rejilla horaria continua')
    hora = serie.index.hour
    g = serie.groupby(hora)
    p14 = g.transform(lambda s: s.shift(1).rolling(dias, min_periods=1).mean())
    phora = g.transform(lambda s: s.shift(1).expanding().mean())
    pglobal = serie.shift(1).expanding().mean()

    base = p14.copy()
    origen = pd.Series(np.where(p14.notna(), '14d', ''), index=serie.index, dtype=object)
    for respaldo, nombre in ((phora, 'historico_hora'), (pglobal, 'historico_global')):
        usar = base.isna() & respaldo.notna()
        base[usar] = respaldo[usar]
        origen[usar] = nombre
    origen[base.isna()] = 'sin_historia'
    return pd.DataFrame({'base': base, 'origen_base': origen})


def ejemplos_validos(valores: pd.DataFrame, objetivo: str, perfil: pd.DataFrame,
                     ventana: int = VENTANA) -> pd.Series:
    """Booleano por hora: objetivo observado, base disponible y `ventana` horas previas en la rejilla."""
    ok = valores[objetivo].notna() & perfil['base'].notna()
    ok.iloc[:ventana] = False
    return ok


def _racha_max(falta: np.ndarray) -> int:
    if not falta.any():
        return 0
    b = np.diff(np.r_[0, falta.astype(int), 0])
    return int((np.flatnonzero(b == -1) - np.flatnonzero(b == 1)).max())


def cobertura_etapas(valores: pd.DataFrame, inactivos=()) -> pd.DataFrame:
    """Una fila por objetivo × etapa con ejemplos efectivos y clasificación §3.2."""
    etapa = etapa_de(valores.index)
    filas = []
    for s in ESTACIONES:
        perfil = perfil_causal(valores[s])
        ok = ejemplos_validos(valores, s, perfil)
        for nombre in ETAPAS:
            m = (etapa == nombre).to_numpy()
            okm = ok[m]
            filas.append(dict(
                objetivo=s, etapa=nombre,
                horas_etapa=int(m.sum()),
                horas_validas=int(valores.loc[m, s].notna().sum()),
                ejemplos=int(okm.sum()),
                meses_con_ejemplos=int(okm[okm].index.to_period('M').nunique()),
                racha_max_sin_dato_h=_racha_max(valores.loc[m, s].isna().to_numpy()),
                base_14d=int((perfil.loc[m, 'origen_base'][okm] == '14d').sum()),
                base_historico_hora=int((perfil.loc[m, 'origen_base'][okm] == 'historico_hora').sum()),
                base_historico_global=int((perfil.loc[m, 'origen_base'][okm] == 'historico_global').sum()),
                canal_inactivo=s in inactivos))
    cob = pd.DataFrame(filas)
    cob['cumple_minimo'] = (cob.ejemplos >= MIN_HORAS) & (cob.meses_con_ejemplos >= MIN_MESES)
    return cob.merge(clasificar(cob), on='objetivo')


def clasificar(cob: pd.DataFrame) -> pd.DataFrame:
    """fuera | baja_representatividad | principal, con motivo (§3.2)."""
    out = []
    for s, g in cob[cob.etapa.isin(OBLIGATORIAS)].groupby('objetivo', sort=False):
        g = g.set_index('etapa')
        vacias = [e for e in OBLIGATORIAS if g.at[e, 'ejemplos'] == 0]
        bajas = [e for e in OBLIGATORIAS if not g.at[e, 'cumple_minimo'] and e not in vacias]
        if vacias:
            clase, motivo = 'fuera', 'sin ejemplos en ' + ', '.join(vacias)
        elif bajas:
            clase = 'baja_representatividad'
            motivo = '; '.join(f'{e}: {g.at[e, "ejemplos"]} ejemplos, {g.at[e, "meses_con_ejemplos"]} meses'
                               for e in bajas)
        else:
            clase, motivo = 'principal', ''
        out.append(dict(objetivo=s, clasificacion=clase, motivo=motivo))
    return pd.DataFrame(out)


def ventana_ejemplo(entradas: pd.DataFrame, objetivo: str, t, mu, sigma, perfil: pd.DataFrame,
                    valores: pd.DataFrame | None = None, ventana: int = VENTANA) -> dict:
    """Ventana 24 × 66 de un ejemplo, en el orden de canales de `construir_ventanas`.

    `entradas` ya trae los canales inactivos como NaN.
    """
    t = pd.Timestamp(t)
    i = entradas.index.get_loc(t)
    vecinas = [c for c in entradas.columns if c != objetivo]
    ctx = entradas.iloc[i - ventana:i][vecinas]
    norm = ((ctx - mu[vecinas]) / sigma[vecinas]).fillna(0.0)
    mascara = ctx.notna().astype(np.float32)
    h = ctx.index.hour.to_numpy()
    X = pd.concat([norm.add_suffix('_valor'), mascara.add_suffix('_mascara'),
                   pd.DataFrame({'hora_sin': np.sin(2 * np.pi * h / 24),
                                 'hora_cos': np.cos(2 * np.pi * h / 24)}, index=ctx.index)], axis=1)
    original = (valores if valores is not None else entradas).at[t, objetivo]
    return dict(X=X, crudo=ctx, objetivo=objetivo, t=t, etapa=etapa_de([t]).iat[0],
                original=original, base=perfil.at[t, 'base'],
                origen_base=perfil.at[t, 'origen_base'],
                y=original - perfil.at[t, 'base'])
