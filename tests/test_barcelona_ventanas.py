import numpy as np
import pandas as pd

from experiments.barcelona.preparar_ventanas import (
    ajustar, bloque_paraad, matrices, perfil_local, preparar, ventana_l0, ventana_v4)


def ejemplo(inicio='2015-01-01', dias=18):
    idx = pd.date_range(inicio, periods=dias * 24, freq='h', tz='UTC')
    codes = ['A', 'B', 'C', 'D', 'E']
    v = pd.DataFrame(np.arange(len(idx) * 5).reshape(-1, 5).astype(float), index=idx, columns=codes)
    loc = idx.tz_convert('Europe/Madrid')
    reloj = pd.DataFrame(dict(hora_local=loc.hour, hora_sin=np.sin(2 * np.pi * loc.hour / 24),
                             hora_cos=np.cos(2 * np.pi * loc.hour / 24)), index=idx)
    vec = {s: [t for t in codes if t != s] for s in codes}
    return v, reloj, vec


def test_recortes_sin_futuro_y_objetivo_excluido_solo_en_v4():
    v, reloj, vec = ejemplo()
    base = perfil_local(v)
    _, z, F = matrices(v, base, reloj, vec, 2015)
    mask = v.notna().to_numpy(np.float32)
    hora = reloj[['hora_sin', 'hora_cos']].to_numpy(np.float32)
    x4 = ventana_v4(z, mask, hora, 0, [30])
    np.testing.assert_array_equal(x4[0, :, :4], z[6:30, 1:])
    x0 = ventana_l0(F, list(v), vec, 'A', [30])
    np.testing.assert_array_equal(x0[0, :, 0], F[7:31, 0])
    zp = z.copy(); zp[30, 0] += 100
    np.testing.assert_array_equal(x4, ventana_v4(zp, mask, hora, 0, [30]))
    xp, mp = bloque_paraad(z, mask, [24])
    np.testing.assert_array_equal(xp[0], z[24:48].T)
    assert mp.all()


def test_perfil_causal_no_usa_presente_ni_futuro():
    v, _, _ = ejemplo()
    b = perfil_local(v)
    cambiado = v.copy(); cambiado.iloc[72:] += 100000
    pd.testing.assert_frame_equal(b.iloc[:73], perfil_local(cambiado).iloc[:73], check_exact=True)
    # A la misma hora, los 14 días previos; no sólo días con datos.
    v.iloc[24:48] = np.nan
    b = perfil_local(v)
    assert b.iloc[16 * 24, 0] == v.iloc[np.arange(2, 16) * 24, 0].mean()


def test_escala_no_usa_validacion_o_examen():
    v, _, vec = ejemplo('2015-12-25', 18)
    base = perfil_local(v)
    esc, _, _ = ajustar(v, base, vec, 2015)
    cambiado = v.copy(); cambiado.loc[cambiado.index.year >= 2016] *= 1000
    esc2, _, _ = ajustar(cambiado, perfil_local(cambiado), vec, 2015)
    pd.testing.assert_frame_equal(esc, esc2, check_exact=True)


def test_hueco_no_se_comprime_y_contexto_previo_pasa_de_etapa():
    v, reloj, _ = ejemplo('2015-12-30', 4)
    filas = []
    for s in v:
        for i, t in enumerate(v.index):
            filas.append(dict(timestamp_utc=t, codi_eoi=s, o3=v.loc[t, s],
                              excluida_cambio_reloj=i == 30, **reloj.loc[t].to_dict()))
    r = pd.DataFrame(filas)
    r.loc[r.excluida_cambio_reloj, 'o3'] = np.nan
    vv, _, _, l0, v4, d = preparar(r, list(v))
    assert len(vv) == len(v)
    # V4 necesita t−24..t−1 y L0 t−23..t: límites distintos tras exclusión.
    assert not l0.iloc[53].any() and l0.iloc[54].all()
    assert not v4.iloc[54].any() and v4.iloc[55].all()
    assert v4.iloc[72].all()  # Contexto de diciembre permitido en enero.
    assert d[d.dia_utc == pd.Timestamp('2016-01-02', tz='UTC')].comun.all()


def test_faltante_ordinario_conserva_mascara_y_dia_con_12_horas():
    v, reloj, _ = ejemplo(dias=4)
    filas = []
    v.iloc[48:60, 0] = np.nan
    for s in v:
        for t in v.index:
            filas.append(dict(timestamp_utc=t, codi_eoi=s, o3=v.loc[t, s],
                              excluida_cambio_reloj=False, **reloj.loc[t].to_dict()))
    _, _, _, _, _, d = preparar(pd.DataFrame(filas), list(v))
    caso = d[(d.estacion == 'A') & (d.dia_utc == v.index[48])].iloc[0]
    assert caso.horas_observadas == 12 and caso.comun
