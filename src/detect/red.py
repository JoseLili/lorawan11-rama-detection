"""Evaluación de ataques aislados a un mensaje, con detectores por estación.

No se mezclan ataques simultáneos: cada fila es un contrafactual independiente.
La decisión diaria se refiere al máximo OBSERVADO, no a declaraciones oficiales.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.decision.nom172 import banda_o3


def perfil_v4_sin_test(serie, corte, dias=14):
    """Perfil V4 con respaldo ajustado sólo al train, nunca al año completo.

En test la media móvil usa exclusivamente datos anteriores. El respaldo de
arranque usa medias horarias de train (y su media global si falta esa hora).
No cambia la función histórica ni sus artefactos; es una variante explícita.
"""
    h = serie.index.hour
    pasado = serie.groupby(h).transform(
        lambda s: s.shift(1).rolling(dias, min_periods=1).mean())
    train = serie.iloc[:corte]
    respaldo = train.groupby(train.index.hour).mean().reindex(h).to_numpy()
    return pasado.fillna(pd.Series(respaldo, index=serie.index)).fillna(train.mean())


def contexto_diario(matriz):
    """Cada mensaje con máximo del día y máximo excluyendo sólo ese mensaje.

Se conservan competidores sin modelo, empates y otras horas del mismo día.
Los faltantes NO se interpretan como cero. Una fila por mensaje observado.
"""
    filas = []
    for fecha, bloque in matriz.groupby(matriz.index.normalize()):
        raw = bloque.to_numpy(dtype=float)
        ii, jj = np.where(np.isfinite(raw))
        v = raw[ii, jj]
        if len(v) == 0:
            continue
        maximo = v.max()
        unicos = (v == maximo).sum() == 1
        segundo = np.partition(v, -2)[-2] if len(v) > 1 else np.nan
        otros = np.where((v == maximo) & unicos, segundo, maximo)
        filas.append(pd.DataFrame({
            'fecha': fecha, 'timestamp': bloque.index.to_numpy()[ii],
            'estacion': bloque.columns.to_numpy()[jj], 'original_ppb': v,
            'maximo_original_ppb': maximo, 'maximo_otros_ppb': otros,
            'mensajes_observados_dia': len(v),
            'mensajes_posibles_dia': len(bloque) * len(bloque.columns),
        }))
    if not filas:
        raise ValueError('No hay observaciones en el periodo común de prueba.')
    return pd.concat(filas, ignore_index=True)


def efectos_red(contexto, recibidos, tau=155):
    """Reemplaza UNA lectura; las demás del día permanecen intactas."""
    original = contexto.maximo_original_ppb.to_numpy()
    recibido = np.asarray(recibidos)
    nuevo = np.fmax(contexto.maximo_otros_ppb.to_numpy(), recibido)
    return pd.DataFrame({
        'maximo_atacado_ppb': nuevo,
        'falsa_fase1': (original < tau) & (nuevo >= tau),
        'anulada_fase1': (original >= tau) & (nuevo < tau),
        'cambio_banda_red': banda_o3(original) != banda_o3(nuevo),
        'cambio_banda_local': banda_o3(contexto.original_ppb.to_numpy()) != banda_o3(recibido),
    }, index=contexto.index)


def metricas_binarias(etiquetas, alertas):
    y, a = np.asarray(etiquetas, dtype=bool), np.asarray(alertas, dtype=bool)
    tp, fp = int((y & a).sum()), int((~y & a).sum())
    fn, tn = int((y & ~a).sum()), int((~y & ~a).sum())
    def porcentaje(n, d):
        return 100 * n / d if d else np.nan
    return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                recall_pct=porcentaje(tp, tp+fn), precision_pct=porcentaje(tp, tp+fp),
                f2_pct=porcentaje(5*tp, 5*tp+4*fn+fp), fpr_pct=porcentaje(fp, fp+tn))


def resumir_dias(eventos, fechas):
    """Denominador de días fijo. Sin predicción => desconocido, nunca negativo.

Un día puede tener oportunidades detectadas Y no detectadas. Por eso la
fracción de días no detectados no se obtiene multiplicando promedios.
"""
    resumen, detalle = [], []
    for (bit, tipo), g in eventos.groupby(['bit', 'tipo_dano']):
        d = pd.DataFrame(index=pd.DatetimeIndex(fechas, name='fecha'))
        for col in ['dano_observado', 'dano_evaluable', 'dano_detectado',
                    'dano_no_detectado', 'dano_sin_evaluacion']:
            d[col] = g.groupby('fecha')[col].any().reindex(d.index, fill_value=False)
        d['bit'], d['tipo_dano'] = bit, tipo
        detalle.append(d.reset_index())
        n = len(d)
        ne, nd = int(g.dano_evaluable.sum()), int(g.dano_detectado.sum())
        resumen.append(dict(bit=bit, tipo_dano=tipo, n_dias=n,
            dias_vulnerables_observados=int(d.dano_observado.sum()),
            dias_vulnerables_evaluables=int(d.dano_evaluable.sum()),
            dias_dano_no_detectado=int(d.dano_no_detectado.sum()),
            dias_con_dano_sin_evaluacion=int(d.dano_sin_evaluacion.sum()),
            pct_dias_vulnerables_evaluables=100*d.dano_evaluable.mean(),
            pct_dias_dano_no_detectado=100*d.dano_no_detectado.mean(),
            ataques_daninos_evaluables=ne, ataques_daninos_detectados=nd,
            deteccion_dano_pct=100*nd/ne if ne else np.nan))
    return pd.DataFrame(resumen), pd.concat(detalle, ignore_index=True)
