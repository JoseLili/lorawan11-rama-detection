import numpy as np
import pandas as pd
import pytest

from experiments.cayenne_mod.flip_dirigido import POOLS, evaluar, ejemplos, indices_sorteados
from src.detect.red import contexto_diario


def contexto():
    matriz = pd.DataFrame({"CCA": [60.,28.],"AJM":[45.,45.]},
                          index=pd.to_datetime(["2025-01-01","2025-01-02"]))
    c = contexto_diario(matriz)
    c["base_ppb"] = c["perfil_ppb"] = 0.
    c["predicho_ppb"] = c.original_ppb
    c["umbral_ppb"] = 20.
    c["evaluable"] = True
    return c


def test_ejemplos_y_probabilidades_del_grupo():
    e = ejemplos()
    for formato, recibido in [("base",28),("A",44),("B",52)]:
        t = e.query("original == 60 and formato == @formato")
        assert t.recibido.eq(recibido).all()
        assert np.isclose(t.prob_eleccion.sum(),1)
    b = e.query("original == 28 and formato == 'B'")
    assert (b.recibido==20).sum()==2
    assert (b.recibido==36).sum()==4
    assert np.isclose(b.loc[b.recibido==20,'prob_eleccion'].sum(),1/3)


def test_un_sorteo_por_mensaje_y_peso_constante():
    c = contexto()
    r = evaluar(c,True)
    assert len(r['sorteo'])==3*len(c)
    for f, pool in POOLS.items():
        t = r['sorteo'].query("formato == @f")
        assert len(t)==len(c)
        assert set(t.bit_elegido)<=set(pool)
        assert t.delta_ppb.abs().eq({'base':32,'A':16,'B':8}[f]).all()
    r2 = evaluar(c,True)
    for k in r:
        pd.testing.assert_frame_equal(r[k],r2[k],check_exact=True)


def test_esperanza_ponderada_no_suma_seis_intentos():
    r = evaluar(contexto(),True)
    for row in r['resumen'].itertuples():
        op = r['por_opcion'].query("formato == @row.formato and tipo_dano == @row.tipo_dano")
        assert np.isclose(row.daninos_esperados,(op.daninos*op.prob_eleccion).sum())
        assert np.isclose(row.escapan_esperados,(op.escapan*op.prob_eleccion).sum())
        assert row.escapan_esperados<=row.mensajes
    # Para el ejemplo limpio 60, apagar un fragmento siempre baja de la banda
    # >58: 1 mensaje dañino esperado, incluso con seis posiciones elegibles.
    base = r['resumen'].query("formato == 'B' and tipo_dano == 'cambio_banda_red'").iloc[0]
    assert base.daninos_esperados==1
    assert base.escapan_esperados==1


def test_muestreo_cubre_opciones_y_rechaza_uniformes_invalidos():
    pool = POOLS['B']
    u = (np.arange(6)+.5)/6
    np.testing.assert_array_equal(indices_sorteados(6,pool,u),np.arange(6))
    with pytest.raises(ValueError):
        indices_sorteados(1,pool,np.array([1.]))
